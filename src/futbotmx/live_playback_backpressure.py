"""
Live playback backpressure and degradation management.

Maintains a bounded frame queue and state machine so video playback remains
fluid even when the analysis engine is delayed or stalled.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Degradation state constants
# ---------------------------------------------------------------------------

DEGRADATION_LIVE = "live"
DEGRADATION_DELAYED = "delayed"
DEGRADATION_REPLAYING_CACHE = "replaying_cache"
DEGRADATION_ANALYSIS_PAUSED = "analysis_paused"

DEGRADATION_STATES = (
    DEGRADATION_LIVE,
    DEGRADATION_DELAYED,
    DEGRADATION_REPLAYING_CACHE,
    DEGRADATION_ANALYSIS_PAUSED,
)

# Overlay source labels
OVERLAY_SOURCE_EXACT = "exact"
OVERLAY_SOURCE_FALLBACK = "fallback"
OVERLAY_SOURCE_NONE = "none"

# Visual layers that can be disabled to reduce rendering load (least- to most-important)
REDUCIBLE_LAYERS = ("trails", "debug", "minimap", "highlights")

BACKPRESSURE_JSONL_FIELDS = (
    "video_frame",
    "analysis_frame",
    "degradation_state",
    "lag_frames",
    "frames_since_analysis",
    "skip_inference",
    "reduce_layers",
    "reduced_layers",
    "recommend_precomputed",
    "overlay_frame",
    "overlay_source",
    "queue_size",
    "dropped_frame_count",
    "consecutive_late_frames",
    "budget_ms",
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class BackpressureConfig:
    """Tunable parameters for the backpressure engine."""

    session_id: str = "default"
    fps: float = 30.0
    # Queue
    max_queue_size: int = 8
    # State-machine thresholds (frames)
    delayed_threshold_frames: int = 3
    paused_threshold_frames: int = 30
    # Policy thresholds (frames)
    skip_inference_at_lag: int = 5
    reduce_layers_at_lag: int = 8
    # How many consecutive late analysis results before recommending precomputed mode
    precomputed_consecutive_threshold: int = 10
    # Per-frame inference budget in milliseconds
    budget_ms: float = 33.3
    # Layers to disable under load, in order of least-to-most importance
    reducible_layers: tuple[str, ...] = ("trails", "debug")


# ---------------------------------------------------------------------------
# Frame queue
# ---------------------------------------------------------------------------


@dataclass
class FrameQueueEntry:
    """Analysis result held in the queue."""

    frame: int
    data: Any
    enqueued_ms: float = field(default_factory=lambda: time.monotonic() * 1000.0)


class FrameQueue:
    """
    Bounded dict of analysis results keyed by frame number.

    Eviction policy (when at capacity):
    - If the new frame is older than the oldest queued frame, it is stale and
      discarded (the queue is already ahead of it).
    - Otherwise the oldest queued frame is evicted to make room for the new one.

    This keeps the queue focused on the most recent available data.
    """

    def __init__(self, max_size: int = 8) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._max_size = max_size
        self._entries: dict[int, FrameQueueEntry] = {}
        self._dropped: int = 0

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def dropped_count(self) -> int:
        return self._dropped

    def push(self, frame: int, data: Any) -> int:
        """
        Add or replace an analysis result for *frame*.

        Returns the number of frames dropped during this call (0 or 1).
        """
        if frame in self._entries:
            self._entries[frame] = FrameQueueEntry(frame=frame, data=data)
            return 0

        if len(self._entries) >= self._max_size:
            oldest = min(self._entries)
            if frame < oldest:
                # Incoming frame is stale — reject it without touching the queue.
                self._dropped += 1
                return 0
            del self._entries[oldest]
            self._dropped += 1

        self._entries[frame] = FrameQueueEntry(frame=frame, data=data)
        return 0

    def get(self, frame: int) -> FrameQueueEntry | None:
        """Return the entry for an exact frame match, or None."""
        return self._entries.get(frame)

    def get_best_for(self, video_frame: int) -> tuple[int | None, FrameQueueEntry | None]:
        """
        Return the entry with the highest frame number that is <= *video_frame*.

        Provides the most recent analysis data that can be displayed right now.
        Returns ``(None, None)`` when no such entry exists.
        """
        best: int | None = None
        for f in self._entries:
            if f <= video_frame and (best is None or f > best):
                best = f
        if best is None:
            return None, None
        return best, self._entries[best]

    def discard_older_than(self, cutoff_frame: int) -> int:
        """Remove all entries with frame < *cutoff_frame*. Returns count removed."""
        to_remove = [f for f in self._entries if f < cutoff_frame]
        for f in to_remove:
            del self._entries[f]
        return len(to_remove)

    def available_frames(self) -> list[int]:
        """Sorted list of queued frame numbers."""
        return sorted(self._entries.keys())

    def clear(self) -> None:
        self._entries.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "dropped_count": self._dropped,
            "available_frames": self.available_frames(),
        }


# ---------------------------------------------------------------------------
# Degradation state machine
# ---------------------------------------------------------------------------


class DegradationMonitor:
    """
    Tracks two independent clocks — video and analysis — and derives the
    current degradation state from their difference.

    ``advance(video_frame)`` moves the video clock forward and returns the state.
    ``notify_analysis(frame)`` updates the analysis clock when results arrive.
    """

    def __init__(
        self,
        delayed_threshold_frames: int = 3,
        paused_threshold_frames: int = 30,
    ) -> None:
        self._delayed_threshold = delayed_threshold_frames
        self._paused_threshold = paused_threshold_frames

        self._video_frame: int = 0
        self._analysis_frame: int | None = None
        self._frames_since_analysis: int = 0
        self._analysis_notified: bool = False
        self._explicitly_paused: bool = False

    # ------------------------------------------------------------------
    # Properties

    @property
    def video_frame(self) -> int:
        return self._video_frame

    @property
    def analysis_frame(self) -> int | None:
        return self._analysis_frame

    @property
    def frames_since_analysis(self) -> int:
        return self._frames_since_analysis

    @property
    def lag_frames(self) -> int:
        if self._analysis_frame is None:
            return self._video_frame
        return max(0, self._video_frame - self._analysis_frame)

    # ------------------------------------------------------------------
    # Mutators

    def advance(self, video_frame: int) -> str:
        """
        Advance the video clock to *video_frame* and return the degradation state.

        Call once per displayed video frame, before deciding whether to run
        inference for that frame.
        """
        advance_by = max(0, video_frame - self._video_frame)
        self._video_frame = video_frame

        if advance_by > 0:
            if self._analysis_notified:
                self._frames_since_analysis = 0
            else:
                self._frames_since_analysis += advance_by
            self._analysis_notified = False

        return self._compute_state()

    def notify_analysis(self, frame: int) -> None:
        """Call when an analysis result for *frame* arrives."""
        self._analysis_frame = frame
        self._analysis_notified = True
        self._frames_since_analysis = 0

    def set_paused(self, paused: bool) -> None:
        """Explicitly mark the analysis engine as paused or resumed."""
        self._explicitly_paused = paused

    def reset(self, video_frame: int = 0) -> None:
        """Full state reset (e.g. after a seek)."""
        self._video_frame = video_frame
        self._analysis_frame = None
        self._frames_since_analysis = 0
        self._analysis_notified = False
        self._explicitly_paused = False

    # ------------------------------------------------------------------
    # Internal

    def _compute_state(self) -> str:
        if self._explicitly_paused:
            return DEGRADATION_ANALYSIS_PAUSED
        lag = self.lag_frames
        if self._frames_since_analysis >= self._paused_threshold:
            return DEGRADATION_ANALYSIS_PAUSED
        if lag > self._paused_threshold:
            return DEGRADATION_REPLAYING_CACHE
        if lag >= self._delayed_threshold:
            return DEGRADATION_DELAYED
        return DEGRADATION_LIVE

    def snapshot(self) -> dict[str, Any]:
        return {
            "video_frame": self._video_frame,
            "analysis_frame": self._analysis_frame,
            "lag_frames": self.lag_frames,
            "frames_since_analysis": self._frames_since_analysis,
            "state": self._compute_state(),
        }


# ---------------------------------------------------------------------------
# Fallback policy
# ---------------------------------------------------------------------------


class BackpressurePolicy:
    """
    Decides how aggressively to degrade analysis when the engine is behind.

    - ``should_skip_inference`` — avoid heavy computation entirely for this frame
    - ``layers_to_reduce`` — visual layers to disable to reduce rendering load
    - ``should_switch_to_precomputed`` — recommend switching to precomputed data
    """

    def __init__(
        self,
        budget_ms: float = 33.3,
        skip_inference_at_lag: int = 5,
        reduce_layers_at_lag: int = 8,
        precomputed_consecutive_threshold: int = 10,
        reducible_layers: tuple[str, ...] = ("trails", "debug"),
    ) -> None:
        self._budget_ms = budget_ms
        self._skip_at_lag = skip_inference_at_lag
        self._reduce_at_lag = reduce_layers_at_lag
        self._precomputed_threshold = precomputed_consecutive_threshold
        self._reducible_layers = reducible_layers

    @property
    def budget_ms(self) -> float:
        return self._budget_ms

    def should_skip_inference(self, state: str, lag_frames: int) -> bool:
        """Return True when heavy inference should be skipped for this frame."""
        if state in (DEGRADATION_ANALYSIS_PAUSED, DEGRADATION_REPLAYING_CACHE):
            return True
        if state == DEGRADATION_DELAYED and lag_frames >= self._skip_at_lag:
            return True
        return False

    def layers_to_reduce(self, state: str, lag_frames: int) -> list[str]:
        """
        Return the list of visual layers to disable, ordered from least to most
        important. Returns an empty list when no degradation is needed.
        """
        if state == DEGRADATION_LIVE:
            return []
        if state == DEGRADATION_DELAYED:
            if lag_frames >= self._reduce_at_lag:
                return list(self._reducible_layers[:1])
            return []
        # replaying_cache or analysis_paused — disable all configured layers
        return list(self._reducible_layers)

    def should_switch_to_precomputed(self, consecutive_late_frames: int) -> bool:
        """Return True when sustained latency warrants switching to precomputed mode."""
        return consecutive_late_frames >= self._precomputed_threshold

    def select_fallback_frame(
        self, available_frames: list[int], video_frame: int
    ) -> int | None:
        """
        Return the best available overlay frame for *video_frame*.

        Picks the largest frame number that is <= video_frame, or None if
        nothing is available.
        """
        best: int | None = None
        for f in available_frames:
            if f <= video_frame and (best is None or f > best):
                best = f
        return best


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BackpressureStatus:
    """Snapshot of engine state for a single video frame tick."""

    video_frame: int
    analysis_frame: int | None
    degradation_state: str
    lag_frames: int
    frames_since_analysis: int
    skip_inference: bool
    reduce_layers: bool
    reduced_layers: tuple[str, ...]
    recommend_precomputed: bool
    overlay_frame: int | None
    overlay_source: str
    queue_size: int
    dropped_frame_count: int
    consecutive_late_frames: int
    budget_ms: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "video_frame": self.video_frame,
            "analysis_frame": self.analysis_frame,
            "degradation_state": self.degradation_state,
            "lag_frames": self.lag_frames,
            "frames_since_analysis": self.frames_since_analysis,
            "skip_inference": self.skip_inference,
            "reduce_layers": self.reduce_layers,
            "reduced_layers": list(self.reduced_layers),
            "recommend_precomputed": self.recommend_precomputed,
            "overlay_frame": self.overlay_frame,
            "overlay_source": self.overlay_source,
            "queue_size": self.queue_size,
            "dropped_frame_count": self.dropped_frame_count,
            "consecutive_late_frames": self.consecutive_late_frames,
            "budget_ms": self.budget_ms,
        }


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


class PlaybackBackpressureEngine:
    """
    Integrates FrameQueue, DegradationMonitor, and BackpressurePolicy into a
    single interface.

    Typical usage::

        engine = PlaybackBackpressureEngine(config)

        for video_frame in player:
            status = engine.tick(video_frame)
            if not status.skip_inference:
                result = run_inference(video_frame)
                engine.push_analysis_result(video_frame, result)
            data = engine.get_data(status.overlay_frame)
            render(data, status.reduced_layers)
    """

    def __init__(self, config: BackpressureConfig | None = None) -> None:
        self._config = config or BackpressureConfig()
        self._queue = FrameQueue(self._config.max_queue_size)
        self._monitor = DegradationMonitor(
            delayed_threshold_frames=self._config.delayed_threshold_frames,
            paused_threshold_frames=self._config.paused_threshold_frames,
        )
        self._policy = BackpressurePolicy(
            budget_ms=self._config.budget_ms,
            skip_inference_at_lag=self._config.skip_inference_at_lag,
            reduce_layers_at_lag=self._config.reduce_layers_at_lag,
            precomputed_consecutive_threshold=self._config.precomputed_consecutive_threshold,
            reducible_layers=self._config.reducible_layers,
        )
        self._consecutive_late: int = 0
        self._status_history: list[BackpressureStatus] = []

    # ------------------------------------------------------------------
    # Public interface

    def push_analysis_result(self, frame: int, data: Any) -> None:
        """
        Register a completed analysis result for *frame*.

        Tracks whether the result arrived late (behind the current video frame)
        so the policy can accumulate ``consecutive_late_frames``.
        """
        self._queue.push(frame, data)
        self._monitor.notify_analysis(frame)
        if frame < self._monitor.video_frame:
            self._consecutive_late += 1
        else:
            self._consecutive_late = 0

    def tick(self, video_frame: int) -> BackpressureStatus:
        """
        Advance the video clock to *video_frame* and return a BackpressureStatus.

        Call once per displayed video frame, before deciding whether to run
        inference for that frame.
        """
        state = self._monitor.advance(video_frame)
        lag = self._monitor.lag_frames

        skip = self._policy.should_skip_inference(state, lag)
        layers = self._policy.layers_to_reduce(state, lag)
        recommend_precomputed = self._policy.should_switch_to_precomputed(
            self._consecutive_late
        )

        overlay_frame, _ = self._queue.get_best_for(video_frame)
        if overlay_frame == video_frame:
            overlay_source = OVERLAY_SOURCE_EXACT
        elif overlay_frame is not None:
            overlay_source = OVERLAY_SOURCE_FALLBACK
        else:
            overlay_source = OVERLAY_SOURCE_NONE

        # Evict frames that are too far behind to serve as useful fallbacks.
        if video_frame > 0:
            self._queue.discard_older_than(
                video_frame - self._config.max_queue_size
            )

        status = BackpressureStatus(
            video_frame=video_frame,
            analysis_frame=self._monitor.analysis_frame,
            degradation_state=state,
            lag_frames=lag,
            frames_since_analysis=self._monitor.frames_since_analysis,
            skip_inference=skip,
            reduce_layers=bool(layers),
            reduced_layers=tuple(layers),
            recommend_precomputed=recommend_precomputed,
            overlay_frame=overlay_frame,
            overlay_source=overlay_source,
            queue_size=self._queue.size,
            dropped_frame_count=self._queue.dropped_count,
            consecutive_late_frames=self._consecutive_late,
            budget_ms=self._config.budget_ms,
        )
        self._status_history.append(status)
        return status

    def get_data(self, frame: int | None) -> Any:
        """Return analysis data for *frame*, or None if not in the queue."""
        if frame is None:
            return None
        entry = self._queue.get(frame)
        return entry.data if entry is not None else None

    def seek(self, target_frame: int) -> None:
        """Reset all state for a seek operation (forward or backward)."""
        self._queue.clear()
        self._monitor.reset(target_frame)
        self._consecutive_late = 0
        self._status_history.clear()

    def pause_analysis(self) -> None:
        """Explicitly signal that the analysis engine has stopped."""
        self._monitor.set_paused(True)

    def resume_analysis(self) -> None:
        """Signal that the analysis engine has resumed."""
        self._monitor.set_paused(False)

    def emit_jsonl(self) -> str:
        """Emit all recorded status history as JSONL."""
        lines = [
            json.dumps(s.as_dict(), ensure_ascii=True)
            for s in self._status_history
        ]
        return "\n".join(lines)

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self._config.session_id,
            "config": {
                "max_queue_size": self._config.max_queue_size,
                "delayed_threshold_frames": self._config.delayed_threshold_frames,
                "paused_threshold_frames": self._config.paused_threshold_frames,
                "skip_inference_at_lag": self._config.skip_inference_at_lag,
                "reduce_layers_at_lag": self._config.reduce_layers_at_lag,
                "precomputed_consecutive_threshold": self._config.precomputed_consecutive_threshold,
                "budget_ms": self._config.budget_ms,
            },
            "monitor": self._monitor.snapshot(),
            "queue": self._queue.snapshot(),
            "consecutive_late_frames": self._consecutive_late,
            "status_history_count": len(self._status_history),
        }
