#!/usr/bin/env bash
# WEKA 3.9.7 command-line run of ONE pipeline fold: A_stft (cycle-aligned STFT bands, expert labels), repeat 0, outer
# fold 0, RandomForest with exactly the pipeline options. The ARFFs are copies of the pipeline's own files
# (experiments/repro_mac/arff/, written by scripts/06_run_patient_level_weka.py, unchanged). Run from the repo root:
#   bash weka_demo/run_cli.sh
# Outputs: weka_demo/cli_output.txt (WEKA evaluation summary + confusion matrix) and weka_demo/cli_predictions.csv
# (per-instance class distribution, 10 decimals). Then: .venv/bin/python weka_demo/check_cli_vs_pipeline.py
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
CP="tools/weka.jar:tools/mtj.jar:tools/arpack_combined.jar:tools/core.jar"
D=weka_demo
RF=(weka.classifiers.trees.RandomForest -I 300 -K 0 -S 1 -num-slots 1
    -t "$D/A_stft_r0_f0_outer_train.arff" -T "$D/A_stft_r0_f0_outer_test.arff" -o -v)
# 1) evaluation summary and confusion matrix (WEKA's default argmax decision = 0.5 threshold for two classes)
{ echo "\$ java -cp $CP ${RF[*]}"; java -cp "$CP" "${RF[@]}" 2>/dev/null; } > "$D/cli_output.txt"
# 2) per-instance class distribution, 10 decimals (the pipeline writes p_present with %.10f)
java -cp "$CP" "${RF[@]}" -classifications "weka.classifiers.evaluation.output.prediction.CSV -file $D/cli_predictions.csv -distribution -decimals 10" > /dev/null 2>&1
echo "wrote $D/cli_output.txt and $D/cli_predictions.csv"
