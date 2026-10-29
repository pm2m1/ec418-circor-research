"""POST-HOC, descriptive (not pre-registered): is the G1a external AUROC an age artefact?
ZCHSound CHD children are much younger than NORMAL ones. Reports AUROC of age alone, Spearman(score, age) and AUROC
within age tertiles for every G1a model (clean subset). -> results/tables/p3/g1a_posthoc_age_check.csv"""
import os
import sys
import pandas as pd
from sklearn.metrics import roc_auc_score
Z = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ZCH_DIR", "data/external/ZCHSound")) + "/"
c = pd.read_csv(Z + "Clean Heartsound Data Details.csv"); n = len(c)
c["chd"] = (c.diagnosis != "NORMAL").astype(int); c["age"] = c["age(days)"]; c["t"] = pd.qcut(c.age, 3, labels=False)
rows = [dict(model="age alone (days)", auroc_all=roc_auc_score(c.chd, c.age))]
for S in ["W_stft", "W_wpd_db4_smooth", "B0", "W_scat1"]:
    for v in ["all", "pv"]:
        for C in ["RF", "SMO"]:
            c["s"] = pd.read_csv(f"experiments/p3_external/arff/{S}_{v}_{C}.pred.csv").p_present.values[:n]
            r = dict(model=f"{S}|{C}|{v}", auroc_all=roc_auc_score(c.chd, c.s), spearman_score_age=c[["s", "age"]].corr("spearman").iloc[0, 1])
            for t, g in c.groupby("t"):
                r[f"auroc_age_tertile{t}"] = roc_auc_score(g.chd, g.s); r[f"n_t{t}"] = len(g); r[f"chd_t{t}"] = int(g.chd.sum())
            rows.append(r)
R = pd.DataFrame(rows); R.round(4).to_csv("results/tables/p3/g1a_posthoc_age_check.csv", index=False)
print(R.round(3).to_string(index=False))
