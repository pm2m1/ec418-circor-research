# REPOSITORY_AUDIT — final audit before submission (2026-10-29)

Branch `docs/final-submission-readiness`, created from `phase4-writeup` at `4966715` (which contains all three phases,
the write-up and the history record). Frozen evidence was not modified: `scripts/p5_verify_integrity.py` passes before
and after every commit (both manifests, folds, protocol locks, history map).

| Issue | File | Severity | Proposed action | Status |
|---|---|---|---|---|
| README described only the Phase-1 pilot (status, "reproduce everything" with Phase-1 commands, provenance pending, 39 tests) | `README.md` | high | rewrite for the completed study; results generated from saved tables | done |
| H9a reported as "reaches expert-label performance" / "non-inferior" although its rule was a point estimate and the CI crosses −0.03 | `docs/RESULTS_SUMMARY.md`, `E4_RESULTS.md`, `S1_SHORTCUT.md`, `report/EC418_report.tex`, slides | high | erratum E2-2 and dated notes; report and slides reworded; verdicts unchanged | done |
| "This gain is all timing" can be read as alignment explaining every difference | `docs/RESULTS_SUMMARY.md` | medium | erratum E2-3 (scope limited to the decomposition) | done |
| Historical documents read as current status (STOPPED provenance, GO/NO-GO future work, pilot audit, old title decisions) | `docs/GO_NO_GO.md`, `PROVENANCE_PHYSIONET.md`, `PILOT_RESULTS.md`, `RESEARCH_AUDIT.md`, `P3_CLOUD_STATUS.md`, `P3_G3_AUDIT.md`, `P4_TITLE.md`, `P4_FRAMING.md` | medium | "Historical phase document" note at the top; content unchanged | done |
| No navigation across ~30 documents | `docs/INDEX.md` | medium | add index by phase | done |
| No statement of supported and unsupported claims | `docs/INTERPRETATION_GUIDE.md` | medium | add | done |
| Reproduction instructions incomplete and partly wrong for later phases; protocol lock hashes fail on current files (amendments) with no explanation | `docs/REPRODUCIBILITY.md`, `scripts/p5_verify_integrity.py` | high | three-level guide; integrity script checks locks at their commits | done (Level 1 and 2 executed; Level 3 not re-run) |
| `configs/requirements_frozen.txt` contains `-e file:///home/claude/...` (path of the original build machine) | `configs/requirements_frozen.txt` | low | frozen environment record, left unchanged; install instructions filter that line | documented |
| Scripts `07`, `31`, `32`, `p4_*` write into frozen paths when re-run | `scripts/` | medium | documented: re-run only in a disposable worktree | documented |
| Rules file covered Phase 1–2 only and one manifest | `docs/PROJECT_RULES.md` (local `CLAUDE.md` points to it) | medium | update for all phases, both manifests, amendments, errata, AI disclosure | done |
| Personal e-mail address hard-coded in four public scripts and sent to OpenAlex/Crossref/Semantic Scholar/Unpaywall | `scripts/p4_g3b_*.py` | medium | read from `EC418_CONTACT_EMAIL`; address remains in earlier commits (history) | done (history: owner's decision) |
| No secrets or credentials found (pattern scan for tokens and private keys) | all tracked files | — | none | checked |
| WEKA/MTJ jars redistributed without GPL/LGPL texts; two jars without stated licence | `tools/` | medium | inventory in `THIRD_PARTY_NOTICES.md`; add licence texts after owner decision | open (owner) |
| No licence for project code; GPL-3.0 LR-HSMM port and WEKA linkage constrain the choice | repository | medium | `docs/LICENSING_DECISION_REQUIRED.md`; no licence added | open (owner) |
| No citation metadata | `CITATION.cff` | low | add with verified metadata; validated (schema 1.2.0) | done |
| Submission title was dropped on 2026-10-29 for overlap with Lin et al. (LNCS 2026) and for overstating "multiresolution" | `docs/P4_TITLE.md` | low | the author's later instruction sets this title; note added | author's choice, flagged |
| Missing submission deliverables (detailed report, presentation, checklist) | `submission/` | high | build from the numbers registry and saved figures | done (rendered and inspected) |
| Large tracked files: WEKA jar 14 MB, Scholar screenshots + duplicate zip 23 MB, feature CSVs and predictions up to 10 MB | `tools/`, `references/g3b/scholar_pages/`, `data/processed/`, `results/` | low | evidence or provenance records; the zip duplicates the PNGs but was kept on the author's instruction | kept |
| Phase-1 figure `fig8` not byte-identical on regeneration (macOS vs Linux) | `results/figures/fig8_roc_auroc_ci_rf.png` | low | verified pixel-identical (0 of 1,350,000 pixels differ); only PNG encoding differs | documented |
| Team and course metadata missing (roll number, instructor, date, department) | `submission/` report and slides | medium | clearly marked placeholders | open (author) |
| README stated test count 39; actual 81 | `README.md`, `docs/PROJECT_RULES.md` | low | updated | done |
