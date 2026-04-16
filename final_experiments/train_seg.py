#!/usr/bin/env python3
"""Segmentation training for final_experiments (Experiment 4).

Uses moove models and helper functions directly so the training is
provably identical to what MooveTAF runs in the GUI.

Outputs per seed×bird (suffix _overlap when --overlap_chunks is set):
  results/<bird>/seg/seed_<N>/results[_overlap].json
  results/<bird>/seg/seed_<N>/predictions[_overlap].npz
  results/<bird>/seg/seed_<N>/<bird>_seg_seed<N>[_overlap].pth
  results/runs/seg[_overlap]/<bird>/seed_<N>/  (TensorBoard)

Usage
-----
  uv run python3 final_experiments/train_seg.py --bird ye04gr05 --seed 42
  uv run python3 final_experiments/train_seg.py --bird ye04gr05 --seed 42 --overlap_chunks
  uv run python3 final_experiments/train_seg.py --bird ye04gr05 --seed 42 --eval_only
  uv run python3 final_experiments/train_seg.py --bird ye04gr05 --seed 42 --overlap_chunks --eval_only
"""
import argparse
import copy
import json
import logging
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset
from torch.utils.tensorboard import SummaryWriter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── moove imports ─────────────────────────────────────────────────────
from moove.models.ConvMLP import ConvMLP

# Metrics from paper_experiments (same module, no GUI dependency)
from paper_experiments.metrics import (
    apply_sliding_window,
    collar_ms_to_frames,
    collar_segmentation_metrics,
    framewise_metrics,
    offset_collar_segmentation_metrics,
    onset_collar_segmentation_metrics,
)

from final_experiments.config import (
    BIRDS, COLLAR_VALUES_MS, OUTPUT_DIR, REPLICATE_SEEDS,
    SAMPLE_RATE, SEG_DATASET_PARAMS, SEG_HYPERPARAMS, SLIDING_WINDOW_PARAMS,
    TENSORBOARD_DIR,
)
from final_experiments.create_dataset import build_seg_dataset, get_wav_files

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def _apply_sliding_window_per_file(all_preds, te_file_ids, sw_params):
    """Apply sliding window independently per test file to avoid boundary artifacts.

    Returns smoothed predictions (same length as all_preds) and total segment count.
    """
    smoothed = [0] * len(all_preds)
    n_segs = 0
    for fid in np.unique(te_file_ids):
        idxs = np.where(te_file_ids == fid)[0]
        file_preds = [all_preds[i] for i in idxs]
        file_sw, file_n = apply_sliding_window(file_preds, **sw_params)
        n_segs += file_n
        for k, i in enumerate(idxs):
            smoothed[i] = file_sw[k]
    return smoothed, n_segs


def _compute_metrics(all_true, all_preds, smoothed_preds, chunk_size, sw_params):
    """Compute all segmentation metrics (framewise + collar for raw and SW predictions)."""
    fw = framewise_metrics(all_true, all_preds)
    fw_sw = framewise_metrics(all_true, smoothed_preds)
    n_true_seg = sum(1 for i in range(len(all_true))
                     if all_true[i] == 1 and (i == 0 or all_true[i - 1] == 0))
    n_pred_seg = sum(1 for i in range(len(smoothed_preds))
                     if smoothed_preds[i] == 1 and (i == 0 or smoothed_preds[i - 1] == 0))

    collar_raw, collar_sw = {}, {}
    onset_raw, onset_sw   = {}, {}
    offset_raw, offset_sw = {}, {}

    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, chunk_size, SAMPLE_RATE)
        tag = f"@{cms}ms"
        collar_raw[tag] = collar_segmentation_metrics(all_true, all_preds,     cf)
        collar_sw[tag]  = collar_segmentation_metrics(all_true, smoothed_preds, cf)
        onset_raw[tag]  = onset_collar_segmentation_metrics(all_true, all_preds,     cf)
        onset_sw[tag]   = onset_collar_segmentation_metrics(all_true, smoothed_preds, cf)
        offset_raw[tag] = offset_collar_segmentation_metrics(all_true, all_preds,     cf)
        offset_sw[tag]  = offset_collar_segmentation_metrics(all_true, smoothed_preds, cf)

    return {
        "framewise": fw, "framewise_smoothed": fw_sw,
        "collar": collar_raw, "collar_smoothed": collar_sw,
        "onset_collar": onset_raw, "onset_collar_smoothed": onset_sw,
        "offset_collar": offset_raw, "offset_collar_smoothed": offset_sw,
        "sliding_window_params": sw_params,
        "n_true_segments_smoothed": n_true_seg,
        "n_pred_segments_smoothed": n_pred_seg,
    }


