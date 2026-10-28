"""Phase 3, Mac vs cloud: compare the Mac G4/G1a outputs with results/p3_cloud_reference/ (read-only reference).

  features   5 feature files (Mac data/processed/*.csv vs cloud features/*.csv.gz): max |delta|, NaN pattern
             -> STOP (exit 2) if any gated |delta| > 1e-6 or the NaN pattern differs. The gate covers every feature column
             except the 13 B0 MFCC columns of zch_features_whole.csv, which are reported descriptively (author decision
             2026-10-29): max |delta|, max |delta| / column median |value|, per-value float32 multiple
             |delta| / spacing(float32(max(|mac|,|cloud|))) and column-scale multiple |delta| / spacing(float32(column max)).
             Note: the per-value rule given in the prompt was the wrong yardstick for frame-averaged MFCCs (author error). No
             tolerance was chosen after the fact; B0 MFCCs are excluded from the gate because B0 enters no pre-registered
             verdict. Same float32 cause as docs/REPRO_MAC.md. Their NaN pattern is still required to be identical.
  scores     CirCor CV predictions (p3_cv, p3_cv_smo) and ZCHSound scores: max |delta| per set/clf(/variant)
  tables     every row of g4_scattering_{metrics,contrasts}, g1a_external_{any_chd,by_subtype}, g1a_posthoc_age_check,
             g1a_verdicts.json: Mac value, cloud value, delta (numbers) or equality (text)
  verdicts   H10a, H10b, H11a, H11b, H11c must equal the cloud -> STOP (exit 3) otherwise
The Mac ZCHSound scores are assembled from experiments/p3_external/arff/*_pred.csv into
results/predictions/p3_external_zch_scores.csv in the cloud file's format (fileName, subset, diagnosis, set, variant,
clf, score). Writes results/tables/p3/p3_mac_vs_cloud.csv and results/logs/p3_mac_vs_cloud.json.
usage: .venv/bin/python scripts/p3_05_compare_cloud.py [ZCH_DIR]
"""
import json
import os
import sys

import numpy as np
import pandas as pd

REF = "results/p3_cloud_reference"
ZCH = sys.argv[1] if len(sys.argv) > 1 else "data/external/ZCHSound"
FEAT_TOL = 1e-6
MFCC_FILE = "zch_features_whole"
rows = []


def add(section, item, key, column, mac, cloud):
    num = isinstance(mac, (int, float, np.integer, np.floating)) and isinstance(cloud, (int, float, np.integer, np.floating))
    d = float(mac) - float(cloud) if num and not (pd.isna(mac) or pd.isna(cloud)) else np.nan
    same = (pd.isna(mac) and pd.isna(cloud)) if num and (pd.isna(mac) or pd.isna(cloud)) else (abs(d) == 0 if num else str(mac) == str(cloud))
    rows.append(dict(section=section, item=item, key=key, column=column, mac=mac, cloud=cloud, delta=d, identical=bool(same)))


# ---------------------------------------------------------------- features
feat_ok = True
for f in ["rec_features_A_scat1", "rec_features_A_scat12", "rec_features_W_scat1", "zch_features_W_scat1", "zch_features_whole"]:
    M = pd.read_csv(f"data/processed/{f}.csv")
    C = pd.read_csv(f"{REF}/features/{f}.csv.gz")
    key = M.columns[0]
    M, C = M.set_index(key).sort_index(), C.set_index(key).sort_index()
    same_shape = M.index.equals(C.index) and list(M.columns) == list(C.columns)
    num = [c for c in M.columns if pd.api.types.is_numeric_dtype(M[c]) and pd.api.types.is_numeric_dtype(C[c])] if same_shape else []
    nan_same = bool((M[num].isna() == C[num].isna()).all().all()) if same_shape else False
    mfcc = [c for c in num if f == MFCC_FILE and c.startswith("B0::b0_mfcc")]
    rest = [c for c in num if c not in mfcc]
    mad = float(np.nanmax(np.abs(M[rest].to_numpy() - C[rest].to_numpy()))) if rest else np.nan
    text_same = bool(M.drop(columns=num).fillna("").astype(str).equals(C.drop(columns=num).fillna("").astype(str))) if same_shape else False
    ok = same_shape and nan_same and text_same and mad <= FEAT_TOL
    for c in mfcc:                                   # excluded from the gate: descriptive only
        a, b = M[c].to_numpy(float), C[c].to_numpy(float)
        d = np.abs(a - b)
        per_value = np.where(d == 0, 0.0, d / np.spacing(np.maximum(np.abs(a), np.abs(b)).astype(np.float32)).astype(float))
        col_scale = float(np.nanmax(d) / np.spacing(np.float32(max(np.nanmax(np.abs(a)), np.nanmax(np.abs(b))))))
        rel_med = float(np.nanmax(d) / np.nanmedian(np.abs(a)))
        for col, v in [("max_abs_delta", float(np.nanmax(d))), ("max_abs_delta_over_column_median", rel_med),
                       ("per_value_float32_multiple_max", float(np.nanmax(per_value))), ("column_scale_float32_multiple", col_scale)]:
            add("features_b0_mfcc_descriptive", f, c, col, v, np.nan)
        print(f"  [not gated] {c}: max|d| {np.nanmax(d):.3e}, /column median {rel_med:.2e}, per-value multiple {np.nanmax(per_value):.0f}, column-scale multiple {col_scale:.2f}")
    feat_ok &= ok
    add("features", f, "max_abs_delta", "all numeric", mad, 0.0)
    add("features", f, "nan_pattern_and_shape", "identical", int(same_shape and nan_same and text_same), 1)
    print(f"{f}: rows {len(M)} cols {M.shape[1]} | same rows/cols {same_shape} | NaN pattern same {nan_same} | text same {text_same} | "
          f"max|d| (1e-6 columns) {mad:.3e}{' | + ' + str(len(mfcc)) + ' MFCC columns reported, not gated' if mfcc else ''} -> {'OK' if ok else 'FAIL'}")

