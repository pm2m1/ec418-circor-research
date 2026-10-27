"""H1 — evaluation-design effect on the published wavelet baseline (B1).

Features: authors' own B1 values, re-aligned (scripts/03). Classifier: the paper's weighted SVM
(RBF, C=100, gamma=0.1, class weight Absent 1 : Present 4), unscaled features, as in their code.
Only the SPLIT changes:
  A  random 80/20 split of RECORDINGS (paper protocol; a patient's recordings straddle the split)
  B  subject-grouped 5-fold CV (20 % of SUBJECTS per test fold), 5 repeats
Metrics are recording-level for both (that is the paper's unit), plus patient-level for B.
Also: A' = random split on the ORIGINAL shipped (mis-aligned, Unknown-contaminated) table."""
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, recall_score, roc_auc_score

FEATS = ["b1_entropy_cv", "b1_slope", "b1_Hurst_spectral_mode", "b1_LeftSlope", "b1_RightSlope",
         "b1_LeftTangent", "b1_LeftTangentPoint", "b1_RightTangentPoint"]  # same 8 as authors' demo

d = pd.read_csv("data/processed/rec_features_B1.csv")
d["y"] = (d.murmur == "Present").astype(int)
X, y, g = d[FEATS].values, d.y.values, d.subject_id.values


def svm():
    return SVC(kernel="rbf", C=100, gamma=0.1, class_weight={0: 1, 1: 4})


def rec_metrics(yt, s, thr=0.0):
    p = (s >= thr).astype(int)
    return dict(acc=accuracy_score(yt, p), present_recall=recall_score(yt, p, pos_label=1),
                absent_recall=recall_score(yt, p, pos_label=0), auc=roc_auc_score(yt, s))


rows = []
for seed in range(25):
    tr, te = train_test_split(np.arange(len(d)), test_size=0.2, random_state=seed, stratify=y)
    m = svm().fit(X[tr], y[tr])
    r = rec_metrics(y[te], m.decision_function(X[te]))
    r.update(protocol="A_random_recording_split", seed=seed,
             test_recs_with_patient_in_train=float(np.isin(d.patient_id.values[te], d.patient_id.values[tr]).mean()))
    rows.append(r)

pat_rows = []
for rep in range(5):
    for k, (tr, te) in enumerate(StratifiedGroupKFold(5, shuffle=True, random_state=rep).split(X, y, g)):
        assert not set(g[tr]) & set(g[te])
        m = svm().fit(X[tr], y[tr])
        s = m.decision_function(X[te])
        r = rec_metrics(y[te], s)
        r.update(protocol="B_subject_grouped_cv", seed=rep * 5 + k, test_recs_with_patient_in_train=0.0)
        rows.append(r)
        pdf = pd.DataFrame(dict(pid=d.patient_id.values[te], y=y[te], s=s)).groupby("pid").agg(y=("y", "max"), s=("s", "max"))
        pat_rows.append(dict(rep=rep, fold=k, **rec_metrics(pdf.y.values, pdf.s.values)))

res = pd.DataFrame(rows)
summ = res.groupby("protocol")[["acc", "present_recall", "absent_recall", "auc", "test_recs_with_patient_in_train"]].agg(["mean", "std"])
print(summ.round(4).T.to_string())
pat = pd.DataFrame(pat_rows)
print("\nB (grouped), PATIENT level (max over recordings):")
print(pat[["acc", "present_recall", "absent_recall", "auc"]].agg(["mean", "std"]).round(4).to_string())

a = res[res.protocol.str.startswith("A")].auc.values
b = res[res.protocol.str.startswith("B")].auc.values
rng = np.random.default_rng(0)
boot = [rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean() for _ in range(5000)]
out = dict(auc_A_mean=float(a.mean()), auc_B_mean=float(b.mean()), delta=float(a.mean() - b.mean()),
           delta_ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
           note="CI from resampling the 25 split-level AUCs per protocol (splits share data; CI is indicative only)")
print(json.dumps(out, indent=1))
res.to_csv("results/tables/h1_b1_split_protocols_recording_level.csv", index=False)
pat.to_csv("results/tables/h1_b1_grouped_patient_level.csv", index=False)
json.dump(out, open("results/tables/h1_summary.json", "w"), indent=1)
