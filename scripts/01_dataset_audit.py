"""Dataset audit on the real CirCor files: counts, labels, linkage, audio properties,
segmentation coverage. Writes results/tables/*.csv and results/logs/dataset_audit.json."""
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd
import soundfile as sf

from ec418.data.circor import linkage_report, load_patients, load_segmentation, patient_table, recording_table

DATA = sys.argv[1] if len(sys.argv) > 1 else "data/raw/circor_training_data"
OUT_T, OUT_L = "results/tables", "results/logs"

pats = load_patients(DATA)
pt = patient_table(pats)
rt = recording_table(pats)
link = linkage_report(pats)

# CSV cross-check (the CSV failed its checksum; we only use it to detect disagreements)
csv = pd.read_csv(os.path.join(DATA, "training_data.csv"))
csv_lab = dict(zip(csv["Patient ID"], csv["Murmur"]))
csv_mismatch = [p for p in pt.patient_id if csv_lab.get(p) != pats[p].murmur]

# audio properties of every recording
audio = []
for r in rt.itertuples():
    info = sf.info(r.wav)
    x, fs = sf.read(r.wav, dtype="int16")
    seg = load_segmentation(r.tsv)
    dur = info.frames / info.samplerate
    lab_dur = {k: 0.0 for k in range(5)}
    for s, e, l in seg:
        lab_dur[int(l)] += max(0.0, min(e, dur) - max(s, 0.0))
    n_sys = int((seg[:, 2] == 2).sum()) if seg.size else 0
    audio.append(dict(rec_id=r.rec_id, fs=info.samplerate, channels=info.channels, subtype=info.subtype,
                      duration_s=dur, clipped_frac=float(np.mean(np.abs(x.astype(int)) >= 32767)),
                      flat=bool(x.std() == 0), n_systoles=n_sys,
                      annotated_frac=float(1 - lab_dur[0] / dur) if dur > 0 else 0.0,
                      sys_s=lab_dur[2], dia_s=lab_dur[4]))
au = pd.DataFrame(audio)
rt = rt.merge(au, on="rec_id")
rt.assign(has_tsv=rt.tsv.apply(lambda p: isinstance(p, str))).drop(columns=["wav", "tsv"]).to_csv(f"{OUT_T}/recordings_audit.csv", index=False)
pt.to_csv(f"{OUT_T}/patients_audit.csv", index=False)

summary = dict(
    data_dir=DATA,
    n_patients=int(len(pt)), n_recordings=int(len(rt)),
    murmur_patients=pt.murmur.value_counts().to_dict(),
    murmur_recordings=rt.murmur.value_counts().to_dict(),
    outcome_available=bool(pt.outcome.notna().any()),
    campaign=pt.campaign.value_counts().to_dict(),
    recordings_per_patient=pt.n_recordings.value_counts().sort_index().to_dict(),
    location_counts=rt.location.value_counts().to_dict(),
    linkage=link,
    csv_label_mismatches_vs_txt=csv_mismatch,
    fs_values=au.fs.value_counts().to_dict(), channels=au.channels.value_counts().to_dict(),
    subtype=au.subtype.value_counts().to_dict(),
    duration_s=dict(min=float(au.duration_s.min()), median=float(au.duration_s.median()),
                    max=float(au.duration_s.max()), total_h=float(au.duration_s.sum() / 3600)),
    recordings_with_any_clipping=int((au.clipped_frac > 0).sum()),
    flat_recordings=int(au.flat.sum()),
    segmentation=dict(
        recordings_with_tsv=int(rt.tsv.apply(lambda p: isinstance(p, str) and os.path.exists(p)).sum()),
        median_annotated_frac=float(au.annotated_frac.median()),
        recordings_zero_systoles=int((au.n_systoles == 0).sum()),
        recordings_lt3_systoles=int((au.n_systoles < 3).sum()),
        annotated_frac_by_murmur=rt.groupby("murmur").annotated_frac.median().round(3).to_dict(),
    ),
    present_patients_grading=pt[pt.murmur == "Present"].systolic_grading.value_counts(dropna=False).to_dict(),
    present_patients_pitch=pt[pt.murmur == "Present"].systolic_pitch.value_counts(dropna=False).to_dict(),
    present_patients_with_diastolic=int(pt[pt.murmur == "Present"].diastolic_timing.notna().sum()),
    present_recordings_at_murmur_location=int(rt[(rt.murmur == "Present")].murmur_at_location.sum()),
    subjects_binary_task=int(pt[pt.murmur != "Unknown"].subject_id.nunique()),
    patients_binary_task=int((pt.murmur != "Unknown").sum()),
)
json.dump(summary, open(f"{OUT_L}/dataset_audit.json", "w"), indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
