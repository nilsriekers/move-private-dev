# Data Analysis: Fig. 7 Repeat Targeting Session

## Experiment overview

- **Bird:** gy07bu07
- **Date:** 2025-09-02 (~11:08–16:21, ~5h session)
- **92 recording bouts** (.wav + .rec + .not.mat)

## What the co-author did

### Targeting setup (bout_target_seq_log.txt)

She targeted **variable repeat positions simultaneously**, using regex-style sequences:

| Target string | # 'a' syllables | Occurrences logged |
|---|---|---|
| `[de]aa$` | 2 | 334 |
| `[de]aaaa$` | 4 | 324 |
| `[de]aaaaaa$` | 6 | 331 |
| `[de]aaaaaaaa$` | 8 | 362 |
| `[de]aaaaaaaaaa$` | 10 | 363 |
| `[de]aaaaaaaaaaaa$` | 12 | 359 |
| `[de]aaaaaaaaaaaaaa$` | 14 | 350 |
| (empty / catch) | — | 365 |

→ All even repeat lengths from 2 to 14 were targeted. This was **not** a clean "target position 4" experiment. It is unclear what exactly triggered WN and at what position in the phrase.

### Excel analysis (matrix_blabla.xlsx, created by Jacqueline Göbl)

She manually evaluated only the `[de]aaaa$` cases (4-'a' matches):

- Filtered for **file_type = 'k'** (= bouts where trigger fired)
- For each matching file, manually counted from spectrograms: `right` vs. `wrong` triggers
- Files with file_type `'d'` have no data (#NV) — likely catch trials or discarded

**Result for aaaa$ (k-files only):**

| File | Phrases | Right | Wrong | Accuracy |
|---|---|---|---|---|
| 250902_143043 | 5 | 5 | 0 | 1.00 |
| 250902_120715 | 4 | 4 | 0 | 1.00 |
| 250902_115940 | 2 | 2 | 0 | 1.00 |
| 250902_161219 | 1 | 1 | 0 | 1.00 |
| 250902_132156 | 5 | 4 | 1 | 0.80 |
| 250902_161452 | 4 | 3 | 1 | 0.75 |
| 250902_115531 | 4 | 3 | 1 | 0.75 |
| 250902_124534 | 2 | 1 | 1 | 0.50 |
| 250902_115923 | 2 | 1 | 1 | 0.50 |
| 250902_142805 | 3 | 1 | 2 | 0.33 |
| 250902_131843 | 1 | 0 | 1 | 0.00 |
| 250902_133448 | 3 | 0 | 3 | 0.00 |
| **Total / Average** | **36** | **25** | **11** | **0.636** |

## Problems with this approach

1. **63.6% accuracy is poor** and likely reflects a bad model / misconfigured targeting rather than inherent difficulty of the task.

2. **Variable targeting (2/4/6/.../14 'a's simultaneously):** It's unclear what the bird was actually trained to do. Targeting all even repeat lengths at once is not a clean repeat-position targeting experiment. It is likely that many triggers fired on correct detections of shorter/longer repeat strings, and the manual scoring was done inconsistently.

3. **Manual right/wrong scoring from spectrograms:** No scripted analysis, subjective, only 12/92 files evaluated for aaaa$ specifically.

4. **Only 11/92 files hand-segmented** (batch_segmented.txt), rest were not re-segmented. The .not.mat files in the main 250902 folder are corrected labels, but the `OldNotMat_moved_09Sep2025_0948` archive contains the original online labels — meaning the network used for online targeting may have been different from what the current labels reflect.

5. **File type 'd' rows in Excel have no data** — large number of evaluated files excluded from the accuracy computation without explanation.

## Better approach: offline / theoretical targeting capability

Instead of reporting this messy online accuracy, it makes more sense to demonstrate Moove's **offline theoretical targeting capability**:

- Use the (corrected) .not.mat labels from the 250902 recording session
- Simulate the repeat-targeting logic: for each bout, find all phrases where ≥ 4 'a' syllables occur consecutively after [d/e], and check whether Moove's segmentation + classification would have correctly identified position 4
- This gives a clean TP/FP/FN without depending on the co-author's manual scoring or the online model quality
- Can be done on the full 92-file session, not just the 12 manually scored files

### What to compute
- **N phrases with ≥ 4 'a' syllables** (= target phrases)
- **N correct triggers** = phrase where position 4 detected (TP)
- **N missed triggers** = phrase where position 4 not detected (FN)
- **N spurious triggers** = trigger fired outside a valid repeat phrase of ≥ 4 'a' (FP)
- Report TP rate, FP rate — these reflect segmentation + classification accuracy, not online model quality

### Data needed
- Corrected .not.mat files from `250902/` (labels already fixed)
- A script to parse .not.mat → syllable sequences per bout → count repeats and target positions

## Open questions

- Which network did the co-author use for online targeting? Was it trained on this bird's data?
- Are the corrected .not.mat labels reliable enough for offline analysis?
- Was there a defined playback stimulus for each repeat length, or was the same WN always used?
