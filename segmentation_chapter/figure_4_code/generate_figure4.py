#!/usr/bin/env python3
"""Generate new Figure 4 for the revised paper.

Reads results.json from final_experiments/results/ (5 birds x 3 seeds)
and produces a multi-panel figure:

  A) Training loss curves over epochs (one subplot per bird, mean +/- std)
  B) Framewise Precision / Recall / F1 per bird (RAW, dot plot)
  C) Onset-based segment-level collar F1 vs tolerance (WITH sliding window)
  D) Training set duration vs Framewise F1 (scatter)

Outputs are saved as SVG and PNG in segmentation_chapter/figure_4_code/.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import fontManager
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D
import numpy as np

# ── Config flags ─────────────────────────────────────────────────────
USE_LOG_SCALE = True  # Log scale for Panel D x-axis (training duration)

# ── Paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "final_experiments", "results")
OUTPUT_DIR = SCRIPT_DIR

# ── Bird order and display names ─────────────────────────────────────
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
COLLAR_VALUES_MS = [5, 10, 15, 20]
SEEDS = [42, 123, 456]
VAL_COLOR = "#888888"  # grey for validation curves


# ── Font setup ───────────────────────────────────────────────────────

def setup_fonts():
    cmu_regular = "/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf"
    cmu_bold = "/Library/Fonts/CMU-Serif-Roman/cmunbx.ttf"

    if os.path.isfile(cmu_regular):
        fontManager.addfont(cmu_regular)
        if os.path.isfile(cmu_bold):
            fontManager.addfont(cmu_bold)
        rcParams["font.family"] = "CMU Serif"
    else:
        rcParams["font.family"] = "serif"

    rcParams["font.size"] = 10
    rcParams["axes.labelsize"] = 11
    rcParams["axes.titlesize"] = 11
    rcParams["legend.fontsize"] = 8
    rcParams["xtick.labelsize"] = 9
    rcParams["ytick.labelsize"] = 9
    rcParams["figure.dpi"] = 300
    rcParams["savefig.dpi"] = 300
    rcParams["text.usetex"] = False
    rcParams["lines.linewidth"] = 1.5
    rcParams["axes.linewidth"] = 0.8
    rcParams["axes.spines.top"] = False
    rcParams["axes.spines.right"] = False
    rcParams["axes.grid"] = True
    rcParams["axes.axisbelow"] = True
    rcParams["grid.alpha"] = 0.3
    rcParams["grid.linewidth"] = 0.5


# ── Data loading ─────────────────────────────────────────────────────

def load_seg_results():
    results = {}
    for bird in BIRD_IDS:
        runs = []
        for seed in SEEDS:
            path = os.path.join(RESULTS_DIR, bird, "seg", f"seed_{seed}", "results.json")
            if os.path.isfile(path):
                with open(path) as f:
                    runs.append(json.load(f))
        if runs:
            results[bird] = runs
    return results


# ── Panel A: Loss curves (small multiples) ───────────────────────────

def plot_loss_small_multiples(axes, results):
    """One subplot per bird. Train in bird color, Val in grey."""
    # First pass: collect all data to compute global y-range
    all_vals = []
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        histories = [r["history"] for r in runs if "history" in r]
        if not histories:
            continue
        min_len = min(len(h["train_loss"]) for h in histories)
        train_arr = np.array([h["train_loss"][:min_len] for h in histories])
        val_arr = np.array([h["val_loss"][:min_len] for h in histories])
        all_vals.extend((train_arr.mean(0) + train_arr.std(0)).tolist())
        all_vals.extend((val_arr.mean(0) + val_arr.std(0)).tolist())
        all_vals.extend((train_arr.mean(0) - train_arr.std(0)).tolist())
        all_vals.extend((val_arr.mean(0) - val_arr.std(0)).tolist())
    # OLD: each subplot had its own auto-scaled y-range
    global_ymin = max(0.0, min(all_vals) * 0.95)
    global_ymax = max(all_vals) * 1.05

    for idx, bird in enumerate(BIRD_IDS):
        ax = axes[idx]
        if bird not in results:
            ax.set_visible(False)
            continue

        runs = results[bird]
        color = BIRD_COLORS[bird]
        label = BIRD_LABELS[bird]

        histories = [r["history"] for r in runs if "history" in r]
        if not histories:
            continue

        min_len = min(len(h["train_loss"]) for h in histories)
        train_arr = np.array([h["train_loss"][:min_len] for h in histories])
        val_arr = np.array([h["val_loss"][:min_len] for h in histories])
        ep = np.arange(1, min_len + 1)

        # Train: bird color, solid
        ax.plot(ep, train_arr.mean(0), color=color, linewidth=1.8, label="Train")
        ax.fill_between(ep,
                        train_arr.mean(0) - train_arr.std(0),
                        train_arr.mean(0) + train_arr.std(0),
                        color=color, alpha=0.15)

        # Val: grey, dashed
        ax.plot(ep, val_arr.mean(0), color=VAL_COLOR, linewidth=1.8,
                linestyle="--", label="Val")
        ax.fill_between(ep,
                        val_arr.mean(0) - val_arr.std(0),
                        val_arr.mean(0) + val_arr.std(0),
                        color=VAL_COLOR, alpha=0.12)

        ax.set_ylim(global_ymin, global_ymax)
        ax.set_title(label, fontsize=10)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        if idx == 0:
            ax.set_ylabel("Loss")
            ax.legend(fontsize=7, loc="upper right")
        if idx == 2:
            ax.set_xlabel("Epoch")


# ── Panel B: Framewise P/R/F1 dot plot (RAW) ────────────────────────

def plot_framewise_dots(ax, results):
    """Dot plot with error bars for framewise P/R/F1 per bird (RAW, no SW)."""
    birds = [b for b in BIRD_IDS if b in results]
    metrics = ["precision", "recall", "f1"]
    metric_labels = ["Precision", "Recall", "F1"]
    metric_markers = ["o", "s", "D"]
    metric_colors = ["#4e79a7", "#f28e2b", "#59a14f"]

    y = np.arange(len(birds))

    for i, (m, ml, mk, mc) in enumerate(zip(metrics, metric_labels,
                                              metric_markers, metric_colors)):
        means = [np.mean([r["framewise"][m] for r in results[b]]) for b in birds]
        stds = [np.std([r["framewise"][m] for r in results[b]]) for b in birds]

        offset = (i - 1) * 0.15
        ax.errorbar(means, y + offset, xerr=stds, fmt=mk, color=mc,
                    markersize=7, capsize=3, capthick=1.2, linewidth=1.2,
                    label=ml, markeredgecolor="white", markeredgewidth=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels([BIRD_LABELS[b] for b in birds])
    ax.set_xlabel("Score")
    ax.set_title("Framewise Segmentation (no SW)")
    # ax.set_xlim(0.88, 1.0)  # OLD: narrow range
    ax.set_xlim(0.7, 1.0)
    ax.legend(loc="lower left", fontsize=8)
    ax.invert_yaxis()


def load_baseline_results():
    results = {}
    for bird in BIRD_IDS:
        runs = []
        for seed in SEEDS:
            path = os.path.join(RESULTS_DIR, bird, "seg_baseline", f"seed_{seed}", "results.json")
            if os.path.isfile(path):
                with open(path) as f:
                    runs.append(json.load(f))
        if runs:
            results[bird] = runs
    return results


# ── Panel C: Collar F1 vs tolerance (WITH sliding window) ───────────

def plot_collar_f1(ax, results, baseline_results=None):
    """Onset-based segment-level F1 vs collar tolerance.
    Moove: onset_collar_SMOOTHED (with sliding window) — solid lines.
    Baseline: onset_collar RAW (no SW, not applicable for energy segmenter) — dashed lines.
    """
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        color = BIRD_COLORS[bird]
        label = BIRD_LABELS[bird]

        means, stds = [], []
        for cms in COLLAR_VALUES_MS:
            collar_key = f"@{cms}ms"
            vals = [r["onset_collar_smoothed"][collar_key]["f1"] for r in runs]
            means.append(np.mean(vals))
            stds.append(np.std(vals))
        means, stds = np.array(means), np.array(stds)

        ax.plot(COLLAR_VALUES_MS, means, "o-", color=color, label=label,
                linewidth=2, markersize=5)
        ax.fill_between(COLLAR_VALUES_MS, means - stds, means + stds,
                        color=color, alpha=0.12)

    # Baseline: raw onset_collar (no SW — not applicable for energy segmenter)
    if baseline_results:
        for bird in BIRD_IDS:
            if bird not in baseline_results:
                continue
            runs = baseline_results[bird]
            color = BIRD_COLORS[bird]

            means, stds = [], []
            for cms in COLLAR_VALUES_MS:
                collar_key = f"@{cms}ms"
                vals = [r["onset_collar"][collar_key]["f1"] for r in runs]
                means.append(np.mean(vals))
                stds.append(np.std(vals))
            means, stds = np.array(means), np.array(stds)

            ax.plot(COLLAR_VALUES_MS, means, "--", color=color,
                    linewidth=1.2, markersize=0, alpha=0.7)
            ax.fill_between(COLLAR_VALUES_MS, means - stds, means + stds,
                            color=color, alpha=0.07)

    ax.set_xlabel("Collar tolerance (ms)")
    ax.set_ylabel("Onset-based F1")
    ax.set_title("Onset Collar F1 (Moove +SW vs Baseline)")
    ax.set_xticks(COLLAR_VALUES_MS)
    # ax.set_ylim(0.1, 1.0)  # OLD: too much empty space below
    ax.set_ylim(0.5, 1.0)  # baseline @5ms goes down to ~0.53
    ax.legend(fontsize=8)


# ── Panel D: Training duration vs F1 scatter ─────────────────────────

def plot_duration_vs_f1(ax, results):
    """Scatter: training duration (s) vs framewise F1, one point per seed."""
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        color = BIRD_COLORS[bird]
        label = BIRD_LABELS[bird]

        durs = [r["data_stats_before_downsampling"]["duration_train_s"] for r in runs]
        f1s = [r["framewise"]["f1"] for r in runs]

        ax.scatter(durs, f1s, color=color, s=60, label=label, edgecolors="white",
                   linewidth=0.5, zorder=3)

    ax.set_xlabel("Training set duration (s)")
    ax.set_ylabel("Framewise F1")
    ax.set_title("Training Data Size vs. Performance")
    if USE_LOG_SCALE:
        ax.set_xscale("log")
    # OLD: no explicit ylim set
    ax.set_ylim(0.7, 1.0)
    ax.legend(fontsize=8)


# ── Compose figure ───────────────────────────────────────────────────

def generate_figure4():
    setup_fonts()
    results = load_seg_results()
    baseline_results = load_baseline_results()

    if not results:
        print("ERROR: No segmentation results found in", RESULTS_DIR)
        sys.exit(1)

    print(f"Loaded segmentation results for {len(results)} birds, "
          f"seeds per bird: {[len(v) for v in results.values()]}")
    print(f"Loaded baseline results for {len(baseline_results)} birds")

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 6, hspace=0.55, wspace=0.5,
                          height_ratios=[1, 1.2])

    # Row 1: 5 small loss subplots
    loss_axes = [fig.add_subplot(gs[0, i]) for i in range(5)]

    # Row 2: 3 panels
    ax_b = fig.add_subplot(gs[1, 0:2])
    ax_c = fig.add_subplot(gs[1, 2:4])
    ax_d = fig.add_subplot(gs[1, 4:6])

    plot_loss_small_multiples(loss_axes, results)
    plot_framewise_dots(ax_b, results)
    plot_collar_f1(ax_c, results, baseline_results=baseline_results)
    plot_duration_vs_f1(ax_d, results)

    # Add legend clarifying solid=Moove+SW, dashed=Baseline (raw)
    legend_elements = [
        Line2D([0], [0], color="black", linewidth=2, linestyle="-", label="Moove (+SW)"),
        Line2D([0], [0], color="black", linewidth=1.2, linestyle="--", alpha=0.7, label="Baseline (raw)"),
    ]
    ax_c.legend(handles=legend_elements, fontsize=7, loc="lower right")

    # Panel labels
    fig.text(0.02, 0.97, "A", fontsize=16, fontweight="bold", va="top")
    ax_b.text(-0.15, 1.15, "B", transform=ax_b.transAxes,
              fontsize=16, fontweight="bold", va="top")
    ax_c.text(-0.15, 1.15, "C", transform=ax_c.transAxes,
              fontsize=16, fontweight="bold", va="top")
    ax_d.text(-0.15, 1.15, "D", transform=ax_d.transAxes,
              fontsize=16, fontweight="bold", va="top")

    for ext in ["svg", "png"]:
        path = os.path.join(OUTPUT_DIR, f"figure4.{ext}")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close(fig)

    print_summary_table(results, baseline_results)


def print_summary_table(results, baseline_results=None):
    """Print combined summary: RAW framewise + SW collar + Baseline comparison."""
    print("\n=== SEGMENTATION SUMMARY ===")
    print("Moove: onset_collar_SMOOTHED (with SW) | Baseline: onset_collar RAW (no SW)")
    header = (f"{'Bird':<10} {'Label':<8} {'Dur(s)':<10} "
              f"{'FW-F1':<18} {'Col@10ms(SW)':<18} "
              f"{'Col@10ms(raw)':<18} {'ΔSW':<8} "
              f"{'Baseline':<18} {'ΔvsBase':<10}")
    print(header)
    print("-" * len(header))

    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        label = BIRD_LABELS[bird]
        durs = [r["data_stats_before_downsampling"]["duration_train_s"] for r in runs]
        fw_f1 = [r["framewise"]["f1"] for r in runs]
        c10_sw = [r["onset_collar_smoothed"]["@10ms"]["f1"] for r in runs]
        c10_raw = [r["onset_collar"]["@10ms"]["f1"] for r in runs]

        def ms(vals):
            a = np.array(vals)
            return f"{a.mean():.4f}±{a.std():.4f}"

        sw_mean = np.mean(c10_sw)
        raw_mean = np.mean(c10_raw)
        delta_sw = sw_mean - raw_mean

        base_str = "—"
        delta_base_str = "—"
        if baseline_results and bird in baseline_results:
            b_runs = baseline_results[bird]
            b10 = [r["onset_collar"]["@10ms"]["f1"] for r in b_runs]
            base_str = ms(b10)
            delta_base_str = f"{sw_mean - np.mean(b10):+.3f}"

        print(f"{bird:<10} {label:<8} {np.mean(durs):<10.1f} "
              f"{ms(fw_f1):<18} {ms(c10_sw):<18} "
              f"{ms(c10_raw):<18} {delta_sw:+.3f}   "
              f"{base_str:<18} {delta_base_str:<10}")


if __name__ == "__main__":
    generate_figure4()
