"""G4 analysis: H11a-c (pre-registered) on frozen folds, plus descriptive W_scat1."""
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap, threshold_metrics

P = pd.concat([pd.read_csv(f"results/predictions/{t}_predictions.csv") for t in ["main", "posthoc_smoothing", "p3_cv", "p3_cv_smo"]],
              ignore_index=True)
SETS = ["A_stft", "A_wpd_db4", "A_wpd_db4_smooth", "A_scat1", "A_scat12", "W_stft", "W_wpd_db4_smooth", "W_scat1"]


def avg(S, C):
    g = P[(P.set == S) & (P.clf == C)]
    return g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean()


rows = []
for C in ["RF", "SMO"]:
    for S in SETS:
        g = P[(P.set == S) & (P.clf == C)]
        if g.empty:
            continue
        per = g.groupby("repeat").apply(lambda h: roc_auc_score(h.y, h.score), include_groups=False)
        a = avg(S, C)
        lo, hi, _ = subject_bootstrap(a, lambda d: roc_auc_score(d.y, d.score), n_boot=2000, seed=1)
        sens = g.groupby("repeat").apply(lambda h: threshold_metrics(h.y.values, (h.score >= h.thr_spec80).astype(int).values, 0.5)["sensitivity"],
                                         include_groups=False).mean()
        rows.append(dict(set=S, clf=C, auroc_mean_of_repeats=per.mean(), sd=per.std(ddof=1),
                         auroc_repeat_avg_scores=roc_auc_score(a.y, a.score), ci_lo=lo, ci_hi=hi, sens_at_spec80op=sens))
M = pd.DataFrame(rows)
os.makedirs("results/tables/p3", exist_ok=True)
print(M.round(3).to_string(index=False))

out = []
for C in ["RF", "SMO"]:
    for h, a, b in [("H11a", "A_scat1", "A_stft"), ("H11b", "A_scat12", "A_stft"), ("H11c", "A_scat12", "A_scat1"),
                    ("desc", "A_scat1", "A_wpd_db4"), ("desc", "A_scat12", "A_wpd_db4_smooth"), ("desc", "W_scat1", "W_stft")]:
        A, B = avg(a, C), avg(b, C)
        if A.empty or B.empty:
            continue
        J = A.merge(B, on=["patient_id", "subject_id", "y"], suffixes=("_a", "_b"))
        d = roc_auc_score(J.y, J.score_a) - roc_auc_score(J.y, J.score_b)
        lo, hi, _ = subject_bootstrap(J, lambda x: roc_auc_score(x.y, x.score_a) - roc_auc_score(x.y, x.score_b), n_boot=2000, seed=2)
        fa = P[(P.set == a) & (P.clf == C)].groupby(["repeat", "fold"]).apply(lambda x: roc_auc_score(x.y, x.score), include_groups=False)
        fb = P[(P.set == b) & (P.clf == C)].groupby(["repeat", "fold"]).apply(lambda x: roc_auc_score(x.y, x.score), include_groups=False)
        pos = int(((fa - fb) > 0).sum())
        ok = d >= 0.03 and lo > 0 and pos >= 18
        out.append(dict(hypothesis=h, clf=C, a=a, b=b, delta=d, ci_lo=lo, ci_hi=hi, folds_positive=f"{pos}/{len(fa)}",
                        verdict=("SUPPORTED" if ok else "NOT SUPPORTED") if (C == "RF" and h != "desc") else "descriptive"))
O = pd.DataFrame(out)
print(O.round(4).to_string(index=False))
M.round(4).to_csv("results/tables/p3/g4_scattering_metrics.csv", index=False)
O.round(4).to_csv("results/tables/p3/g4_scattering_contrasts.csv", index=False)
