# Repeat Targeting Analysis Notes

## Setup

- Bird: gy07bu07
- 12 bouts from 2025-09-02 (Jacqui's fig. 7 files)
- Pattern: ≥4 consecutive 'a' predictions → trigger on onset of 4th 'a'
  - Note: `[de]aaaa` was never matched because 'f'/'n' syllables always sit between d/e and the 'a' run in gy07bu07 song syntax

---

## Optimized Parameters vs. Defaults

| Parameter | Default | Optimized | Where changed |
|-----------|---------|-----------|---------------|
| Seg model seed | 42 | 42 | — |
| Cls model seed | **42** | **123** | grid_search_seeds.py |
| Seg threshold | 0.750 (model tuned) | **0.80** | grid_search_threshold.py |
| SW onset_window_size | 5 | **3** | grid_search_threshold.py |
| SW n_onset_true | 3 | 3 | — |
| SW offset_window_size | 5 | **3** | grid_search_threshold.py |
| SW n_offset_false | 4 | **3** | grid_search_threshold.py |

Default = parameters used in `run_inference_fig7.py` (seg_seed=42, cls_seed=42, threshold=model's tuned_threshold=0.75, SW from original paper experiments).

Optimized configuration script: `analyze_best_seeds.py`  
Predicted .not.mat output: `/Users/riekers/.moove/rec_data/gy07bu07/fig7_pred_best/250902/`

---

## Results Comparison

| Config | TP | FP | FN | Precision | Recall | F1 |
|--------|----|----|-----|-----------|--------|-----|
| Default (seg42+cls42, thr=0.75, SW=5/3/5/4) | 26 | 5 | 10 | 0.839 | 0.722 | 0.776 |
| Best cls seed (seg42+cls123, thr=0.75, SW=5/3/5/4) | 30 | 4 | 6 | 0.882 | 0.833 | 0.857 |
| **Optimized (seg42+cls123, thr=0.80, SW=3/3/3/3)** | **34** | **1** | **2** | **0.971** | **0.944** | **0.958** |

Total true triggers: 36. Collar: 10ms. Typ3 excluded.

---

## How parameters were found

1. **Seed grid search** (`grid_search_seeds.py`): all 9 combos of seg×cls seeds (42/123/456).  
   → cls=123 consistently better; seg=42 still best for seg.

2. **Threshold + SW grid search** (`grid_search_threshold.py`): threshold 0.30–0.90 × all valid SW combos.  
   Uses cached seg probs (precomputed once per file) + cls cache by onset_frame for speed.  
   → Best: threshold=0.80, SW=(3,3,3,3). Baseline rank was outside top 30.

---

## FP Root Cause Analysis (original baseline)

All 3 FPs in the baseline share the same pattern:

**Mechanism**: Within a long 'a' run (e.g., 7 consecutive 'a' syllables), the very first
'a' is classified with low confidence (p(a) = 0.38–0.52). Because the run detection waits
for 4 *consecutive* predicted 'a's, the low-confidence first 'a' breaks the streak:
- True run: a a a a a a a  → trigger should fire at position 4
- Predicted: [non-a] a a a a → trigger fires at position 5 (shifted ~70–160 ms too late)
- Result: predicted trigger outside 20 ms collar → counted as FP, true trigger as FN

A confidence threshold of 0.7 on 'a' was tried (`run_inference_fig7_conf.py`) but made
results worse: it created 6 new FNs without fixing the 3 FPs, because the threshold
also demoted valid borderline 'a' syllables.

---

## Files

| File | Purpose |
|------|---------|
| `run_inference_fig7.py` | Baseline inference (default params), writes `fig7_pred/` |
| `run_inference_fig7_conf.py` | Confidence-gated inference (abandoned approach) |
| `grid_search_seeds.py` | Grid search over seg × cls seed combinations |
| `grid_search_threshold.py` | Grid search over threshold × SW parameters |
| `analyze_best_seeds.py` | Full per-file analysis with optimized params, writes `fig7_pred_best/` |
| `compare_repeat_targeting.py` | Evaluate `fig7_pred/` vs original .not.mat |
| `compare_repeat_targeting_best.py` | Evaluate `fig7_pred_best/` vs original .not.mat |
| `analyze_repeat_targeting.py` | Detailed FP type breakdown (Typ1/Typ2/Typ3) |
| `plot_predictions.py` | Plot spectrogram + true/pred label rows |


## Setup

- Bird: gy07bu07
- 12 bouts from 2025-09-02 (Jacqui's fig. 7 files)
- Segmentation: seed 42, overlap model (`gy07bu07_seg_seed42_overlap.pth`)
- Classification: seed 42 (`gy07bu07_class_seed42.pth`)
- Pattern: ≥4 consecutive 'a' predictions → trigger on onset of 4th 'a'
  - Note: `[de]aaaa` was never matched because 'f'/'n' syllables always sit between d/e and the 'a' run in gy07bu07 song syntax

---

## Baseline Results (`fig7_pred/`, no confidence threshold)

Compared predicted .not.mat (from full inference) vs. corrected original .not.mat.
Collar = 20 ms, Typ3 excluded.

| Metric | Value |
|--------|-------|
| True triggers (total) | 36 |
| TP | 28 |
| FP | 3 |
| FN | 8 |
| Precision | 0.903 |
| Recall | 0.778 |
| F1 | 0.836 |

---

## FP Root Cause Analysis

All 3 FPs share the same pattern:

**Mechanism**: Within a long 'a' run (e.g., 7 consecutive 'a' syllables), the very first
'a' is classified with low confidence (p(a) = 0.38–0.52). Because the run detection waits
for 4 *consecutive* predicted 'a's, the low-confidence first 'a' breaks the streak:
- True run: a a a a a a a  → trigger should fire at position 4
- Predicted: [non-a] a a a a → trigger fires at position 5 (shifted ~70–160 ms too late)
- Result: predicted trigger outside 20 ms collar → counted as FP, true trigger as FN

Low-confidence misclassification examples (from `analyze_repeat_targeting.py`):
- 161219 at ~74 s: p(a) ≈ 0.45
- 115923 at ~9 s:  p(a) ≈ 0.52  
- 115531 at ~15 s: p(a) ≈ 0.38

Correctly classified 'a' syllables typically have p(a) > 0.90.

---

## Confidence Threshold Fix

**Script**: `run_inference_fig7_conf.py`  
**Threshold**: `CONF_THRESHOLD = 0.7`

If the top-1 predicted class is 'a' but the softmax probability p(a) < 0.7, the segment
is instead classified as the runner-up class. This prevents a low-confidence 'a' from
contributing to the run counter.

Predicted .not.mat files written to:
`/Users/riekers/.moove/rec_data/gy07bu07/fig7_pred_conf/250902/`

Evaluation: run `compare_repeat_targeting_conf.py`

Expected improvement: the 3 FP cases (low-confidence 'a' at run start → shifted trigger)
should be resolved. Possible cost: any borderline true 'a' with p(a) in [0.70, 0.90)
would be demoted, potentially increasing FN.

---

## Files

| File | Purpose |
|------|---------|
| `run_inference_fig7.py` | Baseline inference, writes `fig7_pred/` |
| `run_inference_fig7_conf.py` | Confidence-gated inference, writes `fig7_pred_conf/` |
| `compare_repeat_targeting.py` | Evaluate `fig7_pred/` vs original |
| `compare_repeat_targeting_conf.py` | Evaluate `fig7_pred_conf/` vs original |
| `analyze_repeat_targeting.py` | Detailed FP type breakdown (Typ1/Typ2/Typ3) |
| `plot_predictions.py` | Plot spectrogram + true/pred label rows |
