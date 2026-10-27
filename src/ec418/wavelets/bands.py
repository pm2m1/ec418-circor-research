"""Wavelet-packet and matched-STFT band-energy maps.

Frequency bookkeeping (real-valued signal sampled at fs):
    Nyquist bandwidth            = fs / 2
    packet bands at depth J      = 2**J
    nominal packet band width    = fs / (2 * 2**J)
    fs = 2000, J = 4  ->  16 bands of 62.5 Hz  (0-62.5, 62.5-125, ..., 937.5-1000 Hz)
    fs = 4000, J = 4  ->  16 bands of 125 Hz
    DWT detail level j covers nominally [fs / 2**(j+1), fs / 2**j]; approximation at level J
    covers [0, fs / 2**(J+1)].

These are NOMINAL (ideal brick-wall) ranges. Real finite-length filters (db4: 8 taps, sym8:
16 taps, coif3: 18 taps) have transition bands and side-lobes, so energy leaks into
neighbouring packets; longer filters leak less. tests/test_wavelets.py measures this.

Packet ordering: pywt's ``get_level(J, order='natural')`` returns Paley (filter-bank) order,
which is NOT frequency order because each high-pass split mirrors the spectrum. We always use
``order='freq'`` (Gray-code corrected) so feature index b corresponds to nominal band b.

Boundary handling: mode='periodization' gives exactly ceil(N/2) coefficients per split, so a
level-J coefficient k maps to input samples [k*2**J, (k+1)*2**J) (ignoring the filter group
delay of a few coefficients). Wrap-around only contaminates the first/last ~filter_len
coefficients of a ~20 s recording (<0.5 % of coefficients).
"""
from __future__ import annotations

import numpy as np
import pywt
from scipy.signal import stft


def nominal_packet_bands(fs: float, depth: int) -> np.ndarray:
    n = 2 ** depth
    w = fs / 2 / n
    return np.array([[b * w, (b + 1) * w] for b in range(n)])


def nominal_dwt_bands(fs: float, levels: int) -> list[tuple[str, float, float]]:
    out = []
    for j in range(1, levels + 1):
        out.append((f"D{j}", fs / 2 ** (j + 1), fs / 2 ** j))
    out.append((f"A{levels}", 0.0, fs / 2 ** (levels + 1)))
    return out


def wpd_energy_map(x: np.ndarray, wavelet: str = "db4", depth: int = 4) -> np.ndarray:
    """Return E[b, k]: squared level-`depth` packet coefficients, bands in frequency order.

    Column k covers input samples [k*2**depth, (k+1)*2**depth)."""
    if x.size < 2 ** depth:
        raise ValueError("signal shorter than one level-J coefficient")
    wp = pywt.WaveletPacket(data=x, wavelet=wavelet, mode="periodization", maxlevel=depth)
    nodes = wp.get_level(depth, order="freq")
    lens = {len(n.data) for n in nodes}
    assert len(lens) == 1
    return np.vstack([n.data ** 2 for n in nodes])


def stft_energy_map(x: np.ndarray, fs: float, depth: int = 4) -> np.ndarray:
    """Matched short-time Fourier band energies: same nominal bands and the same hop
    (2**depth samples) as the level-`depth` packet map, Hann window of 4*hop samples."""
    hop = 2 ** depth
    nper = 4 * hop
    f, t, Z = stft(x, fs=fs, window="hann", nperseg=nper, noverlap=nper - hop, boundary=None, padded=False)
    P = np.abs(Z) ** 2
    edges = nominal_packet_bands(fs, depth)
    nb = edges.shape[0]
    idx = np.minimum((f / (fs / 2 / nb)).astype(int), nb - 1)
    E = np.vstack([P[idx == b].sum(axis=0) for b in range(nb)])
    # frame m is centred at sample m*hop + nper/2 -> shift to align with packet column index
    shift = (nper // 2) // hop - 0  # frames start at t = nper/2
    n_cols = int(np.ceil(x.size / hop))
    out = np.full((nb, n_cols), np.nan)
    end = min(n_cols, shift + E.shape[1])
    out[:, shift:end] = E[:, : end - shift]
    return out


def column_labels(seg: np.ndarray, n_cols: int, hop_samples: int, fs: float) -> np.ndarray:
    """Assign each energy-map column (centre time) the segmentation label (0 = unannotated)."""
    lab = np.zeros(n_cols, dtype=int)
    if seg.shape[0] == 0:
        return lab
    centres = (np.arange(n_cols) * hop_samples + hop_samples / 2) / fs
    for s, e, l in seg:
        m = (centres >= s) & (centres < e)
        lab[m] = int(l)
    return lab
