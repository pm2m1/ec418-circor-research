# PROTOCOL_V3_PREREG — Phase 3 (pre-registered 2026-10-28, before any Phase-3 analysis was run)

Written in the claude.ai validation workspace and committed there before any Phase-3 code ran (commit hash and
UTC time in `configs/protocol_v3_lock.sha256`). To be copied unchanged into the main repository
(`pm2m1/ec418-circor-research`) as a dated Phase-3 section. Phase-3 work was designed **after** all Phase-1/2
results were known (including E4 and S1); it is labelled exploratory-confirmatory, not a fresh study.

Machine-readable copy: `configs/protocol_v3.json`.

Fixed from earlier phases: preprocessing (2 kHz, 25–900 Hz Butterworth, z-score), patient aggregation
[median, max], frozen CirCor folds (sha256 `c4aa74c7…2339`), WEKA 3.9.7 RF (primary) / SMO (secondary) with the
same options, subject-level bootstrap (2000), decision rule "Δ ≥ 0.03, CI lower bound > 0, Δ > 0 in ≥ 18/25 folds"
for internal contrasts. Present = positive.

---------------------------------------------------------------------------------------------------------------
## G1 — External validation on ZCHSound (independent paediatric CHD cohort)

**Data.** ZCHSound (Jia et al., IEEE TBME 71(8):2278–2286, 2024), GitHub `WeiJieOvO/ZCHSound-Dataset`,
`ZCHSound.zip` sha256 `112432cb10c5ab768cabf217f0a090a20bd0102b093d8b42dbdabc19e39b58b7`.
Clean set: 941 children (NORMAL 533, VSD 187, ASD 119, PFO 70, PDA 32), one ~20 s recording each, left sternal
border 2nd–3rd intercostal space, 8 kHz. Noisy set: 318 neonates ≤ 5 days (NORMAL 160, ASD 102, PFO 35, VSD 14, PDA 7).
Diagnosis = echocardiography-confirmed CHD subtype. **The label is CHD, not murmur**: PFO and many ASDs are
acoustically silent; in neonates PFO/PDA can be normal transitional physiology.

**Processing.** Channel 0 (stereo files have identical channels), `preprocess(x, 8000, 2000, 25, 900)`, same feature
code as CirCor. One recording per participant → patient vector [median, max] of that one recording.
ZCHSound is **never** used for training, feature choice, thresholds or any tuning.

**Models.** Trained once on all 874 CirCor binary-task patients (Present vs Absent).
- G1a (this workspace; whole-signal, no segmentation needed): W_stft (**primary**), W_wpd_db4_smooth (wavelet),
  B0, W_scat1 (whole-signal first-order scattering, see G4). RF primary, SMO secondary.
  Site-matched secondary variant: same, trained on CirCor **PV-location** recordings only.
- G1b (Mac; needs the Phase-2 code): E4 pipeline (HSMM + span detector + aligned features) for stft and wpds,
  with HSMM and span detector trained on all CirCor training annotations; plus the G2 variant E4q if it exists.

**Thresholds.** Spec-80 threshold computed on CirCor repeat-averaged out-of-fold scores of the same feature set
and classifier (from the frozen CirCor CV predictions), applied unchanged to ZCHSound.

**Endpoints and hypotheses** (participant-level bootstrap, 2000 resamples):
- **H10a (primary):** RF W_stft AUROC(any CHD vs NORMAL), clean set, 95 % CI lower bound > 0.5.
- **H10b (physiology ordering):** AUROC(VSD vs NORMAL) − AUROC(PFO vs NORMAL) > 0 with CI lower bound > 0, AND
  AUROC(VSD vs NORMAL) − AUROC(ASD vs NORMAL) > 0 with CI lower bound > 0 (RF W_stft, clean set).
  Rationale: restrictive VSDs produce loud holosystolic murmurs; ASD gives at most a soft flow murmur; PFO is silent.
  PDA (n = 32) descriptive only.
- **H10c (G1b, Mac):** E4-stft AUROC(any CHD) − W_stft AUROC(any CHD) on clean ZCHSound > 0 with CI lower bound > 0.
- Descriptive: every feature set × classifier × subtype; sensitivity/specificity at the CirCor threshold;
  internal-vs-external AUROC gap; noisy neonatal set (no hypothesis; expected near chance); wpds/scattering vs stft
  external difference with CI (no direction).

