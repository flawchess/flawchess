# Pitfalls Research

**Domain:** Advanced chess analytics — ELO-adjusted metrics, cross-platform rating normalization, opening risk scores, refined endgame statistics
**Researched:** 2026-04-04
**Confidence:** HIGH (codebase verified, domain patterns confirmed via external sources)

---

## Critical Pitfalls

### Pitfall 1: Lichess-to-Chess.com Rating Offset Is Not a Fixed Constant

**What goes wrong:**
The backlog spec (Phase 999.5) uses a fixed tapering formula: `offset = max(0, 350 - (lichess_rating - 1400) * 0.3)`. This is a reasonable approximation but the actual offset is neither linear nor symmetric across time controls. External analysis (NoseKnowsAll 2024 converter) shows the relationship varies significantly by skill level — the gap can invert near 2100+ rated players. If the formula is treated as authoritative rather than an approximation, ELO-adjusted skill scores will be systematically biased at the extremes of the rating range.

The formula is also per-platform but not per-time-control. Players who only play bullet on lichess get the blitz-calibrated offset applied, which is wrong by roughly 30–50 points.

**Why it happens:**
Developers find a plausible-looking formula and treat it as ground truth without documenting its limits. The formula is derived from community analysis that drifts over time as platforms update their rating systems.

**How to avoid:**
- Implement the formula as a named function `normalize_lichess_rating(rating: int) -> int` with a docstring explicitly calling it an approximation.
- Do not display the adjusted score with more than one decimal of precision — false precision amplifies the formula's error.
- Add a tooltip/info label on the gauge: "Normalized to chess.com blitz equivalent (approximate)" so users understand this is a heuristic.
- Accept the per-time-control limitation explicitly; document it in code rather than silently applying blitz calibration to bullet games.

**Warning signs:**
- Adjusted score shows no difference from raw score for a mixed chess.com/lichess user — the normalization branch is not executing.
- Users who only play bullet on lichess complain the score looks wrong.

**Phase to address:**
ELO-Adjusted Endgame Skill — backend service function. Name and document the normalization function before wiring it into the skill calculation.

---

### Pitfall 2: Deriving Opponent Rating from white_rating/black_rating Gets the Color Logic Inverted

**What goes wrong:**
The `games` table stores `white_rating` and `black_rating` — absolute by piece color, not user-relative. Deriving opponent rating requires inverting the user's color: if `user_color == "white"` then opponent is `black_rating`, and vice versa. This is the exact opposite of the user-rating pattern already in `stats_repository.py`. Getting this backwards produces an `opponent_rating` that equals the user's own rating, making the ELO adjustment multiply by the user's own strength instead of their opponent's. The resulting adjusted score will be perfectly correlated with the user's rating history but measure nothing about opponent quality.

**Why it happens:**
The correct pattern for `user_rating_expr` already exists in `stats_repository.py` as `case((Game.user_color == "white", Game.white_rating), else_=Game.black_rating)`. The opponent derivation is the mirror image, and it is easy to copy the user-rating pattern and forget to flip it.

**How to avoid:**
```python
# CORRECT opponent rating derivation (user_color is white -> opponent is black)
opponent_rating_expr = case(
    (Game.user_color == "white", Game.black_rating),
    else_=Game.white_rating,
).label("opponent_rating")
```
Write a unit test that creates a game where `user_color="white"`, `white_rating=1200`, `black_rating=1500`, and asserts `opponent_rating == 1500`.

**Warning signs:**
- Adjusted endgame skill produces a smooth upward trend that exactly mirrors the user's own rating history — this is the tell that the user's own rating is being used.
- `avg_normalized_opponent_rating` matches the user's own ELO perfectly for a user who has only played one platform.

**Phase to address:**
ELO-Adjusted Endgame Skill — the endgame repository query that includes opponent_rating in the SELECT. Add the unit test before wiring the value into the performance calculation.

---

### Pitfall 3: Opponent Rating Average Must Come From the Same Row Population as the Skill Score

**What goes wrong:**
The ELO-adjusted skill score requires `avg_normalized_opponent_rating` computed over the same games that contributed to `raw_endgame_skill`. Conversion games are only those where the user entered the endgame with >= 300cp material advantage. Recovery games are only those where the user was down >= 300cp. These subsets may cluster at different opponent rating ranges (e.g., lower-rated opponents blunder material more often, so conversion games may skew toward weaker opponents). Computing `avg_opponent_rating` over all endgame games, or worse over all games, will introduce a systematic bias in the adjusted score.

