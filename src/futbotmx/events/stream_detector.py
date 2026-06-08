from __future__ import annotations

import io
import csv
import json
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any


RULE_VERSION = "stream_event_detector_v0.1"

STREAM_EVENT_STATUS_CANDIDATE = "candidate"
STREAM_EVENT_STATUS_PROVISIONAL = "provisional"
STREAM_EVENT_STATUS_CONFIRMED = "confirmed"
STREAM_EVENT_STATUS_DISCARDED = "discarded"

STREAM_EVENT_LABELS = (
    "possession_candidate",
    "shot_approximate",
    "pass_simple",
    "collision_dispute",
    "highlight_provisional",
)

STREAM_EVENT_JSONL_FIELDS = (
    "event_id",
    "label",
    "start_frame",
    "end_frame",
    "start_time_sec",
    "end_time_sec",
    "confidence",
    "status",
    "clip_id",
    "track_ids",
    "team",
    "zone",
    "reason",
    "source_event_ids",
    "session_id",
    "rule_version",
    "last_updated_frame",
)

_BALL_CLASS_NAMES = {"ball"}
_ROBOT_SUBSTRINGS = {"robot", "ally", "opponent"}


def _is_ball(row: dict[str, Any]) -> bool:
    cls = str(row.get("class", row.get("class_name", ""))).lower()
    return cls in _BALL_CLASS_NAMES


def _is_robot(row: dict[str, Any]) -> bool:
    cls = str(row.get("class", row.get("class_name", ""))).lower()
    return any(sub in cls for sub in _ROBOT_SUBSTRINGS)


def _cx(row: dict[str, Any]) -> float:
    return float(row.get("center_x", row.get("x", 0)) or 0)


def _cy(row: dict[str, Any]) -> float:
    return float(row.get("center_y", row.get("y", 0)) or 0)


def _track_id(row: dict[str, Any]) -> str:
    return str(row.get("track_id", ""))


def _team(row: dict[str, Any]) -> str:
    return str(row.get("team", "unknown"))


