# D_DIAGNOSTICS — How much of the expert-label gain is span selection vs timing? (diagnostics D1–D3)

> **DIAGNOSTICS ONLY.** All three use the expert annotation of the *test* recordings at test time, so none of them is
> deployable. They were **designed after the E1b results were known** (and after erratum E2-1), pre-registered on
> 2026-10-27 23:05 IST in `docs/PROTOCOL_V2_LOCKED.md` "Diagnostics D1–D3" + `configs/protocol_v2.json`
> (commit `4009275`, tag `diag-prereg`, pushed before any diagnostic code). No pass/fail thresholds: a descriptive
> decomposition, every number reported. (Unrelated to the data-version amendments D1/D2.)

| Step | Command | Output |
|---|---|---|
| D2, D3 features | `NPROC=10 python scripts/24_diag_extract.py d23` | `data/processed/diag/rec_features_D{2,3}_<rep>.csv` |
| D1 features (fold-wise) | `… 24_diag_extract.py d1 0,1,2,3,4` | `data/interim/diag/features/` (gitignored), `results/logs/diag_d1_folds.csv` |
| WEKA | `python scripts/06_run_patient_level_weka.py diag D1_*,D2_*,D3_*,W_wpd_db4_smooth RF,SMO 8` | `results/predictions/diag_predictions.csv` (2,000 jobs), `results/logs/run_diag.log` |
| analysis | `python scripts/25_diag_analyze.py` | `results/tables/diag_{auroc,contrasts,d1_coverage}.csv`, `results/logs/diag_analysis.{json,log}` |

**Definitions.** "Expert spans" = level-4 columns with expert label 1–4 (as the E2 `true` arm).
* **D1** = the E1b fold-wise LR-HSMM labels (same models and seeds; every outer-model decode re-derived and checked
  identical to the saved E1b decodes — 15,035/15,035) with all columns outside the expert spans set to 0.
* **D2** = the expert labels permuted only among the expert-span columns (`perm` seed rule; 14 label-null unit tests).
* **D3** = whole-signal features on the expert-span columns only.
Comparators from the same Mac: expert `true` and E2 `perm` (tag `e2`), HSMM-full = E1b (tag `e1b`), W_stft / W_wpd_db4
(tag `e1`), W_wpd_db4_smooth (tag `diag`, committed features). Frozen folds, 874 patients, RF primary, SMO secondary.

## 1. AUROC (RF; repeat-averaged [subject-bootstrap 95 % CI] / mean of repeats)
| Labels / features | stft | wpd | wpds |
|---|---|---|---|
| expert true (E2) | 0.815 [0.772, 0.853] / 0.811 | 0.798 [0.753, 0.838] / 0.793 | 0.800 [0.756, 0.839] / 0.797 |
| **D1** HSMM timing inside expert spans | **0.800** [0.757, 0.840] / 0.792 | **0.783** [0.738, 0.827] / 0.778 | **0.791** [0.746, 0.834] / 0.785 |
| HSMM-full (E1b) | 0.709 [0.664, 0.753] / 0.702 | 0.707 [0.662, 0.749] / 0.697 | 0.712 [0.670, 0.754] / 0.704 |
| **D2** timing destroyed inside expert spans | **0.622** [0.573, 0.668] / 0.614 | **0.629** [0.579, 0.677] / 0.619 | **0.607** [0.557, 0.653] / 0.598 |
| E2 perm (timing destroyed, whole recording) | 0.642 [0.592, 0.690] / 0.636 | 0.651 [0.604, 0.700] / 0.642 | 0.669 [0.618, 0.717] / 0.661 |
| **D3** whole-signal features on expert spans | **0.741** [0.692, 0.788] / 0.737 | **0.701** [0.656, 0.747] / 0.695 | **0.754** [0.706, 0.798] / 0.750 |
| whole-signal, full recording (W) | 0.751 [0.701, 0.794] / 0.744 | 0.685 [0.637, 0.732] / 0.678 | 0.743 [0.694, 0.790] / 0.739 |

SMO (repeat-averaged): true 0.816 / 0.785 / 0.794; D1 0.800 / 0.802 / 0.805; HSMM-full 0.727 / 0.710 / 0.710;
D2 0.533 / 0.571 / 0.582; E2 perm 0.581 / 0.600 / 0.596; D3 0.744 / 0.712 / 0.770; W 0.747 / 0.687 / 0.746
(stft / wpd / wpds; CIs in `diag_auroc.csv`).

