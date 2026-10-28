"""Phase 3 G2, step 4.6: cross-platform robustness check (descriptive, no verdicts), run only AFTER the Mac G2 results
were reported. Compares the Mac predictions (results/predictions/p3_g2_predictions.csv) with the sealed cloud predictions
(results/p3_cloud_reference/p3_g2_predictions_SEALED_unopened.csv, opened here for the first time) per set/clf:
repeat-averaged AUROC and mean-of-repeats AUROC (Mac, cloud, delta) and max |score delta|.
Writes results/tables/p3/g2_mac_vs_cloud_sealed.csv.
usage: .venv/bin/python scripts/p3_06_g2_sealed_compare.py
"""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

M = pd.read_csv("results/predictions/p3_g2_predictions.csv")
C = pd.read_csv("results/p3_cloud_reference/p3_g2_predictions_SEALED_unopened.csv")
assert list(M.columns) == list(C.columns), "column mismatch"


def summ(g):
    a = g.groupby(["patient_id", "y"], as_index=False).score.mean()
    return roc_auc_score(a.y, a.score), np.mean([roc_auc_score(h.y, h.score) for _, h in g.groupby("repeat")])


J = M.merge(C, on=["set", "clf", "repeat", "fold", "patient_id"], suffixes=("_mac", "_cloud"), how="outer", indicator=True)
rows = []
for (S, Cl), g in M.groupby(["set", "clf"]):
    gc = C[(C.set == S) & (C.clf == Cl)]
    j = J[(J.set == S) & (J.clf == Cl)]
    ra_m, mor_m = summ(g)
    ra_c, mor_c = summ(gc) if len(gc) else (np.nan, np.nan)
    rows.append(dict(set=S, clf=Cl, rows_mac=len(g), rows_cloud=len(gc), rows_matched=int((j._merge == "both").sum()),
                     auroc_repeat_averaged_mac=ra_m, auroc_repeat_averaged_cloud=ra_c, delta_repeat_averaged=ra_m - ra_c,
                     auroc_mean_of_repeats_mac=mor_m, auroc_mean_of_repeats_cloud=mor_c, delta_mean_of_repeats=mor_m - mor_c,
                     max_abs_score_delta=float((j.score_mac - j.score_cloud).abs().max())))
R = pd.DataFrame(rows)
R.to_csv("results/tables/p3/g2_mac_vs_cloud_sealed.csv", index=False)
pd.set_option("display.width", 220)
print(R.round(4).to_string(index=False))
print("max |delta AUROC| repeat-averaged: %.4f, mean of repeats: %.4f" % (R.delta_repeat_averaged.abs().max(), R.delta_mean_of_repeats.abs().max()))
