# RESULTS_SUMMARY — EC418 CirCor study, final (tag `results-final`)

PhysioNet CirCor DigiScope v1.0.3 (training set, 942 patients / 3,163 recordings; binary task 874 patients, 179 Present /
695 Absent, 816 subjects), frozen subject-grouped folds (5 repeats × 5 folds, sha256 `c4aa74c7…2339`), WEKA 3.9.7
(RF primary, SMO secondary), patient-level AUROC. Phase 1 = tag `v1.0-pilot` (Linux), Phase 2 = this Mac (OpenJDK 21,
Python 3.12). Every number below is copied from a saved table by `scripts/32_results_summary.py`
(`results/tables/final_hypotheses.csv`, `final_decomposition.csv`). Δ = AUROC of repeat-averaged patient scores, CI =
subject bootstrap (2000 resamples). Detail: `docs/PILOT_RESULTS.md`, `E2_RESULTS.md`, `E1_RESULTS.md`, `E1b_RESULTS.md`,
`D_DIAGNOSTICS.md`, `E4_RESULTS.md`, `S1_SHORTCUT.md`, `ERRATA_v1.md`, `ERRATA_PHASE2.md`, `REPRO_MAC.md`,
`PROVENANCE_PHYSIONET.md`.

## Headline answers
1. **Does cardiac-cycle timing help?** Yes, with expert-assisted segmentation: aligned features beat timing-free controls
   by +0.13 to +0.21 AUROC (H5a–d). The diagnostics show this gain is all timing (within-span timing +0.17 to +0.19),
   not the expert's choice of spans.
2. **Does it survive automatic segmentation?** Not with either segmenter alone (E1: envelope peaks; E1b: LR-HSMM; all H6/H8
   NOT SUPPORTED). The HSMM's timing is near-expert inside clean spans (D1). What is missing is span selection.
3. **With an automatic span selector (E4)** the pipeline reaches expert-label performance (H9a) and beats the 2025 baseline B1
   (H9b). Its advantage over whole-signal STFT (H9c) is significant for stft and wpds, but **not for the pre-registered
   primary wpd**. **Once whole-signal STFT is given the same span/missingness information (S1), E4's advantage is "possibly
   shortcut-driven"** for all three representations (+0.026 to +0.043, CIs include 0). A deployable gain over a
   shortcut-aware STFT baseline is therefore not established.
4. **Wavelet vs Fourier:** no wavelet advantage anywhere. WPD ≤ matched STFT under every labelling
   (`results/tables/final_wavelet_vs_stft.csv`), and equivalence within ±0.03 is not shown (CI −0.032…+0.003).

