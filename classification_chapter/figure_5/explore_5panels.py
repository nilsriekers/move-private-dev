#!/usr/bin/env python3
"""Explore 5 candidate plots for classification chapter.

1. n_classes vs. accuracy
2. n_train/n_classes vs. accuracy
3. Class imbalance (CV of train distribution) vs. macro-F1
4. Macro-Precision vs. Macro-Recall scatter
5. Confusion matrix entropy vs. accuracy

Output: classification_chapter/figure_5/explore_5panels.{svg,png}
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
from scipy import stats

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
        "font.size": 10, "axes.labelsize": 11, "axes.titlesize": 10,
        "legend.fontsize": 8, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "figure.dpi": 300, "savefig.dpi": 300, "text.usetex": False,
        "lines.linewidth": 1.5, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True,
        "grid.alpha": 0.3, "grid.linewidth": 0.5,
    })


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


def _scatter_birds(ax, xs, ys, xlabel, ylabel, title, fmt_y_pct=True,
                   jitter_x=False, integer_x=False):
    """Generic scatter: one mean point + seed jitter per bird, regression line."""
    all_x_mean, all_y_mean = [], []

    for bird in BIRD_IDS:
        if bird not in xs:
            continue
        color = BIRD_COLORS[bird]
        x_vals = np.array(xs[bird])
        y_vals = np.array(ys[bird])

        jit = np.random.default_rng(0).uniform(-0.15, 0.15, len(x_vals)) \
              if jitter_x else np.zeros(len(x_vals))

        ax.scatter(x_vals + jit, y_vals, color=color, s=30,
                   alpha=0.45, zorder=2, edgecolors="none")
        mx, my = np.mean(x_vals), np.mean(y_vals)
        ax.scatter([mx], [my], color=color, s=90, zorder=4,
                   edgecolors="white", linewidth=0.8, label=BIRD_LABELS[bird])
        ax.errorbar([mx], [my], yerr=np.std(y_vals),
                    fmt="none", color=color, linewidth=1.4,
                    capsize=3, capthick=1.1, zorder=3)
        ax.annotate(BIRD_LABELS[bird], (mx, my),
                    textcoords="offset points", xytext=(5, 4),
                    fontsize=8, color=color)
        all_x_mean.append(mx)
        all_y_mean.append(my)

    # Regression over bird means
    all_x_mean = np.array(all_x_mean)
    all_y_mean = np.array(all_y_mean)
    if len(all_x_mean) > 2:
        slope, intercept, r, p, _ = stats.linregress(all_x_mean, all_y_mean)
        xl = np.linspace(all_x_mean.min() * 0.90, all_x_mean.max() * 1.05, 200)
        ax.plot(xl, slope * xl + intercept, "k--", linewidth=1.1, alpha=0.55,
                label=f"r={r:.2f}, p={p:.3f}", zorder=1)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if fmt_y_pct:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    if integer_x:
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.legend(fontsize=7, loc="lower right")


# ── Plot 1: n_classes vs. accuracy ───────────────────────────────────

def plot1_nclasses_vs_acc(ax, results):
    xs, ys = {}, {}
    for bird, runs in results.items():
        xs[bird] = [r["num_classes"] for r in runs]
        ys[bird] = [r["test_accuracy"] for r in runs]
    _scatter_birds(ax, xs, ys,
                   xlabel="Number of syllable classes",
                   ylabel="Test accuracy",
                   title="1. Repertoire size vs. accuracy",
                   jitter_x=True, integer_x=True)


# ── Plot 2: n_train/n_classes vs. accuracy ────────────────────────────

def plot2_samplesperclass_vs_acc(ax, results):
    xs, ys = {}, {}
    for bird, runs in results.items():
        xs[bird] = [r["data_stats_before_downsampling"]["n_train"] / r["num_classes"]
                    for r in runs]
        ys[bird] = [r["test_accuracy"] for r in runs]
    _scatter_birds(ax, xs, ys,
                   xlabel="Training samples per class",
                   ylabel="Test accuracy",
                   title="2. Samples/class vs. accuracy")


# ── Plot 3: CV of training distribution vs. macro-F1 ─────────────────

def plot3_imbalance_vs_f1(ax, results):
    xs, ys = {}, {}
    for bird, runs in results.items():
        cvs, f1s = [], []
        for r in runs:
            counts = np.array(list(
                r["data_stats_before_downsampling"]["class_distribution_train"].values()
            ), dtype=float)
            cvs.append(counts.std() / counts.mean())
            f1s.append(r["classification"]["macro"]["f1"])
        xs[bird] = cvs
        ys[bird] = f1s
    _scatter_birds(ax, xs, ys,
                   xlabel="Class imbalance (CV of train distribution)",
                   ylabel="Macro-F1",
                   title="3. Class imbalance vs. macro-F1")


# ── Plot 4: Macro-Precision vs. Macro-Recall ─────────────────────────

def plot4_precision_vs_recall(ax, results):
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        color = BIRD_COLORS[bird]
        runs  = results[bird]
        precs = [r["classification"]["macro"]["precision"] for r in runs]
        recs  = [r["classification"]["macro"]["recall"]    for r in runs]
        ax.scatter(precs, recs, color=color, s=50, zorder=3,
                   edgecolors="white", linewidth=0.5)
        mp, mr = np.mean(precs), np.mean(recs)
        ax.scatter([mp], [mr], color=color, s=100, zorder=4,
                   edgecolors="white", linewidth=0.8, label=BIRD_LABELS[bird])
        ax.annotate(BIRD_LABELS[bird], (mp, mr),
                    textcoords="offset points", xytext=(5, 3),
                    fontsize=8, color=color)

    # Diagonal (P = R)
    lims = [0.85, 1.01]
    ax.plot(lims, lims, "k:", linewidth=0.9, alpha=0.5, label="P = R")
    ax.set_xlim(*lims)
    ax.set_ylim(*lims)
    ax.set_xlabel("Macro-Precision")
    ax.set_ylabel("Macro-Recall")
    ax.set_title("4. Macro-Precision vs. Macro-Recall")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(fontsize=7, loc="lower right")


# ── Plot 5: Confusion-matrix entropy vs. accuracy ────────────────────

def _off_diagonal_entropy(cm_norm):
    """Shannon entropy of the off-diagonal error distribution."""
    n = cm_norm.shape[0]
    off = []
    for i in range(n):
        for j in range(n):
            if i != j:
                off.append(cm_norm[i, j])
    off = np.array(off)
    off = off[off > 0]
    if len(off) == 0:
        return 0.0
    return float(-np.sum(off * np.log2(off)))


def plot5_entropy_vs_acc(ax, results):
    xs, ys = {}, {}
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        entropies, accs = [], []
        for seed in SEEDS:
            npy = os.path.join(RESULTS_DIR, bird, f"seed_{seed}",
                               "confusion_matrix_norm.npy")
            if not os.path.isfile(npy):
                continue
            cm_norm = np.load(npy)
            entropies.append(_off_diagonal_entropy(cm_norm))
            # match to the right run
            run = next((r for r in results[bird] if r["seed"] == seed), None)
            if run:
                accs.append(run["test_accuracy"])
        if entropies:
            xs[bird] = entropies
            ys[bird] = accs

    _scatter_birds(ax, xs, ys,
                   xlabel="Off-diagonal entropy (bits)",
                   ylabel="Test accuracy",
                   title="5. Confusion entropy vs. accuracy")


# ── Compose ───────────────────────────────────────────────────────────

def main():
    setup_fonts()
    results = load_results()

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.subplots_adjust(hspace=0.45, wspace=0.38)

    plot1_nclasses_vs_acc(axes[0, 0], results)
    plot2_samplesperclass_vs_acc(axes[0, 1], results)
    plot3_imbalance_vs_f1(axes[0, 2], results)
    plot4_precision_vs_recall(axes[1, 0], results)
    plot5_entropy_vs_acc(axes[1, 1], results)
    axes[1, 2].set_visible(False)

    for i, ax in enumerate(axes.flat[:5]):
        ax.text(-0.12, 1.10, "ABCDE"[i],
                transform=ax.transAxes, fontsize=14,
                fontweight="bold", va="top")

    for ext in ["svg", "png"]:
        path = os.path.join(OUTPUT_DIR, f"explore_5panels.{ext}")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
