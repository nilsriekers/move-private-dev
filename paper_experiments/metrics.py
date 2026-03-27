"""Metrics for paper experiments.

#1  Framewise precision / recall / F1  (binary segmentation)
#3  Collar-based segmentation P / R / F1  (segment-level, multiple tolerances)
"""
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, classification_report


# ── #1  Framewise metrics ────────────────────────────────────────────

def framewise_metrics(y_true, y_pred):
    """Compute framewise precision, recall, F1 for binary segmentation.

    Parameters
    ----------
    y_true, y_pred : array-like of {0, 1}
        Frame-level ground truth and predictions.

    Returns
    -------
    dict with keys: precision, recall, f1, tp, tn, fp, fn, n_total
    """
    yt = np.asarray(y_true)
    yp = np.asarray(y_pred)
    tp = int(np.sum((yt == 1) & (yp == 1)))
    tn = int(np.sum((yt == 0) & (yp == 0)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    fn = int(np.sum((yt == 1) & (yp == 0)))
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0,
    )
    return {
        "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn, "n_total": tp + tn + fp + fn,
    }


# ── #3  Collar-based segmentation metrics ────────────────────────────

def _extract_segments(labels):
    """Return list of (onset_idx, offset_idx) from a binary label array."""
    segments = []
    in_seg = False
    onset = 0
    for i, v in enumerate(labels):
        if v == 1 and not in_seg:
            onset = i
            in_seg = True
        elif v == 0 and in_seg:
            segments.append((onset, i))
            in_seg = False
    if in_seg:
        segments.append((onset, len(labels)))
    return segments


def collar_segmentation_metrics(y_true, y_pred, collar_frames):
    """Segment-level P / R / F1 with collar tolerance.

    A predicted segment counts as a true-positive if **both** its onset and
    offset are within *collar_frames* of a ground-truth segment (greedy
    matching, each true segment used at most once).

    Parameters
    ----------
    y_true, y_pred : array-like of {0, 1}
        Frame-level ground truth and predictions (for one file).
    collar_frames : int
        Tolerance in number of frames.

    Returns
    -------
    dict with keys: precision, recall, f1, n_true, n_pred, tp
    """
    true_segs = _extract_segments(np.asarray(y_true))
    pred_segs = _extract_segments(np.asarray(y_pred))

    if not pred_segs and not true_segs:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0,
                "n_true": 0, "n_pred": 0, "tp": 0}
    if not pred_segs:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0,
                "n_true": len(true_segs), "n_pred": 0, "tp": 0}
    if not true_segs:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0,
                "n_true": 0, "n_pred": len(pred_segs), "tp": 0}

    matched_true = set()
    tp = 0
    for p_on, p_off in pred_segs:
        for j, (t_on, t_off) in enumerate(true_segs):
            if j in matched_true:
                continue
            if abs(p_on - t_on) <= collar_frames and abs(p_off - t_off) <= collar_frames:
                tp += 1
                matched_true.add(j)
                break

    precision = tp / len(pred_segs)
    recall = tp / len(true_segs)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {"precision": float(precision), "recall": float(recall), "f1": float(f1),
            "n_true": len(true_segs), "n_pred": len(pred_segs), "tp": tp}


def collar_ms_to_frames(collar_ms, chunk_size, sample_rate):
    """Convert a collar in milliseconds to number of frames (chunks)."""
    frame_duration_ms = (chunk_size / sample_rate) * 1000
    return max(1, int(round(collar_ms / frame_duration_ms)))


# ── Sliding window post-processing (matches real-time inference) ─────

def apply_sliding_window(y_pred, onset_window_size=5, n_onset_true=3,
                         offset_window_size=5, n_offset_false=4):
    """Apply the MooveTAF sliding window to raw binary chunk predictions.

    Mirrors the logic in ``segment_utils.segment_ml`` / the real-time
    ``stream_callback``: an onset is detected when *n_onset_true* of the
    last *onset_window_size* chunks are 1; an offset when *n_offset_false*
    of the last *offset_window_size* chunks are 0.

    Returns
    -------
    smoothed : list[int]
        Same length as *y_pred*, 1 inside detected segments, 0 outside.
    n_segments : int
        Number of detected syllable segments.
    """
    preds = list(y_pred)
    onset_flag = False
    onset_idxs, offset_idxs = [], []

    for i in range(len(preds)):
        sub_on = preds[max(0, i - onset_window_size + 1):i + 1]
        sub_off = preds[max(0, i - offset_window_size + 1):i + 1]

        if not onset_flag and sub_on.count(1) >= n_onset_true:
            # find first 1 in the window (onset position)
            rev = sub_on[::-1]
            if 0 in rev:
                onset_pos = i - rev.index(0)
            else:
                onset_pos = i - len(sub_on) + 1
            onset_idxs.append(onset_pos)
            onset_flag = True
        elif onset_flag and sub_off.count(0) >= n_offset_false:
            rev = sub_off[::-1]
            if 1 in rev:
                offset_pos = i - rev.index(1)
            else:
                offset_pos = i
            offset_idxs.append(offset_pos)
            onset_flag = False

    # balance onset/offset counts
    if len(onset_idxs) == len(offset_idxs) + 1:
        onset_idxs.pop()

    smoothed = [0] * len(preds)
    for on, off in zip(onset_idxs, offset_idxs):
        for j in range(on, min(off + 1, len(preds))):
            smoothed[j] = 1

    return smoothed, len(onset_idxs)


