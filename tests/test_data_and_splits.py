import os

import numpy as np
import pandas as pd
import pytest
import soundfile as sf

from ec418.data.circor import canonical_subjects, linkage_report, load_patients, load_segmentation, patient_table
from ec418.evaluation.splits import LeakageError, assert_disjoint, grouped_folds, make_fold_table, verify_fold_table

REAL = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "circor_training_data")


def _write_patient(d, pid, murmur, add_id="nan", locs=("AV", "MV"), fs=4000):
    lines = [f"{pid} {len(locs)} {fs}"]
    for loc in locs:
        lines.append(f"{loc} {pid}_{loc}.hea {pid}_{loc}.wav {pid}_{loc}.tsv")
        sf.write(os.path.join(d, f"{pid}_{loc}.wav"), (np.sin(np.arange(8000) / 10) * 1000).astype("int16"), fs,
                 subtype="PCM_16")
        open(os.path.join(d, f"{pid}_{loc}.tsv"), "w").write("0\t0.1\t1\n0.1\t0.3\t2\n0.3\t0.4\t3\n0.4\t0.8\t4\n")
    lines += [f"#Murmur: {murmur}", f"#Additional ID: {add_id}", "#Campaign: CC2015", "#Murmur locations: nan"]
    open(os.path.join(d, f"{pid}.txt"), "w").write("\n".join(lines) + "\n")


@pytest.fixture
def toy(tmp_path):
    d = str(tmp_path)
    _write_patient(d, 1, "Present", add_id="2")
    _write_patient(d, 2, "Absent", add_id="1")
    _write_patient(d, 3, "Absent")
    _write_patient(d, 4, "Unknown")
    open(os.path.join(d, "LICENSE.txt"), "w").write("not a patient")
    open(os.path.join(d, "4_AV.txt"), "w").write("stray dump file")
    return d


def test_loader_skips_non_patient_txt_and_maps_labels(toy):
    p = load_patients(toy)
    assert sorted(p) == [1, 2, 3, 4]
    assert p[1].murmur == "Present" and p[4].murmur == "Unknown"
    assert p[1].additional_id == 2 and p[3].additional_id is None
    assert len(p[1].recordings) == 2


def test_canonical_subject_links(toy):
    s = canonical_subjects(load_patients(toy))
    assert s[1] == s[2] == 1 and s[3] == 3 and s[4] == 4
    rep = linkage_report(load_patients(toy))
    assert rep["n_subjects"] == 3
    assert rep["label_conflicts"] == [([1, 2], ["Absent", "Present"])]


def test_wrong_fs_rejected(tmp_path):
    _write_patient(str(tmp_path), 9, "Absent", fs=8000)
    with pytest.raises(AssertionError):
        load_patients(str(tmp_path))


def test_segmentation_loading(toy):
    seg = load_segmentation(os.path.join(toy, "1_AV.tsv"))
    assert seg.shape == (4, 3) and set(seg[:, 2]) == {1, 2, 3, 4}
    assert load_segmentation(None).shape == (0, 3)
    assert load_segmentation(float("nan")).shape == (0, 3)


def _toy_patients(n=120, seed=0):
    rng = np.random.default_rng(seed)
    pid = np.arange(n)
    subj = pid.copy()
    subj[1::7] = subj[0::7][: len(subj[1::7])]           # some linked pairs
    y = (rng.random(n) < 0.2).astype(int)
    return pd.DataFrame(dict(patient_id=pid, subject_id=subj, y=y))


def test_grouped_folds_no_subject_leak():
    df = _toy_patients()
    seen = []
    for k, tr, te in grouped_folds(df, 5, 0):
        assert not set(df.subject_id.iloc[tr]) & set(df.subject_id.iloc[te])
        seen += list(df.patient_id.iloc[te])
    assert sorted(seen) == sorted(df.patient_id)       # each patient tested exactly once


def test_fold_table_verifies_and_is_deterministic():
    df = _toy_patients()
    a = make_fold_table(df, 5, (0, 1), 3)
    b = make_fold_table(df, 5, (0, 1), 3)
    pd.testing.assert_frame_equal(a, b)
    rep = verify_fold_table(a)
    assert rep["repeat0_tested_patients"] == len(df)


def test_assert_disjoint_detects_leak():
    tr = pd.DataFrame(dict(subject_id=[1, 2], patient_id=[1, 2]))
    te = pd.DataFrame(dict(subject_id=[2, 3], patient_id=[5, 3]))
    with pytest.raises(LeakageError):
        assert_disjoint(tr, te)


@pytest.mark.skipif(not os.path.isdir(REAL), reason="real CirCor data not present")
def test_real_data_counts_and_frozen_folds():
    p = load_patients(REAL)
    pt = patient_table(p)
    assert len(pt) == 942 and pt.n_recordings.sum() == 3163
    assert pt.murmur.value_counts().to_dict() == {"Absent": 695, "Present": 179, "Unknown": 68}
    ft = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "configs", "folds_patient_level.csv"))
    verify_fold_table(ft)
    # frozen folds must use the canonical subject grouping
    subj = canonical_subjects(p)
    assert all(subj[a] == b for a, b in zip(ft.patient_id, ft.subject_id))
