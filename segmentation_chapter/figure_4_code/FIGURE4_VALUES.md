# Figure 4 & Tables — Data Sources and Current Values

Last updated: 2026-03-30

## Data Sources

| Data | Source Path | Notes |
|------|------------|-------|
| Seg results (per bird/seed) | `paper_experiments/results/seg/{bird}/seed_{42,123,456}/results.json` | Bird 3 currently from `gy07bu07_OLD` (pre-fix); FIX version training on GCloud |
| Class results (per bird/seed) | `paper_experiments/results/class/{bird}/seed_{42,123,456}/results.json` | Same note for Bird 3 |
| Combined results | `paper_experiments/results/combined/{bird}/seed_{42,123,456}/results.json` | Seg x Class pipeline |
| TensorBoard logs (loss curves) | `paper_experiments/results/runs/{seg,class}/{bird}/seed_*/**/*.tfevents.*` | Panel A |
| Energy baseline | `new_plots/figure_4/baseline_results.json` | Bird 1 BROKEN (threshold range issue, fix running) |
| Figure generation | `new_plots/figure_4/generate_figure4.py` | Panels A-D |
| Table generation | `new_plots/figure_4/generate_table1.py` | Tables 1 & 2 |
| Output files | `new_plots/figure_4/figure4.{svg,png}`, `table1.{csv,tex}`, `table2.{csv,tex}` | |

## Pending

- **Bird 3 (gy07bu07) FIX**: Training on GCloud with `gy07bu07_nooverlapchunks_seg_seg.pkl` / `gy07bu07_nooverlapchunks_clas_class.pkl`. Results will go to `$BUCKET/results/gy07bu07_FIX/`. Once done, replace `gy07bu07_OLD` results.
- **Bird 1 (ye00pu07) baseline**: Dynamic threshold range fix running locally. int16 WAV files have dB range [-28, +72] vs float32 birds [-134, +19]. Old fixed range (-120 to -30) missed Bird 1 entirely.
- **Energy baseline on GCloud**: Running with old range (-120 to -30). Will need re-run after Bird 1 fix confirmed.

---

## Table 1: Segmentation Performance (3 replicates, mean +/- SD)

### Framewise (RAW — no post-processing)

| Bird | ID | Dur (s) | Syllables | FW-Precision | FW-Recall | FW-F1 |
|------|----|---------|-----------|-------------|-----------|-------|
| Bird 1 | ye00pu07 | 5798 | 18689 | 0.9644 +/- 0.0068 | 0.9564 +/- 0.0029 | 0.9603 +/- 0.0019 |
| Bird 2 | bu04bk04 | 174 | 3734 | 0.9503 +/- 0.0081 | 0.9388 +/- 0.0143 | 0.9444 +/- 0.0045 |
| Bird 3 | gy07bu07 | 274 | 7450 | 0.9641 +/- 0.0021 | 0.9535 +/- 0.0032 | 0.9588 +/- 0.0016 |
| Bird 4 | br08pk08 | 1557 | 7173 | 0.9540 +/- 0.0043 | 0.9593 +/- 0.0022 | 0.9566 +/- 0.0012 |
| Bird 5 | ye04gr05 | 180 | 3165 | 0.9629 +/- 0.0061 | 0.9308 +/- 0.0060 | 0.9466 +/- 0.0054 |

### Collar (onset + offset) — RAW and Sliding Window (SW)

| Bird | Col@10ms RAW | Col@20ms RAW | Col@10ms SW | Col@20ms SW |
|------|-------------|-------------|------------|------------|
| Bird 1 | 0.4408 +/- 0.0139 | 0.5249 +/- 0.0126 | 0.8988 +/- 0.0058 | 0.9368 +/- 0.0038 |
| Bird 2 | 0.8104 +/- 0.0257 | 0.8601 +/- 0.0151 | 0.8592 +/- 0.0157 | 0.8702 +/- 0.0189 |
| Bird 3 | 0.8467 +/- 0.0106 | 0.9138 +/- 0.0059 | 0.5872 +/- 0.0051 | 0.5900 +/- 0.0071 |
| Bird 4 | 0.6526 +/- 0.0176 | 0.6904 +/- 0.0172 | 0.8949 +/- 0.0150 | 0.9311 +/- 0.0086 |
| Bird 5 | 0.8161 +/- 0.0167 | 0.8338 +/- 0.0109 | 0.8289 +/- 0.0125 | 0.8333 +/- 0.0076 |

### Onset-Only Collar — RAW and SW

