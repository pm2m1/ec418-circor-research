# P4_FRAMING — decisions for the report and slides (author, 2026-10-29)

* **Title:** "Timing, Not Transform: Shortcut-Controlled and Externally Validated Murmur Detection on CirCor" (#1 in
  `docs/P4_TITLE.md`).
* **Comparison with a 2024–26 journal paper:** lead with **B1** (Vimalajeewa et al., *Sci Rep* 2025), reproduced on the same data
  and frozen folds: **E4 − B1 (H9b)** and **A_wpd − B1 (H4b)** from the registry, with CIs and fold counts.
* **The Nogueira (2026) / Nie (2024) case study comes second:** it explains why published 95 %+ figures are not comparable
  (test-time expert conditioning; different label, metric, unit and patient set), stated neutrally as in `docs/P4_CASE_STUDY.md`.
  Include the same-scale figure: our expert-label (Se + Sp)/2 at the inner-fold specificity ≥ 0.80 threshold, with that
  definition.
* No new analysis. Every number comes from `report/numbers.json`.

## Novelty wording (author decision, 2026-10-29)
* Do **not** claim that external validation of CirCor-trained models is new: Kutlu & Çolak 2026 (J Clin Med 15(20), doi
  10.3390/jcm15208058) already test CirCor-trained murmur models zero-shot on PhysioNet/CinC 2016 and Yaseen 2018.
* Allowed claim, **only if the pending G3b full-text checks find no other CirCor → ZCHSound evaluation**: "to our knowledge the
  first evaluation of CirCor-trained murmur models on ZCHSound, an independent paediatric CHD cohort, with a pre-registered
  physiology (subtype-ordering) check". Until those checks are done, the report keeps this sentence marked as conditional.
* Related work cites Kutlu & Çolak 2026 (external validation of CirCor-trained models) and Ladislaus et al. 2026 (arXiv
  2609.37161: aggregation choice and evaluation conventions change measured robustness), next to the oracle-conditioning
  message. Details: `docs/P4_RELATED_WORK_CHECK.md`.
