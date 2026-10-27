#!/usr/bin/env bash
# Build the two input folders from the PhysioNet v1.0.3 download without editing the download
# (docs/PROTOCOL_V2_LOCKED.md amendment D1). Both are directories of per-file symlinks, laid out as the
# scripts expect (README "Data": training_data/* plus training_data.csv and SHA256SUMS.txt in one folder):
#   data/raw/circor_training_data/      v1.0.3 exactly as downloaded            -> all Phase-2 runs
#   data/interim/repro_phase1_view/     same, except 50782.txt is a COPY of the Phase-1 copy's header
#                                       (github.com/chihoon1/Murmur@56b9846, sha256-verified against
#                                       references/data_provenance/circor_copy_SHA256SUMS.txt), so 50782_MV_1
#                                       has no segmentation as in Phase 1  -> docs/REPRO_MAC.md only
#
# usage: bash scripts/17_make_data_views.sh V103_ROOT   (folder holding SHA256SUMS.txt, training_data.csv, training_data/)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$1" && pwd)"
RAW="$REPO/data/raw/circor_training_data"
VIEW="$REPO/data/interim/repro_phase1_view"
URL="https://raw.githubusercontent.com/chihoon1/Murmur/56b9846/data/training_data/50782.txt"
WANT="$(grep ' training_data/50782.txt$' "$REPO/references/data_provenance/circor_copy_SHA256SUMS.txt" | cut -d' ' -f1)"

link_all() {   # $1 = target dir, $2 = file name to skip (optional)
  mkdir -p "$1"
  for f in "$ROOT"/training_data/* "$ROOT/training_data.csv" "$ROOT/SHA256SUMS.txt"; do
    b="$(basename "$f")"
    [ "$b" = "${2:-}" ] || ln -s "$f" "$1/$b"
  done
}

for d in "$RAW" "$VIEW"; do
  if [ -L "$d" ]; then rm "$d"; elif [ -e "$d" ]; then echo "$d exists; remove it first" >&2; exit 1; fi
done
link_all "$RAW"
link_all "$VIEW" 50782.txt
curl -sf -o "$VIEW/50782.txt" "$URL"
GOT="$(shasum -a 256 "$VIEW/50782.txt" | cut -d' ' -f1)"
[ "$GOT" = "$WANT" ] || { echo "50782.txt sha256 $GOT != Phase-1 copy $WANT" >&2; exit 1; }
echo "raw : $RAW ($(ls "$RAW" | wc -l | tr -d ' ') symlinks)"
echo "view: $VIEW ($(ls "$VIEW" | wc -l | tr -d ' ') entries; 50782.txt = Phase-1 copy, sha256 $GOT)"
