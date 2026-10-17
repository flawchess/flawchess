# Codebase Cleanup Style Guide

Scope: naming and comment hygiene only. No architecture changes, no behavior changes, no new features.
A cleanup commit passes the full pre-merge gate **with no test assertion changed** (test code may change
only to follow a rename). Any diff line that is neither a comment nor a rename needs a justification.

Baseline (2026-10-16): ~11,400 planning-artifact tags (`Phase NNN`, `D-NN`, `SEED-NNN`) in `app/` +
`frontend/src`, ~3,500 more in `tests/`; ~550 TODO / legacy / deprecated / "no longer" markers.

---

## 1. Off-limits (never rename, flag instead)

Anything a type checker cannot see the other side of. Renaming these breaks something outside the repo
or outside the current deploy.

| Contract | Where | Why |
|---|---|---|
| DB tables, columns, indexes, constraint names | `app/models/`, raw SQL | needs a migration; not cleanup |
| Persisted enum values (`IntEnum` ints, `TEXT CHECK` strings) | models, schemas | stored in rows |
| Alembic migrations (code AND comments) | `alembic/versions/` | historical record |
| Remote-worker protocol: endpoint paths, JSON fields | `app/routers/eval_remote.py`, `app/schemas/eval_remote.py`, `scripts/remote_eval_worker.py` | workers in the fleet run older code |
| Public API paths and JSON field names | `app/routers/`, `app/schemas/` ↔ `frontend/src/api`, `frontend/src/types` | separate planned change if worth it |
| Generated files | `frontend/src/generated/*` | edit the source registry, re-run `scripts/gen_*.py` |
| Sentry messages, tags, context keys | `sentry_sdk.*`, `Sentry.*` | issue grouping and dashboard continuity |
| Umami event names and props | `trackEvent(...)` | analytics history |
| `localStorage` / `sessionStorage` keys, cookie names | frontend | users lose saved state |
| URL paths and query params | routes, `?type=` etc. | shared links |
| `data-testid` values | frontend | tests and UAT tooling |
| Env vars, config keys | `app/core/config.py`, `.env*` | deploy config |
| LLM prompt text (strings, not comments) | `app/services/insights_llm.py` | changes model output |
| Out of tree | `CHANGELOG.md`, `.planning/`, `fixtures/`, `stories/`, `analysis/`, `scripts/archive/` | history, data, or separate projects |

Internal names that *happen to match* a contract (a Python attribute mirroring a JSON field) may be
renamed only if the wire name is pinned explicitly (Pydantic `serialization_alias`, explicit mapping).
Default: don't.

---

## 2. Comments

### 2.1 Planning-artifact tags

Tags: `Phase NNN`, `D-NN`, `SEED-NNN`, `CR-NN`, `WR-NN`, `FE-IN-NN`, `SC2`, `RESEARCH Pitfall N`,
quick-task IDs (`261016-fwd`), `REQ-IDs`. They point into `.planning/`, which readers of the code
don't have open, and most refer to closed work.

| Comment shape | Action |
|---|---|
| Tag + non-obvious *why* | Drop the tag, keep the why |
| Tag only, or tag + provenance ("Phase 238: added X") | Delete the comment |
| Tag stands in for a decision ("per D-04") | Replace the tag with the decision itself, in one clause |
| Pointer to an **open** seed for deliberately deferred work | Keep as `(see SEED-NNN)`. Open = file is in `.planning/seeds/`, not `.planning/seeds/closed/` |
| Bug-fix comment (required by CLAUDE.md) | Keep the explanation of what broke and why; drop the tag |

Before:
```python
# Phase 230 D-16: None means unchanged (the repository drops None values),
```
After:
```python
# None means unchanged (the repository drops None values),
```

Before (`frontend/src/hooks/useChessGame.ts`):
```ts
// Phase 210 (SEED-042): this loop was fully unguarded, and chess.js 1.4
// move() throws on illegal SAN. The history comes from sessionStorage, so a
// stale or hand-edited payload (...) would throw straight through the caller.
// Stop at the last legal ply and report that ply, rather than claiming one we never reached.
```
After (the history becomes a rule):
```ts
// chess.js 1.4 move() throws on illegal SAN, and the history comes from
// sessionStorage, so a stale or hand-edited payload (...) must not throw through
// the caller. Stop at the last legal ply and report that ply, rather than
// claiming one we never reached.
```