def _log_metrics(metrics):
    fw   = metrics["framewise"]
    fw_sw = metrics["framewise_smoothed"]
    log.info("Framewise (raw) P=%.4f  R=%.4f  F1=%.4f", fw["precision"], fw["recall"], fw["f1"])
    log.info("Framewise (sw)  P=%.4f  R=%.4f  F1=%.4f", fw_sw["precision"], fw_sw["recall"], fw_sw["f1"])
    for cms in COLLAR_VALUES_MS:
        tag = f"@{cms}ms"
        cr  = metrics["collar"][tag]
        cs  = metrics["collar_smoothed"][tag]
        or_ = metrics["onset_collar"][tag]
        osw = metrics["onset_collar_smoothed"][tag]
        ofr = metrics["offset_collar"][tag]
        ofs = metrics["offset_collar_smoothed"][tag]
        log.info("Collar(raw)  %2dms  P=%.4f  R=%.4f  F1=%.4f", cms, cr["precision"], cr["recall"], cr["f1"])
        log.info("Collar(sw)   %2dms  P=%.4f  R=%.4f  F1=%.4f", cms, cs["precision"], cs["recall"], cs["f1"])
        log.info("OnsetCol raw %2dms  F1=%.4f   sw  F1=%.4f", cms, or_["f1"], osw["f1"])
        log.info("OnsetCol sw  %2dms  detected=%d  missed=%d  fp=%d (multi=%d  spurious=%d)  n_true=%d",
                 cms, osw["tp"], osw["fn"], osw["fp"],
                 osw["double_detections"], osw["pure_fp"], osw["n_true"])
        log.info("OffsetCol raw %2dms  F1=%.4f   sw  F1=%.4f", cms, ofr["f1"], ofs["f1"])


