#!/usr/bin/env python3
"""Energy-based segmentation baseline evaluation for final_experiments.

Uses the same file-based val/test split as the neural net (train_seg.py)
and reports the same metrics: framewise P/R/F1, collar @5/10/15/20ms
(raw + sliding window), onset/offset collar (raw + sliding window).

Pipeline: raw audio -> evfuncs.smooth_data() -> decibel() -> evfuncs.segment_song()
Grid-searches optimal dB threshold on the val set (maximize collar@10ms F1).

Saves per run:
  results/{bird}/baseline/seed_{seed}/results.json       - aggregate test metrics
  results/{bird}/baseline/seed_{seed}/grid_search.json   - full grid search results
  results/{bird}/baseline/seed_{seed}/per_file_results.json - per-file breakdown

Usage
-----
  python -m final_experiments.eval_baseline --bird ye04gr05 --seed 42
  python -m final_experiments.eval_baseline                  # all birds, all seeds
"""
import argparse
import json
import logging
import os
import sys

import evfuncs
import numpy as np
from scipy.io import wavfile
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Inline decibel to avoid moove/utils/__init__.py → PyQt6 chain on headless VMs
def decibel(x, xref=1.0):
    """Identical to moove.utils.audio_utils.decibel."""
    x_copy = np.copy(x)
    x_copy[x_copy < 1e-10] = 1e-10
    return 20.0 * np.log10(x_copy / xref)


from paper_experiments.metrics import (
    apply_sliding_window,
    collar_ms_to_frames,
    collar_segmentation_metrics,
    framewise_metrics,
    offset_collar_segmentation_metrics,
    onset_collar_segmentation_metrics,
)
from final_experiments.config import (
    BASELINE_GRID_MARGIN_DB, BASELINE_GRID_STEP_DB,
    BIRDS, COLLAR_VALUES_MS, EVFUNCS_PARAMS, OUTPUT_DIR,
    REPLICATE_SEEDS, SAMPLE_RATE, SEG_DATASET_PARAMS, SLIDING_WINDOW_PARAMS,
)
from final_experiments.create_dataset import get_wav_files

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

CHUNK_SIZE = SEG_DATASET_PARAMS["chunk_size"]


# ── Audio processing ────────────────────────────────────────────────

def precompute_file(wav_path):
    """Load WAV, compute smoothed dB envelope, load ground truth."""
    sr, audio = wavfile.read(wav_path)
    audio = audio.astype(np.float64)
    if audio.ndim > 1:
        audio = audio[:, 0]

    smooth = evfuncs.smooth_data(
        audio, sr,
        EVFUNCS_PARAMS["freq_cutoffs"],
        EVFUNCS_PARAMS["smooth_window"],
    )
    db_smooth = decibel(smooth)

    notmat = evfuncs.load_notmat(wav_path + ".not.mat")
    gt_onsets_ms = np.array(notmat.get("onsets", []), dtype=np.float64)
    gt_offsets_ms = np.array(notmat.get("offsets", []), dtype=np.float64)

    n_frames = len(audio) // CHUNK_SIZE

    return {
        "sr": sr,
        "db_smooth": db_smooth,
        "n_frames": n_frames,
        "gt_onsets_ms": gt_onsets_ms,
        "gt_offsets_ms": gt_offsets_ms,
        "wav_path": wav_path,
    }


def segment_with_threshold(db_smooth, sr, threshold):
    """Run evfuncs thresholding on precomputed dB signal."""
    onsets_s, offsets_s = evfuncs.segment_song(
        db_smooth, sr, threshold,
        EVFUNCS_PARAMS["min_syl_dur"],
        EVFUNCS_PARAMS["min_silent_dur"],
    )
    if onsets_s is None or offsets_s is None:
        return np.array([]), np.array([])
    return onsets_s * 1000, offsets_s * 1000  # to ms


def onsets_offsets_to_frames(onsets_ms, offsets_ms, n_frames, sr):
    """Convert onset/offset times (ms) to binary frame-level labels."""
    labels = np.zeros(n_frames, dtype=int)
    for on, off in zip(onsets_ms, offsets_ms):
        on_sample = int(on * sr / 1000)
        off_sample = int(off * sr / 1000)
        on_frame = on_sample // CHUNK_SIZE
        off_frame = off_sample // CHUNK_SIZE
        labels[max(0, on_frame):min(n_frames, off_frame + 1)] = 1
    return labels


# ── Threshold grid search ──────────────────────────────────────────