---------------------------------------------------------------------------------------------------------------
## G2 — Shortcut-free E4 (Mac; needs the Phase-2 code)

**E4q.** Same as E4 except span selection: in every recording, keep the top-q fraction of 1-s windows by span-detector
probability, q = that training fold's expert-annotated window fraction (computed on training patients only;
cross-fitted for training patients as in E4). Every recording therefore has the same selected fraction, so the
selected-fraction shortcut is removed by construction. Same aligned features, coverage minimum, WEKA settings, folds.
Selection controls with the identical q: **rand-q** (uniformly random windows, seed `zlib.crc32(rec_id)`) and
**snr-q** (top-q windows by the 20–200 / 0–1000 Hz spectral-ratio gate value, no learning).

- **H12a:** E4q − (W_stft+SC) ≥ 0.03? Rule: Δ > 0 with subject-bootstrap CI lower bound > 0 (S1 rule; SC re-derived
  for E4q exactly as in S1). Primary representation **stft**; wpd and wpds reported.
- **H12b:** E4q − rand-q > 0 with CI lower bound > 0 (does learned selection matter?).
- **H12c:** E4q − snr-q, descriptive.
- Report missing-aligned-feature rates by class for E4q (must no longer differ by construction of span fraction;
  coverage-minimum failures can still differ — report them).

---------------------------------------------------------------------------------------------------------------
## G3 — Oracle-segmentation ("conditioning-availability") audit

(a) **Reframing of existing results (no new runs):** for stft/wpd/wpds report Δ_oe = AUROC(expert) − AUROC(estimated)
for estimated ∈ {E1, E1b, E4, E4q} and Δ_or = AUROC(expert) − AUROC(perm) and AUROC(expert) − AUROC(shift),
following Cao et al. (arXiv 2608.03342) terminology.

(b) **Literature audit (team, mostly reading):** sources FastTrack/OpenAlex, PubMed, Consensus, alphaXiv; query
"CirCor OR PhysioNet 2022 OR 'PhysioNet Challenge 2022'" AND murmur, 2022–2026; include original studies reporting
murmur-detection performance on CirCor. Code per paper (two coders, disagreements resolved and counted):
uses dataset .tsv segmentation at test time (yes / no / unclear); evaluation unit (patient / recording / segment);
split grouping (patient-grouped / not / unclear); Unknown handling; hidden-test evaluated (yes/no); reported
headline metric. Primary output: proportion using test-time expert segmentation and the median reported accuracy
in each group (descriptive; no inference).

---------------------------------------------------------------------------------------------------------------
## G4 — Wavelet scattering (this workspace)

**Transform.** kymatio 0.3.0 `Scattering1D(J=6, Q=(8,1), oversampling=2)` at 2 kHz: averaging scale 2^6 = 64 samples
(32 ms), output hop 16 samples = the 8 ms segmentation grid. 38 first-order filters (centres ≈ 8–871 Hz), 87
second-order paths. Signal length truncated to the largest multiple of 1024 samples (drops < 0.512 s tail).
Energy proxy = squared scattering coefficient.

**Features (per recording, expert labels as in v1, same coverage minimum).**
- A_scat1: first-order analogue of the v1 aligned definitions: log(systolic energy / S1 total energy) and
  log(systolic / diastolic energy) per first-order filter, plus systolic and diastolic entropies (78 dims).
- A_scat12: A_scat1 + per second-order path log(systolic / diastolic energy) (78 + 87 = 165 dims).
- W_scat1: whole-signal first-order analogue of the v1 W definitions (relative energy, q90/q50 burstiness per filter,
  2 entropies; 78 dims) — used in G1a and as an internal descriptive set.

**Hypotheses** (RF, frozen folds, expert labels = oracle-assisted, best-vs-best, dimensionality differs and is reported):
- **H11a:** A_scat1 − A_stft (v1 values, 0.812 mean-of-repeats) ≥ 0.03 with the decision rule.
- **H11b:** A_scat12 − A_stft, same rule.
- **H11c:** A_scat12 − A_scat1, same rule (value of second-order / modulation information).
SMO secondary. Mean-of-repeats and repeat-averaged-score AUROCs both reported, labelled.

