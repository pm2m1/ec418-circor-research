"""Phase-3 G2 analysis (sandbox PROTOCOL_V3_PREREG "G2" + A1). RF decides, SMO descriptive.

Gate 2: E4R_<rep> predictions must equal results/predictions/e4_predictions.csv (E4_<rep>) -> else stop.
H12a  E4q_<rep> - G2_Wstft_SCq : CI lower > 0 (S1 rule) -> "not explained by the shortcut"; primary rep = stft
H12b  E4q_<rep> - RQ_<rep>     : CI lower > 0 -> "learned selection matters"
H12c  E4q_<rep> - SNRQ_<rep>   : descriptive
Repeat-averaged AUROC, subject bootstrap 2000 (seed 1 AUROC, seed 2 contrasts), folds with delta > 0, mean of repeats.
Coverage: share of TEST recordings without aligned features, by murmur class, per selection.
usage: python scripts/p3_g2_analyze.py -> results/tables/p3/g2_{gate,auroc,contrasts,coverage}.csv, results/logs/p3_g2_analysis.json
"""
import glob
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap

N_BOOT = 2000
os.makedirs("results/tables/p3", exist_ok=True)
g2 = pd.read_csv("results/predictions/p3_g2_predictions.csv")
e4 = pd.read_csv("results/predictions/e4_predictions.csv")
s1 = pd.read_csv("results/predictions/s1_predictions.csv")
e1 = pd.read_csv("results/predictions/e1_predictions.csv")

# ---- gate 2: exact reproduction of E4
K = ["patient_id", "clf", "repeat", "fold", "rep"]
a = g2[g2.set.str.startswith("E4R_")].assign(rep=lambda d: d.set.str[4:])
b = e4.assign(rep=lambda d: d.set.str[3:])
J = a.merge(b, on=K, suffixes=("_g2", "_e4"))
gate = dict(rows_e4=len(b), rows_e4r=len(a), matched=len(J),
            max_abs_score_diff=float((J.score_g2 - J.score_e4).abs().max()),
            max_abs_thr_diff=float((J.thr_spec80_g2 - J.thr_spec80_e4).abs().max()))
gate["pass"] = bool(gate["matched"] == gate["rows_e4"] == gate["rows_e4r"] and gate["max_abs_score_diff"] < 1e-9
                    and gate["max_abs_thr_diff"] < 1e-9)
pd.DataFrame([gate]).to_csv("results/tables/p3/g2_gate.csv", index=False)
print("GATE 2 (E4R == E4):", gate)
if not gate["pass"]:
    raise SystemExit("reproduction gate failed: no G2 result is reported (amendment A1.2)")

pred = pd.concat([g2[~g2.set.str.startswith("E4R_")], e4, s1[s1.set == "S1_Wstft_SC"], e1[e1.set == "W_stft"]], ignore_index=True)
avg = {k: g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean() for k, g in pred.groupby(["set", "clf"])}


def auc(df):
    return roc_auc_score(df.y, df.score)


def sel(S, C):
    return pred[(pred.set == S) & (pred.clf == C)]


def mor(S, C):
    return np.mean([auc(h) for _, h in sel(S, C).groupby("repeat")])


def contrast(x, y, C):
    J = avg[(x, C)].merge(avg[(y, C)], on=["patient_id", "subject_id", "y"], suffixes=("_a", "_b"))
    d = roc_auc_score(J.y, J.score_a) - roc_auc_score(J.y, J.score_b)
    lo, hi, _ = subject_bootstrap(J, lambda df: roc_auc_score(df.y, df.score_a) - roc_auc_score(df.y, df.score_b),
                                  n_boot=N_BOOT, seed=2)
    fa = sel(x, C).groupby(["repeat", "fold"]).apply(auc, include_groups=False)
    fb = sel(y, C).groupby(["repeat", "fold"]).apply(auc, include_groups=False)
    return dict(delta=d, ci_lo=lo, ci_hi=hi, folds_positive=f"{int(((fa - fb) > 0).sum())}/{len(fa)}",
                delta_mean_of_repeats=mor(x, C) - mor(y, C))


