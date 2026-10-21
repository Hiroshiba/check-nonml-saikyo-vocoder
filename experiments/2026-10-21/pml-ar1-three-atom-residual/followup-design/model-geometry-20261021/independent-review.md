Verdict: mathematically coherent as a publication-only audit of the unchanged working model, with these minimal corrections.

1. Separate atom evidence from full H1 evidence.
Let
AqK(z) = (1/3) Σa m1(z | a,q,K),
E0(z) = (1/3) Σa m0(z | a),
E1(z) = (1/4610) Σq,K AqK(z).

Then BF = E1/E0 and P(H1 | z) = 7BF/(3+7BF). The supplied integrated-density constant, exponent 203, and determinant power are correct for IG(shape 3, scale 2). The 0.3/0.7 probabilities do not enter BF.

A ratio of a-mixtures is not the unweighted mean of fixed-a BFs. It does equal their H0-posterior-weighted mean.

2. Qualify “not a hard bandlimit.”
The noiseless harmonic process has spectral atoms only at ±hf, h≤K, hence maximum line Kf. Suggested replacement:
“This is a finite harmonic-line prior, not a broadband low-pass prior. Finite-window DFT leakage need not vanish above Kf, while the noisy observation model has full R400 support.”

3. State what equal trace establishes.
diag(S)=1 and trace(S)=400 imply E[||Xβ||² | s]=400s, not fixed realized energy or equal determinants. With diag(C)=1, the model also fixes the ratio of prior expected signal and noise energies at one; s is not an independent harmonic-amplitude/SNR parameter.

For nesting, write multiplier r≥2, or say the priors “generally differ.” The trivial r=1,L=K case is identical.

4. Make the local diagnostic exact.
For low/high-q atoms at the same a,K:
Δ = −½ log(|Vlow|/|Vhigh|)
    −203 log{[2+zᵀVlow⁻¹z/2]/[2+zᵀVhigh⁻¹z/2]}.

If Δ>0 while its determinant contribution is ≤0, that contrast contradicts a determinant-only explanation. It does not refute B overall or establish the cause of a K/a-marginalized decision. Call the second contribution the “quadratic-form/scale term,” rather than an independently optimized residual fit.

5. Preserve the remaining qualifications.
- Explicitly define Cnm=a^|n−m|. Then (Wv)0=v0, (Wv)n=(vn−avn−1)/√(1−a²), and det(C)=(1−a²)^399.
- A’s covariance-sum formula assumes conditional independence; a common nuisance covariance does not cancel from BF. Deferral without choosing Λ is sound.
- Proper R400 density normalization does not establish normalization or ordering for the induced RMS-normalized feature distribution. Describe resulting evidence/posteriors as working-model quantities, not calibrated physiological V/UV probabilities.
- Marginalized saved b values cannot reconstruct missing per-K/a determinant and quadratic-form contributions. Numerical causation remains undecided.

The literature characterization is accurate: [Shi 2019](https://publications.aston.ac.uk/id/eprint/39590/1/Harmonic_Model.pdf) uses MMSE noise-PSD estimation and LP order 30; [Jaramillo et al. 2020](https://vbn.aau.dk/ws/files/321346849/icassp2020AAJM_accepted.pdf) uses AR order 25, trained Par-NMF dictionaries, and threshold-stopped refinement. Neither directly validates the current finite AR(1) mixture.

No new model, hyperparameters, or experiment gate is required by this review.
