#!/usr/bin/env python3
"""Copy ye00pu07/baseline to ye00pu07_letters/baseline with number→letter label conversion.

Label mapping:
  0 → l    1 → a    2 → b    3 → c    4 → d
  5 → e    6 → f    7 → g    8 → k    9 → h

NOTE: 5 and 8 are ambiguous (e/k vs k/e). This script defaults to 5→e, 8→k.
      If that's wrong, swap them in LABEL_MAP below before running.
"""

import os
import shutil
import glob
import evfuncs
from moove.utils.movefuncs_utils import save_notmat

# ── Configuration ────────────────────────────────────────────────────
SRC_BIRD = os.path.expanduser("~/.moove/rec_data/ye00pu07")
DST_BIRD = os.path.expanduser("~/.moove/rec_data/ye00pu07_letters")
EXPERIMENT = "baseline"

LABEL_MAP = {
    "0": "l",
    "1": "a",
    "2": "b",
    "3": "c",
    "4": "d",
    "5": "e",   # ambiguous: could be k – verify!
    "6": "f",
    "7": "g",
    "8": "e",   # ambiguous: could be e – verify!
    "9": "h",
}

# ── Main ─────────────────────────────────────────────────────────────
def convert_labels(label_str):
    """Convert a label string using LABEL_MAP, character by character."""
    converted = []
    for ch in label_str:
        key = str(ch)
        if key in LABEL_MAP:
            converted.append(LABEL_MAP[key])
        else:
            print(f"  WARNING: unknown label character '{key}' – kept as-is")
            converted.append(key)
    return "".join(converted)


def main():
    src_exp = os.path.join(SRC_BIRD, EXPERIMENT)
    dst_exp = os.path.join(DST_BIRD, EXPERIMENT)

    if not os.path.isdir(src_exp):
        print(f"ERROR: source directory not found: {src_exp}")
        return

    if os.path.exists(DST_BIRD):
        print(f"ERROR: destination already exists: {DST_BIRD}")
        print("       Remove it first if you want to re-run.")
        return

    # Discover day folders
    day_dirs = sorted(
        d for d in os.listdir(src_exp)
        if os.path.isdir(os.path.join(src_exp, d)) and not d.startswith(".")
    )
    print(f"Source:      {src_exp}")
    print(f"Destination: {dst_exp}")
    print(f"Day folders: {day_dirs}")
    print()

    total_files = 0
    total_converted = 0
    label_stats = {}  # original char → count

    for day in day_dirs:
        src_day = os.path.join(src_exp, day)
        dst_day = os.path.join(dst_exp, day)
        os.makedirs(dst_day, exist_ok=True)

        # Copy batch files
        for batch_name in ("batch.txt", "batch_keep.txt"):
            src_batch = os.path.join(src_day, batch_name)
            if os.path.exists(src_batch):
                shutil.copy2(src_batch, os.path.join(dst_day, batch_name))

        # Find all wav files
        wav_files = sorted(glob.glob(os.path.join(src_day, "*.wav")))

        for wav_path in wav_files:
            basename = os.path.basename(wav_path)
            stem = os.path.splitext(basename)[0]  # e.g. ye00pu07_240424_151533.0

            # Copy WAV
            shutil.copy2(wav_path, os.path.join(dst_day, basename))

            # Copy REC
            rec_src = os.path.join(src_day, stem + ".rec")
            if os.path.exists(rec_src):
                shutil.copy2(rec_src, os.path.join(dst_day, stem + ".rec"))

            # Convert notmat labels
            notmat_src = wav_path + ".not.mat"
            notmat_dst = os.path.join(dst_day, basename + ".not.mat")

            if os.path.exists(notmat_src):
                notmat = evfuncs.load_notmat(notmat_src)
                raw_labels = notmat.get("labels", "")
                # evfuncs may return a numpy array or a string – normalise
                old_labels_str = "".join(str(ch) for ch in raw_labels)

                # Count original label characters
                for ch in old_labels_str:
                    label_stats[ch] = label_stats.get(ch, 0) + 1

                new_labels = convert_labels(raw_labels)

                # Build dict for save_notmat
                save_dict = {
                    "labels": new_labels,
                    "onsets": notmat["onsets"],
                    "offsets": notmat["offsets"],
                    "file_name": notmat.get("fname", basename),
                    "Fs": notmat.get("Fs", 44100),
                    "min_int": notmat.get("min_int"),
                    "min_dur": notmat.get("min_dur"),
                    "threshold": notmat.get("threshold"),
                    "sm_win": notmat.get("sm_win"),
                    "__header__": notmat.get("__header__", "MATLAB 5.0 MAT-file"),
                    "__version__": notmat.get("__version__", "1.0"),
                    "__globals__": notmat.get("__globals__", []),
                }
                save_notmat(notmat_dst, save_dict)

                if old_labels_str != new_labels:
                    total_converted += 1
                    print(f"  [{day}] {basename}: '{old_labels_str}' → '{new_labels}'")
                else:
                    print(f"  [{day}] {basename}: labels unchanged ('{old_labels_str}')")
            else:
                print(f"  [{day}] {basename}: no notmat file")

            total_files += 1

    print()
    print(f"Done! Copied {total_files} files, converted {total_converted} label strings.")
    print()
    print("Original label character counts:")
    for ch in sorted(label_stats.keys(), key=str):
        mapped = LABEL_MAP.get(str(ch), f"??? ({ch})")
        print(f"  '{ch}' → '{mapped}': {label_stats[ch]} syllables")


if __name__ == "__main__":
    main()
