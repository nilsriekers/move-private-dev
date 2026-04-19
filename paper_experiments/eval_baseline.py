#!/usr/bin/env python3
"""Energy-based segmentation baseline evaluation.

Uses the same val/test split as the neural net (from the PKL file indices)
and reports the same metrics: framewise P/R/F1, collar @5/10/15/20ms
(raw + sliding window), onset collar @5/10/15/20ms (raw + sliding window).

Pipeline: raw audio → evfuncs.smooth_data() → decibel() → evfuncs.segment_song()
Grid-searches optimal dB threshold on the val set (maximize collar@10ms F1).

Usage
-----
    python -m paper_experiments.eval_baseline --bird ye04gr05 --seed 42
    python -m paper_experiments.eval_baseline  # all birds, all seeds
"""
import argparse
import json
import logging
import os
import pickle
import sys

import evfuncs
import numpy as np
from scipy.io import wavfile
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from moove.utils.audio_utils import decibel
from paper_experiments.config import (
    BIRDS, COLLAR_VALUES_MS, EVFUNCS_PARAMS, OUTPUT_DIR,
    RAW_DATA_DIRS, REPLICATE_SEEDS, SAMPLE_RATE, SLIDING_WINDOW_PARAMS,
    TRAINING_DATA_DIR,
)
from paper_experiments.metrics import (
    apply_sliding_window, collar_ms_to_frames,
    collar_segmentation_metrics, framewise_metrics,
    onset_collar_segmentation_metrics,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

CHUNK_SIZE = 64


# ── File discovery (same ordering as create_dataset.py) ─────────────

def get_annotated_wav_files(data_dir):
    """Return sorted WAV paths that have a paired .not.mat."""
    paths = []
    root = os.path.expanduser(data_dir)
    for dirpath, _, filenames in os.walk(root):
        for fname in sorted(filenames):
            if fname.endswith(".wav"):
                fpath = os.path.join(dirpath, fname)
                if os.path.exists(fpath + ".not.mat"):
                    paths.append(fpath)
    return sorted(paths)


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
    return onsets_s * 1000, offsets_s * 1000


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

GRID_STEP_DB = 0.5  # dB step size for threshold grid search
GRID_MARGIN_DB = 20  # margin beyond observed dB range


def _get_threshold_range(precomputed_files):
    """Determine search range from actual dB values."""
    all_min, all_max = [], []
    for fd in precomputed_files:
        all_min.append(fd["db_smooth"].min())
        all_max.append(fd["db_smooth"].max())
    db_min = float(np.floor(np.min(all_min)))  # use min, not median
    db_max = float(np.ceil(np.max(all_max)))    # use max, not median
    return np.arange(db_min - GRID_MARGIN_DB, db_max + GRID_MARGIN_DB, GRID_STEP_DB)


def find_best_threshold(precomputed_files):
    """Grid-search for best dB threshold (maximize collar@10ms F1 on val).

    Returns (best_threshold, best_f1, grid_results_list).
    grid_results_list contains one dict per threshold with all metrics.
    """
    collar_frames_10 = collar_ms_to_frames(10, CHUNK_SIZE, SAMPLE_RATE)
    threshold_range = _get_threshold_range(precomputed_files)
    log.info("Threshold search: %.1f to %.1f dB, step=%.1f (%d values)",
             threshold_range[0], threshold_range[-1], GRID_STEP_DB,
             len(threshold_range))

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

    # ── Edge warning ────────────────────────────────────────────────
    best_idx = next(i for i, g in enumerate(grid_results)
                    if g["threshold_db"] == best_threshold)
    if best_idx <= 1:
        log.warning("EDGE: best threshold %.1f dB is at the LOWER edge of "
                    "search range [%.1f, %.1f]. Optimum may lie outside!",
                    best_threshold, threshold_range[0], threshold_range[-1])
    elif best_idx >= len(grid_results) - 2:
        log.warning("EDGE: best threshold %.1f dB is at the UPPER edge of "
                    "search range [%.1f, %.1f]. Optimum may lie outside!",
                    best_threshold, threshold_range[0], threshold_range[-1])

    return best_threshold, best_f1, grid_results


# ── Evaluation (all metrics) ────────────────────────────────────────

def evaluate_baseline(precomputed_files, threshold):
    """Evaluate energy baseline on test files with all metrics.

    Returns (results_dict, per_file_results_list).
    """
    all_true, all_pred = [], []
    per_file_results = []

    for i, fd in enumerate(precomputed_files):
        pred_on_ms, pred_off_ms = segment_with_threshold(
            fd["db_smooth"], fd["sr"], threshold)
        pred_frames = onsets_offsets_to_frames(
            pred_on_ms, pred_off_ms, fd["n_frames"], fd["sr"])
        gt_frames = onsets_offsets_to_frames(
            fd["gt_onsets_ms"], fd["gt_offsets_ms"], fd["n_frames"], fd["sr"])
        all_true.append(gt_frames)
        all_pred.append(pred_frames)

        # Per-file metrics
        fw_file = framewise_metrics(gt_frames, pred_frames)
        collar_10_cf = collar_ms_to_frames(10, CHUNK_SIZE, SAMPLE_RATE)
        collar_10_file = collar_segmentation_metrics(gt_frames, pred_frames, collar_10_cf)
        per_file_results.append({
            "file_index": fd.get("file_index", i),
            "n_frames": int(fd["n_frames"]),
            "n_true_segments": int(collar_10_file["n_true"]),
            "n_pred_segments": int(collar_10_file["n_pred"]),
            "framewise_f1": float(fw_file["f1"]),
            "framewise_precision": float(fw_file["precision"]),
            "framewise_recall": float(fw_file["recall"]),
            "collar_10ms_f1": float(collar_10_file["f1"]),
            "collar_10ms_precision": float(collar_10_file["precision"]),
            "collar_10ms_recall": float(collar_10_file["recall"]),
            "n_pred_onsets_ms": len(pred_on_ms),
            "n_gt_onsets_ms": len(fd["gt_onsets_ms"]),
        })

    y_true = np.concatenate(all_true).tolist()
    y_pred = np.concatenate(all_pred).tolist()

    # Framewise (raw)
    fw = framewise_metrics(y_true, y_pred)
    log.info("Framewise  P=%.4f  R=%.4f  F1=%.4f", fw["precision"], fw["recall"], fw["f1"])

    # Collar (raw)
    collar_results = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, CHUNK_SIZE, SAMPLE_RATE)
        cm = collar_segmentation_metrics(y_true, y_pred, cf)
        collar_results[f"@{cms}ms"] = cm
        log.info("Collar(raw)  %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, cm["precision"], cm["recall"], cm["f1"])

    # Onset collar (raw)
    onset_collar_raw = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, CHUNK_SIZE, SAMPLE_RATE)
        cm = onset_collar_segmentation_metrics(y_true, y_pred, cf)
        onset_collar_raw[f"@{cms}ms"] = cm
        log.info("OnsetCol(raw) %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, cm["precision"], cm["recall"], cm["f1"])

    # Sliding window post-processing
    sw = SLIDING_WINDOW_PARAMS
    smoothed_preds, n_pred_segments = apply_sliding_window(y_pred, **sw)

    def _count_segments(labels):
        arr = np.asarray(labels)
        changes = np.diff(arr)
        n = int(np.sum(changes == 1))
        if len(arr) > 0 and arr[0] == 1:
            n += 1
        return n

    n_true_segments = _count_segments(y_true)

    # Framewise (smoothed)
    fw_smoothed = framewise_metrics(y_true, smoothed_preds)
    log.info("Framewise(sw)  P=%.4f  R=%.4f  F1=%.4f",
             fw_smoothed["precision"], fw_smoothed["recall"], fw_smoothed["f1"])

    # Collar (smoothed)
    collar_smoothed = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, CHUNK_SIZE, SAMPLE_RATE)
        cm = collar_segmentation_metrics(y_true, smoothed_preds, cf)
        collar_smoothed[f"@{cms}ms"] = cm
        log.info("Collar(sw)   %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, cm["precision"], cm["recall"], cm["f1"])

    # Onset collar (smoothed)
    onset_collar_smoothed = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, CHUNK_SIZE, SAMPLE_RATE)
        cm = onset_collar_segmentation_metrics(y_true, smoothed_preds, cf)
        onset_collar_smoothed[f"@{cms}ms"] = cm
        log.info("OnsetCol(sw)  %2dms  P=%.4f  R=%.4f  F1=%.4f",
                 cms, cm["precision"], cm["recall"], cm["f1"])

    return {
        "framewise": fw,
        "collar": collar_results,
        "onset_collar": onset_collar_raw,
        "sliding_window_params": sw,
        "framewise_smoothed": fw_smoothed,
        "collar_smoothed": collar_smoothed,
        "onset_collar_smoothed": onset_collar_smoothed,
        "n_pred_segments_smoothed": n_pred_segments,
        "n_true_segments": n_true_segments,
    }, per_file_results


