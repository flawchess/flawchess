# Phase 259: Facepalm Score Refit on First Principles - Pattern Map

**Mapped:** 2026-11-21
**Files analyzed:** 24 (new or modified across R1 / SW / DROP)
**Analogs found:** 23 / 24 (every analog path below is git-tracked source)

Release step key: **R1** = behaviour-neutral dual-write, **SW** = switch release, **DROP** = human-gated array drop.
Research (259-RESEARCH.md "Reader and Writer Inventory") lists every line-level touch point; this map gives the
pattern to copy for each file.

## File Classification

| New/Modified File | Step | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|---|
| `app/services/line_material.py` (add `quiet_line_facts`, `quiet_best_line_facts`, `_count_step`) | R1 | service (pure) | transform | same file: `_net_loss`, `_facts_after_first_move`, `line_facts`, `best_line_facts` (lines ~205-321) | exact |
| `app/services/facepalm_material.py` (write-time scalar helper; `*_sql` builders deleted at DROP) | R1/DROP | utility | transform | same file `decaying_mean` / `loss_by_depth`; `facepalm_score.material_loss` / `material_missed` (299-367) | exact |
| `app/services/maia_flaw_scoring.py` (reply prob, scalars, `"reply"` mode, stamps) | R1 | service | batch / event-driven (post-commit hook) | same file: `_derive_reply_spread` (448-472), `_pre_inputs` (557-570), `_facepalm_values` (487-515), `_STAMP_COLUMN_BY_MODE` / `_mark_stamps` (1018-1045) | exact |
| `app/services/maia_flaw_stats.py` (`MaiaReason` + `"reply_missing"`, `FacepalmStats` keys) | R1 | model (TypedDict) | transform | same file 20-69 | exact |
| `app/repositories/game_flaws_repository.py` (`FACEPALM_COLUMNS` + scalars, new `FACEPALM_REPLY_COLUMNS`, stamp mark/clear) | R1 | repository | CRUD | `FACEPALM_PRE_COLUMNS` (200-203), `clear_maia_flaws_completed` (390-421) | exact |
| `app/models/game_flaw.py` (3 REAL columns, new index, drop arrays/CHECKs/old index) | R1/SW/DROP | model | CRUD | same file 43-71, 165-190 | exact |
| `app/models/game.py` (`facepalm_reply_completed_at`) | R1 | model | CRUD | `facepalm_pre_completed_at` (282-296) | exact |
| `alembic/versions/<R1>_phase_259_facepalm_scalars.py` | R1 | migration | DDL | `20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py` | exact |
| `alembic/versions/<SW>_phase_259_ix_game_flaws_facepalm_inputs.py` | SW | migration | DDL (CIC) | `20260610_183000_b7c1d9e2f3a4_batch1_index_planner_stats_seed_041.py` | exact |
| `alembic/versions/<DROP>_phase_259_drop_material_arrays.py` | DROP | migration | DDL | `a7d2c9e1b254` downgrade() + `b7c1d9e2f3a4` autocommit block | role-match |
| `app/services/facepalm_score.py` (scalar twin, `FacepalmModel` 6 coefs, `_game_flaw_columns`, type twin) | SW | service (expression builder) | transform | same file `facepalm_score_sql` / `_game_flaw_columns` (600-635), `facepalm_type_of` | exact |
| `app/services/blunder_check_rules.py` (new `FACEPALM_*` constants, rule constants block + tripwire) | SW | config | — | same file 61-117 | exact |
| `app/repositories/library_repository.py` (JIT helper keep/remove only) | SW/DROP | repository | request-response | `disable_jit_for_transaction` 1679-1688 | exact |
| `scripts/backfill_maia_flaws.py` (`"reply"` mode, clause, status) | R1 | script | batch | `_PRE_PENDING_CLAUSE` + `_STAMP_CLAUSE_BY_MODE` (195-246), `BACKFILL_MODE_CHOICES` 176 | exact |
| `scripts/blunder_check/quiet_rule_review.py` (NEW, D-09) | R1 | script (report) | batch read-only | `scripts/blunder_check/facepalm_features.py` (`read_game_inputs` 467-528, `make_readonly_engine` from `sample.py`) | role-match |
| `scripts/blunder_check/facepalm_features.py` (new TSV schema, `--skip-missing`) | SW | script | batch read-only | same file (`_spread_for` 162-173, `EXIT_ROWS_MISSING` 302) | exact |
| `scripts/blunder_check/fit_facepalm.py` (fixed shape, info-only alternatives, `--check-constants`) | SW | script | batch | same file `fit_logistic` 521, `cv_predictions` 579, `--check-constants` 2478-2564 | exact |
| `scripts/blunder_check/{sample,render,spot_check,metrics}.py` | SW | script | batch | themselves (re-point to scalars) | exact |
| `tests/services/line_material_fixtures.py` + `test_line_material.py` | R1 | test | — | same files (`LineFixture`) | exact |
| `tests/scripts/test_quiet_rule_review.py` (NEW) | R1 | test | — | `tests/scripts/test_facepalm_features.py` | role-match |
| `tests/facepalm_seed.py`, `tests/services/test_facepalm_score.py` | SW | test | — | same files | exact |
| `tests/services/test_maia_flaw_scoring.py`, `tests/services/maia_fakes.py`, `tests/scripts/test_backfill_maia_flaws.py` | R1 | test | — | same files (key-set pins, `assert_maia_lane_state`) | exact |
| `tests/test_query_utils.py:526,533,539`, `tests/test_library_repository.py:2743`, `tests/services/test_flaw_comparison.py:1274-1304,1402-1420` | SW | test | — | themselves (string/name swap) | exact |
| `CHANGELOG.md` | SW | docs | — | existing `## [Unreleased]` | n/a |

