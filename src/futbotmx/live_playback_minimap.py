from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any


RULE_VERSION = "live_minimap_v0.1"

MINIMAP_QUALITY_RECTIFIED = "rectified"
MINIMAP_QUALITY_FALLBACK = "fallback"
MINIMAP_QUALITY_UNAVAILABLE = "unavailable"

MINIMAP_CALIBRATION_MIN_CONFIDENCE = 0.30

MINIMAP_POINT_FIELDS = (
    "track_id",
    "class",
    "team",
    "x_norm",
    "y_norm",
    "quality",
    "state",
    "confidence",
)

_BALL_CLASSES = {"ball"}
_ROBOT_SUBSTRINGS = ("robot", "ally", "opponent")


def _is_ball(row: dict[str, Any]) -> bool:
    return str(row.get("class", row.get("class_name", ""))).lower() in _BALL_CLASSES


def _is_robot(row: dict[str, Any]) -> bool:
    cls = str(row.get("class", row.get("class_name", ""))).lower()
    return any(sub in cls for sub in _ROBOT_SUBSTRINGS)


def _cx(row: dict[str, Any]) -> float:
    return float(row.get("center_x", row.get("x", 0)) or 0)


def _cy(row: dict[str, Any]) -> float:
    return float(row.get("center_y", row.get("y", 0)) or 0)


def _track_id(row: dict[str, Any]) -> str:
    return str(row.get("track_id", ""))


def _clip(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _apply_homography(H: tuple, x: float, y: float) -> tuple[float, float]:
    """Apply 3x3 homography tuple-of-rows to point (x, y). Pure Python, no numpy."""
    w = H[0][0] * x + H[0][1] * y + H[0][2]
    q = H[1][0] * x + H[1][1] * y + H[1][2]
    d = H[2][0] * x + H[2][1] * y + H[2][2]
    if abs(d) < 1e-12:
        raise ValueError("Homography produced a point at infinity")
    return w / d, q / d


def _norm_zone(x_norm: float, y_norm: float, zone_axis: str = "y") -> str:
    pos = y_norm if zone_axis == "y" else x_norm
    if pos < 1.0 / 3.0:
        return "defensive_third"
    if pos < 2.0 / 3.0:
        return "middle_third"
    return "attacking_third"


# ---------------------------------------------------------------------------
# Calibration wrapper
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MinimapCalibration:
    """Wraps calibration data for live minimap coordinate transformation.

    Supports:
    - Rectified: homography from ClipCalibration (usable status)
    - Fallback: normalize by image dimensions when homography is unavailable
    - Unavailable: no spatial data; all points marked as unreliable
    """

    status: str
    confidence: float
    image_width: float
    image_height: float
    homography: tuple | None
    source: str

    @classmethod
    def from_clip_calibration(cls, calibration: Any) -> "MinimapCalibration":
        """Build from a level3 ClipCalibration object."""
        usable = getattr(calibration, "usable", False)
        return cls(
            status="rectified" if usable else "fallback",
            confidence=float(getattr(calibration, "confidence", 0.0)),
            image_width=float(getattr(calibration, "image_width", 1920)),
            image_height=float(getattr(calibration, "image_height", 1080)),
            homography=getattr(calibration, "homography", None) if usable else None,
            source=str(getattr(calibration, "calibration_id", "clip_calibration")),
        )

    @classmethod
    def from_homography(
        cls,
        homography: tuple,
        image_width: float,
        image_height: float,
        confidence: float,
        source: str = "manual",
    ) -> "MinimapCalibration":
        """Build from an explicit homography matrix (tuple of rows)."""
        return cls(
            status="rectified",
            confidence=confidence,
            image_width=image_width,
            image_height=image_height,
            homography=homography,
            source=source,
        )

    @classmethod
    def from_image_extent(
        cls,
        image_width: float,
        image_height: float,
        source: str = "image_extent_fallback",
    ) -> "MinimapCalibration":
        """Fallback calibration: normalize pixel coordinates by image dimensions."""
        return cls(
            status=MINIMAP_QUALITY_FALLBACK,
            confidence=0.0,
            image_width=image_width,
            image_height=image_height,
            homography=None,
            source=source,
        )

    @classmethod
    def unavailable(cls) -> "MinimapCalibration":
        """No spatial data; all points will be marked unavailable."""
        return cls(
            status=MINIMAP_QUALITY_UNAVAILABLE,
            confidence=0.0,
            image_width=0.0,
            image_height=0.0,
            homography=None,
            source="none",
        )

    def transform(self, cx: float, cy: float) -> tuple[float, float, str]:
        """Convert pixel (cx, cy) → (x_norm, y_norm, quality).

        If x_norm / y_norm are already known (precomputed tracks), skip this
        and pass them directly to the minimap point builder.
        """
        if self.homography is not None:
            try:
                x_norm, y_norm = _apply_homography(self.homography, cx, cy)
                return _clip(x_norm), _clip(y_norm), MINIMAP_QUALITY_RECTIFIED
            except ValueError:
                pass
        if self.image_width > 0 and self.image_height > 0:
            x_norm = _clip(cx / self.image_width)
            y_norm = _clip(cy / self.image_height)
            return x_norm, y_norm, MINIMAP_QUALITY_FALLBACK
        return 0.5, 0.5, MINIMAP_QUALITY_UNAVAILABLE

    @property
    def reliable(self) -> bool:
        """True when calibration confidence meets the minimum threshold."""
        return self.status == MINIMAP_QUALITY_RECTIFIED and self.confidence >= MINIMAP_CALIBRATION_MIN_CONFIDENCE

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence": round(self.confidence, 6),
            "image_width": self.image_width,
            "image_height": self.image_height,
            "has_homography": self.homography is not None,
            "source": self.source,
            "reliable": self.reliable,
        }


