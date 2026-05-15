#!/usr/bin/env python3
"""Generate Table 1 (Segmentation) and Table 2 (Classification) from final_experiments/results/."""
import json
import os
import numpy as np

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

BIRD_IDS = ["ye00pu07", "bu04bk04", "gy07bu07", "br08pk08", "ye04gr05"]
BIRD_LABELS = {
    "ye00pu07": "Bird 1", "bu04bk04": "Bird 2", "gy07bu07": "Bird 3",
    "br08pk08": "Bird 4", "ye04gr05": "Bird 5",
}
SEEDS = [42, 123, 456]


def ms(vals):
    a = np.array(vals)
    return f"{a.mean():.3f} ± {a.std():.3f}"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def table1_segmentation():
    print("=" * 90)
    print("TABLE 1 — Segmentation (framewise_smoothed + onset_collar_smoothed with SW)")
    print("=" * 90)
    header = (f"{'Bird':<8} {'#Syl':>6} {'Dur(s)':>8} {'Ep':>4}  "
              f"{'FW-P':>16} {'FW-R':>16} {'FW-F1':>16} "
              f"{'Col@10ms':>16} {'Col@20ms':>16}")
    print(header)
    print("-" * len(header))

    for bird in BIRD_IDS:
        fw_p, fw_r, fw_f1 = [], [], []
        col10, col20 = [], []
        syl_total, dur_total, epochs = [], [], []

        for seed in SEEDS:
            p = os.path.join(RESULTS_DIR, bird, "seg", f"seed_{seed}", "results.json")
            if not os.path.isfile(p):
                continue
            r = load_json(p)
            fw_p.append(r["framewise_smoothed"]["precision"])
            fw_r.append(r["framewise_smoothed"]["recall"])
            fw_f1.append(r["framewise_smoothed"]["f1"])
            col10.append(r["onset_collar_smoothed"]["@10ms"]["f1"])
            col20.append(r["onset_collar_smoothed"]["@20ms"]["f1"])
            ds = r["data_stats_before_downsampling"]
            syl_total.append(ds["n_syllables_train"])
            dur_total.append(ds["duration_train_s"])
            epochs.append(len(r["history"]["train_loss"]))

        if not fw_f1:
            print(f"{BIRD_LABELS[bird]:<8}  (no results)")
            continue

        n_syl = int(round(np.mean(syl_total)))
        n_dur = np.mean(dur_total)
        n_ep  = int(round(np.mean(epochs)))
        print(f"{BIRD_LABELS[bird]:<8} {n_syl:>6} {n_dur:>8.1f} {n_ep:>4}  "
              f"{ms(fw_p):>16} {ms(fw_r):>16} {ms(fw_f1):>16} "
              f"{ms(col10):>16} {ms(col20):>16}")

    print()


def table2_classification():
    print("=" * 90)
    print("TABLE 2 — Classification (weighted CrossEntropy, 3 replicates)")
    print("=" * 90)
    header = (f"{'Bird':<8} {'#Cls':>5} {'#Syl':>6} {'Ep':>4}  "
              f"{'Accuracy':>16} {'Mac-P':>16} {'Mac-R':>16} {'Mac-F1':>16}")
    print(header)
    print("-" * len(header))

    for bird in BIRD_IDS:
        acc, mac_p, mac_r, mac_f1 = [], [], [], []
        syl_total, epochs, n_cls = [], [], []

        for seed in SEEDS:
            p = os.path.join(RESULTS_DIR, bird, "class", f"seed_{seed}", "results.json")
            if not os.path.isfile(p):
                continue
            r = load_json(p)
            acc.append(r["test_accuracy"])
            mac_p.append(r["classification"]["macro"]["precision"])
            mac_r.append(r["classification"]["macro"]["recall"])
            mac_f1.append(r["classification"]["macro"]["f1"])
            syl_total.append(r["n_train"])
            epochs.append(len(r["history"]["train_loss"]))
            n_cls.append(r["num_classes"])

        if not acc:
            print(f"{BIRD_LABELS[bird]:<8}  (no results)")
            continue

        n_syl = int(round(np.mean(syl_total)))
        n_ep  = int(round(np.mean(epochs)))
        cls   = int(round(np.mean(n_cls)))
        print(f"{BIRD_LABELS[bird]:<8} {cls:>5} {n_syl:>6} {n_ep:>4}  "
              f"{ms(acc):>16} {ms(mac_p):>16} {ms(mac_r):>16} {ms(mac_f1):>16}")

    print()


if __name__ == "__main__":
    table1_segmentation()
    table2_classification()
