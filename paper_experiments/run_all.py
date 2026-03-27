#!/usr/bin/env python3
"""Run all paper experiments: N replicates × all birds × seg + class.

Aggregates per-bird results as mean ± std and writes summary tables.

Usage
-----
    python -m paper_experiments.run_all              # all birds, 3 seeds
    python -m paper_experiments.run_all --birds bu04bk04
    python -m paper_experiments.run_all --type seg   # segmentation only
"""
import argparse
import json
import logging
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from paper_experiments.config import BIRDS, N_REPLICATES, OUTPUT_DIR, REPLICATE_SEEDS
from paper_experiments.metrics import combined_pipeline_metrics
from paper_experiments.plot_results import generate_all_plots
from paper_experiments.train_segmentation import train_segmentation
from paper_experiments.train_classification import train_classification

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def _mean_std(values):
    """Return formatted mean ± std string."""
    a = np.array(values)
    return f"{a.mean():.4f} ± {a.std():.4f}"


def aggregate_segmentation(all_results):
    """Aggregate segmentation results per bird → mean ± std."""
    summary = {}
    for bird, runs in all_results.items():
        accs = [r["test_accuracy"] for r in runs]
        fw_p = [r["framewise"]["precision"] for r in runs]
        fw_r = [r["framewise"]["recall"] for r in runs]
        fw_f1 = [r["framewise"]["f1"] for r in runs]

        bird_summary = {
            "test_accuracy": _mean_std(accs),
            "framewise_precision": _mean_std(fw_p),
            "framewise_recall": _mean_std(fw_r),
            "framewise_f1": _mean_std(fw_f1),
        }

        # Collar metrics
        collar_keys = list(runs[0]["collar"].keys())
        for ck in collar_keys:
            cp = [r["collar"][ck]["precision"] for r in runs]
            cr = [r["collar"][ck]["recall"] for r in runs]
            cf = [r["collar"][ck]["f1"] for r in runs]
            bird_summary[f"collar_{ck}_precision"] = _mean_std(cp)
            bird_summary[f"collar_{ck}_recall"] = _mean_std(cr)
            bird_summary[f"collar_{ck}_f1"] = _mean_std(cf)

        summary[bird] = bird_summary
    return summary


def aggregate_classification(all_results):
    """Aggregate classification results per bird → mean ± std."""
    summary = {}
    for bird, runs in all_results.items():
        accs = [r["test_accuracy"] for r in runs]
        mac_p = [r["classification"]["macro"]["precision"] for r in runs]
        mac_r = [r["classification"]["macro"]["recall"] for r in runs]
        mac_f1 = [r["classification"]["macro"]["f1"] for r in runs]

        summary[bird] = {
            "test_accuracy": _mean_std(accs),
            "macro_precision": _mean_std(mac_p),
            "macro_recall": _mean_std(mac_r),
            "macro_f1": _mean_std(mac_f1),
        }
    return summary


def aggregate_combined(all_results):
    """Aggregate combined seg+class results per bird → mean ± std."""
    summary = {}
    for bird, runs in all_results.items():
        bird_summary = {}

        # Framewise combined (smoothed)
        fw_accs = [r["framewise_smoothed"]["accuracy"] for r in runs]
        fw_p = [r["framewise_smoothed"]["precision"] for r in runs]
        fw_r = [r["framewise_smoothed"]["recall"] for r in runs]
        fw_f1 = [r["framewise_smoothed"]["f1"] for r in runs]
        bird_summary["framewise_sw_accuracy"] = _mean_std(fw_accs)
        bird_summary["framewise_sw_precision"] = _mean_std(fw_p)
        bird_summary["framewise_sw_recall"] = _mean_std(fw_r)
        bird_summary["framewise_sw_f1"] = _mean_std(fw_f1)

        # Syllable-level collar combined (use sw collar values)
        collar_keys = [k for k in runs[0]["syllable_collar"] if k.endswith("_sw")]
        for ck in collar_keys:
            cp = [r["syllable_collar"][ck]["precision"] for r in runs]
            cr = [r["syllable_collar"][ck]["recall"] for r in runs]
            cf = [r["syllable_collar"][ck]["f1"] for r in runs]
            bird_summary[f"combined_{ck}_precision"] = _mean_std(cp)
            bird_summary[f"combined_{ck}_recall"] = _mean_std(cr)
            bird_summary[f"combined_{ck}_f1"] = _mean_std(cf)

        summary[bird] = bird_summary
    return summary


