# E2_RESULTS — Does cardiac-cycle timing alignment itself help? (Phase 2, pre-registered)

> **Erratum E2-1 (2026-10-27, `docs/ERRATA_PHASE2.md`):** the `perm` null also moved ~48 % of the labels into columns the expert left unannotated, so the true − perm gap = timing **+ expert span selection** (the `shift` null moved only ~3 % and is close to a pure timing contrast). No number changes.

Run 2026-10-27 on the Mac, PhysioNet CirCor **v1.0.3** as downloaded (amendments D1, D2), frozen folds
(sha256 `c4aa74c7…2339`), protocol `docs/PROTOCOL_V2_LOCKED.md` (E2 + amendment I1, all committed before the run).
Every number below comes from:

| Step | Command | Output |
|---|---|---|
| features | `NPROC=10 python scripts/15_e2_extract_label_nulls.py` | `data/processed/e2/rec_features_E2_<rep>_<labels>.csv`, `label_null_log.csv`, `results/logs/e2_feature_extraction.log` |
| WEKA | `python scripts/06_run_patient_level_weka.py e2 E2_{stft,wpd,wpds}_{true,perm,shift} RF,SMO 8` | `results/predictions/e2_predictions.csv` (1,800 jobs, 58 s), `results/logs/run_e2.log`, `weka_e2_jvm*.log` |
| analysis | `python scripts/16_e2_analyze.py e2` | `results/tables/e2_auroc.csv`, `e2_contrasts.csv`, `e2_equivalence.csv`, `e2_true_arm_vs_v1.csv`, `results/logs/e2_analysis.{json,log}` |

## Design (unchanged from the lock)
Same preprocessing, energy maps and 34 cycle-aligned feature definitions as v1; only the per-column
S1/systole/S2/diastole labels change: `true` (expert `.tsv`), `perm` (primary null: labels permuted within each
recording, seed crc32(rec_id) — same label counts, no timing), `shift` (secondary null: circular shift by u·T,
u ~ U(0.2, 0.8), T = median S1-to-S1 interval — contiguity kept, wrong phase). Representations `stft`, `wpd` (raw db4)
and `wpds` (db4 smoothed with the 4-tap Hann). Patient vector = median + max over recordings (68 dims). RF primary,
SMO secondary. 874 patients (179 Present / 695 Absent), 816 subjects, 5 × 5 subject-grouped outer folds.

**Recording 50782_MV_1 has no aligned features in every condition** (all 9 sets): its v1.0.3 `.tsv` is the degenerate
6-byte file `0 0 28` (D2), so it has no annotated columns under `true`, and `perm`/`shift` of an all-unannotated
label vector are still all-unannotated. Patient 50782 keeps features from its other 5 recordings. No other recording
lacks aligned features; 0 extraction errors; no patient lacks all features.

**Sanity check (true arm vs v1):** the `true` features equal the frozen v1 `A_stft`, `A_wpd_db4`, `A_wpd_db4_smooth`
features to ≤ 5.1e-13 with the same NaN pattern, and RF AUROCs agree with v1 to ≤ 0.0002
(`e2_true_arm_vs_v1.csv`).

## AUROC (two summaries, both reported)
* **Mean of repeats** = mean ± SD over the 5 repeats of the per-repeat patient AUROC.
* **Repeat-averaged** = AUROC of each patient's score averaged over the 5 repeats, with subject-bootstrap 95 % CI
  (2,000 resamples). The decision rule uses this one.

| RF | true | perm | shift |
|---|---|---|---|
| stft — mean of repeats | 0.811 ± 0.007 | 0.636 ± 0.005 | 0.607 ± 0.017 |
| stft — repeat-averaged [CI] | 0.815 [0.772, 0.853] | 0.642 [0.592, 0.690] | 0.613 [0.564, 0.659] |
| wpd — mean of repeats | 0.793 ± 0.008 | 0.642 ± 0.005 | 0.601 ± 0.009 |
| wpd — repeat-averaged [CI] | 0.798 [0.753, 0.838] | 0.651 [0.604, 0.700] | 0.606 [0.557, 0.654] |
| wpds — mean of repeats | 0.797 ± 0.010 | 0.661 ± 0.006 | 0.592 ± 0.009 |
| wpds — repeat-averaged [CI] | 0.800 [0.756, 0.839] | 0.669 [0.618, 0.717] | 0.595 [0.542, 0.642] |

