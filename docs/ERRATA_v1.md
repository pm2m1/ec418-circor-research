# ERRATA_v1 — wording corrections after external review (2026-10-27)

No number, prediction file, fold or figure changed. Only interpretation text was corrected.
The original wording is preserved at git tag `v1.0-pilot`; `git diff v1.0-pilot -- docs/` shows every edit.

| # | Was | Now | Why |
|---|---|---|---|
| 1 | "the improvement comes from **aligning features to the cardiac cycle**" | "the **cycle-aligned feature pipeline** gives the improvement" | Whole and aligned extractors use different statistics, so the gain mixes interval choice, feature definitions and normalisation. Isolating timing is Phase-2 E2. |
| 2 | "identical bands, time grid and dimensionality" | adds "not identical effective time resolution" | Decimated packets vs 64-sample Hann frames smooth time differently. |
| 3 | Smoothing result: "WPD ≈ STFT, no wavelet advantage" | "consistent with an estimator-variance explanation; exploratory, not proof of equivalence" | Designed after seeing H2. |
| 4 | Main-table AUROC unlabelled | labelled "mean of 5 repeats"; repeat-averaged-score AUROC (0.815/0.798/0.751/0.747/0.726/0.685) listed separately | Two different summaries; the CI belongs to the second. An external reviewer recomputed the second set exactly from the saved predictions. |
| 5 | Headline "alignment, not the wavelet, is what helps" | "the cycle-aligned pipeline helps; the wavelet does not by itself" | Same as #1. |
| 6 | Baseline-defect description | adds a public-claim caveat: re-check on the PhysioNet copy, contact the authors, say "appears to be misaligned" | Not yet independently reproduced outside this repository. |

External review points accepted in full: both methodological concerns (alignment not isolated;
time resolution not matched) and the recommended title. They are addressed by `PROTOCOL_V2_LOCKED.md`.
