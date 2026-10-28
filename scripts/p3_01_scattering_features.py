"""G4 + G1a: scattering features for CirCor (expert labels) and W_scat1 for ZCHSound.
Run with the kymatio env:  PYTHONPATH=src .venv-scat/bin/python scripts/p3_01_scattering_features.py
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.phase3 import load_any_wav, scattering_feature_sets
from ec418.preprocessing.signal import preprocess

OUT = "data/processed"
ZCH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ZCH_DIR", "data/external/ZCHSound")

rt = recording_table(load_patients(os.environ.get("CIRCOR_DIR", "data/raw/circor_training_data")))
meta = rt[["rec_id", "patient_id", "subject_id", "location", "murmur"]]
rows = {"A_scat1": [], "A_scat12": [], "W_scat1": []}
errs = []
t0 = time.time()
for r in rt.itertuples():
    try:
        x, fs = load_any_wav(r.wav)
        assert fs == 4000
        res = scattering_feature_sets(preprocess(x, 4000, 2000), load_segmentation(r.tsv))
        for k in rows:
            rows[k].append(dict(rec_id=r.rec_id, **(res[k] or {})))
    except Exception as e:
        errs.append((r.rec_id, repr(e)))
        for k in rows:
            rows[k].append(dict(rec_id=r.rec_id))
print(f"CirCor scattering: {len(rt)} recordings in {time.time() - t0:.0f}s, errors {errs}")
for k, v in rows.items():
    df = meta.merge(pd.DataFrame(v), on="rec_id", how="left")
    df.to_csv(f"{OUT}/rec_features_{k}.csv", index=False)
    fc = [c for c in df.columns if c not in meta.columns]
    print(k, df.shape, "recordings without features:", int(df[fc].isna().all(axis=1).sum()))

# ZCHSound: whole-signal scattering only (no segmentation exists)
zrows = []
for sub, csvname, sep in [("clean Heartsound Data", "Clean Heartsound Data Details.csv", ","),
                          ("Noise Heartsound Data Details", "Noise Heartsound Data Details.csv", ";")]:
    lab = pd.read_csv(os.path.join(ZCH, csvname), sep=sep, encoding="utf-8-sig")
    for f in lab.itertuples():
        x, fs = load_any_wav(os.path.join(ZCH, sub, f.fileName))
        res = scattering_feature_sets(preprocess(x, fs, 2000), np.zeros((0, 3)))
        zrows.append(dict(rec_id=f.fileName[:-4], subset="clean" if sub.startswith("clean") else "noisy", **res["W_scat1"]))
pd.DataFrame(zrows).to_csv(f"{OUT}/zch_features_W_scat1.csv", index=False)
print("ZCH W_scat1:", len(zrows))
