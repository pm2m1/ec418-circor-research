# E4_RESULTS — Automatic span selector + LR-HSMM timing (Phase 2)

Pre-registered in `docs/PROTOCOL_V2_LOCKED.md` "E4" + `configs/protocol_v2.json` (commit `64e0e91`, tag `e4-prereg`, pushed
before any E4 code; the section header says 23:30 IST, the commit was made at 23:26 IST). **E4 was designed after the
diagnostics D1–D3 were known.** Data: PhysioNet CirCor v1.0.3, frozen folds, 874 patients, all 5 repeats × 5 folds.
Classification finished 2026-10-27 23:40 IST, inside the 2026-10-29 23:59 IST timebox. Nothing was tuned after the
classification results.

| Step | Command | Output |
|---|---|---|
| window cache | `NPROC=10 python scripts/26_e4_run.py cache` | `data/interim/e4/windows/` (gitignored) |
| fold-wise HSMM + detectors + features | `… 26_e4_run.py run 0,1,2,3,4` (210 s) | `data/interim/e4/features/` (gitignored), `results/logs/e4_models/`, `results/logs/e4_run_folds.csv` |
| detector evaluation | `… 26_e4_run.py evaluate` | `results/tables/e4_span_detector.csv`, `results/logs/e4_span_detector.{json,log}` |
| WEKA | `python scripts/06_run_patient_level_weka.py e4 E4_stft,E4_wpd,E4_wpds RF,SMO 8` | `results/predictions/e4_predictions.csv` (600 jobs), `results/logs/run_e4.log` |
| analysis | `python scripts/27_e4_analyze.py` | `results/tables/e4_{auroc,hypotheses,references,grade_sensitivity,feature_coverage}.csv`, `results/logs/e4_analysis.{json,log}` |
| post-hoc caveat check | `python scripts/28_e4_shortcut_check.py` | `results/tables/e4_shortcut_check.csv` |

## 1. Implementation
* `src/ec418/segmentation/spans.py` (5 unit tests; suite 81/81). There are 67,313 1-s windows over the 3,007 binary-task
  recordings, 54.9 % expert-annotated, with no missing feature values. The trailing partial windows are dropped.
* **Six features, as pre-registered.** Feature 6 is included: the LR-HSMM port exposes the per-state logistic-regression
  probabilities P(state | o) (`lr_hsmm.state_probabilities`, a refactor of the emission code). It is **not** an HSMM
  forward–backward posterior, which the port does not compute.
* **Detector:** StandardScaler + L2 logistic regression, C = 1.0. Repeat 0 / fold 0 outer-detector weights (standardised
  features): 20–200 Hz ratio +0.91, envelope periodicity +0.65, clipping −0.61, 25–400 Hz fraction +0.05, kurtosis −0.05,
  HSMM probability +0.07. Threshold 0.562 (training predicted fraction = training expert fraction). All 100 detectors are in
  `results/logs/e4_models/`.
* **Cross-fitting exactly as E1b.** All 15,035 outer-model HSMM decodes were re-derived and checked identical to E1b.
* **Fix before any classification run:** a first run passed the column-rounded duration to `states_to_segments`, so one
  decode (50782_MV_2, last column) differed. It was fixed to E1b's exact duration and the run was repeated.

## 2. Span detector vs the expert mask (test-fold windows; repeat 0; repeats 1–4 within ±0.001)
| Group | Windows | Window AUROC | Accuracy | Expert annotated | Predicted annotated | Sensitivity | Specificity |
|---|---:|---:|---:|---:|---:|---:|---:|
| **All** | 67,313 | **0.770** | **0.709** | 0.549 | 0.549 | 0.735 | 0.678 |
| Absent | 53,892 | 0.774 | 0.709 | 0.541 | 0.527 | 0.718 | 0.699 |
| Present | 13,421 | 0.752 | 0.709 | 0.582 | **0.638** | 0.798 | 0.586 |
| Neonate | 154 | 0.790 | 0.773 | 0.325 | 0.396 | 0.760 | 0.779 |
| Infant | 5,094 | 0.753 | 0.732 | 0.258 | 0.285 | 0.534 | 0.801 |
| Child | 50,161 | 0.761 | 0.705 | 0.567 | 0.564 | 0.737 | 0.663 |
| Adolescent | 5,702 | 0.766 | 0.722 | 0.610 | 0.635 | 0.792 | 0.612 |
| Age missing | 6,202 | 0.770 | 0.717 | 0.595 | 0.567 | 0.739 | 0.684 |

