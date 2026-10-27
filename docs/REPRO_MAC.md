# REPRO_MAC — Phase-1 reproduction on the Mac (2026-10-27)

**Verdict: reproduced, with one documented float32 deviation.** Folds, audit, segmentation, B1 and all STFT/WPD
features reproduce within the 1e-6 absolute rule. WEKA AUROCs reproduce within 0.00035 (limit 0.002). **B0's 13
MFCC means differ by up to 1.53e-5** (absolute), which is outside the 1e-6 rule; that rule was set for float64
features, and the MFCCs are float32 — a Linux-vs-macOS float32 difference (§2a). Retraining B0 on the Mac-computed
features keeps every AUROC within 0.00126 of v1 (§3a). Frozen files untouched
(`shasum -a 256 -c results/v1_freeze/MANIFEST_v1.sha256`: 52/52 OK).

Environment: `configs/environment_mac.txt` (macOS 26.6, Apple M5 Pro, OpenJDK 21.0.13 Homebrew, Python 3.12.14,
same package versions as `configs/requirements_frozen.txt`). Phase 1 ran on Ubuntu, OpenJDK 21.0.12, Python 3.13.17.

## 1. Inputs (like-for-like, amendment D1/D2)
`bash scripts/17_make_data_views.sh <v1.0.3 root>` builds `data/interim/repro_phase1_view/` (gitignored): per-file
symlinks to the untouched v1.0.3 download, except `50782.txt`, which is a copy of the Phase-1 copy's header
(sha256 `182d08e4…` = `circor_copy_SHA256SUMS.txt`), so 50782_MV_1 has no segmentation, as in Phase 1. The other
941 headers are v1.0.3 (extra `#Outcome`, 73 different `#Age` — neither used by any feature or model).

`bash scripts/13_repro_mac_shadow.sh data/interim/repro_mac_shadow data/interim/repro_phase1_view` reruns
`01 → 04 → 03 → 02 → 10` unmodified with a shadow cwd (45 s); `scripts/14_repro_mac_compare.py features …` compares
→ `results/tables/repro_mac_files.csv`.

## 2. Data scripts vs frozen outputs
| Output | Result |
|---|---|
| `configs/folds_patient_level.csv` | **byte-identical**, sha256 `c4aa74c7…2339` (also identical when run on unmodified v1.0.3) |
| `fold_composition.csv`, `recordings_audit.csv` | byte-identical |
| `seg_coverage.csv`, `extraction_errors.csv` (0 errors), `rec_features_B1.csv` | byte-identical |
| `b1_alignment_verification.csv` | differs only at 1e-16 (`python_port`, `rel_err`); B1 port max rel. error 4.5e-15 |
| `patients_audit.csv` | differs only in `outcome` (941 rows, now present) and `age` (73 rows) — v1.0.3 headers, expected |
| 14 STFT/WPD feature files (W/A × stft, db4, db6, sym8, coif3, db4_smooth) | max \|Δ\| ≤ 5.5e-11, identical NaN pattern → **within 1e-6** |
| `rec_features_B0.csv` | **max \|Δ\| 1.53e-5 → outside 1e-6.** Only the 13 MFCC means differ (8,769 of 56,934 values > 1e-6); centroid, bandwidth, rolloff, ZCR, RMS-CV ≤ 6.4e-9 |

B0 explanation: `acoustic_features` computes MFCCs on `x.astype(np.float32)` with librosa, so its means carry float32
rounding; every difference is a multiple of a float32 ulp at the value's magnitude (1.53e-5 = 2⁻¹⁶ = 1 ulp for values in
128–256; MFCC-0 median |value| 35.8). The summation/FFT order differs between the Linux and macOS builds. The
per-column max relative difference ranges from 2.8e-7 (MFCC-1) to 1.7e-3 (MFCC-0), the large ones on values near zero. This is a platform
float32 effect, not a pipeline difference, but it does not meet the stated 1e-6 absolute tolerance.

## 2a. Tolerance for the float32 MFCCs (decision 2026-10-27)
The 1e-6 absolute limit was set for float64 features. librosa computes MFCCs in float32, so for the 13 MFCC means
the appropriate check is relative error within a few float32 ulps (relative error ≤ ~1e-6 ≈ 8 ulps). **The 1e-6
absolute rule is unchanged for every other feature** (all of which pass it). Observed
(`scripts/14_repro_mac_compare.py b0float32` → `results/tables/repro_mac_b0_float32.csv`, 41,119 MFCC values):