def train_seg(bird, seed, hyperparams=None, overlap_chunks=False):
    hp = {**SEG_HYPERPARAMS, **(hyperparams or {})}
    suffix = "_overlap" if overlap_chunks else ""

    bird_cfg  = BIRDS[bird]
    raw_dir   = bird_cfg["raw_data_dir"]
    run_dir   = os.path.join(OUTPUT_DIR, bird, "seg", f"seed_{seed}")
    tb_dir    = os.path.join(TENSORBOARD_DIR, f"seg{suffix}", bird, f"seed_{seed}")
    os.makedirs(run_dir, exist_ok=True)

    log.info("== %s  seed=%d  overlap_chunks=%s  (segmentation) ==", bird, seed, overlap_chunks)
    log.info("Raw data: %s", raw_dir)
    log.info("Params  : %s", hp)

    # ── Build dataset ─────────────────────────────────────────────────
    file_paths = get_wav_files(raw_dir)
    ds_params  = {**SEG_DATASET_PARAMS, "overlap_chunks": overlap_chunks}
    data_dict  = build_seg_dataset(file_paths, **ds_params)
    features   = np.array(data_dict["features"])
    metadata   = data_dict["metadata"]
    chunk_size = metadata.get("chunk_size", 64)
    log.info("Dataset params: %s", ds_params)

    if features.ndim != 2:
        raise ValueError(f"Empty or malformed dataset for {bird}")

    file_indices = np.unique(features[:, 0])

    # ── Train/val/test split (by file when possible) ──────────────────
    def _by_files(data, fs):
        return data[np.isin(data[:, 0], fs)]

    used_file_split = len(file_indices) >= 7
    if used_file_split:
        tr_files, tmp = train_test_split(file_indices, test_size=0.3, random_state=seed)
        va_files, te_files = train_test_split(tmp, test_size=0.5, random_state=seed)
        tr = _by_files(features, tr_files)
        va = _by_files(features, va_files)
        te = _by_files(features, te_files)
        test_file_basenames = sorted(
            os.path.basename(file_paths[int(i)]) for i in te_files
        )
    else:
        tr, tmp = train_test_split(features, test_size=0.3, random_state=seed)
        va, te  = train_test_split(tmp, test_size=0.5, random_state=seed)
        test_file_basenames = []

    # Capture per-frame file IDs for val and test sets BEFORE dropping the file-index col.
    va_file_ids = va[:, 0].astype(int)
    te_file_ids = te[:, 0].astype(int)

    tr, va, te = tr[:, 1:], va[:, 1:], te[:, 1:]
    X_tr, y_tr = tr[:, :-1].astype("float32"), tr[:, -1].astype("float32")
    X_va, y_va = va[:, :-1].astype("float32"), va[:, -1].astype("float32")
    X_te, y_te = te[:, :-1].astype("float32"), te[:, -1].astype("float32")

    def _dur(n): return n * chunk_size / SAMPLE_RATE

    def _count_seg(labels):
        arr = np.asarray(labels)
        n = int(np.sum(np.diff(arr) == 1))
        if len(arr) > 0 and arr[0] == 1:
            n += 1
        return n

    stats_before = {
        "n_train": len(X_tr), "n_val": len(X_va), "n_test": len(X_te),
        "n_total": len(X_tr) + len(X_va) + len(X_te),
        "duration_train_s": _dur(len(X_tr)),
        "duration_val_s":   _dur(len(X_va)),
        "duration_test_s":  _dur(len(X_te)),
        "duration_total_s": _dur(len(X_tr) + len(X_va) + len(X_te)),
        "n_syllables_train": _count_seg(y_tr),
        "n_syllables_val":   _count_seg(y_va),
        "n_syllables_test":  _count_seg(y_te),
    }

    # ── Downsampling (identical to GUI training_utils.downsample_data) ─
    def _downsample(data, labels):
        unique, counts = np.unique(labels, return_counts=True)
        mc = int(counts.min())
        dd, dl = [], []
        rng = np.random.RandomState(seed)
        for u in unique:
            idx = np.where(labels == u)[0]
            dd.append(data[rng.choice(idx, mc, replace=False)])
            dl.append(labels[rng.choice(idx, mc, replace=False)])
        return np.vstack(dd), np.hstack(dl)

    if hp["downsampling"]:
        X_tr, y_tr = _downsample(X_tr, y_tr)
        X_va, y_va = _downsample(X_va, y_va)
        # Test set NOT downsampled

    stats_after = {
        "n_train": len(X_tr), "n_val": len(X_va), "n_test": len(X_te),
        "n_total": len(X_tr) + len(X_va) + len(X_te),
        "duration_train_s": _dur(len(X_tr)),
        "duration_val_s":   _dur(len(X_va)),
        "duration_test_s":  _dur(len(X_te)),
        "duration_total_s": _dur(len(X_tr) + len(X_va) + len(X_te)),
        "n_syllables_train": _count_seg(y_tr),
        "n_syllables_val":   _count_seg(y_va),
        "n_syllables_test":  _count_seg(y_te),
    }
    log.info("After DS: train=%d (%.1fs)  val=%d (%.1fs)  test=%d (%.1fs)",
             stats_after["n_train"], stats_after["duration_train_s"],
             stats_after["n_val"],   stats_after["duration_val_s"],
             stats_after["n_test"],  stats_after["duration_test_s"])

    # ── Tensors + normalisation (identical to GUI) ────────────────────
    Xtr = torch.tensor(X_tr)
    ytr = torch.tensor(y_tr).unsqueeze(1)
    Xva = torch.tensor(X_va)
    yva = torch.tensor(y_va).unsqueeze(1)
    Xte = torch.tensor(X_te)
    yte = torch.tensor(y_te).unsqueeze(1)

    mean, std = Xtr.mean(), Xtr.std()
    Xtr = ((Xtr - mean) / std).nan_to_num(0.0)
    Xva = ((Xva - mean) / std).nan_to_num(0.0)
    Xte = ((Xte - mean) / std).nan_to_num(0.0)

    bs = hp["batch_size"]
    train_loader = DataLoader(TensorDataset(Xtr, ytr), batch_size=bs, shuffle=True,  drop_last=True)
    val_loader   = DataLoader(TensorDataset(Xva, yva), batch_size=bs, shuffle=False, drop_last=True)
    test_loader  = DataLoader(TensorDataset(Xte, yte), batch_size=bs, shuffle=False, drop_last=False)

    # ── Model (moove.models.ConvMLP) ──────────────────────────────────
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    log.info("Device: %s", device)

    model = ConvMLP(input_size=X_tr.shape[1]).to(device)

    # Weighted BCE: pos_weight = n_negative / n_positive (addresses class imbalance
    # without discarding data, as suggested by reviewer).
    n_pos = float((y_tr == 1).sum())
    n_neg = float((y_tr == 0).sum())
    pos_weight_val = n_neg / n_pos if n_pos > 0 else 1.0
    pos_weight = torch.tensor([pos_weight_val], device=device)
    log.info("Class balance: pos=%d  neg=%d  pos_weight=%.3f", int(n_pos), int(n_neg), pos_weight_val)

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = optim.Adam(model.parameters(), lr=hp["learning_rate"])

    best_val_loss = float("inf")
    patience_ctr  = 0
    best_model    = None
    history       = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    def _acc(outputs, labels):
        return ((torch.sigmoid(outputs) > 0.5) == labels).float().mean().item()

    writer = SummaryWriter(log_dir=tb_dir)

    for epoch in range(hp["epochs"]):
        model.train()
        tl, ta, nb = 0.0, 0.0, 0
        for inp, lab in train_loader:
            inp, lab = inp.to(device), lab.to(device)
            optimizer.zero_grad()
            out  = model(inp)
            loss = criterion(out, lab)
            loss.backward()
            optimizer.step()
            tl += loss.item()
            ta += _acc(out, lab)
            nb += 1
        tl /= nb; ta /= nb

        model.eval()
        vl, va_acc, vn = 0.0, 0.0, 0
        with torch.no_grad():
            for inp, lab in val_loader:
                inp, lab = inp.to(device), lab.to(device)
                out = model(inp)
                vl     += criterion(out, lab).item()
                va_acc += _acc(out, lab)
                vn += 1
        vl /= vn; va_acc /= vn

        writer.add_scalars("loss",     {"train": tl, "val": vl},     epoch)
        writer.add_scalars("accuracy", {"train": ta, "val": va_acc}, epoch)
        history["train_loss"].append(tl)
        history["val_loss"].append(vl)
        history["train_acc"].append(ta)
        history["val_acc"].append(va_acc)

        if vl < best_val_loss:
            best_val_loss = vl
            best_model    = copy.deepcopy(model)
            patience_ctr  = 0
        else:
            patience_ctr += 1
            if patience_ctr >= hp["early_stopping_patience"]:
                log.info("Early stopping at epoch %d", epoch + 1)
                break

        if (epoch + 1) % 10 == 0 or epoch == 0:
            log.info("Epoch %3d  tl=%.4f  vl=%.4f  ta=%.4f  va=%.4f",
                     epoch + 1, tl, vl, ta, va_acc)

    writer.close()
    if best_model is None:
        best_model = model

    # ── Val threshold tuning ──────────────────────────────────────────
    # Find the threshold maximising onset-collar @10ms SW F1 on the val set.
    # Using val (not test) keeps this methodologically clean for paper reporting.
    sw = SLIDING_WINDOW_PARAMS
    best_model.eval(); best_model.to(device)
    val_eval_loader = DataLoader(TensorDataset(Xva, yva), batch_size=bs,
                                 shuffle=False, drop_last=False)
    val_probs, val_true_lab = [], []
    with torch.no_grad():
        for inp, lab in val_eval_loader:
            inp, lab = inp.to(device), lab.to(device)
            val_probs.extend(torch.sigmoid(best_model(inp)).cpu().numpy().flatten())
            val_true_lab.extend(lab.cpu().numpy().flatten())

    n_va = len(val_probs)   # may be < len(va_file_ids) if drop_last cut some
    va_fids = va_file_ids[:n_va]

    best_thr, best_thr_f1 = 0.5, -1.0
    for thr in np.round(np.arange(0.05, 0.96, 0.05), 2):
        vpreds = [int(p >= thr) for p in val_probs]
        if used_file_split:
            vsm, _ = _apply_sliding_window_per_file(vpreds, va_fids, sw)
        else:
            vsm, _ = apply_sliding_window(vpreds, **sw)
        vf1 = _compute_metrics(val_true_lab, vpreds, vsm, chunk_size, sw
                               )["onset_collar_smoothed"]["@10ms"]["f1"]
        if vf1 > best_thr_f1:
            best_thr_f1, best_thr = vf1, float(thr)
    log.info("Val threshold tuning: best_threshold=%.2f  onset@10ms_sw_val_F1=%.4f",
             best_thr, best_thr_f1)

    # ── Test evaluation ───────────────────────────────────────────────
    best_model.eval(); best_model.to(device)
    all_preds, all_true = [], []
    with torch.no_grad():
        for inp, lab in test_loader:
            inp, lab = inp.to(device), lab.to(device)
            preds = (torch.sigmoid(best_model(inp)) >= best_thr).long()
            all_preds.extend(preds.cpu().numpy().flatten())
            all_true.extend(lab.cpu().numpy().flatten())

    # ── Sliding window: per-file when file-based split was used ──────
    if used_file_split:
        smoothed_preds, n_pred_seg = _apply_sliding_window_per_file(
            all_preds, te_file_ids, sw)
        log.info("Sliding window applied per-file (%d test files)", len(test_file_basenames))
    else:
        smoothed_preds, n_pred_seg = apply_sliding_window(all_preds, **sw)
        log.info("Sliding window applied globally (frame-level split)")

    metrics = _compute_metrics(all_true, all_preds, smoothed_preds, chunk_size, sw)
    _log_metrics(metrics)

    # ── Save .pth ─────────────────────────────────────────────────────
    ckpt_meta = {**metadata, "mean": mean.item(), "std": std.item(),
                 "hyperparameters": hp, "overlap_chunks": overlap_chunks,
                 "tuned_threshold": best_thr, "tuned_threshold_val_f1": best_thr_f1}
    ckpt_path = os.path.join(run_dir, f"{bird}_seg_seed{seed}{suffix}.pth")
    torch.save({"model": best_model, "metadata": ckpt_meta}, ckpt_path)
    log.info("Checkpoint: %s", ckpt_path)

    # ── Save predictions + test features (enables --eval_only) ───────
    np.savez_compressed(
        os.path.join(run_dir, f"predictions{suffix}.npz"),
        y_true         = np.array(all_true,       dtype=np.int8),
        y_pred         = np.array(all_preds,       dtype=np.int8),
        y_pred_smoothed= np.array(smoothed_preds,  dtype=np.int8),
        X_te           = X_te,                   # pre-normalisation, float32
        te_file_ids    = te_file_ids.astype(np.int32),
    )
    log.info("Predictions + test features saved to predictions%s.npz", suffix)

    # ── Save results.json ─────────────────────────────────────────────
    results = {
        "bird": bird, "seed": seed,
        "overlap_chunks": overlap_chunks,
        "tuned_threshold": best_thr,
        "tuned_threshold_val_f1": best_thr_f1,
        "test_accuracy": float(np.mean(np.array(all_preds) == np.array(all_true))),
        **metrics,
        "hyperparameters": hp,
        "pos_weight": pos_weight_val,
        "chunk_size": chunk_size,
        "sample_rate": SAMPLE_RATE,
        "used_file_split": used_file_split,
        "test_files": test_file_basenames,
        "data_stats_before_downsampling": stats_before,
        "data_stats_after_downsampling":  stats_after,
        "n_train": stats_after["n_train"],
        "n_val":   stats_after["n_val"],
        "n_test":  stats_after["n_test"],
        "history": history,
    }
    results_path = os.path.join(run_dir, f"results{suffix}.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results: %s", results_path)
    return results