The detector is moderate (AUROC 0.77) and **over-selects Present windows** (0.638 vs expert 0.582), while slightly
under-selecting Absent ones (0.527 vs 0.541).

## 3. Missing aligned features (per fold; min–max, mean)
Recordings without aligned features: 418–456 (mean 439 = 14.6 %), of which Present 59–66 (mean 62 = 10.1 % of Present
recordings) and Absent 357–392 (mean 377 = 15.8 % of Absent recordings). Patients without any: 37–43 (mean 41), Present
4–5 (2.3 %), Absent 33–39 (5.3 %). WEKA sees these as missing values. **The missingness is class-related.** For
comparison: expert labels 1 recording, E1b ≤ 1 per fold, D1 mean 221 recordings / 24 patients.

## 4. AUROC (repeat-averaged [subject-bootstrap 95 % CI] / mean of repeats ± SD)
| Set | RF | SMO |
|---|---|---|
| **E4 stft** | **0.809** [0.766, 0.849] / 0.803 ± 0.009 | **0.814** [0.772, 0.854] / 0.808 ± 0.006 |
| **E4 wpd** | **0.791** [0.746, 0.831] / 0.784 ± 0.009 | **0.809** [0.767, 0.850] / 0.803 ± 0.006 |
| **E4 wpds** | **0.796** [0.751, 0.836] / 0.789 ± 0.007 | **0.814** [0.772, 0.852] / 0.808 ± 0.006 |
| expert labels stft / wpd / wpds | 0.815 / 0.798 / 0.800 | 0.816 / 0.785 / 0.794 |
| D1 (expert spans, upper) stft / wpd / wpds | 0.800 / 0.783 / 0.791 | 0.800 / 0.802 / 0.805 |
| E1b (no selection, lower) stft / wpd / wpds | 0.709 / 0.707 / 0.712 | 0.727 / 0.710 / 0.710 |
| B1 | 0.726 [0.677, 0.773] / 0.721 | 0.744 [0.698, 0.788] / 0.741 |
| W_stft | 0.751 [0.701, 0.794] / 0.744 | 0.747 [0.698, 0.795] / 0.743 |

## 5. Pre-registered hypotheses (RF; primary representation wpd)
| Hypothesis | Representation | Contrast | Δ repeat-averaged [95 % CI] | folds Δ > 0 | Δ mean of repeats | Verdict |
|---|---|---|---|---|---|---|
| **H9a** (≥ expert − 0.03) | **wpd** | E4 − expert | **−0.007** [−0.044, +0.031] | 10/25 | −0.009 | **SUPPORTED** |
| **H9b** (> B1, CI lo > 0) | **wpd** | E4 − B1 | **+0.065** [+0.022, +0.115] | 25/25 | +0.063 | **SUPPORTED** |
| **H9c** (> W_stft, CI lo > 0) | **wpd** | E4 − W_stft | **+0.040** [−0.003, +0.089] | 21/25 | +0.040 | **NOT SUPPORTED** |
| H9a | stft | E4 − expert | −0.006 [−0.044, +0.031] | 8/25 | −0.009 | SUPPORTED |
| H9b | stft | E4 − B1 | +0.083 [+0.036, +0.135] | 24/25 | +0.082 | SUPPORTED |
| H9c | stft | E4 − W_stft | +0.058 [+0.011, +0.108] | 22/25 | +0.059 | SUPPORTED |
| H9a | wpds | E4 − expert | −0.005 [−0.044, +0.035] | 9/25 | −0.007 | SUPPORTED |
| H9b | wpds | E4 − B1 | +0.070 [+0.027, +0.120] | 25/25 | +0.068 | SUPPORTED |
| H9c | wpds | E4 − W_stft | +0.045 [+0.001, +0.094] | 21/25 | +0.045 | SUPPORTED |

