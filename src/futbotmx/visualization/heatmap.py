from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


def write_heatmap(tracks_csv: str | Path, output_path: str | Path, width: int, height: int) -> None:
    xs: list[float] = []
    ys: list[float] = []
    with Path(tracks_csv).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.hist2d(xs, ys, bins=24, range=[[0, width], [0, height]], cmap="magma")
    plt.gca().invert_yaxis()
    plt.title("FutBotMX activity heatmap")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.colorbar(label="positions")
    plt.tight_layout()
    plt.savefig(output)
    plt.close()
