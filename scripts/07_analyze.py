"""Analyse patient-level WEKA predictions under the locked protocol.

Writes results/tables/{main_metrics,contrasts,wavelet_sensitivity,subgroups}.csv/.md and figures."""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from ec418.evaluation.metrics import (ranking_metrics, sens_at_spec_descriptive, subject_bootstrap,
                                      threshold_metrics)

N_BOOT = 2000
cfg = json.load(open("configs/protocol.json"))
pred = pd.concat([pd.read_csv(f"results/predictions/{t}_predictions.csv")
                  for t in sys.argv[1:] or ["main"]], ignore_index=True)
pt = pd.read_csv("results/tables/patients_audit.csv")[["patient_id", "systolic_grading", "systolic_pitch",
                                                       "systolic_timing", "n_recordings"]]
LABEL = {"B0": "B0 acoustic (MFCC etc.)", "B1": "B1 Vimalajeewa'25 wavelet", "W_stft": "STFT bands, whole",
         "W_wpd_db4": "WPD db4, whole", "A_stft": "STFT bands, cycle-aligned", "A_wpd_db4": "P1 WPD db4, cycle-aligned"}


def per_repeat_metrics(g):
    out = []
    for r, h in g.groupby("repeat"):
        y, s = h.y.values, h.score.values
        m = ranking_metrics(y, s)
        m["sens_at_spec80_test_roc"] = sens_at_spec_descriptive(y, s, 0.80)
        p80 = (s >= h.thr_spec80.values).astype(int)
        pw = (s >= h.thr_wacc.values).astype(int)
        t80 = threshold_metrics(y, p80, 0.5)
        tw = threshold_metrics(y, pw, 0.5)
        for k in ["accuracy", "sensitivity", "specificity", "precision", "f1_present", "macro_f1", "weighted_accuracy"]:
            m[f"spec80op_{k}"] = t80[k]
            m[f"waccop_{k}"] = tw[k]
        m["repeat"] = r
        out.append(m)
    return pd.DataFrame(out)


def averaged_scores(g):
    return g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean()


def auc_fn(df):
    return roc_auc_score(df.y, df.score)


rows, avg = [], {}
for (S, C), g in pred.groupby(["set", "clf"]):
    pr = per_repeat_metrics(g)
    a = averaged_scores(g); avg[(S, C)] = a
    lo, hi, _ = subject_bootstrap(a, auc_fn, n_boot=N_BOOT, seed=1)
    rec = dict(set=S, clf=C, n_patients=a.shape[0], auroc_avgscore=auc_fn(a), auroc_ci_lo=lo, auroc_ci_hi=hi)
    for c in pr.columns:
        if c != "repeat":
            rec[c] = pr[c].mean(); rec[c + "_sd"] = pr[c].std(ddof=1)
    rows.append(rec)
M = pd.DataFrame(rows)
dims = {}
for t in sys.argv[1:] or ["main"]:
    try:
        dims.update(json.load(open(f"experiments/{t}/dims.json")))
    except FileNotFoundError:
        pass
M["patient_dims"] = M.set.map(dims)
M.to_csv("results/tables/main_metrics_full.csv", index=False)

show = ["set", "clf", "patient_dims", "auroc", "auroc_sd", "auroc_avgscore", "auroc_ci_lo", "auroc_ci_hi", "auprc",
        "sens_at_spec80_test_roc", "spec80op_sensitivity", "spec80op_specificity", "spec80op_precision",
        "spec80op_f1_present", "spec80op_macro_f1", "spec80op_accuracy", "waccop_weighted_accuracy",
        "waccop_sensitivity", "waccop_specificity"]
T = M[show].sort_values(["clf", "auroc"], ascending=[True, False])
T.round(3).to_csv("results/tables/main_metrics.csv", index=False)
print(T.round(3).to_string(index=False))

# ---------------- pre-registered contrasts (RF primary; others descriptive) ----------------
CONTR = [("H2a", "A_wpd_db4", "A_stft"), ("H2b", "W_wpd_db4", "W_stft"), ("H3", "A_wpd_db4", "W_wpd_db4"),
         ("H4a", "A_wpd_db4", "B0"), ("H4b", "A_wpd_db4", "B1"), ("aux", "A_stft", "W_stft"), ("aux", "B1", "B0")]
