import numpy as np
import pytest

from ec418.segmentation import spans as S


def test_window_bookkeeping():
    assert S.n_windows(125 * 7 + 30, 4000 * 7 + 900) == 7
    cols = np.zeros(125 * 3, int); cols[:70] = 2; cols[125:180] = 1; cols[250:] = 4
    assert S.window_targets(cols, 3).tolist() == [1, 0, 1]                  # >= 50 % annotated
    m = S.column_mask(np.array([1, 0, 1]), 125 * 3 + 40)
    assert m.sum() == 250 and not m[375:].any() and not m[125:250].any()


def test_signal_features_shape_and_clipping():
    rng = np.random.default_rng(0)
    raw = (rng.standard_normal(4000 * 6) * 3000).astype(np.int16)
    raw[4000 * 2: 4000 * 2 + 400] = 32767
    x2 = rng.standard_normal(2000 * 6)
    F = S.signal_window_features(raw, x2, n_cols=int(np.ceil(x2.size / 16)))
    assert F.shape == (6, 5) and np.isfinite(F).all()
    assert F[2, 4] == pytest.approx(0.1) and F[0, 4] == 0
    assert (F[:, 1] <= 0).all() and (F[:, 0] <= 0).all()                     # log fractions


def test_periodicity_detects_rhythm():
    t = np.arange(150) / 50
    periodic = 1 + np.cos(2 * np.pi * t / 0.6) ** 8
    assert S._periodicity(periodic) > 0.5
    assert S._periodicity(np.ones(150)) == 0.0 and S._periodicity(np.ones(20)) == 0.0


def test_hsmm_confidence():
    p = np.tile([0.2, 0.9, 0.1, 0.3], (120, 1))
    assert np.allclose(S.hsmm_window_confidence(p, 2), 0.9)


def test_detector_threshold_matches_training_fraction():
    rng = np.random.default_rng(1)
    X = rng.standard_normal((2000, 6)); y = (X[:, 0] + 0.5 * rng.standard_normal(2000) > 0.3).astype(int)
    d = S.fit_detector(X, y)
    assert d.train_predicted_frac == pytest.approx(y.mean(), abs=0.002)
    assert d.predict(X).mean() == pytest.approx(y.mean(), abs=0.002)
    X2 = X.copy(); X2[0, 3] = np.nan
    assert np.isfinite(d.proba(X2)).all()
