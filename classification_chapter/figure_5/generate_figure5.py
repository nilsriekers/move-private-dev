#!/usr/bin/env python3
"""Generate Figure 5 for the revised eNeuro paper.

Layout (7 panels, A–G):
  A  Training loss curves — 5 small multiples, full width
  B  Classification performance (accuracy + macro-F1 dot plot)
  C  Accuracy vs. input duration (all birds, 3 seeds)
  D  Cluster separability vs. macro-F1
  E  Confusion matrix Bird 1 seed_42
  F  UMAP — 30 ms after onset (Bird 1)
  G  UMAP — full syllable (Bird 1)

Data: classification_chapter/results/  (final_experiments, weighted CE, 3 seeds)
      classification_chapter/results/separability.json
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import fontManager
from matplotlib.ticker import MaxNLocator, FuncFormatter
from scipy import stats
import numpy as np
import pandas as pd

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT     = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RESULTS_DIR   = os.path.join(REPO_ROOT, "classification_chapter", "results")
SEP_JSON      = os.path.join(RESULTS_DIR, "separability.json")
CLUSTER_DIR   = os.path.join(SCRIPT_DIR, "real_figure_5", "cluster_data")
SWEEP_DIR     = os.path.join(REPO_ROOT, "final_experiments", "results_duration_sweep")
OUTPUT_DIR    = SCRIPT_DIR

SWEEP_LENGTHS = [4, 7, 10, 14, 17, 21, 24, 28, 31, 34]
LENGTHS_MS    = np.array([L * 64 / 44100 * 1000 for L in SWEEP_LENGTHS])

BIRD_IDS = ["ye00pu07", "bu04bk04", "gy07bu07", "br08pk08", "ye04gr05"]
BIRD_LABELS = {
    "ye00pu07": "Bird 1", "bu04bk04": "Bird 2", "gy07bu07": "Bird 3",
    "br08pk08": "Bird 4", "ye04gr05": "Bird 5",
}
BIRD_COLORS = {
    "ye00pu07": "#1f77b4", "bu04bk04": "#ff7f0e", "gy07bu07": "#2ca02c",
    "br08pk08": "#d62728", "ye04gr05": "#9467bd",
}
SEEDS     = [42, 123, 456]
VAL_COLOR = "#888888"


# ── Fonts (identical to Figure 4) ────────────────────────────────────

def setup_fonts():
    cmu_r = "/Library/Fonts/CMU-Serif-Roman/cmunrm.ttf"
    cmu_b = "/Library/Fonts/CMU-Serif-Roman/cmunbx.ttf"
    if os.path.isfile(cmu_r):
        fontManager.addfont(cmu_r)
        if os.path.isfile(cmu_b):
            fontManager.addfont(cmu_b)
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


# ── Data loading ──────────────────────────────────────────────────────

def load_class_results():
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

def load_separability():
    with open(SEP_JSON) as f:
        return json.load(f)


# ── Panel A: Loss curves (5 small multiples) ─────────────────────────

def plot_loss_small_multiples(axes, results):
    for idx, bird in enumerate(BIRD_IDS):
        ax = axes[idx]
        if bird not in results:
            ax.set_visible(False)
            continue
        color     = BIRD_COLORS[bird]
        histories = [r["history"] for r in results[bird] if "history" in r]
        if not histories:
            continue
        min_len   = min(len(h["train_loss"]) for h in histories)
        tr = np.array([h["train_loss"][:min_len] for h in histories])
        vl = np.array([h["val_loss"][:min_len]   for h in histories])
        ep = np.arange(1, min_len + 1)
        ax.plot(ep, tr.mean(0), color=color, linewidth=1.8, label="Train")
        ax.fill_between(ep, tr.mean(0)-tr.std(0), tr.mean(0)+tr.std(0),
                        color=color, alpha=0.15)
        ax.plot(ep, vl.mean(0), color=VAL_COLOR, linewidth=1.8,
                linestyle="--", label="Val")
        ax.fill_between(ep, vl.mean(0)-vl.std(0), vl.mean(0)+vl.std(0),
                        color=VAL_COLOR, alpha=0.12)
        ax.set_title(BIRD_LABELS[bird], fontsize=10)
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
        ("test_accuracy",           "Accuracy", "o", "#4e79a7"),
        ("classification.macro.f1", "Macro-F1", "D", "#59a14f"),
    ]
    y = np.arange(len(birds))
    for i, (key, label, marker, color) in enumerate(metrics):
        means, stds = [], []
        for bird in birds:
            vals = []
            for r in results[bird]:
                v = r
                for p in key.split("."): v = v[p]
                vals.append(v)
            means.append(np.mean(vals)); stds.append(np.std(vals))
        offset = (i - 0.5) * 0.2
        ax.errorbar(means, y + offset, xerr=stds, fmt=marker, color=color,
                    markersize=7, capsize=3, capthick=1.2, linewidth=1.2,
                    label=label, markeredgecolor="white", markeredgewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels([BIRD_LABELS[b] for b in birds])
    ax.set_xlabel("Score")
    ax.set_title("Classification Performance\n(weighted CE, 3 replicates)")
    ax.set_xlim(0.83, 1.02)
    ax.legend(loc="lower right", fontsize=8)
    ax.invert_yaxis()


# ── Panel D: Separability vs. macro-F1 ──────────────────────────────

def _sep_scatter(ax, sep_data, metric_key, metric_std_key, ylabel, title):
    xs = np.array([sep_data[b]["separability"]    for b in BIRD_IDS if b in sep_data])
    ys = np.array([sep_data[b][metric_key]         for b in BIRD_IDS if b in sep_data])
    ye = np.array([sep_data[b][metric_std_key]     for b in BIRD_IDS if b in sep_data])
    birds = [b for b in BIRD_IDS if b in sep_data]

    for i, bird in enumerate(birds):
        color = BIRD_COLORS[bird]
        ax.scatter([xs[i]], [ys[i]], color=color, s=90, zorder=4,
                   edgecolors="white", linewidth=0.8, label=BIRD_LABELS[bird])
        ax.errorbar([xs[i]], [ys[i]], yerr=[ye[i]],
                    fmt="none", color=color, linewidth=1.4,
                    capsize=3, capthick=1.1, zorder=3)
        ax.annotate(BIRD_LABELS[bird], (xs[i], ys[i]),
                    textcoords="offset points", xytext=(5, 3),
                    fontsize=8, color=color)

    slope, intercept, r, p, _ = stats.linregress(xs, ys)
    xl = np.linspace(xs.min() * 0.90, xs.max() * 1.05, 200)
    ax.plot(xl, slope * xl + intercept, "k--", linewidth=1.1, alpha=0.55,
            label=f"r={r:.2f}, p={p:.3f}", zorder=1)

    ax.set_xlabel("Mean inter-centroid distance\n(PCA space)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(fontsize=7, loc="lower right")


def plot_sep_vs_f1(ax, sep_data):
    _sep_scatter(ax, sep_data, "mean_macro_f1", "std_macro_f1",
                 "Macro-F1", "Separability vs. Macro-F1")


def load_sweep_results():
    """Load duration sweep results → {bird: {L: [acc_seed42, acc_seed123, acc_seed456]}}"""
    sweep = {}
    for bird in BIRD_IDS:
        sweep[bird] = {}
        for L in SWEEP_LENGTHS:
            accs = []
            for seed in SEEDS:
                p = os.path.join(SWEEP_DIR, bird, f"input_length_{L}",
                                 f"seed_{seed}", "results.json")
                if os.path.isfile(p):
                    with open(p) as f:
                        accs.append(json.load(f)["test_accuracy"])
            if accs:
                sweep[bird][L] = accs
    return sweep


# ── Panel C: Accuracy vs. input duration (all birds, 3 seeds) ────────

def plot_input_duration(ax, sweep):
    for bird in BIRD_IDS:
        if bird not in sweep or not sweep[bird]:
            continue
        color  = BIRD_COLORS[bird]
        ms_pts, means, stds = [], [], []
        seed_curves = {s: [] for s in SEEDS}
        for i, L in enumerate(SWEEP_LENGTHS):
            if L not in sweep[bird]:
                continue
            accs = sweep[bird][L]
            ms_pts.append(LENGTHS_MS[i])
            means.append(np.mean(accs))
            stds.append(np.std(accs))
            for j, s in enumerate(SEEDS):
                if j < len(accs):
                    seed_curves[s].append((LENGTHS_MS[i], accs[j]))

        ms_pts = np.array(ms_pts)
        means  = np.array(means)
        stds   = np.array(stds)

        ax.fill_between(ms_pts, means - stds, means + stds,
                        color=color, alpha=0.15)
        ax.plot(ms_pts, means, "o-", color=color,
                linewidth=2.0, markersize=4, label=BIRD_LABELS[bird])

    ax.axvline(30, color="gray", linewidth=1.0, linestyle=":", alpha=0.7)
    ax.set_xlabel("Input duration (ms)")
    ax.set_ylabel("Test accuracy")
    ax.set_title("Accuracy vs. Input Duration\n(5 birds, 3 replicates each)", fontsize=10)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlim(0, 55)
    ax.set_ylim(0.40, 1.01)
    ax.set_xticks(np.arange(0, 56, 10))
    ax.legend(fontsize=7, loc="lower right")


# ── Panel C: Confusion matrix from .npy ──────────────────────────────

def plot_confusion_matrix(ax):
    npy = os.path.join(RESULTS_DIR, "ye00pu07", "seed_42",
                       "confusion_matrix_norm.npy")
    res = os.path.join(RESULTS_DIR, "ye00pu07", "seed_42", "results.json")
    if not os.path.isfile(npy):
        ax.text(0.5, 0.5, "confusion_matrix_norm.npy not found",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=9, color="gray")
        ax.set_title("Confusion Matrix\nBird 1 (seed 42)", fontsize=10)
        return
    cm_norm = np.load(npy)
    with open(res) as f:
        labels = json.load(f).get("label_names",
                                  [str(i) for i in range(cm_norm.shape[0])])
    n  = cm_norm.shape[0]
    im = ax.imshow(cm_norm * 100, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for i in range(n):
        for j in range(n):
            val = cm_norm[i, j] * 100
            if val > 0.5:
                ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                        fontsize=7 if val < 10 else 8,
                        color="white" if val > 50 else "black")
    ax.set_xticks(range(n)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticks(range(n)); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Predicted", fontsize=10)
    ax.set_ylabel("True", fontsize=10)
    ax.set_title("Confusion Matrix\nBird 1 (seed 42)", fontsize=10)
    ax.grid(False)
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    cax = make_axes_locatable(ax).append_axes("right", size="4%", pad=0.05)
    plt.colorbar(im, cax=cax, label="%")


# ── Panels G & H: UMAP ───────────────────────────────────────────────

UMAP_COLORS = ["#1f77b4","#fd7f0e","#2ca02c","#d62728","#9467bd",
               "#8c564b","#e377c2","#7f7f7f","#bcbd22","#1ebecf"]

def plot_umap(ax, df, title, show_legend=True):
    col = "label" if "label" in df.columns else "Labels"
    df  = df.copy(); df["_l"] = df[col]
    counts = df["_l"].value_counts().to_dict()
    for idx, lbl in enumerate(sorted(counts)):
        mask = df["_l"] == lbl
        ax.scatter(df.loc[mask,"UMAP1"], df.loc[mask,"UMAP2"],
                   s=1, c=UMAP_COLORS[idx % len(UMAP_COLORS)],
                   label=f"{lbl} (n={counts[lbl]})")
    ax.set_xlim(-7.5, 20); ax.set_ylim(-7.5, 17.5)
    ax.set_xticks(np.arange(-5,21,5)); ax.set_yticks(np.arange(-5,18,5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_: str(int(x))))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_: str(int(x))))
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal", adjustable="box")
    if show_legend:
        ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5),
                  borderaxespad=0., handlelength=1, handletextpad=0,
                  labelspacing=0.5, borderpad=0.2, frameon=True,
                  framealpha=1, title="Syllable", fontsize=9, markerscale=5)


# ── Compose figure ────────────────────────────────────────────────────

def generate_figure5():
    setup_fonts()
    results  = load_class_results()
    sep_data = load_separability()
    sweep    = load_sweep_results()

    if not results:
        print("ERROR: No classification results found in", RESULTS_DIR)
        sys.exit(1)
    print(f"Loaded results: {len(results)} birds, "
          f"{[len(v) for v in results.values()]} seeds each")

    # ── Grid: 3 rows × 15 cols ─────────────────────────────────────────
    # 15 cols: 5 loss plots each take 3 cols (full width, centered)
    #          3-panel rows each take 5 cols (equal thirds)
    fig = plt.figure(figsize=(15, 18))
    gs  = fig.add_gridspec(3, 15,
                           hspace=0.55, wspace=0.52,
                           height_ratios=[1.0, 1.2, 1.6])

    # Row 0: A — 5 loss small multiples, each 3 cols wide (centered, full width)
    loss_axes = [fig.add_subplot(gs[0, i*3:(i+1)*3]) for i in range(5)]

    # Row 1: B (cols 0–5) | C (cols 5–10) | D (cols 10–15)
    ax_b = fig.add_subplot(gs[1, 0:5])
    ax_c = fig.add_subplot(gs[1, 5:10])
    ax_d = fig.add_subplot(gs[1, 10:15])

    # Row 2: E (cols 0–5) | F (cols 5–10) | G (cols 10–15)
    ax_e = fig.add_subplot(gs[2, 0:5])
    ax_f = fig.add_subplot(gs[2, 5:10])
    ax_g = fig.add_subplot(gs[2, 10:15])

    # ── Draw all panels ──
    plot_loss_small_multiples(loss_axes, results)
    plot_class_metrics_dots(ax_b, results)
    plot_input_duration(ax_c, sweep)
    plot_sep_vs_f1(ax_d, sep_data)
    plot_confusion_matrix(ax_e)

    pkl_30   = os.path.join(CLUSTER_DIR, "your_new_processed_dataset_class.pkl")
    pkl_full = os.path.join(CLUSTER_DIR, "prod_cluster_data_baseline_ml_segmented.pkl")
    for pkl, ax, title, legend in [
        (pkl_30,   ax_f, "UMAP — 30 ms after onset (Bird 1)", False),
        (pkl_full, ax_g, "UMAP — full syllable (Bird 1)",     True),
    ]:
        if os.path.isfile(pkl):
            plot_umap(ax, pd.read_pickle(pkl), title, show_legend=legend)
        else:
            ax.text(0.5, 0.5, f"[{os.path.basename(pkl)}\nnot found]",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=8, color="gray")
            ax.set_title(title, fontsize=10)

    # ── Panel labels ──
    label_kwargs = dict(fontsize=16, fontweight="bold", va="top")
    fig.text(0.02, 0.985, "A", **label_kwargs)
    ax_b.text(-0.14, 1.12, "B", transform=ax_b.transAxes, **label_kwargs)
    ax_c.text(-0.14, 1.12, "C", transform=ax_c.transAxes, **label_kwargs)
    ax_d.text(-0.14, 1.12, "D", transform=ax_d.transAxes, **label_kwargs)
    ax_e.text(-0.14, 1.12, "E", transform=ax_e.transAxes, **label_kwargs)
    ax_f.text(-0.14, 1.12, "F", transform=ax_f.transAxes, **label_kwargs)
    ax_g.text(-0.14, 1.12, "G", transform=ax_g.transAxes, **label_kwargs)

    for ext in ["svg", "png"]:
        path = os.path.join(OUTPUT_DIR, f"figure5.{ext}")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close(fig)
    print_summary(results)


def print_summary(results):
    print("\n=== CLASSIFICATION SUMMARY (weighted CE, 3 replicates) ===")
    print(f"{'Bird':<10} {'Accuracy':<22} {'Macro-F1':<22}")
    print("-" * 56)
    for bird in BIRD_IDS:
        if bird not in results: continue
        acc = [r["test_accuracy"]                        for r in results[bird]]
        f1  = [r["classification"]["macro"]["f1"]        for r in results[bird]]
        print(f"{bird:<10} {np.mean(acc):.4f} +/- {np.std(acc):.4f}    "
              f"{np.mean(f1):.4f} +/- {np.std(f1):.4f}")


if __name__ == "__main__":
    generate_figure5()
