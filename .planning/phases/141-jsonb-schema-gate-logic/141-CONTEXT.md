# Phase 141: JSONB Schema + Gate Logic - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the **storage substrate** and the **pure forcing-line gate module** for the v1.30
Forcing-Line Tactic Gate — independently testable with no engine and no DB:

1. Two nullable JSONB columns `allowed_pv_lines` / `missed_pv_lines` on `game_flaws`, added via
   one Alembic migration. (STORE-01)
2. A query-site regression guarantee so the new blob columns never leak into existing stats
   scans (`mistake-stats`, `flaw-comparison`, benchmark-delta). (STORE-02)
3. A new pure-math module `app/services/forcing_line_gate.py` exporting
   `apply_forcing_line_filter()` (and helpers) with every threshold as a named constant,
   reusing `eval_utils.LICHESS_K`. (GATE-01)
4. The gate's rejection filters: only-move win-prob margin, already-winning reject,
   still-winning floor, trailing-only-move strip, one-mover discard — all unit-tested. (GATE-02)

**In scope:** the migration, the ORM column declarations, the audit/regression guard, the pure
gate module + its unit tests.

**Out of scope (later phases):** the MultiPV=2 engine pass that *fills* the columns (Phase 142),
the offline re-tagger CLI that *calls* the gate against stored blobs (Phase 143), A/B validation
(144), and corpus backfill/rollout (145). `tactic_detector.py` is **not** modified in this
milestone at all.

</domain>

<decisions>
## Implementation Decisions

### Mate handling scope (141 vs 143 boundary)
- **D-01:** The **full mate-priority hierarchy lives in `forcing_line_gate.py` in this phase**,
  not deferred to the Phase 143 re-tagger. The gate's solver-node forced-ness test implements:
  only-best-is-mate → forced; both-mates → shorter-distance-to-mate is forced; mate-in-1 is
  **never** suppressed; otherwise fall through to the win-prob sigmoid margin. Rationale: keep
  all gate math in one independently-unit-testable home; Phase 143 just calls it. Phase 143's
  SC #2 (mate-priority unit tests) is then a *verification* of this module, exercised by the
  re-tagger, not a second implementation. **Note for planner/verifier:** the roadmap lists the
  mate hierarchy under Phase 143's success criteria — that wording stands; the *implementation*
  is pulled forward to 141 and 143 covers it via the re-tagger's tests.

### JSONB leak prevention (STORE-02)
- **D-02:** Use **`deferred=True`** on both JSONB columns at the ORM mapper as the structural
  guarantee — they never load on any `select(GameFlaw)` unless explicitly `undefer()`-ed (the
  re-tagger opts in in Phase 143). This is a single point of control and is future-proof against
  new `select(GameFlaw)` sites, vs hand-rewriting each site to an explicit column projection.
- **D-02a:** **Also audit all 5 existing `select(GameFlaw)` sites** (see code_context) to confirm
  none of them implicitly access the blob attributes. Under SQLAlchemy async, an implicit access
  of a deferred attribute outside an `undefer()` raises `MissingGreenlet` — a desirable fail-loud
  signal, but each site must be confirmed clean so no stats path trips it.
- **D-02b:** **SC-wording nuance:** roadmap SC #4 / STORE-02 say "explicit column projections."
  `deferred=True` achieves the *intent* (blobs never fetched by stats scans) more robustly. The
  verifier should treat STORE-02 as satisfied by `deferred=True` + the site audit, not require a
  literal projection rewrite of every site.
- **D-02c:** Add a regression test asserting a representative stats-style `select(GameFlaw)` does
  **not** emit the blob columns (e.g. assert the loaded entity's deferred attrs are unloaded / no
  blob column in the compiled SQL).

### JSONB blob node coverage
- **D-03:** Store a MultiPV=2 entry at **every node** along each capped PV line (both solver and
  defender plies), per the design note's recommendation — maximum flexibility for the user-28
  experiment and future defender-side rules. Solver-only storage (halves cost) is an explicit
  *later* optimization, not done now. **141 only fixes the blob's index semantics** (entry per
  ply, indexed 0..n along the line); the actual fill is Phase 142.

