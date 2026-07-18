# Phase 178: Lichess-compatible accuracy & ACPL (computed columns) - Research

**Researched:** 2026-07-18
**Domain:** Backend eval-derived metric computation (Python port of lichess accuracy/ACPL formulas) + Alembic column repurposing + live-hook wiring
**Confidence:** HIGH (eval semantics, sign, post-move shift, and ACPL formula empirically reproduced against the dev DB to the exact imported value; formulas cross-checked against lichess source in SEED-110)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Canonical columns `white_accuracy` / `black_accuracy` / `white_acpl` / `black_acpl` become **our uniform lichess-formula values** for every analyzed game.
- **D-02:** Current platform-provided values move into new `*_imported` columns: `white_accuracy_imported` / `black_accuracy_imported` / `white_acpl_imported` / `black_acpl_imported`.
- **D-03:** Migration flow: add `*_imported` columns → copy existing values in → NULL the canonical columns → code (hook + backfill) refills canonical. Keep types: `REAL` for accuracy, `SmallInteger` for acpl, nullable.
- **D-04:** ONLY accuracy + acpl are moved/repurposed. `inaccuracies`/`mistakes`/`blunders` left **completely untouched** (`white_blunders IS NOT NULL` is the `is_analyzed` sentinel).
- **D-05:** No API/frontend changes. `accuracy`/`acpl` are not surfaced today.
- **D-06:** Ship migration, compute path, live hook, and `scripts/backfill_*.py` (verified on dev). Prod backfill (~718k games) is a separate operator step; phase completion NOT gated on it. Batch + `--db dev|benchmark|prod`.
- **D-07:** Validation script comparing computed `accuracy`/`acpl` vs preserved `*_imported`; PLUS hand-checked fixture unit tests against a known lichess game's published accuracy/ACPL.
- **D-08:** Win% from cp: `50 + 50*clamp(2/(1+exp(-0.00368208*cp))-1, -1, +1)`, with `cp` ceiled to ±1000 BEFORE the sigmoid; mate → ±1000 by sign.
- **D-09:** Per-move accuracy: `clamp(103.1668100711649*exp(-0.04354415386753951*(before-after)) - 3.166924740191411 + 1, 0, 100)` (evals from the moving player's POV; trailing +1 is real).
- **D-10:** Game-level accuracy: seed sequence with initial position at 15cp, sliding volatility window `windowSize = clamp(nMoves//10, 2, 8)`, per-window weight `clamp(pop_stddev(window), 0.5, 12)`, then per color `(weightedMean(acc, weights) + harmonicMean(acc)) / 2`. Start padded with `windowSize-2` copies of the first window.
- **D-11:** ACPL = arithmetic mean of `max(0, before_cp - after_cp)` (mover's POV, evals capped ±1000). Plain mean, NOT the volatility/harmonic aggregation.

### Claude's Discretion (researched below)
- Exact live-hook seam (§ Live-Hook Seam) — **resolved: `apply_full_eval`**.
- Eval sign convention + post-move shift (§ Eval Semantics) — **resolved empirically**.
- Terminal ply / checkmate handling, games with 0–1 moves (§ Eval Semantics, § Edge Cases).
- Data-move migration mechanics + complete-sequence gate query (§ Migration, § Complete-Sequence Gate).

### Deferred Ideas (OUT OF SCOPE)
- Surfacing computed accuracy/ACPL in API + frontend (future phase).
- Uniform recomputation of inaccuracy/mistake/blunder counts.
- Running the prod backfill to 100% coverage (operator step).
</user_constraints>

<phase_requirements>
## Phase Requirements

No requirement IDs mapped for this phase (REQUIREMENTS.md TBD). The locked decisions D-01..D-11 above are the acceptance surface.
</phase_requirements>

## Summary

This is a self-contained backend phase: port four lichess formulas to Python, write the result into repurposed canonical `games` columns via one shared compute path used by both a live hook and a backfill script, after a data-preserving migration. **No new external packages** — pure `math` stdlib plus the existing `app.services.eval_utils.LICHESS_K = 0.00368208` constant already in the codebase.

The single highest-risk area (eval sign + post-move shift + mover parity) is **fully resolved and empirically verified**: I reconstructed white/black ACPL from the raw stored `game_positions.eval_cp` sequence of a real analyzed lichess game (id 296343) and reproduced lichess's own imported values `white_acpl=18`, `black_acpl=61` **to the exact rounded integer**. This nails the storage convention beyond doubt (see § Eval Semantics for the worked example).

**Primary recommendation:** Create `app/services/accuracy_acpl.py` with one pure function `compute_game_accuracy_acpl(positions, *, start_color="white") -> AccuracyAcplResult | None` that takes the ply-ordered `game_positions` rows, applies the post-move-shift inverse + White-POV→mover-POV sign flip + the D-08..D-11 formulas, and returns `None` when the per-ply eval sequence has an interior hole. Call it (a) inside `app/services/eval_apply.py::_classify_and_fill_oracle` (reusing the `positions` list it already loads) so it commits atomically with the completion markers, and (b) from `scripts/backfill_accuracy_acpl.py` (clone of `scripts/backfill_full_evals.py`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Formula port (win%, per-move acc, windowed aggregation, ACPL) | Pure Python service (`app/services/`) | — | No I/O; unit-testable in isolation like `eval_utils.py` |
| Live write of canonical columns | Backend service (`eval_apply.py` write session) | Database | Must commit atomically with `full_evals_completed_at` stamp |
| Bulk historical fill | Backfill script (`scripts/`) | Database | Operator-run, batched, `--db` targeted |
| Column repurposing + data preservation | Alembic migration | Database | One-shot DDL + `UPDATE` copy |
| Correctness validation | Validation script + pytest fixtures | Database | Compare computed vs `*_imported` |

## Eval Semantics — Sign, Post-Move Shift, Mover Parity (RESOLVED EMPIRICALLY)

This is the correctness core of the phase. All three facts below were verified against real dev-DB data, not inferred.

### The three facts

1. **Sign convention: `eval_cp` / `eval_mate` are White-POV.** Positive = White ahead. `[VERIFIED: app/services/eval_utils.py:44-66 + flaws_service.py:222-230 _pov_cp_or_zero negates for a black mover]`. To get mover-POV: `eval_pov = eval_cp if mover=="white" else -eval_cp`.

2. **Post-move shift (storage convention Y): row `ply=P` stores the eval of the position AFTER the move played from P, i.e. the eval of position `P+1`.** So `eval_of_position[Q] = row(Q-1).eval` for `Q >= 1`, and position 0 (initial) has no stored eval. This is exactly what `app/services/eval_apply.py:2024 _eval_of_position_map` encodes: `{ply + 1: eval for ply, eval in rows}` `[VERIFIED: eval_apply.py:2044 + flaws_service.py:358-361]`. Uniform across lichess `%eval` and engine games since SEED-044.

3. **Mover parity: the move played FROM ply `P` is White iff `P` is even, Black iff `P` is odd.** (Ply 0 → White's move 1; ply 1 → Black's move 1.) Equivalently, in `flaws_service._run_all_moves_pass` the move *arriving at* list index `n` is `white if n % 2 == 0 else black` — but note that indexes the *arrival* ply; for a compute keyed on the *departure* ply (which is what you need for before/after), White departs from even plies. `[VERIFIED: flaws_service.py:378-379 + empirical reproduction below]`.

### before / after mapping for the move played from ply P

```
before_cp = eval_of_position[P]     # = row(P-1).eval_cp   (or the 15cp seed when P == 0)
after_cp  = eval_of_position[P+1]   # = row(P).eval_cp
mover     = "white" if P % 2 == 0 else "black"
# mover-POV:
before_pov = before_cp if mover=="white" else -before_cp
after_pov  = after_cp  if mover=="white" else -after_cp
```

### Worked example — game 296343 (lichess, 25 plies, imported `white_acpl=18` `black_acpl=61`)

Stored `eval_cp` by ply (White-POV, post-move-shifted): `[18,25,0,11,-21,-25,-26,-28,-18,0,0,0,0,-3,209,44,63,62,58,55,88,88,519,557]` for plies 0..24; ply 25 (terminal) is `NULL`.

Apply D-11 (`per_move_loss = max(0, before_pov - after_pov)`, seed position 0 = 15cp):

- White moves depart from even plies 0,2,…,24 (13 moves). Losses: `0,25,32,1,0,0,0,3,165,1,3,0,0` → sum **230**, mean 230/13 = **17.7 → 18** ✅ (== imported `white_acpl`).
- Black moves depart from odd plies 1,3,…,23 (12 moves). Losses (mover-POV, so `max(0, after_cp - before_cp)`): `7,11,0,0,18,0,0,212,19,0,33,431` → sum **731**, mean 731/12 = **60.9 → 61** ✅ (== imported `black_acpl`).

This single reproduction validates sign + shift + parity + ACPL formula simultaneously. `[VERIFIED: dev DB game 296343, this session]`

### Terminal / checkmate handling

- **Terminal position (ply = ply_count)** has no outgoing move → its row carries `NULL` eval. It is *not* a hole. `[VERIFIED: game 296343 row 25 = NULL; game_position.py:141 move_san None on final]`
- **Checkmating final move:** the mating move's *after*-eval (the game-over position) is legitimately `NULL` at row `ply_count-1`. Verified on game 690201 (checkmate, ply_count=63): `Rd4#` at row 62 has `NULL/NULL`; the prior ply's `eval_mate=1`. This mirrors the existing `ends_game` handling (`eval_apply.py:135-138`, `_GAME_ENDING_PLY_OFFSET`). For accuracy/ACPL, the delivered mate is 100% / loss 0, so the game-ending move may be treated as `after = ±1000` (mate by sign) or simply skipped — both give the same aggregate to <0.5%. `[VERIFIED: dev DB game 690201]`
- **Mate evals use `eval_mate` (also post-move shifted).** D-08: map to `±1000` by sign before the sigmoid. Follow `flaws_service.py:207-209` (`MATE_CP_EQUIVALENT = 1000`), which already does exactly this for the drop math. Never route mate through the plain `eval_cp` path.

### Practical note on list-index vs ply

`positions` is loaded `ORDER BY ply` and normally contiguous (ply 0..N), but the compute MUST key by explicit `.ply` (build `eval_of_position: dict[int, tuple[cp, mate]]` via the `{ply+1: ...}` inverse), **not** by Python list index — a defensive habit that also survives the rare game with a missing row.

## Live-Hook Seam (RESOLVED)

**Fire the compute inside `app/services/eval_apply.py::_classify_and_fill_oracle`** (eval_apply.py:825), extending the existing oracle-count `UPDATE games ...` at eval_apply.py:1069-1080 to also set the four canonical accuracy/acpl columns.

Why this is the right seam:
- `_classify_and_fill_oracle` is called by `apply_full_eval` (eval_apply.py:2375), which is the **single shared write-session body** for BOTH the server-pool drain (`eval_drain.py::_full_drain_tick`:1041) AND the remote-worker atomic-submit path (`eval_remote.py`). One insertion covers every completion route. `[VERIFIED: eval_apply.py:2322-2373]`
- It already loads `positions` (ply-ordered, incl. ply 0 + terminal) at eval_apply.py:921-929 — **reuse that list, zero extra query.**
- It already performs the atomic `UPDATE games` for oracle counts in the same `write_session` transaction as the `full_evals_completed_at` / `full_pv_completed_at` stamps (T-117-11). Adding four columns to that `.values()` guarantees accuracy/acpl commit atomically with completion — never a torn write.
- It already applies the coverage gate (`if "reason" in flaw_result: return` at :950) so `GameNotAnalyzed` games write nothing. Accuracy/ACPL should additionally short-circuit on the stricter hole-free gate (below).

**Completeness at the seam:** `_classify_and_fill_oracle` runs only after `_apply_full_eval_results` wrote this pass's evals in the same session, so `positions` reloaded here reflects the just-written evals. However `apply_completion_decision` can still stamp complete *with residual holes* (Path C / `MAX_EVAL_ATTEMPTS`, ~0.5% of analyzed games — see § Complete-Sequence Gate). Therefore **do not assume completeness from the stamp**; the compute function must run its own hole-free gate and return `None` (leave the four columns NULL) when the sequence is incomplete. This is why the windowed accuracy aggregation (D-10) cannot be trusted on a holed game and why NULL is correct there.

**Do NOT add a second hook at lichess import** (`normalization.py:477-486` sets the *imported* platform values; `import_service.py:902` sets `lichess_evals_at`). Post-174-06 every lichess game later flows through the drain's full MultiPV-2 pass → `apply_full_eval` → `_classify_and_fill_oracle`, so the single seam already covers lichess games; the imported values are preserved separately in `*_imported`. A lichess game between import and its full-pass completion simply has `NULL` canonical accuracy/acpl until the drain reaches it — acceptable (D-05: nothing displays them).

`start_color` is always `"white"` for real games (standard chess). Pass `game.user_color` is NOT needed — accuracy/ACPL are computed per *board color* (white/black), and the mapping to the user happens later (out of scope, D-05).

## Complete-Sequence Gate

**Definition of "complete / hole-free":** every position from which a move is played (ply 0 .. ply_count-1) must have a resolvable eval, EXCEPT the game-ending move when the final position is checkmate/stalemate (that after-eval is legitimately NULL).

Because `before(move P) = eval_of_position[P] = row(P-1).eval` and `after(move P) = row(P).eval`, a hole in the compute is: **any `row(P).eval_cp IS NULL AND row(P).eval_mate IS NULL` for `P` in `0 .. ply_count-2`** (these rows are the *after* of a non-final move and the *before* of the next move). The row at `ply_count-1` is allowed NULL iff the final board is game-over.

**Recommended implementation — gate in Python, not SQL.** The compute function replays nothing; it just walks `positions`. As it builds `eval_of_position`, if any required interior before/after is missing it returns `None`. This is authoritative and mirrors `flaws_service._compute_eval_coverage` / SEED-049 `ends_game`. `[VERIFIED: eval_apply.py:260-271, flaws_service.py:291-312]`

**Coarse SQL candidate filter for the backfill** (cheap pre-selection, not authoritative): select games where `white_blunders IS NOT NULL` (the `is_analyzed` sentinel — analyzed games have near-complete evals by construction). The Python gate then rejects the ~0.5% with residual interior holes. Empirically: of 3000 sampled analyzed games, **2985 hole-free, 15 (0.5%) with interior holes** `[VERIFIED: dev DB, this session]`. Do NOT gate the backfill on `full_evals_completed_at IS NOT NULL` alone — that misses nothing but includes Path-C holed games, which the Python gate correctly leaves NULL.

## Migration Mechanics (D-03)

Follow the add-nullable-column + `op.execute` data-copy pattern from `alembic/versions/20260521_015028_..._add_evals_completed_at_to_games.py` (the canonical example: `op.add_column` + `op.execute("UPDATE ...")`). `[VERIFIED: that file, upgrade() lines 41-62]`

**`upgrade()` steps (single migration):**
1. `op.add_column("games", sa.Column("white_accuracy_imported", REAL, nullable=True))` — and `black_accuracy_imported`. Import `from sqlalchemy.dialects.postgresql import REAL` (matches `game.py:15,163`).
2. `op.add_column("games", sa.Column("white_acpl_imported", sa.SmallInteger, nullable=True))` — and `black_acpl_imported` (matches `game.py:168` type).
3. Copy existing values in: `op.execute("UPDATE games SET white_accuracy_imported = white_accuracy, black_accuracy_imported = black_accuracy, white_acpl_imported = white_acpl, black_acpl_imported = black_acpl")`.
4. NULL the canonical columns: `op.execute("UPDATE games SET white_accuracy = NULL, black_accuracy = NULL, white_acpl = NULL, black_acpl = NULL")`.
   - Combine steps 3+4 into one `UPDATE` for a single table pass if desired (large table: ~718k prod rows — see Pitfall 3 on batching).
5. Update model `game.py:162-169` comments to reflect the new semantics (canonical = uniform computed; `_imported` = platform-reported). Add the four `*_imported` `mapped_column`s.

**`downgrade()`:** copy `*_imported` back into the canonical columns, then `op.drop_column` the four `_imported` columns. (Lossy note: the downgrade restores platform values but loses any computed values written after upgrade — acceptable, standard.)

**D-04 guardrail:** the migration must NOT reference `inaccuracies`/`mistakes`/`blunders` at all. `white_blunders IS NOT NULL` remains the untouched `is_analyzed` sentinel read across `library_repository`/`library_service`.

**Provenance correction for the planner (IMPORTANT — supersedes CONTEXT D-02's note):** CONTEXT/SEED say `*_accuracy` is "chess.com only" and `*_acpl` is "lichess only". **The live DB disproves the accuracy claim.** Actual provenance `[VERIFIED: dev DB counts + normalization.py:477-486]`:

| Column | chess.com games | lichess games | self/flawchess |
|--------|-----------------|---------------|----------------|
| `white_accuracy` | chess.com formula (75,192) | **lichess formula (4,565)** | none |
| `white_acpl` | none (0) | lichess (4,565) | none |

So after the migration `*_accuracy_imported` holds **mixed-provenance** accuracy (chess.com's formula for chess.com games, lichess's formula for lichess games). This is a **bonus validation surface**: for lichess games, `*_accuracy_imported` was computed by lichess with the *same formula we are porting*, so our computed accuracy should track it as closely as ACPL does — use it as a second correctness signal in the validation script (D-07), alongside the primary `*_acpl_imported` signal. `*_acpl_imported` remains lichess-only and sparse.

## Formula Port (D-08..D-11)

All four formulas are cleanly implementable in stdlib `math`. Recommended module `app/services/accuracy_acpl.py`, importing `LICHESS_K` from `eval_utils.py` (do not re-declare the constant — CLAUDE.md "no magic numbers"; single source of truth).

### Win% (D-08)
```python
CP_CEILING = 1000  # lichess Cp.CEILING
def win_pct(cp: int) -> float:
    c = max(-CP_CEILING, min(CP_CEILING, cp))
    wc = 2.0 / (1.0 + math.exp(-LICHESS_K * c)) - 1.0   # winningChances in [-1, 1]
    return 50.0 + 50.0 * max(-1.0, min(1.0, wc))         # [0, 100]
# mate -> cp: sign(mate) * CP_CEILING, then win_pct(that)
```
Note: `win_pct(cp) == 100 * eval_cp_to_expected_score(cp, "white")` algebraically (both collapse to `100/(1+exp(-K*cp))`), but the D-08 path adds the ±1000 ceiling BEFORE the sigmoid — the existing `eval_cp_to_expected_score` does NOT clamp, so **write the dedicated clamped `win_pct` rather than reusing it.**

### Per-move accuracy (D-09)
```python
ACC_A, ACC_B, ACC_C = 103.1668100711649, -0.04354415386753951, -3.166924740191411
def move_accuracy(before_win: float, after_win: float) -> float:
    if after_win >= before_win:
        return 100.0
    raw = ACC_A * math.exp(ACC_B * (before_win - after_win)) + ACC_C + 1.0  # trailing +1 is real
    return max(0.0, min(100.0, raw))
```
`before_win`/`after_win` are Win% from the **mover's POV** (invert cp sign for Black before calling `win_pct`).

### Game-level windowed aggregation (D-10) — the only tricky part
- Build `win_pcts = [win_pct(15)] + [win_pct(mover_pov_cp) for each played ply]`? **No** — lichess builds the win% sequence in *White* POV over all positions, then computes each move's accuracy from the mover-POV pair. Concretely: `win_seq[i]` = Win% of position `i` (White POV, seeded with 15cp at position 0). For move from ply P (mover M), `before = win_seq[P]` mapped to M's POV, `after = win_seq[P+1]` mapped to M's POV. Mapping White-POV Win% `w` to Black POV = `100 - w`.
- `n_moves = len(win_seq) - 1`; `window_size = max(2, min(8, n_moves // 10))`.
- Windows = sliding windows of `win_seq` of length `window_size`, **left-padded with `window_size - 2` copies of the first window** so move `i` gets weight from window `i`.
- `weight_i = max(0.5, min(12.0, pop_stddev(window_i)))` where `pop_stddev` is the **population** standard deviation of the raw (White-POV) Win% values in the window.
- Per color: collect that color's `(accuracy_i, weight_i)` pairs; `game_acc = (weighted_mean(acc, w) + harmonic_mean(acc)) / 2`.
- `harmonic_mean(xs) = len(xs) / sum(1/x for x in xs)` — **guard against a zero accuracy** (a 0% move makes `1/x` blow up). Lichess's Scala `Maths.harmonicMean` operates on the accuracy list; a literal 0.0 accuracy yields harmonic mean 0. Reproduce lichess's behavior (a single 0 collapses harmonic mean toward 0); clamp `x` to a tiny epsilon only if a div-by-zero is otherwise unavoidable, and unit-test the zero-accuracy case.

**Numerical edge-case checklist:**
1. Clamp order: ceil cp to ±1000 → sigmoid → clamp winningChances to ±1 → scale (D-08). Do NOT clamp after scaling to [0,100] instead of at the winningChances stage.
2. `window_size // 10` uses integer floor division on `n_moves` (number of *moves*, not plies+1). For a 25-move game `25//10 = 2` → clamped to 2.
3. Padding count `window_size - 2` can be 0 (when window_size==2) — then no left padding. Handle `window_size - 2 <= 0` as "no pad".
4. Harmonic mean with an empty per-color list (0 moves for that color, e.g. a 1-ply game) → return `None` for that color.
5. `pop_stddev` of a constant window = 0 → clamped up to 0.5 (min weight). Good.

### ACPL (D-11)
```python
def acpl_for_color(losses: list[int]) -> int | None:
    if not losses:
        return None
    return round(sum(losses) / len(losses))
# loss per mover-move: max(0, before_pov_cp - after_pov_cp), with each cp clamped to ±1000 first
```
Plain arithmetic mean, rounded to `SmallInteger`. Clamp each cp to ±1000 before differencing (D-11 "evals capped ±1000"); mate → ±1000 by sign.

### Fixture for unit tests (D-07)
- **Portable hand-checked fixture:** embed game 296343's eval sequence (above) with expected `white_acpl=18`, `black_acpl=61` — already reproduced this session, so it is a known-good ACPL fixture independent of the DB.
- **Accuracy fixture:** fetch one specific lichess game with published accuracy (e.g. any rated game via `https://lichess.org/game/export/{id}?evals=true&accuracy=true` — the JSON `players.white.analysis.accuracy` field), embed its `%eval` sequence + published accuracy, assert the windowed compute matches within ±1 (lichess rounds). Game 296343's imported `white_accuracy=84`/`black_accuracy=61` (lichess-computed) can also serve as an in-repo integration assertion once the windowed path is implemented. `[VERIFIED: normalization.py stores lichess's own accuracy]`

## Backfill Script Convention

Clone `scripts/backfill_full_evals.py` structure verbatim `[VERIFIED: that file]`:
- Argparse `--db {dev,benchmark,prod}` (required), `--user-id` (make it **optional** here — the backfill should support all-users, unlike the enqueue script; default None = all analyzed users), `--dry-run`, `--limit`.
- `db_url_for_target(db)` + `create_async_engine(url, pool_pre_ping=True)` + `async_sessionmaker(expire_on_commit=False)`.
- Import `Game`, `GamePosition`, `User`, `OAuthAccount` (the last two so `select(Game...)` compiles — NoReferencedTableError otherwise, see backfill_full_evals.py:59-63).
- Batch commits (`ENQUEUE_GAMES_PER_BATCH = 100` analog); timestamped `_log()`.
- **Unlike the enqueue script, this backfill does the compute+write directly** (it does not enqueue a drain job): for each candidate game, load its `positions` (ply-ordered), call `compute_game_accuracy_acpl(positions)`, and `UPDATE games SET white_accuracy=..., ... WHERE id=...` — reusing the exact same pure function the live hook uses (single-path guarantee, D-06/SEED-110 §4). Sequential per session (no `asyncio.gather` on one session — CLAUDE.md).
- Candidate query: `select(Game.id, Game.user_id).where(Game.white_blunders.isnot(None))` (optionally `AND Game.white_accuracy.is_(None)` for resumability), ordered by id, `--limit` applied.
- `--db prod` requires `bin/prod_db_tunnel.sh` (localhost:15432) per CLAUDE.md.

## Validation Script (D-07)

A read-mostly comparison script (can live in `scripts/` as `validate_accuracy_acpl.py`, or be a pytest that runs against dev):
- **Primary signal — ACPL vs lichess:** for lichess games (`white_acpl_imported IS NOT NULL`), compare computed `white_acpl`/`black_acpl` against `*_acpl_imported`. Expect near-exact match (±1-2 from rounding). Report mean/median/p95 absolute delta and the count exceeding a small tolerance.
- **Secondary signal — accuracy vs lichess:** for lichess games (`white_accuracy_imported IS NOT NULL AND lichess_evals_at IS NOT NULL`), compare computed accuracy vs `*_accuracy_imported` (lichess's own, same formula) — expect close tracking (±1-3).
- **Divergent-by-design:** chess.com `*_accuracy_imported` uses chess.com's formula — expect a *systematic* offset, so report it separately and do NOT treat divergence as a failure.
- Output a summary table; flag any lichess game whose ACPL delta > tolerance for manual inspection (likely a holed/mate edge case).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| White-POV → mover-POV sign flip | New sign logic | Mirror `flaws_service._pov_cp_or_zero` (:222) | Already the audited convention |
| Post-move-shift inverse | Ad-hoc `ply-1` indexing | The `{ply+1: eval}` map shape (`_eval_of_position_map`, :2024) | Single audited off-by-one site (SEED-044) |
| Win% sigmoid constant | Re-typing `0.00368208` | `from app.services.eval_utils import LICHESS_K` | No magic numbers; single source |
| Mate → cp for drop math | `eval_mate_to_expected_score` (hard 0/1) | `MATE_CP_EQUIVALENT`-style ±1000 mapping (flaws_service.py:207) | D-08 requires ±1000 pre-sigmoid, not hard 0/1 |
| Loading positions in the hook | New query | Reuse `positions` already loaded in `_classify_and_fill_oracle` (:921) | Zero extra round-trip, guaranteed same txn |
| Add-column + data-copy migration | Novel DDL | Clone `20260521_..._add_evals_completed_at` pattern | Proven; matches project convention |
| Backfill scaffolding | New script shape | Clone `scripts/backfill_full_evals.py` | `--db`/batching/import-bootstrap already correct |

## Common Pitfalls

### Pitfall 1: Treating the post-move shift as pre-move (off-by-one)
**What goes wrong:** using `row(P).eval` as the *before* of move P (convention X) instead of the *after*. **Detection:** convention X gives white_acpl ≈ 0.8 for game 296343 vs the correct 18. **Avoid:** always `before = eval_of_position[P] = row(P-1).eval`, verified by the 296343 reproduction. Unit-test that fixture.

### Pitfall 2: Missing the 15cp seed for move 1's before-eval
**What goes wrong:** move 1 (White) departs from ply 0, whose *before* is the initial position — never stored. **Avoid:** seed `eval_of_position[0] = (15, None)`. The ACPL denominator INCLUDES move 1 (confirmed: 230/13=18, not 230/12=19).

### Pitfall 3: Forgetting the trailing `+1` and the ±1000 ceiling
**Avoid:** D-09's `+1` "uncertainty bonus" and D-08's cp ceil-BEFORE-sigmoid are both easy to drop and both shift results by 1-3 points. Keep them; assert against the lichess-accuracy fixture.

### Pitfall 4: Large-table migration `UPDATE` on ~718k prod rows
**What goes wrong:** a single unbatched `UPDATE games SET ...` over 718k rows on prod holds one long transaction / bloats WAL (see CLAUDE.md prod OOM/WAL history). **Avoid:** the migration's copy+NULL is a full-table rewrite regardless; keep it a single statement (Postgres handles it, and `max_wal_size=8GB` is set), but be aware the migration runs automatically on backend startup via `deploy/entrypoint.sh` — flag for the operator that this migration touches every games row. Batching in the migration is optional; the *backfill* (separate operator step, D-06) is the batched one.

### Pitfall 5: Harmonic-mean division by zero on a 0% move
**Avoid:** a move accuracy of exactly 0.0 makes `1/x` undefined. Reproduce lichess semantics and unit-test; clamp with an epsilon only as a last resort.

### Pitfall 6: Assuming `stamp_complete` ⇒ hole-free
**Avoid:** Path C stamps complete with residual holes (~0.5%). The compute's own hole-free gate is authoritative; return `None` → leave columns NULL.

## Edge Cases

| Case | Behavior |
|------|----------|
| 0-move game (ply_count 0) | Only terminal position; no moves → return `None` (all four NULL). 78 such games exist, 6 "analyzed". `[VERIFIED: dev DB]` |
| 1-move game | White has 1 move (before=15 seed, after=row0.eval); Black has 0 → `black_accuracy`/`black_acpl` = NULL, white values computed. |
| Interior hole (~0.5%) | Return `None` (leave all four NULL). |
| Checkmate final move | After-eval NULL is legitimate; treat delivered mate as 100%/loss 0 or skip the move. |
| Mate evals mid-game | Use `eval_mate` → ±1000 by sign (D-08); never the `eval_cp` path (it's NULL when mate is set). |
| self/flawchess games | Currently unanalyzed (0 accuracy/acpl); when analyzed via drain they flow through the same seam. |

## Runtime State Inventory

Not a rename/refactor phase — but it repurposes column *semantics* in place, so the migration's data-copy is the relevant "state" action:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `games.white_accuracy/black_accuracy/white_acpl/black_acpl` (mixed platform provenance) | Migration copies to `*_imported` then NULLs canonical (D-03) |
| Live service config | None | — |
| OS-registered state | None | — |
| Secrets/env vars | None | — |
| Build artifacts | None | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (async, per-run cloned DB) — see `tests/conftest.py` |
| Config file | `pyproject.toml` (pytest addopts) |
| Quick run command | `uv run pytest tests/services/test_accuracy_acpl.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| ACPL formula (D-11) reproduces 296343 (18/61) | unit | `uv run pytest tests/services/test_accuracy_acpl.py::test_acpl_fixture -x` | ❌ Wave 0 |
| Win%/per-move accuracy (D-08/D-09) incl. +1 & ceiling | unit | `... ::test_win_pct_and_move_accuracy -x` | ❌ Wave 0 |
| Windowed game accuracy (D-10) matches a lichess-published game | unit | `... ::test_game_accuracy_fixture -x` | ❌ Wave 0 |
| Hole-free gate returns None on interior hole | unit | `... ::test_incomplete_sequence_returns_none -x` | ❌ Wave 0 |
| 0/1-move + checkmate edge cases | unit | `... ::test_edge_cases -x` | ❌ Wave 0 |
| Live hook writes canonical cols atomically | integration | `uv run pytest tests/services/test_full_eval_drain.py -k accuracy -x` | ❌ Wave 0 (extend existing) |
| Migration copies then NULLs; `_imported` preserved | migration/integration | `uv run pytest -k migration_178 -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/services/test_accuracy_acpl.py -x`
- **Per wave merge:** `uv run pytest -n auto` + `uv run ty check app/ tests/`
- **Phase gate:** full suite green + `uv run ruff format/check` + `ty check` before verify.

### Wave 0 Gaps
- [ ] `tests/services/test_accuracy_acpl.py` — pure-formula + gate + edge cases (embed 296343 sequence)
- [ ] Extend `tests/services/test_full_eval_drain.py` — assert the four canonical columns after a drain tick
- [ ] Migration test — assert `*_imported` == old canonical and canonical NULLed post-upgrade

## Security Domain

Backend-only, no external/untrusted input surface (input is already-stored engine/lichess evals; no new API/user input, D-05).

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | no | No new external input; evals are internal SMALLINTs |
| V6 Cryptography | no | — |
| Others | no | Pure compute + parameterized SQLAlchemy writes |

Standard controls already met: all DB writes go through SQLAlchemy Core/ORM (parameterized); migration uses bound `op.execute` with no interpolated user data.

## Package Legitimacy Audit

**No external packages installed by this phase.** Compute uses stdlib `math` + existing `app.services.eval_utils.LICHESS_K`. Migration uses existing `alembic`/`sqlalchemy`. Backfill uses existing `app.core` bootstrap. Audit not applicable.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (dev) | migration + backfill verify | ✓ | 18 (Docker) | — |
| uv / pytest | tests | ✓ | per repo | — |
| prod SSH tunnel | prod backfill (operator step) | n/a this phase | — | — |

## State of the Art

| Old (SEED-110 original) | Current (CONTEXT) | Impact |
|--------------------------|-------------------|--------|
| Four new `*_computed` columns, canonical untouched | Repurpose canonical + `*_imported` (D-01/D-02) | Avoids a future "swap app to `_computed`" migration |
| "accuracy = chess.com only" | **DB shows lichess games also carry accuracy** | `*_accuracy_imported` is a second validation surface for lichess |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Lichess builds the win% sequence in White-POV then maps per-move to mover-POV (vs building directly in mover-POV) — both give identical per-move accuracy; the population-stddev *weights* are computed on White-POV win% (symmetric, so POV-invariant for stddev). | Formula Port D-10 | Weight values could differ if lichess used mover-POV win% per window; low risk (stddev is invariant to the `100-w` flip within a window only if the window is single-color, which it is NOT — windows mix colors). **Planner: confirm against `AccuracyPercent.scala` that weights use the raw White-POV win% sequence (they do in lichess source).** |
| A2 | Harmonic mean of accuracies treats a literal 0.0 per lichess `Maths.harmonicMean` | Formula Port D-10, Pitfall 5 | A zero-accuracy game's accuracy could be off; covered by a unit test |
| A3 | The lichess-accuracy fixture game will match the windowed compute within ±1 | Fixture D-07 | If off, indicates a D-10 detail (padding/window) to reconcile against source; the fixture IS the reconciliation mechanism |

## Open Questions (RESOLVED)

1. **Weight-window POV (A1).** — RESOLVED (empirically, not by independent source confirmation).
   - Known: ACPL sign/shift/parity are proven; per-move accuracy formula is locked.
   - Was unclear: whether population-stddev window weights are computed on White-POV or mover-POV win% values (matters because windows span both colors).
   - Resolution: encode weights on the single raw White-POV `winPercents` list (weights from that list, per-move accuracies via per-color POV mapping of the same list). This is **pinned by the accuracy fixture, not by an independent read of `AccuracyPercent.scala`** — the compute is required to reproduce lichess's published 84/61 within ±1 (`test_game_accuracy_fixture`). If the fixture drifts, the D-10 padding/window/POV detail is the thing to reconcile; the ±1 reconciliation gate is the source of truth, not a claimed source confirmation.

2. **`user_id` scoping of `game_positions` reads in the backfill.** — RESOLVED. `game_positions` PK is `(user_id, game_id, ply)`. Plan 04's backfill selects the candidate's `user_id` alongside `id` and filters on `(user_id, game_id)` (see § Backfill), so reads are correctly scoped; the live hook already has `game.user_id`. Just don't query by `game_id` alone.

## Sources

### Primary (HIGH confidence)
- `app/models/game.py:162-175` — column types (`REAL`, `SmallInteger`) + provenance comments.
- `app/models/game_position.py:159-161` — `eval_cp`/`eval_mate` SMALLINT, nullable, "eval AFTER move" note.
- `app/services/eval_apply.py:161-350` (`_collect_full_ply_targets`, `_post_move_eval`, `_resolve_full_eval`), `:825-1130` (`_classify_and_fill_oracle`), `:2024-2044` (`_eval_of_position_map`), `:2286-2451` (`apply_full_eval`) — seam, shift, oracle-UPDATE pattern.
- `app/services/eval_utils.py:38-97` — `LICHESS_K`, White-POV sign convention, mate handling.
- `app/services/flaws_service.py:197-390` — mover-POV conversion, mate→±1000, post-move eval-AFTER classifier loop.
- `app/services/normalization.py:477-486` — lichess import stores platform accuracy+acpl+counts (provenance ground truth).
- `scripts/backfill_full_evals.py` — backfill scaffolding convention.
- `alembic/versions/20260521_015028_..._add_evals_completed_at_to_games.py` — add-column + data-copy migration pattern.
- **Dev DB reproduction (this session):** games 296343 (ACPL 18/61 exact match), 690201 (checkmate terminal), aggregate hole/provenance counts.
- `.planning/seeds/SEED-110-...md` — locked lichess formulas + source citations (`eval.scala`, `AccuracyPercent.scala`, lila PR #11148).

### Secondary (MEDIUM confidence)
- Memory `project_atomic_eval_submit_incremental_lease`, `project_eval_completion_columns` — post-move shift + completion-column semantics (corroborated empirically here).

## Metadata

**Confidence breakdown:**
- Eval semantics (sign/shift/parity/ACPL): HIGH — reproduced to exact imported integer.
- Live-hook seam: HIGH — single shared write-body traced through both drain + remote paths.
- Migration mechanics: HIGH — direct clone of an existing proven pattern.
- Windowed accuracy aggregation (D-10): MEDIUM — formula locked, but one POV detail (A1) to confirm against Scala source + fixture during planning.

**Research date:** 2026-07-18
**Valid until:** ~2026-08-17 (stable internal codebase; re-verify seam line numbers if `eval_apply.py` is refactored)
</content>
</invoke>
