# Phase 148: Pipeline & tactic correctness fixes (code-review 2026-07-02) - Research

**Researched:** 2026-07-04
**Domain:** Backend correctness fixes — tactic-motif detection, eval-drain circuit breaking, statistical significance testing, import robustness, lease-scoping. No new libraries, no new endpoints, no schema changes.
**Confidence:** HIGH (all five fix sites read and verified in the current codebase this session; one path-level anchor drift found and corrected below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

User chose "leave the decisions to you" on every fork. The four genuine forks are
resolved below; the rest of each item follows the todo's prescribed fix verbatim.

**Item 1 — tactic mate fallback (recall vs precision)**
- **D-01:** On a truncated forced-mate PV (`has_forced_mate` set but the capped PV
  doesn't end in `is_checkmate()`), **tag generic `mate`** — do NOT suppress.
  Rationale: `has_forced_mate` derives from a real engine mate score; the PV is only
  truncated at `PV_CAP_PLIES = 12`, so the mate is genuine, not a false positive.
  Suppressing would drop a real tag (the current bug). Skip geometry-dependent mate
  subtypes when the line is truncated — we cannot verify the mating pattern.
- **D-02:** The `fen_map` fix stores full `board.fen()` in the **detector-internal**
  map only (for `parse_san` / PV replay). Keep `board_fen()` for Zobrist position
  comparisons per the CLAUDE.md rule — do not swap those call sites.
- **D-03:** Add `has_forced_mate` flag coverage (zero today). Research MUST re-run the
  tactic precision gate after this change — newly-tagging deep mates can shift
  `fixtures/tagger/*.csv` scores; confirm no motif regresses below its precision floor.

**Item 3 — quintile stats fix depth**
- **D-04:** Use the **covariance-correction term**, not a full paired test. Track the
  shared-game count `m` per (tc, quintile) and subtract the anti-correlated covariance
  (`+2m·cov/(n_u·n_o)` in the SE). Reuses the existing `compute_score_difference_test`
  path; point estimates are unaffected; least invasive. Also fix the wrong
  independence docstring at `endgame_service.py:2140-2143`.

**Item 5 — entry-submit scoping depth**
- **D-05:** Ship the **minimum guard** — add `entry_eval_lease_expiry > now()` to the
  submit guard. Do NOT build the full echoed-`game_ids`-intersection path; it's
  operator-error-triggered and the shipped worker uses random ids (low real-world
  likelihood). The fuller version is captured as a deferred idea.

**Plan decomposition**
- **D-06:** Recommend splitting into subsystem-cohesive plans so each has an isolated
  test + verify loop; final decomposition is the planner's call. Natural seams:
  (a) tactics = item 1, (b) eval-lease correctness = items 2 + 5 (both eval-pipeline
  lease/submit), (c) stats covariance = item 3, (d) import robustness = item 4.
  Whatever the grouping, **every one of the five items gets its own test + verify**.

### Claude's Discretion

- Exact test fixture selection and the precise covariance algebra are left to
  research/planning, constrained by the decisions above and the verification notes
  in the source todo.

### Deferred Ideas (OUT OF SCOPE)

- **Item 5 full scoping** — return claimed `game_ids` from `/entry-lease` and stamp
  only the echoed/intersected set. Deferred in favor of the minimum guard (D-05);
  capture as a seed if the worker ever moves off random ids.
- **SEED-077** — per-request `game_positions` aggregation elimination (import-time
  columns). Explicitly deferred in the triage; not this phase.
- **SEED-078** — chess.com archive streaming (OOM headroom). Explicitly deferred.
- Report items #8/#12/#13/#15 and tactic-recall (#14/6.2.1) — not scheduled; see triage.
</user_constraints>

## Project Constraints (from CLAUDE.md)

- **Sentry:** always `capture_exception()` in non-trivial `except` blocks in
  `app/services/`/`app/routers/`; never embed variables in the message text (use
  `set_context`/`set_tag`); retry loops capture on last attempt only (not applicable
  to items 2/4 — these are not retry loops, each iteration is a distinct game/batch).
- **`board_fen()` vs `fen()`:** use `board_fen()` (piece-placement only) for Zobrist
  position comparisons; item 1's fix is the one sanctioned exception — it swaps to
  full `fen()` **only** in the detector-internal `fen_map`, per D-02.
- **`asyncio.gather`** must never run inside an open `AsyncSession` — both drain
  loops already honor this (AST-scan tests enforce it); the item-2 fix must not move
  the gather call.
- **ty compliance** — zero `ty check app/ tests/` errors; no magic numbers; `#
  ty: ignore[rule-name]` with reason if unavoidable.
- **No dev DB reset in plans** — all five items' tests must run against the existing
  dev DB / test-DB-per-run isolation, never `bin/reset_db.sh`.

## Summary

All five fix sites were located and read in the current codebase. Two of the seven
file:line anchors in CONTEXT.md's Canonical References have drifted meaningfully
since the 2026-07-02 review (see the drift table at the end of this document) — most
importantly, `precision_floors.py` lives at `tests/scripts/tagger/precision_floors.py`,
**not** `app/services/precision_floors.py`, and the entry-ply drain's actual stamp
call (`_mark_evals_completed`) and the entry-submit function are both ~75-135 lines
further down their files than claimed. All five underlying bugs described in the todo
are still present and reproducible by reading the code (none were incidentally fixed
by intervening quick-tasks).

The deepest research finding is the **D-04 covariance algebra**, which is now fully
worked out and numerically validated against CONTEXT.md's own example (100%-shared
100-vs-100 cohort: buggy SE 0.0707 → corrected SE 0.1000, exactly reproducing the
cited "true SE 0.10"). The second-deepest finding is that the **D-03 precision gate
is structurally decoupled** from the item-1 fix: the tagger harness (which lives
outside the default `pytest -n auto` run — `--ignore=tests/scripts/tagger` in
`pyproject.toml`) calls `detect_tactic_motif(board, row["pv"])` with `has_forced_mate`
always defaulting to `False`, so the new fallback branch is provably unreachable in
that gate today. Re-running the gate after the fix is still the required verify step
(to catch any unrelated regression), but it cannot by itself validate the new
behavior — a dedicated unit test with an explicit `has_forced_mate=True` + a
hand-truncated mate PV is the only way to exercise the fix, matching what the
source todo already asks for.

**Primary recommendation:** implement the five items as five independent plans (or
four, folding 2+5 as D-06 suggests), each touching one subsystem, each with its own
unit test(s) reusing the exact existing test-fixture patterns identified below (no
new test infrastructure needed). Two items (1 and 3) will require updating existing
tests whose assertions currently encode the *buggy* behavior as correct — this is
expected and must be called out explicitly in each plan, not treated as scope creep.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tactic motif detection (item 1) | API / Backend (`app/services/tactic_detector.py`, pure function) | — | Called synchronously inside the classify pipeline (drain + submit paths); no I/O, no DB |
| `fen_map` replay/storage (item 1) | API / Backend (`app/services/flaws_service.py`) | — | In-memory PGN replay per classify call; not persisted |
| Entry-ply eval drain (item 2) | API / Backend, background coroutine (`app/services/eval_drain.py`) | Database (writes `games.evals_completed_at`) | Server-pool lifespan task, not request-scoped |
| Quintile significance test (item 3) | API / Backend (`app/services/endgame_service.py`, `app/services/score_confidence.py`) | Database (reads aggregated clock rows) | Pure post-query aggregation, no new queries needed |
| Import normalization (item 4) | API / Backend (`app/services/chesscom_client.py`, `app/services/lichess_client.py`) | External API (chess.com / lichess) | Per-game normalization inside the import async-generator pipeline |
| Entry-submit lease guard (item 5) | API / Backend (`app/routers/eval_remote.py`) | Database (`games.entry_eval_lease_expiry`) | Router-level trust-boundary guard against a remote worker's submission |

## Standard Stack

No new libraries, no version changes. This phase is a pure bugfix phase inside the
existing stack (FastAPI/SQLAlchemy async/python-chess/pytest). Skipping the
Standard Stack / Package Legitimacy Audit sections — no packages are added.

## Architecture Patterns

### Item 1 — Tactic mate fallback + `fen_map` full-FEN storage

**Bug A — `has_forced_mate` no-op (VERIFIED, reproduced by reading the code).**

`app/services/tactic_detector.py:2462`:
```python
_can_run_mate = boards[-1].is_checkmate() or has_forced_mate
```
This guard is already correct — it lets execution into the Tier-1 mate block when
`has_forced_mate=True` even if the capped PV doesn't reach checkmate. **The actual
bug is one level down**: every individual mate detector re-checks
`boards[-1].is_checkmate()` internally and bails when the PV is truncated:

```
detect_back_rank_mate            tactic_detector.py:1061  if not boards[-1].is_checkmate(): return False, None, None
detect_generic_mate              tactic_detector.py:1128  if not boards[-1].is_checkmate(): return False, None, None
detect_smothered_mate            tactic_detector.py:1157  if not boards[-1].is_checkmate() or not moves: ...
detect_anastasia_mate            tactic_detector.py:1201  same guard
detect_hook_mate                 tactic_detector.py:1272  same guard
detect_arabian_mate              tactic_detector.py:1330  same guard
detect_boden_or_double_bishop_mate tactic_detector.py:1386 same guard
detect_dovetail_mate             tactic_detector.py:1437  same guard
```

So today, when `has_forced_mate=True` but `boards[-1].is_checkmate()` is `False`
(truncated PV), **every** one of these detectors returns `(False, None, None)` and
the Tier-1 block falls through with nothing tagged — exactly the "no-op" the review
describes. D-01 correctly keeps every one of those detectors unchanged (their
`is_checkmate()` requirement is *desired*: named-mate geometry can't be verified on
a truncated line) and instead requires a **new fallback branch** after the existing
Tier-1 cascade fails, mirroring `detect_generic_mate`'s own piece/depth derivation but
without the checkmate requirement:

```python
# --- Tier 1: mate subtypes ... (existing code, unchanged, ends at line ~2490) ---
        gm_fired, gm_piece, gm_depth = detect_generic_mate(boards, moves, pov)
        if gm_fired:
            return TacticMotifInt.MATE, gm_piece, TACTIC_CONFIDENCE_HIGH, gm_depth

        # D-01 (Phase 148): has_forced_mate is True (Stockfish reports a genuine
        # eval_mate score) but the PV is capped at PV_CAP_PLIES=12 before reaching
        # the mating position. Named-mate geometry cannot be verified on a
        # truncated line, so tag the generic fallback only — do NOT suppress a
        # real mate (the current bug).
        if has_forced_mate and not boards[-1].is_checkmate():
            _fallback_depth = len(moves) - 1 if moves else None
            _fallback_piece: int | None = None
            if moves:
                _last = boards[-1].piece_at(moves[-1].to_square)
                if _last is not None and _last.color == pov:
                    _fallback_piece = _last.piece_type
            return TacticMotifInt.MATE, _fallback_piece, TACTIC_CONFIDENCE_HIGH, _fallback_depth
```

Insertion point: immediately after the existing `detect_generic_mate` check inside
the `if _can_run_mate:` block (current lines ~2487-2490), before the block closes
and the Tier-2+ dispatch begins. `moves` is guaranteed non-empty at this point (the
function early-returns at line ~2454-2455 when `not moves`), so `moves[-1]` is safe.

**Bug B — `fen_map` loses castling/en-passant state (VERIFIED).**

The actual **storage** site is `_recompute_fen_map` in `app/services/flaws_service.py`
(lines 312-335), not the consumption site CONTEXT.md's anchor points at:

```python
def _recompute_fen_map(pgn: str) -> dict[int, str]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return {}
    board = game.board()
    fens: dict[int, str] = {0: board.board_fen()}   # <-- change to board.fen()
    try:
        for ply, node in enumerate(game.mainline(), start=1):
            board.push(node.move)
            fens[ply] = board.board_fen()           # <-- change to board.fen()
    except (ValueError, AssertionError) as exc:
        ...
    return fens
```

D-02 fix: change both `board.board_fen()` calls to `board.fen()`. This is the ONLY
sanctioned exception to the CLAUDE.md `board_fen()`-only rule — the map is
detector-internal (never touches Zobrist comparisons).

The **consumption** site (`_detect_tactic_for_flaw`, `flaws_service.py:443-451`,
anchor accurate) currently does a manual side-to-move override that becomes
redundant (not harmful) once the fen is a full FEN:

```python
fen_before_flaw = fen_map.get(n, "")
if not fen_before_flaw:
    return None, None, None, None
# fen_map stores board.board_fen() (piece-placement only, no side-to-move).
# chess.Board() defaults to white to move, so we must set the side explicitly
# from ply parity: even = white mover, odd = black mover.
board_before = chess.Board(fen_before_flaw)
board_before.turn = chess.WHITE if n % 2 == 0 else chess.BLACK
```
Once `fen_map` stores full `board.fen()`, `chess.Board(fen_before_flaw)` already
carries the correct `turn` (verified: `n=0` → WHITE, `n=1` → BLACK, matching the
parity rule exactly), plus correct castling rights and en-passant square. The
`board_before.turn = ...` override line becomes dead-but-harmless (re-asserts the
same value chess.Board already parsed). **Recommendation:** leave the override line
in place unless the planner wants a small cleanup — removing it is optional, not
required for correctness, and touching it enlarges the diff for zero behavior
change. Flag as a "could simplify but out of fix-scope" note rather than mandating
removal (avoids unscoped refactor per CLAUDE.md's `/gsd-quick` guidance analog).

### D-03 — Precision-gate re-run mechanics (worked out concretely)

The gate lives at `tests/scripts/tagger/test_detector_precision.py`
(`test_detector_precision_and_recall`), **not** under `app/services/` — this whole
directory is **excluded from the default test run**:

```toml
# pyproject.toml
addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"
```
Run it explicitly:
```bash
uv run pytest tests/scripts/tagger/test_detector_precision.py -v
# or, for the human-readable per-motif markdown report:
uv run python scripts/tactic_tagger_report.py
```

**Critical finding:** the harness (`tests/scripts/tagger/test_detector_precision.py:93`)
calls the detector as:
```python
motif_int, _piece, _confidence, depth = detect_tactic_motif(board, row["pv"])
```
— `has_forced_mate` is **never passed**, so it always defaults to `False`. Since the
new Bug-A fallback branch is gated on `if has_forced_mate and not
boards[-1].is_checkmate()`, **it is structurally unreachable in this harness** as
written. This means:

1. Running the gate after the fix is a **regression check, not a fix-validation
   check** — it will pass trivially (bit-identical results) because the new code
   path is never exercised. It is still worth running (confirms nothing else in
   `detect_tactic_motif` was disturbed), but it does **not** satisfy "confirm the
   fix works," and cannot regress the `mate` floor (0.95 in
   `tests/scripts/tagger/precision_floors.py:273`) from this specific change.
2. Real validation of Bug A requires the **dedicated unit test** the source todo
   already asks for: a hand-built position with a genuine mate-in-N (N large enough
   that a 12-ply-capped PV doesn't reach checkmate), called with
   `has_forced_mate=True` explicitly. Place this in `tests/services/test_tactic_detector.py`
   (which has a `TestPriorityOrder`-style class already; zero `has_forced_mate`
   coverage exists there today per D-03's own note) — a plain `chess.Board(fen)` is
   sufficient here since mate-subtype/generic detection reads only
   `boards`/`moves` from the PV parse, not `boards[0].move_stack` (the move-stack
   dependency the `build_detector_board` fixture exists for is specific to
   hanging-piece/intermezzo/recapture-exclusion detectors, not the mate branch).
3. **Optional (not required, flag as discretionary):** the fixture CSVs carry a
   `Themes` column with `mateIn1`..`mateIn5`/`mate` tags
   (`tests/scripts/tagger/motif_theme_map.py:58`) — a future enhancement could
   derive `has_forced_mate` from ground truth themes in the harness itself for
   fuller real-data coverage. This is **not** part of this fix's scope (it would
   change the offline gate's semantics beyond the todo's ask) — mention only as an
   Open Question for the planner to explicitly decline.

**Verify command for item 1 (both bugs):**
```bash
uv run pytest tests/services/test_tactic_detector.py tests/services/test_flaws_service.py -v
uv run pytest tests/scripts/tagger/test_detector_precision.py -v   # explicit path override
```

### Existing test blast radius for item 1 (must update, not just add)

`tests/services/test_flaws_service.py::TestFenRecompute` (lines 535-614) currently
asserts the **buggy** piece-placement-only format as the *correct* contract:

| Test | Current assertion | Must become |
|------|-------------------|-------------|
| `test_initial_position_at_ply_zero` | `fen_map[0] == "rnbqkbnr/.../RNBQKBNR"` (no suffix) | Full initial FEN: `"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"` |
| `test_after_e4_board_fen` | `assert " " not in fen` | Invert: assert full FEN fields present (`" " in fen`, split into 6 space-separated fields) |
| `test_board_fen_not_full_fen` | Docstring + body assert exactly 8 `/`-fields and no space — the whole point of this test contradicts the fix | Rewrite (rename to e.g. `test_full_fen_not_board_fen`) to assert the OPPOSITE: 6 space-separated fields, includes `w`/`b`, castling rights, en-passant target |
| `test_replay_failure_captured_to_sentry` | Monkeypatches `chess.Board.board_fen` to simulate a mid-replay crash | Monkeypatch `chess.Board.fen` instead — `board_fen()` is no longer called by the replay loop, so the old patch target would never fire |

The class docstring (`"""Tests for _recompute_fen_map — PGN replay using
board.board_fen()."""`) also needs updating. This is expected fallout of the fix,
not scope creep — flag explicitly in the plan so the executor doesn't treat 4 failing
pre-existing tests as a regression to revert.

**New tests needed (both bugs):**
- Bug A: hand-built mate-in-N position (N chosen so the capped-at-12-ply PV doesn't
  reach checkmate) + `has_forced_mate=True` → asserts `TacticMotifInt.MATE` returned,
  not `None`. Add a companion test with `has_forced_mate=False` on the same
  truncated PV to assert the fallback does NOT fire without the flag (regression
  guard for the flag's gating).
- Bug B: a short PGN reaching an en-passant capture or a castling move, replayed
  through `_recompute_fen_map`, then through `_detect_tactic_for_flaw`'s consumption
  path, asserting (a) the SAN parses (no more `parse_san` failure) and (b) the
  resulting board after pushing an ep-capture PV move correctly removes the
  captured pawn (board occupant count check). No existing EP/castling PGN fixture
  exists in `test_flaws_service.py` today (`_SHORT_PGN`/`_PGN_THREE_MOVES` are both
  plain `1.e4 e5 ...`-style) — construct a new small PGN fixture for this.

### Item 2 — Entry-ply drain all-fail circuit breaker (WR-05 mirror)

**Structural difference from the full-ply lane (important for planning):** the
full-ply drain already extracted its per-tick body into a standalone, directly
testable `_full_drain_tick() -> bool` function (`eval_drain.py:2488-2809`,
docstring: "Extracted from run_full_eval_drain (WR-07) so tests can drive exactly
one tick deterministically"). **The entry-ply drain has no equivalent extraction** —
`run_eval_drain()` (`eval_drain.py:2311-2415`) is a single monolithic `while True:`
loop; existing tests drive it via `asyncio.create_task(drain_module.run_eval_drain())`
+ `asyncio.wait_for(..., timeout=...)` + `task.cancel()` (see
`tests/services/test_eval_drain.py::TestIdempotentOnSimulatedCrash` and
`TestEngineNoneMarksComplete`, lines 271-448). The fix must therefore be added
**inline** inside `run_eval_drain()`'s existing loop body — extracting a
`_entry_drain_tick()` helper (to mirror `_full_drain_tick`'s test ergonomics) is a
reasonable structural improvement but is **beyond fix-scope** unless the planner
explicitly wants the refactor; the minimal fix does not require it.

**Exact insertion point.** In `run_eval_drain()`, between Step 4 (gather) and Step 5
(open the write session):

```python
            # Step 4: fan out engine evaluations.
            if eval_targets:
                eval_results: Sequence[tuple[int | None, int | None]] = await asyncio.gather(
                    *(engine_service.evaluate(t.board) for t in eval_targets)
                )
            else:
                eval_results = []

            # --- NEW: WR-05 mirror for the entry-ply lane ---
            # Gate on eval_targets being non-empty (mirrors the full-ply WR-05 gate
            # at eval_drain.py:2637 exactly) — an empty eval_targets list is the
            # legitimate D-09 "no positions to evaluate" case (see
            # test_engine_none_marks_complete, which inserts games with ZERO
            # GamePosition rows and asserts they ARE stamped complete). Gating on
            # eval_targets prevents this fix from breaking that existing invariant.
            if eval_targets and all(cp is None and mt is None for cp, mt in eval_results):
                sentry_sdk.set_context(
                    "eval", {"game_id_count": len(game_ids), "failed_ply_count": len(eval_targets)}
                )
                sentry_sdk.set_tag("source", "eval_drain")
                sentry_sdk.capture_message(
                    "entry-drain: all engine evals failed for batch — leaving pending",
                    level="warning",
                )
                await asyncio.sleep(_DRAIN_IDLE_SLEEP_SECONDS)
                continue  # skip Step 5 entirely: no _apply_eval_results, no
                          # _classify_and_insert_flaws, no _mark_evals_completed.
                          # entry_eval_lease_expiry (20s TTL, set at claim time in
                          # _claim_entry_eval_games) expires naturally — the SAME
                          # "release" mechanism the crash-idempotency test already
                          # relies on (test_idempotent_on_simulated_crash, TTL reclaim).

            # Step 5: open session LATE ...
```

Notes:
- **"Release the lease" = do nothing extra, let the 20s TTL expire.** No explicit
  `UPDATE games SET entry_eval_lease_expiry = NULL ...` is needed or used anywhere
  else in this file for this purpose — `_mark_evals_completed` is the only thing
  that permanently ends a lease; skipping it and doing nothing else is sufficient,
  matching how `test_idempotent_on_simulated_crash` already proves TTL-based
  reclaim works. (Contrast with `eval_remote.py`'s error-path explicit
  `entry_eval_lease_expiry=None` release — that path exists because an HTTP request
  needs to release quickly rather than wait out a TTL from a remote worker's
  perspective; the in-process server-pool drain has no such urgency.)
- **The `await asyncio.sleep(...)` is required**, unlike the full-ply lane (which
  gets its sleep "for free" from `run_full_eval_drain`'s outer `if not processed:
  await asyncio.sleep(...)`). `run_eval_drain`'s loop currently only sleeps when
  `game_ids` is empty; without an explicit sleep here, a fully-dead pool would burn
  through the ENTIRE not-yet-leased backlog at un-throttled speed (each `evaluate()`
  call on a dead pool answers near-instantly per `EnginePool._analyse`'s re-queue
  behavior — see engine.py finding below), leasing (but not completing) many
  batches in quick succession.
- `ENTRY_LEASE_TTL_SECONDS = 20` (eval_drain.py:169), `_DRAIN_IDLE_SLEEP_SECONDS = 5`
  (eval_drain.py:95) — both already-defined constants, no new ones needed.

**`engine.py` `EnginePool` docstring fix (VERIFIED wrong, matches the review).**
Actual lines 379-381 (claimed ~380-382, off by ~1-2 lines — negligible):
```python
    On per-worker timeout / crash, that worker restarts in place; siblings
    keep going. If restart fails the worker is permanently disabled and its
    slot is dropped from the queue — remaining workers continue to serve.
```
This is factually wrong: `_analyse`'s `finally` block (`engine.py:494-495`)
**always** does `self._available.put_nowait(idx)` regardless of whether
`_restart_worker` succeeded — a permanently-failed worker's slot is **never**
dropped; it stays in the queue forever, and every future pickup of that slot hits
`if protocol is None: return None, None` (near-instant) then re-queues itself again.
Corrected docstring text:
```
    On per-worker timeout / crash, that worker restarts in place; siblings
    keep going. If restart fails, the worker's slot is NOT dropped — it
    stays in the available queue and every future pickup returns (None, None)
    almost instantly (see the `protocol is None` early-return in `_analyse`).
    A pool where every worker has permanently failed therefore answers
    every `evaluate()` call near-instantly with (None, None) rather than
    hanging — this is what the entry/full-ply drain "all engine evals
    failed" circuit breakers (WR-05) detect and react to.
```

**Test pattern (item 2).** Mirror
`tests/services/test_full_eval_drain.py::test_all_fail_keeps_game_pending` (lines
778-829) but adapted to `run_eval_drain`'s task-based test style (per
`TestEngineNoneMarksComplete`, lines 384-447): insert a game with real
`GamePosition` rows (so `eval_targets` is non-empty), monkeypatch
`drain_module.engine_service.evaluate` to `AsyncMock(return_value=(None, None))`,
run `run_eval_drain()` as a background task with a short `wait_for` timeout, cancel,
then assert `evals_completed_at IS NULL` (opposite of `test_engine_none_marks_complete`,
which asserts `IS NOT NULL` for its zero-eval-target case — do not confuse the two;
both must coexist and both must keep passing).

**Verify command:**
```bash
uv run pytest tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py -v
```

### Item 3 — D-04 covariance algebra (worked out concretely)

**Current code (VERIFIED, anchors accurate).** `endgame_service.py:2139-2143`
(docstring, off-by-one from claimed 2140-2143 — negligible) asserts independence:
```
User and opponent quintile assignments are INDEPENDENT within the same row:
a game where the user banked clock but the opponent burned it will fall in
different quintiles for the two splits. That independence is what makes the
unpaired two-sample test (compute_score_difference_test) valid in
_build_quintile_bullets.
```
This is false whenever `user_quintile == opp_quintile` for the same game (both
players in the same time-pressure quintile) — that game is counted once (as `X`) in
the user-side cohort and once (as `1-X`, the exact linear inverse) in the
opponent-side cohort for the SAME quintile bucket `q`.

`compute_score_difference_test` (`score_confidence.py:173-253`, exact anchor match
at the `endgame_service.py:2326-2328` call site) currently computes:
```python
var_eg = max(0.0, (eg_w + 0.25 * eg_d) / eg_n - score_eg ** 2)
var_ne = max(0.0, (ne_w + 0.25 * ne_d) / ne_n - score_ne ** 2)
se_diff = math.sqrt(var_eg / eg_n + var_ne / ne_n)     # <-- treats cohorts as independent
```

**Derivation of the correction.** Let quintile bucket `q` (fixed `tc`) have:
- `n_u` = user-side cohort size, `n_o` = opp-side cohort size (as today).
- `m` = **shared-game count** = number of games where `user_quintile == q AND
  opp_quintile == q` **simultaneously** (i.e., BOTH players were in the same
  time-pressure quintile — the game contributes to both `n_u` and `n_o` for the
  SAME bucket `q`). `m ≤ min(n_u, n_o)` always, by construction.

For a shared game `i`, its contribution to `score_eg` is `X_i` (user outcome,
weight `1/n_u`) and its contribution to `score_ne` is `Y_i = 1 - X_i` (opponent
outcome, exact linear inverse — verified from the accumulator code: a user win
increments the opponent bucket's **loss** slot, a user loss increments the
opponent's **win** slot, draws map to draws — this is a deterministic `Y=1-X`
relationship, not merely a statistical correlation). For non-shared games,
`Cov(X_i, Y_j) = 0` for `i != j` (different games, independent draws).

```
Cov(score_eg, score_ne) = (1 / (n_u · n_o)) · Σ_{i shared} Cov(X_i, 1 - X_i)
                        = -(1 / (n_u · n_o)) · Σ_{i shared} Var(X_i)
                        ≈ -m · v / (n_u · n_o)      [v = per-game outcome variance, shared subset]
```

The general variance-of-a-difference identity `Var(A - B) = Var(A) + Var(B) -
2·Cov(A,B)` then gives:

```
Var(score_eg - score_ne)_corrected
    = var_eg/n_u + var_ne/n_o  -  2 · Cov(score_eg, score_ne)
    = var_eg/n_u + var_ne/n_o  -  2 · ( -m·v / (n_u·n_o) )
    = var_eg/n_u + var_ne/n_o  +  2·m·v / (n_u·n_o)
```

This is exactly D-04's prescribed form (`+2m·cov/(n_u·n_o)`), with `cov` in D-04's
shorthand meaning the per-game variance `v` of the shared subset (not the
covariance itself, which is negative — the `+` sign in D-04's formula already
absorbs the double-negative from `-2·Cov`).

**Numerical validation against CONTEXT.md's own worked example.** CONTEXT.md states:
"100 fully-shared games with true SE 0.10 get reported SE 0.0707." Setting
`n_u = n_o = m = 100` (fully shared) and `var_eg = var_ne = v = 0.25` (max trinomial
variance, at `score ≈ 0.5`):
- **Buggy (current) SE:** `sqrt(0.25/100 + 0.25/100) = sqrt(0.005) = 0.0707` ✓ exact match.
- **Corrected SE:** `sqrt(0.25/100 + 0.25/100 + 2·100·0.25/(100·100)) = sqrt(0.005 +
  0.005) = sqrt(0.01) = 0.10` ✓ exact match to the cited "true SE 0.10."

This is strong confirmation the derivation above is correct and matches the
decision's intent exactly.

**Choice of `v` (the per-game variance proxy — D-04 says track only the *count*
`m`, not a separate WDL breakdown for the shared subset).** Since D-04 explicitly
locks "track the shared-game count `m`" (not a full W/D/L accumulator for the
intersection), the least-invasive choice is to approximate `v` using the two
already-computed cohort variances:
```python
v_shared = (var_eg + var_ne) / 2.0
cov_correction = 2.0 * m * v_shared / (eg_n * ne_n)
se_diff = math.sqrt(max(0.0, var_eg / eg_n + var_ne / ne_n + cov_correction))
```
This is an approximation (the *exact* shared-subset variance would require a third
`(w, d, l)` accumulator restricted to `user_quintile == opp_quintile == q` rows —
a few more lines, fully consistent with the derivation, and strictly more
statistically correct) — flag both options for the planner; recommend the
count-only averaged-variance approach as the default per D-04's explicit "least
invasive" instruction, and note the exact-WDL alternative as a documented
possible upgrade if the planner/reviewer wants tighter fidelity.

**Where `m` is computed.** `_iterate_clock_rows` (`endgame_service.py:2106-2245`)
already computes `user_quintile` and `opp_quintile` independently per row
(lines 2203-2204). Add one line inside the existing loop:
```python
tc_shared_quintile_count: dict[tuple[str, int], int] = defaultdict(int)
...
if user_quintile == opp_quintile:
    tc_shared_quintile_count[(tc, user_quintile)] += 1
```
and add it as a 6th element of the function's return tuple.

**Threading through the call chain (blast radius — small, 2 files):**
1. `_iterate_clock_rows` return signature: 5-tuple → 6-tuple. Update its type
   annotation and docstring.
2. **Production call site** (`endgame_service.py:2383-2389`, exactly 1 site) —
   destructure the new 6th value and pass it to `_build_quintile_bullets`.
3. **`_build_quintile_bullets`** (`endgame_service.py:2263-2342`) — add a
   `shared_wdl_count: dict[tuple[str, int], int]` parameter; look up
   `m = shared_wdl_count.get((tc, q), 0)` alongside the existing `u_w/u_d/u_l` /
   `o_w/o_d/o_l` lookups; pass `m` to `compute_score_difference_test`.
4. **`compute_score_difference_test`** (`score_confidence.py:173`) — add a new
   trailing parameter `shared_n: int = 0` (default 0 preserves every existing
   caller/test unchanged — this is the ONLY other call site, per
   `grep -rn "compute_score_difference_test("`, confirmed single production
   consumer). Implement the `cov_correction` term as derived above.
5. **4 existing test call sites** in
   `tests/services/test_time_pressure_service.py` (lines 113, 131, 152, 161, all in
   `TestUserAndOppQuintileIndependentSplit`) destructure `_iterate_clock_rows`'s
   return as a 5-tuple — **these will raise `ValueError: too many values to
   unpack`** once the 6th element is added and MUST be updated to a 6-tuple
   destructure (even if the new value is ignored via `_tc_shared` in those specific
   tests). This is expected fallout, not a regression.

**Fix the wrong docstring** at `endgame_service.py:2139-2143` (`_iterate_clock_rows`)
to state the actual (non-)independence and reference the new correction — do not
just delete the claim, since it explains WHY the correction exists.

**New tests needed:**
- `test_score_confidence.py`: a `shared_n > 0` case reproducing the CONTEXT.md
  worked example numerically (100/100/100, `var=0.25` both sides) asserting the
  corrected SE ≈ 0.10 (and, by extension, that the two-sided p-value for a 0.14
  delta is ≈ 0.16, not ≈ 0.048 — matches z ≈ 1.4 not z ≈ 1.98). Also a `shared_n=0`
  regression test confirming byte-identical output to the pre-fix behavior (default
  param preserves this automatically, but assert it explicitly).
- `test_time_pressure_service.py`: extend the existing
  `TestUserAndOppQuintileIndependentSplit` fixture-row builder (`_make_row`) to
  build a case where `user_quintile == opp_quintile` for multiple games in the
  same bucket, assert `tc_shared_quintile_count[(tc, q)]` counts them, and assert
  the resulting `PressureQuintileBullet.ci_low/ci_high` widen relative to a
  non-shared control case with the same W/D/L totals (per the todo's stated
  verification: "a shared-cohort significance test asserting SE widens").

**Verify command:**
```bash
uv run pytest tests/services/test_score_confidence.py tests/services/test_time_pressure_service.py tests/test_endgame_service.py -v
```

### Item 4 — Malformed platform game aborts the whole import

**Exact call sites (both anchors accurate, negligible drift).**
`app/services/chesscom_client.py:326`:
```python
for game in games:
    normalized = normalize_chesscom_game(game, username, user_id)
    if normalized is not None:
        yield normalized
        ...
```
`app/services/lichess_client.py:184` (inside the NDJSON `async for line in
response.aiter_lines()` loop, after the existing `json.JSONDecodeError` guard at
lines 178-182):
```python
normalized = normalize_lichess_game(game, username, user_id)
if normalized is not None:
    yield normalized
    ...
```

**Confirmed failure mode.** `normalize_chesscom_game` (`app/services/normalization.py:224`)
does `white = game["white"]` — a direct subscript, no `.get()` — so a malformed
chess.com game object missing the `"white"` key raises `KeyError: 'white'`
uncaught, propagating out of the async generator and aborting the whole import job
(matches the review's claim exactly).

**Existing pattern to mirror (PGN-parse, already CLAUDE.md-compliant).**
`app/services/import_service.py:922-932`:
```python
for game_id, platform_game_id in id_platform_pairs:
    pgn = pgn_by_platform_id.get(platform_game_id, "")
    if not pgn:
        continue
    try:
        processing_result = process_game_pgn(pgn)
    except Exception:
        logger.warning("Failed to process PGN for game_id=%s", game_id)
        sentry_sdk.set_context("import", {"game_id": game_id})
        sentry_sdk.capture_exception()
        continue
```
Note this existing precedent calls `capture_exception()` **once per failed game**
(not a single end-of-batch aggregated event) — the todo's phrase "one aggregated
Sentry capture" is most naturally read as "one event per malformed game" (as
opposed to one event per retry attempt, which doesn't apply here since
normalization isn't retried), matching this exact precedent. **Recommend mirroring
this pattern verbatim** for consistency rather than inventing a new
end-of-import-summary-event shape; flag this reading as an assumption for the
planner to confirm (see Assumptions Log).

**Recommended fix (both files, same shape):**
```python
# chesscom_client.py
for game in games:
    try:
        normalized = normalize_chesscom_game(game, username, user_id)
    except Exception as exc:
        logger.warning("Failed to normalize chess.com game for user_id=%s", user_id)
        sentry_sdk.set_context("import", {"platform": "chess.com", "user_id": user_id})
        sentry_sdk.capture_exception(exc)
        continue
    if normalized is not None:
        yield normalized
        if on_game_fetched is not None:
            on_game_fetched()
```
```python
# lichess_client.py — same shape, wrapping only the normalize_lichess_game(...) call
# (leave the existing json.JSONDecodeError guard on the raw line untouched)
```
No variable interpolation in the log/Sentry *message* text (CLAUDE.md rule);
`user_id` goes in `set_context`, matching the existing precedent's shape exactly
(which uses `game_id` in context, not in the message).

**Test pattern (item 4).** Mirror
`tests/test_lichess_client.py::TestFetchLichessGames::test_malformed_json_lines_skipped`
(lines 163-179) — same "inject a bad item between two good ones, assert only the
good ones survive" shape, but for a normalization-level failure instead of a
JSON-decode failure:
```python
async def test_normalization_failure_skipped_and_continues(self) -> None:
    good1 = _make_lichess_game(game_id="g1")
    malformed = {"id": "bad", "variant": {"key": "standard"}}  # missing "players" -> KeyError
    good2 = _make_lichess_game(game_id="g2")
    lines = [json.dumps(good1), json.dumps(malformed), json.dumps(good2)]
    ...
    assert [g.platform_game_id for g in results] == ["g1", "g2"]
```
For chess.com, use `tests/test_chesscom_client.py`'s existing `_make_game()` helper
(lines 23-52) and delete the `"white"` key from one dict in a 3-game archive
response to reproduce the exact `KeyError` the review found; mirror
`test_valid_username_yields_normalized_games` (line 102) for the request-mocking
scaffolding (`_make_response`).

**Verify command:**
```bash
uv run pytest tests/test_chesscom_client.py tests/test_lichess_client.py -v
```

### Item 5 — Entry-submit lease-expiry guard (D-05 minimum guard)

**Exact site (drifted — actual function at lines 853-990, not the claimed
~746-813).** `app/routers/eval_remote.py`, `entry_submit_eval` (line 853), guard
query at lines 891-903:
```python
async with async_session_maker() as guard_session:
    leased_game_ids: list[int] = list(
        (
            await guard_session.execute(
                select(Game.id).where(
                    Game.entry_eval_leased_by == worker_id,
                    Game.evals_completed_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
```
This has no `entry_eval_lease_expiry` check — a game leased by `worker_id` whose
20-second TTL has since expired (e.g. re-leased under the same fixed `--worker-id`
by a different worker instance, or a restarted worker resubmitting late) is still
matched here and gets stamped complete with whatever the late/wrong submission
contains.

**Minimum fix (D-05):**
```python
import sqlalchemy as sa   # already imported at the top of this file
...
        result = await guard_session.execute(
            select(Game.id).where(
                Game.entry_eval_leased_by == worker_id,
                Game.evals_completed_at.is_(None),
                Game.entry_eval_lease_expiry > sa.func.now(),   # D-05 (Phase 148)
            )
        )
```
`func.now()` is the established pattern for server-side timestamp comparisons
elsewhere in this codebase (`app/users.py`, `app/routers/auth.py`,
`user_rating_anchors_repository.py`, etc. — all use `func.now()` on `.values()` and
comparisons; `sa` is already imported in this file as `import sqlalchemy as sa`, so
`sa.func.now()` needs no new import). No NULL-handling edge case: a never-leased
game never matches `entry_eval_leased_by == worker_id` in the first place (NULL !=
any string), and the release path (lines 974-980, error handler) already nulls
`entry_eval_lease_expiry` on explicit release, which also naturally excludes it here.

**On guard failure:** implicit skip, not an explicit error response — the excluded
`game_id` simply doesn't appear in `leased_game_ids`, so it's not classified, not
stamped, and stays `evals_completed_at IS NULL`, reclaimable by a fresh lease later
(D-05's own framing: "reject/skip", confirmed as the correct behavior — no new
HTTP status code or response field needed; `EntrySubmitResponse.game_ids` will
simply report a smaller/different set than before in this edge case, which is
correct).

**Test pattern (item 5).** Mirror the exact fixture-construction style of
`tests/test_eval_worker_endpoints.py::test_lease_reclaim` (lines 1179-1234, raw
`sa.text("UPDATE games SET entry_eval_lease_expiry = :ts, entry_eval_leased_by =
'...' WHERE id = :gid")`) to manufacture one game with a **past** expiry and one
with a **future** expiry, both leased to the SAME `worker_id`, then POST to
`/entry-submit` for that worker and assert only the future-expiry game appears in
`resp.json()["game_ids"]` / gets `evals_completed_at` stamped — the
past-expiry one must remain `NULL`. Reuse `_insert_game`, `_get_game_entry_eval_leased_by`,
`_get_game_evals_completed_at` helpers already present in
`tests/test_eval_worker_endpoints.py` (lines 104, 234).

**Verify command:**
```bash
uv run pytest tests/test_eval_worker_endpoints.py -v -k entry_submit
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Two-sample proportion significance test with a covariance correction | A new paired/bootstrap significance routine | Extend the existing `compute_score_difference_test` in-place with an additive `+2m·v/(n_u·n_o)` term (D-04) | Point estimates, gating, and CI-widening logic are already correct; only the SE formula is missing a term — a full rewrite would touch far more surface than the bug requires |
| Server-side "now" comparison for a lease-expiry guard | Comparing a Python `datetime.now(timezone.utc)` against a DB column fetched separately | `sa.func.now()` in the `.where()` clause (already the established pattern in `app/users.py`, `app/routers/auth.py`, etc.) | Avoids clock-skew between app server and DB server; matches every other lease-expiry comparison in this codebase |

**Key insight:** none of these five fixes need new abstractions — each is a
targeted change to an existing, already-tested function. The risk is entirely in
under-scoping the blast radius (existing tests whose assertions encode the bug),
not in under-building new machinery.

## Common Pitfalls

### Pitfall 1: Treating "re-run the precision gate" as sufficient validation for item 1's Bug A
**What goes wrong:** The plan ships the `has_forced_mate` fallback, runs
`tests/scripts/tagger/test_detector_precision.py`, sees it pass unchanged, and
concludes the fix is validated.
**Why it happens:** The harness's only call to `detect_tactic_motif` never passes
`has_forced_mate=True` (see D-03 section above) — a passing gate run is
mathematically guaranteed regardless of whether the fix is correct.
**How to avoid:** Require the dedicated unit test (hand-built truncated mate-in-N +
explicit `has_forced_mate=True`) as the actual verification for Bug A; treat the
gate re-run as a pure regression check on the rest of the detector.
**Warning signs:** A plan or verify-work session that lists "tactic-tagger-report
green" as the sole evidence item 1 is fixed.

### Pitfall 2: Breaking `test_engine_none_marks_complete` while fixing item 2
**What goes wrong:** Gating the new WR-05-mirror circuit breaker on anything other
than "`eval_targets` non-empty" (e.g. gating on `game_ids` non-empty, or omitting
the `eval_targets and` guard entirely) will also trip on the legitimate D-09
"zero eval targets, mark complete anyway" case that
`tests/services/test_eval_drain.py::TestEngineNoneMarksComplete` already covers and
asserts.
**Why it happens:** Both scenarios superficially look like "engine returned nothing
useful" — but one (`eval_targets` empty — nothing to evaluate) is a legitimate
no-op-complete, and the other (`eval_targets` non-empty but every call failed) is
the genuine dead-pool bug.
**How to avoid:** Mirror the full-ply lane's exact gate shape:
`if engine_targets and all(...)` — the `and` on a non-empty check is load-bearing,
not incidental.
**Warning signs:** `test_engine_none_marks_complete` starts failing after the item-2
change.

### Pitfall 3: Forgetting the 4-site blast radius when threading `shared_n`/`m` through item 3
**What goes wrong:** Adding the new 6th return value to `_iterate_clock_rows`
without updating its 4 existing test-side destructures
(`tests/services/test_time_pressure_service.py` lines 113, 131, 152, 161) causes an
immediate `ValueError: too many values to unpack (expected 5)` in every one of
those tests.
**Why it happens:** Python tuple-unpacking is positional and arity-strict; there is
no default/optional trailing element.
**How to avoid:** Grep for `_iterate_clock_rows(` before landing the change (this
research already did — exactly 1 production site + 4 test sites, no others) and
update all 5 in the same commit.
**Warning signs:** `pytest tests/services/test_time_pressure_service.py` failing
with unpack errors, not assertion errors.

### Pitfall 4: `TestFenRecompute`'s existing tests silently "passing" for the wrong reason after a partial fix
**What goes wrong:** If only the consumption site (`flaws_service.py:443-451`) is
touched and the actual storage site (`_recompute_fen_map`, lines 312-335) is left
calling `board.board_fen()`, the ep/castling bug is NOT fixed (fen_map still lacks
side-to-move/castling/ep state) even though the CONTEXT.md anchor for this bug
points at the consumption site, which could mislead a plan into editing the wrong
location.
**Why it happens:** The CONTEXT.md canonical-reference anchor for this bug
(`flaws_service.py:443-451`) is accurate as a *file:line pointer* but describes the
*consumer* of the bug, not its *source* — the actual one-line-times-two fix is at
`_recompute_fen_map` (lines 312, 327), a different location in the same file.
**How to avoid:** Fix `_recompute_fen_map`'s two `board.board_fen()` calls; the
consumption site needs no code change (the manual `turn` override there becomes
redundant, not broken).
**Warning signs:** New ep/castling regression test still fails after editing only
lines 443-451.

## Code Examples

See the per-item "Architecture Patterns" sections above for exact insertion-ready
code for all five fixes — each is a complete, minimal diff against the verified
current source, not illustrative pseudocode.

## State of the Art

Not applicable — this is an internal bugfix phase against the project's own
existing, current-generation code. No external library/API version drift is
involved in any of the five fixes.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Item 4's "one aggregated Sentry capture" means one `capture_exception()` call per malformed game (mirroring the existing PGN-parse precedent), not a single end-of-import summary event | Item 4 | Low — either reading satisfies "don't abort the whole import"; if the planner wants a true single end-of-batch summary instead, that's a small additional accumulator (count + one message after the loop) rather than a redesign |
| A2 | The averaged-variance proxy `v = (var_eg + var_ne) / 2` is an acceptable approximation for the shared subset's per-game variance in the D-04 correction (rather than tracking a separate W/D/L accumulator for the intersection) | Item 3 (D-04 algebra) | Low-Medium — the approximation only affects the MAGNITUDE of the SE widening in asymmetric cases (var_eg far from var_ne); it never breaks the direction (always widens, never narrows, since `m ≥ 0` and `v ≥ 0`); the exact-WDL alternative is a documented drop-in upgrade if precision matters more than the "least invasive" framing in D-04 |
| A3 | The `has_forced_mate` fallback's `tactic_piece`/`tactic_depth` derivation (mirroring `detect_generic_mate`'s own logic minus the checkmate check) is the intended semantics, since D-01 only specifies "skip geometry-dependent mate subtypes" and doesn't literally specify piece/depth derivation | Item 1 (Bug A) | Low — `detect_generic_mate` is the closest existing analog (same tier, same "catch-all" role); any planner deviation here is cosmetic (which piece gets attributed), not a correctness risk |
| A4 | Leaving the now-redundant `board_before.turn = ...` override at `flaws_service.py:450-451` in place (rather than removing it as part of the fix) is acceptable / preferred, since it's harmless post-fix and removing it would be an unscoped simplification | Item 1 (Bug B) | Very low — either choice is behaviorally identical; flagged only so the planner makes a deliberate choice rather than an accidental one |

## Open Questions

1. **Should the tagger precision-gate harness be enhanced to derive `has_forced_mate`
   from the fixture's `Themes` column (e.g. `mateInN`/`mate` tags) for fuller
   real-data coverage of Bug A?**
   - What we know: the CSV already carries this ground-truth signal
     (`motif_theme_map.py:58`); it is not currently threaded into the harness's
     detector call.
   - What's unclear: whether any fixture rows actually have PVs long enough to
     exercise the truncation path even if this were wired up (puzzle solution PVs
     are the actual solution length, not capped at 12 — most mate puzzles are
     short).
   - Recommendation: **decline for this phase** (scope creep beyond the todo's ask);
     capture as a follow-up seed if deeper empirical validation of Bug A against
     real puzzle data is ever wanted. The dedicated hand-built unit test already
     satisfies D-03's stated verification requirement.

2. **Should `run_eval_drain()` be refactored into an extracted, directly-testable
   `_entry_drain_tick()` (mirroring `_full_drain_tick`'s WR-07 extraction), given the
   asymmetry documented under Item 2?**
   - What we know: the existing task-based test pattern
     (`asyncio.create_task` + `wait_for` + `cancel`) already works and is used by 3
     existing tests in this exact file for exactly this kind of scenario.
   - What's unclear: whether the planner considers this refactor "beyond fix-scope"
     (CLAUDE.md's phase-scope discipline) or a reasonable piggyback improvement.
   - Recommendation: **do not refactor** as part of this fix — the inline fix is
     fully testable with the existing pattern; recommend flagging the extraction as
     a separate, optional follow-up if the planner wants long-term test-ergonomics
     parity between the two drain lanes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (dev, per-run-DB isolation) | All 5 items' integration tests | ✓ (per CLAUDE.md `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`) | 18 (per CLAUDE.md) | — |
| pytest / uv | All verify commands | ✓ (project-standard) | per `pyproject.toml` | — |

No new external dependencies. `tests/scripts/tagger/` requires no DB/network (pure
offline CSV scoring, per its own module docstring) — only the default addopts
`--ignore` needs to be overridden with an explicit path, as shown in each item's
verify command above.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (per `tests/scripts/tagger/conftest.py`'s pytest-asyncio usage and observed `pytest-9.0.3` in `.pyc` cache names) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"`) |
| Quick run command | `uv run pytest tests/services/test_tactic_detector.py tests/services/test_flaws_service.py tests/services/test_eval_drain.py tests/services/test_score_confidence.py tests/services/test_time_pressure_service.py tests/test_chesscom_client.py tests/test_lichess_client.py tests/test_eval_worker_endpoints.py -x` |
| Full suite command | `uv run pytest -n auto` (does NOT include `tests/scripts/tagger` — run that explicitly per item 1's verify command) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ITEM-1a | Truncated forced-mate PV tags generic `mate`, not nothing | unit | `pytest tests/services/test_tactic_detector.py -k has_forced_mate -x` | ❌ Wave 0 — new test |
| ITEM-1b | `fen_map` preserves castling/en-passant; ep-capture PV replays correctly | unit | `pytest tests/services/test_flaws_service.py -k "fen_map or FenRecompute" -x` | ⚠️ Existing `TestFenRecompute` tests must be UPDATED (encode buggy contract today), not just added to |
| ITEM-1c | Tactic-tagger precision gate does not regress | regression | `pytest tests/scripts/tagger/test_detector_precision.py -x` | ✅ exists (excluded from default run — explicit path required) |
| ITEM-2 | Dead-pool all-fail entry-ply batch is NOT stamped complete; lease naturally expires | unit/integration | `pytest tests/services/test_eval_drain.py -k all_fail -x` | ❌ Wave 0 — new test (mirror `test_all_fail_keeps_game_pending` pattern from `test_full_eval_drain.py`) |
| ITEM-3 | Shared-quintile games widen the reported SE (covariance correction) | unit | `pytest tests/services/test_score_confidence.py tests/services/test_time_pressure_service.py -k shared -x` | ❌ Wave 0 — new test |
| ITEM-4 | One malformed platform game is skipped; import completes with the rest | unit | `pytest tests/test_chesscom_client.py tests/test_lichess_client.py -k "normaliz" -x` | ❌ Wave 0 — new test (mirror `test_malformed_json_lines_skipped`) |
| ITEM-5 | Entry-submit excludes a leased-but-expired game from stamping | unit/integration | `pytest tests/test_eval_worker_endpoints.py -k entry_submit -x` | ❌ Wave 0 — new test (mirror `test_lease_reclaim`) |

### Sampling Rate
- **Per task commit:** run the specific item's file(s) above with `-x`.
- **Per wave merge:** `uv run pytest -n auto` (full backend suite, excludes the
  tagger dir by design) **plus** `uv run pytest tests/scripts/tagger/test_detector_precision.py`
  explicitly for item 1's wave.
- **Phase gate:** full pre-merge gate per CLAUDE.md (`ruff format`, `ruff check
  --fix`, `ty check`, `pytest -n auto -x`, frontend lint+test — though this phase is
  backend-only, so the frontend step is a no-op) before squash-merging to `main`.

### Wave 0 Gaps
- [ ] New `has_forced_mate=True` truncated-mate unit test in
      `tests/services/test_tactic_detector.py` — covers ITEM-1a.
- [ ] Update (not just add to) `TestFenRecompute` in `tests/services/test_flaws_service.py`
      (4 existing tests encode the pre-fix contract) — covers ITEM-1b.
- [ ] New ep/castling PGN fixture + regression test in `tests/services/test_flaws_service.py`
      — covers ITEM-1b.
- [ ] New dead-pool all-fail test in `tests/services/test_eval_drain.py` — covers ITEM-2.
- [ ] New `shared_n`/`m`-widening test in `tests/services/test_score_confidence.py`
      and `tests/services/test_time_pressure_service.py` (plus updating the 4
      existing 5-tuple destructures in the latter to 6-tuple) — covers ITEM-3.
- [ ] New malformed-game-skip test in `tests/test_chesscom_client.py` and
      `tests/test_lichess_client.py` — covers ITEM-4.
- [ ] New expired-lease-excluded test in `tests/test_eval_worker_endpoints.py` —
      covers ITEM-5.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surfaces touched — all 5 items are internal pipeline/detector logic; `/entry-submit` already sits behind `require_operator_token` (unchanged) |
| V3 Session Management | No | Not applicable |
| V4 Access Control | Marginal (item 5) | The item-5 fix *tightens* an existing advisory (not authz) lease-ownership check between trusted, operator-token-authenticated remote workers — it is not a new access-control boundary, just closing a data-integrity gap between co-operating trusted parties |
| V5 Input Validation | No new surface | Item 4 adds defensive per-item error handling around already-validated (Pydantic `NormalizedGame`) output; no new input surface is introduced |
| V6 Cryptography | No | Not applicable |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Silent data loss from an unguarded per-item loop (items 2, 4) | Repudiation / Denial of Service (partial) | Per-item try/except + skip + Sentry capture (item 4); circuit-breaker-and-retry rather than false-complete (item 2) — both already-established patterns in this codebase, extended here rather than invented |
| Stale/shared worker identity permitting a foreign write (item 5) | Tampering / Spoofing (mild — operator-token-trusted parties only) | Time-boxed lease with an expiry check at write time (`entry_eval_lease_expiry > now()`), matching the existing full-ply `eval_jobs.status='leased'` pattern's intent |

No new attack surface is introduced by this phase; all five fixes reduce existing
silent-failure / data-integrity risk rather than opening new risk.

## Sources

### Primary (HIGH confidence — read directly this session)
- `app/services/tactic_detector.py` (lines 1030-1180, 2400-2545) — mate-detector
  guards, Tier-1 dispatch, `_parse_pv`
- `app/services/flaws_service.py` (lines 300-510) — `_recompute_fen_map`,
  `_detect_tactic_for_flaw`
- `app/services/eval_drain.py` (lines 2016-2420, 2488-2650, 2810-2848) —
  `_apply_eval_results`, `_mark_evals_completed`, `run_eval_drain`,
  `_full_drain_tick`, WR-05 breaker, `run_full_eval_drain`
- `app/services/engine.py` (lines 370-499) — `EnginePool`, `_analyse`, `_restart_worker`
- `app/services/endgame_service.py` (lines 2100-2345) — `_iterate_clock_rows`,
  `_build_quintile_bullets`
- `app/services/score_confidence.py` (whole file) — `compute_score_difference_test`
  and siblings
- `app/routers/eval_remote.py` (lines 853-990) — `entry_submit_eval`
- `app/services/chesscom_client.py` (lines 240-333), `app/services/lichess_client.py`
  (lines 130-210), `app/services/normalization.py` (lines 1-40, 210-270)
- `tests/scripts/tagger/{conftest,motif_theme_map,precision_floors}.py`,
  `tests/scripts/tagger/test_detector_precision.py` — precision gate mechanics,
  location correction
- `tests/services/test_flaws_service.py` (lines 530-620) — `TestFenRecompute` blast radius
- `tests/services/test_eval_drain.py` (whole file), `tests/services/test_full_eval_drain.py`
  (lines 778-830) — existing test patterns for items 2
- `tests/services/test_time_pressure_service.py` (lines 1-165), `tests/test_endgame_service.py`
  — existing test patterns for item 3
- `tests/test_chesscom_client.py`, `tests/test_lichess_client.py` (whole files) —
  existing test patterns for item 4
- `tests/test_eval_worker_endpoints.py` (lines 100-250, 1179-1235, 1625-1720) —
  existing test patterns for item 5
- `pyproject.toml` (pytest addopts) — confirms tagger-dir exclusion from default run
- `.planning/todos/pending/2026-07-03-code-review-pipeline-tactic-correctness-phase.md`,
  `.planning/notes/2026-07-03-code-review-fable-triage.md`,
  `reports/code-review-fable-2026-07-02.md`, `148-CONTEXT.md` — phase source docs

### Secondary (MEDIUM confidence)
- None — all claims in this document were verified directly against the current
  codebase in this session; no web/external documentation was needed for a
  backend-internal bugfix phase.

### Tertiary (LOW confidence)
- None.

## Fix-site anchor drift report

| Anchor (CONTEXT.md claim) | Claimed location | Actual location | Status |
|---|---|---|---|
| `has_forced_mate` no-op branch | `tactic_detector.py` ~2462-2490 | `tactic_detector.py` 2462-2490 (guard) + 1061/1128/1157/1201/1272/1330/1386/1437 (per-detector bail-out sites, not previously enumerated) | ✅ ACCURATE, but incomplete — the guard line is right; the actual "no-op" behavior lives in 8 additional per-detector locations, now enumerated above |
| `fen_map` construction | `flaws_service.py` ~443-451 | Consumption site 443-451 is accurate; **actual storage/fix site is `_recompute_fen_map`, lines 312-335, a different function not cited by this anchor** | ⚠️ PARTIAL — anchor's line range is real code but is the wrong site for the actual one-line×2 fix; both sites must be understood, only 312/327 need edits |
| `precision_floors.py` | `app/services/precision_floors.py` | `tests/scripts/tagger/precision_floors.py` | ❌ DRIFTED (wrong directory entirely) — flag prominently, this file does not exist under `app/services/` |
| Entry-ply drain stamp site | `eval_drain.py` ~2304-2308 | Unrelated code at 2304-2308 (a per-game exception handler in `_classify_and_insert_flaws`); actual stamp function `_mark_evals_completed` defined at 2148-2166, called at line 2374 | ❌ DRIFTED (~70 lines, and points at the wrong function entirely) |
| WR-05 full-ply breaker to mirror | `eval_drain.py` ~2556-2570 | `eval_drain.py` 2630-2647 | ❌ DRIFTED (~75 lines) |
| `EnginePool` docstring | `engine.py` ~380-382 | `engine.py` 379-381 | ✅ ACCURATE (off by ~1-2 lines, negligible) |
| Wrong-independence docstring | `endgame_service.py` ~2140-2143 | `endgame_service.py` 2139-2143 | ✅ ACCURATE (off by ~1 line, negligible) |
| Quintile fix site (`compute_score_difference_test` call) | `endgame_service.py` ~2326-2328 | `endgame_service.py` 2326-2328 | ✅ ACCURATE (exact match) |
| Entry-submit stamping | `eval_remote.py` ~746-813 | Function `entry_submit_eval` at 853-990; guard query 891-903; stamp call 957 | ❌ DRIFTED (~100-135 lines) |
| `chesscom_client.py` unguarded normalize | ~325-330 | Line 326 | ✅ ACCURATE (exact match) |
| `lichess_client.py` unguarded normalize | ~184-188 | Line 184 | ✅ ACCURATE (exact match) |

**Summary for the planner:** 3 of 11 anchors have drifted enough to matter
(precision_floors.py's directory, the entry-ply drain stamp site, the WR-05
full-ply breaker location, and the entry-submit function) — re-verify these 4
specific locations at plan-write time rather than trusting the CONTEXT.md line
numbers verbatim; the other 7 are accurate or negligibly off.

## Metadata

**Confidence breakdown:**
- Item 1 (tactics): HIGH — both bugs reproduced by direct code reading; D-03 gate
  mechanics fully traced through to the `addopts` exclusion and the harness's
  exact call signature; existing test blast radius enumerated line-by-line.
- Item 2 (drain circuit breaker): HIGH — exact insertion point identified; the
  structural asymmetry with the full-ply lane (no extracted tick function) is a
  concrete, load-bearing finding, not a guess; `EnginePool` docstring falsity
  independently verified by reading `_analyse`'s `finally` block.
- Item 3 (stats covariance): HIGH — algebra derived from first principles and
  numerically validated against CONTEXT.md's own worked example to 3 decimal
  places; blast radius (1 production + 4 test call sites) confirmed by exhaustive grep.
- Item 4 (import robustness): HIGH — exact `KeyError` reproduction path confirmed
  by reading `normalize_chesscom_game`; existing precedent pattern read verbatim.
- Item 5 (entry-submit guard): HIGH — exact one-line fix confirmed against the
  established `func.now()` idiom used elsewhere in this codebase; existing test
  fixture pattern (`test_lease_reclaim`) is a near-exact template.
- Anchor drift audit: HIGH — every one of the 7 canonical-reference anchors was
  independently opened and read this session; 4 confirmed drifted, 7 confirmed accurate.

**Research date:** 2026-07-04
**Valid until:** 14 days (backend-internal bugfix phase against actively-changing
code — this codebase ships multiple commits per day; re-verify anchors if planning
is delayed past ~2 weeks).
