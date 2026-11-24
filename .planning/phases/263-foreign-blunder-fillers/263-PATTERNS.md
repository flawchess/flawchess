# Phase 263: Similarly Rated Players' Blunders Replace the Lichess Fillers - Pattern Map

**Mapped:** 2026-11-23
**Files analyzed:** 14 new/changed seams. The full delete/change list is in RESEARCH.md § Touchpoint Inventory and is not repeated here.
**Analogs found:** 13 / 14

All analog paths are git-tracked (`git ls-files` checked). Line numbers are from the worktree `/home/aimfeld/Projects/Games/flawchess-263`.

## File Classification

| New/Modified seam | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/train_pool.py` + `foreign_candidate_stmt` (and a thin-tail fallback stmt) | statement builder | batch read (TABLESAMPLE) | `blunder_check_repository.pick_foreign_game_ids` (504-550) + `train_pool.pool_entry_stmt` (1004-1051) | exact (composition of two) |
| `app/repositories/train_repository.py` `_backfill_foreign_blunders` | repository stage | request-response, batch | `_backfill_sharp_fillers` (2604-2663) + `blunder_check_selection._foreign_source` (573-627) | exact |
| `app/repositories/train_repository.py` `_pick_foreign` (pure) | utility | transform | `blunder_check_selection._fill_nearest_first` (735-760), `_pinned` (143-158) | role-match |
| Owner-aware joins (`_answer_keys_by_position`, `_composition_puzzle_types`, `_classify_sr_solve`, `_mark_session_complete_if_done`, `load_session_puzzles`) | repository | CRUD read | `_answer_keys_by_position` (3205-3274) + `aliased(...)` usage in `library_repository.py:898`, `openings_repository.py:460-461` | exact |
| `reveal_for_puzzle` FOREIGN branch + `game_info` | repository | request-response | own herring gate `train_repository.py:4655-4676`, `blunder_check_repository.game_info_for` (1272-1299) | exact |
| `_wire_source` + Literals | utility | transform | `_wire_source` itself (3484-3509) | exact |
| `app/models/drill_solve.py` `DrillSource` + CHECK | model | n/a | same file 87-93, 126 | exact |
| `alembic/versions/2026MMDD_..._phase_263_foreign_blunder_source.py` | migration | DDL + data | `20260807_114022_e5f71b11fa51_phase_206_sharp_filler_source.py` (shape), `20261201_120000_e5c1b7d3a9f2_...points_rescale.py` (STATEMENTS tuples) | exact |
| `tests/routers/test_phase_263_migration.py` (or similar) | test | DDL round trip | `tests/routers/test_blunder_check_points_migration.py` | exact |
| `TrainSessionResponse.own_puzzle_count` / `ComposedSession.own_puzzle_count` | schema field, derived | request-response | `ComposedSession.requested_count` / `blob_pending_count` (train_repository.py 292-332) | role-match |
| `PuzzleRevealResponse.game_info` + frontend neutral footer | schema + component | request-response | `app/schemas/blunder_check.py:191-197` `GameInfo`, `routers/blunder_check.py:389-398` `_game_info_schema`, `BlunderCheckGameFooter.tsx` `ForeignGameFooter` | exact |
| `tests/conftest.py` autouse foreign-draw stub + opt-in `foreign_pool` fixture | test fixture | n/a | `test_train_repository.py:385-418` (`_install_sharp_fixture` / `_default_empty_sharp_set`), `conftest.py:577-587` (`reset_blob_claim_leases`), `test_blunder_check_selection.py:228-240` | exact |
| `frontend/src/lib/trainBotCopy.ts` `returnPhrase` FOREIGN tail | utility (copy) | transform | same function 566-580 | exact |
| `frontend/src/pages/activity/render.js` + `ActivityPage.tsx` source rows | component | transform | `render.js:384-390` `PZ_DIFF_ROWS`, `ActivityPage.tsx:556-564` | exact |
| Thin-tail fallback (Prod EXPLAIN item 3) | statement builder | batch | `pick_nearest_foreign_game_ids` (553-604) is the shape but NOT the cost (14.8 s at 20%) | no usable analog for the cost profile |

## Pattern Assignments

### `foreign_candidate_stmt` in `app/services/train_pool.py` (statement builder, TABLESAMPLE batch)

**Analog A, stage 1 (sampled games):** `app/repositories/blunder_check_repository.py` lines 525-550
```python
sampled = tablesample(Game.__table__, func.system(sample_percent), name="g")
owner_rating = case(
    (sampled.c.user_color == "white", sampled.c.white_rating),
    else_=sampled.c.black_rating,
)
stmt = (
    select(sampled.c.id)
    .join(User, User.id == sampled.c.user_id)
    .where(
        sampled.c.user_id != user_id,
        User.is_guest.is_(False),
        sampled.c.full_evals_completed_at.isnot(None),
        sampled.c.platform.in_(ANALYTICS_INCLUDED_PLATFORMS),
        owner_rating.between(raw_low, raw_high),
    )
)
...
stmt = stmt.limit(limit)
```
Imports used there (lines 15-31): `from sqlalchemy import case, func, select, tablesample, ...`. Differences for Train: add `.order_by(func.random())` before `.limit()` (RESEARCH Pitfall 1), make it a `.cte()` / `.subquery()`, and do NOT copy the `require_facepalm` NOT EXISTS (D-14). Keep the "only ids leave the repository" docstring discipline (no usernames, owner ids). The `full_evals_completed_at` predicate is not one of D-06's six; keep it only if the planner decides it is implied (blob-backed flaws need it anyway); flag in the plan.

**Analog B, stage 2 (servable predicates):** `app/services/train_pool.py` lines 1027-1051 (`pool_entry_stmt`)
```python
prior_position = _prior_position_lateral(
    name="pool_entry_prior_position",
    user_id_col=GameFlaw.user_id,
    game_id_col=GameFlaw.game_id,
    ply_expr=GameFlaw.ply - 1,
)
expected_score = expected_score_sql(
    prior_position.c.eval_cp, prior_position.c.eval_mate, Game.user_color
)
return (
    select(GameFlaw, Game)
    .join(Game, Game.id == GameFlaw.game_id)
    .outerjoin(prior_position, true())
    .options(undefer(GameFlaw.missed_pv_lines))
    .where(
        GameFlaw.user_id == user_id,
        GameFlaw.severity == _SEVERITY_BLUNDER,
        player_only_gate(GameFlaw.ply, Game.user_color),
        answer_key_present(GameFlaw.missed_pv_lines),
        dead_band_admissible(GameFlaw.missed_pv_lines, GameFlaw.ply),
        second_best_not_winning_admissible(GameFlaw.missed_pv_lines, GameFlaw.ply),
        expected_score >= WINNABILITY_FLOOR_ES,
    )
)
```
Foreign version: replace `GameFlaw.user_id == user_id` with `GameFlaw.user_id == Game.user_id` and `Game.id.in_(select(sampled_cte.c.id))` (or join the CTE). Keep the other six predicates byte-identical. Select light columns only (`game_id, ply, missed_pv_lines, platform, time_control_bucket, time_control_str, owner_rating`), not `(GameFlaw, Game)`, so `Game.pgn` is not loaded (Anti-pattern "Reading PGN for every candidate"). Naming the `missed_pv_lines` column in the select loads the deferred column, as `_answer_keys_by_position` already relies on.

**Constants:** follow `blunder_check_selection.py:86-112` style: one-line comment above each, typed module-level constant. New ones (Train-owned, per Prod EXPLAIN item 1/2): e.g. `FOREIGN_FILLER_SAMPLE_PERCENT: float = 0.1`, `FOREIGN_FILLER_CANDIDATE_GAMES: int` well below 200. Reuse `FOREIGN_RATING_BAND` (`blunder_check_rules.py:164`) and `FOREIGN_RAW_PREFILTER_MARGIN` by import.

---

### `_backfill_foreign_blunders` in `app/repositories/train_repository.py` (repository stage)

**Analog 1, stage contract and output shape:** `_backfill_sharp_fillers` (2604-2663). Keep its docstring contract (self-contained post-reconstruction stage, scalar inputs, list output, "Caller commits") and its served-set read:
```python
served = {
    pid
    for pid in (await session.execute(served_sharp_ids_stmt(user_id))).scalars()
    if pid is not None
}
picks = pick_sharp_fillers(served, limit=shortfall)
...
picked.append(
    _ReconstructedPuzzle(
        game_id=None, ply=puzzle.ply, fen=puzzle.fen,
        last_move_uci=puzzle.first_move_uci, side_to_move=puzzle.side_to_move,
        source=DrillSource.SHARP_FILLER, herring_pool_id=None, sharp_puzzle_id=puzzle.puzzle_id,
    )
)
```
Foreign: served set is `{(game_id, ply)}` from `DrillSolve.source == FOREIGN_BLUNDER` (Python set, Prod EXPLAIN item 4, not a NOT EXISTS), `game_id=<foreign game id>` on the `_ReconstructedPuzzle` (non-NULL at composition so `uq_drill_solves_session_puzzle` is the DB guard), `sharp_puzzle_id` field deleted.

**Analog 2, level computation:** `app/services/blunder_check_selection.py` lines 582-586
```python
level = user_level_elo(
    await repo.recent_rated_games(session, user_id=user_id, limit=USER_LEVEL_SCAN_GAMES),
    fallback=fallback_elo,
)
raw_margin = FOREIGN_RATING_BAND + FOREIGN_RAW_PREFILTER_MARGIN
```
with `fallback_elo=level_fallback_elo(settings_row.blunder_check_level)` (`blunder_check_selection.py:190-192`). `raw_low=int(level - raw_margin)`, `raw_high=int(level + raw_margin)` exactly as 590-591. Import from `app.services.blunder_check_selection` and `app.repositories.blunder_check_repository` (cycle-free, RESEARCH § Recommended module placement).

**Analog 3, staged sample escalation:** `_load_nearest_foreign` (700-732) loops `for sample_percent in (FOREIGN_SAMPLE_PERCENT, FOREIGN_WIDE_SAMPLE_PERCENT):` and stops once a full batch came back. Copy the loop-over-a-tuple-of-percents shape, but with Train-owned, much smaller steps and a hard cap (Prod EXPLAIN item 3: the 20% step costs 14.8 s cold and must not ship). Accept a short session on an empty result.

**Reconstruction:** load `Game.pgn` only for picks, then the existing `fen_and_last_move_at_ply` path used for SR reconstruction in `_assemble_session_items`; drop failures.

---

### `_pick_foreign` (pure function, transform)

**Analog:** pinned Elo via `blunder_check_selection._pinned` (143-158), which is private; use its public callees directly:
```python
return pinned_elo_for_mover(
    raw_rating=raw_rating,
    platform=cast(Platform, platform),
    time_control_bucket=cast(TimeControlBucket | None, time_control_bucket),
    is_correspondence=is_correspondence_time_control(time_control_str),
)
```
Nearest-first ordering: `_fill_nearest_first` (735-760) widens the reach one band at a time with no distance cap (Phase 251 UAT). For a flat candidate list the equivalent is: in-band shuffled first, then out-of-band sorted by `abs(pinned - level)`. Seeded RNG: namespaced string seed `random.Random(f"train-foreign:{user_id}:{today.isoformat()}")` (RESEARCH § Python pick). Keep it free of I/O so a unit test can call it with hand-built rows; nesting depth <= 4 (use early `continue`).

---

### Owner-aware joins (repository, CRUD read)

**Analog:** `_answer_keys_by_position` (train_repository.py 3226-3253). Current SR join, to keep byte-identical:
```python
.outerjoin(
    GameFlaw,
    and_(
        GameFlaw.user_id == DrillSolve.user_id,
        GameFlaw.game_id == DrillSolve.game_id,
        GameFlaw.ply == DrillSolve.ply,
    ),
)
.outerjoin(
    GamePosition,
    and_(
        GamePosition.user_id == DrillSolve.user_id,
        GamePosition.game_id == DrillSolve.game_id,
        GamePosition.ply == DrillSolve.ply,
    ),
)
```
Aliasing convention in this codebase: `GuardPos = aliased(GamePosition, name="best_move_guard_pos")  # noqa: N806` (`library_repository.py:898`) or lowercase `gp1 = aliased(GamePosition, name="gp1")` (`openings_repository.py:460`). Use a module-level or local `aliased(GameFlaw, name="foreign_flaw")` and add a source-gated join (`DrillSolve.source == DrillSource.FOREIGN_BLUNDER`, `ForeignFlaw.user_id == Game.user_id`, game_id, ply) after `.outerjoin(Game, Game.id == DrillSolve.game_id)`. Then `func.coalesce` or a Python pick of the two blob columns per source in `_position_answer_key`. RESEARCH Pattern 1 has the shape; apply the same alias pair at each site in § Solver-Ownership Assumptions. Every site must still filter `DrillSolve.user_id == user_id` in the WHERE (V4/IDOR).

