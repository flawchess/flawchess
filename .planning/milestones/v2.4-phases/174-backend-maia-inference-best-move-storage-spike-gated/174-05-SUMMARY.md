---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
plan: 05
subsystem: backend
tags: [maia, onnxruntime, eval-apply, best-move, gems, stockfish, rss, gem-great]

# Dependency graph
requires:
  - phase: 174-backend-maia-inference-best-move-storage-spike-gated
    plan: 03
    provides: game_best_moves candidate table (composite (game_id, ply) PK, CASCADE FK, continuous-only storage).
  - phase: 174-backend-maia-inference-best-move-storage-spike-gated
    plan: 04
    provides: maia_engine.score_move + best_move_candidates (pinned_elo_for_mover, passes_inaccuracy_gate, mover_color_for_ply).
provides:
  - eval_apply._build_best_move_candidates — off-session builder that emits game_best_moves candidate rows for out-of-book played==best plies passing the inaccuracy gate (GEMS-03).
  - eval_apply._upsert_best_move_rows — idempotent ON CONFLICT (game_id, ply) upsert inside apply_full_eval's shared write session (T-174-12).
  - Pitfall-1 targeted backend-owned evaluate_nodes_multipv2 fallback for played==best plies lacking second-best (remote-worker MultiPV-1 lane) — no worker-protocol change.
  - _FullPlyEvalTarget.move_uci / move_san captured in the existing PGN walk (Pitfall 3/4).
  - scripts/measure_maia_rss.py — steady-state Maia RSS gate vs the 4GB container budget (D-03b).
