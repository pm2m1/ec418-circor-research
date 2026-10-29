# P4_TITLE — title candidates and clash checks (2026-10-29)

> **Historical phase document — superseded by later experimental results.** Title candidates and clash checks of 2026-10-29. On a later instruction of the author the submission uses "Physiology-Aligned Multiresolution Analysis for Patient-Independent Heart-Murmur Detection: A Comparative Study of Wavelet and Fourier Features", the title this document had dropped (overlap with Lin et al., LNCS 2026, and the wording note below); that choice is the author's. The historical content and results below are unchanged.

Excluded by instruction: "Physiology-Aligned Hierarchical Network for Heart Murmur Detection" (Lin et al., LNCS 2026; the
title exists in OpenAlex, 2026) and close variants. Our earlier working title, "Physiology-Aligned Multiresolution Analysis…",
is also dropped (too close, and "multiresolution" overstates the role of the transform, which our results show does not matter).

Clash checks: OpenAlex exact-phrase title search (`filter=title.search:"…"`), OpenAlex relevance search, and one web search
for candidate 1 (2026-10-29). "Hits" = OpenAlex works whose title contains the phrase.

| # | Candidate | Distinctive phrases checked → result | Notes |
|---|---|---|---|
| 1 | **Timing, Not Transform: Shortcut-Controlled and Externally Validated Murmur Detection on CirCor** | "timing, not transform" → 0; "timing not transform" → 0; "externally validated murmur" → 0; "shortcut-controlled" → 3 (closest: *Shortcut-controlled performance attribution for multi-sensor acoustic emission source classification on a PMMA plate*, Smart Mater. Struct. 2026, doi 10.1088/1361-665x/ae9a1a, a different field); "not the transform" → 1 (*DriftNet: Learn the Decision, Not the Transform*, Zenodo 2026, ML software); web search for "Timing, Not Transform" murmur → no such title | Short and states finding 1 + 2. "Externally validated" is accurate but the external label is CHD, not murmur, so the abstract must say so. "Shortcut-controlled" is accurate (S1/G2 control the shortcut), but the title must not suggest a shortcut-free gain over STFT (H12a not established). |
| 2 | Cardiac-Cycle Timing, Not the Time–Frequency Transform, Drives Patient-Level Murmur Detection: A Pre-registered CirCor Study with External Validation | "drives murmur" → 0; "pre-registered" + murmur → 1 (unrelated: bird murmuration replication, 2026); "murmur detection" + "external validation" → 0 | Most explicit. Long. "Drives" is strong; it is supported by the E2 and D2 results (+0.15 AUROC) only with expert or near-expert timing. |
| 3 | Wavelets, Fourier or Scattering? Cardiac Timing Matters More Than the Transform for Heart-Murmur Detection | "timing matters more than" → 18 (business/management titles, none on signals); "wavelets, fourier" → 76 (signal-processing method titles, none on murmurs) | Question form fits the course theme (wavelets). The phrase "timing matters more than" is common in other fields. |
| 4 | Where the Gain Comes From: Cardiac Timing, Span Selection and Shortcuts in Pre-registered Murmur Detection on CirCor | "where the gain comes from" → 0; "span selection" + murmur → 0 | Emphasises the decomposition (D1–D3, E4, S1, G2). Does not mention external validation. |
| 5 | The Cost of Oracle Segmentation: A Pre-registered, Shortcut-Controlled Study of Murmur Detection on CirCor and ZCHSound | "cost of oracle" → 2 (unrelated, 1992 database cost estimation); "oracle segmentation" → 2 (computer vision, unrelated); "murmur detection" + ZCHSound → 0 | Fits the G3 framing (test-time oracle use). Risk: our own deployable pipeline nearly closes the oracle gap (Δ_oe for E4 ≈ 0.006), so the title must not imply that the cost is large for every pipeline. |

Recommendation: **#1** (as proposed). It is short, has no clash and states the two robust findings. The subtitle wording keeps the
claims within what was shown.
