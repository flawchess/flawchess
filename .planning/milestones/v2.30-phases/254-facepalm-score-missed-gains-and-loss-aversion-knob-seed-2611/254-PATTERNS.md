# Phase 254: Facepalm Score Missed Gains and Loss-Aversion Knob - Pattern Map

**Mapped:** 2026-11-14
**Files analyzed:** 27 (new + modified)
**Analogs found:** 26 / 27 (almost every file is an extension of itself; the analog is the Phase 250 version of the same file)

This phase is an extension of Phase 250's facepalm code. For most files the best analog is the file itself
(extend in place, copying its existing shape). All paths below are git-tracked source.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/facepalm_score.py` | service (pure model, Python + SQL twins) | transform | itself (lines 68-144) | exact |
| `app/services/blunder_check_rules.py` | config (constants) | n/a | itself (lines 60-76) | exact |
| `app/services/line_material.py` | service (pure) | transform | itself (`line_facts`, lines 220-245; `LineFacts` 70-92) | exact |
| `app/services/maia_flaw_stats.py` | utility (TypedDicts, `MaiaReason`, effective moves) | transform | itself (lines 20-74) | exact |
| `app/services/maia_flaw_scoring.py` | service (post-commit hook, batch) | event-driven / batch | itself (`_derive_flaw_values` 437-470, `_flaw_fingerprint_select` 172-200, `_STAMP_COLUMN_BY_MODE` 679-697) | exact |
| `app/repositories/game_flaws_repository.py` | repository | CRUD | itself (`FACEPALM_COLUMNS` 185-194, `clear_maia_flaws_completed` 362-391) | exact |
| `app/repositories/library_repository.py` | repository | request-response (filter + select) | itself (`_facepalm_clause` 336-352) | exact |
| `app/repositories/blunder_check_repository.py` | repository | request-response (EXISTS predicate, load) | itself (lines 194-225, 400-420) | exact |
| `app/services/library_service.py` | service | request-response | itself (`facepalm_by_ply` 691-707) | exact |
| `app/models/game_flaw.py` | model | CRUD | itself (lines 108-123) | exact |
| `app/models/game.py` | model (stamp column) | CRUD | itself (`facepalm_line_completed_at`, line 289) | exact |
| `alembic/versions/2026111x_..._phase_254_facepalm_facts.py` (NEW, R1) | migration | schema add | `alembic/versions/20261113_120000_e8b3c6d2f250_phase_250_facepalm.py` + NOT VALID from `20260610_184500_c8d2e0f3a4b5_gp_composite_fk_seed_041.py:58-64` | exact |
| `alembic/versions/2026xxxx_..._phase_254_drop_stored_score.py` (NEW, last, gated) | migration | schema drop | `alembic/versions/20261114_120000_f9c4d7e3a250_phase_250_drop_maia_columns.py` | exact |
| `scripts/backfill_maia_flaws.py` (`pre` mode, `copy` mode, status counts) | operator script | batch | itself (`_STAMP_CLAUSE_BY_MODE` 164-168, `_fetch_facepalm_value_counts` 776-803) | exact |
| `scripts/blunder_check/facepalm_features.py` | operator script | batch / file-I/O (TSV) | itself (`FEATURE_COLUMNS` 66-84, `read_game_inputs` 392-439) | exact |
| `scripts/blunder_check/fit_facepalm.py` | operator script | batch / transform | itself (constants 56-87, `constants_mismatches` 781-796) | exact |
| `scripts/blunder_check/miss_labels.py` (NEW) | operator script | batch (read-only prod) / file-I/O | `scripts/blunder_check/sample.py` (`make_readonly_engine` 97-105) + `facepalm_features.py` | role-match |
| `scripts/blunder_check/sample.py`, `render.py`, `spot_check.py` | operator scripts | batch | themselves | exact |
| `tests/services/test_facepalm_score.py` | test | DB unit (parity grid) | itself (`test_sql_twin_matches_python` 141-179) | exact |
| `tests/services/test_line_material.py` | test | unit | itself + `tests/services/line_material_fixtures.py` | exact |
| `tests/services/test_maia_flaw_scoring.py` | test | DB | itself | exact |
| `tests/scripts/test_backfill_maia_flaws.py` (copy + pre tests) | test | DB | itself | exact |
| `tests/scripts/test_fit_facepalm.py`, `test_facepalm_features.py`, `test_blunder_check_calibration.py` | test | unit | themselves | exact |
| `tests/scripts/test_miss_labels.py` (NEW) | test | unit (fake rows) | `tests/scripts/test_facepalm_features.py` | role-match |
| `tests/blunder_check_seed.py` (facts-based seeding helper) | test fixture | CRUD | itself (`SeedBlunder.facepalm_score` line 63, insert 280) | exact |
| `tests/repositories/test_library_repository.py`, `test_blunder_check_repository.py`, `tests/test_library_router.py` | test | DB integration | themselves (band-edge seeds ~line 794) | exact |
| ROADMAP.md / 250 phase docs (D-11 close-out) | docs | n/a | none needed | n/a |

## Pattern Assignments

### `app/services/facepalm_score.py` (service, transform; Python + SQL twins)

**Analog:** itself. Extend `FacepalmModel` with the full candidate space (RESEARCH Pattern 1): `material_form: Literal["combined", "split"]`, `missed_coef`, `missed_floor`, `missed_cap`, `missed_mate`, `spread_form: Literal["always", "loss_only", "best_prob_for_misses"]`, `best_prob_coef`, `pre_spread_coef`, plus a `lam` parameter on both twins. Keep the twin docstring cross-references.

**Python twin shape** (lines 68-112):
```python
def loss_feature(
    loss_3: int | None, mate_ply: int | None, *, loss_floor: int | None
) -> float | None:
    if mate_ply is not None and mate_ply <= LINE_DEPTH:
        return float(MATE_LOSS)
    if loss_3 is None:
        return None
    capped = min(loss_3, LOSS_CAP)
    if loss_floor is not None:
        capped = max(capped, loss_floor)
    return float(capped)

