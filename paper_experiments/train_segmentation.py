#!/usr/bin/env python3
"""Standalone segmentation training for paper experiments.

Trains a ConvMLP binary segmenter for one bird / one replicate, with:
  - TensorBoard logging  (#5)
  - Framewise P / R / F1  (#1)
  - Collar-based segmentation metrics  (#3)
  - Configurable .pth saving  (disk-space guard)

Can be called directly or via run_all.py for multiple replicates (#4).
"""
import argparse
import copy
import json
import logging
import os
import pickle
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset
from torch.utils.tensorboard import SummaryWriter

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from moove.models.ConvMLP import ConvMLP
from paper_experiments.config import (
    BIRDS, COLLAR_VALUES_MS, OUTPUT_DIR, SAMPLE_RATE,
    SAVE_CHECKPOINTS, SEG_HYPERPARAMS, SLIDING_WINDOW_PARAMS,
    TENSORBOARD_DIR, TRAINING_DATA_DIR,
)
from paper_experiments.metrics import (
    apply_sliding_window, collar_ms_to_frames,
    collar_segmentation_metrics, framewise_metrics,
    onset_collar_segmentation_metrics,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


# ── Core training function ───────────────────────────────────────────

def train_segmentation(bird, seed, hyperparams=None, save_checkpoint=None):
    """Train one segmentation replicate and return metrics dict."""

    hp = {**SEG_HYPERPARAMS, **(hyperparams or {})}
    if save_checkpoint is None:
        save_checkpoint = SAVE_CHECKPOINTS
    bird_cfg = BIRDS[bird]
    dataset_path = os.path.join(TRAINING_DATA_DIR, bird_cfg["seg_dataset"])

    # ── Output dirs ──────────────────────────────────────────────────
    run_tag = f"seg/{bird}/seed_{seed}"
    run_dir = os.path.join(OUTPUT_DIR, "seg", bird, f"seed_{seed}")
    os.makedirs(run_dir, exist_ok=True)
    tb_dir = os.path.join(TENSORBOARD_DIR, run_tag)

    log.info("== %s  seed=%d ==", bird, seed)
    log.info("Dataset : %s", dataset_path)
    log.info("Params  : %s", hp)

    # ── Load data ────────────────────────────────────────────────────
    with open(dataset_path, "rb") as f:
        data_dict = pickle.load(f)

    features = np.array(data_dict["features"])
    metadata = data_dict["metadata"]
    chunk_size = metadata.get("chunk_size", 64)

    if features.ndim != 2:
        raise ValueError("Empty or malformed dataset")

    file_indices = np.unique(features[:, 0])

    # ── Split (by file when possible) ────────────────────────────────
    def filter_by_files(data, file_set):
        return data[np.isin(data[:, 0], file_set)]

    if len(file_indices) >= 7:
        train_files, temp_files = train_test_split(
            file_indices, test_size=0.3, random_state=seed)
        val_files, test_files = train_test_split(
            temp_files, test_size=0.5, random_state=seed)
        train_data = filter_by_files(features, train_files)
        val_data = filter_by_files(features, val_files)
        test_data = filter_by_files(features, test_files)
    else:
        train_data, temp_data = train_test_split(
            features, test_size=0.3, random_state=seed)
        val_data, test_data = train_test_split(
            temp_data, test_size=0.5, random_state=seed)

    # strip file-index column
    train_data = train_data[:, 1:]
    val_data = val_data[:, 1:]
    test_data = test_data[:, 1:]

    X_train = train_data[:, :-1].astype("float32")
    y_train = train_data[:, -1].astype("float32")
    X_val = val_data[:, :-1].astype("float32")
    y_val = val_data[:, -1].astype("float32")
    X_test = test_data[:, :-1].astype("float32")
    y_test = test_data[:, -1].astype("float32")

    # ── Data stats BEFORE downsampling ────────────────────────────────
    def _seg_duration(n_samples):
        return n_samples * chunk_size / SAMPLE_RATE

    def _count_segments(labels):
        """Count onset/offset transitions in a binary label sequence."""
        arr = np.asarray(labels)
        changes = np.diff(arr)
        n_onsets = int(np.sum(changes == 1))
        # also count if sequence starts with 1
        if len(arr) > 0 and arr[0] == 1:
            n_onsets += 1
        return n_onsets

    n_seg_train = _count_segments(y_train)
    n_seg_val = _count_segments(y_val)
    n_seg_test = _count_segments(y_test)

    stats_before = {
        "n_train": len(X_train), "n_val": len(X_val), "n_test": len(X_test),
        "n_total": len(X_train) + len(X_val) + len(X_test),
        "duration_train_s": _seg_duration(len(X_train)),
        "duration_val_s": _seg_duration(len(X_val)),
        "duration_test_s": _seg_duration(len(X_test)),
        "duration_total_s": _seg_duration(len(X_train) + len(X_val) + len(X_test)),
        "n_syllables_train": n_seg_train,
        "n_syllables_val": n_seg_val,
        "n_syllables_test": n_seg_test,
        "n_syllables_total": n_seg_train + n_seg_val + n_seg_test,
    }
    log.info("Data BEFORE downsampling: train=%d (%.1fs, %d syl)  val=%d (%.1fs, %d syl)  test=%d (%.1fs, %d syl)  total=%d (%.1fs, %d syl)",
             stats_before["n_train"], stats_before["duration_train_s"], n_seg_train,
             stats_before["n_val"], stats_before["duration_val_s"], n_seg_val,
             stats_before["n_test"], stats_before["duration_test_s"], n_seg_test,
             stats_before["n_total"], stats_before["duration_total_s"],
             n_seg_train + n_seg_val + n_seg_test)

    # ── Optional downsampling ────────────────────────────────────────
    def downsample(data, labels):
        unique, counts = np.unique(labels, return_counts=True)
        mc = int(counts.min())
        d, l = [], []
        for u in unique:
            idx = np.where(labels == u)[0]
            rng = np.random.RandomState(seed)
            chosen = rng.choice(idx, size=mc, replace=False)
            d.append(data[chosen])
            l.append(labels[chosen])
        return np.vstack(d), np.hstack(l)

    if hp["downsampling"]:
        X_train, y_train = downsample(X_train, y_train)
        X_val, y_val = downsample(X_val, y_val)
        # Test set is NOT downsampled: evaluate on real data distribution
        # and preserve temporal ordering for collar/segment metrics.

    # ── Data stats AFTER downsampling (or same as before if disabled) ─
    n_seg_train_af = _count_segments(y_train)
    n_seg_val_af = _count_segments(y_val)
    n_seg_test_af = _count_segments(y_test)

    stats_after = {
        "n_train": len(X_train), "n_val": len(X_val), "n_test": len(X_test),
        "n_total": len(X_train) + len(X_val) + len(X_test),
        "duration_train_s": _seg_duration(len(X_train)),
        "duration_val_s": _seg_duration(len(X_val)),
        "duration_test_s": _seg_duration(len(X_test)),
        "duration_total_s": _seg_duration(len(X_train) + len(X_val) + len(X_test)),
        "n_syllables_train": n_seg_train_af,
        "n_syllables_val": n_seg_val_af,
        "n_syllables_test": n_seg_test_af,
        "n_syllables_total": n_seg_train_af + n_seg_val_af + n_seg_test_af,
    }
    log.info("Data AFTER  downsampling: train=%d (%.1fs, %d syl)  val=%d (%.1fs, %d syl)  test=%d (%.1fs, %d syl)  total=%d (%.1fs, %d syl)",
             stats_after["n_train"], stats_after["duration_train_s"], n_seg_train_af,
             stats_after["n_val"], stats_after["duration_val_s"], n_seg_val_af,
             stats_after["n_test"], stats_after["duration_test_s"], n_seg_test_af,
             stats_after["n_total"], stats_after["duration_total_s"],
             n_seg_train_af + n_seg_val_af + n_seg_test_af)

    # ── Tensors + normalisation ──────────────────────────────────────
    X_tr = torch.tensor(X_train)
    y_tr = torch.tensor(y_train).unsqueeze(1)
    X_va = torch.tensor(X_val)
    y_va = torch.tensor(y_val).unsqueeze(1)
    X_te = torch.tensor(X_test)
    y_te = torch.tensor(y_test).unsqueeze(1)

    mean, std = X_tr.mean(), X_tr.std()
    X_tr = ((X_tr - mean) / std).nan_to_num(0.0)
    X_va = ((X_va - mean) / std).nan_to_num(0.0)
    X_te = ((X_te - mean) / std).nan_to_num(0.0)

    bs = hp["batch_size"]
    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=bs, shuffle=True, drop_last=True)
    val_loader = DataLoader(TensorDataset(X_va, y_va), batch_size=bs, shuffle=False, drop_last=True)
    test_loader = DataLoader(TensorDataset(X_te, y_te), batch_size=bs, shuffle=False, drop_last=False)

    # ── Model / optimiser ────────────────────────────────────────────
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    log.info("Device: %s", device)
    model = ConvMLP(input_size=X_train.shape[1]).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=hp["learning_rate"])

    best_val_loss = float("inf")
    patience_ctr = 0
    best_model = None

    def calc_acc(outputs, labels):
        return ((torch.sigmoid(outputs) > 0.5) == labels).float().mean().item()

    # ── Training loop with TensorBoard (#5) ──────────────────────────
    writer = SummaryWriter(log_dir=tb_dir)
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    for epoch in range(hp["epochs"]):
        model.train()
        train_loss, train_acc, n_batches = 0.0, 0.0, 0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            train_acc += calc_acc(outputs, labels)
            n_batches += 1

        train_loss /= n_batches
        train_acc /= n_batches

        # Validation
        model.eval()
        val_loss, val_acc, vn = 0.0, 0.0, 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                val_loss += criterion(outputs, labels).item()
                val_acc += calc_acc(outputs, labels)
                vn += 1
        val_loss /= vn
        val_acc /= vn

        writer.add_scalars("loss", {"train": train_loss, "val": val_loss}, epoch)
        writer.add_scalars("accuracy", {"train": train_acc, "val": val_acc}, epoch)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model = copy.deepcopy(model)
            patience_ctr = 0
        else:
            patience_ctr += 1

        if patience_ctr >= hp["early_stopping_patience"]:
            log.info("Early stopping at epoch %d", epoch + 1)
            break

        if (epoch + 1) % 10 == 0 or epoch == 0:
            log.info("Epoch %3d/%d  train_loss=%.4f  val_loss=%.4f  train_acc=%.4f  val_acc=%.4f",
                     epoch + 1, hp["epochs"], train_loss, val_loss, train_acc, val_acc)

    writer.close()

    if best_model is None:
        best_model = model

    # ── Test evaluation ──────────────────────────────────────────────
    best_model.eval()
    best_model.to(device)
    all_preds, all_true = [], []
    test_loss_sum, tn = 0.0, 0
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = best_model(inputs)
            test_loss_sum += criterion(outputs, labels).item()
            preds = (torch.sigmoid(outputs) > 0.5).long()
            all_preds.extend(preds.cpu().numpy().flatten().tolist())
            all_true.extend(labels.cpu().numpy().flatten().tolist())
            tn += 1

    test_loss = test_loss_sum / tn

    # ── #1  Framewise P / R / F1 ─────────────────────────────────────
    fw = framewise_metrics(all_true, all_preds)
    log.info("Framewise  P=%.4f  R=%.4f  F1=%.4f", fw["precision"], fw["recall"], fw["f1"])

    # ── #3  Collar-based segmentation metrics (raw predictions) ──────
    collar_results = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, chunk_size, SAMPLE_RATE)
        cm = collar_segmentation_metrics(all_true, all_preds, cf)
        collar_results[f"@{cms}ms"] = cm
        log.info("Collar(raw)  %2dms  P=%.4f  R=%.4f  F1=%.4f  (tp=%d/%d pred, %d true)",
                 cms, cm["precision"], cm["recall"], cm["f1"],
                 cm["tp"], cm["n_pred"], cm["n_true"])

    # ── #3b  Collar metrics AFTER sliding window (matches inference) ──
    sw = SLIDING_WINDOW_PARAMS
    smoothed_preds, n_pred_segments = apply_sliding_window(
        all_preds, **sw)
    # Count true segments directly from ground truth (don't smooth GT)
    n_true_segments = _count_segments(all_true)

    fw_smoothed = framewise_metrics(all_true, smoothed_preds)
    log.info("Framewise(sw)  P=%.4f  R=%.4f  F1=%.4f",
             fw_smoothed["precision"], fw_smoothed["recall"], fw_smoothed["f1"])
    log.info("Segments: %d predicted (smoothed), %d true",
             n_pred_segments, n_true_segments)

    collar_smoothed = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, chunk_size, SAMPLE_RATE)
        cm = collar_segmentation_metrics(all_true, smoothed_preds, cf)
        collar_smoothed[f"@{cms}ms"] = cm
        log.info("Collar(sw)   %2dms  P=%.4f  R=%.4f  F1=%.4f  (tp=%d/%d pred, %d true)",
                 cms, cm["precision"], cm["recall"], cm["f1"],
                 cm["tp"], cm["n_pred"], cm["n_true"])

    # ── Onset-only collar metrics (raw + smoothed) ────────────────────
    onset_collar_raw = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, chunk_size, SAMPLE_RATE)
        cm = onset_collar_segmentation_metrics(all_true, all_preds, cf)
        onset_collar_raw[f"@{cms}ms"] = cm
        log.info("OnsetCol(raw) %2dms  P=%.4f  R=%.4f  F1=%.4f", cms, cm["precision"], cm["recall"], cm["f1"])

    onset_collar_smoothed = {}
    for cms in COLLAR_VALUES_MS:
        cf = collar_ms_to_frames(cms, chunk_size, SAMPLE_RATE)
        cm = onset_collar_segmentation_metrics(all_true, smoothed_preds, cf)
        onset_collar_smoothed[f"@{cms}ms"] = cm
        log.info("OnsetCol(sw)  %2dms  P=%.4f  R=%.4f  F1=%.4f", cms, cm["precision"], cm["recall"], cm["f1"])

    # ── Save checkpoint (if enabled) ─────────────────────────────────
    if save_checkpoint:
        ckpt_metadata = {
            **metadata,
            "mean": mean.item(), "std": std.item(),
            "hyperparameters": hp,
        }
        ckpt_path = os.path.join(run_dir, f"{bird}_seg_seed{seed}.pth")
        torch.save({"model": best_model, "metadata": ckpt_metadata}, ckpt_path)
        log.info("Checkpoint saved: %s", ckpt_path)

    # ── Save predictions for future metric computation ──────────────
    preds_path = os.path.join(run_dir, "predictions.npz")
    np.savez_compressed(preds_path,
                        y_true=np.array(all_true, dtype=np.int8),
                        y_pred=np.array(all_preds, dtype=np.int8),
                        y_pred_smoothed=np.array(smoothed_preds, dtype=np.int8))
    log.info("Predictions saved: %s", preds_path)

    # ── Collect results ──────────────────────────────────────────────
    results = {
        "bird": bird,
        "seed": seed,
        "test_loss": float(test_loss),
        "test_accuracy": float(np.mean(np.array(all_preds) == np.array(all_true))),
        "framewise": fw,
        "collar": collar_results,
        "onset_collar": onset_collar_raw,
        "sliding_window_params": sw,
        "framewise_smoothed": fw_smoothed,
        "collar_smoothed": collar_smoothed,
        "onset_collar_smoothed": onset_collar_smoothed,
        "n_pred_segments_smoothed": n_pred_segments,
        "n_true_segments_smoothed": n_true_segments,
        "hyperparameters": hp,
        "chunk_size": chunk_size,
        "sample_rate": SAMPLE_RATE,
        "data_stats_before_downsampling": stats_before,
        "data_stats_after_downsampling": stats_after,
        "n_train": stats_after["n_train"],
        "n_val": stats_after["n_val"],
        "n_test": stats_after["n_test"],
        "history": history,
    }

    results_path = os.path.join(run_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results saved: %s", results_path)

    return results


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train segmentation model for one bird")
    parser.add_argument("--bird", required=True, choices=list(BIRDS.keys()))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-checkpoint", action="store_true", default=None)
    args = parser.parse_args()

    save_ckpt = args.save_checkpoint if args.save_checkpoint is not None else SAVE_CHECKPOINTS
    train_segmentation(args.bird, args.seed, save_checkpoint=save_ckpt)


if __name__ == "__main__":
    main()
