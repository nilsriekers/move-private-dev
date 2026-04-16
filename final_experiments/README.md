# final_experiments

Experiment 4: final replicated training runs for all 5 birds.
Runs segmentation and classification training for 3 random seeds each,
producing the numbers reported in the paper.

---

## Overview

| Script | Purpose |
|--------|---------|
| `config.py` | All constants: birds, paths, hyperparameters |
| `create_dataset.py` | Build seg/class datasets from raw WAV files |
| `train_seg.py` | Train one bird × one seed (segmentation) |
| `train_class.py` | Train one bird × one seed (classification) |
| `run_all.py` | Orchestrate all birds × all seeds locally or on GCloud |
| `gcloud_run.sh` | Launch, monitor, collect, and clean up GCloud VMs |

---

## Dataset creation

Datasets are **built at runtime** from raw `.wav` + `.wav.not.mat` files.
No pre-built PKL files are needed.  The logic mirrors moove's GUI functions exactly:

| moove function | used in |
|---|---|
| `extract_raw_audio()` from `moove.utils.movefuncs_utils` | `build_seg_dataset` |
| `seconds_to_index()` from `moove.utils.audio_utils` | `build_class_dataset` |
| `evfuncs.load_notmat()` | both |

Default parameters (from `moove.app_state.AppState`):

| Parameter | Seg | Class |
|-----------|-----|-------|
| chunk_size | 64 | 64 |
| hist_size | 3 (stored as 4) | — |
| overlap_chunks | False | — |
| input_length | — | 21 |
| nperseg | — | 64 |
| noverlap | — | 32 |
| nfft | — | 128 |
| freq_cutoffs | — | (0, 22050) |

---

## Bird configuration

| Bird | ID | Raw data (local) | Excluded labels |
|------|----|-----------------|-----------------|
| Bird 1 | ye00pu07 | `~/.moove/rec_data/ye00pu07_letters/baseline` | — |
| Bird 2 | bu04bk04 | `~/.moove/rec_data/bu04bk04/screening_cleaned` | — |
| Bird 3 | gy07bu07 | `~/.moove/rec_data/gy07bu07/exp2` | m, n, x |
| Bird 4 | br08pk08 | `~/.moove/rec_data/br08pk08/exp1` | — |
| Bird 5 | ye04gr05 | `~/.moove/rec_data/ye04gr05/more_data` | — |

gy07bu07: `m` and `n` are legitimate motif variants, `x` marks noise.
All three are excluded to match the original training PKL (`gy07bu07_1812_no_mnx_class.pkl`).

---

## Local usage

```bash
# All birds, all seeds, both tasks:
uv run python3 final_experiments/run_all.py

# Single bird + single seed:
uv run python3 final_experiments/run_all.py --bird ye04gr05 --seed 42

# Segmentation only:
uv run python3 final_experiments/run_all.py --type seg

# Re-run even if results.json exists:
uv run python3 final_experiments/run_all.py --force
```

Results are written to `final_experiments/results/<bird>/{seg,class}/seed_<N>/`.

---

## GCloud usage

Raw training data is stored in GCS: `gs://gen-lang-client-0761701245-moove-raw-data/bird_N.zip`.
Each VM downloads its bird's ZIP, extracts it, and builds the dataset on-the-fly.

```bash
gcloud auth login
gcloud config set project gen-lang-client-0761701245

# 1. Upload code to GCS (raw data is already uploaded)
bash final_experiments/gcloud_run.sh setup

# 2. Launch one VM per bird
bash final_experiments/gcloud_run.sh launch

# 3. Monitor
bash final_experiments/gcloud_run.sh status

# 4. Download results when VMs shut down
bash final_experiments/gcloud_run.sh collect

# 5. Clean up VMs and code bucket
bash final_experiments/gcloud_run.sh cleanup
```

The `MOOVE_RAW_DATA_BASE` environment variable is set to `/opt/moove-raw` on each VM.
`config.py` picks this up automatically and maps bird names to `bird_1` … `bird_5` subdirs.

---

## Output structure

```
results/
├── summary.json                       ← aggregated results across all seeds
├── runs/                              ← TensorBoard logs
│   ├── seg/<bird>/seed_<N>/
│   └── class/<bird>/seed_<N>/
└── <bird>/
    ├── seg/seed_<N>/
    │   ├── results.json
    │   ├── predictions.npz
    │   └── <bird>_seg_seed<N>.pth
    └── class/seed_<N>/
        ├── results.json
        ├── confusion_matrix.svg
        ├── confusion_matrix.npy
        ├── confusion_matrix_norm.npy
        └── <bird>_class_seed<N>.pth
```

---

## Skipping completed runs

`run_all.py` checks for `results.json` with a `test_accuracy` key before running.
Pass `--force` to re-run even if results already exist.
