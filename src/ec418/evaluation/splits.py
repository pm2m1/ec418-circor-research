"""Subject-grouped, label-stratified fold generation with explicit leakage assertions."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold


class LeakageError(AssertionError):
    pass


def assert_disjoint(train: pd.DataFrame, test: pd.DataFrame, cols=("subject_id", "patient_id")):
    for c in cols:
        if c in train and c in test:
            inter = set(train[c]) & set(test[c])
            if inter:
                raise LeakageError(f"{c} overlap between train and test: {sorted(inter)[:5]} (n={len(inter)})")


def grouped_folds(patients: pd.DataFrame, n_splits: int, seed: int, label_col="y", group_col="subject_id"):
    """Yield (fold, train_idx, test_idx) over rows of a ONE-ROW-PER-PATIENT table."""
    if patients["patient_id"].duplicated().any():
        raise ValueError("expected one row per patient")
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for k, (tr, te) in enumerate(sgkf.split(patients, patients[label_col], patients[group_col])):
        assert_disjoint(patients.iloc[tr], patients.iloc[te])
        yield k, tr, te


def make_fold_table(patients: pd.DataFrame, n_splits=5, seeds=(0, 1, 2, 3, 4), inner_splits=3):
    """Long table: repeat, outer_fold, patient_id, subject_id, role in {'test','train'},
    inner_fold (for train rows; -1 for test rows). Saved to disk and frozen before modelling."""
    rows = []
    for r, seed in enumerate(seeds):
        for k, tr, te in grouped_folds(patients, n_splits, seed):
            trp = patients.iloc[tr].reset_index(drop=True)
            inner = np.full(len(trp), -1)
            for ik, itr, ite in grouped_folds(trp, inner_splits, 1000 + 10 * seed + k):
                inner[ite] = ik
            for pid, sid in zip(patients.iloc[te]["patient_id"], patients.iloc[te]["subject_id"]):
                rows.append((r, k, pid, sid, "test", -1))
            for pid, sid, ik in zip(trp["patient_id"], trp["subject_id"], inner):
                rows.append((r, k, pid, sid, "train", int(ik)))
    return pd.DataFrame(rows, columns=["repeat", "outer_fold", "patient_id", "subject_id", "role", "inner_fold"])


def verify_fold_table(ft: pd.DataFrame) -> dict:
    """Re-check every invariant from the frozen table alone."""
    report = dict(n_checks=0)
    for (r, k), g in ft.groupby(["repeat", "outer_fold"]):
        tr, te = g[g.role == "train"], g[g.role == "test"]
        assert_disjoint(tr, te)
        report["n_checks"] += 1
        for ik, gi in tr.groupby("inner_fold"):
            itr = tr[tr.inner_fold != ik]
            assert_disjoint(itr, gi)
            report["n_checks"] += 1
    for r, g in ft[ft.role == "test"].groupby("repeat"):
        if g["patient_id"].duplicated().any():
            raise LeakageError(f"repeat {r}: a patient is tested twice")
        report[f"repeat{r}_tested_patients"] = int(g.patient_id.nunique())
    return report
