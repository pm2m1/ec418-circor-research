"""Patient-level, subject-grouped evaluation of all feature sets with WEKA classifiers.

For every feature set x repeat x outer fold:
  * write outer train/test ARFF (+ ids sidecars) and 3 inner train/test pairs (training part only)
  * WEKA trains on train.arff and scores test.arff (one JVM per job list, no WEKA row-wise CV)
  * inner out-of-fold scores -> thresholds (spec>=0.80, max weighted accuracy) -> applied to outer
Outputs results/predictions/<tag>_predictions.csv (one row per set/clf/repeat/patient).

usage: python scripts/06_run_patient_level_weka.py TAG SET[,SET..] CLF[,CLF..] [NJVM]
       env FEATDIR=<dir> reads recording features from <dir> instead of data/processed
"""
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd

from ec418.evaluation.metrics import threshold_for_specificity, threshold_max_weighted_accuracy
from ec418.features.extract import aggregate_patient
from ec418.weka.arff import CLASSIFIERS, build_runner, classpath, read_arff_header, write_arff

# FEATDIR: folder holding the rec_features_*.csv (default the committed data/processed)
FEATDIR = os.environ.get("FEATDIR", "data/processed")
META = ["rec_id", "patient_id", "subject_id", "location", "murmur"]
SETFILE = {
    "B0": "rec_features_B0.csv", "B1": "rec_features_B1.csv",
    "W_stft": "rec_features_W_stft.csv", "A_stft": "rec_features_A_stft.csv",
}
for w in ["db4", "db6", "sym8", "coif3"]:
    SETFILE[f"W_wpd_{w}"] = f"rec_features_W_wpd_{w}.csv"
    SETFILE[f"A_wpd_{w}"] = f"rec_features_A_wpd_{w}.csv"
SETFILE["W_wpd_db4_smooth"] = "rec_features_W_wpd_db4_smooth.csv"
SETFILE["A_wpd_db4_smooth"] = "rec_features_A_wpd_db4_smooth.csv"
for rep in ["stft", "wpd", "wpds"]:          # Phase-2 E2 (scripts/15_e2_extract_label_nulls.py)
    for cond in ["true", "perm", "shift"]:
        SETFILE[f"E2_{rep}_{cond}"] = f"e2/rec_features_E2_{rep}_{cond}.csv"
    SETFILE[f"E1_{rep}_auto"] = f"e1/rec_features_E1_{rep}_auto.csv"   # Phase-2 E1 (scripts/19)
    # Phase-2 E1b (scripts/21): fold-specific features, {r}/{k} = repeat / outer fold, path relative to the repo
    SETFILE[f"E1b_{rep}_auto"] = "data/interim/e1b/features/r{r}_f{k}/rec_features_E1b_" + rep + "_auto.csv"
    # diagnostics D1-D3 (scripts/24; diagnostics only, use the expert annotation at test time)
    SETFILE[f"D1_{rep}"] = "data/interim/diag/features/r{r}_f{k}/rec_features_D1_" + rep + ".csv"
    SETFILE[f"D2_{rep}"] = f"diag/rec_features_D2_{rep}.csv"
    SETFILE[f"D3_{rep}"] = f"diag/rec_features_D3_{rep}.csv"
B1_USED = ["b1_entropy_cv", "b1_slope", "b1_Hurst_spectral_mode", "b1_LeftSlope", "b1_RightSlope",
           "b1_LeftTangent", "b1_LeftTangentPoint", "b1_RightTangentPoint"]


def fold_specific(set_name: str) -> bool:
    return "{r}" in SETFILE[set_name]


def patient_matrix(set_name: str, patients: pd.DataFrame, r=None, k=None) -> pd.DataFrame:
    path = SETFILE[set_name].format(r=r, k=k)
    rec = pd.read_csv(path if path.startswith("data/") else os.path.join(FEATDIR, path))
    cols = B1_USED if set_name == "B1" else [c for c in rec.columns if c not in META]
    P = aggregate_patient(rec, cols)
    P = patients[["patient_id"]].merge(P, left_on="patient_id", right_index=True, how="left").set_index("patient_id")
    return P


def _valid_pred(path, n_rows):
    if not os.path.exists(path):
        return False
    try:
        d = pd.read_csv(path)
    except Exception:
        return False
    return len(d) == n_rows and d["actual"].notna().all() and d["p_present"].notna().all()


