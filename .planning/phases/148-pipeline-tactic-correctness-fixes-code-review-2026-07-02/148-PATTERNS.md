# Phase 148: Pipeline & Tactic Correctness Fixes - Pattern Map

**Mapped:** 2026-07-04
**Files analyzed:** 12 fix-site files + 7 test files
**Analogs found:** 12 / 12 (this is a bugfix phase — analogs are the pre-existing sibling code paths within the same files, already verified by RESEARCH.md)

Note: RESEARCH.md already contains verified line anchors and ready-to-adapt code
excerpts for every fix site. This document reframes that material as an explicit
file → analog → excerpt map for the planner, and flags which anchors drifted from
CONTEXT.md's claims (use the VERIFIED lines below, not CONTEXT.md's).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog (same file or sibling) | Match Quality |
|---|---|---|---|---|
| `app/services/tactic_detector.py` (mate fallback, ~2487-2490 insertion) | service (pure function, detector) | transform | `detect_generic_mate` (same file, ~1128) | exact — same tier, same catch-all role |
| `app/services/flaws_service.py` (`_recompute_fen_map`, lines 312-335) | service (PGN replay) | transform | its own pre-fix loop (change `board_fen()` → `fen()`) | exact — one-line-times-two edit |
| `app/services/eval_drain.py` (`run_eval_drain`, WR-05 mirror, ~2374-2415) | service (background drain loop) | event-driven / batch | `_full_drain_tick` WR-05 breaker at `eval_drain.py:2630-2647` | exact — same repo, same bug pattern, different lane |
| `app/services/engine.py` (`EnginePool` docstring, 379-381) | utility (docstring only) | — | n/a (doc fix) | n/a |
| `app/services/endgame_service.py` (`_iterate_clock_rows` + `_build_quintile_bullets`, 2106-2342) | service (stats aggregation) | batch / transform | `compute_score_difference_test` (`app/services/score_confidence.py:173-253`) | exact — extend in place |
| `app/services/score_confidence.py` (`compute_score_difference_test`, 173-253) | service (pure stats function) | transform | itself (add optional trailing param) | exact |
| `app/services/chesscom_client.py` (import loop, line 326) | service (async generator, import pipeline) | streaming / event-driven | `app/services/import_service.py:922-932` per-game try/except pattern | exact — established CLAUDE.md pattern already in codebase |
| `app/services/lichess_client.py` (import loop, line 184) | service (async generator, NDJSON stream) | streaming | same `import_service.py:922-932` pattern; sibling existing `json.JSONDecodeError` guard at lines 178-182 | exact |
| `app/routers/eval_remote.py` (`entry_submit_eval`, guard query 891-903) | router (trust-boundary guard) | request-response | existing lease-expiry idiom used in `app/users.py`, `app/routers/auth.py` (`sa.func.now()` comparisons) | exact |
| `tests/services/test_tactic_detector.py` | test | unit | existing `TestPriorityOrder`-style class in same file | exact |
| `tests/services/test_flaws_service.py` (`TestFenRecompute`, 535-614) | test | unit | itself — 4 existing tests must be UPDATED, not just added to | exact (inverted assertions) |
| `tests/services/test_eval_drain.py` | test | unit/integration | `tests/services/test_full_eval_drain.py::test_all_fail_keeps_game_pending` (778-829) + `TestEngineNoneMarksComplete` (384-447) task-based style | exact |
| `tests/services/test_score_confidence.py` + `tests/services/test_time_pressure_service.py` | test | unit | `TestUserAndOppQuintileIndependentSplit` (`_make_row` builder, lines 113-161) | exact |
| `tests/test_chesscom_client.py` / `tests/test_lichess_client.py` | test | unit | `test_malformed_json_lines_skipped` (lichess, 163-179); `_make_game()` helper + `test_valid_username_yields_normalized_games` (chess.com, 23-52, 102) | exact |
| `tests/test_eval_worker_endpoints.py` | test | unit/integration | `test_lease_reclaim` (1179-1234) + `_insert_game`/`_get_game_entry_eval_leased_by`/`_get_game_evals_completed_at` helpers (104, 234) | exact |

## Pattern Assignments

### `app/services/tactic_detector.py` (service, transform) — Item 1 Bug A

**Analog:** `detect_generic_mate` and the existing Tier-1 mate cascade in the same file (~1030-1180, 2400-2545).