## Every pre-registered hypothesis (RF)
| Experiment | Hypothesis | Contrast (RF) | Rule | Δ AUROC [95 % CI] | Folds Δ > 0 | Verdict |
|---|---|---|---|---|---|---|
| v1 | H1 | B1+SVM recording AUC: random split - subject-grouped | material inflation (v1 PILOT_RESULTS §1) | +0.015 [-0.004, +0.035] | n/a | NOT SUPPORTED |
| v1 | H2a | A\_wpd\_db4 - A\_stft | delta>=0.03, CI lo>0, >=18/25 | -0.017 [-0.034, -0.000] | 3/25 | NOT SUPPORTED |
| v1 | H2b | W\_wpd\_db4 - W\_stft | delta>=0.03, CI lo>0, >=18/25 | -0.066 [-0.095, -0.036] | 1/25 | NOT SUPPORTED |
| v1 | H3 | A\_wpd\_db4 - W\_wpd\_db4 | delta>=0.03, CI lo>0, >=18/25 | +0.113 [+0.065, +0.165] | 25/25 | SUPPORTED |
| v1 | H4a | A\_wpd\_db4 - B0 | delta>=0.03, CI lo>0, >=18/25 | +0.051 [-0.002, +0.102] | 21/25 | NOT SUPPORTED |
| v1 | H4b | A\_wpd\_db4 - B1 | delta>=0.03, CI lo>0, >=18/25 | +0.072 [+0.026, +0.122] | 24/25 | SUPPORTED |
| E2 | H5a | E2\_wpd\_true - E2\_wpd\_perm | delta>=0.03, CI lo>0, >=18/25 | +0.147 [+0.094, +0.199] | 25/25 | SUPPORTED |
| E2 | H5b | E2\_stft\_true - E2\_stft\_perm | delta>=0.03, CI lo>0, >=18/25 | +0.174 [+0.115, +0.229] | 25/25 | SUPPORTED |
| E2 | H5c | E2\_wpds\_true - E2\_wpds\_perm | delta>=0.03, CI lo>0, >=18/25 | +0.131 [+0.079, +0.185] | 25/25 | SUPPORTED |
| E2 | H5d | E2\_wpd\_true - E2\_wpd\_shift | delta>=0.03, CI lo>0, >=18/25 | +0.192 [+0.141, +0.248] | 25/25 | SUPPORTED |
| E2 | H5d | E2\_stft\_true - E2\_stft\_shift | delta>=0.03, CI lo>0, >=18/25 | +0.202 [+0.152, +0.254] | 25/25 | SUPPORTED |
| E2 | H5d | E2\_wpds\_true - E2\_wpds\_shift | delta>=0.03, CI lo>0, >=18/25 | +0.206 [+0.153, +0.260] | 25/25 | SUPPORTED |
| E1 | H6a | E1\_wpd\_auto - E2\_wpd\_true | delta >= -0.03 | -0.062 [-0.102, -0.021] | 3/25 | NOT SUPPORTED |
| E1 | H6b | E1\_wpd\_auto - B1 | delta > 0 and CI lower > 0 | +0.010 [-0.038, +0.060] | 15/25 | NOT SUPPORTED |
| E1 | H6c(a) | E1\_stft\_auto - E2\_stft\_true | delta >= -0.03 | -0.050 [-0.090, -0.011] | 1/25 | NOT SUPPORTED |
| E1 | H6c(b) | E1\_stft\_auto - B1 | delta > 0 and CI lower > 0 | +0.039 [-0.009, +0.088] | 20/25 | NOT SUPPORTED |
| E1 | H6c(a) | E1\_wpds\_auto - E2\_wpds\_true | delta >= -0.03 | -0.077 [-0.120, -0.037] | 1/25 | NOT SUPPORTED |
| E1 | H6c(b) | E1\_wpds\_auto - B1 | delta > 0 and CI lower > 0 | -0.003 [-0.051, +0.047] | 12/25 | NOT SUPPORTED |
| E1b | H8a | E1b\_wpd\_auto - E2\_wpd\_true | delta >= -0.03 | -0.091 [-0.135, -0.045] | 1/25 | NOT SUPPORTED |
| E1b | H8b | E1b\_wpd\_auto - B1 | delta > 0 and CI lower > 0 | -0.019 [-0.064, +0.029] | 6/25 | NOT SUPPORTED |
| E1b | H8c(a) | E1b\_stft\_auto - E2\_stft\_true | delta >= -0.03 | -0.106 [-0.148, -0.063] | 0/25 | NOT SUPPORTED |
| E1b | H8c(b) | E1b\_stft\_auto - B1 | delta > 0 and CI lower > 0 | -0.017 [-0.061, +0.031] | 11/25 | NOT SUPPORTED |
| E1b | H8c(a) | E1b\_wpds\_auto - E2\_wpds\_true | delta >= -0.03 | -0.088 [-0.130, -0.045] | 0/25 | NOT SUPPORTED |
| E1b | H8c(b) | E1b\_wpds\_auto - B1 | delta > 0 and CI lower > 0 | -0.013 [-0.057, +0.034] | 10/25 | NOT SUPPORTED |
| E4 | H9a | E4\_wpd - E2\_wpd\_true | delta >= -0.03 | -0.007 [-0.044, +0.031] | 10/25 | SUPPORTED |
| E4 | H9b | E4\_wpd - B1 | delta > 0 and CI lower > 0 | +0.065 [+0.022, +0.115] | 25/25 | SUPPORTED |
| E4 | H9c | E4\_wpd - W\_stft | delta > 0 and CI lower > 0 | +0.040 [-0.003, +0.089] | 21/25 | NOT SUPPORTED |
| E4 | H9a | E4\_stft - E2\_stft\_true | delta >= -0.03 | -0.006 [-0.044, +0.031] | 8/25 | SUPPORTED |
| E4 | H9b | E4\_stft - B1 | delta > 0 and CI lower > 0 | +0.083 [+0.036, +0.135] | 24/25 | SUPPORTED |
| E4 | H9c | E4\_stft - W\_stft | delta > 0 and CI lower > 0 | +0.058 [+0.011, +0.108] | 22/25 | SUPPORTED |
| E4 | H9a | E4\_wpds - E2\_wpds\_true | delta >= -0.03 | -0.005 [-0.044, +0.035] | 9/25 | SUPPORTED |
| E4 | H9b | E4\_wpds - B1 | delta > 0 and CI lower > 0 | +0.070 [+0.027, +0.120] | 25/25 | SUPPORTED |
| E4 | H9c | E4\_wpds - W\_stft | delta > 0 and CI lower > 0 | +0.045 [+0.001, +0.094] | 21/25 | SUPPORTED |
| E2 | equivalence | E2\_wpds\_true - E2\_stft\_true | CI within +/-0.03 | -0.015 [-0.032, +0.003] | 5/25 | equivalence NOT shown |
| E3 | H7 | soft murmurs (grade I/VI sensitivity) | - | — | - | NOT RUN (dropped, amendment E3-drop) |
| S1 (diagnostic) | S1(a) | E4\_stft - S1\_Wstft\_SC | CI lo>0 -> not shortcut-explained | +0.043 [-0.005, +0.096] | 21/25 | possibly shortcut-driven |
| S1 (diagnostic) | S1(a) | E4\_stft - S1\_Wwpd\_SC | CI lo>0 -> not shortcut-explained | +0.095 [+0.043, +0.149] | 23/25 | not explained by the span/missingness shortcut |
| S1 (diagnostic) | S1(a) | E4\_wpd - S1\_Wstft\_SC | CI lo>0 -> not shortcut-explained | +0.026 [-0.020, +0.075] | 21/25 | possibly shortcut-driven |
| S1 (diagnostic) | S1(a) | E4\_wpd - S1\_Wwpd\_SC | CI lo>0 -> not shortcut-explained | +0.077 [+0.027, +0.131] | 24/25 | not explained by the span/missingness shortcut |
| S1 (diagnostic) | S1(a) | E4\_wpds - S1\_Wstft\_SC | CI lo>0 -> not shortcut-explained | +0.030 [-0.015, +0.081] | 18/25 | possibly shortcut-driven |
| S1 (diagnostic) | S1(a) | E4\_wpds - S1\_Wwpd\_SC | CI lo>0 -> not shortcut-explained | +0.082 [+0.031, +0.137] | 23/25 | not explained by the span/missingness shortcut |

