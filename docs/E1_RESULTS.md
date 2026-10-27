# E1_RESULTS — Does the aligned-feature gain survive without the expert segmentation? (Phase 2, pre-registered)

Run 2026-10-27 on the Mac, PhysioNet CirCor **v1.0.3** as downloaded (amendments D1, D2), frozen folds
(sha256 `c4aa74c7…2339`), protocol `docs/PROTOCOL_V2_LOCKED.md` "E1" with **all segmenter constants unchanged** and
amendment I2 (implementation details + analysis plan) committed after the segmentation metrics and **before** the
classification run. **Flag: low-quality segmentation (S1 F1 0.510, S2 F1 0.493 < 0.70)** — results are reported as
pre-registered.

| Step | Command | Output |
|---|---|---|
| segment + evaluate | `NPROC=10 python scripts/18_e1_autosegment.py` | `data/interim/autoseg/*.tsv` (gitignored), `results/tables/e1_segmentation_{per_recording,summary}.csv`, `results/logs/e1_segmentation.{json,log}` |
| features | `NPROC=10 python scripts/19_e1_extract_auto_features.py` | `data/processed/e1/rec_features_E1_<rep>_auto.csv`, `seg_coverage_auto.csv`, `results/logs/e1_feature_coverage.json` |
| WEKA | `python scripts/06_run_patient_level_weka.py e1 E1_stft_auto,E1_wpd_auto,E1_wpds_auto,B1,W_stft,W_wpd_db4 RF,SMO 8` | `results/predictions/e1_predictions.csv` (1,200 jobs, 32 s), `results/logs/run_e1.log`, `weka_e1_jvm*.log` |
| analysis | `python scripts/20_e1_analyze.py` | `results/tables/e1_{auroc,hypotheses,vs_whole_signal,grade_sensitivity}.csv`, `results/logs/e1_analysis.{json,log}` |

`true` = `E2_<rep>_true` (tag `e2`, expert labels). B1, W_stft, W_wpd_db4 were rerun in tag `e1` on the committed
features; their predictions are bit-identical to tag `repro_mac`.

## 1. Segmenter (`src/ec418/segmentation/autoseg.py`, 15 unit tests)
Pure function of the preprocessed signal (no expert `.tsv`, murmur label or metadata; a test checks the source).
Homomorphic envelope of 25–400 Hz (|Hilbert| → log → 8 Hz low-pass → exp, 50 Hz); T = highest local maximum of the
envelope autocorrelation in [0.3, 1.5] s; peaks ≥ 0.2·T apart and ≥ 25th percentile; non-overlapping interval pairs,
shorter = systole; S1/S2 extent ≥ 50 % of peak clipped to 40–160 ms; labels mapped to the level-4 WPD column grid
with the same `column_labels` as the expert annotation (output length = WPD grid, tested). Flat, very short or
non-finite input → all-zero labels (tested).

**Two properties found by the unit tests (constants left unchanged, per protocol):**
* Noise sensitivity: a noise-free synthetic PCG (S1/S2 every 0.8 s) is segmented correctly (T = 0.80 s, S1 hit rate
  1.00, S2 0.96), but adding white noise at only 0.1 % of the sound amplitude already adds envelope peaks inside
  diastole (S1/S2 hit rates 0.24/0.24; 0.16–0.20 at 0.5 %, ≈ 0–0.08 at 2–5 %). The log step makes the envelope
  scale-free, so noise bumps pass the 25th-percentile / 0.2·T peak rule.
* No periodicity gate: irregular rhythms are not forced to all-zero labels (the test checks only that they do not
  crash and give well-formed labels).

## 2. Segmentation quality vs the expert `.tsv` (inside expert-annotated spans)
Centre F1 at ±50 ms (pooled), frame-wise 4-state accuracy on the 8 ms grid, failure = no segments. The evaluation
code scores the expert annotation against itself at F1 = 1.000 and accuracy = 1.000 (200-recording check).

