# PROJECT_RULES — project rules for every session

EC418 CirCor murmur-detection study, completed in three pre-registered phases: Phase 1 frozen at tag `v1.0-pilot`;
Phase 2 pre-registered in `docs/PROTOCOL_V2_LOCKED.md` (tag `protocol-v2-lock`, later pre-registrations `e1b-prereg`,
`diag-prereg`, `e4-prereg`, `s1-prereg`) and frozen at `results-final`; Phase 3 in `docs/PROTOCOL_V3_PREREG.md`, results
at `phase3-results`. **Entry points:** `README.md`, `docs/INDEX.md`, `docs/RESULTS_SUMMARY.md`, `docs/P3_RESULTS.md`,
`docs/INTERPRETATION_GUIDE.md`, `docs/REPRODUCIBILITY.md`. Documents marked "Historical phase document" describe an
earlier state; do not treat their status lines as current.

## Rules (non-negotiable)
1. Never modify, regenerate or delete files listed in `results/v1_freeze/MANIFEST_v1.sha256` or
   `results/final_freeze/MANIFEST_final.sha256`, the frozen folds, saved predictions, frozen tables, logs or figures, or
   raw data. New runs use new tags/paths. Check with `.venv/bin/python scripts/p5_verify_integrity.py` (or
   `shasum -a 256 -c` on each manifest). Scripts that write into frozen paths (`07`, `31`, `32`, `p4_*`) are re-run only in
   a disposable `git worktree` (`docs/REPRODUCIBILITY.md` §3).
2. Never rewrite history, force-push, or move/delete tags.
   *Exception (2026-10-29, author's explicit decision, one operation only):* the repository owner, Parth Mishra, rewrote the
   history once to normalise commit metadata to the sole author (author/committer/tagger; AI attribution trailer lines
   removed; one commit subject reworded), with every tree hash unchanged, and force-pushed all branches and tags. Details,
   verification and the old → new hash map: `docs/HISTORY_REWRITE.md`, `results/history_hash_map.csv`. Rule 2 applies again
   without exception from this point on.
3. Frozen protocols (`docs/PROTOCOL_LOCKED.md`, `PROTOCOL_V2_LOCKED.md`, `PROTOCOL_V3_PREREG.md`, `G3B_AUDIT_PROTOCOL.md`,
   `configs/protocol*.json` and their lock hashes) are never edited. A deviation is written in the protocol's
   "Amendments" section, dated, and committed **before** the affected run. New experimental work needs a new, dated,
   committed protocol before any code or run; a choice made after seeing results is labelled post-hoc, never presented
   as pre-registered.
4. No tuning or choice (features, wavelet, thresholds, segmenter constants, which result to report) based on
   test-fold results. Thresholds come from inner folds only.
5. Folds are subject-grouped (`configs/folds_patient_level.csv`, sha256 `c4aa74c7…2339`); never use WEKA's
   row-wise CV for evaluation; never write patient/subject IDs as features.
6. Every reported number must come from a script in the repo and a saved output file (report and slides: only through
   `report/numbers.json`, checked by `scripts/p4_check_numbers.py`). Report negative results. Interpretation corrections go
   into an erratum (`docs/ERRATA_*.md`) or a dated note, never into saved numbers or recorded verdicts.
7. Raw data stays out of git (`data/raw/`, `data/interim/`, `experiments/**/arff/` are gitignored). Data provenance: the
   official PhysioNet CirCor v1.0.3 download, verified against PhysioNet's `SHA256SUMS.txt` (`docs/PROVENANCE_PHYSIONET.md`,
   amendments D1/D2). Commit messages explain what changed and why, and carry no attribution trailers.
8. If a step fails or something does not match, stop and report it plainly instead of working around it.
9. AI assistance is disclosed, not hidden: keep the disclosure in `README.md` (and the submission report) accurate, and do
   not present AI-generated work as manually written.

## Practical notes
* Python env: `uv venv -p 3.12 .venv && uv pip install -p .venv -e .`; tests: `.venv/bin/python -m pytest -q` (81 tests).
* Java: JDK 21 from Homebrew, `export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"`. WEKA 3.9.7 jars are
  committed in `tools/` (WEKA is GPL-3.0; see `THIRD_PARTY_NOTICES.md`).
* Raw data: `data/raw/circor_training_data/` (symlink to the PhysioNet v1.0.3 download outside the repo).
* The local `CLAUDE.md` only points here and is excluded from git (`.git/info/exclude`).