# ---------------------------------------------------------------------------
# Trail buffer
# ---------------------------------------------------------------------------

class _TrailBuffer:
    """Rolling buffer of normalized field positions per track."""

    def __init__(self, trail_length: int) -> None:
        self._trail_length = max(1, trail_length)
        self._trails: dict[str, deque[tuple[float, float]]] = {}

    def push(self, track_id: str, x_norm: float, y_norm: float) -> None:
        if track_id not in self._trails:
            self._trails[track_id] = deque(maxlen=self._trail_length)
        self._trails[track_id].append((x_norm, y_norm))

    def trail(self, track_id: str) -> list[tuple[float, float]]:
        return list(self._trails.get(track_id, []))

    def all_trails(self) -> dict[str, list[tuple[float, float]]]:
        return {tid: list(pts) for tid, pts in self._trails.items()}

    def clear(self) -> None:
        self._trails.clear()

    def prune_to(self, active_ids: set[str]) -> None:
        for tid in list(self._trails):
            if tid not in active_ids:
                del self._trails[tid]


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LiveMinimapFrame:
    """Minimap state for a single playback frame, ready for the UI."""

    frame: int
    timestamp_sec: float
    session_id: str
    calibration_status: str
    calibration_confidence: float
    calibration_source: str
    hide_unreliable: bool
    points: list[dict[str, Any]]
    trails: dict[str, list[tuple[float, float]]]
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame,
            "timestamp_sec": round(self.timestamp_sec, 6),
            "session_id": self.session_id,
            "rule_version": RULE_VERSION,
            "calibration": {
                "status": self.calibration_status,
                "confidence": round(self.calibration_confidence, 6),
                "source": self.calibration_source,
                "hide_unreliable": self.hide_unreliable,
            },
            "points": self.points,
            "trails": {tid: list(pts) for tid, pts in self.trails.items()},
            "metrics": self.metrics,
        }


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

