"""Phase-2 E1b: logistic-regression HSMM heart-sound segmenter (docs/PROTOCOL_V2_LOCKED.md "E1b").

Python port of Springer, Tarassenko & Clifford, "Logistic Regression-HSMM-based Heart Sound Segmentation",
IEEE TBME 63(4):822-832, 2016, following the authors' MATLAB/C reference code (PhysioNet "hss" v1.0,
DOI 10.13026/vnt9-kf93): getSpringerPCGFeatures, schmidt_spike_removal, getHeartRateSchmidt,
trainBandPiMatricesSpringer, get_duration_distributions, viterbiDecodePCG_Springer + viterbi_Springer.c (the mex
version, use_mex = true). The reference code is GPL-3.0; this port is distributed under GPL-3.0 as well.

Deviation from the reference, pre-registered: the duration / heart-rate constants that the reference hard-codes for
adults are LEARNED from the training annotations (``learn_duration_params``); the PSD series is brought to the
envelope length by linear interpolation. Everything else uses the paper's fixed values.
Decoding uses only the recording's audio; annotations are used only by ``train``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pywt
from scipy.signal import butter, filtfilt, hilbert, resample_poly
from scipy.stats import multivariate_normal
from sklearn.linear_model import LogisticRegression

AUDIO_FS = 1000
FEAT_FS = 50
N_STATES = 4                      # 1 S1, 2 systole, 3 S2, 4 diastole (index 0..3 internally)
PI = np.full(N_STATES, 0.25)
FLT_MIN = np.finfo(np.float32).tiny
REALMIN = np.finfo(np.float64).tiny
MAX_D = 150                       # duration_probs[4][150] in viterbi_Springer.c


# ------------------------------------------------------------------ features (fixed, from the paper)
def _filtfilt(b, a, x):
    return filtfilt(b, a, x, padlen=3 * (max(len(a), len(b)) - 1))        # MATLAB filtfilt padding


def schmidt_spike_removal(x: np.ndarray, fs: int) -> np.ndarray:
    win = int(round(fs / 2))
    n_full = (x.size // win) * win
    if n_full == 0:
        return x.copy()
    frames = x[:n_full].reshape(-1, win).T.copy()                       # MATLAB column-major frames
    maas = np.abs(frames).max(axis=0)
    while np.any(maas > np.median(maas) * 3):
        w = int(np.argmax(maas))
        col = frames[:, w]
        p = int(np.argmax(np.abs(col)))
        zc = np.r_[np.abs(np.diff(np.sign(col))) > 1, False]
        before = np.flatnonzero(zc[: p + 1])
        start = before[-1] if before.size else 0
        zc[: p + 1] = False
        after = np.flatnonzero(zc)
        end = min(after[0], win - 1) if after.size else win - 1
        col[start: end + 1] = 0.0001
        maas = np.abs(frames).max(axis=0)
    return np.r_[frames.T.reshape(-1), x[n_full:]]


def springer_audio(x4k: np.ndarray, fs_in: int = 4000) -> np.ndarray:
    """4 kHz -> 1 kHz, Butterworth order-2 LP 400 Hz and HP 25 Hz (zero-phase), Schmidt spike removal."""
    x = resample_poly(np.asarray(x4k, float), AUDIO_FS, fs_in)
    b, a = butter(2, 2 * 400 / AUDIO_FS, "low")
    x = _filtfilt(b, a, x)
    b, a = butter(2, 2 * 25 / AUDIO_FS, "high")
    x = _filtfilt(b, a, x)
    return schmidt_spike_removal(x, AUDIO_FS)


def homomorphic_envelope(x: np.ndarray, fs: int, lpf: float = 8.0) -> np.ndarray:
    b, a = butter(1, 2 * lpf / fs, "low")
    env = np.exp(_filtfilt(b, a, np.log(np.maximum(np.abs(hilbert(x)), REALMIN))))
    env[0] = env[1]
    return env


def _z(v):
    return (v - v.mean()) / v.std(ddof=1)


def _psd_40_60(x: np.ndarray, fs: int) -> np.ndarray:
    """mean 40-60 Hz power of a Hamming(fs/40) spectrogram with round(fs/80) overlap at 1-Hz bins."""
    nw, nov = int(fs / 40), int(round(fs / 80))
    hop = nw - nov
    n_fr = (x.size - nov) // hop
    w = np.hamming(nw)
    idx = np.arange(nw)[None, :] + hop * np.arange(n_fr)[:, None]
    fr = x[idx] * w
    f = np.arange(40, 61)
    E = np.exp(-2j * np.pi * f[:, None] * np.arange(nw)[None, :] / fs)
    return (np.abs(fr @ E.T) ** 2).mean(axis=1)


def _wavelet_feature(x: np.ndarray, n_keep: int) -> np.ndarray:
    if x.size < AUDIO_FS * 1.025:
        x = np.r_[x, np.zeros(int(round(0.025 * AUDIO_FS)))]
    d3 = pywt.wavedec(x, "rbio3.9", mode="symmetric", level=3)[1]            # level-3 detail
    rep = np.repeat(d3, 2 ** 3)
    first = (rep.size - x.size) // 2                                         # wkeep1 central part
    cd = rep[first: first + x.size]
    cd = np.where(np.abs(cd) < np.sqrt(np.finfo(float).eps), 0.0, cd)
    return np.abs(cd)[:n_keep]


def springer_features(x4k: np.ndarray, fs_in: int = 4000) -> tuple[np.ndarray, np.ndarray]:
    """(F, ac): F = (n, 4) z-scored 50 Hz features [homomorphic, Hilbert, PSD, wavelet]; ac = autocorrelation
    (coefficient, lags 0..N-1) of the 1 kHz homomorphic envelope used for heart rate (getHeartRateSchmidt)."""
    x = springer_audio(x4k, fs_in)
    he = homomorphic_envelope(x, AUDIO_FS)
    down = AUDIO_FS // FEAT_FS
    f_he = _z(resample_poly(he, 1, down))
    f_hil = _z(resample_poly(np.abs(hilbert(x)), 1, down))
    psd = _psd_40_60(x, AUDIO_FS)
    f_psd = _z(np.interp(np.linspace(0, psd.size - 1, f_he.size), np.arange(psd.size), psd))
    f_wav = _z(resample_poly(_wavelet_feature(x, he.size), 1, down))
    n = min(f_he.size, f_hil.size, f_wav.size)
    F = np.column_stack([f_he[:n], f_hil[:n], f_psd[:n], f_wav[:n]])
    y = he - he.mean()
    m = 1 << int(np.ceil(np.log2(2 * y.size)))
    r = np.fft.irfft(np.abs(np.fft.rfft(y, m)) ** 2, m)[: y.size]
    return F, r / r[0]


# ------------------------------------------------------------------ learned duration / heart-rate parameters
def _rows(seg, lab):
    return seg[seg[:, 2] == lab] if seg.size else np.zeros((0, 3))


def learn_duration_params(segs: list[np.ndarray]) -> dict:
    """Paediatric replacements for the reference's adult constants, from expert rows (labels 1-4, end > start)."""
    d = {k: [] for k in (1, 2, 3, 4)}
    sys_ss, sys_dof, dia_mean, dia_sd, periods, ratios = [], [], [], [], [], []
    for seg in segs:
        for k in d:
            d[k].extend((_rows(seg, k)[:, 1] - _rows(seg, k)[:, 0]).tolist())
        s = _rows(seg, 2)[:, 1] - _rows(seg, 2)[:, 0]
        if s.size >= 2:
            sys_ss.append(((s - s.mean()) ** 2).sum()); sys_dof.append(s.size - 1)
        dd = _rows(seg, 4)[:, 1] - _rows(seg, 4)[:, 0]
        if dd.size >= 2:
            dia_mean.append(dd.mean()); dia_sd.append(dd.std(ddof=1))
        on1, on2 = _rows(seg, 1)[:, 0], _rows(seg, 3)[:, 0]
        if on1.size >= 2:
            T = float(np.median(np.diff(on1)))
            periods.append(T)
            lags = [on2[on2 > a][0] - a for a in on1 if np.any((on2 > a) & (on2 - a < T))]
            if lags:
                ratios.append(float(np.median(lags)) / T)
    a, b = np.polyfit(np.array(dia_mean), np.array(dia_sd), 1)
    return dict(mean_s1=float(np.mean(d[1])), sd_s1=float(np.std(d[1], ddof=1)),
                mean_s2=float(np.mean(d[3])), sd_s2=float(np.std(d[3], ddof=1)),
                sd_sys=float(np.sqrt(np.sum(sys_ss) / np.sum(sys_dof))), dia_a=float(a), dia_b=float(b),
                period_range=(float(np.percentile(periods, 1)), float(np.percentile(periods, 99))),
                sys_ratio_range=(float(np.percentile(ratios, 1)), float(np.percentile(ratios, 99))),
                n_recordings=len(segs), n_periods=len(periods))


