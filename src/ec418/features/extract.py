"""Recording-level feature extractors (all training-independent: no statistics are fitted on
other recordings or patients) and patient-level aggregation.

Feature families (each 34-dim for the 2x2 ablation, see docs/PROTOCOL_LOCKED.md):
  WHOLE-signal pooling   : rel_b, burst_b (16+16), spectral entropy, mean frame entropy
  CYCLE-aligned pooling  : sysrel_b, sdratio_b (16+16), systolic entropy, diastolic entropy
crossed with the band-energy map:
  WPD  (wavelet packets, depth 4, 62.5 Hz nominal bands at fs=2 kHz)
  STFT (Hann 64-sample frames, hop 16, identical nominal bands)  -- the non-wavelet control

B0 is a conventional acoustic set (MFCC means + 4 spectral descriptors + envelope CV).
"""
from __future__ import annotations

import numpy as np

from ..wavelets.bands import column_labels, stft_energy_map, wpd_energy_map

EPS = 1e-12
MIN_SYS_COLUMNS = 40     # >= 40 level-4 columns = 0.32 s of annotated systole at 2 kHz
MIN_DIA_COLUMNS = 40
MIN_S1_COLUMNS = 10


def _entropy(p: np.ndarray) -> float:
    p = p[p > 0]
    p = p / p.sum()
    return float(-(p * np.log2(p)).sum())


def whole_features(E: np.ndarray, prefix: str) -> dict:
    E = E[:, ~np.isnan(E).any(axis=0)]
    nb = E.shape[0]
    mean_b = E.mean(axis=1) + EPS
    tot = mean_b.sum()
    f = {}
    for b in range(nb):
        f[f"{prefix}_rel{b:02d}"] = float(np.log(mean_b[b] / tot))
    for b in range(nb):
        q90, q50 = np.percentile(E[b], [90, 50])
        f[f"{prefix}_burst{b:02d}"] = float(np.log((q90 + EPS) / (q50 + EPS)))
    f[f"{prefix}_entropy"] = _entropy(mean_b)
    frame_ent = [_entropy(E[:, k] + EPS) for k in range(0, E.shape[1], 4)]
    f[f"{prefix}_frame_entropy"] = float(np.mean(frame_ent))
    return f


def aligned_features(E: np.ndarray, labels: np.ndarray, prefix: str) -> dict | None:
    """Cycle-aligned pooling. Returns None when segmentation coverage is insufficient."""
    valid = ~np.isnan(E).any(axis=0)
    sys_m = (labels == 2) & valid
    dia_m = (labels == 4) & valid
    s1_m = (labels == 1) & valid
    if sys_m.sum() < MIN_SYS_COLUMNS or dia_m.sum() < MIN_DIA_COLUMNS or s1_m.sum() < MIN_S1_COLUMNS:
        return None
    nb = E.shape[0]
    es = E[:, sys_m].mean(axis=1) + EPS
    ed = E[:, dia_m].mean(axis=1) + EPS
    e1 = E[:, s1_m].mean(axis=1).sum() + EPS
    f = {}
    for b in range(nb):
        f[f"{prefix}_sysrel{b:02d}"] = float(np.log(es[b] / e1))
    for b in range(nb):
        f[f"{prefix}_sdratio{b:02d}"] = float(np.log(es[b] / ed[b]))
    f[f"{prefix}_sys_entropy"] = _entropy(es)
    f[f"{prefix}_dia_entropy"] = _entropy(ed)
    return f


def band_feature_sets(x2k: np.ndarray, seg: np.ndarray, fs: int = 2000, wavelet: str = "db4",
                      depth: int = 4) -> dict:
    """Compute the four 2x2-ablation feature dicts for one preprocessed recording."""
    hop = 2 ** depth
    Ew = wpd_energy_map(x2k, wavelet, depth)
    Es = stft_energy_map(x2k, fs, depth)
    n = min(Ew.shape[1], Es.shape[1])
    Ew, Es = Ew[:, :n], Es[:, :n]
    lab = column_labels(seg, n, hop, fs)
    return {
        "W_wpd": whole_features(Ew, "wpdW"),
        "W_stft": whole_features(Es, "stftW"),
        "A_wpd": aligned_features(Ew, lab, "wpdA"),
        "A_stft": aligned_features(Es, lab, "stftA"),
        "seg_cov": dict(sys_cols=int((lab == 2).sum()), dia_cols=int((lab == 4).sum()),
                        s1_cols=int((lab == 1).sum()), unannot_frac=float((lab == 0).mean())),
    }


def acoustic_features(x2k: np.ndarray, fs: int = 2000) -> dict:
    """B0: conventional (non-wavelet) acoustic descriptors on the preprocessed signal."""
    import librosa
    n_fft, hop = 256, 64
    mf = librosa.feature.mfcc(y=x2k.astype(np.float32), sr=fs, n_mfcc=13, n_fft=n_fft, hop_length=hop,
                              n_mels=32, fmin=20, fmax=fs / 2)
    S = np.abs(librosa.stft(x2k.astype(np.float32), n_fft=n_fft, hop_length=hop)) ** 2
    cen = librosa.feature.spectral_centroid(S=S, sr=fs)[0]
    bw = librosa.feature.spectral_bandwidth(S=S, sr=fs)[0]
    ro = librosa.feature.spectral_rolloff(S=S, sr=fs, roll_percent=0.85)[0]
    zcr = librosa.feature.zero_crossing_rate(x2k, frame_length=n_fft, hop_length=hop)[0]
    rms = librosa.feature.rms(y=x2k, frame_length=n_fft, hop_length=hop)[0]
    f = {f"b0_mfcc{i:02d}": float(mf[i].mean()) for i in range(13)}
    f.update(b0_centroid=float(cen.mean()), b0_bandwidth=float(bw.mean()), b0_rolloff=float(ro.mean()),
             b0_zcr=float(zcr.mean()), b0_rms_cv=float(rms.std() / (rms.mean() + EPS)))
    return f


def aggregate_patient(rec_feats, feature_cols, patient_col="patient_id"):
    """Patient vector = [median over recordings, max over recordings] per feature (NaN-aware).

    Median summarises the typical site; max mirrors the clinical rule 'murmur present at any
    auscultation site'. Fixed a priori; not tuned."""
    import pandas as pd
    g = rec_feats.groupby(patient_col)[feature_cols]
    med = g.median().add_suffix("__med")
    mx = g.max().add_suffix("__max")
    return pd.concat([med, mx], axis=1)
