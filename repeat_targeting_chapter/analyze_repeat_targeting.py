#!/usr/bin/env python3
"""Detailed FP/FN analysis for repeat targeting simulation.

Runs seg (overlap, seed 42) + cls (seed 42) on the 12 Fig. 7 bouts and
classifies each false positive into:
  - Typ 1: real 'a' run detected but trigger onset outside collar window (matching artefact)
  - Typ 2: non-'a' segments misclassified as 'a', forming spurious run
  - Typ 3: second trigger on same long run (already counted as TP) — EXCLUDED from FP count
             (in real Moove the targeting rule resets after trigger delivery)

Writes per-file and global summary to stdout.
"""

import sys
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import torch
import evfuncs
from scipy.io import wavfile
from scipy.signal import spectrogram as scipy_spectrogram
from paper_experiments.metrics import apply_sliding_window
from final_experiments.create_dataset import extract_raw_audio, _concat_windows

DATA_DIR = Path(__file__).parent / "data_fig7" / "250902"
SEG_CKPT = REPO_ROOT / "final_experiments/results/gy07bu07/seg/seed_42/gy07bu07_seg_seed42_overlap.pth"
CLS_CKPT = REPO_ROOT / "final_experiments/results/gy07bu07/class/seed_42/gy07bu07_class_seed42.pth"

TARGET_FILES = [
    "250902_161452", "250902_161219", "250902_143043", "250902_142805",
    "250902_133448", "250902_132156", "250902_131843", "250902_124534",
    "250902_120715", "250902_115940", "250902_115923", "250902_115531",
]

CHUNK_SIZE = 64
SAMPLE_RATE = 44100
MS_PER_FRAME = CHUNK_SIZE / SAMPLE_RATE * 1000
COLLAR_FRAMES = round(10 * SAMPLE_RATE / (CHUNK_SIZE * 1000))
SW_PARAMS = {"onset_window_size": 5, "n_onset_true": 3, "offset_window_size": 5, "n_offset_false": 4}


def load_models():
    seg_ckpt = torch.load(SEG_CKPT, map_location="cpu", weights_only=False)
    cls_ckpt = torch.load(CLS_CKPT, map_location="cpu", weights_only=False)
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


def nearest_true_label(frame, onsets_ms, offsets_ms, labels_str):
    best_i, best_dist = None, 1e9
    for i, (on, off) in enumerate(zip(onsets_ms, offsets_ms)):
        on_f = int(on * SAMPLE_RATE / (1000 * CHUNK_SIZE))
        off_f = int(off * SAMPLE_RATE / (1000 * CHUNK_SIZE))
        dist = 0 if on_f <= frame <= off_f else min(abs(frame - on_f), abs(frame - off_f))
        if dist < best_dist:
            best_dist = dist
            best_i = i
    if best_i is None:
        return "?", 999
    return labels_str[best_i] if best_i < len(labels_str) else "?", best_dist


