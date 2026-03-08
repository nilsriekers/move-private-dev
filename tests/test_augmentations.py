import numpy as np
import pytest
from moove.utils.training_utils import (
    augment_spectrogram,
    add_noise_to_spectrogram,
    frequency_mask,
    time_mask,
    dynamic_range_compression,
)


@pytest.fixture
def sample_spectrogram():
    np.random.seed(0)
    return np.random.rand(64, 32).astype(np.float32)


class TestAddNoise:
    def test_shape_preserved(self, sample_spectrogram):
        result = add_noise_to_spectrogram(sample_spectrogram)
        assert result.shape == sample_spectrogram.shape

    def test_noise_is_small(self, sample_spectrogram):
        result = add_noise_to_spectrogram(sample_spectrogram, noise_level=0.0001)
        diff = np.abs(result - sample_spectrogram)
        assert diff.max() < 0.01


class TestFrequencyMask:
    def test_shape_preserved(self, sample_spectrogram):
        result = frequency_mask(sample_spectrogram)
        assert result.shape == sample_spectrogram.shape

    def test_does_not_modify_input(self, sample_spectrogram):
        original = sample_spectrogram.copy()
        frequency_mask(sample_spectrogram)
        np.testing.assert_array_equal(sample_spectrogram, original)

    def test_some_values_changed(self, sample_spectrogram):
        np.random.seed(1)
        result = frequency_mask(sample_spectrogram, F=20)
        assert not np.array_equal(result, sample_spectrogram)


class TestTimeMask:
    def test_shape_preserved(self, sample_spectrogram):
        result = time_mask(sample_spectrogram)
        assert result.shape == sample_spectrogram.shape

    def test_does_not_modify_input(self, sample_spectrogram):
        original = sample_spectrogram.copy()
        time_mask(sample_spectrogram)
        np.testing.assert_array_equal(sample_spectrogram, original)

    def test_some_values_changed(self, sample_spectrogram):
        np.random.seed(1)
        result = time_mask(sample_spectrogram, T=20)
        assert not np.array_equal(result, sample_spectrogram)


class TestDynamicRangeCompression:
    def test_shape_preserved(self, sample_spectrogram):
        result = dynamic_range_compression(sample_spectrogram)
        assert result.shape == sample_spectrogram.shape

    def test_no_nans(self, sample_spectrogram):
        result = dynamic_range_compression(sample_spectrogram)
        assert not np.any(np.isnan(result))


class TestAugmentSpectrogram:
    def test_shape_preserved(self, sample_spectrogram):
        result = augment_spectrogram(sample_spectrogram)
        assert result.shape == sample_spectrogram.shape

    def test_sometimes_unchanged(self):
        """With 80% probability the spectrogram should be returned unchanged."""
        spec = np.ones((32, 16), dtype=np.float32)
        np.random.seed(0)
        unchanged_count = sum(
            np.array_equal(augment_spectrogram(spec.copy()), spec)
            for _ in range(100)
        )
        assert unchanged_count > 50, "Augmentation should leave most samples unchanged"