| SMO (secondary) | true | perm | shift |
|---|---|---|---|
| stft — mean of repeats / repeat-averaged | 0.814 / 0.816 | 0.556 / 0.581 | 0.541 / 0.564 |
| wpd — mean of repeats / repeat-averaged | 0.783 / 0.785 | 0.562 / 0.600 | 0.517 / 0.532 |
| wpds — mean of repeats / repeat-averaged | 0.793 / 0.794 | 0.556 / 0.596 | 0.509 / 0.520 |

## Pre-registered hypotheses (RF; rule: Δ ≥ 0.03 AND CI lower bound > 0 AND Δ > 0 in ≥ 18/25 folds)
| Hypothesis | Contrast | Δ repeat-averaged [95 % CI] | Δ mean of repeats | folds Δ > 0 | Verdict |
|---|---|---|---|---|---|
| **H5a** | wpd: true − perm | **+0.147** [+0.094, +0.199] | +0.151 | 25/25 | **SUPPORTED** |
| **H5b** | stft: true − perm | **+0.174** [+0.115, +0.229] | +0.176 | 25/25 | **SUPPORTED** |
| **H5c** | wpds: true − perm | **+0.131** [+0.079, +0.185] | +0.135 | 25/25 | **SUPPORTED** |
| H5d (secondary) | wpd: true − shift | +0.192 [+0.141, +0.248] | +0.192 | 25/25 | SUPPORTED |
| H5d (secondary) | stft: true − shift | +0.202 [+0.152, +0.254] | +0.204 | 25/25 | SUPPORTED |
| H5d (secondary) | wpds: true − shift | +0.206 [+0.153, +0.260] | +0.205 | 25/25 | SUPPORTED |

SMO (descriptive only): true − perm +0.184 / +0.235 / +0.198 and true − shift +0.253 / +0.252 / +0.274 for
wpd / stft / wpds, all CIs > 0, 25/25 folds.

## Equivalence report: wpds vs stft (aligned, true labels)
| clf | Δ (wpds − stft) repeat-averaged [95 % CI] | Δ mean of repeats | folds Δ > 0 | CI within ±0.03? |
|---|---|---|---|---|
| RF | −0.0147 [−0.0321, +0.0026] | −0.0149 | 5/25 | **No** |
| SMO (descriptive) | −0.0222 [−0.0408, −0.0044] | −0.0219 | 2/25 | No |

**Equivalence is NOT shown**: the RF CI's lower end (−0.032) lies just outside −0.03, so "no meaningful difference"
may not be claimed. The point estimate favours STFT; the CI does not exclude 0 for RF (it does for SMO).

## What this means for the research question
*Does cardiac-cycle timing alignment improve patient-independent murmur detection, and does the wavelet-vs-Fourier
choice matter once alignment is controlled?*

1. **Timing matters (all three primary hypotheses supported).** With feature definitions, normalisation, label counts
   and annotation coverage held fixed, destroying the timing of the S1/systole/S2/diastole labels costs 0.13–0.17
   AUROC (RF) for every representation, in all 25 folds; wrong-phase but contiguous labels (`shift`) cost 0.19–0.21.
   This answers the open question in `docs/ERRATA_v1.md` #1/#5 and `docs/GO_NO_GO.md`: the v1 gain of the cycle-aligned
   pipeline is **not** explained by feature definitions/normalisation alone — physiological timing carries most of it.
   The pre-registered fallback interpretation ("attributed to feature definitions, not timing") is therefore not used.
2. **The nulls are not chance.** `perm` still reaches 0.64–0.67 (RF) and `shift` 0.59–0.61: band-energy ratios
   computed over arbitrary column subsets keep some spectral information. They are lower than v1's whole-signal sets
   (W_stft 0.744, W_wpd_db4 0.678 RF mean of repeats), so "true − perm" (this experiment) and "aligned − whole" (v1,
   different statistics) are different contrasts and should not be added or compared directly. `shift` < `perm` is
   consistent with the pre-registered caveat that shifts near 0.5·T partly swap systole and diastole.
3. **The wavelet choice does not help once alignment is controlled.** Under true labels STFT is numerically best
   (RF 0.815 vs wpd 0.798, wpds 0.800); wpds − stft = −0.015 with a CI that just fails the ±0.03 equivalence margin.
   Honest wording: "no evidence that wavelet packets improve on matched Fourier bands; equivalence within ±0.03 is
   not demonstrated (CI −0.032 … +0.003)". This matches v1 (H2a −0.017, NOT SUPPORTED; post-hoc smoothing −0.0147).
4. **Caveat — still oracle segmentation.** All `true` results use the dataset's expert-assisted `.tsv`; E2 shows that
   *correct* timing helps, not that it is obtainable automatically. That is E1 (not started, per instructions).