def _get_threshold_range(precomputed_files):
    """Determine search range from actual dB values."""
    all_min = [fd["db_smooth"].min() for fd in precomputed_files]
    all_max = [fd["db_smooth"].max() for fd in precomputed_files]
    db_min = float(np.floor(np.min(all_min)))
    db_max = float(np.ceil(np.max(all_max)))
    return np.arange(db_min - BASELINE_GRID_MARGIN_DB,
                     db_max + BASELINE_GRID_MARGIN_DB,
                     BASELINE_GRID_STEP_DB)


def find_best_threshold(precomputed_files):
    """Grid-search for best dB threshold (maximize collar@10ms F1 on val).

    Returns (best_threshold, best_f1, grid_results_list).
    """
    collar_frames_10 = collar_ms_to_frames(10, CHUNK_SIZE, SAMPLE_RATE)
    threshold_range = _get_threshold_range(precomputed_files)
    log.info("Threshold search: %.1f to %.1f dB, step=%.1f (%d values)",
             threshold_range[0], threshold_range[-1],
             BASELINE_GRID_STEP_DB, len(threshold_range))

    best_threshold = -50.0
    best_f1 = -1.0
    grid_results = []

    for thresh in threshold_range:
        total_tp, total_true, total_pred = 0, 0, 0

        for fd in precomputed_files:
            pred_on_ms, pred_off_ms = segment_with_threshold(
                fd["db_smooth"], fd["sr"], thresh)
            pred_frames = onsets_offsets_to_frames(
                pred_on_ms, pred_off_ms, fd["n_frames"], fd["sr"])
            gt_frames = onsets_offsets_to_frames(
                fd["gt_onsets_ms"], fd["gt_offsets_ms"], fd["n_frames"], fd["sr"])
            cm = collar_segmentation_metrics(gt_frames, pred_frames, collar_frames_10)
            total_tp += cm["tp"]
            total_true += cm["n_true"]
            total_pred += cm["n_pred"]

        p = total_tp / total_pred if total_pred > 0 else 0
        r = total_tp / total_true if total_true > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        grid_results.append({
            "threshold_db": float(thresh),
            "collar_10ms_precision": float(p),
            "collar_10ms_recall": float(r),
            "collar_10ms_f1": float(f1),
            "tp": int(total_tp),
            "n_true": int(total_true),
            "n_pred": int(total_pred),
        })

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(thresh)

    # Edge warning
    best_idx = next(i for i, g in enumerate(grid_results)
                    if g["threshold_db"] == best_threshold)
    if best_idx <= 1:
        log.warning("EDGE: best threshold %.1f dB is at the LOWER edge of "
                    "range [%.1f, %.1f]. Optimum may lie outside!",
                    best_threshold, threshold_range[0], threshold_range[-1])
    elif best_idx >= len(grid_results) - 2:
        log.warning("EDGE: best threshold %.1f dB is at the UPPER edge of "
                    "range [%.1f, %.1f]. Optimum may lie outside!",
                    best_threshold, threshold_range[0], threshold_range[-1])

    return best_threshold, best_f1, grid_results


# ── Evaluation (all metrics, matching train_seg.py) ─────────────────

def _apply_sliding_window_per_file(all_true_per_file, all_pred_per_file, sw_params):
    """Apply sliding window independently per file, then concatenate."""
    smoothed_all = []
    n_segs = 0
    for pred_frames in all_pred_per_file:
        sm, ns = apply_sliding_window(pred_frames.tolist(), **sw_params)
        smoothed_all.extend(sm)
        n_segs += ns
    return smoothed_all, n_segs


