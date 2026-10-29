# INDEX — documents in reading order

The study ran in phases on 2026-10-27/29. Each phase was pre-registered before its results; later documents add to,
but never overwrite, earlier ones. Documents marked *historical* carry a note at the top pointing to the current status.

## Research overview
* [`../README.md`](../README.md) — project overview, key results, installation, reproduction summary.
* [`INTERPRETATION_GUIDE.md`](INTERPRETATION_GUIDE.md) — which conclusions the results support and which they do not.
* [`RESULTS_SUMMARY.md`](RESULTS_SUMMARY.md) — final Phase 1–2 results, every hypothesis, decomposition, design timeline.
* [`P3_RESULTS.md`](P3_RESULTS.md) — Phase 3: scattering (G4), external test on ZCHSound (G1a), shortcut-free E4q (G2), conditioning gaps (G3a).

## Dataset and provenance
* [`DATASET_AUDIT.md`](DATASET_AUDIT.md) — counts, labels, `Additional ID` linkage (816 subjects), segmentation coverage.
* [`PROVENANCE_PHYSIONET.md`](PROVENANCE_PHYSIONET.md) — *historical (E0)*: official PhysioNet v1.0.3 download and checksum verification; decision in amendments D1/D2 of [`PROTOCOL_V2_LOCKED.md`](PROTOCOL_V2_LOCKED.md).
* [`REPRO_MAC.md`](REPRO_MAC.md) — Phase-1 reproduction on macOS (float32 MFCC note).

## Baseline reproduction
* [`BASELINE_AUDIT.md`](BASELINE_AUDIT.md) — the 2025 *Scientific Reports* wavelet baseline (B1): code, re-alignment, H1 leakage test.
* [`RESEARCH_AUDIT.md`](RESEARCH_AUDIT.md) — *historical*: source checks of the original project dossier.

## Frozen protocols (never edited except appended amendments)
* [`PROTOCOL_LOCKED.md`](PROTOCOL_LOCKED.md) — Phase 1 (v1) protocol, folds and hypotheses H1–H4.
* [`PROTOCOL_V2_LOCKED.md`](PROTOCOL_V2_LOCKED.md) — Phase 2 (E0–E4, D1–D3, S1) with dated amendments.
* [`PROTOCOL_V3_PREREG.md`](PROTOCOL_V3_PREREG.md) — Phase 3 (G1–G4) with amendments A1–A3.
* [`G3B_AUDIT_PROTOCOL.md`](G3B_AUDIT_PROTOCOL.md) — literature-audit protocol with amendments A1–A3 (coding not completed).

## Phase 1 results
* [`PILOT_RESULTS.md`](PILOT_RESULTS.md) — *historical*: frozen Phase-1 results (tag `v1.0-pilot`).
* [`GO_NO_GO.md`](GO_NO_GO.md) — *historical*: the end-of-Phase-1 decision.
* [`ERRATA_v1.md`](ERRATA_v1.md) — wording errata for Phase 1.

## Phase 2 experiments
* [`E2_RESULTS.md`](E2_RESULTS.md) — expert labels vs timing-destroyed nulls (H5).
* [`E1_RESULTS.md`](E1_RESULTS.md) — envelope-peak segmentation (H6).
* [`E1b_RESULTS.md`](E1b_RESULTS.md) — LR-HSMM segmentation (H8).
* [`D_DIAGNOSTICS.md`](D_DIAGNOSTICS.md) — D1–D3: timing vs span selection.
* [`E4_RESULTS.md`](E4_RESULTS.md) — learned span detector (H9).
* [`S1_SHORTCUT.md`](S1_SHORTCUT.md) — span/missingness shortcut control.
* [`ERRATA_PHASE2.md`](ERRATA_PHASE2.md) — E2-1 (null spans), E2-2 (H9a is not a non-inferiority test), E2-3 (scope of "all timing").

## Phase 3
* [`PROTOCOL_V3_PREREG.md`](PROTOCOL_V3_PREREG.md), [`P3_RESULTS.md`](P3_RESULTS.md).
* [`P3_CLOUD_STATUS.md`](P3_CLOUD_STATUS.md) — *historical*: the cloud-workspace state before the Mac run.
* [`P3_G3_AUDIT.md`](P3_G3_AUDIT.md) — G3a conditioning gaps (current); 11-paper literature pilot (*historical*, not a finding).

## Write-up and literature
* [`P4_CASE_STUDY.md`](P4_CASE_STUDY.md) — two 2024–26 papers that use expert segmentation on test data, and why their numbers are not on our scale.
* [`P4_RELATED_WORK_CHECK.md`](P4_RELATED_WORK_CHECK.md) — Kutlu & Çolak 2026, Ladislaus et al. 2026.
* [`P4_FRAMING.md`](P4_FRAMING.md), [`P4_TITLE.md`](P4_TITLE.md) — *historical* write-up decisions.
* `../references/g3b/` — literature search, deduplication and screening records (documentation only; amendment A3).

## Reproduction and tooling
* [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) — environment checks, integrity checks, three reproduction levels.
* [`WEKA_SETUP.md`](WEKA_SETUP.md) and [`../weka_demo/`](../weka_demo/) — classifier strings, CLI demo, Explorer steps.
* [`PROJECT_RULES.md`](PROJECT_RULES.md) — repository rules for anyone (or any tool) changing the repository.
* [`HISTORY_REWRITE.md`](HISTORY_REWRITE.md) — the one-off commit-metadata normalisation; old → new hashes in `../results/history_hash_map.csv`.
* [`REPOSITORY_AUDIT.md`](REPOSITORY_AUDIT.md) — final repository audit.

## Submission artifacts
* [`../submission/`](../submission/) — research report (PDF and LaTeX source), presentation (PPTX), submission checklist.
* [`../report/`](../report/) — short IEEE-format paper draft and the numbers registry used by both documents.
* Licensing: [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), [`LICENSING_DECISION_REQUIRED.md`](LICENSING_DECISION_REQUIRED.md); citation: [`../CITATION.cff`](../CITATION.cff).
