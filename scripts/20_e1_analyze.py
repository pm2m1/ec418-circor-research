"""Phase-2 E1 analysis under the locked rule (docs/PROTOCOL_V2_LOCKED.md "E1", amendment I2).

Inputs: results/predictions/e1_predictions.csv (E1_<rep>_auto + B1, W_stft, W_wpd_db4 rerun in the same tag on the
committed features) and results/predictions/e2_predictions.csv (E2_<rep>_true = expert labels, same Mac, v1.0.3).
Statistics as scripts/07 and 16: delta = AUROC of repeat-averaged per-patient scores (a) - (b); subject-bootstrap
95 % CI (2000 resamples, seed 2); sign count over the 25 outer folds (reported).
  H6a  (wpd)        : AUROC(auto) - AUROC(true) >= -0.03                      -> SUPPORTED / NOT SUPPORTED (RF)
  H6b  (wpd)        : AUROC(auto) - AUROC(B1) > 0 AND CI lower bound > 0      -> SUPPORTED / NOT SUPPORTED (RF)
  H6c  (stft, wpds) : the same two tests                                       (RF; SMO descriptive throughout)
Descriptive: auto vs whole-signal sets (W_stft, W_wpd_db4); sensitivity by systolic murmur grade at the
inner-fold spec>=0.80 threshold (mean over repeats). Two AUROC summaries, labelled as in E2.

usage: python scripts/20_e1_analyze.py
Writes results/tables/e1_auroc.csv, e1_hypotheses.csv, e1_vs_whole_signal.csv, e1_grade_sensitivity.csv,
results/logs/e1_analysis.json.
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap

N_BOOT, MARGIN = 2000, 0.03
REPS = ["wpd", "stft", "wpds"]
e1 = pd.read_csv("results/predictions/e1_predictions.csv")
e2 = pd.read_csv("results/predictions/e2_predictions.csv")
pred = pd.concat([e1, e2[e2.set.str.endswith("_true")]], ignore_index=True)
seg = json.load(open("results/logs/e1_segmentation.json"))


def averaged(g):
    return g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean()


def auc(df):
    return roc_auc_score(df.y, df.score)


def sel(S, C):
    return pred[(pred.set == S) & (pred.clf == C)]


avg = {k: averaged(g) for k, g in pred.groupby(["set", "clf"])}


def mean_of_repeats(S, C):
    return np.mean([auc(h) for _, h in sel(S, C).groupby("repeat")])


def contrast(a, b, C):
    J = avg[(a, C)].merge(avg[(b, C)], on=["patient_id", "subject_id", "y"], suffixes=("_a", "_b"))
    d = roc_auc_score(J.y, J.score_a) - roc_auc_score(J.y, J.score_b)
    lo, hi, _ = subject_bootstrap(J, lambda df: roc_auc_score(df.y, df.score_a) - roc_auc_score(df.y, df.score_b),
                                  n_boot=N_BOOT, seed=2)
    fa = sel(a, C).groupby(["repeat", "fold"]).apply(lambda x: auc(x), include_groups=False)
    fb = sel(b, C).groupby(["repeat", "fold"]).apply(lambda x: auc(x), include_groups=False)
    return dict(delta_auroc_repeat_averaged=d, ci_lo=lo, ci_hi=hi, folds_positive=f"{int(((fa - fb) > 0).sum())}/{len(fa)}",
                delta_auroc_mean_of_repeats=mean_of_repeats(a, C) - mean_of_repeats(b, C))


rows = []
for (S, C), a in avg.items():
    lo, hi, _ = subject_bootstrap(a, auc, n_boot=N_BOOT, seed=1)
    rep = [auc(h) for _, h in sel(S, C).groupby("repeat")]
    rows.append(dict(set=S, clf=C, n_patients=len(a), auroc_mean_of_repeats=np.mean(rep),
                     auroc_mean_of_repeats_sd=np.std(rep, ddof=1), auroc_repeat_averaged=auc(a),
                     auroc_repeat_averaged_ci_lo=lo, auroc_repeat_averaged_ci_hi=hi))
A = pd.DataFrame(rows).sort_values(["clf", "set"])
A.to_csv("results/tables/e1_auroc.csv", index=False)

hyp = []
for C in ["RF", "SMO"]:
    for rep in REPS:
        auto = f"E1_{rep}_auto"
        ha, hb = ("H6a", "H6b") if rep == "wpd" else ("H6c(a)", "H6c(b)")
        r = contrast(auto, f"E2_{rep}_true", C)
        ok = r["delta_auroc_repeat_averaged"] >= -MARGIN
        hyp.append(dict(hypothesis=ha, clf=C, representation=rep, a=auto, b=f"E2_{rep}_true",
                        rule="delta >= -0.03", **r,
                        verdict=("SUPPORTED" if ok else "NOT SUPPORTED") if C == "RF" else "descriptive"))
        r = contrast(auto, "B1", C)
        ok = r["delta_auroc_repeat_averaged"] > 0 and r["ci_lo"] > 0
        hyp.append(dict(hypothesis=hb, clf=C, representation=rep, a=auto, b="B1", rule="delta > 0 and CI lower > 0", **r,
                        verdict=("SUPPORTED" if ok else "NOT SUPPORTED") if C == "RF" else "descriptive"))
H = pd.DataFrame(hyp)
H["low_quality_segmentation"] = seg["low_quality_segmentation"]
H.to_csv("results/tables/e1_hypotheses.csv", index=False)

W = pd.DataFrame([dict(clf=C, a=f"E1_{rep}_auto", b=w, **contrast(f"E1_{rep}_auto", w, C))
                  for C in ["RF", "SMO"] for rep in REPS for w in ["W_stft", "W_wpd_db4"]])
W.to_csv("results/tables/e1_vs_whole_signal.csv", index=False)

pt = pd.read_csv("results/tables/v103_patients_audit.csv")[["patient_id", "systolic_grading"]]
gs = []
for (S, C), g in pred.groupby(["set", "clf"]):
    g = g[g.y == 1].merge(pt, on="patient_id")
    g = g.assign(hit=(g.score >= g.thr_spec80).astype(int), grade=g.systolic_grading.fillna("none"))
    for grade, h in [("all Present", g)] + list(g.groupby("grade")):
        gs.append(dict(set=S, clf=C, grade=grade, n_patients=h.patient_id.nunique(),
                       sensitivity_spec80_mean_over_repeats=h.groupby("repeat").hit.mean().mean()))
G = pd.DataFrame(gs)
G.to_csv("results/tables/e1_grade_sensitivity.csv", index=False)

json.dump(dict(segmentation=dict(s1_f1=seg["s1_f1"], s2_f1=seg["s2_f1"], frame_accuracy_4state=seg["frame_accuracy_4state"],
                                 low_quality_segmentation=seg["low_quality_segmentation"]),
               rf_verdicts=H[H.clf == "RF"][["hypothesis", "representation", "b", "delta_auroc_repeat_averaged", "ci_lo",
                                             "verdict"]].to_dict("records")),
          open("results/logs/e1_analysis.json", "w"), indent=2)
pd.set_option("display.width", 250)
for name, df in [("AUROC", A), ("HYPOTHESES", H), ("VS WHOLE-SIGNAL", W),
                 ("GRADE SENSITIVITY (RF)", G[G.clf == "RF"].pivot(index="grade", columns="set",
                                                                   values="sensitivity_spec80_mean_over_repeats"))]:
    print(f"\n== {name} ==\n" + df.round(4).to_string())
