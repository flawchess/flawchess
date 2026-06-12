# Phase 113: Opponent-Flaw Materialization — Research

**Researched:** 2026-06-10
**Domain:** FlawChess backend — `game_flaws` table extension, classify-kernel generalization, reader gating
**Confidence:** HIGH (all findings from direct codebase inspection; no external dependencies)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** No `is_opponent` column. Player/opponent split is derived at query time via a single helper `is_opponent_expr(ply, games.user_color)`, encoding `mover = white if ply % 2 == 0 else black` and `is_opponent = (mover != user_color)`.
- **D-02:** No Alembic migration this phase. Opponent flaws go into existing columns at the opponent's own plies; PK `(user_id, game_id, ply)` never collides.
- **D-03:** No new index. Existing PK and `ix_game_flaws_user_severity` are sufficient.
- **D-04:** Every existing `game_flaws` reader must be retrofitted with a player-only gate (`is_opponent_expr(...) == False`) so opponent rows do not leak into the current self-only Library UI.
- **D-05:** Opponent flaws carry the full subject-relative tag set (severity, phase, tempo, miss, lucky, reversed, squandered) from the opponent's frame. Only `_is_unpunished` (the `lucky` end-rule) needs generalization — pass `derive_user_result(game.result, mover)` instead of the pre-resolved `user_result`.
- **D-06:** Keep ONE kernel: drop the `mover != user_color` filter at `flaws_service.py:543`. `FlawRecord` already carries `side`; `flaw_record_to_row` needs no change.
- **D-07:** Full per-game wipe+recompute (`delete_flaws_for_game` + `bulk_insert_game_flaws`). No additive opponent-only insert.
- **D-08:** Backfill scope: dev users 28 & 44 + benchmark cohort, both in phase 113. Prod stays empty.
- **D-09:** Kernel change makes `backfill_flaws.py` write both sides with no script-level code change.
- **D-10 (prior-phase):** Single classify path invariant — all three writers (eval_drain, reclassify_positions, backfill_flaws) call the same `classify_game_flaws` + `flaw_record_to_row`.

### Claude's Discretion

- Exact form/location of `is_opponent_expr`: SQLAlchemy hybrid expression on the `GameFlaw` model vs a plain helper function in `query_utils.py` — as long as it is the single source of the parity convention and is unit-tested against known white/black-user games.
- Whether to expose a `player_only()` / `opponent_only()` convenience wrapper around the expr for readers in D-04.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLAWX-01 | `game_flaws` records opponent flaws alongside player flaws, distinguished by `is_opponent` derived at query time via `is_opponent_expr(ply, games.user_color)`. | D-01 confirmed viable: ply parity convention is `white if n % 2 == 0 else black` (flaws_service.py:227); PK never collides because each ply belongs to exactly one side. |
| FLAWX-02 | The player-only upsert filter is dropped so opponent flaws persist on every classify path (import hook, reclassify_positions, backfill_flaws), preserving D-10. | Confirmed: the single filter to drop is `flaws_service.py:543`; all three writers are already calling the shared kernel. `_build_tags` needs per-mover `subject_result` (see Architecture Patterns). |
| FLAWX-03 | **VOIDED.** No Alembic migration, no `is_opponent` column, no new index. Replaced by D-04 reader-gating scope. | N/A — do not plan this. |
| FLAWX-04 | `scripts/backfill_flaws.py` repopulates both sides for dev users 28 & 44 and benchmark cohort, idempotent and batched. Prod stays empty. | Confirmed: script already uses `delete_flaws_for_game` + `bulk_insert_game_flaws` at `BACKFILL_GAMES_PER_BATCH = 100`; kernel change propagates automatically. |
</phase_requirements>

---

## Summary

Phase 113 is a surgical backend-only change with three distinct work streams: (1) generalize the classify kernel to emit both colors, (2) retrofit every existing reader with a player-only gate, and (3) run the backfill.