**Completion leniency** (`_mark_session_complete_if_done`, 4036-4047), current:
```python
# Same leniency for a sharp filler with a NULL identity column: ...
or_(
    DrillSolve.source != DrillSource.SHARP_FILLER,
    DrillSolve.sharp_puzzle_id.isnot(None),
),
```
Replace with the bug-fix-commented single clause from RESEARCH § Code Examples (`DrillSolve.source != DrillSource.LEGACY_SHARP_FILLER`). The herring clause right above (`or_(DrillSolve.source != RED_HERRING, HerringPool.id.isnot(None))`) is the pattern for a FOREIGN orphan clause (`or_(source != FOREIGN_BLUNDER, ForeignFlaw.game_id.isnot(None))`).

---

### `reveal_for_puzzle` FOREIGN branch (repository, request-response)

**Analog for the played move:** the herring ownership gate, `train_repository.py` 4665-4676:
```python
played_in_game_san: str | None = None
if game is not None and game.user_id == user_id:
    position_row = (
        await session.execute(
            select(GamePosition.move_san).where(
                GamePosition.user_id == user_id,
                GamePosition.game_id == game.id,
                GamePosition.ply == solve.ply,
            )
        )
    ).one_or_none()
    played_in_game_san = position_row.move_san if position_row is not None else None
```
Leave this gate untouched (D-20). Add a separate `elif solve.source == DrillSource.FOREIGN_BLUNDER and game is not None:` branch with `GamePosition.user_id == game.user_id`, and expose it under a neutral field or label (planner choice), never under the existing "Played in game" label semantics.