**Bug:** every per-detector mate function re-checks `boards[-1].is_checkmate()` and bails on a truncated (PV_CAP_PLIES=12) but genuine forced mate — see the 8 bail-out sites:
```
detect_back_rank_mate            tactic_detector.py:1061
detect_generic_mate              tactic_detector.py:1128
detect_smothered_mate             tactic_detector.py:1157
detect_anastasia_mate              tactic_detector.py:1201
detect_hook_mate                    tactic_detector.py:1272
detect_arabian_mate                  tactic_detector.py:1330
detect_boden_or_double_bishop_mate    tactic_detector.py:1386
detect_dovetail_mate                   tactic_detector.py:1437
```
Each: `if not boards[-1].is_checkmate(): return False, None, None` (or equivalent).

**Fix — insert immediately after the existing `detect_generic_mate` check, inside the `if _can_run_mate:` block (current lines ~2487-2490), before Tier-2+ dispatch:**
```python
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
`moves` is guaranteed non-empty here (early-return at ~2454-2455 when `not moves`).

**Test analog:** no existing `has_forced_mate` coverage exists — write new tests in
`tests/services/test_tactic_detector.py` using plain `chess.Board(fen)` (mate-branch
detection reads only `boards`/`moves`, not `boards[0].move_stack` — the
`build_detector_board` fixture is only required for hanging-piece/intermezzo/recapture
detectors, per memory `project_tactic_detector_flaw_move_context`). Build a hand-made
mate-in-N position where N is large enough the 12-ply-capped PV doesn't reach
checkmate; assert `TacticMotifInt.MATE` returned with `has_forced_mate=True`, and
assert `None` (unchanged) with `has_forced_mate=False` on the same truncated PV
(regression guard for the flag gate).

---

### `app/services/flaws_service.py` (service, transform) — Item 1 Bug B

**Analog:** the function's own pre-fix loop — this is a same-site fix, not a cross-file copy.

**Current (buggy) code**, `_recompute_fen_map`, lines 312-335:
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
**Fix (D-02):** change both `board.board_fen()` calls to `board.fen()`. This is the
ONLY sanctioned exception to the CLAUDE.md `board_fen()`-only rule (the map is
detector-internal, never touches Zobrist comparisons). Zobrist/position-comparison
call sites elsewhere in the codebase must NOT be touched.

**Consumption site** (`_detect_tactic_for_flaw`, lines 443-451) needs NO code change
— the manual `board_before.turn = ...` override becomes redundant-but-harmless once
`fen_map` stores a full FEN. Leave it in place (out of fix-scope to remove per
RESEARCH.md A4 — flag as optional cleanup only, don't do it opportunistically).

**Test analog:** `tests/services/test_flaws_service.py::TestFenRecompute` (535-614) —
these 4 existing tests currently assert the BUGGY piece-placement-only contract as
correct and must be UPDATED (inverted), not left alone:

| Test | Current assertion | Must become |
|---|---|---|
| `test_initial_position_at_ply_zero` | `fen_map[0] == "rnbqkbnr/.../RNBQKBNR"` (no suffix) | Full FEN: `"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"` |
| `test_after_e4_board_fen` | `assert " " not in fen` | Invert: assert 6 space-separated fields |
| `test_board_fen_not_full_fen` | asserts exactly 8 `/`-fields, no space | Rewrite (rename `test_full_fen_not_board_fen`) to assert the opposite |
| `test_replay_failure_captured_to_sentry` | monkeypatches `chess.Board.board_fen` | Monkeypatch `chess.Board.fen` instead |

Also update the class docstring (currently: `"""Tests for _recompute_fen_map — PGN
replay using board.board_fen()."""`). New tests needed: an ep-capture or castling PGN
fixture (no existing one — `_SHORT_PGN`/`_PGN_THREE_MOVES` are plain `1.e4 e5`-style)
replayed through both `_recompute_fen_map` and `_detect_tactic_for_flaw`, asserting the
SAN parses and the resulting occupant count is correct after an ep capture.

---

### `app/services/eval_drain.py` (service, event-driven/batch) — Item 2

**Analog:** the full-ply lane's WR-05 breaker, VERIFIED at `eval_drain.py:2630-2647`
(CONTEXT.md's claimed ~2556-2570 has drifted ~75 lines — use 2630-2647).

**Structural note:** unlike the full-ply lane (which has an extracted, directly
testable `_full_drain_tick() -> bool`, 2488-2809), the entry-ply lane's
`run_eval_drain()` (2311-2415, VERIFIED — CONTEXT.md's claimed stamp site ~2304-2308
is WRONG, it points at an unrelated per-game exception handler in
`_classify_and_insert_flaws`) is a single monolithic `while True:` loop. Do NOT
extract a `_entry_drain_tick()` helper as part of this fix (RESEARCH.md Open Question
2 — explicitly declined; would be a scope-creep refactor). Add the fix inline.

**Insertion point** — between Step 4 (gather) and Step 5 (open write session):
```python
            if eval_targets:
                eval_results: Sequence[tuple[int | None, int | None]] = await asyncio.gather(
                    *(engine_service.evaluate(t.board) for t in eval_targets)
                )
            else:
                eval_results = []

            # --- NEW: WR-05 mirror for the entry-ply lane ---
            # Gate on eval_targets being non-empty (mirrors the full-ply WR-05 gate
            # at eval_drain.py:2637 exactly) — an empty eval_targets list is the
            # legitimate "no positions to evaluate" case that must still be stamped
            # complete (see test_engine_none_marks_complete).
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
                continue  # skip Step 5: no _apply_eval_results, no
                          # _classify_and_insert_flaws, no _mark_evals_completed.
                          # lease TTL (20s, ENTRY_LEASE_TTL_SECONDS) expires naturally.

            # Step 5: open session LATE ...
