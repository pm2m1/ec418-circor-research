# Google Scholar transcription check (2026-10-29)

**Scope.** Ranks 1–100 of `scholar_manual.csv` (transcribed from the screenshots by Claude in the cloud workspace) were checked
row by row against the 10 screenshots `scholar_pages/scholar_p1a.png` … `scholar_p5b.png` (Scholar pages 1–5, 20 results each)
by Claude Code on the Mac. Fields checked: title, authors, year, venue, source domain and rank. The 14 PNGs match
`scholar_pages/SHA256SUMS.txt` (14/14; the checksum file lists them under an `imgs/` prefix, verified by file name).

**Result: 100 rows checked, 0 errors, 0 fixes.**

Observations (correct transcriptions, not errors):
* Titles, author lists and venues are truncated with "…" exactly as Scholar shows them (e.g. rank 11). Ranks 97
  ("Classification of phonocardiograms using") and 99 ("Signals Using Support Vector Machines") are partial titles as displayed.
  These are resolved by title match during deduplication.
* No year is shown for ranks 27, 54, 66 and 97; the year is left empty.
* Scholar's own spellings are kept (rank 13 "aproach … MurMur"). Author superscript markers (rank 42 "Chávez-Loya¹") are
  omitted.
* Ranks 101–140 (`scholar_manual_extra_rank101-140.csv`, Scholar pages 6–7) are kept but **not screened**, per the locked
  protocol (first 100 results).
