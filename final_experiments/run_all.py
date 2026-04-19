#!/usr/bin/env python3
"""Orchestrate final_experiments training runs.

Can run a single bird/seed (for distributed GCloud execution) or all.

Usage
-----
  # All birds, all seeds, both tasks:
  uv run python3 final_experiments/run_all.py

  # Single bird (one GCloud VM):
  uv run python3 final_experiments/run_all.py --bird ye04gr05

  # Single bird + single seed (finest granularity):
  uv run python3 final_experiments/run_all.py --bird ye04gr05 --seed 42

  # Only segmentation:
  uv run python3 final_experiments/run_all.py --type seg

  # Skip already-completed runs (default: True):
  uv run python3 final_experiments/run_all.py --force   # re-run everything
"""
import argparse
import json
import logging
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from final_experiments.config import BIRDS, OUTPUT_DIR, REPLICATE_SEEDS
from final_experiments.train_seg   import train_seg
from final_experiments.train_class import train_class
from final_experiments.eval_baseline import run_baseline

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def _is_complete(path, required_key="test_accuracy"):
    if not os.path.isfile(path):
        return False
    try:
        with open(path) as f:
            d = json.load(f)
        return required_key in d
    except Exception:
        return False


def _ms(vals):
    a = np.array(vals)
    return f"{a.mean():.4f} ± {a.std():.4f}"


def run_all(birds, seeds, run_seg=True, run_class=True, run_baseline_eval=False,
            force=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Energy-based baseline ──────────────────────────────────────
    if run_baseline_eval:
        baseline_results = {}
        for bird in birds:
            baseline_results[bird] = []
            for seed in seeds:
                rpath = os.path.join(OUTPUT_DIR, bird, "seg_baseline",
                                     f"seed_{seed}", "results.json")
                if not force and _is_complete(rpath, required_key="framewise"):
                    log.info("SKIP baseline %s seed=%d (already complete)", bird, seed)
                    with open(rpath) as f:
                        baseline_results[bird].append(json.load(f))
                    continue
                r = run_baseline(bird, seed)
                baseline_results[bird].append(r)

        log.info("\n=== BASELINE SUMMARY ===")
        bl_summary = {}
        for bird, runs in baseline_results.items():
            if not runs:
                continue
            s = {
                "threshold_db":         _ms([r["threshold_db"]                                for r in runs]),
                "framewise_f1":         _ms([r["framewise"]["f1"]                             for r in runs]),
                "collar@10ms_sw_f1":    _ms([r["collar_smoothed"]["@10ms"]["f1"]              for r in runs]),
                "onset@10ms_sw_f1":     _ms([r["onset_collar_smoothed"]["@10ms"]["f1"]        for r in runs]),
            }
            bl_summary[bird] = s
            log.info("%s: %s", bird, json.dumps(s))
        summary_path = os.path.join(OUTPUT_DIR, "baseline_summary.json")
        with open(summary_path, "w") as f:
            json.dump({"baseline": bl_summary}, f, indent=2)
        log.info("Summary: %s", summary_path)
        return {"baseline": bl_summary}

    seg_results   = {}
    class_results = {}

    for bird in birds:
        if run_seg:
            seg_results[bird] = []
            for seed in seeds:
                rpath = os.path.join(OUTPUT_DIR, bird, "seg", f"seed_{seed}", "results.json")
                if not force and _is_complete(rpath):
                    log.info("SKIP seg  %s seed=%d (already complete)", bird, seed)
                    with open(rpath) as f:
                        seg_results[bird].append(json.load(f))
                    continue
                r = train_seg(bird, seed)
                seg_results[bird].append(r)

        if run_class:
            class_results[bird] = []
            for seed in seeds:
                rpath = os.path.join(OUTPUT_DIR, bird, "class", f"seed_{seed}", "results.json")
                if not force and _is_complete(rpath):
                    log.info("SKIP class %s seed=%d (already complete)", bird, seed)
                    with open(rpath) as f:
                        class_results[bird].append(json.load(f))
                    continue
                r = train_class(bird, seed)
                class_results[bird].append(r)

    # ── Summary ──────────────────────────────────────────────────────
    summary = {}

    if run_seg and seg_results:
        summary["segmentation"] = {}
        log.info("\n=== SEGMENTATION SUMMARY ===")
        for bird, runs in seg_results.items():
            if not runs:
                continue
            s = {
                "test_accuracy":        _ms([r["test_accuracy"]          for r in runs]),
                "framewise_f1":         _ms([r["framewise"]["f1"]        for r in runs]),
                "onset_collar@10ms_f1": _ms([r["onset_collar_smoothed"]["@10ms"]["f1"] for r in runs]),
            }
            summary["segmentation"][bird] = s
            log.info("%s: %s", bird, json.dumps(s))

    if run_class and class_results:
        summary["classification"] = {}
        log.info("\n=== CLASSIFICATION SUMMARY ===")
        for bird, runs in class_results.items():
            if not runs:
                continue
            s = {
                "test_accuracy": _ms([r["test_accuracy"]                         for r in runs]),
                "macro_f1":      _ms([r["classification"]["macro"]["f1"]          for r in runs]),
                "epochs_mean":   float(np.mean([len(r["history"]["train_loss"])   for r in runs])),
            }
            summary["classification"][bird] = s
            log.info("%s: %s", bird, json.dumps(s))

    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info("Summary: %s", summary_path)
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--birds", nargs="+", default=list(BIRDS.keys()),
                   choices=list(BIRDS.keys()))
    p.add_argument("--bird",  default=None, choices=list(BIRDS.keys()),
                   help="Single bird (shorthand for --birds)")
    p.add_argument("--seeds", nargs="+", type=int, default=None)
    p.add_argument("--seed",  type=int,   default=None,
                   help="Single seed (shorthand for --seeds)")
    p.add_argument("--type",  choices=["seg", "class", "both", "baseline"],
                   default="both")
    p.add_argument("--force", action="store_true",
                   help="Re-run even if results.json already exists")
    args = p.parse_args()

    birds = [args.bird] if args.bird else args.birds
    seeds = [args.seed] if args.seed else (args.seeds or REPLICATE_SEEDS)
    run_seg   = args.type in ("seg",  "both")
    run_class = args.type in ("class", "both")
    run_baseline_eval = args.type == "baseline"

    run_all(birds, seeds, run_seg=run_seg, run_class=run_class,
            run_baseline_eval=run_baseline_eval, force=args.force)


if __name__ == "__main__":
    main()