def heart_rate(ac: np.ndarray, p: dict) -> tuple[float, float]:
    """getHeartRateSchmidt with the learned search ranges. Returns (period_s, systolic_interval_s)."""
    fs = AUDIO_FS
    lo, hi = int(round(p["period_range"][0] * fs)), int(round(p["period_range"][1] * fs))
    hi = min(hi, ac.size - 1)
    if hi <= lo:
        raise ValueError("recording too short for the heart-period search range")
    lag = lo + int(np.argmax(ac[lo: hi + 1]))
    T = lag / fs
    smin, smax = int(round(p["sys_ratio_range"][0] * T * fs)), int(round(p["sys_ratio_range"][1] * T * fs))
    smax = max(smax, smin)
    pos = int(np.argmax(ac[smin: smax + 1])) + 1                             # MATLAB 1-based position
    return T, (smin + pos) / fs


def duration_distributions(T: float, sys_t: float, p: dict):
    """get_duration_distributions with learned parameters (50 Hz samples). Returns means, vars, mins, maxs."""
    fs = FEAT_FS
    m1, s1 = round(p["mean_s1"] * fs), max(1, round(p["sd_s1"] * fs))
    m2, s2 = round(p["mean_s2"] * fs), max(1, round(p["sd_s2"] * fs))
    msys, ssys = round(sys_t * fs) - m1, p["sd_sys"] * fs
    mdia = (T - sys_t - p["mean_s2"]) * fs
    sdia = max(1.0, p["dia_a"] * mdia + p["dia_b"] * fs)
    means = np.array([m1, msys, m2, mdia], float)
    sds = np.array([s1, ssys, s2, sdia], float)
    mins = np.array([max(m1 - 3 * s1, fs / 50), msys - 3 * (ssys + s1), max(m2 - 3 * s2, fs / 50), mdia - 3 * sdia])
    maxs = np.array([m1 + 3 * s1, msys + 3 * (ssys + s1), m2 + 3 * s2, mdia + 3 * sdia])
    return means, sds ** 2, mins, maxs


