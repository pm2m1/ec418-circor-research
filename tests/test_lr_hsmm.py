import numpy as np
import pytest

from ec418.segmentation import lr_hsmm as H

FS4 = 4000


def _rec(period=0.6, systole=0.24, dur=20.0, seed=0, noise=0.05):
    """Synthetic 4 kHz PCG with expert-style segments: S1 (70 Hz) and S2 (110 Hz) Hann bursts."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * FS4)) / FS4
    x = noise * rng.standard_normal(t.size)
    seg, t0, w1, w2 = [], 0.2, 0.11, 0.09
    while t0 + period < dur - 0.2:
        sy = systole + rng.uniform(-0.01, 0.01)                    # real systoles vary (non-zero learned SD)
        for c, w, f in ((t0, w1, 70.0), (t0 + sy, w2, 110.0)):
            m = (t >= c) & (t < c + w)
            x[m] += np.hanning(m.sum()) * np.sin(2 * np.pi * f * t[m])
        seg += [(t0, t0 + w1, 1), (t0 + w1, t0 + sy, 2), (t0 + sy, t0 + sy + w2, 3), (t0 + sy + w2, t0 + period, 4)]
        t0 += period
    return x, np.array(seg, float)


@pytest.fixture(scope="module")
def model_and_data():
    recs = [_rec(period=p, seed=i) for i, p in enumerate([0.55, 0.6, 0.65, 0.7, 0.58, 0.62])]
    feats = [H.springer_features(x) for x, _ in recs]
    return H.train([F for F, _ in feats], [s for _, s in recs], seed=0), recs, feats


def test_features_shape_and_normalised():
    x, _ = _rec()
    F, ac = H.springer_features(x)
    assert F.shape[1] == 4 and abs(F.shape[0] - 20 * 50) <= 1
    assert np.allclose(F.mean(axis=0), 0, atol=1e-6) and np.allclose(F.std(axis=0, ddof=1), 1, atol=1e-6)
    assert ac[0] == pytest.approx(1.0) and ac.size == 20 * 1000


def test_learned_duration_params(model_and_data):
    p = model_and_data[0].params
    assert p["mean_s1"] == pytest.approx(0.11, abs=1e-9) and p["mean_s2"] == pytest.approx(0.09, abs=1e-9)
    assert 0.5 <= p["period_range"][0] <= p["period_range"][1] <= 0.75
    assert p["sys_ratio_range"][0] == pytest.approx(0.24 / 0.7, abs=0.03) and p["sd_sys"] > 0


def test_decodes_held_out_synthetic_recording(model_and_data):
    m = model_and_data[0]
    x, seg = _rec(period=0.6, seed=42)
    F, ac = H.springer_features(x)
    qt, info = H.decode(m, F, ac)
    assert info["period_s"] == pytest.approx(0.6, abs=0.03)
    lab = H.labels_50hz(seg, F.shape[0])
    mk = lab > 0
    assert (qt[mk] == lab[mk]).mean() >= 0.8
    # state order always follows the cycle S1 -> sys -> S2 -> dia
    runs = qt[np.r_[0, np.flatnonzero(np.diff(qt)) + 1]]
    assert all(b == a % 4 + 1 for a, b in zip(runs, runs[1:]))


def test_deterministic(model_and_data):
    m, recs, feats = model_and_data
    a = H.train([F for F, _ in feats], [s for _, s in recs], seed=0)
    assert np.array_equal(a.coef, m.coef) and a.params == m.params
    F, ac = feats[0]
    assert np.array_equal(H.decode(m, F, ac)[0], H.decode(a, F, ac)[0])


def test_states_to_segments():
    qt = np.array([1, 1, 2, 2, 2, 3, 4, 4, 1])
    seg = H.states_to_segments(qt, 9 / 50)
    assert list(seg[:, 2]) == [1, 2, 3, 4, 1] and seg[0, 0] == 0 and seg[-1, 1] == pytest.approx(8.5 / 50)
    assert np.allclose(seg[1:, 0], seg[:-1, 1])
    assert H.labels_50hz(seg, 9).tolist() == qt.tolist()


def test_spike_removal_removes_spike():
    rng = np.random.default_rng(0)
    x = 0.1 * rng.standard_normal(5000)
    x[2200] = 10.0
    y = H.schmidt_spike_removal(x, 1000)
    assert y.size == x.size and np.abs(y).max() < 1.0


def test_too_short_recording_raises(model_and_data):
    m = model_and_data[0]
    x, _ = _rec(dur=0.5)
    F, ac = H.springer_features(np.r_[x, np.zeros(4000)])
    with pytest.raises(ValueError):
        H.decode(m, F[:10], ac[:200])


def test_decoder_reads_no_annotation():
    import inspect
    src = inspect.getsource(H.decode) + inspect.getsource(H.viterbi) + inspect.getsource(H.springer_features)
    assert "seg" not in src.replace("segment", "")