def facepalm_score(*, played_prob, reply_spread, loss_3, mate_ply, model=FACEPALM_MODEL) -> float | None:
    """Python twin of `facepalm_score_sql`: if either side changes, update the other."""
    if played_prob is None or reply_spread is None:
        return None
    ...
    z = (model.intercept
        + model.played_coef * math.log(played_prob + PLAYED_PROB_OFFSET)
        + model.spread_coef * reply_spread
        + model.loss_coef * loss)
    return 1.0 / (1.0 + math.exp(-z))
```

**SQL twin shape** (lines 115-144) — NULL guarding via explicit CASE, never bare LEAST/GREATEST on a nullable fact:
```python
capped = func.least(loss3_col, LOSS_CAP)
if model.loss_floor is not None:
    capped = func.greatest(capped, model.loss_floor)
loss = case(
    (mate_col <= LINE_DEPTH, literal(float(MATE_LOSS))),
    (loss3_col.is_(None), null()),
    else_=capped,
)
z = (model.intercept + model.played_coef * func.ln(played_col + PLAYED_PROB_OFFSET)
     + model.spread_coef * spread_col + model.loss_coef * loss)
# type_coerce only retypes the expression for the checker (PostgreSQL exp() is double precision).
return type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))
```
Rules to carry over: branch on model selectors at Python build time (static), omit any term whose coefficient is exactly 0.0 in BOTH twins (RESEARCH Pitfall 1), CASE-gated spread forms must give 0 (not NULL) for a pure miss with NULL spread (Pitfall 6). Read input columns as `GameFlaw.played_line_material[LINE_DEPTH]` (one-based ARRAY indexing); see RESEARCH Code Example 2 for the loss/missed CASE shapes. Add one helper (e.g. `facepalm_expr(lam)`) bound to the `GameFlaw` columns so every reader uses the same expression.

---

### `app/services/blunder_check_rules.py` (config)

**Analog:** itself, constants block lines 60-76:
```python
# Plies of the stored refutation line the score reads (one depth for all ratings in this phase).
LINE_DEPTH: int = 3
LOSS_CAP: int = 5
MATE_LOSS: int = 5
# 250 D-01 / D-04 fitted facepalm coefficients: the output of scripts/blunder_check/fit_facepalm.py
# on reports/blunder-check/facepalm-features-2026-11-13.tsv ... pasted as printed, never hand-adjusted.
FACEPALM_INTERCEPT: float = -1.4193
FACEPALM_PLAYED_COEF: float = -0.6629
FACEPALM_SPREAD_COEF: float = -0.3304
FACEPALM_LOSS_COEF: float = 1.1570
FACEPALM_LOSS_FLOOR: int | None = 0
```
Add after it, same comment style: `FACEPALM_DRILL_LAMBDA: float = 1.0`, `FACEPALM_LIBRARY_LAMBDA: float = 1.0` (D-03/D-04, separate constants), and the pre-refit selectors/coefs (`FACEPALM_MATERIAL_FORM: Literal[...] = "split"`, `FACEPALM_MISSED_COEF: float = 0.0`, `FACEPALM_SPREAD_FORM = "always"`, `FACEPALM_BEST_PROB_COEF = 0.0`, `FACEPALM_PRE_SPREAD_COEF = 0.0`, missed floor/cap/mate). Literal types, not `str`.

---

### `app/services/line_material.py` (pure service, transform)

**Analog:** itself. `LineFacts` (lines 70-92) and `line_facts` (220-245):
```python
@dataclass(frozen=True, slots=True)
class LineFacts:
    loss_by_depth: Mapping[int, int | None]
    mate_ply: int | None
    def loss_at(self, depth: int) -> int | None: ...
    def as_columns(self) -> dict[str, int | None]: ...