Notes: H1 used the authors' SVM at recording level, with an indicative CI over the 25 split-level AUCs. H2–H4 are v1 (Linux,
frozen) results. Rules for H6/H8/H9 come from the protocol sections (wpd primary, stft/wpds under the same rules). S1
labels follow the fixed rule "CI lower bound > 0 → not explained by the shortcut". H7 (E3) was not run.

## Decomposition (RF, repeat-averaged AUROC; * = diagnostic using the expert annotation at test time)
| Labels / features (RF, repeat-averaged AUROC [95 % CI]) | stft | wpd | wpds |
|---|---|---|---|
| expert labels (E2 true) | 0.815 [0.772, 0.853] | 0.798 [0.753, 0.838] | 0.800 [0.756, 0.839] |
| E4 automatic spans + HSMM | 0.809 [0.766, 0.849] | 0.791 [0.746, 0.831] | 0.796 [0.751, 0.836] |
| D1 HSMM in expert spans* | 0.800 [0.757, 0.840] | 0.783 [0.738, 0.827] | 0.791 [0.746, 0.834] |
| E1b HSMM, whole recording | 0.709 [0.664, 0.753] | 0.707 [0.662, 0.749] | 0.712 [0.670, 0.754] |
| D2 timing destroyed in spans* | 0.622 [0.573, 0.668] | 0.629 [0.579, 0.677] | 0.607 [0.557, 0.653] |
| E2 perm, timing destroyed (whole rec.) | 0.642 [0.592, 0.690] | 0.651 [0.604, 0.700] | 0.669 [0.618, 0.717] |
| D3 whole-signal features in spans* | 0.741 [0.692, 0.788] | 0.701 [0.656, 0.747] | 0.754 [0.706, 0.798] |
| whole-signal features, full recording | 0.751 [0.701, 0.794] | 0.685 [0.637, 0.732] | 0.743 [0.694, 0.790] |

