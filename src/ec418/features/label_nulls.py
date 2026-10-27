"""Phase-2 E2 label nulls (docs/PROTOCOL_V2_LOCKED.md, configs/protocol_v2.json "E2_isolate_alignment").

Both nulls act on the per-column segmentation labels produced by ``column_labels`` (0 = unannotated,
1 = S1, 2 = systole, 3 = S2, 4 = diastole) and are fed to the unchanged ``aligned_features``:

  perm  (primary)   : labels permuted within the recording -> same label counts, no timing.
  shift (secondary) : labels circularly shifted by u*T columns, u ~ U(0.2, 0.8), T = median S1-to-S1
                      interval of the recording (0.6 s if < 2 S1 events) -> contiguity kept, wrong phase.

Seed = zlib.crc32(rec_id); each null draws from its own freshly seeded generator, so a recording's
null labels do not depend on which other nulls were computed or in what order.
"""
from __future__ import annotations

import zlib

import numpy as np

S1_LABEL = 1
DEFAULT_PERIOD_S = 0.6
SHIFT_U_RANGE = (0.2, 0.8)


def rec_seed(rec_id: str) -> int:
    return zlib.crc32(rec_id.encode("utf-8"))


def s1_onsets(labels: np.ndarray) -> np.ndarray:
    """Column indices where an S1 run starts (one S1 event per contiguous run of label 1)."""
    is_s1 = labels == S1_LABEL
    return np.flatnonzero(is_s1 & ~np.r_[False, is_s1[:-1]])


def median_s1_period_cols(labels: np.ndarray, cols_per_s: float) -> float:
    """T in columns: median S1-to-S1 onset interval, or DEFAULT_PERIOD_S if fewer than 2 S1 events."""
    on = s1_onsets(labels)
    if on.size < 2:
        return DEFAULT_PERIOD_S * cols_per_s
    return float(np.median(np.diff(on)))


def perm_labels(labels: np.ndarray, rec_id: str) -> np.ndarray:
    """Primary null: permute the column labels of one recording (seed = crc32(rec_id))."""
    return np.random.default_rng(rec_seed(rec_id)).permutation(labels)


def shift_labels(labels: np.ndarray, rec_id: str, cols_per_s: float) -> tuple[np.ndarray, int]:
    """Secondary null: circular shift by round(u*T) columns. Returns (labels, shift_in_columns)."""
    u = np.random.default_rng(rec_seed(rec_id)).uniform(*SHIFT_U_RANGE)
    k = int(round(u * median_s1_period_cols(labels, cols_per_s)))
    return np.roll(labels, k), k


def null_labels(labels: np.ndarray, condition: str, rec_id: str, cols_per_s: float) -> np.ndarray:
    if condition == "true":
        return labels
    if condition == "perm":
        return perm_labels(labels, rec_id)
    if condition == "shift":
        return shift_labels(labels, rec_id, cols_per_s)[0]
    raise ValueError(f"unknown label condition {condition!r}")
