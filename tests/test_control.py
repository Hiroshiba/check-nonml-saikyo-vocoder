"""Behavioral edit tests, including unvoiced gaps and independent gain scaling."""

from dataclasses import dataclass, replace
import unittest

import numpy as np

from vocoderbench.control import edit_parameters, make_synthetic_parameters


@dataclass
class Parameters:
    f0: np.ndarray
    time: np.ndarray
    spectral_envelope: np.ndarray
    aperiodicity: np.ndarray
    sample_rate: int
    frame_period: float
    n_samples: int


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.params = make_synthetic_parameters(Parameters, duration_s=0.3)

    def test_identity_is_exact_independent_copy(self):
        result = edit_parameters(self.params)
        for field in ("f0", "time", "spectral_envelope", "aperiodicity"):
            np.testing.assert_array_equal(getattr(result, field), getattr(self.params, field))
            self.assertFalse(np.shares_memory(getattr(result, field), getattr(self.params, field)))

    def test_pitch_changes_only_voiced_frequency(self):
        self.params.f0[20:30] = 0
        result = edit_parameters(self.params, pitch_semitones=12)
        np.testing.assert_array_equal(result.f0[:20], 280.0)
        np.testing.assert_array_equal(result.f0[20:30], 0.0)
        np.testing.assert_array_equal(result.spectral_envelope, self.params.spectral_envelope)
        np.testing.assert_array_equal(self.params.f0[:20], 140.0)

    def test_gain_is_power_scaling_and_roundtrip(self):
        raised = edit_parameters(self.params, gain_db=20)
        # +20 dB means ten times the amplitude and one hundred times the power.
        np.testing.assert_allclose(np.sqrt(raised.spectral_envelope), 10 * np.sqrt(self.params.spectral_envelope))
        lowered = edit_parameters(raised, gain_db=-20)
        np.testing.assert_allclose(lowered.spectral_envelope, self.params.spectral_envelope, rtol=1e-14)
        np.testing.assert_array_equal(raised.f0, self.params.f0)

    def test_retime_preserves_unvoiced_gap_and_separate_islands(self):
        self.params.f0[:] = 100
        self.params.f0[20:30] = 0
        self.params.f0[30:] = 300
        result = edit_parameters(self.params, time_scale=2)
        source_time = result.time / 2
        # Safely inside the known unvoiced cell interval: no invented low F0.
        gap = (source_time >= 0.100) & (source_time <= 0.140)
        np.testing.assert_array_equal(result.f0[gap], 0.0)
        np.testing.assert_allclose(result.f0[source_time < 0.095], 100)
        np.testing.assert_allclose(result.f0[source_time >= 0.150], 300)
        self.assertTrue(set(np.round(result.f0, 8)) <= {0.0, 100.0, 300.0})

    def test_round_half_up_length_and_frame_grid(self):
        params = replace(self.params, n_samples=4801)
        result = edit_parameters(params, time_scale=0.5)
        self.assertEqual(result.n_samples, 2401)
        np.testing.assert_allclose(np.diff(result.time), 0.005, atol=1e-15)

    def test_log_power_and_linear_aperiodicity_interpolation(self):
        self.params.spectral_envelope[0] = 1
        self.params.spectral_envelope[1] = 9
        self.params.aperiodicity[0] = 0.2
        self.params.aperiodicity[1] = 0.8
        result = edit_parameters(self.params, time_scale=2)
        np.testing.assert_allclose(result.spectral_envelope[1], 3)
        np.testing.assert_allclose(result.aperiodicity[1], 0.5)

    def test_all_zero_power_stays_zero(self):
        params = make_synthetic_parameters(Parameters, f0_hz=0, spectral_power=0, aperiodicity=1)
        result = edit_parameters(params, time_scale=1.25)
        np.testing.assert_array_equal(result.spectral_envelope, 0)
        np.testing.assert_array_equal(result.f0, 0)
        self.assertTrue(np.all(np.isfinite(result.spectral_envelope)))

    def test_invalid_edits_and_parameters_are_rejected(self):
        for kwargs in ({"pitch_semitones": float("nan")}, {"gain_db": float("inf")},
                       {"time_scale": 0}, {"pitch_semitones": 25}, {"gain_db": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                edit_parameters(self.params, **kwargs)
        bad = replace(self.params, aperiodicity=self.params.aperiodicity.copy())
        bad.aperiodicity[0, 0] = 1.1
        with self.assertRaises(ValueError):
            edit_parameters(bad)
        bad = replace(self.params, time=self.params.time + 0.001)
        with self.assertRaises(ValueError):
            edit_parameters(bad)


if __name__ == "__main__":
    unittest.main()
