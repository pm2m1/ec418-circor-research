"""Diagnose the failed G2 gate 2 (E4R predictions != saved E4) on repeat 0 / fold 0 only, without any G2 result.
Compares (1) HSMM parameters vs results/logs/e1b_models/r0_f0.json, (2) test-recording decodes vs
results/tables/e1b_segmentation_per_recording.csv (period, systolic interval, D, S1/S2 matches, column counts).
-> results/tables/p3/g2_gate_diagnosis_r0f0.csv"""
import json, os
import numpy as np, pandas as pd
from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.segmentation import lr_hsmm as H
from ec418.segmentation.evaluation import evaluate_recording
RT = recording_table(load_patients("data/raw/circor_training_data")); FT = pd.read_csv("configs/folds_patient_level.csv")
g = FT[(FT.repeat == 0) & (FT.outer_fold == 0)]; tr, te = g[g.role == "train"], g[g.role == "test"]
r = RT[RT.patient_id.isin(set(tr.patient_id))]
ld = lambda i: np.load(f"data/interim/e1b/springer/{i}.npz")
m = H.train([ld(x)["F"] for x in r.rec_id], [load_segmentation(t) for t in r.tsv], seed=0)
saved = json.load(open("results/logs/e1b_models/r0_f0.json"))["outer"]
def flat(d, p=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict): out.update(flat(v, p + k + "."))
        else: out[p + k] = np.asarray(v, dtype=float).ravel()
    return out
a, b = flat(json.loads(json.dumps(m.params, default=float))), flat(saved)
pdiff = {k: float(np.max(np.abs(a[k] - b[k]))) if a[k].shape == b[k].shape else np.inf for k in b}
print("HSMM param max abs diff:", max(pdiff.values()), {k: v for k, v in pdiff.items() if v > 1e-10})
S = pd.read_csv("results/tables/e1b_segmentation_per_recording.csv"); S = S[(S.repeat == 0) & (S.fold == 0) & (S.model == "outer")].set_index("rec_id")
rows = []
for x in RT[RT.patient_id.isin(set(te.patient_id))].itertuples():
    z = ld(x.rec_id); x2 = preprocess(load_wav(x.wav), 4000, 2000, 25.0, 900.0)
    qt, info = H.decode(m, z["F"], z["ac"]); seg = H.states_to_segments(qt, x2.size / 2000)
    ev = evaluate_recording(load_segmentation(x.tsv), seg, x2.size)
    s = S.loc[x.rec_id]
    rows.append(dict(rec_id=x.rec_id, period_new=info.get("period_s"), period_saved=s.period_s, D_new=info.get("D"), D_saved=s.D,
                     auto_cols_new=ev.get("n_auto_labelled_cols"), auto_cols_saved=s.n_auto_labelled_cols,
                     correct_new=ev.get("n_correct_cols"), correct_saved=s.n_correct_cols, s1_tp_new=ev.get("s1_tp"), s1_tp_saved=s.s1_tp))
R = pd.DataFrame(rows); os.makedirs("results/tables/p3", exist_ok=True); R.to_csv("results/tables/p3/g2_gate_diagnosis_r0f0.csv", index=False)
for c in ["period", "D", "auto_cols", "correct", "s1_tp"]:
    d = (R[f"{c}_new"].astype(float) - R[f"{c}_saved"].astype(float)).abs()
    print(f"{c:10s} recordings differing: {(d > 1e-9).sum()}/{len(R)}  max |diff| {d.max():.6g}")