## 2. Paired contrasts (RF; Δ repeat-averaged [95 % CI], folds Δ > 0, Δ mean of repeats)
| Contrast | stft | wpd | wpds |
|---|---|---|---|
| (1) expert true − D1 | +0.015 [−0.017, +0.051], 18/25, +0.019 | +0.014 [−0.020, +0.054], 14/25, +0.016 | +0.010 [−0.025, +0.049], 15/25, +0.011 |
| (2) expert true − D2 | +0.193 [+0.137, +0.246], 25/25, +0.197 | +0.169 [+0.115, +0.225], 25/25, +0.174 | +0.193 [+0.136, +0.248], 25/25, +0.199 |
| (3) D3 − W full recording | −0.009 [−0.042, +0.024], 12/25, −0.008 | +0.017 [−0.019, +0.054], 17/25, +0.017 | +0.010 [−0.022, +0.043], 14/25, +0.011 |
| (4) D1 − HSMM-full | +0.091 [+0.046, +0.132], 25/25, +0.090 | +0.077 [+0.032, +0.118], 24/25, +0.081 | +0.078 [+0.035, +0.118], 24/25, +0.081 |
| (+) D2 − E2 perm | −0.020 [−0.075, +0.037], 10/25, −0.021 | −0.022 [−0.073, +0.031], 7/25, −0.023 | −0.062 [−0.116, −0.010], 3/25, −0.064 |
| total: true − E2 perm | +0.174 [+0.115, +0.229] | +0.147 [+0.094, +0.199] | +0.131 [+0.079, +0.185] |
| total: true − HSMM-full | +0.106 [+0.063, +0.148] | +0.091 [+0.045, +0.135] | +0.088 [+0.045, +0.130] |

SMO: (1) +0.016 / −0.017 / −0.011; (2) +0.283 / +0.213 / +0.212; (3) −0.003 / +0.025 / +0.025; (4) +0.074 / +0.091 /
+0.095; (+) −0.048 / −0.029 / −0.014 (stft / wpd / wpds; CIs in `diag_contrasts.csv`).

## 3. Plain decomposition (RF, repeat-averaged AUROC; the two identities hold exactly)
**A. Expert labels vs the timing-free null (E2's +0.13 to +0.17):**
`true − perm = (true − D2) [timing within the spans] + (D2 − perm) [span selection, no timing]`

| | stft | wpd | wpds |
|---|---|---|---|
| total true − perm | +0.174 | +0.147 | +0.131 |
| timing within spans | +0.193 (111 %) | +0.169 (115 %) | +0.193 (147 %) |
| span selection without timing | −0.020 | −0.022 | −0.062 |

→ **Timing accounts for all of E2's gain.** Keeping the timing-free labels inside the expert spans does not help
(D2 is, if anything, below perm). Erratum E2-1 was a valid concern about interpretation, but the diagnostic shows that
span selection did not inflate the E2 result.

**B. Expert labels vs the deployable HSMM (E1b's −0.09 to −0.11):**
`true − HSMM-full = (true − D1) [HSMM timing error inside the spans] + (D1 − HSMM-full) [span selection with HSMM timing]`

| | stft | wpd | wpds |
|---|---|---|---|
| total true − HSMM-full | +0.106 | +0.091 | +0.088 |
| HSMM timing error inside the spans | +0.015 (14 %) | +0.014 (16 %) | +0.010 (11 %) |
| span selection | +0.091 (86 %) | +0.077 (84 %) | +0.078 (89 %) |

→ **Most of the gap between expert and automatic labels is span selection, not timing.** Inside the expert-annotated
spans the HSMM's timing comes within 0.010–0.015 AUROC of the expert's (CIs include 0; SMO D1 ≥ true for wpd and wpds).
What drags E1b down is applying aligned features to the whole recording, including the stretches the expert did not
annotate.

**C. Span selection alone (D3):** whole-signal features restricted to the expert spans change AUROC by −0.009 to +0.017
(all CIs include 0). **"Use the clean parts" by itself is worth nothing.** It matters only together with timing (B).

## 4. Caveats
* **D1 coverage:** restricting HSMM labels to the spans leaves some recordings below the v1 minimum (≥ 40 systolic,
  40 diastolic, 10 S1 columns): 207–235 recordings per fold (mean 221; 36–45 Present, 170–190 Absent) without aligned
  features, and 21–27 patients per fold (2–5 Present, 17–24 Absent) without any (`diag_d1_coverage.csv`). One cause,
  seen in individual recordings: the HSMM gives some recordings very long S1 and short systole labels (e.g. 39403_MV:
  723 S1 vs 119 systole columns over the recording). The missingness is class-related (mostly Absent), which may
  favour D1 slightly. D2/D3 lack features only for 50782_MV_1 (no expert spans).
* All D results use the expert's choice of spans for the *test* recordings, so they bound what an automatic span (signal
  quality) selector could achieve. They are not results a deployed system could reach.
* Designed after E1b; descriptive only; no hypothesis was tested and no verdict changes.

## 5. What it means
The cycle-aligned features need **both** correct cardiac timing (A: +0.17 to +0.19 AUROC within the spans) **and**
restriction to the cleanly annotated stretches (B: +0.08 to +0.09 with HSMM timing). Neither alone is enough: span
selection without timing gives nothing (A, C), and HSMM timing over the whole recording loses most of the benefit (B).
A trained segmenter already supplies near-expert timing inside good spans. The missing piece for a deployable system is
therefore an **automatic span or signal-quality selector**, not a better segmenter. That would be a new, separately
pre-registered experiment and has not been started.
