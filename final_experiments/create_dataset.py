#!/usr/bin/env python3
"""Build segmentation and classification datasets from raw bird recordings.

Mirrors create_segmentation_training_dataset() and
create_classification_training_dataset() in moove exactly, but without any
GUI dependencies.  Uses the same defaults as moove.app_state.AppState:
    chunk_size=64, hist_size=3, overlap_chunks=False,
    nperseg=64, noverlap=32, nfft=128, input_length=21

Public API
----------
get_wav_files(raw_data_dir)          -> list[str]
build_seg_dataset(file_paths, ...)   -> dict  (train_seg.py compatible)
build_class_dataset(file_paths, ...) -> dict  (train_class.py compatible)
"""

import os
import sys

import evfuncs
import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.signal import spectrogram as scipy_spectrogram

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import moove helpers to guarantee identical computations
from moove.utils.movefuncs_utils import extract_raw_audio
from moove.utils.audio_utils import seconds_to_index


# ── File collection ───────────────────────────────────────────────────

def get_wav_files(raw_data_dir: str) -> list:
    """Return sorted absolute paths of WAV files that have a paired .not.mat."""
    paths = []
    root = os.path.expanduser(raw_data_dir)
    for dirpath, _, filenames in os.walk(root):
        for fname in sorted(filenames):
            if fname.endswith(".wav"):
                fpath = os.path.join(dirpath, fname)
                if os.path.exists(fpath + ".not.mat"):
                    paths.append(fpath)
    return sorted(paths)


# ── Internal helpers ──────────────────────────────────────────────────

def _load_wav(fpath: str):
    """Load WAV as (sampling_rate: int, data: float32 1-D array)."""
    rate, data = wavfile.read(fpath)
    data = data.astype(np.float32)
    if data.ndim > 1:   # stereo → mono
        data = data[:, 0]
    return rate, data


def _concat_windows(arr: np.ndarray, hist: int, step: int) -> np.ndarray:
    """Identical to generate_concatenated_chunks_with_labels in segment_utils.py.

    arr : (n_chunks, 1 + chunk_size + 1)  [file_idx | features | label]
    Returns (n_windows, 1 + hist*chunk_size + 1)
    """
    n = len(arr)
    if n < hist:
        return np.empty((0, arr.shape[1]), dtype=np.float32)
    features = arr[:, 1:-1]
    labels   = arr[:, -1]
    file_idx = arr[0, 0]
    cw       = features.shape[1]
    ccat     = hist * cw
    indices  = list(range(0, n - (hist - 1), step))
    m = len(indices)
    if m == 0:
        return np.empty((0, 1 + ccat + 1), dtype=np.float32)
    result = np.empty((m, 1 + ccat + 1), dtype=np.float32)
    result[:, 0] = file_idx
    for j, i in enumerate(indices):
        result[j, 1:-1] = features[i:i + hist].ravel()
        result[j, -1]   = labels[i]
    return result


# ── Public builders ───────────────────────────────────────────────────

def build_seg_dataset(
    file_paths: list,
    chunk_size: int = 64,
    hist_size: int = 3,          # moove stores hist_size+1 in metadata
    overlap_chunks: bool = False,
) -> dict:
    """Build segmentation dataset dict matching moove's PKL format.

    Mirrors create_segmentation_training_dataset() from
    moove/utils/segment_utils.py without GUI callbacks.

    Returns
    -------
    dict
        "features"  : np.ndarray  shape (N, 1 + (hist_size+1)*chunk_size + 1)
        "metadata"  : {"chunk_size": int, "hist_size": int}
        "syllables" : int
    """
    _hist = hist_size + 1          # moove convention: stored value = hist_size + 1
    step  = 1 if overlap_chunks else _hist

    all_arrays = []
    num_segs   = 0

    for file_index, fpath in enumerate(file_paths):
        try:
            rate, rawsong = _load_wav(fpath)
        except Exception as e:
            print(f"[seg] Skipped (load error) {fpath}: {e}")
            continue

        notmat    = evfuncs.load_notmat(fpath + ".not.mat")
        onsets_ms = np.array(notmat.get("onsets",  []), dtype=np.float32)
        offsets_ms = np.array(notmat.get("offsets", []), dtype=np.float32)
        if len(onsets_ms) == 0:
            continue

        onsets_s  = (onsets_ms  * rate / 1000).astype(int)
        offsets_s = (offsets_ms * rate / 1000).astype(int)
        num_segs += min(len(onsets_s), len(offsets_s))

        # extract_raw_audio returns (chunk_size, n_chunks) — transpose to (n_chunks, chunk_size)
        audio_feats = extract_raw_audio(rawsong, chunk_size)
        chunks      = np.asarray(audio_feats, dtype=np.float32).T
        n_chunks    = chunks.shape[0]

        labels = np.zeros(n_chunks, dtype=np.float32)
        for i, start in enumerate(range(0, len(rawsong) - chunk_size + 1, chunk_size)):
            end = start + chunk_size
            if i < n_chunks and any(
                on <= end and start <= off
                for on, off in zip(onsets_s, offsets_s)
            ):
                labels[i] = 1.0

        fi_col        = np.full((n_chunks, 1), file_index, dtype=np.float32)
        lb_col        = labels.reshape(-1, 1)
        file_features = np.hstack([fi_col, chunks, lb_col])

        windowed = _concat_windows(file_features, _hist, step)
        if windowed.size > 0:
            all_arrays.append(windowed)

    if not all_arrays:
        raise RuntimeError(f"No valid files produced segmentation features. "
                           f"Checked {len(file_paths)} files.")

    features = np.vstack(all_arrays)
    print(f"[seg] {len(file_paths)} files → {features.shape[0]} windows  "
          f"({num_segs} syllables)")
    return {
        "features":  features,
        "metadata":  {"chunk_size": chunk_size, "hist_size": _hist},
        "syllables": num_segs,
    }


