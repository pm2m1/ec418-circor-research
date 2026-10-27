"""Phase-2 E1 step 2: the 34 cycle-aligned features for stft / wpd / wpds with the AUTOMATIC labels.

Identical to the `true` arm of scripts/15_e2_extract_label_nulls.py (same preprocessing, energy maps, wpds kernel,
column grid and aligned_features) except that the segmentation is read from data/interim/autoseg/<rec_id>.tsv
(scripts/18_e1_autosegment.py) instead of the expert .tsv. Recordings below the v1 coverage minimum get no aligned
features (WEKA sees them as missing).

Outputs data/processed/e1/rec_features_E1_<rep>_auto.csv, data/processed/e1/extraction_errors.csv,
results/logs/e1_feature_coverage.json.
usage: NPROC=10 python scripts/19_e1_extract_auto_features.py
"""
import json
import os
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy.signal import convolve

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import aligned_features
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.wavelets.bands import column_labels, stft_energy_map, wpd_energy_map

DATA = "data/raw/circor_training_data"
SEGDIR = "data/interim/autoseg"
OUT = "data/processed/e1"
FS2, DEPTH = 2000, 4
HOP = 2 ** DEPTH
KER = np.hanning(6)[1:-1]          # as scripts/10 and 15
KER = KER / KER.sum()
REPS = {"stft": "stftA", "wpd": "wpdA", "wpds": "wpdAs"}


def one(args):
    rec_id, wav = args
    try:
        x2 = preprocess(load_wav(wav), 4000, FS2, 25.0, 900.0)
        Ew = wpd_energy_map(x2, "db4", DEPTH)
        Es = stft_energy_map(x2, FS2, DEPTH)
        assert Ew.shape[1] == Es.shape[1], "wpd/stft column counts differ"
        maps = {"stft": Es, "wpd": Ew, "wpds": np.vstack([convolve(e, KER, mode="same") for e in Ew])}
        lab = column_labels(load_segmentation(f"{SEGDIR}/{rec_id}.tsv"), Ew.shape[1], HOP, FS2)
        cov = dict(rec_id=rec_id, s1_cols=int((lab == 1).sum()), sys_cols=int((lab == 2).sum()),
                   s2_cols=int((lab == 3).sum()), dia_cols=int((lab == 4).sum()), unannot_frac=float((lab == 0).mean()))
        return dict(rec_id=rec_id, feats={rep: aligned_features(E, lab, REPS[rep]) for rep, E in maps.items()}, cov=cov, err=None)
    except Exception as e:  # recorded, never silently dropped
        return dict(rec_id=rec_id, feats=None, cov=None, err=repr(e))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rt = recording_table(load_patients(DATA))
    with Pool(int(os.environ.get("NPROC", "2"))) as pool:
        res = pool.map(one, list(zip(rt.rec_id, rt.wav)), chunksize=8)
    errs = [(r["rec_id"], r["err"]) for r in res if r["err"]]
    pd.DataFrame(errs, columns=["rec_id", "error"]).to_csv(f"{OUT}/extraction_errors.csv", index=False)
    pd.DataFrame([r["cov"] for r in res if r["cov"]]).to_csv(f"{OUT}/seg_coverage_auto.csv", index=False)
    meta = rt[["rec_id", "patient_id", "subject_id", "location", "murmur"]]
    binary = set(pd.read_csv("configs/folds_patient_level.csv").patient_id)
    cov = dict(errors=errs)
    for rep in REPS:
        rows = [dict(rec_id=r["rec_id"], **(r["feats"][rep] or {})) for r in res if r["feats"]]
        df = meta.merge(pd.DataFrame(rows), on="rec_id", how="left")
        df.to_csv(f"{OUT}/rec_features_E1_{rep}_auto.csv", index=False)
        fc = [c for c in df.columns if c not in meta.columns]
        none = df[fc].isna().all(axis=1)
        b = df.patient_id.isin(binary)
        pat_none = df[b].assign(none=none[b]).groupby("patient_id").none.all()
        cov[rep] = dict(recordings_without_aligned=int(none.sum()), recordings_total=len(df),
                        binary_task_recordings_without_aligned=int(none[b].sum()), binary_task_recordings=int(b.sum()),
                        binary_task_patients_without_any_aligned=int(pat_none.sum()), binary_task_patients=int(pat_none.size),
                        by_murmur_recordings_without_aligned=df[none].murmur.value_counts().to_dict())
    json.dump(cov, open("results/logs/e1_feature_coverage.json", "w"), indent=2)
    print(json.dumps(cov, indent=2))
