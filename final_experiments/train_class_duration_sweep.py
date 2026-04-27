#!/usr/bin/env python3
"""Classification training sweep over input_length values.

Trains one model per (bird, seed, input_length) and writes results to
  results_duration_sweep/{bird}/input_length_{L}/seed_{N}/results.json

SAFETY: never writes to final_experiments/results/ (protected).

Usage
-----
  # single run:
  uv run python3 final_experiments/train_class_duration_sweep.py \
      --bird ye04gr05 --seed 42 --input_length 14

  # all lengths for one bird (used by gcloud startup script):
  for L in 4 7 10 14 17 21 24 28 31 34; do
    for S in 42 123 456; do
      uv run python3 final_experiments/train_class_duration_sweep.py \
          --bird $BIRD --seed $S --input_length $L
    done
  done
"""
import argparse
import copy
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

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

from moove.models.CNN import CNN
from paper_experiments.metrics import classification_metrics

from final_experiments.config import (
    AUGMENTATION_PARAMS, BIRDS, CLASS_DATASET_PARAMS, CLASS_HYPERPARAMS,
    OUTPUT_DIR, REPLICATE_SEEDS, SAMPLE_RATE, TENSORBOARD_DIR,
)
from final_experiments.create_dataset import build_class_dataset, get_wav_files

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── Safety guard ──────────────────────────────────────────────────────
_SCRIPT_DIR    = Path(__file__).resolve().parent
_PROTECTED_DIR = (_SCRIPT_DIR / "results").resolve()
SWEEP_OUT_DIR  = (_SCRIPT_DIR / "results_duration_sweep").resolve()

def _assert_safe_output(path: Path) -> None:
    p = Path(path).resolve()
    if p.is_relative_to(_PROTECTED_DIR):
        raise RuntimeError(
            f"SAFETY ABORT: attempted write to protected dir {_PROTECTED_DIR}\n"
            f"  path={p}"
        )

# ── Augmentation helpers (inlined to avoid PyQt6 dep) ─────────────────

def _add_noise(spec, noise_level=0.0001):
    return spec + noise_level * np.random.randn(*spec.shape)

def _dynamic_range_compression(spec, compression_factor=0.5):
    return np.log1p(compression_factor * np.expm1(spec))

def _frequency_mask(spec, F=10, num_masks=1):
    cloned = spec.copy()
    nf = spec.shape[0]
    for _ in range(num_masks):
        f = max(1, min(int(np.random.uniform(1, min(F, nf))), nf - 1))
        ms = nf - f
        if ms <= 0:
            continue
        f0 = np.random.randint(0, ms)
        cloned[f0:f0 + f, :] = cloned.mean()
    return cloned

def _time_mask(spec, T=10, num_masks=1):
    cloned = spec.copy()
    nt = spec.shape[1]
    for _ in range(num_masks):
        t = max(1, min(int(np.random.uniform(1, min(T, nt))), nt - 1))
        ms = nt - t
        if ms <= 0:
            continue
        t0 = np.random.randint(0, ms)
        cloned[:, t0:t0 + t] = cloned.mean()
    return cloned

def augment_spectrogram(spec, aug_params=None):
    import random
    if aug_params is None:
        aug_params = {'enabled': True, 'probability': 0.2, 'noise_level': 0.0001,
                      'freq_mask_width': 10, 'time_mask_width': 10, 'compression_factor': 0.5}
    if not aug_params.get('enabled', True):
        return spec
    prob = float(aug_params.get('probability', 0.2))
    if np.random.rand() < prob:
        augmentations = [
            lambda s: _add_noise(s, float(aug_params.get('noise_level', 0.0001))),
            lambda s: _dynamic_range_compression(s, float(aug_params.get('compression_factor', 0.5))),
            lambda s: _frequency_mask(s, int(aug_params.get('freq_mask_width', 10))),
            lambda s: _time_mask(s, int(aug_params.get('time_mask_width', 10))),
        ]
        spec = random.choice(augmentations)(spec)
    return spec


# ── Main training function ─────────────────────────────────────────────

