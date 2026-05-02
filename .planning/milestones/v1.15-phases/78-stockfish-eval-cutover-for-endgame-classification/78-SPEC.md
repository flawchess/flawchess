# Phase 78: Stockfish-Eval Cutover for Endgame Classification — Specification

**Created:** 2026-05-02
**Ambiguity score:** 0.09
**Requirements:** 16 locked

## Goal

Replace the material-imbalance + 4-ply persistence proxy used by `app/repositories/endgame_repository.py` for endgame conversion / parity / recovery classification with Stockfish eval at depth 15 stored in the existing `eval_cp` / `eval_mate` columns on `game_positions`. Backfill historical span-entry rows in benchmark and prod, populate them at import time going forward, refactor the three endgame queries to threshold on eval (after a user-color sign flip), and delete the proxy entirely. No fallback, hard cutover.

## Background

Today, conv/parity/recov classification in `app/repositories/endgame_repository.py` lives in three queries (`query_endgame_entry_rows`, `query_endgame_bucket_rows`, `query_endgame_elo_timeline_rows`). Each one uses two signals at the span-entry row of every `(game_id, endgame_class)` group: `material_imbalance` at entry, plus `material_imbalance` at entry + `PERSISTENCE_PLIES = 4` (sourced via `array_agg(material_imbalance ORDER BY ply)[PERSISTENCE_PLIES + 1]` with a contiguity case-expression that rejects spans where the next row is not exactly +4 plies away). Conversion / recovery require `|material_imbalance|` to clear `_MATERIAL_ADVANTAGE_THRESHOLD = 100` (centipawns of material) at both points.

The schema already supports white-perspective Stockfish-style scoring: `game_positions.eval_cp` (Integer) and `game_positions.eval_mate` (SmallInteger) are populated today only from lichess `%eval` PGN annotations in `app/services/zobrist.py:170-220` — about 22% of prod position rows. There is no Stockfish binary in the backend image, no engine wrapper, no backfill tooling, and no import-time evaluator. The index `ix_gp_user_endgame_game` (defined in `app/models/game_position.py:27`) is shaped for the current proxy with `INCLUDE(material_imbalance)` so the queries stay index-only.

The validation report at `reports/conv-recov-validation-2026-05-02.md` (the source signal that opened v1.15) shows the proxy holds at ~81.5% agreement with Stockfish on the populated subset, but misses ~24% of substantive material-edge sequences and underperforms structurally on queen and pawnless classes. Replacing the proxy with engine eval at the span-entry row eliminates the proxy/ground-truth gap by construction (validation post-cutover should measure ~100% agreement on populated rows because both sides of the comparison read the same column).

## Requirements

1. **ENG-01 — Stockfish in backend image, long-lived UCI process**: Stockfish (recent stable, version pinned) is available inside the backend Docker image and runs as a persistent UCI process inside the wrapper, not as a per-call subprocess fork.
   - Current: No Stockfish binary in `deploy/Dockerfile` or any container image; no UCI process exists in the backend
   - Target: Backend Docker image ships a pinned Stockfish; the wrapper holds a long-lived engine handle reused across evaluations
   - Acceptance: `docker compose exec backend stockfish --help` succeeds inside the running backend container; version printed matches the pinned tag in the Dockerfile; profiling the wrapper shows no per-call process spawn (single `pgrep stockfish` count remains stable across evaluations)

2. **ENG-02 — Async-friendly engine wrapper, depth 15, white-perspective**: A thin wrapper module exposes a single async-friendly API for evaluating a `chess.Board` at depth 15 and returns `(eval_cp, eval_mate)` using the same white-perspective sign convention already used by `app/services/zobrist.py:170-220` for the lichess `%eval` ingest path.
   - Current: No engine wrapper module exists in `app/`
   - Target: New module (e.g. `app/services/engine.py`) exposes one entry point `evaluate(board) -> (eval_cp: int | None, eval_mate: int | None)` callable from async contexts; sign convention matches existing column semantics
   - Acceptance: A unit test feeds known mate-in-N and known cp-advantage positions and confirms returned `(eval_cp, eval_mate)` matches expected white-perspective values within depth-15 tolerance; mate positions return `eval_mate` non-NULL with `eval_cp` NULL (or sentinel)

