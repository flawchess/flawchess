#!/usr/bin/env bash
# Run the Phase 180 three-preset bot strength-curve sweep — all three presets in
# PARALLEL — then combine the per-preset aggregates and fit the internal-scale
# bot-curves JSON (SEED-104 interface).
#
# Each preset is a DIFFERENT ELO grid, so they cannot share one ledger
# (`--resume` refuses a changed grid). This script gives each preset its own
# --out-dir, launches all three at once, waits, then combines the three
# `-cells.tsv` aggregates into one and runs the fitter.
#
# Usage:
#   bin/run_bot_curves_sweep.sh                 # defaults: 24 games/cell, 4 SF procs/preset, seed 1
#   bin/run_bot_curves_sweep.sh --procs 3       # fewer SF procs each (if the box is busy)
#   bin/run_bot_curves_sweep.sh --games 30      # more games per (cell,anchor)
#   bin/run_bot_curves_sweep.sh --seed 2        # a different experiment seed
#   bin/run_bot_curves_sweep.sh --no-fit        # run the sweep only; skip combine + fit
#
# Resume: if a preset's out-dir already holds a ledger from a prior (killed) run,
# this script auto-resumes THAT preset from it. The three presets are independent
# — a death in one never touches the others.
#
# CPU model (verified): Maia is onnxruntime-web wasm pinned to 1 thread; Stockfish
# is the -single wasm build, 1 thread per proc. So the parallel footprint is
# roughly (3 Maia) + (3 x --procs) cores. On a 16-core box, --procs 4 (=> ~15
# cores) is the sweet spot. Drop to 3 if other work (e.g. tier-4 workers) is live.
set -euo pipefail

cd "$(dirname "$0")/.."

# ── Defaults ────────────────────────────────────────────────────────────────
STOCKFISH_PROCS=4
GAMES_PER_CELL=24
SEED=1
RUN_FIT=1

DATA_DIR="reports/data"
HARNESS="scripts/calibration-harness.mjs"
HOOK="scripts/lib/frontend-alias-hook.mjs"
FITTER="scripts/calibration_anchor_fit.py"
COMBINED_TSV="${DATA_DIR}/bot-cells-sweep.tsv"
OUT_CURVES="${DATA_DIR}/bot-curves-internal-scale.json"

# Preset grids (D-03/D-04): "name|blend|elo-csv". Each is a separate invocation.
PRESETS=(
  "human|0|700,1100,1500,1900,2300"
  "light|0.05|1100,1300,1500,1700,1900"
  "deep|0.5|1100,1500,1900,2300,2600"
)

# ── Parse flags ─────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --procs) STOCKFISH_PROCS="${2:?--procs needs a value}"; shift 2 ;;
    --games) GAMES_PER_CELL="${2:?--games needs a value}"; shift 2 ;;
    --seed)  SEED="${2:?--seed needs a value}"; shift 2 ;;
    --no-fit) RUN_FIT=0; shift ;;
    -h|--help) awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "ERROR: unknown flag '$1' (see --help)" >&2; exit 2 ;;
  esac
done

# ── Preflight ───────────────────────────────────────────────────────────────
# Guard against the duplicate-run footgun: refuse if a harness is already live.
# Match only actual `node` processes (via `ps -C node`), NOT shell command lines
# that merely mention the path — otherwise an open editor / a shell history entry
# would false-trigger.
if ps -C node -o args= 2>/dev/null | grep -q "calibration-harness\.mjs"; then
  echo "ERROR: a calibration-harness.mjs node process is already running. Only one" >&2
  echo "       sweep may write engine output at a time. Kill it or wait, then re-run." >&2
  echo "       Offenders:" >&2
  ps -C node -o pid=,args= 2>/dev/null | grep "calibration-harness\.mjs" >&2 || true
  exit 1
fi

