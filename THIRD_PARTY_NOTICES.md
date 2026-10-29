# THIRD_PARTY_NOTICES

Components in this repository that are not the author's own work, with the licence **as verified in the files** (or
marked as not verified), what is redistributed, and the obligations that follow. This is an inventory, not legal advice;
items under "Open questions" are unresolved. The project's own licence is not yet chosen: see
[`docs/LICENSING_DECISION_REQUIRED.md`](docs/LICENSING_DECISION_REQUIRED.md).

| Component | Path | Source / version | Copyright holder | Licence (verification) | Redistributed? | Obligations |
|---|---|---|---|---|---|---|
| WEKA 3.9.7 | `tools/weka.jar` | Univ. of Waikato; jar taken unmodified from the python-weka-wrapper3 0.3.3 sdist (PyPI); `weka/core/version.txt` = 3.9.7 | University of Waikato | GPL-3.0 (per the WEKA project; **no licence text is included in the jar or in `tools/`**) | yes, binary | GPL-3.0: ship the licence text and give access to the corresponding source (WEKA 3.9.7 sources are public from the WEKA project/SourceForge); keep notices. |
| Matrix Toolkits Java (MTJ) | `tools/mtj.jar` | from the same sdist; Maven POM inside the jar | MTJ authors | LGPL (POM names "GNU Lesser General Public License", version not stated) | yes, binary | LGPL: ship licence text, allow relinking/replacement, offer source. |
| netlib-java core 1.1 | `tools/core.jar` | com.github.fommil.netlib:core 1.1 (POM in jar) | netlib-java authors | **not stated in the jar** (upstream project states a BSD-style licence — to verify) | yes, binary | keep copyright notice once the licence is confirmed. |
| ARPACK (F2J build) | `tools/arpack_combined.jar` | from the same sdist; no metadata in the jar | ARPACK / netlib authors | **not stated in the jar** (to verify) | yes, binary | confirm licence before further redistribution. |
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
1. **GPL-3.0 text and source offer for WEKA (and LGPL for MTJ):** the repository redistributes the jars but contains no
   licence texts; adding `tools/LICENSES/` (GPL-3.0, LGPL text) and a pointer to the WEKA 3.9.7 source would satisfy the
   usual conditions. The licences of `core.jar` and `arpack_combined.jar` must be confirmed from their upstream projects.
2. **GPL-3.0 reach:** `lr_hsmm.py` is a GPL-3.0 derivative and `WekaBatchRunner.java` links WEKA. Whether the whole project
   must be distributed under GPL-3.0, or only these files, is a decision for the owner (see the decision document).
3. **Origin of `dwtr.m`:** it may come from an earlier wavelet toolbox rather than from the baseline authors; if so, its
   original licence governs `dwtr_port.py`.
4. **Derived data:** per-patient features and predictions derived from CirCor (ODC-By) and ZCHSound (CC BY 4.0) are
   redistributed; both licences permit this with attribution, which `README.md` and the reports give.
