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
