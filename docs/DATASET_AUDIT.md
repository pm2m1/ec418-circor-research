# DATASET_AUDIT — CirCor DigiScope (PhysioNet/CinC 2022 public training set)

All numbers below were computed by `scripts/01_dataset_audit.py` on the actual files
(`results/logs/dataset_audit.json`, `results/tables/patients_audit.csv`, `recordings_audit.csv`).

> **Note (2026-10-27, Mac E0 — see `docs/PROVENANCE_PHYSIONET.md` and amendments D1/D2 in
> `docs/PROTOCOL_V2_LOCKED.md`).** This audit was run on the Phase-1 copy (Challenge-2022 redistribution), not on
> PhysioNet CirCor v1.0.3. Two findings below are properties of that copy and v1.0.3 corrects both:
> * **Age counts (§2):** v1.0.3 recategorises 73 patients (65 Infant→Child, 7 Young Adult→Adolescent,
>   1 Adolescent→Child) → Child 664, Infant 126, Adolescent 72, Neonate 6, missing 74. Age is not used anywhere.
> * **"Missing `.tsv` for 50782_MV_1" (§5):** in v1.0.3 the header lists `50782_MV_1.tsv` (the copy had the same
>   bytes misnamed `50782_MV.tsv`). The file is a degenerate 6-byte `0 0 28` row with no annotated time, so the
>   recording still has no aligned features and every downstream number is unchanged.
> The v1.0.3 audit is in `results/logs/dataset_audit_v103.json` and `results/tables/v103_*.csv`; murmur labels,
> Additional IDs, counts and folds are identical.

## 1. How the data was obtained (provenance — read this)
* **PhysioNet, its AWS/GCS mirrors, Zenodo, Kaggle and Hugging Face were blocked by this session's
  network policy (HTTP 403).** I did not download from physionet.org.
* The **complete public training set** is redistributed inside the baseline authors' GitHub repo
  (`github.com/chihoon1/Murmur`, commit `56b9846`, MIT licence for code; data under ODC-By as stated in
  the shipped `LICENSE.txt`). I cloned it and copied `data/training_data/` to `data/raw/circor_training_data/`.
* Integrity: the folder ships PhysioNet's `SHA256SUMS.txt`. **10,433 of 10,434 listed files match**
  (all 3163 WAV, 3163 HEA, 3163 TSV, 942 patient TXT, LICENSE, RECORDS). The single mismatch is
  `training_data.csv` (re-saved by a third party). Therefore **labels are read from the checksum-verified
  per-patient `.txt` headers, not the CSV**; the CSV agrees with the TXT on all 942 murmur labels anyway.
* Caveat: the checksum list came with the same copy. To close the loop, on your Mac run
  `curl -O https://physionet.org/files/circor-heart-sound/1.0.3/SHA256SUMS.txt` (or the challenge-2022
  1.0.0 one) and compare with `sha256sum data/raw/circor_training_data/SHA256SUMS.txt`
  (`579410299db55e327b621c562cc53606cf3d97ddc41fd4c530c6166600ee8fc6`). If PhysioNet's file differs only by
  path prefix / CSV entry, the recordings are identical.
* **Version:** the patient headers have no `#Outcome` field, so this copy matches the Challenge-2022
  training release the baseline paper cites (physionet.org/content/challenge-2022/1.0.0), not necessarily
  CirCor v1.0.3 byte-for-byte. Recordings/labels counts match the v1.0.3 public portion (942 / 3163).
  **Clinical Outcome labels are therefore NOT available here** → outcome study deferred.

