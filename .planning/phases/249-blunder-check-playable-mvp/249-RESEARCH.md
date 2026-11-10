# Phase 249: Blunder-Check Playable MVP - Research

**Researched:** 2026-11-10
**Domain:** Train mode extension: per-session window selection from per-ply evals + precomputed Maia stats, server-graded drill API with a secret answer key, new beta-only React drill UI
**Confidence:** HIGH for code paths, conventions and the selection approach (dev-DB timing measured); MEDIUM for prod latency of the heaviest user (extrapolated, needs one read-only prod probe); MEDIUM for UI reuse effort (component coupling read, not prototyped)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Entry point and audience (owner, 2026-11-10)
- **D-01: Beta-only Train tab.** A 4th tab "Blunder check" on `/train` (beside Today, Leaderboard, Archive), visible
  and reachable only for users with `beta_enabled`. A non-beta user hitting the route or the API gets the normal
  not-found/forbidden behaviour. Start screen with a Start button. No guests in the MVP (guests cannot be beta).
- **D-02: Session size 6 windows**, a named constant (`BLUNDER_CHECK_SESSION_WINDOWS = 6`). Phase 250 turns it into a
  per-mode setting. A session is not tied to the Train schedule, streak or reminders in this phase, and does not
  touch the personalized-puzzle session tables' semantics (see D-14).

