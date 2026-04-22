#!/usr/bin/env python3
"""Compute signed onset time differences between Moove predictions and ground truth.

For all matched segments (TP in onset collar @10ms), compute:
    signed_error_ms = pred_onset_ms - true_onset_ms

Reads from final_experiments/results/{bird}/seg/seed_{n}/predictions.npz
(y_true, y_pred_smoothed, te_file_ids).

Writes results to segmentation_chapter/onset_error_analysis/onset_errors.json
Nothing in final_experiments/ is modified.
"""

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

RESULTS_DIR = REPO_ROOT / "final_experiments" / "results"
OUT_DIR = Path(__file__).parent
OUT_FILE = OUT_DIR / "onset_errors.json"

BIRDS = ["ye00pu07", "bu04bk04", "gy07bu07", "br08pk08", "ye04gr05"]
SEEDS = [42, 123, 456]
COLLAR_MS = 10  # match collar used for onset_collar_smoothed @10ms


def extract_segments(labels):
    """Return list of (onset_idx, offset_idx) from binary label array."""
    segs, in_seg, onset = [], False, 0
    for i, v in enumerate(labels):
        if v == 1 and not in_seg:
            onset, in_seg = i, True
        elif v == 0 and in_seg:
            segs.append((onset, i))
            in_seg = False
    if in_seg:
        segs.append((onset, len(labels)))
    return segs


def compute_signed_errors(y_true, y_pred_smoothed, chunk_size, sample_rate, collar_ms):
    """Compute signed onset errors (ms) for all TP matches."""
    collar_frames = round(collar_ms * sample_rate / (chunk_size * 1000))
    true_segs = extract_segments(y_true)
    pred_segs = extract_segments(y_pred_smoothed)

    matched_true = set()
    errors_frames = []

    for p_onset, _ in pred_segs:
        for j, (t_onset, _) in enumerate(true_segs):
            if j in matched_true:
                continue
            if abs(p_onset - t_onset) <= collar_frames:
                matched_true.add(j)
                errors_frames.append(p_onset - t_onset)
                break

    ms_per_frame = chunk_size / sample_rate * 1000
    errors_ms = [e * ms_per_frame for e in errors_frames]
    return errors_ms


def main():
    all_results = {}

    for bird in BIRDS:
        bird_errors = []
        per_seed = []

        for seed in SEEDS:
            npz_path = RESULTS_DIR / bird / "seg" / f"seed_{seed}" / "predictions.npz"
            json_path = RESULTS_DIR / bird / "seg" / f"seed_{seed}" / "results.json"

            if not npz_path.exists():
                print(f"  MISSING: {npz_path}")
                continue

            data = np.load(npz_path, allow_pickle=True)
            y_true = data["y_true"]
            y_pred_smoothed = data["y_pred_smoothed"]

            with open(json_path) as f:
                meta = json.load(f)
            chunk_size = meta["chunk_size"]
            sample_rate = meta["sample_rate"]

            errors_ms = compute_signed_errors(
                y_true, y_pred_smoothed, chunk_size, sample_rate, COLLAR_MS
            )

            n = len(errors_ms)
            mean = float(np.mean(errors_ms)) if n else float("nan")
            std = float(np.std(errors_ms)) if n else float("nan")
            median = float(np.median(errors_ms)) if n else float("nan")

            per_seed.append({
                "seed": seed,
                "n_matched": n,
                "mean_ms": round(mean, 3),
                "std_ms": round(std, 3),
                "median_ms": round(median, 3),
            })
            bird_errors.extend(errors_ms)

            print(f"  {bird} seed_{seed}: n={n}, mean={mean:.2f} ms, "
                  f"std={std:.2f} ms, median={median:.2f} ms")

        if bird_errors:
            all_errors = np.array(bird_errors)
            all_results[bird] = {
                "per_seed": per_seed,
                "pooled": {
                    "n_matched": len(bird_errors),
                    "mean_ms": round(float(np.mean(all_errors)), 3),
                    "std_ms": round(float(np.std(all_errors)), 3),
                    "median_ms": round(float(np.median(all_errors)), 3),
                    "p5_ms": round(float(np.percentile(all_errors, 5)), 3),
                    "p95_ms": round(float(np.percentile(all_errors, 95)), 3),
                },
            }

    # Overall pooled across all birds
    all_errors_flat = []
    for bird in BIRDS:
        if bird in all_results:
            for s in all_results[bird]["per_seed"]:
                pass  # already collected above; re-collect below

    # Re-collect all errors across birds for global summary
    global_errors = []
    for bird in BIRDS:
        for seed in SEEDS:
            npz_path = RESULTS_DIR / bird / "seg" / f"seed_{seed}" / "predictions.npz"
            json_path = RESULTS_DIR / bird / "seg" / f"seed_{seed}" / "results.json"
            if not npz_path.exists():
                continue
            data = np.load(npz_path, allow_pickle=True)
            with open(json_path) as f:
                meta = json.load(f)
            errors_ms = compute_signed_errors(
                data["y_true"], data["y_pred_smoothed"],
                meta["chunk_size"], meta["sample_rate"], COLLAR_MS
            )
            global_errors.extend(errors_ms)

    global_arr = np.array(global_errors)
    all_results["_global"] = {
        "collar_ms": COLLAR_MS,
        "n_matched": len(global_errors),
        "mean_ms": round(float(np.mean(global_arr)), 3),
        "std_ms": round(float(np.std(global_arr)), 3),
        "median_ms": round(float(np.median(global_arr)), 3),
        "p5_ms": round(float(np.percentile(global_arr, 5)), 3),
        "p95_ms": round(float(np.percentile(global_arr, 95)), 3),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved: {OUT_FILE}")

    print("\n=== SUMMARY ===")
    g = all_results["_global"]
    print(f"Global (all birds pooled, collar @{COLLAR_MS}ms):")
    print(f"  n={g['n_matched']}, mean={g['mean_ms']} ms, "
          f"std={g['std_ms']} ms, median={g['median_ms']} ms")
    print(f"  5th–95th percentile: {g['p5_ms']} – {g['p95_ms']} ms")


if __name__ == "__main__":
    main()
