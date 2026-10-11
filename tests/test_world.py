"""Boundary tests for the native adapter, not a speech-quality certificate."""
from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

import numpy as np

from vocoderbench import world


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sr = 24000
        t = np.arange(cls.sr // 4) / cls.sr
        cls.x = sum(0.15 / k * np.sin(2 * np.pi * 150 * k * t) for k in range(1, 12))
        cls.params = world.encode(cls.x, cls.sr)

    def test_both_analysis_variants(self):
        for method in ("dio", "harvest"):
            with self.subTest(method=method):
                p = world.encode(self.x, self.sr, method=method)
                y = world.decode(p)
                self.assertEqual(y.shape, self.x.shape)
                self.assertEqual(y.dtype, np.float64)
                self.assertTrue(np.isfinite(y).all())
                self.assertEqual(p.method, method)
                voiced = p.f0[5:-5]
                voiced = voiced[voiced > 0]
                self.assertGreater(voiced.size, 10)
                self.assertLess(abs(np.median(voiced) - 150), 2)

    def test_fixed_rng_repeated_decode(self):
        np.testing.assert_array_equal(world.decode(self.params), world.decode(self.params))

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "parameters.npz"
            world.save(self.params, path)
            loaded = world.load(path)
            np.testing.assert_array_equal(world.decode(loaded), world.decode(self.params))
            self.assertEqual(loaded.source_revision, world.REVISION)

    def test_exact_silence_not_bypassed(self):
        for method in ("dio", "harvest"):
            with self.subTest(method=method):
                p = world.encode(np.zeros(4000), 16000, method)
                y = world.decode(p)
                self.assertEqual(p.status, "silent_input")
                self.assertTrue(np.isfinite(y).all())
                self.assertEqual(np.count_nonzero(p.f0), 0)
                # Stock CheapTrick injects its safety epsilon. Record, do not replace with silence.
                # -120 dBFS peak is only a numerical-safety bound, not a perceptual target.
                self.assertLess(np.max(np.abs(y)), 1e-6)

    def test_reject_unsafe_inputs(self):
        invalid = [np.zeros(0), np.zeros(10), np.full(4000, np.nan),
                   np.full(4000, np.inf), np.zeros((4000, 2)), np.zeros(4000, dtype=complex)]
        for x in invalid:
            with self.subTest(shape=x.shape):
                with self.assertRaises(ValueError):
                    world.encode(x, 16000)
        with self.assertRaises(ValueError):
            world.encode(np.zeros(4000), 8000)

    def test_reject_unsafe_parameters(self):
        invalid = [replace(self.params, aperiodicity=np.full_like(self.params.aperiodicity, -0.1)),
                   replace(self.params, spectral_envelope=np.zeros_like(self.params.spectral_envelope)),
                   replace(self.params, f0=np.full_like(self.params.f0, 1.0)),
                   replace(self.params, time=self.params.time + 0.001),
                   replace(self.params, n_samples=2**31),
                   replace(self.params, source_revision="unknown")]
        for p in invalid:
            with self.subTest():
                with self.assertRaises(ValueError):
                    world.decode(p)

    def test_exact_requested_length_and_coverage(self):
        self.assertEqual(world.decode(self.params, n_samples=5001).size, 5001)
        with self.assertRaises(ValueError):
            world.decode(self.params, n_samples=24000)


if __name__ == "__main__":
    unittest.main()
