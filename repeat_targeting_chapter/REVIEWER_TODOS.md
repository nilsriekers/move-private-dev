# Reviewer Requirements: Repeat Targeting (Fig. 7)

## Reviewer comment (verbatim)

> "For Fig. 7, where the authors target the 4th syllable in a repeat phrase, it is unclear
> how reliably they were able to do this. Some accuracy measures along with false positive
> and false negative proportions would be useful."

## What needs to be added to the paper

1. **Targeting accuracy for the repeat targeting demo** (Fig. 7 bird):
   - True positive rate (= hits / total target positions presented)
   - False positive rate (= spurious triggers / total bouts or per phrase)
   - False negative rate (= missed triggers / total target positions)
   - Report these over the full recording session shown in Fig. 7 (not just the example bout)

2. **Clarify which repeat position was targeted** — caption says "fourth syllable" but
   text says "fifth repetition (a5)". Needs to be consistent. The trigger happens on a4
   so that playback covers a5 → caption should say "targeting the fourth occurrence (a4)
   to deliver feedback overlapping a5".

## Implementation plan

### Step 1 — identify raw data
- Find the raw log file or trigger log from the Fig. 7 recording session
- The log should contain: per-bout trigger events, detected syllable sequences, timestamps
- Typical location: experiment folder for the repeat-targeting bird (bird 3 = br08pk08?)

### Step 2 — compute metrics
Create `repeat_targeting_chapter/compute_repeat_targeting_accuracy.py`:

```
For each bout in the session:
  - count number of repeat phrases containing ≥ 4 'a' syllables  → N_target_phrases
  - count triggered events on position a4                         → N_TP
  - count bouts where trigger fired but repeat phrase had < 4 'a' → N_FP
  - count phrases with ≥ 4 'a' but no trigger                   → N_FN

TP rate = N_TP / N_target_phrases
FP rate = N_FP / N_total_bouts  (or per phrase)
FN rate = N_FN / N_target_phrases
```

### Step 3 — update paper text

Add 1–2 sentences to the repeat targeting paragraph, e.g.:

> "Across the full session (N = XX bouts), Moove triggered on XX% of target phrases
> (false negative rate: XX%), with XX false positives (XX% of bouts)."

### Step 4 — fix caption inconsistency
Fix "fourth syllable" vs "a4/a5" wording in Fig. 7 caption and main text so they agree.

## Open questions

- Where is the raw log / trigger data for the Fig. 7 session?
- Is this bird br08pk08 or a different bird?
- Was a formal accuracy session run, or only the example bout exists?