## Pattern Assignments

### `app/services/line_material.py` (service, transform) — R1

**Analog:** the same file. Do NOT modify `line_facts` / `best_line_facts` / `_net_loss` behaviour before DROP (old arrays must stay byte-identical, D-11).

**Step replay to reuse as is** (`_replay_line`):
```python
def _replay_line(board, tokens, blunderer) -> tuple[list[_Step], chess.Board]:
    steps: list[_Step] = []
    for token in tokens:
        move = _parse_move(token)
        if move is None or move not in board.legal_moves:
            break
        opponent_move = board.turn != blunderer
        victim = _victim_value(board, move)
        board.push(move)
        ...
        steps.append(_Step(opponent_move, victim, move.to_square, blunderer_mated, opponent_mated))
    return steps, board
```

**Loop body to extract into `_count_step(loss, quiet_square, step) -> tuple[int, int | None]`** (from `_net_loss`; desperado rule must exist once, `_net_loss` calls the helper too):
```python
        if step.opponent_move:
            if step.victim_value and step.to_square != quiet_blunderer_square:
                loss += step.victim_value
            quiet_blunderer_square = None
        else:
            loss -= step.victim_value
            quiet_blunderer_square = step.to_square if step.victim_value == 0 else None
```

**Mate-first branch to keep ahead of the "too short" check** (`_facts_after_first_move`, Pitfall 2):
```python
    board.push(first)
    if board.is_checkmate():
        return LineFacts(loss_by_depth=dict.fromkeys(LINE_MATERIAL_DEPTHS, -first_victim),
                         mate_ply=None, opponent_mate_ply=0)
    steps, end_board = _replay_line(board, rest, blunderer)
    if not steps:
        return null_line_facts()
```
New `_facts_after_first_move_quiet` mirrors this, filling only `LINE_LOSS_DEPTHS = (1, 3, 5, 7, 9)` with the `_quiet_loss` shape in RESEARCH "Code Examples" (walk while `index < depth or steps[index].victim_value`; SEE via `_best_recapture(end_board, last.to_square)` only when the walk consumed the whole line on a non-mating capture; sign by `last.opponent_move`). Public entry points copy the guards of `line_facts` / `best_line_facts` verbatim (empty pv -> `null_line_facts()`, `_parse_move` + legality check). Keep nesting <= 4: one small helper per concern.

---

### `app/services/maia_flaw_scoring.py` (service, batch + post-commit hook) — R1

**Reply probability:** extend `_derive_reply_spread` to also return the reply prob; copy the lookup idiom from `_pre_inputs`:
```python
    best_uci = best_move_uci(flaw.best_pv, flaw.best_move)
    best_prob = float(probs[best_uci]) if best_uci is not None and best_uci in probs else None
    pre = MaiaPreStats(maia_best_prob=best_prob, maia_pre_spread=pre_blunder_spread(probs))
    return pre, ([] if best_prob is not None else ["best_move_missing"])
```
-> `reply_uci = flaw.refutation_pv.split(_PV_SEPARATOR)[0]` (first token of pv@ply+1), `reply_prob = float(probs[reply_uci]) if ... in probs else None`, reason `"reply_missing"`. The existing helper's contract (copy on `pre_board`, `played_not_legal`, `no_legal_reply`, raise `MaiaInferenceUnavailableError` on `None`) stays.