**FEN branch** (4684-4693): delete the `SHARP_FILLER` arm; FOREIGN falls to the `full_fen_at_ply(game.pgn, solve.ply)` arm, guarded by the extended not_found gate (`game is None` for SR or FOREIGN -> not_found, D-09).

**Analog for `game_info`:** `blunder_check_repository.game_info_for` (1272-1299)
```python
@dataclass(frozen=True)
class GameInfoRow:
    """Neutral facts about a game: nothing that identifies its owner (D-09)."""
    time_control_str: str | None
    time_control_bucket: str | None
    played_at: datetime.datetime | None
    mover_rating: int | None
```
```python
owner_rating = case((Game.user_color == "white", Game.white_rating), else_=Game.black_rating)
```
The reveal already has the `game` ORM row loaded, so build `GameInfoRow(...)` from it in Python (owner rating = `game.white_rating if game.user_color == "white" else game.black_rating`) instead of a second query; reuse the `GameInfoRow` type by import.

**Router mapping:** copy `_game_info_schema` from `app/routers/blunder_check.py:389-398`:
```python
def _game_info_schema(info: GameInfoRow | None) -> GameInfo | None:
    if info is None:
        return None
    return GameInfo(
        time_control_str=info.time_control_str,
        time_control_bucket=cast(TimeControlBucketWire | None, info.time_control_bucket),
        played_at=info.played_at,
        mover_rating=info.mover_rating,
    )
```
Either import `GameInfo` from `app.schemas.blunder_check` into `app/schemas/train.py` (`game_info: GameInfo | None = None`) or move it to a shared schema module; importing is the smaller change. Same for the frontend type `GameInfo` in `frontend/src/types/blunderCheck.ts:157-163`.