```
`_mark_evals_completed` is defined at 2148-2166, called at line 2374 (VERIFIED — this
is the actual stamp call CONTEXT.md's ~2304-2308 anchor was pointing at incorrectly).
"Release the lease" = do nothing extra; let the 20s TTL (`ENTRY_LEASE_TTL_SECONDS =
169`, `_DRAIN_IDLE_SLEEP_SECONDS = 95` — both already-defined) expire, same mechanism
`test_idempotent_on_simulated_crash` already relies on. The explicit `sleep` here IS
required (unlike the full-ply lane, which gets it "for free" from its outer `if not
processed`).

**`app/services/engine.py` docstring fix** — VERIFIED lines 379-381 (claimed ~380-382,
negligible drift):
```python
    On per-worker timeout / crash, that worker restarts in place; siblings
    keep going. If restart fails, the worker's slot is NOT dropped — it
    stays in the available queue and every future pickup returns (None, None)
    almost instantly (see the `protocol is None` early-return in `_analyse`).
    A pool where every worker has permanently failed therefore answers
    every `evaluate()` call near-instantly with (None, None) rather than
    hanging — this is what the entry/full-ply drain "all engine evals
    failed" circuit breakers (WR-05) detect and react to.
```

**Test analog:** `tests/services/test_full_eval_drain.py::test_all_fail_keeps_game_pending`
(778-829) adapted to the task-based test style of `tests/services/test_eval_drain.py::
TestEngineNoneMarksComplete` (384-447): insert a game with real `GamePosition` rows,
monkeypatch `drain_module.engine_service.evaluate` to `AsyncMock(return_value=(None,
None))`, run `run_eval_drain()` as a background task with `wait_for` + `cancel`,
assert `evals_completed_at IS NULL`. Do NOT break `test_engine_none_marks_complete`
(opposite assertion, zero-eval-target case) — the `eval_targets and` gate is
load-bearing for exactly this reason.

---

### `app/services/endgame_service.py` + `app/services/score_confidence.py` (service, batch/transform) — Item 3

**Analog:** `compute_score_difference_test` itself (`score_confidence.py:173-253`) —
extend in place, don't replace.

**Current (buggy, VERIFIED) SE formula:**
```python
var_eg = max(0.0, (eg_w + 0.25 * eg_d) / eg_n - score_eg ** 2)
var_ne = max(0.0, (ne_w + 0.25 * ne_d) / ne_n - score_ne ** 2)
se_diff = math.sqrt(var_eg / eg_n + var_ne / ne_n)     # treats cohorts as independent
```
**Fix (D-04, covariance correction, numerically validated against CONTEXT.md's own
100/100/100 worked example: buggy SE 0.0707 → corrected SE 0.1000 exactly):**
```python
v_shared = (var_eg + var_ne) / 2.0
cov_correction = 2.0 * m * v_shared / (eg_n * ne_n)
se_diff = math.sqrt(max(0.0, var_eg / eg_n + var_ne / ne_n + cov_correction))
```
New trailing parameter `shared_n: int = 0` (default preserves every existing caller —
confirmed single production call site via grep). `m` = count of games where
`user_quintile == opp_quintile` for the same `(tc, q)` bucket, computed in
`_iterate_clock_rows` (2106-2245) by adding one line to the existing loop next to its
already-computed `user_quintile`/`opp_quintile` (lines 2203-2204):
```python
tc_shared_quintile_count: dict[tuple[str, int], int] = defaultdict(int)
...
if user_quintile == opp_quintile:
    tc_shared_quintile_count[(tc, user_quintile)] += 1