SMO (descriptive): E4 − expert +0.024 / −0.002 / +0.020; E4 − B1 +0.065 / +0.070 / +0.069; E4 − W_stft +0.062 / +0.067 /
+0.067 (wpd / stft / wpds), all E4 − B1 and E4 − W_stft CIs > 0.

**The deployability test fails for the primary representation:** for wpd, the gain over whole-signal STFT is +0.040, but
the CI lower bound is −0.003. It passes for the two secondary representations (stft +0.058, CI from +0.011; wpds +0.045,
CI from +0.001, a very narrow margin).

## 6. References and caveats
| (RF) | stft | wpd | wpds |
|---|---|---|---|
| E4 − D1 (expert spans) | +0.009 [−0.026, +0.045] | +0.008 [−0.025, +0.043] | +0.005 [−0.027, +0.039] |
| E4 − E1b (no selection) | +0.099 [+0.054, +0.144] | +0.085 [+0.043, +0.125] | +0.083 [+0.042, +0.123] |

E4 recovers all of the span-selection gain: it sits at the D1 upper reference and +0.08 to +0.10 above E1b.

**Caveat — class information in the selection itself.** This check was not pre-registered (post-hoc, descriptive,
`scripts/28_e4_shortcut_check.py`), and it changes no verdict. It scores test patients by span-selection by-products alone,
with no acoustic features. Mean per-fold AUROC over the 25 folds:
* the detector's predicted-annotated fraction: **0.646** (SD 0.055);
* the share of recordings left without aligned features, as a score for Absent: **0.567** (SD 0.040);
* for comparison, the expert-annotated fraction: 0.547 (SD 0.056).

So the detector's choice of spans carries more Present/Absent information than the expert's did. Part of E4's gain could
come through that route (e.g. missing-value patterns or class-dependent span choice) rather than through cleaner cardiac
timing. This study does not separate the two.

**Grade sensitivity** (RF, spec ≥ 0.80 inner threshold, mean of repeats): grade I/VI (n = 104) E4 0.544 / 0.475 / 0.483
(stft / wpd / wpds) vs expert 0.538 / 0.479 / 0.496, W_stft 0.475, B1 0.458; all Present E4 0.679 / 0.632 / 0.645 vs
expert 0.663 / 0.627 / 0.636 (`e4_grade_sensitivity.csv`).

## 7. What it means
1. **The span-selection hypothesis from D1–D3 holds.** Restricting HSMM labels to automatically detected annotatable
   spans brings the fully automatic pipeline to the expert-label level (H9a supported for all representations; E4 ≈ D1)
   and clearly above the 2025 baseline B1 (H9b supported, +0.065 to +0.083).
2. **The deployability test (H9c) is not met for the pre-registered primary representation (wpd).** The gain over
   whole-signal STFT is +0.040, but its CI includes 0. With STFT bands (+0.058, CI > 0) and smoothed WPD (+0.045, CI
   barely > 0) it is met. Honest wording: "an automatic span-selected, cycle-aligned pipeline matches expert-label
   performance and beats the published baseline; its advantage over plain whole-signal STFT features is +0.04 to +0.06
   AUROC, significant for stft and wpds but not for the primary wpd representation."
3. **Caveats limit the claim:**
   * the detector's span choice itself separates the classes better than the expert's (0.646 vs 0.547), and missing
     features are class-related, so part of the gain may not be cardiac timing;
   * E4 was designed after E1b and D1–D3 on the same data and folds, so it is a sequentially designed result that needs
     confirmation on independent data (e.g. the CirCor test set or another cohort) before any deployment claim.
4. **Wavelet vs Fourier:** unchanged. With RF, STFT is numerically best for expert, HSMM-full and span-selected labels
   (with SMO, E4 stft and wpds tie at 0.814); WPD gives no advantage.