3. **ENG-03 — Single shared wrapper for backfill and import**: Engine lifecycle (startup, hash size, depth) is configured in exactly one place; the backfill script and the import path import the same wrapper.
   - Current: No engine code exists in either path
   - Target: Backfill script and import worker call the wrapper from ENG-02 — neither path duplicates engine setup or option setting
   - Acceptance: `grep -rn "stockfish\|UCI\|setoption" app/ scripts/` shows engine option configuration only inside the wrapper module; both call sites import from there

4. **FILL-01 — Span-entry NULL-eval backfill script with SAN replay**: A backfill script identifies endgame span-entry rows where both `eval_cp` AND `eval_mate` are NULL, replays SAN from the game's `pgn` column up to the span-entry ply, evaluates, and writes back. A "span entry" is `MIN(ply)` of a `(game_id, endgame_class)` group having `count(ply) ≥ ENDGAME_PLY_THRESHOLD`.
   - Current: No backfill script exists
   - Target: New script (under `scripts/`) takes a DB target (benchmark | prod) and walks span-entry rows with `eval_cp IS NULL AND eval_mate IS NULL`, evaluates them at depth 15 via the wrapper, writes `eval_cp` / `eval_mate` back
   - Acceptance: Running the script against a tiny seeded benchmark subset populates `eval_cp` or `eval_mate` for every targeted span-entry row; a dry-run mode lists the row count without writing

5. **FILL-02 — Idempotent, resumable**: The script is idempotent (rerunning it does not re-evaluate already-populated rows) and resumable (interruption mid-run does not require restart from scratch). Idempotency is row-level: skip rows where `eval_cp` OR `eval_mate` is already non-NULL. No cross-row dedup — endgame span-entry positions are effectively unique across games, so cross-row cache lookup would cost more than re-evaluating the astronomically rare collision.
   - Current: No backfill semantics exist
   - Target: Re-running the script over an already-completed dataset performs zero engine calls; mid-run kill leaves committed work intact and skips it on resume
   - Acceptance: A test seeded with N span-entry rows produces N engine calls; a second run produces zero engine calls; killing the script after batch K and rerunning resumes from row K+1 without re-evaluating rows ≤ K

6. **FILL-03 — Benchmark first, prod second, operator-gated**: The script runs against the benchmark database to completion and the operator validates the result before running it against prod.
   - Current: No procedure exists
   - Target: Documented and enforced run order — benchmark backfill, then VAL-01 re-run + operator sign-off, then prod backfill
   - Acceptance: Phase plan(s) sequence the two backfill runs with VAL-01 as a hard gate between them; runbook (or task list) explicitly requires operator sign-off

7. **FILL-04 — Prod span-entry rows fully populated**: After the prod backfill completes, every endgame span-entry row in prod has either `eval_cp` or `eval_mate` populated; pre-existing lichess `%eval` annotations are trusted and never overwritten.
   - Current: ~22% of prod position rows have any eval (lichess subset only); span-entry coverage on prod is partial
   - Target: 100% of prod endgame span-entry rows have non-NULL `eval_cp` or non-NULL `eval_mate`; all rows that already had a lichess eval keep their original value byte-for-byte
   - Acceptance: Post-backfill SQL — `SELECT COUNT(*) FROM game_positions gp WHERE gp.endgame_class IS NOT NULL AND <span-entry condition> AND gp.eval_cp IS NULL AND gp.eval_mate IS NULL` returns 0 on prod; spot check of pre-existing lichess-evaluated rows confirms unchanged values

8. **IMP-01 — Import-time evaluation of new span entries**: When a game is imported, after endgame classification has marked positions with `endgame_class`, the import worker evaluates each per-class span-entry position and writes `eval_cp` / `eval_mate` to those rows where the lichess `%eval` annotation did not already populate them.
   - Current: Import path in `app/services/zobrist.py` writes `eval_cp` / `eval_mate` only from lichess `%eval`; no engine call
   - Target: Import path adds an evaluation step on per-class span-entry rows that are still NULL after lichess parse; engine path is skipped when lichess already set the value
   - Acceptance: Importing a chess.com game (no lichess `%eval`) populates eval on its endgame span entries; importing a lichess game with `%eval` annotations leaves those evals byte-for-byte unchanged; importing a Standard game with no endgame produces zero engine calls