def build_class_dataset(
    file_paths: list,
    exclude_labels=None,      # set/None – e.g. {'m', 'n', 'x'} for gy07bu07
    input_length: int  = 21,
    chunk_size:   int  = 64,
    nperseg:      int  = 64,
    noverlap:     int  = 32,
    nfft:         int  = 128,
    freq_cutoffs: tuple = (0, 22050),
) -> dict:
    """Build classification dataset dict matching moove's PKL format.

    Mirrors create_classification_training_dataset() from
    moove/utils/label_utils.py without GUI callbacks.

    Returns
    -------
    dict
        "dataframe" : pd.DataFrame  columns [file, onset_no,
                                              taf_unflattend_spectrogram, label]
        "metadata"  : dict
    """
    exclude          = set(exclude_labels) if exclude_labels else set()
    input_array_size = input_length * chunk_size
    rows             = []

    for fpath in file_paths:
        try:
            rate, rawsong = _load_wav(fpath)
        except Exception as e:
            print(f"[class] Skipped (load error) {fpath}: {e}")
            continue

        notmat    = evfuncs.load_notmat(fpath + ".not.mat")
        onsets_ms = np.array(notmat.get("onsets", []))
        labels_str = notmat.get("labels", "")
        if len(onsets_ms) == 0:
            continue

        n_usable = min(len(onsets_ms), len(labels_str))
        fname    = os.path.basename(fpath)

        for syllable_no in range(n_usable):
            lbl = labels_str[syllable_no]
            if lbl in exclude:
                continue

            # seconds_to_index takes ms and returns sample index (moove naming quirk)
            onset_idx = seconds_to_index(onsets_ms[syllable_no], rate)
            clip      = rawsong[onset_idx : onset_idx + input_array_size]

            f, t, Sxx = scipy_spectrogram(clip, fs=rate, nperseg=nperseg,
                                          noverlap=noverlap, nfft=nfft)
            Sxx = Sxx[(f >= freq_cutoffs[0]) & (f <= freq_cutoffs[1]), :]
            if Sxx.ndim != 2:
                continue

            rows.append({
                "file":                      fname,
                "onset_no":                  syllable_no,
                "taf_unflattend_spectrogram": Sxx,
                "label":                     lbl,
            })

    if not rows:
        raise RuntimeError(f"No usable syllables found. "
                           f"Checked {len(file_paths)} files, "
                           f"excluded labels: {exclude}")

    df = pd.DataFrame(rows, columns=["file", "onset_no",
                                     "taf_unflattend_spectrogram", "label"])
    print(f"[class] {len(file_paths)} files → {len(df)} syllables  "
          f"labels={sorted(df['label'].unique())}")
    metadata = {
        "input_length": f"{input_length},{chunk_size}",
        "nperseg":  nperseg,
        "noverlap": noverlap,
        "nfft":     nfft,
        "lowcut":   freq_cutoffs[0],
        "highcut":  freq_cutoffs[1],
    }
    return {"dataframe": df, "metadata": metadata}
