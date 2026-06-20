from __future__ import annotations

from pathlib import Path


SPATIAL_DIR = "spatial_model"
TACTICAL_METRICS_DIR = "tactical_metrics"
ADVANCED_EVENTS_DIR = "advanced_events"
VISUALIZATIONS_DIR = "visualizations"

SPATIAL_TRACKS_CSV = "spatial_tracks.csv"
TEAM_TRACKS_CSV = "tracks_with_teams.csv"
TACTICAL_METRICS_CSV = "tactical_metrics.csv"
TACTICAL_METRICS_JSON = "tactical_metrics.json"
ADVANCED_EVENTS_JSON = "advanced_events.json"
HIGHLIGHTS_CSV = "highlights.csv"
NARRATIVE_MD = "narrative.md"
VISUALIZATION_MANIFEST_CSV = "visualization_manifest.csv"

LEGACY_SPATIAL_DIR = "level3_spatial"
LEGACY_TACTICAL_METRICS_DIR = "level3_metrics"
LEGACY_ADVANCED_EVENTS_DIR = "level3_events"
LEGACY_VISUALIZATIONS_DIR = "level3_visualizations"

LEGACY_SPATIAL_TRACKS_CSV = "level3_tracks.csv"
LEGACY_TEAM_TRACKS_CSV = "level3_tracks_with_teams.csv"
LEGACY_TACTICAL_METRICS_CSV = "level3_metrics.csv"
LEGACY_TACTICAL_METRICS_JSON = "level3_metrics.json"
LEGACY_ADVANCED_EVENTS_JSON = "level3_events.json"
LEGACY_HIGHLIGHTS_CSV = "level3_highlights.csv"
LEGACY_NARRATIVE_MD = "level3_narrative.md"
LEGACY_VISUALIZATION_MANIFEST_CSV = "level3_visualization_manifest.csv"


def first_existing(*paths: str | Path) -> Path:
    candidates = [Path(path) for path in paths]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def mirror_legacy_file(primary: str | Path, legacy: str | Path) -> None:
    primary_path = Path(primary)
    legacy_path = Path(legacy)
    if primary_path == legacy_path or not primary_path.exists():
        return
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_bytes(primary_path.read_bytes())
