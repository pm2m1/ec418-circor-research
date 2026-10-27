"""Phase-2 E4: automatic span selector + E1b LR-HSMM labels (docs/PROTOCOL_V2_LOCKED.md "E4", tag e4-prereg).

  cache        fold-independent window features 0-4 and expert window targets of every binary-task recording
               -> data/interim/e4/windows/<rec_id>.npz (gitignored)
  run REPEATS  per outer fold (r, k): the E1b HSMM models (same training sets / seeds; outer decodes checked identical to
               E1b) label every recording and give window feature 5; span detectors are cross-fitted exactly like the HSMM
               (test patients: detector on all training patients; training patients in inner fold i: detector on the
               others); HSMM labels are kept only in predicted-annotated windows; 34 aligned features (stft/wpd/wpds)
               -> data/interim/e4/features/r<r>_f<k>/rec_features_E4_<rep>.csv, .../windows_test.csv (gitignored),
                  results/logs/e4_models/r<r>_f<k>.json, results/logs/e4_run_folds.csv
  evaluate     detector vs expert mask on the test windows -> results/tables/e4_span_detector.csv,
               results/logs/e4_span_detector.json
usage: NPROC=10 python scripts/26_e4_run.py cache | run 0,1,2,3,4 | evaluate
"""
import json
import os
import sys
import time
from multiprocessing import Pool

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import convolve
from sklearn.metrics import roc_auc_score

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import aligned_features
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.segmentation import lr_hsmm as H
from ec418.segmentation import spans as SP
from ec418.wavelets.bands import column_labels, stft_energy_map, wpd_energy_map

DATA = "data/raw/circor_training_data"
HCACHE, WCACHE, FEAT = "data/interim/e1b/springer", "data/interim/e4/windows", "data/interim/e4/features"
FS2, HOP = 2000, 16
KER = np.hanning(6)[1:-1]
KER = KER / KER.sum()
A_PREFIX = {"stft": "stftA", "wpd": "wpdA", "wpds": "wpdAs"}
RT = recording_table(load_patients(DATA))
FT = pd.read_csv("configs/folds_patient_level.csv")
RTB = RT[RT.patient_id.isin(FT.patient_id)]
META = RT[["rec_id", "patient_id", "subject_id", "location", "murmur"]]


def cache_one(args):
    rec_id, wav, tsv = args
    raw, fs = sf.read(wav, dtype="int16")
    x2 = preprocess(load_wav(wav), 4000, FS2, 25.0, 900.0)
    n_cols = int(np.ceil(x2.size / HOP))
    nw = SP.n_windows(n_cols, raw.size)
    expert = column_labels(load_segmentation(tsv), n_cols, HOP, FS2)
    np.savez(f"{WCACHE}/{rec_id}.npz", X=SP.signal_window_features(raw, x2, n_cols),
             y=SP.window_targets(expert, nw), n_cols=n_cols)
    return rec_id


def load_h(rec_id):
    z = np.load(f"{HCACHE}/{rec_id}.npz")
    return z["F"], z["ac"]


def train_hsmm(patients, seed):                    # identical to scripts/21_e1b_run.py
    r = RT[RT.patient_id.isin(patients)]
    return H.train([load_h(x)[0] for x in r.rec_id], [load_segmentation(t) for t in r.tsv], seed=seed)


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
    # 1) HSMM labels + window features (feature 5 from the patient's HSMM model)
    rec = {}
    n_check = n_same = 0
    for x in RTB.itertuples():
        m = hsmm[assign[x.patient_id]]
        F, ac = load_h(x.rec_id)
        z = np.load(f"{WCACHE}/{x.rec_id}.npz")
        n_cols = int(z["n_cols"])
        try:
            seg = H.states_to_segments(H.decode(m, F, ac)[0], n_cols * HOP / FS2)
        except Exception:
            seg = np.zeros((0, 3))
        if assign[x.patient_id] == "outer":
            saved = load_segmentation(f"data/interim/e1b/autoseg/r{r}/{x.rec_id}.tsv")
            saved = saved[saved[:, 2] > 0] if saved.size else saved.reshape(0, 3)
            n_check += 1
            n_same += int(saved.shape == seg.shape and np.allclose(saved, seg, atol=1e-6))
        nw = z["X"].shape[0]
        X = np.column_stack([z["X"], SP.hsmm_window_confidence(H.state_probabilities(m, F), nw)])
        rec[x.rec_id] = dict(patient=x.patient_id, seg=seg, X=X, y=z["y"], n_cols=n_cols, wav=x.wav)
    # 2) span detectors, cross-fitted like the HSMM
    def fit_on(patients):
        ids = [i for i, v in rec.items() if v["patient"] in patients]
        return SP.fit_detector(np.vstack([rec[i]["X"] for i in ids]), np.concatenate([rec[i]["y"] for i in ids]))
    det = {"outer": fit_on(set(tr.patient_id))}
    for ik in inner:
        det[f"inner{int(ik)}"] = fit_on(set(tr[tr.inner_fold != ik].patient_id))
    # 3) labels inside predicted spans -> aligned features
    rows = {rep: [] for rep in A_PREFIX}
    wrows = []
    for rec_id, v in rec.items():
        d = det[assign[v["patient"]]]
        p = d.proba(v["X"])
        sel = (p >= d.threshold).astype(int)
        if assign[v["patient"]] == "outer":
            wrows += [dict(rec_id=rec_id, window=w, proba=p[w], pred=sel[w], target=int(v["y"][w])) for w in range(len(p))]
        x2 = preprocess(load_wav(v["wav"]), 4000, FS2, 25.0, 900.0)
        Ew = wpd_energy_map(x2, "db4", 4)
        Es = stft_energy_map(x2, FS2, 4)
        maps = {"stft": Es, "wpd": Ew, "wpds": np.vstack([convolve(e, KER, mode="same") for e in Ew])}
        lab = column_labels(v["seg"], Ew.shape[1], HOP, FS2)
        lab[~SP.column_mask(sel, lab.size)] = 0
        for rep, E in maps.items():
            rows[rep].append(dict(rec_id=rec_id, **(aligned_features(E, lab, A_PREFIX[rep]) or {})))
    out = f"{FEAT}/r{r}_f{k}"
    os.makedirs(out, exist_ok=True)
    for rep in A_PREFIX:
        META.merge(pd.DataFrame(rows[rep]), on="rec_id", how="inner").to_csv(f"{out}/rec_features_E4_{rep}.csv", index=False)
    pd.DataFrame(wrows).to_csv(f"{out}/windows_test.csv", index=False)
    json.dump({n: dict(coef=d.lr.coef_[0].tolist(), intercept=float(d.lr.intercept_[0]), scaler_mean=d.scaler.mean_.tolist(),
                       scaler_scale=d.scaler.scale_.tolist(), threshold=d.threshold, train_annotated_frac=d.train_annotated_frac,
                       train_predicted_frac=d.train_predicted_frac, n_train_windows=d.n_train_windows, features=SP.FEATURES)
               for n, d in det.items()}, open(f"results/logs/e4_models/r{r}_f{k}.json", "w"), indent=1)
    return dict(repeat=r, fold=k, recordings=len(rec), outer_decodes_checked=n_check, identical_to_e1b=n_same,
                seconds=time.time() - t0)


