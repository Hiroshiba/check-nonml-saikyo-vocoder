# Independent static numerical review: direct harmonic posterior

Date: 2026-10-19 UTC. Scope: read-only inspection of the implementation in `direct-harmonic-posterior-job-20261019`, the fixed author sources in `probabilistic-pitch-octave-job-20261019/upstream`, and `direct-harmonic-posterior-feasibility-20261019.md`. This review ran no estimator, numerical experiment, compilation, dependency installation, or tests. Shell activity was limited to source reading, file comparison/hashing, and writing this report.

## Decision

**No proven numerical implementation blocker found in the inspected snapshot.** The implementation follows the declared direct-projection mathematical path and the author's posterior/filter equations. This is a static consistency conclusion, not evidence of numerical accuracy on the five recordings, runtime completion, MATLAB equivalence, probability calibration, or audio quality. The actual authorized scientific diagnostic remains the first numerical observation.

The package was being finalized during review. Missing final manifest/NOTICE at the time of inspection is not interpreted as a numerical defect; deployment must use the finalized manifest and must not imply that later source changes were reviewed here.

## Snapshot

SHA-256 at review:

- model.py: `111c5bfda62595a3b5f01208741fc52303dc78c2569d9dbc889b399244c95955`
- run.py: `dcadae6ae2ee9d126d971c3db3c6ebd2805604fc34843fced52a413de851929e`
- summaries.py: `e258a7a98c76bab89856ecf23412c0ffdc2f153b11fb8ecb8019115c84810050`
- storage.py: `a02527453ecc36036f13b3068f978b045f890d5469ee11c59dfbc9639be703ea`

The copied BayesianfastF0NLS.m was byte-identical to the fixed upstream class inspected. This report does not assert independently verified hashes for every helper or remote commit.

## Static checks that pass

### Grid, basis, projection

- model.py:8–14 fixes Fs=16000, N=400, hop=160, FFT=16384, K=1..10, q=52..512, varSpeech=5e-6, target RMS=sqrt(3.1623e-5). The lowest actual candidate is 50.78125 Hz, not 50 Hz. All ten harmonics are below Nyquist even at 500 Hz.
- model.py:41–50 uses the centered time basis t=n−(N−1)/2, not mean subtraction from the observations. Symmetric times make the cosine/sine cross block zero in exact arithmetic. Each Gram is formed directly; there is no ridge, DC column, pseudoinverse, rank truncation, or candidate omission.
- model.py:43,75–77 applies the positive centered-origin phase to the usual unnormalized forward FFT. Its real part is Cᵀx and minus its imaginary part is Sᵀx. The author's imaginary-part sign convention differs by a uniform sine-column sign; the quadratic projection is unchanged.
- model.py:57,77–82 solves both lower Cholesky systems in harmonic order. The leading K×K principal Cholesky block is exactly the factor for the first K harmonics. Consequently cumulative squared solve coefficients produce the independent order-K projection energies in exact arithmetic. The implementation does not mistakenly take a prefix of a full inverse or a full least-squares coefficient vector.
- model.py:48–68 records cross-block, symmetry, condition number, factorization residual, and stops on detected inconsistency. It does not silently discard failed frequencies. The floating-point magnitude of these recorded quantities remains unknown.

### Laplace local log Bayes factor

- model.py:91–115 agrees with computePitchLogLikelihood.m for delta=3 and K laid out on the last array dimension. In particular w=(N−2K−3)/2, u=N/2, v=1, and the factor log(g/2) is correct.
- For r in [0,1), a=−(K+1/2)(1−r)<0. The positive-root branch for b>=0 and rationalized branch 2v/(sqrt(D)−b) for b<0 are algebraically equivalent to the author's root. The rationalized branch avoids its subtractive cancellation.
- Curvature uses the author's difference, and log1p is used for the likelihood terms. A nonpositive/nonfinite curvature causes failure rather than clipping or replacement. This does not prove that cancellation is negligible on real frames.
- H0 has likelihood ratio 1 (log ratio 0), as seen in posterior's null weight. Regularization is in r=J/(E+N*varSpeech), not in the Gram factorization. The output should be described as using the author's regularized cod, not as an unregularized exact Bayes factor.

### Local views and temporal filtering

- model.py:137–141 constructs local/base with total voiced mass .7 and H0=.3. local/log-Hz replaces only the F0 prior by normalized 1/f, keeping uniform K and the same voiced/null totals. Neither local view mutates filter state.
- model.py:30–35 row-normalizes a Gaussian kernel. Dropping its constant normal-density prefactor is exact after row normalization. FREQ uses Hz with sd=2, equivalent to the author's normalized-frequency sd=2/16000; K uses sd=1.
- model.py:160 has the correct orientation, .7 Aᵀ Q B + .4 p0 R. With rows representing previous-state-to-next-state probabilities, both multiplications move mass in the intended direction, including asymmetric row-normalized boundaries. It does not transpose B incorrectly.
- model.py:161 correctly uses u0=.3(1−p0)+.6p0. The first update at 156–158 uses the initial prior without an extra transition.
- model.py:163–165 updates revoicing memory only for posterior H0<.5, using the conditional voiced distribution. Initial R is uniform, and source-frame metadata reports the memory available before the current update. This matches the author's branch; it is not a new quality gate.
- The same log-sum-exp includes every voiced cell and H0 (119–134). Prior/posterior mass is checked. Exponentiating normalized results is expected because the author's temporal transition is also performed on probability arrays.