affects: [phase-175, phase-176, gem-great-classification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Session-closed-then-gather off-session builder (mirrors _build_flaw_multipv2_blobs): candidate identification is pure in-memory, the Stockfish fallback gather runs with NO session open, rating metadata is read in a short session closed before Maia inference, and rows persist in apply_full_eval's LATE write session (same commit)."
    - "Both eval-apply lanes funnel candidate rows through the ONE shared apply_full_eval write body: local drain passes its whole-game second_best_map; the remote atomic-submit lane passes None so every candidate takes the targeted MultiPV-2 fallback (Pitfall 1) — the worker protocol / atomic-submit schema stay untouched."
    - "Gem detection is a fail-open secondary concern: any unexpected builder failure is Sentry-captured and yields no rows, never aborting the primary eval/flaw write; Maia-disabled (onnxruntime absent, score_move None) degrades to zero rows."

key-files:
  created:
    - scripts/measure_maia_rss.py
    - tests/services/test_eval_apply.py
  modified:
    - app/services/eval_apply.py
    - app/services/eval_drain.py
    - app/routers/eval_remote.py

key-decisions:
  - "The builder runs OFF-SESSION in each lane (before write_session opens) and returns row dicts; apply_full_eval UPSERTs them in its own write session — the only shape that satisfies BOTH the CLAUDE.md no-gather-under-session rule AND the same-commit atomicity requirement (T-174-12). apply_full_eval itself can't gather because it receives an already-open write_session."
  - "Played move UCI/SAN captured on _FullPlyEvalTarget during the existing _collect_full_ply_targets PGN walk (no re-parse, no fresh query — Pitfall 3); the out-of-book test uses the contiguous SAN prefix from ply 0 so lichess-filtered targets never mis-detect book depth."
  - "eval_remote.py (the remote atomic-submit lane) was modified even though it was not in the plan's files_modified list — without it the remote-worker lane (per Pitfall 1, plausibly the majority of games) would get ZERO candidate rows, defeating GEMS-03's 'every newly analyzed game'."
  - "best/second cp sourced white-POV from engine_result_map (best) + second_best_map-or-fallback (second), matching the flaw pipeline's convention; the mover's pinned+clamped lichess-blitz ELO comes from the Game row read (white/black rating by ply parity), skipping candidates with no rating."

patterns-established:
  - "Candidate-row builder: off-session Maia inference + bounded targeted Stockfish fallback, persisted in the shared eval-apply commit."

requirements-completed: [GEMS-03]

coverage:
  - id: D1
    description: "An out-of-book played==best ply passing the >=0.05 inaccuracy gate yields exactly one candidate row (maia_prob + raw best/second cp); a sub-margin, in-book, or played!=best ply yields none (GEMS-02/03)."
    requirement: "GEMS-03"
    verification:
      - kind: integration
        ref: "tests/services/test_eval_apply.py::TestCandidateGate (out_of_book_played_best_yields_row, below_margin_no_row, in_book_ply_no_row, played_not_best_no_row, maia_disabled_no_rows)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A played==best out-of-book ply with MISSING second-best (remote-worker MultiPV-1 lane) fires a targeted backend evaluate_nodes_multipv2 fallback and still produces a row; no fallback fires when second-best is present (Pitfall 1)."
    requirement: "GEMS-03"
    verification:
      - kind: integration
        ref: "tests/services/test_eval_apply.py::TestPitfall1Fallback (missing_second_best_triggers_targeted_fallback, no_fallback_when_second_best_present)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Re-running the builder over the same game upserts on (game_id, ply) — updates in place, no duplicate rows (T-174-12)."
    requirement: "GEMS-03"
    verification:
      - kind: integration
        ref: "tests/services/test_eval_apply.py::TestUpsertIdempotency (upsert_updates_in_place, upsert_empty_is_noop)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Worker protocol untouched: no Maia/onnxruntime import in scripts/remote_eval_worker.py and no change to the /atomic-submit contract (app/schemas/eval_remote.py) (D-3/GEMS-03)."
    requirement: "GEMS-03"
    verification:
      - kind: other
        ref: "grep -icE 'maia|onnxruntime' scripts/remote_eval_worker.py == 0; git diff main -- app/schemas/eval_remote.py scripts/remote_eval_worker.py == 0 files"
        status: pass
    human_judgment: false
  - id: D5
    description: "Steady-state backend RSS with the Maia session + a one-game inference burst is measured against the 4GB budget alongside the 6-worker Stockfish pool; soft-gates on a documented headroom (D-03b, Pitfall 5)."
    requirement: "GEMS-03"
    verification:
      - kind: other
        ref: "uv run python scripts/measure_maia_rss.py — Maia ~235 MiB, projected total ~2743/4096 MiB, exit 0"
        status: pass
    human_judgment: false
  - id: D6
    description: "Live-board gem vs stored-DB gem agreement for the same position/rating (cross-stack UAT), deferred to the Phase 175 board-read surface — no board read exists in Phase 174."
    verification: []
    human_judgment: true
    rationale: "Requires the Phase 175 board-read surface to compare a live-computed gem marker against the stored maia_prob tier; not implementable or verifiable within Phase 174."

# Metrics
duration: 45min
completed: 2026-07-16
status: complete
---

# Phase 174 Plan 05: Best-Move Candidate Builder in Eval-Apply Summary

> **Post-verification correction (2026-07-16).** This summary originally claimed
> full candidate coverage for "every newly analyzed game (local OR remote-worker
> lane)". Phase verification (see `174-VERIFICATION.md` Truth 2, and CR-01/WR-02
> in `174-REVIEW.md`) found that is **not** true for **lichess-eval games**
> (`lichess_evals_at IS NOT NULL`, ~6.0% of prod games / 18% of lichess games).
> On the local drain lane their `targets` are pre-filtered to holes +
> flaw-adjacent plies (`eval_drain.py:738-745`), so `book_plies` collapses to ~0
> and non-flaw out-of-book best moves are never nominated (those plies carry no
> Stockfish best move). Coverage there is limited to flaw-adjacent plies. Full,
> exact coverage holds for the chess.com / non-eval-lichess and remote-worker
> lanes (the 94%+ path). Closing the lichess-eval gap is deferred to **SEED-109**
> (full-analyze lichess games / retire the special-case lane), to be inserted as
> a phase before Phase 176. The line below and the T-174-11 note about
> "lichess-filtered targets never mis-detect book depth" are the inaccurate
> originals, kept for provenance.

