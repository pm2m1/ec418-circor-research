# LICENSING_DECISION_REQUIRED — what the owner must decide

The repository is public but has **no licence for the project's own code**, so by default all rights are reserved by
the author. No licence has been added on the owner's behalf. Third-party components and their obligations are listed in
[`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

## Facts that constrain the choice
1. `src/ec418/segmentation/lr_hsmm.py` is a port of GPL-3.0 code and is declared GPL-3.0; it must stay GPL-3.0.
2. `tools/weka.jar` (GPL-3.0) is redistributed, and `src/ec418/weka/WekaBatchRunner.java` links against WEKA.
3. `references/baseline_repo/` (MIT) and `references/official_eval/` (BSD-2-Clause) keep their own licences.
4. Data derived from CirCor (ODC-By 1.0) and ZCHSound (CC BY 4.0) keep their licences and need attribution.

## Decision 1 — licence for the project's own code (choose one)
* **A. GPL-3.0 for the whole repository (simplest and safest).** Compatible with the GPL-3.0 port, WEKA, MIT and BSD-2
  components. Add a top-level `LICENSE` with the GPL-3.0 text.
* **B. A permissive licence (e.g. MIT) for the project's own files, with GPL-3.0 kept for `lr_hsmm.py` and the WEKA
  runner**, stated file by file. Possible, but anyone distributing the combined work must still comply with GPL-3.0;
  it needs a clear per-file statement.
* **C. No licence** (all rights reserved). Others may read the public code but not legally reuse it; the GPL-3.0
  obligations for the redistributed WEKA jars and the GPL port still apply.

## Decision 2 — licence for documentation, report and slides
For example CC BY 4.0, or the same as Decision 1, or all rights reserved. Check whether the course or the institute
has rules on publishing coursework.

## Decision 3 — compliance actions (independent of 1 and 2)
* Add the GPL-3.0 and LGPL texts and a WEKA 3.9.7 source pointer under `tools/` (or stop redistributing the jars and
  document how to obtain them; the old README gave a recipe).
* Confirm the licences of `tools/core.jar` and `tools/arpack_combined.jar`.
* Decide whether to ask the baseline authors about the origin of `dwtr.m`.

Once decided, add the `LICENSE` file(s), update the "Licensing" section of `README.md` and `CITATION.cff`
(`license:` field), and remove this document or mark it resolved.
