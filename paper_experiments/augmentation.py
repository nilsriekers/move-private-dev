"""Augmentation functions extracted from moove.utils.training_utils.

Avoids importing the full moove.utils package (which pulls in PyQt6).
These are identical to the original implementations.
"""
import random

import numpy as np

DEFAULT_AUGMENTATION_PARAMS = {
    "enabled": True,
    "probability": 0.2,
    "noise_level": 0.0001,
    "freq_mask_width": 10,
    "time_mask_width": 10,
    "compression_factor": 0.5,
}


def augment_spectrogram(spec, aug_params=None):
    if aug_params is None:
        aug_params = DEFAULT_AUGMENTATION_PARAMS
    if not aug_params.get("enabled", True):
        return spec
    prob = float(aug_params.get("probability", 0.2))
    if np.random.rand() < prob:
        noise_level = float(aug_params.get("noise_level", 0.0001))
        freq_w = int(aug_params.get("freq_mask_width", 10))
        time_w = int(aug_params.get("time_mask_width", 10))
        comp = float(aug_params.get("compression_factor", 0.5))
        augmentations = [
            lambda s: add_noise_to_spectrogram(s, noise_level=noise_level),
            lambda s: dynamic_range_compression(s, compression_factor=comp),
            lambda s: frequency_mask(s, F=freq_w),
            lambda s: time_mask(s, T=time_w),
        ]
        chosen = random.choice(augmentations)
        spec = chosen(spec)
    return spec


def add_noise_to_spectrogram(spec, noise_level=0.0001):
    return spec + noise_level * np.random.randn(*spec.shape)


def frequency_mask(spec, F=10, num_masks=1, replace_with_zero=False):
    cloned = spec.copy()
    nf = spec.shape[0]
    for _ in range(num_masks):
        f = int(np.random.uniform(1, min(F, nf)))
        f = max(1, min(f, nf - 1))
        ms = nf - f
        if ms <= 0:
            continue
        f0 = np.random.randint(0, ms)
        cloned[f0:f0 + f, :] = 0 if replace_with_zero else cloned.mean()
    return cloned


def time_mask(spec, T=10, num_masks=1, replace_with_zero=False):
    cloned = spec.copy()
    nt = spec.shape[1]
    for _ in range(num_masks):
        t = int(np.random.uniform(1, min(T, nt)))
        t = max(1, min(t, nt - 1))
        ms = nt - t
        if ms <= 0:
            continue
        t0 = np.random.randint(0, ms)
        cloned[:, t0:t0 + t] = 0 if replace_with_zero else cloned.mean()
    return cloned


def dynamic_range_compression(spec, compression_factor=0.5):
    return np.log1p(compression_factor * np.expm1(spec))
