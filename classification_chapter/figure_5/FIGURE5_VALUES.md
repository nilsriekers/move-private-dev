# Figure 5 — Data Sources and Current Values

Last updated: 2026-03-30

---

## Data Sources

| Panel | Content | Source | Status |
|-------|---------|--------|--------|
| A | Classification loss curves per bird | `paper_experiments/results/class/{bird}/seed_{42,123,456}/results.json` → `history.train_loss`, `history.val_loss` | ✅ available |
| B | Accuracy + Macro-F1 dot plot | Same results.json → `test_accuracy`, `classification.macro.f1` | ✅ available |
| C | Confusion matrix Bird 1 (ye00pu07) | `paper_experiments/results/class/ye00pu07/seed_42/confusion_matrix.svg` | ✅ exists (SVG) → convert to PNG for embedding |
| D | Accuracy vs input duration Bird 1 | Needs separate script: vary input window size and re-evaluate | ❌ not yet |
| E | UMAP 30 ms Bird 1 | MooveGUI UMAP export (30 ms window) | ❌ not in results.json |
| F | UMAP full syllable Bird 1 | MooveGUI UMAP export (full duration) | ❌ not in results.json |

**Bird 3 note**: `gy07bu07_OLD` results used for now. [change: replace with FIX results once GCloud training completes and results are collected]

---

## Panel B — Current Values (mean ± SD, 3 seeds)

**Source**: `paper_experiments/results/class/{bird}/seed_{42,123,456}/results.json`

| Bird | ID | Dur (s) | N_syl_train | Accuracy | Macro-P | Macro-R | Macro-F1 |
|------|----|---------|------------|----------|---------|---------|----------|
| Bird 1 | ye00pu07 | 559 | ~18,335 | 0.9780 ± 0.0011 | 0.9731 ± 0.0014 | 0.9806 ± 0.0010 | 0.9766 ± 0.0009 |
| Bird 2 | bu04bk04 | 116 | ~3,803 | 0.9354 ± 0.0107 | 0.9152 ± 0.0159 | 0.9569 ± 0.0022 | 0.9320 ± 0.0089 |
| Bird 3 | gy07bu07 | 231 | ~7,580 | 0.9730 ± 0.0062 | 0.9661 ± 0.0071 | 0.9779 ± 0.0060 | 0.9717 ± 0.0062 |
| Bird 4 | br08pk08 | 224 | ~7,360 | 0.9083 ± 0.0129 | 0.8468 ± 0.0256 | 0.9102 ± 0.0179 | 0.8691 ± 0.0245 |
| Bird 5 | ye04gr05 | 96 | ~3,146 | 0.9638 ± 0.0043 | 0.9515 ± 0.0046 | 0.9677 ± 0.0052 | 0.9578 ± 0.0051 |

**Range across birds**: Accuracy 0.908–0.978, Macro-F1 0.869–0.977

**Epochs**: 12–26 (mean 18 ± 5) [change: update once FIX done]

**All values marked [change] need updating once Bird 3 FIX results are collected.**

---

## Panel C — Confusion Matrix (Bird 1, ye00pu07)

File: `paper_experiments/results/class/ye00pu07/seed_42/confusion_matrix.svg`

**To embed in generate_figure5.py:**
Convert SVG to PNG first:
```bash
# Option 1 (cairosvg):
python3 -c "import cairosvg; cairosvg.svg2png(url='paper_experiments/results/class/ye00pu07/seed_42/confusion_matrix.svg', write_to='paper_experiments/results/class/ye00pu07/seed_42/confusion_matrix.png', dpi=300)"

# Option 2 (Inkscape):
inkscape paper_experiments/results/class/ye00pu07/seed_42/confusion_matrix.svg --export-png=.../confusion_matrix.png --export-dpi=300
```

**Bird 1 label set**: `['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'l']` — 9 classes (c/h merged for learning experiment; in paper described as 9 classes not 10)

---

## Panel D — Accuracy vs Input Duration (Bird 1)

**Not yet generated for the new experiment runs.**

Previous result (from old Fig 5): accuracy increased from ~86% at 5.8 ms to ~96% at 30 ms (without c/h merge).

**To generate**: Run a sweep of input window durations (e.g., 5, 10, 15, 20, 25, 30, 40, 50 ms) for Bird 1 and record test accuracy at each. This requires re-evaluating the trained model with different `input_length` parameters.

[change: create `accuracy_vs_duration.py` script once final Bird 1 model is confirmed]

---

## Panels E & F — UMAP Projections (Bird 1)

**Not stored in results.json.** These are generated in MooveGUI during the interactive clustering step.

To regenerate:
1. Load the Bird 1 classification PKL (`bird1_new_class_ds_class.pkl`) in MooveGUI
2. Compute UMAP with 30 ms window → export point coordinates + labels → **Panel E**
3. Compute UMAP with full syllable window → export → **Panel F**

[change: export UMAP data and load in generate_figure5.py once available]

---

## Pending / [change] markers

| Item | What needs to change | When |
|------|---------------------|------|
| Bird 3 results | Replace `gy07bu07_OLD` with FIX results in `BIRD_DIRS` | Once GCloud VM completes |
| All panel B values | Update table above | Same |
| Panel C PNG | Convert SVG to PNG for embedding | Anytime |
| Panel D | Create accuracy-vs-duration sweep script | Before final figure |
| Panels E–F | Export UMAP data from MooveGUI | Before final figure |
| paper_new.txt | Replace `[change]` markers in classification paragraph | Once FIX done |
