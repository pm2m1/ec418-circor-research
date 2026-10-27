import os
import subprocess

import numpy as np
import pandas as pd
import pytest
import soundfile as sf

from ec418.evaluation.metrics import (confusion, official_weighted_accuracy_binary, threshold_for_specificity,
                                      threshold_max_weighted_accuracy, threshold_metrics)
from ec418.features.extract import aggregate_patient, aligned_features, band_feature_sets, whole_features
from ec418.preprocessing.signal import bandpass, load_wav, preprocess, resample, znorm
from ec418.weka.arff import CLASS_VALUES, build_runner, classpath, read_arff_header, write_arff


# ---------------- signal ----------------
def test_load_wav_checks_fs(tmp_path):
    p = tmp_path / "a.wav"
    sf.write(p, np.zeros(400, dtype="int16") + 5, 4000, subtype="PCM_16")
    assert load_wav(str(p)).shape == (400,)
    sf.write(tmp_path / "b.wav", np.zeros(400, dtype="int16"), 8000, subtype="PCM_16")
    with pytest.raises(ValueError):
        load_wav(str(tmp_path / "b.wav"))


def test_resample_length_and_antialias():
    fs = 4000
    t = np.arange(fs * 2) / fs
    x_lo = np.sin(2 * np.pi * 200 * t)
    x_hi = np.sin(2 * np.pi * 1500 * t)      # above the new 1 kHz Nyquist -> must be removed
    y_lo, y_hi = resample(x_lo, 4000, 2000), resample(x_hi, 4000, 2000)
    assert y_lo.size == x_lo.size // 2
    assert np.std(y_lo[100:-100]) > 0.65                  # passband preserved (~0.707)
    assert np.std(y_hi[100:-100]) < 0.01                  # alias suppressed (>~37 dB)


def test_bandpass_rejects_out_of_band():
    fs = 2000
    t = np.arange(fs * 3) / fs
    assert np.std(bandpass(np.sin(2 * np.pi * 5 * t), fs)[500:-500]) < 0.02
    assert np.std(bandpass(np.sin(2 * np.pi * 200 * t), fs)[500:-500]) > 0.65
    with pytest.raises(ValueError):
        bandpass(np.ones(4000), fs, 25, 1000)


def test_constant_and_empty_inputs():
    with pytest.raises(ValueError):
        znorm(np.ones(100))
    with pytest.raises(ValueError):
        preprocess(np.zeros(10))


# ---------------- features ----------------
def _toy_pcg(fs=2000, dur=6.0, murmur=False, seed=0):
    rng = np.random.default_rng(seed)
    n = int(fs * dur)
    x = 0.01 * rng.standard_normal(n)
    seg = []
    t = 0.0
    while t + 0.8 < dur:
        s1 = int(t * fs); x[s1:s1 + 60] += np.hanning(60) * np.sin(2 * np.pi * 50 * np.arange(60) / fs)
        if murmur:
            a, b = int((t + 0.12) * fs), int((t + 0.30) * fs)
            x[a:b] += 0.3 * rng.standard_normal(b - a)
        s2 = int((t + 0.32) * fs); x[s2:s2 + 50] += np.hanning(50) * np.sin(2 * np.pi * 70 * np.arange(50) / fs)
        seg += [[t, t + 0.1, 1], [t + 0.1, t + 0.32, 2], [t + 0.32, t + 0.4, 3], [t + 0.4, t + 0.8, 4]]
        t += 0.8
    return x, np.array(seg)


def test_feature_determinism_and_dims():
    x, seg = _toy_pcg()
    a = band_feature_sets(x, seg)
    b = band_feature_sets(x, seg)
    assert a == b
    for k in ["W_wpd", "W_stft", "A_wpd", "A_stft"]:
        assert len(a[k]) == 34 and all(np.isfinite(v) for v in a[k].values())


def test_aligned_features_detect_systolic_noise():
    xm, seg = _toy_pcg(murmur=True)
    xn, _ = _toy_pcg(murmur=False)
    fm = band_feature_sets(xm, seg)["A_wpd"]; fn = band_feature_sets(xn, seg)["A_wpd"]
    # systolic/diastolic ratio in a 125-375 Hz band must rise with a systolic murmur
    assert np.mean([fm[f"wpdA_sdratio{b:02d}"] for b in range(2, 6)]) > \
        np.mean([fn[f"wpdA_sdratio{b:02d}"] for b in range(2, 6)]) + 1.0


