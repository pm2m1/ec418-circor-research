"""Original figures from REAL CirCor recordings (no synthetic signals).

Representative recordings are chosen by a fixed metadata rule (not by model results):
  Present: lowest patient ID with systolic grade III/VI, its most-audible-location recording
  Absent : lowest patient ID with Murmur=Absent, same auscultation location as the Present one
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pywt

from ec418.data.circor import load_patients, load_segmentation, patient_table
from ec418.preprocessing.signal import load_wav, preprocess
from ec418.wavelets.bands import column_labels, nominal_dwt_bands, nominal_packet_bands, wpd_energy_map

DATA = "data/raw/circor_training_data"
OUT = "results/figures"
pats = load_patients(DATA)
pt = patient_table(pats)

pres = pt[(pt.murmur == "Present") & (pt.systolic_grading == "III/VI")].sort_values("patient_id").iloc[0]
P = pats[int(pres.patient_id)]
ma = [l for l in open(f"{DATA}/{P.patient_id}.txt") if l.startswith("#Most audible location")][0].split(":")[1].strip()
rec_p = [r for r in P.recordings if r.location == ma][0]
absent_ids = pt[pt.murmur == "Absent"].sort_values("patient_id").patient_id
rec_a = None
for pid in absent_ids:
    cand = [r for r in pats[int(pid)].recordings if r.location == rec_p.location]
    if cand:
        rec_a = cand[0]; break
meta = dict(present=dict(rec=rec_p.rec_id, patient=P.patient_id, grade=P.systolic_grading, pitch=P.systolic_pitch,
                         timing=P.systolic_timing),
            absent=dict(rec=rec_a.rec_id, patient=rec_a.patient_id))
json.dump(meta, open(f"{OUT}/figure_sources.json", "w"), indent=1)
print(meta)

plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3})
COL = {1: "#4c72b0", 2: "#dd8452", 3: "#55a868", 4: "#8172b3"}
NAME = {1: "S1", 2: "systole", 3: "S2", 4: "diastole"}

# Fig 1/2: raw waveforms
fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
for a, rec, title in [(ax[0], rec_p, "Murmur Present"), (ax[1], rec_a, "Murmur Absent")]:
    x = load_wav(rec.wav); t = np.arange(x.size) / 4000
    m = t < 4
    a.plot(t[m], x[m] / np.max(np.abs(x[m])), lw=0.6, color="k")
    a.set_title(f"{title} - recording {rec.rec_id} (raw, 4 kHz, first 4 s)"); a.set_ylabel("norm. amplitude")
ax[1].set_xlabel("time (s)")
fig.tight_layout(); fig.savefig(f"{OUT}/fig1_raw_pcg_present_vs_absent.png", dpi=150); plt.close(fig)

# Fig 3: annotated cycle segmentation on the preprocessed Present signal
x2 = preprocess(load_wav(rec_p.wav)); fs = 2000
seg = load_segmentation(rec_p.tsv)
t0 = seg[seg[:, 2] == 1][0, 0] if (seg[:, 2] == 1).any() else 0
win = (t0, t0 + 2.5)
t = np.arange(x2.size) / fs
m = (t >= win[0]) & (t < win[1])
fig, ax = plt.subplots(figsize=(10, 3.2))
ax.plot(t[m], x2[m], lw=0.6, color="k")
for s, e, l in seg:
    if l in COL and e > win[0] and s < win[1]:
        ax.axvspan(max(s, win[0]), min(e, win[1]), color=COL[int(l)], alpha=0.25, lw=0)
for l in (1, 2, 3, 4):
    ax.plot([], [], color=COL[l], lw=8, alpha=0.4, label=NAME[l])
ax.legend(ncol=4, loc="upper right", fontsize=8)
ax.set_title(f"{rec_p.rec_id}: dataset S1/systole/S2/diastole annotation (preprocessed 2 kHz, 25-900 Hz)")
ax.set_xlabel("time (s)"); fig.tight_layout(); fig.savefig(f"{OUT}/fig3_annotated_cycles.png", dpi=150); plt.close(fig)

# Fig 4: DWT decomposition (db4, 5 levels) of 2.5 s of the Present signal
y = x2[m]
coeffs = pywt.wavedec(y, "db4", mode="periodization", level=5)
bands = {n: (lo, hi) for n, lo, hi in nominal_dwt_bands(fs, 5)}
names = ["A5"] + [f"D{j}" for j in range(5, 0, -1)]
fig, ax = plt.subplots(len(coeffs) + 1, 1, figsize=(10, 9), sharex=True)
ax[0].plot(np.linspace(*win, y.size), y, lw=0.6, color="k"); ax[0].set_ylabel("x")
for i, (c, n) in enumerate(zip(coeffs, names)):
    ax[i + 1].plot(np.linspace(*win, c.size), c, lw=0.7)
    lo, hi = bands[n]
    ax[i + 1].set_ylabel(f"{n}\n{lo:.0f}-{hi:.0f} Hz", fontsize=8)
ax[-1].set_xlabel("time (s)")
fig.suptitle(f"db4 DWT of {rec_p.rec_id} at fs = 2 kHz (nominal bands)"); fig.tight_layout()
fig.savefig(f"{OUT}/fig4_dwt_decomposition.png", dpi=150); plt.close(fig)

# Fig 5: WPD time-frequency map (depth 4, freq order) with segmentation strip
fig, ax = plt.subplots(2, 2, figsize=(12, 6), gridspec_kw=dict(height_ratios=[5, 1]), sharex="col")
for j, rec in enumerate([rec_p, rec_a]):
    xr = preprocess(load_wav(rec.wav)); sg = load_segmentation(rec.tsv)
    tt0 = sg[sg[:, 2] == 1][0, 0] if (sg[:, 2] == 1).any() else 0
    E = wpd_energy_map(xr, "db4", 4)
    c0, c1 = int(tt0 * fs / 16), int((tt0 + 2.5) * fs / 16)
    im = ax[0, j].imshow(10 * np.log10(E[:, c0:c1] + 1e-8), aspect="auto", origin="lower",
                         extent=[tt0, tt0 + 2.5, 0, 1000], cmap="magma", vmin=-40, vmax=20)
    ax[0, j].set_title(f"{'Present' if j == 0 else 'Absent'} {rec.rec_id}: db4 WPD, J=4", fontsize=9)
    ax[0, j].set_ylabel("nominal band (Hz)")
    lab = column_labels(sg, E.shape[1], 16, fs)[c0:c1]
    ax[1, j].imshow(lab[None, :], aspect="auto", extent=[tt0, tt0 + 2.5, 0, 1], cmap=matplotlib.colors.ListedColormap(
        ["#dddddd", COL[1], COL[2], COL[3], COL[4]]), vmin=0, vmax=4)
    ax[1, j].set_yticks([]); ax[1, j].set_xlabel("time (s); strip: S1 blue, systole orange, S2 green, diastole purple", fontsize=8)
fig.colorbar(im, ax=ax, label="dB", shrink=0.8)
fig.savefig(f"{OUT}/fig5_wpd_time_frequency.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# Fig 6: cohort-level systolic/diastolic WPD energy profile (descriptive, all binary-task patients)
A = pd.read_csv("data/processed/rec_features_A_wpd_db4.csv")
A = A[A.murmur.isin(["Present", "Absent"])]
cols = [f"wpdA_sdratio{b:02d}" for b in range(16)]
Pm = A.groupby(["patient_id", "murmur"])[cols].median().reset_index()
edges = nominal_packet_bands(fs, 4); centres = edges.mean(axis=1)
fig, ax = plt.subplots(figsize=(8, 4))
for mm, c in [("Present", "#c44e52"), ("Absent", "#4c72b0")]:
    v = Pm[Pm.murmur == mm][cols]
    med = v.median(); q1, q3 = v.quantile(0.25), v.quantile(0.75)
    ax.plot(centres, med, "-o", color=c, label=f"{mm} (n={len(v)} patients)", ms=3)
    ax.fill_between(centres, q1, q3, color=c, alpha=0.15)
ax.axhline(0, color="k", lw=0.5)
ax.set_xlabel("WPD band centre (Hz)"); ax.set_ylabel("log(systolic / diastolic band energy)")
ax.set_title("Per-patient median systolic-to-diastolic WPD energy ratio (median, IQR)")
ax.legend(); fig.tight_layout(); fig.savefig(f"{OUT}/fig6_wpd_systolic_diastolic_profile.png", dpi=150); plt.close(fig)

# Fig 7: actual (non-ideal) frequency responses of the depth-4 packet filters vs nominal bands
fig, ax = plt.subplots(1, 2, figsize=(12, 3.5), sharey=True)
for a, w in zip(ax, ["db4", "sym8"]):
    nfreq = 4096
    for b in range(16):
        # impulse response of packet b: reconstruct from a unit coefficient in node b
        wp = pywt.WaveletPacket(np.zeros(1024), w, mode="periodization", maxlevel=4)
        nodes = wp.get_level(4, order="freq")
        for n in nodes:
            n.data = np.zeros_like(n.data)
        nodes[b].data[nodes[b].data.size // 2] = 1.0
        h = wp.reconstruct(update=False)
        H = np.abs(np.fft.rfft(h, nfreq)) ** 2
        f = np.fft.rfftfreq(nfreq, 1 / fs)
        a.plot(f, 10 * np.log10(H / H.max() + 1e-12), lw=0.7)
    for e in edges[:, 0]:
        a.axvline(e, color="k", lw=0.3, ls=":")
    a.set_ylim(-60, 3); a.set_xlim(0, 1000); a.set_title(f"{w}: depth-4 packet responses (dotted = nominal edges)")
    a.set_xlabel("Hz")
ax[0].set_ylabel("dB")
fig.tight_layout(); fig.savefig(f"{OUT}/fig7_packet_frequency_responses.png", dpi=150); plt.close(fig)
print("figures written")
