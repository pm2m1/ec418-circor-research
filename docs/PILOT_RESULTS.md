# PILOT_RESULTS — real-data experiments actually executed (2026-10-27)

Everything below was run in this repository on the 942-patient CirCor public training set.
Unit of analysis: **patient** (874 patients, 179 Present / 695 Absent, 816 subjects), unless stated.
Splits: frozen subject-grouped 5-fold × 5 repeats (`configs/folds_patient_level.csv`). Classifiers: WEKA 3.9.7.
"± sd" = across the 5 repeats (not independent samples). CI = 95 % subject bootstrap (2000 resamples) on
repeat-averaged scores. Present is the positive class everywhere. **These are public-set cross-validation
results; they are not comparable to the Challenge hidden-test leaderboard (0.780 weighted accuracy).**

## 0. Pipeline checks
* 39/39 pytest tests pass (`results/logs/pytest_latest.txt`): wavelet band math & ordering, Parseval,
  reconstruction, anti-alias, filters, flat/empty inputs, missing segmentation, label mapping, subject
  linkage, leakage assertions, fold determinism, ARFF headers & ID guard, confusion-matrix order,
  sensitivity/specificity formulas, official weighted accuracy, WEKA end-to-end, exact baseline DWT port.
* 100 split-integrity checks pass; every repeat tests each of the 874 patients exactly once.
* Feature extraction: 3163/3163 recordings, 0 errors, 165 s on 2 cores (all 11 band/acoustic feature sets).
* WEKA: 3,200 train/test jobs (main 2,400 + wavelet sensitivity 600 + post-hoc 200) completed;
  train/test headers identical; row→patient alignment asserted on every prediction file.

