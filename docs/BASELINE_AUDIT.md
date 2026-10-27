# BASELINE_AUDIT — Vimalajeewa, Lee & Vidakovic (2025), *Sci. Rep.* 15:10315

DOI 10.1038/s41598-025-93989-0 (registered with Crossref; 3 authors; vol 15, art. 10315, published
25 Mar 2025). Code: github.com/chihoon1/Murmur, commit `56b9846` (MIT), copied to
`references/baseline_repo/`. Logs: `results/logs/b1a_*.log`, `b1_realign.log`, `h1_leakage_b1.log`.

## 1. Published method vs released code

| Item | Paper (text) | Released code (inspected) |
|---|---|---|
| Target | murmur present vs absent | Present = 1 ("Case"), Absent = 0 |
| Data | 2547 "absent" + 616 present signals | 616 Present recordings; **2547 = 2391 Absent + 156 Unknown recordings** in the multifractal table |
| Unknown | not stated | silently placed in the control class (multifractal table) |
| Unit | not stated | **recording**; `train_test_split` on rows → patient overlap |
| Pre-processing | normalise to [-1,1], truncate to 2^⌊log2 N⌋ | `(x-mean)/max|x|`, truncate — matches |
| Window | 1024 samples (256 ms) | 1024 — matches |
| Wavelet | "Daubechies 6" | hard-coded 8-tap filter = **Symlet-4** (identical to `pywt sym4` dec_lo to 1e-12; db6 has 12 taps) |
| Features | slope, entropy CV, 8 multifractal (10) | demo uses 8 (drops Broadness, Right Tangent) |
| Best model | SVM RBF, kernel scale 0.1, C 100, class weights 1:4 | demo `SVC(C=100, gamma=0.1)`, `class_weight='balanced'` (≈1:4.1) |
| Scaling | – | none in demo; `MinMaxSclProcess` elsewhere fits on train+test |
| Split | 80/20 (+ inner 80/20) | 80/20 random rows, `random_state=0` |
| Reported | Acc 76.61 %, Sens 82.12 %, Spec 54.02 %, AUC 0.741 | – |
| Sens/Spec definition | not stated | code: sensitivity = recall(Present), specificity = recall(Absent) |

## 2. Defect found in the released feature tables (verified)
`Window_Entropy/Slope_Control.csv` hold **2391** rows (Absent only) while `Window_Mf_Control.csv`
holds **2547** rows (Absent + Unknown, IDs in column 0). The demo joins them **by row position**:
* **2375 of 2391 control rows combine entropy/slope from one recording with multifractal features of
  another recording**;
* the last 156 control rows (Unknown recordings) receive **mean-imputed** entropy/slope, all labelled control.

Verification: I wrote an exact NumPy port of the authors' `dwtr.m` and wavelet-entropy code
(`src/ec418/wavelets/dwtr_port.py`; reproduces the `dwtr.m` doc example) and recomputed the
entropy-CV feature for 100 random recordings. **Re-aligned rows match the shipped values to ≤ 4.5e-15
relative error (100/100); the demo's positional pairing is off by a median 31 %.**
`data/processed/rec_features_B1.csv` holds the corrected, per-recording B1 features (3007 rows).

## 3. Reproduction (B1-A, original recording-level protocol)
All with the paper's SVM (RBF, C = 100, γ = 0.1). Recording-level metrics, Present = positive.

| Run | Acc | Present recall | Absent recall | AUC | test recordings whose patient is in train |
|---|---|---|---|---|---|
| Paper (reported) | 0.766 | "sens" 0.821 | "spec" 0.540 | 0.741 | not reported |
| Authors' demo, shipped features, as released (1 run) | 0.720 | 0.513 | 0.768 | 0.704 | – |
| Shipped (buggy) features, weights 1:4, 10 seeds | 0.749 ± 0.018 | 0.560 ± 0.038 | 0.795 ± 0.024 | 0.738 ± 0.014 | 95.8 % of patients |
| **Corrected features, weights 1:4, 25 seeds** | **0.770 ± 0.014** | **0.541 ± 0.031** | **0.828 ± 0.019** | **0.738 ± 0.017** | 95.8 % |

**Numerical reproduction: achieved** for accuracy (0.770 vs 0.766) and AUC (0.738 vs 0.741), using the
authors' own feature values and code-level settings (I could not run their MATLAB; the features are
theirs).

### Sensitivity / specificity (Issue D)
With 616 Present and 2547 control recordings, the reported pair is internally inconsistent with the
reported accuracy if sensitivity means Present recall:
* Present recall 0.8212 & Absent recall 0.5402 → accuracy = (0.8212·616 + 0.5402·2547)/3163 = **0.595**;
* swapped (Absent recall 0.8212, Present recall 0.5402) → **0.7665** = the reported 76.61 %.
Both reproductions give Absent recall ≈ 0.80–0.83 and Present recall ≈ 0.54–0.56.
**Conclusion (evidence-based, not proven):** the published "sensitivity 82.12 %" is consistent with
recall of the *Absent* class and "specificity 54.02 %" with recall of the *Present* class. The true
murmur sensitivity of this model under its own protocol is ≈ 0.54. I did not see the paper's tables
(only the text), so this should be phrased as "appears to be" and confirmed with the authors.

## 4. Patient-independent evaluation of the same features (B1-B)
Same features, same SVM, only the split changed to subject-grouped 5-fold × 5 repeats:

| Protocol | AUC (recording level) | Present recall | Absent recall |
|---|---|---|---|
| A random recording split (25 seeds) | 0.738 ± 0.017 | 0.541 | 0.828 |
| B subject-grouped CV (25 folds) | 0.724 ± 0.048 | 0.519 | 0.822 |

ΔAUC = **+0.015** (indicative 95 % CI −0.004 to +0.035). **H1 (leakage inflates this baseline) is NOT
supported at the pre-registered 0.03 threshold.** Honest reading: this particular feature set carries
little patient-identity information, so the recording split is not what makes the paper's numbers
look good — the problems are the feature misalignment / Unknown contamination and the metric labelling.
Patient-level (max over a patient's recordings) under protocol B: AUC 0.752 ± 0.052, Present recall
0.725, Absent recall 0.612 (at the SVM's default decision threshold).

## 5. Deviations from an exact reproduction
* MATLAB was not run; I reused the authors' MATLAB-computed values and verified one feature family
  (entropy CV) with an exact port. Slope and multifractal values were not independently recomputed
  (they are aligned through the verified ID sequence in the multifractal table).
* Inner 80/20 validation and grid search from the paper were not repeated; the paper's final
  hyper-parameters were used directly.
* sklearn 1.9.1 vs the authors' (unknown) version; SVM decision function used for AUC.

## 6. B1 inside the main patient-level WEKA study
See `docs/PILOT_RESULTS.md` (feature set `B1`, 16 patient features = median & max of the 8 used features).
