"""Phase-2 E4: automatic span selector (docs/PROTOCOL_V2_LOCKED.md "E4").

Per non-overlapping 1-s window (125 level-4 columns, 50 HSMM samples, 4,000 raw samples; a trailing partial window is
dropped) the detector predicts whether the expert annotated it (>= 50 % of its columns labelled 1-4). It uses only the
recording's audio and the patient's LR-HSMM model, never murmur labels or patient metadata. Features (pre-registered):
  0 log10 P(20-200 Hz) / P(0-1000 Hz)        1 log10 P(25-400 Hz) / P(0-2000 Hz)   (raw 4 kHz, Hann power spectrum)
  2 envelope periodicity (E1 homomorphic envelope, 3-s context, autocorrelation local max at 0.3-1.5 s)
  3 kurtosis of the 500-1000 Hz band           4 clipping fraction (|int16| >= 32767)
  5 mean over the window of max-state LR-HSMM probability P(state | o)
Model: StandardScaler + L2 logistic regression (C = 1.0); threshold = training-window quantile matching the training
annotated fraction. NaN feature values (e.g. kurtosis of a constant window) are set to 0 before scaling.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt
from scipy.stats import kurtosis
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .autoseg import homomorphic_envelope

FS_RAW, FS2, ENV_FS, HOP = 4000, 2000, 50, 16
WIN_COLS, WIN_ENV, WIN_RAW = 125, 50, 4000
CTX_ENV = 150                                    # 3-s context for the periodicity feature
LAG_LO, LAG_HI = 15, 75                          # 0.3-1.5 s at 50 Hz
EPS = 1e-12
FEATURES = ["log_ratio_20_200_over_0_1000", "log_frac_25_400", "env_periodicity", "kurtosis_500_1000",
            "clipping_frac", "hsmm_max_state_prob"]


def n_windows(n_cols: int, n_raw: int) -> int:
    return min(n_cols // WIN_COLS, n_raw // WIN_RAW)


def _periodicity(e: np.ndarray) -> float:
    e = e - e.mean()
    den = float(np.dot(e, e))
    if e.size <= LAG_HI + 1 or den <= 0 or not np.isfinite(den):
        return 0.0
    ac = np.array([np.dot(e[: e.size - k], e[k:]) for k in range(LAG_HI + 2)]) / den
    peaks = [ac[k] for k in range(LAG_LO, LAG_HI + 1) if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1]]
    return float(max(peaks)) if peaks else 0.0


def signal_window_features(raw_i16: np.ndarray, x2: np.ndarray, n_cols: int) -> np.ndarray:
    """Features 0-4 for every full window, shape (n_win, 5). raw_i16: 4 kHz int16; x2: v1-preprocessed 2 kHz."""
    x = raw_i16.astype(float)
    nw = n_windows(n_cols, x.size)
    hp = sosfiltfilt(butter(4, [500, 1000], btype="bandpass", fs=FS_RAW, output="sos"), x)
    env = homomorphic_envelope(x2, FS2)
    f = np.fft.rfftfreq(WIN_RAW, 1 / FS_RAW)
    m20, m1k, m25 = (f >= 20) & (f <= 200), f <= 1000, (f >= 25) & (f <= 400)
    hann = np.hanning(WIN_RAW)
    out = np.zeros((nw, 5))
    for w in range(nw):
        seg = x[w * WIN_RAW:(w + 1) * WIN_RAW]
        P = np.abs(np.fft.rfft((seg - seg.mean()) * hann)) ** 2
        out[w, 0] = np.log10((P[m20].sum() + EPS) / (P[m1k].sum() + EPS))
        out[w, 1] = np.log10((P[m25].sum() + EPS) / (P.sum() + EPS))
        c = w * WIN_ENV + WIN_ENV // 2
        st = int(np.clip(c - CTX_ENV // 2, 0, max(0, env.size - CTX_ENV)))
        out[w, 2] = _periodicity(env[st: st + CTX_ENV])
        out[w, 3] = kurtosis(hp[w * WIN_RAW:(w + 1) * WIN_RAW], fisher=True)
        out[w, 4] = np.mean(np.abs(raw_i16[w * WIN_RAW:(w + 1) * WIN_RAW].astype(int)) >= 32767)
    return out


def hsmm_window_confidence(state_probs: np.ndarray, nw: int) -> np.ndarray:
    """Feature 5: mean over each window's 50 Hz samples of max over states of P(state | o)."""
    m = state_probs.max(axis=1)
    return np.array([m[w * WIN_ENV:(w + 1) * WIN_ENV].mean() if m[w * WIN_ENV:(w + 1) * WIN_ENV].size else np.nan
                     for w in range(nw)])


def window_targets(expert_cols: np.ndarray, nw: int) -> np.ndarray:
    return np.array([(expert_cols[w * WIN_COLS:(w + 1) * WIN_COLS] > 0).mean() >= 0.5 for w in range(nw)], dtype=int)


def column_mask(selected: np.ndarray, n_cols: int) -> np.ndarray:
    """Columns inside predicted-annotated windows; the trailing partial window is never selected."""
    mask = np.zeros(n_cols, dtype=bool)
    for w in np.flatnonzero(selected):
        mask[w * WIN_COLS:(w + 1) * WIN_COLS] = True
    return mask


@dataclass
class SpanDetector:
    scaler: StandardScaler
    lr: LogisticRegression
    threshold: float
    train_annotated_frac: float
    train_predicted_frac: float
    n_train_windows: int

    def proba(self, X: np.ndarray) -> np.ndarray:
        return self.lr.predict_proba(self.scaler.transform(np.nan_to_num(X, nan=0.0)))[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.proba(X) >= self.threshold).astype(int)


def fit_detector(X: np.ndarray, y: np.ndarray) -> SpanDetector:
    X = np.nan_to_num(X, nan=0.0)
    sc = StandardScaler().fit(X)
    lr = LogisticRegression(C=1.0, max_iter=1000).fit(sc.transform(X), y)
    p = lr.predict_proba(sc.transform(X))[:, 1]
    frac = float(y.mean())
    thr = float(np.quantile(p, 1 - frac)) if 0 < frac < 1 else (0.0 if frac == 1 else 1.0 + 1e-9)
    return SpanDetector(sc, lr, thr, frac, float((p >= thr).mean()), int(len(y)))