**The load-bearing integration: an off-session candidate-row builder wired into the ONE shared `apply_full_eval` write body so every newly analyzed game (local drain OR remote-worker lane) gets `game_best_moves` rows — out-of-book played==best plies passing the 0.05 inaccuracy gate, scored by backend Maia-3 at the mover's pinned ELO, with a targeted Stockfish MultiPV-2 fallback covering the remote-worker lane's missing second-best (Pitfall 1), all persisted in the same commit as the eval; plus an RSS budget gate (D-03b) measuring Maia at ~235 MiB, well inside the 4GB container alongside the 6-worker Stockfish pool.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-16
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- **`app/services/eval_apply.py`** — `_build_best_move_candidates` (off-session, session-closed-then-gather) + `_upsert_best_move_rows` (idempotent PG upsert), wired into `apply_full_eval` via a new `best_move_rows` param so rows land in the shared write commit. `_FullPlyEvalTarget` gained `move_uci`/`move_san`, captured during the existing `_collect_full_ply_targets` PGN walk (Pitfall 3/4). The builder: computes the out-of-book book depth from the contiguous SAN prefix; selects out-of-book plies where the played UCI == the ply's Stockfish best_move; runs the Pitfall-1 targeted `evaluate_nodes_multipv2` fallback (one gather, no session) for plies lacking a runner-up; reads the mover's rating/platform/TC in a short session closed before inference; applies `passes_inaccuracy_gate`; and for survivors scores the played move with `score_move` at the `pinned_elo_for_mover` ELO, emitting a `GameBestMove` row. Fail-open: unexpected errors are Sentry-captured and yield no rows; Maia-disabled yields no rows.
- **`app/services/eval_drain.py`** — the local `_full_drain_tick` calls the builder (passing its whole-game `second_best_map`, so the fallback rarely fires) right after `_build_flaw_multipv2_blobs`, and threads `best_move_rows` into `apply_full_eval`.
- **`app/routers/eval_remote.py`** — the remote `_apply_atomic_submit` calls the builder with `second_best_map=None` (every candidate takes the targeted fallback, Pitfall 1) and threads `best_move_rows` through. The `/atomic-submit` schema and worker are untouched.
- **`scripts/measure_maia_rss.py`** — loads the eager Maia session, runs a 20-call inference burst (one game's candidate volume), prints baseline/post-load/post-burst RSS + the Maia total summed against the 4GB budget alongside engine.py's 6-worker Stockfish residency, and soft-gates (exit non-zero) on a documented 512 MiB Maia headroom or a >4GB projected total.
- **`tests/services/test_eval_apply.py`** (new) — 9 tests: candidate gate (yields/sub-margin/in-book/played!=best/Maia-disabled), Pitfall-1 fallback (fires + row / no-fire when present), idempotent upsert (in-place update / empty no-op). Gate + fallback run in the default suite with `score_move` and the Stockfish fallback monkeypatched.

## Measured RSS (D-03b, Pitfall 5)

Local run of `uv run python scripts/measure_maia_rss.py` (onnxruntime 1.20.1 synced):

| Metric | Value |
|---|---|
| baseline RSS (no session) | ~35 MiB |
| after `start_maia()` load | ~122 MiB (Δ +87) |
| after 20-call inference burst | ~270 MiB (Δ +149) |
| **Maia session total RSS** | **~235 MiB** |
| Stockfish pool (6×368 MB, engine.py accounting) | 2208 MiB |
| FastAPI/Uvicorn baseline | 300 MiB |
| **projected backend total** | **~2743 / 4096 MiB** |

Maia fits the 4GB budget with ~1.3 GB headroom alongside the 6-subprocess Stockfish pool — well under the documented 512 MiB Maia headroom. This empirically replaces the "~44 MB model file size" estimate with real InferenceSession RSS. **Prod enablement remains gated:** enabling backend Maia in prod (adding `--group maia-inference` to the backend Dockerfile) is a human decision confirmed by this measurement; if a future onnxruntime bump or model change pushes it over budget, the documented escape hatch (Maia-on-workers) is a human decision, not auto-taken (D-02/D-03).

## Observed candidate-row volume

Per SEED-108 the expected volume is ~10–20 out-of-book best-move plies/game (the RSS burst used 20 = one game's worth). The row-writing plumbing is proven end-to-end by the tests (build → upsert → read-back); an empirical dev-DB dry-run count across a real game corpus is a prod-enablement diagnostic (threat T-174-10) tied to backend-Maia enablement, not a blocking task here (backend Maia is not yet enabled and no board-read surface exists until Phase 175).

## Gate / Prohibition Status

| Prohibition | Status | Evidence |
|---|---|---|
| Maia MUST NOT run on remote workers / change the worker protocol (D-3/GEMS-03) | ENFORCED | `grep -icE 'maia|onnxruntime' scripts/remote_eval_worker.py` == 0; `git diff main -- app/schemas/eval_remote.py scripts/remote_eval_worker.py` == 0 files. The remote fallback runs on the BACKEND's own SCHED_IDLE Stockfish pool. |
| Builder MUST NOT assume second-best coverage — missing coverage triggers the targeted fallback, not a dropped candidate (Pitfall 1) | ENFORCED | `test_missing_second_best_triggers_targeted_fallback` proves a played==best ply with no second-best still yields a row via a targeted `evaluate_nodes_multipv2` call (spy await_count == 1). |
| No asyncio.gather over engine/inference while an AsyncSession is open (CLAUDE.md hard rule) | ENFORCED | The builder identifies candidates in-memory, gathers the Stockfish fallback with NO session open, and reads rating metadata in a short session CLOSED before any Maia inference; rows persist in apply_full_eval's late write session. |
| Steady-state RSS measured vs the 4GB budget before prod enablement (D-03b) | ENFORCED | `scripts/measure_maia_rss.py`: Maia ~235 MiB, projected ~2743/4096 MiB, exit 0. |

## Deviations from Plan

### Auto-fixed / necessary deviations

**1. [Rule 3 - Blocking] Modified `app/routers/eval_remote.py` (not in the plan's `files_modified`)**
- **Found during:** Task 1 (wiring both lanes).
- **Issue:** The plan's `files_modified` listed only `eval_apply.py`/`eval_drain.py`, but the plan's own must_haves require candidate rows for EVERY newly analyzed game including the remote-worker lane (`_apply_atomic_submit` lives in `eval_remote.py`). Because the builder must gather off-session (CLAUDE.md) yet persist in the same commit (T-174-12), it must be called before the write session in each lane — which requires touching the remote call site.
- **Fix:** Added the `_build_best_move_candidates(..., None)` call + `best_move_rows` pass-through in `_apply_atomic_submit`. The worker script and `/atomic-submit` schema stay untouched (the prohibition is scoped to those two files, which are unchanged).
- **Files modified:** app/routers/eval_remote.py
- **Committed in:** d8d2d0c3

**2. [Rule 3 - Blocking] Created `tests/services/test_eval_apply.py` (plan said "modified")**
- **Issue:** The plan listed the test file as MODIFIED, but no `tests/services/test_eval_apply.py` existed (eval-apply/shared-write-body tests live in `test_full_eval_drain.py`/`test_eval_drain.py`).
- **Fix:** Created the file with the three required test groups (gate, Pitfall-1 fallback, idempotency).
- **Committed in:** d8d2d0c3

---

**Total deviations:** 2 (both blocking necessities to fulfill the plan's own success criteria). No scope creep beyond what GEMS-03 requires.

## Issues Encountered

- **REAL (float32) round-trip:** `maia_prob` stored as REAL returns `0.41999998…` not `0.42`; the idempotency test uses `pytest.approx`.
- **ty tuple/dict invariance:** literal `engine_result_map`/`second_best_map` test dicts needed explicit type aliases to match the builder's `int | None` union params (dict/tuple invariance). Fixed with `_EngineResultMap`/`_SecondBestMap` aliases.
- **Script `sys.path`:** `scripts/measure_maia_rss.py` needs the repo root on `sys.path` (standard `scripts/` pattern) to `import app.*`.

## Deferred Issues

- **D-174-DEFER-01 (out of scope — Plan-04 file):** whole-tree `uv run ty check app/ tests/` surfaces 48 pre-existing `invalid-argument-type` errors in `tests/services/test_best_move_candidates.py` (Plan 04's test — NOT touched by this plan), the same tuple-literal invariance class fixed in this plan's own test. Plan 05's files are all ty-clean. Logged in `.planning/phases/174-.../deferred-items.md`; must be resolved before the phase pre-merge gate. Trivial fix: annotate the affected `classify_best_move` call literals.

## User Setup Required

None for this plan. Backend Maia prod enablement (adding `--group maia-inference` to the backend Dockerfile) is a separate, human-gated step confirmed by the RSS measurement above; `Dockerfile.worker` stays lean (GEMS-06).

## Next Phase Readiness

- `game_best_moves` candidate rows are now written on every newly analyzed game (both lanes). Phase 175 can read them and wire the board-read surface for the deferred live-vs-stored gem agreement UAT (D6).
- Reminder: real Maia inference requires the `maia-inference` group synced; the default no-group suite skips real-inference tests via `importorskip` (Plan 04) and this plan's tests run fully via monkeypatch.

## Self-Check: PASSED

All created/modified files present on disk (`scripts/measure_maia_rss.py`, `tests/services/test_eval_apply.py`, `app/services/eval_apply.py`, `app/services/eval_drain.py`, `app/routers/eval_remote.py`); both task commits (`d8d2d0c3`, `5b75c28e`) present in git history. 9/9 new tests green; full suite 3369 passed / 18 skipped; ty clean on all Plan-05 files; prohibition greps clean.

---
*Phase: 174-backend-maia-inference-best-move-storage-spike-gated*
*Completed: 2026-07-16*