def main():
    tag, sets, clfs = sys.argv[1], sys.argv[2].split(","), sys.argv[3].split(",")
    njvm = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    ft = pd.read_csv("configs/folds_patient_level.csv")
    patients = ft[["patient_id", "subject_id", "y"]].drop_duplicates().sort_values("patient_id").reset_index(drop=True)
    wdir = f"experiments/{tag}/arff"
    os.makedirs(wdir, exist_ok=True)
    jobs, meta = [], []
    pair_idx, n_skipped = 0, 0
    dims = {}
    for S in sets:
        if not fold_specific(S):
            P = patient_matrix(S, patients)
            feats = list(P.columns)
            dims[S] = len(feats)
            miss = P.isna().all(axis=1).sum()
            print(f"{S}: {len(feats)} patient features, patients with all-missing: {miss}", flush=True)
        for (r, k), g in ft.groupby(["repeat", "outer_fold"]):
            if fold_specific(S):           # features differ per outer fold (fold-trained segmenter)
                P = patient_matrix(S, patients, r, k)
                feats = list(P.columns)
                dims[S] = len(feats)
                print(f"{S} r{r} f{k}: {len(feats)} patient features, patients with all-missing: "
                      f"{P.isna().all(axis=1).sum()}", flush=True)
            tr = g[g.role == "train"]; te = g[g.role == "test"]
            pairs = [("outer", tr, te)]
            for ik in sorted(tr.inner_fold.unique()):
                pairs.append((f"inner{ik}", tr[tr.inner_fold != ik], tr[tr.inner_fold == ik]))
            for name, a, b in pairs:
                assert not set(a.subject_id) & set(b.subject_id)
                base = f"{wdir}/{S}_r{r}_f{k}_{name}"
                for part, df in (("train", a), ("test", b)):
                    X = P.loc[df.patient_id.values]
                    write_arff(f"{base}_{part}.arff", X, df.y.values, f"{S}_{part}", feats)
                    df[["patient_id", "subject_id", "y"]].to_csv(f"{base}_{part}.ids.csv", index=False)
                assert read_arff_header(f"{base}_train.arff") == read_arff_header(f"{base}_test.arff")
                pair_idx += 1
                for C in clfs:
                    cls, opts = CLASSIFIERS[C]
                    out = f"{base}_{C}.pred.csv"
                    meta.append(dict(set=S, clf=C, repeat=r, fold=k, part=name, pred=out, ids=f"{base}_test.ids.csv"))
                    if _valid_pred(out, len(b)):   # resume: finished, complete prediction file
                        n_skipped += 1
                        continue
                    jobs.append((pair_idx, "\t".join([f"{S}|{C}|{r}|{k}|{name}", f"{base}_train.arff", f"{base}_test.arff", out, cls, opts])))
    json.dump(dims, open(f"experiments/{tag}/dims.json", "w"))
    print(f"jobs to run: {len(jobs)}, already complete (resumed): {n_skipped}", flush=True)
    # distribute by train/test PAIR (all classifiers of a pair on one JVM) -> balanced classifier mix
    build_runner()
    procs = []
    t0 = time.time()
    for j in range(njvm):
        jf = f"experiments/{tag}/jobs_{j}.tsv"
        with open(jf, "w") as f:
            f.write("\n".join(line for pi, line in jobs if pi % njvm == j) + "\n")
        log = open(f"results/logs/weka_{tag}_jvm{j}.log", "w")
        cmd = ["java", "-Xmx2g", "-cp", classpath(), "WekaBatchRunner", jf]
        log.write("$ " + " ".join(cmd) + "\n"); log.flush()
        procs.append((subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT), log))
    for p, log in procs:
        rc = p.wait(); log.close()
        if rc != 0:
            raise SystemExit(f"WEKA JVM failed (rc={rc}); see results/logs/weka_{tag}_jvm*.log")
    print(f"WEKA: {len(jobs)} jobs in {time.time() - t0:.0f}s", flush=True)

    # collect predictions, derive thresholds from inner OOF, apply to outer
    M = pd.DataFrame(meta)
    rows = []
    for (S, C, r, k), g in M.groupby(["set", "clf", "repeat", "fold"]):
        parts = {}
        for m in g.itertuples():
            pr = pd.read_csv(m.pred); ids = pd.read_csv(m.ids)
            assert len(pr) == len(ids)
            assert (pr.actual.map({"Present": 1, "Absent": 0}).values == ids.y.values).all(), "row/ID misalignment"
            parts[m.part] = ids.assign(score=pr.p_present.values)
        inner = pd.concat([v for n, v in parts.items() if n.startswith("inner")])
        assert inner.patient_id.is_unique
        t_spec = threshold_for_specificity(inner.y.values, inner.score.values, 0.80)
        t_wacc = threshold_max_weighted_accuracy(inner.y.values, inner.score.values)
        o = parts["outer"].assign(set=S, clf=C, repeat=r, fold=k, thr_spec80=t_spec, thr_wacc=t_wacc)
        rows.append(o)
    pred = pd.concat(rows, ignore_index=True)
    pred.to_csv(f"results/predictions/{tag}_predictions.csv", index=False)
    # timing from WEKA logs
    tim = []
    import glob as _glob
    for lf in sorted(_glob.glob(f"results/logs/**/weka_{tag}_jvm*.log", recursive=True)):
        for line in open(lf):
            mm = re.match(r"job (\S+) ok train=(\d+) test=(\d+) fit_s=([\d.]+) predict_s=([\d.]+)", line)
            if mm:
                S, C, r, k, part = mm.group(1).split("|")
                tim.append(dict(set=S, clf=C, part=part, n_train=int(mm.group(2)), n_test=int(mm.group(3)),
                                fit_s=float(mm.group(4)), predict_s=float(mm.group(5))))
    pd.DataFrame(tim).to_csv(f"results/tables/{tag}_weka_timing.csv", index=False)
    print("saved", pred.shape)


if __name__ == "__main__":
    main()
