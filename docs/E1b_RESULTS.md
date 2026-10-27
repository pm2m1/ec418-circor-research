# E1b_RESULTS — A standard trained segmenter (LR-HSMM) instead of the expert labels (Phase 2)

Pre-registered 2026-10-27 22:35 IST in `docs/PROTOCOL_V2_LOCKED.md` "E1b" + `configs/protocol_v2.json`
(commit `7f07b74`, tag `e1b-prereg`, pushed before any E1b code). **E1b was designed after the E1 results were known**
(E1: S1/S2 F1 0.510/0.493, all H6 NOT SUPPORTED); E1 and its segmenter are unchanged. Data: PhysioNet CirCor v1.0.3
(D1/D2), frozen folds (sha256 `c4aa74c7…2339`). **Full design ran: all 5 repeats × 5 folds** (runtime rule: estimated
0.34 CPU-h < 4 h, `results/logs/e1b_timing.json`, so no reduction). Classification finished 2026-10-27 22:50 IST,
inside the 2026-10-30 23:59 IST timebox.

| Step | Command | Output |
|---|---|---|
| features cache | `NPROC=10 python scripts/21_e1b_run.py cache` | `data/interim/e1b/springer/*.npz` (gitignored) |
| timing | `… 21_e1b_run.py time 50` | `results/logs/e1b_timing.json` |
| fold-wise segmentation + features | `… 21_e1b_run.py run 0,1,2,3,4` (220 s) | `data/interim/e1b/{features,autoseg}/` (gitignored), `results/logs/e1b_models/r<r>_f<k>.json`, `results/logs/e1b_run_folds_r01234.csv` |
| Unknown recordings | `… 21_e1b_run.py unknown` | `results/logs/e1b_models/unknown_all_binary.json` |
| segmentation metrics | `… 21_e1b_run.py evaluate` | `results/tables/e1b_segmentation_{per_recording,summary}.csv`, `results/logs/e1b_segmentation.{json,log}` |
| WEKA | `python scripts/06_run_patient_level_weka.py e1b E1b_stft_auto,E1b_wpd_auto,E1b_wpds_auto RF,SMO 8` | `results/predictions/e1b_predictions.csv` (600 jobs), `results/logs/run_e1b.log` |
| analysis | `python scripts/22_e1b_analyze.py` | `results/tables/e1b_{auroc,hypotheses,descriptive_contrasts,grade_sensitivity,feature_coverage,label_coverage}.csv`, `results/logs/e1b_analysis.{json,log}` |

## 1. Segmenter: source, licence, what is learned
* **Source:** Springer, Tarassenko & Clifford, IEEE TBME 63(4):822–832, 2016, ported to Python
  (`src/ec418/segmentation/lr_hsmm.py`) from the authors' MATLAB/C reference code, PhysioNet `hss` v1.0
  (DOI 10.13026/vnt9-kf93), **GPL-3.0**; the port is GPL-3.0 too. The Viterbi follows `viterbi_Springer.c` (the
  version the reference runs, `use_mex = true`). Existing Python code checked and not used:
  `EchoStatements/Springer-Segmentation-Python` (no licence) and `pyPCG-toolbox` 0.1b5 (GPL-3.0-only, but no training).
* **Fixed from the paper:** 1 kHz audio, order-2 25–400 Hz filtering, Schmidt spike removal, four 50 Hz features
  (homomorphic, Hilbert, 40–60 Hz PSD, rbio3.9 level-3 wavelet), per-state logistic regressions with balanced
  sampling, emission P(s|o)·N(o)/π, cyclic transitions, ±3-SD duration bounds, extended duration Viterbi.
* **Learned from the training annotations, per fold (paediatric, replaces adult defaults)** — e.g. repeat 0 / fold 0
  outer model (2,413 training recordings): mean S1 119 ms (SD 23), mean S2 105 ms (SD 23), systole SD 19 ms,
  diastole SD = 0.210·mean − 12 ms, heart-period search 0.38–0.96 s (reference: 0.5–2 s), systolic interval
  0.32–0.54·T (reference: 0.2 s–T/2). All 100 fold models + the Unknown model: `results/logs/e1b_models/`.
* **No leakage (audited):** each outer fold's test patients were decoded by a model trained only on that fold's
  training patients; training patients by cross-fitting over the 3 inner folds. All 75,175 decodes used the intended
  model (0 mismatches) and every model's training-set size equals its intended patient set. 8 unit tests
  (`tests/test_lr_hsmm.py`: features, learned parameters, held-out synthetic decoding ≥ 0.8 accuracy, cycle order,
  determinism, spike removal, short input, decoder reads no annotation); full suite 75/75 pass.

## 2. Segmentation quality vs the expert `.tsv` (inside annotated spans; definitions identical to E1)
The evaluation module (`src/ec418/segmentation/evaluation.py`) reproduces E1's published numbers exactly from E1's files.
Test-fold decodings, **repeat 0** (each recording once; Unknown recordings by the all-binary model):

