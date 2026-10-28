"""Write-up numbers registry: every number used in the report and slides, read ONLY from saved tables.

Inputs: results/tables/{final_hypotheses,final_decomposition,main_metrics,s1_contrasts,s1_auroc}.csv,
results/tables/p3/*.csv + g1a_verdicts.json, results/tables/p4/*.csv (G3b once it exists), and the sourced literature
numbers in references/g3b/case_study_numbers.csv (value + page/quote for each).
Rounding: one rule everywhere, Decimal(str(value)) rounded half-up (AUROC and deltas to 3 decimals, shares as percent with 1).
Writes report/numbers.json ({key: {value, raw, source}}) and report/numbers.tex (one \\newcommand per key; the macro name is
the key in CamelCase with digits spelled out, e.g. aucExternal -> \\NaucExternal).
usage: .venv/bin/python scripts/p4_numbers.py
"""
import json
import os
import re
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

T, P3, P4 = "results/tables", "results/tables/p3", "results/tables/p4"
N = {}
DIG = dict(zip("0123456789", ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]))


def fmt(v, d=3, signed=False, pct=False):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "--"
    x = Decimal(str(v)) * (100 if pct else 1)
    q = x.quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    if q == 0:
        q = abs(q)
    s = f"{q:f}"
    if signed and q > 0:
        s = "+" + s
    return s.replace("-", "−")


def put(key, v, src, **kw):
    assert key not in N, f"duplicate key {key}"
    N[key] = dict(value=fmt(v, **kw) if not isinstance(v, str) else v, raw=None if isinstance(v, str) else float(v), source=src)


def put_ci(key, est, lo, hi, src, signed=False):
    put(key, est, src, signed=signed)
    put(key + "Lo", lo, src, signed=signed)
    put(key + "Hi", hi, src, signed=signed)
    N[key + "Ci"] = dict(value=f"[{fmt(lo, signed=signed)}, {fmt(hi, signed=signed)}]", raw=None, source=src)
    N[key + "Full"] = dict(value=f"{fmt(est, signed=signed)} [{fmt(lo, signed=signed)}, {fmt(hi, signed=signed)}]", raw=None, source=src)


def k(*parts):
    s = "".join(p[:1].upper() + p[1:] for p in re.sub(r"[^A-Za-z0-9 ]", " ", " ".join(map(str, parts))).split())
    return s[:1].lower() + s[1:]


# ---- Phase 1 baselines and aligned sets (frozen v1, RF and SMO)
mm = pd.read_csv(f"{T}/main_metrics.csv")
for _, r in mm[mm.clf.isin(["RF", "SMO"])].iterrows():
    b = k("v1", r.set, r.clf)
    put_ci(b + "Auc", r.auroc_avgscore, r.auroc_ci_lo, r.auroc_ci_hi, "main_metrics.csv")
    put(b + "AucMor", r.auroc, "main_metrics.csv")
    put(b + "SensSpecEighty", r.spec80op_sensitivity, "main_metrics.csv")
    put(b + "Wacc", r.waccop_weighted_accuracy, "main_metrics.csv")

# ---- every pre-registered hypothesis (RF)
H = pd.read_csv(f"{T}/final_hypotheses.csv")
for _, r in H.iterrows():
    rep = next((x for x in ["wpds", "wpd", "stft"] if f"_{x}" in str(r.contrast)), "")
    tgt = "Wwpd" if "Wwpd" in str(r.contrast) else ("Wstft" if "Wstft" in str(r.contrast) else "")
    b = k("hyp", r.hypothesis, rep, tgt if r.hypothesis.startswith("S1") else "")
    if b in N:
        b = k(b, "two")
    if pd.notna(r.delta):
        put_ci(b, r.delta, r.ci_lo, r.ci_hi, "final_hypotheses.csv", signed=True)
    put(b + "Folds", str(r.folds_positive), "final_hypotheses.csv")
    put(b + "Verdict", str(r.verdict), "final_hypotheses.csv")

