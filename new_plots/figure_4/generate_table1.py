#!/usr/bin/env python3
"""Generate Table 1 (segmentation) and Table 2 (classification) for the paper.

Combined format: RAW framewise metrics + SW collar metrics.
Outputs LaTeX and CSV files.
"""
import csv
import json
import os
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "paper_experiments", "results")
OUTPUT_DIR = SCRIPT_DIR

BIRD_IDS = ["ye00pu07", "bu04bk04", "gy07bu07", "br08pk08", "ye04gr05"]
BIRD_LABELS = {
    "ye00pu07": "Bird 1", "bu04bk04": "Bird 2", "gy07bu07": "Bird 3",
    "br08pk08": "Bird 4", "ye04gr05": "Bird 5",
}
SEEDS = [42, 123, 456]


def load_results(network_type):
    results = {}
    for bird in BIRD_IDS:
        runs = []
        for seed in SEEDS:
            path = os.path.join(RESULTS_DIR, network_type, bird, f"seed_{seed}", "results.json")
            if os.path.isfile(path):
                with open(path) as f:
                    runs.append(json.load(f))
        if runs:
            results[bird] = runs
    return results


def fmt(vals, decimals=3):
    """Format mean +/- std (LaTeX)."""
    a = np.array(vals, dtype=float)
    return f"{a.mean():.{decimals}f} $\\pm$ {a.std():.{decimals}f}"


def fmt_plain(vals, decimals=3):
    """Format mean +/- std (plain text)."""
    a = np.array(vals, dtype=float)
    return f"{a.mean():.{decimals}f} +/- {a.std():.{decimals}f}"


def generate_seg_table(results):
    """Combined table: RAW framewise + SW collar."""
    rows = []
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        label = BIRD_LABELS[bird]

        durs = [r["data_stats_before_downsampling"]["duration_train_s"] for r in runs]
        syls = [r["data_stats_before_downsampling"]["n_syllables_train"] for r in runs]
        epochs = [len(r["history"]["train_loss"]) for r in runs]

        # RAW framewise
        fw_p = [r["framewise"]["precision"] for r in runs]
        fw_r = [r["framewise"]["recall"] for r in runs]
        fw_f1 = [r["framewise"]["f1"] for r in runs]
        # SW collar
        c10 = [r["collar_smoothed"]["@10ms"]["f1"] for r in runs]
        c20 = [r["collar_smoothed"]["@20ms"]["f1"] for r in runs]

        rows.append({
            "bird": label, "bird_id": bird,
            "dur": f"{np.mean(durs):.0f}", "syls": f"{int(np.mean(syls))}",
            "epochs": f"{np.mean(epochs):.0f}",
            "fw_p": fmt(fw_p), "fw_r": fmt(fw_r), "fw_f1": fmt(fw_f1),
            "c10": fmt(c10), "c20": fmt(c20),
            "fw_p_p": fmt_plain(fw_p), "fw_r_p": fmt_plain(fw_r), "fw_f1_p": fmt_plain(fw_f1),
            "c10_p": fmt_plain(c10), "c20_p": fmt_plain(c20),
        })
    return rows


def generate_class_table(results):
    """Classification table."""
    rows = []
    for bird in BIRD_IDS:
        if bird not in results:
            continue
        runs = results[bird]
        label = BIRD_LABELS[bird]

        n_classes = [r["num_classes"] for r in runs]
        syls = [r["data_stats_before_downsampling"]["n_train"] for r in runs]
        dur = [r["data_stats_before_downsampling"].get("duration_train_s", 0) for r in runs]
        epochs = [len(r["history"]["train_loss"]) for r in runs]
        accs = [r["test_accuracy"] for r in runs]
        mac_p = [r["classification"]["macro"]["precision"] for r in runs]
        mac_r = [r["classification"]["macro"]["recall"] for r in runs]
        mac_f1 = [r["classification"]["macro"]["f1"] for r in runs]

        rows.append({
            "bird": label, "bird_id": bird,
            "classes": f"{int(np.mean(n_classes))}",
            "syls": f"{int(np.mean(syls))}",
            "dur": f"{np.mean(dur):.0f}" if np.mean(dur) > 0 else "-",
            "epochs": f"{np.mean(epochs):.0f}",
            "acc": fmt(accs), "mac_p": fmt(mac_p), "mac_r": fmt(mac_r), "mac_f1": fmt(mac_f1),
            "acc_p": fmt_plain(accs), "mac_p_p": fmt_plain(mac_p),
            "mac_r_p": fmt_plain(mac_r), "mac_f1_p": fmt_plain(mac_f1),
        })
    return rows


