#!/usr/bin/env bash
# Runs every test that reads app/ or frontend/src SOURCE TEXT. Comment edits can break these
# (some count how often a name is mentioned, comments included), so every comment plan of
# Phase 241 runs them before committing.
#
# Usage (from the checkout root):
#   bash .planning/phases/241-codebase-cleanup/tools/source_scan_tests.sh [--py] [--fe]
# Default is both parts. Measured at planning time: py part ~25 s, fe part ~5 s.
set -euo pipefail

run_py=0
run_fe=0
if [ "$#" -eq 0 ]; then
  run_py=1
  run_fe=1
fi
for arg in "$@"; do
  case "$arg" in
    --py) run_py=1 ;;
    --fe) run_fe=1 ;;
    *)
      echo "usage: $0 [--py] [--fe]" >&2
      exit 2
      ;;
  esac
done

if [ "$run_py" -eq 1 ]; then
  echo "== source-scan tests (python) =="
  uv run pytest -q -n 4 -p no:warnings \
    tests/services/test_eval_utils.py \
    tests/services/test_sharp_filler.py \
    tests/test_no_conversion_elo_string.py \
    tests/test_users_account_type_invariant.py \
    tests/test_push_send.py \
    "tests/test_endgame_service.py::test_K_constant_deleted_from_endgame_service" \
    tests/schemas/test_train_telemetry_parity.py \
    tests/services/test_train_score_parity.py \
    tests/services/test_opening_insights_arrow_consistency.py
  uv run pytest -q -p no:warnings \
    tests/test_library_repository.py \
    tests/services/test_insights_service.py \
    tests/services/test_stats_service_phase_entry.py \
    tests/services/test_train_leaderboard.py \
    -k "family_to_motif_ints or module_source or no_asyncio_gather or frontend or _ts or parity"
fi

if [ "$run_fe" -eq 1 ]; then
  echo "== source-scan tests (frontend) =="
  if [ ! -d frontend/node_modules ]; then
    echo "run npm --prefix frontend ci" >&2
    exit 2
  fi
  (
    cd frontend
    npx vitest run \
      src/__tests__/noEndgameSkillString.test.tsx \
      src/components/move-explorer/__tests__/MoveExplorer.test.tsx \
      src/lib/engine/__tests__/engineAssetCache.test.ts \
      src/lib/engine/__tests__/stockfishWorkerSource.test.ts \
      src/lib/engine/__tests__/ortRuntimeMemoryCap.test.ts \
      src/lib/engine/__tests__/maiaWorkerScript.test.ts \
      src/pages/__tests__/Import.endgameOverviewInvalidation.test.ts \
      src/pages/__tests__/Import.stateMachine.test.tsx \
      src/__tests__/pushServiceWorker.test.ts
  )
fi
