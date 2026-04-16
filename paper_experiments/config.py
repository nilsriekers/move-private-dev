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
