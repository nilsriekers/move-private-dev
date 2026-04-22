# eNeuro Revision: Reviewer-Anforderungen – Status & Fortschritt

**Stand:** 2026-04-22 | **Paper:** paper_new.txt | **Ziel:** Alle Anforderungen systematisch abarbeiten

---

## Übersicht: Kategorien

| Kategorie | Anforderungen | Status |
|-----------|---------------|--------|
| **Paper-Text** | Related Work, Modellresultate-Präsentation, Spezifische Textpassagen | ⚠️ Teilweise |
| **Daten/Zahlen** | [change]-Marker füllen | ✅ Meiste fertig |
| **Figuren** | Figure 4, 5, 6, 7, 8 überprüfen/neu generieren | ⚠️ Teilweise |
| **Tabellen** | Table 1, Table 2 mit neuen Metriken | ✅ Skripts vorhanden |
| **Code/Software** | Unit Tests, conda-forge, Installation | ❌ Ausstehend |
| **Dokumentation** | Installation, Software-Guides | ⚠️ Teilweise |

---

## I. PAPER-TEXT ANFORDERUNGEN

### ✅ 1.1 – Related Work Überarbeitung (MAJOR)

| # | Anforderung | Status | Priorität | Notizen |
|---|------------|--------|-----------|---------|
| 1.1.1 | Paragraph ab Zeile 96 überarbeiten: nicht "two-stage ist normal" sondern Unterscheidung Frame-Classification vs. two-stage | ❌ Ausstehend | **HOCH** | Reviewer schlägt Struktur vor |
| 1.1.2 | Vocal Activity Detection & Lightweight Binary Classifiers als Kontext einbauen | ❌ Ausstehend | **HOCH** | Baggi et al. 2023, Hughes & Mierle 2013 |
| 1.1.3 | Pearre et al. 2017 als related work ergänzen (closes-loop targeting) | ❌ Ausstehend | **HOCH** | Direkt relevant |
| 1.1.4 | Schultheiss vs. Kawaji Latenzen explizit nennen (~4ms vs ~109ms) | ❌ Ausstehend | **HOCH** | Im Intro motivieren |
| 1.1.5 | DAS/TweetyNet Frame-classification Ansätze klarer von 2-stage abgrenzen | ❌ Ausstehend | **HOCH** | WhisperSeg auch erwähnen |
| 1.1.6 | Unseren Kernbeitrag klarer herausarbeiten: onset-basiert statt offset-basiert | ❌ Ausstehend | **HOCH** | Unterschied zu Schultheiss |
| 1.1.7 | DAS-Closed-Loop Evidence prüfen (Reviewer sieht keine publizierten CL-Ergebnisse) | ❌ Ausstehend | MITTEL | Optional aber sauberer |

**Reviewer-Kommentar:** "I think you are missing an opportunity to link what you have done to broader areas of research."

---

### 📋 1.2 – Spezifische Textpassagen Überarbeiten

| # | Zeile/Abschnitt | ALT | NEU | Status | Notizen |
|----|----------------|----|-----|--------|---------|
| 1.2.1 | Zeile 141 | "but require faster inference" | "reduce latency and allow for faster inference" | ⚠️ Teilweise | Sprachliche Klarheit |
| 1.2.2 | Zeile 148 | [nicht erwähnt] | Zusammenhang zwischen "segmentation", "detection", "binary classification" explizit erklären | ❌ Ausstehend | Im Intro nicht in Methods |
| 1.2.3 | Zeile 155 | "segment membership (syllable/gap)" | Ausführlicher: "classify each frame as belonging to either syllables or background class..." | ❌ Ausstehend | Präzisierung |
| 1.2.4 | Zeile 236 | "algorithm-driven segmentation" | "energy-based segmentation methods" | ❌ Ausstehend | Präziserer Term |
| 1.2.5 | Zeile 249 | "with logits" | "binary cross entropy" | ❌ Ausstehend | Implementierungsdetail raus |
| 1.2.6 | Zeile 81 (Results) | [WN-Rolle nicht betont] | White Noise expliziter als "negative reinforcement" framem | ❌ Ausstehend | Kontextualisierung |
| 1.2.7 | Zeile 199 (Disc) | [knapp] | Alternative Feedback-Modalitäten erweitern + Implementierungsoptionen | ⚠️ Teilweise | Discussion |
| 1.2.8 | Zeile 250 (Methods) | [Hyperparameter teils nicht genannt] | Alle Hyperparameter explizit aufzählen (LR, batch size, dropout, etc.) | ⚠️ Teilweise | In Methods/Code teilweise vorhanden |

