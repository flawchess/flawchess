# Phase 254: Facepalm Score Missed Gains and Loss-Aversion Knob (SEED-261114-mg7) - Research

**Researched:** 2026-11-14
**Domain:** Internal: facepalm score model (Python/SQL twin), `game_flaws` storage migration, Maia/line backfill passes, logistic refit tooling, blind label sampling
**Confidence:** HIGH for the codebase map and mechanics; MEDIUM for the fit design (depends on labels not yet collected); the prod-side numbers are from committed reports, not measured this session.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (not re-discussed)
- The knob is wanted regardless of how the loss-aversion question is answered (seed, owner 2026-11-14).
- Missed gains are valid drill items: the drill asks "Good move or blunder?" (seed).
- The score is a ranking, never presented as a probability or a share of peers (250 D-01, 253 D-03).
- False alarms are worse than misses; tune for the fair share among passers (250 D-03).
- Scope is user-side blunders only (250 D-06). No engine at scoring time (250 D-07).
- Fitted values are named constants in `app/services/blunder_check_rules.py`; the fit lives in
  `scripts/blunder_check/` and `--check-constants` reproduces the constants from a committed features TSV (250 D-04).
- Long prod runs are started by the orchestrator, detached, never by an executor; operator connections stay under
  about 25 (prod `max_connections` 50).
- Library band cutoffs 30/70 are UI constants, independent of the drill cut (253 D-09).

#### Where lambda lives
- **D-01: The score is computed at query time.** `game_flaws` stores only facts; every consumer calls the SQL score
  expression with its own lambda. A refit or a lambda change is a constants deploy with no UPDATE pass over prod.
  Consequence: plan 250-10's score recompute and its mixed-score window (T-250-38) no longer exist.
  - Measured on dev (user 28, 18.6k flaws, 4.6k scored): filter on the stored column 38 ms, on the full expression
    25 ms, same plan (`ix_game_flaws_user_severity`, then filter). No index on the score exists today. Dev only; not
    measured on prod or for the drill's foreign-pool queries, which probe flaws by game id.
  - The chip percent and the filter must come from the same SQL expression, so a score at a band edge cannot show in
    one band and filter into another (253 D-10, and the float note in `library_repository._facepalm_clause`).
  - The Python and SQL twins stay pinned together by `tests/services/test_facepalm_score.py`.
- **D-02: Drop the stored `facepalm_score` column in this phase,** as the last, human-gated plan (same shape as
  250-11): once every reader uses the expression and prod is checked, stop writing it in the hook and the backfill
  and drop it. — **Reversibility:** one-way — needs an Alembic migration; the values are re-derivable from the
  stored facts, but a rollback to the stored-column readers needs a column re-add and a prod pass.
- **D-03: Drill lambda = 1.0 (symmetric).** Blunder-check selection ships symmetric while GM Noel Studer's answer is
  pending. One named constant, lowered if he says the drill should be loss-averse. Expect a larger drill pool
  (no-refit estimate from the seed: 27% to 40% of blunders pass; direction only).
- **D-04: Library lambda = 1.0, as its own named constant.** Facepalm chip, Facepalm Score filter, analysis move
  list and eval chart tooltip use it. Separate from the drill constant so the two can diverge.

