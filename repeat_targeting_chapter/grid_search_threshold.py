#!/usr/bin/env python3
"""Grid search over segmentation threshold + sliding-window parameters.

Uses seg=42 (overlap) + cls=123 (best combo from seed search).
Precomputes seg probabilities once per file, then sweeps threshold × SW params.
Classification results are cached by (file_idx, onset_frame) so each unique
segment position is classified only once.

Prints top results ranked by repeat-targeting F1.

Usage:
    python3 grid_search_threshold.py
"""

import sys
import itertools
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import torch
from scipy.io import wavfile
from scipy.signal import spectrogram as scipy_spectrogram
import evfuncs
from paper_experiments.metrics import apply_sliding_window
from final_experiments.create_dataset import extract_raw_audio, _concat_windows

DATA_DIR    = Path(__file__).parent / "data_fig7" / "250902"
RESULTS_DIR = REPO_ROOT / "final_experiments/results/gy07bu07"

SEG_SEED = 42
CLS_SEED = 123

TARGET_FILES = [
    "250902_161452", "250902_161219", "250902_143043", "250902_142805",
    "250902_133448", "250902_132156", "250902_131843", "250902_124534",
    "250902_120715", "250902_115940", "250902_115923", "250902_115531",
]

CHUNK_SIZE    = 64
SAMPLE_RATE   = 44100
MS_PER_FRAME  = CHUNK_SIZE / SAMPLE_RATE * 1000
COLLAR_FRAMES = round(10 * SAMPLE_RATE / (CHUNK_SIZE * 1000))

# ── Grid ──────────────────────────────────────────────────────────────────────
THRESHOLDS      = [round(x, 2) for x in np.arange(0.30, 0.91, 0.05)]
ONSET_WINDOWS   = [3, 5, 7, 9]
N_ONSET_TRUES   = [2, 3, 4, 5]
OFFSET_WINDOWS  = [3, 5, 7, 9]
N_OFFSET_FALSES = [2, 3, 4, 5]


def load_models():
    seg_name = f"gy07bu07_seg_seed{SEG_SEED}_overlap.pth"
    cls_name = f"gy07bu07_class_seed{CLS_SEED}.pth"
    seg_ckpt = torch.load(RESULTS_DIR / f"seg/seed_{SEG_SEED}/{seg_name}",
                          map_location="cpu", weights_only=False)
    cls_ckpt = torch.load(RESULTS_DIR / f"class/seed_{CLS_SEED}/{cls_name}",
                          map_location="cpu", weights_only=False)
    return (seg_ckpt["model"].eval(), seg_ckpt["metadata"],
            cls_ckpt["model"].eval(), cls_ckpt["metadata"])


