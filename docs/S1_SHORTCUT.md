# S1_SHORTCUT — Does E4 still beat whole-signal features once they get the span/missingness shortcut? (diagnostic)

> **Interpretation note (2026-10-29).** Numbers and verdicts below are unchanged. "Reaches expert-label performance" (§ conclusions) means only that H9a's point-estimate rule was met; statistical non-inferiority is not established (erratum E2-2, [`ERRATA_PHASE2.md`](ERRATA_PHASE2.md)). The Phase-3 shortcut-free test H12a likewise does not establish a gain ([`P3_RESULTS.md`](P3_RESULTS.md)).

Pre-registered in `docs/PROTOCOL_V2_LOCKED.md` "S1" + `configs/protocol_v2.json` (commit `a2bddb5`, tag `s1-prereg`, pushed
before any S1 code; the section header says 00:05 IST, the commit was made at 00:03 IST on 2026-10-28). **Designed after
the E4 results were known; a diagnostic.** WEKA RF (decides the label) and SMO (descriptive), frozen folds, 874 patients,
5 × 5 folds.

| Step | Command | Output |
|---|---|---|
| shortcut variables | `NPROC=10 python scripts/29_s1_build.py 0,1,2,3,4` | `data/interim/s1/features/` (gitignored), `results/logs/s1_build_folds.csv` |
| WEKA | `python scripts/06_run_patient_level_weka.py s1 S1_Wstft_SC,S1_Wwpd_SC,S1_SC_only RF,SMO 8` | `results/predictions/s1_predictions.csv`, `results/logs/run_s1.log` |
| analysis | `python scripts/30_s1_analyze.py` | `results/tables/s1_{auroc,contrasts}.csv`, `results/logs/s1_analysis.{json,log}` |

**Shortcut variables (SC), exactly as in E4.** The span detectors were re-derived per fold with the same HSMM models,
seeds, row order and cross-fitting; all test-window predictions are identical to the saved E4 ones (25/25 folds). SC is
the patient median and max of the predicted-span fraction plus the number and fraction of recordings without E4 aligned
features. The count and fraction enter as identical `__med`/`__max` columns, so a patient vector has 6 SC columns (74 in
total with the 68 whole-signal features). No patient lacks features in any S1 set.

## Results (repeat-averaged AUROC [subject-bootstrap 95 % CI] / mean of repeats)
| Set | RF | SMO |
|---|---|---|
| (c) **SC alone** (no audio) | **0.587** [0.533, 0.641] / 0.562 | 0.536 [0.485, 0.585] / 0.513 |
| W_stft | 0.751 [0.701, 0.794] / 0.744 | 0.747 [0.698, 0.795] / 0.743 |
| **W_stft + SC** | **0.765** [0.718, 0.808] / 0.759 | 0.759 [0.713, 0.804] / 0.756 |
| W_wpd_db4 | 0.685 [0.637, 0.732] / 0.678 | 0.687 [0.633, 0.737] / 0.680 |
| **W_wpd_db4 + SC** | **0.714** [0.666, 0.759] / 0.707 | 0.718 [0.671, 0.765] / 0.714 |
| E4 stft / wpd / wpds | 0.809 / 0.791 / 0.796 | 0.814 / 0.809 / 0.814 |

**(b) How much the shortcut alone adds:** W_stft + SC − W_stft = **+0.015** [+0.003, +0.028], 21/25 folds (SMO +0.012
[−0.009, +0.031]); W_wpd_db4 + SC − W_wpd_db4 = **+0.029** [+0.011, +0.048], 25/25 (SMO +0.031 [+0.002, +0.059]).

**(a) E4 vs the shortcut-augmented baselines (RF; fixed rule: CI lower bound > 0 → "not explained by the shortcut")**
| Contrast | Δ repeat-averaged [95 % CI] | folds Δ > 0 | Δ mean of repeats | Label |
|---|---|---|---|---|
| E4 stft − (W_stft + SC) | +0.043 [−0.005, +0.096] | 21/25 | +0.044 | **possibly shortcut-driven** |
| E4 wpd − (W_stft + SC) | +0.026 [−0.020, +0.075] | 21/25 | +0.025 | **possibly shortcut-driven** |
| E4 wpds − (W_stft + SC) | +0.030 [−0.015, +0.081] | 18/25 | +0.030 | **possibly shortcut-driven** |
| E4 stft − (W_wpd_db4 + SC) | +0.095 [+0.043, +0.149] | 23/25 | +0.096 | not explained by the shortcut |
| E4 wpd − (W_wpd_db4 + SC) | +0.077 [+0.027, +0.131] | 24/25 | +0.077 | not explained by the shortcut |
| E4 wpds − (W_wpd_db4 + SC) | +0.082 [+0.031, +0.137] | 23/25 | +0.082 | not explained by the shortcut |

SMO (descriptive): E4 − (W_stft + SC) +0.056 / +0.051 / +0.055 (stft / wpd / wpds), CI lower bounds +0.009 / +0.005 / +0.010;
E4 − (W_wpd_db4 + SC) +0.097 / +0.092 / +0.096, all CIs > 0.

## Interpretation (by the fixed rule)
* The shortcut variables carry real but small information. Alone they reach AUROC 0.59 (CI excludes 0.5), and they add
  +0.015 to whole-signal STFT and +0.029 to whole-signal WPD.
* **Against the stronger baseline, whole-signal STFT + SC, E4's advantage is "possibly shortcut-driven" for every
  representation (RF).** The point estimates stay positive (+0.026 to +0.043, 18–21/25 folds), but no CI excludes 0.
  The deployable advantage over a shortcut-aware STFT baseline is therefore not established. SMO points the other way
  (CI > 0), but the pre-registered label follows RF.
* Against whole-signal WPD + SC, E4's advantage is not explained by the shortcut (+0.077 to +0.095, CI > 0). That
  baseline is weak, though (0.714).
* Together with E4: the automatic span-selected aligned pipeline reaches expert-label performance and beats B1. However,
  its margin over a whole-signal STFT model that is given the same span/missingness information is +0.03 to +0.04 AUROC
  and not significant (RF).