**Why it happens:**
A single `AVG(opponent_rating)` over all endgame entry rows is tempting and cheap. The mismatch with the skill score's actual population is non-obvious.

**How to avoid:**
Accept a documented approximation: compute `avg_opponent_rating` over all endgame entry rows (not split by conversion/recovery subset), and document this in code. This is a second-order error and acceptable for a heuristic metric. What is not acceptable is computing the average over all user games — the calculation must be scoped to the same endgame entry row set used for skill computation.

The cleanest implementation: fetch opponent_rating as an extra column in `query_endgame_entry_rows`, then compute the average Python-side from the same rows that produce `raw_endgame_skill`. No separate query needed.

**Warning signs:**
- `avg_normalized_opponent_rating` is approximately 1500 (the reference rating) for a user who only plays against 1200-rated opponents — signals the unfiltered or wrong population is being used.
- The adjusted score is identical to the raw score for all users despite playing varied opponents.

**Phase to address:**
ELO-Adjusted Endgame Skill — add `opponent_rating` column to the existing `query_endgame_entry_rows` result set rather than writing a new query.

---

### Pitfall 4: NULL Opponent Ratings Break the Adjustment Without Failing Visibly

**What goes wrong:**
`white_rating` and `black_rating` are nullable in the `games` table. Computer games, casual unrated games, and some early imports may have NULL. SQL `AVG()` ignores NULLs silently. If a user has 500 endgame games but only 50 have opponent ratings, `avg_opponent_rating` is computed from 50 games while `raw_endgame_skill` is computed from 500. The adjusted score appears valid but reflects opponent quality from a non-representative sample with no error or warning.

**Why it happens:**
SQL AVG() ignores NULLs silently. Python averaging over a list that skips None produces no error. Neither path warns that the denominator shrank.

**How to avoid:**
- Track `rated_games_count` (non-NULL opponent ratings) alongside `total_endgame_games` in the Python aggregation.
- Define a constant `MIN_RATED_GAMES_FOR_ELO_ADJUSTMENT = 10`.
- If `rated_games_count < MIN_RATED_GAMES_FOR_ELO_ADJUSTMENT`, return `elo_adjusted: false` and show the raw score with a label indicating insufficient rating data.
- Include `elo_adjusted: bool` in the API response schema from day one so the frontend can conditionally show "ELO-adjusted" vs "Raw" in the gauge label.

**Warning signs:**
- User has only casual/unrated games; adjusted score shows a value but no warning appears.
- `avg_normalized_opponent_rating` equals exactly 1500 (the reference) — this should only happen when there is no rating data, meaning the fallback is triggered but not being surfaced in the UI.

**Phase to address:**
ELO-Adjusted Endgame Skill — include `elo_adjusted: bool` and `rated_games_count: int` in the response schema. Decide the fallback behavior before writing the computation.

---

### Pitfall 5: Opening Risk Score Conflates Draw Rate With Risk

