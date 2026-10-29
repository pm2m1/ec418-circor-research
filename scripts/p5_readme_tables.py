"""README key-results tables, generated from saved tables only (no retraining, no new analysis).

Writes the markdown between the markers <!-- BEGIN:results --> and <!-- END:results --> in README.md (and prints it).
Two AUROC definitions are kept apart, as in the saved tables:
  * mean of repeat AUROCs: the AUROC of each of the 5 CV repeats, averaged (± SD over repeats);
  * AUROC of repeat-averaged scores: each patient's out-of-fold score averaged over the 5 repeats, then one AUROC,
    with a 95 % subject-bootstrap CI (2000 resamples). This is the definition used by every hypothesis test.
Rounding: half-up to 3 decimals (as scripts/p4_numbers.py).
usage: .venv/bin/python scripts/p5_readme_tables.py
"""
import json
import re
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

T = "results/tables"


def f(x, signed=False):
    q = Decimal(str(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    q = abs(q) if q == 0 else q
    s = f"{q:f}"
    return ("+" + s if signed and q > 0 else s).replace("-", "−")


E = pd.read_csv(f"{T}/e4_auroc.csv").query("clf == 'RF'").set_index("set")
G = pd.read_csv(f"{T}/p3/g2_auroc.csv").query("clf == 'RF'").set_index("set")
S = pd.read_csv(f"{T}/s1_auroc.csv").query("clf == 'RF'").set_index("set")
M = pd.read_csv(f"{T}/main_metrics.csv").query("clf == 'RF'").set_index("set")
H = pd.read_csv(f"{T}/final_hypotheses.csv")
GC = pd.read_csv(f"{T}/p3/g2_contrasts.csv").query("clf == 'RF'")
X = pd.read_csv(f"{T}/p3/g1a_external_any_chd.csv")

rows = [("Expert-aligned STFT bands (E2 `true`)", "expert annotation (oracle)", E.loc["E2_stft_true"], "auroc_mean_of_repeats",
         "auroc_mean_of_repeats_sd", "auroc_repeat_averaged", "auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi", "Phase 2"),
        ("Expert-aligned WPD db4 (E2 `true`)", "expert annotation (oracle)", E.loc["E2_wpd_true"], "auroc_mean_of_repeats",
         "auroc_mean_of_repeats_sd", "auroc_repeat_averaged", "auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi", "Phase 2"),
        ("Automatic spans, STFT (E4)", "LR-HSMM + learned span detector", E.loc["E4_stft"], "auroc_mean_of_repeats",
         "auroc_mean_of_repeats_sd", "auroc_repeat_averaged", "auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi", "Phase 2"),
        ("Automatic spans, WPD db4 (E4)", "LR-HSMM + learned span detector", E.loc["E4_wpd"], "auroc_mean_of_repeats",
         "auroc_mean_of_repeats_sd", "auroc_repeat_averaged", "auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi", "Phase 2"),
        ("Automatic spans, shortcut-free, STFT (E4q)", "same fraction of windows per recording", G.loc["E4q_stft"],
         "auroc_mean_of_repeats", "sd", "auroc_repeat_averaged", "ci_lo", "ci_hi", "Phase 3"),
        ("Whole-signal STFT bands (W_stft)", "none", S.loc["W_stft"], "auroc_mean_of_repeats", "auroc_mean_of_repeats_sd",
         "auroc_repeat_averaged", "auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi", "Phase 2 (Mac)"),
        ("Whole-signal WPD db4 (W_wpd_db4)", "none", S.loc["W_wpd_db4"], "auroc_mean_of_repeats", "auroc_mean_of_repeats_sd",
         "auroc_repeat_averaged", "auroc_repeat_averaged_ci_lo", "auroc_repeat_averaged_ci_hi", "Phase 2 (Mac)"),
        ("Reproduced 2025 wavelet baseline (B1, Vimalajeewa et al.)", "none", M.loc["B1"], "auroc", "auroc_sd",
         "auroc_avgscore", "auroc_ci_lo", "auroc_ci_hi", "Phase 1 (frozen, Linux)")]
L = ["| Model (WEKA RandomForest) | Segmentation used at test time | Mean of repeat AUROCs ± SD | "
     "AUROC of repeat-averaged scores [95 % CI] | Source |", "|---|---|---|---|---|"]
for lab, seg, r, m, sd, a, lo, hi, src in rows:
    L.append(f"| {lab} | {seg} | {f(r[m])} ± {f(r[sd])} | {f(r[a])} [{f(r[lo])}, {f(r[hi])}] | {src} |")


def hyp(h, contrast):
    r = H[(H.hypothesis == h) & (H.contrast == contrast)].iloc[0]
    return f"{f(r.delta, True)} [{f(r.ci_lo, True)}, {f(r.ci_hi, True)}]", r.folds_positive, r.verdict


def g2(h, rep):
    r = GC[(GC.hypothesis == h) & (GC.rep == rep)].iloc[0]
    return f"{f(r.delta, True)} [{f(r.ci_lo, True)}, {f(r.ci_hi, True)}]", r.folds_positive, r.label


C = [("Timing destroyed (expert labels permuted), STFT", "H5b", *hyp("H5b", "E2_stft_true - E2_stft_perm"), "confirmatory"),
     ("Wavelet packets vs matched STFT bands, aligned", "H2a", *hyp("H2a", "A_wpd_db4 - A_stft"), "confirmatory"),
     ("Aligned vs whole-signal WPD", "H3", *hyp("H3", "A_wpd_db4 - W_wpd_db4"), "confirmatory"),
     ("Automatic (E4) vs expert labels, WPD (primary)", "H9a", *hyp("H9a", "E4_wpd - E2_wpd_true"),
      "confirmatory; rule = point estimate ≥ −0.03 (see note)"),
     ("Automatic (E4) vs whole-signal STFT, WPD (primary)", "H9c", *hyp("H9c", "E4_wpd - W_stft"), "confirmatory"),
     ("E4 vs whole-signal STFT + span/missingness shortcut, STFT", "S1(a)", *hyp("S1(a)", "E4_stft - S1_Wstft_SC"),
      "diagnostic (pre-registered after E4)"),
     ("Shortcut-free E4q vs whole-signal STFT + shortcut, STFT (primary)", "H12a", *g2("H12a", "stft"),
      "confirmatory (Phase 3)")]
L2 = ["| Contrast (RF, Δ AUROC of repeat-averaged scores) | Hypothesis | Δ [95 % CI] | Folds Δ > 0 | Recorded verdict | Type |",
      "|---|---|---|---|---|---|"]
for lab, h, d, fp, v, t in C:
    L2.append(f"| {lab} | {h} | {d} | {fp} | {v} | {t} |")

x = X[(X.set == "W_stft") & (X.clf == "RF") & (X.variant == "all") & (X.subset == "clean")].iloc[0]
xn = X[(X.set == "W_stft") & (X.clf == "RF") & (X.variant == "all") & (X.subset == "noisy")].iloc[0]
ext = (f"External test (Phase 3, H10a, pre-registered): W_stft RF trained once on all {int(x.circor_train_patients)} CirCor "
       f"patients, applied unchanged to the ZCHSound clean set ({int(x.n)} children, {int(x.n_chd)} with congenital heart "
       f"disease): AUROC {f(x.auroc_any_chd)} [{f(x.ci_lo)}, {f(x.ci_hi)}] for any CHD (a diagnosis label, not a murmur label); "
       f"noisy neonatal set ({int(xn.n)}): {f(xn.auroc_any_chd)} [{f(xn.ci_lo)}, {f(xn.ci_hi)}], i.e. chance.")
h9 = H[(H.hypothesis == "H9a") & (H.contrast == "E4_wpd - E2_wpd_true")].iloc[0]
note = (f"*Note on H9a.* The pre-registered rule was a point-estimate criterion (Δ ≥ −0.03), and it is met (Δ = "
        f"{f(h9.delta, True)}), so the recorded verdict stays SUPPORTED. Formal statistical non-inferiority within −0.03 is "
        f"**not** established, because the 95 % CI lower bound ({f(h9.ci_lo, True)}) lies below −0.03; clinical equivalence "
        f"is not demonstrated.")
md = "\n".join(["**Table 1 — CirCor, patient level, 874 patients, 5 repeats × 5 subject-grouped folds.**", "", *L, "",
                "**Table 2 — Pre-registered contrasts (RF).**", "", *L2, "", note, "", ext,
                "", "*Generated by `scripts/p5_readme_tables.py` from `results/tables/` — do not edit by hand.*"])
R = open("README.md").read()
new = re.sub(r"(<!-- BEGIN:results -->\n).*?(\n<!-- END:results -->)", lambda m: m.group(1) + md + m.group(2), R, flags=re.S)
assert new != R or md in R, "README.md needs the <!-- BEGIN:results --> / <!-- END:results --> markers"
open("README.md", "w").write(new)
print(md)
