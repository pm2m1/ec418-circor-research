"""Phase-2 E1 step 1: unsupervised segmentation of every recording + evaluation against the expert .tsv.

Segmentation (ec418.segmentation.autoseg) sees only the preprocessed signal. The expert .tsv and the patient
table are read afterwards, for evaluation only, inside the expert-annotated spans (runs of valid labels 1-4):
  * S1 / S2 centre detection: segment midpoints, one-to-one greedy matching at +/-50 ms; auto centres outside
    the annotated spans are ignored; pooled TP/FP/FN -> precision, recall, F1;
  * frame-wise 4-state accuracy on the level-4 column grid (8 ms) over columns the expert labels 1-4;
  * failure = the segmenter returns no segments (reason recorded).
Breakdowns by murmur class and v1.0.3 age group. Descriptive diagnostics: auto period vs expert period
(median S1-onset interval of the expert rows; agreement within 10 %), and swapped F1 (auto S2 centres scored
against expert S1 centres and vice versa) to detect S1/S2 inversion. Low-quality flag if S1 or S2 F1 < 0.70 (protocol E1).

Writes data/interim/autoseg/<rec_id>.tsv (gitignored), results/tables/e1_segmentation_per_recording.csv,
results/tables/e1_segmentation_summary.csv, results/logs/e1_segmentation.json.
usage: NPROC=10 python scripts/18_e1_autosegment.py
"""
import json
import os
from multiprocessing import Pool

import numpy as np
import pandas as pd

from ec418.data.circor import load_patients, load_segmentation, recording_table
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.segmentation.autoseg import autoseg, write_tsv
from ec418.wavelets.bands import column_labels

DATA = "data/raw/circor_training_data"
OUT = "data/interim/autoseg"
FS2, HOP, TOL = 2000, 16, 0.050
F1_FLAG = 0.70


def segment_one(args):
    rec_id, wav = args
    x2 = preprocess(load_wav(wav), 4000, FS2, 25.0, 900.0)
    r = autoseg(x2, FS2)
    write_tsv(f"{OUT}/{rec_id}.tsv", r.segments, x2.size / FS2)
    return dict(rec_id=rec_id, n_samples=int(x2.size), failure=r.failure or "", period_s=r.period_s,
                n_peaks=r.n_peaks, n_auto_segments=int(len(r.segments)))


def valid_rows(seg):
    if seg.size == 0:
        return seg
    return seg[np.isin(seg[:, 2], [1, 2, 3, 4]) & (seg[:, 1] > seg[:, 0])]


def spans(seg):
    """Merge contiguous/overlapping valid expert rows into annotated spans."""
    out = []
    for s, e, _ in sorted(map(tuple, seg)):
        if out and s <= out[-1][1] + 1e-9:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def match(ref, det, tol=TOL):
    pairs = sorted((abs(r - d), i, j) for i, r in enumerate(ref) for j, d in enumerate(det) if abs(r - d) <= tol)
    ur, ud, tp = set(), set(), 0
    for _, i, j in pairs:
        if i not in ur and j not in ud:
            ur.add(i); ud.add(j); tp += 1
    return tp, len(det) - tp, len(ref) - tp


def evaluate(rec_id, tsv, n_samples):
    ex = valid_rows(load_segmentation(tsv))
    au = load_segmentation(f"{OUT}/{rec_id}.tsv")
    au = au[au[:, 2] > 0] if au.size else au
    sp = spans(ex)
    inside = lambda t: any(a <= t < b for a, b in sp)
    row = {}
    for name, lab, other in (("s1", 1, 3), ("s2", 3, 1)):
        ref = [(s + e) / 2 for s, e, l in ex if l == lab]
        det = [(s + e) / 2 for s, e, l in au if l == lab and inside((s + e) / 2)] if au.size else []
        row[f"{name}_tp"], row[f"{name}_fp"], row[f"{name}_fn"] = match(ref, det)
        swp = [(s + e) / 2 for s, e, l in au if l == other and inside((s + e) / 2)] if au.size else []
        row[f"{name}_swapped_tp"], row[f"{name}_swapped_fp"], row[f"{name}_swapped_fn"] = match(ref, swp)
    on = np.array([s for s, e, l in ex if l == 1])
    row["expert_period_s"] = float(np.median(np.diff(on))) if on.size >= 2 else np.nan
    n_cols = int(np.ceil(n_samples / HOP))
    le, la = column_labels(ex, n_cols, HOP, FS2), column_labels(au, n_cols, HOP, FS2)
    m = le > 0
    row.update(n_expert_cols=int(m.sum()), n_correct_cols=int((la[m] == le[m]).sum()), n_auto_labelled_cols=int((la > 0).sum()))
    return row


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else np.nan
    r = tp / (tp + fn) if tp + fn else np.nan
    return p, r, (2 * p * r / (p + r) if p + r else np.nan)


