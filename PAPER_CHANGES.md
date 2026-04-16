# Paper Changes: paper.txt → paper_new.txt

Alle Änderungen chronologisch nach Zeile/Abschnitt.
`[change]`-Marker in paper_new.txt = diese Stellen müssen in Word ersetzt werden.

---

## 1. Methods — Segmentation Network Training (Zeile ~59)

**ALT:**
> Downsampling is applied by default to balance the number of samples per label, addressing the inherent class imbalance between syllable and background frames.

**NEU:**
> Downsampling is applied by default to balance the number of samples per label.

*(Satzteil gestrichen)*

✅ Final — keine Daten nötig.

---

## 2. Methods — Experiment 2 Post-Screening Timing (Zeile ~70)

**ALT:**
> Two post-screening sessions were conducted **X and Y days** after the last training day

**NEU:**
> Two post-screening sessions were conducted **16 and 37 days** after the last training day

✅ Final.

---

## 3. Results — Segmentation Performance (Zeile ~74)

**ALT:**
> training after **XXX–XXX epochs (mean: XXX ± XXX epochs)**
> mean F1 scores ranging from **XXX to XXX**

**NEU (finale Werte):**
> training after **9–28 epochs (mean: 17 ± 5 epochs)**
> mean F1 scores ranging from **0.938 to 0.962**

**In paper_new.txt ersetzen:**
| Stelle | ALT | NEU |
|--------|-----|-----|
| Epochen | `9–28 epochs (mean: 17 ± 5 epochs) [change]` | `9–28 epochs (mean: 17 ± 5 epochs)` |
| FW-F1 | `0.944 to 0.960 [change]` | `0.938 to 0.962` |

✅ Werte final.

---

## 4. Results — Collar Metrics (Zeile ~76) ⚠️ METHODIK GEÄNDERT

**Wichtig:** Wir wechseln von **onset+offset collar** auf **onset-only collar** (onset_collar_smoothed).

**Grund:** Bird 3 (gy07bu07) hat sehr kurze Inter-Silben-Intervalle. Der Sliding Window kann Offset nicht korrekt detektieren → merged Silben. Onset-only Metrik ist für Closed-Loop-Targeting die relevante Metrik (nur Onset-Timing bestimmt Feedback).

**ALT (in paper_new.txt):**
> A predicted segment was counted as a true positive only when **both** its onset and offset fell within ±collar ms of a ground-truth boundary. With a 10 ms collar, segment-level F1 scores ranged from **0.829 to 0.899** across birds (Table 1) [change]

**NEU (komplett ersetzen):**
> A predicted segment was counted as a true positive when its onset fell within ±collar ms of a ground-truth syllable onset, regardless of offset timing. This onset-only criterion reflects the primary requirement for closed-loop targeting, where reliable onset detection determines feedback timing. With a 10 ms collar, onset-based F1 scores ranged from **0.720 to 0.942** across birds (Table 1), with four birds achieving F1 ≥ 0.910 and one bird (Bird 3, gy07bu07) achieving 0.720 due to short inter-syllable intervals that limit the sliding window's ability to separate rapidly successive syllables. When evaluated without sliding window post-processing, Bird 3 achieved an onset collar F1 of 0.937, confirming that the network itself detects syllable onsets accurately.

**Figure 4C Caption (Zeile ~75) ersetzen:**

ALT:
> (C) Segment-level collar F1-score as a function of collar tolerance (5–20 ms) with sliding window post-processing applied, reflecting system-level detection performance. [change]

NEU:
> (C) Onset-based segment-level F1-score as a function of collar tolerance (5–20 ms) with sliding window post-processing applied. A predicted segment is counted as a true positive when its onset falls within ±collar ms of a ground-truth onset, reflecting onset detection performance relevant for closed-loop targeting.

✅ Werte final.

---

## 5. Results — Onset Error (Zeile ~77)

**ALT:**
> mean onset error was **[change]** ms (median: **[change]** ms) and mean offset error was **[change]** ms...

**NEU (nur Onset im Paper):**
> mean onset error was **−1.7 ± 2.6 ms (median: −1.5 ms)**, confirming that detected onsets closely match manual annotations. The small negative bias corresponds to approximately one audio chunk (1.45 ms), consistent with the frame-level resolution of the network output.