| Group | Recordings | Failure | S1 P / R / **F1** | S2 P / R / **F1** | 4-state acc. | T within 10 % | swapped F1 S1/S2 |
|---|---:|---:|---|---|---:|---:|---|
| **All** | 3163 | 0 % | 0.850 / 0.873 / **0.861** | 0.811 / 0.837 / **0.824** | **0.787** | 0.765 | 0.058 / 0.065 |
| Absent | 2391 | 0 % | 0.857 / 0.888 / 0.872 | 0.813 / 0.844 / 0.828 | 0.791 | 0.767 | 0.061 / 0.070 |
| Present | 616 | 0 % | 0.852 / 0.850 / 0.851 | 0.845 / 0.847 / 0.846 | 0.795 | 0.836 | 0.033 / 0.034 |
| Unknown | 156 | 0 % | 0.626 / 0.652 / 0.639 | 0.521 / 0.558 / 0.539 | 0.598 | 0.462 | 0.144 / 0.166 |
| Neonate | 10 | 0 % | 0.857 / 0.734 / 0.791 | 0.723 / 0.632 / 0.675 | 0.638 | 0.400 | 0.124 / 0.055 |
| Infant | 269 | 0 % | 0.759 / 0.645 / 0.697 | 0.632 / 0.548 / 0.587 | 0.580 | 0.494 | 0.167 / 0.110 |
| Child | 2386 | 0 % | 0.854 / 0.880 / 0.867 | 0.826 / 0.855 / 0.840 | 0.792 | 0.790 | 0.055 / 0.063 |
| Adolescent | 259 | 0 % | 0.867 / 0.921 / 0.893 | 0.838 / 0.893 / 0.864 | 0.828 | 0.811 | 0.038 / 0.055 |
| Age missing | 239 | 0 % | 0.836 / 0.908 / 0.871 | 0.746 / 0.809 / 0.776 | 0.794 | 0.782 | 0.039 / 0.071 |

Repeats 1–4 overall: S1 F1 0.864–0.865, S2 F1 0.827–0.828, accuracy 0.790–0.791. **Not low-quality (both F1 ≥ 0.70)**
— a large improvement over E1 (0.510 / 0.493 / 0.325). The class gap seen in E1 is gone (Present 0.851 vs Absent
0.872 S1 F1). Infants remain hardest (S1 F1 0.697, S2 0.587).

## 3. Feature coverage and label coverage
* 0 decoding failures. Recordings without aligned features: at most 1 per fold (20 recording-folds in total, all
  Absent); 0 patients without aligned features in any fold.
* **Label coverage (descriptive, `e1b_label_coverage.csv`, median per binary-task recording):** the expert labels
  53.8 % of the columns (Present 59.6 %, Absent 52.0 %); E1 labels 59.8 %; **the HSMM labels 99.97 %** (it always
  decodes the whole recording). Of the columns each automatic method labels, 46 % (E1) and 46 % (E1b) lie outside the
  expert-annotated spans.

## 4. AUROC (both summaries; comparators from the same Mac run: expert = tag `e2`, B1 / W / E1 = tag `e1`)
"Mean of repeats" = mean ± SD of the 5 per-repeat AUROCs; "repeat-averaged" = AUROC of per-patient scores averaged over
repeats, with subject-bootstrap 95 % CI (used by the rule).

