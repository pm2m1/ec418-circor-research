# PROTOCOL_V2_LOCKED — Phase 2 (pre-registered 2026-10-27, before any Phase-2 code was run)

Machine-readable copy: `configs/protocol_v2.json` (hash in `configs/protocol_v2_lock.sha256`).
Phase-1 results are frozen and unchanged: git tag `v1.0-pilot`, checksums in
`results/v1_freeze/MANIFEST_v1.sha256`. Wording corrections after external review: `docs/ERRATA_v1.md`.

## Working title
**Physiology-Aligned Multiresolution Analysis for Patient-Independent Heart-Murmur Detection:
A Comparative Study of Wavelet and Fourier Features**

## Research question
Does **cardiac-cycle timing alignment** improve patient-independent murmur detection, and does the
**wavelet vs Fourier** choice matter once alignment is controlled?

## What does not change from v1
Data, labels (Present vs Absent; Unknown excluded), subject grouping, the **same frozen folds**
(sha256 `c4aa74c7…2339`), preprocessing, WPD/STFT settings, the 34 aligned feature definitions,
patient aggregation, inner-fold thresholds, metrics, subject bootstrap, decision rule
(Δ ≥ 0.03, CI lower bound > 0, ≥ 18/25 folds). RF primary, SMO secondary.

Representations: `stft`, `wpd` (raw db4, as v1), and **`wpds` = db4 energies smoothed with the STFT's
64-sample Hann window — pre-registered now** (it was post-hoc in v1).

## E2 — Does timing alignment itself help? (run first)
Same extractor and same feature definitions; only the S1/systole/S2/diastole labels change.

| Condition | Labels | Purpose |
|---|---|---|
| `true` | expert `.tsv` | as v1 |
| `perm` (**primary null**) | each recording's column labels randomly permuted (seed = crc32(rec_id)) | same label counts and coverage, **no timing** — the "matched whole-signal statistics" control |
| `shift` (secondary null) | label sequence circularly shifted by u·T, u ~ U(0.2, 0.8), T = median S1-to-S1 interval | keeps contiguity/periodicity, wrong phase. Caveat: shifts near 0.5T can partly invert systole/diastole |

Because `perm` and `shift` keep each recording's annotation coverage, they also control for the
coverage shortcut (coverage alone: AUROC 0.56).

* **H5a/b/c:** AUROC(`true`) − AUROC(`perm`) ≥ 0.03 for `wpd` / `stft` / `wpds` (RF).
* **H5d (secondary):** same against `shift`.
* If not supported: the v1 gain is attributed to feature definitions/normalisation, **not** physiological timing.

## E1 — Does it survive without the expert segmentation?
Unsupervised segmenter, every constant fixed now, no murmur labels and no expert `.tsv` used:
1. Homomorphic envelope of the 25–400 Hz band (|Hilbert| → log → 8 Hz low-pass → exp, 50 Hz).
2. Heart period T = envelope autocorrelation peak in [0.3, 1.5] s (40–200 bpm, paediatric range).
3. Peaks = envelope maxima, spacing ≥ 0.2·T, height ≥ 25th percentile of the envelope.
4. Consecutive peak intervals paired; the shorter of each pair = systole (S1→S2), longer = diastole.
5. S1/S2 extent = region around the peak where envelope ≥ 50 % of peak, clipped to 40–160 ms.

Segmentation is evaluated against the expert `.tsv` (inside annotated spans only): S1 and S2 centre
F1 at ±50 ms, and frame-wise 4-state accuracy. Constants may be changed **only** on segmentation
metrics and only as a logged amendment before classification is re-run.

* **H6a:** AUROC(`auto`, wpd) ≥ AUROC(`true`, wpd) − 0.03.
* **H6b:** AUROC(`auto`, wpd) > AUROC(B1), subject-bootstrap CI lower bound > 0.
* **H6c:** same for `stft` and `wpds`.
* If S1/S2 F1 < 0.70, results are still reported, flagged as low-quality segmentation.

## E3 — Soft murmurs (optional, only if E1 + E2 are done by 30 Oct)
Add one feature: log(systolic / S1 energy in 62.5–187.5 Hz). **H7:** grade-I/VI sensitivity at the
spec80 operating point rises by ≥ 0.05 with overall RF AUROC no lower than v1 − 0.01.

