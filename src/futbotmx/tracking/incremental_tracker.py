from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass
from typing import Any

from futbotmx.io.detections import Detection
from .simple_tracker import team_for_class


LIVE_TRACK_STATE_ACTIVE = "active"
LIVE_TRACK_STATE_LOST = "lost"

INCREMENTAL_JSONL_FIELDS = (
    "session_id",
    "frame",
    "timestamp_sec",
    "track_id",
    "class",
    "team",
    "x",
    "y",
    "w",
    "h",
    "center_x",
    "center_y",
    "confidence",
    "state",
    "lost_count",
)


@dataclass
class _TrackState:
    track_id: str
    class_name: str
    team: str
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    confidence: float
    first_frame: int
    last_frame: int
    state: str
    lost_count: int = 0


@dataclass(frozen=True)
class LiveTrackRow:
    session_id: str
    frame: int
    timestamp_sec: float
    track_id: str
    class_name: str
    team: str
    x: float
    y: float
    w: float
    h: float
    center_x: float
    center_y: float
    confidence: float
    state: str
    lost_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "frame": self.frame,
            "timestamp_sec": round(self.timestamp_sec, 6),
            "track_id": self.track_id,
            "class": self.class_name,
            "team": self.team,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "w": round(self.w, 4),
            "h": round(self.h, 4),
            "center_x": round(self.center_x, 4),
            "center_y": round(self.center_y, 4),
            "confidence": round(self.confidence, 6),
            "state": self.state,
            "lost_count": self.lost_count,
        }


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def detections_from_precomputed_rows(rows: list[dict[str, Any]]) -> list[Detection]:
    """Convert live_tracks.csv or tracking CSV rows to Detection list."""
    detections: list[Detection] = []
    for row in rows:
        class_name = str(row.get("class", row.get("class_name", ""))).strip()
        if not class_name:
            continue
        if "w" in row and "h" in row:
            x = float(row.get("x", 0) or 0)
            y = float(row.get("y", 0) or 0)
            w = float(row.get("w", 0) or 0)
            h = float(row.get("h", 0) or 0)
            bbox = (x, y, x + w, y + h)
            center_x = float(row.get("center_x", x + w / 2) or x + w / 2)
            center_y = float(row.get("center_y", y + h / 2) or y + h / 2)
        elif "bbox_x1" in row:
            x1 = float(row.get("bbox_x1", 0) or 0)
            y1 = float(row.get("bbox_y1", 0) or 0)
            x2 = float(row.get("bbox_x2", 0) or 0)
            y2 = float(row.get("bbox_y2", 0) or 0)
            bbox = (x1, y1, x2, y2)
            center_x = float(row.get("center_x", row.get("x", (x1 + x2) / 2)) or (x1 + x2) / 2)
            center_y = float(row.get("center_y", row.get("y", (y1 + y2) / 2)) or (y1 + y2) / 2)
        else:
            continue
        confidence = float(row.get("confidence", row.get("score", 1.0)) or 1.0)
        detections.append(
            Detection(
                class_name=class_name,
                bbox=bbox,
                centroid=(center_x, center_y),
                confidence=confidence,
            )
        )
    return detections


