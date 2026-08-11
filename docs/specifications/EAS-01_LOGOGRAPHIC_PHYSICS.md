# EAS-01: Logographic Physics & Empirical Falsification Report


## Executive Summary
This normative document records the empirical falsification series (EAS-01 Phase 1, 1b, 1c) evaluated over the 111-note control corpus (`tools/experiments/_wp1_corpus.py`).


## Findings Summary
1. **EAS-01 Phase 1 (Orthogonal Sparse)**: Falsified. Degenerated into keyword matching ($\theta_{\text{dyn}} = 0.0$). Failed control C4 (keyword injection consolidated pure noise).
2. **EAS-01 Phase 1b (Non-Orthogonal Sparse)**: Falsified. Rescued $\theta_{\text{dyn}} > 0.0$, but retained lexical vulnerability under C4 injection.
3. **Markov Spectral Gap**: Falsified ($p = 0.68$). Measures language orthographic regularity rather than conceptual depth.
4. **EAS-01 Phase 1c (NCD Compression Coupling)**: Validated ($AUC > 0.93$, $p < 10^{-6}$). Defeated keyword injection (C4).


## Conclusion
Natural language notes require Normalized Compression Distance (NCD) or Human-In-The-Loop (HITL) validation. Continuous spectral variance ($\sigma^2$) is reserved for continuous physical signals and sensor modalities ($S_n = (V_n, E_n, K_n)$).
