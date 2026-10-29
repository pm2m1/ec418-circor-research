"""Phase-3 G2: shortcut-free E4 (sandbox docs/PROTOCOL_V3_PREREG.md "G2" + amendment A1).

Per outer fold (r, k) exactly as scripts/26_e4_run.py (same HSMM models/seeds, window features, row order,
cross-fitting), then four window selections feed the same HSMM-label masking and 34 aligned features:
  E4R   E4 threshold selection (reproduction gate)          E4q   top-k windows by detector probability
  RQ    k random windows (seed crc32(rec_id))               SNRQ  top-k windows by feature 0 (no learning)
with k = min(n_win, max(1, floor(q*n_win + 0.5))), q = train_annotated_frac of the scoring detector.
SC_q (S1 variables recomputed for E4q) -> G2_Wstft_SCq, G2_Wwpd_SCq, G2_SCq_only.
Gate: detector parameters must equal results/logs/e4_models/r<r>_f<k>.json (max abs diff < 1e-8).
Outputs data/interim/g2/features/r<r>_f<k>/rec_features_<SET>.csv (gitignored), results/logs/p3_g2_build_folds.csv
usage: NPROC=2 python scripts/p3_g2_run.py 0,1,2,3,4
"""
import json
import os
import sys
import time
import zlib
from multiprocessing import Pool

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from scipy.signal import convolve

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import aligned_features
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.segmentation import lr_hsmm as H
from ec418.segmentation import spans as SP
from ec418.wavelets.bands import column_labels, stft_energy_map, wpd_energy_map

DATA = "data/raw/circor_training_data"
HCACHE, WCACHE, OUT = "data/interim/e1b/springer", "data/interim/e4/windows", "data/interim/g2/features"
FS2, HOP = 2000, 16
KER = np.hanning(6)[1:-1]
KER = KER / KER.sum()
A_PREFIX = {"stft": "stftA", "wpd": "wpdA", "wpds": "wpdAs"}
SELS = ["E4R", "E4q", "RQ", "SNRQ"]
RT = recording_table(load_patients(DATA))
FT = pd.read_csv("configs/folds_patient_level.csv")
RTB = RT[RT.patient_id.isin(FT.patient_id)]
META = RT[["rec_id", "patient_id", "subject_id", "location", "murmur"]]
METAC = list(META.columns)
W = {"Wstft": pd.read_csv("data/processed/rec_features_W_stft.csv"), "Wwpd": pd.read_csv("data/processed/rec_features_W_wpd_db4.csv")}


def load_h(rec_id):
    z = np.load(f"{HCACHE}/{rec_id}.npz")
    return z["F"], z["ac"]


def train_hsmm(patients, seed):                    # identical to scripts/21, 26, 29
    r = RT[RT.patient_id.isin(patients)]
    return H.train([load_h(x)[0] for x in r.rec_id], [load_segmentation(t) for t in r.tsv], seed=seed)


def n_keep(q, nw):
    return 0 if nw == 0 else int(min(nw, max(1, np.floor(q * nw + 0.5))))


