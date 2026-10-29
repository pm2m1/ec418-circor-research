"""Write-up: LaTeX tables for the report, built from the numbers registry only (report/numbers.json).

Every cell is a \\nm{key} call (resolved by report/numbers.tex), so no number is typed. Hypothesis labels and verdict words
come from the registry's text entries (final_hypotheses.csv).
Writes report/tables/{tab_main,tab_g3a,tab_external,tab_hypotheses}.tex.
usage: .venv/bin/python scripts/p4_report_tables.py
"""
import json
import os

import pandas as pd

N = json.load(open("report/numbers.json"))
OUT = "report/tables"
os.makedirs(OUT, exist_ok=True)


def nm(key):
    assert key in N, f"unknown registry key {key}"
    return f"\\nm{{{key}}}"


def tex(s):
    return str(s).replace("_", "\\_").replace("%", "\\%")


# ---- main models: AUROC and operating points (RF; Mac/Phase-2 platform)
rows = [("B0 acoustic baseline", "v1B0RFAucFull", "opReproMacB0RF"), ("B1 Vimalajeewa et al.", "v1B1RFAucFull", "opReproMacB1RF"),
        ("whole-signal STFT (W\\_stft)", "decWholeStftFull", "opReproMacWStftRF"),
        ("expert-aligned STFT (oracle)", "decExpertStftFull", "opE2E2StftTrueRF"),
        ("E4 automatic STFT", "decEFourStftFull", "opE4E4StftRF"), ("E4q shortcut-free STFT", "gTwoAucE4qStftFull", "opP3G2E4qStftRF")]
L = ["\\begin{tabular}{@{}lcccc@{}}", "\\toprule", "Model (RF) & AUROC [95\\,\\% CI] & Se & Sp & W.acc \\\\", "\\midrule"]
for lab, auc, op in rows:
    L.append(f"{lab} & {nm(auc)} & {nm(op + 'Sens')} & {nm(op + 'Spec')} & {nm(op + 'Wacc')} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
open(f"{OUT}/tab_main.tex", "w").write("\n".join(L) + "\n")

# ---- G3a conditioning gaps
L = ["\\begin{tabular}{@{}lccc@{}}", "\\toprule", "Gap (RF AUROC) & stft & wpd & wpds \\\\", "\\midrule"]
for lab, key in [("$\\Delta_{or}$ expert $-$ perm", "E2{r}Perm"), ("$\\Delta_{or}$ expert $-$ shift", "E2{r}Shift"),
                 ("$\\Delta_{oe}$ expert $-$ E1", "E1{r}Auto"), ("$\\Delta_{oe}$ expert $-$ E1b", "E1b{r}Auto"),
                 ("$\\Delta_{oe}$ expert $-$ E4", "E4{r}"), ("$\\Delta_{oe}$ expert $-$ E4q", "E4q{r}")]:
    L.append(lab + " & " + " & ".join(nm("gThreeA" + key.format(r=r) + "Full") for r in ["Stft", "Wpd", "Wpds"]) + " \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
open(f"{OUT}/tab_g3a.tex", "w").write("\n".join(L) + "\n")

# ---- external validation (clean and noisy ZCHSound; RF)
L = ["\\begin{tabular}{@{}lccc@{}}", "\\toprule", "Model (RF, trained on CirCor) & clean & noisy & CirCor internal \\\\", "\\midrule"]
for lab, b in [("W\\_stft (pre-registered, H10a)", "zchWStftRFAll"), ("W\\_wpd\\_db4\\_smooth", "zchWWpdDb4SmoothRFAll"),
               ("W\\_scat1", "zchWScat1RFAll"), ("B0 (artefact, no verdict)", "zchB0RFAll")]:
    L.append(f"{lab} & {nm(b + 'CleanFull')} & {nm(b + 'NoisyFull')} & {nm(b + 'CleanInternal')} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
open(f"{OUT}/tab_external.tex", "w").write("\n".join(L) + "\n")

# ---- every pre-registered hypothesis (appendix)
H = pd.read_csv("results/tables/final_hypotheses.csv")
keys = []
for _, r in H.iterrows():
    rep = next((x for x in ["wpds", "wpd", "stft"] if f"_{x}" in str(r.contrast)), "")
    tgt = "Wwpd" if "Wwpd" in str(r.contrast) else ("Wstft" if "Wstft" in str(r.contrast) else "")
    s = " ".join(map(str, ["hyp", r.hypothesis, rep, tgt if r.hypothesis.startswith("S1") else ""]))
    import re
    k = "".join(p[:1].upper() + p[1:] for p in re.sub(r"[^A-Za-z0-9 ]", " ", s).split())
    k = k[:1].lower() + k[1:]
    if k in keys:
        k = k + "Two"
    keys.append(k)
    delta = nm(k + "Full") if k + "Full" in N else "--"
    L2 = f"{tex(r.hypothesis)} & {tex(r.contrast)} & {delta} & {nm(k + 'Folds')} & {nm(k + 'Verdict')} \\\\"
    keys[-1] = (k, L2)
L = ["\\begin{tabular}{@{}llccl@{}}", "\\toprule", "Hyp. & Contrast (RF) & $\\Delta$ AUROC [95\\,\\% CI] & folds $>0$ & verdict \\\\",
     "\\midrule"] + [x[1] for x in keys]
G2 = [("H12a", "E4q $-$ (W\\_stft + SC$_q$)", "gTwoH12a"), ("H12b", "E4q $-$ rand-q", "gTwoH12b"), ("H12c (desc.)", "E4q $-$ snr-q", "gTwoH12c")]
for h, c, b in G2:
    for rep in ["Stft", "Wpd", "Wpds"]:
        L.append(f"{h} & {c}, {rep.lower()} & {nm(b + rep + 'Full')} & {nm(b + rep + 'Folds')} & {nm(b + rep + 'Verdict')} \\\\")
for h, c, b in [("H11a", "A\\_scat1 $-$ A\\_stft", "gFourH11aAScat1AStft"), ("H11b", "A\\_scat12 $-$ A\\_stft", "gFourH11bAScat12AStft"),
                ("H11c", "A\\_scat12 $-$ A\\_scat1", "gFourH11cAScat12AScat1")]:
    L.append(f"{h} & {c} & {nm(b + 'Full')} & {nm(b + 'Folds')} & {nm(b + 'Verdict')} \\\\")
L.append(f"H10a & ZCHSound clean any-CHD AUROC, W\\_stft & {nm('hTenAFull')} & n/a & {nm('h10aVerdict')} \\\\")
L.append(f"H10b & AUROC(VSD) $-$ AUROC(PFO) & {nm('hTenBvsdPfoFull')} & n/a & {nm('h10bVerdict')} \\\\")
L.append(f"H10b & AUROC(VSD) $-$ AUROC(ASD) & {nm('hTenBvsdAsdFull')} & n/a & {nm('h10bVerdict')} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
open(f"{OUT}/tab_hypotheses.tex", "w").write("\n".join(L) + "\n")
print("tables ->", sorted(os.listdir(OUT)))
