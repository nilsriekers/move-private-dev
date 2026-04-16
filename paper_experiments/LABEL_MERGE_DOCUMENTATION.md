# Label Merge Documentation — paper_experiments

## Overview

For each bird, the raw classification PKL contains all k-means cluster labels.
Some labels were merged (reassigned to another label) or dropped (rows removed)
before training. This file documents all merges applied.

**Rule:** Never delete original PKL files. Merges are applied by creating new PKL files.

---

## Bird 1 — ye00pu07

**Raw PKL:** `bird1_new_class_ds_class.pkl`
**Merged PKL:** same (no merge in PKL)
**Classes (9):** a b c d e f g h l
**Merges applied:** none in PKL
**Note:** For the learning experiment (Figure 7 / bird 1), syllables 'c' and 'h'
were merged in the targeting rule (not in the training data). This is handled
at the MooveTAF level, not in the PKL.

---

## Bird 2 — bu04bk04

**Raw PKL:** `bu04bk04_sc_1812_class.pkl` — 11 classes: a b c d f g h i j k m
**Merged PKL:** `bu04bk04_sc_1812_merged_class.pkl` — 10 classes: a c d f g h i j k m
**Classes (10):** a c d f g h i j k m

**Merges applied:**
| From | To | n instances | Reason |
|------|----|-------------|--------|
| 'b'  | 'i' | 1228 | Acoustically similar / same cluster region |

**Status:** Merged PKL already exists and correct. Training results match (10 classes). ✓

---

## Bird 3 — gy07bu07

**Raw PKL:** `gy07bu07_1812_class.pkl` — 14 classes: a b c d e f g h i j k m n x

**Label counts in raw PKL:**
| Label | n    | % of total |
|-------|------|-----------|
| a     | 2948 | 27.1%     |
| b     | 1865 | 17.1%     |
| c     |  696 |  6.4%     |
| d     |  632 |  5.8%     |
| e     | 1433 | 13.2%     |
| f     |  426 |  3.9%     |
| g     |  555 |  5.1%     |
| h     |  188 |  1.7%     |
| i     |  344 |  3.2%     |
| j     |  686 |  6.3%     |
| k     |  459 |  4.2%     |
| m     |   21 |  0.2%     |
| n     |  193 |  1.8%     |
| x     |  438 |  4.0%     |
| TOTAL |10884 |           |

**EXISTING (inconsistent) merged PKL:** `gy07bu07_1812_merged_class.pkl` — 8 classes: b c d e f g i j
(This PKL additionally dropped a, h, k — reason unclear. NOT used for paper training.)

**PKL actually used for paper training:** `gy07bu07_nooverlapchunks_clas_class.pkl`
— 11 classes: a b c d e f g h i j k (n=1428, m/n/x removed)
— MISMATCH with config.py (which pointed to 8-class merged PKL)

**TARGET merge (to fix inconsistency):**
New PKL: `gy07bu07_1812_no_mnx_class.pkl` — 11 classes: a b c d e f g h i j k
| Action | Labels | Reason |
|--------|--------|--------|
| DROP rows | m (21), n (193), x (438) | Very rare / spurious clusters |

**Status:** ⚠ NEW PKL TO BE CREATED — config.py to be updated — retraining needed

---

## Bird 4 — br08pk08

**Raw PKL:** `br08pk08_1812_class.pkl` — 12 classes: a b c d e f g i j k l m
**Merged PKL:** `br08pk08_1812_merged_class.pkl` — 8 classes: a b c d e f g j
**Classes (8):** a b c d e f g j

**Merges applied:**
| From | To   | n instances | Reason |
|------|------|-------------|--------|
| 'i'  | 'a'  | 1025        | Acoustically similar |
| 'k'  | 'a'  | 1078        | Acoustically similar |
| 'l'  | 'e'  |  226        | Acoustically similar |
| 'm'  | 'b'  |  166        | Acoustically similar |

**Status:** Merged PKL already exists and correct. Training results match (8 classes). ✓

---

## Bird 5 — ye04gr05

**Raw PKL:** `ye04gr05_1812_class.pkl` — 10 classes: a b c d e f g h i j
**Merged PKL:** `ye04gr05_1812_merged_class.pkl` — 8 classes: a b c d e f g h
**Classes (8):** a b c d e f g h

**Merges applied:**
| From | To  | n instances | Reason |
|------|-----|-------------|--------|
| 'i'  | 'b' |  230        | Acoustically similar |
| 'j'  | 'b' |  527        | Acoustically similar |

**Status:** Merged PKL already exists and correct. Training results match (8 classes). ✓

---

## Summary of Actions Required

| Bird     | PKL status        | Retraining needed |
|----------|-------------------|-------------------|
| ye00pu07 | ✓ OK              | No                |
| bu04bk04 | ✓ OK              | No                |
| gy07bu07 | ⚠ Inconsistency   | Yes — see above   |
| br08pk08 | ✓ OK              | No                |
| ye04gr05 | ✓ OK              | No                |

Only **gy07bu07 classification** needs a new PKL and retraining.
Segmentation is NOT affected (different PKL pipeline).