---

### `_wire_source` and the source Literals (utility, transform)

**Analog:** itself, 3484-3509. Keep the exhaustive if-chain and the final `raise ValueError(f"Unrecognized DrillSource value: {source!r}")` (existing line; do not add new variable-embedding messages elsewhere). Add `FOREIGN_BLUNDER -> "foreign_blunder"`, rename the value-2 arm to `LEGACY_SHARP_FILLER -> "sharp_filler"`. Widen the return Literal and the matching Literals on `ComposedSolvedResult.source`, `RecordedSolve.source`, `RevealedPuzzle.source`, and `app/schemas/train.py` `SolvedResult` / `SolveResponse` / `PuzzleRevealResponse`.

---

### `app/models/drill_solve.py` (model)

**Analog:** lines 87-93 and 126:
```python
class DrillSource(IntEnum):
    SR_ITEM = 0
    RED_HERRING = 1
    SHARP_FILLER = 2
...
CheckConstraint("source IN (0, 1, 2)", name="ck_drill_solves_source"),
```
-> `LEGACY_SHARP_FILLER = 2`, `FOREIGN_BLUNDER = 3`, `"source IN (0, 1, 2, 3)"`. Update the class docstring. Delete `sharp_puzzle_id` (161-165) and `drill_session.py` `is_warmup` (306-310) together with the migration; remove now-unused `Text`/`Boolean` imports.

