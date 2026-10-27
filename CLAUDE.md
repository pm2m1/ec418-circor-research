# CLAUDE.md — project rules for every session

EC418 CirCor murmur-detection study. Phase 1 is frozen at tag `v1.0-pilot`; Phase 2 is pre-registered in
`docs/PROTOCOL_V2_LOCKED.md` (tag `protocol-v2-lock`). Before changing anything, read `README.md`,
`docs/PROTOCOL_LOCKED.md`, `docs/PROTOCOL_V2_LOCKED.md`, `docs/GO_NO_GO.md` and `docs/ERRATA_v1.md`.

## Rules (non-negotiable)
1. Never modify, regenerate or delete files listed in `results/v1_freeze/MANIFEST_v1.sha256`; new runs use
   new tags/paths. Check with `shasum -a 256 -c results/v1_freeze/MANIFEST_v1.sha256`.
2. Never rewrite history, force-push, or move/delete tags.
3. Any deviation from `docs/PROTOCOL_V2_LOCKED.md` must be written in its "Amendments" section and committed
   BEFORE the affected run.
4. No tuning or choice (features, wavelet, thresholds, segmenter constants, which result to report) based on
   test-fold results. Thresholds come from inner folds only.
5. Folds are subject-grouped (`configs/folds_patient_level.csv`, sha256 `c4aa74c7…2339`); never use WEKA's
   row-wise CV for evaluation; never write patient/subject IDs as features.
6. Every reported number must come from a script in the repo and a saved output file. Report negative results.
7. Raw data stays out of git (`data/raw/`, `data/interim/`, `experiments/**/arff/` are gitignored). Commit
   messages explain what changed and why.
8. If a step fails or something does not match, stop and report it plainly instead of working around it.

## Practical notes
* Python env: `uv venv -p 3.12 .venv && uv pip install -p .venv -e .`; tests: `.venv/bin/python -m pytest -q`.
* Java: JDK 21 from Homebrew, `export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"`. WEKA 3.9.7 jars are
  committed in `tools/` (WEKA is GPL-3.0).
* Raw data: `data/raw/circor_training_data/` (symlink to the PhysioNet v1.0.3 download outside the repo).
