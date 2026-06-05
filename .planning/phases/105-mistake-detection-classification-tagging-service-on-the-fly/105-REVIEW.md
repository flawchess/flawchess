---
phase: 105-mistake-detection-classification-tagging-service-on-the-fly
reviewed: 2026-06-05T13:34:35Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - app/services/mistakes_service.py
  - app/repositories/mistakes_repository.py
  - tests/services/test_mistakes_service.py
  - tests/test_mistakes_repository.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 105: Code Review Report

**Reviewed:** 2026-06-05T13:34:35Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

The mistake-detection service is a pure transform over stored per-ply evals,
with a thin repository and an extensive unit-test suite. The structure is clean
(small helpers, named constants, Literal types, ownership-guarded query) and the
security surface is sound. However, the core ply/color attribution logic does
not match the project's established ply-to-color convention or the eval-storage
convention used by `zobrist.py`. Two BLOCKER-class defects mis-attribute flaws
and read evals off by one row. The test suite does not catch them because the
synthetic fixtures encode the same incorrect convention the production code uses
(circular validation), so every test passes against wrong behavior.

The repository file and the security mitigations (ownership guard, parameterized
binds) are correct. The findings below concentrate on the service's correctness.

## Critical Issues

### CR-01: Mover-to-color mapping is inverted — every flaw is attributed to the wrong player

**File:** `app/services/mistakes_service.py:200`
**Issue:**
`_run_all_moves_pass` assigns the mover color by ply parity:

```python
mover: Literal["white", "black"] = "white" if n % 2 == 0 else "black"
```

The move that *produces* ply `n` (the move played from the board at ply `n-1`)
is white when `n` is **odd** and black when `n` is **even**. Verified directly
with python-chess on `1. e4 e5 2. Nf3 ...`:

```
ply 1: move=e4  (white played it)
ply 2: move=e5  (black played it)
ply 3: move=Nf3 (white played it)
```

So the mover producing ply `n` is white for **odd** `n`, but the code assigns
white to **even** `n`. The mapping is inverted.

Downstream impact: `classify_game_mistakes` filters flaws with
`if mover != user_color: continue` (line 459) and stamps `side=mover` on every
`FlawRecord`. With the inversion, a white user's flaws are computed from the
opponent's (black's) move transitions and vice versa, and `side` is wrong on
every emitted record. This is a data-correctness defect that propagates into the
library page (LIBG-02), so it must be fixed before any caller wires this in.

Note this is distinct from the project's "white = even plies" convention
(`endgame_service.py:2089`, `canonical_slice_sql.py:346`), which describes whose
*turn/clock* a ply row represents — not who *played the move arriving at* that
ply. The service needs the latter.

**Fix:**
```python
# Mover who PLAYED the move arriving at ply n: white for odd n, black for even n.
# (python-chess: ply 1 = white's 1st move, ply 2 = black's 1st move, ...)
mover: Literal["white", "black"] = "white" if n % 2 == 1 else "black"
```
Then add a test fixture whose color attribution is derived from an actual parsed
PGN (not hand-tuned to the old convention) so the assertion is independent of the
code under test. See WR-01.

### CR-02: `es_before` / `es_after` and `move_san` read the wrong `GamePosition` rows (eval-storage offset)

**File:** `app/services/mistakes_service.py:193-208` (eval reads), `230` (move_san)
**Issue:**
The service's stated model (docstring lines 193-196) is
"`positions[N].eval_cp` = eval AFTER move N was played." That contradicts how
`zobrist.py` actually populates the column. In `process_game_pgn`
(`zobrist.py:173-217`):

- The board is in its **pre-move** state for row `ply`.
- `move_san = board.san(node.move)` (line 179) — the move played **from** this
  position, i.e. leading to `ply+1`.
- `eval_cp = node.eval()` (lines 185-189) — the eval of the position **after**
  that move, i.e. the eval of position `ply+1`, stored on row `ply`.
- Confirmed by the module docstring lines 288-290: "`move_san` is the SAN of the
  move played FROM position at `ply` (leading to ply+1)."