---

### 📊 1.3 – Modellresultate-Darstellung (MAJOR)

#### Tabelle 1 — Segmentation (erweitern)

| Anforderung | Aktueller Status | Zielwert | Notizen |
|-------------|------------------|----------|---------|
| Trainings-Datengröße in **Sekunden** | `[change]` | `108–576 bouts` aber auch Duration in Sekunden angeben | ❌ Ausstehend |
| Framewise P/R/F1 | Nur für Bird 1 im Text | Alle Birds in Tabelle | ❌ Ausstehend |
| Onset-based Collar F1 (@5, @10, @15, @20 ms) | Neue Metriken (onset-only) | Mehrere Collar-Werte | ⚠️ Teilweise |
| Energy-Baseline Vergleich | [nicht vorhanden] | Segmentierungsmetriken für energy-based Baseline | ❌ Ausstehend |
| Multiple Replicates Mean ± SD | Einzelne Werte | Alle Birds × 3 Replicates → Mean ± SD | ⚠️ Teilweise |
| Signal Onset Error (μ, σ) | `-1.7 ± 2.6 ms` | Aktuell im Text, sollte auch quantifiziert sein | ✅ Final |

**Reviewer:** "Table 1 and 2 are much more informative than Figures 4 and 5"

#### Tabelle 2 — Classification (aktuell)

| Anforderung | Status | Notizen |
|-------------|--------|---------|
| Test Accuracy + Macro F1 | ✅ Vorhanden | Bird 1–5, multiple replicates |
| Per-Class F1 (detailed) | ⚠️ Nur Bird 1 in Text | Sollte für alle Birds verfügbar sein oder sehr detailliert für Bird 1 |

#### Figur 4 — Segmentation

| Aspekt | Aktueller Zustand | Reviewer-Wunsch | Status |
|--------|-------------------|------------------|--------|
| (A) Loss-Kurven | Nur final values | Trainingsverlauf mit SummaryWriter/TensorBoard über Schritte | ❌ Ausstehend |
| (B) Framewise P/R/F1 | Vorhanden | Bleiben, aber mehrere Replikate mit SD-Banden | ✅ Teilweise |
| (C) Onset-Collar F1 | Raw Daten vorhanden | Mit verschiedenen Collar-Werten (5, 10, 15, 20 ms) | ⚠️ Teilweise |
| (D) Trainings-Datengröße vs. Performance | [nicht vorhanden] | Training set duration (seconds, log scale) vs. F1 | ❌ Ausstehend |

**Reviewer:** "instead of just plotting what you already have in tables, what I would really like to see is some sort of analysis"

#### Figur 5 — Classification

| Aspekt | Aktueller Zustand | Reviewer-Wunsch | Status |
|--------|-------------------|------------------|--------|
| (A) Loss-Kurven | Nur Accuracy/Loss | Trainingsverlauf über Schritte (wie Fig. 4A) | ❌ Ausstehend |
| (B) Test Accuracy + Macro F1 | Vorhanden | Dot Plot mit Error Bars (SD) für alle Birds | ⚠️ Teilweise |
| (C) Confusion Matrix | Bird 1 vorhanden | Bleiben wie ist oder für alle Birds | ✅ Teilweise |
| (D) Input Duration vs. Accuracy | Bird 1 5–50 ms | Bleiben wie ist | ✅ Teilweise |
| (E) UMAP 30ms | Bird 1 vorhanden | Bleiben wie ist | ✅ Teilweise |
| (F) UMAP full-length | Bird 1 vorhanden | Bleiben wie ist | ✅ Teilweise |

**Reviewer:** "Figures 4 and 5 are helpful [...] but I find them a bit hard to read"

---

### 🔢 1.4 – Konkrete Datenwerte ([change]-Marker füllen)

