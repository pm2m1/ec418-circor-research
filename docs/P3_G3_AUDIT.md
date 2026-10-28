# G3 — Oracle-segmentation ("conditioning-availability") audit — pilot

Pre-registered in `docs/PROTOCOL_V3_PREREG.md` (G3). Status: **(a) done from reported numbers; (b) pilot, 11 papers,
single coder (Claude) — must be completed and double-coded by the team.**

## (a) Reframing our own results (RF, repeat-averaged AUROC; numbers as reported by the Phase-2 runs on the Mac
— CIs are in the Phase-2 result docs; recompute this table from the saved predictions when merging)

Following Cao et al. (arXiv 2608.03342): oracle = expert `.tsv` labels; estimated = an automatic segmenter;
random = timing destroyed.

| Representation | Oracle (expert) | E1 naive | E1b HSMM | **E4 HSMM + span sel.** | D1 HSMM ∩ expert spans | perm (random) | shift (wrong phase) |
|---|---|---|---|---|---|---|---|
| stft | 0.815 | 0.765 | 0.709 | **0.809** | 0.800 | 0.642 | 0.613 |
| wpd  | 0.798 | 0.736 | 0.707 | **0.791** | 0.783 | 0.651 | 0.606 |
| wpds | 0.800 | 0.723 | 0.712 | **0.796** | 0.791 | 0.669 | 0.595 |

Derived gaps:

| | Δ_oe(E1) | Δ_oe(E1b) | **Δ_oe(E4)** | Δ_or(perm) | Δ_or(shift) |
|---|---|---|---|---|---|
| stft | 0.050 | 0.106 | **0.006** | 0.173 | 0.202 |
| wpd  | 0.062 | 0.091 | **0.007** | 0.147 | 0.192 |
| wpds | 0.077 | 0.088 | **0.004** | 0.131 | 0.205 |

Reading: the aligned features are **highly sensitive to conditioning** (Δ_or 0.13–0.21: wrong timing destroys them).
With a naive or full-recording segmenter the deployable path loses 0.05–0.11 (**this is the inflation any paper
using the expert `.tsv` at test time carries relative to an honest automatic pipeline of that kind**). Learned
span selection (E4) closes Δ_oe to < 0.01 — but S1 showed part of E4's edge over whole-signal STFT may be a
span/missingness shortcut (G2 tests this).

## (b) Literature audit — pilot coding (11 papers; full text read where marked)

Code: test-time expert segmentation = uses the dataset `.tsv` (or expert-annotated spans) to segment/select test
data. Hidden = scored by PhysioNet on the hidden test set (no `.tsv` available there — verified on the Challenge page).

| # | Paper | Test-time expert seg.? | Other test-time oracle | Unit / split | Headline | Source read |
|---|---|---|---|---|---|---|
| 1 | Nogueira et al. 2026, arXiv 2608.21499 | **Yes** (segments start at annotated S1) | expert-annotated parts only | patient, 10-fold stratified (735 pts) | "overall" (mean Se/Sp) **96.5 %** | full text |
| 2 | Nie et al. 2024, MLSP (arXiv 2407.18424) | **Yes** (snippets only from annotated periods > 5 s) | — | snippet; subject-disjoint 80/10/10 | accuracy **95–97 %** (snippet level) | full text |
| 3 | Patwa et al. 2023/25, arXiv 2303.11423 / IEEE Sens J | No | **manual GUI relabelling of noise-only segments (E3), incl. test** | 4-s segment, "not patient-wise" | E2 acc 90.1 %; E3 W.acc 83.7 % | full text |
| 4 | Niizumi et al. 2024, EMBC (arXiv 2404.17107) | No | — | patient; stratified 65/10/25 ×3 (linked visits not stated) | W.acc 0.832 | full text |
| 5 | Zhang et al. 2024, ICASSP (arXiv 2405.03953) | No | — | patient; split not fully specified | W.acc 0.798 | full text |
| 6 | McDonald et al. 2024, PLOS DH (CUED, winner) | No (train only) | — | patient; **hidden test** | W.acc 0.776 (hidden) | full text (medRxiv) |
| 7 | Walker et al. 2022, CinC (arXiv 2305.16691) | No | — | patient; **hidden test** | W.acc 0.771 (hidden) | full text |
| 8 | Elola et al. 2023, JBHI | No | — | patient; 10-fold + **hidden test** | UAR 80.4 % (hidden) | abstract |
| 9 | Vimalajeewa et al. 2025, Sci Rep | No | — | **recording**, random 80/20 | acc 76.6 %, AUC 0.741 | full text + code |
| 10 | Dehghan Manshadi & Mihandoost 2024, Sci Rep | Not stated (12.5-s crop) | — | patient, 80/20 | "accuracy"/"weighted accuracy" 93 % (inconsistent) | full text |
| 11 | Ameen et al. 2026, Sci Rep | No (own peak segmentation) | — | segment/unclear; patient split | acc **98.6 %**; class counts 1,617 "normal" / 1,546 "murmur" recordings — do **not** match CirCor murmur labels (616 Present recordings); **unclear which label was used** | full text |

Pilot pattern (descriptive, n = 11, single coder — not a finding yet): the two papers using expert annotations at
test time report the highest numbers (95–97 %), while hidden-test-scored entries sit at 0.77–0.78 weighted accuracy.
Several papers' units/labels make their numbers non-comparable with any patient-level benchmark.

**To do (team, before any claim):** systematic search per protocol; second coder for all papers; code ≥ 25 papers;
resolve "unclear" by reading code/repos; for #11, check whether the 1,617/1,546 split equals CirCor *Outcome*
recording counts on v1.0.3 (Mac). Report agreement (Cohen's κ).
