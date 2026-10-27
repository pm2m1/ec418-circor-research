"""SECONDARY / EXPLORATORY: audio-derived signal-quality indices (SQI), no expert annotations used.

Q1  Do simple SQIs separate Murmur=Unknown patients from Present/Absent patients?
    (single-index AUROC, orientation fixed a priori: lower quality -> more 'Unknown')
Q2  Risk-coverage: if the RF/P1 model abstains on the lowest-SQI patients, how do retained-patient
    metrics change? Coverage cut-offs are SQI quantiles (unsupervised, label-free); descriptive only.
Compared against a spectral-ratio gate (20-200 Hz power / 0-1000 Hz power) as the simple baseline."""
import sys
from multiprocessing import Pool

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pywt
from scipy.signal import butter, hilbert, sosfiltfilt, welch
from scipy.stats import kurtosis
from sklearn.metrics import roc_auc_score

from ec418.data.circor import load_patients, recording_table
from ec418.evaluation.metrics import threshold_metrics
from ec418.preprocessing.signal import load_wav, resample

DATA = "data/raw/circor_training_data"


def sqi(args):
    rec_id, wav = args
    x = load_wav(wav); fs = 4000
    xi = np.round(x * 32768)
    clip = float(np.mean(np.abs(xi) >= 32767))
    f, P = welch(x, fs, nperseg=1024)
    spec_ratio = P[(f >= 20) & (f < 200)].sum() / (P[f < 1000].sum() + 1e-20)      # preprint-style gate
    band_frac = P[(f >= 25) & (f < 400)].sum() / (P.sum() + 1e-20)
    x2 = resample(x, 4000, 2000)
    # wavelet envelope periodicity: db4 SWT-free proxy = level-3..5 detail energy envelope (62.5-250 Hz)
    coeffs = pywt.wavedec(x2, "db4", mode="periodization", level=5)
    rec = pywt.waverec([np.zeros_like(coeffs[0]), coeffs[1], coeffs[2], coeffs[3], np.zeros_like(coeffs[4]),
                        np.zeros_like(coeffs[5])], "db4", mode="periodization")[: x2.size]
    env = np.abs(hilbert(rec))
    env = sosfiltfilt(butter(2, 15, fs=2000, output="sos"), env)
    env = env[::20] - env[::20].mean()     # 100 Hz envelope
    ac = np.correlate(env, env, "full")[env.size - 1:]
    ac = ac / (ac[0] + 1e-20)
    lo, hi = int(0.3 * 100), int(1.5 * 100)
    period = float(ac[lo:hi].max()) if ac.size > hi else float("nan")
    hf = pywt.wavedec(x2, "db4", mode="periodization", level=1)[1]   # 500-1000 Hz detail
    impuls = float(kurtosis(hf))
    return dict(rec_id=rec_id, sqi_periodicity=period, sqi_band_frac=float(band_frac), sqi_hf_kurtosis=impuls,
                sqi_clip=clip, gate_spectral_ratio=float(spec_ratio))


if __name__ == "__main__":
    rt = recording_table(load_patients(DATA))
    with Pool(1) as p:
        rows = p.map(sqi, list(zip(rt.rec_id, rt.wav)), chunksize=16)
    S = rt[["rec_id", "patient_id", "subject_id", "murmur"]].merge(pd.DataFrame(rows), on="rec_id")
    S.to_csv("data/processed/rec_sqi.csv", index=False)
    # patient-level: median over recordings
    cols = ["sqi_periodicity", "sqi_band_frac", "sqi_hf_kurtosis", "sqi_clip", "gate_spectral_ratio"]
    Pq = S.groupby(["patient_id", "subject_id", "murmur"], as_index=False)[cols].median()
    # a-priori orientation: score of being 'Unknown' (higher = worse quality)
    orient = {"sqi_periodicity": -1, "sqi_band_frac": -1, "sqi_hf_kurtosis": +1, "sqi_clip": +1,
              "gate_spectral_ratio": -1}
    yU = (Pq.murmur == "Unknown").astype(int)
    q1 = [dict(index=c, orientation="higher=worse" if o > 0 else "lower=worse",
               auroc_unknown_vs_known=roc_auc_score(yU, o * Pq[c])) for c, o in orient.items()]
    Q1 = pd.DataFrame(q1); print(Q1.round(3).to_string(index=False))
    Q1.round(4).to_csv("results/tables/sqi_unknown_separation.csv", index=False)

    # Q2 risk-coverage using RF/P1 predictions (repeat 0, spec80 operating point)
    pred = pd.read_csv("results/predictions/main_predictions.csv")
    out = []
    for S_, lab in [("A_wpd_db4", "P1"), ("B0", "B0")]:
        g = pred[(pred.set == S_) & (pred.clf == "RF")].merge(Pq, on=["patient_id", "subject_id"])
        for gate, o in [("sqi_periodicity", -1), ("gate_spectral_ratio", -1)]:
            for cov in [1.0, 0.95, 0.9, 0.8, 0.7]:
                accs = []
                for r, h in g.groupby("repeat"):
                    bad = o * h[gate]
                    keep = bad <= np.quantile(bad, cov) if cov < 1 else np.ones(len(h), bool)
                    hh = h[keep]
                    m = threshold_metrics(hh.y.values, (hh.score >= hh.thr_spec80).astype(int).values, 0.5)
                    accs.append(dict(auroc=roc_auc_score(hh.y, hh.score), sens=m["sensitivity"], spec=m["specificity"],
                                     wacc=m["weighted_accuracy"], kept_present=int(hh.y.sum()),
                                     rejected_present_frac=1 - hh.y.sum() / h.y.sum(),
                                     rejected_absent_frac=1 - (1 - hh.y).sum() / (1 - h.y).sum()))
                a = pd.DataFrame(accs).mean()
                out.append(dict(model=lab, gate=gate, coverage=cov, **a.to_dict()))
    Q2 = pd.DataFrame(out); print(Q2.round(3).to_string(index=False))
    Q2.round(4).to_csv("results/tables/sqi_risk_coverage.csv", index=False)
    fig, ax = plt.subplots(figsize=(6, 4))
    for (m, gte), h in Q2.groupby(["model", "gate"]):
        ax.plot(h.coverage, h.auroc, "-o", ms=3, label=f"{m}, gate={gte}")
    ax.set_xlabel("coverage (fraction of patients retained)"); ax.set_ylabel("patient AUROC among retained")
    ax.invert_xaxis(); ax.legend(fontsize=7); ax.set_title("Exploratory risk-coverage (RF, mean of 5 repeats)")
    fig.tight_layout(); fig.savefig("results/figures/fig9_sqi_risk_coverage.png", dpi=150)
