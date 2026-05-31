from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.segmentation import SAM3Segmenter, SAM3UnavailableError
from futbotmx.video_io import inspect_video


@dataclass(frozen=True)
class GpuSnapshot:
    name: str
    driver_version: str
    memory_total_mb: float
    memory_used_mb: float
    temperature_c: float | None = None
    power_draw_w: float | None = None


@dataclass(frozen=True)
class BenchmarkRun:
    name: str
    frames: tuple[int, ...]
    frame_count: int
    prompt_count: int
    detection_count: int
    elapsed_sec: float
    sec_per_frame: float
    fps_effective: float
    cuda_memory_allocated_peak_mb: float | None
    cuda_memory_reserved_peak_mb: float | None
    nvidia_smi_memory_before_mb: float | None
    nvidia_smi_memory_after_mb: float | None
    nvidia_smi_memory_delta_mb: float | None


def parse_float(value: str) -> float | None:
    text = value.strip()
    if not text or text.upper() in {"N/A", "[N/A]"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_nvidia_smi_row(row: str) -> GpuSnapshot:
    parts = [part.strip() for part in row.split(",")]
    if len(parts) < 6:
        raise ValueError("nvidia-smi row must contain 6 comma-separated fields")
    temperature = parse_float(parts[4])
    power_draw = parse_float(parts[5])
    return GpuSnapshot(
        name=parts[0],
        driver_version=parts[1],
        memory_total_mb=float(parts[2]),
        memory_used_mb=float(parts[3]),
        temperature_c=temperature,
        power_draw_w=power_draw,
    )


def read_gpu_snapshot() -> GpuSnapshot | None:
    command = [
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    first_row = next((line for line in result.stdout.splitlines() if line.strip()), "")
    if not first_row:
        return None
    return parse_nvidia_smi_row(first_row)


def get_package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for module_name in ("cv2", "numpy", "pandas", "torch", "supervision"):
        try:
            module = __import__(module_name)
        except ImportError:
            versions[module_name] = "not_importable"
            continue
        versions[module_name] = str(getattr(module, "__version__", "unknown"))

    try:
        import sam3
    except ImportError:
        versions["sam3"] = "not_importable"
    else:
        versions["sam3"] = str(getattr(sam3, "__version__", "editable_or_unknown"))
    return versions


def get_torch_cuda_info() -> dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {"torch_importable": False}

    info: dict[str, Any] = {
        "torch_importable": True,
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count(),
    }
    if torch.cuda.is_available():
        info["cuda_device_name"] = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        info["cuda_total_memory_mb"] = round(props.total_memory / (1024 * 1024), 2)
    return info


def cuda_synchronize(segmenter: SAM3Segmenter) -> None:
    torch = segmenter._torch
    if torch is not None and torch.cuda.is_available():
        torch.cuda.synchronize()


def reset_cuda_peak_stats(segmenter: SAM3Segmenter) -> None:
    torch = segmenter._torch
    if torch is not None and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def cuda_peak_memory_mb(segmenter: SAM3Segmenter) -> tuple[float | None, float | None]:
    torch = segmenter._torch
    if torch is None or not torch.cuda.is_available():
        return None, None
    allocated = torch.cuda.max_memory_allocated() / (1024 * 1024)
    reserved = torch.cuda.max_memory_reserved() / (1024 * 1024)
    return round(allocated, 2), round(reserved, 2)


def benchmark_frames(
    segmenter: SAM3Segmenter,
    video_path: str,
    frames: list[int],
    prompts: list[str],
    name: str,
) -> BenchmarkRun:
    before_gpu = read_gpu_snapshot()
    reset_cuda_peak_stats(segmenter)
    cuda_synchronize(segmenter)
    start = time.perf_counter()
    detections = segmenter.segment_video(video_path, frames, prompts)
    cuda_synchronize(segmenter)
    elapsed = time.perf_counter() - start
    after_gpu = read_gpu_snapshot()
    allocated_peak, reserved_peak = cuda_peak_memory_mb(segmenter)
    detection_count = sum(len(frame.detections) for frame in detections)
    frame_count = len(detections)
    before_memory = before_gpu.memory_used_mb if before_gpu else None
    after_memory = after_gpu.memory_used_mb if after_gpu else None
    delta = None
    if before_memory is not None and after_memory is not None:
        delta = round(after_memory - before_memory, 2)
    sec_per_frame = elapsed / max(frame_count, 1)
    return BenchmarkRun(
        name=name,
        frames=tuple(frames),
        frame_count=frame_count,
        prompt_count=len(prompts),
        detection_count=detection_count,
        elapsed_sec=round(elapsed, 4),
        sec_per_frame=round(sec_per_frame, 4),
        fps_effective=round(frame_count / elapsed, 4) if elapsed > 0 else 0.0,
        cuda_memory_allocated_peak_mb=allocated_peak,
        cuda_memory_reserved_peak_mb=reserved_peak,
        nvidia_smi_memory_before_mb=before_memory,
        nvidia_smi_memory_after_mb=after_memory,
        nvidia_smi_memory_delta_mb=delta,
    )


def write_metrics_csv(runs: list[BenchmarkRun], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(runs[0]).keys()) if runs else ["name"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            row = asdict(run)
            row["frames"] = " ".join(str(frame) for frame in run.frames)
            writer.writerow(row)


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    runs = payload["runs"]
    single = next((run for run in runs if run["name"] == "single_frame"), None)
    multi = next((run for run in runs if run["name"] == "multi_frame"), None)
    lines = [
        "# test_007_msi_benchmarks",
        "",
        "## Configuracion",
        "",
        f"- Video: `{payload['video']['path']}`",
        f"- Resolucion: `{payload['video']['width']}x{payload['video']['height']}`.",
        f"- FPS video: `{payload['video']['fps']}`.",
        f"- Checkpoint: `{payload['checkpoint_path']}`.",
        f"- Prompts: `{', '.join(payload['prompts'])}`.",
        f"- Frames single: `{', '.join(str(frame) for frame in payload['single_frame'])}`.",
        f"- Frames multi: `{', '.join(str(frame) for frame in payload['multi_frame'])}`.",
        "",
        "## Hardware/software",
        "",
        f"- SO: `{payload['environment']['platform']}`.",
        f"- Python: `{payload['environment']['python_version']}`.",
    ]
    gpu = payload.get("gpu_before_load")
    if gpu:
        lines.extend(
            [
                f"- GPU: `{gpu['name']}`.",
                f"- Driver NVIDIA: `{gpu['driver_version']}`.",
                f"- VRAM total: `{gpu['memory_total_mb']} MB`.",
            ]
        )
    cuda = payload["environment"]["torch_cuda"]
    lines.extend(
        [
            f"- PyTorch: `{payload['environment']['packages'].get('torch')}`.",
            f"- CUDA disponible para PyTorch: `{cuda.get('cuda_available')}`.",
            f"- CUDA runtime PyTorch: `{cuda.get('torch_cuda_version')}`.",
        ]
    )
    lines.extend(["", "## Resultados", ""])
    lines.append(
        "- Carga SAM 3: `{load_sec}s`; VRAM nvidia-smi antes/despues `{before}` -> `{after}` MB.".format(
            load_sec=payload["load_time_sec"],
            before=payload.get("gpu_before_load", {}).get("memory_used_mb") if payload.get("gpu_before_load") else "n/a",
            after=payload.get("gpu_after_load", {}).get("memory_used_mb") if payload.get("gpu_after_load") else "n/a",
        )
    )
    for run in runs:
        lines.append(
            "- `{name}`: `{frame_count}` frames, `{elapsed_sec}s`, `{sec_per_frame}s/frame`, "
            "`{fps_effective}` FPS efectivos, detecciones `{detection_count}`, pico CUDA allocated/reserved "
            "`{cuda_memory_allocated_peak_mb}`/`{cuda_memory_reserved_peak_mb}` MB, nvidia-smi `{nvidia_smi_memory_before_mb}` -> `{nvidia_smi_memory_after_mb}` MB.".format(
                **run
            )
        )
    if single and multi:
        ratio = multi["sec_per_frame"] / single["sec_per_frame"] if single["sec_per_frame"] else 0
        lines.extend(
            [
                "",
                "## Comparacion",
                "",
                "- Multi-frame queda en `{ratio:.2f}x` del tiempo por frame de la corrida single-frame.".format(
                    ratio=ratio
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Artefactos",
            "",
            "- `benchmark.json`",
            "- `metrics.csv`",
            "- `config.yaml`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark SAM 3 load/inference on the MSI GPU laptop.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--video", required=True)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--experiment", default="experiments/test_007_msi_benchmarks/video_836_sam3")
    parser.add_argument("--single-frame", type=int, default=120)
    parser.add_argument("--multi-frame", nargs="+", type=int, default=[120, 130, 140, 150, 160])
    parser.add_argument("--prompt", action="append", dest="prompts", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    prompt_values = args.prompts or config["segmentation"]["classes"]
    prompts = [prompt.replace("_", " ") for prompt in prompt_values]
    video_metadata = inspect_video(args.video)
    gpu_before_load = read_gpu_snapshot()

    try:
        segmenter = SAM3Segmenter(
            checkpoint_path=args.checkpoint,
            confidence_threshold=float(config["segmentation"].get("confidence_threshold", 0.5)),
        )
        load_start = time.perf_counter()
        segmenter._ensure_processor()
        cuda_synchronize(segmenter)
        load_time_sec = round(time.perf_counter() - load_start, 4)
        gpu_after_load = read_gpu_snapshot()
        runs = [
            benchmark_frames(segmenter, args.video, [args.single_frame], prompts, "single_frame"),
            benchmark_frames(segmenter, args.video, list(args.multi_frame), prompts, "multi_frame"),
        ]
    except SAM3UnavailableError as exc:
        (experiment / "errors.md").write_text(
            "# SAM 3 benchmark pending\n\n"
            f"{exc}\n\n"
            "Run this script on the MSI laptop with CUDA available.\n",
            encoding="utf-8",
        )
        print(str(exc))
        return 2

    payload = {
        "video": video_metadata.to_dict(),
        "checkpoint_path": args.checkpoint,
        "prompts": prompts,
        "single_frame": [args.single_frame],
        "multi_frame": list(args.multi_frame),
        "load_time_sec": load_time_sec,
        "gpu_before_load": asdict(gpu_before_load) if gpu_before_load else None,
        "gpu_after_load": asdict(gpu_after_load) if gpu_after_load else None,
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "packages": get_package_versions(),
            "torch_cuda": get_torch_cuda_info(),
        },
        "runs": [asdict(run) for run in runs],
    }
    (experiment / "benchmark.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_metrics_csv(runs, experiment / "metrics.csv")
    write_summary(experiment / "summary.md", payload)
    print(f"Wrote benchmark to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