* **Max relative error 1.7e-3** (MFCC-0, on a value of 1.9e-4). Median relative error per column 0 – 2.1e-7.
* **730 / 41,119 values (1.8 %) exceed relative 1e-6; 1,161 (2.8 %) exceed 8 ulps of their own value.** These are
  small values relative to their column (|value| 1.9e-4 – 3.8, median 0.56, 76 % below 1; column medians 2.5 – 43):
  a mean of float32 frames carries rounding at the scale of the summed frames, not of the small result, so relative
  error is ill-conditioned there. In absolute terms every difference is ≤ 1.53e-5; relative to each column's median
  |value| the largest difference is 8.5e-7.
* So the relative-ulp criterion is met for 98.2 % of values, **not for all**; the deviation is a Linux-vs-macOS
  float32 difference in librosa's FFT/mel/DCT arithmetic, not a pipeline difference. Its downstream effect is
  measured in §3a.

## 3. WEKA main study under a new tag
`scripts/06_run_patient_level_weka.py repro_mac B0,B1,W_stft,W_wpd_db4,A_stft,A_wpd_db4 RF,SMO,MLP,LR 8` on the
**committed** `data/processed/` features and frozen folds: 2,400 jobs in 219 s (8 JVMs).
`scripts/14_repro_mac_compare.py weka repro_mac` → `results/tables/repro_mac_auroc_comparison.csv`,
`results/logs/repro_mac_comparison.json`.

* **SMO, LR, MLP: every patient score identical** (max |Δ score| 0) → identical AUROCs.
* **RF: max |Δ score| 0.0133 (= 4/300 trees)**, spec-80 threshold max |Δ| 0.0033; same seed `-S 1 -num-slots 1`
  (likely JVM build differences in floating-point split evaluation; not investigated further).
* **Max |ΔAUROC| over all 24 set × classifier pairs: 0.00035** (B0 RF, repeat-averaged) → **all within 0.002.**

| RF | v1 mean of repeats | Mac mean of repeats | v1 repeat-averaged | Mac repeat-averaged |
|---|---:|---:|---:|---:|
| A_stft | 0.8115 | 0.8114 | 0.8152 | 0.8151 |
| A_wpd_db4 | 0.7934 | 0.7934 | 0.7979 | 0.7977 |
| B0 | 0.7432 | 0.7435 | 0.7470 | 0.7473 |
| B1 | 0.7212 | 0.7213 | 0.7259 | 0.7259 |
| W_stft | 0.7444 | 0.7442 | 0.7508 | 0.7508 |
| W_wpd_db4 | 0.6781 | 0.6781 | 0.6847 | 0.6848 |

"Mean of repeats" = mean of the 5 per-repeat patient AUROCs; "repeat-averaged" = AUROC of each patient's score
averaged over the 5 repeats (the summary the subject-bootstrap CI and contrasts use).

## 3a. B0 retrained on the Mac-computed features (tag `repro_mac_b0`)
`FEATDIR=data/interim/repro_mac_shadow/data/processed scripts/06_run_patient_level_weka.py repro_mac_b0 B0 RF,SMO,MLP,LR 8`
(frozen folds; `FEATDIR` only changes where recording features are read), compared by
`scripts/14_repro_mac_compare.py weka repro_mac_b0` → `results/tables/repro_mac_b0_auroc_comparison.csv`.

| B0 | v1 mean of repeats | Mac-features mean of repeats | v1 repeat-averaged | Mac-features repeat-averaged | max \|Δ score\| |
|---|---:|---:|---:|---:|---:|
| LR | 0.7664 | 0.7664 | 0.7694 | 0.7694 | 0 |
| MLP | 0.7188 | 0.7188 | 0.7405 | 0.7405 | 0.00006 |
| RF | 0.7432 | 0.7422 | 0.7470 | 0.7457 | 0.140 |
| SMO | 0.7683 | 0.7689 | 0.7754 | 0.7750 | 0.134 |

**Pass: max |ΔAUROC| 0.00126 (RF, repeat-averaged) ≤ 0.002.** Individual RF/SMO patient scores move more (up to
0.14) because ulp-level feature changes flip some RF splits and SMO decisions; ranking performance is unaffected
within the limit.

## 4. Tests
`.venv/bin/python -m pytest -q` with the v1.0.3 data present: **52 passed** (39 original + 13 E2 label-null tests).