def line_facts(pre_board: chess.Board, played_uci: str, pv: str | None) -> LineFacts:
    if not pv:
        return null_line_facts()
    played = _parse_move(played_uci)
    if played is None or played not in pre_board.legal_moves:
        return null_line_facts()
    board = pre_board.copy(stack=False)
    blunderer = board.turn
    first_victim = _victim_value(board, played)
    board.push(played)
    steps, end_board = _replay_line(board, pv.split(_PV_SEPARATOR), blunderer)
    ...
```
Changes (RESEARCH Pattern 2): keep `_net_loss`/`loss_by_depth` untouched (pins the 250 fixtures); add a signed 9-slot accessor (`material[N] = -loss_at(N)`); extend depths from `LINE_LOSS_DEPTHS = (1, 3, 5, 7, 9)` (line 36) to 1..9; add `opponent_mated` settling in `_replay_line` (line 144); best-line entry point that handles an empty rest-of-pv (mate by the first move = mate ply 0). Put new branches in new small helpers (nesting gate).

---

### `app/services/maia_flaw_stats.py` (utility)

**Analog:** itself. `MaiaReason` Literal (lines 20-28) — add a "best move missing/not legal" value. `FacepalmStats` TypedDict + `null_facepalm_stats()` (40-68) — add the new keys (`played_line_material`, `best_line_material`, `best_line_mate_ply`, `maia_best_prob`, `maia_pre_spread`), keeping both in lockstep. Reuse `_effective_moves` (71-74) for the pre-blunder spread:
```python
def _effective_moves(probs: Mapping[str, float]) -> float:
    entropy_bits = -sum(p * math.log2(p) for p in probs.values() if p > 0.0)
    return float(_ENTROPY_LOG_BASE**entropy_bits)
```

---

### `app/services/maia_flaw_scoring.py` (hook, event-driven + batch)

**Analog:** itself.

**Inputs/fingerprint** (lines 172-200): add a second aliased `GamePosition` outer join at `GameFlaw.ply` (best line) mirroring `gp_next`, and add it to `FlawMaiaInput` and `FlawFingerprint` (line 99, `tuple[int, str, int, str | None]`):
```python
gp_next = aliased(GamePosition)
...
.outerjoin(gp_next, sa.and_(
    gp_next.game_id == GameFlaw.game_id,
    gp_next.user_id == GameFlaw.user_id,
    gp_next.ply == GameFlaw.ply + 1,
))
```

**Pre-blunder Maia inputs from the existing call** (lines 458-470) — no new inference; derive `best_prob = probs.get(best_uci)` and `pre_spread = _effective_moves(probs)` from `probs` here and pass into `_facepalm_values`:
```python
probs = full_policy(board.fen(), elo)
if probs is None:
    raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
