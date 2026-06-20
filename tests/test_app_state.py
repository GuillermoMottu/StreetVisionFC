from __future__ import annotations

import threading
import time
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.app_state import AppState


class AppStateTests(unittest.TestCase):
    def test_initial_state_is_idle(self) -> None:
        state = AppState()
        snap = state.snapshot()
        self.assertEqual(snap["status"], "idle")
        self.assertEqual(snap["experiment_dir"], "")
        self.assertEqual(snap["log_count"], 0)

    def test_start_sets_running_and_clears_previous(self) -> None:
        state = AppState()
        state.start("/old/video.mp4", "experiments/old")
        state.complete()
        state.append_log("old line")

        state.start("/new/video.mp4", "experiments/new_run")
        snap = state.snapshot()

        self.assertEqual(snap["status"], "running")
        self.assertEqual(snap["video_path"], "/new/video.mp4")
        self.assertEqual(snap["experiment_dir"], "experiments/new_run")
        self.assertEqual(snap["log_count"], 0)
        self.assertEqual(snap["error"], "")

    def test_complete_sets_status_and_timestamp(self) -> None:
        state = AppState()
        state.start("/v.mp4", "experiments/x")
        state.complete()
        snap = state.snapshot()
        self.assertEqual(snap["status"], "complete")
        self.assertNotEqual(snap["finished_at"], "")

    def test_fail_stores_error_message(self) -> None:
        state = AppState()
        state.start("/v.mp4", "experiments/x")
        state.fail("returncode=1")
        snap = state.snapshot()
        self.assertEqual(snap["status"], "error")
        self.assertIn("returncode=1", snap["error"])

    def test_append_log_and_snapshot_are_consistent(self) -> None:
        state = AppState()
        state.start("/v.mp4", "experiments/x")
        for i in range(5):
            state.append_log(f"line {i}")
        lines = state.log_snapshot()
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], "line 0")
        self.assertEqual(lines[4], "line 4")

    def test_log_snapshot_returns_copy(self) -> None:
        state = AppState()
        state.start("/v.mp4", "experiments/x")
        state.append_log("a")
        snap1 = state.log_snapshot()
        state.append_log("b")
        snap2 = state.log_snapshot()
        self.assertEqual(len(snap1), 1)
        self.assertEqual(len(snap2), 2)

    def test_thread_safety_concurrent_appends(self) -> None:
        state = AppState()
        state.start("/v.mp4", "experiments/x")
        errors: list[Exception] = []

        def writer() -> None:
            try:
                for _ in range(100):
                    state.append_log("line")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(state.snapshot()["log_count"], 800)

    def test_has_detections_returns_false_when_no_dir(self) -> None:
        state = AppState()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(state.has_detections(tmp))

    def test_has_detections_returns_true_when_file_exists(self) -> None:
        state = AppState()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exp = root / "experiments" / "run_x"
            exp.mkdir(parents=True)
            (exp / "detections.json").write_text("{}", encoding="utf-8")
            state.start("/v.mp4", "experiments/run_x")
            state.complete()
            self.assertTrue(state.has_detections(tmp))


if __name__ == "__main__":
    unittest.main()