---

### Alembic migration (migration, DDL + data)

**Analog 1 (exact inverse):** `alembic/versions/20260807_114022_e5f71b11fa51_phase_206_sharp_filler_source.py`. Upgrade body to mirror:
```python
op.drop_constraint("ck_drill_solves_source", "drill_solves", type_="check")
op.create_check_constraint("ck_drill_solves_source", "drill_solves", "source IN (0, 1, 2)")
```
Its downgrade docstring's bug-fix note (DELETE before narrowing the CHECK, caught only by serial CI) is the template for this phase's downgrade: `op.execute("DELETE FROM drill_solves WHERE source = 3")` before re-creating `"source IN (0, 1, 2)"`, then re-add `sharp_puzzle_id TEXT NULL` and `is_warmup BOOLEAN NOT NULL server_default "false"` (`sa.Column("is_warmup", sa.Boolean(), server_default="false", nullable=False)`). Header: module docstring stating the one-way parts (D-04), `revision`/`down_revision = "e5c1b7d3a9f2"` typed as in the analog.

**Analog 2 (testable statements):** `20261201_120000_e5c1b7d3a9f2_quick_261123_lb8_blunder_check_points_rescale.py` lines 24, 54-74 expose `UPGRADE_STATEMENTS` / `DOWNGRADE_STATEMENTS: tuple[str, ...]` at module level and loop `op.execute(sa.text(statement))`. Use this for the data step (delete untouched open sessions holding unsolved source-2 rows, RESEARCH § Schema and Migration step 4) so the test can run the exact SQL. DDL can stay as `op.*` calls. Literal values only, no app-constant imports (`f3a7b9c1e259` docstring rule).

### Migration test (test)

**Analog:** `tests/routers/test_blunder_check_points_migration.py`
- Load the module by path (lines 41-46, 75-80):
```python
spec = importlib.util.spec_from_file_location("lb8_points_rescale", _MIGRATION_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```
- Chain test (105-108): `assert module.revision == ...; assert module.down_revision == "e5c1b7d3a9f2"`.
- Round trip inside a rolled-back transaction (147-157):
```python
async with test_engine.connect() as conn:
    async with conn.begin() as transaction:
        before = await _snapshot(conn, session_ids)
        for statement in migration.DOWNGRADE_STATEMENTS:
            await conn.execute(sa.text(statement))
        ...
        await transaction.rollback()
```
- `try/finally` cleanup of committed seed rows (158-159). For this phase: seed one untouched open session with an unsolved source-2 row and one touched one; assert only the untouched one is deleted by the data statement.

---

### `own_puzzle_count` (derived, non-persisted response field)

