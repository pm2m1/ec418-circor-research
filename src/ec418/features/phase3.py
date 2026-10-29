"""Phase-3 feature helpers (pre-registered in docs/PROTOCOL_V3_PREREG.md).

* scattering features (G4) — needs kymatio 0.3.0 (separate env `.venv-scat`, scipy 1.14)
* whole-signal feature sets for external validation (G1a) — main env
"""
from __future__ import annotations

import numpy as np
import soundfile as sf

from ..wavelets.bands import column_labels, wpd_energy_map, stft_energy_map
from .extract import EPS, aligned_features, whole_features, MIN_SYS_COLUMNS, MIN_DIA_COLUMNS

SMOOTH_KER = np.hanning(6)[1:-1]
SMOOTH_KER = SMOOTH_KER / SMOOTH_KER.sum()     # 4-tap Hann over level-4 columns = 64 samples at 2 kHz (as scripts/10)
SCAT_J, SCAT_Q, SCAT_OVERSAMPLING, SCAT_BLOCK = 6, (8, 1), 2, 1024
_scat_cache: dict = {}


def load_any_wav(path: str) -> tuple[np.ndarray, int]:
    """Read a WAV; for multi-channel files take channel 0 (ZCHSound stereo files have identical channels)."""
    x, fs = sf.read(path, dtype="float64", always_2d=True)
    if x.size == 0:
        raise ValueError(f"{path}: empty")
    return x[:, 0], int(fs)


# ------------------------------------------------------------------ scattering (G4)
def scattering_maps(x2k: np.ndarray):
    """Return (E1, E2, n_cols): squared 1st/2nd-order scattering coefficients on the 16-sample (8 ms) grid."""
    from kymatio.numpy import Scattering1D
    n = (x2k.size // SCAT_BLOCK) * SCAT_BLOCK
    if n < 4 * SCAT_BLOCK:
        raise ValueError("signal too short for scattering")
    if n not in _scat_cache:
        S = Scattering1D(J=SCAT_J, shape=n, Q=SCAT_Q, oversampling=SCAT_OVERSAMPLING)
        _scat_cache[n] = (S, S.meta()["order"])
    S, order = _scat_cache[n]
    out = S(x2k[:n])
    assert out.shape[1] * 16 == n, out.shape
    return out[order == 1] ** 2, out[order == 2] ** 2, out.shape[1]


def scattering_feature_sets(x2k: np.ndarray, seg: np.ndarray, fs: int = 2000) -> dict:
    E1, E2, n_cols = scattering_maps(x2k)
    lab = column_labels(seg, n_cols, 16, fs)
    a1 = aligned_features(E1, lab, "scatA")
    a12 = None
    if a1 is not None:
        sys_m, dia_m = lab == 2, lab == 4
        es2 = E2[:, sys_m].mean(axis=1) + EPS
        ed2 = E2[:, dia_m].mean(axis=1) + EPS
        a12 = dict(a1)
        for p in range(E2.shape[0]):
            a12[f"scatA2_sdratio{p:03d}"] = float(np.log(es2[p] / ed2[p]))
    return {"A_scat1": a1, "A_scat12": a12, "W_scat1": whole_features(E1, "scatW")}


# ------------------------------------------------------------------ whole-signal sets (G1a)
def whole_signal_sets(x2k: np.ndarray, fs: int = 2000) -> dict:
    from .extract import acoustic_features
    Ew = wpd_energy_map(x2k, "db4", 4)
    Es = stft_energy_map(x2k, fs, 4)
    n = min(Ew.shape[1], Es.shape[1])
    Ews = np.vstack([np.convolve(e, SMOOTH_KER, mode="same") for e in Ew[:, :n]])
    return {"W_stft": whole_features(Es[:, :n], "stftW"),
            "W_wpd_db4": whole_features(Ew[:, :n], "wpdW"),
            "W_wpd_db4_smooth": whole_features(Ews, "wpdWs"),
            "B0": acoustic_features(x2k, fs)}
