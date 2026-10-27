"""Phase-2 E4 analysis under the pre-registered rules (docs/PROTOCOL_V2_LOCKED.md "E4", tag e4-prereg).

E4_<rep> (HSMM labels kept in predicted spans, tag e4) vs expert labels E2_<rep>_true (tag e2), B1 and W_stft (tag e1);
references D1_<rep> (tag diag, expert spans = upper) and E1b_<rep>_auto (tag e1b, no span selection = lower).
RF primary with wpd as the primary representation (stft, wpds under the same rules); SMO descriptive.
  H9a: AUROC(E4) - AUROC(expert) >= -0.03
  H9b: AUROC(E4) - AUROC(B1) > 0 and subject-bootstrap CI lower bound > 0
  H9c: AUROC(E4) - AUROC(W_stft) > 0 and CI lower bound > 0   (deployability test)
Delta = AUROC of repeat-averaged per-patient scores; subject bootstrap 2000, seed 2 (AUROC CIs seed 1); folds with
delta > 0 and both AUROC summaries reported. Also: sensitivity by murmur grade, missing aligned features by class.
usage: python scripts/27_e4_analyze.py
Writes results/tables/e4_{auroc,hypotheses,references,grade_sensitivity,feature_coverage}.csv, results/logs/e4_analysis.json.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap

N_BOOT, MARGIN = 2000, 0.03
REPS = ["wpd", "stft", "wpds"]
e4 = pd.read_csv("results/predictions/e4_predictions.csv")
e2 = pd.read_csv("results/predictions/e2_predictions.csv")
e1 = pd.read_csv("results/predictions/e1_predictions.csv")
e1b = pd.read_csv("results/predictions/e1b_predictions.csv")
dg = pd.read_csv("results/predictions/diag_predictions.csv")
pred = pd.concat([e4, e2[e2.set.str.endswith("_true")], e1[e1.set.isin(["B1", "W_stft"])], e1b,
                  dg[dg.set.str.startswith("D1_")]], ignore_index=True)
det = json.load(open("results/logs/e4_span_detector.json"))


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
A.to_csv("results/tables/e4_auroc.csv", index=False)

hyp = []
for C in ["RF", "SMO"]:
    for rep in REPS:
        a = f"E4_{rep}"
        for h, b, rule in [("H9a", f"E2_{rep}_true", "delta >= -0.03"), ("H9b", "B1", "delta > 0 and CI lower > 0"),
                           ("H9c", "W_stft", "delta > 0 and CI lower > 0")]:
            r = contrast(a, b, C)
            d = r["delta_auroc_repeat_averaged"]
            ok = d >= -MARGIN if h == "H9a" else (d > 0 and r["ci_lo"] > 0)
            hyp.append(dict(hypothesis=h, clf=C, representation=rep, primary=rep == "wpd", a=a, b=b, rule=rule, **r,
                            verdict=("SUPPORTED" if ok else "NOT SUPPORTED") if C == "RF" else "descriptive"))
H = pd.DataFrame(hyp)
H.to_csv("results/tables/e4_hypotheses.csv", index=False)

D = pd.DataFrame([dict(clf=C, a=f"E4_{rep}", b=b, **contrast(f"E4_{rep}", b, C))
                  for C in ["RF", "SMO"] for rep in REPS for b in [f"D1_{rep}", f"E1b_{rep}_auto"]])
D.to_csv("results/tables/e4_references.csv", index=False)

pt = pd.read_csv("results/tables/v103_patients_audit.csv")[["patient_id", "systolic_grading"]]
gs = []
for (S, C), g in pred.groupby(["set", "clf"]):
    g = g[g.y == 1].merge(pt, on="patient_id")
    g = g.assign(hit=(g.score >= g.thr_spec80).astype(int), grade=g.systolic_grading.fillna("none"))
    for grade, h in [("all Present", g)] + list(g.groupby("grade")):
        gs.append(dict(set=S, clf=C, grade=grade, n_patients=h.patient_id.nunique(),
                       sensitivity_spec80_mean_over_repeats=h.groupby("repeat").hit.mean().mean()))
G = pd.DataFrame(gs)
G.to_csv("results/tables/e4_grade_sensitivity.csv", index=False)

cov = []
for d in sorted(os.listdir("data/interim/e4/features")):
    r, k = (int(x[1:]) for x in d.split("_"))
    rec = pd.read_csv(f"data/interim/e4/features/{d}/rec_features_E4_wpd.csv")
    none = rec[[c for c in rec.columns if c.startswith("wpdA")]].isna().all(axis=1)
    pat = rec.assign(n=none).groupby(["patient_id", "murmur"]).n.all().reset_index()
    cov.append(dict(repeat=r, fold=k, recordings=len(rec), recordings_without_aligned=int(none.sum()),
                    present_recordings_without=int((none & (rec.murmur == "Present")).sum()),
                    absent_recordings_without=int((none & (rec.murmur == "Absent")).sum()),
                    patients_without_any=int(pat.n.sum()), present_patients_without_any=int(pat[pat.murmur == "Present"].n.sum()),
                    absent_patients_without_any=int(pat[pat.murmur == "Absent"].n.sum())))
CV = pd.DataFrame(cov)
CV.to_csv("results/tables/e4_feature_coverage.csv", index=False)

json.dump(dict(repeats=sorted(int(x) for x in e4.repeat.unique()), span_detector=det,
               rf_verdicts=H[H.clf == "RF"][["hypothesis", "representation", "b", "delta_auroc_repeat_averaged", "ci_lo",
                                             "verdict"]].to_dict("records")),
          open("results/logs/e4_analysis.json", "w"), indent=2, default=float)
pd.set_option("display.width", 250)
for name, df in [("AUROC", A), ("HYPOTHESES", H), ("REFERENCES", D),
                 ("COVERAGE", CV.drop(columns=["repeat", "fold"]).agg(["min", "max", "mean"])),
                 ("GRADE SENSITIVITY (RF)", G[G.clf == "RF"].pivot(index="grade", columns="set",
                                                                   values="sensitivity_spec80_mean_over_repeats"))]:
    print(f"\n== {name} ==\n" + df.round(4).to_string())
