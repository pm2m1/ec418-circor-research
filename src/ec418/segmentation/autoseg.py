"""Phase-2 E1 unsupervised heart-sound segmenter (docs/PROTOCOL_V2_LOCKED.md "E1",
configs/protocol_v2.json "E1_automatic_segmentation"; implementation details in amendment I2).

Input is the preprocessed signal only (2 kHz, 25-900 Hz, z-scored, as ``preprocess``). It never reads the
expert .tsv, murmur labels or patient metadata. Steps (pre-registered constants below):
  1. homomorphic envelope of the 25-400 Hz band: |Hilbert| -> log -> 8 Hz low-pass -> exp, sampled at 50 Hz;
  2. heart period T = highest local maximum of the envelope autocorrelation at lags in [0.3, 1.5] s;
  3. peaks = envelope local maxima with spacing >= 0.2*T and height >= 25th percentile of the envelope;
  4. consecutive peak intervals paired (d0,d1), (d2,d3), ...: the shorter of each pair = systole (S1 -> S2),
     the longer = diastole (S2 -> S1); intervals that break the systole/diastole alternation are invalid;
  5. S1/S2 extent = contiguous region around the peak where the envelope >= 50 % of the peak, clipped to
     [40, 160] ms; systole/diastole fill the gaps between the sounds of a valid interval;
  6. everything else is 0 (unannotated). Failure (no period, < 3 peaks, flat or too short input) -> no segments.
Segments use the dataset .tsv layout [start_s, end_s, label] (1 S1, 2 systole, 3 S2, 4 diastole) and are mapped
to the level-4 WPD column grid with the same ``column_labels`` used for the expert annotation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import butter, find_peaks, hilbert, sosfiltfilt

from ..wavelets.bands import column_labels

# pre-registered constants (protocol_v2.json) -- change only through a dated amendment
BAND_HZ = (25.0, 400.0)
ENV_LP_HZ = 8.0
ENV_FS = 50
PERIOD_RANGE_S = (0.3, 1.5)
MIN_PEAK_SPACING_T = 0.2
PEAK_HEIGHT_PCTL = 25
SOUND_REL_LEVEL = 0.5
SOUND_WIDTH_S = (0.040, 0.160)
# implementation details the protocol leaves open (amendment I2)
BAND_ORDER = 4           # Butterworth, zero-phase, as the v1 25-900 Hz band-pass
ENV_LP_ORDER = 1         # Butterworth, zero-phase (Springer et al. 2016 homomorphic envelope)
LOG_EPS = 1e-12
S1, SYS, S2, DIA = 1, 2, 3, 4


@dataclass
class AutoSeg:
    segments: np.ndarray                     # (n, 3) [start_s, end_s, label], labels 1-4 only
    period_s: float | None = None
    n_peaks: int = 0
    failure: str | None = None               # None = segmented; otherwise the reason for no segments
    info: dict = field(default_factory=dict)


def homomorphic_envelope(x: np.ndarray, fs: float) -> np.ndarray:
    """|Hilbert| of the 25-400 Hz band -> log -> 8 Hz low-pass -> exp, sampled at ENV_FS."""
    xb = sosfiltfilt(butter(BAND_ORDER, BAND_HZ, btype="bandpass", fs=fs, output="sos"), x)
    lp = butter(ENV_LP_ORDER, ENV_LP_HZ, btype="low", fs=fs, output="sos")
    env = np.exp(sosfiltfilt(lp, np.log(np.abs(hilbert(xb)) + LOG_EPS)))
    return env[:: int(round(fs / ENV_FS))]


def heart_period(env: np.ndarray) -> float | None:
    """Lag (s) of the highest local maximum of the normalised autocorrelation in PERIOD_RANGE_S, else None."""
    lo, hi = (int(round(t * ENV_FS)) for t in PERIOD_RANGE_S)
    e = env - env.mean()
    den = float(np.dot(e, e))
    if e.size <= hi + 1 or not np.isfinite(den) or den <= 0:
        return None
    ac = np.array([np.dot(e[: e.size - k], e[k:]) for k in range(hi + 2)]) / den
    cand = [k for k in range(lo, hi + 1) if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1]]
    if not cand:
        return None
    return max(cand, key=lambda k: ac[k]) / ENV_FS


def interval_states(peaks: np.ndarray) -> np.ndarray:
    """State of each inter-peak interval: SYS / DIA from pairwise comparison, 0 if unpaired, tied or not alternating."""
    d = np.diff(peaks)
    st = np.zeros(d.size, dtype=int)
    for k in range(0, d.size - 1, 2):
        if d[k] < d[k + 1]:
            st[k], st[k + 1] = SYS, DIA
        elif d[k] > d[k + 1]:
            st[k], st[k + 1] = DIA, SYS
    valid = st.copy()
    for i in range(st.size):
        if st[i] and ((i > 0 and st[i - 1] == st[i]) or (i + 1 < st.size and st[i + 1] == st[i])):
            valid[i] = 0
    return valid


def _sound_extent(env: np.ndarray, p: int) -> tuple[float, float]:
    thr = SOUND_REL_LEVEL * env[p]
    l = r = p
    while l > 0 and env[l - 1] >= thr:
        l -= 1
    while r < env.size - 1 and env[r + 1] >= thr:
        r += 1
    t0, t1, tp = (l - 0.5) / ENV_FS, (r + 0.5) / ENV_FS, p / ENV_FS
    wmin, wmax = SOUND_WIDTH_S
    if t1 - t0 < wmin:
        c = (t0 + t1) / 2
        t0, t1 = c - wmin / 2, c + wmin / 2
    elif t1 - t0 > wmax:
        t0, t1 = tp - wmax / 2, tp + wmax / 2
    return t0, t1


def autoseg(x: np.ndarray, fs: float = 2000) -> AutoSeg:
    """Segment one preprocessed recording. Returns AutoSeg with an empty segment array on failure."""
    empty = np.zeros((0, 3))
    x = np.asarray(x, dtype=float)
    dur = x.size / fs
    lo_hi_lag = int(round(PERIOD_RANGE_S[1] * ENV_FS)) + 2
    if x.size < (lo_hi_lag + 1) * int(round(fs / ENV_FS)) or not np.isfinite(x).all() or x.std() == 0:
        return AutoSeg(empty, failure="flat_or_too_short")
    env = homomorphic_envelope(x, fs)
    T = heart_period(env)
    if T is None:
        return AutoSeg(empty, failure="no_period")
    dist = max(1, int(np.ceil(MIN_PEAK_SPACING_T * T * ENV_FS)))
    pk, _ = find_peaks(env, height=np.percentile(env, PEAK_HEIGHT_PCTL), distance=dist)
    if pk.size < 3:
        return AutoSeg(empty, period_s=T, n_peaks=int(pk.size), failure="lt3_peaks")
    st = interval_states(pk)
    lab = np.zeros(pk.size, dtype=int)            # sound label of each peak
    for j in range(pk.size):
        after = st[j] if j < st.size else 0
        before = st[j - 1] if j > 0 else 0
        if after == SYS or before == DIA:
            lab[j] = S1
        elif after == DIA or before == SYS:
            lab[j] = S2
    ext = {j: list(_sound_extent(env, int(pk[j]))) for j in np.flatnonzero(lab)}
    js = sorted(ext)
    for a, b in zip(js, js[1:]):                  # overlapping sounds: split at the midpoint of the two peaks
        if ext[a][1] > ext[b][0]:
            m = (pk[a] + pk[b]) / 2 / ENV_FS
            ext[a][1], ext[b][0] = m, m
    segs = []
    for j in js:
        t0, t1 = max(0.0, ext[j][0]), min(dur, ext[j][1])
        if t1 > t0:
            segs.append((t0, t1, lab[j]))
    for i in np.flatnonzero(st):
        if lab[i] and lab[i + 1]:
            t0, t1 = ext[i][1], ext[i + 1][0]
            if t1 > t0:
                segs.append((max(0.0, t0), min(dur, t1), st[i]))
    if not segs:
        return AutoSeg(empty, period_s=T, n_peaks=int(pk.size), failure="no_valid_pairing")
    seg = np.array(sorted(segs), dtype=float)
    return AutoSeg(seg, period_s=T, n_peaks=int(pk.size),
                   info=dict(n_valid_intervals=int((st > 0).sum()), n_intervals=int(st.size)))


def autoseg_column_labels(x: np.ndarray, fs: float = 2000, depth: int = 4) -> np.ndarray:
    """Per-column labels 0-4 on the level-`depth` WPD grid (ceil(N / 2**depth) columns)."""
    hop = 2 ** depth
    return column_labels(autoseg(x, fs).segments, int(np.ceil(np.asarray(x).size / hop)), hop, fs)


def write_tsv(path: str, segments: np.ndarray, duration_s: float) -> None:
    """Write segments in the dataset .tsv layout (start, end, label), with label-0 rows filling the gaps."""
    rows, t = [], 0.0
    for s, e, l in segments:
        if s > t:
            rows.append((t, s, 0))
        rows.append((s, e, int(l)))
        t = e
    if duration_s > t:
        rows.append((t, duration_s, 0))
    with open(path, "w") as f:
        f.write("\n".join(f"{s:.6f}\t{e:.6f}\t{l}" for s, e, l in rows) + ("\n" if rows else ""))
