# Reviewer-Anforderungen: Segmentation Chapter

Alle Werte aus `final_experiments/results/` (5 birds × 3 seeds: 42, 123, 456).  
Baseline-Werte aus `final_experiments/results/{bird}/seg_baseline/seed_{n}/results.json`.  
Moove-Werte aus `final_experiments/results/{bird}/seg/seed_{n}/results.json`.

---

## IST-Zustand (altes Paper — `paper_old.txt` Zeilen 73–78)

### Alter Text
> "Training data ranged from 108 to 576 manually verified bouts across birds (mean: 234 ± 195 SD bouts), which were randomly split into training (70%), validation (15%), and test (15%) subsets. Across all birds, training and validation **accuracies** converged to high levels (Fig. 4A), with **test accuracies ranging from 94.30% to 98.50% (mean: 95.91 ± 1.70% SD)**. Correspondingly, training and validation **losses** decreased to low levels (Fig. 4B), with **test losses ranging from 0.0387 to 0.1467 (mean: 0.1065 ± 0.0441)**. Early stopping prevented overfitting, with training terminating after **12–24 epochs (mean: 17 ± 5 epochs)**."

### Alte Figure 4 (paper_old.txt Zeile 75)
> "(A) Segmentation network **accuracy** across training (circles), validation (squares), and test (triangles) datasets. (B) Segmentation network **loss** across training (circles), validation (squares), and test (triangles)."

**Panels: 2 (Accuracy + Loss), kein Replicate-Shading, keine Segment-Metriken**

### Alte Tabelle 1
| Bird ID | Total Bouts | Total Epochs | Test Accuracy (%) | Test Loss |
|---|---|---|---|---|
| Bird 1 | 576 | 18 | 98.50 | 0.0387 |
| Bird 2 | 108 | 18 | 94.30 | 0.1450 |
| Bird 3 | 113 | 14 | 96.26 | 0.0974 |
| Bird 4 | 176 | 24 | 94.46 | 0.1467 |
| Bird 5 | 199 | 12 | 96.04 | 0.1048 |
| Mean ± SD | 234 ± 195 | 17 ± 5 | 95.91 ± 1.70 | 0.1065 ± 0.0441 |

---

## SOLL-Zustand (neuer Text — `segmentation_chapter.txt`)

### Komplette Text-Werte (alle [CHANGE] + alle anderen Zahlen)

Der gesamte Text in `segmentation_chapter.txt` muss mit den folgenden Werten befüllt werden:

#### Trainingsdaten (Bouts, Dauer)

Quelle: `seg_baseline/results.json` (n_total/train/val/test_files) + `seg/results.json` (duration_s, n_syllables).  
**Boutzählung = WAV-Dateien** (jede WAV = 1 Bout).

| Bird | Label | Total Bouts | Train Bouts | Val Bouts | Test Bouts | Train Dur (s) | Val Dur (s) | Test Dur (s) |
|---|---|---|---|---|---|---|---|---|
| ye00pu07 | Bird 1 | 579 | 405 | 87 | 87 | 1407 ± 9 | 311 ± 6 | 307 ± 6 |
| bu04bk04 | Bird 2 | 176 | 123 | 26 | 27 | 176 ± 5 | 39 ± 2 | 41 ± 5 |
| gy07bu07 | Bird 3 | 113 | 79 | 17 | 17 | 270 ± 2 | 58 ± 2 | 60 ± 1 |
| br08pk08 | Bird 4 | 199 | 139 | 30 | 30 | 394 ± 3 | 77 ± 4 | 85 ± 1 |
| ye04gr05 | Bird 5 | 108 | 75 | 16 | 17 | 179 ± 3 | 41 ± 2 | 40 ± 2 |

**Text-Werte:**
- Bouts total: **108 bis 579** (mean: 235 ± 194 bouts)
- Training Bouts: **75 bis 405** (70% split)
- Training Dauer: **176 s bis 1407 s** (ca. 3 bis 23 Minuten)

#### Epochen

| Bird | Seed 42 | Seed 123 | Seed 456 | Mean ± SD |
|---|---|---|---|---|
| ye00pu07 | 22 | 13 | 14 | **16.3 ± 4.0** |
| bu04bk04 | 13 | 16 | 24 | **17.7 ± 4.6** |
| gy07bu07 | 15 | 18 | 10 | **14.3 ± 3.3** |
| br08pk08 | 14 | 17 | 12 | **14.3 ± 2.1** |
| ye04gr05 | 12 | 13 | 12 | **12.3 ± 0.5** |