def analyze_file(fid, seg_model, seg_meta, cls_model, cls_meta, verbose=True):
    wav_path = list(DATA_DIR.glob(f"gy07bu07_{fid}*.wav"))[0]
    rate, audio = wavfile.read(str(wav_path))
    audio = audio.astype(np.float32)
    nm = evfuncs.load_notmat(str(wav_path) + ".not.mat")
    onsets_ms = np.array(nm["onsets"], dtype=np.float32)
    offsets_ms = np.array(nm["offsets"], dtype=np.float32)
    labels_str = nm["labels"]
    n_frames = len(audio) // CHUNK_SIZE

    # Segmentation
    hist_size = seg_meta["hist_size"]
    mean_val = seg_meta["mean"]
    std_val = seg_meta["std"]
    threshold = seg_meta["tuned_threshold"]

    chunks = np.asarray(extract_raw_audio(audio, CHUNK_SIZE), dtype=np.float32).T
    n_chunks = chunks.shape[0]
    file_features = np.hstack([np.zeros((n_chunks, 1), dtype=np.float32),
                                chunks,
                                np.zeros((n_chunks, 1), dtype=np.float32)])
    windowed = _concat_windows(file_features, hist_size, 1)
    feats = windowed[:, 1:-1].astype(np.float32)
    X = ((torch.tensor(feats) - mean_val) / std_val).nan_to_num(0.0)
    with torch.no_grad():
        probs = torch.sigmoid(seg_model(X)).cpu().numpy().flatten()
    y_bin = (probs >= threshold).astype(int).tolist()
    y_sm, _ = apply_sliding_window(y_bin, **SW_PARAMS)
    frame_indices = [i + hist_size - 1 for i in range(len(y_sm))]

    full_y_sm = np.zeros(n_frames, dtype=int)
    for i, fi in enumerate(frame_indices):
        if fi < n_frames:
            full_y_sm[fi] = y_sm[i]
    pred_segs = segs_from_labels(full_y_sm)

    # True trigger positions: 4th 'a' in each run of >=4 consecutive 'a's
    # Store full run boundaries (first frame, last frame of run) for Typ-3 detection
    labels_list = list(labels_str[:len(onsets_ms)])
    true_triggers = []  # (syllable_idx_of_4th_a, run_start_frame, run_end_frame)
    i = 0
    while i < len(labels_list):
        if labels_list[i] == 'a':
            rs = i
            while i < len(labels_list) and labels_list[i] == 'a':
                i += 1
            run_len = i - rs
            if run_len >= 4:
                trigger_syl = rs + 3
                run_start_f = int(float(onsets_ms[rs]) * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                run_end_f = int(float(offsets_ms[i - 1]) * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                true_triggers.append((trigger_syl, run_start_f, run_end_f))
        else:
            i += 1
    true_trigger_frames = [int(float(onsets_ms[t[0]]) * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                           for t in true_triggers]

    # Classify all predicted segments
    pred_labeled = []
    for p_on, p_off in pred_segs:
        lbl = run_cls(audio, p_on * MS_PER_FRAME, cls_model, cls_meta)
        pred_labeled.append((p_on, lbl))

    # Find predicted triggers: runs of >=4 'a' in predicted sequence
    pred_labels = [x[1] for x in pred_labeled]
    pred_trigger_frames = []
    j = 0
    while j < len(pred_labels):
        if pred_labels[j] == 'a':
            rs = j
            while j < len(pred_labels) and pred_labels[j] == 'a':
                j += 1
            if j - rs >= 4:
                pred_trigger_frames.append(pred_labeled[rs + 3][0])
        else:
            j += 1

    # Match: TP if within collar. Track which true runs are already matched.
    matched_true = set()   # indices into true_triggers
    matched_run_frames = set()  # (run_start_f, run_end_f) of already-matched true runs

    tp = fp_typ1 = fp_typ2 = fp_typ3 = 0

    for pf in pred_trigger_frames:
        # Check if this falls in an already-matched run (Typ 3 exclusion)
        in_matched_run = any(rs <= pf <= re for rs, re in matched_run_frames)
        if in_matched_run:
            fp_typ3 += 1
            if verbose:
                print(f"  [Typ3-FP] {fid}: pred trigger frame={pf} ({pf*MS_PER_FRAME:.0f}ms) "
                      f"falls in already-triggered run → excluded")
            continue

        hit = False
        for ti, (tsyl, trs, tre) in enumerate(true_triggers):
            if ti in matched_true:
                continue
            tf = true_trigger_frames[ti]
            if abs(pf - tf) <= COLLAR_FRAMES:
                matched_true.add(ti)
                matched_run_frames.add((trs, tre))
                tp += 1
                hit = True
                break

        if not hit:
            # Classify this FP: what are the true labels under the predicted 'a' segments?
            # Find which pred run this trigger came from
            pred_run_labels = []
            for k, (pf2, lbl2) in enumerate(pred_labeled):
                # find the run containing this trigger
                pass
            true_lbl_at_trigger, dist = nearest_true_label(pf, onsets_ms, offsets_ms, labels_str)
            if true_lbl_at_trigger == 'a':
                fp_typ1 += 1
                fp_type = "Typ1 (real 'a', onset outside collar)"
            else:
                fp_typ2 += 1
                fp_type = f"Typ2 (non-'a' misclassified, true={true_lbl_at_trigger})"
            if verbose:
                print(f"  [FP-{fp_type}] {fid}: pred trigger frame={pf} ({pf*MS_PER_FRAME:.0f}ms)")

    fn = len(true_triggers) - len(matched_true)
    fp_counted = fp_typ1 + fp_typ2  # Typ3 excluded

    return {
        "n_true": len(true_triggers),
        "n_pred": len(pred_trigger_frames),
        "tp": tp,
        "fp": fp_counted,
        "fp_typ1": fp_typ1,
        "fp_typ2": fp_typ2,
        "fp_typ3_excluded": fp_typ3,
        "fn": fn,
    }


def main():
    seg_model, seg_meta, cls_model, cls_meta = load_models()
    print(f"Seg threshold={seg_meta['tuned_threshold']:.3f}  hist_size={seg_meta['hist_size']}")
    print(f"Cls classes: {list(cls_meta['label_to_int'].keys())}\n")

    totals = {"n_true": 0, "n_pred": 0, "tp": 0, "fp": 0,
              "fp_typ1": 0, "fp_typ2": 0, "fp_typ3_excluded": 0, "fn": 0}

    for fid in TARGET_FILES:
        r = analyze_file(fid, seg_model, seg_meta, cls_model, cls_meta, verbose=True)
        hr = r["tp"] / r["n_true"] if r["n_true"] else None
        print(f"  {fid}: n_true={r['n_true']} n_pred={r['n_pred']} "
              f"TP={r['tp']} FP={r['fp']} FN={r['fn']} "
              f"(FP_typ1={r['fp_typ1']} FP_typ2={r['fp_typ2']} excluded_typ3={r['fp_typ3_excluded']}) "
              f"hit={hr:.2f}" if hr is not None else f"  {fid}: n_true=0")
        for k in totals:
            totals[k] += r[k]

    n = totals["n_true"]
    np_ = totals["n_pred"]
    tp = totals["tp"]
    fp = totals["fp"]
    fn = totals["fn"]
    print(f"\n=== GLOBAL (Typ3 excluded from FP) ===")
    print(f"  True triggers:    {n}")
    print(f"  Pred triggers:    {np_} ({totals['fp_typ3_excluded']} Typ3 excluded)")
    print(f"  TP:  {tp}  ({tp/n*100:.1f}% of true triggers)")
    print(f"  FN:  {fn}  ({fn/n*100:.1f}% of true triggers)")
    print(f"  FP:  {fp}  (Typ1={totals['fp_typ1']}, Typ2={totals['fp_typ2']})")
    if tp + fp > 0:
        print(f"  Precision: {tp/(tp+fp):.4f}  Recall: {tp/(tp+fn):.4f}")


if __name__ == "__main__":
    main()
