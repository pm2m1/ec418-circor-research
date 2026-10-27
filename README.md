# EC418 — Patient-level, leakage-audited wavelet murmur detection on CirCor (WEKA + Python)

NIT Warangal · EC418 Biomedical Instrumentation & Signal Processing · Assignment-2 validation phase.

**Status:** feasibility/validation pilot. Read `docs/GO_NO_GO.md` first, then `docs/PILOT_RESULTS.md`.
Every number in `docs/` comes from a script in this repo run on the real CirCor files.

## What is here
```
configs/      protocol.json (LOCKED), folds_patient_level.csv (+sha256), PROTOCOL copy
docs/         RESEARCH_AUDIT, DATASET_AUDIT, PROTOCOL_LOCKED, BASELINE_AUDIT, PILOT_RESULTS, GO_NO_GO
src/ec418/    data/ (loader, subject linkage) preprocessing/ wavelets/ (WPD, STFT, exact baseline DWT port)
              features/ evaluation/ (splits, metrics incl. OFFICIAL weighted accuracy) weka/ (ARFF + Java runner)
scripts/      01 audit · 02 features · 03 B1 realign · 04 folds · 05 H1 leakage · 06 WEKA runs · 07 analysis
              08 figures · 09 quality (exploratory)
tests/        39 unit/integration tests (pytest)
references/   baseline repo snapshot (MIT), official Challenge scoring code (vendored, unmodified)
results/      tables/ figures/ predictions/ logs/
tools/        WEKA 3.9.7 jars (from the python-weka-wrapper3 0.3.3 sdist on PyPI) — not committed
```

## Setup (macOS Apple Silicon or Linux)
```bash
# Python 3.11+ and a JDK 11+ (macOS: brew install openjdk; or Temurin)
uv venv -p 3.12 .venv && uv pip install -p .venv -e .
# WEKA 3.9.7 jar: either the official installer from waikato.github.io/weka-wiki, or
pip download --no-deps python-weka-wrapper3==0.3.3 -d /tmp/pww3 && \
  tar xzf /tmp/pww3/python_weka_wrapper3-0.3.3.tar.gz -C /tmp/pww3 && \
  cp /tmp/pww3/python_weka_wrapper3-0.3.3/python/weka/lib/{weka,mtj,arpack_combined,core}.jar tools/
```

## Data
Official: https://physionet.org/content/circor-heart-sound/1.0.3/ (open, ODC-By). On the Mac:
```bash
wget -r -N -c -np https://physionet.org/files/circor-heart-sound/1.0.3/   # ~0.6 GB
# put training_data/*  ->  data/raw/circor_training_data/   (also training_data.csv, SHA256SUMS.txt)
```
This validation run used the identical training-set copy redistributed in github.com/chihoon1/Murmur
(PhysioNet was unreachable from the build machine); 10,433/10,434 files pass PhysioNet's SHA256SUMS.
See `docs/DATASET_AUDIT.md §1` for how to re-verify against PhysioNet, and note the v1.0.3 `Outcome` column.

## Reproduce everything (≈ 1.5–2 h on 2 CPU cores; faster on an M5 Pro)
```bash
.venv/bin/python -m pytest -q                                  # 39 tests
.venv/bin/python scripts/01_dataset_audit.py
.venv/bin/python scripts/02_extract_features.py                # ~3 min
.venv/bin/python scripts/03_b1_realign_shipped_features.py     # baseline features + 1e-15 verification
.venv/bin/python scripts/04_make_folds.py                      # must reproduce configs/folds_patient_level.sha256
.venv/bin/python scripts/05_h1_leakage_b1.py
.venv/bin/python scripts/06_run_patient_level_weka.py main B0,B1,W_stft,W_wpd_db4,A_stft,A_wpd_db4 RF,SMO,MLP,LR 2
.venv/bin/python scripts/06_run_patient_level_weka.py wavelet_sensitivity W_wpd_db6,W_wpd_sym8,W_wpd_coif3,A_wpd_db6,A_wpd_sym8,A_wpd_coif3 RF 2
.venv/bin/python scripts/07_analyze.py main wavelet_sensitivity
.venv/bin/python scripts/08_figures_signals.py
.venv/bin/python scripts/09_quality_exploratory.py             # optional, exploratory
sha256sum -c <(cat configs/folds_patient_level.sha256 | sed 's/$/  configs\/folds_patient_level.csv/')
```
Single-fold WEKA command line (no GUI), as logged in `results/logs/weka_cli_demo_A_wpd_db4_r0_f0.log`:
```bash
java -cp "tools/*" weka.classifiers.trees.RandomForest -I 300 -K 0 -S 1 \
  -t experiments/main/arff/A_wpd_db4_r0_f0_outer_train.arff -T experiments/main/arff/A_wpd_db4_r0_f0_outer_test.arff -o -v
```

## Integrity notes
* Protocol and folds were frozen (git commit `Lock protocol and folds before modelling`) before any model ran.
* WEKA's row-wise CV is never used; folds are subject-grouped in Python. IDs are never ARFF attributes.
* Aligned-feature results use the dataset's expert-assisted segmentation → "oracle-segmentation-assisted".
* AI assistance (Claude) was used to write code and drafts; every reported number is reproducible from
  the scripts above. Disclose this in the report, and have each team member re-run and explain the pipeline.
