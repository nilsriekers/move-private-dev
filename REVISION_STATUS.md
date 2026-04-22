# Revision Status – Response to Reviewer Comments
> Basis: `response_2_reviewers.txt` × `paper_new.txt` | Stand: 2026-04-22
> Tags: [TEXT] [ANALYSIS] [CODE] [FIGURE] [TABLE] [INFO]
> Status: ✅ erledigt | ⚠️ teilweise / zu prüfen | ❌ ausstehend

---

## Synthesis Statement

| # | Kommentar | Status | Notiz |
|---|-----------|--------|-------|
| — | Editor: Software-Kommentare beachten | ✅ | Adressiert unter 4.x |
| — | Manuskript umfassend überarbeiten | ✅ | Großteils erledigt |

---

## 1 – Related Work (Introduction)

| # | [TAG] Anforderung | Status | Verifikation in paper_new.txt |
|---|-------------------|--------|-------------------------------|
| 1.1 | [TEXT] Paragraph ab Zeile 96 umschreiben: klar zwischen Frame-Classification (DAS, TweetyNet) und Two-Stage-Ansatz unterscheiden | ✅ | Zeile 33: „Models such as DAS...assign a label to each audio frame...Other approaches first detect syllable segments..." |
| 1.2 | [TEXT] Kernbeitrag explizit nennen: binäres Modell → schnelle Segmentierung; Onset statt Offset | ✅ | Zeile 35: „classifies syllables using acoustic information from shortly after onset rather than waiting for offset" |
| 1.3 | [TEXT] Latenzen von Schultheiss (~4 ms) und Kawaji (~109 ms) im Intro nennen; VAD/Bioacoustics-Kontext | ✅ Intro / ✅ Disc | Zeile 33: „reporting approximately 4 ms...Kawaji et al. report approximately 109 ms". VAD/Bioacoustics in Discussion (Zeile 108), wegen Wortlimit. |
| 1.4 | [TEXT] Zwei-Teil-Struktur des Reviewers als Vorlage nutzen | ✅ | Umgesetzt in Intro + Discussion |
| 1.5 | [TEXT] Pearre et al. 2017 zitieren | ✅ | Zeile 33: „Pearre et al. (2017) demonstrated low-latency detection..." |
| 1.6 | [TEXT] DAS Closed-Loop-Evidenz prüfen | ✅ | Zeile 108 (Discussion): „we are not aware of published results from actual closed-loop experiments using DAS" |
| 1.7 | [TEXT] Kawaji-Ansatz kurz erklären (warum hohe Latenz) | ✅ | Zeile 108: „threshold-based spectral change detection...long temporal windows that likely include preceding syllables" |
| 1.8 | [TEXT] WhisperSeg erwähnen | ✅ | Zeile 108: „transformer-based approaches such as WhisperSeg (Gu et al., 2024)...orders of magnitude larger" |
| 1.9 | [TEXT] Neue Refs: Graves 2012, Stowell 2022, Hughes & Mierle 2013, Kershenbaum 2016/2025, Baggi 2023, WhisperSeg | ✅ | Alle im Text (Graves Z.33, Hughes/Stowell/Kershenbaum/Baggi Z.108). Fukuzawa bewusst nicht zitiert. |

---

## 2 – Results: Modellperformance

| # | [TAG] Anforderung | Status | Verifikation in paper_new.txt |
|---|-------------------|--------|-------------------------------|
| 2.1 | [ANALYSIS][TEXT] Framewise P/R/F1 für alle 5 Birds (nicht nur Bird 1); downsampling statt gewichtetes BCE | ✅ | Zeile 75: „Framewise precision, recall, and F1-score were computed for each bird's test set (Fig. 4B)". Werte im Text und Table. Downsampling in Methods Z.60. |
| 2.2 | [ANALYSIS][TABLE] Collar-Metriken @5, @10, @15, @20 ms mit Onset-only-Kriterium; Energy-Baseline-Vergleich | ✅ Text + ⚠️ Table | Zeile 77: Onset-only-Kriterium + Werte @10ms. Table 2 zeigt Col@10 + Col@20, aber **kein @5/@15 und keine Energy-Baseline-Spalte sichtbar**. Baseline-Daten in `baseline_results.json` vorhanden. |
| 2.3 | [TABLE] Trainingsset-Größe in Sekunden (zusätzlich zu Bouts) | ✅ | Table 2 (Segmentierung): „Dur"-Spalte mit Werten (5798, 174, 274, 1557, 180 s). |
| 2.4 | [ANALYSIS] 3 Replikate pro Bird, Mean ± SD aller Metriken | ✅ | Zeile 75: „three replicates per bird with different random seeds...mean ± standard deviation across replicates" |
| 2.5 | [FIGURE] Fig. 4 ersetzen durch: (A) Loss-Kurven, (B) FW P/R/F1, (C) Collar F1, (D) Trainings-Duration vs. F1-Scatter | ❌ | Caption in paper_new.txt Z.76 ist aktualisiert. **Aber: `response_2_reviewers.txt` enthält explizit „Figure 5 TODO"** — Fig. 5 unfertig. Auch mehrere `[CHANGE]`-Marker in Results-Text noch drin (Z.75, Z.77, Z.81). |
| 2.6 | [CODE][FIGURE] TensorBoard-Logging; Loss-Kurven über Trainingssteps (nicht nur Endwert) | ✅ Caption | Loss-Kurven in Fig. 4A + 5A laut Caption. Ob tatsächlich generiert: file `figure4.png` existiert (April 9), `figure5.png` (April 1). |
| 2.7 | [TABLE] Loss-Werte aus Tabellen entfernen | ✅ | Tables haben keine Loss-Spalte mehr: Table 1 (Cls/Acc/Mac-F1), Table 2 (FW-P/R/F1/Col@10/Col@20). |