## E1b — Standard segmenter: logistic-regression HSMM (pre-registered 2026-10-27 22:35 IST)
**Designed after the E1 results were known** (E1 segmenter S1/S2 F1 0.510/0.493, flagged low quality; all H6
NOT SUPPORTED; `docs/E1_RESULTS.md`). E1 and its segmenter are unchanged and stand as reported. E1b asks whether a
standard, trained segmenter recovers the expert-label performance. Machine-readable copy:
`configs/protocol_v2.json` → `E1b_lr_hsmm_segmentation` (sha256 of the updated file in `configs/protocol_v2_e1b.sha256`).

**Source.** Springer, Tarassenko & Clifford, "Logistic Regression-HSMM-based Heart Sound Segmentation", IEEE TBME
63(4):822–832, 2016, and the authors' MATLAB reference code (PhysioNet `hss` v1.0, DOI 10.13026/vnt9-kf93,
**GPL-3.0**). Existing Python implementations checked: `EchoStatements/Springer-Segmentation-Python` (no licence →
not used); `pyPCG-toolbox` 0.1b5 (GPL-3.0-only, but model training not implemented → not usable). E1b is therefore a
Python port of the paper/reference code in `src/ec418/segmentation/lr_hsmm.py`, licensed GPL-3.0.

**Fixed from the paper / reference code (no tuning):** audio resampled 4 kHz → 1 kHz; Butterworth order-2 low-pass
400 Hz and order-2 high-pass 25 Hz (zero-phase); Schmidt spike removal (500 ms windows, 3 × median MAA); four
features at 50 Hz, each z-scored per recording: homomorphic envelope (order-1 8 Hz low-pass), Hilbert envelope,
40–60 Hz PSD (spectrogram, 25-sample Hamming window, 13-sample overlap, 1-Hz bins), and |level-3 detail| of an
`rbio3.9` DWT (coefficients repeated 2³ times, central part kept); one binary logistic regression per state
(unpenalised, state vs. an equal-size random sample of the other three states, as `trainBandPiMatricesSpringer`);
emission = P(state | o)·N(o; μ, Σ)/π with π = 0.25 and μ, Σ over all training samples; deterministic cycle
S1 → systole → S2 → diastole; Gaussian state durations truncated to [mean − 3 SD, mean + 3 SD] (systole: ±3(SD_sys + SD_S1);
S1/S2 lower bound ≥ 1 sample), normalised over 1…D with D = round(T·50); Springer's extended duration Viterbi
(`viterbiDecodePCG_Springer`, segments may start before / end after the recording); per-recording heart period T and
systolic interval from the autocorrelation of the 1 kHz homomorphic envelope (`getHeartRateSchmidt`).
Two numerical substitutes: features resampled with `scipy.signal.resample_poly` (Kaiser, as MATLAB `resample`); the PSD
series is brought to the envelope length by linear interpolation.

**Learned from the training annotations only (paediatric, replaces the adult defaults):** S1 and S2 duration mean and
SD (rounded to 50 Hz samples as in the reference; SD ≥ 1 sample); systole SD = pooled within-recording SD of expert
systole durations; diastole SD = a·mean_diastole + b with (a, b) from an OLS fit of within-recording SD on
within-recording mean diastole duration (SD ≥ 1 sample); mean_systole = systolic interval − mean S1, mean_diastole =
T − systolic interval − mean S2 (as the reference, with learned means); heart-period search range = [1st, 99th]
percentile of the training recordings' median S1-onset-to-S1-onset interval (replaces 0.5–2 s); systolic-interval
search range = [1st, 99th] percentile of the per-recording ratio median(S1→S2 onset)/median(S1→S1 onset), times T
(replaces 0.2 s … T/2). Training samples = 50 Hz feature samples inside valid expert rows (labels 1–4).

**No leakage.** For each outer fold (repeat r, fold k) of the frozen folds:
* test patients are decoded by a segmenter trained on all training patients of (r, k), without reading their `.tsv`;
* training patients (classifier training and inner-fold thresholds) are decoded by cross-fitting over the 3 frozen inner
  folds of (r, k): patients of inner fold i by a segmenter trained on the other training patients;
* so every feature the classifier sees comes from a segmenter that never saw that patient's annotation. Unknown-murmur
  recordings (not classified) are decoded by one segmenter trained on all 874 binary-task patients, for the
  segmentation report only. Random seed for the balanced sampling: 1000·r + 10·k + i (i = 0 outer, 1–3 inner);
  Unknown model: seed 9999.

