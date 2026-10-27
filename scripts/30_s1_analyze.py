"""S1 shortcut-control analysis (docs/PROTOCOL_V2_LOCKED.md "S1", tag s1-prereg). Diagnostic.

Sets: S1_Wstft_SC, S1_Wwpd_SC, S1_SC_only (tag s1); E4_<rep> (tag e4); W_stft, W_wpd_db4 (tag e1). RF decides labels,
SMO descriptive. Repeat-averaged AUROC with subject-bootstrap CI (2000; seed 1 for AUROC, seed 2 for contrasts), folds
with delta > 0, both summaries.
  (a) E4_<rep> - S1_Wstft_SC, E4_<rep> - S1_Wwpd_SC   -> "not explained by the span/missingness shortcut" iff CI lower > 0,
                                                         else "possibly shortcut-driven"
  (b) S1_Wstft_SC - W_stft, S1_Wwpd_SC - W_wpd_db4     (c) S1_SC_only AUROC
usage: python scripts/30_s1_analyze.py   -> results/tables/s1_{auroc,contrasts}.csv, results/logs/s1_analysis.json
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap

N_BOOT = 2000
s1 = pd.read_csv("results/predictions/s1_predictions.csv")
e4 = pd.read_csv("results/predictions/e4_predictions.csv")
e1 = pd.read_csv("results/predictions/e1_predictions.csv")
pred = pd.concat([s1, e4, e1[e1.set.isin(["W_stft", "W_wpd_db4"])]], ignore_index=True)


def averaged(g):
    return g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean()


def auc(df):
    return roc_auc_score(df.y, df.score)


def sel(S, C):
    return pred[(pred.set == S) & (pred.clf == C)]


avg = {k: averaged(g) for k, g in pred.groupby(["set", "clf"])}


def mor(S, C):
    return np.mean([auc(h) for _, h in sel(S, C).groupby("repeat")])


def contrast(a, b, C):
    J = avg[(a, C)].merge(avg[(b, C)], on=["patient_id", "subject_id", "y"], suffixes=("_a", "_b"))
    d = roc_auc_score(J.y, J.score_a) - roc_auc_score(J.y, J.score_b)
    lo, hi, _ = subject_bootstrap(J, lambda df: roc_auc_score(df.y, df.score_a) - roc_auc_score(df.y, df.score_b),
                                  n_boot=N_BOOT, seed=2)
    fa = sel(a, C).groupby(["repeat", "fold"]).apply(lambda x: auc(x), include_groups=False)
    fb = sel(b, C).groupby(["repeat", "fold"]).apply(lambda x: auc(x), include_groups=False)
    return dict(delta_auroc_repeat_averaged=d, ci_lo=lo, ci_hi=hi, folds_positive=f"{int(((fa - fb) > 0).sum())}/{len(fa)}",
                delta_auroc_mean_of_repeats=mor(a, C) - mor(b, C))


rows = []
for (S, C), a in avg.items():
    lo, hi, _ = subject_bootstrap(a, auc, n_boot=N_BOOT, seed=1)
    rep = [auc(h) for _, h in sel(S, C).groupby("repeat")]
    rows.append(dict(set=S, clf=C, n_patients=len(a), auroc_mean_of_repeats=np.mean(rep), auroc_mean_of_repeats_sd=np.std(rep, ddof=1),
                     auroc_repeat_averaged=auc(a), auroc_repeat_averaged_ci_lo=lo, auroc_repeat_averaged_ci_hi=hi))
A = pd.DataFrame(rows).sort_values(["clf", "set"])
A.to_csv("results/tables/s1_auroc.csv", index=False)

ct = []
for C in ["RF", "SMO"]:
    for rep in ["stft", "wpd", "wpds"]:
        for b in ["S1_Wstft_SC", "S1_Wwpd_SC"]:
            r = contrast(f"E4_{rep}", b, C)
            lab = "not explained by the span/missingness shortcut" if r["ci_lo"] > 0 else "possibly shortcut-driven"
            ct.append(dict(part="(a)", clf=C, a=f"E4_{rep}", b=b, **r, label=lab if C == "RF" else f"descriptive ({lab})"))
    for a, b in [("S1_Wstft_SC", "W_stft"), ("S1_Wwpd_SC", "W_wpd_db4")]:
        ct.append(dict(part="(b)", clf=C, a=a, b=b, **contrast(a, b, C), label="descriptive"))
CT = pd.DataFrame(ct)
CT.to_csv("results/tables/s1_contrasts.csv", index=False)
json.dump(dict(rf_labels=CT[(CT.clf == "RF") & (CT.part == "(a)")][["a", "b", "delta_auroc_repeat_averaged", "ci_lo", "ci_hi", "label"]].to_dict("records"),
               sc_only=A[A.set == "S1_SC_only"][["clf", "auroc_repeat_averaged", "auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi"]].to_dict("records")),
          open("results/logs/s1_analysis.json", "w"), indent=2, default=float)
pd.set_option("display.width", 250)
print(A.round(4).to_string(index=False)); print(CT.round(4).to_string(index=False))