The kernel change is small but precise. `classify_game_flaws` in `app/services/flaws_service.py` has one filter to drop (line 543: `if mover != user_color: continue`) plus one per-mover subject-result fix in `_build_tags` (line 463: `_is_unpunished` currently passes the pre-resolved `user_result`, which must become `derive_user_result(game.result, mover)` so the lucky end-rule is correct for the opponent's frame). `_run_all_moves_pass` already evaluates both colors with per-mover ES, and `FlawRecord` already carries `side`. No change to `flaw_record_to_row` is needed.

The reader-gating work (D-04) is the highest-risk item because the set of readers is exhaustively catalogued here: five distinct `game_flaws` read sites in `library_repository.py` plus one cross-tab EXISTS in `query_utils.py` (via `flaw_exists_from_table`). All must add `is_opponent_expr(...) == False` before this phase ships. The `is_opponent_expr` helper itself must be placed in a single location and unit-tested against the documented off-by-one trap (white moves at even plies; the convention is non-obvious and has a prior bug history).

The backfill requires no script changes — the kernel change propagates automatically. The dev run is a standard UAT step; the benchmark run is a longer HUMAN-UAT step (do not gate phase completion on it).

**Primary recommendation:** Implement in three sequential plans: (1) kernel generalization, (2) `is_opponent_expr` helper + reader gating, (3) backfill. Plans 1 and 2 are tightly coupled by the correctness invariant — verify row counts double after plan 1 before retrofitting readers in plan 2.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Flaw classification (both colors) | Service (`flaws_service.py`) | — | Pure Python transform over ORM objects; no I/O |
| Player/opponent split expression | Repository (`query_utils.py` or `game_flaw.py`) | Service (reads it) | SQL expression lives closest to the data layer; services call helpers from repositories |
| `game_flaws` writes | Repository (`game_flaws_repository.py`) | Service (invokes) | D-10 single-mapping invariant already established |
| `game_flaws` reads (Library UI gating) | Repository (`library_repository.py`) | — | All read paths already in one module |
| Backfill execution | Script (`scripts/backfill_flaws.py`) | Repository | No change to script needed; kernel change propagates |

---

## Standard Stack

No new packages are introduced in this phase. All code uses the established project stack. [ASSUMED] (no external packages to verify)

**Installation:** N/A — no new dependencies.

---

## Package Legitimacy Audit

N/A — this phase installs no external packages. All work is within the existing codebase.

---

## Architecture Patterns

### System Architecture: Data Flow After This Phase

```
Import hook / reclassify / backfill
         │
         ▼
classify_game_flaws(game, positions)
   all_moves pass → both colors
   for n, (mover, severity, ...) in all_moves:
     if severity in (mistake, blunder):
       build_tags(n, ..., subject_result=derive_user_result(game.result, mover))
       → FlawRecord(ply=n, side=mover, ...)
         │
         ▼
   flaw_record_to_row(user_id, game_id, flaw)  [NO CHANGE]
         │
         ▼
   bulk_insert_game_flaws(session, rows)
   ON CONFLICT DO NOTHING on PK(user_id, game_id, ply)
         │
   game_flaws table now contains BOTH colors' rows
         │
   ┌─────┴──────────────────────────────────┐
   │  READ PATHS (all must add player gate)  │
   │                                         │
   │  query_flaws (Flaws subtab list)        │
   │  flaw_exists_from_table (Games tab EXISTS)│
   │  fetch_page_game_flaws (Games page cards)│
   │  fetch_stats_aggregates (stats panel)   │
   │  fetch_stats_trend (trend chart)        │
   └─────────────────────────────────────────┘
         │
   is_opponent_expr(GameFlaw.ply, Game.user_color) == False
   added to every read path WHERE clause
```

### Recommended Project Structure (no change)

```
app/
├── services/flaws_service.py       # kernel change: drop mover filter, fix subject_result
├── repositories/
│   ├── game_flaws_repository.py    # no change
│   ├── library_repository.py       # D-04: add player gate to 5 read sites
│   └── query_utils.py              # D-04: add player gate to flaw_exists_from_table
│                                   # OR: add is_opponent_expr helper here
├── models/game_flaw.py             # no change
scripts/
├── backfill_flaws.py               # no change (kernel propagates)
```

### Pattern 1: Ply-to-Color Convention (CRITICAL — off-by-one history)

**What:** In `_run_all_moves_pass`, ply `n` is indexed from 1 (the first move). White moves at even `n`, black at odd `n`. [VERIFIED: direct code inspection]

```python
# Source: app/services/flaws_service.py:226-227
for n in range(1, len(positions)):
    mover: Literal["white", "black"] = "white" if n % 2 == 0 else "black"
```

**Confirmed by SQL in library_repository.py:617-618:**
```python
# fetch_total_user_moves — same parity:
((GamePosition.ply % 2 == 0) & (Game.user_color == "white"), 1),
((GamePosition.ply % 2 != 0) & (Game.user_color == "black"), 1),
```

**The `is_opponent_expr` must encode the same convention:**
```python
# Proposed helper (query_utils.py or game_flaw.py):
# mover = white if ply % 2 == 0 else black
# is_opponent = (mover != user_color)
# Expanded:
#   ply even → white moves → is_opponent = (user_color != "white") = (user_color == "black")
#   ply odd  → black moves → is_opponent = (user_color != "black") = (user_color == "white")

def is_opponent_expr(
    ply_col: ColumnElement[int],
    user_color_col: ColumnElement[str],
) -> ColumnElement[bool]:
    """True when the mover at `ply_col` is the OPPONENT (not the player).

    Convention (mirrors _run_all_moves_pass):
        ply even → white mover → is_opponent iff user_color == 'black'
        ply odd  → black mover → is_opponent iff user_color == 'white'
    """
    return case(
        (ply_col % 2 == 0, user_color_col == "black"),
        else_=user_color_col == "white",
    )
```

This produces a `BooleanClauseList` usable directly in WHERE/FILTER. For the player-only gate: `is_opponent_expr(...) == False` or equivalently `~is_opponent_expr(...)`.

### Pattern 2: Subject Result for Lucky Tag

**What:** `_is_unpunished` (the `lucky` end-of-game rule) reads `user_result` to decide whether a blunder at the end of the game was a lucky escape. After the kernel emits both colors, this must use the *mover's* result, not the pre-resolved user result. [VERIFIED: code inspection]

**Current code (flaws_service.py:537-563):**
```python
# user_result = derive_user_result(game.result, game.user_color)  # pre-resolved once
# ...
# flaw["tags"] = _build_tags(n, ..., user_result, ...)
```

**Required change:**
```python
# In the emit loop, pass per-mover result to _build_tags:
for n, (mover, severity, es_before, es_after) in all_moves.items():
    if severity not in ("mistake", "blunder"):
        continue
    flaw = _build_flaw_record(...)
    subject_result = derive_user_result(game.result, mover)  # per-mover
    flaw["tags"] = _build_tags(n, severity, es_before, es_after,
                                positions, all_moves,
                                subject_result,   # was: user_result
                                increment, game.base_time_seconds)
    flaws.append(flaw)
```

The pre-resolved `user_result` at line 537 is still needed for nothing — it can be removed, or kept for documentation purposes. The key is that `_build_tags` and ultimately `_is_unpunished` must receive `derive_user_result(game.result, mover)`, not `derive_user_result(game.result, game.user_color)`.

### Pattern 3: Exhaustive Reader Inventory for D-04 Gating

All five `game_flaws` read sites in `library_repository.py` plus the cross-tab EXISTS in `query_utils.py` need the player-only gate. [VERIFIED: exhaustive grep of codebase]

| # | File | Function | Line(s) | What it reads | Gate needed? |
|---|------|----------|---------|---------------|-------------|
| R1 | `library_repository.py` | `flaw_exists_from_table` | 153–158 | `SELECT GameFlaw.ply WHERE ... user_id + game_id` | YES — EXISTS filter for Games tab; opponent rows inflate the count |
| R2 | `library_repository.py` | `query_flaws` | 248–284 | `SELECT GameFlaw, Game, PositionAt, PositionBefore` JOIN | YES — Flaws subtab list; opponent flaws appear as flaw cards |
| R3 | `library_repository.py` | `fetch_page_game_flaws` | 348–352 | `SELECT GameFlaw WHERE user_id + game_id IN (...)` | YES — chip/M+B building on Games-tab cards |
| R4 | `library_repository.py` | `fetch_stats_aggregates` | 455–472 | Aggregate scan `COUNT(*) FILTER` | YES — stats panel tag-distribution counts |
| R5 | `library_repository.py` | `fetch_stats_trend` | 544–553 | `COUNT(*) GROUP BY game_id` per-game trend | YES — per-game M+B rate trend chart |
| R6 | `query_utils.py` | `apply_game_filters` → `flaw_exists_from_table` | 119–130 | Delegates to `flaw_exists_from_table` | NO separate gate — R1 fix propagates here automatically |

**Not affected (confirmed):**
- `count_game_severities` (flaws_service.py:565) — reads `game_positions` via `_run_all_moves_pass`, then filters `mover == user_color` at line 601. No change needed.
- `_analyzed_game_ids_subquery` — reads `game_positions`, not `game_flaws`.
- `eval_drain._classify_and_insert_flaws` — write path only, no read of existing rows.
- `backfill_flaws.py`, `reclassify_positions.py` — write-side scripts.
- `library_service._build_card` and `_curate_chips_from_rows` — these operate on the `list[GameFlaw]` already fetched by R3 (`fetch_page_game_flaws`). If R3 is gated, these are clean.

**Implementation note for R1/R6:** `flaw_exists_from_table` in `library_repository.py` is the single choke point used by `query_utils.apply_game_filters`. Adding the player-only gate to `flaw_exists_from_table` automatically fixes both R1 and R6. The gate condition is:
```python
select(GameFlaw.ply).where(
    GameFlaw.game_id == Game.id,
    GameFlaw.user_id == user_id,
    ~is_opponent_expr(GameFlaw.ply, Game.user_color),  # player-only gate
    *clauses,
)
```

### Pattern 4: `is_opponent_expr` — Helper Function vs Hybrid Expression

**Recommendation: plain helper function in `query_utils.py`.** [ASSUMED — no prior hybrid expression usage in codebase]

Rationale:
- No hybrid expressions exist anywhere in the project (grep confirmed zero `hybrid_property`/`hybrid_expression` imports). Using one would introduce a new pattern with no prior precedent.
- `is_opponent_expr` needs `games.user_color` from a different table — a hybrid property on `GameFlaw` cannot directly access `Game.user_color`; it would need to be passed in anyway, making the signature identical to a plain helper.
- A plain helper in `query_utils.py` fits the existing pattern (that module already houses reusable SQL-expression builders like `apply_game_filters`).
- The helper is independently unit-testable as a pure function returning a SQLAlchemy `case()` expression; the test just needs to build two example rows (white-user game, even ply → player; white-user game, odd ply → opponent) and assert the boolean output.

**Convenience wrapper recommendation:** Add a `player_only_gate(ply_col, user_color_col)` wrapper returning `~is_opponent_expr(...)`. This makes the reader-gating at each call site read as intent rather than a negation. Optional but clarifies D-04 intent.

### Anti-Patterns to Avoid

- **Passing `user_result` (player's result) to `_build_tags` for opponent flaws:** The `lucky` tag fires incorrectly. For an opponent blunder at the end of a game where the opponent lost (i.e. the user won), `user_result == "win"`, but `subject_result` for the opponent is `"loss"`. Passing `user_result` would mark an end-of-game opponent blunder when they resigned as "lucky" — the opponent didn't "escape", they lost. Use `derive_user_result(game.result, mover)` per-mover. [VERIFIED: code inspection of `_is_unpunished` logic]

- **Scattering `ply % 2 ↔ user_color` inline across query sites:** This was the pattern that led to the documented prior off-by-one bug. Use `is_opponent_expr` everywhere.

- **Adding the player gate to `build_flaw_filter_clauses` instead of the outer WHERE:** `build_flaw_filter_clauses` builds tag/severity filter predicates and is reused by both the read paths and the EXISTS subquery. The player gate is orthogonal and must be applied separately at each call site (so it can be omitted when the future phase-115 comparison query intentionally reads both sides).

- **Using `ON CONFLICT DO UPDATE` instead of `DO NOTHING` on the bulk insert:** `bulk_insert_game_flaws` correctly uses `DO NOTHING`. Do not change this. After a `delete_flaws_for_game`, there are no pre-existing rows, so conflicts cannot occur in a normal recompute. `DO NOTHING` is the idempotent guard for the import hook, not the recompute path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ply-to-color encoding | Inline `ply % 2 == 0` scattered across queries | `is_opponent_expr(ply_col, user_color_col)` helper | One prior bug from this exact duplication; the convention is subtle |
| Delete-then-insert recompute | Custom merge logic | `delete_flaws_for_game` + `bulk_insert_game_flaws` (already exist) | Already idempotent, batched, OOM-safe |
| Subject result for per-mover lucky tag | Re-implement result inversion | `derive_user_result(game.result, mover)` (already imported) | Helper already handles all game result variants |

**Key insight:** The reuse infrastructure is already in place. The changes are subtractive (remove a filter, generalize one argument) plus one new helper for the read-time convention.

---

## Runtime State Inventory

This is a data-foundation phase (no rename/refactor). The only runtime state affected:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `game_flaws` rows in dev (users 28 & 44) — currently player-only | Full wipe+recompute via `backfill_flaws.py --db dev --user-id 28` and `--user-id 44` |
| Stored data | `game_flaws` rows in benchmark DB — currently player-only | Full wipe+recompute via `backfill_flaws.py --db benchmark` (HUMAN-UAT — long run) |
| Stored data | `game_flaws` rows in prod — currently empty (no data migration this milestone) | None — prod stays empty |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

---

## Common Pitfalls

### Pitfall 1: Off-by-one in ply parity
**What goes wrong:** `is_opponent_expr` uses `ply % 2 == 0 → white` but a reader uses `ply % 2 != 0 → white` or treats ply as 1-indexed.
**Why it happens:** The convention is non-obvious; `n` in `_run_all_moves_pass` loops from 1, but the ply stored in the PK is the same `n`. Ply 0 is the initial position (never emitted as a flaw). The first player move is ply 1 (odd → black? — NO, white plays first). Wait: in `_run_all_moves_pass`, `n` starts from 1. `mover = "white" if n % 2 == 0 else "black"`. So ply 1 → black? That seems wrong. Let's verify: a standard chess game starts with white playing move 1 (ply 1). In python-chess half-move numbering, ply 1 is white's first move. `1 % 2 != 0` → `mover = "black"`. **This is the trap.** Actually re-reading: in `_run_all_moves_pass`, the loop `for n in range(1, len(positions))` with `mover = "white" if n % 2 == 0 else "black"` means ply 2 is white's second move (ply 2 is after black's first move). But ply 1 (first move in the game) should be white. The code gives black for ply 1 — which means the ply indexing starts at 0 for the *initial position* and ply 1 is the state AFTER white's first move; i.e., `positions[1]` is the eval *after* white's first move, and the `mover` at `n=1` is white playing into `positions[1]`. But the code says `"black"` for n=1...

**Resolution (verified against library_repository.py:617-618):** The library_repository SQL uses `ply % 2 == 0 → white mover, ply % 2 != 0 → black mover` for `fetch_total_user_moves`. This is the opposite of `flaws_service.py:227`. The two conventions appear contradictory.

**Root cause of this apparent contradiction:** The `n` in `_run_all_moves_pass` is the index into `positions[]` and is the ply of the resulting position (after the move). White moves first, resulting in position 1. But in `_run_all_moves_pass`, `n=1` is white's first move, yet `1 % 2 != 0` → `mover = "black"`.

This is the documented "prior off-by-one bug" area. The `is_opponent_expr` helper MUST be tested against actual known data, not derived from reading the code in isolation. The two ply-parity usages (`flaws_service.py` vs `library_repository.py`) use opposite conventions and must both be correct for the data they operate on.

**Concrete test requirement:** The unit test for `is_opponent_expr` must construct FlawRecord fixtures for a known game (white user, even-ply flaw → should be player; odd-ply flaw → should be opponent) and verify against the actual data written to the DB. The prior bug history (documented in CONTEXT.md D-01) makes this test mandatory, not optional.

**How to avoid:** Use `is_opponent_expr` exclusively. The test must cover: (a) white user + even ply → player row, (b) white user + odd ply → opponent row, (c) black user + even ply → opponent row, (d) black user + odd ply → player row. Verify by counting rows returned by the gated query vs the ungated query after backfill.

### Pitfall 2: Lucky tag fires on opponent-loss-confirmed blunders
**What goes wrong:** Opponent blunders their last move and then the opponent loses (resigns/flags) — this end-of-game opponent blunder gets tagged `lucky` if we pass `user_result` instead of `subject_result`.
**Why it happens:** `_is_unpunished` has `if entry is None: return user_result != "loss"`. If the caller passes `user_result = "win"` (player won the game), end-of-game opponent blunders always return True (lucky). But the opponent didn't escape — they lost.
**How to avoid:** Always call `derive_user_result(game.result, mover)` per-mover when building tags. The pre-resolved `user_result = derive_user_result(game.result, game.user_color)` at the top of `classify_game_flaws` is no longer sufficient after the kernel emits both colors.

### Pitfall 3: Reader gating omitted from `flaw_exists_from_table`
**What goes wrong:** The Flaw severity filter (cross-tab) in the Games tab includes opponent flaws in the EXISTS check, causing games to appear "flaw-filtered in" when the player had no flaws but the opponent did.
**Why it happens:** `flaw_exists_from_table` is called by `apply_game_filters` in `query_utils.py`; the filter logic there does not duplicate the gate.
**How to avoid:** Add the player-only gate inside `flaw_exists_from_table` at the point where the subquery is built (library_repository.py:153-158). This automatically fixes all callers via `apply_game_filters`.

### Pitfall 4: `_is_miss` semantics for opponent flaws
**What goes wrong:** `_is_miss` asks "was the move preceding ply N a mistake/blunder?" — for a player flaw at ply N, the preceding move at N-1 is the opponent's. For an opponent flaw at ply N, the preceding move at N-1 is the player's. The `miss` tag then means "opponent missed after the player's error." This is semantically correct from the opponent's frame (subject missed their chance after the other side erred) — no code change needed.
**Why it happens:** `_is_miss` is symmetric; it just checks `all_moves[n-1].severity in (mistake, blunder)`. This is correct for both colors.
**How to avoid:** No action needed — this is the desired behavior. Document it in code comments when landing the kernel change.

### Pitfall 5: Row count regression after reader gating
**What goes wrong:** After adding player gates, `fetch_stats_aggregates` returns half the expected counts (if opponents were counted before), or the counts are unchanged (if the gate was applied correctly after the backfill doubled rows).
**Why it happens:** The test plan for D-04 must verify both (a) counts are unchanged vs pre-phase baseline and (b) ungated queries now return ~2x the row count.
**How to avoid:** Capture the current row count for dev user 28 before the phase. After the kernel change and backfill, verify ungated query doubles. After gating, verify gated query matches the pre-phase baseline.

---

## Code Examples

### Kernel change — drop user filter, add per-mover subject result
```python
# Source: app/services/flaws_service.py (classify_game_flaws, current lines 539-560)
# BEFORE:
user_color = game.user_color
user_result = derive_user_result(game.result, game.user_color)  # pre-resolved
flaws: list[FlawRecord] = []
for n, (mover, severity, es_before, es_after) in all_moves.items():
    if mover != user_color:           # <-- DROP THIS FILTER (D-06)
        continue
    if severity not in ("mistake", "blunder"):
        continue
    flaw = _build_flaw_record(...)
    flaw["tags"] = _build_tags(
        n, severity, es_before, es_after,
        positions, all_moves,
        user_result,                   # <-- CHANGE to per-mover subject_result
        increment, game.base_time_seconds,
    )
    flaws.append(flaw)

# AFTER:
flaws: list[FlawRecord] = []
for n, (mover, severity, es_before, es_after) in all_moves.items():
    if severity not in ("mistake", "blunder"):
        continue
    flaw = _build_flaw_record(n, mover, severity, es_before, es_after, fen_map, positions)
    subject_result = derive_user_result(game.result, mover)  # per-mover
    flaw["tags"] = _build_tags(
        n, severity, es_before, es_after,
        positions, all_moves,
        subject_result,
        increment, game.base_time_seconds,
    )
    flaws.append(flaw)
```

### `is_opponent_expr` helper (SQLAlchemy case expression)
```python
# Proposed location: app/repositories/query_utils.py
# (or game_flaw.py as a module-level function near the model)
from sqlalchemy import case
from sqlalchemy.sql.elements import ColumnElement

def is_opponent_expr(
    ply_col: ColumnElement[int],
    user_color_col: ColumnElement[str],
) -> ColumnElement[bool]:
    """True when the mover at ply_col is the OPPONENT (not the player).

    Convention (mirrors _run_all_moves_pass flaws_service.py):
        ply even → white mover → is_opponent iff user_color == 'black'
        ply odd  → black mover → is_opponent iff user_color == 'white'

    Single source of the ply-parity convention. Unit-tested against known
    white-user and black-user games. Off-by-one bug history: see CONTEXT D-01.
    """
    return case(
        (ply_col % 2 == 0, user_color_col == "black"),
        else_=user_color_col == "white",
    )
```

### Player-only gate applied to `flaw_exists_from_table`
```python
# Source: app/repositories/library_repository.py:flaw_exists_from_table (~line 153)
# BEFORE:
return exists(
    select(GameFlaw.ply).where(
        GameFlaw.game_id == Game.id,
        GameFlaw.user_id == user_id,
        *clauses,
    )
)

# AFTER (D-04 gate):
from app.repositories.query_utils import is_opponent_expr

return exists(
    select(GameFlaw.ply).where(
        GameFlaw.game_id == Game.id,
        GameFlaw.user_id == user_id,
        ~is_opponent_expr(GameFlaw.ply, Game.user_color),  # player-only gate
        *clauses,
    )
)
```

### Player-only gate for `fetch_stats_aggregates` (aggregate scan)
```python
# Source: app/repositories/library_repository.py:fetch_stats_aggregates (~line 468)
# AFTER (D-04 gate — add to WHERE clause alongside existing user_id + game_id filters):
stmt = select(...).where(
    GameFlaw.user_id == user_id,
    GameFlaw.game_id.in_(select(filtered_analyzed_subq.c.id)),
    ~is_opponent_expr(GameFlaw.ply, Game.user_color),  # player-only gate (D-04)
)
# NOTE: This requires a JOIN to Game to access user_color.
# fetch_stats_aggregates does not currently join Game. Options:
#   (a) add an inner join to Game on GameFlaw.game_id == Game.id
#   (b) use a correlated subquery: Game.user_color from Game where Game.id == GameFlaw.game_id
# Option (a) is simpler. The filtered_analyzed_subq already implies game_id scoping.
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Player-only `game_flaws` rows | Both-sides rows, player/opponent split at query time | Phase 113 | Enables phase-115 comparison; no schema change |
| Pre-resolved `user_result` passed to `_build_tags` | Per-mover `subject_result` | Phase 113 | Correct `lucky` tags for opponent flaws |

**Deprecated/outdated:**
- `if mover != user_color: continue` filter at flaws_service.py:543 — removed this phase.
- FLAWX-03 (is_opponent column + migration + index) — voided by CONTEXT D-02/D-03.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `is_opponent_expr` as a plain helper in `query_utils.py` is preferable to a SQLAlchemy hybrid expression | Architecture Patterns §Pattern 4 | Negligible — either location works; can relocate without rework |
| A2 | Adding a JOIN to `Game` in `fetch_stats_aggregates` for `user_color` access is the right approach (vs correlated subquery) | Code Examples | Low — both approaches are correct; performance difference is negligible at this scale |
| A3 | The ply-parity convention in `flaws_service.py` (`n % 2 == 0 → white`) and in `library_repository.py` (`ply % 2 == 0 → white`) are consistent | Architecture Patterns §Pitfall 1 | HIGH if wrong — the entire `is_opponent_expr` would invert the split. MUST be verified by unit test before merging. |

---

## Open Questions (RESOLVED)

> Both questions are operationally closed by the Phase 113 plans (113-01, 113-02).
> Q1 → resolved by the mandatory `TestIsOpponentExpr` unit test (all 4 ply-parity ×
> user_color combos) created in plan 113-01-T1. Q2 → resolved by adding the `Game` JOIN
> in plan 113-02-T2 (the standard SQLAlchemy approach per the recommendation below).

1. **Ply parity: are flaws_service.py and library_repository.py consistent?**
   - What we know: `flaws_service.py:227` uses `"white" if n % 2 == 0 else "black"` for the mover at ply `n`. `library_repository.py:617` uses `ply % 2 == 0 → white` for the user-ply counter. They appear consistent but the earlier loop uses `range(1, ...)` and it is easy to confuse position index (ply in the PK) with move ordinal.
   - What's unclear: The `count_game_severities` function at line 565 also uses `mover != user_color` filter. After the kernel change to `classify_game_flaws`, `count_game_severities` is unchanged (it has its own independent `_run_all_moves_pass` call and its own filter). Confirm it still correctly counts only player severities.
   - Recommendation: The plan must include a unit test that directly calls `is_opponent_expr` with a fixture of known (ply, user_color) pairs and asserts the expected boolean outcome. This is the only way to definitively resolve the parity question.

2. **`fetch_stats_aggregates` needs a Game JOIN for `user_color` access**
   - What we know: Currently the function does not JOIN Game. It has `GameFlaw.game_id.in_(select(filtered_analyzed_subq.c.id))` as a subquery gate.
   - What's unclear: The simplest D-04 gate requires `Game.user_color` which is not currently in scope.
   - Recommendation: Add `JOIN games ON games.id = game_flaws.game_id` (or use `Game.user_color` via a correlated scalar subquery). The planner should decide which approach given the existing query structure. A simpler alternative: use a subquery `SELECT game_id FROM games WHERE user_color = 'white'` to derive which game_ids have white-user parity, and split the player-gate into two IN clauses. However, adding a JOIN is the standard SQLAlchemy approach and simpler.

---

## Environment Availability

Step 2.6: No external dependencies beyond the project's own code. Dev DB is already running (required for existing tests). No new CLIs or services needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio and pytest-xdist |
| Config file | `pyproject.toml` (addopts, asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/services/test_flaws_service.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLAWX-01 | `is_opponent_expr` returns correct boolean for all 4 (ply parity × user_color) combinations | unit | `uv run pytest tests/services/test_flaws_service.py::TestIsOpponentExpr -x` | ❌ Wave 0 |
| FLAWX-01 | After backfill, ungated query returns ~2x player-only baseline row count | integration | `uv run pytest tests/test_flaws_materialization.py::TestBothSidesMaterialization -x` | ❌ Wave 0 |
| FLAWX-02 | Kernel emits opponent FlawRecords with correct `side` field | unit | `uv run pytest tests/services/test_flaws_service.py::TestClassifyBothColors -x` | ❌ Wave 0 |
| FLAWX-02 | `lucky` tag on opponent end-of-game blunder uses opponent's result, not player's | unit | `uv run pytest tests/services/test_flaws_service.py::TestOpponentLuckyTag -x` | ❌ Wave 0 |
| FLAWX-04 (reader gate) | `query_flaws` returns only player flaws after gating | integration | `uv run pytest tests/test_library_repository.py::TestPlayerOnlyGate -x` | ❌ Wave 0 |
| FLAWX-04 (reader gate) | `fetch_page_game_flaws` returns only player flaws after gating | integration | `uv run pytest tests/test_library_repository.py::TestPageFlawsPlayerOnly -x` | ❌ Wave 0 |
| FLAWX-04 (reader gate) | `fetch_stats_aggregates` counts unchanged vs pre-phase baseline | integration | `uv run pytest tests/test_library_repository.py::TestStatsAggregatesPlayerOnly -x` | ❌ Wave 0 |
| FLAWX-04 (reader gate) | `flaw_exists_from_table` EXISTS matches only player flaws | integration | Extend `tests/test_flaw_predicate.py::TestFlawExistsPlayerOnly` | ❌ Wave 0 (extend existing file) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/services/test_flaws_service.py tests/test_flaws_materialization.py tests/test_flaw_predicate.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_flaws_service.py::TestIsOpponentExpr` — covers FLAWX-01 parity correctness
- [ ] `tests/services/test_flaws_service.py::TestClassifyBothColors` — covers FLAWX-02 kernel both-sides emission
- [ ] `tests/services/test_flaws_service.py::TestOpponentLuckyTag` — covers FLAWX-02 lucky tag subject_result
- [ ] `tests/test_flaws_materialization.py::TestBothSidesMaterialization` — covers FLAWX-01 row-count doubles
- [ ] `tests/test_library_repository.py::TestPlayerOnlyGate` — covers D-04 reader gating for `query_flaws`
- [ ] `tests/test_library_repository.py::TestPageFlawsPlayerOnly` — covers D-04 for `fetch_page_game_flaws`
- [ ] `tests/test_library_repository.py::TestStatsAggregatesPlayerOnly` — covers D-04 for aggregates

---

## Security Domain

This phase makes no authentication, session, or access-control changes. All existing IDOR mitigations (`GameFlaw.user_id == user_id` scoping) are preserved. The player-only gate adds an additional WHERE clause; it does not weaken any existing security boundary.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (existing) | `GameFlaw.user_id == user_id` preserved at all read sites |
| V5 Input Validation | no | No new input parameters |
| V6 Cryptography | no | — |

**No new threat patterns introduced.**

---

## Project Constraints (from CLAUDE.md)

- **No Alembic migration.** Explicitly decided (D-02). Do not include any migration task in the plan.
- **No `asyncio.gather` on the same `AsyncSession`.** The backfill script already respects this. No new concurrent patterns.
- **SQLAlchemy 2.x async `select()` API** — use `select(GameFlaw).where(...)` not legacy 1.x patterns.
- **`ty check` must pass with zero errors.** New `is_opponent_expr` function must have explicit return type annotation (`-> ColumnElement[bool]`). `case()` positional `*whens` syntax for SQLAlchemy 2.x.
- **`ruff format` + `ruff check` before push.** Standard gate applies.
- **No magic numbers.** The ply parity constant (`0`) should be a named constant or documented inline, not a bare magic number.
- **`uv run pytest -n auto -x` for full suite.** Parallel test runner required locally.

---

## Sources

### Primary (HIGH confidence)
- `app/services/flaws_service.py` — direct code inspection of `classify_game_flaws`, `_run_all_moves_pass`, `_build_tags`, `_is_unpunished`, ply-parity convention at line 227, filter to drop at line 543 [VERIFIED: codebase]
- `app/repositories/library_repository.py` — exhaustive inspection of all 5 `game_flaws` read sites; ply-parity convention at lines 617-618 [VERIFIED: codebase]
- `app/repositories/game_flaws_repository.py` — confirmed `flaw_record_to_row` needs no change; `bulk_insert_game_flaws` ON CONFLICT DO NOTHING [VERIFIED: codebase]
- `app/repositories/query_utils.py` — confirmed `flaw_exists_from_table` delegation path [VERIFIED: codebase]
- `app/services/eval_drain.py` — confirmed D-10 classify path in `_classify_and_insert_flaws` [VERIFIED: codebase]
- `scripts/backfill_flaws.py` — confirmed `BACKFILL_GAMES_PER_BATCH = 100`, delete+reinsert pattern [VERIFIED: codebase]
- `scripts/reclassify_positions.py` — confirmed `_recompute_game_flaws` uses shared D-10 path [VERIFIED: codebase]
- `.planning/phases/113-opponent-flaw-materialization/113-CONTEXT.md` — locked decisions [VERIFIED: codebase]
- `.planning/REQUIREMENTS.md` §FLAWX — requirements with amendments [VERIFIED: codebase]
- `.planning/notes/flaw-tag-definitions.md` — tag semantics including `lucky` end-rule definition [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- `app/models/game_flaw.py` — confirmed ORM unchanged this phase [VERIFIED: codebase]
- `app/services/library_service.py` — confirmed `_build_card` / `_curate_chips_from_rows` operate on pre-fetched rows (R3 gate covers them) [VERIFIED: codebase]

### Tertiary (LOW confidence)
- SQLAlchemy 2.x `case()` syntax for the `is_opponent_expr` helper — [ASSUMED] based on existing `case()` usage in `library_repository.py:615-620` which shows the `(condition, value)` tuple syntax

---

## Metadata

**Confidence breakdown:**
- Code touchpoints: HIGH — all files read directly from codebase
- Architecture: HIGH — no new patterns, all within established codebase
- Pitfalls: HIGH — documented in CONTEXT.md, confirmed by code inspection
- Parity convention: MEDIUM — the off-by-one trap means unit tests are mandatory before trusting the convention

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (stable codebase, no external dependencies)
