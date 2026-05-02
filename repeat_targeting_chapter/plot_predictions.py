#!/usr/bin/env python3
"""Plot spectrogram with seg + cls predictions for a Fig. 7 bout.

Usage:
    python3 plot_predictions.py 250902_143043
    python3 plot_predictions.py 250902_143043 --start 5 --end 15   # time range in seconds
    python3 plot_predictions.py 250902_143043 --all                 # save all 12 files as PNGs
"""

import sys
import argparse
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import torch
import evfuncs
from scipy.io import wavfile
from scipy.signal import spectrogram as scipy_spectrogram
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from paper_experiments.metrics import apply_sliding_window
from final_experiments.create_dataset import extract_raw_audio, _concat_windows

DATA_DIR = Path(__file__).parent / "data_fig7" / "250902"
SEG_CKPT = REPO_ROOT / "final_experiments/results/gy07bu07/seg/seed_42/gy07bu07_seg_seed42_overlap.pth"
CLS_CKPT = REPO_ROOT / "final_experiments/results/gy07bu07/class/seed_42/gy07bu07_class_seed42.pth"

TARGET_FILES = [
    "250902_161452", "250902_161219", "250902_143043", "250902_142805",
    "250902_133448", "250902_132156", "250902_131843", "250902_124534",
    "250902_120715", "250902_115940", "250902_115923", "250902_115531",
]

CHUNK_SIZE = 64
SAMPLE_RATE = 44100
MS_PER_FRAME = CHUNK_SIZE / SAMPLE_RATE * 1000
SW_PARAMS = {"onset_window_size": 5, "n_onset_true": 3, "offset_window_size": 5, "n_offset_false": 4}

# Color per syllable label
LABEL_COLORS = {
    'a': '#e41a1c', 'b': '#377eb8', 'c': '#4daf4a', 'd': '#984ea3',
    'e': '#ff7f00', 'f': '#a65628', 'g': '#f781bf', 'h': '#999999',
    'i': '#66c2a5', 'j': '#fc8d62', 'k': '#8da0cb',
    'n': '#b3b3b3', 'w': '#ffffb3',
}
DEFAULT_COLOR = '#cccccc'


def load_models():
    seg_ckpt = torch.load(SEG_CKPT, map_location="cpu", weights_only=False)
    cls_ckpt = torch.load(CLS_CKPT, map_location="cpu", weights_only=False)
    return (seg_ckpt["model"].eval(), seg_ckpt["metadata"],
            cls_ckpt["model"].eval(), cls_ckpt["metadata"])