**Analog:** `ComposedSession.requested_count` / `blob_pending_count` (train_repository.py 303-329), computed per response and passed through to `TrainSessionResponse` in `app/routers/train.py:110-154`. Resume path: replace
```python
# Read the stored column, never recompute — ...
is_warmup=drill_session.is_warmup,
```
(2306-2309) with a count over the session's rows. `blob_pending_count` at 1537 (`(await session.execute(blob_pending_stmt(user_id))).scalar_one()`) is the one-scalar query shape; a sibling `select(func.count()).where(DrillSolve.session_id == ..., DrillSolve.source == DrillSource.SR_ITEM)` fits. Fresh path: `len(items.surviving_sr_keys)`. Docstring must say why recomputation is safe now (rows never change source), replacing the old "never recompute" comment.

---

### Neutral footer (frontend component)

**Analog:** `frontend/src/components/train/blunder-check/BlunderCheckGameFooter.tsx` lines 41-52:
```tsx
function ForeignGameFooter({ gameInfo }: { gameInfo: GameInfo | null }): ReactElement | null {
  if (gameInfo === null) return null;
  return (
    <GameLine
      parts={[
        timeControlLabel(gameInfo.time_control_bucket, gameInfo.time_control_str),
        gameInfo.mover_rating === null ? null : `player rated ${gameInfo.mover_rating}`,
        gameInfo.played_at === null ? null : formatDateWithYear(gameInfo.played_at),
      ]}
    />
  );
}
```
`GameLine` hard-codes `data-testid="blunder-check-game-footer"`. Export `ForeignGameFooter` with an optional testid prop (or extract `GameLine`/`ForeignGameFooter`/`timeControlLabel` to a shared module) so Train gets its own testid (e.g. `train-reveal-foreign-game-footer`). Consumer: `TrainRevealGameFooter.tsx:53` currently `if (verdict.source !== 'sr_item') return null;`; add a `verdict.source === 'foreign_blunder'` branch before it that renders the neutral footer from `revealQuery.data?.game_info` (note the comment at 38-52 about reading `verdict` vs `revealQuery`: the foreign footer necessarily waits for the reveal query, document that). knip will flag any leftover unused export.

---

### `returnPhrase` (frontend copy)

**Analog:** `frontend/src/lib/trainBotCopy.ts` 530-580. Pattern: a module-level `const XXX_TAIL = "..."` and one guard-clause line per source.
```ts
const HERRING_TAIL = "A red herring, so it won't come back.";
const FILLER_TAIL = "Not from your games, so it won't come back.";
...
if (input.source === 'red_herring') return HERRING_TAIL;
if (input.source === 'sharp_filler') return FILLER_TAIL;
```
Replace `FILLER_TAIL` with `FOREIGN_TAIL` (D-11 copy) keyed on `'foreign_blunder'`, map `'sharp_filler'` to `''`, delete the `is_warmup` field and the `neverReturns && is_warmup` early return, widen the `source` union. Rewrite the docstring (it explains warm-up).

---

### Activity source rows (admin frontend)

**Analog:** `frontend/src/pages/activity/render.js` 384-390:
```js
// One row per DrillSource value (0 SR item, 1 red herring, 2 sharp filler), in
// display order. ...
const PZ_DIFF_ROWS=[
  {source:0,label:"Own flaw · own"},{source:1,label:"Herring · foreign"},
  {source:2,label:"Sharp filler · lichess"}];
```
`puzzleDifficultyRow` looks up by `def.source`, so adding `{source:3,label:"Similar player's blunder"}` and relabelling 2 to `"Sharp filler · lichess (retired)"` is all render needs (the SQL in `activity_queries.fetch_puzzle_difficulty` already groups by source). Update the comment, the card note in `ActivityPage.tsx:556-564` (keep the plain-prose style, mention retired), `frontend/scripts/check-activity-layout.mjs` labels, and `docs/activity-dashboard.md`.

---

### `tests/conftest.py` autouse stub + opt-in fixture (test fixture)

**Analog 1 (autouse default + opt-in installer):** `tests/repositories/test_train_repository.py` 385-418
```python
def _install_sharp_fixture(monkeypatch: pytest.MonkeyPatch, puzzles: ... = _TEST_SHARP_PUZZLES) -> None:
    ...
    monkeypatch.setattr(sharp_filler, "SHARP_SET", ordered)
    monkeypatch.setattr(train_repository, "SHARP_SET_BY_ID", by_id)

@pytest.fixture(autouse=True)
def _default_empty_sharp_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file defaults to an EMPTY sharp-filler set unless it opts in ..."""
    monkeypatch.setattr(...)
```
Note the docstring's warning: patch the name where it is looked up (`train_repository` binds imports at import time). For the foreign seam, stub the attribute that `_backfill_foreign_blunders` calls through the module (e.g. `monkeypatch.setattr(train_repository, "_draw_foreign_candidates", _empty)`), so one patch covers every caller.

