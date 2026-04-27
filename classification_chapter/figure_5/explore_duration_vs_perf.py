#!/usr/bin/env python3
"""Training duration (30 ms snippets) vs. classification performance.
Analogous to Figure 4D (segmentation: duration vs. framewise F1).

Note: duration here = n_train × 30.5 ms — NOT the real syllable duration,
only the fixed onset window used for training.

Output: classification_chapter/figure_5/explore_duration_vs_perf.{svg,png}
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import fontManager
from matplotlib.ticker import FuncFormatter
import numpy as np

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "classification_chapter", "results")
OUTPUT_DIR  = SCRIPT_DIR

BIRD_IDS = ["ye00pu07", "bu04bk04", "gy07bu07", "br08pk08", "ye04gr05"]
BIRD_LABELS = {
    "ye00pu07": "Bird 1", "bu04bk04": "Bird 2", "gy07bu07": "Bird 3",
    "br08pk08": "Bird 4", "ye04gr05": "Bird 5",
}
BIRD_COLORS = {
    "ye00pu07": "#1f77b4", "bu04bk04": "#ff7f0e", "gy07bu07": "#2ca02c",
    "br08pk08": "#d62728", "ye04gr05": "#9467bd",
}
SEEDS = [42, 123, 456]


def setup_fonts():
    cmu = "/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf"
    if os.path.isfile(cmu):
        fontManager.addfont(cmu)
        rcParams["font.family"] = "CMU Serif"
    else:
        rcParams["font.family"] = "serif"
    rcParams.update({
        "font.size": 10, "axes.labelsize": 11, "axes.titlesize": 11,
        "legend.fontsize": 8, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "figure.dpi": 300, "savefig.dpi": 300, "text.usetex": False,
        "lines.linewidth": 1.5, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True,
        "grid.alpha": 0.3, "grid.linewidth": 0.5,
    })


def plot_duration_vs_perf(ax, metric_key, ylabel, title):
    for bird in BIRD_IDS:
        color = BIRD_COLORS[bird]
        durs, vals = [], []
        for seed in SEEDS:
            p = os.path.join(RESULTS_DIR, bird, f"seed_{seed}", "results.json")
            with open(p) as f:
                r = json.load(f)
            dur = r["data_stats_before_downsampling"]["duration_train_s"]
            v = r
            for part in metric_key.split("."):
                v = v[part]
            durs.append(dur)
            vals.append(v)

        durs = np.array(durs)
        vals = np.array(vals)

        # Individual seed points
        ax.scatter(durs, vals, color=color, s=40, alpha=0.45,
                   zorder=2, edgecolors="none")
        # Mean point with SD
        ax.scatter([durs.mean()], [vals.mean()], color=color, s=100,
                   zorder=4, edgecolors="white", linewidth=0.8,
                   label=f"{BIRD_LABELS[bird]} ({r['num_classes']} cls)")
        ax.errorbar([durs.mean()], [vals.mean()], yerr=vals.std(),
                    fmt="none", color=color, linewidth=1.5,
                    capsize=4, capthick=1.2, zorder=3)
        ax.annotate(BIRD_LABELS[bird], (durs.mean(), vals.mean()),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=8, color=color)

    ax.set_xscale("log")
    ax.set_xlabel("Training set duration (s, log scale)\n"
                  "[= n_train x 30.5 ms onset windows]")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(fontsize=7, loc="lower right", title="n classes in legend")


def main():
    setup_fonts()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.subplots_adjust(wspace=0.35)

    plot_duration_vs_perf(axes[0],
                          metric_key="test_accuracy",
                          ylabel="Test accuracy",
                          title="Training duration vs. Accuracy")

    plot_duration_vs_perf(axes[1],
                          metric_key="classification.macro.f1",
                          ylabel="Macro-F1",
                          title="Training duration vs. Macro-F1")

    axes[0].text(-0.12, 1.08, "A", transform=axes[0].transAxes,
                 fontsize=14, fontweight="bold", va="top")
    axes[1].text(-0.12, 1.08, "B", transform=axes[1].transAxes,
                 fontsize=14, fontweight="bold", va="top")

    for ext in ["svg", "png"]:
        path = os.path.join(OUTPUT_DIR, f"explore_duration_vs_perf.{ext}")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