### 2.2 Content

| Smell | Action |
|---|---|
| Contradicted by the code (outdated) | Fix to match the code. If the *code* looks wrong, don't touch either; flag it as a suspected bug |
| Refers to a function, file, column, component, or flag that no longer exists | Fix or delete (grep before deciding) |
| History narration ("previously", "used to", "was renamed", "retired in") | Rewrite in present tense. Keep history only when it prevents a likely regression, phrased as a rule: "Don't X: Y breaks" |
| Restates the code | Delete |
| Commented-out code | Delete |
| TODO that is done or obsolete | Delete |
| TODO that is real | Keep if actionable in one line; otherwise list it as a seed candidate (don't create seeds) |
| Wrong or stale docstring | Fix; don't add docstrings where none existed |

Don't raise comment density. The only new comment text allowed is the reason that replaces a tag.

Section-divider and banner comments (`# ─── Seam A ───`) stay unless they label code that's gone.

---

## 3. Naming

### 3.1 What counts as a finding

Report a name only if a reader would be **misled or slowed down**, not because another name is
marginally nicer. Churn without clear gain is a rejection.

| Smell | Example |
|---|---|
| Misleading: says X, does/holds Y | `get_games()` that also writes; `flaws` that holds only blunders |
| Stale: the concept was renamed elsewhere (UI, schema, other layer) and this name kept the old term | old feature name in code after a UI rename |
| Inconsistent: one concept, several names across layers or files | see §3.3 glossary |
| Vague: `data`, `info`, `result2`, `tmp`, `handle`, `process`, `do_stuff`, `obj`, `item` in a non-trivial scope | |
| Wrong shape: `_list` that's a dict, plural for a scalar, `get_` for something expensive or side-effecting | |
| Missing unit on a time/size/score quantity | `timeout` (ms or s?), `delta` (cp or score?) |
| Boolean not predicate-shaped | `analysis` for a bool → `is_analyzed` / `hasAnalysis` |
| Unexplained abbreviation outside the domain vocabulary | `cnt`, `prc`, `tmpRes` |

Short names in tiny scopes (`i`, `fen`, `ply`, `cp`, `wdl`, `tc`, lambda args) are fine.

### 3.2 Conventions (match what the codebase already does)

| | Python | TypeScript |
|---|---|---|
| Case | `snake_case`, `PascalCase` classes, `UPPER_SNAKE` constants | `camelCase`, `PascalCase` components and types, `UPPER_SNAKE` module constants |
| Booleans | `is_ / has_ / should_ / can_` | `is / has / should / can` |
| Counts | `<thing>_count` (preferred) or `n_<things>` in math-heavy code | `<thing>Count` |
| Units | `_ms`, `_seconds`, `_cp`; avoid bare `_s` | `Ms`, `Seconds`, `Cp` |
| Hooks | — | `useXyz`; data-shaping hooks `useXyzData` |
| Repos / services | `<entity>_repository.py`, `<domain>_service.py` | — |

Domain vocabulary that needs no expansion: `fen`, `ply`, `cp`, `wdl`, `tc`, `elo`, `pv`, `uci`, `san`,
`pgn`, `acpl`, `maia`, `zobrist`, `eval`.

### 3.3 Glossary

The audit produces a terminology-conflict table (one concept, several names). Canonical terms bind
prose (comments, docstrings, test titles) and code written from now on. Existing identifiers change
only through INVENTORY §3/§5, D-05 and D-16, and a comment that names an identifier uses that
identifier's actual name. Glossary terms do not spawn renames in this phase.

Row numbers are the INVENTORY §2 row numbers. Names that are wire fields, DB columns, testids, Umami
events or persisted values are contracts (§1) and stay whatever the row says.

| # | Concept | Canonical | Also seen (to retire) | Decided |
|---|---|---|---|---|
| 1 | Which hash a position match uses | `match_side` stays (wire); document the two value sets, no rename | none (all contracts): `BookmarkMatchSide` and `MatchSideUpdateRequest.match_side` value sets | D-02 |
| 2 | User side of a you-vs-opponent comparison | `player` (paired with `opp`); `you_*` and `player_*` wire fields stay | `you_rate`, `you_events`, `youRate`, `youEvents`, `is_user`, `user_moves` | D-03 |
| 3 | Counted flaws on each side of a gap | Code: `events`; UI copy: "flaws" (GapPopover already states this rule) | `yourFlaws` (TacticCell local) | D-02 |
| 4 | Tempo / phase flaw tag spellings | Kebab for tag values, snake for metric ids; no rename | none (all contracts): `'low-clock'`, `'endgame'`, `'low_clock'`, `'endgame_phase'` | D-02 |
| 5 | Clock-pressure flaw tags (low-clock / hasty / unrushed) | Code: `tempo`; UI: "Clock" | `clock` in code | D-02 |
| 6 | Tactic motif vs tactic family ids for the same tactic | Both persisted or cross-stack: document the mapping, no rename | none (all contracts): hyphenated `hanging-piece`, `x-ray`, `double-check`, `discovered-attack` vs snake `hanging`, `x_ray`, `double_check`, `discovered_attack` | D-02 |
| 7 | Tactic orientation (missed vs allowed) | `orientation`; one alias `TacticOrientation` for the 3-value filter and `TacticSide` for the 2-value slot, imported everywhere. In `fetch_tactic_comparison`, `orientation` (count column set) and `tactic_filter_orientation` (filter) are two different things and both stay | `tactic_orientation`, `orientation_kind`, `side`, `TACTIC_SIDES`, `TacticOrientationFilter`, `TacticChipOrientation`, restated inline `Literal` / union types, `line` (flaw-blob token) | D-02 |
| 8 | Minimum tactic confidence for a chip (70) | `MIN_TACTIC_CHIP_CONFIDENCE` | `_TACTIC_CHIP_CONFIDENCE_MIN`, `tactic_confidence_min` | D-02 |
| 9 | Side that delivers / should have found a tactic | `solver` for the tactic side; `mover` for the side that played the move | `pov`, `refuter` / "refuting side" | D-02 |
| 10 | Point-of-view color for expected-score conversion | `mover_color` where the value is the mover's POV; `user_color` only where it really is the user | `mover` (accuracy_acpl) | D-02 |
| 11 | Whose result a flaw's `user_result` parameter holds | `mover_result` (it holds the flaw-maker's result) | `user_result`, `subject_result` | D-02 |
| 12 | Train streak counter | `session_streak_count`; retire `settled_streak_weeks` from comments (column stays) | `settled_streak_weeks` | D-02 |
| 13 | Streak buffer (missable days) | UI and FE code: "freezes"; `shield_level` and the `train-shield-*` testids stay (contract) | `shield_level`, `SHIELD_CAP` in prose about the UI | D-02 |
| 14 | Medal not yet acknowledged | Internal: `uncelebrated` / `celebrated` (matches the column); the `/medals/unclaimed` route path stays | `unclaimed` in internal names (`fetch_unclaimed`, `UnclaimedRow`) | D-02 |
| 15 | Solves excluding sharp fillers | `non_filler` | `nf_` prefix (`nf_points`, `nf_puzzles`), `_NON_FILLER`, `SHARP_FILLER` | D-02 |
| 16 | A Train exercise | "puzzle" in prose and new code; `drill_*` tables and models stay; `item` only for the SR bookkeeping row | `drill` in prose | D-03 |
| 17 | Per-puzzle move grade in Train | `moveTier` for the 3-value tier; `move_quality` wire stays | `moveQuality` (param typed `TrainMoveTier`), `TrainMoveQuality` for the 3-value tier | D-02 |
| 18 | The "only one good move" guess | Internal `'critical'`, label "Only one"; `sharp` is the puzzle type (distinct concept) | "only one good move" in prose | D-02 |
| 19 | The user's played move in the Train reveal | "played move" in code | `'your'` (RoleKey), "Your move" | D-02 |
| 20 | The Train puzzle's server answer move | `key*` (`GradeResult` is in the sessionStorage reveal cache, so its fields are a contract) | `bestMoveUci`, `bestLine`, `esBefore` | D-02 |
| 21 | First-reveal onboarding on the Train reveal | "tour" (matches the persisted `reveal_tour_stage`); testids stay | "walkthrough" | D-05: walkthrough → tour is the one cross-layer rename this phase applies to existing identifiers (plan 241-69); contracts kept: `review_walkthrough`, testids `train-bot-walkthrough` / `btn-train-bot-walkthrough-next`, persisted/wire keys in `trainTelemetry.ts` |
| 22 | Jump the reveal board back to the puzzle position | "Rewind"; the `train-solution` Umami target stays | "Solution", "Reset" (`onReset`, `canReset`, `revealCanReset`) | D-02 |
| 23 | User-played moves off the known lines on the reveal | "sideline" | "free-play", "fork", "off-line" | D-02 |
| 24 | Desktop verdict surface on the Train reveal | `TrainVerdictCard` | "verdict bubble" | D-02 |
| 25 | Whether a game's stored evals came from lichess | `is_lichess_eval_game` via the `eval_utils` derivation (already enforced by an AST test) | `derive_raw_lichess_eval_game`, `stored_eval_predates_engine`, `lichess_arm`, "lichess-arm game", "lichess %eval game" | D-02 |
| 26 | A game counts as "analyzed" | "analyzed" = `full_evals_completed_at IS NOT NULL`; other predicates get names that say what they test (e.g. `has_oracle_counts`, `has_eval_coverage`); column names stay | `Game.is_analyzed`, `already_analyzed`, "oracle-present gate", bare `evals_completed_at` | D-02 |
| 27 | Tier-4b best-move backfill lane | `best_move` in Python identifiers; `bestmove` only in endpoint paths (remote-worker contract) | `bestmove` in Python identifiers | D-02 |
| 28 | Per-color inaccuracy/mistake/blunder counts on `games` | "flaw counts" | "oracle counts", "oracle columns", "severities" | D-02 |
| 29 | MultiPV-2 continuation data on a flaw | "PV-line blob"; "answer key" only for the Train use of it | "continuation blob", "slim blob", "pv lines" | D-02 |
| 30 | Attempt-cap terminal path of the completion decision | "attempt cap" | "Path C", "cap reached", "capacity reached" | D-02 |
| 31 | Position-keyed eval map (before the post-move shift) | `eval_of_position` | `pos_eval`, `engine_result_map` | D-02 |
| 32 | Opening-region eval reuse | "opening cache" for the table, "dedup transplant" for the act of copying from it | bare "dedup" for the table | D-02 |
| 33 | Import-time entry-ply eval lane | "entry-ply lane" | "cold drain", "cold lane", "entry eval" | D-02 |
| 34 | Time-control bucket field | New code: `time_control_bucket`; the others are DB columns or wire fields, no rename | none (all contracts): `tc`, `tc_bucket`, `tc_tranche`, `time_control` | D-02 |
| 35 | Time-control bucket type and order | `TimeControlBucket`; one shared TC order constant (seed-sized) | `TcBucket`, inline `Literal['bullet','blitz','rapid','classical']`, per-module order constants | D-02 |
| 36 | Platform-reported vs our computed accuracy/ACPL | `NormalizedGame` fields should map to `*_imported`; tied to suspected bug #1 in INVENTORY §7 | `white_accuracy` / `white_acpl` on `NormalizedGame` for the platform-reported value | D-02 |
| 37 | Entry-eval bucket (conversion/parity/recovery) | `MaterialBucket` (already dominant) | `_MATERIAL_BUCKETS`, `bucket` (`RankedBucketOut`) | D-02 |
| 38 | Recovery-bucket score gap | Internal `score_gap_<bucket>`; `recovery_score_gap` is a persisted enum value and stays | `score_gap_recov`, `recov_score_gap` | D-02 |
| 39 | Conversion / parity / recovery rate | `*_rate` for 0-1 fractions, `*_pct` only for 0-100 (see row 42) | `conv_rate`, `recov_rate`, `per_user_cte_conv_rate_tc`; `conversion_win_pct` / `parity_score_pct` / `recovery_save_pct` are 0-1 wire ids and stay | D-02 |
| 40 | Clock advantage at endgame entry vs base time | "clock gap" (UI term); wire ids and testids stay | "Clock Difference", `clock_diff_pct`, `clock_gap_frac` (locals) | D-02 |
| 41 | Net timeout outcome rate | "net flag rate" | `net_timeout_rate` in prose (zone MetricId stays) | D-02 |
| 42 | What a `pct` suffix means | Rule: `_pct` = 0-100, `_frac` or `_rate` = 0-1; wire ids stay | `MAX_CLOCK_PCT_OF_BASE`, `TIME_PRESSURE_CLOCK_PCT_THRESHOLD`, `user_clk_pct` (all 0-1 under a `pct` name) | D-02 |
| 43 | \|eval_cp\| >= 2000 outlier trim | `EVAL_OUTLIER_TRIM_CP`, one definition | `EVAL_CLIP_MAX_CP`, the literal `2000` in canonical CTE SQL | D-04: seed candidate, no merge in this phase |
| 44 | Trend direction vocabulary | improving / declining / stable; values that reach the LLM prompt text are contract (§1), so change only with a prompt-version bump | improving / regressing / flat (player profile, `_trend_info`, ELO variant lines) | D-02 |
| 45 | Endgame Metrics section | `endgame_metrics` internally; the `metrics_elo` wire id stays | `_METRICS_ELO_BUCKETS` | D-02 |
| 46 | Score gap at endgame entry vs engine expectation | Code: `achievable_score_gap`; UI: "Eval Score Gap"; retire "vs. engine" | "Achievable Score Gap" in docstrings, "vs. engine" (`VS_ENGINE_DOMAIN`, `vsEngineValue`), "vs. expected", "vs. eval" | D-02 |
| 47 | Score the engine expects from the endgame-entry eval | "expected score" | "Entry Eval Score", "Expected" (FlowBox label) | D-02 |
| 48 | Avg eval at the opening-to-middlegame transition | "opening-end eval" (matches evalContext); "avg eval" when a component serves both contexts (see INVENTORY §5 `hasAvgEval`) | "MG entry" (`hasMgEval`, `mgEvalTextContent`), "End Eval" | D-02 |
| 49 | Sigmoid of a centipawn eval on [0,1] | "expected score" | "win-prob" / "win probability" (`ONLY_MOVE_WIN_PROB_MARGIN`, `p_best`, `p_second`) | D-02 |
| 50 | Flaw tag for a blunder the opponent failed to punish | `lucky` (persisted); UI copy may say "unpunished" | `unpunished` in internal names (`_is_unpunished`) | D-02 |
| 51 | The bot's rating on a bot game | `bot_rating` for the stored value, `nominal_elo` for the dial; the `bot_elo` wire field stays | `bot_elo` outside the wire field | D-02 |
| 52 | Opponent-matching rating for bot setup | `current_strength` | `normalizedRating`, `lichess_blitz_equivalent_rating` (retired) | D-02 |
| 53 | User's rating at game time | `user_rating`; `anchor_rating` is a different concept (the median anchor) and stays | `user_elo` | D-02 |
| 54 | The user's endgame insights report object | `insights` (`report` collides with the response's `.report` field) | `matchingInsights`, `cachedInsights`, `rendered`, `response`, `report` | D-02 |
| 55 | Eval chart's active scrub ply | `activePly` / `onActivePlyChange`; `hoverPly` only for real hover state | `onHoverPlyChange`, `notifyActivePly`, `handleEvalChartPlyChange` | D-02 |
| 56 | Confidence popover/tooltip pairs | Score/Eval pairs: `WdlConfidenceTooltip`, `EvalConfidenceTooltip` | `ScoreConfidencePopover`, `BulletConfidencePopover` | D-02 |
| 57 | One you-vs-opponents gap datum | Keep both: `bullet` = API datum, `GapCell` = render shape | none (two distinct roles) | D-02 |
| 58 | Weekly game count behind timeline volume bars | Wire fields stay; new fields: `per_week_game_count` | none (all contracts): `per_week_total_games`, `per_week_games`, `per_week_total_visible` | D-02 |
| 59 | Format a cp/mate eval for display | `formatEval`; the inventoried `formatScore` → `formatEval` rename in `EngineLines.tsx` still ships (plan 241-59) | `formatScore`, `formatEvalText`, `scoreText`, `formatVerdictEval`, `formatPlayerPovEval` | D-04: seed candidate, no merge in this phase |
| 60 | FEN to game-ply offset | `fenToPly` (one lib helper) | `plyFromFen`, `fenToRootPly` | D-04: seed candidate, no merge in this phase |
| 61 | Maia human-move tab/panel on /analysis | "Maia" in code; the `analysis-tab-human` testid stays | "Human" (`HumanTab`, tab value `'human'`) | D-02 |
| 62 | Bots custom-game setup form | No change needed; "custom setup" in prose | none | D-02 |
| 63 | Player info row beside a board | `PlayerBar` for the board row, `AnalysisPlayerBar` for the wrapper | `BoardPlayerBar` (import alias), analysis wrapper named `PlayerBar` | D-02 |
| 64 | Small read-only chess board | `MiniBoard` + `BookmarkMiniBoard` | second `MiniBoard` in `position-bookmarks/` | D-02 |
| 65 | The color the user played (filter) | `playedAs` for the filter; `color` for the Openings board color only | "Played-as" in comments for `FilterState.color` | D-02 |
| 66 | Tactic depth filter | "depth"; presets low / medium / high | "Tactic difficulty", "difficulty band", "Intermediate" (stale preset name) | D-02 |
| 67 | Gem + Great move filter vs the "best" tier | "Gem/Great" for the filter; "best" only for the tier | "Best Moves" as the filter section label | D-02 |
| 68 | Standalone Stockfish analysis engine | `stockfish` prefix (the FlawChess Engine is also an "engine") | bare `engine`, `engineEnabled`, `sf` (`sfArrowCount`, `sfRankCount`) | D-02 |
| 69 | Worker failed to load / died | `hasFailed` | `hasError` | D-02 |
| 70 | Last-move square tint | `lastMoveColor` | `lastMoveHighlightColor`, `lastMoveTierColor` | D-02 |
| 71 | Per-square board badges (`SquareMarker[]`) | `squareMarkers` | `boardMarkers`, `boardSquareMarkers` | D-02 |
| 72 | TanStack staleTime constants | `<X>_STALE_TIME_MS` | `ENDGAME_STALE_TIME`, `LIBRARY_STALE_TIME`, inline `300_000 // 5 minutes` | D-02 |
| 73 | Bot game in-progress gate | `isLive` | `live`, `confirmLive` | D-02 |
| 74 | Neutral grey board arrow | `NEUTRAL_ARROW_COLOR` | `DARK_BLUE`, `ARROW_NEUTRAL`, "DARK_BLUE band" | D-02 |
| 75 | Mobile filter / bookmark drawer | "drawer"; testids stay | `filterSidebarOpen`, "sidebar" | D-02 |
| 76 | Openings "Moves" tab | No change (the `explorer` route value is a URL contract) | none (all contracts) | D-02 |
| 77 | Library Stats tab | "Library Stats"; a file rename would be a separate decision | `GlobalStatsPage` / `GlobalStats.tsx` in prose | D-02 |
| 78 | Most played openings | Keep `mpo` (testids are contract) | none (all contracts) | D-02 |
| 79 | iPadOS desktop-UA detection | One helper and one threshold (`isIpadOsDesktopUserAgent` vs `isIosWebKit`); the two thresholds look equivalent (`>= 2` vs `> 1`) but the owner should confirm before merging | `MIN_TOUCH_POINTS_FOR_IPAD`, `IPAD_MIN_TOUCH_POINTS` (two constants) | D-04: seed candidate, no merge in this phase |