**Scalars in `_facepalm_values`** (current shape):
```python
    facts = line_facts(board, played_uci, flaw.refutation_pv)
    best = best_line_facts(board, flaw.best_pv or flaw.best_move)
    return FacepalmStats(
        maia_reply_spread=spread,
        line_mate_ply=facts.mate_ply,
        played_line_material=_material_or_none(facts),
        best_line_material=_material_or_none(best),
        best_line_mate_ply=best.opponent_mate_ply,
    )
```
Add `material_loss` / `material_missed` computed from `quiet_line_facts` / `quiet_best_line_facts` through `material_loss` / `material_missed` with the named constants (RESEARCH Pattern 2 snippet). Missed is None iff loss is None.

**Mode + stamps** (copy the `"pre"` entries):
```python
_STAMP_COLUMN_BY_MODE: dict[ScoringMode, Any] = {
    ...
    "pre": Game.facepalm_pre_completed_at,
}
...
    if mode == "full":
        ...
        await mark_facepalm_pre_completed(session, game_ids)
    if mode == "pre":
        await mark_facepalm_pre_completed(session, game_ids)
```
Add `"reply"` to `ScoringMode` (137), `Game.facepalm_reply_completed_at`, `mark_facepalm_reply_completed` in both the `full` and a new `reply` branch. Row columns for reply mode = PK + `FACEPALM_REPLY_COLUMNS` only. `LINE_ROW_COLUMNS` (819) derives from `FACEPALM_COLUMNS` so it picks up the scalars automatically and must never contain the reply prob (Pitfall 4). Add `stored_best_reply_prob` to `FlawMaiaInput` / `_flaw_fingerprint_select` / `_read_flaw_inputs` like the other stored values. `_row_score` (862-884) switches at SW.

---

### `app/repositories/game_flaws_repository.py` (repository, CRUD) — R1

**Analog tuple with its rationale comment** (copy the comment style):
```python
# Phase 254 D-08: ... Its OWN tuple, deliberately NOT part of FACEPALM_COLUMNS
# (spread and line modes never write them) and flaw_record_to_row must never emit these keys:
# the diff/upsert preserves them by omission (T-254-06).
FACEPALM_PRE_COLUMNS: tuple[str, ...] = (
    "maia_best_prob",
    "maia_pre_spread",
)
```
-> `FACEPALM_REPLY_COLUMNS: tuple[str, ...] = ("maia_best_reply_prob",)`; append `"material_loss", "material_missed"` to `FACEPALM_COLUMNS` (remove the two arrays at DROP). Add `mark_facepalm_reply_completed` beside `mark_facepalm_pre_completed`, and clear the new stamp in `clear_maia_flaws_completed` (390-421). `bulk_update_flaw_maia_stats` is unchanged.

---

### `app/models/game_flaw.py` / `app/models/game.py` (model) — R1, SW, DROP

**Covering index declaration to copy** (lines 43-59, keep the "keep INCLUDE in step with `_game_flaw_columns`" comment):
```python
        Index(
            "ix_game_flaws_blunder_facts",
            "user_id",
            "game_id",
            postgresql_include=["ply", "maia_played_prob", "maia_reply_spread", "played_line_material",
                                "line_mate_ply", "best_line_material", "best_line_mate_ply",
                                "maia_best_prob", "maia_pre_spread"],
            postgresql_where=text("severity = 2"),
        ),
```
SW: add a second `Index("ix_game_flaws_facepalm_inputs", "user_id", "game_id", postgresql_include=["ply", "maia_played_prob", "material_loss", "material_missed", "maia_best_prob", "maia_best_reply_prob"], postgresql_where=text("severity = 2"))`. New name is mandatory: autogenerate ignores INCLUDE/WHERE changes. DROP: remove the old Index, the two `CheckConstraint(_material_array_shape(...))` entries and `_material_array_shape`. New columns are `Mapped[float | None]` REAL, declared like `maia_best_prob` (165-190). New CHECKs (optional, `(material_loss IS NULL) = (material_missed IS NULL)`, `>= 0`) declared with `postgresql_not_valid=True` exactly like the array shape checks.

---

### R1 migration (migration, DDL) — analog `alembic/versions/20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py`