**⚠️ Zusätzlich gefunden:** Die Tabellen-Labels in paper_new.txt sind **vertauscht**: Table 1 ist mit „Segmentation" beschriftet, enthält aber Classification-Daten (Cls, Acc, Mac-F1); Table 2 ist mit „Classification" beschriftet, enthält aber Segmentation-Daten (Dur, FW-F1, Col@10). Muss im Word-Dokument korrigiert werden.

**⚠️ Noch aktive `[change]`-Marker in paper_new.txt:**
- Z.75: `XXX to XXX seconds` (Trainingsdauer-Range) + `[CHANGE]` bei Epochen + F1
- Z.77: `[CHANGE]` am Satzende (gy07bu07 raw F1)
- Z.81: 4× `[change]` bei Classification-Werten (Syllables, Accuracy, Macro-F1, Epochen)

---

## 3 – Minor Comments

| # | [TAG] Anforderung | Status | Verifikation in paper_new.txt |
|---|-------------------|--------|-------------------------------|
| 3.1 | [TEXT] Z.141: „reduce latency and allow for faster inference" | ✅ | Z.45: „allowing rapid syllable onset detection and thereby reducing latency" |
| 3.2 | [TEXT] Segmentation = Binary Classification schon im Intro erklären | ⚠️ | In Methods Z.47 erklärt. Im Intro selbst nicht explizit — Methods-Verweis reicht ggf. |
| 3.3 | [TEXT] MLP-Formulierung: „classify each frame as belonging to either syllables or the background class..." | ✅ | Z.48: „background class, consisting of silent gaps and all other non-syllable sounds" |
| 3.4 | [TEXT] „approximately 690 inferences per second" | ✅ | Z.48: vorhanden |
| 3.5 | [TEXT] „algorithm-driven segmentation" → „energy-based segmentation" | ✅ | Z.58: „energy-based method" / Fig. 3 Caption: „energy-based threshold method" |
| 3.6 | [TEXT] „with logits" entfernen | ✅ | Z.60: nur „binary cross-entropy loss" |
| 3.7 | [ANALYSIS] Fig. 7: Repeat-Targeting Accuracy, FP-Rate, FN-Rate berechnen | ❌ | Z.94: Platzhalter `n = XXX`, `XXX%`, `XXX/XXX` noch im Paper. Benötigt Analyse der MooveTAF-Logs vom Repeat-Targeting-Experiment. |
| 3.8 | [TEXT] „negative reinforcement" oder Rolle von WN stärker betonen | ⚠️ | „aversive white noise" ist in Z.31 bereits drin. „negative reinforcement" bewusst nicht verwendet (falsche Fachterminologie). **Mit Lena besprechen** ob Formulierung ausreicht. |
| 3.9 | [TEXT] Discussion: andere Feedback-Modalitäten erweitern | ✅ | Z.123: somatosensory, microstimulation, optogenetics etc. erwähnt |
| 3.10 | [TEXT][CODE] Alle Hyperparameter explizit aufführen | ✅ | Z.60+65: LR, batch size, dropout (seg: 0.5, cls: 0.1), Adam, early stopping patience=5, split 70/15/15 |
| 3.11 | [TEXT][CODE] Augmentations beschreiben (welche, Parameter) | ✅ | Z.65: alle 4 Techniken mit Parametern (Gauss noise 0.0001, freq/time mask 10, dyn. range compression 0.5) |
| 3.12 | [TEXT] SD vs. SEM spezifizieren; Median ergänzen | ⚠️ | Seg-Results Z.75: „mean ± standard deviation" explizit. Z.78: „−1.7 ± 2.6 ms (median: −1.5 ms)" ✅. Aber z.B. Z.79 Inference-Speed „0.73 ms ± 0.1 ms" und Z.81 Classification ohne explizit SD. **Noch durchgehen.** |
| 3.13 | [ANALYSIS] Onset- und Offset-Fehler (signed diff auto vs. manuell) für alle Birds | ⚠️ | Z.78: Onset-Error vorhanden (−1.7 ± 2.6 ms, Median −1.5 ms). **Offset-Error fehlt** im Paper-Text. Response enthält Per-Bird-Tabelle inkl. Offsets, aber diese steht nicht in paper_new.txt. |
| 3.14 | [FIGURE] Fig. 6 Caption: welcher Repeat wurde getargetet? | ✅ | Z.92: „second occurrence of syllable 'a' within a repeat phrase was targeted" |
| 3.15 | [TEXT] Catch-Trial-Definition: ursprünglich vs. geändert erklären | ✅ | Z.98: Unterschied erklärt |
| 3.16 | [TEXT] Transition-Probability-Berechnung und Resampling transparent machen | ✅ | Z.99: detailliert beschrieben |
| 3.17 | [TEXT] Post-Screening-Timing konkret angeben | ✅ | Z.71: „16 and 37 days after the last training day" |

