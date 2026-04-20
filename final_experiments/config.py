"""Configuration for final_experiments (Experiment 4).

Dataset creation
----------------
Datasets are built on-the-fly at training time from raw WAV/.not.mat files
via final_experiments/create_dataset.py.  No pre-built PKL files are needed.

Local runs:    raw data lives at the per-bird paths in BIRDS["raw_data_dir"].
GCloud runs:   set MOOVE_RAW_DATA_BASE=/opt/moove-raw; raw ZIPs are extracted
               there as bird_1/ … bird_5/ (mirrors the GCS bucket structure).
"""
import os

# ── Paths ────────────────────────────────────────────────────────────
MOOVE_DIR        = os.path.expanduser("~/.moove")
OUTPUT_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
TENSORBOARD_DIR  = os.path.join(OUTPUT_DIR, "runs")

# Cloud override: set MOOVE_RAW_DATA_BASE to the directory where bird ZIPs
# were extracted (e.g. /opt/moove-raw).  Leave unset for local runs.
_RAW_BASE = os.environ.get("MOOVE_RAW_DATA_BASE", "")

def _raw_dir(cloud_subdir: str, local_path: str) -> str:
    """Return cloud path when MOOVE_RAW_DATA_BASE is set, else local path."""
    if _RAW_BASE:
        return os.path.join(_RAW_BASE, cloud_subdir)
    return os.path.expanduser(local_path)

# ── Audio ────────────────────────────────────────────────────────────
SAMPLE_RATE = 44100

# ── Replicates ───────────────────────────────────────────────────────
REPLICATE_SEEDS = [42, 123, 456]

# ── Collar values for segmentation metrics (ms) ──────────────────────
COLLAR_VALUES_MS = [5, 10, 15, 20]

# ── Bird dataset configuration ───────────────────────────────────────
# raw_data_dir    : directory tree of WAV + .not.mat files used as training data
# exclude_labels  : syllable labels to drop from classification (set, may be empty)
# merge_labels    : map source→target label before training (dict, may be empty)
BIRDS = {
    "ye00pu07": {
        "raw_data_dir": _raw_dir("bird_1", "~/.moove/rec_data/ye00pu07_letters/baseline"),
        "exclude_labels": set(),
        "merge_labels": {},
    },
    "bu04bk04": {
        "raw_data_dir": _raw_dir("bird_2", "~/.moove/rec_data/bu04bk04/screening_cleaned"),
        "exclude_labels": set(),
        "merge_labels": {"b": "i"},
    },
    "gy07bu07": {
        "raw_data_dir": _raw_dir("bird_3", "~/.moove/rec_data/gy07bu07/exp2"),
        # m/n are legitimate motif variants but not part of the core repertoire;
        # x marks noise/artefacts.  Excluded to match the original training PKL.
        "exclude_labels": {"m", "n", "x"},
        "merge_labels": {},
    },
    "br08pk08": {
        "raw_data_dir": _raw_dir("bird_4", "~/.moove/rec_data/br08pk08/exp1"),
        "exclude_labels": set(),
        "merge_labels": {"i": "a", "k": "a", "l": "e", "m": "b"},
    },
    "ye04gr05": {
        "raw_data_dir": _raw_dir("bird_5", "~/.moove/rec_data/ye04gr05/more_data"),
        "exclude_labels": set(),
        "merge_labels": {"i": "b", "j": "b"},
    },
}

# ── Dataset creation parameters (mirror moove app_state defaults) ────
SEG_DATASET_PARAMS = {
    "chunk_size":     64,
    "hist_size":      3,    # stored as hist_size+1 = 4 in PKL metadata
    "overlap_chunks": False,
}

CLASS_DATASET_PARAMS = {
    "input_length": 21,
    "chunk_size":   64,
    "nperseg":      64,
    "noverlap":     32,
    "nfft":         128,
    "freq_cutoffs": (0, 22050),
}

# ── Training hyperparameters ──────────────────────────────────────────
SEG_HYPERPARAMS = {
    "epochs":                  1000,
    "batch_size":              64,
    "learning_rate":           0.001,
    "early_stopping_patience": 5,
    "downsampling":            False,
}

CLASS_HYPERPARAMS = {
    "epochs":                  1000,
    "batch_size":              64,
    "learning_rate":           0.001,
    "early_stopping_patience": 5,
    "downsampling":            False,
}

# ── Augmentation (classification only) ───────────────────────────────
# Identical to moove.utils.training_utils.DEFAULT_AUGMENTATION_PARAMS
AUGMENTATION_PARAMS = {
    "enabled":            True,
    "probability":        0.2,
    "noise_level":        0.0001,
    "freq_mask_width":    10,
    "time_mask_width":    10,
    "compression_factor": 0.5,
}

# ── Sliding window params (must match MooveTAF app_state.mlseg_params) ─
SLIDING_WINDOW_PARAMS = {
    "onset_window_size":  5,
    "n_onset_true":       3,
    "offset_window_size": 5,
    "n_offset_false":     4,
}

# ── evfuncs energy-based segmentation parameters ────────────────────
# Matches moove.app_state defaults (used for energy baseline comparison)
EVFUNCS_PARAMS = {
    "freq_cutoffs": (500, 10000),
    "smooth_window": 2,       # ms
    "min_syl_dur": 0.03,      # s
    "min_silent_dur": 0.005,  # s
}

# ── Energy baseline grid search ─────────────────────────────────────
BASELINE_GRID_STEP_DB = 1.0     # dB step size
BASELINE_GRID_MARGIN_DB = 20    # margin beyond observed dB range
