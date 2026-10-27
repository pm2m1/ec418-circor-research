"""Signal I/O and conditioning for CirCor PCG recordings.

Design decisions (locked in docs/PROTOCOL_LOCKED.md):
* WAV files are 16-bit mono at 4000 Hz; we assert that rather than trusting headers.
* Resampling 4000 -> 2000 Hz uses scipy.signal.resample_poly (polyphase FIR with a Kaiser
  window anti-aliasing low-pass, cutoff at the new Nyquist = 1000 Hz). All content above
  ~1 kHz is discarded; PCG murmur energy of clinical interest lies well below that.
* A zero-phase 4th-order Butterworth band-pass 25-900 Hz (sosfiltfilt) removes baseline
  wander / sub-audible motion and keeps a guard band below the 1 kHz Nyquist.
* Amplitude normalisation: divide by the robust scale (median absolute value * 1.4826 ...)
  is NOT used for features that are already gain-invariant; for features that are not, we
  z-normalise per recording (mean 0, std 1). Nothing here is fitted on other patients.
"""
from __future__ import annotations

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfiltfilt

FS_RAW = 4000


def load_wav(path: str, expected_fs: int = FS_RAW) -> np.ndarray:
    x, fs = sf.read(path, dtype="float64", always_2d=False)
    if fs != expected_fs:
        raise ValueError(f"{path}: fs={fs}, expected {expected_fs}")
    if x.ndim != 1:
        raise ValueError(f"{path}: expected mono, got shape {x.shape}")
    if x.size == 0:
        raise ValueError(f"{path}: empty recording")
    return x


def resample(x: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    if fs_in == fs_out:
        return x.copy()
    g = np.gcd(fs_in, fs_out)
    return resample_poly(x, fs_out // g, fs_in // g)


def bandpass(x: np.ndarray, fs: int, lo: float = 25.0, hi: float = 900.0, order: int = 4) -> np.ndarray:
    if hi >= fs / 2:
        raise ValueError("high cut-off must be below Nyquist")
    sos = butter(order, [lo, hi], btype="bandpass", fs=fs, output="sos")
    if x.size < 3 * (2 * order + 1) * 2:
        raise ValueError("signal too short to filter")
    return sosfiltfilt(sos, x)


def znorm(x: np.ndarray) -> np.ndarray:
    s = x.std()
    if not np.isfinite(s) or s < 1e-12:
        raise ValueError("constant (flat-line) signal cannot be normalised")
    return (x - x.mean()) / s


def preprocess(x: np.ndarray, fs_in: int = FS_RAW, fs_out: int = 2000,
               lo: float = 25.0, hi: float = 900.0) -> np.ndarray:
    return znorm(bandpass(resample(x, fs_in, fs_out), fs_out, lo, hi))