```python
def upgrade() -> None:
    for column in _ARRAY_COLUMNS:
        op.add_column("game_flaws", sa.Column(column, postgresql.ARRAY(sa.SmallInteger()), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_best_prob", sa.REAL(), nullable=True))
    op.add_column("games", sa.Column("facepalm_pre_completed_at", sa.DateTime(timezone=True), nullable=True))
    # NOT VALID: no table scan, enforced on every row written from now on.
    op.execute(f"ALTER TABLE game_flaws ADD CONSTRAINT ck_game_flaws_{column}_shape "
               f"CHECK ({_shape_check(column)}) NOT VALID")

def downgrade() -> None:
    op.execute(f"ALTER TABLE game_flaws DROP CONSTRAINT IF EXISTS ck_game_flaws_{column}_shape")
    op.drop_column("games", "facepalm_pre_completed_at")
    ...
```
Literals only, no app-constant imports. CHECKs hand-written (`checkconstraint_byname` not enabled in `alembic/env.py`).

### SW index migration — analog `alembic/versions/20260610_183000_b7c1d9e2f3a4_batch1_index_planner_stats_seed_041.py`

```python
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_games_user_played_at "
            "ON games (user_id, played_at DESC)"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_games_user_id")
```
Copy its docstring rationale ("Already applied in prod ...; rides in the migration for dev/test parity"). Prefer literal `op.execute` SQL (`... ON game_flaws (user_id, game_id) INCLUDE (...) WHERE severity = 2`), generated by compiling the ORM `Index`, over `op.create_index(..., if_not_exists=True)` unless rehearsed on dev (RESEARCH A6). Prod build is an operator step, then `pg_index.indisvalid` + `pg_get_indexdef` check (Pitfall 5).

### DROP migration — combine both analogs
`autocommit_block()` -> `DROP INDEX CONCURRENTLY IF EXISTS ix_game_flaws_blunder_facts`; then `DROP CONSTRAINT IF EXISTS ck_game_flaws_{played,best}_line_material_shape`; then `op.drop_column` for both arrays. Downgrade re-adds the columns + NOT VALID CHECKs (copy a7d2c9e1b254 upgrade) and the old index non-concurrently.

---

### `app/services/facepalm_score.py` (expression builder, transform) — SW

**The single switch point** (current):
```python
def _game_flaw_columns() -> FacepalmColumns:
    return FacepalmColumns(
        played_prob=GameFlaw.maia_played_prob,
        reply_spread=GameFlaw.maia_reply_spread,
        played_material=GameFlaw.played_line_material,
        ...
    )
```
-> `FacepalmColumns(played_prob, loss=GameFlaw.material_loss, missed=GameFlaw.material_missed, best_prob=GameFlaw.maia_best_prob, reply_prob=GameFlaw.maia_best_reply_prob)`.

**Keep from the current `facepalm_score_sql` tail** (zero-weight omission + coercion):
```python
    weight = _missed_weight(model, lam)
    if weight != 0.0:
        z = z + weight * _missed_sql(columns, model)
    return type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))
```
New body: RESEARCH "Scalar SQL twin (sketch)", with an explicit `loss IS NULL -> NULL` first branch (Pitfall 6). `facepalm_expr`, `facepalm_type_expr` signatures and docstring contract (one bound expression in SELECT and WHERE) unchanged; `facepalm_type_of(loss, missed)` already takes scalars. Python twin must mirror the SQL term-for-term (grid parity test).

---

### `app/services/blunder_check_rules.py` (config) — SW
Paste fitted constants into the existing `FACEPALM_*` block (61-117); move `LOSS_CAP`, `MATE_LOSS`, `FACEPALM_MISSED_FLOOR/CAP/MATE`, `MATERIAL_DECAY_RATIO`, `FACEPALM_LOSS_FLOOR` into a separate "write-time rule constants: changing these needs a prod line pass" block, pinned by a tripwire test. If `FACEPALM_STATS_MIN` moves, also move `FACEPALM_HIGH_CUTOFF` in `frontend/src/lib/facepalm.ts:35-40` (Pitfall 9).

---

### `scripts/backfill_maia_flaws.py` (script, batch) — R1

Copy the `pre` clause:
```python
_PRE_PENDING_CLAUSE: str = (
    "g.facepalm_pre_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL"
)
_STAMP_CLAUSE_BY_MODE: dict[BackfillMode, str] = {
    "full": "g.maia_flaws_completed_at IS NULL",
    "pre": _PRE_PENDING_CLAUSE,
    ...
}
```
-> `_REPLY_PENDING_CLAUSE` on `g.facepalm_reply_completed_at`; add `"reply"` to `BACKFILL_MODE_CHOICES` (176) and `BackfillMode`; Maia starts for every mode except `line` (664-672), so reply gets it for free. Status block (884-913, 1049-1063): add reply stamped/pending and the residue `material_loss > 0 AND maia_played_prob IS NOT NULL AND maia_best_reply_prob IS NULL`. Clauses are constants; the cutoff stays the only bound parameter.

---