crow = []
for C in sorted(pred.clf.unique()):
    for h, a, b in CONTR:
        if (a, C) not in avg or (b, C) not in avg:
            continue
        A, B = avg[(a, C)], avg[(b, C)]
        J = A.merge(B, on=["patient_id", "subject_id", "y"], suffixes=("_a", "_b"))
        d_point = roc_auc_score(J.y, J.score_a) - roc_auc_score(J.y, J.score_b)
        lo, hi, _ = subject_bootstrap(J, lambda df: roc_auc_score(df.y, df.score_a) - roc_auc_score(df.y, df.score_b),
                                      n_boot=N_BOOT, seed=2)
        fa = pred[(pred.set == a) & (pred.clf == C)].groupby(["repeat", "fold"]).apply(lambda x: roc_auc_score(x.y, x.score), include_groups=False)
        fb = pred[(pred.set == b) & (pred.clf == C)].groupby(["repeat", "fold"]).apply(lambda x: roc_auc_score(x.y, x.score), include_groups=False)
        pos = int(((fa - fb) > 0).sum())
        supported = (d_point >= 0.03) and (lo > 0) and (pos >= 18)
        crow.append(dict(hypothesis=h, clf=C, a=a, b=b, delta_auroc=d_point, ci_lo=lo, ci_hi=hi,
                         folds_positive=f"{pos}/{len(fa)}", verdict=("SUPPORTED" if supported else "NOT SUPPORTED") if C == "RF" else "descriptive"))
CT = pd.DataFrame(crow)
CT.round(4).to_csv("results/tables/contrasts.csv", index=False)
print("\n", CT.round(4).to_string(index=False))

# ---------------- subgroup: sensitivity by murmur grade / pitch (RF, spec80 operating point) ----
sg = []
for S in [s for s in LABEL if (s, "RF") in avg]:
    g = pred[(pred.set == S) & (pred.clf == "RF")].merge(pt, on="patient_id")
    g = g[g.y == 1]
    g["hit"] = (g.score >= g.thr_spec80).astype(int)
    for col in ["systolic_grading", "systolic_pitch"]:
        for v, h in g.groupby(col):
            sg.append(dict(set=S, variable=col, value=v, n_patients=h.patient_id.nunique(),
                           sensitivity_mean_over_repeats=h.groupby("repeat").hit.mean().mean()))
SG = pd.DataFrame(sg)
SG.round(3).to_csv("results/tables/subgroup_sensitivity_RF.csv", index=False)
print("\n", SG.pivot_table(index=["variable", "value"], columns="set", values="sensitivity_mean_over_repeats").round(3).to_string())

# ---------------- figures ----------------
fig, ax = plt.subplots(1, 2, figsize=(12, 5))
for S, lab in LABEL.items():
    if (S, "RF") not in avg:
        continue
    a = avg[(S, "RF")]
    f, t, _ = roc_curve(a.y, a.score)
    ax[0].plot(f, t, label=f"{lab} (AUC {roc_auc_score(a.y, a.score):.3f})", lw=1.4)
ax[0].plot([0, 1], [0, 1], "k:", lw=0.6); ax[0].axvline(0.2, color="grey", lw=0.5, ls="--")
ax[0].set_xlabel("1 - specificity (Absent)"); ax[0].set_ylabel("sensitivity (Present)")
ax[0].set_title("Patient-level ROC, WEKA RF, repeat-averaged OOF scores"); ax[0].legend(fontsize=7, loc="lower right")
rf = M[(M.clf == "RF") & M.set.isin(LABEL)].set_index("set").loc[[s for s in LABEL if s in set(M[M.clf == 'RF'].set)]]
yv = np.arange(len(rf))
ax[1].errorbar(rf.auroc_avgscore, yv, xerr=[rf.auroc_avgscore - rf.auroc_ci_lo, rf.auroc_ci_hi - rf.auroc_avgscore],
               fmt="o", capsize=3)
ax[1].set_yticks(yv); ax[1].set_yticklabels([LABEL[s] for s in rf.index], fontsize=8)
ax[1].set_xlabel("patient AUROC (95% subject-bootstrap CI)"); ax[1].set_title("RF, all five repeats averaged")
fig.tight_layout(); fig.savefig("results/figures/fig8_roc_auroc_ci_rf.png", dpi=150); plt.close(fig)
print("done")
