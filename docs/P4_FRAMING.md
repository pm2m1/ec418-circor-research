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