| Group | Recordings | Failure | S1 P / R / **F1** | S2 P / R / **F1** | 4-state acc. | T within 10 % | T ≈ T/2 | S1/S2 swapped F1 |
|---|---:|---:|---|---|---:|---:|---:|---|
| **All** | 3163 | 0.3 % (11) | 0.556 / 0.471 / **0.510** | 0.535 / 0.458 / **0.493** | **0.325** | 0.689 | 0.063 | 0.191 / 0.184 |
| Absent | 2391 | 0.3 % (6) | 0.547 / 0.465 / 0.503 | 0.533 / 0.457 / 0.492 | 0.316 | 0.682 | 0.073 | 0.202 / 0.194 |
| Present | 616 | 0.2 % (1) | 0.599 / 0.501 / 0.546 | 0.555 / 0.471 / 0.509 | 0.363 | 0.800 | 0.018 | 0.145 / 0.143 |
| Unknown | 156 | 2.6 % (4) | 0.489 / 0.386 / 0.431 | 0.452 / 0.370 / 0.407 | 0.275 | 0.355 | 0.079 | 0.245 / 0.216 |
| Neonate | 10 | 0 % | 0.789 / 0.511 / 0.620 | 0.527 / 0.360 / 0.428 | 0.374 | 0.400 | 0.000 | 0.302 / 0.150 |
| Infant | 269 | 0.4 % (1) | 0.559 / 0.363 / 0.440 | 0.495 / 0.326 / 0.393 | 0.257 | 0.373 | 0.000 | 0.290 / 0.264 |
| Child | 2386 | 0.4 % (10) | 0.572 / 0.484 / 0.524 | 0.555 / 0.473 / 0.511 | 0.334 | 0.729 | 0.056 | 0.182 / 0.176 |
| Adolescent | 259 | 0 % | 0.483 / 0.445 / 0.463 | 0.462 / 0.431 / 0.446 | 0.302 | 0.707 | 0.097 | 0.208 / 0.207 |
| Age missing | 239 | 0 % | 0.485 / 0.442 / 0.463 | 0.460 / 0.424 / 0.441 | 0.306 | 0.647 | 0.164 | 0.201 / 0.190 |

(Age = v1.0.3 categories. "T within 10 %" / "T ≈ T/2" compare the automatic period with the median S1-onset interval of
the expert rows; "swapped F1" scores auto S2 against expert S1 and vice versa.)

* **Low-quality segmentation flag: S1 F1 0.510 and S2 F1 0.493 are both < 0.70.** All 11 failures are "no
  autocorrelation peak in range".
* The period is right in 69 % of recordings and S1/S2 are not systematically swapped (swapped F1 ≈ 0.19), so most
  errors are spurious or missed peaks (consistent with the noise sensitivity in §1).
* Quality is worst for infants (period right in 37 %; higher heart rates) and **differs by class: better for
  Present (S1 F1 0.546, period 0.800) than Absent (0.503, 0.682).** A class-dependent segmentation quality is a
  possible shortcut and a confound for the auto-aligned features.

## 3. Feature coverage with auto labels
0 extraction errors. **90 / 3163 recordings have no aligned features** (below the v1 minimum of 40 systolic, 40
diastolic and 10 S1 columns; identical for stft / wpd / wpds): 79 in the binary task (35 Present, 44 Absent — 5.7 % of
Present vs 1.8 % of Absent recordings), 11 Unknown. **0 / 874 binary-task patients lack aligned features entirely**
(each keeps ≥ 1 recording); WEKA sees the dropped recordings only through the median/max aggregation. Under expert
labels only 50782_MV_1 lacked aligned features.

## 4. AUROC (both summaries)
"Mean of repeats" = mean ± SD of the 5 per-repeat patient AUROCs; "repeat-averaged" = AUROC of each patient's score
averaged over repeats, with subject-bootstrap 95 % CI (used by the rule).