# ------------------------------------------------------------------ model
@dataclass
class LRHSMM:
    coef: np.ndarray            # (4, 4) logistic-regression weights per state
    intercept: np.ndarray       # (4,)
    mu: np.ndarray
    cov: np.ndarray
    params: dict


def labels_50hz(seg: np.ndarray, n: int) -> np.ndarray:
    """Expert state at each 50 Hz sample time k/50 from valid rows (0 = not annotated)."""
    lab = np.zeros(n, dtype=int)
    t = np.arange(n) / FEAT_FS
    for s, e, l in seg:
        if l in (1, 2, 3, 4) and e > s:
            lab[(t >= s) & (t < e)] = int(l)
    return lab


def valid_rows(seg: np.ndarray) -> np.ndarray:
    if seg.size == 0:
        return np.zeros((0, 3))
    return seg[np.isin(seg[:, 2], [1, 2, 3, 4]) & (seg[:, 1] > seg[:, 0])]


def train(features: list[np.ndarray], segs: list[np.ndarray], seed: int) -> LRHSMM:
    """trainBandPiMatricesSpringer on the training recordings + learned duration parameters."""
    segs = [valid_rows(s) for s in segs]
    X, y = [], []
    for F, seg in zip(features, segs):
        lab = labels_50hz(seg, F.shape[0])
        m = lab > 0
        X.append(F[m]); y.append(lab[m])
    X, y = np.vstack(X), np.concatenate(y)
    rng = np.random.default_rng(seed)
    coef, inter = np.zeros((N_STATES, X.shape[1])), np.zeros(N_STATES)
    vals = [X[y == s + 1] for s in range(N_STATES)]
    for s in range(N_STATES):
        per_other = min(len(vals[s]) // (N_STATES - 1), min(len(vals[o]) for o in range(N_STATES) if o != s))
        pos = vals[s][rng.permutation(len(vals[s]))[: per_other * (N_STATES - 1)]]
        neg = np.vstack([vals[o][rng.permutation(len(vals[o]))[:per_other]] for o in range(N_STATES) if o != s])
        lr = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=1000)   # unpenalised, as mnrfit
        lr.fit(np.vstack([pos, neg]), np.r_[np.ones(len(pos)), np.zeros(len(neg))])
        coef[s], inter[s] = lr.coef_[0], lr.intercept_[0]
    return LRHSMM(coef, inter, X.mean(axis=0), np.cov(X, rowvar=False), learn_duration_params(segs))


