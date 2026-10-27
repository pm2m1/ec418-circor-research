#!/usr/bin/env bash
# Re-run the Phase-1 data scripts (01 audit, 03 B1, 04 folds, 02 features, 10 smoothed WPD) UNMODIFIED, but
# with a shadow working directory as cwd, so every output lands there instead of on top of the frozen files
# in results/v1_freeze/MANIFEST_v1.sha256. Compare afterwards with scripts/14_repro_mac_compare.py.
#
# usage: bash scripts/13_repro_mac_shadow.sh [SHADOW_DIR]   (default data/interim/repro_mac_shadow, gitignored)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SH="${1:-$REPO/data/interim/repro_mac_shadow}"
PY="$REPO/.venv/bin/python"

mkdir -p "$SH"/{configs,results/tables,results/logs,results/figures,data/processed,data/raw,references}
cp "$REPO/configs/protocol.json" "$SH/configs/"
ln -sfn "$REPO/data/raw/circor_training_data" "$SH/data/raw/circor_training_data"
ln -sfn "$REPO/references/baseline_repo" "$SH/references/baseline_repo"
cd "$SH"

"$PY" "$REPO/scripts/01_dataset_audit.py"            > results/logs/01_dataset_audit.out
"$PY" "$REPO/scripts/04_make_folds.py"               > results/logs/04_make_folds.out
"$PY" "$REPO/scripts/03_b1_realign_shipped_features.py" > results/logs/03_b1.out
NPROC="${NPROC:-8}" "$PY" "$REPO/scripts/02_extract_features.py" > results/logs/02_extract_features.out
"$PY" "$REPO/scripts/10_posthoc_wpd_smoothing.py"    > results/logs/10_posthoc_wpd_smoothing.out
echo "shadow outputs in $SH"