#### Model form for misses
- **D-05: Material definitions** (depth `LINE_DEPTH` = 3, blunderer's side, baseline = position before the blunder):
  `loss = max(0, -played[3])`, `swing = best[3] - played[3]`, `missed = swing - loss`. Lambda multiplies the missed
  term: lambda = 0 reproduces a loss-only score, lambda = 1 is the model as fitted.

  | Case | played[3] | best[3] | loss | missed |
  |---|---|---|---|---|
  | Hangs a rook, nothing better was on | -5 | 0 | 5 | 0 |
  | Rxf5 (wins 5) instead of Qxh1 (wins 10) | +5 | +10 | 0 | 5 |
  | Hangs a rook and misses a free piece | -5 | +3 | 5 | 3 |

- **D-06: The fit script compares two forms** and picks by cross-validated AUC and the fair share at the cut (as
  250 did for the loss floor): (a) one material coefficient on `loss + missed`; (b) separate loss and missed
  coefficients. The fit report states the choice. Under (b), lambda = 1 means "as the owner labelled", not the
  symmetric swing.
- **D-07: Reply spread for pure misses is decided by the fit** among named forms: spread as today; spread applied
  only when `loss > 0`; spread replaced for misses by the best-move probability. Same selection criteria as D-06.
- **D-08: Store both pre-blunder Maia inputs; each must earn its coefficient.** Best-move probability (how findable
  the gain was; the `maia_best_prob` dropped in 250 D-11) and the pre-blunder policy spread (effective number of
  moves, the `maia_effective_moves` formula). Both come from the policy call at the flaw position that already
  yields `maia_played_prob`. An input enters the score only if it improves cross-validated AUC or the fair share at
  the cut; one that earns nothing stays stored for later refits.
- **D-09: Line facts as two symmetric arrays** (owner: symmetric for gains and losses, fewer columns):
  - `played_line_material SMALLINT[]`: the blunder move, then the opponent's stored best reply line (`pv` at flaw
    ply + 1). This is what `line_loss_1/3/5/7/9` hold today.
  - `best_line_material SMALLINT[]`: the best move from the pre-blunder position, then its stored line (`pv` at the
    flaw ply: first token is the move, the rest the line).
  - Slot N = net material at depth N, depths 1 to 9, signed, positive = blunderer up. This flips the sign of today's
    loss columns. A depth the line does not reach is NULL ("line too short to tell", as in 250 D-05).
  - One mate-ply column per side (today's `line_mate_ply` plus its best-line counterpart).
  - The five `line_loss_*` columns are replaced: existing values copy into the array with a plain UPDATE (sign
    flipped), no replay. Four columns in total instead of twelve.
  - Storage cost is an estimate, not measured: roughly 40 bytes more per scored blunder than split columns, about
    100 MB over prod's 2.3M user blunders. Unscored rows stay NULL.
  - 250 D-02's counting rules (captures only, recapture at depth + 1, desperado exclusion, static-exchange credit)
    apply to both lines.
  — **Reversibility:** costly — an Alembic migration plus changes to every reader of `line_loss_*` (hook, backfill,
  `scripts/blunder_check/`); the data itself is preserved.
- **D-10: No forcing flag.** Both stored lines are engine lines, so a depth-3 gain is against best defence whether
  or not the line is forcing. Obviousness is covered by reply spread (loss side) and best-move probability (gain
  side). Named fallback, not scope: if the fit shows quiet-move misses scoring too high, add a "best move is a
  capture or check" fact in the line pass.

#### Refit sequencing
- **D-11: Plan 250-10 is folded into this phase.** One refit, on the repaired lines, with the new inputs and the
  miss labels. 250-10 is closed as superseded by Phase 254 and Phase 250 completes; record that in ROADMAP.md and
  the 250 phase docs.
- **D-12: Build everything now, behaviour unchanged until the refit.** Before Phase 252's prod repair finishes:
  columns and migration, hook, query-time expression, backfill tooling, the labelling, and the prod Maia pass (it
  does not read lines). Consumers switch to the expression with today's coefficients and a zero missed term, so
  scores stay as they are. After 252 (252-06 SUMMARY records EXIT_FULL=0 and `scripts/repair_short_lines.py status
  --db prod` shows nothing left): prod line pass, refit, new constants, then the D-02 column drop.
- **D-13: `FACEPALM_SCORE_MIN` is set by the owner at a blocking checkpoint,** keeping the 250 policy (somewhat
  below the precision-optimal cut, so drill answers cover both sides). The fit report must show fair / unfair among
  passers at several cuts, split by loss-type and miss-type, and the drill pool size per rating band, own and
  foreign.

#### Miss labels
- **D-14: About 50 new rows, mostly pure misses, stratified.** About 40 pure misses (loss 0) spread over missed size
  (1, 3, 5, 9+) and over best-move probability, so the fit sees easy and hard misses; about 10 mixed rows (loses and
  misses). Blind as in 250: score and inputs hidden while labelling; output a TSV like `leg2-labels-2026-11-11.tsv`.
- **D-15: Drawn from prod, all users, movers below 2000,** the population of the 180 existing labels, so the sets
  pool. Limited to rows whose stored lines are already repaired or were never short, so the features do not change
  after 252.
- **D-16: The 180 existing labels stay in the fit, on top of the 50** (about 230 labels). Their best lines are
  pulled from prod; the 17 no-loss rows labelled fair become miss-type evidence.

### Claude's Discretion
- Column names, the array bounds check, and whether the best-line mate ply feeds a `MATE_LOSS`-style missed value
  (propose in the fit; a missed mate within `LINE_DEPTH` should not score as "nothing missed").
- Whether the missed term gets its own cap or shares `LOSS_CAP`; decided by the fit script.
- Minimum missed gain that defines a "miss" for the D-14 sample.
- Backfill shard count and pacing; whether the Maia pass and the line pass share the Phase 250 script.
- API shape: the score still travels as today (`facepalm_score` on the library schemas); lambda is not an API
  parameter.
- Whether the calibration and spot-check reports (`scripts/blunder_check/`) are re-run in full or only the supply
  table D-13 needs.

### Deferred Ideas (OUT OF SCOPE)
- **Loss-aversion weight for the drill** below 1.0: waits for GM Noel Studer's answer; a constant change, no phase.
- **Forcing flag** ("best move is a capture or check"): only if the fit shows quiet-move misses scoring too high
  (D-10).
- **Rating-dependent line depth** and labels above 2000 (250 deferred): the arrays hold depths 1 to 9, so a later
  refit needs no prod pass.
- **Refit from drill answers** (250 deferred): unchanged.
- **Facepalm rate in stats:** SEED-261114-iuv.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs exist for this phase; the CONTEXT decisions are the contract.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Score computed at query time with a per-consumer lambda; chip and filter from one SQL expression | Reader inventory (Pattern 6), twin design (Pattern 1), Pitfalls 1, 3, 4, 9 |
| D-02 | Drop stored `facepalm_score` as the last human-gated plan | Pattern 9 (drop plan), Runtime State Inventory, precedent `f9c4d7e3a250` |
| D-03 | Drill lambda constant = 1.0 | Pattern 1 constants block; readers in `blunder_check_repository` |
| D-04 | Library lambda constant = 1.0 | Readers in `library_repository` / `library_service` |
| D-05 | loss / swing / missed definitions | Derivation `missed = best3 - max(0, played3)`, Pitfall 5 (GREATEST/LEAST NULL), Code Example 2 |
| D-06 | Fit compares one material coef vs split coefs | Pattern 7 (fit staging), Pitfall 10 (selection noise), Pitfall 11 (name clash with existing Form A/B) |
| D-07 | Spread form for pure misses decided by fit | Pattern 1 (model space), Pitfall 6 (NULL gating in twins) |
| D-08 | Store best-move prob and pre-blunder spread; each must earn a coefficient | Pattern 4 (hook + `pre` Maia mode), Pitfall 7 (best-move source) |
| D-09 | Two SMALLINT[] arrays + mate ply per line; copy existing values sign-flipped | Pattern 5 (migration), Pattern 3 (release order + batched copy), Open Question 1 (9 vs 5 slots), Pitfall 2 (best-line mate / empty rest) |
| D-10 | No forcing flag | No work; fallback only |
| D-11 | Fold 250-10 into this phase, close it as superseded | Docs task; 250-10 run book reused (Pattern 8) |
| D-12 | Build now, behaviour unchanged; post-252 line pass, refit, drop | Pattern 3 (two releases), Pitfall 8 (252 connection gate), Open Question 5 |
| D-13 | Owner sets `FACEPALM_SCORE_MIN`; report fair/unfair by loss/miss type + pool per band own/foreign | Pattern 7 report sections; `render.py` supply sections |
| D-14 | ~50 blind miss labels, stratified | Pattern 10 (sampler) |
| D-15 | Prod, movers < 2000, lines already repaired or never short | Pattern 10: both stored lines >= 3 plies |
| D-16 | 180 old labels stay; best lines pulled from prod | `facepalm_features.py` extension (Pattern 7) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend: FastAPI, Python 3.14, SQLAlchemy 2.x async `select()` API, Alembic, asyncpg, Pydantic v2. No new HTTP client; httpx only (not relevant here).
- Layering: routers HTTP only, services hold logic, repositories hold SQL (no SQL in services). The SQL twin lives in `app/services/facepalm_score.py` today as an expression builder; that precedent stands (it builds an expression, it does not execute SQL).
- DB rules: FKs mandatory (no new FK columns here); avoid native ENUM; right-sized column types (SMALLINT for material, REAL for probabilities, matching the existing columns).
- Type safety: explicit return types everywhere; `Literal[...]` for fixed value sets (form selectors must be `Literal`, not `str`); `Sequence[...]` for covariant params; `# ty: ignore[rule]` only with a reason. `uv run ty check app/ tests/ scripts/` must be zero errors.
- No magic numbers: lambdas, caps, floors, miss-size strata, sampler sizes, shard counts are named constants.
- Nesting depth <= 4 per function (gated by `scripts/check_function_size.py app/ --fail-over-depth 4`); `maia_flaw_scoring.py` and `line_material.py` are already close to the guidance, so new branches go in new small helpers.
- Sentry: `capture_exception` in non-trivial `except` blocks in services/routers; no variables in error messages (use `set_context`).
- Never `asyncio.gather` on one `AsyncSession`.
- Pre-merge gate before each squash-merge to `main` (ruff format, ruff check --fix, ty x2, function-size gate, `uv run pytest -n auto -x`, frontend lint/build/test/knip).
- `bin/deploy.sh` / `/deploy` is the only deploy path. Never run `bin/reset_db.sh`. Never touch `.env` files.
- CHANGELOG `## [Unreleased]` bullet when a phase merges to `main`.
- GSD scope: no unplanned features; flag out-of-scope needs.
- Project memory that applies: prod `max_connections=50`, keep operator connections under ~25; long prod runs from the orchestrator (`setsid nohup` + Monitor); executors die on long DB-heavy plans (run those inline); prod has a scheduled reboot around 02:15 UTC that kills tunnels and long runs; benchmark-lane backend on :8001 needs `bin/benchmark_db.sh start` after migrations; fresh worktree gate needs `--group maia-inference`; `asyncpg` JSONB None is JSON null (not relevant to ARRAY, verified below).

## Summary

This is an internal-codebase phase: no new libraries. The score today is a four-input logistic stored in `game_flaws.facepalm_score`, written by the post-commit Maia hook (`app/services/maia_flaw_scoring.py`) and by three backfill modes (`scripts/backfill_maia_flaws.py`). Its inputs are `maia_played_prob`, `maia_reply_spread` and the played-line facts `line_loss_1/3/5/7/9` + `line_mate_ply` computed by `app/services/line_material.line_facts`. The formula exists twice (`facepalm_score` Python, `facepalm_score_sql` SQLAlchemy) and a VALUES-grid test pins them. Six app readers and four script readers consume the stored column.

The phase replaces the stored score with a query-time expression over stored facts, adds a best-line material array, a best-line mate ply and two pre-blunder Maia inputs, and builds a refit that can choose among several model shapes. The single most important planning insight: **because a refit must be a constants-only deploy (D-01), the twins must implement every candidate model shape the fit may pick (D-06 a/b, D-07 three spread forms, D-08 two optional inputs, missed cap/floor, missed-mate value) before the refit, parametrized by named constants including `Literal` form selectors.** Pre-refit constants select the shape that reproduces today's score exactly (split material with missed coefficient 0, spread always, zero coefficients for the new Maia inputs), which is what D-12 "behaviour unchanged" needs. A zero-coefficient input must be omitted from the expression (not multiplied by zero), or a NULL in an unused input silently unscores rows.

The second insight is ordering. Migrations run at backend startup (`deploy/entrypoint.sh`), so the D-09 copy of 2.17M rows must not run inside the migration. Ship **two releases** before Phase 252 finishes: R1 = instant migration (new columns, NOT VALID array CHECKs, new stamp) + writers dual-writing old and new columns + a batched copy tool; the orchestrator runs the copy and the `pre` Maia pass; R2 = all readers switch to the expression (scores identical, verified on prod by comparing the expression to the stored column). After 252: line pass (both lines, cutoff), features + refit + owner checkpoint, constants deploy, then the gated drop of `facepalm_score` and `line_loss_*`. Phase 252's prod repair is far from done (local state shows cursor 145,164 of 1,056,391 games and the run moved to another machine), and its connection gate (`MAX_CONNECTION_RISE: int = 10`) will trip if the `pre` Maia pass launches 12 shards alongside it.

**Primary recommendation:** Build the full candidate model space into `FacepalmModel` + both twins now (pre-refit constants reproduce today), store facts only, ship in two releases (schema/writers/copy, then readers), and keep the refit a constants-only change.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Line material facts (played + best line) | API / Backend (pure service `line_material.py`) | Operator scripts (backfill line pass, features) | Pure CPU from stored lines; one implementation shared by hook, backfill, fit |
| Pre-blunder Maia inputs | API / Backend (post-commit hook `maia_flaw_scoring.py`) | Operator script (`pre` Maia mode) | Reuses the existing flaw-position `full_policy` call |
| Score computation | Database / Storage (SQL expression at query time) | API / Backend (Python twin for hook-era stored column, fit, reports) | D-01: chip and filter from one SQL expression |
| Lambda per consumer | API / Backend (named constants) | — | Not an API parameter (discretion) |
| Library chip / filter / markers | API / Backend (repository selects the expression) | Browser (displays `facepalm_score`, unchanged) | Frontend reads the same field; no frontend change |
| Drill selection | API / Backend (`blunder_check_repository` predicates) | — | EXISTS + filter in SQL |
| Fit, labels, calibration | Operator scripts (`scripts/blunder_check/`) | — | Never imported by the app |
| Schema + copy | Database (Alembic, instant) | Operator script (batched UPDATE) | Migrations run at backend startup; long UPDATEs go to operator tooling |

## Standard Stack

No new libraries. Everything uses the existing pinned stack. [VERIFIED: `uv run python -c` this session]

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.52 | `ARRAY(SmallInteger)` columns, 1-based index access, `CheckConstraint(..., postgresql_not_valid=True)`, expression twin | Already the ORM; ARRAY index is one-based by default [CITED: SQLAlchemy 2.0 docs via Context7 /sqlalchemy/sqlalchemy rel_2_0_55, "Indexed access is one-based by default"] |
| Alembic | 1.19.2 | Migration | Project standard |
| asyncpg | 0.31.0 | Binds Python `list[int | None]` to `smallint[]` with NULL elements | Verified round-trip this session (see Code Example 4) |
| PostgreSQL | 18.6 (dev) | `smallint[]`, `cardinality`, `array_lower`, `array_ndims` | Verified CHECK semantics this session |
| python-chess | 1.11.x | Board replay, legal moves, mate detection | Project standard |
| numpy | 2.5.2 | IRLS fit in `fit_facepalm.py` | Already used by the fit |
| onnxruntime | 1.29.0 | Maia `full_policy` | Pinned (memory: >= 1.30 segfaults on Maia; do not bump) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + pytest-xdist | project pins | Tests | `uv run pytest -n auto` for the full suite |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Two `SMALLINT[]` arrays | Ten split SMALLINT columns | Locked by D-09; arrays chosen |
| Explicit labelled expression columns in selects | ORM `query_expression()` + `with_expression()` | Works [CITED: SQLAlchemy docs, "Query-time SQL expressions as mapped attributes"], but an attribute that silently reads `None` when a query forgets `with_expression` is a correctness trap for the drill filter; prefer explicit labelled columns |
| Copy inside the migration | Batched operator UPDATE | In-migration copy of ~2.17M rows delays backend startup (migrations run in `deploy/entrypoint.sh`); batched copy keeps the migration instant like every Phase 250 migration |

**Installation:** none.

## Package Legitimacy Audit

This phase installs no external packages. No `package-legitimacy check` was needed.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                 eval apply (drain / remote submit / tier-4 submit)          operator backfills
                              │ commit                                       (backfill_maia_flaws.py)
                              ▼                                                    │
               score_game_flaws_after_apply (post-commit hook)          --mode full | spread | pre(new) | line | copy(new)
                              │                                                    │
        load_game_maia_inputs: game + flaws + pv@ply (best line, NEW) + pv@ply+1 (refutation)
                              │
        ┌─────────────────────┴───────────────────────────────┐
        │ score_game (CPU, no session)                         │
        │  full_policy(pre-board) ─► played_prob,              │
        │                            best_prob (NEW),          │
        │                            pre_spread (NEW)          │
        │  full_policy(post-board) ─► reply_spread             │
        │  line_facts(pre, played, pv@ply+1) ─► played_line_material[1..9], line_mate_ply
        │  line_facts(pre, best, rest of pv@ply) ─► best_line_material[1..9], best_line_mate_ply (NEW)
        └─────────────────────┬───────────────────────────────┘
                              ▼
        write_game_maia_scores: advisory lock, fingerprint re-read (now incl. pv@ply), UPDATE facts, stamps
                              │
                              ▼
                        game_flaws (facts only after D-02)
                              │
          ┌───────────────────┼──────────────────────────────────────────┐
          ▼                   ▼                                          ▼
 library_repository     library_service markers                blunder_check_repository
 flaw list + filter     (eval chart, analysis list)            own/foreign EXISTS + load_blunder_flaws
 facepalm_expr(LIB λ)   facepalm_expr(LIB λ)                   facepalm_expr(DRILL λ) >= FACEPALM_SCORE_MIN
          │                   │                                          │
          ▼                   ▼                                          ▼
   FlawListItem.facepalm_score / FlawMarker.facepalm_score (API unchanged)   drill windows

 Refit path (operator): labels TSV ─► facepalm_features.py (prod, read-only; Maia local) ─► features TSV
                        ─► fit_facepalm.py (stages, CV, report, constants block, --check-constants)
                        ─► owner checkpoint ─► constants in blunder_check_rules.py ─► deploy (no prod UPDATE)
```

### Recommended Project Structure (files touched)

```
app/services/
├── line_material.py         # best-line facts, opponent-mate settle, 9-slot signed arrays
├── facepalm_score.py        # FacepalmModel (full candidate space), Python + SQL twins, lambda
├── blunder_check_rules.py   # constants: lambdas, form selectors, new coefs (pre-refit = today)
├── maia_flaw_stats.py       # FacepalmStats keys, best-move prob helper, MaiaReason additions
└── maia_flaw_scoring.py     # pv@ply in inputs + fingerprint, new columns, `pre` mode, stamps
app/repositories/
├── game_flaws_repository.py # FACEPALM_COLUMNS, new stamp mark/clear
├── library_repository.py    # _facepalm_clause + flaw list select the expression
└── blunder_check_repository.py  # both predicates + load_blunder_flaws select the expression
app/services/library_service.py  # facepalm_by_ply from the expression
app/models/game_flaw.py, app/models/game.py
alembic/versions/2026111x_..._phase_254_facepalm_facts.py   # R1 instant
alembic/versions/2026xxxx_..._phase_254_drop_stored_score.py # last, gated
scripts/backfill_maia_flaws.py   # `pre` mode, `copy` mode (or separate script), status counts via expression
scripts/blunder_check/
├── facepalm_features.py     # best line, best prob, pre spread, arrays in TSV
├── fit_facepalm.py          # staged form selection, D-13 sections, extended --check-constants
├── miss_labels.py           # NEW: blind stratified miss sampler (D-14, D-15)
├── sample.py / render.py / spot_check.py  # facts + expression instead of stored score
tests/...                    # see Validation Architecture
```

### Pattern 1: One parametrized model, two twins, pre-refit constants reproduce today

**What:** Extend `FacepalmModel` with every shape the refit can pick, all driven by constants. Both twins branch on the model's selectors at Python build time (static), so the SQL stays a plain expression.

Proposed fields (all new names are proposals; existing names quoted below):
- `material_form: Literal["combined", "split"]` (D-06 a / b). Avoid "form A / form B" because `fit_facepalm.py` already uses `FitForm = Literal["a_log_played", "b_raw_played_binary_loss"]` [VERIFIED: scripts/blunder_check/fit_facepalm.py:76] for a different comparison.
- `loss_coef`, `missed_coef` (split), `loss_floor` (kept), `missed_floor: int | None`, `missed_cap: int`, `missed_mate: int | None` (value for a best-line mate within `LINE_DEPTH`).
- `spread_form: Literal["always", "loss_only", "best_prob_for_misses"]` (D-07).
- `best_prob_coef: float`, `pre_spread_coef: float` (D-08; 0.0 = input not used).

Pre-refit constants: `material_form="split"`, `missed_coef=0.0`, `spread_form="always"`, `best_prob_coef=0.0`, `pre_spread_coef=0.0`, and the existing fitted values unchanged:
```
FACEPALM_INTERCEPT: float = -1.4193
FACEPALM_PLAYED_COEF: float = -0.6629
FACEPALM_SPREAD_COEF: float = -0.3304
FACEPALM_LOSS_COEF: float = 1.1570
FACEPALM_LOSS_FLOOR: int | None = 0
```
[VERIFIED: app/services/blunder_check_rules.py:72-76]. With floor 0, `min(max(x,0),5)` equals today's `max(min(loss3,5),0)`, and `loss = max(0, -played[3])` with `played[3] = -line_loss_3` gives the identical input, so the pre-refit expression equals today's stored score (D-12).

Lambda constants (D-03, D-04), proposed names in the constants block: `FACEPALM_DRILL_LAMBDA: float = 1.0`, `FACEPALM_LIBRARY_LAMBDA: float = 1.0`. Lambda multiplies the missed term only (combined: `loss + lam * missed`; split: `missed_coef * lam * missed_feature`).

**When to use:** every consumer; the fit script builds `FacepalmModel` instances for each candidate and prints the chosen constants.

### Pattern 2: Line facts for both lines from one implementation

**What:** Reuse `line_facts(pre_board, move_uci, rest_pv)` for both lines; for the best line pass the first token of `pv@ply` as the move and the rest as the line. The material code is already blunderer-relative (the blunderer is `board.turn` before the first move), so captures by the best move count in the blunderer's favour exactly like the blunder's own capture.

Required changes (each is a semantic decision the planner must test):
1. **Opponent mated settles the line.** Today `_replay_line` only flags `blunderer_mated`, and `_loss_at_depth` returns None when the walk ends early without a blunderer mate [VERIFIED: app/services/line_material.py:159, 196-209]. A best line ending in mate of the opponent would give NULL `best[3]`. Add an `opponent_mated` flag and settle on either mate.
2. **Mate by the first move.** `line_facts` returns all-None when `pv` is empty [VERIFIED: app/services/line_material.py:227-228, 236-238]. A missed mate-in-1 has a one-token best line, so the rest is empty. The best-line path must push the first move, detect mate, and return settled facts with best mate ply 0.
3. **Sign flip at the output layer only.** Keep `_net_loss` and `loss_by_depth` as they are (the 250 fixtures #153, #156, #165, #170, #176, #177, #13, #35, #154, #184 pin them) and add an accessor that returns the signed 9-slot array (`material[N] = -loss_at(N)`).
4. **Depth set.** Today `LINE_LOSS_DEPTHS: tuple[int, ...] = (1, 3, 5, 7, 9)` [VERIFIED: app/services/line_material.py:36]. See Open Question 1 for 9 slots vs 5.

Measured on the two owner fixtures with today's `line_facts` (dev DB, read-only, this session): game 817357 ply 24 played `c5a3` gives losses 0 at every depth (played[3] = 0); best `d4g7` gives -3 (best[3] = +3), so missed = 3. Game 820181 ply 65 played `f8f5` gives -5 (played[3] = +5); best `d5h1` gives -10 (best[3] = +10), so missed = 5, matching the D-05 table row. Both stored scores are about 0.02.

### Pattern 3: Two releases before the refit (D-12), copy outside the migration

1. **R1 (behaviour-neutral):** instant migration (ADD COLUMN nullable, no default; array CHECKs `NOT VALID`; new games stamp). Writers dual-write: the hook and every backfill mode write the new facts AND keep writing `line_loss_*`, `line_mate_ply` and `facepalm_score` (stored, today's model). Readers unchanged. Ships the copy tool and the `pre` Maia mode.
2. **Orchestrator after R1:** batched copy `played_line_material = ARRAY[-line_loss_1, NULL, -line_loss_3, NULL, -line_loss_5, NULL, -line_loss_7, NULL, -line_loss_9]` (or the 5-slot variant), only where `played_line_material IS NULL` and some `line_loss_*` is not NULL, batched by game id via `ix_game_flaws_game_id`, throttled, resumable. Then the `pre` Maia pass. Check: `count(*) WHERE line_loss_3 IS NOT NULL AND played_line_material IS NULL` = 0.
3. **R2 (readers switch):** every reader uses the expression with its lambda. Prod check before D-02: sample `abs(expression - facepalm_score)` over scored rows, max below float4 precision (about 1e-6), and identical qualifying counts at `FACEPALM_SCORE_MIN`.
4. **After 252:** line pass with a cutoff (now writes both arrays and both mate plies), features + refit + owner checkpoint, constants-only deploy, recheck pool, then the gated drop.

Why not one release: migrations run on backend startup [VERIFIED: deploy/entrypoint.sh:4-5 `alembic upgrade head`], and an in-migration UPDATE of the ~2.17M scored rows would block startup. A single release with readers switched before the copy would drop chips and drill candidates until the copy ends. A transitional `COALESCE(played_line_material[3], -line_loss_3)` inside the expression also works but leaves fallback code in the twin that the parity grid does not cover; two releases are simpler.

### Pattern 4: Pre-blunder Maia inputs (hook + `pre` mode)

**Hook (full mode):** `_derive_flaw_values` already calls `probs = full_policy(board.fen(), elo)` at the flaw position [VERIFIED: app/services/maia_flaw_scoring.py:458]. For a user blunder, add `best_prob = probs.get(best_uci)` and `pre_spread = reply_spread(probs)` (the 247 effective-moves formula, `_effective_moves` [VERIFIED: app/services/maia_flaw_stats.py:71-74]). No extra inference.

**Inputs:** `_flaw_fingerprint_select` joins only `gp_next` at `ply + 1` today [VERIFIED: app/services/maia_flaw_scoring.py:172-200]. Add a second outer join at `ply` for the best line, and add it to `FlawMaiaInput` and to the fingerprint. Today `FlawFingerprint = tuple[int, str, int, str | None]` [VERIFIED: app/services/maia_flaw_scoring.py:99]; Phase 252 can rewrite the pv at the flaw ply too, so best-line facts derived from a pre-repair line must not be written over a repaired one.

**Backfill `pre` mode (proposed new mode):** one inference at the pre-blunder position per user blunder, writes only `maia_best_prob` and the pre-spread column, never touches `maia_played_prob`, stamps a new games column (proposed `facepalm_pre_completed_at`). Existing modes: `ScoringMode = Literal["full", "spread", "line"]` [VERIFIED: app/services/maia_flaw_scoring.py:93], `BACKFILL_MODE_CHOICES: tuple[str, ...] = ("full", "spread", "line")` [VERIFIED: scripts/backfill_maia_flaws.py:129], selectors in `_STAMP_CLAUSE_BY_MODE` [VERIFIED: scripts/backfill_maia_flaws.py:164-168]. The new stamp must also be set by full mode (`_mark_stamps`) and cleared by `clear_maia_flaws_completed` [VERIFIED: app/repositories/game_flaws_repository.py:362-391], which has three callers outside the module (`eval_apply.py`, `scripts/backfill_flaws.py`, `scripts/opening_cache_repair.py`).

Sizing reference: the Phase 250 spread pass did one inference per user blunder on prod with 12 shards at about 32 games per second, 1,035,046 games over two legs, about 9 hours, prod connections 28 of 50 [VERIFIED: .planning/phases/250-facepalm-blunder-selection/250-09-SUMMARY.md:57]. The `pre` pass is the same shape.

### Pattern 5: Migration shape

- Precedent: "Deliberately metadata-only: no server_default, no CHECK constraint, no index and no data UPDATE. A nullable ADD COLUMN without a default is a catalog-only change" [VERIFIED: alembic/versions/20261113_120000_e8b3c6d2f250_phase_250_facepalm.py:21-24]. Down revision for the new migration: current head `f9c4d7e3a250` [VERIFIED: alembic/versions/20261114_120000_f9c4d7e3a250_phase_250_drop_maia_columns.py:42].
- Columns (names are discretion; proposals): `game_flaws.played_line_material SMALLINT[]`, `best_line_material SMALLINT[]`, `best_line_mate_ply SMALLINT`, `maia_best_prob REAL`, `maia_pre_spread REAL`; `games.facepalm_pre_completed_at TIMESTAMPTZ`. Keep `line_mate_ply` as the played-line mate ply (no rename, no copy needed; D-09's "today's `line_mate_ply` plus its best-line counterpart").
- Array bounds check (discretion): `CHECK (x IS NULL OR (cardinality(x) = 9 AND array_lower(x, 1) = 1 AND array_ndims(x) = 1)) NOT VALID`. Verified on PostgreSQL 18.6 this session: NULL passes, `'{}'` fails, a 3-element array fails, `'[0:8]=...'` fails (its `[3]` would read slot 4), a 3x3 array fails. `NOT VALID` keeps the ALTER instant; every row written later is checked, and every existing row is NULL at add time, so nothing is left unvalidated. SQLAlchemy 2.0.52 supports `CheckConstraint(..., postgresql_not_valid=True)` (found in the installed `sqlalchemy/dialects/postgresql/base.py`); `op.execute("ALTER TABLE ... ADD CONSTRAINT ... NOT VALID")` is the repo precedent [VERIFIED: alembic/versions/20260610_184500_c8d2e0f3a4b5_gp_composite_fk_seed_041.py:58-64]. Declare the constraint on the model too so the ORM metadata matches.
- No drift test exists in CI (no `compare_metadata` / `alembic check` found), so model and migration agreement is by review.

### Pattern 6: Reader inventory (every place the stored score or loss columns are read)

| Reader | Today | Change |
|--------|-------|--------|
| `library_repository._facepalm_clause` | `GameFlaw.facepalm_score` bounds | expression(LIB λ) with the same two float comparisons |
| `library_repository._build_flaw_item` | `facepalm_score=flaw.facepalm_score` | labelled expression column added to `base_stmt` in `query_flaws` |
| `query_utils.build_flaw_filter_clauses` → `flaw_exists_from_table` | via `_facepalm_clause` (Games-tab EXISTS) | follows `_facepalm_clause` |
| `library_service` `facepalm_by_ply` | `fr.facepalm_score` from `fetch_page_game_flaws_both_colors` rows | add the expression to that fetch (labelled column) or a small dedicated query |
| `blunder_check_repository._unserved_qualifying_blunder_exists` | `GameFlaw.facepalm_score >= FACEPALM_SCORE_MIN` | expression(DRILL λ); keep the `flaw_owner_id` pin (the prod 17.8 s to 0.4 s fix) |
| `blunder_check_repository.load_blunder_flaws` | selects + filters stored score | select + filter the expression |
| `blunder_check_candidates` (pure) | re-checks `flaw.facepalm_score` | unchanged (value now from SQL) |
| `scripts/backfill_maia_flaws._fetch_facepalm_value_counts` | stored score counts | expression counts |
| `scripts/blunder_check/sample.py` (`BlunderRecord`, JSON cache) | `line_loss_3`, `line_mate_ply`, `facepalm_score` | facts + expression(DRILL λ); cache schema changes |
| `scripts/blunder_check/render.py` | `facepalm_score` thresholds, `_loses_material` uses `line_loss_3 >= FAIR_LOSS_MIN` | facts; sign flip; loss/miss split (D-13) |
| `scripts/blunder_check/spot_check.py` | prints score + `line_loss_3` | new inputs printed |
| `scripts/blunder_check/facepalm_features.py`, `fit_facepalm.py` | old TSV schema | extended (Pattern 7) |

Writers: `maia_flaw_scoring` (`_facepalm_values`, `_flaw_row`, `_spread_row`, `_line_row`, `LINE_ROW_COLUMNS`), `FACEPALM_COLUMNS` [VERIFIED: app/repositories/game_flaws_repository.py:185-194], `FacepalmStats` / `null_facepalm_stats` [VERIFIED: app/services/maia_flaw_stats.py:40-68]. Frontend: none (API field unchanged).

### Pattern 7: Fit tooling (features + staged fit)

- `facepalm_features.py` reads `pv` at `ply + 1` only and computes the reply spread with Maia itself [VERIFIED: scripts/blunder_check/facepalm_features.py:392-439, 129-140]. Extend `read_game_inputs` to read `pv` at `ply`, compute best-line facts, and from one pre-board `policy_fn` call derive best-move prob and pre spread. New TSV columns: the two 9-slot arrays (or per-depth cells), both mate plies, `best_prob`, `pre_spread`, `best_pv_plies`. Today's columns: `FEATURE_COLUMNS` = `"n", "set", "game_id", "ply", "label", "pinned_elo", "played_prob", "reply_spread", "line_loss_1", "line_loss_3", "line_loss_5", "line_loss_7", "line_loss_9", "line_mate_ply", "pv_source", "pv_plies", "note"` [VERIFIED: scripts/blunder_check/facepalm_features.py:66-84].
- `fit_facepalm.py` today: `CV_FOLDS: int = 10`, `FIT_SEED: int = 250`, `FIT_THRESHOLDS: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9)`, `AUC_TIE_TOLERANCE: float = 0.005`, `TRAIN_SETS: tuple[str, ...] = ("1", "2", "3", "4", "5")`, `TEST_SET: str = "6"`, `EXIT_CONSTANTS_MISMATCH: int = 6` [VERIFIED: scripts/blunder_check/fit_facepalm.py:56-58, 64, 84, 86-87]. The current fit used 140 of 181 rows; 33 were excluded for a too-short line [VERIFIED: reports/blunder-check/facepalm-fit-2026-11-13.md:9-16].
- **Staged selection (recommended, prescriptive):** Stage 1 material form (combined vs split) with spread "always" and no new Maia inputs. Stage 2 spread form among the three D-07 forms given the stage-1 winner. Stage 3 add `best_prob` (unless stage 2 already uses it), then `pre_spread`; each kept only if it beats the incumbent per D-08. Missed floor (none vs 0) and cap (shared `LOSS_CAP` vs own) as a stage-1 sub-choice. Report every candidate's CV AUC and fair share at the cut. Use the existing deterministic rule (AUC, then fair share, then simpler model on a tie).
- **D-13 sections:** fair / unfair among passers at several cuts, split by loss-type (`loss > 0`, incl. mate), pure-miss (`loss = 0`, `missed > 0`) and mixed; per label set. Pool size per rating band own / foreign comes from the calibration run (`render.py` supply sections) with the drill lambda.
- **`--check-constants`** must compare every new constant including the `Literal` selectors, not only the four coefficients and the floor (today: `constants_mismatches` [VERIFIED: scripts/blunder_check/fit_facepalm.py:781-796]).
- **Legacy TSV:** `tests/services/test_facepalm_score.py` reads `facepalm-features-2026-11-13.tsv` for Window 14 [VERIFIED: tests/services/test_facepalm_score.py:61-75, 220-232]. Pre-refit, `--check-constants` on that old TSV must keep exiting 0: the fit script should detect the legacy schema, fit only the legacy shape, and require the new coefficients to be zero.

### Pattern 8: Post-252 run book (reuse 250-10)

Reuse 250-10's preconditions, dispatch override and threat rows [VERIFIED: .planning/phases/250-facepalm-blunder-selection/250-10-PLAN.md:51-66, 157-175]. Differences: no score recompute and no mixed-score window (D-01); the line pass now writes both arrays and both mate plies; the refit deploy is constants-only and can follow the line pass. Line pass flags as in 250-10: `--mode line --cutoff <ISO> --workers 4 --throttle-ms 50`, resumable with the same cutoff.

### Pattern 9: Final gated drop (D-02)

Same shape as 250-11 / `f9c4d7e3a250`: stop writing `facepalm_score` (and `line_loss_1..9`, see Open Question 4) in the hook and every backfill mode, remove them from `FACEPALM_COLUMNS` / `FacepalmStats`, then `DROP COLUMN` (catalog-only). Deploy rule from the precedent: no operator script may run during the migration [VERIFIED: alembic/versions/20261114_120000_f9c4d7e3a250_phase_250_drop_maia_columns.py:25-27]. Downgrade re-adds empty columns.

### Pattern 10: Blind miss sampler (D-14, D-15)

A committed script (proposed `scripts/blunder_check/miss_labels.py`; the 250 precedent `temp/blunder-check/set6.py` is gitignored and uses `TABLESAMPLE SYSTEM (3) REPEATABLE (611)` with a `rating < 2000` filter and `make_readonly_engine`). Steps: TABLESAMPLE user-side blunders below 2000 on prod (read-only engine); join `pv` at `ply` and `ply + 1`; keep rows where **both** stored lines have at least 3 plies (Phase 252 re-searches only 1-2 ply lines, so these lines never change; a mate-ended shorter line is also stable); exclude games already in the 180 labels; compute both line facts locally; compute best-move prob with local Maia at the pinned Elo; stratify ~40 pure misses over missed buckets (1-2, 3-4, 5-8, 9+, D-14's 1/3/5/9+) crossed with best-prob tertiles, plus ~10 mixed rows; write a blind TSV with the same columns as `leg2-labels-2026-11-11.tsv` (`n, set, elo, move, link, ..., label`) with the value columns empty, plus a key file in gitignored `temp/` holding the hidden inputs. New set id (e.g. "7"). Minimum missed gain for a "miss": 1 (discretion; every D-14 stratum starts at 1).

### Anti-Patterns to Avoid
- **Multiplying an unused input by a zero coefficient in SQL:** `0 * NULL` is NULL, so a NULL `maia_best_prob` would unscore the row. Omit zero-coefficient terms at build time in both twins.
- **Using GREATEST/LEAST on a possibly NULL fact:** PostgreSQL skips NULLs, Python `max`/`min` do not. Guard every NULL with an explicit CASE (the existing docstring already warns: "PostgreSQL LEAST/GREATEST skip NULLs, so the explicit CASE branch is what keeps a short line unscored" [VERIFIED: app/services/facepalm_score.py:122-125]).
- **Computing the chip in Python and the filter in SQL** (D-01 forbids).
- **Writing the copy UPDATE inside the migration** (startup blocked).
- **Removing the `flaw_owner_id` pin** from the own-game EXISTS when swapping in the expression.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Best-line material | A second material walker | `line_facts` with the best move as the first move | 250 D-02 counting rules and 10 fixtures already pinned |
| Pre-blunder spread | New entropy code | `reply_spread` / `_effective_moves` | The 247 formula, already tested |
| Best-move probability | A second Maia call | `probs` from the existing flaw-position `full_policy` | D-08: no extra inference in the hook |
| Logistic fit / CV / AUC | sklearn or statsmodels | Existing IRLS + seeded K-fold in `fit_facepalm.py` | No new dependency; reproducible `--check-constants` |
| Sharding, resume, stamps | New runner | `backfill_maia_flaws.py` hash-residue shards + stamp checkpoints | Proven on prod (Phase 250) |
| Read-only prod access | Raw asyncpg | `make_readonly_engine` from `scripts/blunder_check/sample.py` | Read-only transactions, statement timeout |
| Array shape validation | Python-only checks | NOT VALID CHECK on the column | Enforced at write time, instant ALTER |

**Key insight:** every piece of math here already exists once; the phase is about wiring it to a second line, a second set of Maia outputs, and a query-time expression without letting the two twins drift.

## Runtime State Inventory

This phase replaces stored columns, so the inventory applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Prod `game_flaws`: 2,318,467 user blunders, 2,317,270 with spread, 1,846,677 with a stored score, 616,310 qualifying at 0.7 (as of 250-09) [VERIFIED: 250-09-SUMMARY.md:59]; `line_loss_1..9`, `line_mate_ply`, `facepalm_score` on those rows. Dev user 28: 5,396 user blunders, 4,557 scored, best-line `pv@ply` NULL on 143, shorter than 4 tokens on 1,081, first token != `best_move` on 24 (measured this session, read-only). Benchmark DB: same table, unknown facepalm population | Data migration: batched sign-flipped copy into `played_line_material`; `pre` Maia pass; post-252 line pass for both arrays. Code edit: writers + readers. Benchmark DB needs the migration (and `bin/benchmark_db.sh start` + :8001 restart per project memory); no backfill there unless the owner wants it |
| Live service config | None: remote eval workers never compute facepalm values (the hook runs server-side after apply; `Dockerfile.worker` has no DB). Verified by the reader/writer inventory | None |
| OS-registered state | None (no cron/systemd/pm2 entries reference these columns; long runs are ad-hoc `setsid nohup`) | None |
| Secrets/env vars | None reference these names | None |
| Build artifacts / caches | `temp/blunder-check/prod-cache-*.json` calibration caches serialize `BlunderRecord` with `line_loss_3` / `facepalm_score` keys (`sample.py` `to_dict` / `from_dict`); `reports/blunder-check/facepalm-features-2026-11-13.tsv` (old schema, read by a test); `temp/line-repair/*` 252 state is per machine | Re-sample after the schema change (old caches will not load); keep the old TSV readable (legacy path) |

**Canonical question answered:** after every file is updated, prod still holds the old stored score and loss columns until the gated drop, the new arrays are empty until the copy and passes run, and the 252 repair state lives on whichever machine runs it.

## Common Pitfalls

### Pitfall 1: Zero coefficient, NULL input, NULL score
**What goes wrong:** pre-refit, `maia_best_prob` is NULL on almost every row; if the SQL multiplies it by 0.0 the whole score becomes NULL and every chip and drill candidate vanishes.
**How to avoid:** both twins skip terms whose coefficient is exactly 0.0 (static check), and the Python twin does not require those inputs. Twin-parity grid includes NULL in every new input with zero and non-zero coefficients.
**Warning signs:** R2 prod check shows fewer scored rows than the stored column.

### Pitfall 2: Best-line mate cases
**What goes wrong:** a missed mate-in-1 (one-token best pv) or a best line ending in the opponent's mate scores as "line too short" (NULL) or "nothing missed".
**How to avoid:** Pattern 2 items 1-2; define `best_line_mate_ply` with the best move as ply 0 (mate-in-1 = 0, mate-in-2 = 2), and the missed term uses a mate value when it is <= `LINE_DEPTH`. Allow 0 in any check.
**Warning signs:** unit test with Scholar's-mate style position returns NULL.

### Pitfall 3: Chip vs filter disagreement at band edges
**What goes wrong:** the flaw list returns a Python-computed score while the filter uses SQL, or the two use different lambdas.
**How to avoid:** one helper `facepalm_expr(lam)` used for the select and `_facepalm_clause`; tests assert, for every returned row, `min <= floor(100 * score) <= max`, and that rows excluded by the filter are exactly those outside the band (property over a facts grid).
**Warning signs:** band-edge test flakes.

### Pitfall 4: Test churn from seeding stored scores
**What goes wrong:** 30 call sites in 9 test files seed `facepalm_score=` directly (`tests/blunder_check_seed.py` `SeedBlunder.facepalm_score`, library and router tests, drill tests). After R2 these seeds do nothing; the band-edge test seeds exact values like `0.2999, 0.30, 0.699, 0.70, 0.7001` [VERIFIED: tests/repositories/test_library_repository.py:794].
**How to avoid:** a shared seeding helper that writes facts; for a target score, invert the twin for `played_prob` (continuous) or use a small table of known fact sets for "qualifying" / "not qualifying". Rewrite band-edge tests to read the actual score back and assert consistency rather than exact seeded values.
**Warning signs:** drill tests silently pass with an empty pool.

### Pitfall 5: The missed term's algebra and NULLs
`missed = swing - loss = best3 - max(0, played3)` (when `played3 < 0` it reduces to `best3`). It can be negative (best line behind at depth 3, e.g. a sacrifice). Decide floor 0 vs none in the fit (discretion). NULL rules: `played3` NULL and no played mate → score NULL (today's rule). `best3` NULL and no best mate → recommend missed = 0 (unknown gain contributes nothing; errs toward fewer false alarms, 250 D-03); see Open Question 2.

### Pitfall 6: Gated spread forms and NULL spread
Under "loss_only" or "best_prob_for_misses", SQL `CASE WHEN loss > 0 THEN coef * spread ELSE 0 END` returns 0 for a pure miss even when the spread is NULL; the Python twin must not return None there. The parity grid must include NULL spread with loss 0.

### Pitfall 7: Which best move
`pv@ply` first token and `game_positions.best_move` disagree on 24 of 5,396 dev rows; `best_move` is NULL on 141. Phase 252 pins its re-search to the stored `best_move` (252 D-01), so after the repair they agree whenever `best_move` exists. Recommend: best UCI = first token of `pv@ply`, falling back to `best_move` when the pv is NULL, so the best-move probability and the best-line facts describe the same move. Add a `MaiaReason` value for "best move not legal / missing" (today `MaiaReason` is `"played_not_legal", "no_rating", "pgn_unparseable", "invalid_root", "ply_beyond_mainline", "fen_mismatch", "no_legal_reply"` [VERIFIED: app/services/maia_flaw_stats.py:20-28]).

### Pitfall 8: Phase 252 connection gate
The 252 repair stops when `pg_stat_activity` rises more than `MAX_CONNECTION_RISE: int = 10` above its start baseline [VERIFIED: scripts/repair_short_lines.py:140-141]. A 12-shard `pre` pass alongside it trips that gate. Either run the `pre` pass with few shards (well under 10 new connections, including the tunnel session and any other operator script), or pause 252 (SIGTERM stops after the batch; the cursor resumes). Owner decision.

### Pitfall 9: Prod performance not measured for the drill probes
D-01's 25 ms vs 38 ms is dev only. The foreign pick uses TABLESAMPLE and an EXISTS per sampled game; the own pick relies on the `flaw_owner_id` pin. The expression adds per-row CPU only, but confirm with `EXPLAIN (ANALYZE, BUFFERS)` on prod (orchestrator, read-only) after R2.

### Pitfall 10: Model-selection noise
About 230 labels, roughly 190 usable after repair, ~50 misses. 10-fold CV AUC has a standard error of a few hundredths; `AUC_TIE_TOLERANCE` is 0.005. Comparing many candidates can pick noise. Keep the staged procedure (Pattern 7), prefer the simpler model on near ties, and report repeated-seed CV (several fixed seeds) next to the single-seed numbers so the owner sees stability.

### Pitfall 11: Name clash in the fit report
`fit_facepalm.py` already reports "Form A" (log played prob, ships) and "Form B" (raw played prob, binary loss). D-06's "(a)/(b)" are a different axis. Use distinct names (`combined` / `split`) in code and report.

### Pitfall 12: 252 status is per machine
`scripts/repair_short_lines.py status` reads `STATE_DIR: Path = REPO_ROOT / "temp" / "line-repair"` [VERIFIED: scripts/repair_short_lines.py:117]. This checkout's state shows the prod work list at 1,056,391 games and cursor 145,164 (stopped by SIGTERM on 2026-11-13; the last report projected 7.26 more days at 8 engines). The repair moved to another machine (250-09-SUMMARY). The D-12 precondition must be checked where the repair runs, plus the 252-06 SUMMARY (not written yet).

### Pitfall 13: `exp()` overflow in SQL
PostgreSQL `exp()` errors on very large arguments, Python `math.exp` raises `OverflowError`. Current coefficients cannot get near that; keep an extreme-value row in the parity grid so a future refit with large coefficients is caught.

### Pitfall 14: Even depths in a 9-slot array
`_net_loss` takes "only a blunderer capture" at depth + 1 [VERIFIED: app/services/line_material.py:183-185]. At even depths depth + 1 is an opponent ply, so even slots are "after the blunderer's own move, before the opponent answers" (optimistic mid-exchange). Nothing in this phase reads them, but a later rating-dependent refit could. See Open Question 1.

## Code Examples

### 1. Today's SQL twin core (to extend, not replace)
```python
# Source: app/services/facepalm_score.py:129-144 (read this session)
capped = func.least(loss3_col, LOSS_CAP)
if model.loss_floor is not None:
    capped = func.greatest(capped, model.loss_floor)
loss = case(
    (mate_col <= LINE_DEPTH, literal(float(MATE_LOSS))),
    (loss3_col.is_(None), null()),
    else_=capped,
)
z = (
    model.intercept
    + model.played_coef * func.ln(played_col + PLAYED_PROB_OFFSET)
    + model.spread_coef * spread_col
    + model.loss_coef * loss
)
return type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))
```

### 2. Proposed loss / missed inputs over the arrays (illustrative; names proposed)
```python
# loss_in: today's semantics on the signed array (played3 = -line_loss_3)
played3 = GameFlaw.played_line_material[LINE_DEPTH]          # 1-based, slot 3 = depth 3
loss_raw = case((played3 < 0, -played3), else_=literal(0))    # max(0, -played3), NULL-safe via CASE below
loss_in = case(
    (GameFlaw.line_mate_ply <= LINE_DEPTH, literal(float(MATE_LOSS))),
    (played3.is_(None), null()),
    else_=func.least(loss_raw, LOSS_CAP),
)
# missed_in = best3 - max(0, played3); unknown best line contributes 0 (Open Question 2)
best3 = GameFlaw.best_line_material[LINE_DEPTH]
played_pos = case((played3 > 0, played3), else_=literal(0))
missed_in = case(
    (GameFlaw.best_line_mate_ply <= LINE_DEPTH, literal(float(model.missed_mate))),
    (best3.is_(None), literal(0.0)),
    (played3.is_(None), null()),
    else_=best3 - played_pos,   # then floor / cap per model
)
```

### 3. Twin-parity grid with array columns (pattern for the test)
```python
# Source: tests/services/test_facepalm_score.py:141-179 uses values(...).data(grid); verified this
# session that the same works with ARRAY(SmallInteger) columns and NULL elements.
rows = values(
    column("played", Float), column("spread", Float),
    column("played_mat", ARRAY(SmallInteger)), column("best_mat", ARRAY(SmallInteger)),
    column("mate", SmallInteger), column("best_mate", SmallInteger),
    column("best_prob", Float), column("pre_spread", Float),
    name="grid",
).data(grid)
```

### 4. Verified ARRAY round-trip (run this session against dev Postgres)
```python
v = values(column("a", ARRAY(SmallInteger)), name="g").data(
    [([-1, None, -3, None, -5, None, -7, None, -9],), (None,)]
)
await conn.execute(select(v.c.a, v.c.a[3]))
# -> [([-1, None, -3, None, -5, None, -7, None, -9], -3), (None, None)]
```

### 5. Batched copy statement shape (operator tool; 9-slot variant)
```sql
UPDATE game_flaws
SET played_line_material = ARRAY[-line_loss_1, NULL, -line_loss_3, NULL, -line_loss_5,
                                 NULL, -line_loss_7, NULL, -line_loss_9]::smallint[]
WHERE game_id = ANY(:game_ids)
  AND played_line_material IS NULL
  AND (line_loss_1 IS NOT NULL OR line_loss_3 IS NOT NULL OR line_loss_5 IS NOT NULL
       OR line_loss_7 IS NOT NULL OR line_loss_9 IS NOT NULL);
```
Rows with all `line_loss_*` NULL keep a NULL array (same as "no usable line"). Run in hash-residue shards with a throttle and a resumable cursor, one connection.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stored `facepalm_score` written by hook/backfill | Query-time expression over facts, per-consumer lambda | This phase (D-01) | Refit = constants deploy; no prod UPDATE pass |
| Loss-only material input | loss + lambda * missed | This phase (D-05) | Missed wins can score high |
| Five `line_loss_*` columns (positive = down) | Signed 9-slot array, positive = blunderer up | This phase (D-09) | Sign flip; readers change |
| 250-10 refit + line recompute with mixed-score window | Folded into 254; no window | This phase (D-11) | 250 closes |

**Deprecated/outdated:** `line_loss_1..9` and `facepalm_score` (dropped in the last plan); the "Form B" comparison in the fit report stays as a reported comparison only.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-09 "slot N = depth N, depths 1 to 9" means 9 slots indexed by depth (even slots NULL after the copy until the line pass) | Patterns 3, 5; Code Example 5 | Wrong shape; CHECK and indexing change. Confirm with owner (Open Question 1) |
| A2 | An unknown best line should contribute missed = 0, not unscore the row | Pitfall 5 | Rows with short best lines under-scored rather than NULL; post-252 the share is small |
| A3 | `line_loss_*` are dropped in the same gated plan as `facepalm_score` | Pattern 9 | Extra columns linger, or a separate drop plan is needed |
| A4 | Keeping `line_mate_ply` (no rename) satisfies D-09's "today's `line_mate_ply` plus its best-line counterpart" | Pattern 5 | Naming asymmetry only |
| A5 | The prod copy of ~2.17M rows finishes within about an hour batched and throttled | Pattern 3 | Longer window between R1 and R2; harmless (readers unchanged until R2) |
| A6 | Dev games 817357 and 820181 exist on prod with the same ids and plies (dev may be a user-28 copy of prod) | Fixtures | If not, they cannot be `--extra` rows in a prod features run; embed them as unit fixtures instead |
| A7 | The `pre` pass has the same per-game cost as the Phase 250 spread pass (one inference per user blunder) | Pattern 4 | Run-time estimate off |
| A8 | Remote workers never compute or store facepalm facts | Runtime State Inventory | A worker release would be needed (none expected; `Dockerfile.worker` is DB-less) |

## Open Questions

1. **9 slots or 5?** D-09 says "Slot N = net material at depth N, depths 1 to 9". Taken literally that is 9 slots with `array[3]` = depth 3, and the copy leaves even slots NULL until the post-252 line pass. Even depths have optimistic mid-exchange semantics (Pitfall 14). Recommendation: 9 slots as locked, even slots computed with the existing rule and documented; ask the owner at plan review if the even-depth semantics should change.
2. **NULL best line.** Recommendation: missed = 0 when `best3` is unknown and no best mate (fewer false alarms). Alternative: unscore. The fit report should count label rows with a NULL best line.
3. **Missed floor and cap.** Fit decides (discretion); prescribe the candidates: floor {none, 0}, cap {LOSS_CAP, own constant}. Missed-mate value: start with `MATE_LOSS`.
4. **Drop scope.** Include `line_loss_1..9` in the D-02 drop migration? Recommended yes (D-09 says they are replaced).
5. **Running the `pre` pass while 252 runs.** Few shards (connection rise well under 10) vs pausing 252 vs waiting. Orchestrator and owner decide; record the 252 baseline first.
6. **Prod EXPLAIN** of the own pick, foreign pick and `load_blunder_flaws` with the expression (orchestrator, read-only, after R2).
7. **Fixture availability on prod** for 817357/24 and 820181/65 (orchestrator query); else embed in a unit fixture file like `tests/services/line_material_fixtures.py`.
8. **Benchmark DB:** confirm whether its `game_flaws` carry facepalm facts and whether any benchmark report should read the score (none found in `scripts/`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker dev Postgres | Tests, dev rehearsal | ✓ | PostgreSQL 18.6 (`flawchess-dev-db-1` healthy) | — |
| Benchmark Postgres | Benchmark migration | ✓ | container healthy | — |
| onnxruntime (Maia) | features script, sampler, `pre` pass | ✓ | 1.29.0 | none; `--group maia-inference` in fresh worktrees |
| numpy | fit | ✓ | 2.5.2 | — |
| Prod DB tunnel | copy, `pre` pass, features, sampler, line pass | ✗ from this agent (orchestrator only) | — | Orchestrator runs `bin/prod_db_tunnel.sh` |
| Phase 252 completion | line pass, refit | ✗ (in progress elsewhere) | — | Build-now work per D-12 |

**Missing dependencies with no fallback:** none for the build-now plans.
**Missing dependencies with fallback:** prod access (orchestrator), 252 completion (sequenced last).

Core tests run green and fast: `uv run pytest tests/services/test_facepalm_score.py tests/services/test_line_material.py tests/scripts/test_fit_facepalm.py -q` → 69 passed in 11.4 s (this session).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-xdist, async tests via the project's `test_engine` fixtures) |
| Config file | `pyproject.toml` / `tests/conftest.py` (per-session cloned Postgres DB) |
| Quick run command | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_line_material.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | SQL twin equals Python twin for every model shape, lambda in {0, 0.5, 1}, NULLs in every input | DB unit | `uv run pytest tests/services/test_facepalm_score.py -x` | ✅ (extend) |
| D-01 | Chip and filter agree for every returned row (facts grid) | DB integration | `uv run pytest tests/repositories/test_library_repository.py -k facepalm -x` | ✅ (rewrite seeds) |
| D-01/D-12 | Pre-refit model reproduces the Phase 250 score on a grid (frozen old formula) | unit | `uv run pytest tests/services/test_facepalm_score.py -k reproduces -x` | ❌ Wave 0 |
| D-02 | Hook/backfill no longer write the dropped columns; model lacks them | unit + DB | `uv run pytest tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -x` | ✅ (extend) |
| D-03/D-04 | Drill uses DRILL λ, library uses LIBRARY λ (distinct constants) | DB integration | `uv run pytest tests/repositories/test_blunder_check_repository.py tests/test_library_router.py -x` | ✅ (extend) |
| D-05 | D-05 table cases: loss/missed derivation incl. negative missed, NULLs, mates | unit | `uv run pytest tests/services/test_facepalm_score.py -k missed -x` | ❌ Wave 0 |
| D-06/D-07/D-08 | Fit stages pick deterministically; zero-coef inputs omitted; `--check-constants` covers selectors | unit (synthetic TSV) | `uv run pytest tests/scripts/test_fit_facepalm.py -x` | ✅ (extend) |
| D-08 | Hook writes best prob + pre spread from the existing policy call (call count unchanged); `pre` mode writes only its keys and stamp | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -k pre -x` | ✅ (extend) |
| D-09 | Arrays: slot N == -loss_at(N) on all 250 fixtures; best-line facts; opponent mate settles; mate by first move = ply 0; CHECK rejects bad shapes | unit + DB | `uv run pytest tests/services/test_line_material.py -x` | ✅ (extend) |
| D-09 | Copy tool: sign flip, NULL rows untouched, idempotent, resumable | DB | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -k copy -x` | ❌ Wave 0 |
| D-09 | Fingerprint includes pv@ply: a changed best line blocks the write | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -k fingerprint -x` | ✅ (extend) |
| D-13 | Report sections exist (cuts x loss/miss type, pool per band own/foreign) | unit | `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_blunder_check_calibration.py -x` | ✅ (extend) |
| D-14/D-15 | Sampler filters (rating < 2000, both lines >= 3 plies, excluded used games), stratification, blind output has no values | unit (fake rows) | `uv run pytest tests/scripts/test_miss_labels.py -x` | ❌ Wave 0 |
| D-16 | Features script reads pv@ply, outputs new columns; legacy TSV still loads | unit | `uv run pytest tests/scripts/test_facepalm_features.py -x` | ✅ (extend) |
| Specifics | Window 14 below cut; fixtures 817357/24 and 820181/65 score high after refit | unit | `uv run pytest tests/services/test_facepalm_score.py -k "window_14 or owner_fixture" -x` | ✅ / ❌ |
| Manual | Owner labels ~50 rows; owner sets `FACEPALM_SCORE_MIN`; prod passes | manual checkpoint | — | n/a |

### Sampling Rate
- **Per task commit:** the quick command plus the module's own test file.
- **Per wave merge:** `uv run pytest -n auto -x`.
- **Phase gate:** full pre-merge gate from CLAUDE.md before each squash-merge (R1, R2, refit, drop); memory notes serial CI can expose isolation bugs that `-n auto` hides, so run the serial suite before a release.

### Wave 0 Gaps
- [ ] Facts-based seeding helper (replaces `facepalm_score=` seeds in 9 test files, 30 call sites)
- [ ] `tests/services/test_facepalm_score.py`: reproduction test + D-05 cases + extended parity grid
- [ ] `tests/scripts/test_miss_labels.py` (new script)
- [ ] Copy-tool tests in `tests/scripts/test_backfill_maia_flaws.py`
- [ ] Owner fixtures 817357/24 and 820181/65 as embedded FEN + lines (no DB dependency)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged |
| V3 Session Management | no | unchanged |
| V4 Access Control | yes | Library queries stay user-scoped (`GameFlaw.user_id == user_id`, `player_only_gate`); foreign pick returns game ids only; keep both unchanged when swapping in the expression |
| V5 Input Validation | yes | `min_facepalm_pct` / `max_facepalm_pct` already bounded by `FACEPALM_PCT_MIN: int = 0` / `FACEPALM_PCT_MAX: int = 100` [VERIFIED: app/repositories/library_repository.py:86-87]; lambda is a constant, never request input |
| V6 Cryptography | no | — |
| V8 Data Protection | yes | Label sheets and reports carry game links, ratings, moves and numbers only (250 precedent, T-248-11); key files with hidden inputs stay in gitignored `temp/` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via expression building | Tampering | SQLAlchemy expressions with bound float params; backfill mode clauses are constants (existing `_STAMP_CLAUSE_BY_MODE` pattern) |
| Prod DB overload from passes | DoS | One connection per shard, `--throttle-ms`, stay under ~25 operator connections and under 252's rise gate; SIGTERM stops after a batch |
| Accidental prod writes from read-only tools | Tampering | `make_readonly_engine` for features and sampler |
| Migration lock on 12 GB table | DoS | Nullable ADD COLUMN, `NOT VALID` CHECKs, no data UPDATE in the migration |
| Constants mismatch between deployed app and operator passes | Tampering | Operator runs from a checkout at the deployed SHA; the line pass no longer writes scores, so only facts must match |

## Sources

### Primary (HIGH confidence)
- Codebase files read this session: `app/services/facepalm_score.py`, `line_material.py`, `maia_flaw_scoring.py`, `maia_flaw_stats.py`, `blunder_check_rules.py`; `app/models/game_flaw.py`, `game.py` (stamps); `app/repositories/game_flaws_repository.py`, `library_repository.py` (clause, flaw item, selects), `blunder_check_repository.py`; `scripts/backfill_maia_flaws.py`, `scripts/blunder_check/facepalm_features.py`, `fit_facepalm.py`, `scripts/repair_short_lines.py` (constants, status); both Phase 250 migrations; `tests/services/test_facepalm_score.py`, `test_line_material.py`.
- Planning docs: 254-CONTEXT, SEED-261114-mg7, 250-10-PLAN, 250-09-SUMMARY, 252-CONTEXT, `reports/blunder-check/facepalm-fit-2026-11-13.md`, `reports/line-repair/repair-prod-all-full-20261113T2238Z.md`.
- Probes this session: dev DB read-only queries (fixtures, best-line stats), `line_facts` on the two fixtures, Postgres CHECK semantics, asyncpg ARRAY round-trip, core test run.
- Context7 `/sqlalchemy/sqlalchemy` rel_2_0_55: ARRAY one-based indexing; `query_expression` / `with_expression`.

### Secondary (MEDIUM confidence)
- None.

### Tertiary (LOW confidence)
- Storage and copy-duration estimates (A5), `pre` pass run time (A7).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new dependencies; versions probed)
- Architecture: HIGH for the code map and ordering; MEDIUM for the model space (the fit decides)
- Pitfalls: HIGH (each traced to a read line or a probe)

**Research date:** 2026-11-14
**Valid until:** 2026-12-14 (internal code; re-check the 252 repair state and any changes to the facepalm modules before planning post-252 plans)
