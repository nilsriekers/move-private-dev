#!/usr/bin/env python3
"""Generate new Figure 5 for the revised paper.

Panel layout (3 rows × 2 cols):
  A) Training loss curves per bird (small multiples, mean ± SD) — from results.json
  B) Classification accuracy + macro-F1 dot plot — from results.json
  C) Confusion matrix Bird 1 (ye00pu07, seed_42) — from SVG/PNG
  D) Accuracy vs input duration Bird 1 — hardcoded values from original experiments
  E) UMAP 30 ms Bird 1 — from real_figure_5/cluster_data/your_new_processed_dataset_class.pkl
  F) UMAP full syllable Bird 1 — from real_figure_5/cluster_data/prod_cluster_data_baseline_ml_segmented.pkl
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import fontManager, FontProperties
from matplotlib.ticker import MaxNLocator, FuncFormatter, MultipleLocator
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RESULTS_DIR   = os.path.join(REPO_ROOT, "paper_experiments", "results")
CLUSTER_DIR   = os.path.join(SCRIPT_DIR, "real_figure_5", "cluster_data")
OUTPUT_DIR    = SCRIPT_DIR

CM_PATH = os.path.join(RESULTS_DIR, "class", "ye00pu07", "seed_42", "confusion_matrix.svg")

# ── Bird config ──────────────────────────────────────────────────────
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
VAL_COLOR = "#888888"

# ── Font setup ───────────────────────────────────────────────────────

def setup_fonts():
    cmu_regular = "/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf"
    cmu_bold    = "/Library/Fonts/CMU-Serif-Roman/cmunbx.ttf"
    if os.path.isfile(cmu_regular):
        fontManager.addfont(cmu_regular)
        if os.path.isfile(cmu_bold):
            fontManager.addfont(cmu_bold)
        rcParams["font.family"] = "CMU Serif"
    else:
        rcParams["font.family"] = "serif"

    rcParams["font.size"]        = 10
    rcParams["axes.labelsize"]   = 11
    rcParams["axes.titlesize"]   = 11
    rcParams["legend.fontsize"]  = 8
    rcParams["xtick.labelsize"]  = 9
    rcParams["ytick.labelsize"]  = 9
    rcParams["figure.dpi"]       = 300
    rcParams["savefig.dpi"]      = 300
    rcParams["text.usetex"]      = False
    rcParams["lines.linewidth"]  = 1.5
    rcParams["axes.linewidth"]   = 0.8
    rcParams["axes.spines.top"]  = False
    rcParams["axes.spines.right"]= False
    rcParams["axes.grid"]        = True
    rcParams["axes.axisbelow"]   = True
    rcParams["grid.alpha"]       = 0.3
    rcParams["grid.linewidth"]   = 0.5


def bold_prop():
    p = "/Library/Fonts/CMU-Serif-Roman/cmunbx.ttf"
    return FontProperties(fname=p) if os.path.isfile(p) else FontProperties(weight="bold")

def reg_prop():
    p = "/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf"
    return FontProperties(fname=p) if os.path.isfile(p) else FontProperties()


# ── Data loading ─────────────────────────────────────────────────────

def load_class_results():
    results = {}
    for bird in BIRD_IDS:
        runs = []
        for seed in SEEDS:
            path = os.path.join(RESULTS_DIR, "class", bird, f"seed_{seed}", "results.json")
            if os.path.isfile(path):
                with open(path) as f:
                    runs.append(json.load(f))
        if runs:
            results[bird] = runs
    return results


# ── Panel A: Loss curves small multiples ─────────────────────────────

def plot_loss_small_multiples(axes, results):
    for idx, bird in enumerate(BIRD_IDS):
        ax = axes[idx]
        if bird not in results:
            ax.set_visible(False)
            continue

        runs   = results[bird]
        color  = BIRD_COLORS[bird]
        label  = BIRD_LABELS[bird]

        histories = [r["history"] for r in runs if "history" in r]
        if not histories:
            continue

        min_len   = min(len(h["train_loss"]) for h in histories)
        train_arr = np.array([h["train_loss"][:min_len] for h in histories])
        val_arr   = np.array([h["val_loss"][:min_len]   for h in histories])
        ep        = np.arange(1, min_len + 1)

        ax.plot(ep, train_arr.mean(0), color=color, linewidth=1.8, label="Train")
        ax.fill_between(ep,
                        train_arr.mean(0) - train_arr.std(0),
                        train_arr.mean(0) + train_arr.std(0),
                        color=color, alpha=0.15)
        ax.plot(ep, val_arr.mean(0), color=VAL_COLOR, linewidth=1.8,
                linestyle="--", label="Val")
        ax.fill_between(ep,
                        val_arr.mean(0) - val_arr.std(0),
                        val_arr.mean(0) + val_arr.std(0),
                        color=VAL_COLOR, alpha=0.12)

        ax.set_title(label, fontsize=10)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        if idx == 0:
            ax.set_ylabel("Loss")
            ax.legend(fontsize=7, loc="upper right")
        if idx == 2:
            ax.set_xlabel("Epoch")


# ── Panel B: Accuracy + Macro-F1 dot plot ────────────────────────────

def plot_class_metrics_dots(ax, results):
    birds   = [b for b in BIRD_IDS if b in results]
    metrics = [
        ("test_accuracy",           "Accuracy",  "o", "#4e79a7"),
        ("classification.macro.f1", "Macro-F1",  "D", "#59a14f"),
    ]
    y = np.arange(len(birds))

    for i, (key, label, marker, color) in enumerate(metrics):
        means, stds = [], []
        for bird in birds:
            vals = []
            for r in results[bird]:
                v = r
                for p in key.split("."):
                    v = v[p]
                vals.append(v)
            means.append(np.mean(vals))
            stds.append(np.std(vals))

        offset = (i - 0.5) * 0.2
        ax.errorbar(means, y + offset, xerr=stds, fmt=marker, color=color,
                    markersize=7, capsize=3, capthick=1.2, linewidth=1.2,
                    label=label, markeredgecolor="white", markeredgewidth=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels([BIRD_LABELS[b] for b in birds])
    ax.set_xlabel("Score")
    ax.set_title("Classification Performance")
    ax.set_xlim(0.83, 1.0)
    ax.legend(loc="lower left", fontsize=8)
    ax.invert_yaxis()


# ── Panel C: Confusion matrix ─────────────────────────────────────────
# Values extracted from ye00pu07 seed_42 confusion_matrix.svg (verified vs results.json)
_CM_LABELS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'l']
_CM_PCT = np.array([
    [93.13,  0.00,  0.00,  6.53,  0.00,  0.00,  0.34,  0.00,  0.00],  # a
    [ 0.00,100.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00],  # b
    [ 0.00,  0.00,100.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00],  # c
    [ 2.56,  0.00,  0.00, 94.98,  0.00,  0.00,  2.34,  0.11,  0.00],  # d
    [ 0.00,  0.00,  0.00,  0.00, 99.87,  0.13,  0.00,  0.00,  0.00],  # e
    [ 0.00,  0.00,  0.00,  0.00,  0.00, 98.86,  0.57,  0.57,  0.00],  # f
    [ 0.00,  0.00,  0.00,  3.09,  0.00,  0.00, 96.53,  0.00,  0.39],  # g
    [ 0.00,  0.00,  0.00,  0.62,  0.00,  0.00,  0.00, 99.38,  0.00],  # h
    [ 0.00,  0.00,  0.25,  0.00,  0.00,  0.00,  0.00,  0.00, 99.75],  # l
])

def plot_confusion_matrix(ax, _cm_path=None):
    n = len(_CM_LABELS)
    im = ax.imshow(_CM_PCT, cmap="Blues", vmin=0, vmax=100, aspect="auto")

    # Annotate cells with values > 0
    thresh = 50.0
    for i in range(n):
        for j in range(n):
            val = _CM_PCT[i, j]
            if val > 0.05:
                text_color = "white" if val > thresh else "black"
                fontsize = 7 if val < 10 else 8
                ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                        fontsize=fontsize, color=text_color)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(_CM_LABELS, fontsize=9)
    ax.set_yticklabels(_CM_LABELS, fontsize=9)
    ax.set_xlabel("Predicted", fontsize=10)
    ax.set_ylabel("True", fontsize=10)
    ax.set_title("Confusion Matrix\nBird 1 (seed 42)", fontsize=10)
    ax.grid(False)

    # Colorbar
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.05)
    plt.colorbar(im, cax=cax, label="%")


# ── Panel C-alt: Performance vs dataset size scatter ─────────────────

def plot_dataset_scatter(ax, results):
    """Accuracy & Macro-F1 vs. after-downsampling training duration (log x)."""
    metrics = [
        ("test_accuracy",           "Accuracy",  "o", "#4e79a7"),
        ("classification.macro.f1", "Macro-F1",  "D", "#59a14f"),
    ]
    for key, label, marker, color in metrics:
        xs, ys, yerrs = [], [], []
        for bird in BIRD_IDS:
            if bird not in results:
                continue
            runs = results[bird]
            durs = [r["data_stats_after_downsampling"]["duration_train_s"] for r in runs]
            vals = []
            for r in runs:
                v = r
                for p in key.split("."):
                    v = v[p]
                vals.append(v)
            xs.append(np.mean(durs))
            ys.append(np.mean(vals))
            yerrs.append(np.std(vals))

        ax.errorbar(xs, ys, yerr=yerrs, fmt=marker, color=color,
                    markersize=7, capsize=3, capthick=1.2, linewidth=1.2,
                    label=label, markeredgecolor="white", markeredgewidth=0.5,
                    zorder=3)

    # Bird name annotations
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        x = np.mean([r["data_stats_after_downsampling"]["duration_train_s"] for r in runs])
        y = np.mean([r["test_accuracy"] for r in runs])
        ax.annotate(BIRD_LABELS[bird], (x, y),
                    textcoords="offset points", xytext=(5, 4),
                    fontsize=7, color=BIRD_COLORS[bird])

    ax.set_xscale("log")
    ax.set_xlabel("Training duration after downsampling (s, log scale)")
    ax.set_ylabel("Score")
    ax.set_title("Classification Performance vs.\nTraining Data Size (after downsampling)")
    ax.set_ylim(0.85, 1.0)
    ax.legend(loc="lower right", fontsize=8)


# ── Panel D: Accuracy vs input duration ──────────────────────────────

def plot_input_duration(ax):
    # Original measured values from old experiments (Bird 1, ye00pu07, no c/h merge)
    input_sizes     = np.array([5.804, 10.159, 14.512, 20.317, 24.671,
                                 30.476, 34.830, 40.635, 44.989, 49.342])
    test_accuracies = np.array([0.8639, 0.8930, 0.9089, 0.9266, 0.9297,
                                 0.9589, 0.9766, 0.9595, 0.9747, 0.9778])

    ax.plot(input_sizes, test_accuracies, "o-", color="#1f77b4",
            linewidth=2, markersize=6)
    ax.set_xlabel("Input Duration (ms)")
    ax.set_ylabel("Test Accuracy")
    ax.set_title("Accuracy vs. Input Duration\n(Bird 1)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0%}"))
    ax.set_xlim(0, 55)
    ax.set_ylim(0.85, 1.0)
    ax.set_xticks(np.arange(0, 60, 10))


# ── Panels E & F: UMAP ───────────────────────────────────────────────

UMAP_COLORS = ["#1f77b4", "#fd7f0e", "#2ca02c", "#d62728", "#9467bd",
               "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#1ebecf"]

def plot_umap(ax, df, title, show_legend=True):
    if "label" in df.columns:
        df = df.copy()
        df["Mapped_Labels"] = df["label"]
    elif "Labels" in df.columns:
        df = df.copy()
        df["Mapped_Labels"] = df["Labels"]

    label_counts = df["Mapped_Labels"].value_counts().to_dict()
    unique_labels = sorted(label_counts.keys())

    ax.set_autoscale_on(False)
    ax.set_xlim(-7.5, 20)
    ax.set_ylim(-7.5, 17.5)
    ax.set_xticks(np.arange(-5, 21, 5))
    ax.set_yticks(np.arange(-5, 18, 5))

    def fmt(x, pos):
        return str(int(x))
    ax.xaxis.set_major_formatter(FuncFormatter(fmt))
    ax.yaxis.set_major_formatter(FuncFormatter(fmt))

    for idx, lbl in enumerate(unique_labels):
        mask = df["Mapped_Labels"] == lbl
        ax.scatter(df.loc[mask, "UMAP1"], df.loc[mask, "UMAP2"],
                   label=f"{lbl} (n={label_counts[lbl]})",
                   s=1, c=UMAP_COLORS[idx % len(UMAP_COLORS)])

    ax.set_xlim(-7.5, 20)
    ax.set_ylim(-7.5, 17.5)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal", adjustable="box")

    if show_legend:
        ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5),
                  borderaxespad=0., handlelength=1, handletextpad=0,
                  labelspacing=0.5, borderpad=0.2, frameon=True,
                  framealpha=1, title="Syllable", fontsize=9, markerscale=5)


# ── Compose figure ───────────────────────────────────────────────────

def _draw_figure5(results):
    fig = plt.figure(figsize=(14, 14))
    gs  = fig.add_gridspec(3, 6, hspace=0.55, wspace=0.55,
                           height_ratios=[1, 1.2, 1.2])

    # Row 0: 5 loss subplots (A)
    loss_axes = [fig.add_subplot(gs[0, i]) for i in range(5)]

    # Row 1: B (scatter) + C (confusion matrix)
    ax_b = fig.add_subplot(gs[1, 0:3])
    ax_c = fig.add_subplot(gs[1, 3:6])

    # Row 2: D + E + F
    ax_d = fig.add_subplot(gs[2, 0:2])
    ax_e = fig.add_subplot(gs[2, 2:4])
    ax_f = fig.add_subplot(gs[2, 4:6])

    # ── Draw panels ──
    plot_loss_small_multiples(loss_axes, results)
    plot_dataset_scatter(ax_b, results)
    plot_confusion_matrix(ax_c)
    plot_input_duration(ax_d)

    # UMAP panels
    pkl_30   = os.path.join(CLUSTER_DIR, "your_new_processed_dataset_class.pkl")
    pkl_full = os.path.join(CLUSTER_DIR, "prod_cluster_data_baseline_ml_segmented.pkl")

    if os.path.isfile(pkl_30):
        df_30 = pd.read_pickle(pkl_30)
        plot_umap(ax_e, df_30, "UMAP — 30 ms after onset\n(Bird 1)", show_legend=False)
    else:
        ax_e.text(0.5, 0.5, f"[{os.path.basename(pkl_30)}\nnot found]",
                  ha="center", va="center", transform=ax_e.transAxes, fontsize=8, color="gray")
        ax_e.set_title("UMAP — 30 ms (Bird 1)", fontsize=10)

    if os.path.isfile(pkl_full):
        df_full = pd.read_pickle(pkl_full)
        plot_umap(ax_f, df_full, "UMAP — full syllable\n(Bird 1)", show_legend=True)
    else:
        ax_f.text(0.5, 0.5, f"[{os.path.basename(pkl_full)}\nnot found]",
                  ha="center", va="center", transform=ax_f.transAxes, fontsize=8, color="gray")
        ax_f.set_title("UMAP — full syllable (Bird 1)", fontsize=10)

    # ── Panel labels ──
    fig.text(0.02, 0.97, "A", fontsize=16, fontweight="bold", va="top")
    ax_b.text(-0.10, 1.12, "B", transform=ax_b.transAxes,
              fontsize=16, fontweight="bold", va="top")
    ax_c.text(-0.10, 1.12, "C", transform=ax_c.transAxes,
              fontsize=16, fontweight="bold", va="top")
    ax_d.text(-0.15, 1.12, "D", transform=ax_d.transAxes,
              fontsize=16, fontweight="bold", va="top")
    ax_e.text(-0.15, 1.12, "E", transform=ax_e.transAxes,
              fontsize=16, fontweight="bold", va="top")
    ax_f.text(-0.15, 1.12, "F", transform=ax_f.transAxes,
              fontsize=16, fontweight="bold", va="top")

    return fig


def generate_figure5():
    setup_fonts()
    results = load_class_results()

    if not results:
        print("ERROR: No classification results found in", RESULTS_DIR)
        sys.exit(1)

    print(f"Loaded classification results for {len(results)} birds, "
          f"seeds per bird: {[len(v) for v in results.values()]}")

    fig = _draw_figure5(results)
    for ext in ["svg", "png"]:
        path = os.path.join(OUTPUT_DIR, f"figure5.{ext}")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close(fig)

    print_summary_table(results)
    print_dataset_scatter_data(results)


def print_summary_table(results):
    print("\n=== CLASSIFICATION SUMMARY (mean ± SD across 3 replicates) ===")
    header = (f"{'Bird':<10} {'Label':<8} {'N_syl':<8} {'Epochs':<8} "
              f"{'Accuracy':<18} {'Macro-P':<18} {'Macro-R':<18} {'Macro-F1':<18}")
    print(header)
    print("-" * len(header))
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs   = results[bird]
        label  = BIRD_LABELS[bird]
        n_syl  = [r["data_stats_before_downsampling"]["n_train"] for r in runs]
        epochs = [len(r["history"]["train_loss"]) for r in runs]
        acc    = [r["test_accuracy"]                          for r in runs]
        mp     = [r["classification"]["macro"]["precision"]   for r in runs]
        mr     = [r["classification"]["macro"]["recall"]      for r in runs]
        mf     = [r["classification"]["macro"]["f1"]          for r in runs]

        def ms(vals):
            a = np.array(vals)
            return f"{a.mean():.4f} ± {a.std():.4f}"

        print(f"{bird:<10} {label:<8} {int(np.mean(n_syl)):<8} "
              f"{np.mean(epochs):<8.1f} {ms(acc):<18} {ms(mp):<18} "
              f"{ms(mr):<18} {ms(mf):<18}")


def print_dataset_scatter_data(results):
    print("\n=== DATASET SIZE vs PERFORMANCE ===")
    header = (f"{'Bird':<10} {'Label':<8} {'N_train_before':>16} {'Dur_train_s':>12} "
              f"{'N_train_after':>14} {'Accuracy':>18} {'Macro-F1':>18}")
    print(header)
    print("-" * len(header))
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        n_bef  = [r["data_stats_before_downsampling"]["n_train"] for r in runs]
        dur    = [r["data_stats_after_downsampling"]["duration_train_s"] for r in runs]
        n_aft  = [r["data_stats_after_downsampling"]["n_train"] for r in runs]
        acc    = [r["test_accuracy"] for r in runs]
        mf     = [r["classification"]["macro"]["f1"] for r in runs]
        def ms(vals):
            a = np.array(vals)
            return f"{a.mean():.4f} ± {a.std():.4f}"
        print(f"{bird:<10} {BIRD_LABELS[bird]:<8} {int(np.mean(n_bef)):>16} "
              f"{np.mean(dur):>12.1f} {int(np.mean(n_aft)):>14} "
              f"{ms(acc):>18} {ms(mf):>18}")


if __name__ == "__main__":
    generate_figure5()
