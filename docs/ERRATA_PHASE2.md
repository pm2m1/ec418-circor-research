# ERRATA_PHASE2 — interpretation corrections for Phase-2 results

No number, prediction file or verdict changes. Only the interpretation of E2 is corrected. Every figure below comes
from `scripts/23_e2_null_span_displacement.py` → `results/tables/e2_null_span_displacement.csv`.

## E2-1 (2026-10-27): the E2 nulls also moved labels out of the expert-annotated spans
**Implementation (confirmed from the code):** `perm` (`np.random.default_rng(crc32(rec_id)).permutation(labels)`) and
`shift` (`np.roll(labels, k)`) in `src/ec418/features/label_nulls.py` act on the **whole-recording** column-label vector
built by `column_labels` in `scripts/15_e2_extract_label_nulls.py`. That vector includes the columns the expert left
unannotated (label 0; median 48.3 % of a recording). Amendment I1 item 1 stated this for `perm`. The E2 interpretation
did not draw the consequence.

**Consequence:** the null labels are not confined to the expert-annotated (probably cleaner) spans. The true-vs-null
gap therefore combines **cardiac-cycle timing** and **the expert's selection of which spans to annotate**:

| Null | median share of its labelled columns in expert label-0 columns | Present | Absent | systole labels in label-0 columns |
|---|---:|---:|---:|---:|
| `perm` (primary, H5a–c) | **48.4 %** | 40.5 % | 47.8 % | 48.4 % |
| `shift` (secondary, H5d) | **2.8 %** | 2.6 % | 2.7 % | 0.0 % |

* **`perm` (H5a–c, true − perm +0.13 to +0.17 RF):** about half of the null's labels sit outside the expert spans,
  and the share differs by class (the expert annotated more of the Present recordings). This gap is **timing + span
  selection** and must not be read as timing alone.
* **`shift` (H5d, true − shift +0.19 to +0.21 RF):** implemented on the whole vector too, but a shift of less than
  one heart cycle moves only ~3 % of the labels (and no systole labels) out of the long annotated blocks. H5d therefore
  holds span selection *almost* fixed and is close to a pure timing (phase) contrast. It still keeps the pre-registered
  caveat that shifts near 0.5·T can partly swap systole and diastole.

**Statements corrected:**
* `docs/E2_RESULTS.md` §"What this means" 1 ("timing matters … physiological timing carries most of it"; "with …
  annotation coverage held fixed") → the *amount* of annotated coverage was held fixed, but its *location* was not for
  `perm`. The primary-null gap is timing + span selection. The secondary-null gap (`shift`) is mostly timing.
* `docs/PROTOCOL_V2_LOCKED.md` E2 ("they also control for the coverage shortcut") → true for the number of annotated
  columns only, not for which columns.
* `docs/E1_RESULTS.md` §8.1 and `docs/E1b_RESULTS.md` §7.4 cite E2 as "timing carries the gain" → read with this
  correction.

The split between span selection and timing is measured by the pre-registered diagnostics D1–D3
(`docs/D_DIAGNOSTICS.md`).
