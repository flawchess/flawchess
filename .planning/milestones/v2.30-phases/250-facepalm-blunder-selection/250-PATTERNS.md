# Phase 250: Facepalm-Blunder Selection - Pattern Map

**Mapped:** 2026-11-13
**Files analyzed:** 22 (new + modified, tests grouped)
**Analogs found:** 20 / 22

All analog paths below are git-tracked source (no `.gsd` mirrors).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/<ts>_phase_250_facepalm.py` (new) | migration | schema | `alembic/versions/20261109_120000_c4e9b1d7f248_phase_248_maia_refutation.py` | exact |
| `app/models/game_flaw.py` (mod: 8 cols) | model | CRUD | same file, Phase 248 block lines 116-123 | exact |
| `app/models/game.py` (mod: 2 stamps) | model | CRUD | same file, `maia_refutation_completed_at` lines ~280-288 | exact |
| `app/services/line_material.py` (new) | utility (pure) | transform | `app/services/maia_flaw_stats.py` (pure, TypedDict, no I/O) | role-match |
| `app/services/facepalm_score.py` (new) | utility (pure + SQL twin) | transform | `app/services/train_pool.py:206-260` (`expected_score_sql` / `expected_score_for`) | exact |
| `app/services/maia_flaw_stats.py` (mod: public `reply_spread`) | utility | transform | own `_effective_moves` lines 97-100 | exact |
| `app/services/maia_flaw_scoring.py` (mod: hook) | service | event-driven (post-commit hook) | own `_derive_refutation` 347-383, `_flaw_row` 442-464, `_refutation_row` 467+ | exact |
| `app/repositories/game_flaws_repository.py` (mod) | repository | CRUD | own `MAIA_REFUTATION_COLUMNS` 188-195, `clear_maia_flaws_completed` 344-367 | exact |
| `app/services/blunder_check_rules.py` (mod) | utility (constants + draw) | transform | own constants 43-80, `draw_window_shape` / `hazard_position_weights` | exact |
| `app/services/blunder_check_candidates.py` (mod) | service (pure) | transform | own `_blunder_candidate` 179-227 | exact |
| `app/services/blunder_check_selection.py` (mod) | service | request-response | own `compose_windows`, `reference_elo` | exact |
| `app/repositories/blunder_check_repository.py` (mod) | repository | CRUD | own `load_blunder_flaws`, `pick_*_game_ids`, `served_for_games`, `recent_rated_games` | exact |
| `app/repositories/current_strength_repository.py` (read-only reference for D-14 filter) | repository | CRUD | `apply_game_filters(rated=True, opponent_type="human")` usage lines 97-115 | reference |
| `scripts/backfill_maia_flaws.py` (mod: `spread`, `line --cutoff`) | script | batch | own `_STAMP_CLAUSE_BY_MODE`, `_start_maia_and_run` | exact |
| `scripts/blunder_check/facepalm_features.py` (new) | script | batch / file-I/O | `scripts/blunder_check/sample.py` (`make_readonly_engine`, records) | role-match |
| `scripts/blunder_check/fit_facepalm.py` (new) | script | batch / transform | none (no numpy fit in repo) | none |
| `scripts/blunder_check/{sample,render,spot_check,oddness,metrics}.py` (mod) | script | batch | themselves | exact |
| `tests/services/test_line_material.py` + fixture module (new) | test | - | `tests/services/test_maia_flaw_stats.py` | role-match |
| `tests/services/test_facepalm_score.py` (new, incl. SQL parity) | test | - | twin parity tests for `expected_score_sql` (grep `expected_score_sql` in tests/) | role-match |
| `tests/services/test_maia_flaw_scoring.py`, `tests/scripts/test_backfill_maia_flaws.py`, `tests/services/test_blunder_check_{candidates,selection,rules}.py`, `tests/repositories/test_blunder_check_repository.py`, `tests/scripts/test_blunder_check_calibration.py`, `tests/blunder_check_seed.py` (mod) | test | - | themselves | exact |
| D-11 drop migration (last plan) | migration | schema | 248 migration `downgrade()` (drop_column) | exact |
| `reports/blunder-check/facepalm-features-<date>.tsv` (new data) | data | file-I/O | `reports/blunder-check/leg2-labels-2026-11-11.tsv` | format-match |

## Pattern Assignments

### Migration (new) — analog `alembic/versions/20261109_120000_c4e9b1d7f248_phase_248_maia_refutation.py`
Copy whole file shape: docstring explaining "deliberately metadata-only: no server_default, no CHECK, no index, no data UPDATE" (instant on 7.6M rows). `down_revision = "d5b8e2f1a249"` (current head, Phase 249).
```python
def upgrade() -> None:
    op.add_column("game_flaws", sa.Column("maia_refutation_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_refutation_rank", sa.SmallInteger(), nullable=True))
    op.add_column("games", sa.Column("maia_refutation_completed_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("games", "maia_refutation_completed_at")
    ...
```
New: `maia_reply_spread` REAL, `line_loss_1/3/5/7/9` SmallInteger, `line_mate_ply` SmallInteger, `facepalm_score` REAL; `games.facepalm_spread_completed_at`, `games.facepalm_line_completed_at`. The D-11 drop migration inverts this (drop in upgrade, re-add nullable in downgrade).

### `app/models/game_flaw.py` / `app/models/game.py`
Analog block `game_flaw.py:116-123`: comment stating meaning, NULL semantics, "Written only by app/services/maia_flaw_scoring.py, never by flaw_record_to_row, so a diff/upsert preserves them by omission", then
```python
maia_refutation_prob: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)
maia_refutation_rank: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```
`game.py` stamp pattern (`maia_refutation_completed_at`): `Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)` with comment "No index on purpose" and "Cleared ... by a reclassification (clear_maia_flaws_completed)".

### `app/services/line_material.py` (new, pure) — analog `app/services/maia_flaw_stats.py`
Conventions to copy: module-level named constants with type annotations (`RANK_BASE: int = 1`, `_ENTROPY_LOG_BASE: float = 2.0`), `Literal` reason types, TypedDict/frozen dataclass outputs, a `null_*()` constructor, no I/O. Shape from RESEARCH Pattern 2:
```python
LINE_LOSS_DEPTHS: tuple[int, ...] = (1, 3, 5, 7, 9)
@dataclass(frozen=True, slots=True)
class LineFacts:
    loss_by_depth: Mapping[int, int | None]
    mate_ply: int | None