# ---- decomposition (RF, repeat-averaged AUROC)
D = pd.read_csv(f"{T}/final_decomposition.csv")
names = ["expert", "eFour", "dOne", "eOneb", "dTwo", "perm", "dThree", "whole"]
for nm, (_, r) in zip(names, D.iterrows()):
    for rep in ["stft", "wpd", "wpds"]:
        lo, hi = [float(x) for x in r[f"{rep}_ci"].strip("[]").split(",")]
        put_ci(k("dec", nm, rep), r[rep], lo, hi, "final_decomposition.csv")

# ---- S1
S1c = pd.read_csv(f"{T}/s1_contrasts.csv")
for _, r in S1c[S1c.clf == "RF"].iterrows():
    b = k("sOne", r.part.strip("()"), r.a, r.b)
    put_ci(b, r.delta_auroc_repeat_averaged, r.ci_lo, r.ci_hi, "s1_contrasts.csv", signed=True)
    put(b + "Folds", r.folds_positive, "s1_contrasts.csv")
S1a = pd.read_csv(f"{T}/s1_auroc.csv")
for _, r in S1a[S1a.clf == "RF"].iterrows():
    put_ci(k("sOneAuc", r.set), r.auroc_repeat_averaged, r.auroc_repeat_averaged_ci_lo, r.auroc_repeat_averaged_ci_hi, "s1_auroc.csv")

# ---- G2
G = pd.read_csv(f"{P3}/g2_auroc.csv")
for _, r in G[G.clf == "RF"].iterrows():
    put_ci(k("gTwoAuc", r.set), r.auroc_repeat_averaged, r.ci_lo, r.ci_hi, "p3/g2_auroc.csv")
GC = pd.read_csv(f"{P3}/g2_contrasts.csv")
for _, r in GC[GC.clf == "RF"].iterrows():
    b = k("gTwo", r.hypothesis, r.rep, r.b if r.hypothesis == "desc" else "")
    put_ci(b, r.delta, r.ci_lo, r.ci_hi, "p3/g2_contrasts.csv", signed=True)
    put(b + "Folds", r.folds_positive, "p3/g2_contrasts.csv")
for _, r in pd.read_csv(f"{P3}/g2_coverage.csv").iterrows():
    put(k("gTwoNofeat", r.selection, r.murmur), r.nofeat_frac, "p3/g2_coverage.csv", d=1, pct=True)

# ---- G4
for _, r in pd.read_csv(f"{P3}/g4_scattering_metrics.csv").query("clf == 'RF'").iterrows():
    put_ci(k("gFourAuc", r.set), r.auroc_repeat_avg_scores, r.ci_lo, r.ci_hi, "p3/g4_scattering_metrics.csv")
    put(k("gFourAucMor", r.set), r.auroc_mean_of_repeats, "p3/g4_scattering_metrics.csv")
for _, r in pd.read_csv(f"{P3}/g4_scattering_contrasts.csv").query("clf == 'RF'").iterrows():
    b = k("gFour", r.hypothesis, r.a, r.b)
    put_ci(b, r.delta, r.ci_lo, r.ci_hi, "p3/g4_scattering_contrasts.csv", signed=True)
    put(b + "Folds", r.folds_positive, "p3/g4_scattering_contrasts.csv")

# ---- G1a (external, ZCHSound)
X = pd.read_csv(f"{P3}/g1a_external_any_chd.csv")
for _, r in X.iterrows():
    b = k("zch", r.set, r.clf, r.variant, r.subset)
    put_ci(b, r.auroc_any_chd, r.ci_lo, r.ci_hi, "p3/g1a_external_any_chd.csv")
    if pd.notna(r.circor_internal_auroc):
        put(b + "Internal", r.circor_internal_auroc, "p3/g1a_external_any_chd.csv")
    if pd.notna(r.sens_any_chd):
        put(b + "Sens", r.sens_any_chd, "p3/g1a_external_any_chd.csv")
        put(b + "Spec", r.spec, "p3/g1a_external_any_chd.csv")