# ── Main entry point ───────────────────────────────────────────────

def run_baseline(bird, seed):
    """Run energy-based baseline for one bird/seed, using the same split as the neural net."""
    bird_cfg = BIRDS[bird]
    dataset_path = os.path.join(TRAINING_DATA_DIR, bird_cfg["seg_dataset"])
    raw_data_dir = RAW_DATA_DIRS[bird]

    run_dir = os.path.join(OUTPUT_DIR, "baseline", bird, f"seed_{seed}")
    os.makedirs(run_dir, exist_ok=True)

    log.info("== BASELINE %s  seed=%d ==", bird, seed)

    # ── Load PKL to get file indices and replicate the split ────────
    with open(dataset_path, "rb") as f:
        data_dict = pickle.load(f)

    features = np.array(data_dict["features"])
    file_indices = np.unique(features[:, 0])
    n_pkl_files = len(file_indices)

    # ── Find raw WAV files (same ordering as create_dataset.py) ─────
    wav_files = get_annotated_wav_files(raw_data_dir)
    n_wav_files = len(wav_files)

    if n_wav_files != n_pkl_files:
        raise RuntimeError(
            f"File count mismatch for {bird}: PKL has {n_pkl_files} file indices, "
            f"but found {n_wav_files} annotated WAVs in {raw_data_dir}. "
            f"Cannot establish file index → WAV mapping."
        )

    log.info("Files: %d WAVs matched to %d PKL file indices", n_wav_files, n_pkl_files)

    # ── Replicate the same train/val/test split ─────────────────────
    if len(file_indices) >= 7:
        train_files, temp_files = train_test_split(
            file_indices, test_size=0.3, random_state=seed)
        val_files, test_files = train_test_split(
            temp_files, test_size=0.5, random_state=seed)
    else:
        raise RuntimeError(
            f"Bird {bird} has only {len(file_indices)} files — file-based split "
            f"requires ≥7. Energy baseline not supported for row-based splits."
        )

    val_indices = sorted([int(i) for i in val_files])
    test_indices = sorted([int(i) for i in test_files])
    log.info("Val files: %s", val_indices)
    log.info("Test files: %s", test_indices)

    # ── Precompute smoothed audio for val + test files ──────────────
    log.info("Precomputing smoothed audio for val files...")
    val_precomputed = []
    for idx in val_indices:
        fd = precompute_file(wav_files[idx])
        fd["file_index"] = idx
        val_precomputed.append(fd)

    log.info("Precomputing smoothed audio for test files...")
    test_precomputed = []
    for idx in test_indices:
        fd = precompute_file(wav_files[idx])
        fd["file_index"] = idx
        test_precomputed.append(fd)

    # ── Grid-search threshold on val set ────────────────────────────
    best_threshold, val_f1, grid_results = find_best_threshold(val_precomputed)
    log.info("Best threshold: %.1f dB (val collar@10ms F1: %.4f)", best_threshold, val_f1)

    # ── Save grid search results ────────────────────────────────────
    grid_path = os.path.join(run_dir, "grid_search.json")
    with open(grid_path, "w") as f:
        json.dump({
            "best_threshold_db": best_threshold,
            "best_val_f1": val_f1,
            "grid_step_db": GRID_STEP_DB,
            "grid_margin_db": GRID_MARGIN_DB,
            "n_thresholds": len(grid_results),
            "results": grid_results,
        }, f, indent=2)
    log.info("Grid search saved: %s", grid_path)

    # ── Evaluate on test set ────────────────────────────────────────
    results, per_file_results = evaluate_baseline(test_precomputed, best_threshold)
    results["bird"] = bird
    results["seed"] = seed
    results["threshold_db"] = best_threshold
    results["val_collar_10ms_f1"] = val_f1
    results["n_val_files"] = len(val_indices)
    results["n_test_files"] = len(test_indices)
    results["val_file_indices"] = val_indices
    results["test_file_indices"] = test_indices
    results["chunk_size"] = CHUNK_SIZE
    results["sample_rate"] = SAMPLE_RATE
    results["evfuncs_params"] = {k: v if not isinstance(v, tuple) else list(v)
                                 for k, v in EVFUNCS_PARAMS.items()}
    results["grid_step_db"] = GRID_STEP_DB
    results["grid_margin_db"] = GRID_MARGIN_DB

    results_path = os.path.join(run_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results saved: %s", results_path)

    # ── Save per-file results ───────────────────────────────────────
    # Add WAV filenames for traceability
    for pfr in per_file_results:
        pfr["wav_file"] = os.path.basename(wav_files[pfr["file_index"]])
    per_file_path = os.path.join(run_dir, "per_file_results.json")
    with open(per_file_path, "w") as f:
        json.dump(per_file_results, f, indent=2)
    log.info("Per-file results saved: %s", per_file_path)

    return results


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Energy-based segmentation baseline evaluation")
    parser.add_argument("--bird", default=None, choices=list(BIRDS.keys()),
                        help="Single bird (default: all birds)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Single seed (default: all replicate seeds)")
    args = parser.parse_args()

    birds = [args.bird] if args.bird else list(BIRDS.keys())
    seeds = [args.seed] if args.seed else REPLICATE_SEEDS[:3]

    for bird in birds:
        for seed in seeds:
            result_path = os.path.join(
                OUTPUT_DIR, "baseline", bird, f"seed_{seed}", "results.json")
            if os.path.exists(result_path):
                try:
                    with open(result_path) as f:
                        existing = json.load(f)
                    if "framewise" in existing:
                        log.info("Skip baseline %s seed=%d (already complete)", bird, seed)
                        continue
                except Exception:
                    pass
            run_baseline(bird, seed)


if __name__ == "__main__":
    main()
