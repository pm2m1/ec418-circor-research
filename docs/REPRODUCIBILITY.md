# REPRODUCIBILITY — environment, integrity checks and three reproduction levels

All commands run from the repository root. Durations are **measured on the author's Mac (Apple M5 Pro)** where given, or
quoted from the run records in the experiment documents; nothing else is an estimate. Results never depend on these
times.

## 0. Environment verification
```bash
uname -a                                      # macOS 26.6 / Ubuntu were used
.venv/bin/python --version                    # Python 3.12.14 (Phase 2–3, Mac); Phase 1 used 3.13 on Linux
java -version                                 # OpenJDK 21 (macOS: export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH")
java -cp "tools/weka.jar" weka.core.Version   # 3.9.7
.venv/bin/python -c "import numpy, scipy, pandas, pywt, sklearn, librosa; print(numpy.__version__, scipy.__version__, pandas.__version__, pywt.__version__, sklearn.__version__, librosa.__version__)"
ls data/raw/circor_training_data/training_data.csv   # only needed for Level 3
```
Recorded environments: `configs/environment_mac.txt` (Phase 2–3), `configs/environment.txt` (Phase 1). Pinned
packages: `configs/requirements_frozen.txt` — its line `-e file:///home/claude/ec418-circor-research` is the original
build machine's editable install, so drop it:
`grep -v '^-e ' configs/requirements_frozen.txt > /tmp/ec418_req.txt && uv pip install -p .venv -r /tmp/ec418_req.txt && uv pip install -p .venv -e .`.
Phase-3 scattering features use a separate environment `.venv-scat` with kymatio 0.3.0, scipy 1.14.1, numpy 2.1.3
(`docs/P3_RESULTS.md`). The write-up needs `tectonic` (PDF) and `python-pptx` (`uv pip install -p .venv -e ".[writeup]"`).

## 1. Data integrity (needed only for Level 3)
The study uses the **official PhysioNet CirCor v1.0.3** download, verified against PhysioNet's own checksum list
(Phase 2, `docs/PROVENANCE_PHYSIONET.md`, amendments D1/D2). Phase 1 used a byte-identical third-party redistribution of
the training set (github.com/chihoon1/Murmur); its checksum list is `references/data_provenance/circor_copy_SHA256SUMS.txt`
and must not be confused with PhysioNet's.
```bash
wget -r -N -c -np https://physionet.org/files/circor-heart-sound/1.0.3/
cd physionet.org/files/circor-heart-sound/1.0.3/
shasum -a 256 -c SHA256SUMS.txt | grep -v ': OK$'      # Linux: sha256sum -c; expected: no output (10,434 files OK)
cd - && ln -s "$PWD/physionet.org/files/circor-heart-sound/1.0.3/training_data" data/raw/circor_training_data
```

## 2. Level 1 — quick verification (no raw data; measured: under 1 s)
```bash
.venv/bin/python scripts/p5_verify_integrity.py       # manifests, frozen folds, protocol locks, history hash map
.venv/bin/python -m pytest -q                         # 81 tests collected, 81 passed (2026-10-29)
.venv/bin/python scripts/p4_check_numbers.py          # report and slides use registry numbers only
```
Expected output of the first command: `MANIFEST_v1.sha256: 52/52 OK`, `MANIFEST_final.sha256: 311/311 OK`, folds OK
(sha256 `c4aa74c7…2339`), every protocol lock OK at the commit where it was made, and `ALL INTEGRITY CHECKS PASSED`.
Why "at the commit where it was made": the protocol documents and `configs/protocol_v2.json` received dated amendments
and later pre-registrations after each lock, so their current hashes differ by design. The script checks each lock
against `git show <lock commit or tag>:<file>` and checks that the Phase-3 pre-registration text is an exact byte prefix
of the current `docs/PROTOCOL_V3_PREREG.md`. Manual equivalent:
`git show protocol-v2-lock:configs/protocol_v2.json | shasum -a 256` must equal the first line of `configs/protocol_v2_lock.sha256`.

## 3. Level 2 — regenerate tables and figures from saved predictions (no raw data)
These scripts write into frozen paths. **Run them in a disposable worktree**, then compare:
```bash
git worktree add --detach /tmp/ec418-verify HEAD && cd /tmp/ec418-verify
PY=~/path/to/ec418-circor-research/.venv/bin/python     # the repository's environment
$PY scripts/07_analyze.py main wavelet_sensitivity       # Phase-1 tables and fig8
$PY scripts/31_final_figures.py                          # final figures + final_wavelet_vs_stft.csv (measured: 23 s)
$PY scripts/32_results_summary.py                        # final_hypotheses.csv, final_decomposition.csv (0.2 s)
$PY scripts/p4_operating_points.py && $PY scripts/p4_numbers.py && $PY scripts/p4_report_tables.py
git status --short                                       # verification criterion: nothing modified
cd - && git worktree remove --force /tmp/ec418-verify
```
Result on 2026-10-29: every table, the final figures and the numbers registry were regenerated **byte-identically**. One
file differed in bytes, `results/figures/fig8_roc_auroc_ci_rf.png` (first rendered on Linux in Phase 1); it is
**pixel-identical** (0 of 1,350,000 pixels differ), so only the PNG encoding differs. Phase-3 tables:
`scripts/p3_03_analyze_scattering.py`, `p3_g2_analyze.py`, `p3_g3a_table.py`, `p3_04_zch_age_check.py` read saved outputs
too, but `p3_02_external_zch.py` needs the ZCHSound data.

## 4. Level 3 — complete reproduction from raw data
Prerequisites: Level 0 and §1 done; Java on the PATH; several GB of free disk for `data/interim/` and `experiments/`.
Outputs go to the same paths as the frozen results, so either work in a fresh clone or compare against the manifests
afterwards. `NPROC` sets the number of worker processes; the last argument of `06` is the number of WEKA JVMs.

