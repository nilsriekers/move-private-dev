# Geplante Änderungen: Segmentation Chapter

Stand: 2026-04-22

---

## Status

| Schritt | Status |
|---|---|
| Daten aggregiert (Bouts, Dauer, Epochen, F1) | ✅ Erledigt |
| reviewer_requirements.md mit allen Werten befüllt | ✅ Erledigt |
| Figure 4 generiert (4 Panels, finale Daten) | ✅ Erledigt → `figure_4_code/figure4.png/.svg` |
| Energy Baseline für alle 5 Birds berechnet | ✅ Erledigt (in reviewer_requirements.md) |
| Text `segmentation_chapter.txt` mit echten Werten | ❌ TODO |
| Tabelle 1 im Paper aktualisieren | ❌ TODO |
| Methods-Ergänzungen | ❌ TODO |

---

## 1. Text-Änderungen in `segmentation_chapter.txt`

Gesamter Text muss überarbeitet werden — nicht nur die `[CHANGE]`-Stellen.

### Satz 1 (Trainingsdaten)
**Alt:**
> "Training data ranged from 108 to 576 manually verified bouts across birds (mean: 234 ± 195 SD bouts)"

**Neu:**
> "Training data ranged from 108 to 579 manually verified bouts across birds (mean: 235 ± 194 SD bouts), comprising 75 to 405 training bouts (176–1407 s of annotated audio) per bird"

### Satz 2 (Konvergenz + Epochen) [war CHANGE]
**Alt:**
> "training and validation loss curves converged smoothly (Fig. 4A), with early stopping terminating training after 9-28 epochs (mean: 17 ± 5 epochs) [CHANGE]"

**Neu:**
> "training and validation loss curves converged smoothly (Fig. 4A), with early stopping terminating training after 10–24 epochs (mean: 15 ± 4 epochs)"

### Satz 3 (Framewise F1) [war CHANGE]
**Alt:**
> "mean F1 scores ranging from 0.938 to 0.962 [CHANGE] across birds (Table 1)"

**Neu:**
> "framewise F1-scores ranging from 0.882 to 0.962 across birds (Table 1)"

### Satz 4 (Onset Collar @10ms Range + gy07bu07) [war CHANGE]
**Alt:**
> "With a 10 ms collar, onset-based F1 scores ranged from 0.720 to 0.942 across birds (Table 1), with four birds achieving F1 ≥ 0.910 and one bird (Bird 3, gy07bu07) achieving 0.720 due to short inter-syllable intervals... [CHANGE]"

**Neu:**
> "With a 10 ms collar, onset-based F1 scores ranged from 0.817 to 0.986 across birds (Table 1), with four birds achieving F1 ≥ 0.949 and one bird (Bird 3, gy07bu07) achieving 0.817, attributable to a parameter mismatch between the bird-specific threshold (0.95) and the global sliding window parameters (see Discussion)."

### Satz 5 (Baseline-Vergleich — NEU, noch nicht im Text)
**Neu (nach dem Collar-Absatz einfügen):**
> "To benchmark performance, we compared Moove against an energy-based segmentation baseline using the same algorithm (evfuncs; Nicholson, 2021) that was used to generate training labels, with the threshold optimized on the validation set per bird. Moove outperformed the energy baseline at onset collar F1 @10ms for four of five birds (Δ = +0.06 to +0.12; Fig. 4C). Bird 3 is the sole exception (Moove: 0.817 vs Baseline: 0.903 at 10 ms collar), consistent with the sliding window parameter mismatch described above; the raw (unsmoothed) Moove onset F1 for Bird 3 was 0.926, exceeding the baseline."

---

## 2. Tabelle 1 aktualisieren

**Alt:** Total Bouts, Total Epochs, Test Accuracy (%), Test Loss  
**Neu:** Training Bouts, Training Duration (s), Epochs, Onset Collar F1 @5/10/15/20ms

Alle Werte stehen in `reviewer_requirements.md` (Abschnitt "Neue Tabelle 1").

---

## 3. Figure 4

**Erledigt.** Neue Figure liegt unter `segmentation_chapter/figure_4_code/figure4.png` und `figure4.svg`.

**Inhalt:**
- Panel A: Loss Curves (5 Subplots, train=farbig/solid, val=grau/gestrichelt, ±1 SD Shading)
- Panel B: Framewise P/R/F1 (dot plot, raw output)
- Panel C: Onset Collar F1 vs Tolerance 5–20 ms (mit Sliding Window, ±1 SD)
- Panel D: Training Duration (s, log-scale) vs Framewise F1 (scatter, 3 Punkte pro Bird)

**Quellen:** `final_experiments/results/{bird}/seg/seed_{n}/results.json`

---

## 4. Methods-Ergänzungen

Drei kurze Ergänzungen im Methods-Abschnitt:

1. **Threshold-Tuning:** Bird-spezifisch auf Val-Set, Optimierungskriterium = Onset Collar F1 @10ms
2. **Onset-Collar-Kriterium:** Definition TP = Onset innerhalb ±collar ms, Offset ignoriert
3. **Replikate:** 3 Seeds (42/123/456), alle Metriken als mean ± SD

---

## 5. Energy Baseline (Methodik)

Kurzer Absatz in Segmentation Results oder Discussion:
- 4/5 Birds: Moove besser (+0.06 bis +0.12 bei @10ms)
- Bird 3 (gy07bu07): Ausnahme wegen SW-Parameter-Bug (raw F1 = 0.926 > Baseline 0.903)
- Bias-Hinweis: GT-Labels energy-basiert erstellt → Baseline bevorzugt