def test_missing_segmentation_returns_none():
    x, _ = _toy_pcg()
    out = band_feature_sets(x, np.zeros((0, 3)))
    assert out["A_wpd"] is None and out["A_stft"] is None and out["W_wpd"] is not None


def test_patient_aggregation_nan_aware():
    rec = pd.DataFrame(dict(patient_id=[1, 1, 2], f=[1.0, np.nan, 3.0], g=[np.nan, np.nan, 1.0]))
    P = aggregate_patient(rec, ["f", "g"])
    assert P.loc[1, "f__med"] == 1.0 and P.loc[1, "f__max"] == 1.0
    assert np.isnan(P.loc[1, "g__max"]) and P.loc[2, "g__med"] == 1.0


# ---------------- metrics ----------------
def test_confusion_class_order_and_formulas():
    y = np.array([1, 1, 1, 0, 0, 0, 0, 0])
    s = np.array([.9, .8, .2, .7, .1, .1, .1, .1])
    m = threshold_metrics(y, s, 0.5)
    assert (m["TP"], m["FN"], m["FP"], m["TN"]) == (2, 1, 1, 4)
    assert m["sensitivity"] == pytest.approx(2 / 3)       # Present recall
    assert m["specificity"] == pytest.approx(4 / 5)       # Absent recall
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["accuracy"] == pytest.approx(6 / 8)


def test_official_weighted_accuracy_matches_formula():
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 200); p = rng.integers(0, 2, 200)
    c = confusion(y, p)
    manual = (5 * c["TP"] + c["TN"]) / (5 * (c["TP"] + c["FN"]) + (c["TN"] + c["FP"]))
    assert official_weighted_accuracy_binary(y, p) == pytest.approx(manual)


def test_threshold_rules_use_given_data_only():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500); s = rng.random(500) + 0.3 * y
    t = threshold_for_specificity(y, s, 0.8)
    spec = np.mean(s[y == 0] < t)
    assert spec >= 0.8 and spec < 0.82
    assert np.isfinite(threshold_max_weighted_accuracy(y, s))


# ---------------- ARFF / WEKA ----------------
def test_arff_header_consistency_and_id_guard(tmp_path):
    X = pd.DataFrame(dict(a=[1.0, np.nan], b=[0.5, 2.0]))
    write_arff(str(tmp_path / "tr.arff"), X, np.array([0, 1]), "r", ["a", "b"])
    write_arff(str(tmp_path / "te.arff"), X.iloc[:1], np.array([1]), "r", ["a", "b"])
    assert read_arff_header(str(tmp_path / "tr.arff")) == read_arff_header(str(tmp_path / "te.arff"))
    txt = open(tmp_path / "tr.arff").read()
    assert "@attribute class {Absent,Present}" in txt and "?,2.0,Present" in txt and "1.0,0.5,Absent" in txt
    assert CLASS_VALUES == ("Absent", "Present")
    with pytest.raises(ValueError):
        write_arff(str(tmp_path / "x.arff"), X.rename(columns={"a": "patient_id"}), None, "r", ["patient_id", "b"])


@pytest.mark.skipif(subprocess.run(["which", "java"], capture_output=True).returncode != 0, reason="no java")
def test_weka_runner_end_to_end(tmp_path):
    rng = np.random.default_rng(0)
    n = 120
    y = rng.integers(0, 2, n)
    X = pd.DataFrame(dict(f1=rng.standard_normal(n) + 2 * y, f2=rng.standard_normal(n)))
    write_arff(str(tmp_path / "tr.arff"), X.iloc[:80], y[:80], "t", ["f1", "f2"])
    write_arff(str(tmp_path / "te.arff"), X.iloc[80:], y[80:], "t", ["f1", "f2"])
    jobs = tmp_path / "jobs.tsv"
    jobs.write_text("\t".join(["t", str(tmp_path / "tr.arff"), str(tmp_path / "te.arff"), str(tmp_path / "p.csv"),
                               "weka.classifiers.functions.Logistic", "-R 1.0"]) + "\n")
    build_runner()
    r = subprocess.run(["java", "-cp", classpath(), "WekaBatchRunner", str(jobs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    pr = pd.read_csv(tmp_path / "p.csv")
    assert len(pr) == 40 and (pr.actual == np.where(y[80:] == 1, "Present", "Absent")).all()
    from sklearn.metrics import roc_auc_score
    assert roc_auc_score(y[80:], pr.p_present) > 0.8
