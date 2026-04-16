# Figure 5 — Fehlende Eingabedaten

Dieser Ordner ist für Dateien die manuell bereitgestellt werden müssen.

## Panel D — Accuracy vs. Input Duration (Bird 1, ye00pu07)

**Datei:** `accuracy_vs_duration.csv`

**Format:**
```
duration_ms,accuracy
5.8,0.8639
11.6,0.91
...
30.0,0.9589
```

**Quelle:** Sweep-Experiment: Bird 1 Classification-Modell mit verschiedenen Input-Window-Größen (5–50 ms) evaluieren.
Alter Wert (ohne c/h-Merge): 5.8 ms → 86.39%, 30 ms → 95.89%

---

## Panel E — UMAP 30 ms (Bird 1, ye00pu07)

**Datei:** `umap_30ms.csv`

**Format:**
```
x,y,label
-3.2,1.4,a
4.1,-2.3,b
...
```

**Quelle:** MooveGUI → UMAP mit 30 ms Input-Window für Bird 1 → Koordinaten + Labels exportieren.

---

## Panel F — UMAP full syllable (Bird 1, ye00pu07)

**Datei:** `umap_full.csv`

**Format:** identisch zu umap_30ms.csv

**Quelle:** MooveGUI → UMAP mit full-length normalisierten Spektrogrammen für Bird 1.

---

## Status

| Panel | Datei | Status |
|-------|-------|--------|
| D | accuracy_vs_duration.csv | ❌ fehlt |
| E | umap_30ms.csv | ❌ fehlt |
| F | umap_full.csv | ❌ fehlt |
