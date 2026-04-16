# Moove Raw Training Data — Documentation

## ZIP Files

| File | Bird ID | Size |
|------|---------|------|
| `bird_1.zip` | ye00pu07 | 164 MB |
| `bird_2.zip` | bu04bk04 | 108 MB |
| `bird_3.zip` | gy07bu07 | 177 MB |
| `bird_4.zip` | br08pk08 | 224 MB |
| `bird_5.zip` | ye04gr05 | 127 MB |

Each ZIP contains only `.wav`, `.rec`, `.wav.not.mat`, and `batch*.txt` files.
Internal structure: `bird_N/<YYMMDD>/<files>`.

---

## Bird 1 — ye00pu07

| Property | Value |
|----------|-------|
| Source dir | `~/.moove/rec_data/ye00pu07_letters/baseline/` |
| Recording days | 240424, 240425, 240430, 240501, 240502 |
| WAV/label files | 579 bouts |
| Seg PKL | `bird1_new_seg_ds_seg.pkl` |
| Class PKL | `bird1_new_class_ds_class.pkl` |
| Overlap chunks | — |

| Day | WAVs |
|-----|------|
| 240424 | 91 |
| 240425 | 211 |
| 240430 | 65 |
| 240501 | 166 |
| 240502 | 46 |

---

## Bird 2 — bu04bk04

| Property | Value |
|----------|-------|
| Source dir | `~/.moove/rec_data/bu04bk04/screening_cleaned/` |
| Recording days | 250707–250711 |
| WAV/label files | 176 bouts |
| Seg PKL | `bu04bk04_sc_1812_seg.pkl` |
| Class PKL | `bu04bk04_sc_1812_merged_class.pkl` |
| Overlap chunks | — |

| Day | WAVs |
|-----|------|
| 250707 | 14 |
| 250708 | 27 |
| 250709 | 54 |
| 250710 | 32 |
| 250711 | 49 |

---

## Bird 3 — gy07bu07

| Property | Value |
|----------|-------|
| Source dir | `~/.moove/rec_data/gy07bu07/exp2/` |
| Recording days | 250526, 250527 |
| WAV/label files | 113 bouts |
| Seg PKL | `gy07bu07_nooverlapchunks_seg_seg.pkl` |
| Class PKL | `gy07bu07_1812_no_mnx_class.pkl` (m/n/x dropped) |
| Overlap chunks | **False** (explicit, no overlap chunks) |

| Day | WAVs | Notes |
|-----|------|-------|
| 250526 | 14 | +1 orphaned .not.mat (no WAV, all 'x'-labeled, ignored) |
| 250527 | 99 | |

**Note on class PKL:** m and n syllables are legitimate motif variants but were excluded from training.
Old PKL `gy07bu07_1812_merged_class.pkl` (8 classes) is superseded by `gy07bu07_1812_no_mnx_class.pkl` (11 classes a–k).

---

## Bird 4 — br08pk08

| Property | Value |
|----------|-------|
| Source dir | `~/.moove/rec_data/br08pk08/exp1/` |
| Recording days | 250707–250711 |
| WAV/label files | 199 bouts |
| Seg PKL | `br08pk08_1812_seg.pkl` |
| Class PKL | `br08pk08_1812_merged_class.pkl` |
| Overlap chunks | — |

| Day | WAVs |
|-----|------|
| 250707 | 4 |
| 250708 | 20 |
| 250709 | 65 |
| 250710 | 52 |
| 250711 | 58 |

---

## Bird 5 — ye04gr05

| Property | Value |
|----------|-------|
| Source dir | `~/.moove/rec_data/ye04gr05/more_data/` |
| Recording days | 250726, 250727, 250728 |
| WAV/label files | 108 bouts |
| Seg PKL | `ye04gr05_1812_seg.pkl` |
| Class PKL | `ye04gr05_1812_merged_class.pkl` |
| Overlap chunks | — |

| Day | WAVs |
|-----|------|
| 250726 | 40 |
| 250727 | 18 |
| 250728 | 50 |

**Note:** 'j' syllable (19 instances, day 250726 only, context `...aaajhf...`) is present in the raw data
but was not verified as included/excluded in the final class PKL.

---

## Open Items (not reflected in these ZIPs)

- **ye04gr05 new data:** `new_ye04gr05/exp/` has a 4th day (250729, 23 bouts) not in this ZIP — original training data only.
- **bu04bk04 paired data:** `new_bu04bk04/exp/` (paired recordings) was deleted; original solo data from `screening_cleaned/` used here.
- **`final_experiments/gcloud_run.sh` bug:** still references old `gy07bu07_1812_merged_class.pkl` — needs fix before next run.