Exact identities (`docs/D_DIAGNOSTICS.md`):
* expert − perm = (expert − D2) [within-span timing, +0.169 to +0.193] + (D2 − perm) [span selection without timing, −0.020 to −0.062];
* expert − E1b = (expert − D1) [HSMM timing error, +0.010 to +0.015] + (D1 − E1b) [span selection, +0.077 to +0.091].

## Post-hoc / descriptive items (not pre-registered; no verdict depends on them)
* **v1 amendment A1:** WPD smoothing explored after H2 was seen (`posthoc_smoothing_*`). wpds was pre-registered only in v2.
* **E2 null span check** (erratum E2-1, `e2_null_span_displacement.csv`): perm put 48.4 % of its labels outside the expert
  spans, shift 2.8 %.
* **E1 segmentation diagnostics** (period agreement, swapped F1), **E1b label coverage**, **D1 coverage**.
* **E4 shortcut check** (`e4_shortcut_check.csv`): the predicted-span fraction alone gives AUROC 0.646, the missing share 0.567,
  and expert coverage 0.547. This motivated S1, which was then pre-registered.
* **Mac reproduction** (`REPRO_MAC.md`): B0 MFCC float32 differences (max 1.53e-5) and the B0 retrain check (|ΔAUROC| ≤ 0.00126).
* **Final wavelet-vs-STFT panel** (`final_wavelet_vs_stft.csv`, subject bootstrap seed 2): computed for the figure.

## When each experiment was designed, relative to which results (git commits, IST)
| Date / time | Commit | Event | Results known at that point |
|---|---|---|---|
| 2026-10-27 13:06 | `c3745de` | v1 protocol + folds locked | none |
| 13:58 | `24b0011` | v1 pilot results (H1–H4) | — |
| 15:26 | `e9a1b98` | Phase 2 locked (E1, E2, E3 pre-registered; tag `protocol-v2-lock`) | v1 |
| 20:33 | `c5d699b` | E2 code + amendment I1 (before any E2 run) | v1 |
| 21:15 / 21:22 | `7283163`, `4855301` | amendments D1/D2 (data version v1.0.3) | E0 provenance |
| 21:37 | `112931c` | **E2 results** | v1 |
| 22:14 | `05dc9b1` | E1 code + amendment I2 (after segmentation metrics, before classification) | E2, E1 segmentation quality |
| 22:18 | `2d69fb1` | **E1 results** | E2 |
| 22:37 | `7f07b74` | **E1b pre-registered** (tag `e1b-prereg`), E3 dropped | E2, E1 |
| 22:57 | `cf1655f` | **E1b results** | E2, E1 |
| 23:04 | `fd6b7d6` | erratum E2-1 | E2, E1, E1b |
| 23:05 | `4009275` | **D1–D3 pre-registered** (tag `diag-prereg`) | E2, E1, E1b, erratum |
| 23:17 | `33a4c35` | **D1–D3 results** | — |
| 23:26 | `64e0e91` | **E4 pre-registered** (tag `e4-prereg`) | E2, E1, E1b, D1–D3 |
| 23:44 | `b462577` | **E4 results** | — |
| 2026-10-28 00:03 | `a2bddb5` | **S1 pre-registered** (tag `s1-prereg`) | everything above, incl. the E4 shortcut check |
| (this commit) | — | S1 results, final figures, final manifest, tag `results-final` | all |

E1b, D1–D3, E4 and S1 were each designed after the preceding results were seen, on the same data and folds. E4 and S1 are
therefore sequentially designed results; any deployment claim needs independent data (e.g. the CirCor hidden test set or
another cohort).

## Final figures (regenerated from saved outputs only, `scripts/31_final_figures.py`; `results/figures_final/`)
* `fig_final_roc.png`: patient ROC (RF, repeat-averaged) for B0, B1, W_stft, expert-aligned stft, E4 stft, E4 wpds.
* `fig_final_decomposition.png`: expert / D1 / E1b / D2 / perm / D3 / whole-signal AUROC with CIs, per representation.
* `fig_final_wavelet_vs_stft.png`: wpd − stft and wpds − stft under each labelling, with the ±0.03 band.
* `fig_final_ladder.png`: E1b → E4 → D1 → expert, with B1 and W_stft reference lines.

## Freeze
`results/final_freeze/MANIFEST_final.sha256` covers every file under `results/` (tables, predictions, logs, figures, the v1
freeze manifest) and `data/processed/`. `results/v1_freeze/MANIFEST_v1.sha256` still verifies 52/52. Tag `results-final`:
no new experiments after it.