So in the DB, **row `k` carries the move and the post-move eval for the
transition `k -> k+1`**, not the transition `k-1 -> k`. The service instead
treats `positions[N]` as "after move N" and `positions[N-1]` as "before move N",
which is shifted by one row. The net effect: `es_before`/`es_after` for the flaw
arriving at ply `N` are read from the wrong pair of rows, and `move_san`
(line 230, `positions[n].move_san`) reports the move played *after* the flaw
rather than the flawed move itself (the flawed move is `positions[n-1].move_san`).

The unit tests cannot detect this because `_make_pos` sets evals directly per
index to satisfy the service's stated convention; there is no end-to-end test
against a real imported game where the storage convention is fixed by `zobrist`.

This is a BLOCKER because it changes which move is flagged and the magnitude of
every ES drop. Because I cannot run the full import pipeline here, confirm the
exact offset with the verification test below before applying the fix — but the
`move_san` mismatch alone (line 230 vs `zobrist.py:215`/`288-290`) is
unambiguous.

**Fix (verify direction first):**
```python
# move_san: the flawed move is the one played FROM ply n-1 (zobrist stores the
# move leading to ply+1 on row ply). The move arriving at ply n is on row n-1.
move_san=positions[n - 1].move_san,
```
And add an integration test that imports a real PGN through `process_game_pgn`,
persists it, runs `classify_game_mistakes`, and asserts the flagged `move_san`
equals the SAN a human reads for that move number. Align the eval `_ply_to_es`
row indices to the same verified convention.

## Warnings

### WR-01: Tests validate against the code's own (incorrect) convention — no independent oracle

**File:** `tests/services/test_mistakes_service.py:446-549`, `851-942`
**Issue:**
Every `classify_game_mistakes` fixture hand-places `eval_cp` at indices chosen to
match the service's assumed mover parity and eval offset (e.g.
`test_blunder_emitted_as_flaw_record` asserts the ply-2 flaw is `side="white"`
because the code maps even plies to white). The "oracle closeness" test
(`_make_oracle_positions_and_counts`) also hand-derives its oracle counts from
the same assumed convention rather than from Lichess's actual game-level columns
(`game.white_blunders` etc. are *set* from the synthetic plan, never compared
against a real annotated PGN). The tests therefore pass even though CR-01/CR-02
make the production output wrong. This is circular validation: the suite asserts
"the code does what the code does."

**Fix:** Add at least one test that derives the expected `side`/`move_san` from a
parsed PGN independently of the service (e.g. compute mover color via python-chess
`board.turn` before the push), and one integration test that feeds a real
Lichess-annotated PGN through `process_game_pgn` and compares derived B/M/I counts
to the PGN's actual `%eval`/annotation-derived counts.

### WR-02: List index is silently assumed equal to `ply`, with no contiguity guard

**File:** `app/services/mistakes_service.py:199-208`, `230`, `399-402`, `464`
**Issue:**
The service indexes `positions[n]`, `positions[n-1]`, `positions[n-2]` and treats
the list position as the ply number. This is only valid if the loaded rows are
dense and contiguous from ply 0 (`positions[i].ply == i`). The repository orders
by ply but does not guarantee density. If any ply row is missing (partial eval
backfill, a deleted row, a future schema where rows are sparse), every index
silently misaligns with both the sibling rows and the PGN-derived `fen_map`,
producing wrong-but-plausible flaws with no error. There is no assertion or guard.

**Fix:** Either assert the invariant once at entry, or index by an explicit
`{pos.ply: pos}` map:
```python
by_ply = {p.ply: p for p in positions}
# ... use by_ply.get(n), by_ply.get(n - 1); skip when missing.
```
At minimum add `assert positions[i].ply == i` in a debug path or a fast guard
that returns `GameNotAnalyzed`/empty on a detected gap.

### WR-03: FEN recomputation failure is silently swallowed, emitting `fen=""`

**File:** `app/services/mistakes_service.py:167-181`, `225`
**Issue:**
`_recompute_fen_map` returns `{}` on an unparseable/empty PGN, and
`_build_flaw_record` falls back to `fen_map.get(n, "")`. A game whose PGN fails to
parse (but whose stored evals pass the 90% coverage gate) will emit FlawRecords
with `fen=""`. An empty FEN is not a valid board and will mislead any consumer
that renders the position. The failure is invisible — no Sentry capture, no log,
no `GameNotAnalyzed`. CLAUDE.md requires `sentry_sdk.capture_exception()` in
non-trivial service failure paths.

