# RESEARCH_AUDIT — corrections to the earlier dossier, source checks, novelty

Evidence levels: **[run]** = measured in this repository; **[code]** = read in released source code;
**[FT]** = paper full text / landing page fetched this session; **[abs]** = abstract only; **[inf]** = inference.

## 1. What the dossier got right
| Claim | Status |
|---|---|
| CirCor public set 942 patients / 3163 recordings, 179/695/68 | **confirmed [run]** |
| 4 kHz, S1/S2 segmentation `.tsv` provided | **confirmed [run]** (3162/3163 recordings) |
| "~70 children have two visits" (community claim) | **confirmed [run]**: 70 symmetric `Additional ID` pairs |
| Baseline splits by recording, not patient | **confirmed [code]**: `train_test_split` on rows; 95.8 % of test patients also in train [run] |
| Baseline "sensitivity 82 %" probably = Absent recall | **strongly supported [run]**: reproduced Absent recall 0.80–0.83, Present recall 0.54–0.56; arithmetic only fits the swapped reading |
| Unknown merged into Absent | **partly confirmed [code]**: Unknown recordings sit in the control *multifractal* table only (see §2) |
| Challenge best hidden-test murmur weighted accuracy 0.780 | **confirmed [FT]** (PLOS Digit Health 2023; 779 entries / 87 teams / 53 working codebases) |
| WEKA's CV is not group-aware → generate folds in Python | **confirmed**; implemented |

## 2. What the dossier got wrong or missed
1. **Band-width arithmetic (Issue A).** Depth-4 WPD at 2 kHz gives 16 bands of **62.5 Hz**
   (fs/(2·2^J) = 1000/16), not 125 Hz. 125 Hz is the 4 kHz figure. Fixed, unit-tested
   (`tests/test_wavelets.py::test_band_width_math`).
2. **Nominal ≠ real bands.** Measured db4 depth-4 packet responses have side-lobes as high as ≈ −5 to −10 dB
   in neighbouring/mirrored bands (`results/figures/fig7_packet_frequency_responses.png`); sym8 is cleaner.
   "62.5 Hz bands" must always be called *nominal*.
3. **Packet ordering.** pywt's default `natural` (Paley) order is **not** frequency order; a test proves a
   10.5-band tone lands in the wrong index in natural order. We use `order='freq'`.
4. **Baseline wavelet.** Paper text says Daubechies-6; the released code uses an 8-tap **Symlet-4** filter
   [code + test]. The dossier repeated "db6".
5. **Missed defect.** The released baseline feature tables are **row-misaligned** for the control class
   (2375/2391 rows mix two recordings; 156 Unknown rows mean-imputed and labelled control). Verified to
   1e-15 with an exact port of the authors' DWT [run]. See `docs/BASELINE_AUDIT.md`.
6. **Leakage size.** The dossier expected a measurable leakage gap for this baseline. Measured:
   ΔAUC +0.015 (CI −0.004…+0.035) — **not supported** at the pre-registered 0.03 threshold [run].
7. **"Ceiling ~0.78".** A leaderboard number on a different (hidden) set is a *reference point*, not a
   ceiling; later work reports higher murmur scores (e.g. Sensors 2024, murmur score 0.82 [abs]).
   Public-set CV must not be compared to hidden-test numbers as if equivalent.
8. **Data version.** The copy obtainable here lacks the `Outcome` field (Challenge-2022 1.0.0 training
   release, as cited by the baseline paper) — the clinical-outcome study cannot be done from it.
9. **Unknown semantics.** "Unknown = poor-quality recording" is an oversimplification: it is the
   annotator's inability to characterise the murmur. Data show it is *partly* quality-related (much lower
   segmentation coverage, 3–5× more clipping) [run].
10. **Linked children disagree.** 15/70 linked children have different labels across visits, including
    4 Absent↔Present [run] — not mentioned in the dossier; matters for grouping and label noise.