```
Blast radius (all VERIFIED, exact — must all update together):
1. `_iterate_clock_rows` return: 5-tuple → 6-tuple (update type annotation + docstring).
2. Production call site `endgame_service.py:2383-2389` — destructure the 6th value.
3. `_build_quintile_bullets` (2263-2342) — add `shared_wdl_count` param, look up
   `m = shared_wdl_count.get((tc, q), 0)`, pass to `compute_score_difference_test`.
4. `compute_score_difference_test` (`score_confidence.py:173`) — add `shared_n: int = 0`.
5. **4 existing test call sites** in `tests/services/test_time_pressure_service.py`
   (lines 113, 131, 152, 161, all in `TestUserAndOppQuintileIndependentSplit`)
   destructure a 5-tuple — WILL raise `ValueError: too many values to unpack` and must
   be updated to 6-tuple in the same commit.

Also fix the wrong independence docstring at `endgame_service.py:2139-2143`
(VERIFIED, off by 1 line from claimed 2140-2143) — explain the actual
non-independence and reference the correction, don't just delete the false claim.

**Test analog:** `TestUserAndOppQuintileIndependentSplit`'s `_make_row` builder
(`tests/services/test_time_pressure_service.py:113-161`) — extend to construct shared
games, assert `tc_shared_quintile_count[(tc,q)]` counts them, assert widened
`ci_low`/`ci_high` vs a non-shared control with identical W/D/L totals. Also add a
`test_score_confidence.py` case reproducing the 100/100/100 worked example
numerically, plus a `shared_n=0` byte-identical regression test.

---

### `app/services/chesscom_client.py` (service, streaming/event-driven) + `app/services/lichess_client.py` (service, streaming) — Item 4

**Analog:** `app/services/import_service.py:922-932` — the existing per-game
try/except + logger.warning + Sentry `set_context`/`capture_exception` + `continue`
pattern (already CLAUDE.md-compliant, established precedent):
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
Note this precedent captures ONCE PER FAILED GAME (not one end-of-batch aggregated
event) — mirror this shape verbatim (RESEARCH.md Assumption A1).

**Bug (VERIFIED):** `chesscom_client.py:326`, `lichess_client.py:184` (both exact —
no drift) call `normalize_chesscom_game`/`normalize_lichess_game` unguarded; a
missing key (e.g. `game["white"]` in `normalize_chesscom_game`,
`normalization.py:224`, direct subscript, no `.get()`) raises `KeyError` uncaught,
aborting the whole import.

**Fix (both files, same shape):**
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
# lichess_client.py — same shape, wrapping only normalize_lichess_game(...);
# leave the existing json.JSONDecodeError guard (lines 178-182) untouched.
```
No variable interpolation in message text; `user_id` goes in `set_context`.

**Test analog:** `tests/test_lichess_client.py::TestFetchLichessGames::
test_malformed_json_lines_skipped` (163-179) — inject a bad item between two good
ones, assert only good ones survive. For chess.com, use the existing `_make_game()`
helper (23-52) and `test_valid_username_yields_normalized_games` (line 102)
request-mocking scaffolding (`_make_response`); delete the `"white"` key from one game
in a 3-game archive to reproduce the exact `KeyError`.

---

### `app/routers/eval_remote.py` (router, request-response) — Item 5

**Analog:** existing `sa.func.now()` lease-expiry idiom used elsewhere (`app/users.py`,
`app/routers/auth.py`, `user_rating_anchors_repository.py`).

