"""Diagnostics D1-D3 analysis (docs/PROTOCOL_V2_LOCKED.md "Diagnostics D1–D3"). DIAGNOSTICS ONLY, descriptive,
no pass/fail thresholds.

Sets: D1_/D2_/D3_<rep> and W_wpd_db4_smooth (tag diag); E2_<rep>_true / _perm (tag e2); E1b_<rep>_auto (tag e1b);
W_stft, W_wpd_db4 (tag e1). AUROC: repeat-averaged with subject-bootstrap CI (2000, seed 1) and mean of repeats.
Paired contrasts on repeat-averaged scores (subject bootstrap 2000, seed 2; folds with delta > 0):
  (1) true - D1   (2) true - D2   (3) D3 - full-recording whole-signal   (4) D1 - HSMM-full   (+) D2 - perm
and the totals of the two exact decompositions: true - perm = (true - D2) + (D2 - perm),
true - HSMM-full = (true - D1) + (D1 - HSMM-full).
usage: python scripts/25_diag_analyze.py
Writes results/tables/diag_{auroc,contrasts,d1_coverage}.csv, results/logs/diag_analysis.json.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap

N_BOOT = 2000
REPS = ["stft", "wpd", "wpds"]
W_FULL = {"stft": "W_stft", "wpd": "W_wpd_db4", "wpds": "W_wpd_db4_smooth"}
diag = pd.read_csv("results/predictions/diag_predictions.csv")
e2 = pd.read_csv("results/predictions/e2_predictions.csv")
e1b = pd.read_csv("results/predictions/e1b_predictions.csv")
e1 = pd.read_csv("results/predictions/e1_predictions.csv")
pred = pd.concat([diag, e2[e2.set.str.endswith(("_true", "_perm"))], e1b, e1[e1.set.isin(["W_stft", "W_wpd_db4"])]],
                 ignore_index=True)


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
    rows.append(dict(set=S, clf=C, n_patients=len(a), auroc_mean_of_repeats=np.mean(rep),
                     auroc_mean_of_repeats_sd=np.std(rep, ddof=1), auroc_repeat_averaged=auc(a),
                     auroc_repeat_averaged_ci_lo=lo, auroc_repeat_averaged_ci_hi=hi))
A = pd.DataFrame(rows).sort_values(["clf", "set"])
A.to_csv("results/tables/diag_auroc.csv", index=False)

spec = []
for rep in REPS:
    t = f"E2_{rep}_true"
    spec += [("(1) true - D1", rep, t, f"D1_{rep}"), ("(2) true - D2", rep, t, f"D2_{rep}"),
             ("(3) D3 - full-recording W", rep, f"D3_{rep}", W_FULL[rep]), ("(4) D1 - HSMM-full", rep, f"D1_{rep}", f"E1b_{rep}_auto"),
             ("(+) D2 - perm", rep, f"D2_{rep}", f"E2_{rep}_perm"),
             ("total: true - perm", rep, t, f"E2_{rep}_perm"), ("total: true - HSMM-full", rep, t, f"E1b_{rep}_auto")]
CT = pd.DataFrame([dict(contrast=c, clf=C, representation=rep, a=a, b=b, **contrast(a, b, C))
                   for C in ["RF", "SMO"] for c, rep, a, b in spec])
CT.to_csv("results/tables/diag_contrasts.csv", index=False)

cov = []
for d in sorted(os.listdir("data/interim/diag/features")):
    r, k = (int(x[1:]) for x in d.split("_"))
    rec = pd.read_csv(f"data/interim/diag/features/{d}/rec_features_D1_wpd.csv")
    none = rec[[c for c in rec.columns if c.startswith("wpdA")]].isna().all(axis=1)
    pat = rec.assign(n=none).groupby(["patient_id", "murmur"]).n.all().reset_index()
    cov.append(dict(repeat=r, fold=k, recordings=len(rec), recordings_without_aligned=int(none.sum()),
                    present_recordings_without=int((none & (rec.murmur == "Present")).sum()),
                    absent_recordings_without=int((none & (rec.murmur == "Absent")).sum()),
                    patients_without_any=int(pat.n.sum()), present_patients_without_any=int(pat[pat.murmur == "Present"].n.sum()),
                    absent_patients_without_any=int(pat[pat.murmur == "Absent"].n.sum())))
CV = pd.DataFrame(cov)
CV.to_csv("results/tables/diag_d1_coverage.csv", index=False)

json.dump(dict(note="diagnostics only (expert annotation used at test time); descriptive, no thresholds",
               rf=CT[CT.clf == "RF"][["contrast", "representation", "delta_auroc_repeat_averaged", "ci_lo", "ci_hi"]].to_dict("records"),
               d1_coverage=CV.drop(columns=["repeat", "fold"]).agg(["min", "max", "mean"]).to_dict()),
          open("results/logs/diag_analysis.json", "w"), indent=2, default=float)
pd.set_option("display.width", 250)
for name, df in [("AUROC", A), ("CONTRASTS", CT), ("D1 COVERAGE", CV.drop(columns=["repeat", "fold"]).agg(["min", "max", "mean"]))]:
    print(f"\n== {name} ==\n" + df.round(4).to_string())
