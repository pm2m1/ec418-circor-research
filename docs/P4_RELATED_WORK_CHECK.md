# P4_RELATED_WORK_CHECK — two 2026 papers read before any novelty wording

This check sits outside the G3b screening and was requested by the authors on 2026-10-29. It reads two recent papers in full,
before any sentence in the report says what is new. For each paper it records the datasets (in particular whether ZCHSound is
used as an external test set), the evaluation unit and split, and where it overlaps with our claims. We describe what each
paper did and quote it with a section or page reference. No judgement is made about either paper's validity for its own aims.

**Result: neither paper uses ZCHSound, and neither evaluates CirCor → ZCHSound.** Neither text contains the string "ZCH". So
the STOP condition is not met. Both papers do overlap with parts of our framing, though, and the novelty wording must respect
that (see the end of this file).

## 1. Kutlu & Çolak 2026, J Clin Med 15(20), doi 10.3390/jcm15208058
"Cross-Dataset Generalization in Phonocardiogram Murmur Classification: A Benchmark Study of Domain-Conditional Performance
and the Role of Multi-Representation Fusion". We read the full text (Europe PMC XML, PMC13706609; the MDPI PDF download was
blocked).

* **Datasets.** CirCor is used for training only. Two external sets are used for zero-shot testing.
  * §1: *"A single internal dataset (CirCor [7]) was used for training, and two external datasets with contrasting
    characteristics were used for zero-shot evaluation: a heterogeneous, multi-source adult/mixed dataset (PhysioNet/CinC 2016
    [5,6]) and a homogeneous, single-protocol five-class dataset (Yaseen 2018 [29])."*
  * §2.1: *"The cross-validation training set comprised 2531 recordings from 753 patients (19 460 five-second segments)"*.
  * **ZCHSound: not used.**
* **Label.** §2.1: *"present and unknown were treated as abnormal, and absent as normal"*. This differs from ours: we exclude
  Unknown. A sensitivity analysis that excludes Unknown is reported in §3.6 and Table S2.
* **Split and unit.**
  * §2.3: *"All models were trained only on the CirCor dataset using five-fold patient-disjoint cross-validation, stratified by
    murmur class."*
  * Internal results are at the **patient** level (*"so internal performance is reported at the patient level (753 patients)"*,
    §2.3). External results are at the **recording** level, because *"the two external datasets provide no patient
    identifiers"* (§2.3).
  * External predictions come from a five-fold ensemble. §2.3: *"No external labels were used at any point in training or model
    selection."*
* **Headline (abstract).**
  * Internal AUROC is about 0.82–0.90 for the deep models.
  * Heterogeneous external set: *"the highest AUROC was 0.738"*.
  * Homogeneous external set: *"PCG-MambaConformer reached an AUROC of 0.985"*.
  * The authors add that *"The near-perfect result on the homogeneous target should be read as technical cross-dataset transfer
    under favorable, highly curated conditions rather than as clinical external validation"*.
  * Reverse transfer (CinC 2016 → CirCor): AUROC 0.612–0.677.
* **Overlap with our claims.**
  * (a) **External validation of CirCor-trained models.** Kutlu & Çolak already test CirCor-trained murmur classifiers zero-shot
    on two independent public datasets. They also report threshold transfer from source to target (§3.4). Our G1a is therefore
    not the first external test of CirCor-trained models. What differs is the target and its label: ZCHSound is a pediatric
    set with CHD diagnoses, our model is a WEKA RF on handcrafted features, and we report external results at the patient level.
  * (b) **Internal vs external gap.** Both papers note that internal accuracy predicts external behaviour poorly.
  * No overlap with our timing/oracle decomposition (E2/E4/E4q) or with the shortcut control (G2).

## 2. Ladislaus, Olatunji, Buol et al. 2026, arXiv 2609.37161v1 (29 Sep 2026)
"The Vote Hides the Failure: Aggregation Choice and Noise Robustness in Heart Murmur Detection" (CMU Africa). We read the full
text (8 pages).

* **Datasets.** CirCor only, *"as released for the George B. Moody PhysioNet Challenge 2022 [2]: 942 patients, 3046
  recordings"* (§3.1, p. 2).
  * Appendix A (p. 6) gives the class counts *"Present 179 (19.0%), Unknown 68 (7.2%), Absent 695 (73.8%)"*, the same patient
    counts as our cohort before Unknown is excluded.
  * **No external dataset.** The single occurrence of "external" in the text is in the funding statement (p. 5). **ZCHSound:
    not used.**
* **Label.** Three classes (Present / Unknown / Absent). The paper reports accuracy, balanced accuracy and the official
  Challenge weighted accuracy (§3.2, p. 2–3).
* **Split and unit.**
  * §3.1 (p. 2): *"We split this into 5 patient-level folds."*
  * Appendix A (p. 6): *"Patients are assigned to 5 folds by sorting patient IDs lexicographically and applying round-robin
    assignment (i mod 5)"*, and *"We confirmed no patient's recordings are split across folds (leakage check, both
    pipelines)."*
  * Grouping of linked visits (`Additional ID`) is not mentioned.
  * The unit is the patient, after aggregating windows/recordings with either the native rule or majority vote. The paper also
    analyses window-level disagreement.
* **What it does.**
  * It reimplements HMS-Net and a BiLSTM (*"verified for structural and behavioral fidelity against their original
    submissions"*, §3.1).
  * It injects four synthetic noise types at inference (§3.2) and compares native vs majority-vote aggregation.
  * It tests noise-augmented fine-tuning with a held-out noise type.
  * Abstract: *"a single aggregate accuracy number can hide failure in opposite directions"*.
* **Overlap with our claims.**
  * (a) **Aggregation and evaluation conventions shape the measured result.** This is close in spirit to our message that a
    test-time oracle changes what a number measures (P4_CASE_STUDY). The mechanism is different (aggregation rule and metric vs
    expert segmentation at test time).
  * (b) **Noise robustness:** we have no noise-injection experiment, so there is no conflict.
  * (c) **Patient-level folds with a leakage check:** the same practice as ours, so it cannot be claimed as new.
  * No overlap with external validation, oracle conditioning, or the shortcut control.

## Consequences for the wording (to be applied in Parts 3 and 5)
1. Do **not** write that external validation of CirCor-trained murmur models is new. Kutlu & Çolak 2026 already do it, on
   CinC 2016 and Yaseen 2018. The report cites them.
2. Author decision (2026-10-29): the allowed claim is "to our knowledge the first evaluation of CirCor-trained murmur models on
   ZCHSound, an independent paediatric CHD cohort, with a pre-registered physiology (subtype-ordering) check", and only if
   the pending G3b full-text checks find no other CirCor → ZCHSound evaluation (see `docs/P4_FRAMING.md`).
3. Ladislaus et al. 2026 are cited next to the oracle-conditioning message as related work on evaluation choices. No claim of
   novelty is made for patient-level folds or leakage checks.