## 2. Counts (verified)
| Item | Value |
|---|---|
| Patients | **942** |
| Recordings | **3163** (mean 3.36 per patient; 1:62, 2:156, 3:123, 4:588, 5:10, 6:3 patients) |
| Murmur (patients) | Present **179**, Absent **695**, Unknown **68** |
| Murmur (recordings) | Present 616, Absent 2391, Unknown 156 |
| Locations (recordings) | MV 861, AV 800, PV 766, TV 732, Phc 4 (repeat recordings at a site are `_1`, `_2`) |
| Campaigns | CC2014 385, CC2015 557 patients |
| Age group | Child 598, Infant 191, Adolescent 66, Young adult 7, Neonate 6, missing 74 |
| Audio | all 4000 Hz, mono, PCM-16; 5.2–64.5 s, median 21.5 s; 20.1 h total; no flat-line files |
| Clipping | 136 recordings have >0.1 % samples at full scale (Absent 3.3 %, Present 5.4 %, **Unknown 15.4 %**) |
| Present-patient grades | I/VI 104, II/VI 28, III/VI 46 (1 missing); pitch Low 87 / Medium 49 / High 42; only **5** with a diastolic murmur |
| Present recordings at an annotated murmur site | 499 / 616 (117 Present-patient recordings are from sites where no murmur was heard) |

## 3. Identity linkage (Issue B)
* `Additional ID` is set for **140 patients = 70 linked pairs**; every link is symmetric and both IDs are
  inside the public set (no dangling links). → **872 canonical subjects** overall;
  binary task: **874 patients in 816 subjects** (58 linked pairs fall entirely in the binary task).
* **15 of the 70 linked children carry different murmur labels at their two visits**
  (Absent/Unknown 6, Present/Unknown 5, **Absent/Present 4**). Grouping by subject is therefore essential:
  a random patient split would put the same child in train and test, sometimes with the opposite label.
* Grouping rule: connected components of the link graph (`src/ec418/data/circor.py::canonical_subjects`).
  Ambiguity left: none detectable — but linkage relies entirely on the dataset's `Additional ID`;
  unlinked duplicates (if any exist) cannot be detected from metadata.

## 4. Label semantics (Issue C)
* Murmur label = **one annotator's** patient-level judgement (Present/Absent/Unknown). Unknown =
  annotator could not characterise the murmur — documented reasons include poor quality, but it is not
  defined purely as "noisy audio". Evidence it is *partly* quality-related: Unknown recordings have far
  less segmentation coverage (median 24 % annotated vs 52–61 %) and 3–5× more clipping.
* Patient label ≠ recording label: 19 % of a Present patient's recordings come from sites with no
  murmur. Recording-level training with patient labels is label-noisy; we classify at patient level.
* Murmur ≠ disease. Outcome (echo-based Normal/Abnormal) is the diagnosis-like target; not present here.

## 5. Segmentation annotations
* 3162/3163 recordings have a `.tsv` (missing: `50782_MV_1`, Absent). Labels 0 unannotated, 1 S1,
  2 systole, 3 S2, 4 diastole. Median annotated fraction 52 %; only 1 recording has < 3 systoles.
* With the protocol's coverage minimum, aligned features exist for **3162/3163** recordings and for all
  874 binary-task patients.
* **Shortcut risk:** annotated fraction differs by class (Present 0.61, Absent 0.52, Unknown 0.24 median).
  Coverage *alone* separates Present vs Absent patients with AUROC **0.56** (recording 0.55). Our features
  do not use coverage directly, but every aligned result is **oracle-segmentation-assisted** and must be
  labelled so; deployment would need automatic segmentation (published options exist on CirCor, e.g.
  Arjoune et al. 2024 IEEE Access; Tatulli et al. 2025 Comput Biol Med).

## 6. Leakage risks and how they are handled
| Risk | Status |
|---|---|
| Recordings of one patient in train & test | prevented: patient-level rows, subject-grouped folds |
| Same child (two IDs) in train & test | prevented: canonical subject grouping (asserted, 100 checks) |
| Cycles/windows/augmentations crossing split | none generated across patients; features are per recording |
| Unknown merged into Absent | not done (excluded from binary task) |
| Label in file names / IDs as predictors | IDs never written to ARFF (guarded by code + test) |
| Hidden test set | not available (PhysioNet withheld 40 %); all results are public-set CV |
