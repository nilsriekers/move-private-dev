#!/usr/bin/env python3
"""Exploratory plots for classification chapter.

Panel 1 — Per-class F1 vs. class support (test set)
  Each point = one syllable class × one seed.
  All birds overlaid, colored per bird.
  Shows whether rare classes are harder to classify.

Panel 2 — Training set size vs. test accuracy
  Each point = one bird × one seed.
  Analogous to Figure 4D (segmentation: duration vs. F1).

Output: classification_chapter/figure_5/explore_class_support.{svg,png}
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import fontManager
import numpy as np
from scipy import stats

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "classification_chapter", "results")
OUTPUT_DIR  = SCRIPT_DIR

BIRD_IDS = ["ye00pu07", "bu04bk04", "gy07bu07", "br08pk08", "ye04gr05"]
BIRD_LABELS = {
    "ye00pu07": "Bird 1",
    "bu04bk04": "Bird 2",
    "gy07bu07": "Bird 3",
    "br08pk08": "Bird 4",
    "ye04gr05": "Bird 5",
}
BIRD_COLORS = {
    "ye00pu07": "#1f77b4",
    "bu04bk04": "#ff7f0e",
    "gy07bu07": "#2ca02c",
    "br08pk08": "#d62728",
    "ye04gr05": "#9467bd",
}
SEEDS = [42, 123, 456]


def setup_fonts():
    cmu = "/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf"
    if os.path.isfile(cmu):
        fontManager.addfont(cmu)
        rcParams["font.family"] = "CMU Serif"
    else:
        rcParams["font.family"] = "serif"
    rcParams["font.size"]         = 10
    rcParams["axes.labelsize"]    = 11
    rcParams["axes.titlesize"]    = 11
    rcParams["legend.fontsize"]   = 8
    rcParams["xtick.labelsize"]   = 9
    rcParams["ytick.labelsize"]   = 9
    rcParams["figure.dpi"]        = 300
    rcParams["savefig.dpi"]       = 300
    rcParams["text.usetex"]       = False
    rcParams["lines.linewidth"]   = 1.5
    rcParams["axes.linewidth"]    = 0.8
    rcParams["axes.spines.top"]   = False
    rcParams["axes.spines.right"] = False
    rcParams["axes.grid"]         = True
    rcParams["axes.axisbelow"]    = True
    rcParams["grid.alpha"]        = 0.3
    rcParams["grid.linewidth"]    = 0.5


def load_results():
    results = {}
    for bird in BIRD_IDS:
        runs = []
        for seed in SEEDS:
            p = os.path.join(RESULTS_DIR, bird, f"seed_{seed}", "results.json")
            if os.path.isfile(p):
                with open(p) as f:
                    runs.append(json.load(f))
        if runs:
            results[bird] = runs
    return results


# ── Panel 1: Per-class F1 vs. support ────────────────────────────────

def plot_f1_vs_support(ax, results):
    all_support, all_f1 = [], []

    for bird in BIRD_IDS:
        if bird not in results:
            continue
        color = BIRD_COLORS[bird]
        label = BIRD_LABELS[bird]

        # Collect per-class F1 + support across all seeds
        # Aggregate: mean F1 per class across seeds, support from seed_42
        per_class_data = {}
        for r in results[bird]:
            for cls, metrics in r["classification"]["per_class"].items():
                if cls not in per_class_data:
                    per_class_data[cls] = {"f1": [], "support": metrics["support"]}
                per_class_data[cls]["f1"].append(metrics["f1"])

        supports = np.array([v["support"] for v in per_class_data.values()])
        f1_means = np.array([np.mean(v["f1"]) for v in per_class_data.values()])
        f1_stds  = np.array([np.std(v["f1"])  for v in per_class_data.values()])

        all_support.extend(supports.tolist())
        all_f1.extend(f1_means.tolist())

        ax.scatter(supports, f1_means, color=color, s=50,
                   label=label, zorder=3,
                   edgecolors="white", linewidth=0.5)
        ax.errorbar(supports, f1_means, yerr=f1_stds,
                    fmt="none", color=color, alpha=0.5,
                    linewidth=1.0, capsize=2, zorder=2)

    # Regression line across all points
    all_support = np.array(all_support)
    all_f1      = np.array(all_f1)
    if len(all_support) > 2:
        slope, intercept, r, p, _ = stats.linregress(all_support, all_f1)
        x_line = np.linspace(all_support.min(), all_support.max(), 200)
        ax.plot(x_line, slope * x_line + intercept,
                color="black", linewidth=1.2, linestyle="--", alpha=0.6,
                label=f"regression (r={r:.2f}, p={p:.3f})", zorder=1)

    ax.set_xlabel("Test set support (n syllables per class)")
    ax.set_ylabel("Per-class F1 (mean ± SD over 3 seeds)")
    ax.set_title("Per-class F1 vs. Class Frequency")
    ax.set_ylim(0.75, 1.02)
    ax.legend(fontsize=8, loc="lower right")


# ── Panel 2: Training set size vs. accuracy ──────────────────────────

def plot_size_vs_accuracy(ax, results):
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        color = BIRD_COLORS[bird]
        label = BIRD_LABELS[bird]

        n_trains = [r["data_stats_before_downsampling"]["n_train"]
                    for r in results[bird]]
        accs     = [r["test_accuracy"] for r in results[bird]]

        # Mean ± SD across seeds shown as single point + error bars
        mean_n   = np.mean(n_trains)
        mean_acc = np.mean(accs)
        std_acc  = np.std(accs)

        # Individual seed points (semi-transparent)
        ax.scatter(n_trains, accs, color=color, s=30, alpha=0.4, zorder=2,
                   edgecolors="none")
        # Mean point
        ax.scatter([mean_n], [mean_acc], color=color, s=90, zorder=4,
                   edgecolors="white", linewidth=0.8, label=label)
        ax.errorbar([mean_n], [mean_acc], yerr=[std_acc],
                    fmt="none", color=color, linewidth=1.5,
                    capsize=4, capthick=1.2, zorder=3)
        ax.annotate(label, (mean_n, mean_acc),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=8, color=color)

    # Regression across bird means
    mean_ns   = []
    mean_accs = []
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        mean_ns.append(np.mean([r["data_stats_before_downsampling"]["n_train"]
                                for r in results[bird]]))
        mean_accs.append(np.mean([r["test_accuracy"] for r in results[bird]]))

    mean_ns   = np.array(mean_ns)
    mean_accs = np.array(mean_accs)
    if len(mean_ns) > 2:
        slope, intercept, r, p, _ = stats.linregress(mean_ns, mean_accs)
        x_line = np.linspace(mean_ns.min() * 0.85, mean_ns.max() * 1.05, 200)
        ax.plot(x_line, slope * x_line + intercept,
                color="black", linewidth=1.2, linestyle="--", alpha=0.6,
                label=f"regression (r={r:.2f}, p={p:.3f})", zorder=1)

    ax.set_xlabel("Training set size (n syllables)")
    ax.set_ylabel("Test accuracy")
    ax.set_title("Training Set Size vs. Accuracy")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
    ax.legend(fontsize=8, loc="lower right")


# ── Compose ───────────────────────────────────────────────────────────

def main():
    setup_fonts()
    results = load_results()
    print(f"Loaded results: {list(results.keys())}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.subplots_adjust(wspace=0.35)

    plot_f1_vs_support(axes[0], results)
    plot_size_vs_accuracy(axes[1], results)

    axes[0].text(-0.12, 1.08, "A", transform=axes[0].transAxes,
                 fontsize=16, fontweight="bold", va="top")
    axes[1].text(-0.12, 1.08, "B", transform=axes[1].transAxes,
                 fontsize=16, fontweight="bold", va="top")

    for ext in ["svg", "png"]:
        path = os.path.join(OUTPUT_DIR, f"explore_class_support.{ext}")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
