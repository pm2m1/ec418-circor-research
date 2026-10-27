# PROTOCOL_LOCKED — patient-level murmur detection on CirCor

Status: **LOCKED 2026-10-27, before any model in `scripts/05_*` was trained.**
Machine-readable copy: `configs/protocol.json`. Frozen folds: `configs/folds_patient_level.csv`
(sha256 `c4aa74c76946253bd3a5daa54d34ddfaa631d20405427993836ab247314e2339`, also in
`configs/folds_patient_level.sha256`). Any change after this point must be logged in the
"Amendments" section with a reason, and results produced before the change must be kept.

## 1. Primary clinical target
Binary **Murmur Present (positive, 1) vs Murmur Absent (0)** per patient.
This is murmur *detection*, not disease diagnosis. The clinical `Outcome` (Normal/Abnormal)
label is not present in the copy of the data we could obtain; the outcome study is deferred.

`Unknown` (68 patients) is **excluded** from the supervised task. Per the dataset documentation
it means the annotator could not characterise the murmur reliably — this can be audio quality
*or* clinical uncertainty, so it is neither merged into Absent nor treated as "noisy recording".

## 2. Dataset
PhysioNet/CinC 2022 training set = public portion of CirCor DigiScope: 942 patients, 3163
recordings, 4 kHz, 16-bit, mono. Binary task: **874 patients (179 Present / 695 Absent) in 816
canonical subjects**. See `docs/DATASET_AUDIT.md` for provenance and checksum status.

## 3. Evaluation unit and grouping
* Unit: **patient**. Every reported primary metric is computed on one score per patient.
* Group: `subject_id` = connected component of the `Additional ID` link graph (70 linked
  pairs; both patient IDs of a child always fall on the same side of every split).
* No recording, cardiac cycle, window, or derived row from a training subject ever reaches the
  corresponding test fold (asserted in code; 100 split checks pass).

## 4. Splits
* Outer: `StratifiedGroupKFold(5, shuffle=True, random_state=seed)`, seeds 0–4 (5 repeats ×
  5 folds = 25 test folds; each patient is tested exactly once per repeat).
* Inner: 3-fold StratifiedGroupKFold inside each outer training part — used **only** for
  decision thresholds.
* Repeats are **not** independent samples: statistics use repeat-averaged scores per patient
  and the subject bootstrap; the 25 fold-level values are only used for the sign-consistency rule.

## 5. Preprocessing (fixed, training-independent)
1. Read WAV; assert fs = 4000 Hz, mono, non-empty.
2. Resample to **2000 Hz** with `scipy.signal.resample_poly` (polyphase FIR, Kaiser-window
   anti-alias low-pass at the new 1 kHz Nyquist). Justification: clinically relevant PCG/murmur
   energy is below ~1 kHz in this cohort; halving fs gives 62.5 Hz packet bands at depth 4.
3. Zero-phase Butterworth band-pass 25–900 Hz, order 4 (`sosfiltfilt`).
4. Per-recording z-score.
No statistic is estimated across recordings or patients.

## 6. Wavelet settings
* Wavelet packet decomposition, depth **J = 4**, `mode='periodization'`, nodes taken with
  `order='freq'`. Nominal band width = fs/(2·2^J) = 2000/32 = **62.5 Hz**, 16 bands, 0–1000 Hz.
  (The earlier dossier's "125 Hz at 2 kHz, depth 4" was wrong; 125 Hz is the 4 kHz figure.)
* **Primary mother wavelet: db4**, fixed a priori (8 taps → best time localisation for 100–300 ms
  systolic intervals; leakage is acknowledged and measured in tests).
  db6, sym8, coif3 are a **sensitivity analysis only** — not used to pick a winner.
* B1 keeps the authors' own transform (their code uses an 8-tap **Symmlet-4** filter in a
  periodic DWT, although the paper text says "Daubechies 6").

## 7. Segmentation
The dataset `.tsv` S1/systole/S2/diastole annotations are used → every aligned result is
**oracle-segmentation-assisted** (expert-assisted labels at test time). A recording contributes
aligned features only if it has ≥ 40 systolic, ≥ 40 diastolic and ≥ 10 S1 level-4 columns
(8 ms each); otherwise its aligned features are missing (reported, not silently dropped).

## 8. Feature sets (recording level → patient level)
Patient vector = **[median, max] over that patient's recordings** for each feature (fixed).

| Set | Content | Rec. dims | Patient dims |
|---|---|---:|---:|
| B0 | 13 MFCC means, centroid, bandwidth, roll-off, ZCR, RMS-envelope CV | 18 | 36 |
| B1 | authors' features (entropy CV, slope, 6 multifractal; same 8 their demo uses) | 8 | 16 |
| W_stft | whole-signal: 16 log relative band energies, 16 log(q90/q50) burstiness, 2 entropies | 34 | 68 |
| W_wpd | same definitions on WPD energies | 34 | 68 |
| A_stft | cycle-aligned: 16 log(systolic band/S1 total), 16 log(systolic/diastolic band), 2 entropies | 34 | 68 |
| **P1 = A_wpd** | same definitions on WPD energies (**proposed**) | 34 | 68 |

The 2×2 {STFT, WPD} × {whole, aligned} design isolates the wavelet effect from the alignment effect
with identical band edges, time grid and dimensionality.

## 9. Classifiers (WEKA 3.9.7, fixed hyper-parameters, no tuning)
RF `-I 300 -K 0 -S 1` (**primary**); SMO linear `PolyKernel -E 1`, `-N 0 -M`; MLP `-L 0.1 -M 0.2 -N 300 -H a`;
Logistic `-R 1.0`. Python writes one train/test ARFF pair per fold (class `{Absent,Present}` last,
IDs never written as attributes); a single-JVM WEKA runner trains/predicts and writes per-row
probabilities. WEKA's own row-wise CV is never used for evaluation.

## 10. Metrics
Primary: patient AUROC; sensitivity at the **train-derived** threshold targeting specificity ≥ 0.80;
macro-F1 at that threshold. Secondary: accuracy, sensitivity, specificity, precision, F1, AUPRC,
official Challenge weighted accuracy (official function, binary encoding), threshold at max
inner-OOF weighted accuracy, fit/predict time, dimensionality. Confusion matrices always labelled
TP/FN/FP/TN with Present positive.

## 11. Hypotheses and decision rule
* H1 leakage: B1 + paper's SVM, recording-level metrics, random recording split vs grouped CV.
* H2 wavelet vs Fourier: A_wpd > A_stft (and W_wpd > W_stft).
* H3 alignment: A_wpd > W_wpd.
* H4 proposed vs baselines: A_wpd > max(B0, B1).

A contrast is **SUPPORTED** only if (RF) ΔAUROC ≥ 0.03, the subject-bootstrap 95 % CI excludes 0,
and Δ > 0 in ≥ 18/25 outer folds. Otherwise **NOT SUPPORTED**, reported unchanged.

## 12. Forbidden
Using test folds to select features, wavelet, depth, thresholds, hyper-parameters, aggregation, or
which result to report. Class balancing before splitting. Scaling fitted on all patients.

## Amendments
(none at lock time)
