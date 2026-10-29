# report/ — research numbers, tables and figures

This directory preserves the **tracked** numerical registry and presentation-ready research figures, not the coursework submission files. Numerical results are generated from saved experimental outputs rather than retyped.

From the repository root:

```bash
.venv/bin/python scripts/p4_numbers.py          # numbers.json and numbers.tex (\nm{key}, \N... macros)
.venv/bin/python scripts/p4_figures.py          # research figures (frozen originals remain in results/)
.venv/bin/python scripts/p4_report_tables.py    # tables/*.tex (registry-backed values)
.venv/bin/python scripts/p4_check_numbers.py    # validates tracked LaTeX tables against the numbers registry
```

**Do not regenerate into frozen paths in your normal working tree.** Use a disposable worktree for reproduction, then compare generated files with the tracked results as described in [`../docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md).

## Optional local report and presentation

The older Phase-4 build scripts remain as optional conveniences:

```bash
.venv/bin/python scripts/p4_slides.py           # creates local, ignored report/EC418_slides.pptx
(cd report && tectonic EC418_report.tex)         # only if you have the local, ignored .tex source
.venv/bin/python scripts/p4_check_numbers.py --include-local
```

The following files are **not tracked** and are **not needed for research reproduction**:

- `report/EC418_report.tex`, `report/EC418_report.pdf`, `report/EC418_slides.pptx`
- `submission/` (coursework report, presentation, screenshots and submission checklist)

The checker verifies the tracked `report/tables/*.tex` files by default. With `--include-local`, it additionally checks any available local report sources and slide decks; it explicitly reports when such optional files are absent.

## Literature-audit scope

The G3b literature audit was **not completed** (see `docs/G3B_AUDIT_PROTOCOL.md`, amendment A3). The Nogueira/Nie case studies remain individual examples, not a literature-wide prevalence estimate. The earlier ZCHSound "first evaluation" claim was removed because its prerequisite full-text audit was not completed. ZCHSound has CHD diagnosis labels, **not murmur labels**.