**Phase 1** (frozen at tag `v1.0-pilot`; Mac reproduction recipe in `docs/REPRO_MAC.md`):
```bash
.venv/bin/python scripts/01_dataset_audit.py
.venv/bin/python scripts/02_extract_features.py
.venv/bin/python scripts/03_b1_realign_shipped_features.py
.venv/bin/python scripts/04_make_folds.py            # must reproduce configs/folds_patient_level.sha256
.venv/bin/python scripts/05_h1_leakage_b1.py
.venv/bin/python scripts/06_run_patient_level_weka.py main B0,B1,W_stft,W_wpd_db4,A_stft,A_wpd_db4 RF,SMO,MLP,LR 2
.venv/bin/python scripts/06_run_patient_level_weka.py wavelet_sensitivity W_wpd_db6,W_wpd_sym8,W_wpd_coif3,A_wpd_db6,A_wpd_sym8,A_wpd_coif3 RF 2
.venv/bin/python scripts/07_analyze.py main wavelet_sensitivity
.venv/bin/python scripts/08_figures_signals.py
.venv/bin/python scripts/10_posthoc_wpd_smoothing.py  # post-hoc (v1 amendment A1)
```
**Phase 2** (each step and its outputs are tabulated at the top of the named document; recorded run times there):
| Experiment | Commands | Document |
|---|---|---|
| E0 provenance | `scripts/12_e0_provenance.py` | `PROVENANCE_PHYSIONET.md` |
| Mac reproduction | `bash scripts/17_make_data_views.sh <v1.0.3 root>`; `bash scripts/13_repro_mac_shadow.sh data/interim/repro_mac_shadow data/interim/repro_phase1_view`; `scripts/14_repro_mac_compare.py …` | `REPRO_MAC.md` |
| E2 | `NPROC=10 python scripts/15_e2_extract_label_nulls.py`; `python scripts/06_run_patient_level_weka.py e2 E2_{stft,wpd,wpds}_{true,perm,shift} RF,SMO 8`; `python scripts/16_e2_analyze.py e2`; `scripts/23_e2_null_span_displacement.py` | `E2_RESULTS.md` |
| E1 | `NPROC=10 python scripts/18_e1_autosegment.py`; `…19_e1_extract_auto_features.py`; `06 … e1 E1_stft_auto,E1_wpd_auto,E1_wpds_auto,B1,W_stft,W_wpd_db4 RF,SMO 8`; `20_e1_analyze.py` | `E1_RESULTS.md` |
| E1b | `NPROC=10 python scripts/21_e1b_run.py cache`, then `… run 0,1,2,3,4`, `… unknown`, `… evaluate`; `06 … e1b E1b_stft_auto,E1b_wpd_auto,E1b_wpds_auto RF,SMO 8`; `22_e1b_analyze.py` | `E1b_RESULTS.md` |
| D1–D3 | `NPROC=10 python scripts/24_diag_extract.py d23`; `06 … diag D1_*,D2_*,D3_*,W_wpd_db4_smooth RF,SMO 8`; `25_diag_analyze.py` | `D_DIAGNOSTICS.md` |
| E4 | `NPROC=10 python scripts/26_e4_run.py cache`, `… run 0,1,2,3,4`, `… evaluate`; `06 … e4 E4_stft,E4_wpd,E4_wpds RF,SMO 8`; `27_e4_analyze.py`; `28_e4_shortcut_check.py` | `E4_RESULTS.md` |
| S1 | `NPROC=10 python scripts/29_s1_build.py 0,1,2,3,4`; `06 … s1 S1_Wstft_SC,S1_Wwpd_SC,S1_SC_only RF,SMO 8`; `30_s1_analyze.py` | `S1_SHORTCUT.md` |
| Final | `31_final_figures.py`; `32_results_summary.py` | `RESULTS_SUMMARY.md` |

**Phase 3** (see each script's header for arguments; `docs/P3_RESULTS.md`):
`PYTHONPATH=src .venv-scat/bin/python scripts/p3_01_scattering_features.py` (G4 features) → `p3_03_analyze_scattering.py`;
`scripts/p3_02_external_zch.py <ZCHSound dir>` (G1a) → `p3_04_zch_age_check.py`; `NPROC=2 python scripts/p3_g2_run.py 0,1,2,3,4`
→ `p3_g2_analyze.py` (G2); `p3_g3a_table.py` (G3a); cross-platform checks `p3_05_compare_cloud.py`, `p3_06_g2_sealed_compare.py`.

**Write-up:** `p4_operating_points.py` → `p4_numbers.py` → `p4_figures.py` → `p4_report_tables.py` →
`(cd report && tectonic EC418_report.tex)`, `p4_slides.py`, `p4_check_numbers.py`; submission report:
`(cd submission/report_src && tectonic EC418_Assignment2_Research_Report.tex)`.

**Verification criteria for Level 3:** folds hash identical; Phase-1 AUROCs within the tolerances of `docs/REPRO_MAC.md`
(WEKA RF with fixed seeds reproduced within 0.00035 across platforms); `p5_verify_integrity.py` still passes on the
repository you compare against.

## 5. Known reproducibility caveats
* B0's MFCCs are float32 and differ across Linux/macOS by up to 1.53e-5 (`docs/REPRO_MAC.md`); B0 enters no Phase-3 verdict.
* SMO on scattering features is platform-sensitive (`docs/P3_RESULTS.md` §2); RF results are stable.
* The Phase-3 G2 reproduction gate failed on Linux/OpenBLAS and passed exactly on the Mac; the Mac values are official.
