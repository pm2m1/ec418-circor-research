"""Write-up: operating-point metrics of the main models from SAVED predictions (no retraining).

Same definition as scripts/07_analyze.py `per_repeat_metrics`: within each repeat, every patient is classified with the
threshold of its own outer fold, derived on the inner training folds (thr_spec80: specificity >= 0.80; thr_wacc: maximum
weighted accuracy). threshold_metrics -> sensitivity, specificity, balanced accuracy = (Se + Sp)/2 and the official Challenge
weighted accuracy; mean and SD over the 5 repeats. Self-check: the v1 values must equal results/tables/main_metrics_full.csv.
Writes results/tables/p4/operating_points.csv.
usage: .venv/bin/python scripts/p4_operating_points.py
"""
import os

import numpy as np
import pandas as pd

from ec418.evaluation.metrics import threshold_metrics

MODELS = [("repro_mac", "B0", "B0 acoustic"), ("repro_mac", "B1", "B1 Vimalajeewa 2025"), ("repro_mac", "W_stft", "whole-signal STFT"),
          ("repro_mac", "W_wpd_db4", "whole-signal WPD db4"), ("e2", "E2_stft_true", "expert-aligned STFT"),
          ("e2", "E2_wpd_true", "expert-aligned WPD"), ("e2", "E2_wpds_true", "expert-aligned WPD smoothed"),
          ("e4", "E4_stft", "E4 automatic STFT"), ("e4", "E4_wpd", "E4 automatic WPD"), ("e4", "E4_wpds", "E4 automatic WPD smoothed"),
          ("p3_g2", "E4q_stft", "E4q shortcut-free STFT"), ("p3_g2", "E4q_wpd", "E4q shortcut-free WPD"),
          ("p3_g2", "E4q_wpds", "E4q shortcut-free WPD smoothed"), ("main", "A_stft", "v1 check: A_stft (Linux)")]
KEYS = ["sensitivity", "specificity", "balanced_accuracy", "weighted_accuracy"]


def per_repeat(g):
    out = []
    for r, h in g.groupby("repeat"):
        y, s = h.y.values, h.score.values
        m80 = threshold_metrics(y, (s >= h.thr_spec80.values).astype(int), 0.5)
        mw = threshold_metrics(y, (s >= h.thr_wacc.values).astype(int), 0.5)
        out.append({**{f"spec80op_{k}": m80[k] for k in KEYS}, **{f"waccop_{k}": mw[k] for k in KEYS}})
    return pd.DataFrame(out)


cache = {}
rows = []
for tag, S, label in MODELS:
    if tag not in cache:
        cache[tag] = pd.read_csv(f"results/predictions/{tag}_predictions.csv")
    P = cache[tag]
    for C in ["RF", "SMO"]:
        g = P[(P.set == S) & (P.clf == C)]
        if not len(g):
            continue
        pr = per_repeat(g)
        rows.append(dict(tag=tag, set=S, label=label, clf=C, **{f"{c}": pr[c].mean() for c in pr.columns},
                         **{f"{c}_sd": pr[c].std(ddof=1) for c in pr.columns}))
R = pd.DataFrame(rows)
v1 = pd.read_csv("results/tables/main_metrics_full.csv").set_index(["set", "clf"])
chk = R[R.tag == "main"]
for _, r in chk.iterrows():
    for c in ["spec80op_sensitivity", "spec80op_specificity", "spec80op_weighted_accuracy", "waccop_weighted_accuracy"]:
        assert abs(r[c] - v1.loc[(r.set, r.clf), c]) < 1e-12, f"definition mismatch vs main_metrics_full: {r.set} {r.clf} {c}"
os.makedirs("results/tables/p4", exist_ok=True)
R.to_csv("results/tables/p4/operating_points.csv", index=False)
pd.set_option("display.width", 220)
print(R[["set", "clf", "spec80op_sensitivity", "spec80op_specificity", "spec80op_balanced_accuracy", "spec80op_weighted_accuracy",
         "waccop_weighted_accuracy"]].round(3).to_string(index=False))
print("v1 self-check vs main_metrics_full.csv: identical")