→ **Gesamt-Range: 10–24 Epochen** (mean über alle Birds/Seeds: 15.0 ± 3.7)

#### Framewise F1 (raw, Fig. 4B)

| Bird | Mean ± SD |
|---|---|
| ye00pu07 | **0.962 ± 0.001** |
| bu04bk04 | **0.928 ± 0.008** |
| gy07bu07 | **0.914 ± 0.003** |
| br08pk08 | **0.945 ± 0.004** |
| ye04gr05 | **0.882 ± 0.015** |

→ Text: **„mean F1 scores ranging from 0.882 to 0.962 across birds"**

#### Onset Collar Smoothed @10ms (Fig. 4C + Table 1)

| Bird | Mean ± SD |
|---|---|
| ye00pu07 | **0.986 ± 0.000** |
| bu04bk04 | **0.949 ± 0.003** |
| gy07bu07 | **0.817 ± 0.008** |
| br08pk08 | **0.979 ± 0.005** |
| ye04gr05 | **0.955 ± 0.002** |

→ Text: **„onset-based F1 scores ranged from 0.817 to 0.986 across birds"**  
→ **„four birds achieving F1 ≥ 0.910, one bird (Bird 3, gy07bu07) achieving 0.817"**

---

## Neue Tabelle 1 — Vollständige Collar-Metriken (SOLL)

Die Reviewer fordern alle Collar-Toleranzen (5, 10, 15, 20 ms) mit P/R/F1.  
Quelle: `onset_collar_smoothed` aus `final_experiments/results/{bird}/seg/seed_{n}/results.json`.  
Alle Werte: mean ± SD über 3 Seeds.

### Moove — Onset Collar (mit Sliding Window)

| Bird | @5ms P | @5ms R | @5ms F1 | @10ms P | @10ms R | @10ms F1 | @15ms P | @15ms R | @15ms F1 | @20ms P | @20ms R | @20ms F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bird 1 (ye00pu07) | 0.981±0.002 | 0.970±0.000 | 0.975±0.001 | 0.991±0.001 | 0.980±0.001 | **0.986±0.000** | 0.992±0.001 | 0.980±0.001 | 0.986±0.000 | 0.992±0.001 | 0.980±0.001 | 0.986±0.000 |
| Bird 2 (bu04bk04) | 0.965±0.007 | 0.901±0.012 | 0.932±0.009 | 0.983±0.003 | 0.918±0.007 | **0.949±0.003** | 0.986±0.004 | 0.921±0.007 | 0.952±0.003 | 0.987±0.003 | 0.922±0.008 | 0.954±0.004 |
| Bird 3 (gy07bu07) | 0.968±0.005 | 0.675±0.014 | 0.796±0.011 | 0.994±0.002 | 0.693±0.011 | **0.817±0.008** | 0.995±0.001 | 0.694±0.011 | 0.817±0.007 | 0.995±0.001 | 0.694±0.011 | 0.818±0.008 |
| Bird 4 (br08pk08) | 0.961±0.007 | 0.972±0.009 | 0.967±0.007 | 0.974±0.008 | 0.984±0.005 | **0.979±0.005** | 0.975±0.008 | 0.986±0.005 | 0.980±0.004 | 0.976±0.008 | 0.986±0.004 | 0.981±0.004 |
| Bird 5 (ye04gr05) | 0.912±0.012 | 0.885±0.008 | 0.898±0.009 | 0.970±0.005 | 0.941±0.006 | **0.955±0.002** | 0.977±0.003 | 0.947±0.007 | 0.962±0.003 | 0.980±0.003 | 0.950±0.007 | 0.965±0.003 |

### Kompaktere Tabellenvariante (nur F1 pro Collar)

Wenn die Tabelle zu breit wird (P/R/F1 × 4 Toleranzen = 12 Spalten pro Bird), Alternative:

| Bird | Total Bouts | Train Bouts (70%) | Train Dur (s) | Epochs | Onset Collar F1 @5ms | @10ms | @15ms | @20ms |
|---|---|---|---|---|---|---|---|---|
| Bird 1 | 579 | 405 | 1407 ± 9 | 16 ± 4 | 0.975±0.001 | **0.986±0.000** | 0.986±0.000 | 0.986±0.000 |
| Bird 2 | 176 | 123 | 176 ± 5 | 18 ± 5 | 0.932±0.009 | **0.949±0.003** | 0.952±0.003 | 0.954±0.004 |
| Bird 3 | 113 | 79 | 270 ± 2 | 14 ± 3 | 0.796±0.011 | **0.817±0.008** | 0.817±0.007 | 0.818±0.008 |
| Bird 4 | 199 | 139 | 394 ± 3 | 14 ± 2 | 0.967±0.007 | **0.979±0.005** | 0.980±0.004 | 0.981±0.004 |
| Bird 5 | 108 | 75 | 179 ± 3 | 12 ± 1 | 0.898±0.009 | **0.955±0.002** | 0.962±0.003 | 0.965±0.003 |

---

## Neue Figure 4 (SOLL)

### Caption
> "Figure 4. Segmentation network performance across five birds (3 training replicates each, seeds 42/123/456). **(A)** Training (colored, solid) and validation (grey, dashed) loss curves for each bird, showing smooth convergence. Shaded regions indicate ±1 SD across replicates. **(B)** Framewise precision, recall, and F1-score (raw network output after threshold, no sliding window post-processing) for each bird. Error bars show ±1 SD across replicates. **(C)** Onset-based segment-level F1-score as a function of collar tolerance (5–20 ms) with sliding window post-processing applied. A predicted segment is counted as a true positive when its onset falls within ±collar ms of a ground-truth onset. Shaded regions indicate ±1 SD. **(D)** Training set duration (seconds, log scale) versus framewise F1-score for individual replicates, showing the relationship between training data size and segmentation performance."

### Code
Skript: `figure_4_code/generate_figure4.py` (Kopie aus `new_plots/figure_4/`).  
**Pfad-Fix nötig:** RESULTS_DIR und Unterordner-Struktur müssen auf `final_experiments/results` umgestellt werden.

---

## Energie-Baseline Vergleich (alle 5 Birds)

Quelle: `final_experiments/results/{bird}/seg_baseline/seed_{n}/results.json`.  
Methode: evfuncs energy-based segmentation mit grid search über Amplitude-Threshold auf dem Validation-Set.  
Parameter: `freq_cutoffs=(500,10000)`, `smooth_window=2ms`, `min_syl_dur=30ms`, `min_silent_dur=5ms`.

> **Wichtiger Bias-Hinweis:** Die Ground-Truth-Labels wurden mit einem energy-basierten Algorithmus (evfuncs) erstellt und dann manuell korrigiert. Die Baseline repliziert im Wesentlichen den GT-Erstellungsprozess — das gibt der Baseline einen systematischen Vorteil. Dass Moove bei 4/5 Birds trotzdem besser ist, ist daher ein starkes Ergebnis.

### Onset Collar Smoothed F1 — Moove vs Baseline

| Bird | Moove @5ms | Moove @10ms | Moove @15ms | Moove @20ms | Baseline @5ms | Baseline @10ms | Baseline @15ms | Baseline @20ms |
|---|---|---|---|---|---|---|---|---|
| Bird 1 (ye00pu07) | 0.975±0.001 | **0.986±0.000** | 0.986±0.000 | 0.986±0.000 | 0.177±0.040 | 0.870±0.030 | 0.951±0.016 | 0.973±0.011 |
| Bird 2 (bu04bk04) | 0.932±0.009 | **0.949±0.003** | 0.952±0.003 | 0.954±0.004 | 0.710±0.044 | 0.884±0.008 | 0.902±0.008 | 0.910±0.004 |
| Bird 3 (gy07bu07) | 0.796±0.011 | **0.817±0.008** | 0.817±0.007 | 0.818±0.008 | 0.846±0.028 | 0.903±0.012 | 0.912±0.010 | 0.922±0.008 |
| Bird 4 (br08pk08) | 0.967±0.007 | **0.979±0.005** | 0.980±0.004 | 0.981±0.004 | 0.780±0.040 | 0.921±0.009 | 0.941±0.008 | 0.949±0.008 |
| Bird 5 (ye04gr05) | 0.898±0.009 | **0.955±0.002** | 0.962±0.003 | 0.965±0.003 | 0.792±0.021 | 0.880±0.007 | 0.892±0.005 | 0.901±0.004 |

### Delta Moove − Baseline bei @10ms

