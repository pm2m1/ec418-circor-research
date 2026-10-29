"""G1a — external validation of CirCor-trained whole-signal models on ZCHSound (pre-registered, PROTOCOL_V3_PREREG.md).

Step A  ZCHSound whole-signal features (W_stft, W_wpd_db4_smooth, B0; W_scat1 comes from p3_01).
Step B  Train WEKA RF/SMO on all 874 CirCor binary patients (and a PV-location-only variant), score ZCHSound.
Step C  Metrics: AUROC any-CHD and per subtype vs NORMAL, participant bootstrap, H10a/H10b, CirCor-derived
        spec-80 threshold applied unchanged.
usage: .venv/bin/python scripts/p3_02_external_zch.py [ZCHSound dir]
"""
import json
import os
import subprocess
import sys
import zlib

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ec418.data.circor import load_patients, patient_table
from ec418.evaluation.metrics import threshold_for_specificity
from ec418.features.extract import aggregate_patient
from ec418.features.phase3 import load_any_wav, whole_signal_sets
from ec418.preprocessing.signal import preprocess
from ec418.weka.arff import CLASSIFIERS, build_runner, classpath, read_arff_header, write_arff

ZCH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ZCH_DIR", "data/external/ZCHSound")
OUTD = "experiments/p3_external"
META = ["rec_id", "patient_id", "subject_id", "location", "murmur"]
SETS = ["W_stft", "W_wpd_db4_smooth", "B0", "W_scat1"]
CLFS = ["RF", "SMO"]
os.makedirs(f"{OUTD}/arff", exist_ok=True)

# ---------------- Step A: ZCHSound features
def zch_labels():
    c = pd.read_csv(os.path.join(ZCH, "Clean Heartsound Data Details.csv"))[["fileName", "gender", "age(days)", "diagnosis"]]
    c["subset"], c["dir"] = "clean", "clean Heartsound Data"
    n = pd.read_csv(os.path.join(ZCH, "Noise Heartsound Data Details.csv"), sep=";", encoding="utf-8-sig")
    n["subset"], n["dir"] = "noisy", "Noise Heartsound Data Details"
    z = pd.concat([c, n], ignore_index=True)
    z["rec_id"] = z.fileName.str[:-4]
    z["chd"] = (z.diagnosis != "NORMAL").astype(int)
    return z

Z = zch_labels()
feat_path = "data/processed/zch_features_whole.csv"
if not os.path.exists(feat_path):
    rows = []
    for r in Z.itertuples():
        x, fs = load_any_wav(os.path.join(ZCH, r.dir, r.fileName))
        s = whole_signal_sets(preprocess(x, fs, 2000))
        row = {"rec_id": r.rec_id}
        for k in ["W_stft", "W_wpd_db4_smooth", "B0"]:
            row.update({f"{k}::{c}": v for c, v in s[k].items()})
        rows.append(row)
    pd.DataFrame(rows).to_csv(feat_path, index=False)
ZF = pd.read_csv(feat_path).set_index("rec_id")
ZS = pd.read_csv("data/processed/zch_features_W_scat1.csv").set_index("rec_id").drop(columns=["subset"])

def zch_matrix(S):
    if S == "W_scat1":
        X = ZS.copy()
    else:
        X = ZF[[c for c in ZF.columns if c.startswith(S + "::")]].copy()
        X.columns = [c.split("::", 1)[1] for c in X.columns]
    # patient vector = [median, max] over the single recording -> identical columns
    P = pd.concat([X.add_suffix("__med"), X.add_suffix("__max")], axis=1)
    return P.loc[Z.rec_id]

# ---------------- Step B: CirCor training matrices + WEKA
pt = patient_table(load_patients(os.environ.get("CIRCOR_DIR", "data/raw/circor_training_data")))
pt = pt[pt.murmur.isin(["Present", "Absent"])].copy()
pt["y"] = (pt.murmur == "Present").astype(int)