class IncrementalTrackerSession:
    """Stateful tracker that processes detections frame by frame without batch finalization.

    Designed for live playback: maintains active and lost tracks in memory,
    supports backward seek reset and state reconstruction from precomputed data.
    """

    def __init__(
        self,
        session_id: str,
        max_lost_frames: int = 15,
        max_distance_px: float = 80.0,
        fps: float = 30.0,
    ) -> None:
        self.session_id = session_id
        self.max_lost_frames = max_lost_frames
        self.max_distance_px = max_distance_px
        self.fps = fps
        self.current_frame: int | None = None
        self.reset_count: int = 0
        self._active: dict[str, _TrackState] = {}
        self._counters: dict[str, int] = {}
        self._emitted: list[LiveTrackRow] = []

    def update(self, frame: int, detections: list[Detection]) -> list[LiveTrackRow]:
        """Process detections for one frame; return active and lost track rows."""
        timestamp = frame / self.fps if self.fps > 0 else 0.0
        used: set[str] = set()
        matched: dict[str, Detection] = {}
        unmatched: list[Detection] = []

        for detection in detections:
            candidates = [
                (tid, _distance(detection.centroid, t.centroid))
                for tid, t in self._active.items()
                if t.class_name == detection.class_name and tid not in used
            ]
            if candidates:
                best_id, best_dist = min(candidates, key=lambda item: item[1])
                if best_dist <= self.max_distance_px:
                    used.add(best_id)
                    matched[best_id] = detection
                    continue
            unmatched.append(detection)

        next_active: dict[str, _TrackState] = {}

        for tid, detection in matched.items():
            prev = self._active[tid]
            next_active[tid] = _TrackState(
                track_id=tid,
                class_name=detection.class_name,
                team=team_for_class(detection.class_name),
                centroid=detection.centroid,
                bbox=detection.bbox,
                confidence=detection.confidence,
                first_frame=prev.first_frame,
                last_frame=frame,
                state=LIVE_TRACK_STATE_ACTIVE,
                lost_count=0,
            )

        for detection in unmatched:
            self._counters[detection.class_name] = self._counters.get(detection.class_name, 0) + 1
            tid = f"{detection.class_name}_{self._counters[detection.class_name]:02d}"
            next_active[tid] = _TrackState(
                track_id=tid,
                class_name=detection.class_name,
                team=team_for_class(detection.class_name),
                centroid=detection.centroid,
                bbox=detection.bbox,
                confidence=detection.confidence,
                first_frame=frame,
                last_frame=frame,
                state=LIVE_TRACK_STATE_ACTIVE,
                lost_count=0,
            )

        for tid, track in self._active.items():
            if tid not in next_active:
                lost_count = track.lost_count + 1
                if lost_count <= self.max_lost_frames:
                    next_active[tid] = _TrackState(
                        track_id=track.track_id,
                        class_name=track.class_name,
                        team=track.team,
                        centroid=track.centroid,
                        bbox=track.bbox,
                        confidence=track.confidence,
                        first_frame=track.first_frame,
                        last_frame=track.last_frame,
                        state=LIVE_TRACK_STATE_LOST,
                        lost_count=lost_count,
                    )

        self._active = next_active
        self.current_frame = frame

        rows = [
            _make_row(self.session_id, frame, timestamp, track)
            for track in sorted(self._active.values(), key=lambda t: t.track_id)
        ]
        self._emitted.extend(rows)
        return rows

    def seek(self, target_frame: int) -> bool:
        """Reset tracker state when seeking backward. Returns True if reset occurred."""
        if self.current_frame is not None and target_frame < self.current_frame:
            self._reset_state()
            return True
        return False

    def rebuild_from_precomputed(
        self,
        tracks_by_frame: dict[int, list[dict[str, Any]]],
        up_to_frame: int,
    ) -> list[LiveTrackRow]:
        """Reconstruct tracker state by replaying precomputed tracks up to a given frame."""
        self._reset_state()
        all_rows: list[LiveTrackRow] = []
        for frame in sorted(f for f in tracks_by_frame if f <= up_to_frame):
            detections = detections_from_precomputed_rows(tracks_by_frame[frame])
            all_rows.extend(self.update(frame, detections))
        return all_rows

    def snapshot(self) -> dict[str, Any]:
        """Export current tracker state dict for debugging."""
        return {
            "session_id": self.session_id,
            "current_frame": self.current_frame,
            "reset_count": self.reset_count,
            "active_count": sum(1 for t in self._active.values() if t.state == LIVE_TRACK_STATE_ACTIVE),
            "lost_count": sum(1 for t in self._active.values() if t.state == LIVE_TRACK_STATE_LOST),
            "total_emitted_rows": len(self._emitted),
            "tracks": [
                {
                    "track_id": t.track_id,
                    "class_name": t.class_name,
                    "team": t.team,
                    "state": t.state,
                    "lost_count": t.lost_count,
                    "first_frame": t.first_frame,
                    "last_frame": t.last_frame,
                    "centroid": list(t.centroid),
                    "confidence": round(t.confidence, 6),
                }
                for t in sorted(self._active.values(), key=lambda t: t.track_id)
            ],
        }

    def compare_with_batch(
        self,
        batch_tracks: list[dict[str, Any]],
        match_distance_px: float = 50.0,
    ) -> dict[str, Any]:
        """Compare incremental output against batch tracks by centroid proximity."""
        emitted_active = [r for r in self._emitted if r.state == LIVE_TRACK_STATE_ACTIVE]
        emitted_by_frame: dict[int, list[LiveTrackRow]] = {}
        for row in emitted_active:
            emitted_by_frame.setdefault(row.frame, []).append(row)

        batch_by_frame: dict[int, list[dict[str, Any]]] = {}
        for track in batch_tracks:
            frame = int(float(track.get("frame", 0)))
            batch_by_frame.setdefault(frame, []).append(track)

        common_frames = sorted(set(emitted_by_frame) & set(batch_by_frame))
        matched = 0

        for frame in common_frames:
            e_rows = emitted_by_frame[frame]
            b_rows = batch_by_frame[frame]
            used_batch: set[int] = set()
            for e_row in e_rows:
                for b_idx, b_track in enumerate(b_rows):
                    if b_idx in used_batch:
                        continue
                    b_cx = float(b_track.get("center_x", b_track.get("x", 0)) or 0)
                    b_cy = float(b_track.get("center_y", b_track.get("y", 0)) or 0)
                    b_class = str(b_track.get("class", b_track.get("class_name", "")))
                    if (
                        e_row.class_name == b_class
                        and _distance((e_row.center_x, e_row.center_y), (b_cx, b_cy)) <= match_distance_px
                    ):
                        matched += 1
                        used_batch.add(b_idx)
                        break

        total_emitted = len(emitted_active)
        total_batch = sum(len(rows) for rows in batch_by_frame.values())
        return {
            "session_id": self.session_id,
            "emitted_frames": len(emitted_by_frame),
            "batch_frames": len(batch_by_frame),
            "common_frames": len(common_frames),
            "total_emitted_active_rows": total_emitted,
            "total_batch_rows": total_batch,
            "matched_detections": matched,
            "match_rate": round(matched / max(1, total_emitted), 4),
            "batch_coverage": round(matched / max(1, total_batch), 4),
            "notes": (
                "Matching by centroid proximity and class name. "
                "Incremental IDs differ from batch IDs; match_rate reflects spatial overlap, not ID continuity."
            ),
        }

    def emit_jsonl(self) -> str:
        """Return all emitted rows as JSONL text."""
        lines = [
            json.dumps(row.as_dict(), ensure_ascii=True, separators=(",", ":"))
            for row in self._emitted
        ]
        return "\n".join(lines) + ("\n" if lines else "")

    def export_csv_rows(self) -> list[dict[str, Any]]:
        """Return all emitted rows as a list of dicts."""
        return [row.as_dict() for row in self._emitted]

    def export_csv_text(self) -> str:
        """Return all emitted rows as CSV text with header."""
        rows = self.export_csv_rows()
        if not rows:
            return ""
        handle = io.StringIO()
        writer = csv.DictWriter(handle, fieldnames=list(INCREMENTAL_JSONL_FIELDS), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in INCREMENTAL_JSONL_FIELDS})
        return handle.getvalue()

    def _reset_state(self) -> None:
        self._active = {}
        self._counters = {}
        self._emitted = []
        self.current_frame = None
        self.reset_count += 1


def _make_row(session_id: str, frame: int, timestamp: float, track: _TrackState) -> LiveTrackRow:
    x1, y1, x2, y2 = track.bbox
    return LiveTrackRow(
        session_id=session_id,
        frame=frame,
        timestamp_sec=timestamp,
        track_id=track.track_id,
        class_name=track.class_name,
        team=track.team,
        x=x1,
        y=y1,
        w=x2 - x1,
        h=y2 - y1,
        center_x=track.centroid[0],
        center_y=track.centroid[1],
        confidence=track.confidence,
        state=track.state,
        lost_count=track.lost_count,
    )
