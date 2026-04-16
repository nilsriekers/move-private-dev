#!/usr/bin/env python3
"""Shorten offsets by 5ms for 'g' syllables that occur in consecutive groups (≥2).

Only modifies .not.mat files in the COPY at ~/.moove/rec_data/gy07bu07_offset_fix/.
"""
import os
from glob import glob

import numpy as np
import scipy.io as sio

DATA_DIR = os.path.expanduser("~/.moove/rec_data/gy07bu07_offset_fix")
SHORTEN_MS = 5.0


def process_notmat(path):
    """Shorten offsets of consecutive g syllables by SHORTEN_MS."""
    mat = sio.loadmat(path)

    labels = str(mat["labels"][0]) if mat["labels"].ndim > 1 else str(mat["labels"])
    # Handle numpy string arrays
    if hasattr(mat["labels"], "flat"):
        labels = str(mat["labels"].flat[0])

    onsets = mat["onsets"].flatten().astype(np.float64)
    offsets = mat["offsets"].flatten().astype(np.float64)

    if len(labels) != len(onsets):
        print(f"  SKIP {os.path.basename(path)}: labels({len(labels)}) != onsets({len(onsets)})")
        return 0

    # Find consecutive g groups (≥2)
    n_shortened = 0
    i = 0
    while i < len(labels):
        if labels[i] == "g":
            # Find the run of consecutive g's
            j = i
            while j < len(labels) and labels[j] == "g":
                j += 1
            run_len = j - i
            if run_len >= 2:
                # Shorten all g's in this group
                for k in range(i, j):
                    offsets[k] -= SHORTEN_MS
                    n_shortened += 1
            i = j
        else:
            i += 1

    if n_shortened > 0:
        mat["offsets"] = offsets.reshape(mat["offsets"].shape)
        sio.savemat(path, mat)

    return n_shortened


def main():
    notmats = sorted(glob(os.path.join(DATA_DIR, "**", "*.not.mat"), recursive=True))
    print(f"Found {len(notmats)} .not.mat files in {DATA_DIR}\n")

    total_files = 0
    total_shortened = 0
    for nm in notmats:
        n = process_notmat(nm)
        if n > 0:
            total_files += 1
            total_shortened += n
            print(f"  {os.path.basename(nm)}: shortened {n} g-offsets by {SHORTEN_MS}ms")

    print(f"\nDone: {total_shortened} offsets shortened in {total_files}/{len(notmats)} files")


if __name__ == "__main__":
    main()