XS = pd.read_csv(f"{P3}/g1a_external_by_subtype.csv")
for _, r in XS[(XS.variant == "all") & (XS.subset == "clean")].iterrows():
    put_ci(k("zchSub", r.set, r.clf, r.diagnosis), r.auroc_vs_normal, r.ci_lo, r.ci_hi, "p3/g1a_external_by_subtype.csv")
v = json.load(open(f"{P3}/g1a_verdicts.json"))
put_ci("hTenA", v["H10a"]["auroc"], v["H10a"]["ci"][0], v["H10a"]["ci"][1], "p3/g1a_verdicts.json")
for nm, d, c in [("hTenBvsdPfo", "VSD_minus_PFO", "ci1"), ("hTenBvsdAsd", "VSD_minus_ASD", "ci2")]:
    lo, hi = [float(x) for x in v["H10b"][c].strip("[]").split(",")]
    put_ci(nm, v["H10b"][d], lo, hi, "p3/g1a_verdicts.json", signed=True)
for h in ["H10a", "H10b"]:
    put(k(h, "verdict"), v[h]["verdict"], "p3/g1a_verdicts.json")
AG = pd.read_csv(f"{P3}/g1a_posthoc_age_check.csv")
for _, r in AG.iterrows():
    b = k("age", r.model)
    put(b + "Auc", r.auroc_all, "p3/g1a_posthoc_age_check.csv")
    for c, nm in [("spearman_score_age", "Rho"), ("auroc_age_tertile0", "TZero"), ("auroc_age_tertile1", "TOne"), ("auroc_age_tertile2", "TTwo")]:
        if pd.notna(r[c]):
            put(b + nm, r[c], "p3/g1a_posthoc_age_check.csv", signed=(nm == "Rho"))

# ---- G3a
for _, r in pd.read_csv(f"{P3}/g3a_conditioning_gaps.csv").query("clf == 'RF'").iterrows():
    put_ci(k("gThreeA", r.other), r.delta, r.ci_lo, r.ci_hi, "p3/g3a_conditioning_gaps.csv")

# ---- operating points (p4)
for _, r in pd.read_csv(f"{P4}/operating_points.csv").iterrows():
    b = k("op", r.tag, r.set, r.clf)
    for c, nm in [("spec80op_sensitivity", "Sens"), ("spec80op_specificity", "Spec"), ("spec80op_balanced_accuracy", "Bacc"),
                  ("spec80op_weighted_accuracy", "Wacc"), ("waccop_weighted_accuracy", "WaccOpt")]:
        put(b + nm, r[c], "p4/operating_points.csv")

# ---- G3b literature audit (after the coders' sheets are complete)
for f in ["g3b_summary.csv", "g3b_kappa.csv"]:
    if os.path.exists(f"{P4}/{f}"):
        for _, r in pd.read_csv(f"{P4}/{f}").iterrows():
            for c in [c for c in r.index if c != "key" and pd.notna(r[c]) and isinstance(r[c], (int, float))]:
                put(k("gThreeB", r.key, c), r[c], f"p4/{f}")

# ---- literature numbers quoted in the case study (sourced: page + quote in the CSV)
for _, r in pd.read_csv("references/g3b/case_study_numbers.csv").iterrows():
    put(k("lit", r.key), r.value, "references/g3b/case_study_numbers.csv",
        d=2 if "nie" in r.key else 3, pct=("nie" in r.key))

os.makedirs("report", exist_ok=True)
json.dump(N, open("report/numbers.json", "w"), indent=1, ensure_ascii=False)


def macro(key):
    return "N" + "".join(DIG.get(c, c) for c in key[:1].upper() + key[1:])


seen = {}
with open("report/numbers.tex", "w") as f:
    f.write("% generated by scripts/p4_numbers.py from saved tables; do not edit\n")
    for key, d in N.items():
        m = macro(key)
        assert m not in seen and re.fullmatch(r"N[A-Za-z]+", m), (key, m)
        seen[m] = key
        val = d["value"].replace("−", "$-$").replace("%", "\\%").replace("[", "{[}").replace("]", "{]}")
        f.write(f"\\newcommand{{\\{m}}}{{{val}}}\n")
print(f"registry: {len(N)} entries -> report/numbers.json, report/numbers.tex")
