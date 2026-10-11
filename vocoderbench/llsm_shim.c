/* SPDX-License-Identifier: GPL-3.0-or-later
 * Offline comparator wrapper for libllsm2. No upstream code is copied here.
 */
#include <math.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include "llsm.h"

/* Returns native output length; negative values are adapter error codes.
 * f0_refine is disabled: the supplied F0 is the analysis condition.
 * No phase synchronization, peak normalization, or input-waveform bypass.
 * The caller must serialize invocations because upstream uses libc rand().
 */
int nonml_llsm_reconstruct(const double *x, int nx, int fs,
    const double *f0, int nfrm, double hop_seconds, unsigned seed,
    double *dst, int capacity) {
  if (!x || !f0 || !dst || nx < 1 || nfrm < 2 || fs < 16000 || fs > 96000 ||
      !isfinite(hop_seconds) || hop_seconds < 1.0 / fs || hop_seconds > 0.05 ||
      seed == UINT_MAX) return -1;
  const double expected_double = round(((double)nfrm + 1) * hop_seconds * fs);
  if (expected_double > INT_MAX || expected_double < 1) return -2;
  const int expected = (int)expected_double;
  if (capacity < expected || expected < 1) return -2;
  for (int i = 0; i < nx; ++i) if (!isfinite(x[i])) return -3;
  for (int i = 0; i < nfrm; ++i)
    if (!isfinite(f0[i]) || f0[i] < 0 ||
        (f0[i] > 0 && (f0[i] < 40 || f0[i] > 2000))) return -4;
  double *xin = malloc(sizeof(double) * nx);
  double *fin = malloc(sizeof(double) * nfrm);
  if (!xin || !fin) { free(xin); free(fin); return -5; }
  memcpy(xin, x, sizeof(double) * nx);
  memcpy(fin, f0, sizeof(double) * nfrm);
  llsm_aoptions *a = llsm_create_aoptions();
  llsm_soptions *s = llsm_create_soptions(fs);
  a->thop = hop_seconds;
  a->f0_refine = 0;
  a->hm_method = LLSM_AOPTION_HMCZT;
  a->maxnhar = 400;
  /* Exclude empty bands at/above Nyquist (e.g. the default 8 kHz break at
   * fs=16 kHz). Keep upstream 2/4/8 kHz edges where strictly below Nyquist. */
  int edges = 0;
  for (int i = 0; i < a->nchannel - 1; ++i)
    if (a->chanfreq[i] < fs / 2.0) a->chanfreq[edges++] = a->chanfreq[i];
  a->nchannel = edges + 1;
  /* glibc maps srand(0) and srand(1) to the same stream. Exclude native 0. */
  srand(seed + 1U);
  llsm_chunk *chunk = llsm_analyze(a, xin, nx, fs, fin, nfrm, NULL);
  llsm_output *out = chunk ? llsm_synthesize(s, chunk) : NULL;
  int result = -6;
  if (out && out->ny <= capacity) {
    result = out->ny;
    for (int i = 0; i < out->ny; ++i) {
      if (!isfinite(out->y[i])) { result = -7; break; }
      dst[i] = out->y[i];
    }
  }
  llsm_delete_output(out);
  if (chunk) llsm_delete_chunk(chunk);
  llsm_delete_aoptions(a);
  llsm_delete_soptions(s);
  free(xin); free(fin);
  return result;
}
