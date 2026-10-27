"""Patient-level metrics with an explicit positive class (Murmur Present = 1).

The Challenge weighted accuracy is computed by calling the OFFICIAL function
``compute_weighted_accuracy`` from physionetchallenges/evaluation-2022 (vendored, unmodified,
in references/official_eval/, commit recorded in COMMIT.txt). For the binary Present/Absent
task we encode predictions in the official 3-class one-hot space with the Unknown column
always 0; this reduces to (5*TP + 1*TN) / (5*P + 1*N).
"""
from __future__ import annotations

import importlib.util
import os

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve

_HERE = os.path.dirname(os.path.abspath(__file__))
_OFFICIAL = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "references", "official_eval", "evaluate_model.py"))
_official_mod = None


def _official():
    global _official_mod
    if _official_mod is None:
        import sys
        sys.path.insert(0, os.path.dirname(_OFFICIAL))  # official module imports helper_code
        spec = importlib.util.spec_from_file_location("official_eval_2022", _OFFICIAL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.path.pop(0)
        _official_mod = mod
    return _official_mod


MURMUR_CLASSES = ["Present", "Unknown", "Absent"]


def official_weighted_accuracy_binary(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    lab = np.zeros((y_true.size, 3), dtype=int)
    out = np.zeros((y_pred.size, 3), dtype=int)
    lab[np.arange(y_true.size), np.where(y_true == 1, 0, 2)] = 1
    out[np.arange(y_pred.size), np.where(y_pred == 1, 0, 2)] = 1
    return float(_official().compute_weighted_accuracy(lab, out, MURMUR_CLASSES))


def confusion(y_true, y_pred) -> dict:
    """Explicitly labelled binary confusion matrix (positive = Present = 1)."""
    y_true = np.asarray(y_true).astype(int); y_pred = np.asarray(y_pred).astype(int)
    return dict(TP=int(((y_true == 1) & (y_pred == 1)).sum()), FN=int(((y_true == 1) & (y_pred == 0)).sum()),
                FP=int(((y_true == 0) & (y_pred == 1)).sum()), TN=int(((y_true == 0) & (y_pred == 0)).sum()))


def _div(a, b):
    return float(a / b) if b > 0 else float("nan")


def threshold_metrics(y_true, score, thr) -> dict:
    y_pred = (np.asarray(score) >= thr).astype(int)
    c = confusion(y_true, y_pred)
    sens = _div(c["TP"], c["TP"] + c["FN"])           # Present recall
    spec = _div(c["TN"], c["TN"] + c["FP"])           # Absent recall
    prec = _div(c["TP"], c["TP"] + c["FP"])           # Present precision
    npv = _div(c["TN"], c["TN"] + c["FN"])
    f1 = _div(2 * prec * sens, prec + sens) if np.isfinite(prec) and np.isfinite(sens) else float("nan")
    f1_abs = _div(2 * npv * spec, npv + spec) if np.isfinite(npv) and np.isfinite(spec) else float("nan")
    n = sum(c.values())
    return dict(threshold=float(thr), **c, accuracy=_div(c["TP"] + c["TN"], n), sensitivity=sens,
                specificity=spec, precision=prec, npv=npv, f1_present=f1, f1_absent=f1_abs,
                macro_f1=float(np.nanmean([f1, f1_abs])), balanced_accuracy=float(np.nanmean([sens, spec])),
                weighted_accuracy=official_weighted_accuracy_binary(y_true, y_pred))


def ranking_metrics(y_true, score) -> dict:
    y_true = np.asarray(y_true).astype(int)
    return dict(auroc=float(roc_auc_score(y_true, score)), auprc=float(average_precision_score(y_true, score)),
                prevalence=float(y_true.mean()))


def sens_at_spec_descriptive(y_true, score, spec_target=0.80) -> float:
    """Sensitivity read off the TEST ROC at specificity >= target (descriptive, test-set
    threshold -> optimistic; reported only alongside the train-derived operating point)."""
    fpr, tpr, _ = roc_curve(y_true, score)
    ok = fpr <= 1 - spec_target + 1e-12
    return float(tpr[ok].max()) if ok.any() else 0.0


def threshold_for_specificity(y_true, score, spec_target=0.80) -> float:
    """Smallest threshold whose specificity on (y_true, score) is >= spec_target.
    Used on INNER out-of-fold training predictions only."""
    y_true = np.asarray(y_true).astype(int); score = np.asarray(score, float)
    neg = np.sort(score[y_true == 0])
    if neg.size == 0:
        return 0.5
    k = int(np.ceil(spec_target * neg.size)) - 1
    k = min(max(k, 0), neg.size - 1)
    thr = neg[k]
    # scores strictly above thr are positive -> nudge to keep >= target specificity
    return float(np.nextafter(thr, np.inf))


def threshold_max_weighted_accuracy(y_true, score) -> float:
    y_true = np.asarray(y_true).astype(int); score = np.asarray(score, float)
    cands = np.unique(np.concatenate([score, [np.inf]]))
    P, N = (y_true == 1).sum(), (y_true == 0).sum()
    best, best_t = -1, 0.5
    for t in cands:
        p = score >= t
        tp = (p & (y_true == 1)).sum(); tn = (~p & (y_true == 0)).sum()
        w = (5 * tp + tn) / (5 * P + N)
        if w > best:
            best, best_t = w, t
    return float(best_t)


def subject_bootstrap(df, metric_fn, group_col="subject_id", n_boot=2000, seed=0):
    """Percentile CI by resampling SUBJECTS (canonical groups), never recordings or cycles."""
    rng = np.random.default_rng(seed)
    groups = df[group_col].unique()
    idx = {g: np.flatnonzero(df[group_col].values == g) for g in groups}
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(groups, size=groups.size, replace=True)
        rows = np.concatenate([idx[g] for g in pick])
        sub = df.iloc[rows]
        try:
            vals.append(metric_fn(sub))
        except ValueError:
            continue
    vals = np.asarray(vals, float)
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5)), vals