def _dist(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(_cx(a) - _cx(b), _cy(a) - _cy(b))


def _zone(row: dict[str, Any], field_width: float) -> str:
    x = _cx(row)
    if x < field_width / 3:
        return "defensive_third"
    if x < 2 * field_width / 3:
        return "middle_third"
    return "attacking_third"


@dataclass
class StreamEventCandidate:
    event_id: str
    label: str
    start_frame: int
    end_frame: int
    clip_id: str
    team: str
    primary_track_id: str
    secondary_track_ids: list[str]
    zone: str
    confidence: float
    status: str
    reason: str
    session_id: str
    fps: float
    source_event_ids: list[str] = field(default_factory=list)
    last_updated_frame: int = 0

    @property
    def duration_frames(self) -> int:
        return max(1, self.end_frame - self.start_frame + 1)

    @property
    def start_time_sec(self) -> float:
        return round(self.start_frame / self.fps, 6) if self.fps > 0 else 0.0

    @property
    def end_time_sec(self) -> float:
        return round(self.end_frame / self.fps, 6) if self.fps > 0 else 0.0

    def update_end(self, frame: int, confidence: float | None = None, reason: str | None = None) -> None:
        self.end_frame = frame
        self.last_updated_frame = frame
        if confidence is not None:
            self.confidence = confidence
        if reason is not None:
            self.reason = reason

    def promote(self) -> None:
        if self.status == STREAM_EVENT_STATUS_CANDIDATE:
            self.status = STREAM_EVENT_STATUS_PROVISIONAL
        elif self.status == STREAM_EVENT_STATUS_PROVISIONAL:
            self.status = STREAM_EVENT_STATUS_CONFIRMED

    def confirm(self) -> None:
        self.status = STREAM_EVENT_STATUS_CONFIRMED

    def discard(self, reason: str = "") -> None:
        self.status = STREAM_EVENT_STATUS_DISCARDED
        if reason:
            self.reason = reason

    def as_dict(self) -> dict[str, Any]:
        all_ids = [self.primary_track_id, *[t for t in self.secondary_track_ids if t != self.primary_track_id]]
        return {
            "event_id": self.event_id,
            "label": self.label,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "start_time_sec": self.start_time_sec,
            "end_time_sec": self.end_time_sec,
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "clip_id": self.clip_id,
            "track_ids": [t for t in all_ids if t],
            "team": self.team,
            "zone": self.zone,
            "reason": self.reason,
            "source_event_ids": self.source_event_ids,
            "session_id": self.session_id,
            "rule_version": RULE_VERSION,
            "last_updated_frame": self.last_updated_frame,
        }


@dataclass
class StreamDetectorConfig:
    session_id: str = "default"
    clip_id: str = ""
    fps: float = 30.0
    window_frames: int = 30
    possession_distance_px: float = 80.0
    possession_min_frames: int = 5
    possession_confirm_frames: int = 15
    max_pass_gap_frames: int = 12
    collision_distance_px: float = 50.0
    collision_min_frames: int = 4
    shot_min_speed_px_per_sec: float = 300.0
    highlight_speed_threshold_px_per_sec: float = 450.0
    field_width: float = 1920.0
    field_height: float = 1080.0


class _FrameBuffer:
    """Rolling window buffer of track rows indexed by frame."""

    def __init__(self, window_frames: int) -> None:
        self._window = window_frames
        self._frames: deque[tuple[int, list[dict[str, Any]]]] = deque()

    def push(self, frame: int, rows: list[dict[str, Any]]) -> None:
        self._frames.append((frame, list(rows)))
        cutoff = frame - self._window + 1
        while self._frames and self._frames[0][0] < cutoff:
            self._frames.popleft()

    def ball_history(self) -> list[tuple[int, dict[str, Any]]]:
        return [(f, row) for f, rows in self._frames for row in rows if _is_ball(row)]

    def robot_history(self) -> list[tuple[int, dict[str, Any]]]:
        return [(f, row) for f, rows in self._frames for row in rows if _is_robot(row)]

    def possession_history(
        self,
        possession_distance_px: float,
    ) -> list[tuple[int, str, str, float]]:
        """Return (frame, robot_track_id, team, distance) for frames where a robot has the ball."""
        result: list[tuple[int, str, str, float]] = []
        for frame, rows in self._frames:
            balls = [r for r in rows if _is_ball(r)]
            robots = [r for r in rows if _is_robot(r)]
            if not balls or not robots:
                continue
            ball = balls[0]
            closest = min(robots, key=lambda r: _dist(ball, r))
            d = _dist(ball, closest)
            if d <= possession_distance_px:
                result.append((frame, _track_id(closest), _team(closest), d))
        return result

    def proximity_pairs(
        self,
        collision_distance_px: float,
    ) -> list[tuple[int, str, str, float]]:
        """Return (frame, track_a, track_b, distance) for robot pairs within collision distance."""
        result: list[tuple[int, str, str, float]] = []
        for frame, rows in self._frames:
            robots = [r for r in rows if _is_robot(r)]
            for i, a in enumerate(robots):
                for b in robots[i + 1 :]:
                    d = _dist(a, b)
                    if d <= collision_distance_px:
                        ta, tb = sorted((_track_id(a), _track_id(b)))
                        result.append((frame, ta, tb, d))
        return result


class StreamEventDetector:
    """Detects football events in streaming mode using a rolling window of track rows.

    Processes one frame at a time via push_frame() and maintains event lifecycle:
    candidate → provisional → confirmed, or candidate → discarded.
    Designed for live playback without waiting for the full batch analysis.
    """

    def __init__(self, config: StreamDetectorConfig | None = None) -> None:
        self._cfg = config or StreamDetectorConfig()
        self._buffer = _FrameBuffer(self._cfg.window_frames)
        self._counter = 0
        self._open: dict[str, StreamEventCandidate] = {}
        self._closed: list[StreamEventCandidate] = []
        self._last_possession_robot: str | None = None
        self._last_possession_team: str | None = None
        self._last_possession_end_frame: int | None = None
        self._last_possession_event_id: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push_frame(self, frame: int, rows: list[dict[str, Any]]) -> list[StreamEventCandidate]:
        """Process one frame; return all non-discarded events visible at this frame."""
        self._buffer.push(frame, rows)
        self._update_possession(frame, rows)
        self._update_collisions(frame, rows)
        self._update_shots(frame)
        return self.visible_events(frame)

    def visible_events(self, frame: int) -> list[StreamEventCandidate]:
        """Return open events plus recently closed events visible at this frame."""
        visible: list[StreamEventCandidate] = list(self._open.values())
        for evt in self._closed:
            if evt.status != STREAM_EVENT_STATUS_DISCARDED and evt.end_frame >= frame - self._cfg.window_frames:
                visible.append(evt)
        return [e for e in visible if e.status != STREAM_EVENT_STATUS_DISCARDED]

    def all_events(self) -> list[StreamEventCandidate]:
        """Return all events including discarded."""
        return list(self._open.values()) + self._closed

    def emit_jsonl(self) -> str:
        """Return all non-discarded events as JSONL text (one JSON object per line)."""
        events = [e for e in self.all_events() if e.status != STREAM_EVENT_STATUS_DISCARDED]
        lines = [json.dumps(e.as_dict(), ensure_ascii=True, separators=(",", ":")) for e in events]
        return "\n".join(lines) + ("\n" if lines else "")

    def export_events(self) -> list[dict[str, Any]]:
        """Return all non-discarded events as list of dicts."""
        return [e.as_dict() for e in self.all_events() if e.status != STREAM_EVENT_STATUS_DISCARDED]

    def export_csv_text(self) -> str:
        """Return all non-discarded events as CSV text."""
        rows = self.export_events()
        if not rows:
            return ""
        handle = io.StringIO()
        writer = csv.DictWriter(handle, fieldnames=list(STREAM_EVENT_JSONL_FIELDS), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            flat = {k: ("|".join(str(x) for x in v) if isinstance(v, list) else v) for k, v in row.items()}
            writer.writerow({f: flat.get(f, "") for f in STREAM_EVENT_JSONL_FIELDS})
        return handle.getvalue()

    def snapshot(self) -> dict[str, Any]:
        """Export detector state summary for debugging."""
        all_ev = self.all_events()
        by_status: dict[str, int] = {
            STREAM_EVENT_STATUS_CANDIDATE: 0,
            STREAM_EVENT_STATUS_PROVISIONAL: 0,
            STREAM_EVENT_STATUS_CONFIRMED: 0,
            STREAM_EVENT_STATUS_DISCARDED: 0,
        }
        for e in all_ev:
            by_status[e.status] = by_status.get(e.status, 0) + 1
        return {
            "session_id": self._cfg.session_id,
            "open_event_count": len(self._open),
            "closed_event_count": len(self._closed),
            "total_events": len(all_ev),
            "by_status": by_status,
            "last_possession_robot": self._last_possession_robot,
            "last_possession_team": self._last_possession_team,
        }

    # ------------------------------------------------------------------
    # Possession detection (Tarea 30.1 + 30.2)
    # ------------------------------------------------------------------

    def _update_possession(self, frame: int, rows: list[dict[str, Any]]) -> None:
        balls = [r for r in rows if _is_ball(r)]
        robots = [r for r in rows if _is_robot(r)]
        cfg = self._cfg

        current_robot: str | None = None
        current_team: str | None = None
        current_zone: str = "unknown"

        if balls and robots:
            ball = balls[0]
            closest = min(robots, key=lambda r: _dist(ball, r))
            if _dist(ball, closest) <= cfg.possession_distance_px:
                current_robot = _track_id(closest)
                current_team = _team(closest)
                current_zone = _zone(ball, cfg.field_width)

        poss_key = "possession"

        if current_robot:
            if poss_key in self._open:
                evt = self._open[poss_key]
                if evt.primary_track_id == current_robot:
                    evt.update_end(frame)
                    if evt.duration_frames >= cfg.possession_confirm_frames:
                        evt.confirm()
                    elif evt.duration_frames >= cfg.possession_min_frames:
                        evt.promote()
                else:
                    self._close_possession(frame)
                    self._maybe_emit_pass(frame, current_robot, current_team or "unknown", current_zone)
                    self._open_possession(frame, current_robot, current_team or "unknown", current_zone)
            else:
                self._open_possession(frame, current_robot, current_team or "unknown", current_zone)
        else:
            if poss_key in self._open:
                self._close_possession(frame)

        self._last_possession_robot = current_robot
        if current_team:
            self._last_possession_team = current_team

    def _open_possession(self, frame: int, robot_id: str, team: str, zone: str) -> None:
        evt = self._new_event(
            label="possession_candidate",
            start_frame=frame,
            end_frame=frame,
            team=team,
            primary_track_id=robot_id,
            zone=zone,
            confidence=0.55,
            reason="Ball within possession distance of robot.",
            status=STREAM_EVENT_STATUS_CANDIDATE,
        )
        self._open["possession"] = evt

    def _close_possession(self, frame: int) -> None:
        evt = self._open.pop("possession", None)
        if evt is None:
            return
        if evt.duration_frames < self._cfg.possession_min_frames:
            evt.discard("Possession too short to confirm.")
        elif evt.status == STREAM_EVENT_STATUS_CANDIDATE:
            evt.promote()
        self._last_possession_end_frame = evt.end_frame
        self._last_possession_event_id = evt.event_id
        self._closed.append(evt)

    def _maybe_emit_pass(self, frame: int, new_robot: str, new_team: str, zone: str) -> None:
        if self._last_possession_end_frame is None:
            return
        gap = frame - self._last_possession_end_frame
        if gap > self._cfg.max_pass_gap_frames:
            return
        prev_evt = next(
            (e for e in reversed(self._closed) if e.label == "possession_candidate" and e.status != STREAM_EVENT_STATUS_DISCARDED),
            None,
        )
        if prev_evt is None:
            return
        same_team = prev_evt.team == new_team and new_team not in ("unknown", "neutral", "")
        label = "pass_simple" if same_team else "collision_dispute"
        confidence = 0.60 if same_team else 0.50
        reason = (
            f"Possession moved from {prev_evt.primary_track_id} to {new_robot} (same team {new_team}) in {gap} frames."
            if same_team
            else f"Possession changed between different teams in {gap} frames."
        )
        evt = self._new_event(
            label=label,
            start_frame=prev_evt.end_frame,
            end_frame=frame,
            team=new_team if same_team else "unknown",
            primary_track_id=prev_evt.primary_track_id,
            secondary_track_ids=[new_robot],
            zone=zone,
            confidence=confidence,
            reason=reason,
            status=STREAM_EVENT_STATUS_PROVISIONAL if same_team else STREAM_EVENT_STATUS_CANDIDATE,
            source_event_ids=[prev_evt.event_id] + ([self._last_possession_event_id] if self._last_possession_event_id else []),
        )
        self._closed.append(evt)

    # ------------------------------------------------------------------
    # Collision detection (Tarea 30.2)
    # ------------------------------------------------------------------

    def _update_collisions(self, frame: int, rows: list[dict[str, Any]]) -> None:
        robots = [r for r in rows if _is_robot(r)]
        cfg = self._cfg
        active_pairs: set[str] = set()

        for i, a in enumerate(robots):
            for b in robots[i + 1 :]:
                d = _dist(a, b)
                if d > cfg.collision_distance_px:
                    continue
                ta, tb = sorted((_track_id(a), _track_id(b)))
                key = f"collision:{ta}:{tb}"
                active_pairs.add(key)
                if key in self._open:
                    evt = self._open[key]
                    evt.update_end(frame)
                    if evt.duration_frames >= cfg.collision_min_frames:
                        if evt.status == STREAM_EVENT_STATUS_CANDIDATE:
                            evt.promote()
                        if evt.duration_frames >= cfg.collision_min_frames * 2:
                            evt.confirm()
                else:
                    evt = self._new_event(
                        label="collision_dispute",
                        start_frame=frame,
                        end_frame=frame,
                        team="unknown",
                        primary_track_id=ta,
                        secondary_track_ids=[tb],
                        zone="unknown",
                        confidence=0.45,
                        reason=f"Robots {ta} and {tb} within collision distance.",
                        status=STREAM_EVENT_STATUS_CANDIDATE,
                    )
                    self._open[key] = evt

        for key in [k for k in list(self._open) if k.startswith("collision:") and k not in active_pairs]:
            evt = self._open.pop(key)
            if evt.duration_frames < self._cfg.collision_min_frames:
                evt.discard("Collision too brief.")
            elif evt.status == STREAM_EVENT_STATUS_CANDIDATE:
                evt.promote()
            self._closed.append(evt)

    # ------------------------------------------------------------------
    # Shot detection (Tarea 30.2)
    # ------------------------------------------------------------------

    def _update_shots(self, frame: int) -> None:
        cfg = self._cfg
        ball_history = self._buffer.ball_history()
        if len(ball_history) < 2:
            return

        frame_b, ball_b = ball_history[-1]
        frame_a, ball_a = ball_history[-2]
        if frame_b != frame:
            return

        dt_frames = max(1, frame_b - frame_a)
        dt_sec = dt_frames / cfg.fps if cfg.fps > 0 else 1.0
        speed = _dist(ball_a, ball_b) / dt_sec
        ball_id = _track_id(ball_b)
        shot_zone = _zone(ball_b, cfg.field_width)

        if speed >= cfg.shot_min_speed_px_per_sec:
            shot_key = "shot"
            if shot_key in self._open:
                evt = self._open[shot_key]
                evt.update_end(frame, confidence=min(0.85, evt.confidence + 0.05))
                if evt.status == STREAM_EVENT_STATUS_CANDIDATE:
                    evt.confirm()
            else:
                evt = self._new_event(
                    label="shot_approximate",
                    start_frame=frame_a,
                    end_frame=frame,
                    team="unknown",
                    primary_track_id=ball_id,
                    zone=shot_zone,
                    confidence=0.60,
                    reason=f"Ball speed {speed:.0f} px/s exceeds shot threshold {cfg.shot_min_speed_px_per_sec:.0f} px/s.",
                    status=STREAM_EVENT_STATUS_CANDIDATE,
                )
                self._open[shot_key] = evt
            if speed >= cfg.highlight_speed_threshold_px_per_sec:
                self._emit_highlight(frame, f"shot_approximate speed {speed:.0f} px/s", ball_id, shot_zone)
        else:
            if "shot" in self._open:
                evt = self._open.pop("shot")
                evt.confirm()
                self._closed.append(evt)

    # ------------------------------------------------------------------
    # Highlight detection (Tarea 30.2)
    # ------------------------------------------------------------------

    def _emit_highlight(
        self,
        frame: int,
        reason: str,
        primary_track_id: str,
        zone: str,
        source_event_ids: list[str] | None = None,
    ) -> None:
        hl_key = f"highlight:{frame}"
        if hl_key in self._open:
            return
        evt = self._new_event(
            label="highlight_provisional",
            start_frame=max(0, frame - 3),
            end_frame=frame,
            team="unknown",
            primary_track_id=primary_track_id,
            zone=zone,
            confidence=0.55,
            reason=reason,
            status=STREAM_EVENT_STATUS_PROVISIONAL,
            source_event_ids=source_event_ids or [],
        )
        self._open[hl_key] = evt
        evt.confirm()
        self._closed.append(self._open.pop(hl_key))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_event(
        self,
        label: str,
        start_frame: int,
        end_frame: int,
        team: str,
        primary_track_id: str,
        zone: str,
        confidence: float,
        reason: str,
        status: str,
        secondary_track_ids: list[str] | None = None,
        source_event_ids: list[str] | None = None,
    ) -> StreamEventCandidate:
        self._counter += 1
        return StreamEventCandidate(
            event_id=f"stream_evt_{self._counter:06d}",
            label=label,
            start_frame=start_frame,
            end_frame=end_frame,
            clip_id=self._cfg.clip_id,
            team=team,
            primary_track_id=primary_track_id,
            secondary_track_ids=secondary_track_ids or [],
            zone=zone,
            confidence=confidence,
            status=status,
            reason=reason,
            session_id=self._cfg.session_id,
            fps=self._cfg.fps,
            source_event_ids=source_event_ids or [],
            last_updated_frame=end_frame,
        )