def evaluate_baseline(precomputed_files, threshold):
    """Evaluate on test files with all metrics. Returns (results, per_file_results)."""
    all_true_per_file = []
    all_pred_per_file = []
    per_file_results = []

    for fd in precomputed_files:
        pred_on_ms, pred_off_ms = segment_with_threshold(
            fd["db_smooth"], fd["sr"], threshold)
        pred_frames = onsets_offsets_to_frames(
            pred_on_ms, pred_off_ms, fd["n_frames"], fd["sr"])
        gt_frames = onsets_offsets_to_frames(
            fd["gt_onsets_ms"], fd["gt_offsets_ms"], fd["n_frames"], fd["sr"])
        all_true_per_file.append(gt_frames)
        all_pred_per_file.append(pred_frames)

        # Per-file metrics
        fw_file = framewise_metrics(gt_frames, pred_frames)
        c10_cf = collar_ms_to_frames(10, CHUNK_SIZE, SAMPLE_RATE)
        c10_file = collar_segmentation_metrics(gt_frames, pred_frames, c10_cf)
        oc10_file = onset_collar_segmentation_metrics(gt_frames, pred_frames, c10_cf)
        per_file_results.append({
            "wav_file": os.path.basename(fd["wav_path"]),
            "n_frames": int(fd["n_frames"]),
            "n_gt_segments": int(c10_file["n_true"]),
            "n_pred_segments": int(c10_file["n_pred"]),
            "framewise_precision": float(fw_file["precision"]),
            "framewise_recall": float(fw_file["recall"]),
            "framewise_f1": float(fw_file["f1"]),
            "collar_10ms_f1": float(c10_file["f1"]),
            "collar_10ms_precision": float(c10_file["precision"]),
            "collar_10ms_recall": float(c10_file["recall"]),
            "onset_collar_10ms_f1": float(oc10_file["f1"]),
            "onset_collar_10ms_precision": float(oc10_file["precision"]),
            "onset_collar_10ms_recall": float(oc10_file["recall"]),
        })

    # Concatenate for aggregate metrics
    y_true = np.concatenate(all_true_per_file).tolist()
    y_pred = np.concatenate(all_pred_per_file).tolist()

    # Raw metrics
    fw = framewise_metrics(y_true, y_pred)
    collar_raw, onset_raw, offset_raw = {}, {}, {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, CHUNK_SIZE, SAMPLE_RATE)
        tag = f"@{cms}ms"
        collar_raw[tag] = collar_segmentation_metrics(y_true, y_pred, cf)
        onset_raw[tag] = onset_collar_segmentation_metrics(y_true, y_pred, cf)
        offset_raw[tag] = offset_collar_segmentation_metrics(y_true, y_pred, cf)

    # Sliding window (per-file, matching train_seg.py)
    sw = SLIDING_WINDOW_PARAMS
    smoothed_preds, n_pred_seg = _apply_sliding_window_per_file(
        all_true_per_file, all_pred_per_file, sw)

    fw_sw = framewise_metrics(y_true, smoothed_preds)
    collar_sw, onset_sw, offset_sw = {}, {}, {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, CHUNK_SIZE, SAMPLE_RATE)
        tag = f"@{cms}ms"
        collar_sw[tag] = collar_segmentation_metrics(y_true, smoothed_preds, cf)
        onset_sw[tag] = onset_collar_segmentation_metrics(y_true, smoothed_preds, cf)
        offset_sw[tag] = offset_collar_segmentation_metrics(y_true, smoothed_preds, cf)

    def _count_seg(labels):
        arr = np.asarray(labels)
        n = int(np.sum(np.diff(arr) == 1))
        if len(arr) > 0 and arr[0] == 1:
            n += 1
        return n

    results = {
        "framewise": fw,
        "framewise_smoothed": fw_sw,
        "collar": collar_raw,
        "collar_smoothed": collar_sw,
        "onset_collar": onset_raw,
        "onset_collar_smoothed": onset_sw,
        "offset_collar": offset_raw,
        "offset_collar_smoothed": offset_sw,
        "sliding_window_params": sw,
        "n_true_segments_smoothed": _count_seg(y_true),
        "n_pred_segments_smoothed": n_pred_seg,
    }

    return results, per_file_results


