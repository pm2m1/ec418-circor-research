import os

import numpy as np
import pandas as pd
import pytest
import pywt
import soundfile as sf

from ec418.wavelets.dwtr_port import SYM4_BASELINE_FILTER, dwtr, window_entropy_cv

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_dwtr_docstring_example():
    out = dwtr([1, 0, -3, 2, 1, 0, 1, 2], 3, [np.sqrt(2) / 2] * 2)
    assert np.allclose(out, [1.4142, -1.4142, 1.0, -1.0, 0.7071, -3.5355, 0.7071, -0.7071], atol=1e-4)


def test_baseline_filter_is_symlet4_not_db6():
    assert np.allclose(SYM4_BASELINE_FILTER, pywt.Wavelet("sym4").dec_lo, atol=1e-12)
    assert len(pywt.Wavelet("db6").dec_lo) == 12


def test_dwtr_energy_preserved():
    x = np.random.default_rng(0).standard_normal(1024)
    assert np.isclose(np.sum(dwtr(x, 9, SYM4_BASELINE_FILTER) ** 2), np.sum(x ** 2))


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "data/processed/rec_features_B1.csv")), reason="needs data")
@pytest.mark.skipif(not all(os.path.exists(os.path.join(ROOT, "data/raw/circor_training_data", r + ".wav"))
                            for r in ["13918_AV", "2530_MV"]), reason="real CirCor wav files not present")
def test_realigned_b1_rows_match_recomputed_entropy():
    b1 = pd.read_csv(os.path.join(ROOT, "data/processed/rec_features_B1.csv"))
    for rec in ["13918_AV", "2530_MV"]:
        row = b1[b1.rec_id == rec]
        if row.empty:
            continue
        x, _ = sf.read(os.path.join(ROOT, "data/raw/circor_training_data", rec + ".wav"), dtype="float64")
        assert window_entropy_cv(x) == pytest.approx(float(row.b1_entropy_cv.iloc[0]), rel=1e-10)
