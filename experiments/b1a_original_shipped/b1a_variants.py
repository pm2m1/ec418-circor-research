"""B1-A variants on the baseline authors' SHIPPED feature files (unchanged features).

Purpose: (1) quantify patient overlap inside the original recording-level 80/20 split,
(2) check the paper's stated class weights (1:4) vs the demo's 'balanced',
(3) show the effect of the row-misalignment bug in the shipped control features.
Run from this directory: ../../.venv/bin/python b1a_variants.py
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import roc_auc_score, recall_score, accuracy_score

COLS = ["Entropy", "Slope", "ID", "Hurst", "LeftSlope", "RightSlope", "LeftTangent",
        "RightTangent", "Broadness", "LeftTangentPoint", "RightTangentPoint"]
FEATS = ["Entropy", "Slope", "Hurst", "LeftSlope", "RightSlope", "LeftTangent",
         "LeftTangentPoint", "RightTangentPoint"]


def load():
    ec = pd.read_csv("case_features/Window_Entropy_Case.csv", header=None)
    sc = pd.read_csv("case_features/Window_Slope_Case.csv", header=None)
    mc = pd.read_csv("case_features/Window_Mf_Case.csv", header=None)
    en = pd.read_csv("control_features/Window_Entropy_Control.csv", header=None)
    sn = pd.read_csv("control_features/Window_Slope_Control.csv", header=None)
    mn = pd.read_csv("control_features/Window_Mf_Control.csv", header=None)
    case = pd.concat([ec.T, sc.T, mc], axis=1); case.columns = COLS; case["y"] = 1
    ctrl = pd.concat([en.T, sn.T, mn], axis=1); ctrl.columns = COLS; ctrl["y"] = 0
    return case, ctrl


def run(data, cw, seed_shuffle=42, seed_split=0):
    d = data.sample(frac=1, random_state=seed_shuffle).reset_index(drop=True)
    d = d.fillna(d.mean())
    X, y = d[FEATS], d["y"]
    Xtr, Xte, ytr, yte, idtr, idte = train_test_split(X, y, d["ID"], test_size=0.2, random_state=seed_split)
    if cw == "balanced":
        from sklearn.utils import class_weight
        w = class_weight.compute_class_weight("balanced", classes=np.array([0, 1]), y=ytr)
        cw = {0: w[0], 1: w[1]}
    m = SVC(probability=True, C=100, gamma=0.1, kernel="rbf", class_weight=cw, random_state=0).fit(Xtr, ytr)
    p = m.predict(Xte); s = m.predict_proba(Xte)[:, 1]
    overlap_pat = len(set(idte) & set(idtr)) / len(set(idte))
    overlap_rows = np.isin(idte, list(set(idtr))).mean()
    return dict(acc=accuracy_score(yte, p), present_recall=recall_score(yte, p, pos_label=1),
                absent_recall=recall_score(yte, p, pos_label=0), auc=roc_auc_score(yte, s),
                test_patients_also_in_train=overlap_pat, test_rows_with_patient_in_train=overlap_rows)


if __name__ == "__main__":
    case, ctrl = load()
    full = pd.concat([case, ctrl], axis=0)
    rows = []
    for cw_name, cw in [("balanced(demo)", "balanced"), ("1:4(paper)", {0: 1, 1: 4})]:
        for s in range(10):
            r = run(full, cw, seed_shuffle=42 + s, seed_split=s); r.update(setting=cw_name, seed=s); rows.append(r)
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(df.groupby("setting")[["acc", "present_recall", "absent_recall", "auc",
                                 "test_patients_also_in_train", "test_rows_with_patient_in_train"]].agg(["mean", "std"]).round(3).T)
    print("\nRows with mean-imputed Entropy/Slope (Unknown recordings appended to controls):",
          int(ctrl["Entropy"].isna().sum()), "all labelled y=0")
    df.to_csv("../../results/tables/b1a_shipped_features_variants.csv", index=False)