✅ Final — Satz in paper_new.txt bereits aktualisiert.

Marker in paper_new.txt: `[change: compute from predictions.npz]` — vorerst stehen lassen oder Satz streichen.

---

## 6. Results — Figure 4 Caption (Zeile ~75)

**NEU (final):**
> Figure 4. Segmentation network performance across five birds (3 training replicates each). (A) Training (colored, solid) and validation (grey, dashed) loss curves for each bird, showing smooth convergence. Shaded regions indicate ± 1 SD across replicates. (B) Framewise precision, recall, and F1-score (raw network output, no post-processing) for each bird. Error bars show SD across replicates. (C) Onset-based segment-level F1-score as a function of collar tolerance (5–20 ms) with sliding window post-processing applied. A predicted segment is counted as a true positive when its onset falls within ±collar ms of a ground-truth onset, reflecting onset detection performance relevant for closed-loop targeting. (D) Training set duration (seconds, log scale) versus framewise F1-score, showing the relationship between training data size and segmentation performance.

✅ Final (nach Änderung in Punkt 4).

---

## 7. Results — Classification Performance (Zeile ~81)

**ALT:**
> Training data ranged from **3,099 to 18,505 syllables** [change]
> test accuracies ranged from **0.908 to 0.978** [change]
> macro-averaged F1 scores ranging from **0.869 to 0.977** [change]
> training terminating after **12–26 epochs (mean: 18 ± 5 epochs)** [change]

**NEU (finale Werte):**
> Training data ranged from **947 to 18,335 syllables**
> test accuracies ranged from **0.908 to 0.978** *(unverändert)*
> macro-averaged F1 scores ranging from **0.869 to 0.977** *(unverändert)*
> training terminating after **12–34 epochs (mean: 21 ± 8 epochs)**

**In paper_new.txt ersetzen:**
| Stelle | ALT | NEU |
|--------|-----|-----|
| Silben | `3,099 to 18,505 syllables [change]` | `947 to 18,335 syllables` |
| Accuracy | `0.908 to 0.978 [change]` | `0.908 to 0.978` (marker entfernen) |
| Macro-F1 | `0.869 to 0.977 [change]` | `0.869 to 0.977` (marker entfernen) |
| Epochen | `12–26 epochs (mean: 18 ± 5 epochs) [change]` | `12–34 epochs (mean: 21 ± 8 epochs)` |

✅ Werte final.

---

## 8. Results — Figure 5 Caption (Zeile ~85)

**ALT:**
> (A) Classification accuracy for training (circles), validation (squares), and test (triangles) datasets...
> (B) Classification loss for training (circles), validation (squares), and test (triangles)...

**NEU:**
> (A) Training (colored, solid) and validation (grey, dashed) loss curves for each bird, showing smooth convergence. Shaded regions indicate ± 1 SD across replicates. (B) Classification accuracy and macro-averaged F1-score (dot plot with error bars) for each bird. Error bars show SD across replicates.

✅ Final — nur Caption tauschen + neue Figur einfügen (generate_figure5.py).

---

## 9. Tabellen 1 & 2

**NEU generieren mit:**
```bash
uv run python3 new_plots/figure_4/generate_table1.py
```

✅ Finale Werte jetzt verfügbar (Bird 3 FIX fertig). Tabellen nach Generierung einfügen.

---

## Zusammenfassung: Was ist final vs. noch ausstehend

| # | Änderung | Status |
|---|----------|--------|
| 1 | Methods Satz gestrichen | ✅ Final |
| 2 | Post-screening 16/37 Tage | ✅ Final |
| 3 | Seg-Paragraph Zahlenwerte | ✅ Final |
| 4 | Collar → Onset-only Metrik + neue Werte | ✅ Final |
| 5 | Onset Error (nur Onset) | ✅ Final |
| 6 | Figure 4 Caption | ✅ Final |
| 7 | Class-Paragraph Zahlenwerte | ✅ Final |
| 8 | Figure 5 Caption | ✅ Final (neue Figur generieren) |
| 9 | Tabellen 1 & 2 | ✅ Bereit zum Generieren |