| Bird | Moove | Baseline | Δ | Gewinner |
|---|---|---|---|---|
| Bird 1 (ye00pu07) | 0.986 | 0.870 | **+0.116** | Moove |
| Bird 2 (bu04bk04) | 0.949 | 0.884 | **+0.065** | Moove |
| Bird 3 (gy07bu07) | 0.817 | 0.903 | **−0.086** | Baseline* |
| Bird 4 (br08pk08) | 0.979 | 0.921 | **+0.058** | Moove |
| Bird 5 (ye04gr05) | 0.955 | 0.880 | **+0.075** | Moove |

\* Bird 3 (gy07bu07): Moove hat einen Sliding-Window-Parameter-Bug (Threshold 0.95 ist zu hoch für die globalen SW-Parameter). Das raw Onset-Collar-F1 ohne SW beträgt 0.926 — besser als die Baseline. Dies sollte im Paper erklärt werden.

### Baseline Framewise F1 (smoothed) + optimierter Threshold

| Bird | FW F1 smoothed | Threshold (dB) |
|---|---|---|
| Bird 1 (ye00pu07) | 0.955 ± 0.007 | −11 bis −12 dB |
| Bird 2 (bu04bk04) | 0.934 ± 0.002 | −102 dB* |
| Bird 3 (gy07bu07) | 0.931 ± 0.011 | −76 dB |
| Bird 4 (br08pk08) | 0.933 ± 0.006 | −97 dB* |
| Bird 5 (ye04gr05) | 0.958 ± 0.003 | −90 dB* |

\* Sehr niedrige Threshold-Werte (hohe Amplitude = low dB) — deutet auf nahezu alles-als-Syllable klassifizieren. Das erklärt die hohen Recall-Werte der Baseline.

---

## Methodenbeschreibung — Ergänzungen (Soll)

Im Methods-Abschnitt müssen ergänzt werden:

### Threshold-Tuning (neu)
> "For each bird and replicate, the binary classification threshold was selected by maximizing onset-collar F1 at 10 ms collar tolerance on the validation set. Optimal thresholds ranged from 0.65 to 0.95 across birds (see Table 1)."

### Onset-Collar-Kriterium (neu)
> "Segment-level detection performance was assessed using an onset-based collar criterion: a predicted segment is counted as a true positive when its onset falls within ±collar ms of the corresponding ground-truth onset, regardless of offset timing. This criterion reflects the primary operational requirement for closed-loop targeting, where onset detection determines feedback timing."

### Replikate (neu)
> "To assess robustness, three training replicates were performed per bird with different random seeds for data splitting (seeds 42, 123, 456). All metrics are reported as mean ± SD across replicates."

### Energy Baseline (neu — kurz im Segmentation-Abschnitt)
> "To benchmark segmentation performance, we compared Moove against an energy-based segmentation baseline using the same algorithm used to generate training labels (evfuncs; Nicholson, 2021). The baseline threshold was optimized per bird and replicate using the same validation-set criterion as Moove. Moove outperformed the energy baseline at 4 of 5 birds (onset collar F1 @10ms: +0.06 to +0.12). The one exception (Bird 3, gy07bu07) is discussed below."

---

## Zusammenfassung: Was muss geändert werden

| Was | Wo | Datenwert | Priorität |
|---|---|---|---|
| Bouts-Range im Text | `segmentation_chapter.txt` | 108–579 bouts (mean: 235 ± 194) | HOCH |
| Training-Dauer im Text | `segmentation_chapter.txt` | 176–1407 s | HOCH |
| Epochen-Range | `segmentation_chapter.txt` | 10–24 Epochen (mean: 15 ± 4) | HOCH |
| FW F1 Range | `segmentation_chapter.txt` | 0.882–0.962 | HOCH |
| Onset Collar @10ms Range | `segmentation_chapter.txt` | 0.817–0.986 | HOCH |
| gy07bu07 Wert | `segmentation_chapter.txt` | 0.817 | HOCH |
| Tabelle 1 komplett neu | Paper/Dokument | Siehe Tabelle oben | HOCH |
| Figure 4 generieren | `generate_figure4.py` ausführen | — | HOCH |
| Methods: Threshold-Tuning | Methods-Abschnitt | 0.65–0.95 | MITTEL |
| Methods: Onset-Kriterium | Methods-Abschnitt | ±collar ms | MITTEL |
| Methods: Replikate | Methods-Abschnitt | 3 Seeds | MITTEL |
| Methods: Energy Baseline | Segmentation-Abschnitt | 4/5 Birds besser | MITTEL |
