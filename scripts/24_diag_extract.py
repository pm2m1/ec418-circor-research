"""Diagnostics D1-D3 (docs/PROTOCOL_V2_LOCKED.md "Diagnostics D1–D3"): DIAGNOSTICS ONLY - all use the expert
annotation of the test recordings at test time and are never deployable.

  d23        D2 = expert labels permuted only among expert-annotated columns (perm seed rule), 34 aligned features;
             D3 = whole-signal features (whole_features) on expert-annotated columns only.
             -> data/processed/diag/rec_features_D2_<rep>.csv, rec_features_D3_<rep>.csv
  d1 REPEATS D1 = the E1b fold-wise LR-HSMM labels (same training sets / seeds as scripts/21: test patients from the
             outer model, training patients cross-fitted) with expert label-0 columns set to 0, 34 aligned features.
             The outer-model decodes are checked against the saved E1b test decodes.
             -> data/interim/diag/features/r<r>_f<k>/rec_features_D1_<rep>.csv (gitignored),
                results/logs/diag_d1_folds.csv
Same preprocessing, energy maps, wpds kernel, column grid, aligned_features / whole_features as E1/E2/E1b.
usage: NPROC=10 python scripts/24_diag_extract.py d23 | d1 0,1,2,3,4
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
from scipy.signal import convolve

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import aligned_features, whole_features
from ec418.features.label_nulls import perm_within_annotated
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.segmentation import lr_hsmm as H
from ec418.wavelets.bands import column_labels, stft_energy_map, wpd_energy_map

DATA = "data/raw/circor_training_data"
CACHE = "data/interim/e1b/springer"
FS2, HOP = 2000, 16
KER = np.hanning(6)[1:-1]
KER = KER / KER.sum()
A_PREFIX = {"stft": "stftA", "wpd": "wpdA", "wpds": "wpdAs"}
W_PREFIX = {"stft": "stftW", "wpd": "wpdW", "wpds": "wpdWs"}
RT = recording_table(load_patients(DATA))
FT = pd.read_csv("configs/folds_patient_level.csv")
META = RT[["rec_id", "patient_id", "subject_id", "location", "murmur"]]


def maps_and_expert(wav, tsv):
    x2 = preprocess(load_wav(wav), 4000, FS2, 25.0, 900.0)
    Ew = wpd_energy_map(x2, "db4", 4)
    Es = stft_energy_map(x2, FS2, 4)
    assert Ew.shape[1] == Es.shape[1]
    maps = {"stft": Es, "wpd": Ew, "wpds": np.vstack([convolve(e, KER, mode="same") for e in Ew])}
    return x2, maps, column_labels(load_segmentation(tsv), Ew.shape[1], HOP, FS2)


def d23_one(args):
    rec_id, wav, tsv = args
    _, maps, lab = maps_and_expert(wav, tsv)
    d2 = perm_within_annotated(lab, rec_id)
    ann = lab > 0
    out = {}
    for rep, E in maps.items():
        out[("D2", rep)] = aligned_features(E, d2, A_PREFIX[rep])
        out[("D3", rep)] = whole_features(E[:, ann], W_PREFIX[rep]) if ann.any() else None
    return rec_id, out


def load_cache(rec_id):
    z = np.load(f"{CACHE}/{rec_id}.npz")
    return z["F"], z["ac"]


def train_on(patients, seed):                      # identical to scripts/21_e1b_run.py
    r = RT[RT.patient_id.isin(patients)]
    return H.train([load_cache(x)[0] for x in r.rec_id], [load_segmentation(t) for t in r.tsv], seed=seed)


def d1_fold(rk):
    r, k = rk
    t0 = time.time()
    g = FT[(FT.repeat == r) & (FT.outer_fold == k)]
    tr, te = g[g.role == "train"], g[g.role == "test"]
    models = {"outer": train_on(set(tr.patient_id), 1000 * r + 10 * k)}
    assign = {p: "outer" for p in te.patient_id}
    for i, ik in enumerate(sorted(tr.inner_fold.unique())):
        models[f"inner{int(ik)}"] = train_on(set(tr[tr.inner_fold != ik].patient_id), 1000 * r + 10 * k + i + 1)
        assign.update({p: f"inner{int(ik)}" for p in tr[tr.inner_fold == ik].patient_id})
    rows = {rep: [] for rep in A_PREFIX}
    n_check = n_same = 0
    for x in RT[RT.patient_id.isin(assign)].itertuples():
        m = assign[x.patient_id]
        x2, maps, lab = maps_and_expert(x.wav, x.tsv)
        F, ac = load_cache(x.rec_id)
        try:
            seg = H.states_to_segments(H.decode(models[m], F, ac)[0], x2.size / FS2)
        except Exception:
            seg = np.zeros((0, 3))
        if m == "outer":                            # must equal the saved E1b test decode
            saved = load_segmentation(f"data/interim/e1b/autoseg/r{r}/{x.rec_id}.tsv")
            saved = saved[saved[:, 2] > 0] if saved.size else saved.reshape(0, 3)
            n_check += 1
            n_same += int(saved.shape == seg.shape and np.allclose(saved, seg, atol=1e-6))
        auto = column_labels(seg, lab.size, HOP, FS2)
        auto[lab == 0] = 0                          # D1: keep HSMM timing only inside the expert spans
        for rep, E in maps.items():
            rows[rep].append(dict(rec_id=x.rec_id, **(aligned_features(E, auto, A_PREFIX[rep]) or {})))
    d = f"data/interim/diag/features/r{r}_f{k}"
    os.makedirs(d, exist_ok=True)
    for rep in A_PREFIX:
        META.merge(pd.DataFrame(rows[rep]), on="rec_id", how="inner").to_csv(f"{d}/rec_features_D1_{rep}.csv", index=False)
    return dict(repeat=r, fold=k, test_decodes_checked=n_check, identical_to_e1b=n_same, seconds=time.time() - t0)


if __name__ == "__main__":
    step = sys.argv[1]
    nproc = int(os.environ.get("NPROC", "2"))
    if step == "d23":
        os.makedirs("data/processed/diag", exist_ok=True)
        with Pool(nproc) as p:
            res = p.map(d23_one, list(zip(RT.rec_id, RT.wav, RT.tsv)), chunksize=8)
        for D in ("D2", "D3"):
            for rep in A_PREFIX:
                df = META.merge(pd.DataFrame([dict(rec_id=r, **(o[(D, rep)] or {})) for r, o in res]), on="rec_id", how="left")
                df.to_csv(f"data/processed/diag/rec_features_{D}_{rep}.csv", index=False)
                fc = [c for c in df.columns if c not in META.columns]
                print(f"{D}_{rep}: {df.shape}, recordings without features: {int(df[fc].isna().all(axis=1).sum())}")
    elif step == "d1":
        jobs = [(r, k) for r in map(int, sys.argv[2].split(",")) for k in range(5)]
        with Pool(nproc) as p:
            R = pd.DataFrame(p.map(d1_fold, jobs, chunksize=1))
        R.to_csv("results/logs/diag_d1_folds.csv", index=False)
        print(R.to_string(index=False))
        print("all outer decodes identical to E1b:", bool((R.test_decodes_checked == R.identical_to_e1b).all()))
    else:
        raise SystemExit(f"unknown step {step}")
