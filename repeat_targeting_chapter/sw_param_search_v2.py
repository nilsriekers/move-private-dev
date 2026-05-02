#!/usr/bin/env python3
"""Extended grid search: threshold (val-based) x SW params x no-SW baseline.

- Uses val-tuned threshold from checkpoint (not oracle/test labels)
- Tests wider SW parameter ranges including larger windows
- Tests no-SW baseline (raw threshold only)
- Seed 42 only, read-only access to final_experiments/

Writes to repeat_targeting_chapter/sw_param_search_v2_results.json
"""

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from paper_experiments.metrics import apply_sliding_window
from final_experiments.train_seg import _apply_sliding_window_per_file

NPZ  = REPO_ROOT / "final_experiments/results/gy07bu07/seg/seed_42/predictions_overlap.npz"
CKPT = REPO_ROOT / "final_experiments/results/gy07bu07/seg/seed_42/gy07bu07_seg_seed42_overlap.pth"
OUT  = Path(__file__).parent / "sw_param_search_v2_results.json"

COLLAR_MS   = 10
CHUNK_SIZE  = 64
SAMPLE_RATE = 44100


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


def onset_f1(y_true, y_smoothed):
    collar_frames = round(COLLAR_MS * SAMPLE_RATE / (CHUNK_SIZE * 1000))
    true_segs = extract_segments(list(y_true))
    pred_segs = extract_segments(list(y_smoothed))
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
    return {"f1": round(f1,4), "precision": round(prec,4), "recall": round(rec,4),
            "tp": tp, "fp": fp, "fn": fn}


def main():
    # Load val-tuned threshold from checkpoint
    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)
    val_threshold = ckpt["metadata"].get("tuned_threshold", 0.5)
    val_f1        = ckpt["metadata"].get("tuned_threshold_val_f1", float("nan"))
    print(f"Val-tuned threshold: {val_threshold:.4f}  (val F1: {val_f1:.4f})")

    # Load test predictions
    data        = np.load(NPZ, allow_pickle=True)
    y_true      = data["y_true"].astype(int)
    y_pred      = data["y_pred"].astype(float)
    te_file_ids = data["te_file_ids"]

    y_bin = (y_pred >= val_threshold).astype(int).tolist()
    n_true_segs = sum(1 for i in range(len(y_true)) if y_true[i]==1 and (i==0 or y_true[i-1]==0))
    print(f"n_frames={len(y_true)}, n_true_segs={n_true_segs}\n")

    results = []

    # ── 1. No SW: raw threshold only ──────────────────────────────────
    m = onset_f1(y_true, y_bin)
    results.append({"config": "no_SW", "threshold": val_threshold,
                    "onset_window": None, "n_onset_true": None,
                    "offset_window": None, "n_offset_false": None, **m})
    print(f"No SW:  F1={m['f1']}  P={m['precision']}  R={m['recall']}  tp={m['tp']} fp={m['fp']} fn={m['fn']}")

    # ── 2. SW grid: wider range ────────────────────────────────────────
    ONSET_WINDOWS  = [3, 5, 7, 9, 11]
    N_ONSET_TRUE   = [2, 3, 4, 5]
    OFFSET_WINDOWS = [3, 5, 7, 9, 11]
    N_OFFSET_FALSE = [2, 3, 4, 5]

    total = sum(
        1 for ow, nv, ofw, nof
        in product(ONSET_WINDOWS, N_ONSET_TRUE, OFFSET_WINDOWS, N_OFFSET_FALSE)
        if nv < ow and nof < ofw
    )
    print(f"SW grid: {total} valid combos")

    best_f1 = m["f1"]  # start with no-SW as baseline
    done = 0

    for ow, nv, ofw, nof in product(ONSET_WINDOWS, N_ONSET_TRUE, OFFSET_WINDOWS, N_OFFSET_FALSE):
        if nv >= ow or nof >= ofw:
            continue

        y_sm, _ = _apply_sliding_window_per_file(
            y_bin, te_file_ids,
            {"onset_window_size": ow, "n_onset_true": nv,
             "offset_window_size": ofw, "n_offset_false": nof}
        )
        m = onset_f1(y_true, y_sm)
        results.append({
            "config": "SW",
            "threshold": val_threshold,
            "onset_window": ow, "n_onset_true": nv,
            "offset_window": ofw, "n_offset_false": nof,
            **m
        })
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            print(f"  New best: F1={m['f1']}  ow={ow} nv={nv} ofw={ofw} nof={nof}  P={m['precision']} R={m['recall']}")
        done += 1

    # Sort by F1 desc
    results.sort(key=lambda x: -x["f1"])

    out = {
        "bird": "gy07bu07", "seed": 42,
        "val_threshold": val_threshold, "val_f1": val_f1,
        "collar_ms": COLLAR_MS,
        "no_sw_result": next(r for r in results if r["config"] == "no_SW"),
        "best": results[0],
        "top20": results[:20],
        "all": results,
    }

    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n=== SUMMARY ===")
    print(f"No SW:  F1={out['no_sw_result']['f1']}")
    print(f"Best:   F1={results[0]['f1']}  config={results[0]}")
    print(f"\nSaved to {OUT}")


if __name__ == "__main__":
    main()