### Schema shape (carried from the design note — locked, not re-discussed)
- **D-04:** Columns are **inline JSONB on `game_flaws`** (not a `game_flaw_pv_lines` sidecar
  table, not on `game_positions`). Sidecar is the documented fallback only if `game_flaws` later
  needs to stay narrow.
- **D-05:** Per-node blob shape: `{"b": best_cp|null, "bm": best_mate|null, "s": second_cp|null,
  "sm": second_mate|null, "su": "<uci>"}`, **white-perspective cp** (matching the existing
  `eval_cp` convention; the gate converts to side-to-move at read time). `allowed_pv_lines` =
  refutation line (flaw_ply+1 PV); `missed_pv_lines` = best-move line (flaw_ply PV).
- **D-06:** Follow the existing `app/models/llm_log.py` JSONB pattern exactly:
  `from sqlalchemy.dialects.postgresql import JSONB`, `Mapped[list[Any] | None]`, **no**
  `MutableDict`/`MutableList` (write-once blobs), no manual asyncpg codec setup (auto-registered).

### Gate constants (locked starting values — tuned empirically in Phase 144, not here)
- **D-07:** `ONLY_MOVE_WIN_PROB_MARGIN = 0.35` — **starting, tunable** value (lichess-puzzler's
  +0.7 in −1..+1 space = +0.35 in our 0..1 win-prob space). Final value committed in Phase 144
  (VALID-02). The gate credits a motif only when its firing node **and every solver node leading
  to it** pass `p(best) − p(second) > ONLY_MOVE_WIN_PROB_MARGIN`, computed via `eval_utils`
  (`LICHESS_K`). This is a best-vs-second forced-ness test, orthogonal to the 15pp move-severity
  blunder threshold.
- **D-08:** `ALREADY_WINNING_CP_THRESHOLD = 300` — reject if the pre-flaw position was already
  > +300 cp (uses existing `game_positions.eval_cp` at the flaw ply).
- **D-09:** `STILL_WINNING_FLOOR_CP = 200` — stop extending the line when best-move eval drops
  below +200 cp.
- **D-10:** Uniqueness/forced-ness is checked at **solver nodes only**. Defender nodes play the
  engine's single best reply with **no** uniqueness check — a line that branches at a defender
  ply but re-converges to a single forcing continuation is fine; only ambiguity on the
  tactic-delivering (solver) side kills the line. Trailing only-moves are stripped; one-movers
  are discarded.

### Claude's Discretion
- Exact function/type signatures in `forcing_line_gate.py` (`PvNode` TypedDict, helper names like
  `is_solver_node_forced()` / `apply_forcing_line_filter()`), Alembic migration boilerplate, and
  the precise form of the regression test — planner/executor decide within the decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source (the authoritative spec for this milestone)
- `.planning/notes/tactic-forcing-line-gate.md` — root-cause diagnosis, the only-move gate model,
  the JSONB storage rationale, blob shape, constants, and the solver-only-uniqueness rule.
  **The most important ref; respects an AGPL boundary (heuristics/constants/names only — copy NO
  lichess-puzzler source).**
- `.planning/REQUIREMENTS.md` §STORE, §GATE — STORE-01, STORE-02, GATE-01, GATE-02 (this phase's
  requirements) plus the v2/out-of-scope boundaries.
- `.planning/research/SUMMARY.md` — HIGH-confidence corroboration; stack verification (python-chess
  `multipv=2`, SQLAlchemy JSONB, asyncpg codec), pitfall list (Pitfall 6 = JSONB leak), 5-phase chain.
- `.planning/research/STACK.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`
  — deeper detail on the verified API patterns, layering, and risks.
- `.planning/ROADMAP.md` §"Phase 141" — the 4 success criteria this phase is graded on.

