# Phase 79: Position-phase classifier and middlegame eval — Specification

**Created:** 2026-05-02
**Ambiguity score:** 0.16
**Requirements:** 13 locked

## Goal

Add a per-position `phase` SmallInteger column (0=opening, 1=middlegame, 2=endgame) to `game_positions`, computed by a Python port of the lichess [Divider.scala](https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala) algorithm using the existing `piece_count`, `backrank_sparse`, and `mixedness` inputs. Extend the import path and the Phase 78 backfill script to also evaluate the **middlegame entry** position (first ply where `phase=1`) with Stockfish at depth 15, write the results into the existing `eval_cp` / `eval_mate` columns, and run the combined Phase 78+79 backfill against benchmark first, then prod. Validate parity, merge 78+79 to main, deploy.

## Background

`app/services/position_classifier.py` already computes the three Lichess Divider inputs at import time — `piece_count` (Q+R+B+N for both sides), `backrank_sparse` (< 4 pieces on either back rank), and `mixedness` (0..~400 score). What is missing today is the *classification step* that turns those inputs into a per-position phase label. Endgame is implicitly detected at query time via `piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD = 6` (matches Divider's `isEndGame`); the middlegame predicate (`majorsAndMinors <= 10` OR `backrankSparse` OR `mixedness >= 10`, see Divider.scala) is not encoded anywhere — `phase` does not exist as a column on `game_positions`.

Phase 78 just shipped the Stockfish toolchain end-to-end: pinned binary in the backend Docker image (`deploy/Dockerfile`), `app/services/engine.py` (long-lived UCI process, depth 15, async-friendly), `scripts/backfill_eval.py` (span-entry NULL-eval backfill, row-level idempotent, resumable), and an import-time eval pass in `app/services/import_service.py:528-600` that evaluates per-class endgame span-entry rows. Phase 78's operational rollout — the benchmark + prod backfill and the deploy — was deliberately deferred (see Phase 78 SUMMARY 78-06 and `STATE.md`) so a single combined run can backfill **both** endgame eval entries (Phase 78) and the new middlegame eval entries (this phase) in one pass.

The `eval_cp` (Integer / SmallInteger) and `eval_mate` (SmallInteger) columns on `game_positions` are reused as-is — no new eval columns. Only one new schema column is added: `phase`.

## Requirements

1. **CLASS-01 — Divider port: `isEndGame` and `isMidGame` predicates**: `app/services/position_classifier.py` exposes pure functions that mirror lichess Divider.scala. `is_endgame` returns True iff `piece_count <= 6`; `is_middlegame` returns True iff `piece_count <= 10` OR `backrank_sparse` OR `mixedness >= 10`. `is_endgame` is checked first, so `is_endgame` implies `phase=2` even when `is_middlegame` would also fire.
   - Current: `position_classifier.py` computes the three inputs but does not classify phase
   - Target: Two predicate functions live in the same module, with thresholds named as module constants (`MIDGAME_MAJORS_AND_MINORS_THRESHOLD = 10`, `MIDGAME_MIXEDNESS_THRESHOLD = 10`, plus the existing `ENDGAME_PIECE_COUNT_THRESHOLD = 6`)
   - Acceptance: Unit tests over hand-curated positions (initial position → opening; mid-development with backrank sparse → middlegame; KR vs KR → endgame; KQR vs KQR → endgame because `piece_count = 4 ≤ 6`; KQ vs KQ + 8 pawns each → endgame because `piece_count = 2`) match the expected phase per Divider.scala

2. **CLASS-02 — `classify_position` returns phase**: `PositionClassification` gains a `phase` field of type `Literal[0, 1, 2]` (0=opening, 1=middlegame, 2=endgame). The phase is derived from the existing inputs in the same call — no recomputation, no second board scan.
   - Current: `classify_position` returns the seven existing fields; no phase
   - Target: `classify_position` returns the eight fields (existing seven plus `phase`); the phase is computed inline from the already-derived `piece_count`, `backrank_sparse`, `mixedness`
   - Acceptance: `grep -n "phase" app/services/position_classifier.py` shows the new constant + classification logic; unit test confirms `classify_position(initial_board).phase == 0`; ty check passes with `Literal[0, 1, 2]` annotation

3. **SCHEMA-01 — `phase` SmallInteger column on `game_positions`**: A new nullable `phase` SmallInteger column is added to `game_positions` via Alembic migration. Nullable because existing rows are populated by the backfill, not by the migration itself.
   - Current: `game_positions` has no `phase` column (see `app/models/game_position.py`)
   - Target: New `phase: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` exists on the SQLAlchemy model and on the database; an Alembic revision under `alembic/versions/` adds the column with no default and no backfill embedded in the migration
   - Acceptance: `\d game_positions` in psql shows `phase | smallint | nullable`; the migration is reversible (down-migration drops the column cleanly)

4. **SCHEMA-02 — phase populated at import time**: Every position row inserted by the import path carries a non-NULL `phase` value, taken from `classify_position(board).phase`. Both intermediate plies and the final position get a phase.
   - Current: `app/services/zobrist.py` `PlyData` does not carry phase; `bulk_insert_positions` does not write phase
   - Target: `PlyData` TypedDict gains a `phase: int` key; the bulk-insert payload in `app/services/import_service.py:497-522` includes `phase`; both ply loops in `zobrist.py` (intermediate and final position) populate it
   - Acceptance: Importing a fresh game in dev DB results in 100% non-NULL phase rows for that game; SQL: `SELECT COUNT(*) FROM game_positions WHERE game_id = <new_game> AND phase IS NULL` returns 0

5. **PHASE-IMP-01 — middlegame entry eval at import time**: The Phase 78 import-time eval pass in `app/services/import_service.py:528-600` is extended so that, in addition to evaluating endgame span-entry rows, it also evaluates the **middlegame entry** position — `MIN(ply)` of the rows in that game with `phase = 1`. At most one middlegame entry per game (the first contiguous middlegame stretch's entry; later middlegame stretches after an endgame are not re-evaluated).
   - Current: The import-time eval pass evaluates per-class endgame span entries only
   - Target: The eval pass also evaluates the single first `phase=1` row per game; `eval_cp`/`eval_mate` are written to that row only when neither the lichess `%eval` annotation nor a prior pass already populated them (T-78-17 lichess preservation rule applies unchanged)
   - Acceptance: Importing a chess.com game (no lichess `%eval`) that reaches a middlegame produces exactly one extra engine call beyond the endgame entries; the row at `MIN(ply WHERE phase=1)` has non-NULL `eval_cp` or `eval_mate`; a game that never leaves opening produces zero middlegame engine calls; an imported lichess game whose first `phase=1` row already has `%eval` set is left byte-for-byte unchanged

6. **PHASE-IMP-02 — sub-1s import budget preserved**: Adding the middlegame eval (one extra evaluation per typical game) keeps the import-path median wall-clock added by engine evals under 1 second per game (the Phase 78 IMP-02 budget). At depth 15 ≈ 70 ms per call, a typical game now does 1–4 evals (1 middlegame entry + 0–3 endgame class entries) instead of 0–3.
   - Current: Phase 78 IMP-02 measured at `eval_pass_ms` logged per batch — no hard gate, operator monitors
   - Target: The same `eval_pass_ms` log line covers both endgame and middlegame evals; median per-game eval-pass wall-clock stays ≤ 1 second on a representative sample
   - Acceptance: `eval_pass_ms` instrumentation in `_flush_batch` is unchanged structurally and logs both endgame + middlegame call counts; no new asyncio.gather over the same session is introduced; ty + ruff + pytest still green

7. **PHASE-FILL-01 — backfill script extended for `phase` column**: `scripts/backfill_eval.py` (or a sibling script) populates `phase` for every existing row where `phase IS NULL`, computed from `(piece_count, backrank_sparse, mixedness)` — no PGN replay needed, the inputs are already in the column. This pass is independent from the engine work and runs at SQL/Python speed.
   - Current: `backfill_eval.py` only fills `eval_cp`/`eval_mate` on endgame span entries; no phase backfill exists
   - Target: A new pass (a `--phase-only` mode, or a sequenced step inside the same script) updates rows where `phase IS NULL` to `classify_position(...).phase`-equivalent values derived directly from the stored inputs; idempotent (`WHERE phase IS NULL`), resumable (commit every N rows, same pattern as Phase 78)
   - Acceptance: Running the phase backfill against a seeded subset populates `phase` on every targeted row; a second run is a no-op (zero updates); SQL `SELECT COUNT(*) FROM game_positions WHERE phase IS NULL` returns 0 after a full run on benchmark, and 0 after the same run on prod (FILL-04 analog)

8. **PHASE-FILL-02 — backfill script extended for middlegame entry eval**: `scripts/backfill_eval.py` is extended so that, in addition to the existing endgame span-entry rows, it also enqueues the middlegame entry row per game — `MIN(ply)` of `phase=1` rows within each game, after the phase backfill (PHASE-FILL-01) has populated the column. Same row-level idempotency rule (`eval_cp IS NULL AND eval_mate IS NULL`), same SAN replay via `_board_at_ply`, same engine wrapper.
   - Current: `_build_span_entry_stmt` in `backfill_eval.py:136-231` selects only endgame class span entries
   - Target: The query (or a second query unioned in) also yields one row per game whose `phase=1` MIN-ply row has both eval columns NULL; the eval + write loop handles both row sets uniformly
   - Acceptance: After a full backfill on a seeded benchmark subset, every game with at least one `phase=1` row has either non-NULL eval at its middlegame entry OR a documented skip reason (PGN parse failure, engine timeout — both already logged via Sentry); a re-run produces zero engine calls

9. **PHASE-FILL-03 — combined three-round operational rollout (benchmark → prod → deploy)**: The combined Phase 78 + Phase 79 backfill executes the runbook from `78-06-SUMMARY.md` extended with the phase + middlegame eval steps: Round 1 dev smoke (subset), Round 2 benchmark full + `/conv-recov-validation` re-run as VAL-01 gate, Round 3 prod (via `bin/prod_db_tunnel.sh`). After Round 3 completes successfully, Phase 78 and Phase 79 are merged together to `main` and deployed via `bin/deploy.sh`.
   - Current: Phase 78's benchmark + prod backfill, VAL-01 re-run, deploy, and VAL-02 are all deferred — see `STATE.md` and `78-06-SUMMARY.md`
   - Target: One combined plan executes the full sequence; the Phase 78 deferred items (FILL-03, FILL-04, VAL-01, VAL-02) close out as part of this phase, not separately
   - Acceptance: After Round 3, prod has zero rows with `phase IS NULL`; prod has zero endgame span-entry or middlegame-entry rows with both `eval_cp` AND `eval_mate` NULL (modulo skipped rows logged to Sentry); the combined PR for Phase 78 + Phase 79 is merged and deployed; `bin/deploy.sh` finishes green

10. **PHASE-VAL-01 — Divider parity test fixture**: A unit test fixture verifies the Python port matches lichess Divider.scala on a hand-curated set of ≥ 10 positions covering the three phases and the boundary cases (sparse backrank, mixedness threshold, `piece_count` boundaries at 6 and 10). The fixture lives in `tests/test_position_classifier.py` and is part of the standard test suite.
   - Current: `tests/test_position_classifier.py` covers the three input metrics; no phase classification tests
   - Target: A new test class (e.g. `TestPhaseClassification`) covers the three phase transitions and the boundary conditions; expected values are sourced from the Divider.scala algorithm spec, not from the Python implementation under test
   - Acceptance: At least 10 `assert classify_position(board).phase == <expected>` assertions exist, each against a known-good Divider expected value; the suite runs in `uv run pytest tests/test_position_classifier.py` with zero failures

11. **PHASE-VAL-02 — `/conv-recov-validation` agreement post-combined-backfill**: After Round 2 (benchmark) of the combined backfill completes, the `/conv-recov-validation` skill is re-run against the benchmark DB and reports ≥ 99% agreement on the populated subset (this is the Phase 78 VAL-01 gate, just gated until after Phase 79's middlegame work also lands so a single validation pass covers both).
   - Current: Pre-Phase-78 baseline is ~81.5% agreement on the lichess-only populated subset (`reports/conv-recov-validation-2026-05-02.md`); post-cutover target is ~100% by construction (proxy and ground truth both read `eval_cp` / `eval_mate`)
   - Target: A new report (e.g. `reports/conv-recov-validation-2026-05-XX.md`) shows ≥ 99% whole-game-endgame-metric agreement on the populated subset
   - Acceptance: The new report file exists, covers the populated subset, and reports agreement ≥ 99%; small residual (≤ 1%) is acknowledged as expected per-class span-boundary noise

12. **PHASE-VAL-03 — Live-UI gauge smoke check on prod (Phase 78 VAL-02 closeout)**: After Round 3 (prod) completes and the combined PR is deployed, the operator inspects 3–5 representative test users' Endgames pages and confirms gauges render sensibly. This closes out Phase 78 VAL-02 inside Phase 79's scope, since Phase 79 is what triggers the deploy.
   - Current: Phase 78 VAL-02 deferred — gauges still read the proxy on prod
   - Target: Post-deploy, gauges read eval-based classification (Phase 78 REFAC-01..05 already merged in the combined PR); operator confirms no nulls, no nonsense spikes, no obvious regressions
   - Acceptance: Operator sign-off recorded in the phase SUMMARY; no Sentry crash spike post-deploy; no production rollback within the first 24 hours

13. **PHASE-INV-01 — phase / endgame_class consistency invariant**: Because `is_endgame` is checked first and uses the same `piece_count <= 6` rule that `endgame_class` is keyed on, `phase = 2` ⟺ `endgame_class IS NOT NULL` on every row (modulo malformed positions that should not occur in practice). A SQL invariant check confirms this after the combined backfill on benchmark and on prod.
   - Current: No such invariant exists because `phase` does not exist
   - Target: Post-backfill, the invariant holds across both DBs
   - Acceptance: SQL `SELECT COUNT(*) FROM game_positions WHERE (phase = 2) <> (endgame_class IS NOT NULL)` returns 0 on benchmark after Round 2 and on prod after Round 3

## Boundaries

**In scope:**
- New `phase` SmallInteger column on `game_positions` (Alembic migration)
- Python port of lichess Divider.scala `isEndGame` / `isMidGame` predicates inside `app/services/position_classifier.py`
- `classify_position` returning a `phase: Literal[0, 1, 2]` field (no recomputation of inputs)
- Import-path population of `phase` for every inserted row (intermediate + final)
- Import-time middlegame entry Stockfish eval (one extra engine call per typical game)
- Backfill script extension: phase column population + middlegame entry NULL-eval backfill
- Combined three-round operational rollout (dev smoke → benchmark + VAL-01 → prod) using the Phase 78 runbook
- Combined merge of Phase 78 + Phase 79 PRs to `main` and a single `bin/deploy.sh` deploy
- Closeout of the Phase 78 deferred operational steps (FILL-03, FILL-04, VAL-01, VAL-02) inside this phase
- Divider parity test fixture in `tests/test_position_classifier.py`

**Out of scope:**
- Refactoring endgame repository queries (`query_endgame_entry_rows` etc.) to read `phase` instead of `endgame_class` — endgame analytics keep their existing key. Phase 78 already cut over to eval-based thresholds; this phase does not move endgame analytics again.
- Middlegame conversion / parity / recovery metrics or any new endgame-style aggregations on `phase=1` data — middlegame eval is *captured* in this phase but not yet *displayed* or *aggregated*. UI work and metric design are deferred to a later milestone.
- Frontend display of `phase` in any panel, gauge, chart, or debug view — this phase ships data plumbing only. There is no React work.
- Deprecating or removing `piece_count`, `backrank_sparse`, `mixedness`, `material_count`, `material_signature`, `material_imbalance`, or `endgame_class` — all are kept; the new column joins them.
- Re-evaluating any position that already has a populated `eval_cp` or `eval_mate` (lichess `%eval` preservation rule from Phase 78 IMP-01 / FILL-04 applies unchanged).
- Tuning Divider thresholds (10 / 10 / 6) or experimenting with FlawChess-specific phase boundaries — port the lichess defaults verbatim. Threshold tuning is a separate exercise.
- Eval coverage outside endgame span entries and the single middlegame entry — opening positions and per-ply phase=1 timelines are not part of this milestone.
- Adding new schema columns beyond `phase` — `eval_cp` and `eval_mate` are reused as-is.
- Backfilling middlegame eval for games whose endgame span entries are also missing eval and whose PGN replay fails — same Sentry-log-and-skip behaviour as Phase 78, no per-game retry harness.
- A reversible cutover, dual-writing both classifiers, or feature-flagging the new `phase` column — same hard-cutover stance as Phase 78. The column is added once; consumers either read it or do not.

## Constraints

- **Same Stockfish wrapper, same depth.** Middlegame eval uses `app/services/engine.evaluate(board)` — no new engine wrapper, no per-call depth tuning, no time-budget mode. Depth 15 stays fixed for both endgame and middlegame evals so all eval columns are mutually comparable.
- **White-perspective sign convention preserved** (Phase 78 ENG-02 constraint). The wrapper writes white-perspective values; sign flip happens at read time only.
- **Lichess `%eval` is never overwritten.** Both the import path (PHASE-IMP-01) and the backfill script (PHASE-FILL-02) check existing `eval_cp` / `eval_mate` and skip evaluation when set.
- **Row-level idempotency for the eval backfill.** Same as Phase 78 FILL-02: skip rows where `eval_cp` OR `eval_mate` is non-NULL. No cross-row hash dedup.
- **Row-level idempotency for the phase backfill.** `WHERE phase IS NULL` is the resume / skip predicate. No re-derivation of phase for already-populated rows.
- **Benchmark first, then prod.** Same FILL-03 gating rule: operator runs `/conv-recov-validation` on benchmark and signs off before the prod backfill starts.
- **Sub-1-second import budget preserved.** Adding one middlegame eval per typical game must not push median `eval_pass_ms` above 1 second per game on a representative sample.
- **No `asyncio.gather` over the same `AsyncSession`** (CLAUDE.md). Middlegame eval is sequenced inside the existing eval loop, not parallelised.
- **No new index migrations** unless the middlegame entry query measurably regresses (e.g. seq scan on prod). The expected query is anchored on `(game_id, phase)` which is already indexable via existing indexes plus a small subselect; defer index work unless `EXPLAIN` shows it is needed.
- **`phase` column is `Optional[int]` on the model but treated as non-NULL by all import-path code.** Nullability exists only as a transient state during backfill; PHASE-FILL-01 closes it out before merge.
- **Combined PR.** Phase 78 and Phase 79 ship as one merge to `main` and one deploy. No interim deploy of Phase 78 alone (per `STATE.md` last_activity 2026-05-02).

## Acceptance Criteria

- [ ] `classify_position(initial_board).phase == 0`; the `PositionClassification` dataclass exposes the new `phase: Literal[0, 1, 2]` field
- [ ] `is_endgame` and `is_middlegame` predicates exist in `app/services/position_classifier.py` with named threshold constants matching lichess Divider.scala defaults (10 / 10 / 6)
- [ ] At least 10 hand-curated phase test cases pass in `tests/test_position_classifier.py`, sourced from the Divider.scala algorithm rather than from the implementation under test
- [ ] Alembic migration adds a nullable `phase: SmallInteger` column to `game_positions`; the down-migration drops it cleanly
- [ ] After import of a fresh game in dev DB, every row of that game has non-NULL `phase` (intermediate plies + final position)
- [ ] Phase 78 import-time eval pass is extended so a typical game with a middlegame produces exactly one additional engine call beyond its endgame entries
- [ ] Importing a lichess game whose middlegame-entry row already has `%eval` populated leaves that row byte-for-byte unchanged (T-78-17 invariant preserved)
- [ ] Median per-game eval-pass wall-clock remains ≤ 1 second on a representative sample (IMP-02 budget held)
- [ ] `scripts/backfill_eval.py` populates `phase` for every row where `phase IS NULL`, idempotent and resumable (re-run = zero updates)
- [ ] `scripts/backfill_eval.py` evaluates the middlegame entry row of every game whose `phase=1 MIN-ply` row has both eval columns NULL, idempotent and resumable
- [ ] Combined Phase 78 + Phase 79 backfill runs successfully Round 1 (dev smoke) → Round 2 (benchmark + `/conv-recov-validation` ≥ 99% agreement) → Round 3 (prod) without operator-blocking errors
- [ ] Post-Round-3, prod has zero rows with `phase IS NULL` and zero endgame-span-entry or middlegame-entry rows with both `eval_cp` AND `eval_mate` NULL (modulo logged skips)
- [ ] Invariant `(phase = 2) <=> (endgame_class IS NOT NULL)` holds on benchmark after Round 2 and on prod after Round 3
- [ ] Combined Phase 78 + Phase 79 PR is merged to `main` and deployed via `bin/deploy.sh`; operator UI smoke check on 3–5 representative users post-deploy confirms gauges render sensibly (closes Phase 78 VAL-02)

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                 |
|--------------------|-------|------|--------|-----------------------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Divider port + phase column + middlegame entry eval + combined rollout |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | Out-of-scope is explicit (no UI, no middlegame metrics, no endgame query refactor) |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Same engine, same depth, same idempotency rules, sub-1s budget preserved |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 13 falsifiable requirements + 14 pass/fail acceptance checkboxes      |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      | 1.0 − (0.35×0.88 + 0.25×0.85 + 0.20×0.80 + 0.20×0.80) = 0.1605        |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

`--auto` mode active under continuous-execution policy. ROADMAP entry for Phase 79 plus the Phase 78 SPEC + SUMMARY artifacts encode the goal, the operational pattern (3-round backfill), and the boundary conditions (combined merge + deploy, deferred Phase 78 ops fold in here). Initial ambiguity from ROADMAP alone was ~0.29; one auto-resolved interview pass through all four perspectives raised every dimension above its minimum and the composite below the 0.20 gate. No human interview rounds.

| Round | Perspective       | Question summary                              | Decision auto-locked |
|-------|-------------------|-----------------------------------------------|----------------------|
| 0     | Researcher (auto) | What exists today vs target state?            | `position_classifier.py` already computes Divider's three inputs (`piece_count`, `backrank_sparse`, `mixedness`) — phase classifier just needs a port of `isMidGame`/`isEndGame`. No `phase` column on `game_positions`. Phase 78 just shipped the engine wrapper, backfill script, import-time eval pass, and endgame query refactor — Phase 79 reuses every Phase 78 building block. Phase 78 deferred operational steps (FILL-03, FILL-04, VAL-01, VAL-02, deploy) are explicitly folded into this phase. |
| 0     | Simplifier (auto) | What's the irreducible core?                  | (1) Divider port → `phase` field on `PositionClassification`. (2) `phase` column added via Alembic. (3) Import path writes phase + does one extra middlegame entry eval. (4) Backfill script populates phase column + middlegame entry eval. (5) Combined 3-round rollout closes out Phase 78 + 79 in one deploy. UI work, middlegame metrics, and endgame query refactor are intentionally NOT in the irreducible core. |
| 0     | Boundary Keeper (auto) | What is explicitly NOT in scope?         | No frontend / UI surface for `phase`; no middlegame conv/recov metrics or aggregations; no refactor of endgame repository queries to read `phase` instead of `endgame_class`; no deprecation of `endgame_class` / `piece_count` / `mixedness` / `backrank_sparse`; no new schema columns beyond `phase`; no Divider threshold tuning (port lichess defaults verbatim); no per-ply middlegame eval timeline (only the single MIN-ply entry); no separate Phase 78 deploy ahead of Phase 79. |
| 0     | Failure Analyst (auto) | What invalidates requirements?           | (1) phase / endgame_class divergence (`phase=2` but `endgame_class IS NULL` or vice versa) — mitigated by PHASE-INV-01 SQL invariant + `is_endgame` checked before `is_middlegame`. (2) Middlegame eval blowing the IMP-02 sub-1s budget — mitigated by reusing the shared depth-15 wrapper and one extra eval per game. (3) Phase backfill non-idempotent on resume — mitigated by `WHERE phase IS NULL` predicate + same commit-every-N pattern as Phase 78. (4) Lichess `%eval` overwritten on middlegame rows — mitigated by reusing the existing eval-skip-when-non-NULL guard verbatim. (5) Prod backfill diverging from benchmark — mitigated by the FILL-03 gating rule (benchmark + VAL-01 + operator sign-off before prod). |
| 0     | Seed Closer (auto) | What's the agreement target for VAL-01?  | Re-use Phase 78 VAL-01's ≥ 99% agreement gate against `/conv-recov-validation`. No new agreement metric introduced — the conv/recov validation already measures the only signal that matters end-to-end (the proxy ↔ engine eval agreement). Middlegame eval has no separate validation target because there is no middlegame metric in the UI yet. |
| 0     | Seed Closer (auto) | What is the middlegame "entry"?          | `MIN(ply)` of `phase=1` rows within a game. Exactly one middlegame entry per game (mirrors lichess Divider's `Division(midGame, endGame)` returning a single transition point). Games that never reach middlegame produce zero middlegame engine calls; games that re-enter `phase=1` after a brief endgame are not re-evaluated (intentional simplification, defer if it ever matters). |

---

*Phase: 79-position-phase-classifier-and-middlegame-eval*
*Spec created: 2026-05-02*
*Next step: /gsd-discuss-phase 79 — implementation decisions (e.g. phase backfill SQL strategy, exact middlegame entry query shape, plan ordering vs Phase 78's pending operational steps)*