def observation_probs(model: LRHSMM, F: np.ndarray) -> np.ndarray:
    p_state = 1.0 / (1.0 + np.exp(-(F @ model.coef.T + model.intercept)))
    p_o = multivariate_normal(model.mu, model.cov, allow_singular=True).pdf(F)
    return p_state * np.atleast_1d(p_o)[:, None] / PI


def viterbi(obs: np.ndarray, log_dur: np.ndarray, D: int) -> np.ndarray:
    """viterbi_Springer.c (extended duration Viterbi) + the backtracking of viterbiDecodePCG_Springer.
    obs (T, 4); log_dur (4, D) = log(duration_probs / duration_sum) for d = 1..D. Returns states 1..4 (T,)."""
    T = obs.shape[0]
    L = T + D - 1
    lo = np.log(np.where(obs == 0, FLT_MIN, obs))
    cs = np.vstack([np.zeros(N_STATES), np.cumsum(lo, axis=0)])
    delta = np.full((L, N_STATES), -np.inf)
    psi = np.zeros((L, N_STATES), dtype=int)
    psid = np.zeros((L, N_STATES), dtype=int)
    delta[0] = np.log(PI) + lo[0]
    prev = np.array([3, 0, 1, 2])                     # a_matrix: S1<-dia, sys<-S1, S2<-sys, dia<-S2
    d = np.arange(1, D + 1)
    ld = log_dur.T                                    # (D, 4)
    for t in range(1, L):
        start = np.clip(t - d, 0, T - 2)
        end = min(t, T - 1)
        v = delta[start][:, prev] + (cs[end + 1] - cs[start]) + ld
        b = np.argmax(v, axis=0)                      # first maximum over d, as the strict '>' in C
        best = v[b, np.arange(N_STATES)]
        upd = best > delta[t]
        delta[t, upd] = best[upd]
        psi[t, upd] = prev[upd]
        psid[t, upd] = d[b][upd]
    qt = np.zeros(L, dtype=int)
    tail = delta[T:]
    pos = int(np.unravel_index(np.argmax(tail), tail.shape)[0]) + T
    state = int(np.argmax(delta[pos]))
    offset = pos
    preceding = psi[offset, state]
    onset = offset - psid[offset, state] + 1
    qt[onset: offset + 1] = state + 1
    state = preceding
    count = 0
    while onset > 1:
        offset = onset - 1
        preceding = psi[offset, state]
        onset = offset - psid[offset, state] + 1
        if onset < 1:
            onset = 0
        qt[onset: offset + 1] = state + 1
        state = preceding
        count += 1
        if count > 1000:
            break
    return qt[:T]


def decode(model: LRHSMM, F: np.ndarray, ac: np.ndarray) -> tuple[np.ndarray, dict]:
    """Segment one recording: 50 Hz states 1..4 and decoding info (period, systolic interval, D)."""
    T, sys_t = heart_rate(ac, model.params)
    D = int(round(T * FEAT_FS))
    if not 1 <= D <= MAX_D:
        raise ValueError(f"max duration D={D} outside 1..{MAX_D}")
    means, var, mins, maxs = duration_distributions(T, sys_t, model.params)
    dd = np.arange(1, D + 1)[None, :]
    dp = np.exp(-((dd - means[:, None]) ** 2) / (2 * var[:, None])) / np.sqrt(2 * np.pi * var[:, None])
    dp = np.where((dd < mins[:, None]) | (dd > maxs[:, None]), REALMIN, dp)
    log_dur = np.log(dp) - np.log(dp.sum(axis=1, keepdims=True))    # finite for REALMIN entries, as in C
    qt = viterbi(observation_probs(model, F), log_dur, D)
    return qt, dict(period_s=T, systolic_s=sys_t, D=D)


def states_to_segments(qt: np.ndarray, duration_s: float) -> np.ndarray:
    """Runs of the 50 Hz state sequence -> [start_s, end_s, label]; sample k covers [(k-0.5)/50, (k+0.5)/50)."""
    if qt.size == 0:
        return np.zeros((0, 3))
    ch = np.flatnonzero(np.diff(qt)) + 1
    starts, ends = np.r_[0, ch], np.r_[ch, qt.size]
    seg = [(max(0.0, (a - 0.5) / FEAT_FS), min(duration_s, (b - 0.5) / FEAT_FS), int(qt[a]))
           for a, b in zip(starts, ends) if qt[a] > 0]
    return np.array([s for s in seg if s[1] > s[0]], dtype=float).reshape(-1, 3)
