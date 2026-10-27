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