def _log_metrics(metrics):
    fw = metrics["framewise"]
    fw_sw = metrics["framewise_smoothed"]
    log.info("Framewise (raw) P=%.4f  R=%.4f  F1=%.4f",
             fw["precision"], fw["recall"], fw["f1"])
    log.info("Framewise (sw)  P=%.4f  R=%.4f  F1=%.4f",
             fw_sw["precision"], fw_sw["recall"], fw_sw["f1"])
    for cms in COLLAR_VALUES_MS:
        tag = f"@{cms}ms"
        cr = metrics["collar"][tag]
        cs = metrics["collar_smoothed"][tag]
        osr = metrics["onset_collar"][tag]
        oss = metrics["onset_collar_smoothed"][tag]
        log.info("Collar(raw)  %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, cr["precision"], cr["recall"], cr["f1"])
        log.info("Collar(sw)   %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, cs["precision"], cs["recall"], cs["f1"])
        log.info("OnsetCol(raw) %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, osr["precision"], osr["recall"], osr["f1"])
        log.info("OnsetCol(sw)  %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, oss["precision"], oss["recall"], oss["f1"])


# ── Main entry point ───────────────────────────────────────────────

def run_baseline(bird, seed):
    """Run energy-based baseline for one bird/seed, same split as train_seg.py."""
    bird_cfg = BIRDS[bird]
    raw_dir = bird_cfg["raw_data_dir"]
    run_dir = os.path.join(OUTPUT_DIR, bird, "seg_baseline", f"seed_{seed}")
    os.makedirs(run_dir, exist_ok=True)

    log.info("== BASELINE %s  seed=%d ==", bird, seed)
    log.info("Raw data: %s", raw_dir)

    # ── Get WAV files (same ordering as train_seg.py / create_dataset.py) ─
    file_paths = get_wav_files(raw_dir)
    file_indices = np.arange(len(file_paths))
    log.info("Found %d annotated WAV files", len(file_paths))

    # ── Replicate the same file-based split as train_seg.py ─────────
    if len(file_indices) < 7:
        raise RuntimeError(
            f"Bird {bird} has only {len(file_indices)} files — need >=7 for "
            f"file-based split. Energy baseline not supported.")

    tr_files, tmp = train_test_split(file_indices, test_size=0.3, random_state=seed)
    va_files, te_files = train_test_split(tmp, test_size=0.5, random_state=seed)

    val_indices = sorted(va_files.tolist())
    test_indices = sorted(te_files.tolist())
    log.info("Split: %d train, %d val, %d test files",
             len(tr_files), len(val_indices), len(test_indices))

    # ── Precompute smoothed audio ───────────────────────────────────
    log.info("Precomputing smoothed audio for val files (%d)...", len(val_indices))
    val_precomputed = [precompute_file(file_paths[i]) for i in val_indices]

    log.info("Precomputing smoothed audio for test files (%d)...", len(test_indices))
    test_precomputed = [precompute_file(file_paths[i]) for i in test_indices]

    # ── Grid-search threshold on val set ────────────────────────────
    best_threshold, val_f1, grid_results = find_best_threshold(val_precomputed)
    log.info("Best threshold: %.1f dB (val collar@10ms F1: %.4f)",
             best_threshold, val_f1)

    # Save grid search
    grid_path = os.path.join(run_dir, "grid_search.json")
    with open(grid_path, "w") as f:
        json.dump({
            "best_threshold_db": best_threshold,
            "best_val_f1": val_f1,
            "grid_step_db": BASELINE_GRID_STEP_DB,
            "grid_margin_db": BASELINE_GRID_MARGIN_DB,
            "n_thresholds": len(grid_results),
            "results": grid_results,
        }, f, indent=2)
    log.info("Grid search saved: %s", grid_path)

    # ── Evaluate on test set ────────────────────────────────────────
    metrics, per_file_results = evaluate_baseline(test_precomputed, best_threshold)
    _log_metrics(metrics)

    # ── Save results ────────────────────────────────────────────────
    fw = metrics["framewise"]
    test_accuracy = (fw["tp"] + fw["tn"]) / fw["n_total"] if fw["n_total"] > 0 else 0.0
    results = {
        "bird": bird,
        "seed": seed,
        "test_accuracy": float(test_accuracy),
        "threshold_db": best_threshold,
        "val_collar_10ms_f1": val_f1,
        "n_total_files": len(file_paths),
        "n_train_files": len(tr_files),
        "n_val_files": len(val_indices),
        "n_test_files": len(test_indices),
        "val_file_indices": val_indices,
        "test_file_indices": test_indices,
        "test_files": [os.path.basename(file_paths[i]) for i in test_indices],
        "chunk_size": CHUNK_SIZE,
        "sample_rate": SAMPLE_RATE,
        "evfuncs_params": {k: list(v) if isinstance(v, tuple) else v
                           for k, v in EVFUNCS_PARAMS.items()},
        "grid_step_db": BASELINE_GRID_STEP_DB,
        "grid_margin_db": BASELINE_GRID_MARGIN_DB,
        **metrics,
    }
    results_path = os.path.join(run_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results saved: %s", results_path)

    # Save per-file results
    per_file_path = os.path.join(run_dir, "per_file_results.json")
    with open(per_file_path, "w") as f:
        json.dump(per_file_results, f, indent=2)
    log.info("Per-file results saved: %s", per_file_path)

    return results


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Energy-based segmentation baseline (final_experiments)")
    parser.add_argument("--bird", default=None, choices=list(BIRDS.keys()),
                        help="Single bird (default: all)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Single seed (default: all replicate seeds)")
    parser.add_argument("--force", action="store_true",
                        help="Re-run even if results already exist")
    args = parser.parse_args()

    birds = [args.bird] if args.bird else list(BIRDS.keys())
    seeds = [args.seed] if args.seed else REPLICATE_SEEDS

    for bird in birds:
        for seed in seeds:
            result_path = os.path.join(
                OUTPUT_DIR, bird, "seg_baseline", f"seed_{seed}", "results.json")
            if not args.force and os.path.exists(result_path):
                try:
                    with open(result_path) as f:
                        existing = json.load(f)
                    if "framewise" in existing:
                        log.info("Skip baseline %s seed=%d (already complete)",
                                 bird, seed)
                        continue
                except Exception:
                    pass
            run_baseline(bird, seed)


if __name__ == "__main__":
    main()
