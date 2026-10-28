"""Check that the WEKA CLI run (weka_demo/run_cli.sh) reproduces the pipeline's saved prediction for A_stft, repeat 0,
outer fold 0, RF, exactly (both print P(Present) with 10 decimals). Also derives the confusion matrix at the 0.5 threshold
from the CLI predictions (= the matrix in the WEKA Explorer result buffer) and compares, for information only, with the
frozen Linux Phase-1 prediction (results/predictions/main_predictions.csv; RF differed by up to 4/300 trees across
platforms, docs/REPRO_MAC.md). Writes weka_demo/check_result.json. Exit 1 if the Mac pipeline match is not exact.
usage: .venv/bin/python weka_demo/check_cli_vs_pipeline.py
"""
import json
import sys
from decimal import Decimal

import pandas as pd

D = "weka_demo"
cli = pd.read_csv(f"{D}/cli_predictions.csv", dtype=str)
p_cli = [Decimal(row[cli.columns[5]].lstrip("*")) for _, row in cli.iterrows()]          # 2nd distribution column = Present
actual = [a.split(":")[1] for a in cli.actual]
pipe = pd.read_csv(f"{D}/pipeline_RF_pred_A_stft_r0_f0.csv", dtype=str)
p_pipe = [Decimal(x) for x in pipe.p_present]
ids = pd.read_csv(f"{D}/A_stft_r0_f0_outer_test.ids.csv")
saved = pd.read_csv("results/predictions/repro_mac_predictions.csv")
saved = saved[(saved.set == "A_stft") & (saved.clf == "RF") & (saved.repeat == 0) & (saved.fold == 0)].set_index("patient_id")
p_saved = [Decimal(f"{saved.score[p]:.10f}") for p in ids.patient_id]
v1 = pd.read_csv("results/predictions/main_predictions.csv")
v1 = v1[(v1.set == "A_stft") & (v1.clf == "RF") & (v1.repeat == 0) & (v1.fold == 0)].set_index("patient_id")
exact_file = len(p_cli) == len(p_pipe) and all(a == b for a, b in zip(p_cli, p_pipe))
exact_saved = all(a == b for a, b in zip(p_cli, p_saved))
same_labels = actual == list(pipe.actual)
pred = ["Present" if p > Decimal("0.5") else "Absent" for p in p_cli]                    # argmax; tie 0.5 -> Absent (index 0)
cm = dict(TN=sum(a == "Absent" and b == "Absent" for a, b in zip(actual, pred)), FP=sum(a == "Absent" and b == "Present" for a, b in zip(actual, pred)),
          FN=sum(a == "Present" and b == "Absent" for a, b in zip(actual, pred)), TP=sum(a == "Present" and b == "Present" for a, b in zip(actual, pred)))
res = dict(n_test=len(p_cli), cli_equals_pipeline_pred_file_exactly=exact_file, cli_equals_repro_mac_predictions_exactly=exact_saved,
           actual_labels_identical=same_labels, confusion_matrix_at_0_5=cm, ties_at_0_5=sum(p == Decimal("0.5") for p in p_cli),
           max_abs_diff_vs_frozen_linux_v1=float(max(abs(float(a) - v1.score[p]) for a, p in zip(p_cli, ids.patient_id))))
json.dump(res, open(f"{D}/check_result.json", "w"), indent=2)
print(json.dumps(res, indent=2))
sys.exit(0 if exact_file and exact_saved and same_labels else 1)
