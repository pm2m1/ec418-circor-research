# PROVENANCE_PHYSIONET — E0: PhysioNet CirCor v1.0.3 vs the Phase-1 copy (2026-10-27, Mac)

**Status: STOPPED for a decision.** The recordings are byte-identical and all murmur labels / Additional IDs
match, but two kinds of header content differ beyond the allowed extra `#Outcome` field (§4). Nothing after
E0 (folds rerun, Phase-1 reproduction, E2) has been run on this data yet.

Every number below comes from `scripts/12_e0_provenance.py` → `results/logs/e0_provenance.json`,
`results/tables/e0_sha256_differences.csv`, `results/tables/e0_patient_txt_content_diffs.csv`.

## 1. How the data was obtained
* `SHA256SUMS.txt` (957,290 B, server mtime 2022-05-10), `LICENSE.txt` and `RECORDS` came straight from
  `https://physionet.org/files/circor-heart-sound/1.0.3/` with `wget -r -N -c -np`.
* **Deviation (transport only):** physionet.org served ≈ 5 KB/s from this machine (≈ 1 day for 0.66 GB), so
  wget was stopped and the 10,431 files under `training_data/` (+ `training_data.csv`) were fetched from
  PhysioNet's official AWS Open Data mirror `https://physionet-open.s3.amazonaws.com/circor-heart-sound/1.0.3/`.
  This does not weaken provenance: every file is checked against the `SHA256SUMS.txt` fetched from physionet.org.
* Location: `~/data/circor-1.0.3/physionet.org/files/circor-heart-sound/1.0.3/` (outside the repo);
  `data/raw/circor_training_data` is a symlink to its `training_data/`.

## 2. Download integrity
All **10,434 / 10,434** files listed in PhysioNet's `SHA256SUMS.txt` are present and hash as listed; no
unlisted files (also confirmed independently with `shasum -a 256 -c`).

## 3. Recording files used in Phase 1 (`references/data_provenance/recording_files_sha256.txt`)
* **9,488 / 9,489** `.wav/.hea/.tsv` are byte-identical under the same name.
* The one exception is a **name, not content**: the copy's `50782_MV.tsv` (sha256 `5e8e2447…`) is
  byte-identical to PhysioNet's `50782_MV_1.tsv`. PhysioNet has no `50782_MV.tsv`.

## 4. Copy `SHA256SUMS` (`circor_copy_SHA256SUMS.txt`) vs PhysioNet `SHA256SUMS.txt` — every difference
945 entries differ (both lists have 10,434 entries):

| Kind | n | Files |
|---|---:|---|
| hash differs | 942 | all patient `<id>.txt` |
| hash differs | 1 | `training_data.csv` (already known not to match in v1) |
| only in copy | 1 | `training_data/50782_MV.tsv` |
| only in PhysioNet | 1 | `training_data/50782_MV_1.tsv` (same bytes as the line above) |

The copy's 942 `.txt` were fetched from `github.com/chihoon1/Murmur@56b9846` (the Phase-1 source) and all
942 verified against `circor_copy_SHA256SUMS.txt`. Line-by-line comparison after normalising line endings
(copy: CRLF without final newline; PhysioNet: LF) and dropping `#Outcome`:

* **868 patients:** identical except the added `#Outcome` line and line endings — allowed.
* **73 patients: `#Age` category differs** (65 × Infant→Child, 7 × Young Adult→Adolescent, 1 × Adolescent→Child —
  see `e0_patient_txt_content_diffs.csv`). Age is not a feature, not used by any model or analysis script;
  it only appears in the `age` column of the frozen `results/tables/patients_audit.csv`.
* **1 patient (50782, Absent, in the binary task): recording line changed.**
  copy `MV 50782_MV_1.hea 50782_MV_1.wav` → PhysioNet `MV 50782_MV_1.hea 50782_MV_1.wav 50782_MV_1.tsv`.
  In Phase 1 this recording therefore had **no segmentation** (`seg_coverage.csv`: 0 S1/systole/diastole columns,
  `has_tsv = False`) and NaN aligned features; with v1.0.3 it has its expert segmentation. This changes the
  aligned (A_*) patient vector of 1 / 874 patients; whole-signal sets, B0, B1, labels and folds are unaffected.

## 5. Labels and counts (PhysioNet v1.0.3)
* Murmur label equal for **942 / 942** patients; `Additional ID` equal for **942 / 942**.
* **942 patients, 3,163 recordings, 179 Present / 695 Absent / 68 Unknown.**
* `#Outcome` now available: 486 Normal / 456 Abnormal.

## 6. What was not run (because of the STOP rule)
`scripts/01_dataset_audit.py` / `04_make_folds.py` (fold sha256 check), Step 4 reproduction and E2.
Expected effects if the v1.0.3 data is accepted as-is: folds reproduce (they depend only on patient, subject and
murmur label, which all match); the shadow `patients_audit.csv` differs in `age` for 73 rows and
`recordings_audit.csv` / `seg_coverage.csv` / every `A_*` feature file differ in the `50782_MV_1` row only.
