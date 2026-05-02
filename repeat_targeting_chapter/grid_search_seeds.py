#!/usr/bin/env python3
"""Grid search over seg × cls seed combinations for repeat targeting.

Tests all 9 combinations (seeds 42/123/456 × 42/123/456) using overlap seg models.
Prints a summary table ranked by F1 (repeat targeting).

Usage:
    python3 grid_search_seeds.py
"""

import sys
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

DATA_DIR = Path(__file__).parent / "data_fig7" / "250902"
RESULTS_DIR = REPO_ROOT / "final_experiments/results/gy07bu07"

SEEDS = [42, 123, 456]

TARGET_FILES = [
    "250902_161452", "250902_161219", "250902_143043", "250902_142805",
    "250902_133448", "250902_132156", "250902_131843", "250902_124534",
    "250902_120715", "250902_115940", "250902_115923", "250902_115531",
]

CHUNK_SIZE   = 64
SAMPLE_RATE  = 44100
MS_PER_FRAME = CHUNK_SIZE / SAMPLE_RATE * 1000
COLLAR_FRAMES = round(10 * SAMPLE_RATE / (CHUNK_SIZE * 1000))  # 10 ms collar
SW_PARAMS = {"onset_window_size": 5, "n_onset_true": 3, "offset_window_size": 5, "n_offset_false": 4}


def load_models(seg_seed, cls_seed):
    seg_name = f"gy07bu07_seg_seed{seg_seed}_overlap.pth"
    cls_name = f"gy07bu07_class_seed{cls_seed}.pth"
    seg_ckpt = torch.load(RESULTS_DIR / f"seg/seed_{seg_seed}/{seg_name}", map_location="cpu", weights_only=False)
    cls_ckpt = torch.load(RESULTS_DIR / f"class/seed_{cls_seed}/{cls_name}", map_location="cpu", weights_only=False)
    return (seg_ckpt["model"].eval(), seg_ckpt["metadata"],
            cls_ckpt["model"].eval(), cls_ckpt["metadata"])


def run_cls(audio, onset_ms, cls_model, cls_meta):
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


def evaluate_combination(seg_seed, cls_seed):
    seg_model, seg_meta, cls_model, cls_meta = load_models(seg_seed, cls_seed)
    device = torch.device("cpu")
    seg_model.to(device); cls_model.to(device)

    total_tp = total_fp = total_fn = 0
    total_n = 0

    for fid in TARGET_FILES:
        wav_files = list(DATA_DIR.glob(f"gy07bu07_{fid}*.wav"))
        if not wav_files:
            continue
        wav_path = wav_files[0]
        notmat_path = Path(str(wav_path) + ".not.mat")
        if not notmat_path.exists():
            continue

        rate, audio = wavfile.read(str(wav_path))
        audio = audio.astype(np.float32)
        nm = evfuncs.load_notmat(str(wav_path) + ".not.mat")
        onsets_ms  = np.array(nm.get("onsets",  []), dtype=np.float32)
        offsets_ms = np.array(nm.get("offsets", []), dtype=np.float32)
        labels_str = nm.get("labels", "")
        n_frames   = len(audio) // CHUNK_SIZE

        # Segmentation
        hist_size = seg_meta["hist_size"]
        chunks = np.asarray(extract_raw_audio(audio, CHUNK_SIZE), dtype=np.float32).T
        n_chunks = chunks.shape[0]
        file_features = np.hstack([np.zeros((n_chunks, 1), dtype=np.float32),
                                    chunks,
                                    np.zeros((n_chunks, 1), dtype=np.float32)])
        windowed = _concat_windows(file_features, hist_size, 1)
        feats = windowed[:, 1:-1].astype(np.float32)
        X = ((torch.tensor(feats) - seg_meta["mean"]) / seg_meta["std"]).nan_to_num(0.0)
        with torch.no_grad():
            probs = torch.sigmoid(seg_model(X.to(device))).cpu().numpy().flatten()
        y_bin = (probs >= seg_meta["tuned_threshold"]).astype(int).tolist()
        y_sm, _ = apply_sliding_window(y_bin, **SW_PARAMS)
        frame_indices = [i + hist_size - 1 for i in range(len(y_sm))]

        full_y_sm = np.zeros(n_frames, dtype=int)
        for i, fi in enumerate(frame_indices):
            if fi < n_frames:
                full_y_sm[fi] = y_sm[i]
        pred_segs = segs_from_labels(full_y_sm)

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
        total_n += len(true_trigger_frames)

        # Classify all predicted segments
        pred_labeled = []
        for p_on, p_off in pred_segs:
            lbl = run_cls(audio, p_on * MS_PER_FRAME, cls_model, cls_meta)
            pred_labeled.append((p_on, lbl))

        # Predicted triggers
        pred_labels = [x[1] for x in pred_labeled]
        pred_trigger_frames = []
        j = 0
        while j < len(pred_labels):
            if pred_labels[j] == 'a':
                rs = j
                while j < len(pred_labels) and pred_labels[j] == 'a': j += 1
                if j - rs >= 4:
                    pred_trigger_frames.append(pred_labeled[rs + 3][0])
            else:
                j += 1

        # Match
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
        total_tp += tp; total_fp += fp; total_fn += fn

    prec = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0
    rec  = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0
    f1   = 2 * prec * rec / (prec + rec) if prec + rec else 0
    return {"tp": total_tp, "fp": total_fp, "fn": total_fn, "n": total_n,
            "prec": prec, "rec": rec, "f1": f1}


def main():
    results = []
    for seg_seed in SEEDS:
        for cls_seed in SEEDS:
            print(f"  seg={seg_seed} cls={cls_seed} ...", end=" ", flush=True)
            r = evaluate_combination(seg_seed, cls_seed)
            results.append((seg_seed, cls_seed, r))
            print(f"TP={r['tp']} FP={r['fp']} FN={r['fn']}  P={r['prec']:.3f} R={r['rec']:.3f} F1={r['f1']:.3f}")

    results.sort(key=lambda x: x[2]["f1"], reverse=True)

    print(f"\n{'seg':>5} {'cls':>5} {'TP':>4} {'FP':>4} {'FN':>4} {'n':>4}  {'Prec':>6} {'Rec':>6} {'F1':>6}")
    print("─" * 60)
    for seg_seed, cls_seed, r in results:
        marker = " ←" if seg_seed == 42 and cls_seed == 42 else ""
        print(f"{seg_seed:>5} {cls_seed:>5} {r['tp']:>4} {r['fp']:>4} {r['fn']:>4} {r['n']:>4}  "
              f"{r['prec']:>6.3f} {r['rec']:>6.3f} {r['f1']:>6.3f}{marker}")


if __name__ == "__main__":
    main()
