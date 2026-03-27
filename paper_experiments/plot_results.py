#!/usr/bin/env python3
"""Generate paper-ready plots from experiment results.

Reads the JSON results produced by train_segmentation / train_classification
and generates:

  1. Loss curves per bird  (individual runs as thin lines, mean as bold line)
  2. Bar plots of framewise P / R / F1  per bird  (mean ± std error bars)
  3. Bar plots of collar-based segmentation metrics per bird
  4. Bar plots of classification macro P / R / F1  per bird

All figures are saved as SVG in paper_experiments/results/figures/.
"""
import argparse
import json
import logging
import os
import sys
from glob import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from paper_experiments.config import BIRDS, COLLAR_VALUES_MS, OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

FIG_DIR = os.path.join(OUTPUT_DIR, "figures")

# Consistent colours
BIRD_COLORS = {bird: c for bird, c in zip(
    BIRDS.keys(), ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"])}
SEED_ALPHA = 0.3  # transparency for individual run curves


# ── Helpers ──────────────────────────────────────────────────────────

def _load_results(network_type):
    """Load all results.json for a given network type (seg / class)."""
    results = {}  # bird → [result_dict, ...]
    base = os.path.join(OUTPUT_DIR, network_type)
    for bird in BIRDS:
        bird_dir = os.path.join(base, bird)
        if not os.path.isdir(bird_dir):
            continue
        runs = []
        for seed_dir in sorted(glob(os.path.join(bird_dir, "seed_*"))):
            rp = os.path.join(seed_dir, "results.json")
            if os.path.isfile(rp):
                with open(rp) as f:
                    runs.append(json.load(f))
        if runs:
            results[bird] = runs
    return results


# ── 1. Loss curves ──────────────────────────────────────────────────

def plot_loss_curves(results, network_type, metric="loss"):
    """Per-bird loss / accuracy curves: thin per-seed + bold mean."""
    for bird, runs in results.items():
        fig, ax = plt.subplots(figsize=(8, 5))
        color = BIRD_COLORS.get(bird, "#333333")

        histories = [r["history"] for r in runs if "history" in r]
        if not histories:
            log.warning("No history for %s/%s – skipping loss plot", network_type, bird)
            continue

        # Plot individual runs (thin, transparent)
        max_epochs = 0
        for h in histories:
            epochs = range(1, len(h[f"train_{metric}"]) + 1)
            max_epochs = max(max_epochs, len(h[f"train_{metric}"]))
            ax.plot(epochs, h[f"train_{metric}"], color=color, alpha=SEED_ALPHA, linewidth=0.8)
            ax.plot(epochs, h[f"val_{metric}"], color=color, alpha=SEED_ALPHA, linewidth=0.8,
                    linestyle="--")

        # Mean curve (bold)
        min_len = min(len(h[f"train_{metric}"]) for h in histories)
        train_arr = np.array([h[f"train_{metric}"][:min_len] for h in histories])
        val_arr = np.array([h[f"val_{metric}"][:min_len] for h in histories])
        epochs_mean = range(1, min_len + 1)

        ax.plot(epochs_mean, train_arr.mean(axis=0), color=color, linewidth=2.5,
                label="train (mean)")
        ax.plot(epochs_mean, val_arr.mean(axis=0), color=color, linewidth=2.5,
                linestyle="--", label="val (mean)")

        # Shade ± std
        ax.fill_between(epochs_mean,
                        train_arr.mean(0) - train_arr.std(0),
                        train_arr.mean(0) + train_arr.std(0),
                        color=color, alpha=0.1)
        ax.fill_between(epochs_mean,
                        val_arr.mean(0) - val_arr.std(0),
                        val_arr.mean(0) + val_arr.std(0),
                        color=color, alpha=0.1)

        ax.set_xlabel("Epoch")
        ax.set_ylabel(metric.replace("_", " ").title())
        ax.set_title(f"{bird} – {network_type} {metric}")
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = os.path.join(FIG_DIR, f"{network_type}_{bird}_{metric}.svg")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        log.info("Saved %s", path)


# ── 2. Framewise P/R/F1 bar plot ────────────────────────────────────

def plot_framewise_bars(seg_results):
    """Grouped bar chart: framewise P / R / F1 per bird (mean ± std)."""
    birds = list(seg_results.keys())
    metrics = ["precision", "recall", "f1"]
    x = np.arange(len(birds))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, m in enumerate(metrics):
        means = [np.mean([r["framewise"][m] for r in seg_results[b]]) for b in birds]
        stds = [np.std([r["framewise"][m] for r in seg_results[b]]) for b in birds]
        ax.bar(x + i * width, means, width, yerr=stds, label=m.title(), capsize=4)

    ax.set_xticks(x + width)
    ax.set_xticklabels(birds)
    ax.set_ylabel("Score")
    ax.set_title("Framewise Segmentation Metrics (mean ± std)")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    path = os.path.join(FIG_DIR, "seg_framewise_prf1.svg")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved %s", path)


# ── 3. Collar metrics bar plots ─────────────────────────────────────

def plot_collar_bars(seg_results):
    """One figure per collar value: P / R / F1 per bird."""
    birds = list(seg_results.keys())
    metrics = ["precision", "recall", "f1"]
    width = 0.25

    for cms in COLLAR_VALUES_MS:
        key = f"@{cms}ms"
        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(birds))

        for i, m in enumerate(metrics):
            means = [np.mean([r["collar"][key][m] for r in seg_results[b]]) for b in birds]
            stds = [np.std([r["collar"][key][m] for r in seg_results[b]]) for b in birds]
            ax.bar(x + i * width, means, width, yerr=stds,
                   label=m.title(), capsize=4)

        ax.set_xticks(x + width)
        ax.set_xticklabels(birds)
        ax.set_ylabel("Score")
        ax.set_title(f"Segment-level Metrics @ {cms}ms collar (mean ± std)")
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        path = os.path.join(FIG_DIR, f"seg_collar_{cms}ms.svg")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        log.info("Saved %s", path)


# ── 4. Classification macro bar plot ────────────────────────────────

def plot_classification_bars(class_results):
    """Macro P / R / F1 per bird."""
    birds = list(class_results.keys())
    metrics = ["precision", "recall", "f1"]
    width = 0.25
    x = np.arange(len(birds))

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, m in enumerate(metrics):
        means = [np.mean([r["classification"]["macro"][m] for r in class_results[b]]) for b in birds]
        stds = [np.std([r["classification"]["macro"][m] for r in class_results[b]]) for b in birds]
        ax.bar(x + i * width, means, width, yerr=stds, label=m.title(), capsize=4)

    ax.set_xticks(x + width)
    ax.set_xticklabels(birds)
    ax.set_ylabel("Score")
    ax.set_title("Classification Macro Metrics (mean ± std)")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    path = os.path.join(FIG_DIR, "class_macro_prf1.svg")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved %s", path)


# ── 5. Combined collar F1 comparison ────────────────────────────────

def plot_collar_f1_by_tolerance(seg_results):
    """Line plot: F1 vs collar tolerance for each bird."""
    fig, ax = plt.subplots(figsize=(8, 5))

    for bird, runs in seg_results.items():
        means, stds = [], []
        for cms in COLLAR_VALUES_MS:
            key = f"@{cms}ms"
            vals = [r["collar"][key]["f1"] for r in runs]
            means.append(np.mean(vals))
            stds.append(np.std(vals))
        means, stds = np.array(means), np.array(stds)
        color = BIRD_COLORS.get(bird, "#333")
        ax.plot(COLLAR_VALUES_MS, means, "o-", color=color, label=bird, linewidth=2)
        ax.fill_between(COLLAR_VALUES_MS, means - stds, means + stds,
                        color=color, alpha=0.15)

    ax.set_xlabel("Collar tolerance (ms)")
    ax.set_ylabel("Segment-level F1")
    ax.set_title("Segmentation F1 vs. collar tolerance")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)

    path = os.path.join(FIG_DIR, "seg_collar_f1_by_tolerance.svg")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved %s", path)


# ── Entry point ──────────────────────────────────────────────────────

def generate_all_plots():
    """Generate all plots from existing results."""
    os.makedirs(FIG_DIR, exist_ok=True)

    seg_results = _load_results("seg")
    class_results = _load_results("class")

    if seg_results:
        plot_loss_curves(seg_results, "seg", "loss")
        plot_loss_curves(seg_results, "seg", "acc")
        plot_framewise_bars(seg_results)
        plot_collar_bars(seg_results)
        plot_collar_f1_by_tolerance(seg_results)
    else:
        log.warning("No segmentation results found")

    if class_results:
        plot_loss_curves(class_results, "class", "loss")
        plot_loss_curves(class_results, "class", "acc")
        plot_classification_bars(class_results)
    else:
        log.warning("No classification results found")

    log.info("All plots saved to %s", FIG_DIR)


def main():
    parser = argparse.ArgumentParser(description="Generate plots from paper experiment results")
    parser.parse_args()
    generate_all_plots()


if __name__ == "__main__":
    main()
