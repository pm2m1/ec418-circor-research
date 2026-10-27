"""Errata check for E2 (docs/ERRATA_PHASE2.md): how much of each null's labelled columns fall in columns the expert
left unannotated (label 0). perm/shift act on the whole-recording column vector (ec418.features.label_nulls), so labels
can leave the expert-annotated spans. Writes results/tables/e2_null_span_displacement.csv (+ summary to stdout)."""
import numpy as np
import pandas as pd

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.label_nulls import null_labels
from ec418.wavelets.bands import column_labels

rt = recording_table(load_patients("data/raw/circor_training_data"))
L = pd.read_csv("data/processed/e2/label_null_log.csv").set_index("rec_id")
rows = []
for x in rt.itertuples():
    lab = column_labels(load_segmentation(x.tsv), int(L.n_cols[x.rec_id]), 16, 2000)
    row = dict(rec_id=x.rec_id, murmur=x.murmur, expert_unannotated_frac=float((lab == 0).mean()))
    for c in ["perm", "shift"]:
        nl = null_labels(lab, c, x.rec_id, 125.0)
        row[f"{c}_labelled_in_expert_label0_frac"] = float(((nl > 0) & (lab == 0)).sum() / (nl > 0).sum()) if (nl > 0).any() else np.nan
        row[f"{c}_systole_in_expert_label0_frac"] = float(((nl == 2) & (lab == 0)).sum() / (nl == 2).sum()) if (nl == 2).any() else np.nan
    rows.append(row)
D = pd.DataFrame(rows)
D.to_csv("results/tables/e2_null_span_displacement.csv", index=False)
print(D.drop(columns="rec_id").groupby("murmur").median().round(3).to_string())
print("all:", D.drop(columns=["rec_id", "murmur"]).median().round(3).to_dict())