def summarise(df, group_col=None):
    rows = []
    for key, g in ([("all", df)] if group_col is None else df.groupby(group_col, dropna=False)):
        rec = dict(group=group_col or "all", value=str(key), n_recordings=len(g), n_patients=g.patient_id.nunique(),
                   failure_frac=float((g.failure != "").mean()))
        for s in ("s1", "s2"):
            p, r, f = prf(g[f"{s}_tp"].sum(), g[f"{s}_fp"].sum(), g[f"{s}_fn"].sum())
            rec.update({f"{s}_precision": p, f"{s}_recall": r, f"{s}_f1": f})
        for s in ("s1", "s2"):
            rec[f"{s}_f1_swapped"] = prf(g[f"{s}_swapped_tp"].sum(), g[f"{s}_swapped_fp"].sum(), g[f"{s}_swapped_fn"].sum())[2]
        ok = g.period_s.notna() & g.expert_period_s.notna()
        rec["period_within_10pct"] = float((np.abs(g.period_s[ok] / g.expert_period_s[ok] - 1) <= 0.10).mean())
        rec["period_about_half"] = float((np.abs(g.period_s[ok] / g.expert_period_s[ok] - 0.5) <= 0.10).mean())
        rec["frame_accuracy_4state"] = g.n_correct_cols.sum() / g.n_expert_cols.sum() if g.n_expert_cols.sum() else np.nan
        rows.append(rec)
    return rows


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    pats = load_patients(DATA)
    rt = recording_table(pats)
    with Pool(int(os.environ.get("NPROC", "2"))) as pool:
        seg = pool.map(segment_one, list(zip(rt.rec_id, rt.wav)), chunksize=8)
    S = pd.DataFrame(seg)
    # ---- evaluation only below: expert .tsv and metadata ----
    S = S.merge(rt[["rec_id", "patient_id", "murmur", "tsv"]], on="rec_id")
    ev = [evaluate(r.rec_id, r.tsv, r.n_samples) for r in S.itertuples()]
    S = pd.concat([S, pd.DataFrame(ev)], axis=1)
    age = pd.read_csv("results/tables/v103_patients_audit.csv")[["patient_id", "age"]]
    S = S.merge(age, on="patient_id", how="left")
    S["age"] = S.age.fillna("missing")
    S.drop(columns=["tsv"]).to_csv("results/tables/e1_segmentation_per_recording.csv", index=False)
    rows = summarise(S) + summarise(S, "murmur") + summarise(S, "age")
    T = pd.DataFrame(rows)
    T.to_csv("results/tables/e1_segmentation_summary.csv", index=False)
    a = T.iloc[0]
    out = dict(n_recordings=len(S), failures=S.failure.replace("", "ok").value_counts().to_dict(),
               s1_f1=a.s1_f1, s2_f1=a.s2_f1, frame_accuracy_4state=a.frame_accuracy_4state,
               low_quality_segmentation=bool(a.s1_f1 < F1_FLAG or a.s2_f1 < F1_FLAG),
               period_s=S.period_s.describe().to_dict())
    json.dump(out, open("results/logs/e1_segmentation.json", "w"), indent=2, default=float)
    pd.set_option("display.width", 220)
    print(T.round(3).to_string(index=False))
    print(json.dumps(out, indent=2, default=float))