def write_seg_latex(rows, path):
    with open(path, "w") as f:
        f.write("\\begin{table}[ht]\n\\centering\n")
        f.write("\\caption{Segmentation network performance. Framewise metrics are computed "
                "on raw network output; collar metrics use sliding window post-processing. "
                "Values are mean $\\pm$ std across 3 training replicates.}\n")
        f.write("\\begin{tabular}{l r r r c c c c c}\n\\toprule\n")
        f.write("Bird & Dur (s) & Syllables & Epochs & FW-P & FW-R & FW-F1 "
                "& Col F1@10ms & Col F1@20ms \\\\\n\\midrule\n")
        for r in rows:
            f.write(f"{r['bird']} & {r['dur']} & {r['syls']} & {r['epochs']} "
                    f"& {r['fw_p']} & {r['fw_r']} & {r['fw_f1']} "
                    f"& {r['c10']} & {r['c20']} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def write_class_latex(rows, path):
    with open(path, "w") as f:
        f.write("\\begin{table}[ht]\n\\centering\n")
        f.write("\\caption{Classification network performance. "
                "Values are mean $\\pm$ std across 3 training replicates.}\n")
        f.write("\\begin{tabular}{l r r r c c c c}\n\\toprule\n")
        f.write("Bird & Classes & Syllables & Epochs & Accuracy "
                "& Macro-P & Macro-R & Macro-F1 \\\\\n\\midrule\n")
        for r in rows:
            f.write(f"{r['bird']} & {r['classes']} & {r['syls']} & {r['epochs']} "
                    f"& {r['acc']} & {r['mac_p']} & {r['mac_r']} & {r['mac_f1']} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def write_csv(rows, path, fields):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    seg_results = load_results("seg")
    class_results = load_results("class")

    if seg_results:
        rows = generate_seg_table(seg_results)
        print("=== Table 1: Segmentation (RAW framewise + SW collar) ===")
        print(f"{'Bird':<8} {'Dur':<6} {'Syl':<8} {'Ep':<5} "
              f"{'FW-P':<16} {'FW-R':<16} {'FW-F1':<16} "
              f"{'Col@10(SW)':<16} {'Col@20(SW)':<16}")
        print("-" * 115)
        for r in rows:
            print(f"{r['bird']:<8} {r['dur']:<6} {r['syls']:<8} {r['epochs']:<5} "
                  f"{r['fw_p_p']:<16} {r['fw_r_p']:<16} {r['fw_f1_p']:<16} "
                  f"{r['c10_p']:<16} {r['c20_p']:<16}")

        write_seg_latex(rows, os.path.join(OUTPUT_DIR, "table1_segmentation.tex"))
        write_csv(rows, os.path.join(OUTPUT_DIR, "table1_segmentation.csv"),
                  ["bird", "bird_id", "dur", "syls", "epochs",
                   "fw_p_p", "fw_r_p", "fw_f1_p", "c10_p", "c20_p"])

    if class_results:
        rows = generate_class_table(class_results)
        print("\n=== Table 2: Classification ===")
        print(f"{'Bird':<8} {'Cls':<5} {'Syl':<8} {'Ep':<5} "
              f"{'Acc':<16} {'Mac-P':<16} {'Mac-R':<16} {'Mac-F1':<16}")
        print("-" * 100)
        for r in rows:
            print(f"{r['bird']:<8} {r['classes']:<5} {r['syls']:<8} {r['epochs']:<5} "
                  f"{r['acc_p']:<16} {r['mac_p_p']:<16} {r['mac_r_p']:<16} {r['mac_f1_p']:<16}")

        write_class_latex(rows, os.path.join(OUTPUT_DIR, "table2_classification.tex"))
        write_csv(rows, os.path.join(OUTPUT_DIR, "table2_classification.csv"),
                  ["bird", "bird_id", "classes", "syls", "dur", "epochs",
                   "acc_p", "mac_p_p", "mac_r_p", "mac_f1_p"])

    print(f"\nFiles saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
