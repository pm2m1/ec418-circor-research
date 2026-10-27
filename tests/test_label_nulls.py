import zlib

import numpy as np
import pytest

from ec418.features.label_nulls import (median_s1_period_cols, null_labels, perm_labels, rec_seed, s1_onsets,
                                        shift_labels)

CPS = 2000 / 16   # level-4 columns per second at 2 kHz


def _cycles(n_cycles=20, period=100, lead=37, tail=23):
    """Synthetic column labels: unannotated lead/tail around regular S1-sys-S2-dia cycles."""
    one = [1] * 12 + [2] * 30 + [3] * 10 + [4] * (period - 52)
    return np.array([0] * lead + one * n_cycles + [0] * tail)


def test_seed_is_crc32():
    assert rec_seed("13918_AV") == zlib.crc32(b"13918_AV")


def test_s1_onsets_and_period():
    lab = _cycles(period=100)
    assert s1_onsets(lab).size == 20
    assert median_s1_period_cols(lab, CPS) == 100.0
    assert median_s1_period_cols(np.array([0, 1, 1, 2, 2, 3, 4, 4]), CPS) == pytest.approx(0.6 * CPS)


@pytest.mark.parametrize("cond", ["perm", "shift"])
def test_label_counts_preserved(cond):
    lab = _cycles()
    out = null_labels(lab, cond, "50001_MV", CPS)
    assert out.shape == lab.shape
    assert np.array_equal(np.bincount(out, minlength=5), np.bincount(lab, minlength=5))


@pytest.mark.parametrize("cond", ["perm", "shift"])
def test_deterministic(cond):
    lab = _cycles()
    a = null_labels(lab, cond, "50001_MV", CPS)
    b = null_labels(lab.copy(), cond, "50001_MV", CPS)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, null_labels(lab, cond, "50001_AV", CPS))   # seed depends on rec_id


@pytest.mark.parametrize("cond", ["perm", "shift"])
def test_differs_from_true(cond):
    lab = _cycles()
    out = null_labels(lab, cond, "50001_MV", CPS)
    assert (out != lab).mean() > 0.3
    assert null_labels(lab, "true", "50001_MV", CPS) is lab


def test_shift_amount_within_range_and_keeps_contiguity():
    lab = _cycles(period=100)
    for rid in ["a", "b", "c", "13918_AV", "85345_PV_2"]:
        out, k = shift_labels(lab, rid, CPS)
        assert 20 <= k <= 80
        assert np.array_equal(out, np.roll(lab, k))
        assert s1_onsets(out).size == s1_onsets(lab).size   # runs stay contiguous (no wrap split here)


def test_perm_destroys_runs():
    lab = _cycles()
    out = perm_labels(lab, "50001_MV")
    # a random permutation fragments the 12-column S1 runs into many short ones
    assert s1_onsets(out).size > 5 * s1_onsets(lab).size


def test_unknown_condition():
    with pytest.raises(ValueError):
        null_labels(_cycles(), "oracle", "x", CPS)
