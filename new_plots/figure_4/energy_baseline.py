#!/usr/bin/env python3
"""Compute energy-based segmentation baseline using evfuncs.

For each bird:
  1. Load all annotated WAV files + .not.mat ground truth
  2. Grid-search optimal dB threshold on 80% tuning set (maximize collar F1@10ms)
  3. Evaluate on 20% eval set
  4. Repeat 3x with different random splits, report mean +/- std

This is an unsupervised method — no train/test split needed,
but we split to avoid overfitting the threshold.

Output: baseline_results.json + console summary.
"""
import json
import os
import sys
from glob import glob

import evfuncs
import numpy as np
import scipy.io.wavfile as wavfile

# Add repo root to path for importing metrics
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, REPO_ROOT)

from paper_experiments.metrics import (
    collar_segmentation_metrics,
    collar_ms_to_frames,
    framewise_metrics,
)

OUTPUT_DIR = SCRIPT_DIR

# ── Bird config ──────────────────────────────────────────────────────
# Map bird ID → directory under ~/.moove/rec_data/ containing annotated WAVs
BIRD_DATA_DIRS = {
    "ye00pu07": os.path.expanduser("~/.moove/rec_data/ye00pu07"),
    "bu04bk04": os.path.expanduser("~/.moove/rec_data/bu04bk04"),
    "gy07bu07": os.path.expanduser("~/.moove/rec_data/gy07bu07"),
    "br08pk08": os.path.expanduser("~/.moove/rec_data/br08pk08"),
    "ye04gr05": os.path.expanduser("~/.moove/rec_data/ye04gr05"),
}
BIRD_LABELS = {
    "ye00pu07": "Bird 1", "bu04bk04": "Bird 2", "gy07bu07": "Bird 3",
    "br08pk08": "Bird 4", "ye04gr05": "Bird 5",
}

# ── evfuncs default parameters (from segment_evfuncs in segment_utils.py) ──
FREQ_CUTOFFS = (500, 10000)
SMOOTH_WINDOW = 2  # ms
MIN_SYL_DUR = 0.03  # s
MIN_SILENT_DUR = 0.005  # s

# ── Grid search range ────────────────────────────────────────────────
# Determined dynamically per bird from actual dB range (see find_best_threshold)

# ── Metrics config ───────────────────────────────────────────────────
CHUNK_SIZE = 64
SAMPLE_RATE = 44100
COLLAR_VALUES_MS = [5, 10, 15, 20]
N_SPLITS = 3
TUNING_FRACTION = 0.8
RANDOM_SEED = 42


def decibel(x, xref=1.0):
    """Convert amplitude to dB (same as moove/utils/audio_utils.py)."""
    x_copy = np.copy(x)
    x_copy[x_copy < 1e-10] = 1e-10
    return 20.0 * np.log10(x_copy / xref)


def find_annotated_wavs(data_dir):
    """Find all WAV files that have a .not.mat annotation file."""
    notmat_files = sorted(glob(os.path.join(data_dir, "**", "*.not.mat"), recursive=True))
    pairs = []
    for nm in notmat_files:
        wav_path = nm.replace(".not.mat", "")
        if os.path.isfile(wav_path):
            pairs.append((wav_path, nm))
    return pairs


def load_file_data(wav_path, notmat_path):
    """Load audio + ground truth onsets/offsets for one file."""
    sr, audio = wavfile.read(wav_path)
    # Pass raw data to evfuncs (same as MooveGUI — no float normalization)
    audio = audio.astype(np.float64)

    notmat = evfuncs.load_notmat(notmat_path)
    onsets_ms = np.array(notmat.get("onsets", []))
    offsets_ms = np.array(notmat.get("offsets", []))

    return sr, audio, onsets_ms, offsets_ms


def precompute_smooth(audio, sr):
    """Precompute smoothed dB signal (expensive bandpass filter — do once per file)."""
    smooth = evfuncs.smooth_data(audio, sr, FREQ_CUTOFFS, SMOOTH_WINDOW)
    return decibel(smooth)


def segment_with_threshold(db_smooth, sr, threshold):
    """Run evfuncs segmentation on precomputed dB signal (cheap — just thresholding)."""
    onsets_s, offsets_s = evfuncs.segment_song(
        db_smooth, sr, threshold, MIN_SYL_DUR, MIN_SILENT_DUR
    )
    if onsets_s is None or offsets_s is None:
        return np.array([]), np.array([])
    return onsets_s * 1000, offsets_s * 1000  # convert to ms