# ---------------------------------------------------------------- scores
for t in ["p3_cv", "p3_cv_smo"]:
    M = pd.read_csv(f"results/predictions/{t}_predictions.csv")
    C = pd.read_csv(f"{REF}/{t}_predictions.csv")
    J = M.merge(C, on=["set", "clf", "repeat", "fold", "patient_id"], suffixes=("_mac", "_cloud"), how="outer", indicator=True)
    assert (J._merge == "both").all(), f"{t}: rows differ"
    for (S, Cl), g in J.groupby(["set", "clf"]):
        add("scores", t, f"{S}|{Cl}", "max_abs_score_delta", float((g.score_mac - g.score_cloud).abs().max()), 0.0)
z = pd.concat([pd.read_csv(os.path.join(ZCH, "Clean Heartsound Data Details.csv"))[["fileName", "diagnosis"]].assign(subset="clean"),
               pd.read_csv(os.path.join(ZCH, "Noise Heartsound Data Details.csv"), sep=";", encoding="utf-8-sig")[["fileName", "diagnosis"]].assign(subset="noisy")],
              ignore_index=True)
zs = []
for S in ["W_stft", "W_wpd_db4_smooth", "B0", "W_scat1"]:
    for v in ["all", "pv"]:
        for Cl in ["RF", "SMO"]:
            pr = pd.read_csv(f"experiments/p3_external/arff/{S}_{v}_{Cl}.pred.csv")
            assert len(pr) == len(z)
            zs.append(z.assign(set=S, variant=v, clf=Cl, score=pr.p_present.values))
ZS = pd.concat(zs, ignore_index=True)[["fileName", "subset", "diagnosis", "set", "variant", "clf", "score"]]
ZS.to_csv("results/predictions/p3_external_zch_scores.csv", index=False)
C = pd.read_csv(f"{REF}/p3_external_zch_scores.csv")
J = ZS.merge(C, on=["fileName", "subset", "diagnosis", "set", "variant", "clf"], suffixes=("_mac", "_cloud"), how="outer", indicator=True)
assert (J._merge == "both").all(), "ZCHSound score rows differ"
for (S, v, Cl), g in J.groupby(["set", "variant", "clf"]):
    add("scores", "p3_external_zch_scores", f"{S}|{v}|{Cl}", "max_abs_score_delta", float((g.score_mac - g.score_cloud).abs().max()), 0.0)

# ---------------------------------------------------------------- tables
KEYS = {"g4_scattering_metrics": ["set", "clf"], "g4_scattering_contrasts": ["hypothesis", "clf", "a", "b"],
        "g1a_external_any_chd": ["set", "clf", "variant", "subset"],
        "g1a_external_by_subtype": ["set", "clf", "variant", "subset", "diagnosis"], "g1a_posthoc_age_check": ["model"]}
for t, keys in KEYS.items():
    M = pd.read_csv(f"results/tables/p3/{t}.csv")
    C = pd.read_csv(f"{REF}/tables/{t}.csv")
    J = M.merge(C, on=keys, suffixes=("_mac", "_cloud"), how="outer", indicator=True)
    assert (J._merge == "both").all(), f"{t}: rows differ"
    for _, r in J.iterrows():
        k = "|".join(str(r[x]) for x in keys)
        for c in [c for c in M.columns if c not in keys]:
            add("tables", t, k, c, r[f"{c}_mac"], r[f"{c}_cloud"])