| # | Zeile | [change]-Marker | Wert (final/bereit) | Status | Notizen |
|----|-------|-----------------|-------------------|--------|---------|
| 1.4.1 | ~74 | `XXX–XXX epochs (mean: XXX ± XXX)` | `9–28 epochs (mean: 17 ± 5)` | ✅ Final | Seg-Training |
| 1.4.2 | ~76 | `XXX to XXX` F1 | `0.938 to 0.962` | ✅ Final | Framewise Seg F1 |
| 1.4.3 | ~76 | `[change]` onset collar | `0.720 to 0.942` @10ms | ✅ Final | Neue Metrik |
| 1.4.4 | ~77 | `[change]` Bird 3 collar | `0.720 due to short inter-syllable intervals` | ✅ Final | Bird-spezifisch |
| 1.4.5 | ~77 | `[change]` Bird 3 raw F1 | `0.937 without sliding window` | ✅ Final | Network raw F1 |
| 1.4.6 | ~78 | `[change]` onset error | `-1.7 ± 2.6 ms (median: -1.5 ms)` | ✅ Final | Onset-Fehler nur |
| 1.4.7 | ~81 | `3,099 to 18,505 syllables` | `947 to 18,335 syllables` | ✅ Final | Class Training-Daten |
| 1.4.8 | ~81 | `0.908 to 0.978` Accuracy | Bleibt wie ist | ✅ Final | Class Test Acc |
| 1.4.9 | ~81 | `0.869 to 0.977` Macro F1 | Bleibt wie ist | ✅ Final | Class Macro F1 |
| 1.4.10 | ~81 | `12–26 epochs (mean: 18 ± 5)` | `12–34 epochs (mean: 21 ± 8)` | ✅ Final | Class Training |
| 1.4.11 | ~70 | `X and Y days` post-screening | `16 and 37 days` | ✅ Final | Post-Screening |
| 1.4.12 | ~93-94 | `XXX bouts`, `XXX%` repeat targeting | **[ausstehend]** | ❌ Ausstehend | Position-specific targeting Stats |

**Status Zusammenfassung:** Die meisten numerischen Platzhalter sind bereit (aus PAPER_CHANGES.md und Daten), nur repeat-targeting (1.4.12) und eventuell weitere Details ausstehend.

---

## II. FIGUREN & VISUALISIERUNGEN

### Figure 4 – Segmentation Network Performance

| Aspekt | Datei | Status | Aktion |
|--------|-------|--------|--------|
| **Vorhanden** | `new_plots/figure_4/figure4.png/.svg` | ✅ Existiert | Prüfen ob mit Reviewer-Anforderungen konform |
| **(A) Loss-Kurven** | Erzeugt? | ⚠️ Teilweise | TensorBoard-Logging für echte Trainingskurven nötig |
| **(B) Framewise P/R/F1** | `generate_figure4.py` | ⚠️ Teilweise | Mit SD-Banden über Replikate |
| **(C) Onset-Collar F1** | `baseline_results.json` | ⚠️ Teilweise | Mehrere Collar-Werte (@5, @10, @15, @20) |
| **(D) Training Size vs. F1** | [nicht vorhanden] | ❌ Ausstehend | Neu generieren: x=Duration(s), y=F1 |
| **Gesamtstatus** | Teilweise final | ⚠️ | Sollte vor Submission nochmal überprüft werden |

**Reviewer-Feedback:** "I find them a bit hard to read" und "analysis that helps us understand the differences"

### Figure 5 – Classification Network Performance

| Aspekt | Datei | Status | Aktion |
|--------|-------|--------|--------|
| **Vorhanden** | `new_plots/figure_5/figure5.png/.svg` | ✅ Existiert | Aber Struktur anpassen? |
| **(A) Loss-Kurven** | Erzeugt? | ⚠️ Teilweise | TensorBoard-Logging wie Fig. 4 |
| **(B) Test Acc + Macro F1** | `generate_figure5.py` | ✅ Vorhanden | Dot plot mit Error Bars OK |
| **(C) Confusion Matrix** | Bird 1 | ✅ Vorhanden | Bleiben wie ist |
| **(D) Input Duration** | Bird 1 5–50ms | ✅ Vorhanden | Bleiben wie ist |
| **(E)/(F) UMAP** | Bird 1 | ✅ Vorhanden | Bleiben wie ist |
| **Gesamtstatus** | Überarbeitung nötig | ⚠️ | Neue Generate-Skripts? |

**Unklarheit:** Reviewer schlägt vor, dass (A) die Loss-Kurven zeigen sollte (wie Fig. 4A), nicht Accuracy. Aktuell in figure5 sind möglicherweise A und B getauscht?

### Figure 6 – Latency Characterization