### `scripts/blunder_check/quiet_rule_review.py` (NEW, read-only report) — R1

**Analog:** `scripts/blunder_check/facepalm_features.py` (labels TSV in, prod read-only via `sample.make_readonly_engine`, per-row `read_game_inputs` 467-528 + `replay_flaw_boards`, deterministic markdown/TSV out). Cause classification as a `Literal["exchange_settled_at_end", "longer_exchange_settled", "later_capture_pulled_earlier"]`; pure classification function separated from I/O so `tests/scripts/test_quiet_rule_review.py` can test it on synthetic lines and the 4 changed fixtures (labels 153, 154, 156, 170) plus 2883555:47. Links use `https://flawchess.com/analysis?game_id=X&ply=Y`.

### `scripts/blunder_check/facepalm_features.py` / `fit_facepalm.py` — SW
Extend in place: reply prob from the same post-board policy `_spread_for` (162-173) already computes; add columns `reply_prob, loss, missed, loss_shipped, missed_shipped, pre_fen, played_uci, played_line, best_line`; add a skip-missing flag instead of exit 5 (`EXIT_ROWS_MISSING`, Pitfall 10). Fit: reuse `fit_logistic`, `cv_predictions`, `REPEAT_SEEDS`, `CV_FOLDS`, `FIT_SEED`, `CHECK_CONSTANTS_TOLERANCE`; drop staged selection; alternatives printed as information only.

---

### Tests
- `tests/services/line_material_fixtures.py`: add `expected_quiet_loss` to `LineFixture` and a new 2883555:47 fixture using the RESEARCH "D-13 fixture" FEN/lines (expected loss 91/31, missed 0.0).
- `tests/services/test_maia_flaw_scoring.py`: key-set pins at 425, 751-753, 974, 1060, 1269, 2231, 2334, 2382, 2462, 2510 gain the scalars; a new test asserts line-mode rows carry no reply key.
- `tests/services/maia_fakes.py:19,72-91`: add the reply stamp to `assert_maia_lane_state`.
- `tests/facepalm_seed.py`: rewrite `facepalm_fact_columns` to solve a target score over scalars via the twin.
- `tests/services/test_flaw_comparison.py:1295-1304`: re-point `test_blunder_facts_index_covers_every_score_input` to `ix_game_flaws_facepalm_inputs`.
- Compiled-SQL strings (`tests/test_query_utils.py:526,533,539`, `tests/test_library_repository.py:2743`): `"played_line_material"` -> `"material_loss"` at SW.

## Shared Patterns

### Own column tuple per writer
**Source:** `app/repositories/game_flaws_repository.py:179-203`. **Apply to:** every new written column. Each mode writes a fixed key set; columns a mode must not touch live in a separate tuple, and `flaw_record_to_row` never emits them.

### Stamp checkpoint per backfill mode
**Source:** `app/services/maia_flaw_scoring.py:1018-1045` + `scripts/backfill_maia_flaws.py:195-246`. **Apply to:** reply mode. Constant SQL clause shared by selector and status counts; full mode sets every stamp; clear helper clears every stamp.

### Zero coefficient omits its term in both twins
**Source:** `facepalm_score_sql` (`_missed_weight` / `_optional_sql`). **Apply to:** the new scalar twin and its Python mirror, so an unused NULL input never unscores a row.

### NOT VALID CHECK + literal-only migrations
**Source:** `a7d2c9e1b254`. **Apply to:** all three migrations.

### CONCURRENTLY inside `autocommit_block()` with IF [NOT] EXISTS
**Source:** `b7c1d9e2f3a4:58-70`. **Apply to:** new covering index (SW) and old index drop (DROP).

### Read-only prod engine for report tools
**Source:** `scripts/blunder_check/sample.py` `make_readonly_engine`. **Apply to:** review tool, features pull, calibration.

### Sentry
Services that catch non-trivial exceptions call `sentry_sdk.capture_exception()` with `set_context`, no variables in messages (CLAUDE.md). The new code paths are pure or reuse existing handlers; no new `except` blocks are expected.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| quiet walk algorithm itself (inside `line_material.py`) | service | transform | New rule; reference only is the gitignored-quality spike `.planning/phases/259-facepalm-first-principles-refit/spike/quiet_spike.py` (tracked, throwaway). Use RESEARCH "Quiet loss at one depth" snippet built on existing helpers. |

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/models/`, `alembic/versions/`, `scripts/`, `scripts/blunder_check/`, `tests/`
**Files scanned:** ~12 read directly, inventory line refs from 259-RESEARCH.md (verified there this session)
**Pattern extraction date:** 2026-11-21
