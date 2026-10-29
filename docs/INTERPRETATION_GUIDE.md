# INTERPRETATION_GUIDE — what the results support, and what they do not

Numbers: `docs/RESULTS_SUMMARY.md` (Phases 1–2), `docs/P3_RESULTS.md` (Phase 3), `results/tables/final_hypotheses.csv`,
`results/tables/p3/`. All AUROCs are patient level (874 CirCor patients, 5 repeats × 5 subject-grouped folds, WEKA
RandomForest unless stated); Δ = AUROC of repeat-averaged scores; CI = 95 % subject bootstrap. This guide adds no number.

## 1. Kinds of analysis
| Kind | Which | How to read |
|---|---|---|
| **Confirmatory** (pre-registered rule, registered before the data were analysed) | H1–H4 (Phase 1); H5a–d, H6, H8 (Phase 2 protocol); H9a–c (E4 pre-registration); H10a/b, H11a–c, H12a/b (Phase 3) | The recorded verdict follows the registered rule. |
| **Pre-registered diagnostics / secondary** | D1–D3, S1, wpd/wpds secondary representations, SMO results, H12c (descriptive) | Registered before running, but sequentially designed after earlier results on the same folds; support interpretation, not new claims. |
| **Exploratory / post-hoc** | WPD smoothing (v1 amendment A1), E2 null-span check, E1 segmentation diagnostics, E4 shortcut check (`28_e4_shortcut_check.py`), wavelet-vs-STFT panel, ZCHSound age check, operating points in the write-up | Labelled post-hoc where reported; no verdict depends on them. |

## 2. Claims the results support (with their limits)
1. **Cardiac-cycle timing carries most of the murmur information available to these features.** Destroying timing while
   keeping the features lowers AUROC in all 25 folds (H5a–d); in the decomposition against that null the gain is within-span
   timing, and span choice without timing does not help (D1–D3). *Limit:* the decomposition is against the timing-destroyed
   null; it does not prove that alignment explains every difference between models (erratum E2-3).
2. **Aligned features beat whole-signal features** for the same transform (H3), and the frozen-fold re-evaluation of the 2025
   wavelet baseline (B1) is lower than our aligned models (H4b, H9b).
3. **The transform does not matter here.** WPD (db4, and db6/sym8/coif3 as sensitivity) is never better than matched STFT
   bands (H2a/H2b not supported), equivalence within ±0.03 is **not** shown, and wavelet scattering does not beat STFT bands
   (H11a/b not supported; H11c's second-order gain is below the registered 0.03).
4. **Automatic segmentation works only with span selection.** E1 (envelope peaks) and E1b (LR-HSMM on whole recordings)
   miss their targets (H6, H8). With a learned span detector (E4), H9a's point-estimate rule (Δ ≥ −0.03) is met.
5. **A whole-signal STFT model transfers to an independent paediatric CHD cohort** (ZCHSound clean set, H10a) with the
   pre-registered physiological subtype order (H10b).

## 3. Claims the results do NOT support
| Claim | Why not |
|---|---|
| "Automatic segmentation matches expert segmentation" / "E4 is non-inferior" | H9a used a point-estimate rule. The CI lower bound (≈ −0.044) is below −0.03, so **statistical non-inferiority is not established** and clinical equivalence is not shown (erratum E2-2). |
| "WPD is equivalent to STFT" | Equivalence within ±0.03 was tested and **not** shown; WPD was, if anything, slightly worse. Say "no wavelet advantage", not "equivalent". |
| "Wavelets improve diagnostic accuracy" | No representation comparison favoured wavelets (H2, H11, wavelet-vs-STFT panel). |
| "Cardiac-cycle alignment causes the entire improvement" | True only of the decomposition against the timing-destroyed null (E2-3); the automatic pipeline's margin over a shortcut-aware whole-signal baseline is not established. |
| "The automatic pipeline beats whole-signal STFT" | H9c is not met for the primary wpd; with the span/missingness shortcut given to STFT, E4's margin has a CI including zero (S1), and the shortcut-free E4q does not establish it either (H12a: lower bound −0.001). Do not call H12a "nearly significant". |
| "The system is deployable / clinically validated" | Cross-validation on one public cohort; no CirCor hidden test, no prospective or clinical study; the noisy neonatal external subset is at chance. |
| "Externally validated for murmur detection" | ZCHSound labels are CHD **diagnoses**, not murmurs; PFO (acoustically silent) is at chance, as expected. |
| "Superior to all published methods" | Published numbers use other metrics, units, splits, label sets and often test-time expert segmentation (`docs/P4_CASE_STUDY.md`); they are not on our scale. Only B1 was re-evaluated under our folds. |
| Any statement from SMO scattering AUROCs | SMO is numerically unstable on scattering features across platforms (`docs/P3_RESULTS.md` §2); those numbers are not evidence. |
| Any statement from B0's external AUROC | B0's external signal is an artefact of recording characteristics (`docs/P3_RESULTS.md` §3). |
| A literature-wide rate of test-time expert segmentation | The G3b audit was not coded (amendment A3); only two case studies are described. |

## 4. Wording to use
* "Point-estimate criterion met; statistical non-inferiority not established."
* "No wavelet advantage over matched STFT bands; equivalence not shown."
* "A gain over a shortcut-aware whole-signal baseline is not established (CI includes zero)."
* "Expert-label (oracle-conditioned) results" whenever the `.tsv` annotation is used at test time.
* "External test on a CHD-labelled cohort", not "external murmur validation".