def run_all(birds, seeds, run_seg=True, run_class=True):
    """Execute all experiments and produce summary."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    seg_results = {}
    class_results = {}
    comb_results = {}

    for bird in birds:
        if run_seg:
            seg_results[bird] = []
            for seed in seeds:
                r = train_segmentation(bird, seed)
                seg_results[bird].append(r)

        if run_class:
            class_results[bird] = []
            for seed in seeds:
                r = train_classification(bird, seed)
                class_results[bird].append(r)

        # ── Combined pipeline metrics (seg × class) ─────────────────
        if run_seg and run_class and bird in seg_results and bird in class_results:
            comb_results[bird] = []
            for seg_r, cls_r in zip(seg_results[bird], class_results[bird]):
                cm = combined_pipeline_metrics(seg_r, cls_r)
                comb_results[bird].append(cm)
                fw = cm["framewise_smoothed"]
                log.info("Combined(%s seed=%d)  framewise(sw) acc=%.4f P=%.4f R=%.4f F1=%.4f",
                         bird, seg_r["seed"], fw["accuracy"],
                         fw["precision"], fw["recall"], fw["f1"])
                # Save per-replicate combined results
                run_dir = os.path.join(OUTPUT_DIR, "combined", bird,
                                       f"seed_{seg_r['seed']}")
                os.makedirs(run_dir, exist_ok=True)
                with open(os.path.join(run_dir, "results.json"), "w") as f:
                    json.dump(cm, f, indent=2)

    # ── Summaries ────────────────────────────────────────────────────
    combined = {}
    if run_seg and seg_results:
        seg_summary = aggregate_segmentation(seg_results)
        combined["segmentation"] = seg_summary
        log.info("\n=== SEGMENTATION SUMMARY ===")
        for bird, s in seg_summary.items():
            log.info("%s: %s", bird, json.dumps(s, indent=2))

    if run_class and class_results:
        class_summary = aggregate_classification(class_results)
        combined["classification"] = class_summary
        log.info("\n=== CLASSIFICATION SUMMARY ===")
        for bird, s in class_summary.items():
            log.info("%s: %s", bird, json.dumps(s, indent=2))

    if comb_results:
        comb_summary = aggregate_combined(comb_results)
        combined["combined_pipeline"] = comb_summary
        log.info("\n=== COMBINED PIPELINE SUMMARY (seg → class) ===")
        for bird, s in comb_summary.items():
            log.info("%s: %s", bird, json.dumps(s, indent=2))

    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(combined, f, indent=2)
    log.info("Summary: %s", summary_path)

    # ── Generate plots ───────────────────────────────────────────────
    log.info("Generating plots...")
    generate_all_plots()

    return combined


def main():
    parser = argparse.ArgumentParser(description="Run all paper experiments")
    parser.add_argument("--birds", nargs="+", default=list(BIRDS.keys()),
                        choices=list(BIRDS.keys()))
    parser.add_argument("--seeds", nargs="+", type=int, default=None,
                        help="Override replicate seeds")
    parser.add_argument("--type", choices=["seg", "class", "both"], default="both",
                        help="Run segmentation, classification, or both")
    args = parser.parse_args()

    seeds = args.seeds or REPLICATE_SEEDS[:N_REPLICATES]
    run_seg = args.type in ("seg", "both")
    run_class = args.type in ("class", "both")
    run_all(args.birds, seeds, run_seg=run_seg, run_class=run_class)


if __name__ == "__main__":
    main()
