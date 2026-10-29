# GO / NO-GO — CirCor wavelet murmur project (decision of 2026-10-27)

> **Historical phase document — superseded by later experimental results.** Covers the end of Phase 1 (validation pilot, 2026-10-27). Its conditional GO and its listing of automatic segmentation as future work were correct at that time; "verify on Mac" was later done (official PhysioNet v1.0.3 verified, `docs/PROVENANCE_PHYSIONET.md`, amendments D1/D2), and automatic segmentation was then tested in Phase 2 (E1, E1b, E4, S1). Current status: [`RESULTS_SUMMARY.md`](RESULTS_SUMMARY.md), [`P3_RESULTS.md`](P3_RESULTS.md), [`INDEX.md`](INDEX.md). The historical content and results below are unchanged.

## Decision: **CONDITIONAL GO** — stay on CirCor, but change the claim

The project is feasible and already produces a defensible result. But the originally proposed
contribution ("cycle-aligned **wavelet-packet** features + **wavelet quality gating** improve murmur
detection") did not hold up in the parts that were specifically about wavelets. Proceed with a
re-framed, reduced scope. Do not switch to ICBHI: nothing in CirCor failed.

## Gate-by-gate evidence
| Gate | Result | Evidence |
|---|---|---|
| Data accessible | **PASS (verify on Mac)** | Full public set obtained via the baseline repo; 10,433/10,434 PhysioNet checksums match; re-download from PhysioNet on the Mac to confirm (DATASET_AUDIT §1) |
| Labels interpretable | **PASS** | Murmur labels from checksum-verified headers; semantics documented; Unknown excluded |
| Patient grouping reliable | **PASS** | 70 symmetric linked pairs → 816 subjects in the binary task; 100 leakage assertions pass |
| Wavelet features reproducible | **PASS** | deterministic extraction, 0 errors; band math & packet order unit-tested |
| WEKA works on real features | **PASS** | 3,200 WEKA train/test jobs via CLI/JVM runner, plus a logged plain `weka.classifiers.trees.RandomForest -t -T` run |
| Meaningful baseline works | **PASS** | 2025 Sci Rep baseline reproduced (acc 0.770 vs 0.766, AUC 0.738 vs 0.741) using the authors' own features |
| No critical leakage | **PASS** | subject-grouped folds; IDs never predictors; thresholds from inner folds only; oracle segmentation disclosed |
| Fits deadline | **PASS** | full study re-runs in < 2 h on 2 cores; 6 days left |
| Proposed wavelet advantage | **FAIL** | WPD < matched STFT (−0.017 aligned, −0.066 whole); no gain after smoothing either |
| Wavelet quality gating | **FAIL** | wavelet SQI (0.689) < simple spectral gate (0.779) at flagging Unknown; abstention gain negligible |
| Outcome (diagnosis) task | **BLOCKED** | Outcome field absent from the obtainable copy |

"CONDITIONAL" because: the wavelet-specific claims must be dropped/re-framed, the quality-gating arm is
removed, the outcome study is deferred, and the baseline was reproduced from the authors' MATLAB outputs
(not re-run in MATLAB).

## What the project now claims (all already measured)
1. **Reproducibility audit of a 2025 *Scientific Reports* wavelet murmur detector:** released features are
   row-misaligned for the control class and include Unknown recordings as controls; reported sensitivity
   and specificity appear swapped (true murmur sensitivity ≈ 0.54); fixing the split changes AUC by only
   +0.015.
2. **Patient-level, leakage-controlled WEKA comparison** of six feature families on 874 patients:
   the cycle-aligned band-feature pipeline beats the corrected 2025 baseline (+0.072 AUROC, CI +0.027…+0.122, 24/25 folds).
3. **2×2 ablation on "do wavelets matter?":** the aligned pipeline adds +0.06–0.11 AUROC over the
   whole-signal pipeline (feature definitions differ, so this is not yet attributable to alignment alone);
   wavelet packets add nothing over Fourier bands with matched nominal bands (and lose when packet energies
   are not smoothed).
4. **Failure analysis:** soft (grade I/VI) and low-pitch murmurs are detected only ~35–54 % of the time at
   80 % specificity.

That still satisfies the brief: wavelet analysis (DWT/WPD, with correct band maths), WEKA classifiers,
a 2024–26 journal comparison with a demonstrated, properly evaluated improvement, and the full metric set.
The honest headline is "**the cycle-aligned pipeline helps; the wavelet does not, by itself**" — present it
that way, and treat "timing alignment is the cause" as the hypothesis tested in Phase 2. Examiners
will respect a correctly designed ablation more than an unsupported "our wavelet method is better".

## Strongest argument against continuing
P1 (WPD) is not even the best model in its own study — aligned STFT is (0.812 vs 0.793). If the grading
rubric rewards "a wavelet method that beats everything", this project cannot honestly deliver that. And all
aligned results rely on oracle segmentation; until Experiment 1 below is done, the improvement is not a
deployable one.

## Next three experiments (in priority order)
### E1 — Remove the oracle (automatic segmentation) — most important
* **Hypothesis:** aligned features keep most of their advantage with automatic S1/S2 segmentation.
* **How:** implement a published, simple segmenter (Shannon-energy envelope + heart-rate autocorrelation,
  e.g. following Arjoune et al. 2024 IEEE Access or Springer's HSMM), output a `.tsv` in the same format,
  then rerun extraction and WEKA with identical folds:
  ```bash
  .venv/bin/python scripts/11_auto_segment.py          # TO WRITE (~1 day): writes data/interim/autoseg/*.tsv
  SEGDIR=data/interim/autoseg .venv/bin/python scripts/02_extract_features.py   # needs a SEGDIR switch (small edit)
  .venv/bin/python scripts/06_run_patient_level_weka.py autoseg A_stft_auto,A_wpd_db4_auto RF,SMO 2
  ```
* **Success:** auto-aligned RF AUROC ≥ oracle − 0.03 **and** > B1 with CI excluding 0.
* **Failure:** drop below B0 (0.743) → report "alignment benefit depends on expert segmentation".
* Also report segmentation F1 against the dataset `.tsv` (±40 ms tolerance).

### E2 — Re-verify data from PhysioNet and add the Outcome task (Mac, ~1 h)
* Download v1.0.3 on the Mac, compare SHA256SUMS, rerun `01`→`07`. Results must be identical for murmur.
* Secondary target Outcome (Normal/Abnormal) with the same features/folds; **success:** pipeline runs and
  metrics are reported with the Challenge cost metric; no improvement claim pre-committed.

### E3 — Fold-internal interpretability + targeted fix for soft/low-pitch murmurs
* Within each training fold only, rank features (WEKA `InfoGainAttributeEval`/RF impurity) and report which
  bands drive decisions; check stability (top-10 overlap ≥ 70 % across folds = success).
* Pre-register one targeted feature (e.g. systolic energy in 62.5–187.5 Hz normalised by S1 energy in the
  same bands) and test only its effect on grade-I/VI sensitivity at 80 % specificity. **Success:** +0.05
  sensitivity on I/VI with overall AUROC not lower than 0.79; otherwise report as negative.

## Fallback
ICBHI 2017 remains the fallback only if E2 reveals the obtained copy is not the PhysioNet data. Before
using ICBHI, audit its official split for patient overlap (community repos report 2 shared patients).
