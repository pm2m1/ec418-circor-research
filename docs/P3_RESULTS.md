# P3_RESULTS — Phase 3 on the Mac (G4, G1a, G2, G3a)

Pre-registration: `docs/PROTOCOL_V3_PREREG.md` (content commit `7acc9fc`, 2026-10-28 18:38:40 +0530; tag `protocol-v3-prereg` →
`54de9b3`, which adds the lock hashes) with amendments A1 (G2 details), A2 (G2 moved to the Mac) and A3 (analysis-script
erratum, below). Phase 3 was designed **after** all Phase-1/2 results were known: it is exploratory-confirmatory, not a
fresh study. Branch `phase3-g2`, imported from the cloud bundle; cloud history kept separate (`results/logs/p3_mac_provenance.txt`).
**Official Phase-3 numbers are the Mac values; the cloud values (`results/p3_cloud_reference/`) are the reproduction
reference.** G1b was not run (decided after G2).

Environment: main `.venv` as Phase 2; scattering env `.venv-scat` (kymatio 0.3.0, scipy 1.14.1, numpy 2.1.3). CirCor views as
Phase 2 (G4/G1a on the Phase-1 view, G2 on v1.0.3). ZCHSound: `ZCHSound.zip` 339,554,986 bytes, sha256 `112432cb…58b7`
(verified), GitHub LFS mirror of the official release, CC BY 4.0 (`results/logs/p3_mac_zchsound.txt`); used for no training,
tuning or threshold.

## 1. Pre-registered hypotheses

| Hypothesis | Contrast (RF) | Cloud | Mac (official) [95 % CI], folds | Verdict |
|---|---|---|---|---|
| H10a | ZCHSound-clean any-CHD AUROC, W_stft (CI lo > 0.5) | 0.706 [0.672, 0.738] | **0.709** [0.675, 0.741] | **SUPPORTED** (both) |
| H10b | AUROC(VSD) − AUROC(PFO); AUROC(VSD) − AUROC(ASD) (both CI lo > 0) | +0.262; +0.124 | **+0.263** [0.180, 0.343]; **+0.126** [0.064, 0.184] | **SUPPORTED** (both) |
| H11a | A_scat1 − A_stft (Δ ≥ 0.03, CI lo > 0, ≥ 18/25) | −0.026 [−0.058, +0.005], 4/25 | **−0.026** [−0.058, +0.005], 4/25 | **NOT SUPPORTED** |
| H11b | A_scat12 − A_stft | −0.013 [−0.044, +0.017], 7/25 | **−0.013** [−0.044, +0.017], 7/25 | **NOT SUPPORTED** |
| H11c | A_scat12 − A_scat1 | +0.013 [+0.001, +0.025], 18/25 | **+0.013** [+0.001, +0.025], 18/25 | **NOT SUPPORTED** (CI > 0, Δ < 0.03) |
| H12a (primary, stft) | E4q − (W_stft + SC_q) (CI lo > 0) | point Δ +0.046 (sealed predictions, no CI) | **+0.046** [−0.001, +0.093], 23/25; Δ ≥ 0.03: yes | **possibly shortcut-driven** |
| H12a (wpd / wpds, secondary) | same | +0.038 / +0.034 | +0.038 [−0.010, +0.086] / +0.035 [−0.013, +0.083] | possibly shortcut-driven |
| H12b (stft / wpd / wpds) | E4q − rand-q (CI lo > 0) | +0.066 / +0.071 / +0.066 | **+0.066** [+0.030, +0.100] / +0.071 [+0.037, +0.102] / +0.066 [+0.031, +0.099] | **learned selection matters** |
| H12c (descriptive) | E4q − snr-q | +0.020 / +0.013 / +0.007 | +0.020 [−0.006, +0.046] / +0.013 [−0.013, +0.040] / +0.007 [−0.021, +0.033] | descriptive |

Cloud G2 values are point differences of the sealed cloud predictions, opened only after the Mac results were reported (§5).

## 2. G4 — wavelet scattering (expert labels, frozen folds)
RF repeat-averaged AUROC [CI] / mean of repeats: A_stft 0.815 / 0.812; **A_scat1 0.789** [0.744, 0.830] / 0.785;
**A_scat12 0.802** [0.760, 0.842] / 0.796; A_wpd_db4 0.798; A_wpd_db4_smooth 0.801; whole-signal W_scat1 0.727 vs W_stft 0.751.
Scattering does not beat matched STFT bands (H11a, H11b). Second-order paths add +0.013 over first order (CI excludes 0), but
the gain is below the pre-registered 0.03 (H11c NOT SUPPORTED).