def line_facts(pre_board: chess.Board, played_uci: str, pv: str | None) -> LineFacts: ...
```
Board handling: copy the never-mutate pattern from `maia_flaw_scoring._derive_refutation` (`post = pre_board.copy(stack=False)`), and the malformed-UCI guard:
```python
try:
    refutation = chess.Move.from_uci(refutation_uci)
except ValueError:
    # Worker-supplied strings land in game_positions (T-248-01) ...
    return null_refutation_stats(), "refutation_not_legal"
```
pv split on `REFUTATION_PV_SEPARATOR: str = " "` (`maia_flaw_scoring.py:98`). Semantics: RESEARCH Q2 "What capture_loss does" + fixture table (#153,#156,#165,#170,#176,#177,#13,#35,#154,#184, mate rows).

### `app/services/facepalm_score.py` (new) — analog `app/services/train_pool.py:206-260`
Twin discipline: SQL docstring names its Python twin and vice versa, "If either side changes, update the other".
```python
def expected_score_sql(cp_col: Any, mate_col: Any, user_color_col: Any) -> ColumnElement[float]:
    sign = case((user_color_col == "white", 1.0), else_=-1.0)
    ...
    return case(
        (mate_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * mate_cp_equiv))),
        (cp_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * cp_col))),
        else_=literal(None),
    )
```
For facepalm: `case((any input IS NULL, literal(None)), else_=1/(1+func.exp(-z)))` with `z = INTERCEPT + B_PLAYED*func.ln(played + PLAYED_PROB_OFFSET) + B_SPREAD*spread + B_LOSS*case((mate_ply <= LINE_DEPTH, MATE_LOSS), else_=func.least(loss3, LOSS_CAP))`. Constants (D-04): coefficients, `PLAYED_PROB_OFFSET`, `LINE_DEPTH`, `LOSS_CAP`, `MATE_LOSS`.

### `app/services/maia_flaw_stats.py` (mod)
Make `_effective_moves` (lines 97-100) public / wrap:
```python
def _effective_moves(probs: Mapping[str, float]) -> float:
    """2 ** (Shannon entropy in bits over all legal moves)."""
    entropy_bits = -sum(p * math.log2(p) for p in probs.values() if p > 0.0)
    return float(_ENTROPY_LOG_BASE**entropy_bits)