def run_cls_single(audio, onset_ms, cls_model, cls_meta):
    input_len, chunk_ = [int(x) for x in cls_meta["input_length"].split(",")]
    onset_idx = int(onset_ms * SAMPLE_RATE / 1000)
    clip = audio[onset_idx: onset_idx + input_len * chunk_]
    if len(clip) < input_len * chunk_:
        clip = np.pad(clip, (0, input_len * chunk_ - len(clip)))
    f, t, Sxx = scipy_spectrogram(clip.astype(np.float32), fs=SAMPLE_RATE,
        nperseg=cls_meta["nperseg"], noverlap=cls_meta["noverlap"], nfft=cls_meta["nfft"])
    Sxx = Sxx[(f >= cls_meta["lowcut"]) & (f <= cls_meta["highcut"]), :]
    X = torch.tensor(Sxx, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    s = Sxx.std()
    if s != 0:
        X = (X - Sxx.mean()) / s
    with torch.no_grad():
        return cls_meta["int_to_label"][int(torch.argmax(cls_model(X), dim=1).item())]


def segs_from_labels(labels):
    segs, ins, on = [], False, 0
    for i, v in enumerate(labels):
        if v == 1 and not ins: on, ins = i, True
        elif v == 0 and ins: segs.append((on, i)); ins = False
    if ins: segs.append((on, len(labels)))
    return segs


def find_triggers(pred_labeled):
    """Find onset frames of 4th 'a' in each run of >=4 consecutive predicted 'a's."""
    pred_labels = [x[1] for x in pred_labeled]
    triggers = []
    j = 0
    while j < len(pred_labels):
        if pred_labels[j] == 'a':
            rs = j
            while j < len(pred_labels) and pred_labels[j] == 'a': j += 1
            if j - rs >= 4:
                triggers.append(pred_labeled[rs + 3][0])
        else:
            j += 1
    return triggers


def match_triggers(pred_trigger_frames, true_trigger_frames):
    matched = set()
    tp = fp = 0
    for pf in pred_trigger_frames:
        hit = False
        for ti, tf in enumerate(true_trigger_frames):
            if ti in matched: continue
            if abs(pf - tf) <= COLLAR_FRAMES:
                matched.add(ti); tp += 1; hit = True; break
        if not hit: fp += 1
    fn = len(true_trigger_frames) - len(matched)
    return tp, fp, fn


def main():
    print(f"Loading models (seg={SEG_SEED}, cls={CLS_SEED})...")
    seg_model, seg_meta, cls_model, cls_meta = load_models()
    device = torch.device("cpu")
    seg_model.to(device); cls_model.to(device)
    hist_size = seg_meta["hist_size"]

    # ── Precompute seg probs + audio + true triggers per file ──────────────────
    print("Precomputing seg probabilities...")
    file_data = []  # list of dicts per file
    for fid in TARGET_FILES:
        wav_files = list(DATA_DIR.glob(f"gy07bu07_{fid}*.wav"))
        if not wav_files or not Path(str(wav_files[0]) + ".not.mat").exists():
            continue
        wav_path = wav_files[0]
        rate, audio = wavfile.read(str(wav_path))
        audio = audio.astype(np.float32)
        nm = evfuncs.load_notmat(str(wav_path) + ".not.mat")
        onsets_ms  = np.array(nm.get("onsets",  []), dtype=np.float32)
        offsets_ms = np.array(nm.get("offsets", []), dtype=np.float32)
        labels_str = nm.get("labels", "")
        n_frames   = len(audio) // CHUNK_SIZE

        # Seg probs
        chunks = np.asarray(extract_raw_audio(audio, CHUNK_SIZE), dtype=np.float32).T
        n_chunks = chunks.shape[0]
        ff = np.hstack([np.zeros((n_chunks, 1), dtype=np.float32),
                        chunks, np.zeros((n_chunks, 1), dtype=np.float32)])
        windowed = _concat_windows(ff, hist_size, 1)
        feats = windowed[:, 1:-1].astype(np.float32)
        X = ((torch.tensor(feats) - seg_meta["mean"]) / seg_meta["std"]).nan_to_num(0.0)
        with torch.no_grad():
            probs = torch.sigmoid(seg_model(X.to(device))).cpu().numpy().flatten()
        frame_indices = [i + hist_size - 1 for i in range(len(probs))]

        # True triggers
        labels_list = list(labels_str[:len(onsets_ms)])
        true_trigger_frames = []
        i = 0
        while i < len(labels_list):
            if labels_list[i] == 'a':
                rs = i
                while i < len(labels_list) and labels_list[i] == 'a': i += 1
                if i - rs >= 4:
                    true_trigger_frames.append(
                        int(float(onsets_ms[rs + 3]) * SAMPLE_RATE / (1000 * CHUNK_SIZE)))
            else:
                i += 1

        file_data.append({
            "fid": fid,
            "audio": audio,
            "n_frames": n_frames,
            "probs": probs,
            "frame_indices": frame_indices,
            "true_trigger_frames": true_trigger_frames,
        })

    print(f"Loaded {len(file_data)} files. Building parameter grid...")

    # ── Build valid SW combos ──────────────────────────────────────────────────
    sw_combos = [
        (ow, nt, fw, nf)
        for ow in ONSET_WINDOWS
        for nt in N_ONSET_TRUES  if nt <= ow
        for fw in OFFSET_WINDOWS
        for nf in N_OFFSET_FALSES if nf <= fw
    ]
    total = len(THRESHOLDS) * len(sw_combos)
    print(f"Grid: {len(THRESHOLDS)} thresholds × {len(sw_combos)} SW combos = {total} combinations\n")

    # ── Classification cache: (file_idx, onset_frame) → label ─────────────────
    cls_cache = {}

    def get_cls(file_idx, onset_frame):
        key = (file_idx, onset_frame)
        if key not in cls_cache:
            audio = file_data[file_idx]["audio"]
            onset_ms = onset_frame * MS_PER_FRAME
            cls_cache[key] = run_cls_single(audio, onset_ms, cls_model, cls_meta)
        return cls_cache[key]

    # ── Grid search ────────────────────────────────────────────────────────────
    results = []
    done = 0
    for thr in THRESHOLDS:
        for (ow, nt, fw, nf) in sw_combos:
            sw = {"onset_window_size": ow, "n_onset_true": nt,
                  "offset_window_size": fw, "n_offset_false": nf}
            total_tp = total_fp = total_fn = total_n = 0

            for fi, fd in enumerate(file_data):
                n_frames = fd["n_frames"]
                y_bin = (fd["probs"] >= thr).astype(int).tolist()
                y_sm, _ = apply_sliding_window(y_bin, **sw)

                full_y = np.zeros(n_frames, dtype=int)
                for i, frame_idx in enumerate(fd["frame_indices"]):
                    if frame_idx < n_frames:
                        full_y[frame_idx] = y_sm[i]
                pred_segs = segs_from_labels(full_y)

                pred_labeled = [(p_on, get_cls(fi, p_on)) for p_on, p_off in pred_segs]
                pred_triggers = find_triggers(pred_labeled)
                tp, fp, fn = match_triggers(pred_triggers, fd["true_trigger_frames"])
                total_tp += tp; total_fp += fp; total_fn += fn
                total_n  += len(fd["true_trigger_frames"])

            prec = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0
            rec  = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0
            f1   = 2 * prec * rec / (prec + rec) if prec + rec else 0
            results.append((thr, ow, nt, fw, nf, total_tp, total_fp, total_fn, prec, rec, f1))

            done += 1
            if done % 100 == 0:
                print(f"  {done}/{total}  cache_size={len(cls_cache)}", flush=True)

    results.sort(key=lambda x: x[10], reverse=True)

    print(f"\nCache hits saved {len(cls_cache)} unique classifications.")
    print(f"\nTop 30 (ranked by F1):")
    print(f"{'thr':>5} {'ow':>3} {'nt':>3} {'fw':>3} {'nf':>3}  "
          f"{'TP':>4} {'FP':>4} {'FN':>4}  {'Prec':>6} {'Rec':>6} {'F1':>6}")
    print("─" * 65)
    baseline_f1 = None
    for row in results:
        thr, ow, nt, fw, nf, tp, fp, fn, prec, rec, f1 = row
        if thr == round(seg_meta["tuned_threshold"], 2) and ow == 5 and nt == 3 and fw == 5 and nf == 4:
            marker = " ← baseline"
            baseline_f1 = f1
        else:
            marker = ""
        print(f"{thr:>5.2f} {ow:>3} {nt:>3} {fw:>3} {nf:>3}  "
              f"{tp:>4} {fp:>4} {fn:>4}  {prec:>6.3f} {rec:>6.3f} {f1:>6.3f}{marker}")
        if results.index(row) >= 29:
            break

    if baseline_f1 is not None:
        baseline_rank = next(i for i, r in enumerate(results) if
                             r[0] == round(seg_meta["tuned_threshold"], 2) and
                             r[1] == 5 and r[2] == 3 and r[3] == 5 and r[4] == 4) + 1
        print(f"\nBaseline rank: {baseline_rank}/{total}  F1={baseline_f1:.3f}")


if __name__ == "__main__":
    main()