**SMO is numerically unstable on scattering features.** Mac and cloud features agree to ≤ 4.2e-10, yet SMO scores shift by up to
0.097 (CV) and 0.158 (ZCHSound), against ≤ 0.017 for RF (`p3_mac_vs_cloud.csv`, section `smo_sensitivity`). SMO scattering
AUROCs (including A_scat12 0.843) are therefore **not reportable as evidence, not even descriptively**. The RF verdicts are
stable on both platforms. SMO was not investigated or tuned further.

## 3. G1a — external validation on ZCHSound (models trained once on all 874 CirCor patients)
* **Clean set (941 children, 408 CHD), RF W_stft:** any-CHD AUROC 0.709 [0.675, 0.741] (internal CirCor 0.751). At the CirCor
  spec-80 threshold: sensitivity 0.520, specificity 0.786. **By subtype vs NORMAL:** PDA 0.854, VSD 0.785, ASD 0.659,
  **PFO 0.522** (silent defect ≈ chance), the physiological ordering H10b predicts.
* Other models (descriptive, clean, RF): W_wpd_db4_smooth 0.784 [0.751, 0.813] (no direction was pre-registered for wpds vs
  stft), B0 0.699, W_scat1 0.559. Site-matched variants (CirCor PV recordings only): W_stft 0.694, W_wpd_db4_smooth 0.714.
* **Noisy neonatal set (318, ≤ 5 days): failure.** Every model is near or below chance: W_stft RF 0.535 [0.471, 0.597],
  W_wpd_db4_smooth 0.497, B0 0.503, W_scat1 0.411 (as expected: transitional physiology plus noise).
* **B0 artefact:** B0 SMO reaches 0.834 on the clean set, but it scores PFO (acoustically silent) at 0.831 vs NORMAL, and B0 RF
  trained on PV recordings is far *below* chance (0.260). The B0 signal is therefore artefact-driven (recording/device
  characteristics), not murmur. B0 enters no verdict.
* **Post-hoc age check (not pre-registered):** age alone separates CHD from NORMAL (AUROC 0.231, i.e. younger = CHD). The RF
  W_stft score is unrelated to age (Spearman −0.03), and its AUROC within age tertiles is 0.694 / 0.774 / 0.745, so H10a is
  not an age effect (`g1a_posthoc_age_check.csv`).

## 4. G2 — shortcut-free E4 (E4q), official Mac run
* **Gate 1:** re-derived span detectors equal the saved E4 models in 25/25 folds, max |Δ| 0.0.
* **Gate 2:** the E4 re-run (E4R) reproduces `e4_predictions.csv` exactly: 26,220 rows, max score and threshold difference 0.0
  (`g2_gate.csv`). This gate failed in the cloud (Linux/OpenBLAS); on the Mac, the platform of Phase 2, it passes exactly.
* **Amendment A3 (code erratum):** `p3_g2_analyze.py` crashed after writing all tables, because one descriptive row lacked
  the `primary` field. It was fixed by setting that field (and `delta_ge_0_03`) on that row only. Table hashes were recorded
  unread before the fix: `g2_auroc.csv` and `g2_coverage.csv` are byte-identical after the fix, and `g2_contrasts.csv` differs
  only in the 4 filled cells (re-blanking them reproduces the pre-fix sha256; `results/logs/p3_g2_fix_hashes.txt`).
* **AUROC (RF, repeat-averaged [CI]):** E4q stft 0.799 [0.756, 0.842], wpd 0.792, wpds 0.789 (E4: 0.809 / 0.791 / 0.796);
  rand-q 0.734 / 0.721 / 0.722; snr-q 0.779 / 0.779 / 0.782; W_stft + SC_q 0.754; W_stft 0.751; **SC_q alone 0.482** (the
  span-fraction shortcut is removed by construction).
* **H12a (primary):** E4q stft − (W_stft + SC_q) = +0.046 [−0.001, +0.093], 23/25, Δ ≥ 0.03, but CI lower bound −0.001 →
  **possibly shortcut-driven** (wpd +0.038, wpds +0.035, the same label).
