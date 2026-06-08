"""
Live playback validation — Activity 33.

Records runtime metrics during playback and compares streaming results
against pre-computed batch data to assess playback quality per clip.
"""

from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Classification constants
# ---------------------------------------------------------------------------

VALIDATION_ACCEPTABLE = "acceptable"
VALIDATION_DEGRADED = "degraded"
VALIDATION_FAILED = "failed"

# Default match-rate thresholds
DEFAULT_TRACK_MATCH_ACCEPTABLE = 0.85
DEFAULT_TRACK_MATCH_DEGRADED = 0.60
DEFAULT_EVENT_OVERLAP_ACCEPTABLE = 0.70
DEFAULT_EVENT_OVERLAP_DEGRADED = 0.40
DEFAULT_LATENCY_ACCEPTABLE_MS = 33.3
DEFAULT_LATENCY_DEGRADED_MS = 100.0

# ---------------------------------------------------------------------------
# CSV field definitions
# ---------------------------------------------------------------------------

RUNTIME_METRICS_CSV_FIELDS = (
    "clip_id",
    "session_id",
    "video_fps",
    "analysis_fps",
    "mean_latency_ms",
    "p95_latency_ms",
    "skipped_frames",
    "total_video_frames",
    "total_analysis_frames",
    "events_emitted",
    "events_updated",
    "classification",
    "notes",
)

TRACK_COMPARISON_CSV_FIELDS = (
    "clip_id",
    "total_streaming_rows",
    "total_batch_rows",
    "matched_rows",
    "match_rate",
    "batch_coverage",
    "classification",
    "notes",
)

EVENT_COMPARISON_CSV_FIELDS = (
    "clip_id",
    "streaming_event_count",
    "batch_event_count",
    "matched_events",
    "overlap_rate",
    "classification",
    "notes",
)

