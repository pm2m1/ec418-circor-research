# report/ — write-up build (Phase 4)

Everything here is generated from saved outputs; no number is typed by hand.

```
.venv/bin/python scripts/p4_numbers.py          # registry: numbers.json + numbers.tex (\nm{key}, \N... macros)
.venv/bin/python scripts/p4_figures.py          # figures/ (new figures; frozen ones are read from results/figures_final/)
.venv/bin/python scripts/p4_report_tables.py    # tables/*.tex (cells are \nm{key} calls)
(cd report && tectonic EC418_report.tex)        # EC418_report.pdf
.venv/bin/python scripts/p4_slides.py           # EC418_slides.pptx (needs: uv pip install -p .venv -e ".[writeup]")
.venv/bin/python scripts/p4_check_numbers.py    # fails on any number not from the registry (whitelist: number_whitelist.txt)
```

The G3b literature-audit section and slide are placeholders until Part 1d (coding of the A1 sample) is complete; the
sentence on ZCHSound novelty is conditional on the pending G3b full-text checks (docs/P4_FRAMING.md).
