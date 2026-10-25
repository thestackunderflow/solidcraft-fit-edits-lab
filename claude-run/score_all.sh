#!/usr/bin/env bash
# Score every V3 run's saved designs (each run folder mounted as /lab/out so SolidCraft may read it), then the table.
#   bash claude-run/score_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
LAB="$(pwd -W 2>/dev/null || pwd)"
for d in out/runs/*-*; do
  [ -d "$d" ] || continue
  [ -f "$d/edit-0/score.json" ] && continue
  MSYS_NO_PATHCONV=1 timeout 900 docker run --rm -v "$LAB:/work" -v "$LAB/$d:/lab/out" -w /work solidcraft-fit-edits-lab:0.22.0 \
    python3 claude-run/score.py design /lab/out > "$d/score.log" 2>&1 || true
done
MSYS_NO_PATHCONV=1 docker run --rm -v "$LAB:/work" -w /work solidcraft-fit-edits-lab:0.22.0 python3 claude-run/score.py table