### Recording normalization, silence, and failures

- run.py:91–102 checks real numeric one-dimensional fixed-length input, converts to float64, rejects nonfinite input, and uses recording-global RMS. It does not frame-normalize or subtract DC. The scale is mathematically the declared RMS normalization, with scaled sum-of-squares to avoid ordinary overflow.
- run.py:103,130–134 uses every hop center, and zero-pads both ends into a 400-sample frame. The basis origin is the half-sample center of that even-length frame. The reported nominal center is the declared frame center; this is not an unexplained one-sample shift in the FFT basis. This framing intentionally differs from the author's offline wrapper's end rule.
- run.py:148–150 applies the strict author energy-floor comparison E/N<1e-10 before inference. It increments the skipped counter without changing posterior or revoicing memory or applying time transitions. A new Filter per recording resets recordings but not silence intervals.
- Missing arrays remain NaN for skipped or failed frames; no silent frame is rewritten as H0=1. Whole-recording zero and ordinary energy floor have separate statuses, and padding counts are independent fields.
- run.py:144–175 restores filter state if a later numerical/summary step fails. It stops that input after recording the failure and preserves later frames as unprocessed. A failed likelihood is not replaced by −inf and renormalized away. This is an intentional stricter behavior than the author's NaN-to−inf handling.

## Proven implementation caveats, not demonstrated failures

1. **Projection rejection is deliberately stricter than a roundoff-aware acceptance scheme.** model.py:86–87 rejects even a tiny positive J−E. This prevents silently clipping J but can terminate a mathematically valid nearly exact harmonic fit owing to rounding. The feasibility design allowed recording an error bound to resolve a roundoff excursion; this implementation instead fails conservatively. It records energy, J extrema, and maximum excess, but not the offending cell's complete intermediate solve. Do not call a resulting failure evidence that the signal violates the harmonic model. No such failure was observed in this static review.
2. **Underflow can produce exact zero transition/posterior cells.** model.py:31–32,123–130 explicitly permits IEEE underflow. A mathematically positive Gaussian tail can therefore become zero, and posterior exponentiation can lose negligible mass. Later prior zeros remain log weight −inf even when the local logBF is finite. This is not deletion of invalid likelihood cells, and the author similarly computes transitions and state buffers in ordinary probability arithmetic, but it is not exact full-support arithmetic. run.py:160–161 records zero counts and grid-transition.npz stores A/B. Do not present a stored zero as a mathematically impossible F0. H0 may itself underflow to zero in output; the next H0 prediction remains positive (.3 when previous H0=0).
3. **Condition/residual checks are safeguards, not forward-error certification.** model.py:59–65 uses a normwise residual bound and the permissive condition criterion cond*K*eps<1. Successful completion does not by itself establish a tight J or logBF forward-error bound. Reporting the actual Gram diagnostics remains important; condition number alone must not become an unapproved candidate pruning rule.
4. **Extreme finite inputs can fail normalization.** run.py:98–102 can encounter scale overflow for an extraordinarily tiny positive global RMS. This is safely rejected by the configured floating-point error handling, not silently converted into a posterior. Whether the five fixed inputs approach such extremes was not inspected numerically.
5. **MAP labels are descriptive even when voiced mass is tiny.** summaries.py:40–51 always names the maximum voiced cell and marginal F0. It also includes H0 and voiced_mass; these must accompany interpretation. A voiced-grid MAP is not a claim of voiced presence or calibrated certainty.

## Unknown until the single authorized diagnostic

Actual dependencies and BLAS behavior in the selected execution environment; Gram conditions and residuals; per-frame J bounds and curvature stability; underflow counts; five-input completion within 30 minutes, 2 GiB RAM, and 1 GiB output; empirical mode/octave patterns; and the scientific utility of this model for the selected recordings all remain unknown. No additional tests or parameter search are recommended as part of this review. Any execution failure should be reported with its saved provenance and classified as numerical/operational, rather than repaired by silently changing support, priors, window, regularization, or tracker.

## Finalization recheck (2026-10-19 21:17 UTC)

The finalized files were re-read statically. model.py and storage.py hashes are unchanged. Current run.py hash is `57b47ffa18a71c786cd71ab588db290dd9f177392c32a92c3cf24e9b2f367300`; current summaries.py hash is `66b5ef6c8cca261e7b6d221452c37fd9410153d99ed5670f61fa8d8075aa77c6`. NOTICE.md, PACKAGE_MANIFEST.json, PROTOCOL.md, README.md, and cloud-b-paths.json are now present. Their existence is not a claim of environment execution or complete packaging audit.

The changed summaries.py:44–51 now marks voiced MAP undefined when numerical voiced mass is exactly zero; :92–93 does likewise for the representative. This supersedes the earlier literal statement that a MAP is always named. The remaining caveat is only that a defined MAP with tiny positive voiced mass is descriptive and must be interpreted alongside H0. summaries.py:74 explicitly labels zero regional prior support. The final run.py writes completed/partial results and returns exit code 0/2 accordingly; module entry uses sys.exit(main()). No numerical blocker is introduced by these inspected finalization changes. Final numerical-review disposition remains: **no proven static numerical blocker; runtime behavior unobserved**.
