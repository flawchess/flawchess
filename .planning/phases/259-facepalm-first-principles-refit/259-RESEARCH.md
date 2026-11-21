# Phase 259: Facepalm Score Refit on First Principles (SEED-261121-tau) - Research

**Researched:** 2026-11-21
**Domain:** Internal codebase: facepalm score inputs (line material rule, stored scalars, Maia best-reply probability), multi-release column swap on a ~7.8M-row table, refit tooling
**Confidence:** HIGH for the codebase inventory and the release mechanics (read this session), MEDIUM for prod run durations (extrapolated from Phase 250/254 runs), LOW for prod facts that need a prod query (open questions)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (not re-discussed)
- The score is a ranking, never presented as a probability or a share of peers (250 D-01). False alarms are worse
  than misses (250 D-03). No engine at scoring time (250 D-06, D-07).
- The score is a SQL expression evaluated at query time, with a Python twin; a coefficient refit or a lambda change
  is a constants deploy with no UPDATE pass over prod (254 D-01). The chip percent and the filter come from the
  same expression (253 D-10). This phase keeps that; only the inputs of the expression change (D-05).
- Fitted values are named constants in `app/services/blunder_check_rules.py`; `--check-constants` reproduces them
  from a committed features TSV (250 D-04). Fit choices are confirmed by the owner, never hand-tuned.
- Label 1 means "the facepalm score should be above 70%" (254 D-23). One label file,
  `reports/blunder-check/facepalm-labels.tsv`.
- `FACEPALM_SCORE_MIN` (drill, 0.50 today) and `FACEPALM_STATS_MIN` (library stats, 0.70) are set by the owner at
  a blocking checkpoint (254 D-13, 257 D-01).
- Drill and library lambda stay 1.0 (254 D-03, D-04). An unknown best line contributes `missed = 0` (254 D-18).
- Facepalm type (allowed loss / missed win) is decided on the same `loss` and `missed` inputs the score reads
  (257 D-02).

#### Owner principle for this phase
- **D-01: First principles decide, the AUC is only a range check.** The owner (2026-11-21) prefers the model shape
  that makes the most sense over a small AUC gain: the labels are few (268 usable rows) and "very subjective".
  A candidate is acceptable when its cross-validated AUC is within about 0.02 of the shipped rule on today's
  lines (0.897 in the spike, D-12). No choice between shapes by AUC differences inside that range.

