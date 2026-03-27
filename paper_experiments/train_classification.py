#!/usr/bin/env python3
"""Standalone classification training for paper experiments.

Trains a CNN syllable classifier for one bird / one replicate, with:
  - TensorBoard logging  (#5)
  - Per-class and macro P / R / F1  (#1)
  - Data augmentation support
  - Confusion matrix SVG
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
from torch.utils.data import DataLoader, TensorDataset
from torch.utils.tensorboard import SummaryWriter

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from moove.models.CNN import CNN
from paper_experiments.augmentation import augment_spectrogram
from paper_experiments.config import (
    AUGMENTATION_PARAMS, BIRDS, CLASS_HYPERPARAMS, OUTPUT_DIR,
    SAMPLE_RATE, SAVE_CHECKPOINTS, TENSORBOARD_DIR, TRAINING_DATA_DIR,
)
from paper_experiments.metrics import classification_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


# ── Core training function ───────────────────────────────────────────

def train_classification(bird, seed, hyperparams=None, aug_params=None,
                         save_checkpoint=None):
    """Train one classification replicate and return metrics dict."""

    hp = {**CLASS_HYPERPARAMS, **(hyperparams or {})}
    aug = {**AUGMENTATION_PARAMS, **(aug_params or {})}
    if save_checkpoint is None:
        save_checkpoint = SAVE_CHECKPOINTS
    bird_cfg = BIRDS[bird]
    dataset_path = os.path.join(TRAINING_DATA_DIR, bird_cfg["class_dataset"])

    # ── Output dirs ──────────────────────────────────────────────────
    run_tag = f"class/{bird}/seed_{seed}"
    run_dir = os.path.join(OUTPUT_DIR, "class", bird, f"seed_{seed}")
    os.makedirs(run_dir, exist_ok=True)
    tb_dir = os.path.join(TENSORBOARD_DIR, run_tag)

    log.info("== %s  seed=%d  (classification) ==", bird, seed)
    log.info("Dataset : %s", dataset_path)
    log.info("Params  : %s", hp)

    # ── Load data ────────────────────────────────────────────────────
    with open(dataset_path, "rb") as f:
        data = pickle.load(f)

    df = data["dataframe"]
    metadata = data["metadata"]

    df["taf_unflattend_spectrogram"] = (
        df["taf_unflattend_spectrogram"].apply(np.array).apply(torch.tensor)
    )
    labels_raw = df["label"].tolist()

    unique_labels = sorted(set(labels_raw))
    label_to_int = {lab: i for i, lab in enumerate(unique_labels)}
    int_to_label = {i: lab for lab, i in label_to_int.items()}
    num_classes = len(unique_labels)

    def preprocess(data_list):
        return [F.pad(a.clone().detach().float().unsqueeze(0) if isinstance(a, torch.Tensor)
                      else torch.tensor(a).float().unsqueeze(0), (0, 1, 0, 1)) for a in data_list]

    # ── Split by file groups when possible ───────────────────────────
    file_groups = df.groupby("file")
    filenames = list(file_groups.groups.keys())
    inputs_all = df["taf_unflattend_spectrogram"].tolist()
    labels_int = [label_to_int[l] for l in labels_raw]

    if len(filenames) >= 7:
        train_files, temp_files = train_test_split(filenames, test_size=0.3, random_state=seed)
        val_files, test_files = train_test_split(temp_files, test_size=0.5, random_state=seed)

        df_train = df[df["file"].isin(train_files)]
        df_val = df[df["file"].isin(val_files)]
        df_test = df[df["file"].isin(test_files)]

        train_data = preprocess(df_train["taf_unflattend_spectrogram"].tolist())
        train_labels = [label_to_int[l] for l in df_train["label"].tolist()]
        val_data = preprocess(df_val["taf_unflattend_spectrogram"].tolist())
        val_labels = [label_to_int[l] for l in df_val["label"].tolist()]
        test_data = preprocess(df_test["taf_unflattend_spectrogram"].tolist())
        test_labels = [label_to_int[l] for l in df_test["label"].tolist()]
    else:
        input_data = preprocess(inputs_all)
        labels_t = torch.tensor(labels_int).long()
        train_data, temp_data, train_labels, temp_labels = train_test_split(
            input_data, labels_t.tolist(), test_size=0.3, stratify=labels_t.tolist(), random_state=seed)
        val_data, test_data, val_labels, test_labels = train_test_split(
            temp_data, temp_labels, test_size=0.5, stratify=temp_labels, random_state=seed)

    input_shape = train_data[0].shape

    # ── Compute syllable duration from spectrogram params ────────────
    nperseg_val = metadata.get("nperseg", 64)
    noverlap_val = metadata.get("noverlap", 32)
    hop = nperseg_val - noverlap_val
    raw_time_bins = [np.array(s).shape[-1] for s in df["taf_unflattend_spectrogram"]]
    avg_syllable_duration_s = np.mean([(tb - 1) * hop + nperseg_val for tb in raw_time_bins]) / SAMPLE_RATE

    def _class_duration(n_syllables):
        return n_syllables * avg_syllable_duration_s

    # ── Shuffle + normalise per-spectrogram ──────────────────────────
    train_data, train_labels = shuffle(train_data, train_labels, random_state=seed)
    val_data, val_labels = shuffle(val_data, val_labels, random_state=seed)
    test_data, test_labels = shuffle(test_data, test_labels, random_state=seed)

    train_data = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in train_data]
    val_data = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in val_data]
    test_data = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in test_data]

    # ── Data stats BEFORE downsampling ────────────────────────────────
    def _class_dist(labels):
        """Count syllables per class."""
        from collections import Counter
        counts = Counter(labels)
        return {int_to_label.get(k, str(k)): v for k, v in sorted(counts.items())}

    dist_train_before = _class_dist(train_labels)
    dist_val_before = _class_dist(val_labels)
    dist_test_before = _class_dist(test_labels)

    stats_before = {
        "n_train": len(train_data), "n_val": len(val_data), "n_test": len(test_data),
        "n_total": len(train_data) + len(val_data) + len(test_data),
        "duration_train_s": _class_duration(len(train_data)),
        "duration_val_s": _class_duration(len(val_data)),
        "duration_test_s": _class_duration(len(test_data)),
        "duration_total_s": _class_duration(len(train_data) + len(val_data) + len(test_data)),
        "avg_syllable_duration_ms": avg_syllable_duration_s * 1000,
        "class_distribution_train": dist_train_before,
        "class_distribution_val": dist_val_before,
        "class_distribution_test": dist_test_before,
    }
    log.info("Data BEFORE downsampling: train=%d (%.1fs)  val=%d (%.1fs)  test=%d (%.1fs)  total=%d (%.1fs)",
             stats_before["n_train"], stats_before["duration_train_s"],
             stats_before["n_val"], stats_before["duration_val_s"],
             stats_before["n_test"], stats_before["duration_test_s"],
             stats_before["n_total"], stats_before["duration_total_s"])
    log.info("Class dist (train before): %s", dist_train_before)

    # ── Optional downsampling ────────────────────────────────────────
    def downsample(data, labels):
        tmp = pd.DataFrame({"data": data, "labels": labels})
        min_sz = tmp["labels"].value_counts().min()
        parts = [g.sample(min_sz, random_state=seed) for _, g in tmp.groupby("labels")]
        ds = pd.concat(parts)
        return ds["data"].tolist(), ds["labels"].tolist()

    if hp["downsampling"]:
        train_data, train_labels = downsample(train_data, train_labels)
        val_data, val_labels = downsample(val_data, val_labels)
        # Test set is NOT downsampled: evaluate on real class distribution.

    # ── Data stats AFTER downsampling (or same as before if disabled) ─
    dist_train_after = _class_dist(train_labels if isinstance(train_labels, list) else train_labels.tolist())
    dist_val_after = _class_dist(val_labels if isinstance(val_labels, list) else val_labels.tolist())
    dist_test_after = _class_dist(test_labels if isinstance(test_labels, list) else test_labels.tolist())

    stats_after = {
        "n_train": len(train_data), "n_val": len(val_data), "n_test": len(test_data),
        "n_total": len(train_data) + len(val_data) + len(test_data),
        "duration_train_s": _class_duration(len(train_data)),
        "duration_val_s": _class_duration(len(val_data)),
        "duration_test_s": _class_duration(len(test_data)),
        "duration_total_s": _class_duration(len(train_data) + len(val_data) + len(test_data)),
        "avg_syllable_duration_ms": avg_syllable_duration_s * 1000,
        "class_distribution_train": dist_train_after,
        "class_distribution_val": dist_val_after,
        "class_distribution_test": dist_test_after,
    }
    log.info("Data AFTER  downsampling: train=%d (%.1fs)  val=%d (%.1fs)  test=%d (%.1fs)  total=%d (%.1fs)",
             stats_after["n_train"], stats_after["duration_train_s"],
             stats_after["n_val"], stats_after["duration_val_s"],
             stats_after["n_test"], stats_after["duration_test_s"],
             stats_after["n_total"], stats_after["duration_total_s"])
    log.info("Class dist (train after):  %s", dist_train_after)

    train_labels = torch.tensor(train_labels).long()
    val_labels = torch.tensor(val_labels).long()
    test_labels = torch.tensor(test_labels).long()

    bs = hp["batch_size"]
    train_loader = DataLoader(TensorDataset(torch.stack(train_data), train_labels),
                              batch_size=bs, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.stack(val_data), val_labels),
                            batch_size=bs, shuffle=False)
    test_loader = DataLoader(TensorDataset(torch.stack(test_data), test_labels),
                             batch_size=bs, shuffle=False)

    # ── Model / optimiser ────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CNN(input_shape=input_shape, num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=hp["learning_rate"])

    best_val_loss = float("inf")
    patience_ctr = 0
    best_model = None

    def calc_acc(loader):
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for inp, lab in loader:
                inp, lab = inp.to(device), lab.to(device)
                _, pred = torch.max(model(inp), 1)
                total += lab.size(0)
                correct += (pred == lab).sum().item()
        model.train()
        return correct / total if total > 0 else 0.0

    # ── Training loop with TensorBoard (#5) ──────────────────────────
    writer = SummaryWriter(log_dir=tb_dir)
    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    for epoch in range(hp["epochs"]):
        model.train()
        running_loss, n_batches = 0.0, 0
        for inp, lab in train_loader:
            augmented = [torch.from_numpy(augment_spectrogram(t.cpu().numpy(), aug)).float()
                         for t in inp]
            augmented = torch.stack(augmented).to(device)
            lab = lab.to(device)
            optimizer.zero_grad()
            out = model(augmented)
            loss = criterion(out, lab)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            n_batches += 1

        train_loss = running_loss / n_batches

        model.eval()
        val_loss_sum, vn = 0.0, 0
        with torch.no_grad():
            for inp, lab in val_loader:
                inp, lab = inp.to(device), lab.to(device)
                out = model(inp)
                val_loss_sum += criterion(out, lab).item()
                vn += 1
        val_loss = val_loss_sum / vn

        train_acc = calc_acc(train_loader)
        val_acc = calc_acc(val_loader)

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
            log.info("Epoch %3d/%d  train_loss=%.4f  val_loss=%.4f  "
                     "train_acc=%.4f  val_acc=%.4f",
                     epoch + 1, hp["epochs"], train_loss, val_loss, train_acc, val_acc)

    writer.close()

    if best_model is None:
        best_model = model

    # ── Test evaluation ──────────────────────────────────────────────
    best_model.eval()
    best_model.to(device)
    all_preds, all_true = [], []
    with torch.no_grad():
        for inp, lab in test_loader:
            inp, lab = inp.to(device), lab.to(device)
            _, pred = torch.max(best_model(inp), 1)
            all_preds.extend(pred.cpu().numpy().tolist())
            all_true.extend(lab.cpu().numpy().tolist())

    test_acc = np.mean(np.array(all_preds) == np.array(all_true))
    label_names = [int_to_label[i] for i in range(num_classes)]
    cls_metrics = classification_metrics(all_true, all_preds, label_names=label_names)
    log.info("Test accuracy=%.4f  macro F1=%.4f", test_acc, cls_metrics["macro"]["f1"])

    # ── Confusion matrix ─────────────────────────────────────────────
    cm = confusion_matrix(all_true, all_preds)
    cm_norm = cm.astype("float") / cm.sum(axis=1, keepdims=True)
    plt.figure(figsize=(10, 7))
    sns.heatmap(cm_norm, annot=True, fmt=".2%", cmap="Blues",
                xticklabels=label_names, yticklabels=label_names)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(f"{bird} seed={seed} – Normalized Confusion Matrix")
    cm_path = os.path.join(run_dir, "confusion_matrix.svg")
    plt.savefig(cm_path)
    plt.close()
    log.info("Confusion matrix: %s", cm_path)

    # ── Save checkpoint (if enabled) ─────────────────────────────────
    if save_checkpoint:
        ckpt_metadata = {
            **metadata,
            "label_to_int": label_to_int,
            "int_to_label": int_to_label,
            "hyperparameters": hp,
            "augmentation": aug,
        }
        ckpt_path = os.path.join(run_dir, f"{bird}_class_seed{seed}.pth")
        torch.save({"model": best_model, "metadata": ckpt_metadata}, ckpt_path)
        log.info("Checkpoint saved: %s", ckpt_path)

    # ── Collect results ──────────────────────────────────────────────
    results = {
        "bird": bird,
        "seed": seed,
        "test_accuracy": float(test_acc),
        "classification": cls_metrics,
        "hyperparameters": hp,
        "augmentation": aug,
        "spectrogram_params": {
            "nperseg": nperseg_val, "noverlap": noverlap_val,
            "hop": hop, "sample_rate": SAMPLE_RATE,
        },
        "data_stats_before_downsampling": stats_before,
        "data_stats_after_downsampling": stats_after,
        "n_train": stats_after["n_train"],
        "n_val": stats_after["n_val"],
        "n_test": stats_after["n_test"],
        "num_classes": num_classes,
        "label_names": label_names,
        "history": history,
    }

    results_path = os.path.join(run_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results saved: %s", results_path)

    return results


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train classification model for one bird")
    parser.add_argument("--bird", required=True, choices=list(BIRDS.keys()))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-checkpoint", action="store_true", default=None)
    args = parser.parse_args()

    save_ckpt = args.save_checkpoint if args.save_checkpoint is not None else SAVE_CHECKPOINTS
    train_classification(args.bird, args.seed, save_checkpoint=save_ckpt)


if __name__ == "__main__":
    main()