9. **IMP-02 — Sub-1s eval budget per typical game**: Import-time evaluation does not block other imports for an unbounded duration. Typical games (1-3 span entries × ~70 ms at depth 15) add well under 1 second per game to the import path.
   - Current: Import path performs zero engine evaluations
   - Target: 1-3 span-entry evals at depth 15 add p50 < 1 second to the import path of a typical game; long games with many class transitions remain bounded
   - Acceptance: Timing instrumentation around the new eval step shows median wall-clock added ≤ 1 second per game on a representative sample (e.g. 100 imported games); the import path remains async-friendly (no event-loop blocking beyond the engine wait itself)

10. **REFAC-01 — Endgame queries threshold on eval, not material**: `query_endgame_entry_rows`, `query_endgame_bucket_rows`, and `query_endgame_elo_timeline_rows` in `app/repositories/endgame_repository.py` are rewritten to read `eval_cp` / `eval_mate` at the span-entry row and threshold from there. No contiguity-checked persistence lookup at entry + 4 plies remains in any of the three queries.
    - Current: All three queries threshold on `material_imbalance` at entry plus a `array_agg(... ORDER BY ply)[PERSISTENCE_PLIES + 1]` lookup with a contiguity case-expression
    - Target: Each query reads `eval_cp` and `eval_mate` at the span-entry ply (`MIN(ply)` of the class group with `count(ply) ≥ ENDGAME_PLY_THRESHOLD`) and classifies from there
    - Acceptance: `grep -n "PERSISTENCE_PLIES\|array_agg.*ply.*PERSISTENCE\|imbalance_after\|material_imbalance" app/repositories/endgame_repository.py` returns zero matches; the three queries' result schemas surface eval-derived classification rather than `(user_material_imbalance, user_material_imbalance_after)` tuples

11. **REFAC-02 — Color-sign flip + ±100 cp + mate rule**: Conversion / parity / recovery follows the rule "apply user-color sign flip first, then `(eval_mate > 0) OR (eval_cp ≥ 100) → conversion`; `(eval_mate < 0) OR (eval_cp ≤ -100) → recovery`; otherwise parity". Mate scores at any non-zero value count as max conversion / recovery (no |mate| threshold).
    - Current: The proxy uses sign-flipped `material_imbalance` and a `_MATERIAL_ADVANTAGE_THRESHOLD = 100` (centipawns of material, not eval)
    - Target: Same `100` threshold but applied to `eval_cp` after color flip; mate handling lifts above the threshold check
    - Acceptance: Unit tests over a small fixture exercise: white-positive cp ≥ 100 → conversion; black-positive cp ≥ 100 with `user_color = black` → conversion; mate-for-user → conversion; |cp| < 100 and no mate → parity; mirror cases for recovery

12. **REFAC-03 — Proxy constants and patterns deleted**: `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, the `array_agg(... ORDER BY ply)[PERSISTENCE_PLIES + 1]` patterns, and the contiguity case-expression are deleted from the codebase. No dead code, no fallback path, no feature flag.
    - Current: All four constructs live in `app/repositories/endgame_repository.py`; `_MATERIAL_ADVANTAGE_THRESHOLD = 100` and `PERSISTENCE_PLIES = 4` defined near the top of the module
    - Target: All four are removed; `material_imbalance` references on the conv/recov path are gone (the column itself stays — see REFAC-05)
    - Acceptance: `grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD\|PERSISTENCE_PLIES" app/ scripts/ tests/` returns no matches; `grep -n "imbalance_after\|aggregate_order_by.*PERSISTENCE" app/repositories/endgame_repository.py` returns no matches