**What goes wrong:**
A common mistake when building opening risk metrics is treating "high draw rate = safe opening" and "high decisive rate = risky opening." This penalizes openings where the user wins sharply (the Sicilian, the King's Indian Attack) and rewards passive drawish openings (the Berlin Defense). From the user's perspective, the relevant risk is the probability of a bad outcome: `P(loss)`, not `P(decisive game)`.

If risk is defined as `(wins + losses) / total` (decisiveness) or `1 - draw_rate`, the metric produces a counterintuitive result that repels users from their best openings.

**Why it happens:**
"Volatility" and "risk" sound similar. Game-level eval-swing volatility (centipawn standard deviation) is easy to compute but measures game drama, not player risk. Developers conflate the two or pick the metric that is easiest to implement rather than the one that is most useful.

**How to avoid:**
Define opening risk explicitly as user-facing loss rate: `risk_score = loss_pct / 100`. This is simple, interpretable, and directly actionable. If a variance-based metric is desired as a secondary signal, use outcome variance (treating win=1, draw=0.5, loss=0) rather than eval-swing volatility. Do not use eval-swing volatility for opening risk: (a) most users lack engine analysis for all games, and (b) chess.com and lichess eval data are not on the same centipawn scale.

**Warning signs:**
- Opening risk metric shows the Berlin Defense (notoriously drawish) as the safest opening.
- The King's Indian Attack (often decisive wins for white) shows as "high risk" even though the user wins most of those decisive games.
- Users report "this seems backwards."

**Phase to address:**
Opening Risk — define the formula explicitly in the phase spec before writing any code.

---

### Pitfall 6: Changing endgame_skill Field Semantics Breaks Gauge Zone Thresholds Silently

**What goes wrong:**
The `EndgamePerformanceResponse` schema's `endgame_skill` field is currently the raw composite (0.7 × conversion_pct + 0.3 × recovery_pct). The gauge in `EndgameGauge.tsx` has hardcoded zone thresholds calibrated to this scale. If `endgame_skill` is changed in-place to return the ELO-adjusted value without a corresponding threshold update, the gauge will show incorrect zone boundaries. TypeScript will not catch this because the type is `number` — the change is semantic, not structural.

The adjusted score can also exceed 100 when a user consistently plays against above-reference opponents, which will peg the gauge needle at maximum.

**Why it happens:**
Backend and frontend are in the same repo, making it tempting to change both "atomically" in one PR. Semantic field reuse looks clean but creates hidden coupling between the formula and the gauge's domain bounds.

**How to avoid:**
- Add `adjusted_endgame_skill: float` as a NEW field in `EndgamePerformanceResponse` alongside the existing `endgame_skill`.
- Keep `endgame_skill` as the raw score until the frontend gauge explicitly opts in to the adjusted version.
- Update the TypeScript `EndgamePerformanceResponse` interface in `endgames.ts` in the same commit as the Pydantic schema change.
- Decide and document the domain bounds for the adjusted score gauge before writing the frontend gauge component.

**Warning signs:**
- Gauge needle pegs at maximum or zero after the change.
- `endgame_skill` docstring says one thing but frontend renders it as something different.

**Phase to address:**
ELO-Adjusted Endgame Skill — schema design step. Explicitly decide new field vs replace in the design notes before any code is written.

---

### Pitfall 7: Rolling ELO-Adjusted Skill Timeline Missing the Pre-Fill Pattern

**What goes wrong:**
The existing `get_endgame_timeline` correctly fetches all historical games (ignoring the recency cutoff) to pre-fill the rolling window, then filters output points to the recency window. If the new "Endgame Skill Over Time" timeline is added without this pattern, users with a recency filter of "last 3 months" will see a chart that starts from a cold window and shows misleadingly volatile scores at the start of the display range.

This is already solved in the codebase — but only for the existing timeline. It is easy to write the new timeline endpoint from scratch and omit the pre-fill.

**Why it happens:**
The pre-fill pattern is non-obvious (why would you fetch more data than you display?). A developer writing a new timeline endpoint without closely studying `get_endgame_timeline` will miss it.

**How to avoid:**
Copy the two-step pattern from `get_endgame_timeline` exactly:
```python
# Step 1: Fetch full history (no recency filter) to pre-fill rolling window
rows = await query_elo_skill_rows(session, ..., recency_cutoff=None)
# Step 2: Compute rolling series over full history
series = _compute_rolling_series(rows, window)
# Step 3: Filter output to recency window
if cutoff_str:
    series = [pt for pt in series if pt["date"] >= cutoff_str]
```

**Warning signs:**
- Timeline chart shows a flat or near-zero line at the start when a recency filter is applied.
- Removing the recency filter shows much smoother historical data — cold-start artifact.

**Phase to address:**
ELO-Adjusted Endgame Skill timeline — apply the pre-fill pattern from day one.

---

### Pitfall 8: asyncpg Arg Limit Violated When Adding Columns to game_positions Bulk Insert

**What goes wrong:**
`bulk_insert_positions` chunks position row inserts to stay under asyncpg's 32767-parameter limit. The current chunk size is tuned for the existing column count on `game_positions`. Adding even one new column (e.g., denormalizing `opponent_rating` for query performance) decreases the safe chunk size below the existing constant. The failure mode is a cryptic asyncpg error during import (`too many parameters`), not caught by unit tests unless a large-batch import is tested.

**Why it happens:**
The chunk-size calculation divides 32767 by the number of columns. If a developer adds a column without recalculating the constant, the first large import silently fails after partial insertion.

**How to avoid:**
- For ELO-adjusted skill: do NOT denormalize `opponent_rating` into `game_positions`. Fetch it at query time via JOIN to `games`. This avoids any bulk insert impact.
- If any new column is added to `game_positions` for other reasons, recalculate the chunk size immediately and update the comment: `# chunk_size = floor(32767 / num_columns_per_position_row)`.
- Add a CI test that imports a synthetic batch of 500 games and verifies all positions were inserted successfully.

**Warning signs:**
- Import fails silently for large game batches after a schema migration.
- Position count in the DB is lower than expected after a large import.
- Sentry shows `asyncpg.exceptions.TooManyArgumentsError` during import.

**Phase to address:**
Any phase that modifies the `game_positions` schema — recalculate and update chunk size immediately as part of the migration PR.

---

### Pitfall 9: Missing NULL Guard on opponent_rating Produces Silent NaN or TypeError

**What goes wrong:**
New endgame repository queries that JOIN `games` for opponent_rating must handle the case where `opponent_rating` is NULL. SQL `AVG()` excludes NULLs silently, but the Python aggregation loop receives a `None` value per row. If the multiplication `raw_endgame_skill * avg_normalized_opponent_rating / reference_rating` is not guarded, the result is either `None * float = TypeError` (crashes) or `0.0 * float = 0.0` (wrong), or the None propagates into the Pydantic model as a validation error.

**Why it happens:**
The existing endgame code does not need to handle per-game ratings, so there is no existing pattern for NULL-guarded rating arithmetic. New code written from scratch often skips the guard.

**How to avoid:**
- When extracting opponent_rating per row, use `row.opponent_rating or None` (not `0`) and skip None values in the average computation.
- Define the fallback explicitly: if no rows have opponent_rating, return `avg_normalized_opponent_rating = reference_rating` (adjustment factor = 1.0, so adjusted == raw) and set `elo_adjusted = false`.
- Use a constant `REFERENCE_RATING = 1500` in the service module — never inline the literal.

**Warning signs:**
- Sentry shows `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'` from the endgame performance endpoint.
- `adjusted_endgame_skill` is 0.0 for all users — signals that `avg_normalized_opponent_rating` is being computed as 0 instead of the reference fallback.

**Phase to address:**
ELO-Adjusted Endgame Skill — service-layer aggregation function. Add the NULL guard and the `elo_adjusted: bool` flag before wiring into the response.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode lichess offset formula without documenting it as approximate | Simpler implementation | Formula drift as platforms update; incorrect adjustment for non-blitz lichess players; users trust it as exact | Acceptable only if labeled as approximate in both code and UI |
| Denormalize opponent_rating into game_positions | Faster endgame queries without JOIN | Increases bulk insert parameter count, risks asyncpg arg limit, increases row storage, requires migration + backfill | Never for v1.8 — JOIN at query time instead |
| Reuse endgame entry rows to compute avg opponent rating without deduplication | One query, no changes | Entry rows are per-(game, endgame_class) — a game with multiple endgame classes appears multiple times, over-weighting its opponent_rating in the average | Never — deduplicate by game_id before computing the average, or use SQL AVG with DISTINCT |
| Define opening risk as 1 - draw_rate | Simple, no schema changes needed | Semantically wrong — high decisive win rate gets penalized equally with high loss rate | Never |
| Replace endgame_skill field in schema with adjusted value | Fewer API fields | Breaks gauge zone thresholds silently; TypeScript type system cannot detect semantic change | Never in v1.8 — add as a separate field |
| Skip `elo_adjusted: bool` flag in API response | Simpler schema | Frontend cannot differentiate between adjusted and raw display; users see "ELO-adjusted" label even when rating data is insufficient | Never — include the flag from day one |

---

## Integration Gotchas

Common mistakes when connecting to existing system components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `apply_game_filters` | Adding a new filter (e.g., min_opponent_rating) directly inside the function body | Add as an optional parameter with default `None` and a clear docstring entry; the function signature feeds 5+ repositories — an undocumented change is a silent footgun |
| `EndgamePerformanceResponse` Pydantic schema | Adding `adjusted_endgame_skill` and updating TypeScript `EndgamePerformanceResponse` in separate commits | Schema change and TypeScript type update must be in the same commit — `ty check` and knip run in CI but neither catches missing interface fields |
| `EndgameGauge.tsx` zone thresholds | Copying existing zone bounds (0/40/60/75/100) for the adjusted score gauge | Adjusted score can exceed 100 when playing against above-reference opponents; decide the display domain before wiring the gauge |
| `query_endgame_entry_rows` result row shape | Adding opponent_rating as column 6 without updating the destructuring tuple in `_aggregate_endgame_stats` | Python will not error on an extra column; it silently ignores it. Use a NamedTuple or TypedDict for the row shape so structural changes are caught |
| Rolling timeline pre-fill | Passing `recency_cutoff` directly to the DB query for the ELO timeline | Pass `recency_cutoff=None` to the DB query; filter output points in Python after computing the rolling series |
| `_compute_rolling_series` | Writing a third nearly-identical rolling series function for the ELO-adjusted timeline | Refactor `_compute_rolling_series` to accept an outcome value extractor callable so all rolling timelines share one implementation |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Computing avg opponent_rating in a separate query instead of inline with entry rows | Two DB round-trips; latency doubles for the performance endpoint | Add opponent_rating as an extra SELECT column to `query_endgame_entry_rows`; compute the average Python-side from the same fetched data | Noticeable at 10K+ games per user |
| Re-running `_aggregate_endgame_stats` multiple times in the same request | Redundant Python aggregation CPU; the function iterates all rows twice | `get_endgame_performance` already calls it once — do not add a second call for ELO-adjusted computation; derive adjusted values from the same aggregation pass | Negligible at current scale but sets a bad precedent |
| Fetching opening risk by querying each opening position individually | N queries for N openings; latency scales linearly | Use the existing `query_position_wdl_batch` pattern — pass a list of hashes, get back a dict in one query | Noticeable at N > 20 openings |
| Running 8+ sequential endgame timeline queries (already exists) | Slow timeline response | Do not add more per-class queries without profiling; the current 8-query approach is already at the edge of acceptable latency | Already 8 queries; each addition multiplies response time |

---

## Security Mistakes

Domain-specific security issues relevant to these features.

| Mistake | Risk | Prevention |
|---------|------|------------|
| New ELO-adjusted query missing `Game.user_id == user_id` WHERE clause | One user could query another user's opponent rating distribution | `apply_game_filters` scopes by user_id already; verify any new raw query that bypasses `apply_game_filters` includes an explicit user_id filter |
| Exposing reference_rating as a user-configurable parameter | Users can inflate or deflate their adjusted score arbitrarily | REFERENCE_RATING must be a server-side constant — never accept it from query parameters |
| Returning individual opponent ratings in the API response | Privacy concern — surfacing per-game opponent data beyond what is already in game cards | Only return aggregates (avg_normalized_opponent_rating, rated_games_count) in the ELO-adjusted response, not per-game opponent ratings |

---

## UX Pitfalls

Common user experience mistakes for these features.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Displaying adjusted_endgame_skill with two decimal places | Implies false precision for a heuristic metric built on a calibration approximation | Round to one decimal; add info popover explaining the formula and its known limits |
| Showing ELO-adjusted score without indicating it differs from raw | Users cannot tell why their score changed after the update | Always show "ELO-adjusted" label with an info icon when `elo_adjusted == true`; show "Raw score (insufficient rating data)" when `elo_adjusted == false` |
| Displaying "Endgame Skill Over Time" chart before the user has enough games | Empty or noisy chart for new users | Apply `MIN_GAMES_FOR_ELO_TIMELINE = 10` threshold; show empty state with explanation instead of a near-flat line |
| Not updating mobile layout alongside desktop layout | Mobile users see old gauge without the new ELO-adjusted label or updated value | The Endgames page has both desktop sidebar and mobile drawer layouts; apply UI changes to both (per CLAUDE.md rule) |
| Opening risk score shown without sample size | Users over-interpret low-sample risk scores | Show game count alongside every risk score; grey out or asterisk scores below `MIN_GAMES_FOR_OPENING_RISK = 5` |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **ELO-adjusted gauge:** `elo_adjusted: bool` field is in the API response — verify the frontend shows "ELO-adjusted" vs "Raw" label conditionally, not unconditionally.
- [ ] **Cross-platform normalization:** Edge case of user with only lichess games (100% offset applied) and user with only chess.com games (0% offset) both produce sensible, distinct scores.
- [ ] **Opponent color logic:** Unit test passes for a known-color game asserting `opponent_rating == black_rating` when `user_color == "white"`.
- [ ] **NULL opponent ratings:** Endpoint tested with a user who has all unrated games — returns valid response with `elo_adjusted: false`, no 500 or NaN.
- [ ] **Rolling ELO-adjusted timeline:** Pre-fill pattern applied — switching recency filter produces no cold-start artifacts in the chart.
- [ ] **TypeScript types:** `EndgamePerformanceResponse` interface in `endgames.ts` updated in the same PR as the Pydantic schema — new field is present and typed correctly.
- [ ] **asyncpg chunk size:** If any new column was added to `game_positions`, chunk size constant was recalculated and a large-batch import test passes.
- [ ] **Opening risk formula:** Definition is `loss_pct` or a clearly labeled WDL decomposition — not `1 - draw_rate`. Verified with a Berlin Defense position (drawish, low-loss) showing low risk.
- [ ] **Mobile layout:** New gauge label and adjusted score appear correctly on mobile — Endgames page mobile section was updated alongside the desktop section.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong color for opponent_rating deployed to production | MEDIUM | Deploy fix immediately; adjusted scores auto-correct on next API call — no stored adjusted values in DB |
| asyncpg arg limit triggered in production import | HIGH | Emergency hotfix: reduce `_BATCH_SIZE` in import_service.py and recalculate chunk size; no data loss but imports fail for affected users until fix ships |
| Schema field renamed, frontend showing wrong data | MEDIUM | Rollback frontend deploy; add deprecated alias in Pydantic model; fix TypeScript type in next PR |
| Lichess offset formula produces obviously wrong results | LOW | The formula is pure Python in a named function — hotfix is a one-line change with no migration needed |
| Opening risk score inverted (risk = 1 - loss_pct) | LOW | Fix Python computation; no DB changes needed; users see corrected scores immediately after deploy |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Lichess offset formula not documented as approximate | ELO-Adjusted Skill — backend service | Code review: `normalize_lichess_rating()` has a docstring with "approximate" and known limits |
| Opponent color logic inverted | ELO-Adjusted Skill — endgame repository | Unit test: white-user game returns `opponent_rating == black_rating` |
| Wrong population for opponent rating avg | ELO-Adjusted Skill — backend service | Code review: opponent_rating extracted from same entry rows as skill, not a separate unscoped query |
| NULL opponent ratings silently biasing adjustment | ELO-Adjusted Skill — backend service | Test: user with all unrated games returns `elo_adjusted: false`, no error |
| endgame_skill semantics changed without new field | ELO-Adjusted Skill — schema design | `adjusted_endgame_skill` is a new field; `endgame_skill` unchanged in response |
| asyncpg arg limit on new columns | Any game_positions schema phase | CI import test of 500-game batch completes without error after migration |
| Rolling timeline missing pre-fill | ELO-Adjusted Skill — timeline | Switching from 3-month filter to all-time shows no cold-start jump |
| Opening risk conflates draw rate with risk | Opening Risk — formula definition | Berlin Defense (high draw rate) shows low risk; Sicilian (decisive wins) shows appropriate risk |
| Mobile layout not updated | All UI phases | Search for mobile counterpart markup before marking phase complete |

---

## Sources

- Codebase: `app/services/endgame_service.py`, `app/repositories/endgame_repository.py`, `app/models/game.py`, `app/repositories/stats_repository.py`, `app/schemas/endgames.py` — HIGH confidence (direct inspection)
- `.planning/ROADMAP.md` Phase 999.5 backlog spec — HIGH confidence (primary requirements source)
- [NoseKnowsAll: Introducing a universal rating converter for 2024 (lichess.org)](https://lichess.org/@/NoseKnowsAll/blog/introducing-a-universal-rating-converter-for-2024/X2QAH27t) — lichess-to-chess.com offset varies by skill level; not a fixed constant — MEDIUM confidence
- [ChessGoals rating comparison](https://chessgoals.com/rating-comparison/) — Community-observed offset patterns — MEDIUM confidence
- [jk_182: Quantifying Volatility of Chess Games (lichess.org)](https://lichess.org/@/jk_182/blog/quantifying-volatility-of-chess-games/H6MWvX98) — eval-swing volatility does not equate to user-facing risk — MEDIUM confidence
- [asyncpg issue #127: Fails with queries with more than 32768 arguments](https://github.com/MagicStack/asyncpg/issues/127) — 32767 parameter limit confirmed — HIGH confidence
- [Andrew Klotz: Passing the Postgres 65535 parameter limit](https://klotzandrew.com/blog/postgres-passing-65535-parameter-limit/) — chunking and staging table workarounds — HIGH confidence

---
*Pitfalls research for: FlawChess v1.8 — ELO-adjusted metrics, opening risk scores, refined endgame statistics*
*Researched: 2026-04-04*