| Set | RF mean of repeats | RF repeat-averaged [CI] | SMO mean of repeats | SMO repeat-averaged [CI] |
|---|---|---|---|---|
| **stft auto-HSMM** | 0.702 ± 0.016 | 0.709 [0.664, 0.753] | 0.723 ± 0.011 | 0.727 [0.679, 0.772] |
| **wpd auto-HSMM** | 0.697 ± 0.011 | 0.707 [0.662, 0.749] | 0.704 ± 0.006 | 0.710 [0.663, 0.755] |
| **wpds auto-HSMM** | 0.704 ± 0.012 | 0.712 [0.670, 0.754] | 0.703 ± 0.009 | 0.710 [0.665, 0.754] |
| stft / wpd / wpds expert (E2) | 0.811 / 0.793 / 0.797 | 0.815 / 0.798 / 0.800 | 0.814 / 0.783 / 0.793 | 0.816 / 0.785 / 0.794 |
| stft / wpd / wpds auto E1 | 0.758 / 0.733 / 0.718 | 0.765 / 0.736 / 0.723 | 0.774 / 0.770 / 0.756 | 0.777 / 0.773 / 0.760 |
| B1 (Vimalajeewa '25) | 0.721 | 0.726 [0.677, 0.773] | 0.741 | 0.744 [0.698, 0.788] |
| W_stft (whole signal) | 0.744 | 0.751 [0.701, 0.794] | 0.743 | 0.747 [0.698, 0.795] |

## 5. Pre-registered hypotheses (RF primary)
| Hypothesis | Contrast | Rule | Δ repeat-averaged [95 % CI] | Δ mean of repeats | folds Δ > 0 | Verdict |
|---|---|---|---|---|---|---|
| **H8a** | wpd: HSMM − expert | Δ ≥ −0.03 | **−0.091** [−0.135, −0.045] | −0.097 | 1/25 | **NOT SUPPORTED** |
| **H8b** | wpd: HSMM − B1 | Δ > 0, CI lo > 0 | **−0.019** [−0.064, +0.029] | −0.024 | 6/25 | **NOT SUPPORTED** |
| **H8c(a)** | stft: HSMM − expert | Δ ≥ −0.03 | −0.106 [−0.148, −0.063] | −0.109 | 0/25 | **NOT SUPPORTED** |
| **H8c(b)** | stft: HSMM − B1 | Δ > 0, CI lo > 0 | −0.017 [−0.061, +0.031] | −0.019 | 11/25 | **NOT SUPPORTED** |
| **H8c(a)** | wpds: HSMM − expert | Δ ≥ −0.03 | −0.088 [−0.130, −0.045] | −0.093 | 0/25 | **NOT SUPPORTED** |
| **H8c(b)** | wpds: HSMM − B1 | Δ > 0, CI lo > 0 | −0.013 [−0.057, +0.034] | −0.017 | 10/25 | **NOT SUPPORTED** |

SMO (descriptive): HSMM − expert −0.074 / −0.090 / −0.084 and HSMM − B1 −0.034 / −0.018 / −0.034 (wpd / stft / wpds).

## 6. Descriptive comparisons (RF; SMO in `e1b_descriptive_contrasts.csv`)
| HSMM set | − W_stft [CI], folds | − W_wpd_db4 [CI], folds | − E1 auto (same rep.) [CI], folds |
|---|---|---|---|
| stft | −0.041 [−0.088, +0.010], 6/25 | +0.025 [−0.024, +0.076], 13/25 | **−0.056** [−0.103, −0.007], 3/25 |
| wpd | −0.044 [−0.089, +0.005], 4/25 | +0.022 [−0.026, +0.071], 16/25 | −0.030 [−0.074, +0.018], 7/25 |
| wpds | −0.038 [−0.084, +0.011], 4/25 | +0.028 [−0.019, +0.078], 16/25 | −0.011 [−0.055, +0.037], 9/25 |

Sensitivity at the inner-fold spec ≥ 0.80 threshold (RF, mean of repeats): grade I/VI (n = 104) 0.338 / 0.292 / 0.308
(stft / wpd / wpds) vs E1 0.417 / 0.406 / 0.390, expert 0.538 / 0.479 / 0.496, B1 0.458; all Present 0.477 / 0.445 /
0.457 vs expert 0.663 / 0.627 / 0.636.

## 7. What it means (with E2 and E1)
1. **All pre-registered E1b hypotheses are NOT SUPPORTED.** A standard trained segmenter, without leakage, does not
   recover the expert-label performance (−0.09 to −0.11 AUROC) and does not beat the 2025 baseline B1.
2. **Better segmentation did not give better classification.** The HSMM is far more accurate than E1's segmenter
   inside the annotated spans (S1/S2 F1 0.86/0.82 vs 0.51/0.49), yet its aligned features score *lower* than E1's
   (RF −0.01 to −0.06) and lower than the whole-signal STFT bands. The pipeline was checked end-to-end (features
   recomputed from the saved decodes match exactly; each fold's ARFF rows come from that fold's feature file; model
   assignment audited), so this is a result, not a bookkeeping error.
3. **What could explain it (hypotheses, not tested here):** (a) the expert labels only 54 % of each recording —
   presumably the cleaner stretches — and the true-label features pool only there, while the HSMM labels 100 % of the
   recording, so its features also pool noisy, un-annotated stretches; (b) E1's higher AUROC may partly be a shortcut —
   its segmentation quality and missing-feature rate differed by class (Present better segmented, more often dropped),
   which the HSMM does not show; (c) the HSMM forces a cycle structure through every stretch, including noise.
   Distinguishing these needs a further, separately pre-registered analysis (e.g. HSMM labels restricted to
   expert-annotated spans, which would use expert annotation coverage at test time and so be diagnostic only).
4. **Overall answer after E2, E1, E1b:** cardiac-cycle timing helps *when the expert-assisted annotation is used*
   (E2: +0.13–0.17 over timing-free controls), but **no automatic segmentation tested here turns that into a
   deployable gain** over the published baseline or over whole-signal STFT features. Wavelet vs Fourier remains
   immaterial (stft ≈ wpd ≈ wpds with HSMM labels: 0.709 / 0.707 / 0.712 RF).