13. **REFAC-04 — `ix_gp_user_endgame_game` migrated for index-only on eval columns**: Index `ix_gp_user_endgame_game` (defined in `app/models/game_position.py:27`) is updated via Alembic migration so the rewritten queries stay index-only — `INCLUDE` columns reflect what the new queries actually read (eval columns rather than material columns).
    - Current: `INCLUDE(material_imbalance)` on `ix_gp_user_endgame_game` enables index-only scans for the current queries (see comments at `app/repositories/endgame_repository.py:177` and `:302`)
    - Target: Alembic migration drops the old `INCLUDE` shape and recreates the index with `INCLUDE` columns matching the new queries' projections
    - Acceptance: A new revision exists under `alembic/versions/` that drops + recreates the index; `EXPLAIN (ANALYZE, BUFFERS)` of the rewritten queries on a non-trivial dataset shows "Index Only Scan" using `ix_gp_user_endgame_game` with `Heap Fetches: 0` (or near-zero)

14. **REFAC-05 — `material_imbalance` column retained**: The `material_imbalance` column on `game_positions` is preserved — it has independent uses outside the conv/recov classification path and must not be dropped.
    - Current: Column exists and is populated at import time
    - Target: Column still exists, still populated; only the conv/recov path stops reading it
    - Acceptance: `material_imbalance` is not referenced by the three endgame queries after the refactor; the column itself remains in `app/models/game_position.py` and is still set during import

15. **VAL-01 — `/conv-recov-validation` re-run shows ~100% agreement**: After the benchmark backfill, the `/conv-recov-validation` skill is re-run against the benchmark DB and the report shows ~100% agreement on the populated subset by construction.
    - Current: `reports/conv-recov-validation-2026-05-02.md` shows ~81.5% agreement on the lichess-only populated subset (~22% of positions)
    - Target: Post-backfill report (e.g. `reports/conv-recov-validation-2026-05-XX.md`) shows ~100% agreement on the populated subset because proxy and ground truth now both derive from the same `eval_cp` / `eval_mate` columns
    - Acceptance: The new report file exists, covers the populated subset, and reports agreement ≥ 99% on whole-game endgame metrics; the small residual (≤ 1%) is explainable by per-endgame-class span boundaries (acceptable noise)

16. **VAL-02 — Live-UI gauge smoke check on representative users**: Headline endgame gauges on the live UI for representative test users do not shift by more than expected for any `(rating, TC)` cell — operator-level smoke check, not a hard numeric threshold (the new classification is more accurate, so some shifts are expected and welcome).
    - Current: Live UI gauges read the proxy via the three endgame queries
    - Target: After REFAC-01..05 ship, gauges read eval-based classification; visible shifts are bounded to "expected accuracy improvement" with no obvious regressions or bugs
    - Acceptance: Operator inspects 3-5 representative test user accounts (covering different ratings + TCs) on the staged Endgames page and confirms gauges look sensible — no zero/null gauges on populated users, no nonsense spikes, no silent breakage of the page

## Boundaries

