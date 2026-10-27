"""Collect every pre-registered hypothesis (H1-H9, equivalence, S1) and the decomposition from SAVED tables only.

Writes results/tables/final_hypotheses.csv, results/tables/final_decomposition.csv and prints both as markdown
(used verbatim in docs/RESULTS_SUMMARY.md). RF rows only (RF is the primary classifier for every rule).
usage: python scripts/32_results_summary.py
"""
import json

import pandas as pd

rows = []


def add(exp, hyp, contrast, rule, d, lo, hi, folds, verdict, source):
    rows.append(dict(experiment=exp, hypothesis=hyp, contrast=contrast, rule=rule, delta=d, ci_lo=lo, ci_hi=hi,
                     folds_positive=folds, verdict=verdict, source=source))


h1 = json.load(open("results/tables/h1_summary.json"))
add("v1", "H1", "B1+SVM recording AUC: random split - subject-grouped", "material inflation (v1 PILOT_RESULTS §1)",
    h1["delta"], h1["delta_ci95"][0], h1["delta_ci95"][1], "n/a", "NOT SUPPORTED", "results/tables/h1_summary.json")
v1 = pd.read_csv("results/tables/contrasts.csv")
for _, r in v1[(v1.clf == "RF") & (v1.hypothesis != "aux")].iterrows():
    add("v1", r.hypothesis, f"{r.a} - {r.b}", "delta>=0.03, CI lo>0, >=18/25", r.delta_auroc, r.ci_lo, r.ci_hi, r.folds_positive,
        r.verdict, "results/tables/contrasts.csv")
for tag, f in [("E2", "e2_contrasts"), ("E1", "e1_hypotheses"), ("E1b", "e1b_hypotheses"), ("E4", "e4_hypotheses")]:
    t = pd.read_csv(f"results/tables/{f}.csv")
    t = t[t.clf == "RF"]
    for _, r in t.iterrows():
        rule = r.get("rule", "delta>=0.03, CI lo>0, >=18/25") if isinstance(r.get("rule", None), str) else "delta>=0.03, CI lo>0, >=18/25"
        add(tag, r.hypothesis, f"{r.a} - {r.b}", rule, r.delta_auroc_repeat_averaged, r.ci_lo, r.ci_hi, r.folds_positive, r.verdict,
            f"results/tables/{f}.csv")
eq = pd.read_csv("results/tables/e2_equivalence.csv")
r = eq[eq.clf == "RF"].iloc[0]
add("E2", "equivalence", "E2_wpds_true - E2_stft_true", "CI within +/-0.03", r.delta_auroc_repeat_averaged, r.ci_lo, r.ci_hi,
    r.folds_positive, "equivalence NOT shown", "results/tables/e2_equivalence.csv")
add("E3", "H7", "soft murmurs (grade I/VI sensitivity)", "-", float("nan"), float("nan"), float("nan"), "-",
    "NOT RUN (dropped, amendment E3-drop)", "docs/PROTOCOL_V2_LOCKED.md")
s1 = pd.read_csv("results/tables/s1_contrasts.csv")
for _, r in s1[(s1.clf == "RF") & (s1.part == "(a)")].iterrows():
    add("S1 (diagnostic)", "S1(a)", f"{r.a} - {r.b}", "CI lo>0 -> not shortcut-explained", r.delta_auroc_repeat_averaged, r.ci_lo,
        r.ci_hi, r.folds_positive, r.label, "results/tables/s1_contrasts.csv")
H = pd.DataFrame(rows)
H.to_csv("results/tables/final_hypotheses.csv", index=False)

A = pd.read_csv("results/tables/diag_auroc.csv")
E = pd.read_csv("results/tables/e4_auroc.csv")
A = pd.concat([A, E[E.set.str.startswith("E4_")]], ignore_index=True)
A = A[A.clf == "RF"].set_index("set")
W = {"stft": "W_stft", "wpd": "W_wpd_db4", "wpds": "W_wpd_db4_smooth"}
levels = [("expert labels (E2 true)", "E2_{r}_true"), ("E4 automatic spans + HSMM", "E4_{r}"), ("D1 HSMM in expert spans*", "D1_{r}"),
          ("E1b HSMM, whole recording", "E1b_{r}_auto"), ("D2 timing destroyed in spans*", "D2_{r}"),
          ("E2 perm, timing destroyed (whole rec.)", "E2_{r}_perm"), ("D3 whole-signal features in spans*", "D3_{r}"),
          ("whole-signal features, full recording", None)]
D = pd.DataFrame([dict(level=lab, **{rep: A.loc[W[rep] if p is None else p.format(r=rep)].auroc_repeat_averaged for rep in W},
                       **{f"{rep}_ci": "[{:.3f}, {:.3f}]".format(*A.loc[W[rep] if p is None else p.format(r=rep)][
                           ["auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi"]]) for rep in W}) for lab, p in levels])
D.to_csv("results/tables/final_decomposition.csv", index=False)


def f(x):
    return "" if pd.isna(x) else f"{x:+.3f}"


print("| Experiment | Hypothesis | Contrast (RF) | Rule | Δ AUROC [95 % CI] | Folds Δ > 0 | Verdict |")
print("|---|---|---|---|---|---|---|")
for _, r in H.iterrows():
    eff = "—" if pd.isna(r.delta) else f"{f(r.delta)} [{f(r.ci_lo)}, {f(r.ci_hi)}]"
    print(f"| {r.experiment} | {r.hypothesis} | {r.contrast.replace('_', chr(92) + '_')} | {r.rule} | {eff} | {r.folds_positive} | {r.verdict} |")
print()
print("| Labels / features (RF, repeat-averaged AUROC [95 % CI]) | stft | wpd | wpds |")
print("|---|---|---|---|")
for _, r in D.iterrows():
    print(f"| {r.level} | {r.stft:.3f} {r.stft_ci} | {r.wpd:.3f} {r.wpd_ci} | {r.wpds:.3f} {r.wpds_ci} |")
