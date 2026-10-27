"""POST-HOC, descriptive caveat check for E4 (not pre-registered; changes no verdict; docs/E4_RESULTS.md §6).

How much Present-vs-Absent information sits in by-products of the span selection alone (no acoustic features)?
Per test patient of each outer fold (outer detector / features of that fold):
  (a) share of the patient's recordings WITHOUT E4 aligned features (below the coverage minimum);
  (b) mean predicted-annotated window fraction over the patient's recordings;
  (c) reference: mean expert-annotated window fraction (the coverage shortcut, v1: AUROC 0.56 at patient level).
AUROC per outer fold, then mean +/- SD over the 25 folds. Writes results/tables/e4_shortcut_check.csv.
"""
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

FT = pd.read_csv("configs/folds_patient_level.csv")
rows = []
for d in sorted(os.listdir("data/interim/e4/features")):
    r, k = (int(x[1:]) for x in d.split("_"))
    te = FT[(FT.repeat == r) & (FT.outer_fold == k) & (FT.role == "test")][["patient_id", "y"]]
    rec = pd.read_csv(f"data/interim/e4/features/{d}/rec_features_E4_wpd.csv")
    rec["no_feat"] = rec[[c for c in rec.columns if c.startswith("wpdA")]].isna().all(axis=1).astype(float)
    W = pd.read_csv(f"data/interim/e4/features/{d}/windows_test.csv").merge(rec[["rec_id", "patient_id"]], on="rec_id")
    per_rec = W.groupby(["patient_id", "rec_id"]).agg(pred=("pred", "mean"), target=("target", "mean")).reset_index()
    P = te.merge(rec.groupby("patient_id").no_feat.mean().rename("a_missing_share"), on="patient_id") \
          .merge(per_rec.groupby("patient_id").pred.mean().rename("b_predicted_frac"), on="patient_id") \
          .merge(per_rec.groupby("patient_id").target.mean().rename("c_expert_frac"), on="patient_id")
    rows.append(dict(repeat=r, fold=k, n_patients=len(P),
                     auroc_a_missing_share_for_Absent=roc_auc_score(1 - P.y, P.a_missing_share),
                     auroc_b_predicted_frac=roc_auc_score(P.y, P.b_predicted_frac),
                     auroc_c_expert_frac=roc_auc_score(P.y, P.c_expert_frac)))
R = pd.DataFrame(rows)
R.to_csv("results/tables/e4_shortcut_check.csv", index=False)
print(R.drop(columns=["repeat", "fold", "n_patients"]).agg(["mean", "std", "min", "max"]).round(3).to_string())