def eval_seg(bird, seed, overlap_chunks=False, threshold_search=False):
    """Re-evaluate a trained model on the saved test set without retraining.

    Loads the checkpoint and the saved test features from predictions[_overlap].npz,
    then recomputes all metrics. Useful for trying different thresholds or
    post-processing parameters without re-running training.

    With threshold_search=True: oracle analysis — best threshold given test labels.
    Do NOT report oracle results as primary paper numbers.
    """
    suffix    = "_overlap" if overlap_chunks else ""
    run_dir   = os.path.join(OUTPUT_DIR, bird, "seg", f"seed_{seed}")
    ckpt_path = os.path.join(run_dir, f"{bird}_seg_seed{seed}{suffix}.pth")
    npz_path  = os.path.join(run_dir, f"predictions{suffix}.npz")

    log.info("== %s  seed=%d  overlap_chunks=%s  threshold_search=%s  (eval only) ==",
             bird, seed, overlap_chunks, threshold_search)

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model    = ckpt["model"]
    meta     = ckpt["metadata"]
    mean_val = meta["mean"]
    std_val  = meta["std"]
    chunk_size = meta.get("chunk_size", 64)
    # Use the val-tuned threshold if present, otherwise fall back to 0.5.
    threshold = meta.get("tuned_threshold", 0.5)
    log.info("Using threshold=%.2f (tuned_val_f1=%.4f)",
             threshold, meta.get("tuned_threshold_val_f1", float("nan")))

    data = np.load(npz_path)
    X_te        = data["X_te"]
    y_te        = data["y_true"]   # saved as y_true in predictions.npz
    te_file_ids = data["te_file_ids"]

    # Load existing results to know split type + test files
    results_path = os.path.join(run_dir, f"results{suffix}.json")
    with open(results_path) as f:
        saved = json.load(f)
    used_file_split     = saved.get("used_file_split", False)
    test_file_basenames = saved.get("test_files", [])

    # Normalise with training stats
    Xte = torch.tensor(X_te)
    Xte = ((Xte - mean_val) / std_val).nan_to_num(0.0)
    yte = torch.tensor(y_te).unsqueeze(1)

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    model.eval(); model.to(device)
    test_loader = DataLoader(TensorDataset(Xte, yte), batch_size=256,
                             shuffle=False, drop_last=False)

    # Collect raw probabilities (needed for threshold search)
    all_probs, all_true = [], []
    with torch.no_grad():
        for inp, lab in test_loader:
            inp, lab = inp.to(device), lab.to(device)
            probs = torch.sigmoid(model(inp))
            all_probs.extend(probs.cpu().numpy().flatten())
            all_true.extend(lab.cpu().numpy().flatten())

    sw = SLIDING_WINDOW_PARAMS

    def _eval_at_threshold(thr):
        preds = [int(p >= thr) for p in all_probs]
        if used_file_split:
            smoothed, _ = _apply_sliding_window_per_file(preds, te_file_ids, sw)
        else:
            smoothed, _ = apply_sliding_window(preds, **sw)
        return _compute_metrics(all_true, preds, smoothed, chunk_size, sw)

    if threshold_search:
        thresholds = np.round(np.arange(0.05, 0.96, 0.05), 2)
        rows = []
        log.info("── Oracle threshold search on TEST set (not for paper reporting) ──")
        log.info("  thr   fw_F1   onset@10ms_sw  onset@20ms_sw  collar@10ms_sw   tp   fn   fp  (onset@10ms sw)")
        for thr in thresholds:
            m = _eval_at_threshold(thr)
            fw_f1   = m["framewise"]["f1"]
            on10    = m["onset_collar_smoothed"]["@10ms"]
            on20    = m["onset_collar_smoothed"]["@20ms"]
            col10   = m["collar_smoothed"]["@10ms"]["f1"]
            log.info("  %.2f  %.4f  %.4f          %.4f          %.4f         %4d %4d %4d",
                     thr, fw_f1, on10["f1"], on20["f1"], col10,
                     on10["tp"], on10["fn"], on10["fp"])
            rows.append({"threshold": float(thr), "framewise_f1": fw_f1,
                         "onset_collar_10ms_sw_f1": on10["f1"],
                         "onset_collar_10ms_sw_tp": on10["tp"],
                         "onset_collar_10ms_sw_fn": on10["fn"],
                         "onset_collar_10ms_sw_fp": on10["fp"],
                         "onset_collar_10ms_sw_n_true": on10["n_true"],
                         "onset_collar_20ms_sw_f1": on20["f1"],
                         "collar_10ms_sw_f1": col10})

        # Best per metric
        best_fw   = max(rows, key=lambda r: r["framewise_f1"])
        best_on10 = max(rows, key=lambda r: r["onset_collar_10ms_sw_f1"])
        best_on20 = max(rows, key=lambda r: r["onset_collar_20ms_sw_f1"])
        log.info("Best framewise F1:         thr=%.2f  F1=%.4f", best_fw["threshold"],   best_fw["framewise_f1"])
        log.info("Best onset@10ms sw F1:     thr=%.2f  F1=%.4f  tp=%d  fn=%d  fp=%d  n_true=%d",
                 best_on10["threshold"], best_on10["onset_collar_10ms_sw_f1"],
                 best_on10["onset_collar_10ms_sw_tp"], best_on10["onset_collar_10ms_sw_fn"],
                 best_on10["onset_collar_10ms_sw_fp"], best_on10["onset_collar_10ms_sw_n_true"])
        log.info("Best onset@20ms sw F1:     thr=%.2f  F1=%.4f", best_on20["threshold"], best_on20["onset_collar_20ms_sw_f1"])

        out = {"bird": bird, "seed": seed, "overlap_chunks": overlap_chunks,
               "oracle_note": "Test labels used to find optimal threshold — do not report as primary result.",
               "thresholds": rows,
               "best_framewise_f1": best_fw,
               "best_onset_collar_10ms_sw_f1": best_on10,
               "best_onset_collar_20ms_sw_f1": best_on20}
        out_path = os.path.join(run_dir, f"threshold_search{suffix}.json")
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        log.info("Threshold search saved: %s", out_path)
        return out

    # Standard eval at val-tuned threshold (or 0.5 fallback)
    all_preds = [int(p >= threshold) for p in all_probs]
    if used_file_split:
        smoothed_preds, _ = _apply_sliding_window_per_file(all_preds, te_file_ids, sw)
        log.info("Sliding window: per-file  (%d files)", len(test_file_basenames))
    else:
        smoothed_preds, _ = apply_sliding_window(all_preds, **sw)

    metrics = _compute_metrics(all_true, all_preds, smoothed_preds, chunk_size, sw)
    _log_metrics(metrics)
    log.info("Test files: %s", test_file_basenames)
    return metrics


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bird", required=True, choices=list(BIRDS.keys()))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--overlap_chunks", action="store_true",
                   help="Use overlapping chunks (step=1) instead of non-overlapping (step=hist_size). "
                        "Outputs saved with _overlap suffix so results are never overwritten.")
    p.add_argument("--eval_only", action="store_true",
                   help="Skip training; re-evaluate saved checkpoint on stored test features.")
    p.add_argument("--threshold_search", action="store_true",
                   help="Oracle threshold analysis on test set (requires --eval_only). "
                        "Tests thresholds 0.05–0.95. Do not report as primary paper result.")
    args = p.parse_args()
    if args.eval_only:
        eval_seg(args.bird, args.seed, overlap_chunks=args.overlap_chunks,
                 threshold_search=args.threshold_search)
    else:
        train_seg(args.bird, args.seed, overlap_chunks=args.overlap_chunks)


if __name__ == "__main__":
    main()
