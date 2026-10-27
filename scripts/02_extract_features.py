"""Extract recording-level features for ALL recordings (training-independent transforms).

Outputs data/processed/rec_features_<set>.csv for sets:
  B0                       conventional acoustic features
  W_stft, A_stft           matched STFT band energies, whole / cycle-aligned pooling
  W_wpd_<wav>, A_wpd_<wav> wavelet-packet band energies for wav in {db4 (primary), db6, sym8, coif3}
plus data/processed/seg_coverage.csv. Unknown-murmur patients are processed too (not used in
the binary task; kept for the optional quality analysis)."""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import acoustic_features, band_feature_sets
from ec418.preprocessing.signal import load_wav, preprocess

DATA = "data/raw/circor_training_data"
OUT = "data/processed"
WAVELETS = ["db4", "db6", "sym8", "coif3"]
FS2 = 2000


def one(args):
    rec_id, wav, tsv = args
    try:
        x = load_wav(wav)
        x2 = preprocess(x, 4000, FS2, 25.0, 900.0)
        seg = load_segmentation(tsv)
        out = {"rec_id": rec_id}
        res = {"B0": acoustic_features(x2, FS2)}
        for w in WAVELETS:
            s = band_feature_sets(x2, seg, FS2, w, 4)
            res[f"W_wpd_{w}"] = s["W_wpd"]
            res[f"A_wpd_{w}"] = s["A_wpd"]
            if w == "db4":
                res["W_stft"] = s["W_stft"]
                res["A_stft"] = s["A_stft"]
                res["seg"] = s["seg_cov"]
        out["res"] = res
        out["err"] = None
    except Exception as e:  # recorded, never silently dropped
        out = {"rec_id": rec_id, "res": None, "err": repr(e)}
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rt = recording_table(load_patients(DATA))
    jobs = list(zip(rt.rec_id, rt.wav, rt.tsv))
    t0 = time.time()
    with Pool(int(os.environ.get("NPROC", "2"))) as pool:
        results = pool.map(one, jobs, chunksize=8)
    print(f"extracted {len(results)} recordings in {time.time() - t0:.1f}s")
    errs = [(r["rec_id"], r["err"]) for r in results if r["err"]]
    print("errors:", errs)
    sets = {}
    for r in results:
        if r["res"] is None:
            continue
        for k, v in r["res"].items():
            row = {"rec_id": r["rec_id"]}
            if v is not None:
                row.update(v)
            sets.setdefault(k, []).append(row)
    meta = rt[["rec_id", "patient_id", "subject_id", "location", "murmur"]]
    for k, rows in sets.items():
        df = meta.merge(pd.DataFrame(rows), on="rec_id", how="left")
        name = "seg_coverage" if k == "seg" else f"rec_features_{k}"
        df.to_csv(f"{OUT}/{name}.csv", index=False)
        feat_cols = [c for c in df.columns if c not in meta.columns]
        miss = df[feat_cols].isna().all(axis=1).sum() if feat_cols else 0
        print(f"{name}: {df.shape}, recordings with all-missing features: {miss}")
    pd.DataFrame(errs, columns=["rec_id", "error"]).to_csv(f"{OUT}/extraction_errors.csv", index=False)
