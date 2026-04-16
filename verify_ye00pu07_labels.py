#!/usr/bin/env python3
"""Verify converted ye00pu07_letters against original ye00pu07.

Checks:
  1. Every WAV/REC/notmat triplet from source exists in destination
  2. WAV files are byte-identical (no corruption)
  3. REC files are byte-identical
  4. notmat onsets/offsets are identical
  5. notmat labels are correctly mapped (number → letter)
  6. No unexpected label characters remain
  7. Label count consistency (len(labels) == len(onsets))
"""

import os
import glob
import filecmp
import numpy as np
import evfuncs

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
    "5": "e",
    "6": "f",
    "7": "g",
    "8": "e",
    "9": "h",
}

EXPECTED_LETTERS = set(LABEL_MAP.values())

# ── Main ─────────────────────────────────────────────────────────────
def main():
    src_exp = os.path.join(SRC_BIRD, EXPERIMENT)
    dst_exp = os.path.join(DST_BIRD, EXPERIMENT)

    if not os.path.isdir(src_exp):
        print(f"ERROR: source not found: {src_exp}")
        return
    if not os.path.isdir(dst_exp):
        print(f"ERROR: destination not found: {dst_exp}")
        print("       Run convert_ye00pu07_labels.py first.")
        return

    errors = []
    warnings = []
    ok_count = 0
    total_syllables_src = 0
    total_syllables_dst = 0
    dst_label_counts = {}

    day_dirs = sorted(
        d for d in os.listdir(src_exp)
        if os.path.isdir(os.path.join(src_exp, d)) and not d.startswith(".")
    )

    dst_day_dirs = sorted(
        d for d in os.listdir(dst_exp)
        if os.path.isdir(os.path.join(dst_exp, d)) and not d.startswith(".")
    )

    # Check day folder parity
    if set(day_dirs) != set(dst_day_dirs):
        missing = set(day_dirs) - set(dst_day_dirs)
        extra = set(dst_day_dirs) - set(day_dirs)
        if missing:
            errors.append(f"Missing day folders in destination: {missing}")
        if extra:
            warnings.append(f"Extra day folders in destination: {extra}")

    for day in day_dirs:
        src_day = os.path.join(src_exp, day)
        dst_day = os.path.join(dst_exp, day)

        if not os.path.isdir(dst_day):
            errors.append(f"[{day}] destination day folder missing")
            continue

        wav_files = sorted(glob.glob(os.path.join(src_day, "*.wav")))

        for wav_path in wav_files:
            basename = os.path.basename(wav_path)
            stem = os.path.splitext(basename)[0]
            file_ok = True

            # --- Check WAV ---
            dst_wav = os.path.join(dst_day, basename)
            if not os.path.exists(dst_wav):
                errors.append(f"[{day}] WAV missing: {basename}")
                file_ok = False
            elif not filecmp.cmp(wav_path, dst_wav, shallow=False):
                errors.append(f"[{day}] WAV differs: {basename}")
                file_ok = False

            # --- Check REC ---
            rec_src = os.path.join(src_day, stem + ".rec")
            rec_dst = os.path.join(dst_day, stem + ".rec")
            if os.path.exists(rec_src):
                if not os.path.exists(rec_dst):
                    errors.append(f"[{day}] REC missing: {stem}.rec")
                    file_ok = False
                elif not filecmp.cmp(rec_src, rec_dst, shallow=False):
                    errors.append(f"[{day}] REC differs: {stem}.rec")
                    file_ok = False

            # --- Check notmat ---
            notmat_src_path = wav_path + ".not.mat"
            notmat_dst_path = os.path.join(dst_day, basename + ".not.mat")

            if os.path.exists(notmat_src_path):
                if not os.path.exists(notmat_dst_path):
                    errors.append(f"[{day}] notmat missing: {basename}.not.mat")
                    file_ok = False
                else:
                    try:
                        src_notmat = evfuncs.load_notmat(notmat_src_path)
                        dst_notmat = evfuncs.load_notmat(notmat_dst_path)
                    except Exception as e:
                        errors.append(f"[{day}] notmat load error {basename}: {e}")
                        file_ok = False
                        continue

                    src_labels_raw = src_notmat.get("labels", "")
                    dst_labels_raw = dst_notmat.get("labels", "")
                    # Normalise to plain Python strings
                    src_labels = "".join(str(ch) for ch in src_labels_raw) if not isinstance(src_labels_raw, str) else src_labels_raw
                    dst_labels = "".join(str(ch) for ch in dst_labels_raw) if not isinstance(dst_labels_raw, str) else dst_labels_raw
                    src_onsets = np.asarray(src_notmat.get("onsets", []))
                    dst_onsets = np.asarray(dst_notmat.get("onsets", []))
                    src_offsets = np.asarray(src_notmat.get("offsets", []))
                    dst_offsets = np.asarray(dst_notmat.get("offsets", []))

                    total_syllables_src += len(src_labels)
                    total_syllables_dst += len(dst_labels)

                    for ch in dst_labels:
                        key = str(ch)
                        dst_label_counts[key] = dst_label_counts.get(key, 0) + 1

                    # Check label length matches onset count
                    if len(dst_labels) != len(dst_onsets):
                        errors.append(
                            f"[{day}] {basename}: label/onset mismatch "
                            f"(labels={len(dst_labels)}, onsets={len(dst_onsets)})"
                        )
                        file_ok = False

                    # Check label length preserved
                    if len(src_labels) != len(dst_labels):
                        errors.append(
                            f"[{day}] {basename}: label count changed "
                            f"({len(src_labels)} → {len(dst_labels)})"
                        )
                        file_ok = False

                    # Check mapping correctness
                    expected = "".join(LABEL_MAP.get(str(ch), str(ch)) for ch in src_labels)
                    if dst_labels != expected:
                        errors.append(
                            f"[{day}] {basename}: label mapping wrong\n"
                            f"         src:      '{src_labels}'\n"
                            f"         expected: '{expected}'\n"
                            f"         got:      '{dst_labels}'"
                        )
                        file_ok = False

                    # Check for unexpected characters in destination
                    unexpected = set(dst_labels) - EXPECTED_LETTERS
                    if unexpected:
                        warnings.append(
                            f"[{day}] {basename}: unexpected label chars: {unexpected}"
                        )

                    # Check onsets/offsets preserved
                    if src_onsets.shape != dst_onsets.shape or not np.allclose(src_onsets, dst_onsets):
                        errors.append(f"[{day}] {basename}: onsets differ")
                        file_ok = False
                    if src_offsets.shape != dst_offsets.shape or not np.allclose(src_offsets, dst_offsets):
                        errors.append(f"[{day}] {basename}: offsets differ")
                        file_ok = False

            if file_ok:
                ok_count += 1

    # --- Summary ---
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Source:      {src_exp}")
    print(f"Destination: {dst_exp}")
    print(f"Day folders: {len(day_dirs)}")
    print(f"Files OK:    {ok_count}")
    print(f"Errors:      {len(errors)}")
    print(f"Warnings:    {len(warnings)}")
    print()
    print(f"Total syllables (source): {total_syllables_src}")
    print(f"Total syllables (dest):   {total_syllables_dst}")
    print()
    print("Destination label distribution:")
    for ch in sorted(dst_label_counts.keys()):
        print(f"  '{ch}': {dst_label_counts[ch]}")
    print()

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  ✗ {e}")
        print()

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()

    if not errors and not warnings:
        print("✓ All checks passed! Conversion is correct.")
    elif not errors:
        print("✓ No errors, but check warnings above.")
    else:
        print("✗ Errors found – review above.")


if __name__ == "__main__":
    main()
