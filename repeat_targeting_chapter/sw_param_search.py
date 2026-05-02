#!/usr/bin/env python3
"""Grid search over threshold x SW parameters for gy07bu07 overlap predictions.

Reads predictions_overlap.npz (seed 42 only, read-only).
Writes results to repeat_targeting_chapter/sw_param_search_results.json.
Nothing in final_experiments/ is modified.
"""

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from paper_experiments.metrics import (
    apply_sliding_window,
    onset_collar_segmentation_metrics,
)

NPZ = REPO_ROOT / "final_experiments/results/gy07bu07/seg/seed_42/predictions_overlap.npz"
OUT = Path(__file__).parent / "sw_param_search_results.json"

COLLAR_MS = 10
CHUNK_SIZE = 64
SAMPLE_RATE = 44100

# Grid
THRESHOLDS = [round(t, 2) for t in np.arange(0.3, 0.96, 0.05)]
ONSET_WINDOWS = [3, 5, 7]
N_ONSET_TRUE  = [2, 3, 4]   # votes needed for onset
OFFSET_WINDOWS = [3, 5, 7]
N_OFFSET_FALSE = [2, 3, 4]  # votes needed for offset


def extract_segments(labels):
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


def onset_f1(y_true, y_smoothed, collar_ms=10):
    collar_frames = round(collar_ms * SAMPLE_RATE / (CHUNK_SIZE * 1000))
    true_segs = extract_segments(y_true)
    pred_segs = extract_segments(y_smoothed)
    matched = set()
    tp = 0
    for p_on, _ in pred_segs:
        for j, (t_on, _) in enumerate(true_segs):
            if j in matched:
                continue
            if abs(p_on - t_on) <= collar_frames:
                matched.add(j)
                tp += 1
                break
    fp = len(pred_segs) - tp
    fn = len(true_segs) - tp
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {"f1": f1, "precision": prec, "recall": rec, "tp": tp, "fp": fp, "fn": fn}


def main():
    data = np.load(NPZ, allow_pickle=True)
    y_true = data["y_true"].astype(int)
    y_pred = data["y_pred"].astype(float)

    print(f"Loaded: n_frames={len(y_true)}, n_true_segs={sum(1 for i in range(len(y_true)) if y_true[i]==1 and (i==0 or y_true[i-1]==0))}")
    print(f"Grid: {len(THRESHOLDS)} thresholds x {len(ONSET_WINDOWS)} ow x {len(N_ONSET_TRUE)} nv x {len(OFFSET_WINDOWS)} ofw x {len(N_OFFSET_FALSE)} nof = "
          f"{len(THRESHOLDS)*len(ONSET_WINDOWS)*len(N_ONSET_TRUE)*len(OFFSET_WINDOWS)*len(N_OFFSET_FALSE)} combos\n")

    results = []
    best_f1 = 0.0
    best = None

    total = len(THRESHOLDS) * len(ONSET_WINDOWS) * len(N_ONSET_TRUE) * len(OFFSET_WINDOWS) * len(N_OFFSET_FALSE)
    done = 0

    for thresh, ow, nv, ofw, nof in product(THRESHOLDS, ONSET_WINDOWS, N_ONSET_TRUE, OFFSET_WINDOWS, N_OFFSET_FALSE):
        if nv >= ow or nof >= ofw:
            done += 1
            continue  # nonsensical: need fewer votes than window

        y_bin = (y_pred >= thresh).astype(int).tolist()
        y_sm, _ = apply_sliding_window(
            y_bin,
            onset_window_size=ow,
            n_onset_true=nv,
            offset_window_size=ofw,
            n_offset_false=nof,
        )
        m = onset_f1(y_true, y_sm, COLLAR_MS)

        row = {
            "threshold": thresh,
            "onset_window": ow,
            "n_onset_true": nv,
            "offset_window": ofw,
            "n_offset_false": nof,
            "f1": round(m["f1"], 4),
            "precision": round(m["precision"], 4),
            "recall": round(m["recall"], 4),
            "tp": m["tp"], "fp": m["fp"], "fn": m["fn"],
        }
        results.append(row)

        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best = row

        done += 1
        if done % 500 == 0:
            print(f"  {done}/{total} done, best so far: F1={best_f1:.4f} @ {best}")

    # Sort by F1 descending
    results.sort(key=lambda x: -x["f1"])

    out = {
        "bird": "gy07bu07",
        "seed": 42,
        "collar_ms": COLLAR_MS,
        "n_results": len(results),
        "best": results[0],
        "top10": results[:10],
        "all": results,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n=== BEST RESULT ===")
    print(json.dumps(results[0], indent=2))
    print(f"\nSaved {len(results)} results to {OUT}")


if __name__ == "__main__":
    main()
