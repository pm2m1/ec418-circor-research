"""Phase-2 E1b analysis under the pre-registered rules (docs/PROTOCOL_V2_LOCKED.md "E1b"; same statistics as E1).

Inputs: results/predictions/e1b_predictions.csv (E1b_<rep>_auto, fold-specific LR-HSMM labels), e2_predictions.csv
(E2_<rep>_true = expert labels) and e1_predictions.csv (B1, W_stft, W_wpd_db4, E1_<rep>_auto), all same Mac / v1.0.3.
  H8a (wpd), H8c(a) (stft, wpds): AUROC(auto-HSMM) - AUROC(expert) >= -0.03                 -> SUPPORTED / NOT
  H8b (wpd), H8c(b) (stft, wpds): AUROC(auto-HSMM) - AUROC(B1) > 0 and CI lower bound > 0  -> SUPPORTED / NOT
RF primary, SMO descriptive. Delta = AUROC of repeat-averaged per-patient scores; subject bootstrap 2000, seed 2;
fold counts and both AUROC summaries reported. Descriptive: vs W_stft / W_wpd_db4, vs E1 auto sets, sensitivity by
murmur grade, aligned-feature coverage.

usage: python scripts/22_e1b_analyze.py
Writes results/tables/e1b_{auroc,hypotheses,descriptive_contrasts,grade_sensitivity,feature_coverage,label_coverage}.csv,
results/logs/e1b_analysis.json.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.evaluation.metrics import subject_bootstrap

N_BOOT, MARGIN = 2000, 0.03
REPS = ["wpd", "stft", "wpds"]
e1b = pd.read_csv("results/predictions/e1b_predictions.csv")
e2 = pd.read_csv("results/predictions/e2_predictions.csv")
e1 = pd.read_csv("results/predictions/e1_predictions.csv")
pred = pd.concat([e1b, e2[e2.set.str.endswith("_true")], e1], ignore_index=True)
repeats = sorted(e1b.repeat.unique())
pred = pred[pred.repeat.isin(repeats)]               # comparators restricted to the repeats E1b ran (all 5 here)
seg = json.load(open("results/logs/e1b_segmentation.json"))


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
                     auroc_mean_of_repeats_sd=np.std(rep, ddof=1) if len(rep) > 1 else np.nan,
                     auroc_repeat_averaged=auc(a), auroc_repeat_averaged_ci_lo=lo, auroc_repeat_averaged_ci_hi=hi))
A = pd.DataFrame(rows).sort_values(["clf", "set"])
A.to_csv("results/tables/e1b_auroc.csv", index=False)

hyp = []
for C in ["RF", "SMO"]:
    for rep in REPS:
        auto = f"E1b_{rep}_auto"
        ha, hb = ("H8a", "H8b") if rep == "wpd" else ("H8c(a)", "H8c(b)")
        r = contrast(auto, f"E2_{rep}_true", C)
        ok = r["delta_auroc_repeat_averaged"] >= -MARGIN
        hyp.append(dict(hypothesis=ha, clf=C, representation=rep, a=auto, b=f"E2_{rep}_true", rule="delta >= -0.03", **r,
                        verdict=("SUPPORTED" if ok else "NOT SUPPORTED") if C == "RF" else "descriptive"))
        r = contrast(auto, "B1", C)
        ok = r["delta_auroc_repeat_averaged"] > 0 and r["ci_lo"] > 0
        hyp.append(dict(hypothesis=hb, clf=C, representation=rep, a=auto, b="B1", rule="delta > 0 and CI lower > 0", **r,
                        verdict=("SUPPORTED" if ok else "NOT SUPPORTED") if C == "RF" else "descriptive"))
H = pd.DataFrame(hyp)
H["low_quality_segmentation"] = seg["low_quality_segmentation"]
H.to_csv("results/tables/e1b_hypotheses.csv", index=False)

D = pd.DataFrame([dict(clf=C, a=f"E1b_{rep}_auto", b=b, **contrast(f"E1b_{rep}_auto", b, C))
                  for C in ["RF", "SMO"] for rep in REPS for b in ["W_stft", "W_wpd_db4", f"E1_{rep}_auto"]])
D.to_csv("results/tables/e1b_descriptive_contrasts.csv", index=False)

pt = pd.read_csv("results/tables/v103_patients_audit.csv")[["patient_id", "systolic_grading"]]
gs = []
for (S, C), g in pred.groupby(["set", "clf"]):
    g = g[g.y == 1].merge(pt, on="patient_id")
    g = g.assign(hit=(g.score >= g.thr_spec80).astype(int), grade=g.systolic_grading.fillna("none"))
    for grade, h in [("all Present", g)] + list(g.groupby("grade")):
        gs.append(dict(set=S, clf=C, grade=grade, n_patients=h.patient_id.nunique(),
                       sensitivity_spec80_mean_over_repeats=h.groupby("repeat").hit.mean().mean()))
G = pd.DataFrame(gs)
G.to_csv("results/tables/e1b_grade_sensitivity.csv", index=False)

cov = []
folds = pd.read_csv("configs/folds_patient_level.csv")
for d in sorted(os.listdir("data/interim/e1b/features")):
    r, k = (int(x[1:]) for x in d.split("_"))
    L = pd.read_csv(f"data/interim/e1b/features/{d}/decode_log.csv")
    rec = pd.read_csv(f"data/interim/e1b/features/{d}/rec_features_E1b_wpd_auto.csv")
    fc = [c for c in rec.columns if c.startswith("wpdA")]
    none = rec[fc].isna().all(axis=1)
    cov.append(dict(repeat=r, fold=k, recordings=len(rec), recordings_without_aligned=int(none.sum()),
                    present_recordings_without_aligned=int((none & (rec.murmur == "Present")).sum()),
                    absent_recordings_without_aligned=int((none & (rec.murmur == "Absent")).sum()),
                    patients_without_any_aligned=int(rec.assign(n=none).groupby("patient_id").n.all().sum()),
                    decode_failures=int(L.failure.notna().sum())))
CV = pd.DataFrame(cov)
CV.to_csv("results/tables/e1b_feature_coverage.csv", index=False)

# label coverage (descriptive): share of level-4 columns each labelling marks 1-4, and share inside expert spans
from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.segmentation.evaluation import valid_rows
from ec418.wavelets.bands import column_labels
rt = recording_table(load_patients("data/raw/circor_training_data"))
rt = rt[rt.patient_id.isin(folds.patient_id)]
n2k = pd.read_csv("data/interim/e1b/features/r0_f0/decode_log.csv").set_index("rec_id").n_samples
lc = []
for x in rt.itertuples():
    n = int(np.ceil(n2k[x.rec_id] / 16))
    ex = column_labels(valid_rows(load_segmentation(x.tsv)), n, 16, 2000) > 0
    row = dict(rec_id=x.rec_id, murmur=x.murmur, expert_labelled_frac=ex.mean())
    for name, path in [("e1", f"data/interim/autoseg/{x.rec_id}.tsv"), ("e1b", f"data/interim/e1b/autoseg/r0/{x.rec_id}.tsv")]:
        au = column_labels(load_segmentation(path), n, 16, 2000) > 0
        row[f"{name}_labelled_frac"] = au.mean()
        row[f"{name}_labelled_outside_expert_frac"] = (au & ~ex).sum() / max(1, au.sum())
    lc.append(row)
LC = pd.DataFrame(lc)
LCS = LC.groupby("murmur").median(numeric_only=True).assign(stat="median").reset_index()
LCS = pd.concat([LCS, LC.median(numeric_only=True).to_frame().T.assign(murmur="all", stat="median")], ignore_index=True)
LCS.to_csv("results/tables/e1b_label_coverage.csv", index=False)

json.dump(dict(repeats=[int(x) for x in repeats], segmentation=dict((k, seg[k]) for k in ["s1_f1", "s2_f1",
               "frame_accuracy_4state", "failure_frac", "low_quality_segmentation"]),
               rf_verdicts=H[H.clf == "RF"][["hypothesis", "representation", "b", "delta_auroc_repeat_averaged", "ci_lo",
                                             "verdict"]].to_dict("records")),
          open("results/logs/e1b_analysis.json", "w"), indent=2, default=float)
pd.set_option("display.width", 250)
for name, df in [("AUROC", A), ("HYPOTHESES", H), ("DESCRIPTIVE", D), ("COVERAGE", CV.describe().loc[["min", "max"]]),
                 ("LABEL COVERAGE (median per recording)", LCS),
                 ("GRADE SENSITIVITY (RF)", G[G.clf == "RF"].pivot(index="grade", columns="set",
                                                                   values="sensitivity_spec80_mean_over_repeats"))]:
    print(f"\n== {name} ==\n" + df.round(4).to_string())
