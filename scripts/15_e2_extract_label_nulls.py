"""Phase-2 E2 (docs/PROTOCOL_V2_LOCKED.md): 34 cycle-aligned features under true / perm / shift labels.

Same preprocessing, energy maps and aligned_features as v1 (scripts/02_extract_features.py for stft and wpd
db4, scripts/10_posthoc_wpd_smoothing.py for wpds = db4 smoothed with the 4-tap Hann over level-4 columns).
Only the per-column segmentation labels change (ec418.features.label_nulls). One label vector per recording
is used for all three representations (their column counts are identical; asserted).

Outputs data/processed/e2/rec_features_E2_<rep>_<cond>.csv for rep in {stft, wpd, wpds}, cond in
{true, perm, shift}, plus data/processed/e2/label_null_log.csv (per-recording T, shift, label counts) and
data/processed/e2/extraction_errors.csv.
"""
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy.signal import convolve

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import aligned_features
from ec418.features.label_nulls import median_s1_period_cols, null_labels, shift_labels
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.wavelets.bands import column_labels, stft_energy_map, wpd_energy_map

DATA = "data/raw/circor_training_data"
OUT = "data/processed/e2"
FS2, DEPTH = 2000, 4
HOP = 2 ** DEPTH
COLS_PER_S = FS2 / HOP
KER = np.hanning(6)[1:-1]          # as scripts/10: 4-tap Hann over level-4 columns = 64 samples at 2 kHz
KER = KER / KER.sum()
REPS = {"stft": "stftA", "wpd": "wpdA", "wpds": "wpdAs"}     # v1 column prefixes
CONDS = ["true", "perm", "shift"]


def one(args):
    rec_id, wav, tsv = args
    try:
        x2 = preprocess(load_wav(wav), 4000, FS2, 25.0, 900.0)
        Ew = wpd_energy_map(x2, "db4", DEPTH)
        Es = stft_energy_map(x2, FS2, DEPTH)
        assert Ew.shape[1] == Es.shape[1], "wpd/stft column counts differ"
        maps = {"stft": Es, "wpd": Ew, "wpds": np.vstack([convolve(e, KER, mode="same") for e in Ew])}
        lab = column_labels(load_segmentation(tsv), Ew.shape[1], HOP, FS2)
        feats = {}
        for c in CONDS:
            lc = null_labels(lab, c, rec_id, COLS_PER_S)
            for rep, E in maps.items():
                feats[(rep, c)] = aligned_features(E, lc, REPS[rep])
        log = dict(rec_id=rec_id, n_cols=int(lab.size), T_cols=median_s1_period_cols(lab, COLS_PER_S),
                   shift_cols=shift_labels(lab, rec_id, COLS_PER_S)[1],
                   **{f"n_lab{k}": int((lab == k).sum()) for k in range(5)})
        return dict(rec_id=rec_id, feats=feats, log=log, err=None)
    except Exception as e:  # recorded, never silently dropped
        return dict(rec_id=rec_id, feats=None, log=None, err=repr(e))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rt = recording_table(load_patients(DATA))
    t0 = time.time()
    with Pool(int(os.environ.get("NPROC", "2"))) as pool:
        res = pool.map(one, list(zip(rt.rec_id, rt.wav, rt.tsv)), chunksize=8)
    print(f"extracted {len(res)} recordings in {time.time() - t0:.1f}s")
    errs = [(r["rec_id"], r["err"]) for r in res if r["err"]]
    print("errors:", errs)
    pd.DataFrame(errs, columns=["rec_id", "error"]).to_csv(f"{OUT}/extraction_errors.csv", index=False)
    pd.DataFrame([r["log"] for r in res if r["log"]]).to_csv(f"{OUT}/label_null_log.csv", index=False)
    meta = rt[["rec_id", "patient_id", "subject_id", "location", "murmur"]]
    for rep in REPS:
        for c in CONDS:
            rows = [dict(rec_id=r["rec_id"], **(r["feats"][(rep, c)] or {})) for r in res if r["feats"]]
            df = meta.merge(pd.DataFrame(rows), on="rec_id", how="left")
            df.to_csv(f"{OUT}/rec_features_E2_{rep}_{c}.csv", index=False)
            fc = [k for k in df.columns if k not in meta.columns]
            print(f"E2_{rep}_{c}: {df.shape}, recordings without aligned features: {int(df[fc].isna().all(axis=1).sum())}")