CORES="$(nproc)"
FOOTPRINT=$(( ${#PRESETS[@]} * STOCKFISH_PROCS + ${#PRESETS[@]} ))  # 3*procs SF + 3 Maia
LOAD1="$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo '?')"
echo "── Bot-curves sweep preflight ──────────────────────────────────────────"
echo "  cores=${CORES}  current 1m-load=${LOAD1}"
echo "  presets=${#PRESETS[@]} (parallel)  procs/preset=${STOCKFISH_PROCS}  games/cell=${GAMES_PER_CELL}  seed=${SEED}"
echo "  est. core footprint ≈ ${FOOTPRINT} (3 Maia + 3×${STOCKFISH_PROCS} Stockfish)"
if [ "$FOOTPRINT" -gt "$CORES" ]; then
  echo "  ⚠ footprint ${FOOTPRINT} > ${CORES} cores — consider --procs $(( (CORES - ${#PRESETS[@]}) / ${#PRESETS[@]} ))" >&2
fi
echo "────────────────────────────────────────────────────────────────────────"

# ── Kill children on Ctrl-C / TERM so a stray engine pool never lingers ──────
PIDS=()
cleanup() {
  echo ""; echo "Interrupted — stopping sweep processes..." >&2
  for p in "${PIDS[@]:-}"; do
    [ -n "$p" ] && kill -TERM "$p" 2>/dev/null || true
  done
  # Best-effort reap of the engine children.
  pkill -TERM -f "calibration-harness.mjs" 2>/dev/null || true
  exit 130
}
trap cleanup INT TERM

# Finds the resumable main ledger in a preset dir (excludes -cells/-summary
# siblings). Echoes the path, or nothing if there is no prior run.
find_resume_ledger() {
  local dir="$1"
  find "$dir" -maxdepth 1 -name 'calibration-harness-*.tsv' \
    ! -name '*-cells.tsv' ! -name '*-summary.tsv' 2>/dev/null | sort | tail -n1
}

# ── Launch the three presets in parallel ────────────────────────────────────
declare -A DIR_OF
for spec in "${PRESETS[@]}"; do
  IFS='|' read -r name blend elo <<<"$spec"
  outdir="${DATA_DIR}/sweep-${name}"
  DIR_OF["$name"]="$outdir"
  mkdir -p "$outdir"

  resume_args=()
  prior="$(find_resume_ledger "$outdir")"
  if [ -n "$prior" ]; then
    echo "  [${name}] resuming from ${prior}"
    resume_args=(--resume "$prior")
  fi

  echo "  [${name}] launching: blend=${blend} elo=${elo} → ${outdir}/run.log"
  node --import "./${HOOK}" "$HARNESS" \
    --blends "$blend" --elo "$elo" \
    --games-per-cell "$GAMES_PER_CELL" --stockfish-procs "$STOCKFISH_PROCS" \
    --seed "$SEED" --out-dir "$outdir" "${resume_args[@]}" \
    >"${outdir}/run.log" 2>&1 &
  PIDS+=("$!")
done

echo ""
echo "All ${#PRESETS[@]} presets running (PIDs: ${PIDS[*]}). Tail a log to watch, e.g.:"
echo "  tail -f ${DATA_DIR}/sweep-human/run.log"
echo ""

# ── Wait; collect per-preset exit codes ─────────────────────────────────────
FAILED=0
i=0
for spec in "${PRESETS[@]}"; do
  IFS='|' read -r name _ _ <<<"$spec"
  pid="${PIDS[$i]}"
  if wait "$pid"; then
    echo "  [${name}] ✓ finished (exit 0)"
  else
    echo "  [${name}] ✗ FAILED — see ${DIR_OF[$name]}/run.log" >&2
    FAILED=1
  fi
  i=$((i + 1))
done
trap - INT TERM

if [ "$FAILED" -ne 0 ]; then
  echo "" >&2
  echo "ERROR: at least one preset failed. Fix it and re-run — completed presets" >&2
  echo "       auto-resume from their ledgers; skipping combine + fit." >&2
  exit 1
fi

echo ""
echo "All presets complete."

if [ "$RUN_FIT" -eq 0 ]; then
  echo "--no-fit set: skipping combine + fit. Aggregates are in ${DATA_DIR}/sweep-*/."
  exit 0
fi

# ── Combine the three -cells.tsv aggregates (one header, all data rows) ──────
echo "Combining per-preset aggregates → ${COMBINED_TSV}"
CELLS_FILES=()
for spec in "${PRESETS[@]}"; do
  IFS='|' read -r name _ _ <<<"$spec"
  f="$(find "${DIR_OF[$name]}" -maxdepth 1 -name '*-cells.tsv' | sort | tail -n1)"
  [ -z "$f" ] && { echo "ERROR: no -cells.tsv found for preset '${name}' in ${DIR_OF[$name]}" >&2; exit 1; }
  CELLS_FILES+=("$f")
done
head -n1 "${CELLS_FILES[0]}" >"$COMBINED_TSV"
tail -q -n +2 "${CELLS_FILES[@]}" >>"$COMBINED_TSV"

# ── Fit ─────────────────────────────────────────────────────────────────────
echo "Fitting → ${OUT_CURVES}"
uv run python "$FITTER" --bot-input "$COMBINED_TSV" --out-bot-curves "$OUT_CURVES"

echo ""
echo "── Done ────────────────────────────────────────────────────────────────"
echo "  combined cells: ${COMBINED_TSV}"
echo "  bot-curves:     ${OUT_CURVES}"
echo "  Next: write the findings note (Plan 04 Task 3, step 3) mirroring"
echo "        .planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md"