rows = []
for (S, C), d in avg.items():
    lo, hi, _ = subject_bootstrap(d, auc, n_boot=N_BOOT, seed=1)
    rep = [auc(h) for _, h in sel(S, C).groupby("repeat")]
    rows.append(dict(set=S, clf=C, n_patients=len(d), auroc_mean_of_repeats=np.mean(rep), sd=np.std(rep, ddof=1),
                     auroc_repeat_averaged=auc(d), ci_lo=lo, ci_hi=hi))
A = pd.DataFrame(rows).sort_values(["clf", "set"])
A.to_csv("results/tables/p3/g2_auroc.csv", index=False)

ct = []
for C in ["RF", "SMO"]:
    for rep in ["stft", "wpd", "wpds"]:
        for h, x, y, yes, no in [("H12a", f"E4q_{rep}", "G2_Wstft_SCq", "not explained by the shortcut", "possibly shortcut-driven"),
                                 ("H12b", f"E4q_{rep}", f"RQ_{rep}", "learned selection matters", "not shown"),
                                 ("H12c", f"E4q_{rep}", f"SNRQ_{rep}", None, None),
                                 ("desc", f"E4q_{rep}", f"E4_{rep}", None, None),
                                 ("desc", f"E4q_{rep}", "S1_Wstft_SC", None, None),
                                 ("desc", f"RQ_{rep}", "G2_Wstft_SCq", None, None)]:
            r = contrast(x, y, C)
            lab = "descriptive" if yes is None or C != "RF" else (yes if r["ci_lo"] > 0 else no)
            ct.append(dict(hypothesis=h, clf=C, rep=rep, a=x, b=y, **r, delta_ge_0_03=bool(r["delta"] >= 0.03),
                           primary=bool(h == "H12a" and rep == "stft" and C == "RF"), label=lab))
    r = contrast("G2_Wstft_SCq", "W_stft", C)
    ct.append(dict(hypothesis="desc", clf=C, rep="-", a="G2_Wstft_SCq", b="W_stft", **r, delta_ge_0_03=bool(r["delta"] >= 0.03),
                   primary=False, label="descriptive"))
CT = pd.DataFrame(ct)
CT.to_csv("results/tables/p3/g2_contrasts.csv", index=False)

# ---- coverage on test recordings (outer-fold test patients), by class
ft = pd.read_csv("configs/folds_patient_level.csv")
cov = []
for d in sorted(glob.glob("data/interim/g2/features/r*_f*")):
    r, k = (int(x[1:]) for x in os.path.basename(d).split("_"))
    test = set(ft[(ft.repeat == r) & (ft.outer_fold == k) & (ft.role == "test")].patient_id)
    for s in ["E4R", "E4q", "RQ", "SNRQ"]:
        f = pd.read_csv(f"{d}/rec_features_{s}_wpd.csv")
        f = f[f.patient_id.isin(test)]
        f["nofeat"] = f[[c for c in f.columns if c.startswith("wpdA_")]].isna().all(axis=1)
        for m, g in f.groupby("murmur"):
            cov.append(dict(repeat=r, fold=k, selection=s, murmur=m, n=len(g), nofeat=int(g.nofeat.sum())))
C = pd.DataFrame(cov).groupby(["selection", "murmur"], as_index=False)[["n", "nofeat"]].sum()
C["nofeat_frac"] = C.nofeat / C.n
C.to_csv("results/tables/p3/g2_coverage.csv", index=False)
prim = CT[CT.primary].iloc[0]
json.dump(dict(gate=gate, H12a_primary=dict(delta=prim.delta, ci=[prim.ci_lo, prim.ci_hi], folds=prim.folds_positive, label=prim.label),
               rf_labels=CT[(CT.clf == "RF") & CT.hypothesis.isin(["H12a", "H12b"])][["hypothesis", "rep", "delta", "ci_lo", "ci_hi", "folds_positive", "label"]].to_dict("records")),
          open("results/logs/p3_g2_analysis.json", "w"), indent=2, default=float)
pd.set_option("display.width", 250)
print(A.round(4).to_string(index=False)); print(CT.round(4).to_string(index=False)); print(C.round(4).to_string(index=False))
