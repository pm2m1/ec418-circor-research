#!/usr/bin/env bash
# Re-run Phase-1 data scripts UNMODIFIED, with a shadow working directory as cwd, so every output lands there
# instead of on top of the frozen files in results/v1_freeze/MANIFEST_v1.sha256. Compare afterwards with
# scripts/14_repro_mac_compare.py.
#
# usage: bash scripts/13_repro_mac_shadow.sh SHADOW_DIR DATA_DIR [STEPS]
#   DATA_DIR : recordings folder the shadow's data/raw/circor_training_data points to
#              (v1.0.3 download, or the Phase-1 view from scripts/17_make_data_views.sh)
#   STEPS    : subset of "01 04 03 02 10" (default: all, in that order)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SH="$1"
DATA="$(cd "$2" && pwd)"
STEPS="${3:-01 04 03 02 10}"
PY="$REPO/.venv/bin/python"

mkdir -p "$SH"/{configs,results/tables,results/logs,results/figures,data/processed,data/raw,references}
cp "$REPO/configs/protocol.json" "$SH/configs/"
ln -sfn "$DATA" "$SH/data/raw/circor_training_data"
ln -sfn "$REPO/references/baseline_repo" "$SH/references/baseline_repo"
cd "$SH"

for s in $STEPS; do
  case $s in
    01) "$PY" "$REPO/scripts/01_dataset_audit.py"               > results/logs/01_dataset_audit.out ;;
    04) "$PY" "$REPO/scripts/04_make_folds.py"                  > results/logs/04_make_folds.out ;;
    03) "$PY" "$REPO/scripts/03_b1_realign_shipped_features.py" > results/logs/03_b1.out ;;
    02) NPROC="${NPROC:-8}" "$PY" "$REPO/scripts/02_extract_features.py" > results/logs/02_extract_features.out ;;
    10) "$PY" "$REPO/scripts/10_posthoc_wpd_smoothing.py"       > results/logs/10_posthoc_wpd_smoothing.out ;;
    *) echo "unknown step $s" >&2; exit 2 ;;
  esac
  echo "step $s done"
done
echo "shadow outputs in $SH (data: $DATA)"
