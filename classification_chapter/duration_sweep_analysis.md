# Duration Sweep Analysis — Marginal Gain

Source: `final_experiments/results_duration_sweep/` (5 birds × 10 lengths × 3 seeds = 150 runs)
Computed: mean accuracy per input_length, averaged across 5 birds and 3 seeds.

## Results

| Input length | ms    | Mean acc | Δ acc    | Δ acc/ms | % of total gain |
|-------------|-------|----------|----------|----------|-----------------|
| L=4         |  5.8  | 0.6657   |    —     |    —     |   0.0%          |
| L=7         | 10.2  | 0.8245   | +0.1589  | +0.0364  |  52.0%          |
| L=10        | 14.5  | 0.8818   | +0.0572  | +0.0132  |  70.7%          |
| L=14        | 20.3  | 0.9285   | +0.0467  | +0.0080  |  86.0%          |
| L=17        | 24.7  | 0.9461   | +0.0176  | +0.0041  |  91.8%          |
| **L=21**    | **30.5** | **0.9599** | **+0.0137** | **+0.0024** | **96.3%** |
| L=24        | 34.8  | 0.9616   | +0.0017  | +0.0004  |  96.9%          |
| L=28        | 40.6  | 0.9673   | +0.0058  | +0.0010  |  98.8%          |
| L=31        | 45.0  | 0.9683   | +0.0009  | +0.0002  |  99.1%          |
| L=34        | 49.3  | 0.9711   | +0.0029  | +0.0007  | 100.0%          |

Total achievable gain (5.8 → 49.3 ms): +30.5 percentage points

## Key numbers for text

- At **30 ms**: 96.3% of total gain captured across all birds
- Remaining gain from 30 → 50 ms: only **+1.1 percentage points**
- Marginal gain drops by ~10× after 30 ms: +0.0024/ms vs. +0.0364/ms at 5–10 ms

## Suggested text formulation

Option A (quantitative sentence to add after "showed only modest improvements thereafter"):
> "At 30 ms, 96% of the total achievable accuracy gain across birds (relative to the 5–50 ms range) was already captured, with only 1.1 percentage points of additional accuracy remaining at longer durations."

Option B (inline):
> "Accuracy increased steeply up to 30 ms, capturing 96% of the total achievable gain, and showed only modest improvements thereafter (+1.1 pp across the remaining 5–50 ms range)."

## Notes

- Separability (Fig. 5D) is computed on **first 30 ms** (same pipeline as training: `CLASS_DATASET_PARAMS`, `input_length=14` = 30.5 ms), NOT full syllable length.
- This is correctly stated in the text: "syllable spectrograms were constructed using the same preprocessing pipeline as training (first 30 ms after onset, z-normalized per sample)"
- Full syllable length is only used for the UMAP comparison (Fig. 5G).