**In scope:**
- Stockfish binary baked into the backend Docker image (pinned version)
- Async-friendly engine wrapper module under `app/` exposing a single depth-15 evaluation API
- Backfill script under `scripts/` for span-entry NULL-eval rows (benchmark first, then prod)
- Import-path integration that evaluates new span entries when lichess `%eval` did not already populate them
- Refactor of the three endgame repository queries to threshold on `eval_cp` / `eval_mate` instead of the material proxy
- Deletion of `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, and the contiguity / persistence patterns from the codebase
- Alembic migration that reshapes `ix_gp_user_endgame_game` to keep the rewritten queries index-only
- Post-backfill `/conv-recov-validation` re-run on benchmark + operator UI smoke check on prod

**Out of scope:**
- Re-evaluating positions that already have a lichess `%eval` annotation — validation report shows lichess evals are accurate enough; re-evaluating burns CPU for no agreement gain. Trust them.
- Adding new columns to `game_positions` — `eval_cp` and `eval_mate` already exist; no schema growth needed. Span entries are derivable from `endgame_class` + `ply` aggregation.
- Tuning the ±100 cp threshold or experimenting with per-class thresholds — with engine eval as ground truth those classes are now classified directly. Per-class threshold tuning is deferred.
- Removing or deprecating the `material_imbalance` column — it has other consumers and may inform future positional features. Decoupled but kept.
- Eval coverage outside endgame span entries — opening / middlegame positions are not part of this milestone. Only `(game_id, endgame_class)` span-entry rows are filled.
- Tactical filters or per-ply eval timeline data — those are part of SEED-010 Library and depend on a different (broader) eval pass, not this targeted backfill.
- Classifier validation replication at 10–100x scale, rating-stratified material-vs-eval offset analysis, parity proxy validation, and `/benchmarks` skill upgrades — all deferred to SEED-002 / SEED-006 (gated on full benchmark ingest).
- A reversible cutover, dual-writing both proxies, or feature-flagging the new classifier — REFAC-03 is explicit: hard cutover, no fallback.

## Constraints

- **Stockfish version pinned in the Docker image.** Floating "latest" is not acceptable; the version is locked alongside the wrapper so eval results are reproducible across deploys and across the backfill / import paths.
- **Long-lived UCI process, not subprocess-per-call.** Forking a process for every evaluation is too slow at backfill scale; the wrapper holds an engine handle.
- **Depth 15 fixed.** No per-call depth tuning, no time-budget mode. Same depth for backfill and import to keep results comparable.
- **White-perspective sign convention preserved.** `eval_cp` / `eval_mate` already follow lichess `%eval` semantics in `app/services/zobrist.py:170-220`; the wrapper must not flip signs at write time. Sign flip happens at read time inside the endgame queries based on `user_color`.
- **Lichess `%eval` values are never overwritten.** Backfill and import paths both check existing values and skip evaluation when set.
- **Backfill idempotency is row-level only.** Skip rows where `eval_cp` OR `eval_mate` is already non-NULL. No cross-row hash dedup — endgame span-entry positions are effectively unique across games and a hash cache lookup costs more than re-evaluating the rare collision.
- **Backfill is benchmark-first.** Operator reruns `/conv-recov-validation` against benchmark and signs off before prod backfill starts.
- **Index-only scans are non-negotiable.** REFAC-04 must keep `EXPLAIN` showing Index Only Scan on the rewritten queries; if the new INCLUDE shape regresses to Heap Fetches, the migration must be revised before merge.
- **Sub-1-second import budget.** IMP-02 sets the budget; if depth-15 wall-clock blows past it on typical games, the wrapper or engine options must be tuned (within the depth-15 constraint above) before merge.
- **No `asyncio.gather` over the same `AsyncSession`** (per CLAUDE.md). The wrapper's async-friendliness is about not blocking the event loop, not about fanning out concurrent DB writes on one session.
- **No `requests` or `berserk`** for any HTTP work the wrapper might want to do (per CLAUDE.md). httpx async only.

## Acceptance Criteria

- [ ] Stockfish (pinned version) is available in the running backend container; `docker compose exec backend stockfish --help` succeeds
- [ ] One engine wrapper module under `app/` exposes a single depth-15 `evaluate(board) -> (eval_cp, eval_mate)` async-friendly API; sign convention matches `app/services/zobrist.py:170-220`
- [ ] Both the backfill script and the import path call the wrapper; engine option configuration appears only inside the wrapper module
- [ ] Backfill script targets endgame span-entry rows with `eval_cp IS NULL AND eval_mate IS NULL`, replays SAN to the entry ply, evaluates, and writes back
- [ ] Backfill script is idempotent (re-run does zero engine calls) and resumable (mid-run kill resumes without redo) — row-level idempotency only, no cross-row hash dedup
- [ ] Backfill ran against benchmark first, operator validated, then ran against prod
- [ ] Post-prod-backfill SQL confirms zero endgame span-entry rows with both `eval_cp` and `eval_mate` NULL
- [ ] Import path evaluates per-class span-entry rows that lichess `%eval` did not populate; lichess values are byte-for-byte unchanged
- [ ] Import-time eval adds median ≤ 1 second per typical game on a representative sample of imports
- [ ] `query_endgame_entry_rows`, `query_endgame_bucket_rows`, and `query_endgame_elo_timeline_rows` threshold on `eval_cp` / `eval_mate` at the span-entry row; no `material_imbalance`, `PERSISTENCE_PLIES`, or contiguity case-expression remain in those queries
- [ ] Conv/parity/recov rule: user-color sign flip first, then `eval_mate != 0 → max conversion/recovery` and `|eval_cp| ≥ 100 → conversion/recovery`, else parity — covered by unit tests
- [ ] `grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD\|PERSISTENCE_PLIES" app/ scripts/ tests/` returns no matches
- [ ] Alembic migration drops + recreates `ix_gp_user_endgame_game` with `INCLUDE` columns matching the rewritten queries; `EXPLAIN (ANALYZE, BUFFERS)` shows Index Only Scan with Heap Fetches near zero
- [ ] `material_imbalance` column on `game_positions` still exists, still populated at import; only the conv/recov path stopped reading it
- [ ] `/conv-recov-validation` post-benchmark-backfill report exists and shows ≥ 99% agreement on the populated subset
- [ ] Operator UI smoke check on 3-5 representative test users post-prod-cutover confirms gauges render sensibly; no nulls/zeros on populated users, no obvious regressions

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                 |
|--------------------|-------|------|--------|-----------------------------------------------------------------------|
| Goal Clarity       | 0.95  | 0.75 | ✓      | Replace proxy with depth-15 Stockfish eval at span entries; hard cutover |
| Boundary Clarity   | 0.92  | 0.70 | ✓      | Out-of-scope is explicit and exhaustive (8 items with rationale)      |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Pinned version, depth 15, sub-1s budget, ±100 cp, lichess-no-overwrite |
| Acceptance Criteria| 0.90  | 0.70 | ✓      | 16 falsifiable requirements + 16 pass/fail acceptance checkboxes      |
| **Ambiguity**      | 0.09  | ≤0.20| ✓      | 1.0 − (0.35×0.95 + 0.25×0.92 + 0.20×0.85 + 0.20×0.90) = 0.0875        |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