| Bird | Onset@10ms RAW | Onset@20ms RAW | Onset@10ms SW | Onset@20ms SW |
|------|---------------|---------------|--------------|--------------|
| Bird 1 | 0.5707 +/- 0.0077 | 0.5707 +/- 0.0078 | 0.9345 +/- 0.0058 | 0.9421 +/- 0.0043 |
| Bird 2 | 0.8687 +/- 0.0125 | 0.8746 +/- 0.0114 | 0.9292 +/- 0.0091 | 0.9326 +/- 0.0071 |
| Bird 3 | 0.8996 +/- 0.0057 | 0.9255 +/- 0.0064 | 0.7443 +/- 0.0046 | 0.7448 +/- 0.0054 |
| Bird 4 | 0.7174 +/- 0.0169 | 0.7225 +/- 0.0148 | 0.9295 +/- 0.0101 | 0.9421 +/- 0.0065 |
| Bird 5 | 0.8607 +/- 0.0116 | 0.8648 +/- 0.0085 | 0.9096 +/- 0.0067 | 0.9112 +/- 0.0053 |

**Note on Bird 3 SW values**: gy07bu07 has very short inter-syllable intervals (median gap = 8.7ms). The sliding window (4/5 offset) merges adjacent syllables, reducing 1725 raw predicted segments to 956 (vs 1572 true). RAW collar values are more appropriate for this bird. The FIX dataset (offsets shortened by 5ms for consecutive g-syllables, b-offsets extended by 5ms) is currently being retrained.

---

## Table 2: Classification Performance (3 replicates, mean +/- SD)

| Bird | ID | Dur (s) | Accuracy | Macro-P | Macro-R | Macro-F1 |
|------|----|---------|----------|---------|---------|----------|
| Bird 1 | ye00pu07 | 559 | 0.9780 +/- 0.0011 | 0.9731 +/- 0.0014 | 0.9806 +/- 0.0010 | 0.9766 +/- 0.0009 |
| Bird 2 | bu04bk04 | 116 | 0.9354 +/- 0.0107 | 0.9152 +/- 0.0159 | 0.9569 +/- 0.0022 | 0.9320 +/- 0.0089 |
| Bird 3 | gy07bu07 | 231 | 0.9730 +/- 0.0062 | 0.9661 +/- 0.0071 | 0.9779 +/- 0.0060 | 0.9717 +/- 0.0062 |
| Bird 4 | br08pk08 | 224 | 0.9083 +/- 0.0129 | 0.8468 +/- 0.0256 | 0.9102 +/- 0.0179 | 0.8691 +/- 0.0245 |
| Bird 5 | ye04gr05 | 96 | 0.9638 +/- 0.0043 | 0.9515 +/- 0.0046 | 0.9677 +/- 0.0052 | 0.9578 +/- 0.0051 |

---

## Energy Baseline (evfuncs amplitude threshold)

Source: `new_plots/figure_4/baseline_results.json`

| Bird | Threshold (dB) | FW-Precision | FW-Recall | FW-F1 | Col@10ms | Col@20ms |
|------|---------------|-------------|-----------|-------|----------|----------|
| Bird 1 | -120 (BUG) | 0.5402 +/- 0.0024 | 1.0000 +/- 0.0000 | 0.7015 +/- 0.0020 | 0.0000 +/- 0.0000 | 0.0000 +/- 0.0000 |
| Bird 2 | -100 | 0.8996 +/- 0.0013 | 0.9727 +/- 0.0010 | 0.9347 +/- 0.0011 | 0.7568 +/- 0.0068 | 0.8342 +/- 0.0042 |
| Bird 3 | -76 | 0.9776 +/- 0.0051 | 0.8829 +/- 0.0074 | 0.9278 +/- 0.0025 | 0.9042 +/- 0.0029 | 0.9256 +/- 0.0061 |
| Bird 4 | -95 | 0.9270 +/- 0.0057 | 0.9243 +/- 0.0035 | 0.9256 +/- 0.0034 | 0.8644 +/- 0.0140 | 0.9312 +/- 0.0043 |
| Bird 5 | -90 | 0.8723 +/- 0.0099 | 0.9769 +/- 0.0051 | 0.9216 +/- 0.0077 | 0.6429 +/- 0.0332 | 0.7074 +/- 0.0203 |

**Bird 1 BUG**: int16 WAV files (values +/-96) produce dB range [-28, +72] after smoothing. The threshold search range (-120 to -30) is entirely below the signal → everything detected as one segment → Col=0. Fix: dynamic threshold range based on actual dB values. Running locally.

---

## Figure 4 Panels

| Panel | Content | Data Source | Metric Type |
|-------|---------|-------------|-------------|
| A | Loss curves (train/val per bird, small multiples) | TensorBoard event files in `results/runs/seg/` | Training dynamics |
| B | Framewise P/R/F1 dot plot | `results/seg/*/results.json` → `framewise` | RAW network output |
| C | Collar F1 vs tolerance (5-20ms) | `results/seg/*/results.json` → `collar_smoothed` | System-level with SW |
| D | Training duration vs FW-F1 scatter | `results/seg/*/results.json` → `data_stats_before_downsampling.duration_train_s` + `framewise.f1` | Data efficiency |