stats, reasons = compute_maia_flaw_stats(probs, played_uci=played_uci)
...
spread, post_reasons = _derive_reply_spread(board, played_uci, elo)
facepalm = _facepalm_values(board, played_uci, flaw.refutation_pv, stats["maia_played_prob"], spread)
```

**Modes/stamps** (line 93 `ScoringMode = Literal["full", "spread", "line"]`; lines 679-697):
```python
_STAMP_COLUMN_BY_MODE: dict[ScoringMode, Any] = {
    "full": Game.maia_flaws_completed_at,
    "spread": Game.facepalm_spread_completed_at,
    "line": Game.facepalm_line_completed_at,
}
async def _mark_stamps(session, mode, game_ids) -> None:
    if mode == "full":
        await mark_maia_flaws_completed(session, game_ids)
        await mark_facepalm_spread_completed(session, game_ids)
        await mark_facepalm_line_completed(session, game_ids)
    ...
```
Add `"pre"` to `ScoringMode`, a `_pre_row` writer modelled on `_spread_row` (line 501) writing only `maia_best_prob` / `maia_pre_spread`, and set the new stamp in full mode too. R1 dual-writes: `_line_row` / `LINE_ROW_COLUMNS` (539-571) keep writing `line_loss_*` + `facepalm_score` AND the arrays until the D-02 drop.

---

### `app/repositories/game_flaws_repository.py` (repository)

**Analog:** itself. `FACEPALM_COLUMNS` (185-194) — add new column names (comment there: these keys must never be emitted by `flaw_record_to_row`; preserved by omission). `clear_maia_flaws_completed` (362-391) — add the new stamp to both the `or_(...isnot(None))` and the `.values(...)`; add a `mark_facepalm_pre_completed` alongside the existing `mark_facepalm_*_completed` helpers.

---

### `app/repositories/library_repository.py` (repository, filter + select)

**Analog:** itself, `_facepalm_clause` (336-352):
```python
if not facepalm_range_active(min_pct, max_pct):
    return None
bounds: list[ColumnElement[bool]] = [GameFlaw.facepalm_score.isnot(None)]
if min_pct is not None and min_pct > FACEPALM_PCT_MIN:
    bounds.append(GameFlaw.facepalm_score >= min_pct / _FACEPALM_PCT_SCALE)
if max_pct is not None and max_pct < FACEPALM_PCT_MAX:
    bounds.append(GameFlaw.facepalm_score < (max_pct + 1) / _FACEPALM_PCT_SCALE)
return and_(*bounds)
```
R2: replace `GameFlaw.facepalm_score` with `score = facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` (same two float comparisons; keep the float docstring note). In `query_flaws`, add the same expression as a labelled column to `base_stmt` and have `_build_flaw_item` read the label instead of `flaw.facepalm_score`. `query_utils.build_flaw_filter_clauses` follows automatically.

---

### `app/repositories/blunder_check_repository.py` (repository)

**Analog:** itself. Predicate (lines 218-225) — keep the `flaw_owner_id` pin:
```python
conditions: list[ColumnElement[bool]] = [
    GameFlaw.game_id == game_id_col,
    GameFlaw.facepalm_score >= FACEPALM_SCORE_MIN,
    not_(already_served),
]
if flaw_owner_id is not None:
    conditions.append(GameFlaw.user_id == flaw_owner_id)