11. **Oracle-segmentation shortcut.** Annotation coverage differs by class (Present 0.61 vs Absent 0.52);
    coverage alone gives AUROC 0.56 [run]. Aligned features must be labelled oracle-assisted.

## 3. Source verification (this session)
| Source | Verified | Method |
|---|---|---|
| Vimalajeewa, Lee, Vidakovic. *Multiscale analysis of heart sound signals in the wavelet domain for heart murmur detection.* Sci Rep 15:10315 (2025). doi:10.1038/s41598-025-93989-0 | title, authors, vol/article, 2025, DOI registered | Crossref (FastTrack verify_reference) + Nature page [FT] |
| Reyna et al. *Heart murmur detection from phonocardiogram recordings: The George B. Moody PhysioNet Challenge 2022.* PLOS Digit Health 2(9):e0000324 (2023). doi:10.1371/journal.pdig.0000324 | weights 5/3/1, patient-level, 0.780 top | [FT] + official scoring code |
| Official scoring code physionetchallenges/evaluation-2022 @ `e5540fb` | `compute_weighted_accuracy` used unmodified | [code], vendored in `references/official_eval/` |
| Oliveira et al. CirCor DigiScope dataset, IEEE JBHI 26(6):2524–2535 (2022) | cited by dataset/README | not re-fetched (PhysioNet blocked) |

## 4. Novelty audit (Issue E) — focused 2023–2026 search
Searched: FastTrack/OpenAlex (wavelet-packet + systolic/diastolic + murmur; quality/abstention + PCG),
PubMed (murmur ∧ CirCor/PhysioNet-2022 ∧ wavelet/patient-level/segmentation, 2024–). Leads read at
abstract level unless noted.

| Idea | Prior art found | Verdict |
|---|---|---|
| Wavelets for murmur detection | Vimalajeewa 2025 [FT]; Dohare 2025 CMBBE (CWT) [abs]; Patwa 2025 IEEE Sens J (scattering) | **Already established** |
| Systolic / cycle-aligned features | Touahria et al. 2023 BSPC — feature selection highlights the systolic segment for normal/murmur beats [abs]; McDonald et al. 2024 PLOS DH (CUED, Challenge winner) — RNN+HSMM segments and detects murmurs [abs] | **Already established** |
| Signal-quality estimation for murmur screening | McDonald et al. 2024 estimates recording quality inside the model [abs]; De Simone et al. 2025 preprint spectral gate + abstention | **Already established** (wavelet SQI = minor variant) |
| Patient-level / leakage-safe CirCor evaluation | Elola 2023 JBHI (patient-level CV + hidden test) [abs]; Ameen et al. 2026 Sci Rep (patient-level splits on PN2022) [abs] | **Already established** |
| Automatic segmentation on CirCor (to remove oracle) | Arjoune 2024 IEEE Access; Tatulli 2025 CBM; Grooby 2024 EMBC; Huo 2026 BPEX [abs, PubMed] | **Established — usable as tooling** |
| 2×2: WPD vs STFT (matched nominal bands/grid/dims; not matched effective time resolution) × whole vs cycle-aligned pipelines (different feature definitions), patient-grouped, WEKA | none found doing this exact controlled comparison | **Incremental improvement / distinctive engineering ablation** (not a new algorithm) |
| Reproducibility audit of the 2025 Sci Rep wavelet baseline (feature misalignment, metric labelling, leakage size) | none found | **Distinctive (small) reproducibility contribution** — must be handled respectfully; contact authors before publishing claims |

**Honest scope:** this project's defensible contribution is *a corrected, patient-independent, fully
reproducible re-evaluation of a 2025 wavelet baseline plus a controlled test of whether wavelet packets
add value over Fourier bands once the cardiac cycle is accounted for*. It is an incremental engineering
study, not a new method. Results: `docs/PILOT_RESULTS.md`.