# ── Combined pipeline metrics (seg + class) ─────────────────────────

def combined_pipeline_metrics(seg_results, class_results):
    """Compute combined segmentation + classification metrics.

    The MooveGUI pipeline is sequential: segment → classify.  A syllable
    is correctly recognised only if it is (1) correctly detected by the
    segmenter **and** (2) correctly classified.  Under the assumption that
    classification accuracy is independent of small boundary errors:

        P(correct) = P(detected) × P(correct class | detected)

    This holds both at syllable level (collar-based) and framewise.

    Parameters
    ----------
    seg_results : dict
        Results from ``train_segmentation`` for one bird/seed.
    class_results : dict
        Results from ``train_classification`` for the same bird/seed.

    Returns
    -------
    dict with ``syllable_collar``, ``framewise``, ``framewise_smoothed``
    """
    class_acc = class_results["test_accuracy"]
    class_macro_f1 = class_results["classification"]["macro"]["f1"]

    # ── Syllable-level: collar-based combined P / R / F1 ─────────────
    combined_collar = {}
    for src_key, src_label in [("collar", "raw"), ("collar_smoothed", "sw")]:
        collar_data = seg_results.get(src_key, {})
        for collar_tag, cm in collar_data.items():
            seg_p = cm["precision"]
            seg_r = cm["recall"]
            comb_p = seg_p * class_acc
            comb_r = seg_r * class_acc
            comb_f1 = (2 * comb_p * comb_r / (comb_p + comb_r)
                       if (comb_p + comb_r) > 0 else 0.0)
            tag = f"{collar_tag}_{src_label}"
            combined_collar[tag] = {
                "precision": float(comb_p),
                "recall": float(comb_r),
                "f1": float(comb_f1),
                "seg_precision": float(seg_p),
                "seg_recall": float(seg_r),
                "class_accuracy": float(class_acc),
            }

    # ── Framewise combined (multi-class approximation) ───────────────
    # Correct frame = silence frame correctly predicted as silence
    #               + syllable frame correctly detected AND correctly classified
    def _framewise_combined(fw):
        tp = fw.get("tp", 0)
        tn = fw.get("tn", 0)
        fp = fw.get("fp", 0)
        fn = fw.get("fn", 0)
        total = tp + tn + fp + fn
        if total == 0:
            return {"accuracy": 0.0, "n_total": 0}
        correct = tn + tp * class_acc
        accuracy = correct / total
        # Weighted precision: of predicted-syllable frames, P(real AND correct class)
        pred_pos = tp + fp
        w_precision = (tp * class_acc / pred_pos) if pred_pos > 0 else 0.0
        # Weighted recall: of true-syllable frames, P(detected AND correct class)
        true_pos = tp + fn
        w_recall = (tp * class_acc / true_pos) if true_pos > 0 else 0.0
        w_f1 = (2 * w_precision * w_recall / (w_precision + w_recall)
                if (w_precision + w_recall) > 0 else 0.0)
        return {
            "accuracy": float(accuracy),
            "precision": float(w_precision),
            "recall": float(w_recall),
            "f1": float(w_f1),
            "class_accuracy": float(class_acc),
            "class_macro_f1": float(class_macro_f1),
            "seg_tp": tp, "seg_tn": tn, "seg_fp": fp, "seg_fn": fn,
            "n_total": total,
        }

    fw_raw = _framewise_combined(seg_results.get("framewise", {}))
    fw_sw = _framewise_combined(seg_results.get("framewise_smoothed", {}))

    return {
        "syllable_collar": combined_collar,
        "framewise": fw_raw,
        "framewise_smoothed": fw_sw,
    }


# ── Classification helpers ───────────────────────────────────────────

def classification_metrics(y_true, y_pred, label_names=None):
    """Per-class and macro P / R / F1 for multi-class classification.

    Returns
    -------
    dict with keys: per_class (dict of label→metrics), macro (dict)
    """
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0,
    )
    mac_p, mac_r, mac_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0,
    )
    labels = label_names or [str(i) for i in range(len(precision))]
    per_class = {}
    for i, lab in enumerate(labels):
        per_class[lab] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
    return {
        "per_class": per_class,
        "macro": {"precision": float(mac_p), "recall": float(mac_r), "f1": float(mac_f1)},
    }