| Set | RF mean of repeats | RF repeat-averaged [CI] | SMO mean of repeats | SMO repeat-averaged [CI] |
|---|---|---|---|---|
| **stft auto** | 0.758 ± 0.012 | 0.765 [0.723, 0.807] | 0.774 ± 0.006 | 0.777 [0.734, 0.817] |
| **wpd auto** | 0.733 ± 0.006 | 0.736 [0.691, 0.781] | 0.770 ± 0.006 | 0.773 [0.730, 0.812] |
| **wpds auto** | 0.718 ± 0.007 | 0.723 [0.677, 0.767] | 0.756 ± 0.002 | 0.760 [0.719, 0.800] |
| stft true (E2) | 0.811 ± 0.007 | 0.815 [0.772, 0.853] | 0.814 ± 0.005 | 0.816 [0.774, 0.856] |
| wpd true (E2) | 0.793 ± 0.008 | 0.798 [0.753, 0.838] | 0.783 ± 0.007 | 0.785 [0.736, 0.829] |
| wpds true (E2) | 0.797 ± 0.010 | 0.800 [0.756, 0.839] | 0.793 ± 0.006 | 0.794 [0.746, 0.837] |
| B1 (Vimalajeewa '25) | 0.721 ± 0.009 | 0.726 [0.677, 0.773] | 0.741 ± 0.010 | 0.744 [0.698, 0.788] |
| W_stft (whole signal) | 0.744 ± 0.010 | 0.751 [0.701, 0.794] | 0.743 ± 0.008 | 0.747 [0.698, 0.795] |
| W_wpd_db4 (whole signal) | 0.678 ± 0.014 | 0.685 [0.637, 0.732] | 0.680 ± 0.013 | 0.687 [0.633, 0.737] |

## 5. Pre-registered hypotheses (RF primary)
| Hypothesis | Contrast | Rule | Δ repeat-averaged [95 % CI] | Δ mean of repeats | folds Δ > 0 | Verdict |
|---|---|---|---|---|---|---|
| **H6a** | wpd: auto − true | Δ ≥ −0.03 | **−0.062** [−0.102, −0.021] | −0.060 | 3/25 | **NOT SUPPORTED** |
| **H6b** | wpd: auto − B1 | Δ > 0, CI lo > 0 | **+0.010** [−0.038, +0.060] | +0.012 | 15/25 | **NOT SUPPORTED** |
| **H6c(a)** | stft: auto − true | Δ ≥ −0.03 | −0.050 [−0.090, −0.011] | −0.053 | 1/25 | **NOT SUPPORTED** |
| **H6c(b)** | stft: auto − B1 | Δ > 0, CI lo > 0 | +0.039 [−0.009, +0.088] | +0.037 | 20/25 | **NOT SUPPORTED** |
| **H6c(a)** | wpds: auto − true | Δ ≥ −0.03 | −0.077 [−0.120, −0.037] | −0.079 | 1/25 | **NOT SUPPORTED** |
| **H6c(b)** | wpds: auto − B1 | Δ > 0, CI lo > 0 | −0.003 [−0.051, +0.047] | −0.003 | 12/25 | **NOT SUPPORTED** |

All under the low-quality-segmentation flag. SMO (descriptive): auto − true −0.012 / −0.039 / −0.034 (wpd / stft / wpds;
wpd would meet the −0.03 margin, CIs include 0); auto − B1 +0.028 / +0.033 / +0.015, all CIs include 0.

## 6. Descriptive: auto vs whole-signal sets (RF; SMO in `e1_vs_whole_signal.csv`)
| auto set | − W_stft [CI], folds | − W_wpd_db4 [CI], folds |
|---|---|---|
| stft auto | +0.014 [−0.030, +0.062], 16/25 | +0.080 [+0.032, +0.131], 24/25 |
| wpd auto | −0.015 [−0.059, +0.032], 11/25 | +0.051 [+0.004, +0.102], 22/25 |
| wpds auto | −0.028 [−0.074, +0.019], 8/25 | +0.038 [−0.007, +0.088], 22/25 |

With automatic labels no aligned set is better than the best whole-signal set (W_stft); they beat only W_wpd_db4.
SMO shows the same picture (vs W_stft +0.013 … +0.030, CIs include 0). For context (not a v2 rule): Mac B0 RF is
0.743 mean of repeats (`repro_mac_auroc_comparison.csv`) — stft auto is above it, wpd and wpds auto below.

## 7. Descriptive: sensitivity by systolic murmur grade (RF, inner-fold spec ≥ 0.80 threshold, mean of repeats)
| Grade (n Present) | stft auto | wpd auto | wpds auto | stft true | wpd true | wpds true | B1 | W_stft | W_wpd_db4 |
|---|---|---|---|---|---|---|---|---|---|
| **I/VI (104)** | 0.417 | 0.406 | 0.390 | 0.538 | 0.479 | 0.496 | 0.458 | 0.475 | 0.385 |
| II/VI (28) | 0.514 | 0.464 | 0.379 | 0.593 | 0.564 | 0.579 | 0.386 | 0.521 | 0.364 |
| III/VI (46) | 0.957 | 0.883 | 0.870 | 1.000 | 1.000 | 1.000 | 0.874 | 0.852 | 0.661 |
| all Present (179) | 0.569 | 0.535 | 0.509 | 0.663 | 0.627 | 0.636 | 0.551 | 0.577 | 0.450 |

(One Present patient has no systolic grade; omitted.) Soft (grade I/VI) murmurs suffer most: auto labels give
0.39–0.42, below both the expert-label sets (0.48–0.54) and B1 (0.46).

## 8. What E1 means, together with E2
1. **E2:** with correct (expert) timing, cycle alignment adds 0.13–0.17 AUROC over timing-free controls with identical
   features — timing carries the v1 aligned-pipeline gain.
2. **E1:** with the pre-registered simple segmenter (S1/S2 F1 ≈ 0.50, flagged low quality) the aligned features lose
   0.05–0.08 AUROC against expert labels (H6a, H6c(a) NOT SUPPORTED) and are **not** demonstrably better than the
   2025 baseline B1 (H6b, H6c(b) NOT SUPPORTED; best case stft +0.039, CI −0.009 … +0.088) or than whole-signal STFT
   bands. They still score above E2's timing-free `perm` controls (RF 0.72–0.77 vs 0.64–0.67), so automatic labels
   recover part of the timing information.
3. **Conclusion for the research question:** the benefit of cardiac-cycle alignment is real but, in this study,
   **depends on segmentation quality — it is demonstrated only with expert-assisted (oracle) segmentation.** A
   deployable improvement over the published baseline is not shown. Because the segmenter is weak (and its quality
   differs between Present and Absent), E1 does not show that automatic alignment *cannot* work — only that this
   pre-registered segmenter is not good enough. A better segmenter (e.g. Springer's HSMM) would be a new,
   separately pre-registered experiment; nothing here was tuned.
4. **Wavelet vs Fourier:** unchanged — STFT is numerically best with expert labels (E2) and with automatic labels
   (stft 0.765 > wpd 0.736 > wpds 0.723 RF); no evidence for a wavelet advantage.
