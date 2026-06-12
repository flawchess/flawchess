# Phase 113: Opponent-Flaw Materialization - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Persist **both sides'** M+B flaws in `game_flaws` for every analyzed game, so the
flaw-stats surface (phase 115) can contrast the user against their actual opponents.
The single classify kernel (`classify_game_flaws`) is generalized from "user only" to
"both subjects," emitting opponent flaws with **correct subject-relative tags** at zero
added engine cost (the all-moves pass already evaluates both colors). The player/opponent
distinction is recovered **at read time** from ply parity + `games.user_color` — there is
**no new column, no new index, and no Alembic migration** this phase.

Backfill repopulates dev (users 28 & 44) + the benchmark cohort in one idempotent
wipe+recompute pass; prod `game_flaws` ships empty as before.

**This phase is data-foundation only.** The benchmark delta-zone computation is phase 114;
the comparison endpoint + bullet-grid UI is phase 115.
</domain>

<decisions>
## Implementation Decisions

### `is_opponent` representation — DERIVE, do not materialize (amends FLAWX-01, voids FLAWX-03)
- **D-01:** Do **not** add an `is_opponent` column to `game_flaws`. The player/opponent
  split is recovered at query time via a single repository helper,
  `is_opponent_expr(ply, games.user_color)`, encoding `mover = white if ply % 2 == 0 else black`
  and `is_opponent = (mover != user_color)`.
  - **Rationale (the deciding analysis):** the indexing benefit of a stored column is
    **nil** — `is_opponent` is ~50% selective (half the flaws are the opponent's), so Postgres
    won't use a standalone index on it, and in phase 115 it is a `GROUP BY` dimension, not a
    selective filter. Phase 115's comparison query **always** joins `games` (to apply the
    TC/platform/rated/recency filters), so `games.user_color` is free; `ply` is already in
    the PK `(user_id, game_id, ply)`. A Postgres generated column is **not** an option (it would
    need `games.user_color`, a different table). With no performance upside, the leaner schema
    wins.
  - **Why a single helper (not inline parity math):** the ply→color convention is
    non-obvious (this code area has a documented prior off-by-one bug; the two kernel helpers
    use `n` with subtly different meanings). One tested `is_opponent_expr` keeps that fragile
    convention in exactly one place; scattering `ply % 2 ↔ user_color` across query sites
    re-introduces the off-by-one trap.