```
`load_blunder_flaws` (400-420) selects and filters `GameFlaw.facepalm_score`; swap both for one `facepalm_expr(FACEPALM_DRILL_LAMBDA)` bound once and reused (label it so `BlunderFlawRow(*row[1:])` still unpacks). `blunder_check_candidates.py` unchanged.

---

### `app/services/library_service.py` (service)

**Analog:** itself, lines 691-693:
```python
facepalm_by_ply: dict[int, float] = {
    fr.ply: fr.facepalm_score for fr in rows_for_tactic if fr.facepalm_score is not None
}
```
Source the value from a labelled expression column added to `fetch_page_game_flaws_both_colors` (repository side), not computed in Python (D-01).

---

### `app/models/game_flaw.py` / `app/models/game.py` (models)

**Analog:** `game_flaw.py` lines 108-123 (comment block describing each column, then `Mapped[Optional[...]] = mapped_column(..., nullable=True)`):
```python
maia_reply_spread: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)
line_loss_3: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
line_mate_ply: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
facepalm_score: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)
```
New: `played_line_material` / `best_line_material: Mapped[Optional[list[int | None]]] = mapped_column(ARRAY(SmallInteger), nullable=True)`, `best_line_mate_ply` SmallInteger, `maia_best_prob` / `maia_pre_spread` REAL. Add the bounds CHECKs to `__table_args__` (line 24) so metadata matches the migration. `game.py`: new stamp next to `facepalm_line_completed_at` (line 289), `DateTime(timezone=True)`.

---

### NEW `alembic/versions/..._phase_254_facepalm_facts.py` (migration, R1)

**Analog:** `alembic/versions/20261113_120000_e8b3c6d2f250_phase_250_facepalm.py` (header docstring states "metadata-only: no server_default, no CHECK constraint, no index and no data UPDATE"; upgrade lines 45-62):
```python
def upgrade() -> None:
    op.add_column("game_flaws", sa.Column("maia_reply_spread", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_1", sa.SmallInteger(), nullable=True))
    ...
    op.add_column("games",
        sa.Column("facepalm_spread_completed_at", sa.DateTime(timezone=True), nullable=True))
```
NOT VALID check precedent (`20260610_184500_c8d2e0f3a4b5_gp_composite_fk_seed_041.py:58-64`): `op.execute("ALTER TABLE ... ADD CONSTRAINT ... NOT VALID")`. Use for `CHECK (x IS NULL OR (cardinality(x) = 9 AND array_lower(x, 1) = 1 AND array_ndims(x) = 1)) NOT VALID`. `down_revision = "f9c4d7e3a250"`. No data copy inside the migration (it runs at backend startup).

### NEW `alembic/versions/..._phase_254_drop_stored_score.py` (migration, last, gated)

**Analog:** `20261114_120000_f9c4d7e3a250_phase_250_drop_maia_columns.py` — copy the docstring structure (dropped / kept / data-loss rationale / "DROP COLUMN is catalog-only" / deploy rule that no operator script runs during the migration) and the `op.drop_column` upgrade + empty re-add downgrade:
```python
def upgrade() -> None:
    op.drop_column("game_flaws", "maia_best_prob")
    ...
def downgrade() -> None:
    """Downgrade schema (re-adds the columns empty)."""
    op.add_column("game_flaws", sa.Column("maia_best_prob", sa.REAL(), nullable=True))
```

---

### `scripts/backfill_maia_flaws.py` (operator script, batch)

**Analog:** itself. Mode selector constants (lines 129, 164-168), never user input:
```python
BACKFILL_MODE_CHOICES: tuple[str, ...] = ("full", "spread", "line")
_STAMP_CLAUSE_BY_MODE: dict[BackfillMode, str] = {
    "full": "g.maia_flaws_completed_at IS NULL",
    "spread": _SPREAD_PENDING_CLAUSE,
    "line": f"{_LINE_STALE_CLAUSE} AND g.facepalm_spread_completed_at IS NOT NULL",
}
```
Add `"pre"` (stamp NULL + base stamped). Copy mode (or a sibling script reusing the same shard/throttle/SIGTERM/report machinery: `_install_signal_handlers` 276, `_run_batches` 439, `_run_spawned_shards` 935) runs the batched sign-flip UPDATE from RESEARCH Code Example 5 by `game_id = ANY(:ids)`. `_fetch_facepalm_value_counts` (776-803) swaps `GameFlaw.facepalm_score` for the expression in `extra_where`.

---

### `scripts/blunder_check/facepalm_features.py`, `fit_facepalm.py` (operator scripts)

**Analog:** themselves. Extend `FEATURE_COLUMNS` (facepalm_features.py:66-84) and `read_game_inputs` (392-439) to read `pv` at `ply`; keep the legacy 2026-11-13 TSV loadable (test reads it). In `fit_facepalm.py`, keep the constants style (`CV_FOLDS`, `FIT_SEED`, `FIT_THRESHOLDS`, `AUC_TIE_TOLERANCE`, lines 56-87) and extend `constants_mismatches` (781-796) to cover every new constant including the Literal selectors. Name forms `combined` / `split` (avoid clash with existing `FitForm = Literal["a_log_played", "b_raw_played_binary_loss"]`, line 76).

### NEW `scripts/blunder_check/miss_labels.py` (operator script, read-only prod sampler)

**Analog:** `scripts/blunder_check/sample.py` for prod access (lines 97-105):
```python
def make_readonly_engine(url: str) -> AsyncEngine:
    """One-connection read-only engine; the URL is never logged."""
    return create_async_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True,
                               connect_args=readonly_connect_args())
```
plus `facepalm_features.py` for local Maia + line facts and the TSV writer. Output columns match `reports/blunder-check/leg2-labels-2026-11-11.tsv`; hidden inputs go to gitignored `temp/`. Strata sizes and the min missed gain as named constants.

### `scripts/blunder_check/sample.py`, `render.py`, `spot_check.py`

Analog: themselves. Replace `line_loss_3` / `facepalm_score` fields in `BlunderRecord` (`to_dict`/`from_dict`) with facts + drill-lambda expression; `render.py` `_loses_material` flips sign (`-played[3] >= FAIR_LOSS_MIN`) and gains loss/miss/mixed splits (D-13).

---

### `tests/services/test_facepalm_score.py` (test, DB parity grid)

**Analog:** itself, lines 141-179:
```python
grid = list(itertools.product(_GRID_PLAYED, _GRID_SPREAD, _GRID_LOSS_3, _GRID_MATE))
rows = values(
    column("played", Float), column("spread", Float),
    column("loss3", SmallInteger), column("mate", SmallInteger),
    name="grid",
).data(grid)
expression = facepalm_score_sql(rows.c.played, rows.c.spread, rows.c.loss3, rows.c.mate, **kwargs)
async with test_engine.connect() as conn:
    fetched = (await conn.execute(select(..., expression))).all()
for ... in fetched:
    expected = facepalm_score(...)
    if expected is None:
        assert sql_score is None
    else:
        assert sql_score == pytest.approx(expected, abs=PARITY_TOLERANCE)
assert saw_none and saw_value
```
Extend with `ARRAY(SmallInteger)` columns (verified to work, RESEARCH Code Example 3), NULLs in every new input, lambda in {0, 0.5, 1}, every model shape, an extreme-value row (exp overflow). Add a frozen-old-formula reproduction test and D-05 table cases. Keep `test_window_14_*` (220-245).

### `tests/blunder_check_seed.py` (test fixture)

**Analog:** itself: `SeedBlunder.facepalm_score: float | None = SEED_FACEPALM_SCORE` (line 63), written at line 280. Replace with a facts-based seed (played_prob/spread/arrays chosen so the expression qualifies or not); ~30 call sites in 9 test files depend on it. Band-edge test at `tests/repositories/test_library_repository.py:~794` must read the score back rather than seed exact values.

## Shared Patterns

### Query-time score expression (single source)
**Source:** `app/services/facepalm_score.py` `facepalm_score_sql` (115-144)
**Apply to:** library_repository, library_service fetch, blunder_check_repository, backfill status counts, sample/render scripts. Bind once per query, use the same object in SELECT and WHERE (chip/filter agreement, D-01).

### Twin discipline
Every change to the Python twin is mirrored in the SQL twin and covered by the parity grid; zero-coef terms omitted in both; NULLs guarded by explicit CASE.

### Constants, never magic numbers / Literal selectors
**Source:** `app/services/blunder_check_rules.py` 60-76 and `scripts/backfill_maia_flaws.py` `_STAMP_CLAUSE_BY_MODE`.

### Stamp-as-checkpoint for every pass
**Source:** `maia_flaw_scoring._STAMP_COLUMN_BY_MODE` / `_mark_stamps` (679-697) + `game_flaws_repository.clear_maia_flaws_completed` (362-391). Any new stamp must be set by full mode and cleared by the reclassify helper.

### Instant migrations, data moves in operator tooling
**Source:** e8b3c6d2f250 docstring; drop shape from f9c4d7e3a250.

### Sentry
Hook code already raises `MaiaInferenceUnavailableError` with constant messages; new `except` blocks in services follow CLAUDE.md (capture_exception, `set_context` for ids, no f-string messages).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| (none in code) | | | `temp/blunder-check/set6.py` (the 250 sampler precedent) is gitignored and must not be named as an analog; `miss_labels.py` composes `sample.py` + `facepalm_features.py` instead |

## Metadata

**Analog search scope:** `app/services`, `app/repositories`, `app/models`, `alembic/versions`, `scripts/`, `scripts/blunder_check/`, `tests/services`, `tests/scripts`, `tests/repositories`
**Files scanned:** ~25
**Pattern extraction date:** 2026-11-14
