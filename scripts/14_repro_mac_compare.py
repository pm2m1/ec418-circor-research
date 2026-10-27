"""Compare the Mac re-run with the frozen Phase-1 outputs (read-only on every frozen file).

  features SHADOW_DIR : outputs of scripts/13_repro_mac_shadow.sh vs committed files
                        -> results/tables/repro_mac_files.csv (sha256 identity, max |diff| for feature CSVs)
  weka TAG            : results/predictions/<TAG>_predictions.csv vs main_predictions.csv and
                        results/tables/main_metrics_full.csv -> results/tables/<TAG>_auroc_comparison.csv

AUROC summaries: "auroc_mean_of_repeats" = mean over the 5 repeats of the per-repeat patient AUROC (the
`auroc` column of main_metrics_full.csv); "auroc_repeat_averaged" = AUROC of the per-patient score averaged
over the 5 repeats (`auroc_avgscore`).

usage: python scripts/14_repro_mac_compare.py features data/interim/repro_mac_shadow
       python scripts/14_repro_mac_compare.py weka repro_mac
"""
import glob
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

TOL = 1e-6
META = ["rec_id", "patient_id", "subject_id", "location", "murmur"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def compare_features(shadow):
    rows = []
    exact = ["configs/folds_patient_level.csv", "results/tables/fold_composition.csv",
             "results/tables/patients_audit.csv", "results/tables/recordings_audit.csv",
             "results/tables/b1_alignment_verification.csv"]
    for rel in exact:
        a, b = rel, os.path.join(shadow, rel)
        rows.append(dict(file=rel, kind="exact", identical=os.path.exists(b) and sha(a) == sha(b),
                         sha256_committed=sha(a), sha256_mac=sha(b) if os.path.exists(b) else None))
    for b in sorted(glob.glob(os.path.join(shadow, "data/processed/*.csv"))):
        rel = os.path.relpath(b, shadow)
        A = pd.read_csv(rel).set_index("rec_id")
        B = pd.read_csv(b).set_index("rec_id")
        rec = dict(file=rel, kind="numeric", identical=sha(rel) == sha(b),
                   same_rows=A.index.equals(B.index), same_columns=list(A.columns) == list(B.columns))
        if rec["same_rows"] and rec["same_columns"]:
            num = A.select_dtypes("number").columns
            same_nan = (A[num].isna() == B[num].isna()).all().all()
            d = (A[num] - B[num]).abs().to_numpy()
            rec.update(same_nan_pattern=bool(same_nan), n_values=int(np.isfinite(d).sum()),
                       max_abs_diff=float(np.nanmax(d)) if np.isfinite(d).any() else 0.0,
                       non_numeric_equal=bool(A.drop(columns=num).fillna("").astype(str).equals(
                           B.drop(columns=num).fillna("").astype(str))))
            rec["within_tol"] = bool(same_nan and rec["max_abs_diff"] <= TOL and rec["non_numeric_equal"])
        rows.append(rec)
    R = pd.DataFrame(rows)
    R.to_csv("results/tables/repro_mac_files.csv", index=False)
    print(R.to_string(index=False))


def per_set_auroc(pred):
    out = []
    for (S, C), g in pred.groupby(["set", "clf"]):
        mor = np.mean([roc_auc_score(h.y, h.score) for _, h in g.groupby("repeat")])
        a = g.groupby(["patient_id", "y"], as_index=False).score.mean()
        out.append(dict(set=S, clf=C, auroc_mean_of_repeats=mor, auroc_repeat_averaged=roc_auc_score(a.y, a.score)))
    return pd.DataFrame(out)


def compare_weka(tag):
    new = pd.read_csv(f"results/predictions/{tag}_predictions.csv")
    old = pd.read_csv("results/predictions/main_predictions.csv")
    key = ["set", "clf", "repeat", "fold", "patient_id"]
    J = old.merge(new, on=key, suffixes=("_v1", "_mac"), how="outer", indicator=True)
    assert (J._merge == "both").all(), "prediction rows differ between runs"
    N = per_set_auroc(new)
    F = pd.read_csv("results/tables/main_metrics_full.csv")[["set", "clf", "auroc", "auroc_avgscore"]]
    F = F.rename(columns={"auroc": "v1_auroc_mean_of_repeats", "auroc_avgscore": "v1_auroc_repeat_averaged"})
    C = F.merge(N, on=["set", "clf"])
    C["delta_mean_of_repeats"] = C.auroc_mean_of_repeats - C.v1_auroc_mean_of_repeats
    C["delta_repeat_averaged"] = C.auroc_repeat_averaged - C.v1_auroc_repeat_averaged
    sd = (J.score_mac - J.score_v1).abs().groupby([J.set, J.clf]).max().rename("max_abs_score_diff").reset_index()
    C = C.merge(sd, on=["set", "clf"])
    C["within_0.002"] = C[["delta_mean_of_repeats", "delta_repeat_averaged"]].abs().max(axis=1) <= 0.002
    C.to_csv(f"results/tables/{tag}_auroc_comparison.csv", index=False)
    summary = dict(rows_compared=int(len(J)), max_abs_score_diff=float((J.score_mac - J.score_v1).abs().max()),
                   max_abs_thr_spec80_diff=float((J.thr_spec80_mac - J.thr_spec80_v1).abs().max()),
                   max_abs_delta_auroc=float(C[["delta_mean_of_repeats", "delta_repeat_averaged"]].abs().max().max()),
                   all_within_0_002=bool(C["within_0.002"].all()))
    json.dump(summary, open(f"results/logs/{tag}_comparison.json", "w"), indent=2)
    print(C.round(5).to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    {"features": compare_features, "weka": compare_weka}[sys.argv[1]](sys.argv[2])