@dataclass
class LiveMinimapConfig:
    session_id: str = "default"
    fps: float = 30.0
    trail_length: int = 12
    possession_distance_px: float = 80.0
    calibration_min_confidence: float = MINIMAP_CALIBRATION_MIN_CONFIDENCE
    zone_axis: str = "y"
    prune_inactive_trails: bool = True


class LiveMinimapEngine:
    """Builds minimap frames for live playback, one frame at a time.

    Responsibilities (Actividad 31):
    - 31.1: Reuses calibration / homography when available; falls back to image
      extent normalization. Maintains per-track trails in field coordinates.
    - 31.2: Computes live metrics per frame: possession by team, active zone,
      approximate ball speed (normalized field units / sec), calibration and
      tracking confidence. Hides unreliable points when calibration is absent.
    """

    def __init__(
        self,
        calibration: MinimapCalibration,
        config: LiveMinimapConfig | None = None,
    ) -> None:
        self._cal = calibration
        self._cfg = config or LiveMinimapConfig()
        self._trails = _TrailBuffer(self._cfg.trail_length)
        self._ball_history: deque[tuple[int, float, float]] = deque(maxlen=8)
        self.current_frame: int | None = None
        self.reset_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push_frame(
        self,
        frame: int,
        rows: list[dict[str, Any]],
    ) -> LiveMinimapFrame:
        """Process one frame of track rows and return a LiveMinimapFrame."""
        timestamp = frame / self._cfg.fps if self._cfg.fps > 0 else 0.0
        self.current_frame = frame

        points: list[dict[str, Any]] = []
        active_ids: set[str] = set()

        for row in rows:
            point = self._build_point(row)
            if point is None:
                continue
            tid = point["track_id"]
            active_ids.add(tid)
            x_norm = float(point["x_norm"])
            y_norm = float(point["y_norm"])
            self._trails.push(tid, x_norm, y_norm)
            if _is_ball(row):
                self._ball_history.append((frame, x_norm, y_norm))
            points.append(point)

        if self._cfg.prune_inactive_trails:
            self._trails.prune_to(active_ids)

        hide = not self._cal.reliable
        trails = self._trails.all_trails()
        metrics = self._compute_metrics(frame, rows, points)

        return LiveMinimapFrame(
            frame=frame,
            timestamp_sec=timestamp,
            session_id=self._cfg.session_id,
            calibration_status=self._cal.status,
            calibration_confidence=self._cal.confidence,
            calibration_source=self._cal.source,
            hide_unreliable=hide,
            points=points,
            trails=trails,
            metrics=metrics,
        )

    def seek(self, target_frame: int) -> bool:
        """Clear trails and ball history on backward seek. Returns True if reset."""
        if self.current_frame is not None and target_frame < self.current_frame:
            self._trails.clear()
            self._ball_history.clear()
            self.current_frame = None
            self.reset_count += 1
            return True
        return False

    def update_calibration(self, calibration: MinimapCalibration) -> None:
        """Replace calibration at runtime (e.g. when manual calibration is loaded)."""
        self._cal = calibration

    def snapshot(self) -> dict[str, Any]:
        """Export engine state for debugging."""
        return {
            "session_id": self._cfg.session_id,
            "current_frame": self.current_frame,
            "reset_count": self.reset_count,
            "trail_count": len(self._trails.all_trails()),
            "ball_history_length": len(self._ball_history),
            "calibration": self._cal.as_dict(),
        }

    # ------------------------------------------------------------------
    # Point construction (31.1: calibration + homography reuse)
    # ------------------------------------------------------------------

    def _build_point(self, row: dict[str, Any]) -> dict[str, Any] | None:
        tid = _track_id(row)
        if not tid:
            return None

        x_norm_pre = row.get("x_norm", "")
        y_norm_pre = row.get("y_norm", "")

        if x_norm_pre not in ("", None) and y_norm_pre not in ("", None):
            x_norm = _clip(float(x_norm_pre))
            y_norm = _clip(float(y_norm_pre))
            cal_conf_pre = row.get("calibration_confidence", "")
            quality_conf = float(cal_conf_pre) if cal_conf_pre not in ("", None) else self._cal.confidence
            quality = MINIMAP_QUALITY_RECTIFIED if quality_conf >= self._cfg.calibration_min_confidence else MINIMAP_QUALITY_FALLBACK
        else:
            cx = _cx(row)
            cy = _cy(row)
            x_norm, y_norm, quality = self._cal.transform(cx, cy)

        return {
            "track_id": tid,
            "class": str(row.get("class", row.get("class_name", ""))),
            "team": str(row.get("team", "unknown")),
            "x_norm": round(x_norm, 6),
            "y_norm": round(y_norm, 6),
            "quality": quality,
            "state": str(row.get("state", "active")),
            "confidence": round(float(row.get("confidence", 1.0) or 1.0), 6),
        }

    # ------------------------------------------------------------------
    # Live metrics (31.2)
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        frame: int,
        rows: list[dict[str, Any]],
        points: list[dict[str, Any]],
    ) -> dict[str, Any]:
        possession = self._possession_metric(rows)
        active_zone = self._active_zone_metric(points)
        ball_speed = self._ball_speed_metric()
        track_conf = self._tracking_confidence_metric(rows)

        return {
            "possession_team": possession["team"],
            "possession_robot_id": possession["robot_id"],
            "possession_confidence": possession["confidence"],
            "active_zone": active_zone,
            "ball_speed_norm_per_sec": round(ball_speed, 6),
            "tracking_confidence": round(track_conf, 6),
            "calibration_confidence": round(self._cal.confidence, 6),
            "calibration_reliable": self._cal.reliable,
        }

    def _possession_metric(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        balls = [r for r in rows if _is_ball(r)]
        robots = [r for r in rows if _is_robot(r)]
        if not balls or not robots:
            return {"team": "none", "robot_id": "", "confidence": 0.0}
        ball = balls[0]
        closest = min(robots, key=lambda r: math.hypot(_cx(ball) - _cx(r), _cy(ball) - _cy(r)))
        dist = math.hypot(_cx(ball) - _cx(closest), _cy(ball) - _cy(closest))
        if dist > self._cfg.possession_distance_px:
            return {"team": "none", "robot_id": "", "confidence": 0.0}
        confidence = round(max(0.0, 1.0 - dist / max(1.0, self._cfg.possession_distance_px)) * 0.8, 4)
        return {
            "team": str(closest.get("team", "unknown")),
            "robot_id": _track_id(closest),
            "confidence": confidence,
        }

    def _active_zone_metric(self, points: list[dict[str, Any]]) -> str:
        ball_points = [p for p in points if p.get("class", "").lower() == "ball"]
        if not ball_points:
            if self._ball_history:
                _, x_last, y_last = self._ball_history[-1]
                return _norm_zone(x_last, y_last, self._cfg.zone_axis)
            return "unknown"
        ball = ball_points[0]
        return _norm_zone(float(ball["x_norm"]), float(ball["y_norm"]), self._cfg.zone_axis)

    def _ball_speed_metric(self) -> float:
        history = list(self._ball_history)
        if len(history) < 2:
            return 0.0
        f1, x1, y1 = history[-2]
        f2, x2, y2 = history[-1]
        dt_frames = max(1, f2 - f1)
        dt_sec = dt_frames / self._cfg.fps if self._cfg.fps > 0 else 1.0
        return math.hypot(x2 - x1, y2 - y1) / dt_sec

    def _tracking_confidence_metric(self, rows: list[dict[str, Any]]) -> float:
        active = [r for r in rows if str(r.get("state", "active")) == "active"]
        if not active:
            return 0.0
        total = sum(float(r.get("confidence", 1.0) or 1.0) for r in active)
        return total / len(active)
