"""B1 features: reuse the baseline authors' OWN MATLAB-computed features (shipped in their repo)
but attach each row to the correct recording.

Bug found in the shipped artefacts: control Entropy/Slope rows cover Absent recordings only
(2391), whereas control Multifractal rows cover Absent + Unknown recordings (2547). The demo
concatenates them by row position, so ~all control rows mix features from different
recordings and 156 rows get mean-imputed Entropy/Slope (all labelled 'control').

Re-alignment: MATLAB `dir` lists *.wav in ASCII order; rows were written in that order filtered
by class. We reconstruct the filtered order, attach rec_ids, and independently VERIFY the
mapping by recomputing the wavelet-entropy feature in Python for a sample of recordings."""
import glob
import os

import numpy as np
import pandas as pd
import soundfile as sf

from ec418.data.circor import load_patients, recording_table

DATA = "data/raw/circor_training_data"
REF = "references/baseline_repo"

pats = load_patients(DATA)
rt = recording_table(pats)
lab = rt.set_index("rec_id")["murmur"]

wavs = sorted(os.path.basename(p) for p in glob.glob(f"{DATA}/*.wav"))   # MATLAB dir() order
rec_order = [w[:-4] for w in wavs]
present = [r for r in rec_order if lab[r] == "Present"]
absent = [r for r in rec_order if lab[r] == "Absent"]
absent_unknown = [r for r in rec_order if lab[r] in ("Absent", "Unknown")]

ent_c = pd.read_csv(f"{REF}/case_features/Window_Entropy_Case.csv", header=None).T[0].values
slo_c = pd.read_csv(f"{REF}/case_features/Window_Slope_Case.csv", header=None).T[0].values
mf_c = pd.read_csv(f"{REF}/case_features/Window_Mf_Case.csv", header=None).values
ent_n = pd.read_csv(f"{REF}/control_features/Window_Entropy_Control.csv", header=None).T[0].values
slo_n = pd.read_csv(f"{REF}/control_features/Window_Slope_Control.csv", header=None).T[0].values
mf_n = pd.read_csv(f"{REF}/control_features/Window_Mf_Control.csv", header=None).values

assert len(ent_c) == len(slo_c) == len(mf_c) == len(present) == 616
assert len(ent_n) == len(slo_n) == len(absent) == 2391
assert len(mf_n) == len(absent_unknown) == 2547
# patient-ID sequence check for the multifractal tables (they carry the ID in column 0)
assert [int(r.split("_")[0]) for r in present] == [int(v) for v in mf_c[:, 0]]
assert [int(r.split("_")[0]) for r in absent_unknown] == [int(v) for v in mf_n[:, 0]]

MF = ["Hurst_spectral_mode", "LeftSlope", "RightSlope", "LeftTangent", "RightTangent", "Broadness",
      "LeftTangentPoint", "RightTangentPoint"]
rows = []
for i, r in enumerate(present):
    rows.append(dict(rec_id=r, b1_entropy_cv=ent_c[i], b1_slope=slo_c[i], **dict(zip(MF, mf_c[i, 1:]))))
mf_n_map = {r: mf_n[i, 1:] for i, r in enumerate(absent_unknown)}
for i, r in enumerate(absent):
    rows.append(dict(rec_id=r, b1_entropy_cv=ent_n[i], b1_slope=slo_n[i], **dict(zip(MF, mf_n_map[r]))))
b1 = pd.DataFrame(rows).rename(columns={m: f"b1_{m}" for m in MF})

# ---- independent verification: recompute window wavelet-entropy CV with an EXACT port of
# the authors' dwtr.m (src/ec418/wavelets/dwtr_port.py) and compare with the shipped value ----
from ec418.wavelets.dwtr_port import window_entropy_cv

rng = np.random.default_rng(0)
check_ids = list(rng.choice(present, 40, replace=False)) + list(rng.choice(absent, 60, replace=False))
wavmap = rt.set_index("rec_id")["wav"]
absent_pos = {r: k for k, r in enumerate(absent)}
ver = []
for r in check_ids:
    shipped = float(b1.loc[b1.rec_id == r, "b1_entropy_cv"].iloc[0])
    x, _ = sf.read(wavmap[r], dtype="float64")
    v = window_entropy_cv(x)
    row = dict(rec_id=r, murmur=lab[r], shipped=shipped, python_port=v, rel_err=abs(v - shipped) / abs(shipped))
    if r in absent_pos:  # value the ORIGINAL positional join would have paired with this recording's Mf row
        k = absent_unknown.index(r)
        row["buggy_join_value"] = float(ent_n[k]) if k < len(ent_n) else float("nan")
    ver.append(row)
ver = pd.DataFrame(ver)
ver.to_csv("results/tables/b1_alignment_verification.csv", index=False)
print(ver.round(5).to_string())
print("median rel. error:", ver.rel_err.median(), " max:", ver.rel_err.max())

# what the ORIGINAL (buggy) positional join would have attached to the same rows
ent_pos = dict(zip(absent_unknown[:2391], ent_n))  # shipped demo pairs Mf row k with entropy row k
mism = sum(1 for k, r in enumerate(absent_unknown[:2391]) if r != absent[k])
print(f"control rows whose entropy/slope came from a different recording in the shipped demo: {mism}/2391")

out = rt[["rec_id", "patient_id", "subject_id", "location", "murmur"]].merge(b1, on="rec_id", how="inner")
out.to_csv("data/processed/rec_features_B1.csv", index=False)
print("B1 realigned:", out.shape, out.murmur.value_counts().to_dict())