#### Selection (SEED decisions + Phase 248 calibration, owner 2026-11-10)
- **D-03: Hazard model.** Per window draw the length L uniform over `WINDOW_LENGTHS` = 3..5 user moves and fire the
  blunder at each user move with `HAZARD` = 0.265; the first firing is the blunder position; none within L = herring.
  Then pick a blunder that fits the drawn position, never the other way round (a uniform position leaks, and position
  1 would be over-represented: about a third of misses follow the user's own mistake and only fit position 1).
- **D-04: Good bar.** Every judged user move before the blunder, and every herring move, has an expected-score drop
  below `INACCURACY_DROP` (the flaw pipeline's threshold). Mistakes never count as safe. The lead-in is not checked.
- **D-05: Eval band** [0.10, 0.90] on the pre-move expected score (user's point of view) for every judged user move,
  in blunder windows and herrings. Named constants.
- **D-06: Findability (face-palm test v2), by case** (miss classification from the seed and 248 D-13):
  - allowed (`is_miss` false): `maia_refutation_prob >= R` or `maia_refutation_rank = 1`, R = 0.3;
  - pure miss (`is_miss` and `ES_played >= ES_ref - INACCURACY_DROP`): `maia_best_prob >= X'` or
    `maia_best_rank = 1`, X' = 0.2;
  - mixed (`is_miss` and `ES_played < ES_ref - INACCURACY_DROP`): passes if either test passes.
  No played-probability cap, no top-move-safety rule (face-palm v1 dropped). NULL Maia values do not qualify.
- **D-07: Missed punishments are included with no session cap** (owner, 2026-11-10; replaces `MAX_MISS_SHARE` = 0.30).
  Calibration: pure misses are 19-23% of the usable supply at every rating, so a 30% cap would rarely bind. Keep the
  cap out of the code; reintroduce only if telemetry shows miss windows dominating. Missed-punishment windows use the
  same "Blunder" label, and the window includes the opponent's blunder (as the last lead-in ply when the miss is the
  first judged move).
- **D-08: No low-rating capture/check/mate rule** (owner, 2026-11-10): selection rests on findability alone.
- **D-09: Supply order.** Own games first (user-side blunders and Good moves of the user's own fully evaluated
  games). When the user's unserved own supply cannot fill the drawn window shape, fall back to windows from other
  FlawChess users' games, matched on the mover's rating at game time (band is a named constant; Claude's discretion
  on the value). Own vs foreign is recorded per window. Copy never says "your move" on a foreign game (herring-pool
  precedent).
- **D-10: No repeats in the MVP.** A blunder or herring window already served to the user is not served again, except:
  a blunder window that ended on a false alarm before the blunder was reached returns to the pool as unseen (herring
  false alarms are simply dropped). Re-serving missed blunders is Phase 250's spaced repetition.
- **D-11: Session composition** is whatever the hazard model draws per window (about 30% herrings), no forced mix.

#### Drill interaction and scoring (SEED decisions, owner 2026-11-09)
- **D-12: Flow per window.** Replay `LEAD_IN_PLIES` = 3 plies (opponent, user, opponent) at a fixed pace (whatever
  exists near the game start), stop on the first judged user move: the move is shown as an arrow with the piece still
  on its source square, prompt "Safe / Blunder". The answer is asked before the move is played and before the
  opponent's reply appears.
  - Correct "safe": +1 point (`SAFE_POINTS`), small animation and sound (reuse Train's point badges and sounds), play
    the user's move and the opponent's reply, show the next arrow.
  - Correct "blunder": +3 (`BLUNDER_POINTS`), then "find the better move" for +2 (`BETTER_MOVE_POINTS`), graded like
    personalized puzzle training. Then the solution screen.
  - False alarm (flagging a safe move): the window ends.
  - Missed blunder (answering "safe" on the blunder): the window's accumulated safe points are forfeited, shown being
    discarded with a small animation and the 0-points feedback sound; then the solution screen.
  - Herring completed: no extra payoff beyond the per-move points.
- **D-13: Timer** 15 s per judged user move (`MOVE_TIMER_SECONDS`). Timeout on a safe move loses that point and
  forfeits all safe points accumulated in the window (same animation and sound); the window continues and the
  blunder can still be caught. Timeout on the blunder move counts as a missed blunder.
- **D-14: Solution screen.** Reuse the personalized-puzzle solution screen pieces: Best and Game cards, line and
  position exploration, game info, Analyze button (deep link to `/analysis`). Session end screen shows points and
  Score % for the session (Score % = points scored / points possible; possible per window = 1 per judged safe move
  plus `BLUNDER_POINTS` + `BETTER_MOVE_POINTS` when it holds a blunder, including the unreached blunder after a false
  alarm).
- **D-15: Persistence from day one.** Store sessions, served windows (game, plies, shape, case, own/foreign, answer
  key) and per-move answers with timing and outcome, so Phase 250 can compute leaderboards, reviews and the
  cross-mode cooldown from MVP data. Own tables (SMALLINT IntEnum + CHECK for high-volume enum columns, TEXT + CHECK
  for low-volume ones, FKs with `ondelete`), not new columns on the personalized-puzzle tables, unless research shows a
  clean shared-session design; the planner decides with the reasoning written down.
- **D-16: Answer key is server-side.** The client gets the window (positions, lead-in, the judged moves as arrows)
  but not which move is the blunder; answers are graded by the server so the key cannot be read from the payload.

### Claude's Discretion
- Selection mechanics (on-the-fly SQL per session vs a precomputed window pool like `herring_pool`), as long as a
  session starts fast (target well under 1 s server time) and D-03 holds.
- Rating band for the foreign-game fallback; preference for older games where cheap.
- Pacing of the lead-in replay and animation details, within the existing Train look and sound set.
- Exact API shape (one call per answer vs batched), within the D-16 constraint.
- Moving reusable pure functions from `scripts/blunder_check/metrics.py` into `app/services/` (the app must not
  import from `scripts/`); the calibration report then imports the app versions.

### Deferred Ideas (OUT OF SCOPE)
- Shared Train schedule and reminders, per-mode session size with 0 allowed, session streak across both modes.
- Spaced repetition of missed-blunder windows (4 days, re-drawn shape, unlabelled; fallback to the original window
  when a re-draw cannot fit).
- Cross-mode cooldown with personalized puzzles (`CROSS_MODE_COOLDOWN_DAYS`).
- Points and Score % leaderboards with medals and a minimum window count.
- Guests and non-beta launch; replacing the lichess warm-up puzzles with similarly rated users' flaws.
- A `MAX_MISS_SHARE` cap or the low-rating capture/check/mate rule, only if telemetry or the spot-check calls for it.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are registered; the coverage contract is CONTEXT decisions D-01..D-16.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Beta-only tab + API gate | Q5 (trainRoute/TrainSubnav), Pattern 7 (`current_beta_user` dependency), Pitfall 10 |
| D-02 | 6 windows/session constant | Pattern 3 (session row `window_count`), Pattern 1 |
| D-03 | Hazard draw then fit | Q1, Pattern 1 (`draw_window_shape`, `max_fit_position` assignment) |
| D-04 | Good bar | Q1 (`_run_all_moves_pass` severity None), Pitfall 1 |
| D-05 | Eval band | Q1 (`in_band`, pre-move ES = `all_moves[q][2]`) |
| D-06 | Findability by case | Q1 (SQL superset + Python `findable`), Pitfall 4 |
| D-07 | Misses, no cap | Q7 (do NOT port `MAX_MISS_SHARE`/`capped_blunder_supply`) |
| D-08 | No capture/check/mate rule | nothing to build |
| D-09 | Own first, foreign fallback by rating | Q6, Pattern 2 |
| D-10 | No repeats, false-alarm return | Pattern 3 (prompted-ply exclusion rule) |
| D-11 | No forced mix | Pattern 1 |
| D-12 | Flow, points, better move | Q3, Q4, Pattern 4/5 |
| D-13 | 15 s timer | Q4, Pattern 6 |
| D-14 | Solution + end screen, Score % | Q5, Pattern 3 (`points_possible` frozen at composition) |
| D-15 | Persistence for Phase 250 | Q2, Pattern 3 |
| D-16 | Server-side key | Q4, Pitfall 2/3 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend layering: routers (HTTP only) -> services (logic) -> repositories (all SQL). `APIRouter(prefix=..., tags=...)` with relative paths.
- SQLAlchemy 2.x async `select()` API; never `asyncio.gather` on one `AsyncSession` (sequential awaits only).
- DB rules: FKs mandatory with explicit `ondelete`; unique constraints for natural keys; no native PG ENUM; high-volume enum columns = SMALLINT + Python `IntEnum` + `CHECK (col IN (...))`; low-volume = TEXT + CHECK; smallest sufficient int type.
- `Literal[...]` for fixed value sets in Pydantic schemas and service/repository signatures; `Sequence[...]` for params receiving `list[Literal]`; explicit return types; ty zero errors (`uv run ty check app/ tests/ scripts/`); suppress only with `# ty: ignore[rule]` + reason.
- No magic numbers: every threshold/count is a named constant.
- Nesting depth <= 4 (gated by `scripts/check_function_size.py app/ --fail-over-depth 4`; eslint `max-depth` 4 on frontend). Soft: ~100 logic lines/function, cognitive complexity <= 15.
- Sentry: `capture_exception` in non-trivial `except` blocks in services/routers; no variables in error messages (use `set_context`/`set_tag`).
- Time-dependent endpoints take `now_utc` from `dev_now_utc` (`app/core/dev_clock.py`), never `datetime.now()` inline.
- `board.board_fen()` for position comparison; exact positions rebuilt from `games.pgn`. API responses never expose internal hashes.
- PGN parsing wrapped per game in try/except.
- Frontend (frontend/CLAUDE.md): theme colors in `theme.ts`; `noUncheckedIndexedAccess`; knip (no dead exports); `text-sm` minimum; mobile parity; `Button` variants (primary `default`, secondary `brand-outline`); `isError` branch on every query; Umami via typed `trackFeature` registry only, user-initiated handlers only, enumerated literals only, **never duplicate DB-known facts**, URL-routed tabs need no event; `data-testid` on every interactive element, board container `data-testid="chessboard"` + `id="chessboard"`, drag-drop and click-click moves.
- `npm run lint`/`npm test` do not type-check: run `npm run build` too.
- Pre-merge gate (ruff format/check, ty x2, function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip) before squash-merge; CHANGELOG `[Unreleased]` bullet on merge.
- GSD scope discipline: nothing outside D-01..D-16; flag rather than add.
- Memory-derived rules that apply: beta flag from `useUserProfile().data.beta_enabled` (never `useAuth().user`); herring pool is cross-user so ownership-gate "your move" copy; plans must not gate on `bin/reset_db.sh`; every non-guest `Game` inserted in tests needs `finally` cleanup (tier-3 lottery isolation); asyncpg JSONB `None` writes `null::jsonb` (omit the column for SQL NULL); run `npm run build` before integrating shared-type changes.

## Summary

The right selection design is **on-the-fly, game-first, per session start**: pick ~40 random unserved fully evaluated games of the user in SQL, load their `game_positions` evals and user-side blunder rows (two indexed `IN` queries), run the flaw classifier's own `_run_all_moves_pass` in Python, and derive every judgement (Good, band, case, findability, maximum window position each blunder fits, herring runs) with the exact pure functions the Phase 248 report used. Measured on the dev DB (read-only): 200-400 ms total for 40 games across the four heaviest dev users (random pick 18-190 ms, positions+flaws load 80-130 ms, Python 45-75 ms), yielding 4-39 fitting blunders at position 1 and 200-440 L=3 herring runs per batch, i.e. far more than a 6-window session needs. A precomputed pool would need hooks into every eval-apply and Maia-scoring write path plus a multi-million-row prod backfill, and would have to be rebuilt each time the owner retunes R, X' or the band after the spot-check; the on-the-fly path makes retuning free. Per-ply ES cannot be done safely in pure SQL (the mate ladder in `_classify_mate_ladder` decides severity on mate transitions), so the SQL layer only narrows candidates and Python owns every judgement.

Persist **own tables**: `blunder_check_sessions` (TEXT status, one open session per user via a partial unique index), `blunder_check_windows` (frozen shape, case, own/foreign, blunder ply as the secret key, frozen `points_possible`, outcome, points) and `blunder_check_answers` (one pre-inserted row per prompt with server `prompted_at`, claimed by an `UPDATE ... WHERE answered_at IS NULL`). Sharing `drill_sessions` is not clean: its `expires_on` and `session_date` are schedule-bound NOT NULL columns and `uq_drill_sessions_user_open` would make an open puzzle session block a blunder-check session. The API must reveal the window **incrementally**: start FEN + lead-in + first arrow, then one POST per answer that returns the opponent's reply and the next arrow only after grading. Sending the whole window at once would leak the punishing reply and the window length, and sending `game_id` before the window ends leaks the key through the public `GET /library/games/{game_id}` flaw card.

The better-move step should reuse the personalized-puzzle grading contract exactly: after the server confirms "Blunder", it returns the key (`game_positions.best_move` at the blunder ply) plus `server_graded_moves` derived from `missed_pv_lines[0]`, the in-browser `useTrainGradingEngine` grades off-key moves, and the server resolves the tier with the existing `_resolve_grade`-style precedence (server-graded move wins, otherwise the client tier). The same move set is correct for all three cases (allowed, pure miss, mixed): any move within `INACCURACY_DROP` of the key's expected score. Points are server-authoritative so Phase 250's leaderboards can aggregate SQL rows without a frontend/backend parity test.

**Primary recommendation:** Build `app/services/blunder_check_rules.py` (ported pure functions), `app/services/blunder_check_selection.py` (game-first composer with own-then-foreign batches), `app/repositories/blunder_check_repository.py`, `app/routers/blunder_check.py` (prefix `/blunder-check`, beta-gated dependency), three new tables in one migration, and a self-contained frontend drill (`BlunderCheckTab` + a pure reducer for the drill state machine) that reuses `ChessBoard`, `sounds.ts`, `useTrainGradingEngine`, `useTrainRevealTree`, `TrainLineChips`, `TrainMoveTreeList` and `buildTrainPuzzleAnalysisUrl`, but not `TrainSolveScreen`/`TrainReveal` wholesale.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Window selection (hazard draw, Good/band/case/findability/fit) | API / Backend (service, Python) | Database (candidate narrowing, indexed loads) | Mate-ladder severity and ES live in Python (`_run_all_moves_pass`); SQL only narrows |
| Answer key (which ply is the blunder), points, forfeits | API / Backend | Database (persisted key + outcomes) | D-16; Phase 250 leaderboards aggregate server rows |
| Better-move grading | API / Backend (key, vetted set, final tier) | Browser (Stockfish WASM grades off-key moves) | Same contract as personalized puzzles; no server Stockfish at request time |
| Move timer | Browser (countdown, timeout submit) | API / Backend (server `prompted_at`, ceiling check) | UX needs a local clock; server records timing for Phase 250 |
| Lead-in replay, arrow prompt, animations, sounds | Browser | — | Pure presentation from server-sent UCI moves |
| Beta gate | API / Backend (dependency) | Browser (tab + route hidden) | D-01 requires the API to refuse too; library precedent of frontend-only gating is not enough |
| Persistence of sessions/windows/answers | Database | API / Backend (repository) | D-15 |

## Standard Stack

### Core (all already in the repo; nothing to install)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI / SQLAlchemy 2 async / Alembic / asyncpg | per CLAUDE.md (FastAPI 0.141.x) | Router, repository, migration | Project stack [VERIFIED: CLAUDE.md] |
| python-chess | 1.11.x | PGN replay for full FEN + UCI moves (`replay_at_ply` pattern) | Project stack; `train_pool.replay_at_ply` is the single Train replay [VERIFIED: app/services/train_pool.py:1507-1541] |
| React 19 + react-chessboard 5 + chess.js + TanStack Query | per CLAUDE.md | Drill UI, board arrows, client move application | Project stack |
| Stockfish WASM via `useTrainGradingEngine` | vendored | Better-move off-key grading | Existing Train grading engine [VERIFIED: frontend/src/hooks/useTrainGradingEngine.ts:1-50,185-249] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| On-the-fly game-first selection | Precomputed per-user window table refreshed on eval apply | Hooks into ~5 write paths + Maia post-commit scorer + prod backfill of millions of rows; stale on every constant retune. Only worth it if the prod probe shows > ~600 ms for the heaviest beta user |
| Own tables | Reuse `drill_sessions`/`drill_solves` | Schedule-bound NOT NULL columns, one-open-session index collision, SR-specific `source`/`guess` semantics (see Q2) |
| Phone grading for off-key better moves | Server Stockfish search at answer time | Prod CPU is shared with the eval drain; adds latency; not how personalized puzzles grade |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase. **Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** none.

## Answers to the Orchestrator's Questions (with evidence)

### Q1. Selection mechanics: on-the-fly SQL vs precomputed pool

**How the Phase 248 sampler derived per-ply ES and Good correctly.** It loads every `game_positions` row of a game ordered by ply (`eval_cp`, `eval_mate`, `move_san`), skips games whose plies are not contiguous from 0, and calls the classifier's own `_run_all_moves_pass(positions)` [VERIFIED: scripts/blunder_check/sample.py:425-448, 540-543, 570-578]. That function returns `{ply_N: (mover_color, severity|None, es_before, es_after)}`, with `ES_before = _ply_to_es(positions[N-1], mover)` and `ES_after = _ply_to_es(positions[N], mover)`, and documents that the post-move convention "is uniform across ALL sources: lichess `%eval` rows (zobrist.py) and the engine full-eval path (eval_apply._post_move_eval) both store it" [VERIFIED: app/services/flaws_service.py:378-411]. Severity on any transition touching a mate eval comes from `_classify_mate_ladder`, otherwise from `classify_severity(es_before - es_after)` [VERIFIED: flaws_service.py:400-410]. The metrics then read:
- Good = `entry[1] is None` (inaccuracies excluded), pre-move ES = `entry[2]` [VERIFIED: scripts/blunder_check/metrics.py `user_move_judgements`];
- `blunder_es`: `es_before = all_moves[p][2]`, `es_played = all_moves[p][3]`, `es_ref = 1.0 - all_moves[p-1][2]` [VERIFIED: metrics.py `blunder_es`];
- the calibration control matched stored `game_flaws` severities on 191633 of 191741 plies (99.9%) [CITED: reports/blunder-check/blunder-check-calibration-2026-11-10.md "Control"].

The two-convention trap (lichess post-move vs entry-lane aligned) does not bite inside games with `full_evals_completed_at IS NOT NULL`: the full drain overwrites entry-lane rows, and the residual risk is caught by the control [CITED: 248-RESEARCH.md Q6]. So the selection gate must be `full_evals_completed_at IS NOT NULL` and must reuse `_run_all_moves_pass`, never a SQL re-derivation.

**Why not pure SQL:** `expected_score_sql` exists [VERIFIED: app/services/train_pool.py:206-239], but Good also requires severity None under the mate ladder (lichess `MateAdvice` port with `MATE_LADDER_DECIDED_CP`/`MATE_LADDER_LOPSIDED_CP` thresholds) [VERIFIED: flaws_service.py:57-80]. Porting that to SQL is a second implementation that can drift from the classifier, exactly what Phase 248 avoided.

**Measurement (dev DB, read-only connection with `default_transaction_read_only=on`, 2026-11-10).** Probe script: `/tmp/claude-1000/-home-aimfeld-Projects-Games-flawchess/cea00e22-1971-4027-b64d-d0a4983c1899/scratchpad/probe_select.py`. Pipeline: `SELECT id FROM games WHERE user_id=:u AND full_evals_completed_at IS NOT NULL AND platform IN ('chess.com','lichess') ORDER BY random() LIMIT 40`, then positions + severity-2 flaws for those ids, then `_run_all_moves_pass` + the metrics functions with R=0.3, X'=0.2, band [0.10, 0.90].

| user (dev) | games / fully evaluated | random pick | load positions+flaws | Python | fitting blunders at pos 1..5 | L=3 herring runs |
|---|---|---|---|---|---|---|
| 28 | 5295 / 2865 | 38 ms (19 warm) | 89 ms (2492 rows) | 72 ms | 39/31/21/15/11 | 233 |
| 14 | 22519 / 1038 | 99 ms | 88 ms | 73 ms | 18/14/12/10/10 | 272 |
| 7 | 67244 / 431 | 191 ms | 130 ms (3441 rows) | 50 ms | 11/10/9/9/8 | 437 |
| 13 | 6563 / 1595 | 63 ms | 117 ms | 45 ms | 4/4/4/2/2 | 313 |
| 28, 80 games | | 18 ms | 141 ms (5133 rows) | 71 ms | 86/60/45/34/30 | 463 |

[VERIFIED: dev DB probe this session]. A session needs on average 0.7 x 6 ≈ 4.2 blunders (hazard normalized weights 0.379/0.279/0.205/0.100/0.037 for positions 1-5 [CITED: calibration report "Window fit"]) and ≈ 1.8 herrings. User 13's low fit counts reflect dev Maia coverage (the Maia backfill is still running on dev; 5362 of 7071 dev lichess-eval user blunders have NULL `maia_refutation_prob` [VERIFIED: dev DB query this session]); prod coverage is >= 99% per Phase 248 D-11.

**Cost driver:** the random pick scans every game row of the user (bitmap heap scan of all 67k game rows for user 7: `read=29759` pages cold, ~180 ms warm [VERIFIED: dev EXPLAIN this session]). On prod the heaviest beta user's fully evaluated count is unknown here. Mitigation: a partial index `ON games (user_id) WHERE full_evals_completed_at IS NOT NULL` restricts the heap visits to evaluated games (helps users with many unevaluated games, like dev user 7); and a Wave 0 read-only prod probe (Open Question 1) decides whether anything else is needed.

**Comparison**

| | On-the-fly game-first (recommended) | Precomputed per-user window/candidate table |
|---|---|---|
| Session start | 200-400 ms dev (measured); prod TBD by probe | ~20-50 ms |
| Write paths to touch | none | local drain, remote atomic submit, tier-4 re-score, reclassify (`_classify_and_fill_oracle` 4-way diff), Maia post-commit scorer (refutation lands after flaws), backfill script |
| Prod backfill | none | all fully evaluated games (millions of rows), sharded run like Phase 247/248 |
| Constant retune (R, X', band, hazard) after spot-check / telemetry | free | rebuild or re-derive the table |
| Correctness risk | one implementation (`_run_all_moves_pass`) | a second materialized copy that can go stale vs `game_flaws` |
| Herring supply | free (same loaded games) | needs its own run table |

**Recommendation:** on-the-fly, game-first, Python judgements. Reasoning: meets the < 1 s target on dev with margin, zero new write paths, and constants stay tunable, which matters because the owner is reviewing the spot-check in parallel and D-07 explicitly anticipates telemetry-driven retuning.

### Q2. Existing Train stack: what to reuse, what is new

- **`drill_sessions`**: `status` TEXT + `CHECK status IN ('open', 'completed', 'expired')`, partial unique index `uq_drill_sessions_user_open` on `user_id WHERE status = 'open'`, NOT NULL `session_date` and `expires_on` computed from the Train schedule (`session_window`), `puzzle_count`, `requested_count`, `is_warmup`, `entered_at`; FK only to `users` with CASCADE so sessions survive game wipes [VERIFIED: app/models/drill_session.py:1-104].
- **`drill_items`**: per-(user, game, ply) SR ladder (`DrillStatus` ACTIVE=0/MASTERED=1/PARKED=2), FK to `games` only, never to `game_flaws`, because reclassification can delete flaw rows; grading-critical fields are live-joined, never snapshotted [VERIFIED: app/models/drill_item.py:1-95].
- **`drill_solves`**: pre-materialized one row per puzzle at composition (`solved_at NULL`), the solve endpoint is a claiming UPDATE; `game_id` FK `ON DELETE SET NULL` because a global pool means a stranger's game deletion must not punch holes in another user's session; `DrillSource` SR_ITEM=0/RED_HERRING=1/SHARP_FILLER=2, `DrillGuess`, `DrillMoveQuality` WRONG=0/INACCURACY=1/GOOD=2; JSONB telemetry with `none_as_null=True` [VERIFIED: app/models/drill_solve.py:1-217].
- **`herring_pool`**: global, identity-blind at serve time, surrogate BIGINT PK, composite FK `(game_id, user_id) -> games(id, user_id) ON DELETE SET NULL`, denormalized FEN so rows survive source deletion, no rating matching [VERIFIED: app/models/herring_pool.py:1-150; app/services/train_pool.py:1170-1300].
- **Composition concurrency**: inserts inside `session.begin_nested()`; an `IntegrityError` from the one-open-session index means a concurrent request won, and the loser resumes the winner's session [VERIFIED: app/repositories/train_repository.py:2456-2575].
- **Grading**: `_resolve_grade` precedence: (1) a played move the server grades itself (`server_graded_moves_for`) takes the server tier, (2) an accepted confirmed phone disagreement, (3) else the client's tier [VERIFIED: train_repository.py:3166-3290].
- **Scoring**: server mirror `MOVE_TIER_POINTS = {"good": 2, "inaccuracy": 1, "wrong": 0}`, `GUESS_POINTS = 1`, `TRAIN_POINTS_PER_PUZZLE = 3`, pinned to `trainScore.ts` by `tests/services/test_train_score_parity.py` [VERIFIED: app/services/train_score.py:24-32].

**Decision for D-15: own tables.** A shared session table is not clean: `drill_sessions.expires_on`/`session_date` are schedule-derived NOT NULL (D-02 says blunder check is not tied to the schedule), and `uq_drill_sessions_user_open` would forbid an open puzzle session and an open blunder-check session at once. Phase 250's cross-mode needs (streak across modes, shared schedule) are served by a UNION over both session tables, which needs no migration of MVP rows. Reuse the *patterns* (partial unique open index, SAVEPOINT + IntegrityError resume, pre-materialized rows + claiming UPDATE, SET NULL game FK for cross-user rows), the PGN replay (`replay_at_ply`), and the grading helpers (`server_graded_moves_for`, `vetted_moves_from_pv_node`, `_matching_server_graded_move`, `_resolve_grade` precedence).

**What Phase 250 needs from MVP rows (so no data migration later):**
- Leaderboards (Points, Score %): per-window `points_scored`, `points_possible`, `ended_at`, `user_id`, `is_own` (in case foreign windows are scored differently). An index on `ended_at` can be added in 250 (metadata-only).
- Spaced repetition of missed blunders: `(user_id, game_id, blunder_ply, outcome = MISSED, ended_at)` identifies the item; re-drawing needs only game + blunder ply.
- Cross-mode cooldown keyed on the flaw: own windows' `(user_id, game_id, blunder_ply, served_at)` vs `drill_solves (game_id, ply, solved_at)`.
- Timing analysis / abuse checks: per-answer `prompted_at`, `answered_at`, `client_elapsed_ms`.
- Review vs new: Phase 250 can add an `origin` column with a server default (metadata-only ALTER, no row migration).

### Q3. Better-move grading (D-12)

- Key for an SR puzzle = `game_positions.best_move` at the flaw ply (decision-keyed: best move FROM that row's position) [VERIFIED: train_pool.py `answer_key_for` docstring, lines 370-399; 248-RESEARCH Q1 proved `best_move` is decision-ply-keyed for both eval populations].
- Vetted alternatives = `vetted_moves_from_pv_node(missed_pv_lines[0], mover, best_uci=best_move)`: `[best, su]` when `su` is within the good band (`best_es - move_es < INACCURACY_DROP`, strict), a lone `[best]` for soft-shaped nodes, `[]` for sharp nodes; plus the sharp runner-up graded "wrong" [VERIFIED: train_pool.py:459-487, 489-579, 614-687].
- Off-key moves are graded by the browser engine: `startGrading(fen, keyUci)` searches the position after the key, `gradeMove` searches after the played move, `severity = classifyLiveSeverity(anchor.es, esAfter)`, `moveTier = moveTierFromSeverity(severity)` [VERIFIED: useTrainGradingEngine.ts:1-50]. The server overrides when the played move is one of its graded moves [VERIFIED: train_repository.py `_resolve_grade`].

**Which move set counts as correct, by case:** the same rule for all three. The position is the pre-blunder board at the blunder ply; the key is `best_move` there.
- Allowed blunder: the better move is anything that does not lose >= `INACCURACY_DROP` vs the key; often several moves (soft-shaped node). Phone grading is essential here because any quiet non-hanging move can be good.
- Pure miss: the key is the punishing move Maia's `maia_best_*` pair was tested on (Phase 247 scored `best_move`); other moves that keep the gift within the band are also good.
- Mixed: same.
Tier -> points: reuse `MOVE_TIER_POINTS` (good 2 / inaccuracy 1 / wrong 0); `BETTER_MOVE_POINTS = 2` equals the good tier, so D-14's possible points stay `BLUNDER_POINTS + BETTER_MOVE_POINTS` [ASSUMED: inaccuracy earning 1 of the 2 better-move points mirrors personalized puzzles; D-12 only says "+2 graded like personalized puzzle training"].
- The user's own played blunder is graded "wrong" without a search (it is a stored blunder) [ASSUMED: a cheap server shortcut; the phone would also grade it wrong].
- Required data: `best_move` at the blunder ply must be non-NULL for a blunder to be selectable (dev: 2 of 9981 engine-game user blunders lack it [VERIFIED: dev DB query this session]). The `missed_pv_lines` blob is optional (27% of dev engine-game user blunders still lack it because the blob backfill is pending [VERIFIED: dev DB query]); without it the vetted set is empty and the phone grades everything except the key, exactly like a no-blob personalized puzzle. Do not gate selection on the blob (would cut supply); see Open Question 3.

### Q4. Answer-key secrecy (D-16) and the timer

**What the client may receive before the window ends:** start FEN (full FEN at `lead_start = max(0, first_judged_ply - LEAD_IN_PLIES)`, from PGN replay), the lead-in UCI list, the board orientation (mover color), and the first judged move's UCI (the arrow). Nothing else.

**What must be withheld until the window ends:**
1. Any opponent reply after a judged move that has not been answered (the reply after the blunder is the punishment).
2. The window length L and the number of remaining prompts (in a blunder window the last prompt is the blunder).
3. `game_id`, ply numbers, game metadata, `is_own`: `GET /library/games/{game_id}` is "Intentionally NOT owner-scoped. Any authenticated user may inspect any game by url" and returns the GameFlawCard with flaws [VERIFIED: app/routers/library.py:129-155]. A `game_id` in the window payload is a key leak.
4. The case (allowed/miss/herring) and any Maia or eval value.

**Per-move flow (one call per answer).** Batching answers is impossible under D-16 because each prompt depends on the previous grade. Recommended endpoints (prefix `/blunder-check`):
- `GET /sessions/open` -> open session summary or null (start screen state).
- `POST /sessions` -> compose or resume (returns session id, window count, per-window status/points for progress, index of the current window).
- `POST /sessions/{sid}/windows/{position}/start` -> window payload above; inserts the answer row for prompt 1 with server `prompted_at`. Idempotent: if already started, returns the progress so far (answered moves with their replies) and the current open prompt, keeping its original `prompted_at`.
- `POST /sessions/{sid}/windows/{position}/answers` body `{move_index, answer: Literal["safe","blunder","timeout"], client_elapsed_ms}` -> `{result, points_awarded, points_forfeited, window_points, next: {reply_uci, move_uci} | null, ended, better_move: {fen, key_uci, server_graded_moves} | null}`.
- `POST /sessions/{sid}/windows/{position}/better-move` body `{played_uci, client_tier, phone_grade?}` -> `{tier, points_awarded, window_points}`.
- `GET /sessions/{sid}/windows/{position}/solution` -> 409 before the window ends; afterwards `game_id`, the blunder ply/UCI, refutation UCI (allowed/mixed: `COALESCE(best_move@ply+1, first token of pv@ply+1)` [CITED: 248-CONTEXT D-20]), missed best (`best_move@ply`), case, `is_own`, game info.

**Timer.** Client-authoritative countdown with a server ceiling:
- The server stamps `prompted_at` (from `dev_now_utc`) when it issues a prompt (window start or the previous answer's response).
- Client sends `timeout` when its 15 s countdown (started after the lead-in or move+reply animation finishes) expires, or the answer with its measured `client_elapsed_ms`.
- Server grades an answer as `timeout` when `server_elapsed > MOVE_TIMER_SECONDS + PROMPT_ANIMATION_ALLOWANCE + NETWORK_GRACE` (named constants, e.g. 15 + 3 + 2 s) [ASSUMED values]. Store both elapsed values. This is enough for beta and gives Phase 250 the data to tighten later; the existing Train leaderboard already trusts client-reported move tiers, so this is not a weaker trust level than shipped.

**Idempotency/concurrency:** the answer row is pre-inserted at prompt time; the answer is a claiming `UPDATE ... WHERE window_id=:w AND move_index=:i AND answered_at IS NULL RETURNING ...` (drill_solves precedent). A double submit gets 0 rows -> return the stored result (or 409).

### Q5. Frontend

- Tabs: `TrainTab = 'today' | 'leaderboard' | 'archive'`, `TRAIN_TAB_PATHS = { today: '/train', leaderboard: '/train/leaderboard', archive: '/train/archive' }`; `parseTrainRoute` returns null for unknown paths and `Train.tsx` redirects null to Today [VERIFIED: frontend/src/lib/trainRoute.ts:16-45; frontend/src/pages/Train.tsx]. Add `'blunder-check'` -> `/train/blunder-check`; `parseTrainRoute` needs the beta flag (or Train.tsx treats the blunder-check route as null for non-beta) so a non-beta user is redirected to Today (the existing not-found behaviour). `TrainSubnav` renders three fixed `TabsTrigger`s with `data-testid="tab-train-*"`; add a fourth behind a `showBlunderCheck` prop [VERIFIED: TrainSubnav.tsx]. No `tab-switch` Umami event (URL-routed, covered by pageview) [VERIFIED: TrainSubnav.tsx docstring; frontend/CLAUDE.md].
- Beta flag: `beta_enabled: boolean` is on the profile type [VERIFIED: frontend/src/types/users.ts:49]; read it from `useUserProfile().data` (Train.tsx already reads `profile` there). No frontend code uses `beta_enabled` today [VERIFIED: grep this session], so this is the first consumer.
- `Train.tsx` couples Today to `useTrainLoop({ isToday, canTrain })` and hides the subnav when `immersive`. The blunder-check drill needs its own immersive flag so the subnav/medal host hide during a window, and must not trip the Today latch (no Today session composition or grading Worker on a blunder-check-only visit).
- Reusable as-is: `ChessBoard` + `BoardArrow` (arrow prompt; piece stays on source since the move is not applied until answered), `playSound` with events `'score-full'`, `'score-partial'`, and `'game-loss'` (the 0-points sound TrainSolveScreen plays for a 0-point puzzle: `points === TRAIN_POINTS_PER_PUZZLE ? 'score-full' : points > 0 ? 'score-partial' : 'game-loss'`) [VERIFIED: frontend/src/lib/sounds.ts:63-75, 94-123; TrainSolveScreen.tsx:1572-1583], `useTrainGradingEngine` (imperative `startGrading(fen, keyUci)`/`gradeMove`) [VERIFIED: useTrainGradingEngine.ts:185-249], `useTrainRevealTree({ startFen, active, chips, ... })` (generic over a start FEN and chip lines) [VERIFIED: useTrainRevealTree.ts:90-255], `TrainLineChips`, `TrainMoveTreeList`, `buildTrainPuzzleAnalysisUrl(gameId, ply)` (`?ply=P-1` shows the pre-move board) [VERIFIED: analysisUrl.ts:111-123], `useWakeLock`, `useFitBoardToViewport`, `TrainScoreBadge` (ring + count-up for the session Score %).
- Not reusable wholesale: `TrainSolveScreen` (2036 lines, bound to `TrainPuzzle`, `UseTrainSessionResult`, guess/telemetry/tour/bot bubble) and `TrainReveal` (props require `TrainPuzzle` + `SolveResponse`); `TrainRevealGameFooter` takes `{ puzzle: TrainPuzzle, verdict: SolveResponse }` and fetches `useLibraryGame(puzzle.game_id)` [VERIFIED: TrainRevealGameFooter.tsx]. Either add a narrow prop variant (`gameId`, `isOwn`) or build a small `BlunderCheckGameFooter` on `useLibraryGame`. The per-puzzle points flash (`pointsFlash` + `TRAIN_POINTS_FLASH_COLORS`) lives inside TrainSolveScreen, not as a component; extracting a small `PointsFlash` component is the clean reuse path.
- New pieces: a pure `blunderCheckDrill.ts` reducer (states: lead-in replay -> prompt(timer) -> grading -> continue/forfeit animation -> better-move -> solution -> next window -> session end), a `useMoveTimer` hook (deadline-based, pauses during animations, fires timeout once), `useBlunderCheckSession` (TanStack mutations for the endpoints), the drill screen, the solution screen (Best/Game chips: Best = `key_uci` line from the grading engine, Game = played blunder followed by the refutation), and the session end screen (points + Score %).
- Telemetry: see Open Question 4 (Umami vs DB-known conflict).

### Q6. Foreign-game fallback (D-09)

The herring pool has no rating matching and is identity-blind [VERIFIED: train_pool.py:1170-1300 docstring], and the copy precedent is "Copy must still not say 'your move' for a stranger's game" (seed) and the herring reveal omits the game footer [VERIFIED: TrainRevealGameFooter.tsx comment]. So the rating match is new:
- Reference Elo of the user: median `pinned_elo_for_mover` over the user's own loaded/recent fully evaluated games (lichess-blitz scale, clamped to [600, 2600]) [VERIFIED: app/services/best_move_candidates.py:79-122]. Pinned Elo makes chess.com and lichess comparable.
- Foreign candidates: `TABLESAMPLE SYSTEM (p)` on `games`, filtered to other non-guest users, `full_evals_completed_at IS NOT NULL`, `platform IN ANALYTICS_INCLUDED_PLATFORMS`, and a raw-rating prefilter wider than the band; then the exact pinned-Elo band in Python. Measured 47 ms on dev at `SYSTEM (2)` [VERIFIED: dev EXPLAIN this session]. `FOREIGN_ELO_BAND = 100` pinned points [ASSUMED]; widen once (e.g. 200) before giving up.
- The mover is the game's owner (`games.user_color`); judged moves are the owner's moves, Maia values were computed at the owner's rating, so findability semantics are unchanged.
- Exclude guest-owned games (guest flaws are never Maia-scored [CITED: calibration report "How to read"]).
- Record `is_own` per window. The solution screen may show game info (deep links are public, owner 2026-11-09) but copy says "the player", not "you".

### Q7. What moves into `app/services/`

Port to a new pure module (suggested `app/services/blunder_check_rules.py`), then make `scripts/blunder_check/metrics.py` and `spot_check.py` import (and re-export) the app versions so `tests/scripts/test_blunder_check_metrics.py` keeps passing unchanged:
- Constants: `HAZARD: float = 0.265`, `WINDOW_LENGTHS: tuple[int, ...] = (3, 4, 5)`, `LEAD_IN_PLIES: int = 3`, `MAX_BLUNDER_POSITION: int = 5` [VERIFIED: scripts/blunder_check/metrics.py:36-42].
- `MoveJudgement`, `user_move_judgements`, `blunder_es`, `MissCase` + `miss_case`, `in_band`, `blunder_fits_position`, `hazard_position_weights` + `HazardWeights`, `FindabilityInputs`, `_pair_passes` + `findable`, `herring_flags`, `count_herring_windows` [VERIFIED: metrics.py].
- From spot_check: `WindowShape`, `draw_window_shape(rng)` [VERIFIED: scripts/blunder_check/spot_check.py `draw_window_shape`].
- New in app: `R`, `X'`, band constants (`REFUTATION_PROB_MIN = 0.3`, `BEST_PROB_MIN = 0.2`, `ES_BAND_LOW = 0.10`, `ES_BAND_HIGH = 0.90`), `max_fit_position(...)` (largest k with `blunder_fits_position` true; fit is monotone in k because position k checks a superset of the moves position k-1 checks), and herring-run extraction returning ply ranges.
- Stay in scripts (report-only): `MAX_MISS_SHARE`, `capped_blunder_supply`, `estimated_user_windows`, `weighted_fit_share`, `elo_bucket`/`ELO_BUCKETS`, `auc`, `quartiles`, `flaw_control`, `SupplyRates` (D-07 forbids a miss cap in app code).
- The app module imports `_MoveEntry`, `INACCURACY_DROP` from `flaws_service` (private import with the existing `# noqa: PLC2701` precedent) and `RANK_BASE` from `maia_flaw_stats` (`RANK_BASE: int = 1`) [VERIFIED: app/services/maia_flaw_stats.py:29].

### Q8. Pitfalls: see `## Common Pitfalls`.

### Q9. Validation: see `## Validation Architecture`.

## Architecture Patterns

### System Architecture Diagram

```
Browser (beta user, /train/blunder-check)
   |  POST /blunder-check/sessions (start/resume)
   v
Router (beta dependency: 403 for non-beta, 401 anon)
   v
Selection service --------------------------------------------------------------+
   | 1. draw 6 shapes: L ~ U{3,4,5}, hazard 0.265 per move -> blunder pos k or herring
   | 2. own batch: random unserved fully-evaluated own games (SQL, LIMIT 40)        |
   |      -> load game_positions (eval_cp, eval_mate, move_san) + user-side        |
   |         severity-2 game_flaws with Maia pairs (2 indexed IN queries)           |
   |      -> _run_all_moves_pass per game (Python, classifier's own ES/severity)    |
   |      -> per game: judgements, usable blunders (case, findable, band,          |
   |         max_fit_position), herring runs; drop served/prompted plies (D-10)     |
   | 3. assign shapes (highest k first), one game per session                       |
   | 4. unfilled shapes -> next own batch (bounded) -> foreign batch (TABLESAMPLE,  |
   |    pinned-Elo band) -> still unfilled: redraw shape (bounded) or short session |
   v                                                                                |
Repository: INSERT session + 6 windows (key = blunder ply, frozen points_possible)  |
   in SAVEPOINT; IntegrityError on one-open index -> resume winner                  |
   v
Browser: POST .../windows/{i}/start -> start FEN + lead-in UCIs + first arrow
   | (server inserts answer row 1 with prompted_at)
   v
Lead-in replay -> arrow prompt + 15 s timer -> POST .../answers {safe|blunder|timeout}
   v
Grader (server): compare move_index ply with secret blunder ply; points/forfeit;
   next prompt? -> return opponent reply + next arrow (insert next answer row)
   caught -> return better-move key + server_graded_moves
   v
Better move: browser Stockfish grades off-key -> POST .../better-move -> server tier
   v
Window end -> GET .../solution (game_id, lines, refutation) -> next window -> session end (points, Score %)
```

### Recommended Project Structure

```
app/
├── models/blunder_check.py               # BlunderCheckSession, BlunderCheckWindow, BlunderCheckAnswer + IntEnums
├── services/blunder_check_rules.py       # ported pure functions + constants (no DB)
├── services/blunder_check_selection.py   # game-first composer (calls repository loaders)
├── services/blunder_check_service.py     # grading/points/forfeit state machine (pure where possible)
├── repositories/blunder_check_repository.py  # all SQL (candidate games, loads, served sets, inserts, claiming updates)
├── routers/blunder_check.py              # prefix /blunder-check, thin
└── schemas/blunder_check.py              # Pydantic wire models with Literal fields
alembic/versions/<ts>_phase_249_blunder_check_tables.py
frontend/src/
├── lib/blunderCheckDrill.ts              # pure reducer / state machine (unit-tested)
├── lib/trainRoute.ts                     # + 'blunder-check'
├── hooks/useBlunderCheckSession.ts
├── hooks/useMoveTimer.ts
├── components/train/blunder-check/       # BlunderCheckTab, StartScreen, DrillScreen, SolutionScreen, EndScreen, PointsFlash
└── types/blunderCheck.ts
scripts/blunder_check/metrics.py, spot_check.py   # import + re-export app versions
```

### Pattern 1: Game-first composition (pure core, injectable RNG)

```python
# Source: ported from scripts/blunder_check/spot_check.py draw_window_shape + metrics.py
# (names other than the ported functions are proposals) [ASSUMED names]
def draw_window_shape(rng: random.Random) -> WindowShape:
    length = rng.choice(WINDOW_LENGTHS)          # (3, 4, 5)
    for position in range(1, length + 1):
        if rng.random() < HAZARD:                 # 0.265
            return WindowShape(length, position)
    return WindowShape(length, None)              # herring

def max_fit_position(preceding: Sequence[MoveJudgement], es_before: float | None) -> int:
    """Largest k in 1..MAX_BLUNDER_POSITION the blunder fits (0 = unusable). Monotone in k."""
    best = 0
    for k in range(1, MAX_BLUNDER_POSITION + 1):
        if not blunder_fits_position(preceding, es_before, k, ES_BAND_LOW, ES_BAND_HIGH):
            break
        best = k
    return best
```

Candidate rules per loaded own/foreign game (all from one `_run_all_moves_pass` result):
- Blunder candidate: stored `game_flaws.severity == 2`, user parity (`mover_is_white_at_ply(ply) == user_is_white`), recomputed `all_moves[ply][1] == "blunder"` (consistency guard), `case = miss_case(...)`, `findable(case, ...)` at R=0.3/X'=0.2, `in_band(es_before)`, `best_move` at ply non-NULL, ply not already prompted as a blunder for this user, `max_fit_position >= 1`.
- Herring candidate: L consecutive user moves with `herring_flags` true, none of whose plies were part of any previously served window of this user in that game.
- Assignment: blunder shapes in descending k first (rarest first), uniform random among candidates with `max_fit_position >= k`; then herrings; at most one window per game per session (spot-check precedent `used` set).
- Window plies for a blunder at ply p and position k: judged `p - 2(k-1), ..., p` (user moves every other ply); lead-in `max(0, first - 3) .. first - 1`.

SQL narrowing: `ORDER BY random()` over the user's evaluated games. Optional, cheap preference for older games (discretion item): weighted sampling `ORDER BY -ln(random()) / (1 + age_days / OLDER_GAME_WEIGHT_DAYS)` [ASSUMED; leave out if the owner prefers uniform].

### Pattern 2: Foreign batch

```sql
-- [ASSUMED shape; percent and band are named constants]
SELECT g.id FROM games g TABLESAMPLE SYSTEM (:pct)
JOIN users u ON u.id = g.user_id
WHERE g.user_id <> :user_id AND NOT u.is_guest
  AND g.full_evals_completed_at IS NOT NULL
  AND g.platform = ANY(:platforms)            -- ANALYTICS_INCLUDED_PLATFORMS
  AND (CASE WHEN g.user_color = 'white' THEN g.white_rating ELSE g.black_rating END)
      BETWEEN :raw_low AND :raw_high          -- wide prefilter; exact pinned band in Python
LIMIT :n
```

### Pattern 3: Persistence schema (one migration)

`blunder_check_sessions` (low volume):
- `id` INT PK; `user_id` FK users CASCADE; `status` TEXT CHECK `status IN ('open','completed')`; `window_count` SMALLINT; `started_at` TIMESTAMPTZ default now(); `completed_at` NULL.
- Partial unique index `uq_blunder_check_sessions_user_open (user_id) WHERE status = 'open'`.

`blunder_check_windows` (one row per served window; SMALLINT enums):
- `id` BIGINT PK; `session_id` FK CASCADE; `position` SMALLINT; UNIQUE (`session_id`, `position`).
- `user_id` FK users CASCADE (the solver; denormalized for per-user exclusion and Phase 250 aggregates).
- `game_id` FK games `ON DELETE SET NULL` (a foreign owner deleting a game must not delete rows from another user's history; drill_solves precedent); `is_own` BOOLEAN.
- `window_length` SMALLINT CHECK 3..5; `blunder_position` SMALLINT NULL CHECK 1..5 (NULL = herring); `first_ply` SMALLINT; `blunder_ply` SMALLINT NULL (the secret key; NULL iff herring, CHECK); `case` SMALLINT CHECK IN (0 herring, 1 allowed, 2 pure_miss, 3 mixed) backed by IntEnum; `mover_elo` SMALLINT (pinned).
- `points_possible` SMALLINT frozen at composition (`judged safe moves + (BLUNDER_POINTS + BETTER_MOVE_POINTS if blunder)`, D-14); `points_scored` SMALLINT default 0.
- `outcome` SMALLINT NULL CHECK IN (0 cleared, 1 caught, 2 missed, 3 false_alarm, 4 void); `better_move_uci` VARCHAR(5) NULL; `better_move_tier` SMALLINT NULL (reuse `DrillMoveQuality` values).
- `started_at`, `ended_at` TIMESTAMPTZ NULL.
- Optional self-sufficiency snapshot (`start_fen` TEXT, `move_ucis` TEXT) so a window survives source-game deletion mid-session [ASSUMED; alternative is marking the window `void` when its game is gone].
- Index `(user_id, game_id)` for the served-set lookup.

`blunder_check_answers` (highest volume; SMALLINT enums):
- PK (`window_id`, `move_index`); `window_id` FK CASCADE; `ply` SMALLINT.
- `answer` SMALLINT NULL CHECK IN (0 safe, 1 blunder, 2 timeout); `result` SMALLINT NULL CHECK IN (0 correct_safe, 1 false_alarm, 2 caught, 3 missed, 4 timeout_safe, 5 timeout_blunder).
- `points_awarded`, `points_forfeited` SMALLINT; `prompted_at` TIMESTAMPTZ NOT NULL; `answered_at` NULL; `client_elapsed_ms` INT NULL.

**D-10 exclusion from these rows (no extra state):**
- A blunder is "seen" iff an answer row exists at its `blunder_ply` (it was prompted). A false alarm before it leaves no row there, so it returns to the pool automatically.
- A herring candidate is excluded if any of its plies was a judged ply of any previously served window of this user in that game (window rows give `first_ply` + `window_length`/`blunder_position`, so the judged ply range is derivable).

### Pattern 4: Grading state machine (server, pure function)

```python
# [ASSUMED names]; constants from D-12/D-13
SAFE_POINTS = 1; BLUNDER_POINTS = 3; BETTER_MOVE_POINTS = 2; MOVE_TIMER_SECONDS = 15
def grade_answer(is_blunder_move: bool, answer: Literal["safe", "blunder", "timeout"],
                 window_safe_points: int) -> AnswerGrade:
    if is_blunder_move:
        if answer == "blunder":  # caught: keep safe points, +3, chain better move
            return AnswerGrade("caught", BLUNDER_POINTS, 0, ends=True, better_move=True)
        # "safe" or timeout on the blunder = missed: forfeit window safe points
        return AnswerGrade("missed" if answer == "safe" else "timeout_blunder",
                           0, window_safe_points, ends=True, better_move=False)
    if answer == "blunder":       # false alarm: window ends, safe points kept
        return AnswerGrade("false_alarm", 0, 0, ends=True, better_move=False)
    if answer == "timeout":       # lose this point + forfeit, window continues
        return AnswerGrade("timeout_safe", 0, window_safe_points, ends=False, better_move=False)
    return AnswerGrade("correct_safe", SAFE_POINTS, 0, ends=False, better_move=False)
```
A herring ends with `cleared` after the last judged move is answered safe (or timed out).

### Pattern 5: Better move resolve (reuse)

Build the graded set with `server_graded_moves_for(source=DrillSource.SR_ITEM, ply=blunder_ply, missed_pv_lines=..., best_move=..., ladder=None, herring_mover_color=None, key=answer_key_for(...))` and resolve: matching server-graded move -> server tier, else client tier (no recheck/disagreement path in the MVP). Return the key and `legal_server_graded_moves(...)` only in the "caught" response.

### Pattern 6: Timer

Client: `useMoveTimer(deadlineMs)` starts after the prompt is rendered (after lead-in/reply animation), fires `onTimeout` once, cancels on answer. Server: `server_elapsed = now_utc - prompted_at`; if it exceeds `MOVE_TIMER_SECONDS + PROMPT_ANIMATION_ALLOWANCE_S + NETWORK_GRACE_S`, record `timeout_*` regardless of the submitted answer.

### Pattern 7: Beta gate

```python
# [ASSUMED name] app/routers/blunder_check.py
async def current_beta_user(user: Annotated[User, Depends(current_active_user)]) -> User:
    if not user.beta_enabled:
        raise HTTPException(status_code=403, detail="Not available")
    return user
```
`users.beta_enabled` is a NOT NULL boolean defaulting false [VERIFIED: app/models/user.py:40-47]. No backend beta dependency exists today (library notes "Backend is NOT beta-gated" [VERIFIED: app/routers/library.py:281]); D-01 requires one here.

### Anti-Patterns to Avoid
- Re-deriving ES/severity in SQL or with a hand-written sigmoid (drifts from the classifier and the mate ladder).
- Picking a blunder first and deriving its position (D-03; position 1 over-represented).
- Shipping the whole window (all judged moves + replies) in one payload, or `game_id` before the window ends.
- Using `game_flaws.fen` (board_fen only) to build the board; always replay `games.pgn`.
- `asyncio.gather` over the same session for the batch loads.
- Porting `MAX_MISS_SHARE`/`capped_blunder_supply` into app code (D-07).
- Duplicating DB-known facts as Umami events (frontend/CLAUDE.md).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-ply ES and Good judgement | SQL window functions / own sigmoid | `flaws_service._run_all_moves_pass` + ported `user_move_judgements` | Mate ladder, identical to stored flaws (99.9% control) |
| Window fit / herring runs / findability | new logic | ported `blunder_fits_position`, `herring_flags`, `findable` | Calibrated and unit-tested in Phase 248 |
| Full FEN and move list | `game_flaws.fen` | `train_pool.replay_at_ply` pattern on `games.pgn` | board_fen lacks castling/ep/side to move |
| Elo normalization for foreign match | raw rating compare | `pinned_elo_for_mover` | cross-platform scale |
| Better-move grading | own ES drop logic | `server_graded_moves_for`, `vetted_moves_from_pv_node`, `useTrainGradingEngine`, `liveFlaw.classifyLiveSeverity` | CI-drift-checked thresholds |
| One open session under races | app-level locking | partial unique index + SAVEPOINT + IntegrityError resume | drill_sessions precedent |
| Ply parity | `ply % 2` inline | `mover_is_white_at_ply` / `is_opponent_expr` | single source (`_PLY_EVEN_MOVER_WHITE = 0`) [VERIFIED: query_utils.py:21,61-68] |

**Key insight:** every judgement the drill makes must be the same one the stored flaw pipeline and the calibration report make, otherwise "Safe" can be a stored mistake and the answer key becomes disputable.

## Common Pitfalls

### Pitfall 1: Eval ply conventions
**What goes wrong:** off-by-one ES, a Good move judged from the wrong row, or entry-lane values on hole rows. **How to avoid:** gate on `full_evals_completed_at IS NOT NULL`; load all plies from 0, skip games with gaps (`_is_contiguous` precedent); index `all_moves` by the flaw ply (`game_flaws.ply` = row of the pre-move position); require recomputed severity "blunder" at the stored blunder ply. **Warning signs:** a test fixture where the recomputed severity disagrees with the stored one.

### Pitfall 2: Key leak via `game_id`
`GET /library/games/{id}` is open to any logged-in user and returns flaws. Never put `game_id`, plies or game metadata in pre-end payloads. Test the exact response key sets (test_train precedent `test_pre_attempt_payload_shape`).

### Pitfall 3: Key leak via the reply or the length
Return the opponent's reply only in the response to the answer of the move it follows; never return remaining-prompt counts.

### Pitfall 4: NULL Maia and missing best_move
NULL pairs never pass (`_pair_passes` returns False) [VERIFIED: metrics.py]; also require `best_move` at the blunder ply for the better-move key. Go-forward games whose Maia scoring has not run yet only feed herrings, which is fine.

### Pitfall 5: Guest exclusion
Beta users are never guests, but the foreign fallback must join `users` and exclude `is_guest` (their flaws are never Maia-scored and their games get pruned).

### Pitfall 6: game_flaws stores both players' flaws
Filter user parity with `mover_is_white_at_ply`/`is_opponent_expr`; `game_flaws.user_id` is the game owner, not the mover [CITED: project memory "game_flaws covers both players"].

### Pitfall 7: Foreign game deleted mid-session
SET NULL on `game_id`; at start/answer time a window whose game is gone must be voided (or served from a snapshot), not 500.

### Pitfall 8: Concurrent starts and double submits
Two `POST /sessions` at once: partial unique index + SAVEPOINT resume. Double answer: claiming UPDATE with `answered_at IS NULL`. Test both like `test_concurrent_compose_yields_one_open_session`.

### Pitfall 9: Opening book moves as "Good"
Judged moves near the game start are often book moves; herrings there are easy. Not in the decisions; flag only (Open Question 5).

### Pitfall 10: Beta gating only in the frontend
D-01 requires 403 (or 404) from the API for non-beta users; test it.

### Pitfall 11: Test isolation
Tier-3 eval lottery is global: every non-guest `Game` inserted in tests needs `finally` cleanup and unique user ids [CITED: project memory "Eval lottery test isolation"]; inject the RNG so selection tests are deterministic; xdist per-worker DBs isolate only the DB.

### Pitfall 12: Dev clock
Timer elapsed must use `dev_now_utc` on both stamps; the offset header is stable across a session in dev, real clock elsewhere [VERIFIED: app/core/dev_clock.py:56-71].

### Pitfall 13: Points drift between client and server
Make the server authoritative for every number shown (points, forfeits, possible, Score %); the frontend displays server values, so no parity test is needed (train_score parity exists only because Train scores client-side).

## Code Examples

### Loading and judging a batch (from the dev probe, trimmed)
```python
# Source: probe_select.py (this session), mirrors scripts/blunder_check/sample.py
pos_rows = (await session.execute(
    select(GamePosition.game_id, GamePosition.ply, GamePosition.eval_cp,
           GamePosition.eval_mate, GamePosition.move_san)
    .where(GamePosition.game_id.in_(ids))
    .order_by(GamePosition.game_id, GamePosition.ply))).all()
# ... group per game, require plies 0..n-1 contiguous
all_moves = _run_all_moves_pass(positions)
judg = user_move_judgements(all_moves, [p.ply for p in positions if p.move_san], user_is_white)
es_before, es_played, es_ref = blunder_es(all_moves, flaw.ply)
case = miss_case(flaw.is_miss, es_ref, es_played)
```

### Score % for the end screen
```python
# D-14: possible is frozen per window at composition
score_pct = floor(100 * sum(w.points_scored) / sum(w.points_possible))  # floor like trainScore.ts
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Face-palm v1 (played-prob cap + top-move safety) | v2 findability by case (R=0.3, X'=0.2) | 248, owner 2026-11-10 | port `findable`, not the probe logic |
| `MAX_MISS_SHARE = 0.30` | no cap | D-07 | do not port |
| Frontend-only beta gating (library) | API dependency for blunder check | D-01 | new `current_beta_user` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Better move tiers reuse good=2/inaccuracy=1/wrong=0 | Q3 | Score % semantics shift slightly; owner may want all-or-nothing +2 |
| A2 | Off-key better moves graded by the browser engine (client tier trusted unless server-graded) | Q3/Q4 | If owner reads D-16 as "no client grading at all", a server Stockfish path is needed |
| A3 | Timer: client-authoritative with server ceiling 15 + 3 + 2 s | Q4 | Too tight/loose allowance on slow devices |
| A4 | `FOREIGN_ELO_BAND = 100` pinned Elo, widened once to 200 | Q6 | Thin foreign supply or poor rating match |
| A5 | Reference Elo = median pinned Elo of the user's recent evaluated games | Q6 | Odd results for users with mixed TCs |
| A6 | 403 for non-beta API calls | Pattern 7 | Owner may prefer 404 |
| A7 | Optional older-game weighting | Pattern 1 | Changes the served mix; can be left out |
| A8 | OWN_BATCH_GAMES = 40, MAX_OWN_BATCHES ~3 | Pattern 1 | latency vs fill rate |
| A9 | Window snapshot columns (start_fen, move_ucis) vs voiding | Pattern 3 | more storage vs voided windows |
| A10 | Herring end shows the final opponent reply and a short "all safe" solution | Q5 | UX detail |

## Open Questions

1. **Prod latency for the heaviest beta user.** Known: dev 200-400 ms per 40-game batch. Unclear: prod row counts and cache state. Recommendation: Wave 0 read-only probe via `flawchess-prod-db` MCP (orchestrator; subagents lack project MCP): `EXPLAIN (ANALYZE, BUFFERS)` of the random-pick query and of the positions load for 40 ids, for `user_id = 28` and the beta user with most fully evaluated games. If the pick exceeds ~300 ms, add the partial index `games (user_id) WHERE full_evals_completed_at IS NOT NULL` in the phase migration (recommended anyway; cheap).
2. **D-16 vs phone grading** (A2). The secret (which move is the blunder) stays server-side; the better-move key is revealed only after the user has committed "Blunder", as personalized puzzles already reveal their key pre-attempt. Confirm with the owner that this satisfies D-16.
3. **Blob coverage on prod.** `missed_pv_lines` provides the vetted alternatives; if prod coverage is low the better-move step relies more on the phone. Probe the share of usable user blunders with an empty/NULL blob; do not gate selection on it.
4. **Umami telemetry vs frontend/CLAUDE.md.** CONTEXT deliverable 5 asks Umami events for session start/finish, window outcome and abandon after a forfeit, but frontend/CLAUDE.md says "Track only what the browser knows and the database cannot ... train guesses ... must not be duplicated." With D-15 persistence, start/finish/outcomes are DB-known, and "abandon after forfeit" is derivable (session left open, last answer a forfeit, no later answer). Recommendation: derive these from the new tables (one SQL query or an admin-activity metric) and add Umami only for genuinely browser-only actions (e.g. an `action` on the solution screen's Analyze click if not already covered). Needs owner confirmation before the planner locks it.
5. **Opening book moves** as judged Good moves (Pitfall 9). Spot-check feedback may ask for a minimum judged ply; keep as a named constant default of no minimum only if the owner asks.
6. **Session resume semantics.** An open session persists until finished; a reload mid-prompt keeps the original `prompted_at` (likely a timeout). Confirm acceptable for beta.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev DB (Docker, :5432) | tests, probes | ✓ | 18 (per CLAUDE.md) | — |
| psql client | read-only probes | ✓ | /usr/bin/psql | uv + asyncpg |
| uv / Python 3.14 | backend | ✓ | — | — |
| Node/npm | frontend | ✓ (repo builds) | — | — |
| Maia at runtime | — | not needed (values precomputed) | — | — |
| Prod DB (read-only MCP, tunnel) | Open Question 1 probe | orchestrator only | — | defer probe to owner |

No blocking missing dependencies. The dev Maia backfill currently running lowers dev Maia coverage; tests use seeded fixtures, not dev data.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-asyncio, xdist) backend; vitest frontend |
| Config file | `pyproject.toml` / `tests/conftest.py` (per-worker cloned DBs); `frontend/vite.config.ts` test block |
| Quick run command | `uv run pytest tests/services/test_blunder_check_rules.py tests/routers/test_blunder_check.py -x` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm test -- --run )` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | non-beta 403, anon 401, beta 200; tab hidden + route redirects for non-beta | router + vitest | `uv run pytest tests/routers/test_blunder_check.py -k beta -x`; `npm test -- --run trainRoute TrainSubnav` | ❌ Wave 0 |
| D-02 | session holds exactly `BLUNDER_CHECK_SESSION_WINDOWS` windows with ample supply | integration | `-k session_size` | ❌ |
| D-03 | shape frequencies match hazard (seeded RNG, herring share ≈ 0.3011); blunder chosen only among `max_fit_position >= k` | unit | `tests/services/test_blunder_check_rules.py -k hazard` | ❌ |
| D-04 | a window never contains an inaccuracy/mistake as a judged safe move (fixture with an inaccuracy before the blunder -> position capped) | unit + integration | `-k good_bar` | ❌ |
| D-05 | out-of-band judged moves excluded (fixture ES 0.95) | unit | `-k band` | ❌ |
| D-06 | allowed/pure/mixed findability, NULL Maia excluded | unit (port existing tests) | `tests/scripts/test_blunder_check_metrics.py` stays green + new app tests | ✅ extend |
| D-07 | no miss cap in app (`MAX_MISS_SHARE` absent from app/) | grep test or unit | `-k no_miss_cap` | ❌ |
| D-09 | own first; foreign used only when own cannot fit; foreign within pinned band; guests excluded; `is_own` recorded | integration | `-k foreign` | ❌ |
| D-10 | served blunder never reselected; false-alarm-before-blunder returns it; herring plies never reused | integration (two sessions) | `-k no_repeat` | ❌ |
| D-12 | safe +1, caught +3 + better move, false alarm ends, missed forfeits | unit (pure grader) + router | `-k grade` | ❌ |
| D-13 | timeout on safe forfeits and continues; timeout on blunder = missed; server ceiling converts late answers | unit + router | `-k timeout` | ❌ |
| D-14 | `points_possible` frozen incl. unreached blunder after false alarm; Score % | unit + router | `-k score_pct` | ❌ |
| D-15 | tables, FKs (`games` SET NULL, users/session CASCADE), CHECKs, partial unique index | migration/schema | `uv run alembic upgrade head && uv run alembic check`; `tests/models/test_blunder_check_schema.py` | ❌ |
| D-16 | exact key sets of start/answer responses exclude game_id/ply/case/reply-ahead; solution 409 before end | router | `-k payload_shape` | ❌ |
| concurrency | concurrent start -> one open session; double answer -> one claim | router | `-k concurrent` | ❌ |
| Q7 | report imports app versions; calibration tests unchanged | unit | `uv run pytest tests/scripts/test_blunder_check_metrics.py tests/scripts/test_blunder_check_calibration.py` | ✅ |
| UI | drill reducer transitions (prompt -> forfeit -> continue; caught -> better move -> solution; false alarm -> end), timer fires once | vitest | `npm test -- --run blunderCheckDrill useMoveTimer` | ❌ |

### Sampling Rate
- **Per task commit:** the quick run command for the touched module.
- **Per wave merge:** `uv run pytest -n auto -x` + frontend `npm test -- --run`.
- **Phase gate:** full pre-merge gate (CLAUDE.md) green before `/gsd-verify-work`; browser UAT of the drill by the agent (memory: run human-action checkpoints yourself) with a beta-enabled dev user.

### Wave 0 Gaps
- [ ] `tests/fixtures` helper `seed_blunder_check_game(test_engine, user_id, pgn, evals_cp, flaws, ...)`: inserts a game with contiguous `game_positions` (hash columns required NOT NULL), `full_evals_completed_at`, `best_move` at blunder plies, and user-side severity-2 `game_flaws` with Maia pairs; `finally` cleanup; unique user ids (grep for collisions).
- [ ] Deterministic RNG injection point in the composer.
- [ ] Beta user fixture (register + flip `beta_enabled`).
- [ ] Prod probe (Open Question 1), orchestrator-run.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (existing FastAPI-Users) | `current_active_user` |
| V3 Session Management | no | existing JWT |
| V4 Access Control | yes | user id only from `current_active_user`; session/window lookups scoped by `user_id` (404 on foreign ids); beta dependency |
| V5 Input Validation | yes | Pydantic with `Literal["safe","blunder","timeout"]`, bounded ints (`move_index` 1..5, `position` 0..5, path ids <= 2^31-1 like `_SESSION_ID_MAX`), UCI regex `^[a-h][1-8][a-h][1-8][qrbn]?$` |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Answer key read from payload (game_id -> public flaw card, full window, reply-ahead) | Information disclosure | incremental reveal, key-set tests, solution gated on window end |
| IDOR on session/window ids | Elevation | scope every query by `user_id`; 404 |
| Replay/double submit to farm points | Tampering | pre-inserted answer row + claiming UPDATE |
| Timer abuse (stall, reload) | Tampering | server `prompted_at` ceiling; resume keeps original stamp |
| Non-beta access | Elevation | server dependency, not just hidden tab |
| Oversized ints reaching asyncpg | DoS (500 to Sentry) | FastAPI `Path`/`Query` bounds (train router precedent) |

## Sources

### Primary (HIGH confidence)
- Codebase files read this session: `app/services/flaws_service.py` (30-80, 180-240, 360-470, 923-935), `app/services/train_pool.py` (200-720, 1170-1300, 1378-1631), `app/models/drill_session.py`, `drill_item.py`, `drill_solve.py`, `herring_pool.py`, `app/repositories/train_repository.py` (2456-2590, 3160-3295), `app/routers/train.py`, `app/routers/library.py` (129-155), `app/services/train_score.py`, `app/services/best_move_candidates.py` (70-122), `app/repositories/query_utils.py`, `app/core/dev_clock.py`, `app/models/user.py`, `scripts/blunder_check/{metrics,sample,spot_check}.py`, frontend `Train.tsx`, `TrainSubnav.tsx`, `trainRoute.ts`, `sounds.ts`, `trainScore.ts`, `useTrainGradingEngine.ts`, `useTrainRevealTree.ts`, `TrainReveal.tsx`, `TrainRevealGameFooter.tsx`, `analysisUrl.ts`, `TrainSolveScreen.tsx` (imports, 1560-1600), `tests/conftest.py`, `tests/routers/test_train.py`.
- Dev DB read-only measurements (psql with `default_transaction_read_only=on`; Python probe with the read-only engine from `scripts/blunder_check/sample.py`).
- Phase 248 CONTEXT/RESEARCH, calibration report 2026-11-10, SEED-261108-dk0, 249-CONTEXT.

### Secondary (MEDIUM confidence)
- Prod latency extrapolated from dev scaling (Open Question 1).

### Tertiary (LOW confidence)
- None used for decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new packages; existing modules read)
- Selection architecture: HIGH on dev (measured), MEDIUM on prod latency
- Persistence/API: HIGH on precedents, MEDIUM on exact column set (planner's call)
- Frontend reuse: MEDIUM (coupling read, not prototyped)
- Pitfalls: HIGH

**Research date:** 2026-11-10
**Valid until:** 2026-12-10 (stable internals; re-check if Phase 248 constants change after the spot-check)

## Prod Latency Probe (orchestrator, 2026-11-10, read-only via prod MCP)

Heaviest beta user on prod: user 95, 40,218 fully evaluated chess.com/lichess games (the next four users are not beta).

| Step | Cold cache | Warm cache |
|---|---|---|
| Pick 40 random fully evaluated games (bitmap heap scan on `ix_games_user_played_at`, 28k heap blocks) | 371 ms | 121 ms |
| Load `game_positions` for the 40 games (3,481 rows, index scan on `ix_game_positions_game_id`) | n/a | ~100 ms (366 blocks read from disk) |

Pick + positions warm: 237 ms. With flaws (~same as positions) and the Python judgements (45-75 ms on dev), a session
start for the heaviest beta user lands around 350-450 ms warm and up to ~800 ms cold: inside the < 1 s target.
The game pick dominates on a cold cache because it touches every heap block of the user's games; the recommended
partial index `games (user_id, id) WHERE full_evals_completed_at IS NOT NULL` turns it into an index-only scan.
Planner's call whether to ship it in this phase (cheap, `CREATE INDEX` on ~1.1M games rows).
