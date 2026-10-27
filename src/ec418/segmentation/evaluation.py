"""Segmentation evaluation against the expert .tsv, identical to scripts/18_e1_autosegment.py (E1), shared by E1b.

Inside the expert-annotated spans (merged valid rows with labels 1-4): S1 / S2 centre detection with one-to-one greedy
matching at +/-50 ms (segment midpoints; auto centres outside the spans ignored), frame-wise 4-state accuracy on the
level-4 column grid over expert-labelled columns, swapped-F1 and period diagnostics."""
from __future__ import annotations

import numpy as np

from ..wavelets.bands import column_labels

FS2, HOP, TOL = 2000, 16, 0.050


def valid_rows(seg):
    if seg.size == 0:
        return seg.reshape(0, 3)
    return seg[np.isin(seg[:, 2], [1, 2, 3, 4]) & (seg[:, 1] > seg[:, 0])]


def spans(seg):
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


def evaluate_recording(expert_seg, auto_seg, n_samples_2k):
    ex = valid_rows(expert_seg)
    au = auto_seg[auto_seg[:, 2] > 0] if auto_seg.size else auto_seg.reshape(0, 3)
    sp = spans(ex)
    inside = lambda t: any(a <= t < b for a, b in sp)
    row = {}
    for name, lab, other in (("s1", 1, 3), ("s2", 3, 1)):
        ref = [(s + e) / 2 for s, e, l in ex if l == lab]
        det = [(s + e) / 2 for s, e, l in au if l == lab and inside((s + e) / 2)]
        row[f"{name}_tp"], row[f"{name}_fp"], row[f"{name}_fn"] = match(ref, det)
        swp = [(s + e) / 2 for s, e, l in au if l == other and inside((s + e) / 2)]
        row[f"{name}_swapped_tp"], row[f"{name}_swapped_fp"], row[f"{name}_swapped_fn"] = match(ref, swp)
    on = np.array([s for s, e, l in ex if l == 1])
    row["expert_period_s"] = float(np.median(np.diff(on))) if on.size >= 2 else np.nan
    n_cols = int(np.ceil(n_samples_2k / HOP))
    le, la = column_labels(ex, n_cols, HOP, FS2), column_labels(au, n_cols, HOP, FS2)
    m = le > 0
    row.update(n_expert_cols=int(m.sum()), n_correct_cols=int((la[m] == le[m]).sum()), n_auto_labelled_cols=int((la > 0).sum()))
    return row


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else np.nan
    r = tp / (tp + fn) if tp + fn else np.nan
    return p, r, (2 * p * r / (p + r) if p + r else np.nan)


def summarise(df, group_col=None):
    """df needs columns failure ('' = ok), patient_id, period_s and the evaluate_recording columns."""
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
