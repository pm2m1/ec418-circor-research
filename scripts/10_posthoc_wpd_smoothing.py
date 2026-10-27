"""POST-HOC (amendment A1, exploratory — does NOT change any pre-registered verdict).

Question: why did matched STFT bands beat WPD bands? Candidate mechanisms:
  (a) filter leakage of short wavelets  -> tested already: db4/db6/sym8/coif3 all similar (rejected)
  (b) estimator variance: one squared decimated packet coefficient (8 ms, ~1 dof) per column vs an
      STFT frame energy that averages a 64-sample Hann window (several dof)
Test of (b): smooth the WPD energy map along time with the same 64-sample (4-column) Hann kernel the
STFT uses, keep everything else identical, rerun RF on the frozen folds."""
import os
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy.signal import convolve

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.features.extract import aligned_features, whole_features
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.wavelets.bands import column_labels, wpd_energy_map

KER = np.hanning(6)[1:-1]          # 4-tap Hann over level-4 columns = 64 samples at 2 kHz
KER = KER / KER.sum()


def one(args):
    rec_id, wav, tsv = args
    x2 = preprocess(load_wav(wav))
    E = wpd_energy_map(x2, "db4", 4)
    Es = np.vstack([convolve(e, KER, mode="same") for e in E])
    lab = column_labels(load_segmentation(tsv), Es.shape[1], 16, 2000)
    return rec_id, whole_features(Es, "wpdWs"), aligned_features(Es, lab, "wpdAs")


if __name__ == "__main__":
    rt = recording_table(load_patients("data/raw/circor_training_data"))
    with Pool(2) as p:
        res = p.map(one, list(zip(rt.rec_id, rt.wav, rt.tsv)), chunksize=8)
    meta = rt[["rec_id", "patient_id", "subject_id", "location", "murmur"]]
    for idx, name in [(1, "W_wpd_db4_smooth"), (2, "A_wpd_db4_smooth")]:
        rows = [dict(rec_id=r[0], **(r[idx] or {})) for r in res]
        meta.merge(pd.DataFrame(rows), on="rec_id", how="left").to_csv(f"data/processed/rec_features_{name}.csv", index=False)
    print("written")
