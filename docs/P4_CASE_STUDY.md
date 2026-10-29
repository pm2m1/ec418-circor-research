# P4_CASE_STUDY — test-time oracle conditioning in a 2026 CirCor paper

Primary case: **Nogueira M., Oliveira J. H., Ferreira C. F., Coimbra M. T., Jorge A. M., "Selection of Heart Sound Segments
for Synchronous Classification of Multi-channel Heart Sounds", arXiv 2608.21499v1 (21 Aug 2026)**, full text read
(12 pages). Second, short case: **Nie J., Liu R., Mahasseni B., Azemi E., Mitra V., "Model-driven Heart Rate Estimation and
Heart Murmur Detection based on Phonocardiogram", arXiv 2407.18424v1 (MLSP 2024)**, full text read (6 pages).
We describe what each paper did, quoting it, and why its numbers are not on the same scale as ours. Nothing here is a
judgement of the papers' validity for their own aims.

## 1. Nogueira et al. 2026

**Where the expert annotation is used.**
* §3.2 Segmentation (p. 4): *"Leveraging the fundamental heart sound (S1, S2) boundary annotations provided in the CirCor
  Digiscope Dataset Oliveira et al. [2021], the original PCG signals were segmented. Segments of length T = 3 seconds were
  extracted starting from the S1 state"*, and *"From a total of 2,940 PCG signals, this process generated 49,833 three-second
  segments."*
* §3 method overview (p. 4): *"Segmentation: Division of signals into three-second segments using provided annotations for
  data augmentation (Section 3.2)."*
* §4 (p. 7): the evaluation uses the same 735 patients, *"each represented by four three-second signal segments—one from each
  auscultation spot"*.
* Reading: 2,940 = 4 × 735, i.e. **every** signal of every patient, including all ten test folds, is segmented from the
  expert S1/S2 annotation. No automatic segmenter is described. A model-input segment can only start at an annotated S1, so it
  comes from an expert-annotated stretch. The one segment per spot is then chosen by clustering (§3.4, Algorithm 1).

**Evaluation unit and split.**
* §4 (p. 7): *"Given the class imbalance (≈ 80% normal vs. 20% abnormal patients), we employed patient-level ten-fold
  stratified cross-validation to maintain the original class distribution across all folds."* Unit = **patient** (one decision
  from four segments). Grouping of linked visits (`Additional ID`) is not mentioned.
* §2 (p. 3): *"From the total of 1,568 patients in the dataset, 735 met the inclusion criterion of having a complete set of
  recordings from all four auscultation spots"*. 1,568 is the size of the full CirCor collection (the public PhysioNet
  release has 942 patients), and the analysed cohort is restricted to patients with all four spots.
* Label: the paper speaks of *"normal vs. abnormal patients"* (§4), *"patient outcome prediction"* (§3, p. 3) and
  *"pathology detection"* (§5). It does not state explicitly whether "abnormal" is the murmur label (Present) or the clinical
  Outcome.

**What the headline measures.** §4.1 (p. 9), Eq. 3: *"Overall = (Se + Sp)/2"*, i.e. **balanced accuracy at one decision
threshold**, called "overall accuracy". Table 1 (p. 9): multi-input CNN Se 0.955, Sp 0.976, **Overall 0.965 (0.043)**, the mean
(SD) over 10 folds. It is not an AUROC.

## 2. On one axis with our results (all ours: WEKA RF, 874 patients, subject-grouped 5 × 5 folds)
Our numbers come from saved tables; the report pulls them from `report/numbers.json`.

| Setting | Uses expert annotation on test data? | Patient AUROC (repeat-averaged) | (Se + Sp)/2 at the inner-fold spec ≥ 0.80 threshold |
|---|---|---|---|
| Nogueira et al. 2026 multi-input CNN | yes (segments start at annotated S1) | not reported | **0.965** ("Overall", Eq. 3) |
| ours: expert labels (E2 `true`, aligned STFT) | yes (oracle) | 0.815 | 0.736 |
| ours: E4 automatic (HSMM + span detector, STFT) | no | 0.809 | 0.739 |
| ours: E4q shortcut-free (STFT) | no | 0.799 | 0.724 |
| ours: timing destroyed (E2 `shift` / `perm`, STFT) | yes, but wrong timing | 0.613 / 0.642 | — |
| ours: whole-signal STFT, no segmentation | no | 0.751 | 0.692 |
| ours: external, ZCHSound clean (CHD label), whole-signal STFT | no | 0.709 | — |

Sources: `results/tables/e4_auroc.csv`, `diag_auroc.csv`, `p3/g2_auroc.csv`, `p4/operating_points.csv`,
`p3/g1a_external_any_chd.csv`.

**Conditioning gap in our own data** (`results/tables/p3/g3a_conditioning_gaps.csv`, RF, STFT; Δ_oe = AUROC(expert) −
AUROC(automatic)): E1 naive envelope segmenter 0.050 [0.011, 0.090]; E1b HSMM on the whole recording 0.106 [0.063, 0.148];
E4 0.006 [−0.031, 0.045]; E4q 0.016 [−0.023, 0.055]. Wrong timing costs Δ_or = 0.174–0.202.

**Why the numbers are not comparable**, as facts:
1. **Different metric:** balanced accuracy at a threshold vs. our AUROC. On the same balanced-accuracy scale, our
   expert-label model reaches 0.736.
2. **Test-time oracle:** their test segments are cut at expert S1 annotations inside expert-annotated stretches. In our data,
   using the expert annotation instead of a naive automatic segmenter is worth 0.05–0.11 AUROC (Δ_oe E1/E1b), whereas our
   learned span selector E4 closes the gap to about 0.01.
3. **Different cohort and label:** 735 patients with all four spots from the full 1,568-patient collection, versus our 874
   public-release patients with Unknown excluded. The label is "normal vs abnormal" without an explicit murmur definition.
4. **Different validation:** a single ten-fold CV without stated linked-visit grouping and no external set (the paper names
   this as a limitation, §5.1), versus our subject-grouped repeated CV plus external validation on ZCHSound.

**Message.** A test-time oracle changes what a number measures. In our data, conditioning on the expert segmentation is worth
up to about 0.1 AUROC over a naive automatic pipeline, and wrong timing costs about 0.17–0.20. The estimates we report as
deployable (E4, E4q) need no expert annotation at test time and are validated externally. Even so, their advantage over
whole-signal STFT given the same span/missingness information is not established (H12a).

## 3. Second case (short): Nie et al. 2024
* §2 Data (p. 2): *"only part of each heart sound recording is annotated"*, and *"a sliding window with window length = 5 s and
  stride = 1 s is applied to the raw PCG audio files with the annotated period longer than 5 s"*. So test snippets, too, come
  only from expert-annotated periods.
* §2 (p. 2): *"The dataset is split into a training set (80%), a validation set (10%), and a test set (10%). The audio
  snippets in each set are from different subjects."* (subject-disjoint).
* Unit = 5-s **snippet**. Murmur loss and accuracy use only snippets labelled Absent or Present (§3.2, Eq. 2), so Unknown is
  excluded.
* Headline: abstract (p. 1) *"accuracy over 95% in murmur detection"*; §4 (p. 4) *"The best 2dCNN-MTL models for murmur detection
  achieve an accuracy of 97.49%"*.
* The authors themselves note the difference in setting, §5 (p. 4): *"detection accuracy is computed using audio snippets with
  labels indicating the presence (1) or absence (0) of murmurs. In contrast, the accuracy figures reported by other projects
  primarily rely on the detection outcomes derived from complete audio recordings within the hidden test set."*