### Codebase patterns to follow
- `app/models/llm_log.py` — the existing JSONB column pattern to mirror exactly (D-06).
- `app/services/eval_utils.py` — `LICHESS_K`, `eval_cp_to_expected_score`, `eval_mate_to_expected_score`;
  the gate's win-prob math reuses these (no new sigmoid).
- `app/models/game_flaw.py` — the model the columns are added to; note the existing tactic-family
  columns and the `allowed_*` / `missed_*` orientation convention.

### Related prior tactic work (context, not to modify)
- `app/services/tactic_detector.py::detect_tactic_motif` — the detector the gate pre-filters;
  **not modified** in v1.30.
- `notes/tactic-tagger-cook-alignment.md` — prior AGPL-boundary cook.py alignment (same rule).
- `reports/tactic-tagger/tactic-tagger-2026-06-23.md` — the "perfect on fixtures" report that
  motivated the gate (fixtures can't see the non-forced tail).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/eval_utils.py`: `LICHESS_K` (0.00368208), `eval_cp_to_expected_score()`,
  `eval_mate_to_expected_score()` — the gate's only-move margin and mate handling build on these;
  no new sigmoid or coefficient.
- `app/models/llm_log.py`: working `JSONB` + `Mapped[... | None]` + asyncpg-auto-codec pattern to
  copy for the two new columns.

### Established Patterns
- Foreign-key + CHECK + named-constant DB conventions (CLAUDE.md "Database Design Rules");
  JSONB is the sanctioned choice here per the note (variable-length, Python-read-only, TOASTed
  out-of-line so it won't bloat stats scans).
- `game_flaws` already carries denormalized tactic columns with the `allowed_*` (flaw_ply+1 PV) /
  `missed_*` (flaw_ply PV) orientation — the new blobs follow the same two-orientation split.

### Integration Points
- **5 `select(GameFlaw)` query sites to audit** (D-02a):
  - `app/repositories/library_repository.py:737` — `select(GameFlaw.ply)` (already column-projected; safe)
  - `app/repositories/library_repository.py:1017` — `select(GameFlaw, Game, PositionAt, ...)` (full entity — check)
  - `app/repositories/library_repository.py:1118` — `select(GameFlaw)` (full entity — check)
  - `app/repositories/library_repository.py:1151` — `select(GameFlaw).where(...)` (full entity — check)
  - `app/repositories/library_repository.py:2255` — `select(GameFlaw).where(...)` (full entity — check)
- `app/services/forcing_line_gate.py` is **new** — does not exist yet.
- Migration: standard Alembic autogenerate against the `game_flaws` table; nullable columns, no
  data backfill in this phase.

</code_context>

<specifics>
## Specific Ideas

- The whole point of JSONB-over-Text is that a *future* gate rule can read a *new* blob field with
  **no migration** — preserve that property (the re-tagger in 143/144 iterates margins engine-free).
- The gate must be importable and fully unit-testable with **zero** engine and **zero** DB fixtures
  — this is an explicit success criterion (#2) and the load-bearing property of the whole milestone.

</specifics>

<deferred>
## Deferred Ideas

- **Solver-only blob storage** (halve MultiPV cost) — explicit later optimization once no rule needs
  defender-node data. Not now (D-03).
- **`game_flaw_pv_lines` sidecar table** — fallback if `game_flaws` later needs to stay narrow (D-04).
- **MultiPV=2 engine pass, eval-drain wiring, remote-worker contract** — Phase 142.
- **Offline re-tagger CLI** (`scripts/retag_flaws.py`, `--dry-run`/`--margin`/`--user-id`/`--db`),
  mate-hierarchy *tests*, defender-branch test, idempotency — Phase 143.
- **User-28 A/B validation + final margin commit** — Phase 144.
- **Corpus backfill + prod rollout + chip-count monitoring** — Phase 145.
- **Tablebase (Syzygy) uniqueness as a forcing signal** — v2 (GATEX-04), out of scope.

</deferred>

---

*Phase: 141-jsonb-schema-gate-logic*
*Context gathered: 2026-06-29*