* **H12b:** learned selection beats random windows of the same fraction: +0.066 to +0.071, all CIs > 0.
* **H12c (descriptive):** learned vs SNR-gate selection +0.007 to +0.020, CIs include 0.
* **Descriptive:** E4q − E4 −0.009 / +0.001 / −0.007 (removing the shortcut costs essentially nothing); E4q − (W_stft + S1 SC)
  +0.034 / +0.026 / +0.023 (CIs include 0); W_stft + SC_q − W_stft +0.003.
* **Coverage (test recordings without aligned features, `g2_coverage.csv`):** E4R 15.8 % Absent / 9.9 % Present (the
  class-related missingness of E4); **E4q 0.6 % / 0.8 %**; rand-q 0.5 % / 1.2 %; snr-q 0.6 % / 1.2 %.
* SMO (descriptive only): E4q stft − (W_stft + SC_q) +0.055 [+0.002, +0.103].

## 5. Mac vs cloud
* **G4/G1a** (`results/tables/p3/p3_mac_vs_cloud.csv`, `scripts/p3_05_compare_cloud.py`):
  * Feature gate (1e-6, identical NaN patterns): all gated columns pass, max |Δ| ≤ 9.9e-9.
  * The 13 B0 MFCC columns of `zch_features_whole.csv` are excluded from the gate and reported descriptively: max |Δ| 4.6e-5,
    ≤ 1.6e-6 of the column median, column-scale float32 multiple ≤ 4.5. The per-value float32 rule first specified was the
    wrong yardstick for frame-averaged MFCCs (author error; it failed, with multiples up to 48,123). No tolerance was chosen
    after the fact; B0 enters no verdict; this is the same float32 cause as `docs/REPRO_MAC.md`.
  * All five pre-registered verdicts (H10a, H10b, H11a–c) are identical. RF score shifts ≤ 0.017; SMO see §2.
* **G2** (`results/tables/p3/g2_mac_vs_cloud_sealed.csv`, `scripts/p3_06_g2_sealed_compare.py`, sealed cloud predictions opened
  only after §4 was written): all 30 set/classifier pairs match row-for-row, and the maximum |ΔAUROC| is 0.0011
  (repeat-averaged) / 0.0015 (mean of repeats). The G2 conclusions are robust across platforms, even though the cloud could
  not pass the exact gate 2.

## 6. G3a — conditioning-availability gaps (`results/tables/p3/g3a_conditioning_gaps.csv`; RF, repeat-averaged)
| | stft | wpd | wpds |
|---|---|---|---|
| Δ_or expert − perm | 0.174 [0.115, 0.229] | 0.147 [0.094, 0.199] | 0.131 [0.079, 0.185] |
| Δ_or expert − shift | 0.202 [0.152, 0.254] | 0.192 [0.141, 0.248] | 0.206 [0.153, 0.260] |
| Δ_oe expert − E1 | 0.050 [0.011, 0.090] | 0.062 [0.021, 0.102] | 0.077 [0.037, 0.120] |
| Δ_oe expert − E1b | 0.106 [0.063, 0.148] | 0.091 [0.045, 0.135] | 0.088 [0.045, 0.130] |
| Δ_oe expert − E4 | 0.006 [−0.031, 0.045] | 0.007 [−0.032, 0.044] | 0.005 [−0.035, 0.044] |
| **Δ_oe expert − E4q** (new) | **0.016** [−0.023, 0.055] | **0.006** [−0.034, 0.047] | **0.012** [−0.029, 0.053] |

The 30 existing rows are identical after adding the E4q rows.

## 7. Negative and limiting results (all reported)
* No scattering advantage over STFT bands (H11a/b), and second-order information is below the 0.03 bar (H11c).
* SMO is unreliable on scattering features (platform-sensitive), so no SMO scattering number is evidence.
* External validation fails completely on the noisy neonatal subset, and is weak for silent defects (PFO ≈ chance), as
  expected for a murmur model applied to a CHD label.
* B0's external result is an artefact, not murmur detection.
* **G2 does not establish a shortcut-free advantage of E4q over a shortcut-aware whole-signal STFT baseline** (H12a CI lower
  bound −0.001). Removing the shortcut leaves E4's AUROC essentially unchanged (E4q ≈ E4) and removes its class-related
  missingness, and learned span selection clearly beats random selection (H12b). But the margin over W_stft + SC_q
  (+0.035 to +0.046) is not significant.
* Everything in Phase 3 was designed after Phase-1/2 results on the same CirCor folds; ZCHSound (G1a) is the only fully
  independent evaluation.