def topk(score, k):
    sel = np.zeros(score.size, dtype=int)
    sel[np.argsort(-score, kind="stable")[:k]] = 1
    return sel


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
        m = hsmm[assign[x.patient_id]]
        F, ac = load_h(x.rec_id)
        z = np.load(f"{WCACHE}/{x.rec_id}.npz")
        try:
            seg = H.states_to_segments(H.decode(m, F, ac)[0], int(z["n_samples"]) / FS2)
        except Exception:
            seg = np.zeros((0, 3))
        nw = z["X"].shape[0]
        X = np.column_stack([z["X"], SP.hsmm_window_confidence(H.state_probabilities(m, F), nw)])
        rec[x.rec_id] = dict(patient=x.patient_id, seg=seg, X=X, y=z["y"], wav=x.wav)

    def fit_on(patients):
        ids = [i for i, v in rec.items() if v["patient"] in patients]
        return SP.fit_detector(np.vstack([rec[i]["X"] for i in ids]), np.concatenate([rec[i]["y"] for i in ids]))
    det = {"outer": fit_on(set(tr.patient_id))}
    for ik in inner:
        det[f"inner{int(ik)}"] = fit_on(set(tr[tr.inner_fold != ik].patient_id))
    # reproduction gate: detector parameters vs the saved E4 models
    saved = json.load(open(f"results/logs/e4_models/r{r}_f{k}.json"))
    gate = 0.0
    for n, d in det.items():
        s = saved[n]
        for a, b in [(d.lr.coef_[0], s["coef"]), ([d.lr.intercept_[0]], [s["intercept"]]), (d.scaler.mean_, s["scaler_mean"]),
                     (d.scaler.scale_, s["scaler_scale"]), ([d.threshold], [s["threshold"]])]:
            gate = max(gate, float(np.max(np.abs(np.asarray(a) - np.asarray(b)))))
    rows = {(sel, rep): [] for sel in SELS for rep in A_PREFIX}
    sc = []
    wrows = []
    for rec_id, v in rec.items():
        d = det[assign[v["patient"]]]
        p = d.proba(v["X"])
        nw = p.size
        kk = n_keep(d.train_annotated_frac, nw)
        rng = np.random.default_rng(zlib.crc32(rec_id.encode()))
        rand = np.zeros(nw, dtype=int)
        if kk:
            rand[rng.choice(nw, kk, replace=False)] = 1
        selections = {"E4R": (p >= d.threshold).astype(int), "E4q": topk(p, kk), "RQ": rand, "SNRQ": topk(v["X"][:, 0], kk)}
        if assign[v["patient"]] == "outer":
            wrows += [dict(rec_id=rec_id, window=w, proba=p[w], target=int(v["y"][w]),
                           **{s: int(selections[s][w]) for s in SELS}) for w in range(nw)]
        x2 = preprocess(load_wav(v["wav"]), 4000, FS2, 25.0, 900.0)
        Ew = wpd_energy_map(x2, "db4", 4)
        Es = stft_energy_map(x2, FS2, 4)
        maps = {"stft": Es, "wpd": Ew, "wpds": np.vstack([convolve(e, KER, mode="same") for e in Ew])}
        lab0 = column_labels(v["seg"], Ew.shape[1], HOP, FS2)
        for s, sel in selections.items():
            lab = lab0.copy()
            lab[~SP.column_mask(sel, lab.size)] = 0
            for rep, E in maps.items():
                rows[(s, rep)].append(dict(rec_id=rec_id, **(aligned_features(E, lab, A_PREFIX[rep]) or {})))
        sc.append(dict(rec_id=rec_id, sc_pred_frac=float(selections["E4q"].mean()) if nw else 0.0))
    out = f"{OUT}/r{r}_f{k}"
    os.makedirs(out, exist_ok=True)
    for (s, rep), rr in rows.items():
        META.merge(pd.DataFrame(rr), on="rec_id", how="inner").to_csv(f"{out}/rec_features_{s}_{rep}.csv", index=False)
    pd.DataFrame(wrows).to_csv(f"{out}/windows_test.csv", index=False)
    e4q = pd.read_csv(f"{out}/rec_features_E4q_wpd.csv")
    e4q["nofeat"] = e4q[[c for c in e4q.columns if c.startswith("wpdA_")]].isna().all(axis=1).astype(int)
    SC = e4q[METAC + ["nofeat"]].merge(pd.DataFrame(sc), on="rec_id")
    pat = SC.groupby("patient_id").nofeat.agg(sc_n_nofeat="sum", sc_frac_nofeat="mean").reset_index()
    SC = SC.merge(pat, on="patient_id").drop(columns="nofeat")
    SC.to_csv(f"{out}/rec_features_G2_SCq_only.csv", index=False)
    cols = ["rec_id", "sc_pred_frac", "sc_n_nofeat", "sc_frac_nofeat"]
    for name, Wdf in W.items():
        Wdf[Wdf.rec_id.isin(SC.rec_id)].merge(SC[cols], on="rec_id").to_csv(f"{out}/rec_features_G2_{name}_SCq.csv", index=False)
    return dict(repeat=r, fold=k, recordings=len(rec), detector_max_abs_diff_vs_e4=gate, gate_pass=gate < 1e-8,
                seconds=time.time() - t0)


if __name__ == "__main__":
    jobs = [(r, k) for r in map(int, sys.argv[1].split(",")) for k in range(5)]
    with Pool(int(os.environ.get("NPROC", "2"))) as p:
        R = pd.DataFrame(p.map(fold_job, jobs, chunksize=1))
    R.to_csv("results/logs/p3_g2_build_folds.csv", index=False)
    print(R.to_string(index=False))
    print("reproduction gate (detectors identical to E4):", bool(R.gate_pass.all()))
