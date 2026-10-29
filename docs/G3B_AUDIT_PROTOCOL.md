# G3B_AUDIT_PROTOCOL — literature audit of test-time expert segmentation on CirCor (locked before screening)

Pre-registered as G3(b) in `docs/PROTOCOL_V3_PREREG.md`; this document fixes the operational details. Written and committed
on 2026-10-29, **before any search result was screened**. The 11-paper single-coder pilot in `docs/P3_G3_AUDIT.md` was
written before this protocol; its papers must appear in the screening and are coded afresh under this protocol.
Descriptive audit only: no inference, no statement that any paper is wrong. Numbers in the literature are reported as the
authors report them, and the reasons why they are not comparable with ours are given.

## 1. Sources and query
* **Query** (adapted to each engine's syntax and recorded verbatim in `references/g3b/search_raw.csv`):
  `("CirCor" OR "PhysioNet 2022" OR "PhysioNet Challenge 2022" OR "George B. Moody PhysioNet Challenge 2022") AND murmur`,
  publication years 2022–2026.
* **Engines:** OpenAlex, Semantic Scholar, PubMed and arXiv (run by Claude Code via their APIs/tools; date, engine and exact query
  string saved). **Google Scholar** blocks automated queries (captcha, checked 2026-10-29). A team member therefore runs the
  query in a browser, sorted by relevance, years 2022–2026, and saves the **first 100 results** (title, authors, year, venue,
  URL) to `references/g3b/scholar_manual.csv`. These are merged into `search_raw.csv` **before screening starts**.
* **Citation check:** works citing (a) the CirCor dataset paper, Oliveira et al. 2022, *IEEE JBHI* 26(6):2524–2535, and (b) the
  Challenge paper, Reyna et al. 2023 (George B. Moody PhysioNet Challenge 2022), via OpenAlex `cites:` filters. The same murmur
  filter applies (title/abstract mentions murmur), years 2022–2026.

## 2. Screening
* **Deduplication:** by DOI, then by normalised title. When a paper exists as preprint and journal/proceedings version, the
  **journal/proceedings version is kept** and the preprint is linked.
* **Inclusion:** original studies that report **murmur-detection performance** (any metric) on CirCor data (training set,
  Challenge data or hidden test set).
* **Exclusion (a reason is recorded for every excluded record):** review/survey; duplicate; no CirCor murmur performance number;
  **Outcome-only** (clinical outcome, no murmur result; listed separately); not about heart sounds; out of the year range;
  full text not obtainable (recorded, not silently dropped).
* Title/abstract screening by Claude Code, full-text eligibility check on the remaining records. Every decision and reason goes
  in `references/g3b/screening.csv`; counts are in a PRISMA-style flow in `references/g3b/prisma.md`.
* **Target ≥ 25 included papers.** If fewer qualify, the true number is reported. The list is never padded.

## 3. Coding fields (fixed definitions; examples are illustrative, not taken from any included paper)
1. **Test-time expert segmentation:** `yes` / `no` / `unclear`. `yes` = the dataset `.tsv` or expert-annotated spans are used
   to segment, select or crop **test** data. *Example yes:* "test segments start at the annotated S1 onset". *Example no:*
   "an HSMM trained on the training folds segments every test recording". *Example unclear:* "recordings were segmented into
   cardiac cycles" with no source given.
2. **Evaluation unit:** `patient` / `recording` / `segment` / `unclear`. *Example patient:* one decision per patient from all of
   its recordings. *Recording:* metrics per `.wav`. *Segment:* metrics over cycles or fixed-length windows.
3. **Split grouping:** `patient-grouped` / `not grouped` / `unclear`, plus a note on whether linked visits (`Additional ID`) are
   handled (`yes` / `no` / `not stated`). *Example patient-grouped:* "train/test split by patient ID". *Example not grouped:*
   "recordings were randomly split 80/20".
4. **Unknown-class handling:** `excluded` / `merged with Present` / `merged with Absent` / `3-class` / `not stated`.
5. **Hidden-test evaluation:** `yes` (scored on the official Challenge hidden test set) / `no`.
6. **Headline metric and value**, as reported (abstract preferred, else main results table), with the metric name exactly as used.
7. **Evidence:** a verbatim quote plus a page or section reference for each of fields 1–3.

## 4. Coders and agreement
* **Two independent human coders (Coder A, Coder B)** code every included paper blind to each other, into
  `references/g3b/coding_coderA.csv` and `coding_coderB.csv`. Claude Code provides an evidence pack
  (`references/g3b/evidence_pack.md`: full-text links and the relevant methods/evaluation passages with references) and
  **blank** sheets. It never pre-fills a code. The names of the coders and the resolver are recorded in
  `references/g3b/coders.md` before coding starts.
* **Agreement:** Cohen's κ (`sklearn.metrics.cohen_kappa_score`) for fields 1–3, computed on the **pre-resolution** codes, with a
  percentile bootstrap CI over papers (2000 resamples, seed 0).
* **Resolution:** disagreements are listed in `references/g3b/disagreements.csv` and resolved by discussion with the third team
  member (Resolver). The final codes go in `references/g3b/coding_final.csv`, and the number of disagreements per field is
  reported.
* **Optional AI coder:** Claude Code may code all papers separately, clearly labelled "AI coder". It is **never** one of the two
  coders and never enters κ; only its agreement with the final codes is reported.

## 5. Primary output (descriptive, no inference)
* The proportion of included papers with test-time expert segmentation = `yes` (with `unclear` reported as its own group).
* The **median headline value per group** (`yes` / `no` / `unclear`), computed over the papers whose headline is an
  accuracy-type metric (accuracy, weighted accuracy, balanced accuracy/UAR, mean of sensitivity and specificity). The metric
  type is shown per paper, and other metrics are listed but not pooled.
* The same values by evaluation unit and by split grouping. One figure: one dot per paper (headline value by test-time
  segmentation group, marker by unit and split).
* Computed by `scripts/p4_g3b_summary.py` → `results/tables/p4/g3b_summary.csv`, `g3b_kappa.csv` and the figure.

## Amendments (each dated and committed before the step it affects)
* **A1 (2026-10-29): coding sample.** Sampling frame = all 137 records (98 included + 39 pending full-text). Random order
  via `numpy.random.default_rng(20261029).permutation` over the frame sorted by record ID. Coding sample = first 30 in that
  order. Pending records in the sample are retrieved by the team via library access; one that truly cannot be obtained, or
  turns out ineligible at full text, is replaced by the next record in the order (logged with reason). Both coders code the
  same 30. κ and all proportions are estimated on the sample, with Wilson 95% CIs, generalised to the frame; the remaining
  records are listed but not coded. The AI coder may code the 30 as a separate labelled comparison only.
  *Reason:* 98–137 eligible records is more than two coders can code in the time available. Written and committed before any
  paper was coded and before the sample was drawn.
