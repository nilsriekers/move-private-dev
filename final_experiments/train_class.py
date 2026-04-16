#!/usr/bin/env python3
"""Classification training for final_experiments (Experiment 4).

Uses moove models and augment_spectrogram directly from
moove.utils.training_utils so training is provably identical to the GUI.

Outputs per seed×bird:
  results/<bird>/class/seed_<N>/results.json
  results/<bird>/class/seed_<N>/confusion_matrix.svg
  results/<bird>/class/seed_<N>/confusion_matrix.npy   ← NEW: raw counts
  results/<bird>/class/seed_<N>/<bird>_class_seed<N>.pth
  results/runs/class/<bird>/seed_<N>/  (TensorBoard)

Usage
-----
  uv run python3 final_experiments/train_class.py --bird ye04gr05 --seed 42
"""
import argparse
import copy
import json
import logging
import os
from collections import Counter
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── moove imports ─────────────────────────────────────────────────────
from moove.models.CNN import CNN
from moove.utils.training_utils import augment_spectrogram

# Metrics from paper_experiments (no GUI dependency)
from paper_experiments.metrics import classification_metrics

from final_experiments.config import (
    AUGMENTATION_PARAMS, BIRDS, CLASS_DATASET_PARAMS, CLASS_HYPERPARAMS,
    OUTPUT_DIR, REPLICATE_SEEDS, SAMPLE_RATE, TENSORBOARD_DIR,
)
from final_experiments.create_dataset import build_class_dataset, get_wav_files

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def train_class(bird, seed, hyperparams=None, aug_params=None):
    hp  = {**CLASS_HYPERPARAMS,    **(hyperparams or {})}
    aug = {**AUGMENTATION_PARAMS,  **(aug_params  or {})}

    bird_cfg = BIRDS[bird]
    raw_dir  = bird_cfg["raw_data_dir"]
    run_dir  = os.path.join(OUTPUT_DIR, bird, "class", f"seed_{seed}")
    tb_dir   = os.path.join(TENSORBOARD_DIR, "class", bird, f"seed_{seed}")
    os.makedirs(run_dir, exist_ok=True)

    log.info("== %s  seed=%d  (classification) ==", bird, seed)
    log.info("Raw data: %s", raw_dir)
    log.info("Params  : %s", hp)

    # ── Build dataset ─────────────────────────────────────────────────
    data = build_class_dataset(
        get_wav_files(raw_dir),
        exclude_labels=bird_cfg.get("exclude_labels"),
        **CLASS_DATASET_PARAMS,
    )
    df       = data["dataframe"]
    metadata = data["metadata"]

    df["taf_unflattend_spectrogram"] = (
        df["taf_unflattend_spectrogram"].apply(np.array).apply(torch.tensor)
    )
    labels_raw    = df["label"].tolist()
    unique_labels = sorted(set(labels_raw))
    label_to_int  = {l: i for i, l in enumerate(unique_labels)}
    int_to_label  = {i: l for l, i in label_to_int.items()}
    num_classes   = len(unique_labels)

    def _preprocess(lst):
        return [F.pad(
            a.clone().detach().float().unsqueeze(0)
            if isinstance(a, torch.Tensor)
            else torch.tensor(a).float().unsqueeze(0),
            (0, 1, 0, 1)
        ) for a in lst]

    # ── Split by file when possible (identical to GUI) ────────────────
    filenames = list(df.groupby("file").groups.keys())

    if len(filenames) >= 7:
        tr_f, tmp_f = train_test_split(filenames, test_size=0.3, random_state=seed)
        va_f, te_f  = train_test_split(tmp_f,      test_size=0.5, random_state=seed)
        def _by(fs):
            sub = df[df["file"].isin(fs)]
            return (_preprocess(sub["taf_unflattend_spectrogram"].tolist()),
                    [label_to_int[l] for l in sub["label"].tolist()])
        tr_d, tr_l = _by(tr_f)
        va_d, va_l = _by(va_f)
        te_d, te_l = _by(te_f)
    else:
        inputs_all = _preprocess(df["taf_unflattend_spectrogram"].tolist())
        labels_int = [label_to_int[l] for l in labels_raw]
        tr_d, tmp_d, tr_l, tmp_l = train_test_split(
            inputs_all, labels_int, test_size=0.3,
            stratify=labels_int, random_state=seed)
        va_d, te_d, va_l, te_l = train_test_split(
            tmp_d, tmp_l, test_size=0.5,
            stratify=tmp_l, random_state=seed)

    # ── Duration helper ───────────────────────────────────────────────
    nperseg  = metadata.get("nperseg", 64)
    noverlap = metadata.get("noverlap", 32)
    hop      = nperseg - noverlap
    raw_bins = [np.array(s).shape[-1] for s in df["taf_unflattend_spectrogram"]]
    avg_syl_s = np.mean([(tb - 1) * hop + nperseg for tb in raw_bins]) / SAMPLE_RATE

    def _dur(n): return n * avg_syl_s

    def _dist(labels):
        c = Counter(labels)
        return {int_to_label.get(k, str(k)): v for k, v in sorted(c.items())}

    stats_before = {
        "n_train": len(tr_d), "n_val": len(va_d), "n_test": len(te_d),
        "n_total": len(tr_d) + len(va_d) + len(te_d),
        "duration_train_s": _dur(len(tr_d)),
        "duration_val_s":   _dur(len(va_d)),
        "duration_test_s":  _dur(len(te_d)),
        "duration_total_s": _dur(len(tr_d) + len(va_d) + len(te_d)),
        "avg_syllable_duration_ms": avg_syl_s * 1000,
        "class_distribution_train": _dist(tr_l),
        "class_distribution_val":   _dist(va_l),
        "class_distribution_test":  _dist(te_l),
    }

    # ── Shuffle + normalise (identical to GUI) ────────────────────────
    tr_d, tr_l = shuffle(tr_d, tr_l, random_state=seed)
    va_d, va_l = shuffle(va_d, va_l, random_state=seed)
    te_d, te_l = shuffle(te_d, te_l, random_state=seed)
    tr_d = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in tr_d]
    va_d = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in va_d]
    te_d = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in te_d]

    # ── Downsampling (identical to GUI) ───────────────────────────────
    def _downsample(data, labels):
        tmp = pd.DataFrame({"data": data, "labels": labels})
        mn  = tmp["labels"].value_counts().min()
        parts = [g.sample(mn, random_state=seed) for _, g in tmp.groupby("labels")]
        ds = pd.concat(parts)
        return ds["data"].tolist(), ds["labels"].tolist()

    if hp["downsampling"]:
        tr_d, tr_l = _downsample(tr_d, tr_l)
        va_d, va_l = _downsample(va_d, va_l)
        # Test NOT downsampled

    stats_after = {
        "n_train": len(tr_d), "n_val": len(va_d), "n_test": len(te_d),
        "n_total": len(tr_d) + len(va_d) + len(te_d),
        "duration_train_s": _dur(len(tr_d)),
        "duration_val_s":   _dur(len(va_d)),
        "duration_test_s":  _dur(len(te_d)),
        "duration_total_s": _dur(len(tr_d) + len(va_d) + len(te_d)),
        "avg_syllable_duration_ms": avg_syl_s * 1000,
        "class_distribution_train": _dist(tr_l),
        "class_distribution_val":   _dist(va_l),
        "class_distribution_test":  _dist(te_l),
    }
    log.info("After DS: train=%d (%.1fs)  val=%d  test=%d",
             stats_after["n_train"], stats_after["duration_train_s"],
             stats_after["n_val"], stats_after["n_test"])

    tr_labels = torch.tensor(tr_l).long()
    va_labels = torch.tensor(va_l).long()
    te_labels = torch.tensor(te_l).long()

    bs = hp["batch_size"]
    train_loader = DataLoader(TensorDataset(torch.stack(tr_d), tr_labels), batch_size=bs, shuffle=True)
    val_loader   = DataLoader(TensorDataset(torch.stack(va_d), va_labels), batch_size=bs, shuffle=False)
    test_loader  = DataLoader(TensorDataset(torch.stack(te_d), te_labels), batch_size=bs, shuffle=False)

    # ── Model (moove.models.CNN) ──────────────────────────────────────
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    log.info("Device: %s", device)

    input_shape = tr_d[0].shape
    model = CNN(input_shape=input_shape, num_classes=num_classes).to(device)

    # Weighted CrossEntropy: weight[c] = n_total / (n_classes * count_c)
    # Addresses class imbalance without discarding data (reviewer suggestion).
    counts = Counter(tr_l)
    class_weights_vals = [len(tr_l) / (num_classes * counts.get(i, 1))
                          for i in range(num_classes)]
    class_weights = torch.tensor(class_weights_vals, dtype=torch.float, device=device)
    log.info("Class weights: %s", {int_to_label[i]: f"{w:.3f}"
                                   for i, w in enumerate(class_weights_vals)})

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=hp["learning_rate"])

    best_val_loss = float("inf")
    patience_ctr  = 0
    best_model    = None
    history       = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    def _calc_acc(loader):
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for inp, lab in loader:
                inp, lab = inp.to(device), lab.to(device)
                _, pred = torch.max(model(inp), 1)
                total   += lab.size(0)
                correct += (pred == lab).sum().item()
        model.train()
        return correct / total if total > 0 else 0.0

    writer = SummaryWriter(log_dir=tb_dir)

    for epoch in range(hp["epochs"]):
        model.train()
        tl, nb = 0.0, 0
        for inp, lab in train_loader:
            # augment_spectrogram from moove.utils.training_utils
            augmented = [torch.from_numpy(augment_spectrogram(t.cpu().numpy(), aug)).float()
                         for t in inp]
            augmented = torch.stack(augmented).to(device)
            lab = lab.to(device)
            optimizer.zero_grad()
            out  = model(augmented)
            loss = criterion(out, lab)
            loss.backward()
            optimizer.step()
            tl += loss.item()
            nb += 1
        tl /= nb

        model.eval()
        vl, vn = 0.0, 0
        with torch.no_grad():
            for inp, lab in val_loader:
                inp, lab = inp.to(device), lab.to(device)
                vl += criterion(model(inp), lab).item()
                vn += 1
        vl /= vn

        ta = _calc_acc(train_loader)
        va = _calc_acc(val_loader)

        writer.add_scalars("loss",     {"train": tl, "val": vl}, epoch)
        writer.add_scalars("accuracy", {"train": ta, "val": va}, epoch)
        history["train_loss"].append(tl)
        history["val_loss"].append(vl)
        history["train_acc"].append(ta)
        history["val_acc"].append(va)

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
                     epoch + 1, tl, vl, ta, va)

    writer.close()
    if best_model is None:
        best_model = model

    # ── Test evaluation ───────────────────────────────────────────────
    best_model.eval(); best_model.to(device)
    all_preds, all_true = [], []
    with torch.no_grad():
        for inp, lab in test_loader:
            inp, lab = inp.to(device), lab.to(device)
            _, pred = torch.max(best_model(inp), 1)
            all_preds.extend(pred.cpu().numpy().tolist())
            all_true.extend(lab.cpu().numpy().tolist())

    test_acc    = float(np.mean(np.array(all_preds) == np.array(all_true)))
    label_names = [int_to_label[i] for i in range(num_classes)]
    cls_metrics = classification_metrics(all_true, all_preds, label_names=label_names)
    log.info("Test accuracy=%.4f  macro F1=%.4f", test_acc, cls_metrics["macro"]["f1"])

    # ── Confusion matrix — SVG + NPY ─────────────────────────────────
    cm      = confusion_matrix(all_true, all_preds)
    cm_norm = cm.astype("float") / cm.sum(axis=1, keepdims=True)

    plt.figure(figsize=(10, 7))
    sns.heatmap(cm_norm, annot=True, fmt=".2%", cmap="Blues",
                xticklabels=label_names, yticklabels=label_names)
    plt.xlabel("Predicted"); plt.ylabel("True")
    plt.title(f"{bird} seed={seed} – Normalized Confusion Matrix")
    plt.savefig(os.path.join(run_dir, "confusion_matrix.svg"))
    plt.close()

    np.save(os.path.join(run_dir, "confusion_matrix.npy"), cm)
    np.save(os.path.join(run_dir, "confusion_matrix_norm.npy"), cm_norm)
    log.info("Confusion matrix saved (SVG + NPY)")

    # ── Save .pth ─────────────────────────────────────────────────────
    ckpt_meta = {
        **metadata,
        "label_to_int":  label_to_int,
        "int_to_label":  int_to_label,
        "hyperparameters": hp,
        "augmentation":  aug,
    }
    ckpt_path = os.path.join(run_dir, f"{bird}_class_seed{seed}.pth")
    torch.save({"model": best_model, "metadata": ckpt_meta}, ckpt_path)
    log.info("Checkpoint: %s", ckpt_path)

    # ── Save results.json ─────────────────────────────────────────────
    results = {
        "bird": bird, "seed": seed,
        "test_accuracy": test_acc,
        "classification": cls_metrics,
        "hyperparameters": hp,
        "augmentation": aug,
        "class_weights": {int_to_label[i]: round(w, 4) for i, w in enumerate(class_weights_vals)},
        "spectrogram_params": {
            "nperseg": nperseg, "noverlap": noverlap,
            "hop": hop, "sample_rate": SAMPLE_RATE,
        },
        "data_stats_before_downsampling": stats_before,
        "data_stats_after_downsampling":  stats_after,
        "n_train": stats_after["n_train"],
        "n_val":   stats_after["n_val"],
        "n_test":  stats_after["n_test"],
        "num_classes": num_classes,
        "label_names": label_names,
        "history": history,
    }
    with open(os.path.join(run_dir, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results: %s/results.json", run_dir)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bird", required=True, choices=list(BIRDS.keys()))
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    train_class(args.bird, args.seed)


if __name__ == "__main__":
    main()
