"""Central configuration for paper experiment runs."""
import os

# ── Disk-space guard ─────────────────────────────────────────────────
# Set to True to save .pth checkpoint files after training.
# When False, only metrics / TensorBoard logs are kept.
SAVE_CHECKPOINTS = True

# ── Replicates ───────────────────────────────────────────────────────
N_REPLICATES = 5
REPLICATE_SEEDS = [42, 123, 456, 789, 1024]

# ── Collar values for segmentation metrics (milliseconds) ───────────
COLLAR_VALUES_MS = [5, 10, 15, 20]

# ── Audio ────────────────────────────────────────────────────────────
SAMPLE_RATE = 44100

# ── Paths ────────────────────────────────────────────────────────────
MOOVE_DIR = os.path.expanduser("~/.moove")
TRAINING_DATA_DIR = os.path.join(MOOVE_DIR, "training_data")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
TENSORBOARD_DIR = os.path.join(OUTPUT_DIR, "runs")

# ── Bird configurations ──────────────────────────────────────────────
BIRDS = {
    "ye00pu07": {
        "seg_dataset": "bird1_new_seg_ds_seg.pkl",
        "class_dataset": "bird1_new_class_ds_class.pkl",
    },
    "bu04bk04": {
        "seg_dataset": "bu04bk04_sc_1812_seg.pkl",
        "class_dataset": "bu04bk04_sc_1812_merged_class.pkl",
    },
    "gy07bu07": {
        "seg_dataset": "gy07bu07_nooverlapchunks_seg_seg.pkl",
        # OLD (inconsistent, 8 classes b/c/d/e/f/g/i/j): "gy07bu07_1812_merged_class.pkl"
        # NEW (2026-04-09): derived from gy07bu07_1812_class.pkl with m/n/x dropped → 11 classes a-k
        "class_dataset": "gy07bu07_1812_no_mnx_class.pkl",
    },
    "br08pk08": {
        "seg_dataset": "br08pk08_1812_seg.pkl",
        "class_dataset": "br08pk08_1812_merged_class.pkl",
    },
    "ye04gr05": {
        "seg_dataset": "ye04gr05_1812_seg.pkl",
        "class_dataset": "ye04gr05_1812_merged_class.pkl",
    },
}

# ── Segmentation hyperparameters ─────────────────────────────────────
SEG_HYPERPARAMS = {
    "epochs": 1000,
    "batch_size": 64,
    "learning_rate": 0.001,
    "early_stopping_patience": 5,
    "downsampling": True,
}

# ── Classification hyperparameters ───────────────────────────────────
CLASS_HYPERPARAMS = {
    "epochs": 1000,
    "batch_size": 64,
    "learning_rate": 0.001,
    "early_stopping_patience": 5,
    "downsampling": True,
}

# ── Augmentation (classification only) ───────────────────────────────
AUGMENTATION_PARAMS = {
    "enabled": True,
    "probability": 0.2,
    "noise_level": 0.0001,
    "freq_mask_width": 10,
    "time_mask_width": 10,
    "compression_factor": 0.5,
}

# ── Sliding window params (segmentation post-processing) ────────────
# Must match MooveTAF defaults (app_state.mlseg_params)
SLIDING_WINDOW_PARAMS = {
    "onset_window_size": 5,
    "n_onset_true": 3,
    "offset_window_size": 5,
    "n_offset_false": 4,
}

# ── Raw data directories (for energy-based baseline) ────────────────
# Cloud override: set MOOVE_RAW_DATA_BASE to the directory where bird ZIPs
# were extracted (e.g. /opt/moove-raw).  Leave unset for local runs.
_RAW_BASE = os.environ.get("MOOVE_RAW_DATA_BASE", "")

def _raw_dir(cloud_subdir: str, local_path: str) -> str:
    if _RAW_BASE:
        return os.path.join(_RAW_BASE, cloud_subdir)
    return os.path.expanduser(local_path)

RAW_DATA_DIRS = {
    "ye00pu07": _raw_dir("bird_1", "~/.moove/rec_data/ye00pu07_letters/baseline"),
    "bu04bk04": _raw_dir("bird_2", "~/.moove/rec_data/bu04bk04/screening_cleaned"),
    "gy07bu07": _raw_dir("bird_3", "~/.moove/rec_data/gy07bu07/exp2"),
    "br08pk08": _raw_dir("bird_4", "~/.moove/rec_data/br08pk08/exp1"),
    "ye04gr05": _raw_dir("bird_5", "~/.moove/rec_data/ye04gr05/more_data"),
}

# ── evfuncs energy-based segmentation parameters ────────────────────
# Matches moove.app_state defaults
EVFUNCS_PARAMS = {
    "freq_cutoffs": (500, 10000),
    "smooth_window": 2,       # ms
    "min_syl_dur": 0.03,      # s
    "min_silent_dur": 0.005,  # s
}
