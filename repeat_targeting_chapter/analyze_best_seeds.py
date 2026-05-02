#!/usr/bin/env python3
"""Per-file failure analysis for the best seed combination (seg=42, cls=123).

Usage:
    python3 analyze_best_seeds.py
"""

import sys
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import torch
from scipy.io import wavfile, savemat
from scipy.signal import spectrogram as scipy_spectrogram
import evfuncs
from paper_experiments.metrics import apply_sliding_window
from final_experiments.create_dataset import extract_raw_audio, _concat_windows

DATA_DIR = Path(__file__).parent / "data_fig7" / "250902"
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
PRED_BEST_DIR = Path("/Users/riekers/.moove/rec_data/gy07bu07/fig7_pred_best/250902")
MS_PER_FRAME  = CHUNK_SIZE / SAMPLE_RATE * 1000
COLLAR_FRAMES = round(10 * SAMPLE_RATE / (CHUNK_SIZE * 1000))
SEG_THRESHOLD = 0.80  # overrides model's tuned_threshold
SW_PARAMS = {"onset_window_size": 3, "n_onset_true": 3, "offset_window_size": 3, "n_offset_false": 3}


def load_models():
    seg_name = f"gy07bu07_seg_seed{SEG_SEED}_overlap.pth"
    cls_name = f"gy07bu07_class_seed{CLS_SEED}.pth"
    seg_ckpt = torch.load(RESULTS_DIR / f"seg/seed_{SEG_SEED}/{seg_name}", map_location="cpu", weights_only=False)
    cls_ckpt = torch.load(RESULTS_DIR / f"class/seed_{CLS_SEED}/{cls_name}", map_location="cpu", weights_only=False)
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


