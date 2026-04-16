# Response to Reviewer — Points 2.1–2.7 (Results from Fitting Neural Networks)

---

## 2.1 Accuracy alone is not informative for binary classification

**Reviewer:** Accuracy is not a super-informative metric for binary classification with unbalanced classes. Compute framewise P/R/F1 for all 5 birds. State in Methods how P/R/F1 are computed. Clarify whether BCE loss was weighted.

**Response:**

We thank the reviewer for this important point. We have expanded the evaluation of the segmentation network beyond accuracy to include framewise precision, recall, and F1-score for all five birds, computed identically to the framewise metrics described in Steinfath et al. (2021). These metrics are now reported in the updated Table 1 and visualized in Figure 4B.

As the reviewer correctly notes, the class distribution in our segmentation task is imbalanced (background frames outnumber syllable frames). To address this during training, we apply downsampling to balance the training and validation sets (see Methods). The BCE loss was not weighted; instead, class balance was achieved through downsampling, which we found to produce stable training dynamics. We have clarified this in the Methods section.

Framewise F1 scores across birds: Bird 1: 0.960 ± 0.002, Bird 2: 0.944 ± 0.005, Bird 3: 0.954 ± 0.002, Bird 4: 0.957 ± 0.001, Bird 5: 0.947 ± 0.005. Range: 0.938–0.962.

**Status: ✅ DONE** — Final values available. Source: `paper_experiments/results/seg/{bird}/seed_{42,123,456}/results.json` → keys `framewise.precision`, `framewise.recall`, `framewise.f1`.

---

## 2.2 Segmentation-level metrics with collar values

**Reviewer:** Present segmentation-level (not framewise) P/R/F1 with collar tolerances (e.g., P_seg@10, P_seg@5). Include baseline comparison with energy-based segmentation.

**Response:**