---

## 4. Rename mechanics

1. **Classify the blast radius** before renaming:
   - `local`: function or file internal
   - `module`: exported but used in one layer
   - `cross-layer`: crosses backend ↔ frontend, or reaches tests and scripts
   - `contract`: touches §1 → don't rename, flag
2. **Python:** after a rename, grep the old name *as a string* too. ty does not see `getattr`, `text()` SQL,
   Pydantic aliases, JSONB keys, string-keyed dicts, `mock.patch("module.name")` targets, or log `extra=` keys.
3. **TypeScript:** `npm run build` (tsc), not just lint and test, because esbuild strips types.
   Also grep for the old name in `vi.mock(...)` paths and string keys.
4. **File renames:** update imports, `vi.mock` / `mock.patch` paths, and doc references in `docs/`, `CLAUDE.md` files.
5. **One cross-layer rename per commit**, message `refactor(naming): old_name → new_name`.
   Comment cleanup is a separate commit per area: `chore(comments): <area>`.

---

## 5. Process

1. Owner approves this guide and the off-limits list.
2. The audit workflow (`.planning/phases/241-codebase-cleanup/241-audit-workflow.js`) writes `.planning/phases/241-codebase-cleanup/241-INVENTORY.md`.
3. Owner prunes the inventory and fills the §3.3 glossary.
4. Comment cleanup, parallel by area (disjoint files).
5. Local and module renames, per area.
6. Cross-layer renames, one at a time in sequence.
7. Full pre-merge gate, squash-merge between phases (no open feature branches).