def onsets_offsets_to_frames(onsets_ms, offsets_ms, n_frames, chunk_size, sr):
    """Convert onset/offset times (ms) to binary frame-level labels."""
    labels = np.zeros(n_frames, dtype=int)
    for on, off in zip(onsets_ms, offsets_ms):
        on_sample = int(on * sr / 1000)
        off_sample = int(off * sr / 1000)
        on_frame = on_sample // chunk_size
        off_frame = off_sample // chunk_size
        labels[max(0, on_frame):min(n_frames, off_frame + 1)] = 1
    return labels


def precompute_file_data(file_pairs):
    """Precompute smoothed audio + ground truth for all files (expensive, do once)."""
    precomputed = []
    for wav_path, notmat_path in file_pairs:
        try:
            sr, audio, gt_onsets_ms, gt_offsets_ms = load_file_data(wav_path, notmat_path)
        except Exception:
            continue
        if len(gt_onsets_ms) == 0:
            continue
        db_smooth = precompute_smooth(audio, sr)
        n_frames = len(audio) // CHUNK_SIZE
        gt_frames = onsets_offsets_to_frames(gt_onsets_ms, gt_offsets_ms, n_frames, CHUNK_SIZE, sr)
        precomputed.append({
            "sr": sr, "db_smooth": db_smooth, "n_frames": n_frames,
            "gt_onsets_ms": gt_onsets_ms, "gt_offsets_ms": gt_offsets_ms,
            "gt_frames": gt_frames,
        })
    return precomputed


def evaluate_precomputed(precomputed, threshold):
    """Run energy segmentation on precomputed data and compute metrics."""
    all_true_frames = []
    all_pred_frames = []

    for fd in precomputed:
        pred_onsets_ms, pred_offsets_ms = segment_with_threshold(
            fd["db_smooth"], fd["sr"], threshold)
        pred_frames = onsets_offsets_to_frames(
            pred_onsets_ms, pred_offsets_ms, fd["n_frames"], CHUNK_SIZE, fd["sr"])
        all_true_frames.append(fd["gt_frames"])
        all_pred_frames.append(pred_frames)

    if not all_true_frames:
        return None

    y_true = np.concatenate(all_true_frames)
    y_pred = np.concatenate(all_pred_frames)
    fw = framewise_metrics(y_true, y_pred)

    # Collar metrics
    collar_results = {}
    for cms in COLLAR_VALUES_MS:
        collar_frames = collar_ms_to_frames(cms, CHUNK_SIZE, SAMPLE_RATE)
        total_tp, total_true, total_pred = 0, 0, 0
        for fd in precomputed:
            pred_onsets_ms, pred_offsets_ms = segment_with_threshold(
                fd["db_smooth"], fd["sr"], threshold)
            pred_frames = onsets_offsets_to_frames(
                pred_onsets_ms, pred_offsets_ms, fd["n_frames"], CHUNK_SIZE, fd["sr"])
            cm = collar_segmentation_metrics(fd["gt_frames"], pred_frames, collar_frames)
            total_tp += cm["tp"]
            total_true += cm["n_true"]
            total_pred += cm["n_pred"]

        p = total_tp / total_pred if total_pred > 0 else 0
        r = total_tp / total_true if total_true > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        collar_results[f"@{cms}ms"] = {
            "precision": p, "recall": r, "f1": f1,
            "tp": total_tp, "n_true": total_true, "n_pred": total_pred,
        }

    return {"framewise": fw, "collar": collar_results}


def _get_threshold_range(precomputed):
    """Determine threshold search range from actual dB values in the data."""
    all_min, all_max = [], []
    for fd in precomputed:
        all_min.append(fd["db_smooth"].min())
        all_max.append(fd["db_smooth"].max())
    db_min = int(np.floor(np.median(all_min)))
    db_max = int(np.ceil(np.median(all_max)))
    # Search from well below median min to well above — 1 dB steps
    return np.arange(db_min - 10, db_max + 10, 1)


