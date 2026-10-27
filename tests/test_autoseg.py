import inspect

import numpy as np
import pytest

from ec418.data.circor import load_segmentation
from ec418.segmentation import autoseg as A
from ec418.wavelets.bands import wpd_energy_map

FS = 2000


def _pcg(period=0.8, systole=0.3, dur=20.0, seed=0, jitter=0.0, noise=0.0):
    """Synthetic PCG: 60 ms Hann-windowed 60/90 Hz bursts for S1/S2, optional white noise.

    Noise-free by default: with any background noise the homomorphic (log-domain) envelope turns noise bumps
    into scale-free local maxima that pass the pre-registered 25th-percentile / 0.2*T peak rule (documented in
    docs/E1_RESULTS.md; constants are locked)."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * FS)) / FS
    x = noise * rng.standard_normal(t.size)
    s1, s2, t0 = [], [], 0.1
    while t0 + systole + 0.1 < dur:
        for c, f, store in ((t0, 60.0, s1), (t0 + systole, 90.0, s2)):
            m = np.abs(t - c) < 0.03
            x[m] += np.hanning(m.sum()) * np.sin(2 * np.pi * f * t[m])
            store.append(c)
        t0 += period + (rng.uniform(-jitter, jitter) if jitter else 0.0)
    return (x - x.mean()) / x.std(), np.array(s1), np.array(s2)


def _centres(seg, label):
    return np.array([(s + e) / 2 for s, e, l in seg if l == label])


def _hit_rate(truth, found, tol=0.05):
    return np.mean([np.min(np.abs(found - c)) <= tol for c in truth]) if found.size else 0.0


def test_periodic_signal_is_segmented():
    x, s1, s2 = _pcg()
    r = A.autoseg(x, FS)
    assert r.failure is None and r.period_s == pytest.approx(0.8, abs=0.04)
    assert _hit_rate(s1, _centres(r.segments, A.S1)) >= 0.9
    assert _hit_rate(s2, _centres(r.segments, A.S2)) >= 0.9
    lab = A.autoseg_column_labels(x, FS)
    col = lambda tt: lab[int(tt * FS / 16)]
    inner = range(2, len(s1) - 2)
    assert np.mean([col(s1[i]) == A.S1 for i in inner]) >= 0.9
    assert np.mean([col(s2[i]) == A.S2 for i in inner]) >= 0.9
    assert np.mean([col(s1[i] + 0.15) == A.SYS for i in inner]) >= 0.9                    # mid-systole
    assert np.mean([col(s2[i] + 0.25) == A.DIA for i in inner]) >= 0.9                    # mid-diastole


@pytest.mark.parametrize("n", [8001, 12345, 40000, 65537])
def test_label_length_matches_wpd_grid(n):
    x = _pcg(dur=n / FS + 1)[0][:n]
    assert A.autoseg_column_labels(x, FS).size == wpd_energy_map(x, "db4", 4).shape[1]


def test_deterministic():
    x = _pcg(seed=3, noise=0.02)[0]
    a, b = A.autoseg(x, FS), A.autoseg(x.copy(), FS)
    assert np.array_equal(a.segments, b.segments) and a.period_s == b.period_s


@pytest.mark.parametrize("x", [np.zeros(20 * FS), np.ones(20 * FS), np.random.default_rng(1).standard_normal(FS // 2),
                               np.array([]), np.full(20 * FS, np.nan)])
def test_flat_short_or_invalid_input_gives_all_zero_labels(x):
    r = A.autoseg(x, FS)
    assert r.segments.shape == (0, 3) and r.failure is not None
    lab = A.autoseg_column_labels(x, FS)
    assert lab.size == int(np.ceil(x.size / 16)) and not lab.any()


def test_arrhythmic_input_does_not_crash():
    # irregular clicks (no consistent period). The pre-registered algorithm has no periodicity gate, so
    # labels are not guaranteed all-zero here; they must be well formed.
    rng = np.random.default_rng(7)
    t = np.arange(20 * FS) / FS
    x = 0.02 * rng.standard_normal(t.size)
    for c in np.cumsum(rng.uniform(0.15, 1.4, 40)):
        m = np.abs(t - c) < 0.03
        x[m] += np.hanning(m.sum()) * np.sin(2 * np.pi * 70 * t[m])
    lab = A.autoseg_column_labels(x, FS)
    assert lab.size == int(np.ceil(x.size / 16)) and set(np.unique(lab)) <= {0, 1, 2, 3, 4}


def test_tsv_roundtrip(tmp_path):
    x, _, _ = _pcg()
    r = A.autoseg(x, FS)
    p = tmp_path / "a.tsv"
    A.write_tsv(str(p), r.segments, x.size / FS)
    back = load_segmentation(str(p))
    assert np.allclose(back[back[:, 2] > 0], r.segments, atol=1e-6)
    assert back[0, 0] == 0 and back[-1, 1] == pytest.approx(x.size / FS)
    assert np.all(back[1:, 0] == back[:-1, 1])                                            # contiguous rows


def test_interval_pairing():
    pk = np.array([0, 15, 40, 55, 80, 95, 120])          # short, long alternating -> S1 S2 S1 ...
    assert list(A.interval_states(pk)) == [2, 4, 2, 4, 2, 4]
    pk = np.array([0, 25, 40, 65, 80])                   # long, short -> starts on diastole
    assert list(A.interval_states(pk)) == [4, 2, 4, 2]
    pk = np.array([0, 15, 40, 65, 80])                   # (s,d),(d,s): d,d breaks alternation -> both invalid
    assert list(A.interval_states(pk)) == [2, 0, 0, 2]


def test_segmenter_uses_no_annotation_or_metadata():
    src = inspect.getsource(A)
    for banned in ["load_segmentation", "circor", "murmur", "read_csv", "open(path, \"r\")"]:
        assert banned not in src.split('"""', 2)[2]