| Aspekt | Status | Reviewer-Wunsch |
|--------|--------|-----------------|
| Vorhanden | ✅ | — |
| (A) Spectrogram mit latency-Messung | ✅ | OK wie ist |
| (B) Latency-Verteilungen über Buffer-Konfigurationen | ✅ | OK wie ist |

### Figure 7 – Repeat Targeting with Position-Specific Feedback

| Aspekt | Status | Reviewer-Wunsch | Aktion |
|--------|--------|-----------------|--------|
| Vorhanden | ✅ | — | |
| Beispiel-Spectrogramm | ✅ | OK wie ist | |
| **Accuracy-Metriken** | ❌ Fehlen | "Some accuracy measures along with false positive and false negative proportions would be useful" | **WICHTIG:** Fehlerquoten für Targeting berechnen |
| Gesamtstatus | ⚠️ Teilweise | Metrics ergänzen | Siehe [change]-Marker 1.4.12 |

**Reviewer:** "it is unclear how reliably they were able to do this"

### Figure 8 – Sequence Modification Learning Experiment

| Aspekt | Status | Notizen |
|--------|--------|---------|
| Vorhanden | ✅ | — |
| (A) Example spectrogram | ✅ | OK |
| (B) Transition probabilities summary | ✅ | OK |
| (C) Probabilities across days + resampling | ✅ | OK |
| (D) Proportion of bouts with target sequence | ✅ | OK |
| Gesamtstatus | ✅ | Keine kritischen Änderungen erforderlich |

---

## III. TABELLEN

### Table 1 – Segmentation Network Performance

**Aktueller Status:** Skripts vorhanden, aber Metrics müssen erweitert werden.

| Metrik | Aktuell | Reviewer-Wunsch | Skript | Status |
|--------|---------|-----------------|--------|--------|
| Bird ID | ✅ | ✅ | `generate_table1.py` | ✅ |
| Total Bouts | ✅ | Zusätzlich: Duration in Sekunden | `generate_table1.py` | ⚠️ |
| Syllable Count | — | Optional | — | — |
| Framewise P, R, F1 | ⚠️ Nur Bird 1 im Text | Für alle Birds in Tabelle | ❌ | ❌ |
| Onset-Collar F1 (@5, @10, @15, @20) | Neue Werte vorhanden | Mehrere Collar-Werte in einer Spalte | `baseline_results.json` | ⚠️ |
| Test Loss | ✅ | Optional (Reviewer: "you don't get a lot out of reporting loss") | — | ✅ |
| Energy-Baseline Metrics | ❌ | "show your model does better than that approach" | `energy_baseline.py` | ❌ |

**Skripte vorhanden:**
- `new_plots/figure_4/generate_table1.py` — erzeugt aktuelle Table 1
- `new_plots/figure_4/energy_baseline.py` — für Baseline-Vergleich

**Aktion:** Skripte überprüfen/erweitern, dann neue Table 1 generieren.

### Table 2 – Classification Network Performance

**Aktueller Status:** Grundstruktur vorhanden.

| Metrik | Aktuell | Reviewer-Wunsch | Status |
|--------|---------|-----------------|--------|
| Bird ID | ✅ | ✅ | ✅ |
| Total Bouts/Syllables | ✅ | ✅ | ✅ |
| Syllable Classes | ✅ | ✅ | ✅ |
| Test Accuracy (%) | ✅ | Mit Mean ± SD über Replikate | ✅ Teilweise |
| Test Loss | ✅ | Optional | ✅ |
| Macro P/R/F1 | ⚠️ Nicht in Tabelle? | In separater Tabelle oder zusätzliche Spalten | ⚠️ |

**Skript:** `new_plots/figure_4/generate_table2.py` vorhanden.

---

## IV. REVIEWER-FEEDBACK ZU CODE & SOFTWARE

### A. Installation & Dependencies

| # | Problem | Reviewer-Lösung | Priorität | Status |
|----|---------|-----------------|-----------|--------|
| 4.1 | tkinter auf Linux schwierig (pyenv, multiple Python versions) | PyQt statt Tkinter | LANGFRISTIG | ❌ |
| 4.2 | poetry wirft Fehler (`name`, `version` missing) | Auf `uv` oder `pixi` wechseln | LANGFRISTIG | ❌ |
| 4.3 | sounddevice/portaudio plattformspezifisch | **conda-forge Package** | MITTELFRISTIG | ❌ |
| 4.4 | Dokumentation Installation unklar | Bessere Docs für Linux/Windows | MITTELFRISTIG | ⚠️ |
| 4.5 | Upper-bounds in Dependencies (`torch < 2.6`) | Lower-bounds statt Upper-bounds | MITTELFRISTIG | ❌ |