```
Add a `FacepalmStats` TypedDict + `null_facepalm_stats()` mirroring `MaiaRefutationStats` / `null_refutation_stats()` (lines ~60-70).

### `app/services/maia_flaw_scoring.py` (mod, hook)
- `FlawFingerprint` (line 82) + `fingerprint_of` (118-121) + `FlawMaiaInput` (dataclass ~104-115): add `refutation_pv: str | None`; select `gp_next.pv` in `_flaw_fingerprint_select` (160+).
- `ScoringMode = Literal["full", "refutation"]` (line 78) → add `"spread"`, `"line"`.
- Restructure `_derive_refutation` (347-383) into `_derive_post_blunder`: keep the `played_not_legal` / `no_legal_reply` early returns, run `full_policy(post.fen(), elo)` once, `raise MaiaInferenceUnavailableError` on None, compute spread always, refutation pair only if UCI usable.
- `_derive_flaw_values` (405-435) branch point: `if stats is None or not _is_user_blunder(inputs, flaw): return ...` — extend outputs with facepalm stats.
- `_flaw_row` (442-464): `row.update(...)` every key for EVERY flaw (null for out-of-scope) — docstring D-08 rationale.
- New per-mode row builders mirror `_refutation_row` (467+).
- `_is_user_blunder` (340-344) reused for D-06 scope.

### `app/repositories/game_flaws_repository.py` (mod)
Add `FACEPALM_COLUMNS` tuple after `MAIA_REFUTATION_COLUMNS` (188-195) with the same "its OWN tuple ... flaw_record_to_row must never emit these keys" comment. Extend `clear_maia_flaws_completed` (344-367): add both new stamps to the `or_(...isnot(None))` and `.values(...)`; update docstring.

### `app/services/blunder_check_rules.py` (mod)
Constants block style (lines 43-80): comment citing decision ID above each constant.
```python
# 249 D-06 findability thresholds: ...
REFUTATION_PROB_MIN: float = 0.3
BEST_PROB_MIN: float = 0.2
```
Replace with `FACEPALM_SCORE_MIN: float = 0.7` (D-01/D-04), D-12 shares (`HERRING_SHARE`, `OWN_BLUNDER_SHARE`, `FOREIGN_BLUNDER_SHARE`). Remove `FindabilityInputs` TypedDict, `_pair_passes`, `findable` (264-288). New conditional-hazard draw next to `draw_window_shape`:
```python
def draw_window_shape(rng: random.Random) -> WindowShape:
    length = rng.choice(WINDOW_LENGTHS)
    for position in range(1, length + 1):
        if rng.random() < HAZARD:
            return WindowShape(length, position)
    return WindowShape(length, None)
```
Closed-form P(k|L) ∝ h(1-h)^(k-1) reuses the `hazard_position_weights` loop shape.

### `app/services/blunder_check_candidates.py` (mod)
In `_blunder_candidate` (179-227) replace the block
```python
maia = FindabilityInputs(refutation_prob=flaw.maia_refutation_prob, ...)
if not findable(case, maia, REFUTATION_PROB_MIN, BEST_PROB_MIN):
    return None
