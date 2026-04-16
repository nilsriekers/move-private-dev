# Reviewer 3.7 — Notes & Erkenntnisse

## Was der Reviewer wollte
> "For Fig. 7, where the authors target the 4th syllable in a repeat phrase, it is unclear
> how reliably they were able to do this. Some accuracy measures along with false positive
> and false negative proportions would be useful."

**Er will konkret:** TP-Rate, FP-Rate für das 4th-a Targeting.
- TP: MooveTAF hat 4th 'a' korrekt erkannt und WN ausgelöst
- FP: MooveTAF hat WN ausgelöst, aber zur falschen Zeit / falscher Run

---

## Datenlage

**92 Aufnahmen = 92 Bouts** (1 recording = 1 bout, bestätigt).

**Das Logfile hat mehr Einträge** — enthält alle Vokalisierungen die MooveTAF verarbeitet hat
(Gesang UND Calls), nicht nur Song-Bouts. Deshalb: im Reviewer-Text keine Zahl aus dem Log
nennen. Stattdessen: "in den 92 aufgezeichneten Bouts..."

**Von diesen 92 Bouts:**
- 12 haben `[de]aaaa$` im Log (= MooveTAF hat 4th-a Pattern erkannt)
  - 10 davon: WN tatsächlich ausgelöst
  - 2 davon: Pattern erkannt, aber WN intentional unterdrückt (Catch-Trial)
- 72 sind Catch-Trials ohne Trigger
- 8 haben andere Positionen getriggert (2, 6, 8... a's)

---

## WAV-Dateiformat (wichtig für Timing-Analyse)

- WAVs sind **volle Bout-Aufnahmen** (7–41 Sekunden), NICHT gecroppt auf T_before+T_after
- `T Before = 2.0s` im .rec = Ringpuffer-Parameter; der Aufnahmestart liegt 2s vor dem Trigger
- `trig time = 2000 ms` im .rec = WN-Trigger liegt immer bei 2000ms ab Aufnahmestart
- **WN-Zeiten** im .rec und **Onsets/Offsets** im .not.mat sind beide **absolut ab WAV-Start** → direkter Vergleich möglich
- `.not.mat`-Zeiten sind in **ms** (evfuncs-Format), keine Konversion nötig

---

## Analyse-Ergebnis (final)

Aus den **10 WN-Delivery-Bouts** (= 12 minus 2 Catch):

| Outcome | n | % |
|---|---|---|
| TP (WN im Annotationsfenster) | 6 | 60% |
| FP_timing (WN außerhalb Fenster) | 4 | 40% |

Aus den **12 detektierten Bouts** gesamt:

| | n |
|---|---|
| Detektiert gesamt | 12 |
| WN ausgelöst | 10 |
| davon TP | 6 |
| davon FP_timing | 4 |
| Catch (detektiert, kein WN) | 2 |

---

## FP_timing — Ursache

**Timing-Fenster:** onset_4 − 100ms bis offset_4 + 500ms

| Bout | WN [ms] | Nächstes Fenster [ms] | Δ |
|---|---|---|---|
| 115531 | 9942 | 10028–10769 | −185ms |
| 115923 | 8311 | 10565–11324 | −2354ms |
| 124534 | 6387 | 8094–8838 | −1807ms |
| 143043 | 8310 | 7441–8179 | +769ms (nach Fenster) |

WN kommt in 3 von 4 Fällen **deutlich zu früh** → MooveTAF hat einen früheren
`[de]aaaa`-Run im Bout detektiert, der in der OldNotMat nicht als solcher annotiert ist.

**Ursache: Mehrfach-Runs pro Bout.**
Der Vogel singt mehrere `[de]aaaa`-Runs pro Bout (bis zu 5 beobachtet, z.B. Bout 132156 mit 5 Runs).
MooveTAF triggert beim ersten matching Run; die Annotation erfasst einen anderen (späteren) Run.

---

## Catch-Trial-Bouts (131843 + 133448)

Beide haben:
- `[de]aaaa$` im Log (Pattern wurde von MooveTAF detektiert)
- `catch_song msec: 0` im .rec (WN intentional unterdrückt)
- Keine WN-Delivery
- Annotation zeigt KEINEN `[de]aaaa`-Run (Labels passen nicht)

→ Diese sind **keine FPs** — WN wurde nie ausgelöst, daher kein falscher Trigger.
→ Ob die Detektion inhaltlich korrekt war, ist nicht verifizierbar (kein WN-Timing zum Abgleich).
→ Annotierungs-Diskrepanz möglich (OldNotMat vs. Echtzeit-Detektor).

---

## Offene Fragen

- [ ] **Catch-Rate (78%)**: War intentional? Für FN-Analyse relevant, aber nicht primäres Ziel.
- [ ] **Cross-check OldNotMat vs. corrected NotMat** für die 4 FP_timing-Bouts — enthält corrected NotMat die früheren Runs?

---

## Analyse-Skript & Daten

- Script: `new_plots/reviewer_3_7/analyze_repeat_targeting.py`
- Ergebnisse: `new_plots/reviewer_3_7/results.json`
- Timing-Fenster: onset_4 − 100ms bis offset_4 + 500ms
