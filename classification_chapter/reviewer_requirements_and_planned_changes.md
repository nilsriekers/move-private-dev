# Classification Chapter — Reviewer Requirements & Planned Changes

Last updated: 2026-04-22

---

## 1. Source Files

| File | Purpose |
|------|---------|
| `classification_chapter/classification_chapter.txt` | Original chapter text |
| `classification_chapter/results/{bird}/seed_{42,123,456}/` | Copied from final_experiments — DO NOT MODIFY originals |
| `classification_chapter/figure_5/` | Copied from new_plots/figure_5 |
| `classification_chapter/reviewer_requirements_and_planned_changes.md` | This file |

---

## 2. Reviewer Requirements (from eneuro_review_todos.txt + response_2_reviewers.txt)

### 2.1 Metrics & Table
- **[DONE]** 3 replicates per bird, report mean ± SD
- **[TODO]** Table 2: add training set size in **seconds** (not just syllable count)
- **[TODO]** Table 2: remove final loss values → keep accuracy + macro P/R/F1
- **[TODO]** Report epochs trained (mean ± SD) — update [change] markers in text
- **[TODO]** Update syllable counts and accuracy/F1 ranges in text

### 2.2 Figure 5
- **[DONE]** Panel A: loss curves with mean ± SD shading (in figure_5/)
- **[TODO]** Panel B: dot plot Accuracy + Macro-F1 — update values from final_experiments (NOT paper_experiments)
- **[TODO]** Panel C: confusion matrix for Bird 1 — confirm using final_experiments seed_42
- **[NOT DONE]** `response_2_reviewers.txt` line 102 explicitly: "Figure 5 TODO" — figure revision incomplete
- Panel D (accuracy vs. input duration), E/F (UMAP): not changed, use existing

### 2.3 Text [change] markers in classification_chapter.txt
- Line 1: syllable count range `[change]` → 4,573–26,410 total syllables per bird
- Line 1: test accuracy range `[change]` → 0.927–0.977
- Line 1: macro F1 range `[change]` → 0.879–0.976
- Line 1: epochs `[change]` → 9–33 epochs (mean 15 ± 6)

---

## 3. Current Numbers from final_experiments

### 3.1 Per-Bird Summary (3 seeds, mean ± SD)

| Bird | Bird # | Classes | N_syl (total) | Dur_train (s) | Accuracy | Macro-P | Macro-R | Macro-F1 | Epochs |
|------|--------|---------|--------------|--------------|----------|---------|---------|----------|--------|
| ye00pu07 | Bird 1 | 9 | 26,410 | 558 | 0.977±0.006 | 0.972±0.008 | 0.981±0.005 | 0.976±0.006 | 11,9,14 |
| bu04bk04 | Bird 2 | 10 | 5,516 | 121 | 0.966±0.005 | 0.956±0.012 | 0.972±0.008 | 0.963±0.005 | 20,33,20 |
| gy07bu07 | Bird 3 | 11 | 10,232 | 220 | 0.948±0.013 | 0.913±0.013 | 0.945±0.012 | 0.923±0.011 | 11,9,17 |
| br08pk08 | Bird 4 | 8 | 10,350 | 223 | 0.927±0.011 | 0.863±0.028 | 0.907±0.020 | 0.879±0.024 | 10,9,12 |
| ye04gr05 | Bird 5 | 8 | 4,573 | 98 | 0.964±0.009 | 0.954±0.012 | 0.963±0.005 | 0.957±0.010 | 10,18,12 |

**Range**: Accuracy 0.927–0.977, Macro-F1 0.879–0.976  
**Epochs**: 9–33 (mean 15 ± 6 across all birds/seeds)

> NOTE: Values differ from FIGURE5_VALUES.md (which was from paper_experiments with different/unmerged labels).
> Always use the `results/` folder in classification_chapter (copied from final_experiments).

### 3.2 Class Labels per Bird

| Bird | Classes |
|------|---------|
| ye00pu07 | a, b, c, d, e, f, g, h, l (9 classes; c/h merged for learning experiment) |
| bu04bk04 | a, c, d, f, g, h, i, j, k, m (10 classes; b merged) |
| gy07bu07 | a, b, c, d, e, f, g, h, i, j, k (11 classes) |
| br08pk08 | a, b, c, d, e, f, g, j (8 classes; i,k,l,m merged) |
| ye04gr05 | a, b, c, d, e, f, g, h (8 classes; i,j merged) |

---

## 4. Planned Changes

### 4.1 classification_chapter_new.txt (to create)
- Update all `[change]` markers with new values (see §3)
- Report mean ± SD for all metrics
- Do NOT name birds by ID — "five birds", "one bird" etc.
- No specific seeds mentioned
- Add sentence: all hyperparameters correspond to Moove default configuration
- Keep Bird 1 detail section (confusion matrix, input duration analysis, UMAP) largely unchanged

### 4.2 Table 2 (to create as table2/table2.csv + table2_text.txt)
Columns: Bird | Classes | Syllables (train/total) | Duration (s) | Epochs | Accuracy | Macro-P | Macro-R | Macro-F1

### 4.3 figure_5/generate_figure5.py
- Update Panel B data source: `classification_chapter/results/` (not paper_experiments)
- Update confusion matrix (Panel C): use `results/ye00pu07/seed_42/confusion_matrix.npy`
- Panel A loss curves: update data source to final_experiments
- Panels D, E, F: unchanged (no new data available)

### 4.4 Track changes document
- Create `classification_chapter_track_changes.txt` mirroring approach from segmentation chapter
- Document all text changes with old → new

---

## 5. Open Questions

- [ ] Confusion matrix: use seed_42 only (as before) or average across seeds?
- [ ] Panel B figure: v1 (with confusion matrix as C) or v2 (scatter only)? — user to decide
- [ ] Text: the original mentions "merge syllables c and h" for Bird 1 learning experiment — this is still valid (ye00pu07 has 9 classes). Keep this section unchanged or update?
- [ ] inference speed: original says ~0.94 ms ± 0.25 ms — is this still correct / from which experiment?
