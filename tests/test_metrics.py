"""Calibration/negative controls, not tests that merely repeat implementation."""
import json
import unittest

import numpy as np
from scipy import signal

from vocoderbench.fixtures import make_synthetic_cases, make_pitch_stress_cases
from vocoderbench.metrics import compare_waveforms, pitch_metrics, estimate_f0_yin


class MetricCalibration(unittest.TestCase):
    def test_independent_f0_known_truth_and_missing_fundamental(self):
        for sr in (16000, 24000, 48000):
            for c in make_synthetic_cases(sr):
                p = pitch_metrics(c["x"], sr, c["f0_truth"])
                self.assertEqual(p["missing_voiced_frames"], 0, c["id"])
                self.assertEqual(p["false_voiced_frames"], 0, c["id"])
                self.assertEqual(p["total_frames"], p["expected_voiced_frames"]+p["expected_unvoiced_frames"]+p["boundary_frames"])
                if p["expected_voiced_frames"]:
                    self.assertLess(p["abs_error_cents_p95"], 5.0, c["id"])
                else:
                    self.assertIsNone(p["abs_error_cents_p95"])

    def test_identity_gain_lowpass_delay(self):
        c = make_synthetic_cases(16000)[1]
        x, sr = c["x"], c["sr"]
        identity = compare_waveforms(x, x, sr)
        self.assertEqual(identity["mr_stft_log_magnitude_mae_db"], 0)
        self.assertEqual(identity["band_energy"]["active_band_mae_db"], 0)
        self.assertEqual(identity["rms_gain_error_db"], 0)
        gain = compare_waveforms(x, x*0.5, sr)
        self.assertAlmostEqual(gain["rms_gain_error_db"], 20*np.log10(0.5), places=8)
        self.assertGreater(gain["mr_stft_log_magnitude_mae_db"], 0)
        self.assertAlmostEqual(gain["band_energy"]["active_band_mae_db"], -20*np.log10(0.5), places=8)
        low = signal.sosfilt(signal.butter(6, 500, fs=sr, output="sos"), x)
        filtered = compare_waveforms(x, low, sr)
        self.assertGreater(filtered["band_energy"]["active_band_mae_db"], 3)
        self.assertGreater(filtered["mr_stft_log_magnitude_mae_db"], 1)
        delayed = np.r_[np.zeros(160), x[:-160]]
        shifted = compare_waveforms(x, delayed, sr)
        self.assertEqual(shifted["alignment"], "none")
        self.assertGreater(shifted["mr_stft_log_magnitude_mae_db"], 0.01)

    def test_failures_are_not_zero_scores(self):
        x = make_synthetic_cases(16000)[0]["x"]
        cropped = compare_waveforms(x, x[:-1], 16000)
        self.assertEqual(cropped["status"], "length_mismatch")
        self.assertEqual(cropped["length_delta_samples"], -1)
        self.assertIsNone(cropped["mr_stft"])
        y = x.copy(); y[10] = np.nan
        invalid = compare_waveforms(x, y, 16000)
        self.assertEqual(invalid["status"], "nonfinite_input_or_output")
        self.assertFalse(invalid["output_finite"])
        self.assertIsNone(invalid["mr_stft"])
        json.dumps(invalid, allow_nan=False)
        empty = compare_waveforms([], [], 16000)
        self.assertEqual(empty["status"], "empty_signal")

    def test_silence_and_noise_floor_do_not_hide_added_noise(self):
        sr = 16000
        silence = np.zeros(sr)
        m = compare_waveforms(silence, silence, sr, np.zeros(sr))
        self.assertIsNone(m["rms_gain_error_db"])
        self.assertIsNone(m["band_energy"]["active_band_mae_db"])
        self.assertTrue(all(row["spectral_convergence"] is None for row in m["mr_stft"]))
        self.assertEqual(m["pitch"]["false_voiced_frames"], 0)
        noise = np.random.default_rng(15).normal(0, 0.01, sr)
        n = compare_waveforms(silence, noise, sr, np.zeros(sr))
        self.assertGreater(n["output_rms_dbfs"], -42)
        self.assertGreater(n["mr_stft_log_magnitude_mae_db"], 10)
        self.assertTrue(all(row["delta_db"] > 40 for row in n["band_energy"]["bands"]))
        json.dumps(n, allow_nan=False)

    def test_wrong_pitch_and_dropped_voicing_are_counted(self):
        sr = 16000
        t = np.arange(sr)/sr
        wrong = pitch_metrics(np.sin(2*np.pi*240*t), sr, np.full(sr, 120.0))
        self.assertGreater(wrong["abs_error_cents_median"], 1190)
        self.assertEqual(wrong["gross_pitch_error_frames"], wrong["expected_voiced_frames"])
        dropped = pitch_metrics(np.zeros(sr), sr, np.full(sr, 120.0))
        self.assertEqual(dropped["missing_voiced_frames"], dropped["expected_voiced_frames"])
        self.assertIsNone(dropped["abs_error_cents_p95"])
        added = pitch_metrics(np.sin(2*np.pi*120*t), sr, np.zeros(sr))
        self.assertEqual(added["false_voiced_frames"], added["expected_unvoiced_frames"])

    def test_dc_energy_is_not_periodicity(self):
        sr = 24000
        dc = pitch_metrics(np.full(sr, 0.1), sr, np.zeros(sr))
        self.assertEqual(dc["false_voiced_frames"], 0)
        t = np.arange(sr)/sr
        tone = pitch_metrics(0.1 + 0.2*np.sin(2*np.pi*150*t), sr, np.full(sr, 150.0))
        self.assertLess(tone["abs_error_cents_p95"], 5)

    def test_broadband_fractional_period_and_endpoint_calibration(self):
        for sr in (16000, 24000, 48000):
            for c in make_pitch_stress_cases(sr):
                p = pitch_metrics(c["x"], sr, c["f0_truth"])
                self.assertEqual(p["missing_voiced_frames"], 0, c["id"])
                self.assertEqual(p["gross_pitch_error_frames"], 0, c["id"])
                self.assertLess(p["abs_error_cents_p95"], 5, c["id"])
        # A independently known 180 Hz broadband pulse must not become a
        # decoder failure: the original unfiltered diagnostic misses it.
        c = next(c for c in make_pitch_stress_cases(24000)
                 if c["fundamental_hz"] == 180 and c["offset_cycles"] == 0)
        raw = estimate_f0_yin(c["x"], 24000, prefilter_hz=None)
        self.assertTrue(np.all(raw["f0_hz"] == 0))

    def test_fixture_seed_reproducibility_and_variability(self):
        a, b, c = (make_synthetic_cases(16000, seed=s) for s in (1, 1, 2))
        for first, second in zip(a, b):
            np.testing.assert_array_equal(first["x"], second["x"])
        self.assertFalse(np.array_equal(a[6]["x"], c[6]["x"]))
        np.testing.assert_array_equal(a[0]["x"], c[0]["x"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