`--auto` mode active under continuous-execution policy. ROADMAP entry for Phase 78 and `.planning/REQUIREMENTS.md` (v1.15) already encode 16 falsifiable requirements, 6 success criteria, an explicit out-of-scope list with rationale, and a traceability table. Initial ambiguity assessment based on those artifacts plus codebase scout was 0.09 — well below the 0.20 gate, with all four dimensions already above their minimums. No interview rounds needed.

| Round | Perspective | Question summary | Decision auto-locked |
|-------|-------------|-------------------|----------------------|
| 0     | Researcher (auto) | What exists today vs target state? | `eval_cp`/`eval_mate` columns exist (white-perspective, lichess-only ~22%); proxy lives in `app/repositories/endgame_repository.py` with `_MATERIAL_ADVANTAGE_THRESHOLD = 100` and `PERSISTENCE_PLIES = 4`; `ix_gp_user_endgame_game` shaped for current proxy via `INCLUDE(material_imbalance)`; no Stockfish in image; no engine wrapper |
| 0     | Simplifier (auto) | What's the irreducible core? | Stockfish in image + wrapper + benchmark backfill + import-time eval + endgame query refactor + index migration. All 16 REQs are load-bearing for the cutover. |
| 0     | Boundary Keeper (auto) | What is explicitly NOT in scope? | No re-eval of lichess `%eval` rows; no schema growth; no per-class threshold tuning; no `material_imbalance` column drop; no opening/middlegame eval; no SEED-010 Library work; no feature-flag fallback (hard cutover per REFAC-03) |
| 0     | Failure Analyst (auto) | What invalidates requirements? | (1) Wrapper that forks a subprocess per eval blows the IMP-02 sub-1s budget at scale (mitigated by ENG-01 long-lived UCI). (2) Backfill that overwrites lichess `%eval` corrupts trusted data (mitigated by FILL-04 + IMP-01 NULL-only writes). (3) Index INCLUDE shape that no longer matches projection regresses to Heap Fetches (mitigated by REFAC-04 + EXPLAIN check). (4) Soft cutover with both classifiers live drifts results across deploys (mitigated by REFAC-03 hard delete). |

---

*Phase: 78-stockfish-eval-cutover-for-endgame-classification*
*Spec created: 2026-05-02*
*Next step: /gsd-discuss-phase 78 — implementation decisions (engine wrapper concurrency model, backfill batching, index INCLUDE columns, etc.)*