def circor_matrix(S, pv_only=False):
    rec = pd.read_csv(f"data/processed/rec_features_{S}.csv")
    if pv_only:
        rec = rec[rec.location == "PV"]
    cols = [c for c in rec.columns if c not in META]
    P = aggregate_patient(rec, cols)
    keep = pt[pt.patient_id.isin(P.index)]
    return P.loc[keep.patient_id], keep.y.values

jobs, meta = [], []
for variant in ["all", "pv"]:
    for S in SETS:
        Xtr, ytr = circor_matrix(S, variant == "pv")
        Xte = zch_matrix(S)
        cols = list(Xtr.columns)
        assert set(cols) == set(Xte.columns), f"{S}: column mismatch"
        base = f"{OUTD}/arff/{S}_{variant}"
        write_arff(base + "_train.arff", Xtr, ytr, f"{S}_train", cols)
        write_arff(base + "_zch.arff", Xte[cols], None, f"{S}_train", cols)
        assert read_arff_header(base + "_train.arff") == read_arff_header(base + "_zch.arff")
        for C in CLFS:
            cls, opts = CLASSIFIERS[C]
            out = f"{base}_{C}.pred.csv"
            jobs.append("\t".join([f"{S}|{C}|{variant}", base + "_train.arff", base + "_zch.arff", out, cls, opts]))
            meta.append(dict(set=S, clf=C, variant=variant, pred=out, n_train=len(ytr), n_pos=int(ytr.sum())))
with open(f"{OUTD}/jobs.tsv", "w") as f:
    f.write("\n".join(jobs) + "\n")
if not all(os.path.exists(m["pred"]) and len(pd.read_csv(m["pred"])) == len(Z) for m in meta):   # resume
    build_runner()
    with open("results/logs/p3_external_weka.log", "w") as log:
        subprocess.run(["java", "-Xmx3g", "-cp", classpath(), "WekaBatchRunner", f"{OUTD}/jobs.tsv"],
                       check=True, stdout=log, stderr=subprocess.STDOUT)

# ---------------- Step C: metrics
cv = pd.concat([pd.read_csv(f"results/predictions/{t}_predictions.csv")
                for t in ["main", "posthoc_smoothing", "p3_cv", "p3_cv_smo"] if os.path.exists(f"results/predictions/{t}_predictions.csv")])

def circor_threshold(S, C):
    g = cv[(cv.set == S) & (cv.clf == C)]
    if g.empty:
        return np.nan, np.nan
    a = g.groupby(["patient_id", "y"], as_index=False).score.mean()
    return threshold_for_specificity(a.y.values, a.score.values, 0.80), roc_auc_score(a.y, a.score)

rng = np.random.default_rng(20261028)
NB = 2000
from scipy.stats import rankdata


def fast_auc(y, s):
    """Mann-Whitney AUROC with mid-ranks for ties; numerically equal to sklearn roc_auc_score (checked below)."""
    y = np.asarray(y); r = rankdata(s)
    n1 = int(y.sum()); n0 = y.size - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


_t = np.random.default_rng(0)
for _ in range(20):
    _y = _t.integers(0, 2, 300); _s = np.round(_t.random(300), 2)
    assert abs(fast_auc(_y, _s) - roc_auc_score(_y, _s)) < 1e-12

def boot_auc(y, s, nb=NB):
    idx_pos, idx_neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    v = []
    for _ in range(nb):
        i = np.concatenate([rng.choice(idx_pos, idx_pos.size), rng.choice(idx_neg, idx_neg.size)])
        v.append(fast_auc(y[i], s[i]))
    return np.percentile(v, [2.5, 97.5])

def boot_diff(score, diag, a, b, nb=NB):
    """AUROC(a vs NORMAL) - AUROC(b vs NORMAL), resampling normals, a-cases and b-cases independently."""
    n, ia, ib = (np.flatnonzero(diag == d) for d in ("NORMAL", a, b))
    v = []
    for _ in range(nb):
        nn, aa, bb = rng.choice(n, n.size), rng.choice(ia, ia.size), rng.choice(ib, ib.size)
        def auc(cases):
            y = np.r_[np.zeros(nn.size), np.ones(cases.size)]
            return fast_auc(y, np.r_[score[nn], score[cases]])
        v.append(auc(aa) - auc(bb))
    return np.percentile(v, [2.5, 97.5])