**Reviewer:** "I would encourage you to invest the development and maintenance time needed to provide alternatives."

### B. Code Quality & Testing

| # | Anforderung | Status | Priorität | Notizen |
|----|-------------|--------|-----------|---------|
| 4.6 | **Unit Tests** fehlen | ❌ Nicht vorhanden | MITTELFRISTIG | Konsultiere pyopensci.org, scientific-python.org |
| 4.7 | Separate **Docs Site** (nicht PDF) | ❌ Nur PDF | LANGFRISTIG | ReadTheDocs oder ähnlich |
| 4.8 | Framewise P/R/F1 **richtig berechnen** | ⚠️ Teilweise | MITTELFRISTIG | Siehe vocalpy.metrics.segmentation |
| 4.9 | Class-weighted BCE (optional, methodisch sauberer) | ⚠️ Teilweise | LANGFRISTIG | Für Klassenungleichgewicht |
| 4.10 | **TensorBoard/SummaryWriter** für Loss-Kurven | ❌ Nicht vorhanden | MITTELFRISTIG | Für Figure 4/5 neue Kurven |

**Reviewer:** "it meets most criteria for 'good enough' scientific software" — also schon ok, aber Verbesserungspotenzial.

### C. conda-forge Paketierung

| Schritt | Status | Notizen |
|---------|--------|---------|
| Package auf PyPI | ✅ Vermutlich | Voraussetzung für conda-forge |
| Alle Deps auf conda-forge verfügbar | ⚠️ Zu prüfen | portaudio, sounddevice, torch vorhanden? |
| Conda-forge Recipe (mit `greyskull`) | ❌ Ausstehend | Skript ist einfach — siehe https://conda-forge.org/docs/maintainer/adding_pkgs/#generating-the-recipe |

**Reviewer-Rationale:** "Conda-forge [...] you can avoid some of the pain of installing a system-wide portaudio package"

---

## V. DOKUMENTATION

### 5.1 – Installation Guide

| Aspekt | Aktuell | Reviewer-Wunsch | Status |
|--------|---------|-----------------|--------|
| **Linux** | [unklar] | Explizit tkinter/pyenv fallback | ⚠️ |
| **Windows** | [unklar] | Poetry-Fehler bekannt & Lösungen | ⚠️ |
| **macOS** | ? | — | ⚠️ |
| **Conda Installation** | ? | Optional aber empfohlen | ❌ |
| **Known Issues** | ? | Tkinter, Poetry, sounddevice fallback | ⚠️ |

**Reviewer:** "it is just no easy way to set up [...] especially if you already have multiple versions of python installed"

### 5.2 – Hyperparameter & Configuration

| Anforderung | Aktuell | Ziel | Status |
|-------------|---------|------|--------|
| Alle Hyperparameter dokumentiert | ⚠️ Teilweise | Learning rate, dropout, batch size, etc. zentral dokumentiert | ⚠️ |
| Augmentation-Techniken erklärt | ⚠️ Teilweise (im Text) | Auch im Code klar nachvollziehbar | ⚠️ |
| Reproduzierbarkeit (Seeds, Splits) | ✅ Wahrscheinlich | — | ✅ |

---

## VI. CATCH-ALL: KLEINERE PUNKTE

| # | Reviewer-Kommentar | Zeile | Aktion | Status |
|----|-------------------|-------|--------|--------|
| 6.1 | "negative reinforcement" explizit | ~81 | Text anpassen | ❌ |
| 6.2 | Post-screening Sessions konkrete Tage | ~487 | "16 and 37 days" | ✅ Final |
| 6.3 | Catch-Trial Definition unklar | ~465 | Erklären was geändert wurde | ⚠️ |
| 6.4 | Transition Probability Berechnung intransparent | ~472-477 | Detailliert erklären | ⚠️ |
| 6.5 | Onset vs. Offset Error Statistics | ~346 | Absolut-Fehler für beides melden | ⚠️ |
| 6.6 | Repeat Targeting Accuracy | Fig. 7 | Fehlerquoten berechnen | ❌ |

---

## 📋 PRIORISIERUNG: Was zuerst tun?

### **BLOCK 1: Sofort (kritisch für Submission)**