## 1. H1 — does correcting the split change the published baseline? (`scripts/05_h1_leakage_b1.py`)
| Protocol (B1 features, paper's SVM) | Recording AUC | Present recall | Absent recall |
|---|---|---|---|
| A: random recording split (paper), 25 seeds | 0.738 ± 0.017 | 0.541 | 0.828 |
| B: subject-grouped CV, 25 folds | 0.724 ± 0.048 | 0.519 | 0.822 |
ΔAUC +0.015 (indicative CI −0.004…+0.035) → **H1 NOT SUPPORTED.** Patient leakage is real (95.8 % of test
patients have recordings in training under protocol A) but does not materially inflate *this* feature set.
The baseline's problems are elsewhere (feature misalignment, metric labelling — `docs/BASELINE_AUDIT.md`).

## 2. Main study: patient-level WEKA Random Forest (primary classifier)
Operating point "spec80" = threshold chosen on **inner** training OOF scores to give specificity ≥ 0.80.
"wAcc-op" = threshold maximising inner-OOF official weighted accuracy (sens/spec in brackets).

| Feature set | dims | AUROC (mean of 5 repeats ± sd) | AUROC 95 % CI (repeat-averaged scores) | AUPRC | Acc | Sens | Spec | Prec | F1 | macro-F1 | wAcc-op |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A_stft — STFT bands, cycle-aligned | 68 | **0.812 ± 0.007** | 0.771–0.852 | 0.664 | 0.780 | 0.664 | 0.810 | 0.474 | 0.553 | 0.703 | 0.720 (0.67/0.78) |
| **P1 A_wpd_db4 — WPD, cycle-aligned (proposed)** | 68 | **0.793 ± 0.008** | 0.753–0.838 | 0.641 | 0.772 | 0.626 | 0.809 | 0.458 | 0.529 | 0.689 | 0.707 (0.66/0.77) |
| W_stft — STFT bands, whole signal | 68 | 0.744 ± 0.010 | 0.701–0.795 | 0.546 | 0.761 | 0.574 | 0.809 | 0.436 | 0.496 | 0.669 | 0.675 (0.63/0.73) |
| B0 — MFCC + spectral descriptors | 36 | 0.743 ± 0.005 | 0.699–0.793 | 0.522 | 0.765 | 0.572 | 0.815 | 0.443 | 0.499 | 0.673 | 0.674 (0.65/0.71) |
| B1 — Vimalajeewa 2025 wavelet features (corrected) | 16 | 0.721 ± 0.008 | 0.677–0.773 | 0.524 | 0.760 | 0.550 | 0.814 | 0.432 | 0.484 | 0.664 | 0.645 (0.57/0.74) |
| W_wpd_db4 — WPD, whole signal | 68 | 0.678 ± 0.013 | 0.637–0.732 | 0.435 | 0.732 | 0.451 | 0.805 | 0.373 | 0.409 | 0.618 | 0.613 (0.65/0.57) |

**Two AUROC summaries — do not mix them.** Column 3 is the mean of the five per-repeat pooled AUROCs.
The CI column is a subject bootstrap on *repeat-averaged* patient scores; the point estimate of that
second summary is slightly higher (A_stft 0.815, P1 0.798, W_stft 0.751, B0 0.747, B1 0.726,
W_wpd 0.685; `auroc_avgscore` in `results/tables/main_metrics.csv`, and the AUCs in fig 8). An external
reviewer recomputed exactly these six values from the saved prediction files.

Prevalence (AUPRC chance level) = 0.205. Specificity lands at 0.80–0.82 on test folds, so the
train-derived thresholds transfer; nothing was tuned on test data.

### Same comparison, all four WEKA classifiers (patient AUROC, mean of 5 repeats)
| Set | RF | SMO (linear) | Logistic | MLP |
|---|---|---|---|---|
| A_stft | 0.812 | 0.815 | 0.808 | 0.780 |
| P1 A_wpd_db4 | 0.793 | 0.783 | 0.762 | 0.746 |
| B0 | 0.743 | 0.768 | 0.766 | 0.719 |
| W_stft | 0.744 | 0.743 | 0.733 | 0.722 |
| B1 | 0.721 | 0.741 | 0.739 | 0.708 |
| W_wpd_db4 | 0.678 | 0.680 | 0.688 | 0.680 |
Ranking is stable across classifiers: cycle-aligned sets first, B1 and whole-signal WPD last.

## 3. Pre-registered hypotheses (RF; rule: Δ ≥ 0.03, CI > 0, ≥ 18/25 folds positive)
| Hypothesis | ΔAUROC | 95 % CI | folds + | Verdict |
|---|---|---|---|---|
| H2a WPD > STFT (aligned) | **−0.017** | −0.034…−0.000 | 3/25 | **NOT SUPPORTED (opposite direction)** |
| H2b WPD > STFT (whole) | **−0.066** | −0.095…−0.036 | 1/25 | **NOT SUPPORTED (opposite direction)** |
| H3 aligned *pipeline* > whole *pipeline* (WPD) ¹ | **+0.113** | +0.065…+0.165 | 25/25 | **SUPPORTED** |
| H4a P1 > B0 | +0.051 | −0.002…+0.102 | 21/25 | NOT SUPPORTED (CI touches 0) |
| H4b P1 > B1 (2025 journal baseline) | **+0.072** | +0.027…+0.122 | 24/25 | **SUPPORTED** |
| aux: aligned *pipeline* > whole *pipeline* (STFT) ¹ | +0.065 | +0.020…+0.109 | 24/25 | supported (not pre-declared as H) |
The other three classifiers give the same signs (`results/tables/contrasts.csv`).

¹ **H3 does not isolate alignment.** The whole-signal and aligned extractors compute *different*
statistics (whole: relative band energy, q90/q50 burstiness, entropy; aligned: systolic energy / S1
energy, systolic / diastolic ratio, entropies). The +0.11 therefore combines (i) choosing physiological
intervals, (ii) different feature definitions and (iii) normalisation against heart sounds. Isolating
(i) is Experiment E2 in `docs/PROTOCOL_V2_LOCKED.md`.

**Plain reading:** the **cycle-aligned feature pipeline** gives the measurable improvement; the
wavelet transform does not. With identical nominal bands, column grid and dimensionality — but not
identical effective time resolution (decimated packets vs 64-sample Hann frames) — wavelet packets were
never better than the short-time Fourier transform. Which ingredient of the aligned pipeline carries the
gain is not yet established.

## 4. Mother-wavelet sensitivity (RF, descriptive only — not used to pick a winner)
| Aligned | db4 0.793 | db6 0.795 | sym8 0.799 | coif3 0.779 | (STFT 0.812) |
|---|---|---|---|---|---|
| **Whole** | db4 0.678 | db6 0.679 | sym8 0.677 | coif3 0.672 | (STFT 0.744) |
Spread across wavelets ≤ 0.02 → the choice of mother wavelet is not what limits WPD. Filter
leakage (fig 7) is therefore an unlikely explanation for the STFT advantage.

## 5. Post-hoc amendment A1 (exploratory, logged in PROTOCOL Amendments)
Mechanism test: one squared decimated packet coefficient per 8 ms is a ~1-degree-of-freedom energy
estimate; the STFT frame averages a 64-sample window. Smoothing the WPD energy map with the same
64-sample Hann kernel:
| | raw WPD | smoothed WPD | STFT | Δ(smoothed − STFT), 95 % CI |
|---|---|---|---|---|
| whole | 0.678 | **0.739** | 0.744 | −0.007 (−0.025…+0.009) |
| aligned | 0.793 | 0.796 | 0.812 | −0.015 (−0.032…+0.003) |
→ Under the tested implementations, smoothing removed most of the whole-signal WPD deficit, which is
consistent with an **estimator-variance** explanation; after smoothing, WPD and STFT were not
distinguishable (CIs include 0). This is exploratory evidence designed after seeing H2, **not** proof that
the two transforms are equivalent.

## 6. Where the models fail (RF, spec80 operating point, mean over repeats)
| Present subgroup | n | A_stft | P1 | B0 | B1 |
|---|---|---|---|---|---|
| Grade I/VI | 104 | 0.54 | 0.48 | 0.48 | 0.46 |
| Grade II/VI | 28 | 0.59 | 0.57 | 0.56 | 0.37 |
| Grade III/VI | 46 | 1.00 | 1.00 | 0.81 | 0.87 |
| Low pitch | 87 | 0.41 | 0.35 | 0.37 | 0.26 |
| Medium pitch | 49 | 0.86 | 0.81 | 0.67 | 0.71 |
| High pitch | 42 | 0.98 | 0.98 | 0.88 | 0.97 |
Loud and high/medium-pitch murmurs are found almost always; **soft (I/VI) and low-pitch murmurs are
missed about half the time** — they overlap S1/S2 energy below ~150 Hz (fig 6). This is the clinically
important weakness.

## 7. Exploratory signal-quality analysis (`scripts/09_quality_exploratory.py`)
* Separating Unknown patients from Present/Absent (single index, a-priori orientation, AUROC):
  spectral-ratio gate (20–200 / 0–1000 Hz) **0.779**; wavelet envelope periodicity 0.689; 25–400 Hz band
  fraction 0.716; clipping 0.608; HF kurtosis 0.285 (wrong-signed a priori → fails).
  **The proposed wavelet SQI does not beat the simple spectral baseline.**
* Selective prediction (P1, drop lowest-quality patients): AUROC 0.793 → 0.808 at 80 % coverage while
  rejecting 13 % of murmur patients. Not worth it. → **Quality gating dropped from scope.**

## 8. Cost
WEKA fit (outer fold, ~700 patients): RF ≈ 0.9 s, SMO ≈ 0.1 s, Logistic ≈ 0.03 s, MLP ≈ 5 s;
prediction < 0.2 ms per patient. Features ≈ 50 ms per recording on one core for all sets.
No GPU is needed; an M5 Pro will be faster than this 2-core VM.

## 9. What these results do and do not show
* They **do** show, under a leakage-controlled patient-level protocol, that the cycle-aligned band-energy
  pipeline beats the published 2025 wavelet baseline (P1 vs B1: +0.072 AUROC, CI excludes 0). The two
  differ in features, aggregation and segmentation use, so this is a pipeline-vs-pipeline result.
* They **do not** yet show that *timing alignment itself* causes the gain (see footnote ¹).
* They **do not** show that wavelets beat Fourier analysis (they do not), nor anything about deployment:
  every aligned result uses the dataset's expert-assisted segmentation (**oracle**).
* Not validated on the hidden test set, on another hospital/device, or against the clinical Outcome.