def run_cls(audio, onset_ms, cls_model, cls_meta):
    input_len, chunk_ = [int(x) for x in cls_meta["input_length"].split(",")]
    onset_idx = int(onset_ms * SAMPLE_RATE / 1000)
    clip = audio[onset_idx: onset_idx + input_len * chunk_]
    if len(clip) < input_len * chunk_:
        clip = np.pad(clip, (0, input_len * chunk_ - len(clip)))
    f, t, Sxx = scipy_spectrogram(clip.astype(np.float32), fs=SAMPLE_RATE,
        nperseg=cls_meta["nperseg"], noverlap=cls_meta["noverlap"], nfft=cls_meta["nfft"])
    Sxx = Sxx[(f >= cls_meta["lowcut"]) & (f <= cls_meta["highcut"]), :]
    X = torch.tensor(Sxx, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    s = Sxx.std()
    if s != 0:
        X = (X - Sxx.mean()) / s
    with torch.no_grad():
        return cls_meta["int_to_label"][int(torch.argmax(cls_model(X), dim=1).item())]


def segs_from_labels(labels):
    segs, ins, on = [], False, 0
    for i, v in enumerate(labels):
        if v == 1 and not ins: on, ins = i, True
        elif v == 0 and ins: segs.append((on, i)); ins = False
    if ins: segs.append((on, len(labels)))
    return segs


def run_inference(fid, seg_model, seg_meta, cls_model, cls_meta):
    """Returns (audio, rate, nm, pred_segs_ms, pred_labels, true_segs_ms, true_labels)."""
    wav_path = list(DATA_DIR.glob(f"gy07bu07_{fid}*.wav"))[0]
    rate, audio = wavfile.read(str(wav_path))
    audio = audio.astype(np.float32)
    nm = evfuncs.load_notmat(str(wav_path) + ".not.mat")

    hist_size = seg_meta["hist_size"]
    mean_val = seg_meta["mean"]
    std_val = seg_meta["std"]
    threshold = seg_meta["tuned_threshold"]
    n_frames = len(audio) // CHUNK_SIZE

    chunks = np.asarray(extract_raw_audio(audio, CHUNK_SIZE), dtype=np.float32).T
    n_chunks = chunks.shape[0]
    file_features = np.hstack([np.zeros((n_chunks, 1), dtype=np.float32),
                                chunks,
                                np.zeros((n_chunks, 1), dtype=np.float32)])
    windowed = _concat_windows(file_features, hist_size, 1)
    feats = windowed[:, 1:-1].astype(np.float32)
    X = ((torch.tensor(feats) - mean_val) / std_val).nan_to_num(0.0)
    with torch.no_grad():
        probs = torch.sigmoid(seg_model(X)).cpu().numpy().flatten()
    y_bin = (probs >= threshold).astype(int).tolist()
    y_sm, _ = apply_sliding_window(y_bin, **SW_PARAMS)
    frame_indices = [i + hist_size - 1 for i in range(len(y_sm))]

    full_y_sm = np.zeros(n_frames, dtype=int)
    for i, fi in enumerate(frame_indices):
        if fi < n_frames:
            full_y_sm[fi] = y_sm[i]

    pred_segs = segs_from_labels(full_y_sm)

    # Classify each predicted segment
    pred_segs_ms = []
    pred_labels = []
    for p_on, p_off in pred_segs:
        onset_ms = p_on * MS_PER_FRAME
        offset_ms = p_off * MS_PER_FRAME
        lbl = run_cls(audio, onset_ms, cls_model, cls_meta)
        pred_segs_ms.append((onset_ms / 1000, offset_ms / 1000))  # in seconds
        pred_labels.append(lbl)

    # True segments from .not.mat
    onsets_s = np.array(nm["onsets"], dtype=np.float32) / 1000
    offsets_s = np.array(nm["offsets"], dtype=np.float32) / 1000
    true_labels = list(nm["labels"])[:len(onsets_s)]
    true_segs_ms = list(zip(onsets_s, offsets_s))

    return audio, rate, pred_segs_ms, pred_labels, true_segs_ms, true_labels


def make_spectrogram(audio, t_start, t_end, rate=44100):
    i0 = int(t_start * rate)
    i1 = int(t_end * rate)
    clip = audio[i0:i1]
    f, t, Sxx = scipy_spectrogram(clip, fs=rate, nperseg=512, noverlap=384, nfft=1024)
    t = t + t_start
    return f, t, 10 * np.log10(Sxx + 1e-10)


def plot_bout(fid, seg_model, seg_meta, cls_model, cls_meta,
              t_start=None, t_end=None, save_path=None):
    print(f"Running inference: {fid} ...", end=" ", flush=True)
    audio, rate, pred_segs, pred_labels, true_segs, true_labels = \
        run_inference(fid, seg_model, seg_meta, cls_model, cls_meta)
    print("done")

    duration = len(audio) / rate
    if t_start is None: t_start = 0.0
    if t_end is None: t_end = duration
    t_start = max(0.0, t_start)
    t_end = min(duration, t_end)

    f, t, Sxx_db = make_spectrogram(audio, t_start, t_end, rate)

    fig, axes = plt.subplots(3, 1, figsize=(max(12, (t_end - t_start) * 2), 7),
                             gridspec_kw={"height_ratios": [6, 1, 1]})
    fig.suptitle(f"{fid}  [{t_start:.1f}s – {t_end:.1f}s]", fontsize=11)

    # ── Spectrogram ──────────────────────────────────────────────────────
    ax = axes[0]
    freq_mask = f <= 10000
    vmin = np.percentile(Sxx_db[freq_mask], 20)
    vmax = np.percentile(Sxx_db[freq_mask], 99.5)
    ax.pcolormesh(t, f[freq_mask], Sxx_db[freq_mask], cmap="inferno",
                  vmin=vmin, vmax=vmax, shading="auto", rasterized=True)
    ax.set_ylabel("Freq (Hz)")
    ax.set_xlim(t_start, t_end)
    ax.set_ylim(0, 10000)
    ax.tick_params(labelbottom=False)

    # ── True labels row ──────────────────────────────────────────────────
    ax_true = axes[1]
    ax_true.set_xlim(t_start, t_end)
    ax_true.set_ylim(0, 1)
    ax_true.set_yticks([])
    ax_true.set_ylabel("True", fontsize=8, rotation=0, labelpad=28)
    ax_true.tick_params(labelbottom=False)
    for (on, off), lbl in zip(true_segs, true_labels):
        if off < t_start or on > t_end:
            continue
        color = LABEL_COLORS.get(lbl, DEFAULT_COLOR)
        ax_true.axvspan(on, off, color=color, alpha=0.85)
        mid = (on + off) / 2
        if t_start <= mid <= t_end:
            ax_true.text(mid, 0.5, lbl, ha='center', va='center',
                         fontsize=7, fontweight='bold', color='white')

    # ── Predicted labels row ─────────────────────────────────────────────
    ax_pred = axes[2]
    ax_pred.set_xlim(t_start, t_end)
    ax_pred.set_ylim(0, 1)
    ax_pred.set_yticks([])
    ax_pred.set_ylabel("Pred", fontsize=8, rotation=0, labelpad=28)
    ax_pred.set_xlabel("Time (s)")
    for (on, off), lbl in zip(pred_segs, pred_labels):
        if off < t_start or on > t_end:
            continue
        color = LABEL_COLORS.get(lbl, DEFAULT_COLOR)
        ax_pred.axvspan(on, off, color=color, alpha=0.85)
        mid = (on + off) / 2
        if t_start <= mid <= t_end:
            ax_pred.text(mid, 0.5, lbl, ha='center', va='center',
                         fontsize=7, fontweight='bold', color='white')

    # Legend
    present = sorted(set(true_labels + pred_labels))
    patches = [mpatches.Patch(color=LABEL_COLORS.get(l, DEFAULT_COLOR), label=l)
               for l in present]
    fig.legend(handles=patches, loc='upper right', ncol=len(present),
               fontsize=7, framealpha=0.7)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
        plt.close(fig)
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_id", nargs="?", help="e.g. 250902_143043 (without bird prefix)")
    parser.add_argument("--start", type=float, default=None, help="Start time in seconds")
    parser.add_argument("--end",   type=float, default=None, help="End time in seconds")
    parser.add_argument("--all",   action="store_true", help="Save all 12 files as PNGs")
    args = parser.parse_args()

    seg_model, seg_meta, cls_model, cls_meta = load_models()

    if args.all:
        out_dir = Path(__file__).parent / "plots"
        out_dir.mkdir(exist_ok=True)
        for fid in TARGET_FILES:
            plot_bout(fid, seg_model, seg_meta, cls_model, cls_meta,
                      save_path=out_dir / f"{fid}.png")
    else:
        if not args.file_id:
            print("Available files:")
            for f in TARGET_FILES:
                print(f"  {f}")
            sys.exit(1)
        fid = args.file_id
        if not fid.startswith("250902_"):
            fid = f"250902_{fid}"
        plot_bout(fid, seg_model, seg_meta, cls_model, cls_meta,
                  t_start=args.start, t_end=args.end)


if __name__ == "__main__":
    main()