def evaluate():
    age = pd.read_csv("results/tables/v103_patients_audit.csv")[["patient_id", "age"]]
    W = []
    for d in sorted(os.listdir(FEAT)):
        r, k = (int(x[1:]) for x in d.split("_"))
        W.append(pd.read_csv(f"{FEAT}/{d}/windows_test.csv").assign(repeat=r, fold=k))
    W = pd.concat(W, ignore_index=True).merge(RT[["rec_id", "patient_id", "murmur"]], on="rec_id").merge(age, on="patient_id")
    W["age"] = W.age.fillna("missing")
    rows = []
    for r, g in W.groupby("repeat"):
        groups = [("all", "all", g)]
        if r == W.repeat.min():
            groups += [("murmur", v, h) for v, h in g.groupby("murmur")] + [("age", v, h) for v, h in g.groupby("age")]
        for grp, val, h in groups:
            rows.append(dict(repeat=r, group=grp, value=val, n_windows=len(h), n_recordings=h.rec_id.nunique(),
                             window_auroc=roc_auc_score(h.target, h.proba) if h.target.nunique() > 1 else np.nan,
                             accuracy=float((h.pred == h.target).mean()), expert_annotated_frac=float(h.target.mean()),
                             predicted_annotated_frac=float(h.pred.mean()),
                             sensitivity=float(h.pred[h.target == 1].mean()), specificity=float(1 - h.pred[h.target == 0].mean())))
    T = pd.DataFrame(rows)
    T.to_csv("results/tables/e4_span_detector.csv", index=False)
    a = T[(T.repeat == W.repeat.min()) & (T.group == "all")].iloc[0]
    json.dump(dict(primary_repeat=int(W.repeat.min()), window_auroc=a.window_auroc, accuracy=a.accuracy,
                   expert_annotated_frac=a.expert_annotated_frac, predicted_annotated_frac=a.predicted_annotated_frac,
                   by_repeat=T[T.group == "all"][["repeat", "window_auroc", "accuracy"]].to_dict("records")),
              open("results/logs/e4_span_detector.json", "w"), indent=2, default=float)
    pd.set_option("display.width", 220)
    print(T.round(3).to_string(index=False))


if __name__ == "__main__":
    step = sys.argv[1]
    nproc = int(os.environ.get("NPROC", "2"))
    os.makedirs(WCACHE, exist_ok=True)
    os.makedirs("results/logs/e4_models", exist_ok=True)
    if step == "cache":
        with Pool(nproc) as p:
            print("cached", len(p.map(cache_one, list(zip(RTB.rec_id, RTB.wav, RTB.tsv)), chunksize=8)))
    elif step == "run":
        jobs = [(r, k) for r in map(int, sys.argv[2].split(",")) for k in range(5)]
        with Pool(nproc) as p:
            R = pd.DataFrame(p.map(fold_job, jobs, chunksize=1))
        R.to_csv("results/logs/e4_run_folds.csv", index=False)
        print(R.to_string(index=False))
        print("all outer HSMM decodes identical to E1b:", bool((R.outer_decodes_checked == R.identical_to_e1b).all()))
    elif step == "evaluate":
        evaluate()
    else:
        raise SystemExit(f"unknown step {step}")
