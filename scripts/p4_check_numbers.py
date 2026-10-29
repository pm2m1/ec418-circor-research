"""Check registry provenance for research tables and optional LOCAL write-ups.

By default, this checks the tracked report/tables/*.tex files against the
numbers registry. It does not depend on ignored coursework report/slide files
and therefore works in a fresh clone.

Use --include-local to check any locally available, git-ignored LaTeX reports
and PowerPoint decks as well. The checker does not claim to have checked files
that are absent; it reports skips explicitly.

Examples:
    python scripts/p4_check_numbers.py
    python scripts/p4_check_numbers.py --report
    python scripts/p4_check_numbers.py --slides --include-local
    python scripts/p4_check_numbers.py --include-local

All numbers in the registry are derived from saved experimental result tables.
This script checks literal numeric tokens and unknown \\nm{key} references; it
does NOT independently establish the scientific validity of those results.
"""

from pathlib import Path
import glob
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

# Preserve the project's existing token and whitespace handling. Work relative
# to the project root so these paths remain predictable in a clean checkout.
N = json.loads((ROOT / "report/numbers.json").read_text(encoding="utf-8"))
WL = {}
for line in (ROOT / "report/number_whitelist.txt").read_text(encoding="utf-8").splitlines():
    line = line.split("#")[0].strip()
    if line:
        tok, why = [x.strip() for x in line.split("|", 1)]
        WL[tok] = why

# A free-standing number is not part of identifiers B0, S1, H6a, E1b, etc.
NUM = re.compile(r"(?<![A-Za-z_\d.])\d+(?:[.,]\d+)*(?![A-Za-z_\d])")
REG = {t for v in N.values() for t in NUM.findall(str(v["value"]))}
bad = []


def strip_tex(s):
    s = re.sub(r"(?<!\\)%.*", "", s)
    s = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "", s, flags=re.S)
    keys = re.findall(r"\\nm\{([^}]*)\}", s)
    for k in keys:
        if k not in N:
            bad.append(f"report: unknown registry key \\nm{{{k}}}")
    s = re.sub(r"\\nm\{[^}]*\}", " ", s)
    s = re.sub(r"\\N[A-Z][A-Za-z]*", " ", s)
    s = re.sub(
        r"\\(cite|label|ref|input|includegraphics|graphicspath|texttt|url|href|bibitem|documentclass|usepackage)"
        r"(\[[^\]]*\])?\{([^{}]|\{[^{}]*\})*\}", " ", s
    )
    s = re.sub(r"\{\{[^}]*\}\{[^}]*\}\}", " ", s)
    s = re.sub(r"(width|itemsep)\s*=?\s*[\d.]+\\?\w*", " ", s)
    s = re.sub(r"\\setlength\\itemsep\{[^}]*\}", " ", s)
    s = re.sub(r"\[\s*[\d.]+\\(linewidth|textwidth)\]", " ", s)
    s = re.sub(r"\{[\d.]+\\(linewidth|textwidth)\}", " ", s)
    s = re.sub(r"\{@\{\}[lcr@{}]+\}", " ", s)
    s = re.sub(r"\\parbox\{[\d.]+\\linewidth\}", " ", s)
    s = re.sub(r"\\newcommand\{\\\w+\}\[\d\]", " ", s)
    s = re.sub(r"#\d", " ", s)
    return s


def check_report(include_local=False):
    # The tracked research tables must exist. Report sources are deliberately
    # optional because coursework write-ups are stored outside Git.
    files = sorted((ROOT / "report/tables").glob("*.tex"))
    if not files:
        bad.append("report: no tracked research tables found in report/tables/")
        print("report: 0 tracked table files found")
        return

    if include_local:
        files += [p for p in [ROOT / "report/EC418_report.tex"] if p.is_file()]
        files += sorted((ROOT / "submission/report_src").glob("*.tex"))

    for path in files:
        lines = strip_tex(path.read_text(encoding="utf-8")).split("\n")
        for i, line in enumerate(lines, 1):
            for token in NUM.findall(line):
                if token not in WL:
                    rel = path.relative_to(ROOT)
                    bad.append(f"{rel}:{i}: typed number '{token}' in: {line.strip()[:110]}")

    n_table = len(list((ROOT / "report/tables").glob("*.tex")))
    print(f"report: checked {n_table} tracked table(s) and {len(files) - n_table} local source(s)")
    if not include_local:
        print("report: ignored local sources skipped (pass --include-local to check them)")


def check_slides(include_local=False):
    if not include_local:
        print("slides: local decks skipped (pass --include-local to check them)")
        return

    decks = [
        ROOT / "report/EC418_slides.pptx",
        ROOT / "submission/EC418_Assignment2_Presentation.pptx",
    ]
    available = [p for p in decks if p.is_file()]
    missing = [p for p in decks if not p.is_file()]
    if not available:
        print("slides: no optional local decks found; skipped")
        return

    from pptx import Presentation

    for path in available:
        presentation = Presentation(str(path))
        for i, slide in enumerate(presentation.slides, 1):
            texts = [
                paragraph.text
                for shape in slide.shapes if shape.has_text_frame
                for paragraph in shape.text_frame.paragraphs
            ]
            texts += [
                cell.text
                for shape in slide.shapes if shape.has_table
                for row in shape.table.rows for cell in row.cells
            ]
            if slide.has_notes_slide:
                texts.append(slide.notes_slide.notes_text_frame.text)
            for token in NUM.findall(" ".join(texts)):
                if token not in REG and token not in WL:
                    rel = path.relative_to(ROOT)
                    bad.append(f"{rel}: slide {i}: number '{token}' not in registry or whitelist")
        print(f"slides: checked {len(presentation.slides)} slides in {path.relative_to(ROOT)}")
    for path in missing:
        print(f"slides: optional local file absent: {path.relative_to(ROOT)}")


def main():
    args = set(sys.argv[1:])
    allowed = {"--report", "--slides", "--include-local"}
    extra = args - allowed
    if extra:
        raise SystemExit("Unknown option(s): " + ", ".join(sorted(extra)))
    if not args & {"--report", "--slides"}:
        args.update({"--report", "--slides"})

    include_local = "--include-local" in args
    if "--report" in args:
        check_report(include_local)
    if "--slides" in args:
        check_slides(include_local)
    if bad:
        print("\n".join(bad))
        print(f"FAIL: {len(bad)} problem(s)")
        raise SystemExit(1)
    print("number check passed")


if __name__ == "__main__":
    main()