def analyze_file(fid, seg_model, seg_meta, cls_model, cls_meta):
    wav_files = list(DATA_DIR.glob(f"gy07bu07_{fid}*.wav"))
    if not wav_files:
        return None
    wav_path = wav_files[0]
    if not Path(str(wav_path) + ".not.mat").exists():
        return None

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
                                chunks, np.zeros((n_chunks, 1), dtype=np.float32)])
    windowed = _concat_windows(file_features, hist_size, 1)
    feats = windowed[:, 1:-1].astype(np.float32)
    X = ((torch.tensor(feats) - seg_meta["mean"]) / seg_meta["std"]).nan_to_num(0.0)
    with torch.no_grad():
        probs = torch.sigmoid(seg_model(X)).cpu().numpy().flatten()
    y_bin = (probs >= SEG_THRESHOLD).astype(int).tolist()
    y_sm, _ = apply_sliding_window(y_bin, **SW_PARAMS)
    frame_indices = [i + hist_size - 1 for i in range(len(y_sm))]
    full_y_sm = np.zeros(n_frames, dtype=int)
    for i, fi in enumerate(frame_indices):
        if fi < n_frames:
            full_y_sm[fi] = y_sm[i]
    pred_segs = segs_from_labels(full_y_sm)

    # True triggers + run boundaries for Typ3 exclusion
    labels_list = list(labels_str[:len(onsets_ms)])
    true_triggers = []  # (trigger_frame, run_start_frame, run_end_frame, run_len)
    i = 0
    while i < len(labels_list):
        if labels_list[i] == 'a':
            rs = i
            while i < len(labels_list) and labels_list[i] == 'a': i += 1
            run_len = i - rs
            if run_len >= 4:
                tf = int(float(onsets_ms[rs + 3]) * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                rs_f = int(float(onsets_ms[rs]) * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                re_f = int(float(offsets_ms[i - 1]) * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                true_triggers.append((tf, rs_f, re_f, run_len,
                                       float(onsets_ms[rs + 3])))
        else:
            i += 1

    # Classify predicted segments
    pred_labeled = []  # (onset_frame, label, offset_frame)
    for p_on, p_off in pred_segs:
        lbl = run_cls(audio, p_on * MS_PER_FRAME, cls_model, cls_meta)
        pred_labeled.append((p_on, lbl, p_off))

    # Write .not.mat to fig7_pred_best/
    PRED_BEST_DIR.mkdir(parents=True, exist_ok=True)
    notmat_out = PRED_BEST_DIR / (wav_path.name + ".not.mat")
    savemat(str(notmat_out), {
        "Fs":        np.array([[float(SAMPLE_RATE)]]),
        "fname":     wav_path.name,
        "labels":    "".join(x[1] for x in pred_labeled),
        "onsets":    np.array([[x[0] * MS_PER_FRAME for x in pred_labeled]]),
        "offsets":   np.array([[x[2] * MS_PER_FRAME for x in pred_labeled]]),
        "min_int":   np.array([[0.0]]),
        "min_dur":   np.array([[0.0]]),
        "threshold": np.array([[SEG_THRESHOLD]]),
        "sm_win":    np.array([[0.0]]),
    })

    # Predicted triggers
    pred_labels = [x[1] for x in pred_labeled]
    pred_trigger_entries = []  # (frame, onset_ms)
    j = 0
    while j < len(pred_labels):
        if pred_labels[j] == 'a':
            rs = j
            while j < len(pred_labels) and pred_labels[j] == 'a': j += 1
            if j - rs >= 4:
                pf = pred_labeled[rs + 3][0]
                pred_trigger_entries.append((pf, pf * MS_PER_FRAME, j - rs))
        else:
            j += 1

    # Match with Typ3 exclusion
    matched_true = set()
    matched_run_ranges = []
    tp = fp = 0
    issues = []

    for pf, pf_ms, run_len_p in pred_trigger_entries:
        if any(rs <= pf <= re for rs, re in matched_run_ranges):
            continue  # Typ3 excluded
        hit = False
        for ti, (tf, trs, tre, run_len_t, tf_ms) in enumerate(true_triggers):
            if ti in matched_true: continue
            if abs(pf - tf) <= COLLAR_FRAMES:
                matched_true.add(ti)
                matched_run_ranges.append((trs, tre))
                tp += 1; hit = True; break
        if not hit:
            # nearest true label at predicted trigger position
            best_lbl, best_dist = "?", 1e9
            for k, (on, off) in enumerate(zip(onsets_ms, offsets_ms)):
                on_f  = int(on  * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                off_f = int(off * SAMPLE_RATE / (1000 * CHUNK_SIZE))
                d = 0 if on_f <= pf <= off_f else min(abs(pf - on_f), abs(pf - off_f))
                if d < best_dist:
                    best_dist = d
                    best_lbl  = labels_str[k] if k < len(labels_str) else "?"
            fp += 1
            issues.append(f"FP {pf_ms/1000:.2f}s (pred {run_len_p}×a, nearest_true={best_lbl})")

    fn = len(true_triggers) - len(matched_true)
    for ti, (tf, trs, tre, run_len_t, tf_ms) in enumerate(true_triggers):
        if ti not in matched_true:
            near = []
            for k, (p_on, lbl, _) in enumerate(pred_labeled):
                if abs(p_on - tf) <= COLLAR_FRAMES * 3:
                    near.append(f"{lbl}({p_on - tf:+d}f)")
            near_str = ", ".join(near[:4]) if near else "—"
            issues.append(f"FN {tf_ms/1000:.2f}s (true {run_len_t}×a, near=[{near_str}])")

    return {"n_true": len(true_triggers), "n_pred": len(pred_trigger_entries),
            "tp": tp, "fp": fp, "fn": fn, "issues": issues}


def main():
    print(f"seg=seed{SEG_SEED} (overlap)  cls=seed{CLS_SEED}  threshold={SEG_THRESHOLD}  SW={SW_PARAMS}\n")
    seg_model, seg_meta, cls_model, cls_meta = load_models()

    rows = []
    totals = {"n_true": 0, "n_pred": 0, "tp": 0, "fp": 0, "fn": 0}
    for fid in TARGET_FILES:
        fid_short = fid.split("_", 1)[1]
        r = analyze_file(fid, seg_model, seg_meta, cls_model, cls_meta)
        if r is None:
            print(f"MISSING: {fid}")
            continue
        rows.append((fid_short, r))
        for k in totals: totals[k] += r[k]

    print(f"{'File':<20} {'n_true':>6} {'n_pred':>6} {'TP':>4} {'FP':>4} {'FN':>4}  {'hit':>5}  Details")
    print("─" * 125)
    for fid_short, r in rows:
        hit    = f"{r['tp']}/{r['n_true']}" if r["n_true"] else "—"
        detail = "  ·  ".join(r["issues"]) if r["issues"] else "✓"
        print(f"{fid_short:<20} {r['n_true']:>6} {r['n_pred']:>6} {r['tp']:>4} {r['fp']:>4} {r['fn']:>4}  {hit:>5}  {detail}")

    print("─" * 125)
    tp = totals["tp"]; fp = totals["fp"]; fn = totals["fn"]; n = totals["n_true"]
    prec = tp / (tp + fp) if tp + fp else 0
    rec  = tp / (tp + fn) if tp + fn else 0
    f1   = 2 * prec * rec / (prec + rec) if prec + rec else 0
    print(f"{'TOTAL':<20} {n:>6} {totals['n_pred']:>6} {tp:>4} {fp:>4} {fn:>4}  {tp}/{n}")
    print(f"Precision={prec:.3f}  Recall={rec:.3f}  F1={f1:.3f}  (collar=10ms, Typ3 excluded)")


if __name__ == "__main__":
    main()