MANIFEST_CSV_FIELDS = (
    "asset_id",
    "asset_type",
    "path",
    "is_versioned",
    "role",
    "notes",
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class LiveValidationConfig:
    """Lightweight per-clip configuration for validation runs."""

    clip_id: str
    video_path: str = ""
    tracks_csv: str = ""
    events_json: str = ""
    fps: float = 30.0
    start_frame: int = 0
    end_frame: int = -1
    inference_mode: str = "precomputed"
    budget_ms: float = 33.3
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "video_path": self.video_path,
            "tracks_csv": self.tracks_csv,
            "events_json": self.events_json,
            "fps": self.fps,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "inference_mode": self.inference_mode,
            "budget_ms": self.budget_ms,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeMetrics:
    """Aggregate runtime metrics computed from a validation recording."""

    clip_id: str
    session_id: str
    video_fps: float
    analysis_fps: float
    mean_latency_ms: float
    p95_latency_ms: float
    skipped_frames: int
    total_video_frames: int
    total_analysis_frames: int
    events_emitted: int
    events_updated: int
    classification: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "session_id": self.session_id,
            "video_fps": self.video_fps,
            "analysis_fps": self.analysis_fps,
            "mean_latency_ms": self.mean_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "skipped_frames": self.skipped_frames,
            "total_video_frames": self.total_video_frames,
            "total_analysis_frames": self.total_analysis_frames,
            "events_emitted": self.events_emitted,
            "events_updated": self.events_updated,
            "classification": self.classification,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class TrackComparisonResult:
    """Result of comparing streaming track rows against batch track rows."""

    clip_id: str
    total_streaming_rows: int
    total_batch_rows: int
    matched_rows: int
    match_rate: float
    batch_coverage: float
    classification: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "total_streaming_rows": self.total_streaming_rows,
            "total_batch_rows": self.total_batch_rows,
            "matched_rows": self.matched_rows,
            "match_rate": self.match_rate,
            "batch_coverage": self.batch_coverage,
            "classification": self.classification,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EventComparisonResult:
    """Result of comparing streaming events against batch events."""

    clip_id: str
    streaming_event_count: int
    batch_event_count: int
    matched_events: int
    overlap_rate: float
    classification: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "streaming_event_count": self.streaming_event_count,
            "batch_event_count": self.batch_event_count,
            "matched_events": self.matched_events,
            "overlap_rate": self.overlap_rate,
            "classification": self.classification,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Metrics recorder
# ---------------------------------------------------------------------------


class RuntimeMetricsRecorder:
    """
    Accumulates per-frame measurements during a live playback session and
    computes aggregate metrics on demand.

    Typical usage::

        rec = RuntimeMetricsRecorder(session_id="s1", clip_id="video_595")
        for frame in player:
            rec.record_video_frame(frame, timestamp_ms=player.elapsed_ms())
            if analysis_done:
                rec.record_analysis_frame(frame, latency_ms=elapsed)
            if skipped:
                rec.record_skip(frame)
        metrics = rec.compute()
    """

    def __init__(
        self,
        session_id: str = "default",
        clip_id: str = "",
        fps: float = 30.0,
        acceptable_latency_ms: float = DEFAULT_LATENCY_ACCEPTABLE_MS,
        degraded_latency_ms: float = DEFAULT_LATENCY_DEGRADED_MS,
    ) -> None:
        self._session_id = session_id
        self._clip_id = clip_id
        self._fps = fps
        self._acceptable_latency_ms = acceptable_latency_ms
        self._degraded_latency_ms = degraded_latency_ms

        # (frame, timestamp_ms)
        self._video_entries: list[tuple[int, float]] = []
        # (frame, latency_ms, timestamp_ms)
        self._analysis_entries: list[tuple[int, float, float]] = []
        self._skipped_frames: list[int] = []
        self._events_emitted: int = 0
        self._events_updated: int = 0

    # ------------------------------------------------------------------
    # Recording

    def record_video_frame(
        self, frame: int, timestamp_ms: float | None = None
    ) -> None:
        """Record a displayed video frame."""
        ts = timestamp_ms if timestamp_ms is not None else time.monotonic() * 1000.0
        self._video_entries.append((frame, ts))

    def record_analysis_frame(
        self,
        frame: int,
        latency_ms: float,
        timestamp_ms: float | None = None,
    ) -> None:
        """Record a completed analysis result with its end-to-end latency."""
        ts = timestamp_ms if timestamp_ms is not None else time.monotonic() * 1000.0
        self._analysis_entries.append((frame, latency_ms, ts))

    def record_skip(self, frame: int) -> None:
        """Record a skipped frame (inference was not attempted)."""
        self._skipped_frames.append(frame)

    def record_event_emitted(self, count: int = 1) -> None:
        """Increment the emitted-event counter."""
        self._events_emitted += count

    def record_event_updated(self, count: int = 1) -> None:
        """Increment the updated-event counter."""
        self._events_updated += count

    # ------------------------------------------------------------------
    # Computation

    def compute(self) -> RuntimeMetrics:
        """Compute and return aggregate RuntimeMetrics from recorded data."""
        n_video = len(self._video_entries)
        n_analysis = len(self._analysis_entries)
        latencies = [e[1] for e in self._analysis_entries]

        # Video FPS from timestamp spread
        if n_video >= 2:
            span_ms = self._video_entries[-1][1] - self._video_entries[0][1]
            video_fps = (n_video - 1) / (span_ms / 1000.0) if span_ms > 0 else 0.0
        else:
            video_fps = self._fps if n_video == 1 else 0.0

        # Analysis FPS from its own timestamp spread
        if n_analysis >= 2:
            span_ms = self._analysis_entries[-1][2] - self._analysis_entries[0][2]
            analysis_fps = (
                (n_analysis - 1) / (span_ms / 1000.0) if span_ms > 0 else 0.0
            )
        else:
            analysis_fps = self._fps if n_analysis == 1 else 0.0

        mean_lat = _mean(latencies)
        p95_lat = _percentile(latencies, 95)
        classification = _classify_latency(
            mean_lat, self._acceptable_latency_ms, self._degraded_latency_ms
        )

        return RuntimeMetrics(
            clip_id=self._clip_id,
            session_id=self._session_id,
            video_fps=round(video_fps, 2),
            analysis_fps=round(analysis_fps, 2),
            mean_latency_ms=round(mean_lat, 2),
            p95_latency_ms=round(p95_lat, 2),
            skipped_frames=len(self._skipped_frames),
            total_video_frames=n_video,
            total_analysis_frames=n_analysis,
            events_emitted=self._events_emitted,
            events_updated=self._events_updated,
            classification=classification,
        )

    def reset(self) -> None:
        """Clear all accumulated data."""
        self._video_entries.clear()
        self._analysis_entries.clear()
        self._skipped_frames.clear()
        self._events_emitted = 0
        self._events_updated = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "clip_id": self._clip_id,
            "total_video_frames": len(self._video_entries),
            "total_analysis_frames": len(self._analysis_entries),
            "skipped_frames": len(self._skipped_frames),
            "events_emitted": self._events_emitted,
            "events_updated": self._events_updated,
        }


