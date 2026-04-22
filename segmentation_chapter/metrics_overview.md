# Segmentation Metrics — Übersicht

Alle Metriken aus `final_experiments/results/` (5 Birds × 3 Seeds: 42, 123, 456).  
Backup der zugehörigen `results.json`-Dateien: `results_backup/`.

---

## 1. Framewise Metriken (chunk-level, frame-by-frame)

Berechnet direkt auf den Netzwerk-Rohdaten (nach Threshold, **vor** Sliding Window).

| Bird | Framewise Precision | Framewise Recall | Framewise F1 |
|---|---|---|---|
| ye00pu07 | — | — | 0.962 ± 0.001 |
| bu04bk04 | — | — | 0.928 ± 0.008 |
| gy07bu07 | — | — | 0.914 ± 0.003 |
| br08pk08 | — | — | 0.945 ± 0.004 |
| ye04gr05 | — | — | 0.882 ± 0.015 |

**Vollständige P/R/F1 aus REPORT.md (Abschnitt 2.1):**  
Die genauen Per-Bird-Werte für Precision und Recall sind in den `results.json`-Backups unter `framewise.precision` / `framewise.recall` / `framewise.f1` verfügbar.

> **Hinweis:** Diese Metriken entsprechen dem **raw output** des Netzwerks — sie reflektieren, wie gut das Netz einzelne Frames klassifiziert, aber **nicht** die tatsächliche Segmentierungsleistung (Onsets/Offsets).

---

## 2. Framewise Metriken nach Sliding Window (Smoothed)

Identische Metrik-Definition, aber auf den geglätteten Vorhersagen nach dem Sliding-Window-Algorithmus.

| Bird | FW F1 (Smoothed) |
|---|---|
| ye00pu07 | 0.958 ± 0.000 |
| bu04bk04 | 0.942 ± 0.006 |
| gy07bu07 | 0.933 ± 0.001 |
| br08pk08 | 0.952 ± 0.001 |
| ye04gr05 | 0.898 ± 0.009 |

---

## 3. Collar F1 (Segment-Level) — Ohne Sliding Window (Raw)

Ein erkanntes Segment gilt als True Positive wenn Onset **und** Offset innerhalb des Collar-Fensters liegen.

| Bird | @5ms | @10ms | @15ms | @20ms |
|---|---|---|---|---|
| ye00pu07 | 0.794 ± 0.003 | 0.863 ± 0.004 | 0.870 ± 0.003 | 0.870 ± 0.003 |
| bu04bk04 | 0.724 ± 0.059 | 0.812 ± 0.027 | 0.841 ± 0.016 | 0.865 ± 0.020 |
| gy07bu07 | 0.818 ± 0.003 | 0.892 ± 0.003 | 0.897 ± 0.002 | 0.924 ± 0.001 |
| br08pk08 | 0.833 ± 0.017 | 0.882 ± 0.012 | 0.892 ± 0.012 | 0.893 ± 0.013 |
| ye04gr05 | 0.445 ± 0.084 | 0.689 ± 0.068 | 0.753 ± 0.051 | 0.776 ± 0.047 |

---

## 4. Collar F1 (Segment-Level) — Mit Sliding Window (Smoothed)

Gleiche Definition wie oben, aber auf den geglätteten Vorhersagen (= reale Betriebsbedingung).

| Bird | @5ms | @10ms | @15ms | @20ms |
|---|---|---|---|---|
| ye00pu07 | 0.959 ± 0.001 | **0.972 ± 0.001** | 0.972 ± 0.001 | 0.972 ± 0.001 |
| bu04bk04 | 0.851 ± 0.016 | **0.890 ± 0.003** | 0.897 ± 0.005 | 0.929 ± 0.010 |
| gy07bu07 | 0.702 ± 0.012 | **0.730 ± 0.009** | 0.732 ± 0.009 | 0.735 ± 0.010 |
| br08pk08 | 0.957 ± 0.009 | **0.974 ± 0.008** | 0.976 ± 0.007 | 0.977 ± 0.007 |
| ye04gr05 | 0.673 ± 0.024 | **0.904 ± 0.002** | 0.926 ± 0.005 | 0.935 ± 0.004 |

