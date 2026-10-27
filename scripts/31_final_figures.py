"""Final figures from SAVED outputs only (no retraining): results/figures_final/*.png.

  fig_final_roc.png              patient ROC (RF, repeat-averaged scores): B0, B1, W_stft, expert-aligned stft, E4 stft, E4 wpds
  fig_final_decomposition.png    RF AUROC with 95 % CI for expert / D1 / E1b / D2 / perm / D3 / whole-signal, per representation
  fig_final_wavelet_vs_stft.png  wpd - stft and wpds - stft (RF, paired subject bootstrap) under each labelling
  fig_final_ladder.png           E1b -> E4 -> D1 -> expert per representation, with B1 and W_stft reference lines
The wavelet-vs-STFT contrasts are computed here (descriptive; subject bootstrap 2000, seed 2) and saved to
results/tables/final_wavelet_vs_stft.csv. Palette: categorical slots 1-3 (stft, wpd, wpds) and 1-6 for the ROC, from the
dataviz reference palette, validated (all checks pass; contrast < 3:1 for slots 3-5 -> legends with values, distinct
line styles / markers and the saved tables carry identity).
usage: python scripts/31_final_figures.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from ec418.evaluation.metrics import subject_bootstrap

OUT = "results/figures_final"
os.makedirs(OUT, exist_ok=True)
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
REP_COLOR = {"stft": SLOT[0], "wpd": SLOT[1], "wpds": SLOT[2]}
REP_MARK = {"stft": "o", "wpd": "s", "wpds": "D"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})

P = {t: pd.read_csv(f"results/predictions/{t}_predictions.csv") for t in ["repro_mac", "e1", "e2", "e1b", "e4", "diag"]}


def scores(tag, S, C="RF"):
    g = P[tag][(P[tag].set == S) & (P[tag].clf == C)]
    assert len(g), (tag, S)
    return g.groupby(["patient_id", "subject_id", "y"], as_index=False).score.mean()


# ---------------------------------------------------------------- ROC
roc_sets = [("B0 acoustic", "repro_mac", "B0", "-"), ("B1 Vimalajeewa '25", "e1", "B1", "--"),
            ("W_stft whole-signal", "e1", "W_stft", ":"), ("Expert-aligned stft", "e2", "E2_stft_true", "-"),
            ("E4 stft (automatic)", "e4", "E4_stft", "-"), ("E4 wpds (automatic)", "e4", "E4_wpds", "-.")]
fig, ax = plt.subplots(figsize=(5.6, 5.0))
for i, (lab, tag, S, ls) in enumerate(roc_sets):
    a = scores(tag, S)
    f, t, _ = roc_curve(a.y, a.score)
    ax.plot(f, t, color=SLOT[i], lw=2, ls=ls, label=f"{lab}  AUROC {roc_auc_score(a.y, a.score):.3f}")
ax.plot([0, 1], [0, 1], color=GRID, lw=1)
ax.axvline(0.2, color=GRID, lw=1, ls="--")
ax.set_xlabel("1 − specificity (Absent)"); ax.set_ylabel("Sensitivity (Present)")
ax.set_title("Patient-level ROC, WEKA RF, repeat-averaged scores (874 patients)", color=INK, fontsize=9)
ax.legend(fontsize=7.5, loc="lower right", frameon=False)
ax.grid(color=GRID, lw=0.6); fig.tight_layout(); fig.savefig(f"{OUT}/fig_final_roc.png"); plt.close(fig)

# ---------------------------------------------------------------- decomposition (RF AUROC with CI)
A = pd.read_csv("results/tables/diag_auroc.csv")
A = A[A.clf == "RF"].set_index("set")
conds = [("Expert labels", "E2_{r}_true"), ("D1: HSMM timing in expert spans", "D1_{r}"),
         ("E1b: HSMM timing, whole recording", "E1b_{r}_auto"), ("D2: timing destroyed in spans", "D2_{r}"),
         ("E2 perm: timing destroyed, whole rec.", "E2_{r}_perm"), ("D3: whole-signal features in spans", "D3_{r}"),
         ("Whole-signal features, full recording", None)]
WFULL = {"stft": "W_stft", "wpd": "W_wpd_db4", "wpds": "W_wpd_db4_smooth"}
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for j, rep in enumerate(["stft", "wpd", "wpds"]):
    for i, (lab, pat) in enumerate(conds):
        x = A.loc[WFULL[rep] if pat is None else pat.format(r=rep)]
        y = len(conds) - 1 - i + (1 - j) * 0.22
        ax.errorbar(x.auroc_repeat_averaged, y, xerr=[[x.auroc_repeat_averaged - x.auroc_repeat_averaged_ci_lo],
                    [x.auroc_repeat_averaged_ci_hi - x.auroc_repeat_averaged]], fmt=REP_MARK[rep], ms=6, color=REP_COLOR[rep],
                    ecolor=REP_COLOR[rep], elinewidth=1.5, capsize=0, label=rep if i == 0 else None)
ax.set_yticks(range(len(conds))); ax.set_yticklabels([c[0] for c in conds][::-1], color=INK)
ax.axvline(0.5, color=GRID, lw=1)
ax.set_xlabel("Patient AUROC (RF, repeat-averaged, 95 % subject-bootstrap CI)")
ax.set_title("Decomposition: timing vs span selection\n(D1–D3 are diagnostics: they use the expert annotation at test time)", color=INK, fontsize=9)
ax.legend(title="representation", fontsize=8, title_fontsize=8, frameon=False, loc="lower left")
ax.grid(axis="x", color=GRID, lw=0.6); fig.tight_layout(); fig.savefig(f"{OUT}/fig_final_decomposition.png"); plt.close(fig)

# ---------------------------------------------------------------- wavelet vs STFT (paired)
labellings = [("Expert labels", "e2", "E2_{r}_true"), ("E4 automatic spans", "e4", "E4_{r}"), ("D1 expert spans", "diag", "D1_{r}"),
              ("E1b HSMM, whole rec.", "e1b", "E1b_{r}_auto"), ("E1 envelope segmenter", "e1", "E1_{r}_auto")]
rows = []
for lab, tag, pat in labellings:
    st = scores(tag, pat.format(r="stft"))
    for rep in ["wpd", "wpds"]:
        J = scores(tag, pat.format(r=rep)).merge(st, on=["patient_id", "subject_id", "y"], suffixes=("_a", "_b"))
        fn = lambda df: roc_auc_score(df.y, df.score_a) - roc_auc_score(df.y, df.score_b)
        lo, hi, _ = subject_bootstrap(J, fn, n_boot=2000, seed=2)
        rows.append(dict(labelling=lab, contrast=f"{rep} - stft", delta=fn(J), ci_lo=lo, ci_hi=hi))
WV = pd.DataFrame(rows)
WV.to_csv("results/tables/final_wavelet_vs_stft.csv", index=False)
fig, ax = plt.subplots(figsize=(6.4, 3.6))
for j, rep in enumerate(["wpd", "wpds"]):
    sub = WV[WV.contrast == f"{rep} - stft"].reset_index(drop=True)
    y = np.arange(len(sub))[::-1] + (0.5 - j) * 0.3
    ax.errorbar(sub.delta, y, xerr=[sub.delta - sub.ci_lo, sub.ci_hi - sub.delta], fmt=REP_MARK[rep], ms=6,
                color=REP_COLOR[rep], elinewidth=1.5, capsize=0, label=f"{rep} − stft")
ax.axvline(0, color=MUTED, lw=1); ax.axvspan(-0.03, 0.03, color=GRID, alpha=0.6, lw=0)
ax.set_yticks(range(len(labellings))); ax.set_yticklabels([l[0] for l in labellings][::-1], color=INK)
ax.set_xlabel("Δ patient AUROC vs matched STFT bands (RF, 95 % CI; shaded ±0.03)")
ax.set_title("Wavelet packets vs Fourier bands, same aligned features", color=INK, fontsize=9)
ax.legend(fontsize=8, frameon=False, loc="upper left"); ax.grid(axis="x", color=GRID, lw=0.6)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_final_wavelet_vs_stft.png"); plt.close(fig)

# ---------------------------------------------------------------- ladder
E = pd.read_csv("results/tables/e4_auroc.csv")
E = E[E.clf == "RF"].set_index("set")
steps = [("E1b\nHSMM, whole rec.", "E1b_{r}_auto"), ("E4\nautomatic spans", "E4_{r}"), ("D1\nexpert spans", "D1_{r}"),
         ("Expert\nlabels", "E2_{r}_true")]
fig, ax = plt.subplots(figsize=(6.4, 4.0))
for j, rep in enumerate(["stft", "wpd", "wpds"]):
    xs = np.arange(len(steps)) + (j - 1) * 0.12
    v = [E.loc[p.format(r=rep)] for _, p in steps]
    ax.plot(xs, [x.auroc_repeat_averaged for x in v], color=REP_COLOR[rep], lw=2, marker=REP_MARK[rep], ms=6, label=rep)
    ax.vlines(xs, [x.auroc_repeat_averaged_ci_lo for x in v], [x.auroc_repeat_averaged_ci_hi for x in v], color=REP_COLOR[rep], lw=1.2)
for S, lab in [("W_stft", "W_stft whole-signal"), ("B1", "B1 Vimalajeewa '25")]:
    y = E.loc[S].auroc_repeat_averaged
    ax.axhline(y, color=MUTED, lw=1.2, ls="--" if S == "B1" else ":", label=f"{lab} {y:.3f}")
ax.set_xticks(range(len(steps))); ax.set_xticklabels([s[0] for s in steps], color=INK)
ax.set_ylabel("Patient AUROC (RF, repeat-averaged, 95 % CI)")
ax.set_title("From automatic to expert labels: E1b → E4 → D1 → expert", color=INK, fontsize=9)
ax.legend(fontsize=8, frameon=False, loc="lower right")
ax.grid(axis="y", color=GRID, lw=0.6); fig.tight_layout(); fig.savefig(f"{OUT}/fig_final_ladder.png"); plt.close(fig)
print("figures:", sorted(os.listdir(OUT)))
print(WV.round(4).to_string(index=False))
