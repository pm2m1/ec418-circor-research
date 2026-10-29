# THIRD_PARTY_NOTICES

Components in this repository that are not the author's own work, with the licence **as verified in the files** (or
marked as not verified), what is redistributed, and the obligations that follow. This is an inventory, not legal advice;
items under "Open questions" are unresolved. The project's own licence is not yet chosen: see
[`docs/LICENSING_DECISION_REQUIRED.md`](docs/LICENSING_DECISION_REQUIRED.md).

| Component | Path | Source / version | Copyright holder | Licence (verification) | Redistributed? | Obligations |
|---|---|---|---|---|---|---|
| WEKA 3.9.7 | `tools/weka.jar` (local-only) | Upstream: University of Waikato; JAR from python-weka-wrapper3 0.3.3 source release | University of Waikato | GPL-3.0 (upstream) | Not in current Git tree; distributed in historical commits | See `tools/WEKA_DEPENDENCIES.md` for pinned archive and checksum. Historical redistribution and applicable GPL source/licence obligations are not erased by removing the current tracked binary. |
| Matrix Toolkits Java (MTJ) | `tools/mtj.jar` (local-only) | Version 1.0.4 (embedded Maven POM); python-weka-wrapper3 0.3.3 | MTJ authors | GNU LGPL (POM does not specify version; upstream terms must be verified) | Not in current Git tree; distributed historically | Preserve upstream LGPL notices and compliance for previous distributions. |
| netlib-java core | `tools/core.jar` (local-only) | Version 1.1.2 (embedded Maven POM) | netlib-java authors | BSD-style upstream; exact bundled-file notice to be confirmed | Not in current Git tree; distributed historically | Preserve applicable upstream copyright and licence notices for historical distributions. |
| ARPACK (F2J build) | `tools/arpack_combined.jar` (local-only) | F2J/ARPACK JAR from python-weka-wrapper3 0.3.3 | ARPACK/netlib authors | Precise bundled-file licence unverified | Not in current Git tree; distributed historically | Identify the original licence/notice if redistributing this binary again; historical compliance is separate. |
| WekaBatchRunner | `src/ec418/weka/WekaBatchRunner.java`, `tools/build/` | written for this project; links against WEKA | the author | project code (see licensing decision); a program that links GPL-3.0 WEKA is likely subject to GPL-3.0 when distributed | yes | see decision document. |
| Springer LR-HSMM segmentation, Python port | `src/ec418/segmentation/lr_hsmm.py` | port of PhysioNet "hss" v1.0 MATLAB/C reference code (DOI 10.13026/vnt9-kf93); Springer, Tarassenko & Clifford, IEEE TBME 2016 | original: D. Springer and co-authors; port: the author | GPL-3.0 (reference code GPL-3.0 per `docs/E1b_RESULTS.md`; the file declares the port GPL-3.0) | yes, source | derivative of GPL-3.0 code: distribute under GPL-3.0 with licence text and attribution. |
| Baseline repository snapshot | `references/baseline_repo/` | github.com/chihoon1/Murmur, commit `56b9846` | Chihoon Lee (2023) | MIT (`references/baseline_repo/LICENSE`) | yes, source + feature CSVs | keep the MIT notice. The shipped `case_features/`, `control_features/` are derived from CirCor data, which is ODC-By (row below); the MIT notice does not change the data licence. |
| Baseline DWT port | `src/ec418/wavelets/dwtr_port.py` | NumPy port of `references/baseline_repo/MatlabFunctions/dwtr.m` | the `dwtr.m` file has **no author or licence header**; distributed in the MIT repository above | MIT via the baseline repository (origin of `dwtr.m` not established) | yes, source | keep MIT notice; see open questions. |
| PhysioNet Challenge 2022 scoring code | `references/official_eval/` | github.com/physionetchallenges/evaluation-2022, commit `e5540fb` (`COMMIT.txt`), unmodified | PhysioNet/Computing in Cardiology Challenges (2022) | BSD-2-Clause (`references/official_eval/LICENSE`) | yes, source | keep copyright notice and licence text. |
| CirCor DigiScope v1.0.3 | not in git (raw data); derived features in `data/processed/`, per-patient predictions in `results/predictions/` | PhysioNet, <https://physionet.org/content/circor-heart-sound/1.0.3/> | Oliveira et al. / PhysioNet | ODC-By 1.0 (dataset `LICENSE.txt`, checksum-verified; `docs/PROVENANCE_PHYSIONET.md`) | derived data only | attribution: cite Oliveira et al. 2022 (IEEE JBHI) and PhysioNet (Goldberger et al. 2000). |
| ZCHSound | not in git; derived per-recording scores in `results/predictions/p3_external_zch_scores.csv` | official release via its GitHub mirror (`results/logs/p3_mac_zchsound.txt`) | Jia et al. | CC BY 4.0 (`results/logs/p3_mac_zchsound.txt`) | derived scores only | attribution: cite Jia et al., IEEE TBME 71(8), 2024, doi 10.1109/TBME.2023.3348800. |
| Python dependencies | `pyproject.toml`, `configs/requirements_frozen.txt` | PyPI (numpy, scipy, pandas, PyWavelets, scikit-learn, librosa, …; kymatio 0.3.0 in `.venv-scat`; python-pptx for slides) | respective authors | their own licences | **no** (installed, not vendored) | none for referencing; check before vendoring. |
| Literature full texts | `data/interim/g3b_fulltext/` | publishers / preprint servers | publishers / authors | various | **no** (git-ignored cache) | `references/g3b/evidence_pack.md` contains short quoted passages for research use; quotations are attributed per paper. |

## Open questions (not resolved here)
1. **Previously tracked binary dependencies:** WEKA, MTJ, netlib-core and ARPACK JARs were removed from the current Git tree but remain accessible through historical commits. Reproduction now uses a pinned source archive and SHA-256 verification (`tools/WEKA_DEPENDENCIES.md`). Historical licence/source obligations should still be reviewed; the full GPL-3.0 text must accompany any GPL-derived source distributed under it.

2. **GPL-3.0 reach:** `lr_hsmm.py` is a GPL-3.0 derivative and `WekaBatchRunner.java` links WEKA. Whether the whole project
   must be distributed under GPL-3.0, or only these files, is a decision for the owner (see the decision document).
3. **Origin of `dwtr.m`:** it may come from an earlier wavelet toolbox rather than from the baseline authors; if so, its
   original licence governs `dwtr_port.py`.
4. **Derived data:** per-patient features and predictions derived from CirCor (ODC-By) and ZCHSound (CC BY 4.0) are
   redistributed; both licences permit this with attribution, which `README.md` and the reports give.