---------------------------------------------------------------------------------------------------------------
## Forbidden / reporting
No ZCHSound data in any training, tuning or threshold step. No change of feature definitions, scattering parameters,
q rule or hypotheses after any Phase-3 result is seen; any deviation → dated amendment before the affected run.
All results reported, including negative ones.

## Amendments
(none at lock time)

### A1 — 2026-10-28, G2 implementation details (written before any G2 code ran and before any Phase-3 result)
1. **Where.** G2 runs in this cloud workspace on a clone of the main repo at tag `results-final` (`cae9708`), using its
   unchanged Phase-2 code (scripts/21, 26, 29; `ec418.segmentation`). Data: the Phase-1 copy viewed through per-file
   symlinks so that every field the code reads equals PhysioNet v1.0.3 (`50782_MV_1.tsv` → the copy's byte-identical
   `50782_MV.tsv`; `50782.txt` MV_1 line gains its `.tsv`, as in v1.0.3). The copy's other header differences (`#Age`,
   missing `#Outcome`) are not read by any G2 step.
2. **Reproduction gate (must pass before any G2 classification).** Re-derived span-detector coefficients, intercepts,
   scaler parameters and thresholds must equal `results/logs/e4_models/r*_f*.json` (max abs diff < 1e-8), and a re-run of
   E4 itself (`E4R_*`, same WEKA settings) must reproduce `results/predictions/e4_predictions.csv` scores exactly. If
   either fails: stop and report; no G2 number is produced.
3. **q and k.** q = `train_annotated_frac` of the detector that scores the recording (outer-fold detector for test
   patients, inner-fold detector for cross-fitted training patients). Windows kept per recording
   k = min(n_win, max(1, floor(q·n_win + 0.5))) for n_win ≥ 1; recordings with n_win = 0 get no windows (as in E4).
   Ties in the ranking score are broken by window index (stable sort).
4. **snr-q** ranks windows by feature 0 (log10 P(20–200 Hz)/P(0–1000 Hz)), highest first. **rand-q** draws k windows
   without replacement with `numpy.random.default_rng(zlib.crc32(rec_id.encode()))` (same draw in every fold).
5. **SC_q** for H12a: the S1 shortcut variables recomputed with the E4q selection (`sc_pred_frac` = k/n_win;
   `sc_n_nofeat`, `sc_frac_nofeat` from the E4q wpd feature file), appended to W_stft (`G2_Wstft_SCq`); SC_q alone and
   W_wpd_db4 + SC_q are descriptive.
6. HSMM labels are kept only inside selected windows; everything downstream (aligned features, coverage minimum,
   aggregation, WEKA RF/SMO, inner-fold thresholds, bootstrap, 18/25-fold rule) is exactly E4 / S1.

### A2 — 2026-10-28/29, G2 moved back to the Mac (after gate 2 failed; no G2 number was opened)
In this workspace gate 1 passed (25/25 folds, detector parameters ≤ 4.3e-14 from the saved E4 models) but gate 2 failed:
E4 re-run predictions are not identical to `e4_predictions.csv` (AUROC within 0.0010, scores differ; diagnosis on
branch `phase3-g2`, commit `c2fc8d8`: Linux/OpenBLAS vs macOS/Accelerate, located in the HSMM-label features). As A1.2
requires, no G2 result was produced or looked at. Decision (user, 2026-10-28): the **official G2 run is on the Mac**, the
platform of Phase 2, with A1 unchanged including the exact gate 2. The cloud predictions
(`results/predictions/p3_g2_predictions.csv` on `phase3-g2`) stay unopened; after the Mac run they may be compared as a
cross-platform robustness check only. G3a's E4q row waits for the Mac run.

### A3 — 2026-10-29, code erratum (no analysis change)
`p3_g2_analyze.py` crashed after writing all tables because one descriptive row lacked the `primary` field; fixed by setting it False. Gates, statistics, rules and labels unchanged; table hashes before/after the fix recorded and compared.