**Bug (VERIFIED — function `entry_submit_eval` at line 853, guard query 891-903;
CONTEXT.md's claimed ~746-813 has drifted ~100-135 lines):**
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
No `entry_eval_lease_expiry` check — a stale/re-leased submission still matches.

**Fix (D-05, minimum guard):**
```python
        result = await guard_session.execute(
            select(Game.id).where(
                Game.entry_eval_leased_by == worker_id,
                Game.evals_completed_at.is_(None),
                Game.entry_eval_lease_expiry > sa.func.now(),   # D-05 (Phase 148)
            )
        )
```
`sa` already imported at top of file as `import sqlalchemy as sa`. On guard failure:
implicit skip (excluded id doesn't appear in `leased_game_ids`), no new HTTP status.

**Test analog:** `tests/test_eval_worker_endpoints.py::test_lease_reclaim`
(1179-1234) — raw `sa.text("UPDATE games SET entry_eval_lease_expiry = :ts,
entry_eval_leased_by = '...' WHERE id = :gid")` fixture pattern. Manufacture one game
with a past expiry and one with a future expiry, both leased to the same
`worker_id`, POST `/entry-submit`, assert only the future-expiry game appears in
`resp.json()["game_ids"]` and gets stamped. Reuse `_insert_game`,
`_get_game_entry_eval_leased_by`, `_get_game_evals_completed_at` helpers (104, 234).

## Shared Patterns

### Sentry aggregated-capture (per-item skip)
**Source:** `app/services/import_service.py:922-932`
**Apply to:** Item 4 (chesscom_client.py, lichess_client.py) — one `capture_exception`
per skipped game, `set_context` for variable data (never embed in message text), no
per-retry-attempt capture (not applicable here — normalization isn't retried).

### WR-05 circuit-breaker (all-fail detection)
**Source:** `app/services/eval_drain.py:2630-2647` (full-ply lane)
**Apply to:** Item 2 (entry-ply lane) — gate on `eval_targets` (or equivalent
non-empty engine-target list) being non-empty AND all results `(None, None)`; release
lease implicitly via TTL expiry; one aggregated Sentry `capture_message`; explicit
`asyncio.sleep` before `continue`.

### `sa.func.now()` server-side lease-expiry comparison
**Source:** `app/users.py`, `app/routers/auth.py`, `user_rating_anchors_repository.py`
**Apply to:** Item 5 (`eval_remote.py`) — avoids app/DB clock skew; `sa` already
imported project-wide as `sqlalchemy as sa`.

### Existing-test blast radius (update, don't just add)
Applies to Items 1 (`TestFenRecompute`, 4 tests) and 3 (`TestUserAndOppQuintileIndependentSplit`,
4 destructure call sites) — both have pre-existing tests whose assertions encode the
current bug as correct behavior. This is expected fallout per RESEARCH.md, not scope
creep or a regression to revert.

## No Analog Found

None — all 12 fix-site files and 7 test files have a directly applicable analog
(either a sibling function in the same file, or an established pattern elsewhere in
the codebase), per RESEARCH.md's exhaustive verification.

## Anchor Drift Warning (apply VERIFIED lines, not CONTEXT.md's claims)

| Anchor | CONTEXT.md claim | VERIFIED location |
|---|---|---|
| `precision_floors.py` | `app/services/precision_floors.py` | `tests/scripts/tagger/precision_floors.py` |
| Entry-ply drain stamp site | `eval_drain.py` ~2304-2308 | `_mark_evals_completed` defined 2148-2166, called at line 2374; 2304-2308 is unrelated code in `_classify_and_insert_flaws` |
| WR-05 full-ply breaker | `eval_drain.py` ~2556-2570 | `eval_drain.py` 2630-2647 |
| Entry-submit function | `eval_remote.py` ~746-813 | `entry_submit_eval` at 853-990; guard query 891-903 |

All other anchors (tactic mate guard, `fen_map` consumption site, `EnginePool`
docstring, quintile docstring/fix-site, chesscom/lichess normalize call sites) are
accurate or off by ≤2 lines — negligible.

## Metadata

**Analog search scope:** same-file sibling functions (Items 1a, 1b, 3) and
cross-file established patterns already read and verified in RESEARCH.md this
session (Items 2, 4, 5); no new codebase search was needed — RESEARCH.md's
"Architecture Patterns" and "Sources" sections already constitute the analog search.
**Files scanned:** 12 fix-site files, 7 test files (all listed in RESEARCH.md Sources).
**Pattern extraction date:** 2026-07-04