**Segmentation report (as E1):** S1/S2 centre F1 at ±50 ms, frame-wise 4-state accuracy, failure fraction (no
segments), by Present/Absent/Unknown and v1.0.3 age, on the test-fold decodings (primary: repeat 0, each recording once;
the other repeats' overall values also reported). Low-quality flag if S1 or S2 F1 < 0.70.

**Classification:** the same 34 aligned features for `stft`, `wpd`, `wpds` (same extractor, coverage minimum, patient
median + max), WEKA RF (primary) and SMO (secondary), frozen folds, tag `e1b`, fold-specific feature files.
* **H8a:** RF AUROC(auto-HSMM, wpd) ≥ AUROC(expert, wpd) − 0.03 (expert = `E2_wpd_true`).
* **H8b:** RF AUROC(auto-HSMM, wpd) > AUROC(B1) with subject-bootstrap 95 % CI lower bound > 0.
* **H8c:** H8a and H8b for `stft` and `wpds`.
Same statistics as E1 (repeat-averaged scores, 2000 subject resamples, seed 2; both AUROC summaries; fold counts reported).
Descriptive: vs W_stft and vs the E1 auto sets; sensitivity by murmur grade.

**Runtime rule (decided on timing only, before the run):** time the segmenter on ~50 recordings and estimate the full
25-fold cost. If it exceeds ~4 h on this Mac, a dated amendment reducing E1b to **repeat 0 only (5 folds)** is committed
before running, with repeat-0 expert-label, B1, W_stft and E1 results as comparators; the results will say so.
**Timebox:** if E1b classification is not complete by **2026-10-30 23:59 IST**, it is stopped and reported as incomplete.

## Diagnostics D1–D3 — span selection vs timing (pre-registered 2026-10-27 23:05 IST)
(Unrelated to the data-version amendments D1/D2.) **Designed after the E1b results were known** and after erratum E2-1
(`docs/ERRATA_PHASE2.md`). **All three use the expert annotation of the test recordings at test time. They are
DIAGNOSTICS ONLY, never deployable, and carry no pass/fail threshold**: descriptive decompositions, every number
reported. Machine-readable: `configs/protocol_v2.json` → `diagnostics_D1_D3` (hash in `configs/protocol_v2_diag.sha256`).

"Expert-annotated columns" = level-4 columns whose expert label (`column_labels` of the expert `.tsv`, exactly as the
E2 `true` arm) is 1–4; label-0 columns are unannotated.
* **D1 — HSMM timing inside the expert spans.** The E1b fold-wise LR-HSMM labels (same models and seeds; test
  patients from the outer model, training patients cross-fitted; re-decoded deterministically and checked identical to
  the saved E1b test decodes) with every expert label-0 column set to 0, then the same 34 aligned features.
  *Question:* with the expert span selection, does automatic timing recover the expert-label result?
* **D2 — within-span timing null.** The expert labels permuted only among the expert-annotated columns
  (`np.random.default_rng(zlib.crc32(rec_id)).permutation`, the `perm` seed rule); label-0 columns stay where they are.
  Same 34 aligned features. *Question:* does timing matter once the span selection is held fixed?
* **D3 — pure selection, no timing.** The whole-signal feature definitions (`whole_features`, as W_stft / W_wpd_db4 /
  W_wpd_db4_smooth) computed only on the expert-annotated columns (for wpds the 4-tap smoothing is applied to the full
  map first, as in v1). Recordings without annotated columns → missing. *Question:* how much is just "use the clean
  parts"?

Representations `stft`, `wpd`, `wpds` for all three. WEKA RF (primary) and SMO (secondary), frozen folds, tag `diag`
(sets D1_/D2_/D3_<rep>, D1 fold-specific; plus W_wpd_db4_smooth on the committed features as the Mac comparator).
Comparators from the same Mac: expert-true = `E2_<rep>_true`, E2 perm = `E2_<rep>_perm` (tag `e2`), HSMM-full =
`E1b_<rep>_auto` (tag `e1b`), W_stft / W_wpd_db4 (tag `e1`).
**Reported:** repeat-averaged AUROC with subject-bootstrap 95 % CI (2000, seed 1) and mean of repeats for every set;
paired contrasts Δ = AUROC(a) − AUROC(b) on repeat-averaged scores, subject-bootstrap CI (2000, seed 2), folds Δ > 0:
(1) expert-true − D1, (2) expert-true − D2, (3) D3 − whole-signal on the full recording (same representation),
(4) D1 − HSMM-full; plus, for the plain decomposition, D2 − E2 perm, using the exact identities
true − perm = (true − D2) [within-span timing] + (D2 − perm) [span selection without timing] and
true − HSMM-full = (true − D1) [timing error inside the spans] + (D1 − HSMM-full) [span selection with HSMM timing].

## Equivalence reporting
For `wpds` vs `stft` (aligned, `true`): report Δ and 95 % CI; claim "no meaningful difference" only if
the entire CI lies within ±0.03.

## Forbidden (in addition to v1)
Re-choosing segmenter constants, null definitions or representations after seeing E1/E2
classification results. Every outcome is reported, including negative ones.

## Schedule
E0 provenance check on the Mac (PhysioNet SHA256SUMS) — any time before 30 Oct ·
E2 27–28 Oct · E1 28–29 Oct · E3 30 Oct if time · **results freeze 31 Oct** · writing 31 Oct–2 Nov ·
submission 3 Nov.

## Amendments
(none at lock time)

* **I1 (2026-10-27, implementation clarification for E2, written and committed before any E2 extraction or
  WEKA run; no constant, null definition, representation or decision rule changed).** Code:
  `src/ec418/features/label_nulls.py`, `scripts/15_e2_extract_label_nulls.py`, `scripts/16_e2_analyze.py`.
  1. Both nulls act on the per-column label vector from `column_labels` (level-4 columns, 8 ms) — the exact
     vector the `true` arm feeds to `aligned_features`. `perm` permutes the whole vector, unannotated (0)
     columns included, so every label count equals `true`.
  2. `shift`: S1 events = starts of contiguous runs of label 1 in that vector; T = median onset-to-onset
     difference in columns (0.6 s = 75 columns if < 2 S1 events); shift = round(u·T) columns, applied with
     `np.roll` (forward, circular).
  3. Seeding: each null uses its own `np.random.default_rng(zlib.crc32(rec_id.encode()))`; `perm` takes
     `.permutation(labels)`, `shift` takes one `.uniform(0.2, 0.8)` draw.
  4. One label vector per recording serves `stft`, `wpd` and `wpds` (column counts are identical; asserted).
     `wpds` uses the v1 kernel `hanning(6)[1:-1]`, normalised (4 taps over level-4 columns = 64 samples).
  5. The `true` arm is re-extracted by the same code path (feature names as v1) and checked against the
     frozen v1 features; all nine sets run under the new tag `e2` (RF + SMO, frozen folds, `scripts/06`).
  6. The decision-rule Δ is the AUROC of repeat-averaged patient scores (as `scripts/07` did for v1); the
     mean-of-repeats Δ is reported alongside and labelled.
  Checked against `configs/protocol_v2.json` (unchanged, sha256 = `configs/protocol_v2_lock.sha256`): no
  constant, null definition, representation or decision rule differs. Item 3 interprets "from the same seeded
  RNG" as "a generator seeded identically (crc32(rec_id))", not as continuing the `perm` generator's stream.

* **D1 (2026-10-27, data version; written and committed before any Phase-2 run on new data).**
  Reason: E0 (`docs/PROVENANCE_PHYSIONET.md`) verified the official PhysioNet CirCor **v1.0.3** download
  (10,434/10,434 files match physionet.org's `SHA256SUMS.txt`; files fetched from PhysioNet's AWS Open Data
  mirror) and found header differences from the Phase-1 copy (Challenge-2022 redistribution). Decision: **all
  Phase-2 runs use v1.0.3 exactly as downloaded** (the download folder is never edited). Differences from the
  Phase-1 copy:
  (a) `50782.txt` now lists `50782_MV_1.tsv` (bytes identical to the copy's misnamed `50782_MV.tsv`), so
      recording 50782_MV_1 has its expert segmentation; this changes the aligned features of 1/874
      binary-task patients (50782, Absent). Whole-signal sets, B0, B1, labels and folds are unaffected.
  (b) 73 `#Age` categories differ; age is not used by any feature, model or analysis.
  (c) `#Outcome` is now present but is **not** added to Phase 2; any outcome analysis needs its own later
      amendment.
  The like-for-like Phase-1 reproduction on the Mac (`docs/REPRO_MAC.md`) uses a separate gitignored view
  (v1.0.3 symlinks + the Phase-1 copy's `50782.txt`) and is not a Phase-2 run.

* **D2 (2026-10-27, correction of D1(a); D1 is left as written; committed before any Phase-2 run).**
  Reason: running the v1.0.3 audit showed that v1.0.3's `50782_MV_1.tsv` is a degenerate 6-byte file
  (`0\t0\t28`: zero length, invalid label 28), so it adds no annotated columns. 50782_MV_1 has **no aligned
  features on either data version**, and Phase-2 aligned features are identical to Phase 1 for all 874
  binary-task patients (verified: `seg_coverage` 0/0/0, `A_wpd`/`A_stft` None on v1.0.3). The statement in
  D1(a) that the aligned features of 1/874 patients change is therefore wrong. `scripts/01_dataset_audit.py`
  now skips segmentation rows with a label outside 0–4 or end ≤ start and lists them (v1.0.3: 16 rows — this
  one plus 15 zero-length label-0 rows, which add 0 s to every duration); its v1.0.3 output goes to
  `results/tables/v103_*.csv` and `results/logs/dataset_audit_v103.json`. No feature or model code changed.

* **I2 (2026-10-27, implementation clarification for E1; written and committed after the segmentation metrics
  and before any E1 classification run; no segmenter constant, hypothesis or decision rule changed).**
  Code: `src/ec418/segmentation/autoseg.py`, `scripts/18_e1_autosegment.py`, `19_e1_extract_auto_features.py`,
  `20_e1_analyze.py`. Pre-registered constants used unchanged: 25–400 Hz band, 8 Hz envelope low-pass, 50 Hz
  envelope, T in [0.3, 1.5] s, peak spacing ≥ 0.2·T, height ≥ 25th percentile, sound extent ≥ 50 % of peak clipped
  to [40, 160] ms. Details the protocol leaves open, fixed here:
  1. Filters: 25–400 Hz Butterworth order 4, zero-phase (as the v1 band-pass); 8 Hz Butterworth order 1,
     zero-phase (Springer et al. homomorphic envelope); log(|Hilbert| + 1e-12); 50 Hz = every 40th sample.
  2. T = highest *local* maximum of the normalised autocorrelation of the mean-removed envelope at lags 15–75
     (0.3–1.5 s); no local maximum → failure.
  3. "Consecutive intervals paired" = non-overlapping pairs (d0, d1), (d2, d3), …; shorter = systole, longer =
     diastole; equal or unpaired → 0; an interval with the same state as a neighbour (alternation broken) → 0.
     A peak is S1 if it starts a valid systole or ends a valid diastole, S2 in the opposite case.
  4. Sound extent: walk from the peak while envelope ≥ 50 % of the peak; < 40 ms → widened symmetrically to 40 ms,
     > 160 ms → peak ± 80 ms; overlapping sounds split at the midpoint of their peaks; systole/diastole fill the
     gap between the two sounds of a valid interval. Failure (flat/too short, no period, < 3 peaks, no valid
     pairing) → no segments (all labels 0). There is **no periodicity gate**, so irregular rhythms are not forced
     to all-zero (the unit test checks only that such input does not crash).
  5. Evaluation (inside expert-annotated spans = merged valid expert rows with labels 1–4): centre = segment
     midpoint; one-to-one greedy matching at ±50 ms; pooled TP/FP/FN; frame accuracy on the 8 ms column grid over
     expert-labelled columns; failure = no segments. Low-quality flag if S1 or S2 F1 < 0.70.
  6. Classification: tag `e1` = `E1_{stft,wpd,wpds}_auto` + `B1`, `W_stft`, `W_wpd_db4` (committed features,
     unchanged on v1.0.3), RF + SMO, frozen folds. `true` = `E2_<rep>_true` from tag `e2`. Δ = AUROC of
     repeat-averaged scores; H6a/H6c(a): Δ(auto − true) ≥ −0.03; H6b/H6c(b): Δ(auto − B1) > 0 and subject-bootstrap
     CI lower bound > 0; fold counts and both AUROC summaries reported; whole-signal comparison and grade
     sensitivity descriptive.
  Segmentation metrics seen before this amendment (`results/logs/e1_segmentation.json`): S1 F1 0.510, S2 F1 0.493,
  frame accuracy 0.325, failures 11/3163 → **flagged low-quality segmentation**; per protocol, E1 continues with
  the constants unchanged. Unit tests also show the locked peak rule is noise-sensitive: noise-free synthetic PCG
  is segmented correctly, but 0.1 % white noise already adds envelope peaks inside diastole.

* **E3-drop (2026-10-27 22:35 IST).** E3 (soft murmurs, H7) is **not run**. Reason: time, and E1 showed that
  segmentation is the bottleneck, so the remaining effort goes to E1b (pre-registered above, designed after E1).
  No E3 result exists or will be reported as such.
* **Lock-file note (2026-10-27).** `configs/protocol_v2.json` gains the E3-drop status and the E1b section; its
  lock-time hash stays in `configs/protocol_v2_lock.sha256` (= tag `protocol-v2-lock`), the updated hash is in
  `configs/protocol_v2_e1b.sha256`. Earlier statements "protocol_v2.json unchanged" (I1) refer to the lock-time file.