---

## 4 – Software Comments

| # | [TAG] Anforderung | Status | Notiz |
|---|-------------------|--------|-------|
| 4.1 | [CODE][DOCS] Installation verbessern (Linux/Windows-Probleme) | ✅ | PyQt6-Migration, uv, CI-Tests, Sphinx-Docs laut Response |
| 4.2 | [INFO] Reviewer 2: kurze Installationsprobleme | ✅ | Gleiche Maßnahmen wie 4.1 |
| 4.3 | [CODE][DOCS] Unit Tests + separate Docs-Site | ✅ | 199 Tests, GitHub Actions CI, Sphinx-Site laut Response |
| 4.4 | [CODE] tkinter-Abhängigkeit auf Linux eliminieren | ✅ | PyQt6-Migration abgeschlossen (Branch: pyqt6-migration) |
| 4.5 | [CODE] Poetry-Fehler auf Windows beheben | ✅ | Auf uv/hatchling migriert |
| 4.6 | [CODE] PyQt statt tkinter | ✅ | Vollständig migriert |
| 4.7 | [CODE] uv statt Poetry | ✅ | uv + PEP 735 dependency groups |
| 4.8 | [CODE] conda-forge Package | ❌ | Recipe vorbereitet, aber **noch nicht submitted**. Explizit: „TODO wenn keine Änderungen mehr zu erwarten sind." |
| 4.9 | [CODE][DOCS] Niedrigschwellige Installationswege | ✅ | Durch 4.1–4.7 abgedeckt |
| 4.10 | [CODE] Version-Constraints: Upper-Bounds entfernen | ✅ | Lower-bounds-only laut Response |

---

## Zusammenfassung offene Punkte

| Priorität | # | Was fehlt |
|-----------|---|-----------|
| 🔴 **sofort** | 2.5 | Figure 5 fertigstellen (TODO); `[change]`-Marker in paper_new.txt ausfüllen (Z.75, 77, 81) |
| 🔴 **sofort** | 3.7 | Repeat-Targeting Stats (FP/FN) aus MooveTAF-Logs berechnen → XXX-Platzhalter füllen |
| 🔴 **sofort** | — | Tabellen-Labels in Word-Dokument korrigieren (Table 1 ↔ Table 2 falsch beschriftet) |
| 🟡 **bald** | 3.13 | Offset-Error in Paper-Text einfügen (Daten in response_2_reviewers.txt vorhanden) |
| 🟡 **bald** | 3.8 | Mit Lena besprechen: reicht „aversive WN" oder soll „negative reinforcement" rein? |
| 🟡 **bald** | 3.12 | Alle ±-Stellen im Text durchgehen und SD explizit angeben |
| 🟡 **bald** | 2.2 | Energy-Baseline in Table 1 einfügen; @5ms und @15ms Collar-Spalten prüfen |
| 🟢 **später** | 4.8 | conda-forge Recipe submittens (nach finaler Code-Stabilisierung) |