- ✅ [change]-Marker füllen (meiste Daten vorhanden)
- ⚠️ **Related Work Überarbeitung** (~2–3h Text-Überarbeitung)
- ⚠️ **Figure 4/5 Überprüfung** (Reviewer-Anforderungen vs. Aktuell)
- ❌ **Figure 7 Targeting-Accuracy** (neue Metrik nötig)

### **BLOCK 2: Mittelfristig (vor oder kurz nach Submission)**

- ❌ **Table 1 erweitern** (framewise P/R/F1, Collar-Werte, Energy-Baseline)
- ❌ **TensorBoard Loss-Kurven** (Fig. 4A, 5A neu generieren)
- ❌ **Figure 4D:** Training-Datengröße vs. Performance
- ⚠️ **Installation Dokumentation** verbessern
- ❌ **Unit Tests beginnen**

### **BLOCK 3: Langfristig (nach Akzeptanz, für Code-Release)**

- ❌ PyQt Migration
- ❌ Poetry → uv/pixi
- ❌ conda-forge Package
- ❌ Separate Docs Site
- ❌ Class-weighted BCE (optional)

---

## 🎯 IMPLEMENTIERUNGS-ROADMAP

### Phase 1: Paper fertig für Submission (1–2 Wochen)

1. **Related Work überarbeiten** (Zeile ~96–)
   - Draft: "Drei Kategorien erklärt..."
   - Neue Literatur einfügen
   - Unseren Ansatz als "onset-basiert" klar machen

2. **Alle [change]-Marker füllen**
   - Zahlen aus PAPER_CHANGES.md / Daten einsetzen
   - Spezifische Textpassagen prüfen (1.2.1–1.2.8)

3. **Figures überprüfen & evtl. finalisieren**
   - Figure 4: Mit neuen Daten/Metriken aktuell?
   - Figure 5: Caption prüfen
   - Figure 7: Targeting-Accuracy berechnen & hinzufügen

4. **Tabellen nochmal generieren & prüfen**
   - `generate_table1.py`, `generate_table2.py` laufen
   - Werte mit Paper-Text synchronisieren

### Phase 2: Kurz nach Submission (parallel)

5. **Code-Anforderungen angehen**
   - Framewise P/R/F1 richtig dokumentieren
   - TensorBoard-Logging für Loss-Kurven
   - Unit Test Skelett

6. **Installation Docs verbessern**
   - Linux/Windows/macOS separate Abschnitte
   - Known Issues & Workarounds

### Phase 3: Nach Akzeptanz

7. **conda-forge Package**
8. **PyQt Migration evaluieren**
9. **Separate Docs Site aufbauen**

---

## 📊 AKTUELLE STATUS-ZUSAMMENFASSUNG

| Kategorie | Fertig | Teilweise | Ausstehend |
|-----------|--------|-----------|-----------|
| **Paper-Text** | 20% | 40% | 40% |
| **Daten/Zahlen** | 70% | 20% | 10% |
| **Figuren** | 40% | 40% | 20% |
| **Tabellen** | 30% | 40% | 30% |
| **Code/Software** | 10% | 20% | 70% |
| **Dokumentation** | 20% | 30% | 50% |
| **GESAMT** | **27%** | **32%** | **41%** |

---

## 🔗 WICHTIGE DATEIEN

- **Paper-Text:** `/Users/riekers/git/maintain_moove/moove/paper_new.txt`
- **Paper-Änderungen (Referenz):** `/Users/riekers/git/maintain_moove/moove/PAPER_CHANGES.md`
- **Reviewer-Feedback (Quelle):** `/Users/riekers/git/maintain_moove/moove/eneuro_review_todos.txt`
- **Figure 4 Skripte:** `/Users/riekers/git/maintain_moove/moove/new_plots/figure_4/`
- **Figure 5 Skripte:** `/Users/riekers/git/maintain_moove/moove/new_plots/figure_5/`
- **Final Experiments Results:** `/Users/riekers/git/maintain_moove/moove/final_experiments/results/`

---

## 🚀 NÄCHSTE SCHRITTE (deine Anweisung)

1. **Markiere deine Priorität:** Was willst du als erstes angehen?
2. **Reviewer-Related-Work Feedback:** Willst du den Vorschlag des Reviewers adaptieren oder selbst umschreiben?
3. **Figures & Tables:** Sollen Figure 4/5 neu generiert werden oder nur aktualisiert?
4. **Zeitrahmen:** Wann soll das Paper submission-ready sein?

