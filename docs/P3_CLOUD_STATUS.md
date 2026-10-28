# Phase 3 — cloud-workspace status (2026-10-28/29) and what the Mac run must do

Phase 3 was pre-registered and partly run in a cloud workspace before the Mac run. Provenance:

| Item | Where | Commit / time (IST) |
|---|---|---|
| Pre-registration `docs/PROTOCOL_V3_PREREG.md`, `configs/protocol_v3.json` | cloud sandbox repo (Phase-1 base) | content commit `7acc9fc` 2026-10-28 18:38:40; tag `protocol-v3-prereg` → `54de9b3` (lock hashes; = `7acc9fc` + `configs/protocol_v3_lock.sha256`, same timestamp) |
| G4/G1a code + amendment A1 (G2 details) | sandbox | `4f85d9d` 18:57:16 (scattering extraction had started at ~18:41 from the same code) |
| G2 code + gate (this repo, branch `phase3-g2`) | `2ccf398` 18:58, analysis `96ccfec` | before any G2 run |
| Amendment A2 (G2 official run on the Mac) | sandbox | `4661383` 2026-10-29 01:06 |

The copies of the PREREG and A1/A2 in this repo are byte-copies of the sandbox file. `configs/protocol_v3_lock.sha256`
hashes the **original lock-time** PREREG (before A1/A2 were appended).

## Cloud results (reference only — the Mac run regenerates the official ones)
`results/p3_cloud_reference/` holds the cloud outputs (tables, CV and ZCHSound scores, gzipped feature files).
Cloud data = the Phase-1 CirCor copy (`50782_MV_1` without `.tsv`, as in v1) for G4/G1a.

* **G4** (RF): H11a A_scat1 − A_stft −0.026 [−0.058, +0.005] NOT SUPPORTED; H11b A_scat12 − A_stft −0.013 NOT SUPPORTED;
  H11c A_scat12 − A_scat1 +0.013 [+0.001, +0.025], 18/25 — CI > 0 but < 0.03 → NOT SUPPORTED. SMO A_scat12 0.842 (descriptive).
* **G1a**: H10a RF W_stft ZCHSound-clean any-CHD AUROC 0.706 [0.672, 0.738] SUPPORTED; H10b VSD−PFO +0.262, VSD−ASD +0.124
  (CIs > 0) SUPPORTED. Noisy subset ≈ chance for all models. Post-hoc age check: score ⟂ age (ρ −0.02), AUROC 0.69–0.77
  within age tertiles. B0 SMO 0.834 but PFO 0.83 and B0 RF-pv 0.26 → artefact-driven. ZCHSound = 1,259 participants,
  one recording each (Jia et al., IEEE TBME 2024).
* **G3a** (`results/tables/p3/g3a_conditioning_gaps.csv`, from saved Phase-2 predictions): Δ_or 0.13–0.21; Δ_oe E1 0.05–0.08,
  E1b 0.09–0.11, E4 0.005–0.007 (CIs include 0).
* **G2: STOPPED in the cloud.** Gate 1 passed (detectors ≤ 4.3e-14 from saved E4 models, 25/25 folds); gate 2 failed
  (E4R ≠ `e4_predictions.csv`; AUROC within 0.001, scores differ; Linux/OpenBLAS vs macOS). Diagnosis tables:
  `results/p3_cloud_reference/tables/g2_gate_diagnosis_*`. Cloud G2 predictions are kept **unopened** as
  `results/p3_cloud_reference/p3_g2_predictions_SEALED_unopened.csv` (cross-platform check only, after the Mac run).