**Fix:** When `fen_map` is empty but coverage passed (an inconsistency: evals
exist but PGN won't replay), capture to Sentry with `set_context` and either
return `GameNotAnalyzed` or skip emission. Do not emit `fen=""`:
```python
if not fen_map:
    sentry_sdk.set_context("mistakes", {"game_id": game.id})
    sentry_sdk.capture_exception(RuntimeError("PGN replay produced no FENs"))
    return GameNotAnalyzed(reason="no_engine_analysis", eval_coverage=coverage)
```

### WR-04: `increment` from `parse_base_and_increment` can be `None` and re-narrowed redundantly; `time_control_str` may be absent

**File:** `app/services/mistakes_service.py:444-451`
**Issue:**
The increment-resolution block is correct but fragile: it relies on
`game.time_control_str` being truthy and on `parsed_inc is not None`. The first
branch reads `game.increment_seconds` (typed `int | float | None`). If a future
caller passes a `Game` with `increment_seconds=None` and a daily/odd
`time_control_str` that parses to `(None, None)`, increment silently stays `0.0`,
which then feeds `_move_time` (`prev - curr + increment`). That is acceptable as a
fallback but is undocumented at the call site, and the tempo classification will
quietly mislabel moves in increment games whenever the increment can't be
resolved. Not wrong per se, but the silent default deserves a comment and ideally
a `knowledge-gap` short-circuit when increment is genuinely unknown rather than
assuming 0.

**Fix:** Add a comment that `increment=0.0` is a deliberate fallback and consider
threading an `increment_known: bool` so `_classify_tempo` can avoid a `hasty`
verdict computed from a wrong move-time when the increment was guessed.

### WR-05: `_move_time` can produce a negative or inflated move time on clock anomalies

**File:** `app/services/mistakes_service.py:234-255`
**Issue:**
`prev_clock - curr_clock + increment` assumes monotonic clocks and a correct
two-ply-back same-side reading. Lichess/chess.com clocks occasionally have
anomalies (clock corrections, Berserk, first-move clock quirks), which can yield a
negative move time. A negative `move_time` is then compared against
`fast_move_threshold` in `_classify_tempo` (line 289) and would register as
`hasty` (since a negative is `< threshold`). There is no clamp or sanity bound.

**Fix:** Clamp and reject implausible values:
```python
mt = prev_clock - curr_clock + increment
if mt < 0:
    return None  # clock anomaly — let tempo fall back to knowledge-gap
return mt
```

## Info

### IN-01: Duplicate docstring line in `TestConstants`

**File:** `tests/services/test_mistakes_service.py:101-103`
**Issue:** The class-level docstring is immediately followed by a second
identical bare string literal (lines 102-103), a copy-paste artifact. Harmless
but dead.
**Fix:** Delete the duplicate string on lines 102-103.

### IN-02: Unused imports in the service test module

**File:** `tests/services/test_mistakes_service.py:18-23`
**Issue:** `MATE_CP_EQUIVALENT` and `TIME_PRESSURE_CLOCK_FRACTION`/
`HASTY_MOVE_FRACTION` are imported and used, but verify `_ply_to_es`-only
constants and re-imports inside test bodies (`_run_all_moves_pass` imported again
at lines 969 and 1010) are redundant with the top-level import surface. The local
re-imports inside `TestOracleCloseness` add noise.
**Fix:** Import `_run_all_moves_pass` once at module top and drop the two
in-body `from app.services.mistakes_service import ...` statements.

### IN-03: `SANITY_TOLERANCE` lives in production module but is test-only

**File:** `app/services/mistakes_service.py:66-68`
**Issue:** `SANITY_TOLERANCE` is documented as an oracle-closeness tolerance used
only by the test suite. Production-module constants that exist purely for tests
blur the module's contract.
**Fix:** Move `SANITY_TOLERANCE` into the test module (it is only referenced
there), or annotate clearly that it is a validation-only constant.

---

_Reviewed: 2026-06-05T13:34:35Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
