#!/usr/bin/env python3
"""Syllable cluster separability vs. classification performance.

For each bird:
  1. Build spectrograms from raw WAV (same pipeline as training)
  2. Normalize per sample, reduce with PCA (50 components)
  3. Compute per-class centroid in PCA space
  4. Compute mean pairwise Euclidean distance between centroids
     → "separability score"
  5. Plot separability vs. test accuracy and macro-F1

Output: classification_chapter/figure_5/explore_separability.{svg,png}
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import fontManager
from matplotlib.ticker import FuncFormatter
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from itertools import combinations

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "classification_chapter", "results")
OUTPUT_DIR  = SCRIPT_DIR

sys.path.insert(0, REPO_ROOT)
from final_experiments.config import BIRDS, CLASS_DATASET_PARAMS
from final_experiments.create_dataset import build_class_dataset, get_wav_files

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
PCA_COMPONENTS = 50


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


def build_feature_matrix(bird):
    """Return (X, labels) where X is (n_samples, n_freq*n_time) flattened+padded."""
    cfg     = BIRDS[bird]
    raw_dir = cfg["raw_data_dir"]
    data    = build_class_dataset(
        get_wav_files(raw_dir),
        exclude_labels=cfg.get("exclude_labels"),
        merge_labels=cfg.get("merge_labels"),
        **CLASS_DATASET_PARAMS,
    )
    df = data["dataframe"]

    X, y = [], []
    target_shape = None
    for _, row in df.iterrows():
        spec = np.array(row["taf_unflattend_spectrogram"], dtype=np.float32)
        # Apply same F.pad as training (adds 1 row + 1 col)
        t = torch.tensor(spec).unsqueeze(0)
        t = F.pad(t, (0, 1, 0, 1))
        arr = t.squeeze(0).numpy()

        if target_shape is None:
            target_shape = arr.shape
        if arr.shape != target_shape:
            continue  # skip clips near file boundary with wrong shape

        # Per-sample z-norm (same as training)
        std = arr.std()
        if std > 0:
            arr = (arr - arr.mean()) / std

        X.append(arr.ravel())
        y.append(row["label"])

    return np.array(X, dtype=np.float32), np.array(y)


def separability_score(X, y):
    """Mean pairwise Euclidean distance between per-class centroids in PCA space."""
    # PCA
    n_components = min(PCA_COMPONENTS, X.shape[0] - 1, X.shape[1] - 1)
    pca = PCA(n_components=n_components, random_state=42)
    Xr  = pca.fit_transform(X)

    classes   = sorted(set(y))
    centroids = np.array([Xr[y == c].mean(axis=0) for c in classes])

    # Mean pairwise distance between centroids
    dists = [np.linalg.norm(centroids[i] - centroids[j])
             for i, j in combinations(range(len(classes)), 2)]
    return float(np.mean(dists)), classes, centroids, Xr, y


def load_mean_performance(bird):
    accs, f1s = [], []
    for seed in SEEDS:
        p = os.path.join(RESULTS_DIR, bird, f"seed_{seed}", "results.json")
        with open(p) as f:
            r = json.load(f)
        accs.append(r["test_accuracy"])
        f1s.append(r["classification"]["macro"]["f1"])
    return np.mean(accs), np.std(accs), np.mean(f1s), np.std(f1s)


def plot_sep_vs_metric(ax, seps, means, stds, ylabel, title):
    xs = np.array([seps[b] for b in BIRD_IDS if b in seps])
    ys = np.array([means[b] for b in BIRD_IDS if b in means])
    ye = np.array([stds[b]  for b in BIRD_IDS if b in stds])
    birds = [b for b in BIRD_IDS if b in seps]

    for i, bird in enumerate(birds):
        color = BIRD_COLORS[bird]
        ax.scatter([xs[i]], [ys[i]], color=color, s=100, zorder=4,
                   edgecolors="white", linewidth=0.8, label=BIRD_LABELS[bird])
        ax.errorbar([xs[i]], [ys[i]], yerr=[ye[i]],
                    fmt="none", color=color, linewidth=1.5,
                    capsize=4, capthick=1.2, zorder=3)
        ax.annotate(BIRD_LABELS[bird], (xs[i], ys[i]),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=8, color=color)

    # Regression
    from scipy import stats
    slope, intercept, r, p, _ = stats.linregress(xs, ys)
    xl = np.linspace(xs.min() * 0.92, xs.max() * 1.05, 200)
    ax.plot(xl, slope * xl + intercept, "k--", linewidth=1.1, alpha=0.55,
            label=f"r={r:.2f}, p={p:.3f}", zorder=1)

    ax.set_xlabel("Mean inter-centroid distance\n(PCA space, 50 components)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(fontsize=7, loc="lower right")
    return r, p


def main():
    setup_fonts()

    print("Building feature matrices and computing separability scores...")
    seps = {}
    for bird in BIRD_IDS:
        print(f"  {BIRD_LABELS[bird]} ({bird})...", flush=True)
        X, y = build_feature_matrix(bird)
        print(f"    {X.shape[0]} samples, {len(set(y))} classes")
        score, classes, _, _, _ = separability_score(X, y)
        seps[bird] = score
        print(f"    separability = {score:.3f}")

    print("\nSeparability scores:")
    for bird in BIRD_IDS:
        print(f"  {BIRD_LABELS[bird]}: {seps[bird]:.3f}")

    acc_means, acc_stds, f1_means, f1_stds = {}, {}, {}, {}
    for bird in BIRD_IDS:
        am, as_, fm, fs = load_mean_performance(bird)
        acc_means[bird] = am; acc_stds[bird] = as_
        f1_means[bird]  = fm; f1_stds[bird]  = fs

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.subplots_adjust(wspace=0.35)

    r1, p1 = plot_sep_vs_metric(axes[0], seps, acc_means, acc_stds,
                                 ylabel="Test accuracy",
                                 title="Cluster separability vs. Accuracy")
    r2, p2 = plot_sep_vs_metric(axes[1], seps, f1_means, f1_stds,
                                 ylabel="Macro-F1",
                                 title="Cluster separability vs. Macro-F1")

    axes[0].text(-0.12, 1.08, "A", transform=axes[0].transAxes,
                 fontsize=14, fontweight="bold", va="top")
    axes[1].text(-0.12, 1.08, "B", transform=axes[1].transAxes,
                 fontsize=14, fontweight="bold", va="top")

    print(f"\nAccuracy: r={r1:.3f}, p={p1:.4f}")
    print(f"Macro-F1: r={r2:.3f}, p={p2:.4f}")

    for ext in ["svg", "png"]:
        path = os.path.join(OUTPUT_DIR, f"explore_separability.{ext}")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
