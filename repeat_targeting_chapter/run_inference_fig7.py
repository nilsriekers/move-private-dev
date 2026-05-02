#!/usr/bin/env python3
"""Run seg (overlap, seed 42) + cls (seed 42) inference on Jacqui's 12 fig7 bouts.

Compares predictions against corrected .not.mat labels.
Writes results to repeat_targeting_chapter/inference_fig7_results.json.
Nothing in final_experiments/ or data_fig7/ is modified.
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.io import wavfile
from scipy.signal import spectrogram as scipy_spectrogram
import evfuncs

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from paper_experiments.metrics import apply_sliding_window
from final_experiments.train_seg import _apply_sliding_window_per_file
from final_experiments.create_dataset import extract_raw_audio, _concat_windows

# ── Paths ─────────────────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent / "data_fig7" / "250902"
SEG_CKPT   = REPO_ROOT / "final_experiments/results/gy07bu07/seg/seed_42/gy07bu07_seg_seed42_overlap.pth"
CLS_CKPT   = REPO_ROOT / "final_experiments/results/gy07bu07/class/seed_42/gy07bu07_class_seed42.pth"
OUT        = Path(__file__).parent / "inference_fig7_results.json"

# 12 files Jacqui evaluated in matrix_blabla.xlsx
TARGET_FILES = [
    "250902_161452", "250902_161219", "250902_143043", "250902_142805",
    "250902_133448", "250902_132156", "250902_131843", "250902_124534",
    "250902_120715", "250902_115940", "250902_115923", "250902_115531",
]

COLLAR_MS   = 10
CHUNK_SIZE  = 64
SAMPLE_RATE = 44100
MS_PER_FRAME = CHUNK_SIZE / SAMPLE_RATE * 1000
COLLAR_FRAMES = round(COLLAR_MS * SAMPLE_RATE / (CHUNK_SIZE * 1000))

SW_PARAMS = {
    "onset_window_size":  5,
    "n_onset_true":       3,
    "offset_window_size": 5,
    "n_offset_false":     4,
}


def load_wav(path):
    rate, data = wavfile.read(str(path))
    data = data.astype(np.float32)
    if data.ndim > 1:
        data = data[:, 0]
    return rate, data


def extract_seg_features_for_inference(audio, chunk_size, hist_size, overlap=True):
    """Extract features using the same method as build_seg_dataset.

    hist_size here is the metadata value (already hist_size_param+1).
    Returns (features: np.ndarray shape (N, hist_size*chunk_size), frame_indices).
    """
    # Replicate create_dataset.py logic exactly
    audio_feats = extract_raw_audio(audio, chunk_size)   # (chunk_size, n_chunks)
    chunks = np.asarray(audio_feats, dtype=np.float32).T  # (n_chunks, chunk_size)
    n_chunks = chunks.shape[0]

    # Dummy file features with placeholder label (0) and file_idx (0)
    fi_col  = np.zeros((n_chunks, 1), dtype=np.float32)
    lb_col  = np.zeros((n_chunks, 1), dtype=np.float32)
    file_features = np.hstack([fi_col, chunks, lb_col])  # (n_chunks, 1+chunk_size+1)

    step = 1 if overlap else hist_size
    windowed = _concat_windows(file_features, hist_size, step)
    if windowed.size == 0:
        return np.empty((0, hist_size * chunk_size), dtype=np.float32), []

    features   = windowed[:, 1:-1]  # strip file_idx and label
    # frame_index of the last chunk in each window
    indices = list(range(0, n_chunks - (hist_size - 1), step))
    frame_indices = [i + hist_size - 1 for i in indices]
    return features.astype(np.float32), frame_indices


def segs_from_labels(labels):
    """Extract (onset_frame, offset_frame) from binary label array."""
    segs, in_s, on = [], False, 0
    for i, v in enumerate(labels):
        if v == 1 and not in_s:
            on, in_s = i, True
        elif v == 0 and in_s:
            segs.append((on, i))
            in_s = False
    if in_s:
        segs.append((on, len(labels)))
    return segs


def match_onsets(true_segs, pred_segs, collar_frames):
    """Return (tp_pairs, fp_pred_indices, fn_true_indices)."""
    matched_true = set()
    tp_pairs, fp_idx = [], []
    for pi, (p_on, p_off) in enumerate(pred_segs):
        hit = False
        for ti, (t_on, t_off) in enumerate(true_segs):
            if ti in matched_true:
                continue
            if abs(p_on - t_on) <= collar_frames:
                matched_true.add(ti)
                tp_pairs.append((pi, ti))
                hit = True
                break
        if not hit:
            fp_idx.append(pi)
    fn_idx = [i for i in range(len(true_segs)) if i not in matched_true]
    return tp_pairs, fp_idx, fn_idx


def run_seg_inference(audio, seg_model, seg_meta, device):
    hist_size = seg_meta["hist_size"]
    threshold = seg_meta["tuned_threshold"]
    mean_val  = seg_meta["mean"]
    std_val   = seg_meta["std"]

    feats, frame_indices = extract_seg_features_for_inference(audio, CHUNK_SIZE, hist_size, overlap=True)
    if len(feats) == 0:
        return [], []

    X = torch.tensor(feats)
    X = ((X - mean_val) / std_val).nan_to_num(0.0)
    seg_model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(seg_model(X.to(device))).cpu().numpy().flatten()

    y_bin = (probs >= threshold).astype(int).tolist()
    y_sm, _ = apply_sliding_window(y_bin, **SW_PARAMS)

    # Map back to original frame space (frame_indices gives the last chunk index)
    # For onset collar: onset_frame in smoothed predictions maps to
    # frame_indices[i] (last chunk of window) - (hist_size) = first chunk
    # Simpler: use the smoothed prediction index directly as frame position
    return y_sm, frame_indices


def run_cls_inference(audio, onset_ms, cls_model, cls_meta, device):
    """Classify a single syllable starting at onset_ms."""
    input_length_str = cls_meta["input_length"]
    input_len, chunk = [int(x) for x in input_length_str.split(",")]
    nperseg  = cls_meta["nperseg"]
    noverlap = cls_meta["noverlap"]
    nfft     = cls_meta["nfft"]
    lowcut   = cls_meta["lowcut"]
    highcut  = cls_meta["highcut"]
    mean_val = cls_meta.get("mean", None)
    std_val  = cls_meta.get("std", None)
    int_to_label = cls_meta["int_to_label"]

    onset_idx = int(onset_ms * SAMPLE_RATE / 1000)
    clip = audio[onset_idx: onset_idx + input_len * chunk]
    if len(clip) < input_len * chunk:
        clip = np.pad(clip, (0, input_len * chunk - len(clip)))

    f, t, Sxx = scipy_spectrogram(clip.astype(np.float32), fs=SAMPLE_RATE,
                                   nperseg=nperseg, noverlap=noverlap, nfft=nfft)
    mask = (f >= lowcut) & (f <= highcut)
    Sxx  = Sxx[mask, :]
    if Sxx.ndim != 2:
        return None, None

    X = torch.tensor(Sxx, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    # Per-spectrogram z-score normalization (identical to train_class.py line 205)
    sxx_mean = Sxx.mean()
    sxx_std  = Sxx.std()
    if sxx_std != 0:
        X = (X - sxx_mean) / sxx_std
    if mean_val is not None and std_val is not None:
        X = ((X - mean_val) / std_val).nan_to_num(0.0)
    cls_model.eval()
    with torch.no_grad():
        logits = cls_model(X.to(device))
        pred_idx = int(torch.argmax(logits, dim=1).cpu().item())
    return int_to_label[pred_idx], int_to_label


def main():
    device = torch.device("cpu")

    # Load seg model
    seg_ckpt  = torch.load(SEG_CKPT, map_location="cpu", weights_only=False)
    seg_model = seg_ckpt["model"].to(device)
    seg_meta  = seg_ckpt["metadata"]
    print(f"Seg model loaded. threshold={seg_meta['tuned_threshold']:.3f} hist_size={seg_meta['hist_size']}")

    # Load cls model
    cls_ckpt  = torch.load(CLS_CKPT, map_location="cpu", weights_only=False)
    cls_model = cls_ckpt["model"].to(device)
    cls_meta  = cls_ckpt["metadata"]
    print(f"Cls model loaded. classes={list(cls_meta['label_to_int'].keys())}\n")

    all_results = []
    global_tp = global_fp = global_fn = 0
    global_cls_correct = global_cls_total = 0

    for fid in TARGET_FILES:
        # Find wav file
        wav_files = list(DATA_DIR.glob(f"gy07bu07_{fid}*.wav"))
        if not wav_files:
            print(f"  MISSING wav: {fid}")
            continue
        wav_path = wav_files[0]
        notmat_path = Path(str(wav_path) + ".not.mat")

        if not notmat_path.exists():
            print(f"  MISSING notmat: {fid}")
            continue

        # Load audio
        rate, audio = load_wav(wav_path)
        assert rate == SAMPLE_RATE, f"Unexpected sample rate: {rate}"

        # Load ground truth from corrected .not.mat
        notmat      = evfuncs.load_notmat(str(wav_path) + ".not.mat")
        onsets_ms   = np.array(notmat.get("onsets",  []), dtype=np.float32)
        offsets_ms  = np.array(notmat.get("offsets", []), dtype=np.float32)
        labels_str  = notmat.get("labels", "")
        n_true      = len(onsets_ms)

        # Build true binary label array (frame-level)
        n_frames = len(audio) // CHUNK_SIZE
        y_true   = np.zeros(n_frames, dtype=int)
        for on_ms, off_ms in zip(onsets_ms, offsets_ms):
            on_f  = int(on_ms  * SAMPLE_RATE / (1000 * CHUNK_SIZE))
            off_f = int(off_ms * SAMPLE_RATE / (1000 * CHUNK_SIZE))
            y_true[on_f:off_f] = 1

        # Run segmentation
        y_sm, frame_indices = run_seg_inference(audio, seg_model, seg_meta, device)
        if not y_sm:
            print(f"  {fid}: no predictions")
            continue

        # Map smoothed predictions back to full frame space
        # overlap step=1: frame_indices[i] is the last chunk of window i
        # → position in y_sm[i] corresponds to frame frame_indices[i] - (hist_size-1)
        hist = seg_meta["hist_size"]
        full_y_sm = np.zeros(n_frames, dtype=int)
        for i, fi in enumerate(frame_indices):
            if fi < n_frames:
                full_y_sm[fi] = y_sm[i]

        true_segs = segs_from_labels(y_true)
        pred_segs = segs_from_labels(full_y_sm)
        tp_pairs, fp_idx, fn_idx = match_onsets(true_segs, pred_segs, COLLAR_FRAMES)

        tp = len(tp_pairs)
        fp = len(fp_idx)
        fn = len(fn_idx)
        global_tp += tp; global_fp += fp; global_fn += fn

        # Classification for TP segments
        cls_results = []
        for pi, ti in tp_pairs:
            onset_ms_pred = frame_indices[pred_segs[pi][0]] * MS_PER_FRAME if pred_segs[pi][0] < len(frame_indices) else pred_segs[pi][0] * MS_PER_FRAME
            # Use true onset for classification (more stable)
            true_onset_ms = float(onsets_ms[ti])
            true_label    = labels_str[ti] if ti < len(labels_str) else "?"

            pred_label, _ = run_cls_inference(audio, true_onset_ms, cls_model, cls_meta, device)
            if pred_label is not None:
                correct = (pred_label == true_label)
                cls_results.append({
                    "true_label": true_label,
                    "pred_label": pred_label,
                    "correct": correct,
                })
                global_cls_correct += int(correct)
                global_cls_total   += 1

        n_correct_cls = sum(1 for r in cls_results if r["correct"])
        print(f"  {fid}: seg TP={tp} FP={fp} FN={fn}  cls {n_correct_cls}/{len(cls_results)} correct")

        # Repeat targeting simulation: simulate Moove's online aaaa pattern matching
        # (4 consecutive 'a' syllables; [de] context doesn't directly precede 'a' in this bird's song)
        labels_list = list(labels_str[:len(onsets_ms)])

        # Step 1: True trigger positions — 4th 'a' in each run of ≥4 consecutive 'a's
        true_trigger_indices = []  # syllable index of the 4th 'a'
        i = 0
        while i < len(labels_list):
            if labels_list[i] == 'a':
                run_start = i
                while i < len(labels_list) and labels_list[i] == 'a':
                    i += 1
                run_len = i - run_start
                if run_len >= 4:
                    true_trigger_indices.append(run_start + 3)  # 0-indexed: 4th = index 3
            else:
                i += 1
        true_trigger_frames = [int(float(onsets_ms[i]) * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                               for i in true_trigger_indices]

        # Step 2: Classify all predicted segments → build predicted label sequence
        pred_labeled = []  # (onset_frame, onset_ms, pred_label)
        for p_on, p_off in pred_segs:
            p_onset_ms = p_on * MS_PER_FRAME
            plabel, _ = run_cls_inference(audio, p_onset_ms, cls_model, cls_meta, device)
            if plabel is not None:
                pred_labeled.append((p_on, p_onset_ms, plabel))

        # Step 3: Find predicted triggers — 4th 'a' in each run of ≥4 consecutive 'a's
        # in the predicted label sequence
        pred_labels_seq = [x[2] for x in pred_labeled]
        pred_trigger_frames = []  # onset frame of predicted 4th 'a'
        j = 0
        while j < len(pred_labels_seq):
            if pred_labels_seq[j] == 'a':
                run_start_j = j
                while j < len(pred_labels_seq) and pred_labels_seq[j] == 'a':
                    j += 1
                run_len_j = j - run_start_j
                if run_len_j >= 4:
                    pred_trigger_frames.append(pred_labeled[run_start_j + 3][0])
            else:
                j += 1

        # Step 4: Match predicted triggers to true triggers with onset collar
        matched_true = set()
        repeat_tp = repeat_fp = 0
        for pf in pred_trigger_frames:
            hit = False
            for ti, tf in enumerate(true_trigger_frames):
                if ti in matched_true:
                    continue
                if abs(pf - tf) <= COLLAR_FRAMES:
                    matched_true.add(ti)
                    hit = True
                    repeat_tp += 1
                    break
            if not hit:
                repeat_fp += 1
        repeat_fn = len(true_trigger_indices) - len(matched_true)

        print(f"    repeat: {len(true_trigger_indices)} true triggers, {len(pred_trigger_frames)} pred triggers → TP={repeat_tp} FP={repeat_fp} FN={repeat_fn}")

        all_results.append({
            "file": fid,
            "n_true_segs": n_true,
            "seg": {"tp": tp, "fp": fp, "fn": fn,
                    "f1": round(2*tp/(2*tp+fp+fn), 4) if (2*tp+fp+fn)>0 else 0},
            "cls": {"correct": n_correct_cls, "total": len(cls_results),
                    "accuracy": round(n_correct_cls/len(cls_results), 4) if cls_results else None},
            "repeat_targeting": {
                "n_target_phrases": len(true_trigger_indices),
                "n_pred_triggers": len(pred_trigger_frames),
                "tp": repeat_tp, "fp": repeat_fp, "fn": repeat_fn,
                "hit_rate": round(repeat_tp/len(true_trigger_indices), 4) if true_trigger_indices else None,
            },
            "per_tp_cls": cls_results,
        })

    # Global summary
    prec = global_tp/(global_tp+global_fp) if (global_tp+global_fp)>0 else 0
    rec  = global_tp/(global_tp+global_fn) if (global_tp+global_fn)>0 else 0
    f1   = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0

    total_rt_tp = sum(r["repeat_targeting"]["tp"] for r in all_results)
    total_rt_fp = sum(r["repeat_targeting"]["fp"] for r in all_results)
    total_rt_fn = sum(r["repeat_targeting"]["fn"] for r in all_results)
    total_rt_n  = sum(r["repeat_targeting"]["n_target_phrases"] for r in all_results)
    total_rt_pred = sum(r["repeat_targeting"]["n_pred_triggers"] for r in all_results)

    summary = {
        "seg_global": {
            "tp": global_tp, "fp": global_fp, "fn": global_fn,
            "precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
        },
        "cls_global": {
            "correct": global_cls_correct, "total": global_cls_total,
            "accuracy": round(global_cls_correct/global_cls_total, 4) if global_cls_total else None,
        },
        "repeat_targeting_global": {
            "n_true_trigger_phrases": total_rt_n,
            "n_pred_triggers": total_rt_pred,
            "tp": total_rt_tp, "fp": total_rt_fp, "fn": total_rt_fn,
            "hit_rate": round(total_rt_tp/total_rt_n, 4) if total_rt_n else None,
            "fp_rate": round(total_rt_fp/total_rt_pred, 4) if total_rt_pred else None,
        },
    }

    out_data = {
        "bird": "gy07bu07",
        "seg_seed": 42, "cls_seed": 42,
        "n_files": len(all_results),
        "collar_ms": COLLAR_MS,
        "sw_params": SW_PARAMS,
        "seg_threshold": float(seg_meta["tuned_threshold"]),
        "summary": summary,
        "per_file": all_results,
    }

    with open(OUT, "w") as f:
        json.dump(out_data, f, indent=2)

    print(f"\n=== SUMMARY ===")
    print(f"Segmentation:      F1={f1:.4f}  P={prec:.4f}  R={rec:.4f}  TP={global_tp} FP={global_fp} FN={global_fn}")
    print(f"Classification:    acc={global_cls_correct}/{global_cls_total}={global_cls_correct/global_cls_total:.4f}" if global_cls_total else "Classification: no data")
    print(f"Repeat targeting:  {total_rt_tp}/{total_rt_n} true triggers hit ({round(total_rt_tp/total_rt_n*100,1) if total_rt_n else 0}%), {total_rt_fp} FP out of {total_rt_pred} predicted triggers")
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    main()