- **D-02:** **No Alembic migration this phase.** Opponent flaws are additional rows in the
  *existing* columns at the opponent's plies; the PK `(user_id, game_id, ply)` never collides
  (a ply is either a player or opponent move, never both). FLAWX-03 ("migration adds
  `is_opponent` with index support") is **voided** — flag for the planner and update
  REQUIREMENTS.md traceability.
- **D-03:** **No new index.** Existing PK `(user_id, game_id, ply)` covers per-game two-sided
  reads; existing `ix_game_flaws_user_severity (user_id, severity)` covers severity scans.
  `is_opponent` at 50% selectivity earns no dedicated index.

### Existing-reader gating — mandatory correctness scope (new, not in original requirements)
- **D-04:** After this phase the table contains **both sides**, so every existing reader that
  today assumes player-only rows MUST be retrofitted with a player-only gate
  (`is_opponent_expr(...) == False`), or opponent flaws leak into the current self-only Library
  UI (inflated Games-tab counts, opponent blunders in the Flaws list, wrong `FlawStatsPanel`).
  Consumers to gate (audit for completeness during planning):
  - `app/repositories/query_utils.py` — the cross-tab Flaw-filter `EXISTS` subquery
  - `app/repositories/library_repository.py` — `query_flaws` (Flaws-subtab list), the flaw-stats
    aggregate scan, the per-game ply subquery, tag reconstruction
  - Any other `select(GameFlaw…)` / `game_flaws` read found in the planning audit.
  - **Not affected:** `count_game_severities` (Games-card B/M/I) reads `game_positions`, not
    `game_flaws`, and keeps its own `mover != user_color` filter — no regression there.

### Opponent tag fidelity — full subject-relative (recommended default, not contested)
- **D-05:** Opponent flaws carry the **full** subject-relative tag set (severity, phase, tempo,
  miss, lucky, reversed, squandered), computed from the **opponent's** frame. This is nearly
  free because `_run_all_moves_pass` already computes `es_before/es_after` **per-mover**
  (`_ply_to_es(positions[n-1], mover)`), so severity and impact (`_classify_impact`) are already
  correct for both colors; `_is_miss` is ply-adjacency (side-symmetric); phase is position-based.
  The **only** user-centric coupling is `_is_unpunished` (the `lucky` end-of-game rule), which
  reads `user_result` — generalize by passing the **per-mover** subject result:
  `derive_user_result(game.result, mover)` (helper already imported in `flaws_service.py`).

### Classify-kernel shape — single path returns both sides (recommended default, not contested)
- **D-06:** Keep ONE kernel: `classify_game_flaws` drops the `mover != user_color` filter
  (flaws_service.py:543) and emits FlawRecords for **all** movers, each computed with its own
  subject result. `FlawRecord` already carries `side`; `flaw_record_to_row` needs **no change**
  (it maps any FlawRecord to a row, and we persist no side/is_opponent column per D-01). This
  preserves the D-10 single-classify-path invariant — the import hook (`eval_drain.py`),
  `reclassify_positions.py`, and `backfill_flaws.py` all keep calling the same kernel and write
  both sides automatically.

### Backfill — wipe+recompute, dev + benchmark, in this phase
- **D-07:** Run a **full per-game wipe+recompute** (the existing `delete_flaws_for_game` wipes
  the whole game's rows, `bulk_insert_game_flaws` with `ON CONFLICT DO NOTHING` reinserts — already
  idempotent and batched at `BACKFILL_GAMES_PER_BATCH = 100`). No additive opponent-only insert.
- **D-08:** Scope: **dev users 28 & 44** AND the **benchmark cohort**, both in phase 113.
  The benchmark `game_flaws` must be populated before phase 114 reads it. Prod stays **empty**
  (no migration data-backfill, FLAWX-04). Row volume per game roughly doubles (~2–10 vs ~1–5) —
  still tiny, OOM-safe.
- **D-09:** The kernel change makes `backfill_flaws.py` write both sides with no code change
  beyond the kernel itself. The **dev** run is a normal execution/UAT step; the **benchmark**
  run is a longer **HUMAN-UAT** step (flag for the executor — do not gate phase completion on an
  unattended long run).

### Claude's Discretion
- Exact form/location of `is_opponent_expr` (SQLAlchemy hybrid expression vs a `query_utils`
  helper function) — planner/executor's call, as long as it is the single source of the parity
  convention and is unit-tested against known white/black-user games.
- Whether to also expose a `player_only()` / `opponent_only()` convenience wrapper around the
  expr for the readers in D-04.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source (locked)
- `.planning/seeds/SEED-040-flaw-stats-opponent-comparison.md` — the milestone's locked design
  decisions table; §"Recommended milestone phase breakdown" item 1 is this phase. Note: SEED-040
  assumes an `is_opponent` column; **this CONTEXT overrides that to a query-time derivation** (D-01).
- `.planning/REQUIREMENTS.md` §"Opponent-Flaw Materialization (FLAWX)" — FLAWX-01..04, with the
  amendments noted in D-01/D-02/D-03 (column + migration + index dropped; FLAWX-02/04 stand).

### Taxonomy / tag semantics
- `.planning/notes/flaw-tag-definitions.md` — flaw-tag definitions incl. the impact (`reversed`/
  `squandered`) thresholds recalibrated 2026-06-09 for this comparison.
- `.planning/notes/flaw-tag-naming.md` — tag naming.

### Code touchpoints (read before changing)
- `app/services/flaws_service.py` — `classify_game_flaws` (kernel, drop filter @543),
  `_run_all_moves_pass` (already mover-relative ES), `_build_tags`, `_is_unpunished` (the lucky
  end-rule needing per-mover `subject_result`), `derive_user_result` (imported).
- `app/repositories/game_flaws_repository.py` — `flaw_record_to_row` (no change needed),
  `bulk_insert_game_flaws`, `delete_flaws_for_game`.
- `app/repositories/library_repository.py` + `app/repositories/query_utils.py` — the readers to
  gate player-only (D-04).
- `app/services/eval_drain.py` — import-hook classify path (D-10 invariant).
- `scripts/backfill_flaws.py`, `scripts/reclassify_positions.py` — the other two classify paths.
- `app/models/game_flaw.py` — `GameFlaw` ORM (unchanged this phase — no column added).

### Prior-phase decisions to preserve
- D-03 (inaccuracies never stored in `game_flaws`), D-10 (single classify path) — from v1.24
  Phase 108; documented in `app/repositories/game_flaws_repository.py` and `app/models/game_flaw.py`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_run_all_moves_pass` already classifies **both** colors with per-mover ES — opponent severity
  + impact tags are already correct without inversion. The "nearly free" claim holds for tagging,
  not just engine cost.
- `derive_user_result(result, color)` (`openings_service.py`) — call per-mover to get the
  subject's result for the `lucky` end-rule.
- `delete_flaws_for_game` + `bulk_insert_game_flaws` (idempotent, user+game-scoped) — backfill
  recompute primitives already exist; no new write code needed.

### Established Patterns
- D-10 single classify path: all three writers call `classify_game_flaws` + `flaw_record_to_row`.
  The kernel change propagates to all three automatically.
- PK `(user_id, game_id, ply)` is the per-side disambiguator (no collision between player and
  opponent plies) — why no schema change is needed.

### Integration Points
- Phase 114 consumes the benchmark `game_flaws` populated here → benchmark backfill (D-08) is the
  hand-off.
- Phase 115's comparison query reuses `is_opponent_expr` (D-01) and the gated readers (D-04).
</code_context>

<specifics>
## Specific Ideas

- User explicitly challenged the `is_opponent` column and chose the derive-via-helper path on the
  basis that it gives no indexing benefit (the leaner-schema instinct was correct; the only real
  argument for materializing was maintainability, which the single tested helper also satisfies).
- Decision rule stated by the user: "if we benefit from `is_opponent` via indexing, materialize it;
  otherwise derive it." The benchmark analysis showed no indexing benefit → derive.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Tactic-motif bullets (SEED-039) and eval-coverage
raising (SEED-012) are already tracked as v2/other-seed scope in REQUIREMENTS.md and SEED-040.
</deferred>

---

*Phase: 113-opponent-flaw-materialization*
*Context gathered: 2026-06-10*
