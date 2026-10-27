"""Freeze the patient-level, subject-grouped fold table BEFORE any model is trained."""
import hashlib
import json

import pandas as pd

from ec418.data.circor import load_patients, patient_table
from ec418.evaluation.splits import make_fold_table, verify_fold_table

cfg = json.load(open("configs/protocol.json"))
pt = patient_table(load_patients(cfg["data_dir"]))
pt = pt[pt.murmur.isin(["Present", "Absent"])].copy()
pt["y"] = (pt.murmur == "Present").astype(int)
pt = pt[["patient_id", "subject_id", "y"]].reset_index(drop=True)

ft = make_fold_table(pt, n_splits=cfg["outer_folds"], seeds=tuple(cfg["repeat_seeds"]), inner_splits=cfg["inner_folds"])
rep = verify_fold_table(ft)
ft = ft.merge(pt[["patient_id", "y"]], on="patient_id")
ft.to_csv("configs/folds_patient_level.csv", index=False)
h = hashlib.sha256(open("configs/folds_patient_level.csv", "rb").read()).hexdigest()
stats = (ft[ft.role == "test"].groupby(["repeat", "outer_fold"]).agg(n=("patient_id", "size"), pos=("y", "sum"),
                                                                       subjects=("subject_id", "nunique")))
print(stats.to_string())
print(json.dumps(rep, indent=1))
print("folds sha256:", h)
open("configs/folds_patient_level.sha256", "w").write(h + "\n")
stats.to_csv("results/tables/fold_composition.csv")
