"""Phase-3 G3a: conditioning-availability gaps from SAVED Phase-2 predictions (no new runs).
Oracle = E2_<rep>_true (expert labels, v1.0.3); estimated = E1_<rep>_auto, E1b_<rep>_auto, E4_<rep>; random = E2 perm / shift.
Delta_oe = AUROC(oracle) - AUROC(estimated), Delta_or = AUROC(oracle) - AUROC(random); RF decides, SMO descriptive.
Repeat-averaged AUROC, subject bootstrap 2000 (seed 2) on paired differences. E4q_<rep> (pre-registered G3a row) is read
from the Mac G2 run, results/predictions/p3_g2_predictions.csv.
-> results/tables/p3/g3a_conditioning_gaps.csv"""
import os
import pandas as pd
from sklearn.metrics import roc_auc_score
from ec418.evaluation.metrics import subject_bootstrap
P = pd.concat([pd.read_csv(f"results/predictions/{t}_predictions.csv") for t in ["e1", "e1b", "e2", "e4"]], ignore_index=True)
G2 = pd.read_csv("results/predictions/p3_g2_predictions.csv")
P = pd.concat([P, G2[G2.set.str.startswith("E4q_")]], ignore_index=True)
avg = {k: g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean() for k, g in P.groupby(["set", "clf"])}
rows = []
for C in ["RF", "SMO"]:
    for rep in ["stft", "wpd", "wpds"]:
        o = f"E2_{rep}_true"
        for kind, e in [("oe", f"E1_{rep}_auto"), ("oe", f"E1b_{rep}_auto"), ("oe", f"E4_{rep}"), ("oe", f"E4q_{rep}"), ("or", f"E2_{rep}_perm"), ("or", f"E2_{rep}_shift")]:
            J = avg[(o, C)].merge(avg[(e, C)], on=["patient_id", "subject_id", "y"], suffixes=("_o", "_e"))
            f = lambda d: roc_auc_score(d.y, d.score_o) - roc_auc_score(d.y, d.score_e)
            lo, hi, _ = subject_bootstrap(J, f, n_boot=2000, seed=2)
            rows.append(dict(clf=C, rep=rep, gap=f"Delta_{kind}", oracle=o, other=e, auroc_oracle=roc_auc_score(J.y, J.score_o),
                             auroc_other=roc_auc_score(J.y, J.score_e), delta=f(J), ci_lo=lo, ci_hi=hi))
R = pd.DataFrame(rows); os.makedirs("results/tables/p3", exist_ok=True); R.round(4).to_csv("results/tables/p3/g3a_conditioning_gaps.csv", index=False)
print(R[R.clf == "RF"].round(3).to_string(index=False))
