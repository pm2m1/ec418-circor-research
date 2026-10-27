"""S1 shortcut control (docs/PROTOCOL_V2_LOCKED.md "S1", tag s1-prereg): build W_*+SC and SC-only recording files.

Per outer fold (r, k), the E4 span detectors are re-derived exactly as scripts/26_e4_run.py builds them (same HSMM models
and seeds, same window features, same row order, same cross-fitting; no decoding is needed because the detectors only use
the HSMM state probabilities). Test patients' window predictions are checked identical to the saved E4 windows_test.csv.
Per recording: sc_pred_frac (share of full windows predicted annotated) and the no-aligned-features flag from the E4 wpd
feature file (identical across stft/wpd/wpds); per patient: sc_n_nofeat, sc_frac_nofeat attached to every recording.
Outputs data/interim/s1/features/r<r>_f<k>/rec_features_S1_{Wstft_SC,Wwpd_SC,SC_only}.csv (gitignored),
results/logs/s1_build_folds.csv.
usage: NPROC=10 python scripts/29_s1_build.py 0,1,2,3,4
"""
import os
import sys
import time
from multiprocessing import Pool

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import numpy as np
import pandas as pd

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.segmentation import lr_hsmm as H
from ec418.segmentation import spans as SP

DATA = "data/raw/circor_training_data"
HCACHE, WCACHE, E4F, OUT = "data/interim/e1b/springer", "data/interim/e4/windows", "data/interim/e4/features", "data/interim/s1/features"
RT = recording_table(load_patients(DATA))
FT = pd.read_csv("configs/folds_patient_level.csv")
RTB = RT[RT.patient_id.isin(FT.patient_id)]
META = ["rec_id", "patient_id", "subject_id", "location", "murmur"]
W = {"Wstft": pd.read_csv("data/processed/rec_features_W_stft.csv"), "Wwpd": pd.read_csv("data/processed/rec_features_W_wpd_db4.csv")}


def load_h(rec_id):
    return np.load(f"{HCACHE}/{rec_id}.npz")["F"]


def train_hsmm(patients, seed):                    # identical to scripts/21 and 26
    r = RT[RT.patient_id.isin(patients)]
    return H.train([load_h(x) for x in r.rec_id], [load_segmentation(t) for t in r.tsv], seed=seed)


def fold_job(rk):
    r, k = rk
    t0 = time.time()
    g = FT[(FT.repeat == r) & (FT.outer_fold == k)]
    tr, te = g[g.role == "train"], g[g.role == "test"]
    inner = sorted(tr.inner_fold.unique())
    hsmm = {"outer": train_hsmm(set(tr.patient_id), 1000 * r + 10 * k)}
    assign = {p: "outer" for p in te.patient_id}
    for i, ik in enumerate(inner):
        hsmm[f"inner{int(ik)}"] = train_hsmm(set(tr[tr.inner_fold != ik].patient_id), 1000 * r + 10 * k + i + 1)
        assign.update({p: f"inner{int(ik)}" for p in tr[tr.inner_fold == ik].patient_id})
    rec = {}
    for x in RTB.itertuples():                      # same order as scripts/26
        z = np.load(f"{WCACHE}/{x.rec_id}.npz")
        nw = z["X"].shape[0]
        X = np.column_stack([z["X"], SP.hsmm_window_confidence(H.state_probabilities(hsmm[assign[x.patient_id]], load_h(x.rec_id)), nw)])
        rec[x.rec_id] = dict(patient=x.patient_id, X=X, y=z["y"])

    def fit_on(patients):
        ids = [i for i, v in rec.items() if v["patient"] in patients]
        return SP.fit_detector(np.vstack([rec[i]["X"] for i in ids]), np.concatenate([rec[i]["y"] for i in ids]))
    det = {"outer": fit_on(set(tr.patient_id))}
    for ik in inner:
        det[f"inner{int(ik)}"] = fit_on(set(tr[tr.inner_fold != ik].patient_id))
    saved = pd.read_csv(f"{E4F}/r{r}_f{k}/windows_test.csv")
    rows, mine = [], []
    for rec_id, v in rec.items():
        d = det[assign[v["patient"]]]
        p = d.proba(v["X"])
        pred = (p >= d.threshold).astype(int)
        if assign[v["patient"]] == "outer":
            mine += [dict(rec_id=rec_id, window=w, pred=pred[w]) for w in range(len(p))]
        rows.append(dict(rec_id=rec_id, sc_pred_frac=float(pred.mean()) if pred.size else 0.0))
    chk = saved.merge(pd.DataFrame(mine), on=["rec_id", "window"], suffixes=("_e4", "_s1"))
    identical = bool(len(chk) == len(saved) == len(mine) and (chk.pred_e4 == chk.pred_s1).all())
    e4 = pd.read_csv(f"{E4F}/r{r}_f{k}/rec_features_E4_wpd.csv")
    e4["nofeat"] = e4[[c for c in e4.columns if c.startswith("wpdA_")]].isna().all(axis=1).astype(int)
    SC = e4[META + ["nofeat"]].merge(pd.DataFrame(rows), on="rec_id")
    pat = SC.groupby("patient_id").nofeat.agg(sc_n_nofeat="sum", sc_frac_nofeat="mean").reset_index()
    SC = SC.merge(pat, on="patient_id").drop(columns="nofeat")
    d = f"{OUT}/r{r}_f{k}"
    os.makedirs(d, exist_ok=True)
    SC.to_csv(f"{d}/rec_features_S1_SC_only.csv", index=False)
    sc_cols = ["rec_id", "sc_pred_frac", "sc_n_nofeat", "sc_frac_nofeat"]
    for name, Wdf in W.items():
        Wdf[Wdf.rec_id.isin(SC.rec_id)].merge(SC[sc_cols], on="rec_id").to_csv(f"{d}/rec_features_S1_{name}_SC.csv", index=False)
    return dict(repeat=r, fold=k, test_windows=len(saved), test_window_preds_identical_to_e4=identical,
                recordings=len(SC), seconds=time.time() - t0)


if __name__ == "__main__":
    jobs = [(r, k) for r in map(int, sys.argv[1].split(",")) for k in range(5)]
    with Pool(int(os.environ.get("NPROC", "2"))) as p:
        R = pd.DataFrame(p.map(fold_job, jobs, chunksize=1))
    R.to_csv("results/logs/s1_build_folds.csv", index=False)
    print(R.to_string(index=False))
    print("all test-window predictions identical to E4:", bool(R.test_window_preds_identical_to_e4.all()))