```
with `if flaw.facepalm_score is None or flaw.facepalm_score < FACEPALM_SCORE_MIN: return None`. Rename param `prompted_blunder_plies` → `served_blunder_plies` (D-17). `FlawLike` protocol (lines 79-89) swaps the four fields for `facepalm_score: float | None`. Keep `miss_case` "unclassified" drop.

### `app/services/blunder_check_selection.py` (mod)
- Constants block 57-73: replace `FOREIGN_ELO_BANDS: tuple[int, ...] = (100, 200)` with `FOREIGN_RATING_BAND: int = 150`; add `USER_LEVEL_SCAN_GAMES`, `DEFAULT_USER_LEVEL_ELO: int = 1500`.
- `reference_elo` (124-139) is the template for new pure `user_level_elo(rows)` (group by `time_control_bucket`, most-played, median `_pinned`, skip correspondence via `is_correspondence_time_control`).
- `compose_windows` (452-471): replace own-first/foreign-fallback with per-slot source draw; keep the `new_session_rng()` monkeypatch seam and the contiguous renumbering loop.

### `app/repositories/blunder_check_repository.py` (mod)
- `BlunderFlawRow` (~328-338) + `load_blunder_flaws`: select `GameFlaw.facepalm_score`, add `GameFlaw.facepalm_score >= FACEPALM_SCORE_MIN` to `.where(...)`; keep `BlunderFlawRow(*row[1:])` positional construction.
- `pick_own_game_ids` (191-203) / `pick_foreign_game_ids` (206+): add keyword `require_facepalm: bool = False` → `.where(exists().where(GameFlaw.game_id == Game.id, GameFlaw.facepalm_score >= FACEPALM_SCORE_MIN))` (for foreign use `sampled.c.id`). Keep the "only game ids leave the repository" rule.
- `served_for_games` (~380-419): replace answer-joined `prompted_stmt` with
  `select(BlunderCheckWindow.game_id, BlunderCheckWindow.blunder_ply).where(user_id==, game_id.in_(...), blunder_ply.isnot(None))`; rename `ServedSets.prompted` → `served_blunder_plies`; update docstring (D-17).
- `recent_rated_games` (~436-453): compose `apply_game_filters(..., rated=True, opponent_type="human", platform=None)` from `app/repositories/query_utils.py` (CLAUDE.md: never duplicate filter logic); pattern in `app/repositories/current_strength_repository.py:97-115`.

### `scripts/backfill_maia_flaws.py` (mod)
```python
BACKFILL_MODE_CHOICES: tuple[str, ...] = ("full", "refutation")
_STAMP_CLAUSE_BY_MODE: dict[BackfillMode, str] = {
    "full": "g.maia_flaws_completed_at IS NULL",
    "refutation": ("g.maia_refutation_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL"),
}
```
Add `"spread": "g.facepalm_spread_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL"` and `"line": "(g.facepalm_line_completed_at IS NULL OR g.facepalm_line_completed_at < CAST(:cutoff AS timestamptz)) AND g.facepalm_spread_completed_at IS NOT NULL"` (cutoff bound, never interpolated). Keep `SHARD_RESIDUE_SQL`, `_SELECT_SHARD_SQL`, `MAX_GAMES_PER_WRITE_TXN`. Make `_start_maia_and_run` (497-506) mode-aware: line mode skips `start_maia` and the `EXIT_MAIA_UNAVAILABLE` gate. Status: mirror `_user_blunder_count_stmt` / `_fetch_refutation_status` (652-690). `--cutoff` required for line mode, echoed in `ShardReport`.

### `scripts/blunder_check/facepalm_features.py` (new) — analog `scripts/blunder_check/sample.py`
Use `make_readonly_engine(url)` (sample.py:95-103: `pool_size=1, max_overflow=0, connect_args=readonly_connect_args()`) for `--db prod`. Import app pure functions (`line_facts`, `reply_spread`, `facepalm_score`); app never imports scripts.

### `scripts/blunder_check/fit_facepalm.py` (new) — no analog
Use RESEARCH Pattern 6 / Q6 (numpy IRLS, seeded 10-fold CV, constants block output). Run with `uv run --group maia-inference`.

### Calibration scripts (mod)
`sample.py` `BlunderRecord` (176-222) / `_load_flaws` (488-552): swap four best/refutation fields for `facepalm_score`, `maia_reply_spread`, `line_loss_3`, `line_mate_ply`; bump cache version. `metrics.py`: drop `findable` re-export. `render.py`/`spot_check.py` (438-466)/`oddness.py` (183) per RESEARCH Q7.

## Shared Patterns

### Preservation by omission + stamp clear
**Source:** `app/repositories/game_flaws_repository.py:176-195, 344-367`; test precedent `test_reclassify_without_maia_keeps_survivors_nulls_new_unstamps` (`tests/services/test_maia_flaw_scoring.py` ~1264). **Apply to:** model, repository, hook.

### Hook never raises; Sentry
**Source:** `score_game_flaws_after_apply` (`maia_flaw_scoring.py:653-692`): `capture_exception` on unexpected errors, `StaleDataError` logged as expected. No variables in messages; use `set_context`.

### Write under advisory locks + fingerprint re-check
**Source:** `_lock_games_ascending` (555-570), `write_game_maia_scores` (590+), `GameOutcome` literals. Line mode adds a "stamp >= cutoff" variant of `already_stamped`.

### Named constants with decision-ID comments
**Source:** `blunder_check_rules.py:43-80`, `blunder_check_selection.py:57-73`.

### Pure test module header
**Source:** `tests/services/test_maia_flaw_stats.py:1-25` — `"""Pure unit tests ... No DB, no ORT."""`, `from __future__ import annotations`, FEN constants, `fake_full_policy` from `tests/services/maia_fakes.py`.

### Twin parity test
SQL twin evaluated via `select(facepalm_score_sql(literal(...), ...))` against the Python twin on a grid; same pattern as the `expected_score_sql` tests.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `scripts/blunder_check/fit_facepalm.py` | script | transform | No regression/fit code in repo; follow RESEARCH Q6 (numpy IRLS) |
| Conditional hazard draw in `blunder_check_rules.py` | utility | transform | Partial: built from `hazard_position_weights` loop, but the conditional closed form is new |

## Metadata
**Analog search scope:** app/services, app/repositories, app/models, alembic/versions, scripts/, scripts/blunder_check, tests/services
**Files scanned:** ~15
**Pattern extraction date:** 2026-11-13
