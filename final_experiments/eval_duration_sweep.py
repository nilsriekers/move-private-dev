#!/usr/bin/env python3
"""Evaluate accuracy vs. input duration for all birds × all seeds.

For each bird and seed, rebuilds the exact same test split as train_class.py,
then evaluates the trained model on spectrograms truncated (then zero-padded)
to simulate shorter input windows from 5.8 ms up to 49.3 ms.

READS:   final_experiments/results/{bird}/class/seed_{N}/{bird}_class_seed{N}.pth
         raw WAV + .not.mat data at the paths in config.BIRDS
WRITES:  final_experiments/results_duration_sweep/{bird}/seed_{N}/duration_sweep.json

Nothing in final_experiments/results/ is modified.

Usage
-----
  uv run python3 final_experiments/eval_duration_sweep.py
  uv run python3 final_experiments/eval_duration_sweep.py --bird ye00pu07
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from scipy.signal import spectrogram as scipy_spectrogram
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from final_experiments.config import BIRDS, CLASS_DATASET_PARAMS, OUTPUT_DIR, REPLICATE_SEEDS
from final_experiments.create_dataset import get_wav_files, _load_wav, seconds_to_index
from moove.models.CNN import CNN

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────
# Same input lengths as original Bird-1-only analysis for comparability
INPUT_LENGTHS = [4, 7, 10, 14, 17, 21, 24, 28, 31, 34]
FULL_INPUT_LENGTH = 21          # model was trained with this
CHUNK_SIZE  = CLASS_DATASET_PARAMS["chunk_size"]    # 64
SAMPLE_RATE = 44100
NPERSEG     = CLASS_DATASET_PARAMS["nperseg"]       # 64
NOVERLAP    = CLASS_DATASET_PARAMS["noverlap"]      # 32
NFFT        = CLASS_DATASET_PARAMS["nfft"]          # 128
FREQ_CUTOFFS = CLASS_DATASET_PARAMS["freq_cutoffs"] # (0, 22050)

OUT_DIR = Path(OUTPUT_DIR).parent / "results_duration_sweep"

# Safety: this script must never write into the main results directory
_PROTECTED_DIR = Path(OUTPUT_DIR).resolve()


def _assert_safe_output(path: Path):
    """Raise immediately if path would land inside the protected results dir."""
    if path.resolve().is_relative_to(_PROTECTED_DIR):
        raise RuntimeError(
            f"SAFETY ABORT: attempted write inside protected directory "
            f"{_PROTECTED_DIR}\n  target: {path}"
        )

# Full model input shape (matches FULL_INPUT_LENGTH=21 after F.pad)
FULL_N_TIME = (FULL_INPUT_LENGTH * CHUNK_SIZE - NPERSEG) // (NPERSEG - NOVERLAP) + 1  # = 41
FULL_N_TIME_PAD = FULL_N_TIME + 1  # = 42 (after F.pad adds 1 col)


def duration_ms(input_length: int) -> float:
    return input_length * CHUNK_SIZE / SAMPLE_RATE * 1000


def n_time_bins(input_length: int) -> int:
    """Number of spectrogram time bins for input_length chunks (before F.pad)."""
    total = input_length * CHUNK_SIZE
    if total < NPERSEG:
        return 0
    return (total - NPERSEG) // (NPERSEG - NOVERLAP) + 1


def build_test_set(bird_id: str, seed: int):
    """Rebuild the exact test set used in training (file-level split, same seed).

    Returns (test_spectrograms_full, test_labels, label_to_int, int_to_label)
    where test_spectrograms_full has input_length=FULL_INPUT_LENGTH.
    """
    bird_cfg = BIRDS[bird_id]
    raw_dir  = bird_cfg["raw_data_dir"]
    exclude  = set(bird_cfg.get("exclude_labels") or [])
    merge    = dict(bird_cfg.get("merge_labels") or {})

    wav_files   = get_wav_files(raw_dir)
    import evfuncs

    # ── Read all syllables (same as train_class.py) ───────────────────
    input_array_size = FULL_INPUT_LENGTH * CHUNK_SIZE
    rows = []
    for fpath in wav_files:
        try:
            rate, rawsong = _load_wav(fpath)
        except Exception as e:
            log.warning("Skipped %s: %s", fpath, e)
            continue

        notmat     = evfuncs.load_notmat(fpath + ".not.mat")
        onsets_ms  = np.array(notmat.get("onsets", []))
        labels_str = notmat.get("labels", "")
        fname      = os.path.basename(fpath)
        n_usable   = min(len(onsets_ms), len(labels_str))

        for syl_no in range(n_usable):
            lbl = labels_str[syl_no]
            lbl = merge.get(lbl, lbl)
            if lbl in exclude:
                continue

            onset_idx = seconds_to_index(onsets_ms[syl_no], rate)
            clip      = rawsong[onset_idx: onset_idx + input_array_size]

            f, t, Sxx = scipy_spectrogram(clip, fs=rate, nperseg=NPERSEG,
                                          noverlap=NOVERLAP, nfft=NFFT)
            Sxx = Sxx[(f >= FREQ_CUTOFFS[0]) & (f <= FREQ_CUTOFFS[1]), :]
            if Sxx.ndim != 2:
                continue

            rows.append({"file": fname, "spec": Sxx, "label": lbl})

    if not rows:
        raise RuntimeError(f"No usable syllables for {bird_id}")

    import pandas as pd
    df = pd.DataFrame(rows)

    unique_labels = sorted(df["label"].unique())
    label_to_int  = {l: i for i, l in enumerate(unique_labels)}
    int_to_label  = {i: l for l, i in label_to_int.items()}

    # ── Reproduce file-level split (identical to train_class.py) ─────
    filenames = list(df.groupby("file").groups.keys())
    if len(filenames) >= 7:
        tr_f, tmp_f = train_test_split(filenames, test_size=0.3, random_state=seed)
        va_f, te_f  = train_test_split(tmp_f,      test_size=0.5, random_state=seed)
        te_df = df[df["file"].isin(te_f)]
    else:
        # fall back to stratified split on items
        all_specs  = df["spec"].tolist()
        all_labels = [label_to_int[l] for l in df["label"].tolist()]
        _, tmp_s, _, tmp_l = train_test_split(
            all_specs, all_labels, test_size=0.3, stratify=all_labels, random_state=seed)
        _, te_specs, _, te_labels_int = train_test_split(
            tmp_s, tmp_l, test_size=0.5, stratify=tmp_l, random_state=seed)
        # Wrap as list for uniform handling below
        return te_specs, te_labels_int, label_to_int, int_to_label

    te_specs  = te_df["spec"].tolist()
    te_labels = [label_to_int[l] for l in te_df["label"].tolist()]

    # Shuffle (same as training pipeline)
    te_specs, te_labels = shuffle(te_specs, te_labels, random_state=seed)

    return te_specs, te_labels, label_to_int, int_to_label


def specs_to_tensors(specs_raw, n_time_cols_keep: int) -> torch.Tensor:
    """Convert raw numpy spectrograms to padded & normalised model inputs.

    For each spectrogram (n_freq, n_time_full):
      1. Keep only first n_time_cols_keep time columns (simulate shorter input)
      2. Normalise using the kept portion
      3. F.pad by +1 in each dim (as in train_class.py)
      4. Zero-pad time dimension to FULL_N_TIME_PAD (= 42)

    Returns (N, 1, 66, 42) tensor.
    """
    tensors = []
    for spec in specs_raw:
        spec = np.array(spec, dtype=np.float32)
        # Truncate time: keep only the first n_time_cols_keep columns
        n_keep = min(n_time_cols_keep, spec.shape[1])
        trunc  = spec[:, :n_keep].copy()

        # Normalise
        s = trunc.std()
        trunc = (trunc - trunc.mean()) / s if s > 0 else trunc

        # Convert to tensor, add channel dim, F.pad +1 in each dim
        t = torch.tensor(trunc).float().unsqueeze(0)  # (1, n_freq, n_keep)
        t = F.pad(t, (0, 1, 0, 1))                   # (1, n_freq+1, n_keep+1)

        # Zero-pad time to FULL_N_TIME_PAD
        current_t = t.shape[2]
        if current_t < FULL_N_TIME_PAD:
            t = F.pad(t, (0, FULL_N_TIME_PAD - current_t))  # pad on right

        tensors.append(t)

    return torch.stack(tensors)  # (N, 1, 66, 42)


def evaluate_model(model, X: torch.Tensor, labels, device) -> float:
    """Return accuracy on X / labels."""
    model.eval()
    correct, total = 0, 0
    batch_size = 256
    label_t = torch.tensor(labels).long().to(device)
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            xb = X[i: i + batch_size].to(device)
            lb = label_t[i: i + batch_size]
            preds = model(xb).argmax(dim=1)
            correct += (preds == lb).sum().item()
            total   += lb.size(0)
    return correct / total if total > 0 else 0.0


def run_sweep(bird_id: str, seed: int, input_lengths=None):
    log.info("=== %s  seed=%d ===", bird_id, seed)

    # ── Load trained model ─────────────────────────────────────────────
    model_path = Path(OUTPUT_DIR) / bird_id / "class" / f"seed_{seed}" / \
                 f"{bird_id}_class_seed{seed}.pth"
    results_json = Path(OUTPUT_DIR) / bird_id / "class" / f"seed_{seed}" / "results.json"

    if not model_path.exists():
        log.error("Model not found: %s", model_path)
        return None
    with open(results_json) as f:
        meta = json.load(f)
    num_classes = meta["num_classes"]

    # Full input shape that model was trained with
    full_input_shape = (1, FULL_N_TIME + 2, FULL_N_TIME_PAD)  # (1, 66, 42)
    # n_freq: nfft//2+1 = 65, after F.pad: 66
    n_freq_pad = NFFT // 2 + 1 + 1  # = 66
    full_input_shape = (1, n_freq_pad, FULL_N_TIME_PAD)

    device = (torch.device("mps") if torch.backends.mps.is_available()
              else torch.device("cpu"))

    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    # Checkpoint format: {"model": CNN object, "metadata": {...}}
    if isinstance(checkpoint, dict) and "model" in checkpoint:
        model = checkpoint["model"].to(device)
    else:
        # plain state_dict fallback
        model = CNN(input_shape=full_input_shape, num_classes=num_classes).to(device)
        model.load_state_dict(checkpoint)
    model.eval()
    log.info("Loaded model: %s (%d classes)", model_path.name, num_classes)

    # ── Rebuild test set ───────────────────────────────────────────────
    te_specs, te_labels, _, _ = build_test_set(bird_id, seed)
    log.info("Test set: %d syllables", len(te_specs))

    # ── Sweep ──────────────────────────────────────────────────────────
    lengths_to_run = input_lengths if input_lengths is not None else INPUT_LENGTHS
    sweep_results = []
    for L in lengths_to_run:
        n_keep  = n_time_bins(L)  # = 2L-1 raw time bins; F.pad adds +1 inside specs_to_tensors
        dur_ms  = duration_ms(L)
        X       = specs_to_tensors(te_specs, n_keep)
        acc     = evaluate_model(model, X, te_labels, device)
        log.info("  L=%2d  dur=%.1f ms  acc=%.4f", L, dur_ms, acc)
        sweep_results.append({
            "input_length": L,
            "duration_ms": round(dur_ms, 3),
            "n_time_bins_kept": n_keep,
            "test_accuracy": round(acc, 6),
        })

    return sweep_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bird", default=None,
                        help="Run for a single bird (default: all birds)")
    parser.add_argument("--test", action="store_true",
                        help="Smoke-test: 1 seed (42), 3 input lengths, does NOT save output")
    args = parser.parse_args()

    birds = [args.bird] if args.bird else list(BIRDS.keys())
    seeds = [42] if args.test else REPLICATE_SEEDS
    lengths = INPUT_LENGTHS[:3] if args.test else INPUT_LENGTHS  # [4,7,10] for test

    for bird_id in birds:
        for seed in seeds:
            out_path = OUT_DIR / bird_id / f"seed_{seed}" / "duration_sweep.json"

            if not args.test and out_path.exists():
                log.info("Already exists, skipping: %s", out_path)
                continue

            results = run_sweep(bird_id, seed, input_lengths=lengths)
            if results is None:
                continue

            if args.test:
                print(f"\n[TEST — not saved] {bird_id} seed_{seed}:")
                for r in results:
                    print(f"  {r['duration_ms']:.1f} ms → acc={r['test_accuracy']:.4f}")
                continue

            _assert_safe_output(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump({
                    "bird": bird_id,
                    "seed": seed,
                    "full_input_length": FULL_INPUT_LENGTH,
                    "sweep": results,
                }, f, indent=2)
            log.info("Saved: %s", out_path)

    if not args.test:
        print("\n=== DURATION SWEEP SUMMARY ===")
        for bird_id in birds:
            print(f"\n{bird_id}:")
            for seed in REPLICATE_SEEDS:
                out_path = OUT_DIR / bird_id / f"seed_{seed}" / "duration_sweep.json"
                if out_path.exists():
                    d = json.load(open(out_path))
                    vals = [(s["duration_ms"], s["test_accuracy"]) for s in d["sweep"]]
                    print(f"  seed_{seed}: " +
                          "  ".join(f"{dur:.0f}ms→{acc:.3f}" for dur, acc in vals))


if __name__ == "__main__":
    main()