# ---------------------------------------------------------------------------
# Comparison functions
# ---------------------------------------------------------------------------


def compare_tracks(
    streaming_rows: list[dict[str, Any]],
    batch_rows: list[dict[str, Any]],
    match_distance_px: float = 50.0,
    clip_id: str = "",
    acceptable_rate: float = DEFAULT_TRACK_MATCH_ACCEPTABLE,
    degraded_rate: float = DEFAULT_TRACK_MATCH_DEGRADED,
) -> TrackComparisonResult:
    """
    Compare streaming track rows against pre-computed batch track rows.

    Matching is done per-frame by centroid proximity (Euclidean distance <=
    *match_distance_px*). Each streaming row is matched to at most one batch row.

    Returns a TrackComparisonResult with:
    - match_rate  = matched / total_streaming_rows
    - batch_coverage = frames_with_any_match / total_batch_frames
    """
    n_s = len(streaming_rows)
    n_b = len(batch_rows)

    if n_s == 0 or n_b == 0:
        classification = VALIDATION_FAILED
        notes = "no streaming data" if n_s == 0 else "no batch data"
        if n_s == 0 and n_b == 0:
            notes = "no data in either set"
        return TrackComparisonResult(
            clip_id=clip_id,
            total_streaming_rows=n_s,
            total_batch_rows=n_b,
            matched_rows=0,
            match_rate=0.0,
            batch_coverage=0.0,
            classification=classification,
            notes=notes,
        )

    # Index batch rows by frame for O(n) lookup per streaming row
    batch_by_frame: dict[int, list[dict[str, Any]]] = {}
    for row in batch_rows:
        f = int(row.get("frame", 0))
        batch_by_frame.setdefault(f, []).append(row)

    matched = 0
    frames_with_match: set[int] = set()

    for row in streaming_rows:
        frame = int(row.get("frame", 0))
        cx = float(row.get("cx", row.get("x", 0.0)))
        cy = float(row.get("cy", row.get("y", 0.0)))

        for candidate in batch_by_frame.get(frame, []):
            bcx = float(candidate.get("cx", candidate.get("x", 0.0)))
            bcy = float(candidate.get("cy", candidate.get("y", 0.0)))
            if _dist(cx, cy, bcx, bcy) <= match_distance_px:
                matched += 1
                frames_with_match.add(frame)
                break

    match_rate = matched / n_s
    batch_coverage = (
        len(frames_with_match) / len(batch_by_frame) if batch_by_frame else 0.0
    )
    classification = _classify_rate(match_rate, acceptable_rate, degraded_rate)

    return TrackComparisonResult(
        clip_id=clip_id,
        total_streaming_rows=n_s,
        total_batch_rows=n_b,
        matched_rows=matched,
        match_rate=round(match_rate, 4),
        batch_coverage=round(batch_coverage, 4),
        classification=classification,
    )