We have added segment-level precision, recall, and F1 metrics with collar tolerances of 5, 10, 15, and 20 ms, following the approach described in vocalpy (https://vocalpy.readthedocs.io/en/latest/). We use an **onset-only collar criterion**: a predicted segment is counted as a true positive when its onset falls within ±collar ms of a ground-truth syllable onset, regardless of offset timing. This criterion reflects the primary requirement for closed-loop targeting, where reliable onset detection determines feedback timing. These metrics are reported in the updated Table 1 (with sliding window post-processing applied) and visualized in Figure 4C.

With a 10 ms collar, onset-based F1 scores were: Bird 1: 0.935 ± 0.006, Bird 2: 0.929 ± 0.009, Bird 3: 0.720 ± 0.001, Bird 4: 0.930 ± 0.010, Bird 5: 0.910 ± 0.007. Bird 3 achieves lower F1 due to short inter-syllable intervals that limit the sliding window's ability to separate rapidly successive syllables; without sliding window post-processing, Bird 3 achieves onset collar F1 of 0.937, confirming accurate network-level onset detection.

As a baseline comparison, we evaluated the energy-based amplitude-threshold segmentation method (evfuncs; Nicholson, 2021) — the same method used in MooveGUI for initial segmentation — using the same onset-only collar metrics. For each bird, we performed a grid search over dB thresholds (-70 to -30 dB) on 80% of annotated files and evaluated on the remaining 20%, repeated 3 times. Results are included in Table 1 alongside the neural network metrics.

**Status: ✅ DONE** — Final values available (Bird 3 FIX complete). Source: `paper_experiments/results/seg/{bird}/seed_*/results.json` → key `onset_collar_smoothed.@10ms.f1`.

---

## 2.3 Training set size in seconds

**Reviewer:** Add training set size in seconds to Tables.

**Response:**

We have added training set duration in seconds as the primary measure of training data size in both Table 1 and Table 2, alongside the number of syllables.

Training durations: Bird 1: 5798s, Bird 2: 174s, Bird 3: 274s, Bird 4: 1557s, Bird 5: 180s. Range: 174–5798s.

**Status: ✅ DONE** — Final values available.

---

## 2.4 Training replicates

**Reviewer:** Run 3 training replicates per bird, report mean ± SD.

**Response:**

We have trained three replicates per bird for both the segmentation and classification networks, using random seeds 42, 123, and 456 to vary the train/validation/test split. All metrics are now reported as mean ± standard deviation across the three replicates.

**Status: ✅ DONE** — All 5 birds × 3 seeds × 2 networks complete. All values reported as mean ± SD.

---

## 2.5 Figures 4 & 5: more informative plots

**Reviewer:** Instead of plotting what's already in tables, show analysis of training set size vs. performance (scatter plot).

**Response:**

We have replaced Figure 4 with a multi-panel figure:
- **Panel A:** Training and validation loss curves for each bird (small multiples), showing convergence behavior across replicates with mean ± SD shading.
- **Panel B:** Framewise precision, recall, and F1 (dot plot with error bars across replicates) for all birds — showing raw network performance without post-processing.
- **Panel C:** Collar-based F1 score versus tolerance (5–20 ms) with sliding window post-processing — showing system-level detection performance.
- **Panel D:** Training set duration (seconds, log scale) versus framewise F1, showing the relationship between training data size and performance across birds.

The log scale in Panel D is necessary because Bird 1 has substantially more training data (~5800s) than the other birds (~180-270s), which would otherwise compress the visualization.

**Status: ✅ DONE** — `figure4.svg/png` regeneriert mit finalen Werten (onset_collar_smoothed). Ausführen: `uv run python3 new_plots/figure_4/generate_figure4.py`

---

## 2.6 Loss curves instead of final loss values

**Reviewer:** Show loss curves over training steps instead of final loss values. Use TensorBoard SummaryWriter. Plot individual runs + mean as darker line.

**Response:**

We have added TensorBoard logging to both training scripts and now display training and validation loss curves in Figure 4A. Individual replicate runs are shown as thin lines with the mean across replicates as a thicker overlaid line, with shaded regions indicating ± 1 standard deviation. Training curves are shown in each bird's color, validation curves in grey (dashed), making the convergence behavior clearly visible.

**Status: ✅ DONE** — Loss curves rendered in Figure 4A/5A from results.json history.

---

## 2.7 Reporting loss values is not very useful

**Reviewer:** Consider removing final loss values from tables.

**Response:**

Following the reviewer's suggestion, we have removed final loss values from both tables. Table 1 now reports training duration (seconds), number of syllables, epochs, framewise P/R/F1, and collar-based F1 at 10 and 20 ms. Table 2 reports training duration, number of classes, number of syllables, epochs, accuracy, and macro P/R/F1. These metrics are more directly interpretable than loss values.

**Status: ✅ DONE** — Tabellen bereit: `uv run python3 new_plots/figure_4/generate_table1.py`

---

## Figure 5 Update (Classification — analogous to Figure 4)

**Reviewer:** For figure 5, instead of just plotting what you already have in tables, show analysis of training set size vs. performance; show loss curves over training steps instead of final values.

**Response:**

We have updated Figure 5 to follow the same structure as the revised Figure 4:

- **Panel A:** Training and validation loss curves for each bird (small multiples, 3 replicates per bird), with mean ± SD shading. Training curves in bird color, validation curves grey (dashed).
- **Panel B:** Classification accuracy and macro-averaged F1-score (dot plot with error bars across 3 replicates) for all five birds — providing a concise multi-metric overview analogous to Figure 4B.
- **Panel C:** Confusion matrix for Bird 1 (retained from previous version).
- **Panel D:** Accuracy vs. input duration for Bird 1 (retained — shows the latency–accuracy trade-off).
- **Panels E–F:** UMAP projections at 30 ms and full syllable duration (retained).

Across all birds, test accuracy ranged from 0.908 to 0.978 and macro-F1 from 0.869 to 0.977. Per bird: Bird 1: acc 0.978 ± 0.001, F1 0.977 ± 0.001 | Bird 2: acc 0.935 ± 0.011, F1 0.932 ± 0.009 | Bird 3: acc 0.934 ± 0.008, F1 0.923 ± 0.010 | Bird 4: acc 0.908 ± 0.013, F1 0.869 ± 0.025 | Bird 5: acc 0.964 ± 0.004, F1 0.958 ± 0.005. Epochs: 12–34 (mean: 21 ± 8). Training syllables: 947–18,335.

**Status: ✅ DONE** — Finale Werte verfügbar (Bird 3 FIX abgeschlossen). Source: `paper_experiments/results/class/{bird}/seed_{42,123,456}/results.json`

---

# Summary of Implementation Status

| Point | Description | Code | Data | Text |
|-------|-------------|------|------|------|
| 2.1 | Framewise P/R/F1 all birds | ✅ | ✅ Final | ✅ PAPER_CHANGES.md |
| 2.2 | Onset-only collar + baseline | ✅ | ✅ Final | ✅ PAPER_CHANGES.md |
| 2.3 | Duration in seconds | ✅ | ✅ Final | ✅ PAPER_CHANGES.md |
| 2.4 | 3 replicates, mean±SD | ✅ | ✅ Final | ✅ PAPER_CHANGES.md |
| 2.5 | New Figure 4 | ✅ | ✅ figure4.svg/png | ✅ paper_new.txt |
| 2.6 | Loss curves (Fig 4 + Fig 5) | ✅ | ✅ Final | ✅ paper_new.txt |
| 2.7 | Remove loss from tables | ✅ | ✅ Final | ✅ paper_new.txt |
| Fig5 | Updated Figure 5 (classification) | ✅ | ✅ Final | ✅ paper_new.txt |