vm, vc = json.load(open("results/tables/p3/g1a_verdicts.json")), json.load(open(f"{REF}/tables/g1a_verdicts.json"))
for h in vc:
    for c in vc[h]:
        a, b = vm[h][c], vc[h][c]
        if isinstance(b, list):
            for i, (x, y) in enumerate(zip(a, b)):
                add("tables", "g1a_verdicts.json", h, f"{c}[{i}]", x, y)
        else:
            add("tables", "g1a_verdicts.json", h, c, a, b)

# ---------------------------------------------------------------- SMO sensitivity on scattering features (descriptive)
cvM = pd.concat([pd.read_csv(f"results/predictions/{t}_predictions.csv") for t in ["p3_cv"]])
cvC = pd.concat([pd.read_csv(f"{REF}/{t}_predictions.csv") for t in ["p3_cv"]])
cvJ = cvM.merge(cvC, on=["set", "clf", "repeat", "fold", "patient_id"], suffixes=("_mac", "_cloud"))
zJ = ZS.merge(pd.read_csv(f"{REF}/p3_external_zch_scores.csv"), on=["fileName", "subset", "diagnosis", "set", "variant", "clf"], suffixes=("_mac", "_cloud"))
gm, gc = pd.read_csv("results/tables/p3/g4_scattering_metrics.csv"), pd.read_csv(f"{REF}/tables/g4_scattering_metrics.csv")
for S in ["A_scat1", "A_scat12", "W_scat1"]:
    for Cl in ["RF", "SMO"]:
        g = cvJ[(cvJ.set == S) & (cvJ.clf == Cl)]
        add("smo_sensitivity", "cv_scores", f"{S}|{Cl}", "max_abs_score_delta", float((g.score_mac - g.score_cloud).abs().max()), 0.0)
        if S == "W_scat1":
            h = zJ[(zJ.set == S) & (zJ.clf == Cl)]
            add("smo_sensitivity", "zch_scores", f"{S}|{Cl}", "max_abs_score_delta", float((h.score_mac - h.score_cloud).abs().max()), 0.0)
        a = gm[(gm.set == S) & (gm.clf == Cl)].auroc_repeat_avg_scores.iloc[0]
        b = gc[(gc.set == S) & (gc.clf == Cl)].auroc_repeat_avg_scores.iloc[0]
        add("smo_sensitivity", "cv_auroc_repeat_averaged", f"{S}|{Cl}", "auroc_repeat_avg_scores", float(a), float(b))

# ---------------------------------------------------------------- verdicts
ver = {h: (vm[h]["verdict"], vc[h]["verdict"]) for h in ["H10a", "H10b"]}
Mc, Cc = pd.read_csv("results/tables/p3/g4_scattering_contrasts.csv"), pd.read_csv(f"{REF}/tables/g4_scattering_contrasts.csv")
for h in ["H11a", "H11b", "H11c"]:
    ver[h] = (Mc[(Mc.hypothesis == h) & (Mc.clf == "RF")].verdict.iloc[0], Cc[(Cc.hypothesis == h) & (Cc.clf == "RF")].verdict.iloc[0])
for h, (a, b) in ver.items():
    add("verdicts", "pre-registered", h, "verdict", a, b)
R = pd.DataFrame(rows)
R.to_csv("results/tables/p3/p3_mac_vs_cloud.csv", index=False)
verd_ok = all(a == b for a, b in ver.values())
sc = R[R.section == "scores"]
sm = R[R.section == "smo_sensitivity"]
summary = dict(features_ok=bool(feat_ok),
               b0_mfcc_not_gated={f"{r.key}:{r.column}": r.mac for r in R[R.section == "features_b0_mfcc_descriptive"].itertuples()},
               smo_sensitivity={f"{r.item}:{r.key}": dict(mac=r.mac, cloud=r.cloud, delta=r.delta) for r in sm.itertuples()}, verdicts_identical=bool(verd_ok), verdicts={h: dict(mac=a, cloud=b) for h, (a, b) in ver.items()},
               max_score_delta={k: float(g.mac.max()) for k, g in sc.assign(k=sc.item + ":" + sc.key.str.split("|").str[-1]).groupby("k")},
               tables_numeric_max_abs_delta={t: float(g.delta.abs().max()) for t, g in R[R.section == "tables"].groupby("item")},
               tables_text_mismatches=int(((R.section == "tables") & R.delta.isna() & ~R.identical).sum()))
json.dump(summary, open("results/logs/p3_mac_vs_cloud.json", "w"), indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
if not feat_ok:
    print("STOP: feature files differ from the cloud beyond 1e-6 or in NaN pattern"); sys.exit(2)
if not verd_ok:
    print("STOP: a pre-registered verdict differs from the cloud"); sys.exit(3)
