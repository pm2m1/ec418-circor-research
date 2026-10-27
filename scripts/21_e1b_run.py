"""Phase-2 E1b: LR-HSMM segmentation (ec418.segmentation.lr_hsmm), fold-wise without leakage, + aligned features.

Pre-registered in docs/PROTOCOL_V2_LOCKED.md "E1b" (tag e1b-prereg). Steps:
  cache          Springer features + heart-rate autocorrelation of every recording (fold-independent; audio only)
                 -> data/interim/e1b/springer/<rec_id>.npz
  time [N=50]    train the repeat-0/fold-0 outer segmenter, decode N of its test recordings and extract their
                 aligned features; estimate the full 25-fold cost -> results/logs/e1b_timing.json
  run REPEATS    for every outer fold of the given repeats (e.g. 0,1,2,3,4): segmenter trained on the fold's training
                 patients decodes its test patients; training patients are decoded by cross-fitting over the 3 inner
                 folds; aligned features (stft / wpd / wpds, same extractor as E1/E2) of all binary-task recordings
                 -> data/interim/e1b/features/r<r>_f<k>/rec_features_E1b_<rep>_auto.csv (gitignored),
                    data/interim/e1b/autoseg/r<r>/<rec_id>.tsv (test decodes), results/logs/e1b_models/r<r>_f<k>.json
  unknown        one segmenter on all 874 binary-task patients decodes the Unknown-murmur recordings (report only)
  evaluate       segmentation metrics as E1 on the test decodes -> results/tables/e1b_segmentation_*.csv,
                 results/logs/e1b_segmentation.json
usage: NPROC=10 python scripts/21_e1b_run.py STEP [ARG]
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
from scipy.signal import convolve

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import aligned_features
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.segmentation import lr_hsmm as H
from ec418.segmentation.autoseg import write_tsv
from ec418.segmentation.evaluation import evaluate_recording, summarise
from ec418.wavelets.bands import column_labels, stft_energy_map, wpd_energy_map

DATA = "data/raw/circor_training_data"
ROOT = "data/interim/e1b"
CACHE, FEAT, SEG = f"{ROOT}/springer", f"{ROOT}/features", f"{ROOT}/autoseg"
FS2, HOP = 2000, 16
KER = np.hanning(6)[1:-1]
KER = KER / KER.sum()
REPS = {"stft": "stftA", "wpd": "wpdA", "wpds": "wpdAs"}
AC_LAGS = 3001                       # 3 s of autocorrelation lags at 1 kHz (>= MAX_D at 50 Hz)
F1_FLAG = 0.70

RT = recording_table(load_patients(DATA))
FT = pd.read_csv("configs/folds_patient_level.csv")


def cache_one(args):
    rec_id, wav = args
    F, ac = H.springer_features(load_wav(wav))
    np.savez(f"{CACHE}/{rec_id}.npz", F=F, ac=ac[:AC_LAGS])
    return rec_id


def load_cache(rec_id):
    z = np.load(f"{CACHE}/{rec_id}.npz")
    return z["F"], z["ac"]


def train_on(patients, seed):
    r = RT[RT.patient_id.isin(patients)]
    feats = [load_cache(x)[0] for x in r.rec_id]
    return H.train(feats, [load_segmentation(t) for t in r.tsv], seed=seed)


def decode_and_features(model, rec_id, wav):
    """Decode one recording (audio only) and compute its 34 aligned features per representation."""
    x2 = preprocess(load_wav(wav), 4000, FS2, 25.0, 900.0)
    dur = x2.size / FS2
    try:
        F, ac = load_cache(rec_id)
        qt, info = H.decode(model, F, ac)
        seg, failure = H.states_to_segments(qt, dur), ""
    except Exception as e:  # recorded, never silently dropped
        seg, info, failure = np.zeros((0, 3)), {}, repr(e)
    Ew = wpd_energy_map(x2, "db4", 4)
    Es = stft_energy_map(x2, FS2, 4)
    assert Ew.shape[1] == Es.shape[1]
    maps = {"stft": Es, "wpd": Ew, "wpds": np.vstack([convolve(e, KER, mode="same") for e in Ew])}
    lab = column_labels(seg, Ew.shape[1], HOP, FS2)
    feats = {rep: aligned_features(E, lab, REPS[rep]) for rep, E in maps.items()}
    return seg, dur, x2.size, feats, dict(info, failure=failure)


def fold_job(rk):
    r, k = rk
    t0 = time.time()
    g = FT[(FT.repeat == r) & (FT.outer_fold == k)]
    tr, te = g[g.role == "train"], g[g.role == "test"]
    models = {"outer": train_on(set(tr.patient_id), 1000 * r + 10 * k)}
    assign = {p: "outer" for p in te.patient_id}
    for i, ik in enumerate(sorted(tr.inner_fold.unique())):
        name = f"inner{int(ik)}"
        models[name] = train_on(set(tr[tr.inner_fold != ik].patient_id), 1000 * r + 10 * k + i + 1)
        assign.update({p: name for p in tr[tr.inner_fold == ik].patient_id})
    recs = RT[RT.patient_id.isin(assign)]
    os.makedirs(f"{FEAT}/r{r}_f{k}", exist_ok=True)
    os.makedirs(f"{SEG}/r{r}", exist_ok=True)
    rows = {rep: [] for rep in REPS}
    log = []
    for x in recs.itertuples():
        m = assign[x.patient_id]
        seg, dur, n2k, feats, info = decode_and_features(models[m], x.rec_id, x.wav)
        if m == "outer":
            write_tsv(f"{SEG}/r{r}/{x.rec_id}.tsv", seg, dur)
        for rep in REPS:
            rows[rep].append(dict(rec_id=x.rec_id, **(feats[rep] or {})))
        log.append(dict(rec_id=x.rec_id, repeat=r, fold=k, model=m, n_samples=n2k,
                        aligned=feats["wpd"] is not None, **info))
    meta = RT[["rec_id", "patient_id", "subject_id", "location", "murmur"]]
    for rep in REPS:
        meta.merge(pd.DataFrame(rows[rep]), on="rec_id", how="inner").to_csv(
            f"{FEAT}/r{r}_f{k}/rec_features_E1b_{rep}_auto.csv", index=False)
    pd.DataFrame(log).to_csv(f"{FEAT}/r{r}_f{k}/decode_log.csv", index=False)
    json.dump({n: m.params for n, m in models.items()}, open(f"results/logs/e1b_models/r{r}_f{k}.json", "w"),
              indent=1, default=float)
    return dict(repeat=r, fold=k, n_recordings=len(recs), seconds=time.time() - t0,
                failures=int(sum(1 for l in log if l["failure"])))


def step_time(n=50):
    t0 = time.time()
    g = FT[(FT.repeat == 0) & (FT.outer_fold == 0)]
    m = train_on(set(g[g.role == "train"].patient_id), 0)
    t_train = time.time() - t0
    te = RT[RT.patient_id.isin(g[g.role == "test"].patient_id)].head(n)
    t0 = time.time()
    for x in te.itertuples():
        decode_and_features(m, x.rec_id, x.wav)
    per_rec = (time.time() - t0) / len(te)
    n_bin = int(RT.patient_id.isin(FT.patient_id).sum())
    nproc = int(os.environ.get("NPROC", "2"))
    full_cpu = 25 * (4 * t_train + n_bin * per_rec)
    est = dict(n_timed=len(te), train_s=t_train, decode_plus_features_s_per_recording=per_rec,
               binary_task_recordings=n_bin, folds=25, trainings_per_fold=4, nproc=nproc,
               full_25_fold_cpu_h=full_cpu / 3600, full_25_fold_wall_h_estimate=full_cpu / nproc / 3600,
               exceeds_4h=bool(full_cpu / nproc / 3600 > 4))
    json.dump(est, open("results/logs/e1b_timing.json", "w"), indent=2)
    print(json.dumps(est, indent=2))


def step_unknown():
    m = train_on(set(FT.patient_id), 9999)
    unk = RT[~RT.patient_id.isin(FT.patient_id)]
    os.makedirs(f"{SEG}/unknown", exist_ok=True)
    log = []
    for x in unk.itertuples():
        seg, dur, n2k, _, info = decode_and_features(m, x.rec_id, x.wav)
        write_tsv(f"{SEG}/unknown/{x.rec_id}.tsv", seg, dur)
        log.append(dict(rec_id=x.rec_id, repeat=-1, fold=-1, model="all_binary", n_samples=n2k, **info))
    pd.DataFrame(log).to_csv(f"{ROOT}/unknown_decode_log.csv", index=False)
    json.dump(m.params, open("results/logs/e1b_models/unknown_all_binary.json", "w"), indent=1, default=float)
    print("unknown recordings decoded:", len(log), "failures:", sum(1 for l in log if l["failure"]))


def step_evaluate():
    age = pd.read_csv("results/tables/v103_patients_audit.csv")[["patient_id", "age"]]
    logs = [pd.read_csv(f"{FEAT}/{d}/decode_log.csv") for d in sorted(os.listdir(FEAT))]
    L = pd.concat(logs, ignore_index=True)
    L = L[L.model == "outer"]
    if os.path.exists(f"{ROOT}/unknown_decode_log.csv"):
        U = pd.read_csv(f"{ROOT}/unknown_decode_log.csv")
        L = pd.concat([L, pd.concat([U.assign(repeat=r) for r in sorted(L.repeat.unique())])], ignore_index=True)
    L["failure"] = L.failure.astype(object).fillna("")
    L = L.merge(RT[["rec_id", "patient_id", "murmur", "tsv"]], on="rec_id")
    ev = []
    for x in L.itertuples():
        d = f"{SEG}/r{x.repeat}" if x.model == "outer" else f"{SEG}/unknown"
        ev.append(evaluate_recording(load_segmentation(x.tsv), load_segmentation(f"{d}/{x.rec_id}.tsv"), x.n_samples))
    L = pd.concat([L.reset_index(drop=True), pd.DataFrame(ev)], axis=1).merge(age, on="patient_id", how="left")
    L["age"] = L.age.fillna("missing")
    L.drop(columns=["tsv"]).to_csv("results/tables/e1b_segmentation_per_recording.csv", index=False)
    rows = []
    for r, g in L.groupby("repeat"):
        groups = summarise(g) + (summarise(g, "murmur") + summarise(g, "age") if r == L.repeat.min() else [])
        rows += [dict(repeat=r, **x) for x in groups]
    T = pd.DataFrame(rows)
    T.to_csv("results/tables/e1b_segmentation_summary.csv", index=False)
    a = T[(T.repeat == L.repeat.min()) & (T.group == "all")].iloc[0]
    out = dict(primary_repeat=int(L.repeat.min()), repeats=sorted(int(x) for x in L.repeat.unique()),
               n_recordings_primary=int(a.n_recordings), s1_f1=a.s1_f1, s2_f1=a.s2_f1,
               frame_accuracy_4state=a.frame_accuracy_4state, failure_frac=a.failure_frac,
               low_quality_segmentation=bool(a.s1_f1 < F1_FLAG or a.s2_f1 < F1_FLAG),
               overall_by_repeat=T[T.group == "all"][["repeat", "s1_f1", "s2_f1", "frame_accuracy_4state"]].to_dict("records"))
    json.dump(out, open("results/logs/e1b_segmentation.json", "w"), indent=2, default=float)
    pd.set_option("display.width", 250)
    print(T.round(3).to_string(index=False))
    print(json.dumps(out, indent=2, default=float))


if __name__ == "__main__":
    step, arg = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs("results/logs/e1b_models", exist_ok=True)
    nproc = int(os.environ.get("NPROC", "2"))
    if step == "cache":
        with Pool(nproc) as p:
            done = p.map(cache_one, list(zip(RT.rec_id, RT.wav)), chunksize=8)
        print("cached", len(done))
    elif step == "time":
        step_time(int(arg or 50))
    elif step == "run":
        jobs = [(r, k) for r in map(int, arg.split(",")) for k in range(5)]
        t0 = time.time()
        with Pool(nproc) as p:
            res = p.map(fold_job, jobs, chunksize=1)
        R = pd.DataFrame(res)
        R.to_csv(f"results/logs/e1b_run_folds_r{arg.replace(',', '')}.csv", index=False)
        print(R.to_string(index=False)); print(f"wall {time.time() - t0:.0f}s")
    elif step == "unknown":
        step_unknown()
    elif step == "evaluate":
        step_evaluate()
    else:
        raise SystemExit(f"unknown step {step}")