> **Hinweis gy07bu07:** Das Smoothing *verschlechtert* hier die Metriken (raw @10ms = 0.892, smoothed = 0.730) wegen eines Parametermismatch zwischen dem optimierten Threshold (0.95) und dem global festkodierten Sliding-Window (benötigt 3/5 Frames = 1). Siehe REPORT.md Abschnitt 6.1.

---

## 5. Onset-Spezifischer Collar F1 — Mit Sliding Window

Ein Segment gilt als TP wenn der **Onset** des erkannten Segments innerhalb ±collar ms liegt (Offset wird ignoriert). Entspricht dem Kriterium für Closed-Loop-Targeting.

| Bird | Onset @10ms (SW) | Onset @20ms (SW) |
|---|---|---|
| ye00pu07 | **0.986 ± 0.000** | — |
| bu04bk04 | **0.949 ± 0.003** | — |
| gy07bu07 | **0.817 ± 0.008** | — |
| br08pk08 | **0.979 ± 0.005** | — |
| ye04gr05 | **0.955 ± 0.002** | — |

Range @10ms: **0.817 – 0.986** (gy07bu07 ist Ausreißer wegen Smoothing-Bug)

---

## 6. Offset-Spezifischer Collar F1 — Mit Sliding Window

| Bird | Offset @10ms (SW) |
|---|---|
| ye00pu07 | 0.986 ± 0.001 |
| bu04bk04 | 0.950 ± 0.003 |
| gy07bu07 | 0.817 ± 0.007 |
| br08pk08 | 0.979 ± 0.005 |
| ye04gr05 | 0.946 ± 0.006 |

---

## 7. Validierter Threshold (aus Val-Set-Tuning)

| Bird | Tuned Threshold |
|---|---|
| ye00pu07 | 0.65 |
| bu04bk04 | 0.80–0.85 |
| gy07bu07 | 0.95 |
| br08pk08 | 0.70–0.75 |
| ye04gr05 | 0.90–0.95 |

---

## 8. Trainings-Epochen (neue Experimente)

Aus den `results.json`-Dateien (`history.train_loss` Länge, d.h. tatsächlich trainierte Epochen):  
Muss aus den Backup-JSONs abgelesen / aggregiert werden. Typischer Bereich: **9–28 Epochen** (je nach Seed/Bird).

---

## 9. Datensatz-Statistiken

| Bird | #Syllables (test) | Duration total (s) | #Syllables train (ca.) |
|---|---|---|---|
| ye00pu07 | 3947 | 2025 | sehr groß |
| bu04bk04 | 745 | 256 | 3934 |
| gy07bu07 | 1542 | 388 | — |
| br08pk08 | 1632 | 556 | — |
| ye04gr05 | 694 | 260 | — |

---

## 10. Energy-Baseline (Vergleich)

| Bird | FW F1 | Collar@10ms (SW) | Onset@10ms (SW) |
|---|---|---|---|
| ye00pu07 | 0.955 ± 0.007 | 0.836 ± 0.014 | 0.870 ± 0.030 |
| bu04bk04 | 0.934 ± 0.002 | 0.773 ± 0.017 | 0.884 ± 0.008 |
| gy07bu07 | 0.931 ± 0.011 | 0.874 ± 0.006 | 0.903 ± 0.012 |
| br08pk08 | 0.933 ± 0.005 | 0.870 ± 0.003 | 0.921 ± 0.009 |
| ye04gr05 | 0.958 ± 0.003 | 0.689 ± 0.009 | 0.880 ± 0.006 |

**Moove vs Baseline (Collar@10ms smoothed):**  
Moove besser bei 4/5 Birds (+0.10 bis +0.21). Ausnahme: gy07bu07 wegen Smoothing-Bug.