def compare_events(
    streaming_events: list[dict[str, Any]],
    batch_events: list[dict[str, Any]],
    clip_id: str = "",
    acceptable_rate: float = DEFAULT_EVENT_OVERLAP_ACCEPTABLE,
    degraded_rate: float = DEFAULT_EVENT_OVERLAP_DEGRADED,
) -> EventComparisonResult:
    """
    Compare streaming events against pre-computed batch events.

    Two events match when they share the same label and have overlapping
    frame ranges. Each batch event is consumed by at most one streaming event.

    overlap_rate = matched_events / max(streaming_count, batch_count)
    """
    n_s = len(streaming_events)
    n_b = len(batch_events)

    if n_s == 0 and n_b == 0:
        return EventComparisonResult(
            clip_id=clip_id,
            streaming_event_count=0,
            batch_event_count=0,
            matched_events=0,
            overlap_rate=0.0,
            classification=VALIDATION_FAILED,
            notes="no events in either set",
        )

    batch_used = [False] * n_b
    matched = 0

    for s_ev in streaming_events:
        s_label = str(s_ev.get("label", s_ev.get("event_type", "")))
        s_start = int(s_ev.get("start_frame", s_ev.get("frame_start", 0)))
        s_end = int(s_ev.get("end_frame", s_ev.get("frame_end", s_start)))

        for i, b_ev in enumerate(batch_events):
            if batch_used[i]:
                continue
            b_label = str(b_ev.get("label", b_ev.get("event_type", "")))
            if b_label != s_label:
                continue
            b_start = int(b_ev.get("start_frame", b_ev.get("frame_start", 0)))
            b_end = int(b_ev.get("end_frame", b_ev.get("frame_end", b_start)))
            if s_start <= b_end and s_end >= b_start:
                matched += 1
                batch_used[i] = True
                break

    denom = max(n_s, n_b)
    overlap_rate = matched / denom
    classification = _classify_rate(overlap_rate, acceptable_rate, degraded_rate)

    return EventComparisonResult(
        clip_id=clip_id,
        streaming_event_count=n_s,
        batch_event_count=n_b,
        matched_events=matched,
        overlap_rate=round(overlap_rate, 4),
        classification=classification,
    )


# ---------------------------------------------------------------------------
# Text output helpers
# ---------------------------------------------------------------------------


def runtime_metrics_csv_text(metrics_list: list[RuntimeMetrics]) -> str:
    """Return CSV text for a list of RuntimeMetrics (header + rows)."""
    return _csv_text(RUNTIME_METRICS_CSV_FIELDS, [m.as_dict() for m in metrics_list])


def track_comparison_csv_text(results: list[TrackComparisonResult]) -> str:
    """Return CSV text for a list of TrackComparisonResult."""
    return _csv_text(TRACK_COMPARISON_CSV_FIELDS, [r.as_dict() for r in results])


def event_comparison_csv_text(results: list[EventComparisonResult]) -> str:
    """Return CSV text for a list of EventComparisonResult."""
    return _csv_text(EVENT_COMPARISON_CSV_FIELDS, [r.as_dict() for r in results])


def manifest_csv_text(artifacts: list[dict[str, str]]) -> str:
    """Return CSV text for the manifest rows."""
    return _csv_text(MANIFEST_CSV_FIELDS, artifacts)