def find_best_threshold(precomputed):
    """Grid search for best threshold on precomputed tuning data."""
    best_threshold = -50
    best_f1 = -1
    collar_frames = collar_ms_to_frames(10, CHUNK_SIZE, SAMPLE_RATE)
    threshold_range = _get_threshold_range(precomputed)
    print(f"    Threshold search range: {threshold_range[0]} to {threshold_range[-1]} dB ({len(threshold_range)} values)")

    for thresh in threshold_range:
        total_tp, total_true, total_pred = 0, 0, 0

        for fd in precomputed:
            pred_onsets_ms, pred_offsets_ms = segment_with_threshold(
                fd["db_smooth"], fd["sr"], thresh)
            pred_frames = onsets_offsets_to_frames(
                pred_onsets_ms, pred_offsets_ms, fd["n_frames"], CHUNK_SIZE, fd["sr"])
            cm = collar_segmentation_metrics(fd["gt_frames"], pred_frames, collar_frames)
            total_tp += cm["tp"]
            total_true += cm["n_true"]
            total_pred += cm["n_pred"]

        p = total_tp / total_pred if total_pred > 0 else 0
        r = total_tp / total_true if total_true > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = thresh

    return float(best_threshold), float(best_f1)


def run_baseline_for_bird(bird, data_dir):
    """Run full baseline pipeline for one bird."""
    file_pairs = find_annotated_wavs(data_dir)
    if not file_pairs:
        print(f"  No annotated files found for {bird} in {data_dir}")
        return None

    print(f"  Found {len(file_pairs)} annotated files")
    print(f"  Precomputing smoothed audio (this is the slow part, done once)...")
    all_precomputed = precompute_file_data(file_pairs)
    print(f"  Precomputed {len(all_precomputed)} files")

    rng = np.random.RandomState(RANDOM_SEED)
    split_results = []

    for split_i in range(N_SPLITS):
        # Random 80/20 split
        indices = rng.permutation(len(all_precomputed))
        n_tune = int(len(all_precomputed) * TUNING_FRACTION)
        tune_data = [all_precomputed[i] for i in indices[:n_tune]]
        eval_data = [all_precomputed[i] for i in indices[n_tune:]]

        print(f"  Split {split_i + 1}/{N_SPLITS}: "
              f"{len(tune_data)} tuning, {len(eval_data)} eval files")

        # Find best threshold on tuning set
        best_thresh, tune_f1 = find_best_threshold(tune_data)
        print(f"    Best threshold: {best_thresh} dB (tuning collar@10ms F1: {tune_f1:.3f})")

        # Evaluate on eval set
        eval_result = evaluate_precomputed(eval_data, best_thresh)
        if eval_result is None:
            continue

        eval_result["threshold"] = best_thresh
        eval_result["n_tune_files"] = len(tune_data)
        eval_result["n_eval_files"] = len(eval_data)
        split_results.append(eval_result)

        fw = eval_result["framewise"]
        c10 = eval_result["collar"]["@10ms"]
        print(f"    Eval: FW-F1={fw['f1']:.3f}, Collar@10ms F1={c10['f1']:.3f}")

    return split_results


def main():
    print("=== Energy-Based Segmentation Baseline ===\n")

    all_results = {}
    for bird in BIRD_DATA_DIRS:
        data_dir = BIRD_DATA_DIRS[bird]
        label = BIRD_LABELS[bird]
        print(f"\n{label} ({bird}):")

        results = run_baseline_for_bird(bird, data_dir)
        if results:
            all_results[bird] = results

    # Save raw results
    out_path = os.path.join(OUTPUT_DIR, "baseline_results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Summary table
    print("\n=== ENERGY BASELINE SUMMARY ===")
    print(f"{'Bird':<10} {'Label':<8} {'Thresh':<10} "
          f"{'FW-P':<16} {'FW-R':<16} {'FW-F1':<16} "
          f"{'Col@10ms':<16} {'Col@20ms':<16}")
    print("-" * 110)

    for bird in BIRD_DATA_DIRS:
        if bird not in all_results:
            continue
        label = BIRD_LABELS[bird]
        splits = all_results[bird]

        thresholds = [s["threshold"] for s in splits]
        fw_p = [s["framewise"]["precision"] for s in splits]
        fw_r = [s["framewise"]["recall"] for s in splits]
        fw_f1 = [s["framewise"]["f1"] for s in splits]
        c10 = [s["collar"]["@10ms"]["f1"] for s in splits]
        c20 = [s["collar"]["@20ms"]["f1"] for s in splits]

        def ms(vals):
            a = np.array(vals)
            return f"{a.mean():.3f} +/- {a.std():.3f}"

        print(f"{bird:<10} {label:<8} {np.mean(thresholds):<10.0f} "
              f"{ms(fw_p):<16} {ms(fw_r):<16} {ms(fw_f1):<16} "
              f"{ms(c10):<16} {ms(c20):<16}")


if __name__ == "__main__":
    main()
