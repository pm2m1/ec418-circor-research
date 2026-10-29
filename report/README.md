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

The G3b literature audit was not completed (docs/G3B_AUDIT_PROTOCOL.md amendment A3): the report and slides contain no
audit result or prevalence claim, keep the Nogueira/Nie case studies, and list the audit as future work. The ZCHSound
"first evaluation" sentence was removed, because its condition (completed G3b full-text checks) can no longer be met.