def summary_md_text(
    clip_metrics: list[RuntimeMetrics],
    track_comparisons: list[TrackComparisonResult],
    event_comparisons: list[EventComparisonResult],
) -> str:
    """Return a Markdown summary combining runtime metrics and comparisons."""
    lines: list[str] = [
        "# Live Playback Validation — Actividad 33",
        "",
        "Experimento: test_040_live_playback_validation",
        "",
        "## Objetivo",
        "",
        "Medir si la experiencia funciona realmente durante reproduccion.",
        "",
        "## Metricas de Runtime",
        "",
        "| Clip | FPS Video | FPS Analisis | Latencia Media ms | Latencia p95 ms | Frames Saltados | Estado |",
        "|------|-----------|--------------|-------------------|-----------------|-----------------|--------|",
    ]
    for m in clip_metrics:
        lines.append(
            f"| {m.clip_id} | {m.video_fps} | {m.analysis_fps} |"
            f" {m.mean_latency_ms} | {m.p95_latency_ms} |"
            f" {m.skipped_frames} | {m.classification} |"
        )

    lines += [
        "",
        "## Tracks: Streaming vs Batch",
        "",
        "| Clip | Streaming | Batch | Matched | Match Rate | Cobertura Batch | Estado |",
        "|------|-----------|-------|---------|------------|-----------------|--------|",
    ]
    for r in track_comparisons:
        lines.append(
            f"| {r.clip_id} | {r.total_streaming_rows} | {r.total_batch_rows} |"
            f" {r.matched_rows} | {r.match_rate:.2%} | {r.batch_coverage:.2%} |"
            f" {r.classification} |"
        )

    lines += [
        "",
        "## Eventos: Streaming vs Batch",
        "",
        "| Clip | Streaming | Batch | Matched | Overlap Rate | Estado |",
        "|------|-----------|-------|---------|--------------|--------|",
    ]
    for r in event_comparisons:
        lines.append(
            f"| {r.clip_id} | {r.streaming_event_count} | {r.batch_event_count} |"
            f" {r.matched_events} | {r.overlap_rate:.2%} | {r.classification} |"
        )

    lines += [
        "",
        "## Notas",
        "",
        "- Usar modo precomputed antes de intentar inferencia online.",
        "- Clasificaciones: acceptable >= 85% match, degraded >= 60%, failed < 60%.",
        "- Para eventos: acceptable >= 70% overlap, degraded >= 40%.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------


def write_runtime_metrics_csv(
    metrics_list: list[RuntimeMetrics], path: Path | str
) -> None:
    _write_text(path, runtime_metrics_csv_text(metrics_list))


def write_track_comparison_csv(
    results: list[TrackComparisonResult], path: Path | str
) -> None:
    _write_text(path, track_comparison_csv_text(results))


def write_event_comparison_csv(
    results: list[EventComparisonResult], path: Path | str
) -> None:
    _write_text(path, event_comparison_csv_text(results))


def write_manifest_csv(artifacts: list[dict[str, str]], path: Path | str) -> None:
    _write_text(path, manifest_csv_text(artifacts))


def write_summary_md(
    clip_metrics: list[RuntimeMetrics],
    track_comparisons: list[TrackComparisonResult],
    event_comparisons: list[EventComparisonResult],
    path: Path | str,
) -> None:
    _write_text(path, summary_md_text(clip_metrics, track_comparisons, event_comparisons))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _percentile(values: list[float], p: float) -> float:
    """p-th percentile (p in 0–100) without numpy, linear interpolation."""
    if not values:
        return 0.0
    s = sorted(values)
    idx = (len(s) - 1) * p / 100.0
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _dist(x1: float, y1: float, x2: float, y2: float) -> float:
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def _classify_rate(rate: float, acceptable: float, degraded: float) -> str:
    if rate >= acceptable:
        return VALIDATION_ACCEPTABLE
    if rate >= degraded:
        return VALIDATION_DEGRADED
    return VALIDATION_FAILED


def _classify_latency(
    mean_ms: float, acceptable_ms: float, degraded_ms: float
) -> str:
    if mean_ms == 0.0 or mean_ms <= acceptable_ms:
        return VALIDATION_ACCEPTABLE
    if mean_ms <= degraded_ms:
        return VALIDATION_DEGRADED
    return VALIDATION_FAILED


def _csv_text(fields: tuple[str, ...], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _write_text(path: Path | str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