#### Material rule
- **D-02: Every depth is read at a quiet point.** The balance at depth N is taken after walking the line N plies
  and then on while the next line move is a capture, on any square. A line that stops inside an exchange is
  settled by a static exchange on that square (the opponent's recapture counts against the blunderer, the
  blunderer's for them). This generalises today's "one blunderer recapture at depth + 1". Same-square-only
  extension is ruled out (spike CV AUC 0.883). The other 250 D-02 counting rules stay (captures only, piece values
  1 / 3 / 3 / 5 / 9, the first move's own capture counts for the blunderer, the desperado exclusion, mate rules).
- **D-03: The aggregate stays the decaying mean** over the odd depths 1, 3, 5, 7, 9, for both the loss and the
  missed gain. Reading: the material a player sees when their look-ahead depth varies, shallow looks being
  likelier. It keeps the early-swing signal of rows like `-3, -3, 0`, which the owner labelled fair in Phase 256.
  The "first stable value" is not a candidate, and the input is not chosen by the fit.
- **D-04: The decay ratio stays 1/2, fixed, not fitted** (`MATERIAL_DECAY_RATIO`).

#### Storage
- **D-05: Store `loss` and `missed` as two scalar columns on `game_flaws`, drop the material arrays.** The quiet
  walk and the decaying mean run in Python when the row is written (go-forward hook and backfill). The SQL score
  expression reads the two numbers; it no longer aggregates arrays, so the SQL twins of the aggregation
  (`facepalm_material` SQL builders) go away. Coefficient refits and lambda changes stay constants deploys. A
  change to the material rule itself (the quiet rule, the decay ratio, the caps and floors, the mate values) needs
  a recompute pass that replays the games and stored lines (no engine, no Maia). The owner chose this over
  (a) rule-applied 9-slot arrays, (b) raw per-ply arrays with the rule in SQL, (c) raw plus rule-applied arrays,
  and (d) a stored final score.
  — **Reversibility:** one-way — dropping `played_line_material` and `best_line_material` needs an Alembic
  migration, and the arrays can only be rebuilt by a prod pass over about 4.4M rows.
- **D-06: The drop is the last, human-gated step,** as 254 D-02 was: once no reader of the arrays is left in app,
  scripts or tests and prod is checked.
  — **Reversibility:** one-way — same migration as D-05.
- The mate ply columns (`line_mate_ply`, `best_line_mate_ply`) and the Maia columns (`maia_played_prob`,
  `maia_best_prob`, `maia_reply_spread`, `maia_pre_spread`) stay stored. Whether the mate plies are still needed
  once mates are folded into `loss` and `missed` is for the planner (Claude's Discretion).

#### Best-reply probability
- **D-07: A new stored column** (working name `maia_best_reply_prob`): Maia's probability of the engine's best
  reply to the blunder, at the **blunderer's** pinned Elo. Reading: "would a player of your level see this
  punishment". It comes from the same full-policy call that yields `maia_reply_spread`, so it is free going
  forward; existing rows need a re-inference backfill.
- **D-08: It replaces the reply spread in the model** on blunders that lose material. Both types then read only
  the probability of the key move: `maia_best_prob` for a missed win, the best-reply probability for an allowed
  loss (the pre-blunder spread already fitted to 0). The `maia_reply_spread` column stays stored and is no longer
  read by the score.

#### Rule review before the build
- **D-09: The plan starts with a review report the owner confirms.** In the spike the quiet rule changed at least
  one odd-depth value on 113 played lines and 139 best lines of 290, more than the exchange artifact alone
  explains. The report groups the changes by cause (longer exchange settled, a later capture pulled one step
  earlier, line ended inside an exchange) and shows about 10 before / after positions with analysis links. The
  recompute is built only after the owner confirms the rule.

#### Scope of the recompute and rollout
- **D-10: Both sides' blunders, on prod only.** The score is one expression used for the player's and the
  opponents' blunders (Phase 257 comparison), so both get the new columns. Prod size 2026-11-21: 4,687,707
  `game_flaws` rows carry a reply spread, 4,417,251 a played-line array, 4,415,594 a best-line array (4,707,735
  blunders of 7,813,403 flaws). The benchmark DB backfill is **not** in this phase (owner, 2026-11-21, reversing
  an earlier answer in the same session); it belongs to the benchmark zones work (SEED-261120-bzq). The code
  must still run there: the migration applies to the benchmark DB and its rows stay unscored until that backfill.
- **D-11: New columns, one switch.** The new columns are filled while the app keeps scoring from the old arrays;
  one release switches the expression and the constants together; a later migration drops the arrays (D-06).
  Users never see half-converted scores. Prod operator runs go one at a time (prod `max_connections` is 50, the
  app pool takes up to 20).
- **D-17: The covering index follows the inputs.** `ix_game_flaws_blunder_facts` includes both material arrays
  today. A covering partial index with the new scalar inputs (`loss`, `missed`, the best-reply probability, and
  the other columns `_game_flaw_columns` reads) must exist on prod before the switch release (built
  `CONCURRENTLY`), otherwise the score queries fall back to heap fetches. The old index is dropped before or with
  the array drop (D-06), since it depends on the array columns.
- **D-18: JIT is re-measured, not assumed.** The score and type expressions are 14.2 KB (98 CASE) and 17.7 KB
  (124 CASE) today, nearly all of it the per-slot array aggregation; that is why 257 D-21 runs the facepalm
  statements with `SET LOCAL jit = off`. With scalar inputs the expressions shrink to a short logistic. After the
  switch, the plan runs EXPLAIN ANALYZE on the largest prod account with JIT on and off, and removes
  `disable_jit_for_transaction` only if the numbers support it. A stored final score stays ruled out (254 D-01,
  D-05 option d): every coefficient refit would be a prod UPDATE pass over about 4.7M rows.
- **The preliminary facepalm bands are held.** The `quick/facepalm-prelim-bands` worktree derives bands from the
  current score; they are not merged before this refit ships and are re-derived from the new score.

#### Acceptance (defaults accepted by the owner, not discussed in depth)
- **D-12: AUC range check:** cross-validated AUC of the final model within about 0.02 of 0.897 (the shipped rule
  on today's lines, spike baseline). The plan re-measures the baseline, since lines keep changing.
- **D-13: Fixture:** prod game 2883555 ply 47 must have a missed gain of 0 under the new rule (best line
  Bxf4 Qxf4 Qxf4 Rxf4). Its new score is reported at the checkpoint, not gated.
- **D-14: No new label set.** The refit uses label sets 1 to 8 as they are.
- **D-15: One blocking owner checkpoint** after the fit report: the owner confirms the model and sets
  `FACEPALM_SCORE_MIN` and `FACEPALM_STATS_MIN`, with the fair / unfair table at cuts from about 50% to 70% and
  the drill pool size, as in Phase 256 D-13.
- **D-16: Release** as a normal release with a changelog bullet: scores change for every user (library chip,
  Facepalm filter, Facepalm rate in the stats, drill pool).

### Claude's Discretion
- Names and types of the new columns, and how NULL is encoded ("line too short to tell" must still leave the row
  unscored, 256 D-03; an unknown best line still gives `missed = 0`).
- How mates enter the stored `loss` and `missed` (a mate within depth 3 must keep scoring as today's `MATE_LOSS` /
  `FACEPALM_MISSED_MATE` case) and whether the mate ply columns can then be dropped too.
- Which move is "the best reply": the first token of the stored refutation line (`game_positions.pv` at flaw
  ply + 1), consistent with the line the material is counted on.
- How the reply probability is gated for pure misses (the spike used it only on rows that lose material and 0
  elsewhere, mirroring `best_prob_for_misses`), and how a NULL reply probability unscores a row (mirror 256 D-04).
- Whether the staged form selection of `fit_facepalm.py` is re-run or the shape is fixed by D-03 and D-08 with
  the alternatives listed as information only (D-01 says the fit does not choose).
- Backfill mechanics: sharding, order of the Maia re-inference and the material pass, resumability, the readiness
  gate before the switch release.
- Whether the spike scripts move into `scripts/blunder_check/` or are rewritten.

### Deferred Ideas (OUT OF SCOPE)
- **Blunder-check sequences with any facepalm score:** serve a small random share of sequences drawn from all
  scored blunders, flagged with a known sampling rate, to validate the score on user outcomes over the whole
  range and later fit on them. Open points: the outcome ("avoided it in a drill") is not the owner's label; the
  share must stay small because low-score blunders are the unfair ones; whether they count towards medals and
  streaks. A drill-selection change, its own phase.
- **A fit on user blunder-check answers:** once enough exist. Today nothing below a score of 0.50 is served.
- **Total probability of all punishing replies** instead of the best reply only: needs evaluations of every reply.
- **`detect_sacrifice` misses an offered sacrifice the engine declines** (same row has no allowed tactic tag): a
  new detector condition, to be checked against the precision fixtures.
- **Benchmark DB backfill of `loss`, `missed` and the reply probability:** with SEED-261120-bzq.
- **Decay ratio by rating** (stronger players look deeper): not fitted here (D-04).
- From Phase 256, still open: "the gain is a simple capture of an undefended piece", "the best move is the only
  winning move", a separate model for pure misses.
</user_constraints>

<phase_requirements>
## Phase Requirements

No requirement IDs are mapped (REQUIREMENTS TBD). The locked decisions are the requirements; this table maps each
to the research that supports it.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-02 | Quiet-point material rule | Pattern 1 (quiet walk on `_replay_line` / `_Step`), Pitfalls 1, 2, 3; fixture check below (the 4 committed fixtures that change) |
| D-03, D-04 | Decaying mean over odd depths, ratio 1/2 | Pattern 2: reuse `material_loss` / `material_missed` Python functions on quiet arrays, the aggregation semantics stay byte-identical |
| D-05, D-06 | Two scalar columns, arrays dropped last | Pattern 2 (encoding), Release sequence R1 / switch / drop, Reader-writer inventory, Runtime State Inventory |
| D-07, D-08 | Best-reply probability column, replaces the spread | Pattern 3 (`_derive_reply_spread` policy), Pattern 4 (`reply` backfill mode), Pattern 5 (new twin) |
| D-09 | Rule review report before the build | Pattern 6 (review tool, cause classification) |
| D-10, D-11 | Both sides, prod only, one switch | Backfill sizing, readiness gate, Pitfall 7 |
| D-12, D-13, D-14 | AUC range check, fixture 2883555:47, label sets 1-8 | Pattern 7 (fit tool), fixture reproduced on dev this session |
| D-15, D-16 | Owner checkpoint, normal release | Pattern 7, Pitfall 9 (`FACEPALM_STATS_MIN` is coupled to the frontend 70%) |
| D-17 | Covering index before the switch, CONCURRENTLY | Pattern 8, Pitfalls 5, 6 |
| D-18 | JIT re-measure, conditional removal | Pattern 9 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend: FastAPI, Python 3.14, SQLAlchemy 2.x async `select()`, Alembic, asyncpg, Pydantic v2; httpx only for HTTP (not used here).
- Layering: routers HTTP only, services logic, repositories SQL. The score twin in `app/services/facepalm_score.py` builds an expression and never executes SQL (existing precedent, keep it).
- DB rules: FKs mandatory (no new FK columns here); no native ENUM; right-sized types (REAL for probabilities and the new fractional material inputs, matching existing `maia_*` REAL columns).
- `Literal[...]` for every fixed set (the new backfill mode name, the review cause names); `Sequence[...]` for covariant params; explicit return types; `# ty: ignore[rule]` only with a reason. `uv run ty check app/ tests/ scripts/` zero errors, plus `uv run --project analysis --with ty ty check analysis/`.
- No magic numbers: shard counts, offsets, caps, thresholds as named constants. Migrations use literals only (never import app constants; precedent in `b7c1d9e2f3a4`).
- Nesting depth <= 4 (gated by `scripts/check_function_size.py app/ --fail-over-depth 4`). `line_material.py` and `maia_flaw_scoring.py` are already long; new branches go in small helpers.
- Sentry: `capture_exception` in non-trivial `except` blocks in services/routers; no variables in messages.
- Never `asyncio.gather` on one `AsyncSession`.
- Comment bug fixes at the fix site.
- Pre-merge gate (full, once per squash-merge): ruff format, ruff check --fix, ty x2, function-size gate, `uv run pytest -n auto -x`, frontend lint/build/test/knip.
- `bin/deploy.sh` / `/deploy` is the only deploy path. Never run `bin/reset_db.sh`. Never touch `.env` files.
- CHANGELOG `## [Unreleased]` bullet when the phase merges to `main` (D-16).
- GSD scope: no unplanned work. Em-dashes sparingly in prose.
- Project memory that applies: prod `max_connections=50`, app pool up to 20, operator connections under ~25 (runbook line 36); long prod runs from the orchestrator with `setsid nohup` + Monitor; executors die on long DB-heavy plans; prod scheduled reboot near 02:15 UTC kills tunnel and runs (relaunch resumes); fresh worktree gate needs `--group maia-inference`; worktrees have no DB config (run prod scripts with cwd at the main checkout); subagents have no prod MCP; "Engine is not gospel" / "First principles over small AUC gains" (the owner's D-01).

## Summary

Every reader of the score goes through one place: `facepalm_expr` / `facepalm_type_expr`, both built over `_game_flaw_columns()` in `app/services/facepalm_score.py:610-621` [VERIFIED: read this session]. The switch is therefore localized to the twin, the column map, the `FACEPALM_*` constants, the covering index and the test seeding helper (`tests/facepalm_seed.py`, used by 13 test files). The writers are equally centralized: the post-commit hook and all backfill modes build their rows in `app/services/maia_flaw_scoring.py` and write through `bulk_update_flaw_maia_stats`, with the key sets fixed by the tuples in `app/repositories/game_flaws_repository.py:179-203`.

The quiet rule fits on top of the existing `_replay_line` / `_Step` machinery in `app/services/line_material.py`. The cleanest R1 implementation produces quiet per-depth odd arrays and feeds them to the **unchanged** Python aggregation (`material_loss` / `material_missed` with `decaying_mean`, loss floor 0, missed floor 0, cap 5, mate 5). That makes the stored scalars exactly "the shipped aggregation applied to quiet lines", which is what the spike measured. I reproduced the D-13 fixture on the dev DB (the dev row has the same lines as prod): under the quiet rule, game 2883555 ply 47 gets `loss = 2.935483870967742` (unchanged) and `missed = 0.0` (was `2.5806451612903225`) [VERIFIED: ran on dev this session]. Running the quiet rule over the 17 committed `LINE_FIXTURES` changes 4 of them, all at depth 7 or 9 (labels 153, 154, 156, 170). Those are ready-made D-09 examples.

The best-reply probability costs nothing extra going forward. `_derive_reply_spread` already computes the full post-blunder policy at the blunderer's pinned Elo (`maia_flaw_scoring.py:448-472`), keyed by `move.uci()` over all legal moves (`maia_encoding.py:183-193`). The value is `probs.get(first token of refutation_pv)`. Existing rows need one post-blunder inference each for blunders of both sides, about 4.7M. At the Phase 250 spread-pass pace (2.32M inferences in 8 h 48 min with 12 shards) that is roughly 18 h. The material recompute is Maia-free and already has a vehicle: `--mode line --cutoff`, which recomputes the line facts of both sides from the stored lines (the Phase 254 line pass did 1.04M games in 70 min with 4 shards).

**Primary recommendation:** ship three releases, the same shape as Phase 254. R1 (behaviour-neutral) adds the columns and dual-writes the old arrays plus the new scalars and the reply probability. Then the prod line pass, the new `reply` Maia pass and an operator-built `CREATE INDEX CONCURRENTLY` of a new, differently named covering index. The switch release changes the twin, the constants and the column map together, after the D-15 owner checkpoint. The drop release, human-gated, removes the arrays, the old index and the old-rule code. Fix the model shape by D-03/D-08 and fit only the coefficients. Report the alternatives (baseline, quiet + spread, quiet + spread + reply probability) as information only.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Quiet-point material walk, decaying mean | API / Backend (pure service `line_material.py`, `facepalm_material.py`) | — | Runs at write time in Python (D-05); no I/O |
| Best-reply probability | API / Backend (`maia_flaw_scoring.py`, Maia inference) | Operator script (`backfill_maia_flaws.py --mode reply`) | Same policy call as the reply spread; backfill runs on the operator machine through the tunnel |
| Storage of `loss` / `missed` / reply prob | Database (`game_flaws` columns, NOT VALID CHECKs) | — | Query-time score reads stored scalars (254 D-01) |
| Score and type at query time | Database (SQL expression) built by API service (`facepalm_score.py`) | Python twin for reports and counts | One expression for chip, filter, drill, stats (253 D-10) |
| Covering index | Database | Operator step (CIC on prod) | Must exist before the switch (D-17) |
| Fit, review report, calibration | Operator scripts (`scripts/blunder_check/`) | Committed reports | Read-only prod access; owner checkpoints |
| Frontend | Browser | — | No change beyond new values, unless `FACEPALM_STATS_MIN` moves (Pitfall 9) |

## Standard Stack

No new libraries. Everything uses what is installed.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.11.x (project pin) | Line replay, legality, SEE helpers | Already the engine of `line_material.py` |
| SQLAlchemy | 2.0.52 [VERIFIED: `uv run python -c` this session] | Expression twin, ORM index declaration | Existing |
| Alembic | 1.19.2 [VERIFIED: same] | Migrations; `op.create_index(..., postgresql_concurrently=True, if_not_exists=True)` inside `autocommit_block()` | `if_not_exists` is in `alembic/operations/ops.py:945` [VERIFIED] |
| onnxruntime | 1.29.0 (exact pin, `maia-inference` group) [VERIFIED: `pyproject.toml:48-52`, import probe] | Maia for the reply pass and the features pull | Never bump (owner decision; >=1.30 segfaults) |
| numpy | project pin | IRLS fit in `fit_facepalm.py` | Existing |

**Installation:** none. Use `uv sync` and `uv run --group maia-inference ...` for Maia runs.

## Package Legitimacy Audit

No external packages are installed in this phase. Gate not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Reader and Writer Inventory (item 1 of the brief)

Every reference found by grep and confirmed by reading the surrounding code this session. "Phase step" says when the line must change: **R1** (dual-write, behaviour-neutral), **SW** (switch release), **DROP** (human-gated drop release).

### App: schema and storage
| File:line | What | Phase step |
|---|---|---|
| `app/models/game_flaw.py:22-27` | `_material_array_shape` CHECK predicate | DROP |
| `app/models/game_flaw.py:43-59` | `ix_game_flaws_blunder_facts` declaration, INCLUDE list quoted below | SW (add new index), DROP (remove old) |
| `app/models/game_flaw.py:62-71` | Two NOT VALID CHECKs `ck_game_flaws_{played,best}_line_material_shape` | DROP |
| `app/models/game_flaw.py:148-163` | `maia_reply_spread`, `line_mate_ply` columns + comment | keep (comment update SW) |
| `app/models/game_flaw.py:165-190` | `played_line_material`, `best_line_material`, `best_line_mate_ply`, `maia_best_prob`, `maia_pre_spread` | R1 add new columns beside; DROP removes the two arrays |
| `app/models/game.py:282-296` | games stamps `facepalm_spread_completed_at`, `facepalm_line_completed_at`, `facepalm_pre_completed_at` | R1 add `facepalm_reply_completed_at` (recommended) |
| `alembic/versions/20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py:58-86` | added the arrays + NOT VALID CHECKs via `op.execute` | reference for R1/DROP migrations |
| `alembic/versions/20261120_180000_b7e4a1c9d257_phase_257_ix_game_flaws_blunder_facts.py:37-54` | old index, created **non-concurrently** inside the migration (docstring line 16-18: "Created non-concurrently ... Expect one sequential pass over game_flaws at deploy") | DROP |

Verbatim INCLUDE list of the current index [VERIFIED: `app/models/game_flaw.py:43-59`]:
`"ply", "maia_played_prob", "maia_reply_spread", "played_line_material", "line_mate_ply", "best_line_material", "best_line_mate_ply", "maia_best_prob", "maia_pre_spread"`, keyed `"user_id", "game_id"`, `postgresql_where=text("severity = 2")`.

### App: writers
| File:line | What | Phase step |
|---|---|---|
| `app/repositories/game_flaws_repository.py:187-193` | `FACEPALM_COLUMNS = ("maia_reply_spread", "line_mate_ply", "played_line_material", "best_line_material", "best_line_mate_ply")` [VERIFIED] | R1 add the two material scalars; DROP remove arrays |
| `app/repositories/game_flaws_repository.py:200-203` | `FACEPALM_PRE_COLUMNS = ("maia_best_prob", "maia_pre_spread")` [VERIFIED] | pattern for a new `FACEPALM_REPLY_COLUMNS` |
| `app/repositories/game_flaws_repository.py:300-314` | `bulk_update_flaw_maia_stats` (one executemany, same key set per row) | unchanged |
| `app/repositories/game_flaws_repository.py:390-421` | `clear_maia_flaws_completed` clears all four stamps | R1 add the reply stamp (if stamp approach) |
| `app/services/maia_flaw_stats.py:20-31` | `MaiaReason` Literal: `"played_not_legal", "no_rating", "pgn_unparseable", "invalid_root", "ply_beyond_mainline", "fen_mismatch", "no_legal_reply", "best_move_missing"` [VERIFIED] | R1 add a reason such as `"reply_missing"` |
| `app/services/maia_flaw_stats.py:43-69` | `FacepalmStats` TypedDict + `null_facepalm_stats` (the five fact keys) | R1 add scalars; DROP remove arrays |
| `app/services/maia_flaw_scoring.py:137` | `ScoringMode = Literal["full", "spread", "line", "pre", "opponent"]` [VERIFIED] | R1 add `"reply"` |
| `app/services/maia_flaw_scoring.py:158-182` | `FlawMaiaInput` (stored values not fingerprinted) | R1 add `stored_best_reply_prob` (+ `_flaw_fingerprint_select:250-262` column, `_read_flaw_inputs:290-316`) |
| `app/services/maia_flaw_scoring.py:448-472` | `_derive_reply_spread` (the full post-blunder policy; source of the reply prob) | R1 |
| `app/services/maia_flaw_scoring.py:487-515` | `_material_or_none`, `_facepalm_values` (writes both arrays and mate plies) | R1 add scalars; DROP remove arrays |
| `app/services/maia_flaw_scoring.py:573-628` | `_opponent_maia_values`, `_derive_flaw_values` (full-mode path, both sides) | R1 |
| `app/services/maia_flaw_scoring.py:662-693` | `_spread_row` (user-only historical spread pass) | R1 (gets scalars via `_facepalm_values` automatically) |
| `app/services/maia_flaw_scoring.py:743` | `OPPONENT_ROW_COLUMNS = ("maia_reply_spread", *FACEPALM_PRE_COLUMNS)` | leave |
| `app/services/maia_flaw_scoring.py:819` | `LINE_ROW_COLUMNS = tuple(c for c in FACEPALM_COLUMNS if c != "maia_reply_spread")` | R1: line mode then writes the scalars; must NOT include the reply prob (Pitfall 4) |
| `app/services/maia_flaw_scoring.py:862-884` | `_row_score` (in-memory score for backfill counts, reads arrays) | SW |
| `app/services/maia_flaw_scoring.py:1018-1045` | `_STAMP_COLUMN_BY_MODE`, `_mark_stamps` | R1 add reply |
| `scripts/backfill_maia_flaws.py:176` | `BACKFILL_MODE_CHOICES = ("full", "spread", "line", "pre", "opponent")` [VERIFIED] | R1 add `"reply"` |
| `scripts/backfill_maia_flaws.py:240-246` | `_STAMP_CLAUSE_BY_MODE` (constant predicates per mode) | R1 add reply clause |
| `scripts/backfill_maia_flaws.py:664-672` | Maia started for every mode but `line` | R1 (reply needs Maia) |
| `scripts/backfill_maia_flaws.py:884-913, 1049-1063` | status counts via `facepalm_expr`; `played_line_material.is_not(None)` at 1055 | R1 add reply status; SW/DROP replace 1055 |

### App: readers of the score and type (all through `_game_flaw_columns`)
| File:line | What |
|---|---|
| `app/services/facepalm_score.py:610-621` | `_game_flaw_columns()` column map (the one switch point) |
| `app/services/facepalm_score.py:624-635, 698-706` | `facepalm_expr`, `facepalm_type_expr` |
| `app/repositories/library_repository.py:350-376` | `_facepalm_clause` (Facepalm filter, also used by `query_utils` EXISTS via `facepalm_range_active`, `query_utils.py:396-431`) |
| `app/repositories/library_repository.py:1211, 1303` | Flaws-tab chip + type |
| `app/repositories/library_repository.py:1411-1429` | eval-chart / move-list markers |
| `app/repositories/library_repository.py:1679-1688` | `disable_jit_for_transaction` |
| `app/repositories/library_repository.py:1717, 1732-1752` | `fetch_facepalm_counts` (timeline band, JIT off, `.offset(0)` fence) |
| `app/repositories/library_repository.py:2589, 2604-2642` | `fetch_facepalm_comparison` (JIT off, fence) |
| `app/services/library_service.py:2119-2121` | extra `disable_jit_for_transaction` before the window statement (258) |
| `app/repositories/blunder_check_repository.py:372-405` | drill EXISTS predicate `facepalm_expr(FACEPALM_DRILL_LAMBDA) >= FACEPALM_SCORE_MIN` |
| `app/repositories/blunder_check_repository.py:646-672` | `load_blunder_flaws` |
| `app/services/blunder_check_selection.py` | no direct reference (only `require_facepalm` flags into the repository) [VERIFIED: grep] |
| `app/schemas/library.py:96-102, 247-252, 299` | comments only |

### Scripts
| File:line | What | Phase step |
|---|---|---|
| `scripts/blunder_check/facepalm_features.py:61-69, 85-105, 141, 162-200, 224-249, 261-285, 565-577` | features TSV (old-rule arrays, spread, best prob) | R1 or SW: new columns (Pattern 7) |
| `scripts/blunder_check/fit_facepalm.py` (2569 lines) | legacy + facts schemas, staged selection, `--check-constants` (2478-2564) | SW: fixed-shape scalar fit (Pattern 7) |
| `scripts/blunder_check/sample.py:41-47, 175-290, 420-436, 556-600, 650-660` | calibration sampler reads arrays, mate plies, spread; scores with the twin | SW |
| `scripts/blunder_check/render.py:439, 938, 953, 1030` | spread, `line_mate_ply`, `material_type` | SW |
| `scripts/blunder_check/spot_check.py:44, 482-501, 522-524` | `missed_feature`, `FACEPALM_MODEL.missed_floor/cap/mate`, arrays | SW |
| `scripts/blunder_check/metrics.py:177-206` | `material_type(played_3, mate_ply, best_3, best_mate_ply)` | SW (re-base on loss/missed) |
| `scripts/blunder_check/miss_labels.py:125` | `line_facts`, `best_line_facts` | DROP (old rule removal) |
| `scripts/blunder_check/decaying_mean.py:26-31` | Phase 256 analysis, imports SQL-side helpers | SW/DROP (delete or re-point) |
| `scripts/blunder_check_calibration.py` | drives sample + render | SW (indirect) |

### Tests (files that read arrays, the spread or the twins)
`tests/facepalm_seed.py` (seeds arrays via the twin, 13 users), `tests/facepalm_models.py` (PHASE_250/254 models), `tests/services/test_facepalm_score.py` (49 tests: grid parity, shape CHECK tests 1174-1190), `tests/services/test_facepalm_material.py` (Python/SQL aggregation parity), `tests/services/test_facepalm_owner_fixtures.py`, `tests/services/facepalm_owner_fixtures.py`, `tests/services/test_line_material.py`, `tests/services/line_material_fixtures.py`, `tests/services/test_maia_flaw_scoring.py` (83 tests; key-set pins at 425, 751-753, 974, 1060, 1269, 2231, 2334, 2382, 2462, 2510), `tests/services/maia_fakes.py:19, 72-91` (stamp + column asserts), `tests/scripts/test_backfill_maia_flaws.py` (53), `tests/scripts/test_fit_facepalm.py`, `tests/scripts/test_facepalm_features.py`, `tests/scripts/test_blunder_check_calibration.py`, `tests/scripts/test_decaying_mean.py`, `tests/scripts/test_miss_labels.py`, `tests/scripts/test_blunder_check_metrics.py`, `tests/services/test_flaw_comparison.py:1274-1304, 1402-1420` (JIT and index-coverage pins), and two compiled-SQL string assertions that name the array column: `tests/test_query_utils.py:526, 533, 539` and `tests/test_library_repository.py:2743` (`assert "played_line_material" in sql`). These four must switch to the new column name in SW, or the gate fails.

Frontend: no reader [VERIFIED: grep of `frontend/src` for `line_material|reply_spread|mate_ply|best_reply` returns nothing].

## Architecture Patterns

### System Architecture Diagram

```
 eval apply lanes (drain / remote submit / blob submit)          operator machine (prod tunnel)
        │ commit                                                         │
        ▼                                                                ▼
 score_game_flaws_after_apply ──► load_game_maia_inputs ◄──── backfill_maia_flaws.py --mode line | reply
        │                         (flaws + pv@ply+1 + pv@ply)            │ (sharded by md5(id) residue,
        ▼                                                                │  one connection per shard)
 score_game (thread, no session)                                         │
   ├─ board replay / fen guard                                           │
   ├─ full_policy(pre board) ─► maia_played_prob, best_prob, pre_spread  │
   ├─ full_policy(post board) ─► reply_spread + BEST-REPLY PROB (new)    │ reply mode: this call only
   ├─ line_facts (old rule) ─► 9-slot arrays (until DROP)                │
   └─ quiet facts (new rule) ─► decaying mean ─► material_loss/missed   │ line mode: no Maia
        ▼                                                                ▼
 write_game_maia_scores: advisory lock, fingerprint re-check, bulk UPDATE by PK, stamps
        ▼
 game_flaws (scalars) ──► ix_game_flaws_facepalm_inputs (covering, severity = 2)
        ▼
 facepalm_expr / facepalm_type_expr (short logistic over scalars)
   ├─► library chip / filter / markers / timeline counts / comparison
   └─► drill selection (EXISTS + load)
```

### Release sequence (template: Phase 254 R1 / R2 / drop, see 254-06 "Branch and checkout map")

1. **R1 code (behaviour-neutral).** Quiet rule + review tool first (D-09 needs the rule code). After the owner confirms the rule: migration (instant ADD COLUMNs + NOT VALID CHECKs + games stamp), model columns, writer changes (hook dual-writes arrays and scalars and the reply prob; line mode writes the scalars; new `reply` mode), status counts, tests. The score keeps reading the arrays.
2. **R1 release + prod runs (orchestrator, one at a time).** Deploy; migrate the benchmark DB too (D-10: code must run there). Line pass with `--cutoff <R1 deploy time>`, then the reply pass, then the readiness gate, then the operator CIC of the new covering index with an `indisvalid` check.
3. **Switch code (unreleased branch).** New twin + model + column map + type twin, constants placeholders, seed helper, reader-test SQL strings, ORM index + CIC-IF-NOT-EXISTS migration, covering-index test, fit tool, calibration sampler/render/spot check.
4. **Fit + owner checkpoint D-15 (orchestrator).** Features pull from prod (read-only), fit with the baseline re-measure, calibration on prod with the candidate constants, D-13 fixture score. The owner confirms the model and sets both cuts.
5. **Switch release.** Paste constants, CHANGELOG bullet (D-16), gate, deploy. Post-deploy: coverage and qualifying counts; D-18 EXPLAIN ANALYZE with JIT on/off on the largest account.
6. **Drop code + human-gated drop release.** Stop writing arrays, delete the old rule and the SQL builders, the remaining script and test readers; migration drops the old index (CONCURRENTLY IF EXISTS) and the two array columns (their CHECKs go with them, Pattern 8). JIT removal rides here if D-18 supports it. Deploy only with no operator script running (254 drop rule).

### Pattern 1: Quiet-point walk (D-02) on the existing machinery

**What:** walk `depth` plies, then keep walking while the next line move is a capture (any square); if the walk runs off the end of the stored line and the last move was a non-mating capture, settle with `_best_recapture` on that square. Keep the 250 counting rules (first move's capture for the blunderer, desperado exclusion via the quiet-square state, mate settles coverage).

**Mapping onto `line_material.py`** [VERIFIED: read lines 120-321]:
- `_replay_line(board, tokens, blunderer)` (170-189) gives `list[_Step]` and the end board; reuse as is.
- `_net_loss` (205-221) is the per-step counting rule with the desperado state (`quiet_blunderer_square`). The quiet walk is the same loop body with a different stop condition. Extract the loop body into a helper (`_count_step(loss, quiet_square, step) -> tuple[int, int | None]`, exactly the spike's `_apply`) and have both `_net_loss` and the new walk call it, so the desperado rule exists once.
- `_recapture_credit` (192-202) is today's "line ended on an opponent capture" settlement, limited to lines shorter than `_MAX_WALK_PLIES = 10` and to opponent captures. The quiet rule generalises it: any final non-mating capture, either side, any line length, sign by side (`loss -= swing` after an opponent capture, `loss += swing` after a blunderer capture).
- Coverage (`_loss_at_depth`, 224-239, D-05 NULL rule): a depth is unknown when the line has fewer than `depth` legal plies, unless a mate of either side lies in `steps[:depth]` or the line ends inside an exchange (SEE settles it). This keeps 256 D-03: an unknown depth 3 leaves the row unscored.
- `_facts_after_first_move` (258-288): a first move that mates settles every depth (`opponent_mate_ply = 0`). **Keep this branch before requiring a non-empty rest** (the spike's `quiet_array` returns all-None when `rest` is empty, which would drop a mating best move; Pitfall 2).
- Only odd depths (`LINE_LOSS_DEPTHS = (1, 3, 5, 7, 9)`, line 46 [VERIFIED]) are needed (D-03).

**Recommendation:** add `quiet_line_facts(pre_board, played_uci, pv) -> LineFacts` and `quiet_best_line_facts(pre_board, best_pv) -> LineFacts` returning `LineFacts` with odd depths filled and even depths None, plus the same `mate_ply` / `opponent_mate_ply`. Leave `line_facts` / `best_line_facts` untouched until DROP (the old arrays must stay byte-identical while the old expression reads them, D-11).

### Pattern 2: Stored scalars and NULL encoding (D-05, discretion)

**Recommended columns** (names are proposals, [ASSUMED] until the planner fixes them): `game_flaws.material_loss REAL NULL`, `game_flaws.material_missed REAL NULL`, `game_flaws.maia_best_reply_prob REAL NULL`. `material_loss` / `material_missed` match the existing Python names `material_loss` / `material_missed` in `facepalm_score.py:299-367`; avoid reusing `line_loss_*` (dropped in 254, confusing history).

**Computation at write time (reuse the shipped aggregation):**
```python
loss = material_loss(quiet.material_array(), quiet.mate_ply,
                     material_input="decaying_mean", loss_floor=0)          # None = line too short
missed = None if loss is None else material_missed(
    quiet.material_array(), quiet_best.material_array(), quiet_best.opponent_mate_ply,
    material_input="decaying_mean", missed_floor=0, missed_cap=5, missed_mate=5)  # 0.0 = unknown best line
```
This inherits every existing semantic exactly [VERIFIED: `facepalm_score.py:299-367`, `facepalm_material.py:77-163`]: a mate within `LINE_DEPTH` short-circuits to `MATE_LOSS` / missed mate; a mate beyond depth 3 counts its value from its ply on inside the mean; unknown depth 3 gives None; an unknown best line gives 0.0 (254 D-18); weights renormalise over known depths. The literals above are today's shipped constants (`FACEPALM_LOSS_FLOOR = 0`, `FACEPALM_MISSED_FLOOR = 0`, `FACEPALM_MISSED_CAP = 5`, `FACEPALM_MISSED_MATE = 5`, `FACEPALM_MATERIAL_INPUT = "decaying_mean"`, `MATERIAL_DECAY_RATIO = 0.5`, `LOSS_CAP = 5`, `MATE_LOSS = 5`, `LINE_DEPTH = 3` [VERIFIED: `blunder_check_rules.py:67-117`]); in code use the named constants, not literals.

**NULL encoding:** `material_loss IS NULL` = unscored (line too short, no line, unusable board) or not computed yet; `material_missed IS NULL` exactly when `material_loss IS NULL` (write-time invariant). "Not computed yet" is told apart from "too short" by the game's line stamp against the R1 cutoff, as the line pass already does. Optional NOT VALID CHECKs (instant, enforced on new writes): `(material_loss IS NULL) = (material_missed IS NULL)` and both `>= 0`. Avoid range CHECKs with the cap value: a later rule change (D-05 recompute) would need a migration for no benefit.

**Mates (discretion):** fold mates into the scalars as above; the score no longer reads `line_mate_ply` / `best_line_mate_ply`. **Recommend keeping both mate columns** (CONTEXT keeps them; SMALLINT, cheap; still useful to `material_type`, the spot check and any future recompute audit). Dropping them is scope creep with no benefit.

**Rule constants become write-time constants after SW.** Changing `LOSS_CAP`, `MATE_LOSS`, `FACEPALM_MISSED_*`, `MATERIAL_DECAY_RATIO` or the quiet rule after SW silently mixes two rules across rows unless a line pass with a new cutoff follows. Move them out of the "fitted" constants block, document "changing this needs a prod line pass", and add a tripwire test that pins their values with that message.

### Pattern 3: Best-reply probability (D-07)

`_derive_reply_spread(pre_board, played_uci, elo)` (448-472) pushes the played move on a copy, returns `None, ["no_legal_reply"]` when the opponent has no move, otherwise `probs = full_policy(post.fen(), elo)` [VERIFIED]. `full_policy` returns `mask_and_softmax(...)`, keyed by `move.uci()` over **every** legal move (`maia_encoding.py:177-193`) [VERIFIED], so any legal first token has a key. Extend the helper to take the reply UCI and return `(spread, reply_prob, reasons)`:
- reply UCI = first token of `flaw.refutation_pv` (`game_positions.pv` at ply + 1, `FlawMaiaInput.refutation_pv`, the same line the material is counted on);
- `reply_prob = float(probs[reply])` when the token parses and is in `probs`, else None with a reason (e.g. `"reply_missing"`), like `_pre_inputs` does for `best_move_missing` (557-570).
- Elo: the blunderer's pinned Elo (`_mover_elo(inputs, board)` on the pre board, 417-428), as for the spread (248 D-04, D-07).
- The fingerprint already contains `refutation_pv` (185-188), so a reply prob from a since-repaired line is never written.
- Spike reference value: Nxe6 (`f4e6`) at 21% for the fixture; known for 279 of 290 label rows (quartiles 0.18 / 0.53 / 0.74) [CITED: 259-CONTEXT specifics].

### Pattern 4: The `reply` backfill mode (discretion: mechanics)

Model it on `pre` mode (one inference per blunder, own stamp) plus the both-sides scope of `opponent`/`line`:
- Scope: blunders of both sides whose `stored_played_prob is not None` (the hook writes the spread only when the played move is in the policy; same proxy as `_is_opponent_target`, 746-757).
- One inference: the post-blunder policy only (no pre-blunder call). Row keys: PK + `FACEPALM_REPLY_COLUMNS = ("maia_best_reply_prob",)` (a new tuple, deliberately not in `FACEPALM_COLUMNS`, Pitfall 4).
- Checkpoint: **recommend a new stamp `games.facepalm_reply_completed_at`**, selected as `facepalm_reply_completed_at IS NULL AND maia_flaws_completed_at IS NOT NULL` (the `pre` clause shape, `backfill_maia_flaws.py:204-206`). Full mode sets it (`_mark_stamps`), `clear_maia_flaws_completed` clears it, `maia_fakes.assert_maia_lane_state` asserts it. Alternative: a row predicate like `_OPPONENT_PENDING_CLAUSE` (`maia_best_reply_prob IS NULL AND maia_played_prob IS NOT NULL`), no games column, but rows with no stored refutation line are re-selected by every run, so `--status` never reaches zero and the readiness gate gets murkier. The stamp wins.
- Status (`--status --mode reply`): stamped / pending games; blunders total (both sides), with reply prob, and the residue that matters for the switch: `material_loss > 0 AND maia_played_prob IS NOT NULL AND maia_best_reply_prob IS NULL`.
- Sizing [ASSUMED: extrapolation]: ~4.7M inferences. Phase 250 spread pass: 2.32M inferences, 12 shards, 8 h 48 min, ~73/s, prod connections 28 of 50 [CITED: `reports/maia-flaws-backfill/prod-facepalm-spread-coverage.md`]. Expect ~18 h at 12 shards; keep total operator connections under ~25 (runbook line 36), so 12 shards is the ceiling. It crosses the ~02:15 UTC scheduled reboot; relaunching resumes from the stamp.

**Material pass:** `--mode line --cutoff <R1 deploy time>` with `LINE_ROW_COLUMNS` now including the two scalars. Both sides, Maia-free, re-runnable. Phase 254: 1.04M games, 4 shards, 70 min (user side only) [CITED: 254-11-SUMMARY]; expect ~2-3 h now [ASSUMED]. It also rewrites the old arrays from today's lines (same rule), so live scores move slightly where Phase 252 repaired lines since 2026-11-15; that is consistent with what the hook writes and is not a half-conversion.

**Order:** line pass first (short, validates the rule on prod, makes `loss` known so the reply residue count is meaningful), then the reply pass, then the CIC. One at a time (D-11).

**Readiness gate before the switch** (all SELECT-only, orchestrator):
1. `line_pending_games = 0` for the R1 cutoff and `reply_pending_games = 0`.
2. Residue counts: blunders with `material_loss > 0`, `maia_played_prob` set and `maia_best_reply_prob` NULL (these become unscored under the new model); blunders with `material_loss <= 0`, `maia_best_prob` NULL (unscored today already, 256 D-04).
3. Old-vs-new coverage: blunders scored by today's `facepalm_expr` vs blunders that will be scored by the candidate (Python twin over a sample, or the switch-branch expression run read-only). Report the delta in the checkpoint.
4. New index exists and `indisvalid`.

### Pattern 5: The new twin (SW; D-08 gating, discretion)

Fixed shape (D-03, D-08; pre-spread fitted to 0 in 256 so it drops out):
```
z = b0 + b_played·ln(played_prob + 0.01) + b_loss·loss + lam·b_missed·missed
    + (loss > 0 ? b_reply·ln(reply_prob + 0.01) : b_best·ln(best_prob + 0.01))
```
- NULL rules: NULL played prob or NULL loss → unscored. Losing row (`loss > 0`, gate None as shipped) with NULL reply prob → unscored; non-losing row with NULL best prob → unscored (256 D-04 mirrored). A zero coefficient omits its term at build time in both twins (existing pattern).
- `FacepalmModel` shrinks to six numbers: `intercept, played_coef, loss_coef, missed_coef, best_prob_coef, reply_prob_coef` (the shape selectors `material_form`, `spread_form`, `material_input`, `loss_floor`, `missed_floor`, `missed_cap`, `missed_mate`, `loss_gate`, `pre_spread_coef`, `spread_coef` leave the model; the material ones become write-time rule constants).
- `FacepalmFacts` / `FacepalmColumns`: `played_prob, loss, missed, best_prob, reply_prob`.
- Type twin: `loss IS NULL → NULL; loss > 0 AND loss >= missed → "allowed_loss"; else "missed_win"` (257 D-02, unchanged rule, scalar inputs).
- `_game_flaw_columns()` maps to `maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob`.
- Spike evidence for the shape: "reply probability instead of spread", CV AUC 0.907, coefficient +0.913, vs baseline 0.897 [CITED: 259-CONTEXT specifics]. Inside D-12's ±0.02.

### Pattern 6: D-09 review report

**Data:** the label rows' stored lines from prod (read-only), the pre board from the PGN replay (`replay_flaw_boards`), both rules applied per odd depth to both lines, and loss/missed under both rules. Spike outputs exist locally (`temp/facepalm-259/baseline-today.tsv`, `quiet-any.tsv`, `reply-prob.tsv`, gitignored) but hold no lines and no walk traces, so they cannot classify causes; the report needs a committed tool.

**Recommendation:** a committed `scripts/blunder_check/quiet_rule_review.py` (rewrite, not the spike; the spike stays in the phase dir as reference) that reuses `facepalm_features.read_game_inputs` (467-528) and the new `line_material` functions, run by the orchestrator on prod read-only (`make_readonly_engine`). Cause per (row, line, odd depth) where the value differs, mechanically:
- **line ended inside an exchange**: the quiet walk reached the end of the stored line on a non-mating capture and the SEE settlement changed the value (the old rule had no credit there);
- **longer exchange settled**: the quiet walk consumed two or more plies beyond `depth` (the old rule takes at most one blunderer capture at `depth + 1`);
- **a later capture pulled one step earlier**: exactly one extra ply, and it is a capture the old rule excludes at `depth + 1` (an opponent capture).
Output: counts per cause and line (played/best), per depth, how many rows change loss/missed by more than a small epsilon, and ~10 before/after examples with `https://flawchess.com/analysis?game_id=X&ply=Y` (the label TSV `link` column format, verified). Include the D-13 fixture and the four committed fixtures that change (below).

Committed fixtures under the quiet rule [VERIFIED: ran this session against `tests/services/line_material_fixtures.py`]: 13 of 17 unchanged; label 153 `(0,3,3,2,1) → (0,3,3,2,2)`, 154 `(1,1,2,4,3) → (1,1,2,4,6)`, 156 `(0,-3,-3,-3,-4) → (0,-3,-3,-3,-1)`, 170 `(0,0,0,-9,-4) → (0,0,0,-4,-4)` (loss per depth 1/3/5/7/9). All changes are at depth 7 or 9 of 12-ply lines, where the walk often runs off the end of the line.

### Pattern 7: Fit tooling (D-01, D-12, D-14, D-15; discretion: staged selection)

**Recommendation: fix the shape, fit only the coefficients, report alternatives as information.** D-01 forbids choosing shapes by AUC inside the range and D-03/D-08 fix the shape, so the staged selection (Stage 1-3b, `fit_facepalm.py:1201-1400+`) has nothing left to decide.

- **Features TSV, new schema** (written by `facepalm_features.py`): keep `n, set, game_id, ply, label, pinned_elo, played_prob, reply_spread, best_prob, pre_spread`; add `reply_prob`, `loss`, `missed` (quiet rule, the exact writer function), `loss_shipped`, `missed_shipped` (old rule arrays through the same aggregation, for the D-12 baseline), the mate plies, and the raw inputs `pre_fen, played_uci, played_line, best_line` so every material value is recomputable offline and a test can assert the TSV's `loss`/`missed` equal the app rule on the stored lines (drift guard). The reply prob comes from the same post-board policy call `_spread_for` already makes (162-173).
- **Missing rows:** `collect_rows` + `_run` exit 5 (`EXIT_ROWS_MISSING`, 302, 645-647) when any label row's game is gone; one label game is gone from prod (spike: 290 of 291 rows). Add an explicit flag that lists missing rows in the summary instead of failing, or the pull cannot run.
- **Fit:** one design matrix `[1, ln(pp+off), loss, missed, best term on non-losing rows, reply term on losing rows]`, same IRLS (`fit_logistic`, 521), same seeded CV (`cv_predictions`, 579; `REPEAT_SEEDS = 5`, `CV_FOLDS = 10`, `FIT_SEED = 250`), same exclusions (undecided, extra, NULL played prob, NULL loss, NULL reply prob on a losing row, NULL best prob on a pure miss), set-8 hold-out, owner section. Score the chosen model with the new Python twin ("what is fitted is what the app computes").
- **Information-only section, same usable rows:** (a) D-12 baseline: shipped rule (`loss_shipped`, `missed_shipped`) + shipped shape (spread on losing rows, best prob on pure misses); (b) quiet + spread; (c) quiet + spread + reply prob; (d) the chosen model. Print `|AUC(d) − AUC(a)|` against the 0.02 range.
- **`--check-constants`:** refit the chosen shape from the committed TSV and compare with the six `FACEPALM_*` constants (`CHECK_CONSTANTS_TOLERANCE = 1e-4`, 96).
- **Legacy paths:** the `legacy` and `facts` schemas and their reproduction tests (`test_check_constants_legacy_still_passes` 688, `test_depth_3_fit_reproduces_the_2026_11_15_constants` 1042, `tests/facepalm_models.py`) depend on the old twin and cannot survive SW. Retire them with the old twin; the committed 2026-11-13/15/16 reports and TSVs stay as history. Run the D-12 baseline from the TSV's `loss_shipped`/`missed_shipped` columns, so the baseline stays reproducible without the old twin.
- **Checkpoint inputs (D-15):** fair/unfair among passers at cuts 0.50 / 0.55 / 0.60 / 0.65 / 0.70 (out of fold), the drill pool by cut from `scripts/blunder_check_calibration.py` on prod with the candidate constants (needs the new columns filled on prod, so after the backfill; ~15-30 min in 254/256), the D-13 fixture's new score, coverage delta from the readiness gate.

### Pattern 8: Covering index (D-17)

- **Autogenerate does not see INCLUDE or WHERE changes.** Alembic 1.19.2 `PostgresqlImpl.compare_indexes` compares only uniqueness, the key expressions and `nulls_not_distinct` (`alembic/ddl/postgresql.py:318-401`) [VERIFIED: read this session]. Changing the INCLUDE list of `ix_game_flaws_blunder_facts` in place would produce no migration and leave prod on the old definition. **Use a new name** (proposal: `ix_game_flaws_facepalm_inputs` [ASSUMED]).
- **CHECK constraints are not autogenerated** either: the `checkconstraint_byname` comparator is an opt-in plugin (`alembic/autogenerate/compare/__init__.py:64-70`) and `alembic/env.py` does not enable it [VERIFIED]. Hand-write them with `op.execute("... NOT VALID")` like `a7d2c9e1b254:82-86`.
- **Prod build:** the old index was built non-concurrently inside a migration at container start. For D-17, follow `b7c1d9e2f3a4` (2026-06-10): the operator builds on prod first ("Already applied in prod ...; this rides in the migration purely for dev/test parity"), and the migration runs `CREATE INDEX CONCURRENTLY IF NOT EXISTS` inside `op.get_context().autocommit_block()`, a no-op on prod that builds dev, benchmark and the test template. In Alembic: `op.create_index(name, "game_flaws", ["user_id", "game_id"], postgresql_include=[...], postgresql_where=sa.text("severity = 2"), postgresql_concurrently=True, if_not_exists=True)` inside the block.
- **When:** after the reply pass, before the switch release. Building it before the backfill makes every backfill UPDATE (both passes, ~4.7M rows each) maintain one more index from empty values and bloats it [ASSUMED: standard PostgreSQL behaviour, indexed-column updates are never HOT].
- **INCLUDE list:** `ply` (the `player_only_gate` parity test reads it) + every column `_game_flaw_columns()` maps (`maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob`). Not `maia_reply_spread`, not the mate plies, not the arrays. Re-point `test_blunder_facts_index_covers_every_score_input` (`test_flaw_comparison.py:1295-1304`) to the new name.
- **Old index:** keep it through SW (a rollback of SW keeps a usable index), drop it in DROP. PostgreSQL drops an index that INCLUDEs a dropped column, and a CHECK on that column, automatically [VERIFIED: rolled-back probe on dev PG 18.6 this session, `DROP COLUMN` left 0 constraints and 0 indexes]. Still write `DROP INDEX CONCURRENTLY IF EXISTS ix_game_flaws_blunder_facts` (autocommit block) and `DROP CONSTRAINT IF EXISTS` explicitly before the column drop, for a clear downgrade and a short lock.

### Pattern 9: JIT re-measure (D-18)

- Call sites [VERIFIED]: definition `library_repository.py:1679-1688`; `fetch_facepalm_counts` 1717; `fetch_facepalm_comparison` 2589; `library_service.py:2119-2121` (258, before `_fetch_recent_window`). Tests pinning it: `tests/services/test_flaw_comparison.py:1274-1292` (`test_facepalm_reads_run_with_jit_off`) and `1402-1420` (`test_facepalm_jit_is_off_before_the_window_statement`).
- Measurement: after the switch deploy, compile the shipped statements with `temp/facepalm-257/gen_shipped_sql.py <user_id>` (exists locally, gitignored) and run `EXPLAIN (ANALYZE, BUFFERS)` with `SET jit = on` and `SET jit = off`, cold and warm, for the timeline counts and the comparison. The largest account in 257 UAT was user 95 (40,218 analyzed games, ~165k blunders; JIT 4,020 ms of 11,048 ms) [CITED: 257-UAT.md test 2]; re-check which account is largest now.
- Decision rule: remove the helper, its three calls and the two tests only if JIT-on is not slower (within noise) on both statements. Otherwise keep it and record the numbers. JIT is triggered by plan cost (`jit_above_cost`), not by expression size, so large accounts still JIT; only the compile cost shrinks [ASSUMED].
- Add a cheap guard test: the compiled `facepalm_expr` / `facepalm_type_expr` SQL is under a small size (e.g. 2 KB), replacing `test_aggregate_expression_is_one_scalar_expression` (`test_facepalm_score.py:731`).

### Anti-Patterns to Avoid
- **Changing `line_facts` / `best_line_facts` in R1.** The old expression reads their arrays until SW; altering them half-converts scores (D-11).
- **Editing the INCLUDE list of the existing index name.** Autogenerate is blind to it (Pattern 8).
- **Putting the reply prob into `FACEPALM_COLUMNS`.** Line mode writes `FACEPALM_COLUMNS` minus the spread and would overwrite the reply prob with NULL without Maia (Pitfall 4).
- **A stored final score.** Ruled out (D-18, 254 D-01).
- **Re-running the staged form selection.** D-01/D-03/D-08 fix the shape.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Line replay, legality, malformed tokens | a new move walker | `_replay_line`, `_parse_move` (`line_material.py:162-189`) | Already handles worker-supplied bad tokens (T-250-01) |
| Static exchange at the line end | custom SEE | `_best_recapture` / `_exchange_value` (139-159) | Least-valuable-attacker ordering, king last |
| Desperado rule | a second copy | one extracted step helper shared with `_net_loss` | One rule, two walks |
| Decaying mean, mates, caps, floors | new aggregation code | `material_loss` / `material_missed` / `decaying_mean` (Python) | Same semantics the spike and the owner's labels were measured with |
| Sharding, resumability, advisory locks, fingerprint | a new backfill script | `backfill_maia_flaws.py` + `write_game_maia_scores` (new mode) | Proven on prod 5 times; hash-residue shards; stamp checkpoint |
| Concurrent index build in a migration | raw psycopg calls | `op.get_context().autocommit_block()` + `op.create_index(..., postgresql_concurrently=True, if_not_exists=True)` | Precedent `b7c1d9e2f3a4`, `84fd28051d7d` |
| Read-only prod access for review / features | ad-hoc engines | `scripts/blunder_check/sample.make_readonly_engine` | `default_transaction_read_only = on` + statement timeout |
| Reader test seeding | per-test hand-built facts | `tests/facepalm_seed.facepalm_fact_columns` (rewritten for scalars) | Solves the target score through the twin, survives refits |

**Key insight:** every new piece is a small extension of a seam that already exists. The risk in this phase is release ordering and missed readers, not new algorithms.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Prod `game_flaws`: ~4.7M blunders with arrays (both sides) and reply spreads (CONTEXT D-10 counts). New columns NULL after R1 until the line pass (scalars) and the reply pass. Benchmark DB: same columns, stays NULL (D-10, deferred to SEED-261120-bzq). Dev: 58,295 blunders, 21,164 with arrays, 21,179 with spread [VERIFIED: dev query this session] | Data passes: line pass (Maia-free), reply pass (Maia). Code edits: hook + modes write new columns. DROP: arrays deleted (one-way) |
| Live service config | None. No external service stores score inputs [VERIFIED: nothing outside the DB reads them; frontend grep empty] | None |
| OS-registered state | None (operator runs are ad-hoc `setsid nohup` processes, no cron/systemd) | None |
| Secrets/env vars | None renamed. Prod writes use `db_url_for_target("prod")` (existing env var, never printed) | None |
| Build artifacts | Committed reports under `reports/blunder-check/` (features TSVs 2026-11-13/15/16, fit reports) become non-reproducible once the old twin is gone; the `quick/facepalm-prelim-bands` worktree (`/home/aimfeld/Projects/Games/flawchess-facepalm-bands`, branch at `6d65c1d66`) derives bands from the old score [VERIFIED: `git worktree list`] | Keep reports as history; prelim bands re-derived after SW (CONTEXT) |

## Common Pitfalls

### Pitfall 1: Quiet walk off the end of a 12-ply line
**What goes wrong:** at depth 7/9 the capture chain often reaches the end of the stored line; the SEE settlement then decides the value (labels 153, 154, 156, 170 above).
**How to avoid:** apply SEE only when the walk consumed the whole line and the last move was a non-mating capture; test both signs (opponent vs blunderer last). Show these in the D-09 report (they weigh 1/31 and 2/31 in the mean, small but visible).

### Pitfall 2: A mating first move with no rest
**What goes wrong:** the spike returns all-None when the rest of the line is empty, so a best move that mates by itself loses its missed-mate value.
**How to avoid:** keep `_facts_after_first_move`'s mate-first branch (264-276) ahead of the "line too short" checks; add a unit test (best move mates, one-token best pv).

### Pitfall 3: Coverage drift between rules
**What goes wrong:** the quiet rule settles some short lines the old rule left unknown (a 1-2 ply line ending on a blunderer capture), and vice versa the old `_recapture_credit` only applied to lines under 10 plies. The number of scored rows changes slightly at SW.
**How to avoid:** report old-vs-new scored counts in the readiness gate; do not treat a small coverage change as a bug.

### Pitfall 4: Line mode overwriting the reply prob with NULL
**What goes wrong:** `LINE_ROW_COLUMNS` (819) is `FACEPALM_COLUMNS` minus the spread; adding the reply prob to `FACEPALM_COLUMNS` makes every line pass NULL it out. Same key-set pins in tests (`test_maia_flaw_scoring.py:753, 1060`).
**How to avoid:** separate `FACEPALM_REPLY_COLUMNS`; a test that a line-mode row has no reply key.

### Pitfall 5: `CREATE INDEX CONCURRENTLY IF NOT EXISTS` and invalid or drifted indexes
**What goes wrong:** a failed CIC leaves an INVALID index that still costs writes; `IF NOT EXISTS` checks the name only ("no guarantee that the existing index is anything like the one that would have been created") [CITED: postgresql.org/docs/current/sql-createindex.html]. The migration then silently accepts a wrong or invalid prod index.
**How to avoid:** generate the operator SQL by compiling the ORM `Index` (never hand-type it), then check `pg_index.indisvalid` and compare `pg_get_indexdef(...)` with the expected text; on failure `DROP INDEX CONCURRENTLY` and retry. CIC cannot run in a transaction (autocommit connection) and waits for older transactions on the table; run it with no other operator job.

### Pitfall 6: CASE with a NULL condition falls to ELSE
**What goes wrong:** `CASE WHEN loss > 0 THEN reply_term ELSE best_term END` with `loss IS NULL` takes the ELSE branch. Today the NULL loss still propagates through `loss_coef * loss`, but a zero loss coefficient or a refactor would hide it.
**How to avoid:** explicit `loss IS NULL → NULL` branch first, as the current twins do (`_loss_sql` 484-488). Keep the grid parity test with NULL in every input.

### Pitfall 7: Switching before the backfill is complete
**What goes wrong:** every losing row without a reply prob or without `material_loss` becomes unscored at SW: chips vanish, drill candidates drop (D-11 violated).
**How to avoid:** the readiness gate (Pattern 4) is a blocking precondition of the switch deploy, re-checked right before the deploy (the hook keeps rows current after R1).

### Pitfall 8: Old process running across the drop
**What goes wrong:** an operator script built before DROP selects a dropped column and fails mid-run (254 drop rule).
**How to avoid:** no operator script during the drop deploy; ship the DROP code (writers stop) before or with the migration.

### Pitfall 9: `FACEPALM_STATS_MIN` is coupled to the frontend 70%
**What goes wrong:** the owner may set `FACEPALM_STATS_MIN` at D-15, but the frontend High preset, the "???" badge and copy use `FACEPALM_HIGH_CUTOFF = 70` (`frontend/src/lib/facepalm.ts:35-40`: "The backend FACEPALM_STATS_MIN is pinned to the same 70% by test"; `blunder_check_rules.py:61-65`; `test_facepalm_score.py:1220` `test_facepalm_stats_min_is_the_high_preset_cut`).
**How to avoid:** if the owner moves the stats cut, the switch release must also move `FACEPALM_HIGH_CUTOFF` and its copy, a small frontend change (run `npm run build`). State this at the checkpoint.

### Pitfall 10: Features pull fails on a deleted game
**What goes wrong:** `facepalm_features.py` exits 5 when any label row's game is missing; one is gone from prod.
**How to avoid:** explicit skip flag that records the missing rows in the report.

### Pitfall 11: Reader tests that grep compiled SQL for the array name
**What goes wrong:** `tests/test_query_utils.py:526,533,539` and `tests/test_library_repository.py:2743` assert `"played_line_material" in sql`; they fail at SW.
**How to avoid:** switch them to `material_loss` in the SW plan.

### Pitfall 12: Worktree and checkout hazards
**What goes wrong:** a fresh worktree has no DB config and misses the `maia-inference` group; concurrent sessions in one checkout land commits on the wrong branch; the GSD commit helper can recreate the phase branch.
**How to avoid:** prod runs with cwd at the main checkout; `git branch --show-current` before each commit/push report; a binding branch map like 254-06.

## Code Examples

### Quiet loss at one depth (production shape of the spike's `quiet_loss`)
```python
# Source: .planning/phases/259-facepalm-first-principles-refit/spike/quiet_spike.py (rule reference),
# helpers from app/services/line_material.py. Names are proposals.
def _quiet_loss(
    first_victim: int, steps: list[_Step], depth: int, end_board: chess.Board
) -> int | None:
    """Net loss at `depth`, read at the first quiet point at or after it (259 D-02)."""
    if not steps:
        return None
    last = steps[-1]
    ends_in_exchange = bool(last.victim_value) and not (last.blunderer_mated or last.opponent_mated)
    mated = any(step.blunderer_mated or step.opponent_mated for step in steps[:depth])
    if len(steps) < depth and not mated and not ends_in_exchange:
        return None  # line too short to tell (250 D-05, 256 D-03)
    loss, quiet_square = -first_victim, None
    index = 0
    while index < len(steps) and (index < depth or steps[index].victim_value):
        loss, quiet_square = _count_step(loss, quiet_square, steps[index])  # shared with _net_loss
        index += 1
    if index == len(steps) and ends_in_exchange:
        swing = _best_recapture(end_board, last.to_square)
        loss += -swing if last.opponent_move else swing
    return loss
```

### D-13 fixture (unit test data, verified on dev)
```python
# Source: dev DB game 2883555 (same lines as the prod row in the seed), replayed this session.
PRE_FEN = "2k3rr/ppq5/2pbp3/3p1p1p/5N2/3P3B/PPP2Q2/R4R1K b - - 3 24"
PLAYED = "c8d7"
REFUTATION = "f4e6 f5f4 e6c7 d7c7 f1g1 g8g4 a1f1 c7b8 f2d4 h8e8 f1e1 e8f8"   # pv @ ply 48
BEST_LINE = "d6f4 f2f4 c7f4 f1f4 c8d7 h1h2 d7d6 a1e1 g8g5 f4f3 g5g6 d3d4"    # pv @ ply 47
# Shipped rule: played [-1,-1,-7,...], best [9,9,0,...]; loss 2.935483870967742, missed 2.5806451612903225
# Quiet rule:   played odd depths -1,-7,-7,-7,-7, best all 0;  loss 2.935483870967742, missed 0.0
```

### Switch migration: covering index, prod no-op
```python
# Source: precedent alembic/versions/20260610_183000_b7c1d9e2f3a4_batch1_index_planner_stats_seed_041.py
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_game_flaws_facepalm_inputs",
            "game_flaws",
            ["user_id", "game_id"],
            unique=False,
            postgresql_include=["ply", "maia_played_prob", "material_loss", "material_missed",
                                "maia_best_prob", "maia_best_reply_prob"],
            postgresql_where=sa.text("severity = 2"),
            postgresql_concurrently=True,
            if_not_exists=True,
        )
```

### Scalar SQL twin (sketch)
```python
def _prob_term(prob: Any, coef: float) -> ColumnElement[Any]:
    if coef == 0.0:
        return literal(0.0)
    return case((prob.is_(None), null()), else_=coef * func.ln(prob + PLAYED_PROB_OFFSET))

def facepalm_score_sql(columns: FacepalmColumns, *, lam: float, model: FacepalmModel) -> ColumnElement[float]:
    _check_lambda(lam)
    key_move = case(
        (columns.loss.is_(None), null()),
        (columns.loss > 0, _prob_term(columns.reply_prob, model.reply_prob_coef)),
        else_=_prob_term(columns.best_prob, model.best_prob_coef),
    )
    z = (model.intercept + model.played_coef * func.ln(columns.played_prob + PLAYED_PROB_OFFSET)
         + model.loss_coef * columns.loss + key_move)
    if model.missed_coef * lam != 0.0:
        z = z + model.missed_coef * lam * columns.missed
    return type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Depth N + one blunderer recapture at N+1 | Quiet point at every depth, SEE at the line end | This phase (D-02) | Even exchanges of any length are neutral |
| 9-slot arrays aggregated in SQL (14-18 KB expressions) | Two stored scalars, short logistic | SW (D-05) | Rule changes need a line pass; refits stay constants deploys |
| Reply spread on losing rows | Maia probability of the best reply | SW (D-08) | Symmetric with `maia_best_prob` for misses |
| Staged shape selection by CV AUC | Fixed shape, coefficients only, alternatives informational | This phase (D-01) | `--check-constants` checks six constants |
| `ix_game_flaws_blunder_facts` (arrays) | New covering index on scalars | SW (D-17) | Old index dropped in DROP |

**Deprecated/outdated after this phase:** `facepalm_material` SQL builders (`*_sql`, `aggregate_sql`, `first_stable*`, `single_depth_material`), `material_at_depth`, `LINE_MATERIAL_SLOTS`, the old `_net_loss` walk, the `legacy`/`facts` fit schemas, `tests/facepalm_models.py`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Column names `material_loss`, `material_missed`, `maia_best_reply_prob`, `games.facepalm_reply_completed_at`, index `ix_game_flaws_facepalm_inputs` | Patterns 2, 4, 8 | Naming only; planner may rename |
| A2 | Reply pass ~18 h at 12 shards, line pass ~2-3 h at 4 shards | Pattern 4 | Schedule only; both are resumable |
| A3 | Building the index before the backfill would bloat it and slow the passes | Pattern 8 | Low; order after the backfill is safe either way |
| A4 | JIT is still triggered by plan cost on large accounts; only compile cost shrinks | Pattern 9 | The measurement decides (D-18) |
| A5 | User 95 is still the largest prod account | Pattern 9 | Wrong account measured; re-check by query |
| A6 | `op.create_index` with `postgresql_include`, `postgresql_concurrently` and `if_not_exists` together compiles to valid CIC IF NOT EXISTS SQL | Pattern 8 | Rehearse on dev; fallback `op.execute` with literal SQL as in `b7c1d9e2f3a4` |
| A7 | Retiring the legacy fit schemas and their reproduction tests is acceptable | Pattern 7 | Owner may want old fits reproducible; then keep a frozen copy of the old twin in `scripts/` |

## Open Questions (prod facts for the orchestrator; no prod access here)

1. **Which label row's game is gone from prod, and is the D-13 fixture row unchanged on prod?** Dev has 2883555:47 with the seed's arrays (`{-1,-1,-7,...}`, `{9,9,0,...}`), `maia_played_prob 0.030116068`, `maia_reply_spread 7.351584` [VERIFIED: dev]. Recommendation: confirm on prod in the D-09 run.
2. **Prod size and build time of the old index, and the prod `statement_timeout` / `maintenance_work_mem` for the operator role.** Needed to size the CIC run. Recommendation: `pg_relation_size('ix_game_flaws_blunder_facts')` and `SHOW` on prod before the CIC.
3. **Blunders with a stored played prob but no refutation pv (reply-prob residue), both sides.** Recommendation: count on prod after R1 to predict the post-switch coverage change.
4. **Current largest account for D-18.** Recommendation: top users by blunder count on prod.
5. **Can the features pull (290 rows, read-only, ~minutes) run during the reply pass?** D-11 says one operator run at a time; the pull uses one connection. Recommendation: ask the owner, default to sequential.
6. **Does the owner want to keep the old fit runs reproducible (A7)?** Recommendation: raise at the D-09 checkpoint, default to retiring.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev (Docker `flawchess-dev-db-1`) | tests, rehearsals | ✓ | 18.6, `jit = on`, `max_connections = 300` | — |
| Benchmark DB container | migration rehearsal (D-10) | ✓ (`flawchess-benchmark-db-1` running) | — | — |
| uv / Python | everything | ✓ | uv 0.10.9, Python 3.14.3 (venv) | — |
| onnxruntime (maia-inference group) | reply pass, features pull | ✓ | 1.29.0 | — |
| Maia model `frontend/public/maia/maia3_simplified.onnx` | Maia runs | ✓ | 45.7 MB | — |
| Prod tunnel `bin/prod_db_tunnel.sh` | all prod runs | script present | — | none: orchestrator only |
| CPU for shards | reply pass | ✓ | 16 cores | fewer shards |
| `temp/facepalm-257/gen_shipped_sql.py` | D-18 | ✓ (gitignored, local) | — | rewrite from library_repository |
| Spike outputs `temp/facepalm-259/*.tsv` | D-09 context | ✓ (gitignored) | — | re-run review tool |

**Missing dependencies with no fallback:** none for code work. All prod steps need the orchestrator (subagents have no prod access).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-xdist, pytest-asyncio), per-worker cloned PG test DBs from a migrated template |
| Config file | `pyproject.toml` / `tests/conftest.py` |
| Quick run command | `uv run pytest tests/services/test_line_material.py tests/services/test_facepalm_score.py -x` |
| Full suite command | `uv run pytest -n auto -x` (plus ruff, ty x2, function-size gate, frontend gate) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-02 | Quiet walk: long exchange neutral, SEE at line end (both signs), desperado kept, mate-first best move, too-short NULL, malformed tokens | unit | `uv run pytest tests/services/test_line_material.py -x` | ✅ extend (add `expected_quiet_loss` to `LineFixture`) |
| D-13 | 2883555:47 gives missed 0.0, loss 91/31 | unit | same | ❌ new fixture |
| D-03/D-04 | Stored scalars equal `material_loss`/`material_missed` on quiet arrays; NULL pair invariant | unit | `uv run pytest tests/services/test_facepalm_material.py -x` | ✅ extend |
| D-05/D-07 | Hook writes scalars + reply prob both sides; full row key set | integration (DB) | `uv run pytest tests/services/test_maia_flaw_scoring.py -x` | ✅ extend |
| D-07 | Line mode writes scalars, never the reply prob; reply mode writes only the reply key, stamps, resumes (second run selects 0), status counts | integration | `uv run pytest tests/scripts/test_backfill_maia_flaws.py tests/services/test_maia_flaw_scoring.py -x` | ✅ extend |
| D-11 | Stamps: full sets reply stamp, clear helper clears it, lane assert | integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -k stamp -x` | ✅ extend (`maia_fakes.py`) |
| D-08 | Scalar twin parity grid (NULL in every input, both branches, lambda 0/1), zero-coef omission, NULL reply on losing row unscored, NULL best on pure miss unscored, type twin parity | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -x` | ✅ rewrite at SW |
| D-08 | `facepalm_expr` over stored scalars equals Python twin; seed helper reaches targets | DB | `uv run pytest tests/services/test_facepalm_seed.py -x` | ✅ rewrite at SW |
| D-17 | New index covers every `_game_flaw_columns` input; migration-built index exists in the test template | unit + DB | `uv run pytest tests/services/test_flaw_comparison.py -k index -x` | ✅ re-point |
| D-18 | JIT tests kept or removed with the helper; expression size guard | unit | `uv run pytest tests/services/test_flaw_comparison.py -k jit -x` | ✅ / ❌ guard |
| D-12/D-15 | Fit: fixed shape, deterministic report, `--check-constants` round trip on the committed TSV, info-only alternatives, missing-row flag | unit | `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_facepalm_features.py -x` | ✅ rewrite |
| D-09 | Review tool cause classification on synthetic lines and the 4 changed fixtures | unit | `uv run pytest tests/scripts/test_quiet_rule_review.py -x` | ❌ new |
| SW readers | Compiled SQL names the new columns | unit | `uv run pytest tests/test_query_utils.py tests/test_library_repository.py -x` | ✅ update strings |
| Rule tripwire | Material rule constants pinned with "needs a line pass" message | unit | `uv run pytest tests/services/test_facepalm_material.py -k tripwire` | ❌ new |
| DROP | No reader of the arrays left (grep-based test or plan step), shape-CHECK tests removed | unit | full suite | ✅ |

Manual / prod-only (orchestrator, cannot be automated in CI): the D-09 review run, line and reply passes with status counts, the readiness gate, the CIC + `indisvalid`, features pull, calibration, owner checkpoints, D-18 EXPLAIN ANALYZE.

### Sampling Rate
- **Per task commit:** the touched test files (quick command above).
- **Per wave merge / before each squash-merge:** full pre-merge gate (CLAUDE.md), and once before a release the full **serial** suite (memory: `-n auto` green is not serial-CI green).
- **Phase gate:** full suite green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/services/line_material_fixtures.py`: `expected_quiet_loss` per fixture + the 2883555:47 fixture (FEN, played move, both lines above).
- [ ] `tests/scripts/test_quiet_rule_review.py` for the review tool.
- [ ] Owner fixtures (`tests/services/facepalm_owner_fixtures.py`, games 817357:24 and 820181:65, on dev only) need the reply prob and the quiet scalars; pull from dev with real Maia.
- [ ] Window 14 test (`test_facepalm_score.py:939-957`) re-pointed to the new features TSV.

## Security Domain

Internal scoring change, no new endpoints, no auth or session change.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (unchanged) | Readers stay user-scoped (`GameFlaw.user_id == user_id`, `player_only_gate`); the column switch must not drop those predicates |
| V5 Input Validation | yes | Worker-supplied PV tokens parsed with `_parse_move`, legality-checked before use (T-250-01); backfill selector built from constants only, bound parameters for values |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed / illegal UCI in stored lines | Tampering | `_parse_move` + `legal_moves` check, all-None facts, never raises |
| Stale values over a repaired line | Tampering | Fingerprint re-check under the advisory lock (`write_game_maia_scores`) |
| Prod connection exhaustion by operator runs | Denial of service | ≤ 12 shards, one connection each, one run at a time (runbook) |
| Accidental prod writes from report tools | Tampering | `make_readonly_engine` (read-only transactions) for review, features, calibration |
| SQL injection through mode/cutoff | Tampering | Mode picks a constant clause; cutoff is a bound parameter (`backfill_maia_flaws.py:263-297`) |

## Sources

### Primary (HIGH confidence, read or run this session)
- `app/services/line_material.py`, `facepalm_material.py`, `facepalm_score.py`, `maia_flaw_scoring.py`, `maia_flaw_stats.py`, `blunder_check_rules.py`, `maia_encoding.py:168-198`, `maia_engine.py:166-205`
- `app/models/game_flaw.py`, `app/repositories/game_flaws_repository.py`, `library_repository.py` (350-376, 1670-1760, 2560-2640), `library_service.py:2105-2130`, `blunder_check_repository.py` (395-405, 640-672)
- `scripts/backfill_maia_flaws.py`, `scripts/blunder_check/facepalm_features.py`, `fit_facepalm.py` (selected ranges), `sample.py`, `metrics.py:177-206`
- Alembic migrations `a7d2c9e1b254`, `c9f4e1a3d254`, `b7e4a1c9d257`, `b7c1d9e2f3a4`; `alembic/env.py`; Alembic 1.19.2 source (`ddl/postgresql.py`, `operations/ops.py`, `autogenerate/compare/__init__.py`)
- Dev DB: fixture row 2883555:47, PG 18.6 DROP COLUMN probe; quiet rule run on the committed fixtures
- Phase artifacts: 259-CONTEXT, SEED-261121-tau, spike scripts, 254-06/07/11 plans and summaries, 254-RESEARCH Pattern 3, 257-UAT, `reports/maia-flaws-backfill/prod-facepalm-spread-coverage.md`
- `frontend/src/lib/facepalm.ts:30-45`, `docs/production-runbook.md:36`

### Secondary (MEDIUM)
- postgresql.org/docs/current/sql-createindex.html (IF NOT EXISTS, CIC failure and recovery, two scans, no transaction block)

### Tertiary (LOW)
- Duration estimates for the prod passes (extrapolated)

## Metadata

**Confidence breakdown:**
- Inventory and release mechanics: HIGH (every location read this session)
- Material rule mapping: HIGH (spike reproduced, fixtures run)
- Backfill sizing and JIT outcome: MEDIUM / LOW (extrapolation, needs prod)

**Research date:** 2026-11-21
**Valid until:** 2026-12-21 (codebase moves fast; re-grep the inventory if another phase touches the facepalm files)

## Orchestrator Prod Answers (2026-11-21, read-only prod MCP)

Answers to the open questions above that a prod SELECT could settle:

- **Fixture (Q1):** prod row 2883555:47 is unchanged: `played_line_material = {-1,-1,-7,-7,-7,-7,-7,-7,-7}`,
  `best_line_material = {9,9,0,0,0,0,0,0,0}`. Which label game is gone from prod was not checked; the features
  pull needs the skip flag either way.
- **Old index size (Q2):** `ix_game_flaws_blunder_facts` is 741 MB on prod. The read-only MCP role reports
  `statement_timeout = 0` and `maintenance_work_mem = 512MB`; these are that role's settings, the operator
  role's values must be read in the operator session before the concurrent build.
- **Reply-probability rows (Q3):** 4,688,557 blunders have `maia_played_prob`, 4,687,985 have
  `maia_reply_spread`. Rows without a refutation line were not counted separately.
- **Largest account (Q4):** user 95 with 164,696 blunders (then 288 with 100,127 and 11 with 94,013). Use user
  95 for the D-18 EXPLAIN ANALYZE.
- **Q5 and Q6 are owner decisions:** plan operator runs strictly one at a time (D-11), and put the retirement
  of the old fit runs' reproducibility in front of the owner at a checkpoint.