**Analog 2 (conftest autouse placement and docstring style):** `tests/conftest.py` 577-587 (`reset_blob_claim_leases`): plain `@pytest.fixture(autouse=True)`, function-local import of the app module, docstring explaining the cross-test bleed. Put the stub there, replacing the four per-file sharp fixtures (`test_train_repository.py:404`, `tests/routers/test_train.py:229`, `test_cross_mode_cooldown.py:62`, `test_train_two_mode_streak.py:86`).

**Analog 3 (opt-in real draw):** `tests/services/test_blunder_check_selection.py` 228-240:
```python
monkeypatch.setattr(blunder_check_selection, "FOREIGN_SAMPLE_PERCENT", 100.0)
...
caller = await _user(test_engine, "bcs-origin")
stranger = await _user(test_engine, "bcs-origin-stranger")
foreign_ids = await _seed_games(test_engine, stranger, 5)
try:
    windows = await _compose(test_engine, caller, seed=3)
finally:
    await delete_games(test_engine, own_ids + foreign_ids)
```
The opt-in `foreign_pool` fixture undoes the stub (request the fixture, `monkeypatch.undo` is not selective, so instead re-set the attribute to the real function), patches the Train sample percents to 100.0, seeds a non-guest stranger's rated games with qualifying blunders (seed helpers in `tests/blunder_check_seed.py:211-253`), and deletes them in `finally` (memory rule: every committed non-guest Game insert needs finally-cleanup).

## Shared Patterns

### Guest and own-game exclusion in cross-user reads
**Source:** `blunder_check_repository.py:533-537`
**Apply to:** every foreign candidate statement.
```python
sampled.c.user_id != user_id,
User.is_guest.is_(False),
sampled.c.platform.in_(ANALYTICS_INCLUDED_PLATFORMS),
```

### Neutral-facts rule (249 D-09)
**Source:** `GameInfoRow` docstring (`blunder_check_repository.py:1274`), `GameInfo` (`schemas/blunder_check.py:191`), `ForeignGameFooter`.
**Apply to:** reveal response, footer, and the wire `game_id` (send `None` for FOREIGN in `TrainPuzzle` and `PuzzleRevealResponse`, RESEARCH § D-21).

### Exhaustive source mapping, raise on unknown
**Source:** `_wire_source` (3484-3509).
**Apply to:** any new per-source dispatch (`_classify_and_certify_solve`, `_position_answer_key`). No two-way if/else that silently mislabels.

### Bug-fix comments at the fix site
**Source:** `e5f71b11fa51` downgrade docstring; `_mark_session_complete_if_done` leniency comment.
**Apply to:** completion leniency change, migration downgrade DELETE, the herring/foreign collision exclusion (Pitfall 2).

### Constants
**Source:** `blunder_check_selection.py:86-120` (comment line above each typed constant).
**Apply to:** Train foreign sample percents, candidate game limit, escalation cap.

## No Analog Found

| Seam | Role | Data Flow | Reason |
|---|---|---|---|
| Thin-tail fallback for 2400+ with a latency budget | statement builder | batch | Blunder check's `pick_nearest_foreign_game_ids` at `FOREIGN_WIDE_SAMPLE_PERCENT = 20.0` measured 14.8 s cold on prod. The shape (ORDER BY abs distance, LIMIT pool, then random) is reusable; the cost profile is not. Planner must pick an escalation (small percent steps or a wider raw band on the small sample) with a hard cap. |

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/routers/`, `app/schemas/`, `app/models/`, `alembic/versions/`, `tests/`, `frontend/src/components/train/`, `frontend/src/lib/`, `frontend/src/pages/activity/`
**Files scanned:** ~20
**Pattern extraction date:** 2026-11-23
