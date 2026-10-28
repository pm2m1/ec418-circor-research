"""Gate-2 diagnosis step 2 (no G2 result used): rebuild E1b features for repeat 0 / fold 0 with scripts/21 and
re-score the OUTER test patients with WEKA SMO/RF exactly as scripts/06 does; compare with results/predictions/e1b_predictions.csv.
If E1b reproduces exactly, the HSMM decodes (outer + cross-fitted inner) are identical and the E4R difference is E4-specific.
-> results/tables/p3/g2_gate_diagnosis_e1b_r0f0.csv"""
import importlib.util, os, subprocess, shutil
import pandas as pd, numpy as np
spec = importlib.util.spec_from_file_location("e1b", "scripts/21_e1b_run.py"); e1b = importlib.util.module_from_spec(spec)
saved_json = open("results/logs/e1b_models/r0_f0.json").read()
spec.loader.exec_module(e1b); print(e1b.fold_job((0, 0)))
open("results/logs/e1b_models/r0_f0.json", "w").write(saved_json)          # keep the committed file byte-identical
spec6 = importlib.util.spec_from_file_location("w6", "scripts/06_run_patient_level_weka.py"); w6 = importlib.util.module_from_spec(spec6); spec6.loader.exec_module(w6)
from ec418.weka.arff import CLASSIFIERS, build_runner, classpath, write_arff, read_arff_header
ft = pd.read_csv("configs/folds_patient_level.csv"); patients = ft[["patient_id", "subject_id", "y"]].drop_duplicates().sort_values("patient_id").reset_index(drop=True)
g = ft[(ft.repeat == 0) & (ft.outer_fold == 0)]; tr, te = g[g.role == "train"], g[g.role == "test"]
d = "experiments/p3_gatediag/arff"; os.makedirs(d, exist_ok=True); jobs = []; out = []
for S in ["E1b_stft_auto", "E1b_wpd_auto", "E4R_stft"]:
    P = w6.patient_matrix(S, patients, 0, 0); feats = list(P.columns)
    for part, df in (("train", tr), ("test", te)):
        write_arff(f"{d}/{S}_{part}.arff", P.loc[df.patient_id.values], df.y.values, f"{S}_{part}", feats)
    for C in ["RF", "SMO"]:
        cls, opts = CLASSIFIERS[C]; jobs.append("\t".join([f"{S}|{C}", f"{d}/{S}_train.arff", f"{d}/{S}_test.arff", f"{d}/{S}_{C}.pred.csv", cls, opts])); out.append((S, C))
open("experiments/p3_gatediag/jobs.tsv", "w").write("\n".join(jobs) + "\n"); build_runner()
subprocess.run(["java", "-Xmx2g", "-cp", classpath(), "WekaBatchRunner", "experiments/p3_gatediag/jobs.tsv"], check=True, capture_output=True)
ref = pd.concat([pd.read_csv("results/predictions/e1b_predictions.csv"), pd.read_csv("results/predictions/e4_predictions.csv")])
rows = []
for S, C in out:
    s = te[["patient_id"]].assign(score=pd.read_csv(f"{d}/{S}_{C}.pred.csv").p_present.values)
    refS = S.replace("E4R_", "E4_")
    r = ref[(ref.set == refS) & (ref.clf == C) & (ref.repeat == 0) & (ref.fold == 0)][["patient_id", "score"]]
    J = s.merge(r, on="patient_id", suffixes=("_here", "_saved")); dd = (J.score_here - J.score_saved).abs()
    rows.append(dict(set=S, clf=C, n=len(J), max_abs_diff=dd.max(), frac_differing=(dd > 1e-9).mean()))
R = pd.DataFrame(rows); R.to_csv("results/tables/p3/g2_gate_diagnosis_e1b_r0f0.csv", index=False); print(R.to_string(index=False))
