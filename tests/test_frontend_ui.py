from __future__ import annotations

import re
from pathlib import Path
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.ui import UI_VERSION, shared_css, ui_body_attrs


ROOT = Path(__file__).resolve().parents[1]
RENDERERS = {
    "playback": ROOT / "src/futbotmx/live_playback.py",
    "launcher": ROOT / "src/futbotmx/local_app.py",
    "review": ROOT / "src/futbotmx/level3/manual_calibration.py",
    "report_dashboard": ROOT / "src/futbotmx/level3/dashboard.py",
    "review_highlight": ROOT / "src/futbotmx/level3/highlight_review.py",
    "report_reel": ROOT / "src/futbotmx/level3/reel.py",
    "report_final": ROOT / "src/futbotmx/level3/final_report.py",
    "report_executive": ROOT / "src/futbotmx/level3/executive_report.py",
}


class FrontendUITests(unittest.TestCase):
    def test_shared_css_contains_shell_components_and_breakpoints(self) -> None:
        css = shared_css()

        self.assertIn(UI_VERSION, css)
        self.assertIn(".fb-shell", css)
        self.assertIn(".summary-grid", css)
        self.assertIn(".visual-grid", css)
        self.assertIn(".btn-primary", css)
        self.assertGreaterEqual(css.count("@media"), 3)

    def test_body_attrs_declares_ui_version_and_flow(self) -> None:
        attrs = ui_body_attrs("report", "dashboard-page")

        self.assertIn(f'data-ui-shell="{UI_VERSION}"', attrs)
        self.assertIn('data-product-flow="report"', attrs)
        self.assertIn("dashboard-page", attrs)

    def test_primary_renderers_use_shared_ui_layer(self) -> None:
        for name, path in RENDERERS.items():
            with self.subTest(renderer=name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("shared_css()", source)
                self.assertIn("ui_body_attrs(", source)

    def test_inline_styles_remain_limited_to_dynamic_video_aspect_ratio(self) -> None:
        for name, path in RENDERERS.items():
            with self.subTest(renderer=name):
                source = path.read_text(encoding="utf-8")
                style_attrs = re.findall(r"style=[\"']", source)
                js_style_mutations = re.findall(r"[.]style[.]", source)
                if name == "playback":
                    self.assertEqual(style_attrs, ['style="'])
                    self.assertIn("--vid-w", source)
                else:
                    self.assertEqual(style_attrs, [])
                self.assertEqual(js_style_mutations, [])


if __name__ == "__main__":
    unittest.main()