res, sub_rows = [], []
for m in meta:
    pr = pd.read_csv(m["pred"])
    assert len(pr) == len(Z)
    Zs = Z.assign(score=pr.p_present.values)
    thr, auc_int = circor_threshold(m["set"], m["clf"]) if m["variant"] == "all" else (np.nan, np.nan)
    for subset in ["clean", "noisy"]:
        g = Zs[Zs.subset == subset]
        y, s, d = g.chd.values, g.score.values, g.diagnosis.values
        auc = roc_auc_score(y, s); lo, hi = boot_auc(y, s)
        row = dict(set=m["set"], clf=m["clf"], variant=m["variant"], subset=subset, n=len(g), n_chd=int(y.sum()),
                   circor_train_patients=m["n_train"], circor_internal_auroc=auc_int,
                   auroc_any_chd=auc, ci_lo=lo, ci_hi=hi, circor_thr_spec80=thr)
        if np.isfinite(thr):
            p = s >= thr
            row.update(sens_any_chd=float(p[y == 1].mean()), spec=float((~p[y == 0]).mean()))
        for dx in ["VSD", "PDA", "ASD", "PFO"]:
            k = (d == dx) | (d == "NORMAL")
            if (d == dx).sum() >= 5:
                yy = (d[k] == dx).astype(int)
                a = roc_auc_score(yy, s[k]); l, h = boot_auc(yy, s[k])
                srow = dict(set=m["set"], clf=m["clf"], variant=m["variant"], subset=subset, diagnosis=dx,
                            n=int((d == dx).sum()), auroc_vs_normal=a, ci_lo=l, ci_hi=h)
                if np.isfinite(thr):
                    srow["sens_at_circor_thr"] = float((s[d == dx] >= thr).mean())
                sub_rows.append(srow)
        if subset == "clean":
            for a_, b_ in [("VSD", "PFO"), ("VSD", "ASD"), ("PDA", "PFO")]:
                def A(dx):
                    k = (d == dx) | (d == "NORMAL")
                    return roc_auc_score((d[k] == dx).astype(int), s[k])
                l, h = boot_diff(s, d, a_, b_)
                row[f"d_{a_}_minus_{b_}"] = A(a_) - A(b_); row[f"d_{a_}_minus_{b_}_ci"] = f"[{l:.3f}, {h:.3f}]"
        res.append(row)

R = pd.DataFrame(res); SR = pd.DataFrame(sub_rows)
os.makedirs("results/tables/p3", exist_ok=True)
R.to_csv("results/tables/p3/g1a_external_any_chd.csv", index=False)
SR.to_csv("results/tables/p3/g1a_external_by_subtype.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(R.round(3).to_string(index=False))
print(SR.round(3).to_string(index=False))

# pre-registered verdicts (RF W_stft, all-CirCor model, clean set)
p = R[(R.set == "W_stft") & (R.clf == "RF") & (R.variant == "all") & (R.subset == "clean")].iloc[0]
def lo_of(ci): return float(ci.strip("[]").split(",")[0])
v = dict(H10a=dict(auroc=p.auroc_any_chd, ci=[p.ci_lo, p.ci_hi], verdict="SUPPORTED" if p.ci_lo > 0.5 else "NOT SUPPORTED"),
         H10b=dict(VSD_minus_PFO=p.d_VSD_minus_PFO, ci1=p.d_VSD_minus_PFO_ci, VSD_minus_ASD=p.d_VSD_minus_ASD, ci2=p.d_VSD_minus_ASD_ci,
                   verdict="SUPPORTED" if (lo_of(p.d_VSD_minus_PFO_ci) > 0 and lo_of(p.d_VSD_minus_ASD_ci) > 0) else "NOT SUPPORTED"))
json.dump(v, open("results/tables/p3/g1a_verdicts.json", "w"), indent=1, default=float)
print(json.dumps(v, indent=1, default=float))
