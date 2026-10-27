"""Phase-2 E2 analysis under the locked rule (docs/PROTOCOL_V2_LOCKED.md).

Contrast statistics are computed exactly as in scripts/07_analyze.py: delta = AUROC of repeat-averaged
per-patient scores (a) minus (b); subject-bootstrap 95 % CI (2000 resamples, seed 2); sign count over
the 25 outer folds. SUPPORTED iff delta >= 0.03 AND CI lower bound > 0 AND delta > 0 in >= 18/25 folds
(RF primary; SMO descriptive).

Two AUROC summaries are reported and labelled:
  auroc_mean_of_repeats  = mean over the 5 repeats of the per-repeat patient AUROC (+ SD)
  auroc_repeat_averaged  = AUROC of the per-patient score averaged over repeats (+ subject-bootstrap CI)

Also: the true-label arm vs the v1 frozen features/metrics (re-extraction sanity check), and the
wpds-vs-stft equivalence report (|CI| within +/-0.03 required to claim "no meaningful difference").

usage: python scripts/16_e2_analyze.py [TAG=e2]
Writes results/tables/e2_auroc.csv, e2_contrasts.csv, e2_equivalence.csv, e2_true_arm_vs_v1.csv,
results/logs/e2_analysis.json.
"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap

TAG = sys.argv[1] if len(sys.argv) > 1 else "e2"
N_BOOT, DELTA_MIN, FOLDS_MIN, EQ_MARGIN = 2000, 0.03, 18, 0.03
pred = pd.read_csv(f"results/predictions/{TAG}_predictions.csv")


def averaged(g):
    return g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean()


def auc(df):
    return roc_auc_score(df.y, df.score)


def fold_aucs(S, C):
    g = pred[(pred.set == S) & (pred.clf == C)]
    return g.groupby(["repeat", "fold"]).apply(lambda x: roc_auc_score(x.y, x.score), include_groups=False)


avg = {}
rows = []
for (S, C), g in pred.groupby(["set", "clf"]):
    a = averaged(g); avg[(S, C)] = a
    rep = [roc_auc_score(h.y, h.score) for _, h in g.groupby("repeat")]
    lo, hi, _ = subject_bootstrap(a, auc, n_boot=N_BOOT, seed=1)
    _, rep_name, cond = S.split("_")
    rows.append(dict(set=S, representation=rep_name, labels=cond, clf=C, n_patients=len(a),
                     auroc_mean_of_repeats=np.mean(rep), auroc_mean_of_repeats_sd=np.std(rep, ddof=1),
                     auroc_repeat_averaged=auc(a), auroc_repeat_averaged_ci_lo=lo, auroc_repeat_averaged_ci_hi=hi))
A = pd.DataFrame(rows).sort_values(["clf", "representation", "labels"])
A.to_csv("results/tables/e2_auroc.csv", index=False)


def contrast(a, b, C, seed=2):
    J = avg[(a, C)].merge(avg[(b, C)], on=["patient_id", "subject_id", "y"], suffixes=("_a", "_b"))
    d = roc_auc_score(J.y, J.score_a) - roc_auc_score(J.y, J.score_b)
    lo, hi, _ = subject_bootstrap(J, lambda df: roc_auc_score(df.y, df.score_a) - roc_auc_score(df.y, df.score_b),
                                  n_boot=N_BOOT, seed=seed)
    fd = fold_aucs(a, C) - fold_aucs(b, C)
    mor = (np.mean([roc_auc_score(h.y, h.score) for _, h in pred[(pred.set == a) & (pred.clf == C)].groupby("repeat")])
           - np.mean([roc_auc_score(h.y, h.score) for _, h in pred[(pred.set == b) & (pred.clf == C)].groupby("repeat")]))
    return d, lo, hi, int((fd > 0).sum()), len(fd), mor


HYP = [("H5a", "wpd", "perm"), ("H5b", "stft", "perm"), ("H5c", "wpds", "perm"),
       ("H5d", "wpd", "shift"), ("H5d", "stft", "shift"), ("H5d", "wpds", "shift")]
crow = []
for C in sorted(pred.clf.unique()):
    for h, rep, null in HYP:
        a, b = f"E2_{rep}_true", f"E2_{rep}_{null}"
        d, lo, hi, pos, n, mor = contrast(a, b, C)
        ok = (d >= DELTA_MIN) and (lo > 0) and (pos >= FOLDS_MIN)
        crow.append(dict(hypothesis=h, clf=C, representation=rep, a=a, b=b, delta_auroc_repeat_averaged=d,
                         ci_lo=lo, ci_hi=hi, folds_positive=f"{pos}/{n}", delta_auroc_mean_of_repeats=mor,
                         crit_delta=d >= DELTA_MIN, crit_ci=lo > 0, crit_folds=pos >= FOLDS_MIN,
                         verdict=("SUPPORTED" if ok else "NOT SUPPORTED") if C == "RF" else "descriptive"))
CT = pd.DataFrame(crow)
CT.to_csv("results/tables/e2_contrasts.csv", index=False)

erow = []
for C in sorted(pred.clf.unique()):
    d, lo, hi, pos, n, mor = contrast("E2_wpds_true", "E2_stft_true", C, seed=3)
    within = (lo >= -EQ_MARGIN) and (hi <= EQ_MARGIN)
    erow.append(dict(contrast="wpds - stft (aligned, true labels)", clf=C, delta_auroc_repeat_averaged=d, ci_lo=lo,
                     ci_hi=hi, folds_positive=f"{pos}/{n}", delta_auroc_mean_of_repeats=mor, margin=EQ_MARGIN,
                     ci_within_margin=within,
                     statement=("no meaningful difference (CI within +/-0.03)" if within else
                                "equivalence NOT shown (CI extends beyond +/-0.03)") + ("" if C == "RF" else " [descriptive]")))
EQ = pd.DataFrame(erow)
EQ.to_csv("results/tables/e2_equivalence.csv", index=False)

# true-label arm vs v1 frozen features and metrics (sanity: same extractor, same folds, deterministic WEKA)
V1F = {"stft": "rec_features_A_stft.csv", "wpd": "rec_features_A_wpd_db4.csv", "wpds": "rec_features_A_wpd_db4_smooth.csv"}
V1S = {"stft": "A_stft", "wpd": "A_wpd_db4", "wpds": "A_wpd_db4_smooth"}
v1p = pd.concat([pd.read_csv("results/predictions/main_predictions.csv"),
                 pd.read_csv("results/predictions/posthoc_smoothing_predictions.csv")], ignore_index=True)
v1p = v1p.drop_duplicates(["set", "clf", "repeat", "patient_id"])
trow = []
for rep in V1F:
    old = pd.read_csv(f"data/processed/{V1F[rep]}").set_index("rec_id")
    new = pd.read_csv(f"data/processed/e2/rec_features_E2_{rep}_true.csv").set_index("rec_id")
    num = old.select_dtypes("number").columns
    same_nan = bool((old[num].isna() == new.loc[old.index, num].isna()).all().all())
    mad = float(np.nanmax((old[num] - new.loc[old.index, num]).abs().to_numpy()))
    for C in sorted(pred.clf.unique()):
        g = v1p[(v1p.set == V1S[rep]) & (v1p.clf == C)]
        a = A[(A.set == f"E2_{rep}_true") & (A.clf == C)].iloc[0]
        trow.append(dict(representation=rep, clf=C, v1_set=V1S[rep], features_same_nan_pattern=same_nan,
                         features_max_abs_diff=mad,
                         v1_auroc_mean_of_repeats=np.mean([auc(h) for _, h in g.groupby("repeat")]) if len(g) else np.nan,
                         v1_auroc_repeat_averaged=auc(averaged(g)) if len(g) else np.nan,
                         e2_auroc_mean_of_repeats=a.auroc_mean_of_repeats, e2_auroc_repeat_averaged=a.auroc_repeat_averaged))
TR = pd.DataFrame(trow)
TR.to_csv("results/tables/e2_true_arm_vs_v1.csv", index=False)

json.dump(dict(tag=TAG, n_pred_rows=len(pred), sets=sorted(pred.set.unique()), clfs=sorted(pred.clf.unique()),
               rf_verdicts=CT[CT.clf == "RF"][["hypothesis", "representation", "b", "verdict"]].to_dict("records")),
          open("results/logs/e2_analysis.json", "w"), indent=2)
pd.set_option("display.width", 250)
for name, df in [("AUROC", A), ("CONTRASTS", CT), ("EQUIVALENCE", EQ), ("TRUE ARM vs V1", TR)]:
    print(f"\n== {name} ==\n" + df.round(4).to_string(index=False))
