import numpy as np
import pytest
import pywt

from ec418.wavelets.bands import (column_labels, nominal_dwt_bands, nominal_packet_bands, stft_energy_map,
                                  wpd_energy_map)


def test_band_width_math():
    # Issue A of the dossier: fs=2000, J=4 -> 62.5 Hz; fs=4000, J=4 -> 125 Hz
    b2 = nominal_packet_bands(2000, 4)
    b4 = nominal_packet_bands(4000, 4)
    assert b2.shape == (16, 2) and b4.shape == (16, 2)
    assert np.allclose(b2[:, 1] - b2[:, 0], 62.5)
    assert np.allclose(b4[:, 1] - b4[:, 0], 125.0)
    assert b2[-1, 1] == 1000.0 and b4[-1, 1] == 2000.0


def test_dwt_band_table_4khz():
    t = {n: (lo, hi) for n, lo, hi in nominal_dwt_bands(4000, 6)}
    assert t["D1"] == (1000.0, 2000.0)
    assert t["D4"] == (125.0, 250.0)
    assert t["A6"] == (0.0, 31.25)


@pytest.mark.parametrize("wavelet", ["db4", "db6", "sym8", "coif3"])
def test_wpd_frequency_order(wavelet):
    fs, J = 2000, 4
    t = np.arange(fs * 4) / fs
    for b in [1, 3, 6, 10, 14]:
        f0 = (b + 0.5) * 62.5            # centre of nominal band b
        E = wpd_energy_map(np.sin(2 * np.pi * f0 * t), wavelet, J)
        assert E.shape[0] == 16
        assert int(np.argmax(E.sum(axis=1))) == b, f"{wavelet}: tone at {f0} Hz landed in wrong band"


def test_natural_order_is_not_frequency_order():
    fs, J = 2000, 4
    t = np.arange(fs * 2) / fs
    x = np.sin(2 * np.pi * (10.5 * 62.5) * t)
    wp = pywt.WaveletPacket(x, "db4", mode="periodization", maxlevel=J)
    nat = np.array([np.sum(n.data ** 2) for n in wp.get_level(J, order="natural")])
    frq = np.array([np.sum(n.data ** 2) for n in wp.get_level(J, order="freq")])
    assert np.argmax(frq) == 10
    assert np.argmax(nat) != 10   # documents why order='freq' is required


@pytest.mark.parametrize("wavelet", ["db4", "sym8"])
def test_wpd_energy_conservation_and_shape(wavelet):
    rng = np.random.default_rng(0)
    x = rng.standard_normal(4096)
    E = wpd_energy_map(x, wavelet, 4)
    assert E.shape == (16, 4096 // 16)
    # orthonormal wavelets + periodization => Parseval: energy preserved
    assert np.isclose(E.sum(), np.sum(x ** 2), rtol=1e-8)


def test_wpd_reconstruction():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(2048)
    wp = pywt.WaveletPacket(x, "db4", mode="periodization", maxlevel=4)
    for n in wp.get_level(4):
        pass
    assert np.allclose(wp.reconstruct(update=False), x, atol=1e-10)


def test_leakage_shrinks_with_longer_filters():
    """Nominal bands are idealised: measure out-of-band energy for a band-centre tone."""
    fs = 2000
    t = np.arange(fs * 4) / fs
    x = np.sin(2 * np.pi * (5.5 * 62.5) * t)
    frac = {}
    for w in ["db4", "sym8", "coif3"]:
        e = wpd_energy_map(x, w, 4).sum(axis=1)
        frac[w] = 1 - e[5] / e.sum()
    assert frac["db4"] > frac["sym8"]
    assert all(0 < v < 0.5 for v in frac.values())


def test_stft_map_same_grid_and_bands():
    fs = 2000
    t = np.arange(fs * 3) / fs
    x = np.sin(2 * np.pi * (7.5 * 62.5) * t)
    E = stft_energy_map(x, fs, 4)
    assert E.shape == (16, int(np.ceil(x.size / 16)))
    col = np.nanargmax(np.nansum(E, axis=1))
    assert col == 7


def test_column_labels_mapping():
    seg = np.array([[0.0, 0.1, 1], [0.1, 0.3, 2], [0.3, 0.4, 3], [0.4, 0.8, 4]])
    lab = column_labels(seg, n_cols=125, hop_samples=16, fs=2000)  # 125*8 ms = 1 s
    assert lab[0] == 1 and lab[20] == 2 and lab[45] == 3 and lab[60] == 4 and lab[110] == 0


def test_short_signal_raises():
    with pytest.raises(ValueError):
        wpd_energy_map(np.ones(8), "db4", 4)
