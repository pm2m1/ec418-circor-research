"""Write-up figures from SAVED outputs only (no retraining, no new experiment): report/figures/*.png.

  fig_external.png        ZCHSound clean set, RF W_stft (models trained once on all 874 CirCor patients): any-CHD ROC, and
                          AUROC by subtype vs NORMAL with 95 % CI (results/predictions/p3_external_zch_scores.csv,
                          results/tables/p3/g1a_external_by_subtype.csv)
  fig_scattering.png      G4: RF AUROC with CI for matched STFT, WPD and scattering features (p3/g4_scattering_metrics.csv)
  fig_pipeline.png        pipeline diagram (no numbers)
  slide_*.png             the same panels with larger fonts for the slides, plus the frozen decomposition and
                          wavelet-vs-STFT data redrawn large (results/tables/final_decomposition.csv, final_wavelet_vs_stft.csv)
The frozen figures in results/figures_final/ are used by the report as they are and are not modified.
Palette: the categorical slots of scripts/31_final_figures.py.
usage: .venv/bin/python scripts/p4_figures.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from sklearn.metrics import roc_curve

OUT = "report/figures"
os.makedirs(OUT, exist_ok=True)
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, MUTED, GRID, BAND = "#1f1f1e", "#6b6a64", "#e4e3de", "#edede8"


def style(fs):
    plt.rcParams.update({"font.size": fs, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 200})


Z = pd.read_csv("results/predictions/p3_external_zch_scores.csv")
XS = pd.read_csv("results/tables/p3/g1a_external_by_subtype.csv")
G4 = pd.read_csv("results/tables/p3/g4_scattering_metrics.csv")
DEC = pd.read_csv("results/tables/final_decomposition.csv")
WV = pd.read_csv("results/tables/final_wavelet_vs_stft.csv")


def external(fs, size, path):
    style(fs)
    z = Z[(Z.set == "W_stft") & (Z.clf == "RF") & (Z.variant == "all") & (Z.subset == "clean")]
    fig, (a, b) = plt.subplots(1, 2, figsize=size, gridspec_kw={"width_ratios": [1, 1.15]})
    fpr, tpr, _ = roc_curve((z.diagnosis != "NORMAL").astype(int), z.score)
    a.plot([0, 1], [0, 1], color=GRID, lw=1)
    a.plot(fpr, tpr, color=SLOT[0], lw=2)
    a.set(xlabel="1 − specificity", ylabel="sensitivity", title="Any CHD vs NORMAL", xlim=(0, 1), ylim=(0, 1))
    a.set_aspect("equal")
    a.set_xticks([0, 0.5, 1])
    a.set_yticks([0, 0.5, 1])
    s = XS[(XS.set == "W_stft") & (XS.clf == "RF") & (XS.variant == "all") & (XS.subset == "clean")]
    s = s.set_index("diagnosis").loc[["PDA", "VSD", "ASD", "PFO"]].reset_index()
    y = range(len(s))[::-1]
    b.axvline(0.5, color=MUTED, lw=1, ls="--")
    b.errorbar(s.auroc_vs_normal, list(y), xerr=[s.auroc_vs_normal - s.ci_lo, s.ci_hi - s.auroc_vs_normal], fmt="o",
               color=SLOT[0], ms=7, capsize=0, lw=2)
    b.set_yticks(list(y), [f"{d} (n={n})" for d, n in zip(s.diagnosis, s.n)])
    b.set(xlabel="AUROC vs NORMAL (95 % CI)", title="By CHD subtype", xlim=(0.4, 0.95))
    b.grid(axis="x", color=GRID)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def scattering(fs, size, path):
    style(fs)
    order = [("A_stft", "aligned STFT bands"), ("A_wpd_db4", "aligned WPD db4"), ("A_wpd_db4_smooth", "aligned WPD smoothed"),
             ("A_scat1", "aligned scattering, 1st order"), ("A_scat12", "aligned scattering, 1st+2nd"),
             ("W_stft", "whole-signal STFT"), ("W_scat1", "whole-signal scattering")]
    g = G4[G4.clf == "RF"].set_index("set")
    fig, ax = plt.subplots(figsize=size)
    for i, (sname, lab) in enumerate(order[::-1]):
        r = g.loc[sname]
        c = SLOT[2] if "scat" in sname else (SLOT[1] if "wpd" in sname else SLOT[0])
        ax.errorbar(r.auroc_repeat_avg_scores, i, xerr=[[r.auroc_repeat_avg_scores - r.ci_lo], [r.ci_hi - r.auroc_repeat_avg_scores]],
                    fmt="o", color=c, ms=7, lw=2)
    ax.set_yticks(range(len(order)), [lab for _, lab in order[::-1]])
    ax.set(xlabel="patient AUROC (RF, repeat-averaged, 95 % CI)")
    ax.grid(axis="x", color=GRID)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def pipeline(fs, size, path):
    style(fs)
    fig, ax = plt.subplots(figsize=size)
    ax.set(xlim=(-0.05, 10.15), ylim=(0.2, 3.1))
    ax.axis("off")
    steps = [("PCG\nrecording\n(4 sites)", SLOT[0]), ("Segmentation\nexpert | HSMM\n+ span detector", SLOT[3]),
             ("Cycle-aligned\nbands: S1, sys,\nS2, dia", SLOT[1]), ("Transform\nSTFT | WPD |\nscattering", SLOT[2]),
             ("Patient\nfeatures\n(median, max)", SLOT[4]), ("WEKA RF/SMO\nsubject-grouped\n5×5 CV", SLOT[5])]
    w, gap = 1.42, 0.27
    for i, (t, c) in enumerate(steps):
        x = 0.05 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 0.95), w, 1.4, boxstyle="round,pad=0.04", fc="white", ec=c, lw=2.2))
        ax.text(x + w / 2, 1.65, t, ha="center", va="center", color=INK, fontsize=fs * 0.78, linespacing=1.25)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((x + w + 0.05, 1.65), (x + w + gap - 0.05, 1.65), arrowstyle="-|>", mutation_scale=10,
                                         color=MUTED, lw=1.3))
    ax.text(5.05, 0.55, "Controls: timing destroyed (perm, shift), whole-signal features, span/missingness shortcut (S1, SC_q)",
            ha="center", color=MUTED, fontsize=fs * 0.8)
    ax.text(5.05, 2.75, "External test: ZCHSound (trained once on all CirCor patients; no tuning on ZCHSound)",
            ha="center", color=MUTED, fontsize=fs * 0.8)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def decomposition_slide(fs, size, path):
    style(fs)
    labels = ["Expert labels", "E4 automatic spans", "D1: HSMM in expert spans*", "E1b: HSMM, whole recording",
              "D2: timing destroyed in spans*", "E2 perm: timing destroyed", "D3: whole-signal in spans*", "Whole-signal features"]
    fig, ax = plt.subplots(figsize=size)
    for j, (rep, c, m) in enumerate([("stft", SLOT[0], "o"), ("wpd", SLOT[1], "s"), ("wpds", SLOT[2], "D")]):
        for i, (_, r) in enumerate(DEC.iterrows()):
            lo, hi = [float(x) for x in r[f"{rep}_ci"].strip("[]").split(",")]
            yy = len(DEC) - 1 - i + (0.22 - 0.22 * j)
            ax.errorbar(r[rep], yy, xerr=[[r[rep] - lo], [hi - r[rep]]], fmt=m, color=c, ms=6, lw=1.8,
                        label=rep if i == 0 else None)
    ax.set_yticks(range(len(DEC)), labels[::-1])
    ax.set(xlabel="patient AUROC (RF, 95 % CI)   * uses the expert annotation at test time")
    ax.grid(axis="x", color=GRID)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def wavelet_slide(fs, size, path):
    style(fs)
    labs = list(dict.fromkeys(WV.labelling))
    fig, ax = plt.subplots(figsize=size)
    ax.axvspan(-0.03, 0.03, color=BAND)
    ax.axvline(0, color=MUTED, lw=1)
    for j, (con, c, m) in enumerate([("wpd - stft", SLOT[1], "s"), ("wpds - stft", SLOT[2], "D")]):
        for i, lab in enumerate(labs):
            r = WV[(WV.labelling == lab) & (WV.contrast == con)].iloc[0]
            yy = len(labs) - 1 - i + (0.15 - 0.3 * j)
            ax.errorbar(r.delta, yy, xerr=[[r.delta - r.ci_lo], [r.ci_hi - r.delta]], fmt=m, color=c, ms=7, lw=2,
                        label=con.replace("-", "−") if i == 0 else None)
    ax.set_yticks(range(len(labs)), labs[::-1])
    ax.set(xlabel="Δ AUROC vs matched STFT bands (RF, 95 % CI; shaded ±0.03)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


external(8, (7.0, 3.0), f"{OUT}/fig_external.png")
scattering(8, (3.5, 2.6), f"{OUT}/fig_scattering.png")
pipeline(8, (7.2, 2.0), f"{OUT}/fig_pipeline.png")
external(21, (12, 5.6), f"{OUT}/slide_external.png")
scattering(21, (10, 5.6), f"{OUT}/slide_scattering.png")
pipeline(15, (13, 3.6), f"{OUT}/slide_pipeline.png")
decomposition_slide(20, (11, 6.4), f"{OUT}/slide_decomposition.png")
wavelet_slide(20, (11, 6.0), f"{OUT}/slide_wavelet.png")
print("figures ->", sorted(os.listdir(OUT)))
