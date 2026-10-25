#!/usr/bin/env bash
# One V3 run = 4 fresh headless Claude Code sessions against SolidCraft 0.22.0 (fit-edits lab, SolidCraft for Beginners #8):
#   edit 0: build the plate + peg block (0.2 mm each side); edit 1: pegs 5 -> 6 mm; edit 2: a third peg in the middle;
#   edit 3: plate 5 -> 8 mm. Each session starts in a NEW empty working folder holding only the saved design from the
#   session before (and, in arm c, a CLAUDE.md), with no session persistence, auto memory off, every CLAUDE.md outside
#   the working folder excluded; a file search before each session and an InstructionsLoaded hook log record what was
#   there and what Claude Code loaded.
#   bash claude-run/run.sh once|named|claudemd RUN_ID
# Arms: once = the gap only in prompt 0; named = prompt 0 asks for a named parameter fit_gap; claudemd = named + a
# CLAUDE.md rule in every session's folder. The edit prompts never mention the gap.
set -euo pipefail
ARM=$1; RUN=$2
cd "$(dirname "$0")/.."
LAB="$(pwd -W 2>/dev/null || pwd)"
OUTR=out/runs/$ARM-$RUN
LEDGER="${LEDGER:-$LAB/../ai-cad-set-BUDGET.tsv}"
MODEL="${MODEL:-claude-sonnet-5-5}"
BUDGET="${BUDGET:-0.60}"
[ -e "$OUTR/run-meta.json" ] && { echo "refusing to overwrite $OUTR"; exit 3; }
mkdir -p "$OUTR"
BASE0="Use the solidcraft MCP tools. In a new design, make two parts that fit together. A peg block: 80 x 30 x 4 mm, lying flat, with two round pegs 5 mm in diameter and 5 mm tall on its top face, 40 mm apart, centred along the block's long axis. A plate: 80 x 30 x 5 mm that sits on top of the block, with two holes the pegs pass through, with a 0.2 mm gap on each side of each peg (each hole 0.4 mm bigger than its peg). Name the bodies PegBlock and Plate."
case "$ARM" in
  once) P0="$BASE0" ;;
  named|claudemd) P0="$BASE0 Make the gap a named parameter called fit_gap, and size the holes from it." ;;
  *) echo "arm: once|named|claudemd"; exit 4 ;;
esac
SAVE="Save the design to /lab/work/fit.solidcraft."
PROMPTS=("$P0 $SAVE"
  "Use the solidcraft MCP tools. Open /lab/work/fit.solidcraft. Make the pegs 6 mm in diameter. $SAVE"
  "Use the solidcraft MCP tools. Open /lab/work/fit.solidcraft. Add a third peg in the middle of the block, between the other two. $SAVE"
  "Use the solidcraft MCP tools. Open /lab/work/fit.solidcraft. Make the plate 8 mm thick. $SAVE")
RULE='# Notes for this project
- Every mating hole = peg diameter + 2 x fit_gap. fit_gap is a named parameter in the design; never hard-code the gap.'
PREV=""
for E in 0 1 2 3; do
  python claude-run/budget.py check "$LEDGER" "$BUDGET" || { echo "BUDGET STOP"; exit 2; }
  S="$OUTR/edit-$E"; W="$S/work"
  mkdir -p "$W"
  [ -n "$PREV" ] && cp "$PREV/work/fit.solidcraft" "$W/fit.solidcraft"
  [ "$ARM" = claudemd ] && printf '%s\n' "$RULE" > "$W/CLAUDE.md"
  # what is in the session's folder and above it (AGENTS.md / CLAUDE.md / notes), before the session
  python claude-run/prerun.py "$W" > "$S/prerun-files.txt" 2>&1 || true
  printf '%s\n' "${PROMPTS[$E]}" > "$S/prompt.txt"
  NAME="fit-$ARM-$RUN-$E-$$"
  cat > "$S/mcp-config.json" <<JSON
{"mcpServers": {"solidcraft": {"command": "docker", "args": ["run", "-i", "--rm", "--name", "$NAME", "-v", "$LAB/proxy:/proxy:ro", "-v", "$LAB/$W:/lab/work", "-v", "$LAB/$S:/lab/log", "solidcraft-fit-edits-lab:0.22.0", "python3", "/proxy/mcp_log_proxy.py", "--log", "/lab/log/transcript.jsonl", "--png-dir", "/lab/log", "--watchdog", "180", "--", "solidcraft-cli", "mcp", "--allow-path", "/lab/work"]}}}
JSON
  HOOKLOG="$LAB/$S/instructions-loaded.jsonl"
  SETTINGS=$(python - "$HOOKLOG" <<'PY'
import json, sys
log = sys.argv[1].replace('\\', '/')
print(json.dumps({"claudeMdExcludes": ["**/.claude/CLAUDE.md"],
                  "autoMemoryEnabled": False,
                  "hooks": {"InstructionsLoaded": [{"hooks": [{"type": "command",
                            "command": f"python -c \"import sys; open(r'{log}', 'a').write(sys.stdin.read() + chr(10))\""}]}]}}))
PY
)
  T0=$(date +%s)
  set +e
  ( cd "$W" && MSYS_NO_PATHCONV=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 timeout 900 "${CLAUDE:-claude}" -p "${PROMPTS[$E]}" --model "$MODEL" \
      --mcp-config "$LAB/$S/mcp-config.json" --strict-mcp-config \
      --tools "" --allowedTools "mcp__solidcraft__*" --permission-mode dontAsk \
      --max-budget-usd "$BUDGET" --no-session-persistence \
      --setting-sources project,local --settings "$SETTINGS" \
      --output-format json < /dev/null > "$LAB/$S/claude-output.json" )
  RC=$?
  set -e
  docker kill "$NAME" >/dev/null 2>&1 || true
  sed -i "s#$LAB#\$LAB#g" "$S/mcp-config.json"
  COST=$(python -c "import json,sys
try: print(json.load(open(sys.argv[1]))['total_cost_usd'])
except Exception: print('')" "$S/claude-output.json")
  python claude-run/budget.py record "$LEDGER" "fit-$ARM-$RUN-e$E" "$COST" "$BUDGET" fit-edits
  echo "{\"arm\": \"$ARM\", \"run\": \"$RUN\", \"edit\": $E, \"exit\": $RC, \"wall_s\": $(( $(date +%s) - T0 )), \"cost\": \"${COST:-killed}\"}" > "$S/meta.json"
  [ -f "$W/fit.solidcraft" ] || { echo "edit $E saved no design: stop"; break; }
  PREV="$S"
done
echo "{\"arm\": \"$ARM\", \"run\": \"$RUN\", \"model\": \"$MODEL\", \"claude_version\": \"$(${CLAUDE:-claude} --version | head -1)\", \"solidcraft\": \"0.22.0\"}" > "$OUTR/run-meta.json"
cat "$OUTR/run-meta.json"
