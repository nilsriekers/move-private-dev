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
from paper_experiments.train_segmentation import train_segmentation
from paper_experiments.train_classification import train_classification
from paper_experiments.eval_baseline import run_baseline

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

        # Collar metrics (raw, smoothed, onset-only variants)
        for section in ["collar", "collar_smoothed", "onset_collar", "onset_collar_smoothed"]:
            if section not in runs[0]:
                continue
            collar_keys = list(runs[0][section].keys())
            for ck in collar_keys:
                cp = [r[section][ck]["precision"] for r in runs]
                cr = [r[section][ck]["recall"] for r in runs]
                cf = [r[section][ck]["f1"] for r in runs]
                bird_summary[f"{section}_{ck}_precision"] = _mean_std(cp)
                bird_summary[f"{section}_{ck}_recall"] = _mean_std(cr)
                bird_summary[f"{section}_{ck}_f1"] = _mean_std(cf)

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


def run_all(birds, seeds, run_seg=True, run_class=True, run_baseline_eval=False):
    """Execute all experiments and produce summary."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Energy-based baseline ──────────────────────────────────────
    if run_baseline_eval:
        baseline_results = {}
        for bird in birds:
            baseline_results[bird] = []
            for seed in seeds:
                result_path = os.path.join(
                    OUTPUT_DIR, "baseline", bird, f"seed_{seed}", "results.json")
                if os.path.exists(result_path):
                    try:
                        with open(result_path) as f:
                            existing = json.load(f)
                        if "framewise" in existing:
                            log.info("Skip baseline %s seed=%d (already complete)", bird, seed)
                            baseline_results[bird].append(existing)
                            continue
                    except Exception:
                        pass
                r = run_baseline(bird, seed)
                baseline_results[bird].append(r)

        baseline_summary = aggregate_segmentation(baseline_results)
        summary_path = os.path.join(OUTPUT_DIR, "baseline_summary.json")
        with open(summary_path, "w") as f:
            json.dump({"baseline": baseline_summary}, f, indent=2)
        log.info("\n=== BASELINE SUMMARY ===")
        for bird, s in baseline_summary.items():
            log.info("%s: %s", bird, json.dumps(s, indent=2))
        log.info("Summary: %s", summary_path)
        return {"baseline": baseline_summary}

    seg_results = {}
    class_results = {}
    comb_results = {}

    for bird in birds:
        if run_seg:
            seg_results[bird] = []
            for seed in seeds:
                # Check if segmentation result exists and is complete (never overwrite!)
                seg_dir = os.path.join(OUTPUT_DIR, "seg", bird, f"seed_{seed}")
                seg_result_path = os.path.join(seg_dir, "results.json")
                seg_result = None
                if os.path.exists(seg_result_path):
                    try:
                        with open(seg_result_path, "r") as f:
                            seg_result = json.load(f)
                        # Check for a key that indicates a complete run (e.g., 'test_accuracy')
                        if "test_accuracy" in seg_result:
                            log.info(f"Skip segmentation {bird} seed={seed} (already complete)")
                            seg_results[bird].append(seg_result)
                            continue
                    except Exception as e:
                        log.warning(f"Could not read {seg_result_path}: {e}")
                # Run if not complete and nothing exists
                r = train_segmentation(bird, seed)
                seg_results[bird].append(r)

        if run_class:
            class_results[bird] = []
            for seed in seeds:
                # Check if classification result exists and is complete (never overwrite!)
                class_dir = os.path.join(OUTPUT_DIR, "class", bird, f"seed_{seed}")
                class_result_path = os.path.join(class_dir, "results.json")
                class_result = None
                if os.path.exists(class_result_path):
                    try:
                        with open(class_result_path, "r") as f:
                            class_result = json.load(f)
                        if "test_accuracy" in class_result:
                            log.info(f"Skip classification {bird} seed={seed} (already complete)")
                            class_results[bird].append(class_result)
                            continue
                    except Exception as e:
                        log.warning(f"Could not read {class_result_path}: {e}")
                r = train_classification(bird, seed)
                class_results[bird].append(r)

        # ── Combined pipeline metrics (seg × class) ─────────────────
        if run_seg and run_class and bird in seg_results and bird in class_results:
            comb_results[bird] = []
            for seg_r, cls_r in zip(seg_results[bird], class_results[bird]):
                # Check if combined result exists and is complete
                run_dir = os.path.join(OUTPUT_DIR, "combined", bird, f"seed_{seg_r.get('seed', cls_r.get('seed', 'unknown'))}")
                comb_result_path = os.path.join(run_dir, "results.json")
                comb_result = None
                if os.path.exists(comb_result_path):
                    try:
                        with open(comb_result_path, "r") as f:
                            comb_result = json.load(f)
                        if "framewise_smoothed" in comb_result:
                            log.info(f"Skip combined {bird} seed={seg_r.get('seed', 'unknown')} (already complete)")
                            comb_results[bird].append(comb_result)
                            continue
                    except Exception as e:
                        log.warning(f"Could not read {comb_result_path}: {e}")
                cm = combined_pipeline_metrics(seg_r, cls_r)
                comb_results[bird].append(cm)
                fw = cm["framewise_smoothed"]
                log.info("Combined(%s seed=%s)  framewise(sw) acc=%.4f P=%.4f R=%.4f F1=%.4f",
                         bird, seg_r.get("seed", "unknown"), fw["accuracy"],
                         fw["precision"], fw["recall"], fw["f1"])
                # Save per-replicate combined results
                os.makedirs(run_dir, exist_ok=True)
                with open(comb_result_path, "w") as f:
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

    # ── Generate plots (skip if matplotlib not available, e.g. on cloud VMs) ──
    try:
        from paper_experiments.plot_results import generate_all_plots
        log.info("Generating plots...")
        generate_all_plots()
    except ImportError:
        log.info("Skipping plot generation (matplotlib not available)")

    return combined


def main():
    parser = argparse.ArgumentParser(description="Run all paper experiments")
    parser.add_argument("--birds", nargs="+", default=list(BIRDS.keys()),
                        choices=list(BIRDS.keys()))
    parser.add_argument("--seeds", nargs="+", type=int, default=None,
                        help="Override replicate seeds")
    parser.add_argument("--type", choices=["seg", "class", "both", "baseline"],
                        default="both",
                        help="Run segmentation, classification, both, or energy baseline")
    args = parser.parse_args()

    # Standardmäßig nur noch 3 Seeds (statt 5) verwenden
    # seeds = args.seeds or REPLICATE_SEEDS[:N_REPLICATES]
    seeds = args.seeds or REPLICATE_SEEDS[:3]  # <--- Nur noch 3 Seeds
    run_seg = args.type in ("seg", "both")
    run_class = args.type in ("class", "both")
    run_baseline_eval = args.type == "baseline"
    run_all(args.birds, seeds, run_seg=run_seg, run_class=run_class,
            run_baseline_eval=run_baseline_eval)


if __name__ == "__main__":
    main()
