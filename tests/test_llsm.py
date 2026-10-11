"""Native integration contracts, not a perceptual quality test.

SPDX-License-Identifier: GPL-3.0-or-later
"""
import unittest
import numpy as np
from vocoderbench.llsm_adapter import reconstruct


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.sr = 16000
        self.time = np.arange(81) * .005
        self.f0 = np.full(81, 150.)
        self.x = .2 * np.sin(2 * np.pi * 150 * np.arange(6400) / self.sr)

    def test_known_periodic_roundtrip_and_input_preservation(self):
        original, original_f0 = self.x.copy(), self.f0.copy()
        y, m = reconstruct(self.x, self.sr, self.f0, self.time)
        self.assertEqual(y.shape, self.x.shape)
        self.assertTrue(np.isfinite(y).all())
        self.assertGreater(np.corrcoef(self.x[500:-500], y[500:-500])[0, 1], .99)
        self.assertEqual(m['native_output_samples'], 6560)
        self.assertTrue(np.array_equal(self.x, original))
        self.assertTrue(np.array_equal(self.f0, original_f0))

    def test_noise_seed_repeatability_and_distinct_streams(self):
        x = np.random.default_rng(132).normal(0, .01, 6400)
        f0 = np.zeros_like(self.f0)
        a, _ = reconstruct(x, self.sr, f0, self.time, seed=0)
        b, _ = reconstruct(x, self.sr, f0, self.time, seed=0)
        c, _ = reconstruct(x, self.sr, f0, self.time, seed=1)
        self.assertTrue(np.array_equal(a, b))
        self.assertFalse(np.array_equal(a, c))

    def test_dangerous_f0_rejected_before_native_call(self):
        for value in (1e-6, -1., 2100., np.nan):
            with self.subTest(value=value), self.assertRaises(ValueError):
                reconstruct(self.x, self.sr, np.full(81, value), self.time)

    def test_complex_and_irregular_time_rejected(self):
        with self.assertRaises(ValueError):
            reconstruct(self.x.astype(complex), self.sr, self.f0, self.time)
        badtime = self.time.copy()
        badtime[12] += .001
        with self.assertRaises(ValueError):
            reconstruct(self.x, self.sr, self.f0, badtime)

    def test_silence_is_finite_without_concealing_noise_floor(self):
        y, m = reconstruct(np.zeros_like(self.x), self.sr, np.zeros_like(self.f0), self.time)
        self.assertTrue(np.isfinite(y).all())
        self.assertEqual(len(y), len(self.x))
        self.assertEqual(m['normalization'], 'none')


if __name__ == '__main__':
    unittest.main()
