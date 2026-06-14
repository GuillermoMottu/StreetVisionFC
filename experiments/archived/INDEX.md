# experiments/archived — Legacy experiments index

These experiment directories contain outputs from earlier pipeline phases.
They are preserved for traceability. Active evaluation is in `experiments/current_evaluation/`.

## Historical experiments

| Directory | Content |
|---|---|
| test_000_environment_check | Initial environment and Python setup |
| test_001_video_ingestion | Video ingestion and frame extraction tests |
| test_002_sam3_segmentation | First SAM3 runs on MSI laptop |
| test_003_tracking | ByteTrack vs simple tracker comparison; real tracks used in evaluation |
| test_004_events | Level 1 events from real ByteTrack tracks |
| test_005_visualizations | Initial visualization experiments |
| test_006_more_copafutmx_videos | Multi-clip exploration (video_595, 667, 480) |
| test_007_msi_benchmarks | SAM3 benchmark — source of production benchmark numbers |
| test_009_level1_solidity | Level 1 solidity audit and deduplication |
| test_011_level2_unlock | Level 2 gate evaluation |
| test_012_level2_metrics | Level 2 metrics computation |
| test_013_level2_events | Level 2 event detection |
| test_014_level2_visualizations | Level 2 visualizations |
| test_015_level2_multiclip | Level 2 multi-clip analysis |
| test_016_level2_demo | Level 2 demo package |
| test_017_level2_closure | Level 2 technical closure gate |
| test_018_level3_readiness | Level 3 readiness evaluation |
| test_019_level3_data_contract | Level 3 data contract audit |
| test_020_level3_spatial_model | Homography, rectified tracks, mini-map |
| test_021_level3_tactical_metrics | Spatial control, Voronoi, interaction graph |
| test_022_level3_advanced_events | Highlights, candidate chains, narrative |
| test_023_level3_visualizations | Voronoi, interaction graph, storyboard |
| test_024_level3_dashboard | Static HTML dashboard |
| test_025_level3_reel | Demo reel package |
| test_026_level3_multiclip | Multi-clip validation (video_595, video_667) |
| test_027_level3_closure | Level 3 closure: 11 pass, 0 fail |
| test_028_local_app | Local app prototype |
| test_029_manual_calibration | Manual homography calibration |
| test_030_manual_spatial_model | Manual spatial model |
| test_031_team_assignment | Team assignment experiments |
| test_032_level3_team_metrics | Team-level tactical metrics |
| test_033_level3_team_events | Team-level event detection |
| test_034_full_analysis | Full pipeline analysis run |
| test_035_human_review | Human review outputs |
| test_036_activity18_clip_validation | Clip validation activity 18 |
| test_037_activity19_video_overlay | Video overlay render |
| test_038_final_report | Final report HTML/PDF |
| test_039_live_playback | Live playback prototype |
| test_040_live_playback_validation | Live playback validation framework |
| evidence_level1 | Level 1 evidence package |
| final_demo_report | Final demo report artifacts |

## Active evaluation

See `experiments/current_evaluation/` for all production outputs, metrics, masks, tracks and closures.