def train_class_sweep(bird: str, seed: int, input_length: int,
                      hyperparams=None, aug_params=None) -> dict:
    hp  = {**CLASS_HYPERPARAMS,   **(hyperparams or {})}
    aug = {**AUGMENTATION_PARAMS, **(aug_params  or {})}

    # Build dataset params with overridden input_length
    ds_params = {**CLASS_DATASET_PARAMS, "input_length": input_length}

    bird_cfg = BIRDS[bird]
    raw_dir  = bird_cfg["raw_data_dir"]

    run_dir = SWEEP_OUT_DIR / bird / f"input_length_{input_length}" / f"seed_{seed}"
    tb_dir  = Path(TENSORBOARD_DIR) / "class_duration_sweep" / bird / f"input_length_{input_length}" / f"seed_{seed}"

    # Safety: confirm we are NOT writing inside results/
    _assert_safe_output(run_dir)

    # Skip if already done
    results_path = run_dir / "results.json"
    if results_path.exists():
        log.info("Already done: %s — skipping.", results_path)
        with open(results_path) as f:
            return json.load(f)

    run_dir.mkdir(parents=True, exist_ok=True)
    tb_dir.mkdir(parents=True, exist_ok=True)

    log.info("== %s  seed=%d  input_length=%d ==", bird, seed, input_length)
    log.info("Raw data: %s", raw_dir)
    log.info("DS params: %s", ds_params)

    # ── Build dataset ─────────────────────────────────────────────────
    data = build_class_dataset(
        get_wav_files(raw_dir),
        exclude_labels=bird_cfg.get("exclude_labels"),
        merge_labels=bird_cfg.get("merge_labels"),
        **ds_params,
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

    def _preprocess(lst, target_time_len=2 * input_length):
        result = []
        for a in lst:
            t = F.pad(
                a.clone().detach().float().unsqueeze(0)
                if isinstance(a, torch.Tensor)
                else torch.tensor(a).float().unsqueeze(0),
                (0, 1, 0, 1)
            )
            cur = t.shape[-1]
            if cur < target_time_len:
                t = F.pad(t, (0, target_time_len - cur))
            elif cur > target_time_len:
                t = t[..., :target_time_len]
            result.append(t)
        return result

    # ── Train/val/test split (file-based when possible) ───────────────
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

    # ── Shuffle + normalise ───────────────────────────────────────────
    tr_d, tr_l = shuffle(tr_d, tr_l, random_state=seed)
    va_d, va_l = shuffle(va_d, va_l, random_state=seed)
    te_d, te_l = shuffle(te_d, te_l, random_state=seed)
    tr_d = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in tr_d]
    va_d = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in va_d]
    te_d = [(a - a.mean()) / a.std() if a.std() != 0 else a for a in te_d]

    bs = hp["batch_size"]
    tr_labels = torch.tensor(tr_l).long()
    va_labels = torch.tensor(va_l).long()
    te_labels = torch.tensor(te_l).long()
    train_loader = DataLoader(TensorDataset(torch.stack(tr_d), tr_labels), batch_size=bs, shuffle=True)
    val_loader   = DataLoader(TensorDataset(torch.stack(va_d), va_labels), batch_size=bs, shuffle=False)
    test_loader  = DataLoader(TensorDataset(torch.stack(te_d), te_labels), batch_size=bs, shuffle=False)

    # ── Device + model ────────────────────────────────────────────────
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    log.info("Device: %s  input_shape: %s", device, tr_d[0].shape)

    input_shape = tr_d[0].shape
    model = CNN(input_shape=input_shape, num_classes=num_classes).to(device)

    # Weighted CrossEntropy
    counts = Counter(tr_l)
    class_weights_vals = [len(tr_l) / (num_classes * counts.get(i, 1))
                          for i in range(num_classes)]
    class_weights = torch.tensor(class_weights_vals, dtype=torch.float, device=device)

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

    writer = SummaryWriter(log_dir=str(tb_dir))

    for epoch in range(hp["epochs"]):
        model.train()
        tl, nb = 0.0, 0
        for inp, lab in train_loader:
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

    # ── Confusion matrix ──────────────────────────────────────────────
    cm      = confusion_matrix(all_true, all_preds)
    cm_norm = cm.astype("float") / cm.sum(axis=1, keepdims=True)
    np.save(str(run_dir / "confusion_matrix.npy"),      cm)
    np.save(str(run_dir / "confusion_matrix_norm.npy"), cm_norm)

    # ── Checkpoint ───────────────────────────────────────────────────
    ckpt_path = run_dir / f"{bird}_class_L{input_length}_seed{seed}.pth"
    _assert_safe_output(ckpt_path)
    ckpt_meta = {
        **metadata,
        "label_to_int":  label_to_int,
        "int_to_label":  int_to_label,
        "hyperparameters": hp,
        "augmentation":  aug,
        "input_length":  input_length,
    }
    torch.save({"model": best_model, "metadata": ckpt_meta}, str(ckpt_path))
    log.info("Checkpoint: %s", ckpt_path)

    # ── results.json ─────────────────────────────────────────────────
    results = {
        "bird":         bird,
        "seed":         seed,
        "input_length": input_length,
        "input_length_ms": round(input_length * 64 / SAMPLE_RATE * 1000, 2),
        "test_accuracy":  test_acc,
        "classification": cls_metrics,
        "hyperparameters": hp,
        "class_weights": {int_to_label[i]: round(w, 4) for i, w in enumerate(class_weights_vals)},
        "n_train": len(tr_d),
        "n_val":   len(va_d),
        "n_test":  len(te_d),
        "num_classes": num_classes,
        "label_names": label_names,
        "history": history,
    }
    _assert_safe_output(results_path)
    with open(str(results_path), "w") as f:
        json.dump(results, f, indent=2)
    log.info("Results: %s", results_path)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bird",         required=True, choices=list(BIRDS.keys()))
    p.add_argument("--seed",         type=int, required=True)
    p.add_argument("--input_length", type=int, required=True,
                   help="Number of 64-sample chunks per syllable window")
    args = p.parse_args()
    train_class_sweep(args.bird, args.seed, args.input_length)


if __name__ == "__main__":
    main()
