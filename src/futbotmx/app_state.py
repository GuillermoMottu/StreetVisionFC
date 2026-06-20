from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class AppState:
    status: str = "idle"        # idle | running | complete | error
    experiment_dir: str = ""    # ruta relativa al último experimento
    video_path: str = ""
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    _log: list[str] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def start(self, video_path: str, experiment_dir: str) -> None:
        with self._lock:
            self.status = "running"
            self.video_path = video_path
            self.experiment_dir = experiment_dir
            self.started_at = _now()
            self.finished_at = ""
            self.error = ""
            self._log = []

    def complete(self) -> None:
        with self._lock:
            self.status = "complete"
            self.finished_at = _now()

    def fail(self, error: str) -> None:
        with self._lock:
            self.status = "error"
            self.error = error
            self.finished_at = _now()

    def append_log(self, line: str) -> None:
        with self._lock:
            self._log.append(line)

    def log_snapshot(self) -> list[str]:
        with self._lock:
            return list(self._log)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "status": self.status,
                "experiment_dir": self.experiment_dir,
                "video_path": self.video_path,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "error": self.error,
                "log_count": len(self._log),
            }

    def has_detections(self, root_str: str) -> bool:
        if not self.experiment_dir:
            return False
        from pathlib import Path
        return (Path(root_str) / self.experiment_dir / "detections.json").exists()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
