# Feature Research

**Domain:** Chess analytics — advanced analytics for v1.8: ELO-adjusted endgame skill, opening risk metrics, refined statistics
**Researched:** 2026-04-04
**Confidence:** HIGH (formula mechanics, competitor feature gaps from direct research); MEDIUM (sharpness/volatility formulas — community blog posts, not academic standard); LOW (lichess/chess.com rating offset exact numbers — empirical, varies by time control and skill level)

---

> This file covers features for v1.8: Advanced Analytics.
> v1.0–v1.7 features are already shipped. Focus: ELO-adjusted endgame skill score, opening risk/volatility metrics, and refinements to existing endgame statistics.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any chess analytics platform must provide when displaying skill or performance scores. Missing or doing these wrong = users distrust the numbers.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Opponent-strength context for skill metrics | Any sports analytics context adjusts for opponent quality. A 70% conversion rate against 800-rated opponents means nothing vs. 1500-rated ones. Users who understand rating systems expect this adjustment. | MEDIUM | The adjustment formula in the milestone spec is straightforward: `raw_score × avg_opponent_rating / reference_rating`. The complexity is cross-platform normalization (lichess vs chess.com offset). |
| Sufficient sample size enforcement | Any aggregate metric (conversion %, recovery %) must have a minimum game count before displaying. Showing "100% conversion rate (1 game)" misleads users. | LOW | Already partially handled by existing conversion/recovery stats. Needs explicit minimum threshold constants and a "not enough data" state in the UI gauge. |
| Trend/timeline for new composite scores | Aimchess, chess.com Insights, and lichess Insights all show metrics over time. A single current score without trend context is less actionable. | MEDIUM | Rolling-window timeline pattern already exists in `endgame_service.py` (`_compute_rolling_series`). New ELO-adjusted skill score needs the same treatment. |
| Hover/tooltip explaining metric calculations | Users encountering "ELO-adjusted skill" or "sharpness score" for the first time need an explanation. Opaque numbers drive churn. | LOW | Info icon + popover pattern already used on the Endgames tab. Reuse it. |

### Differentiators (Competitive Advantage)

Features that go beyond what lichess Insights, chess.com Insights, and Aimchess provide today.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| ELO-adjusted endgame skill score | No public tool adjusts endgame conversion/recovery by the strength of who you faced. A user beating 1800-rated opponents in endgames is more skilled than one beating 1200s. Lichess Insights and Aimchess show raw conversion rates only. | MEDIUM | Formula: `raw_skill × avg_normalized_opponent_rating / 1500`. Normalization requires per-game opponent rating stored at import time (already stored in `game_positions` via `white_rating`/`black_rating` on games). Cross-platform offset: lichess ratings ~200-300 points higher than chess.com at sub-2000 level; a tapering offset is needed when mixing platforms. |
| Opening volatility / sharpness score derived from user's own game data | ChessMonitor has an engine-powered opening explorer; no personal analytics tool surfaces how "wild" your specific opening choices are based on your game history. A high volatility score means your openings lead to high-swing games. | HIGH | Requires per-move eval data (already stored for analyzed games). Volatility = RMS of consecutive expected-score changes: `sqrt(mean((WP[k+1] - WP[k])^2))`. Win probability derived from stored eval/accuracy. Only computable for games with eval annotations — subset of user's games. |
| Opening drawishness from personal game statistics | How often do your specific opening choices lead to draws? No competitor computes this from the user's own position-matched data (they use aggregate database stats instead). FlawChess can compute draw rate at specific board positions via Zobrist hashes. | LOW | Draw rate at a bookmarked/explored position is already computable from existing W/D/L data. The "differentiator" framing is surfacing it as an explicit "drawishness" metric alongside win rate, not just as the D column in a WDL bar. |
| Cross-platform ELO-normalized opponent rating | When a user has games on both chess.com and lichess, comparing opponent ratings is apples-to-oranges. FlawChess is uniquely positioned to normalize these since it ingests both platforms and already associates platform metadata. | MEDIUM | Implement a tapering offset: lichess rating → estimated chess.com equivalent, applied only when mixing platform data. Store a `normalized_opponent_rating` computed at query time or store platform-tagged ratings and normalize in the aggregation layer. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Per-game sharpness score display | Users want to know "how sharp was this game?" | Sharpness requires per-move eval (WDL from engine). Only available for games users previously had analyzed on chess.com/lichess. Showing sharpness for analyzed games only creates a confusing two-tier experience where most games show nothing. | Aggregate sharpness/volatility over a filtered set of games (e.g. per opening position), not per-game display. Show the count of games with eval data used in the calculation. |
| "Risk score" as a single opening recommendation metric | Users want a single number to decide whether an opening is "risky". | Risk is inherently multi-dimensional: volatility (swing size), drawishness (draw rate), and tactical density are distinct properties that can't be collapsed without losing information. A single "risk score" could mislead (e.g. sharp = high risk, but drawish openings like the Petroff are low-volatility AND low-win-rate). | Surface volatility, draw rate, and win rate as separate, labeled metrics. Let users interpret the combination. |
| Running real-time engine analysis to compute sharpness for unanalyzed games | Users would love sharpness for all their games, not just analyzed ones. | Stockfish at depth sufficient for WDL takes 0.5–5 seconds per position. At 40 moves per game, computing sharpness for 500 games = ~10,000 position evaluations. A VPS with shared CPU cannot handle this multi-user. | Use stored eval data from chess.com/lichess APIs where available. Mark analyzed-game-only metrics clearly in the UI. Defer server-side eval to a future compute tier. |
| ELO-adjusted metric for opening statistics (opening "quality by opponent strength") | Logical extension of ELO adjustment from endgames to openings. | Opening performance is inherently more confounded by opponent strength than endgame skill — a stronger opponent is less likely to fall for your preparation. The causal direction is murky. Opening win rates are also well-documented to overstate differences due to rating skew (see D2D4C2C4 lichess blog). | Apply ELO adjustment to endgame metrics first. Evaluate user response before expanding to openings. |
| Automatic lichess ↔ chess.com rating scale conversion using a published formula | Neat feature, precise numbers appeal to analytically minded users. | There is no authoritative universal formula. The offset varies by time control and skill level (~200-300 points sub-2000; ~100 points at 2000-2300; nearly zero at 2400+). Any hardcoded formula will be wrong for edge cases. | Use a conservative single-offset approximation (e.g. subtract 200 from lichess ratings when mixing platforms for the normalization denominator), disclosed transparently to users, and revisable as better empirical data emerges. |

---

## Feature Dependencies

```
ELO-Adjusted Endgame Skill Score (gauge + timeline)
    └──requires──> Raw endgame skill score (already computed: 0.7×conversion + 0.3×recovery)
    └──requires──> Per-game opponent rating (already stored: white_rating/black_rating on games table)
    └──requires──> Platform tag per game (already stored: games.platform)
    └──requires──> Cross-platform rating normalization function (NEW: lichess→chess.com offset)
    └──produces──> adjusted_skill = raw_skill × avg_normalized_opp_rating / 1500

ELO-Adjusted Skill Timeline
    └──requires──> ELO-Adjusted Endgame Skill Score (per above)
    └──requires──> Rolling window implementation (already exists: _compute_rolling_series)
    └──note──> Requires per-game opponent rating to be included in timeline query rows

Opening Volatility Score
    └──requires──> Per-move eval data stored at import (subset of games — analyzed games only)
    └──requires──> Win probability derivation from centipawn eval (NEW: eval→WP conversion function)
    └──produces──> RMS of consecutive WP changes per game, averaged over matching games at a position
    └──depends_on──> Existing Zobrist hash position matching (to scope volatility to specific openings)

Opening Drawishness Metric
    └──requires──> Existing W/D/L data at position level (already computed)
    └──note──> This is NOT a new data computation — it's a UI/surfacing change only
    └──enhances──> Opening Statistics tab (adds draw-rate-focused display alongside win-rate display)

Refined Endgame Stats (conversion/recovery UI improvements)
    └──requires──> Existing conversion/recovery columns (already computed)
    └──may_include──> Threshold recalibration (300cp threshold — already a named constant)
    └──may_include──> Per-endgame-type conversion rates in the performance view (currently aggregate only)

Cross-Platform Rating Normalization
    └──required_by──> ELO-Adjusted Endgame Skill Score
    └──inputs──> games.platform, white_rating/black_rating, user_color
    └──outputs──> normalized_opponent_rating (float, chess.com scale equivalent)
    └──note──> Applied at query/aggregation time, not stored — avoids data denormalization
```

### Dependency Notes

- **ELO adjustment requires opponent rating, not user rating:** The formula uses average opponent rating normalized to a 1500 reference point. The user's own rating is irrelevant to the adjustment — only who they played against matters.
- **Cross-platform normalization is required only when combining platforms:** If the user has games from only one platform, no normalization is needed. The normalization only fires in mixed-platform aggregations.
- **Opening volatility is a strict subset feature:** It can only be computed for games with stored eval data. This is a smaller, filtered computation alongside the main WDL stats — not a replacement. The UI must communicate which subset of games it covers.
- **Drawing rate as a metric is already computable:** The existing WDL data has everything needed. "Drawishness" as a named metric for an opening is a surfacing/framing decision, not a new data pipeline.
- **Refined endgame stats are incremental:** The existing conversion/recovery system (300cp threshold, 6 endgame classes, rolling window timeline) is solid. Refinements are additive — changing presentation, adding breakdowns, adjusting constants — not rewrites.

---

## MVP Definition

### Launch With (v1.8 core)

Minimum viable advanced analytics — enough to make the new features genuinely informative.

- [ ] ELO-adjusted endgame skill score — composite (0.7×conversion + 0.3×recovery) × normalized opponent rating / 1500, displayed in existing performance gauge
- [ ] Cross-platform rating normalization utility — tapering offset (lichess → chess.com equivalent), ~200 points sub-2000, disclosed to users
- [ ] ELO-adjusted skill timeline — rolling window chart alongside or replacing raw endgame_skill timeline
- [ ] Opening drawishness surfacing — draw rate displayed as an explicit labeled metric in Opening Statistics (no new data pipeline needed)

### Add After Validation (v1.8.x)

Features to add once the core advanced analytics are live and users engage with them.

- [ ] Opening volatility score — RMS of WP changes from eval data, scoped to positions with sufficient analyzed games
- [ ] Per-endgame-type ELO adjustment breakdown — show adjusted skill score per rook/minor/pawn endgame class, not only aggregate
- [ ] Refined conversion/recovery presentation — per-type conversion rates in performance view (currently aggregate only)

### Future Consideration (v2+)

- [ ] ELO adjustment for opening statistics — higher complexity, causality concerns, defer until endgame version is validated
- [ ] Server-side eval computation for unanalyzed games — requires a dedicated compute tier, not feasible on current VPS
- [ ] Opponent scouting endgame stats — "how does my opponent handle rook endgames?" — separate scouting feature scope

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| ELO-adjusted endgame skill gauge | HIGH | MEDIUM | P1 |
| Cross-platform rating normalization | HIGH (required for above) | LOW | P1 |
| ELO-adjusted skill timeline | HIGH | LOW (reuses rolling window infra) | P1 |
| Opening drawishness metric | MEDIUM | LOW (no new data pipeline) | P1 |
| Opening volatility score | MEDIUM | HIGH (requires eval→WP pipeline) | P2 |
| Per-type ELO adjustment breakdown | MEDIUM | MEDIUM | P2 |
| Refined conversion/recovery presentation | MEDIUM | LOW | P2 |

**Priority key:**
- P1: Must have for v1.8 launch
- P2: Should have, add when time permits
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | lichess Insights | chess.com Insights | Aimchess | FlawChess v1.8 plan |
|---------|------------------|--------------------|----------|---------------------|
| Opponent-adjusted skill metrics | No — raw percentages only | No — raw percentages only | Compares to players of same rating (benchmark comparison, not per-game adjustment) | ELO-adjusted endgame skill: raw score scaled by avg normalized opponent rating |
| Opening volatility / sharpness | No personal analytics; engine-powered opening explorer on ChessMonitor | No | No | Volatility from stored eval data; subset of analyzed games |
| Opening drawishness | Draw rate visible in opening explorer (aggregate DB, not personal) | Draw rate visible in opening stats | No | Draw rate surfaced as named metric for user's personal positions |
| Cross-platform normalization | N/A — single platform | N/A — single platform | Ingests both platforms; no disclosed normalization | Tapering offset for mixed lichess/chess.com games |
| Timeline for skill metrics | Yes (accuracy over time) | Yes (accuracy trends) | No | Rolling window timeline for ELO-adjusted score (extends existing infra) |

### Key Insight: ELO Adjustment Fills a Real Gap

No chess analytics platform currently adjusts endgame performance metrics by opponent strength. Aimchess benchmarks you against others at your rating level (a cross-user comparison), which is fundamentally different from adjusting your own historical metrics by the strength of opponents you faced. FlawChess's approach — `score × avg_opponent_rating / reference` — is a direct per-user adjustment that doesn't require any cross-user data, preserving data isolation while still accounting for opponent strength.

---

## ELO Normalization Implementation Notes

### Recommended Approach (MEDIUM confidence)

Empirical data from multiple community sources shows a consistent pattern:
- Below 2000: lichess rating ≈ chess.com rating + 200–300 points
- 2000–2300: gap narrows to 100–150 points  
- 2400+: gap largely disappears

**Recommended simple formula for cross-platform normalization:**
```python
def normalize_to_chesscom(rating: int, platform: str) -> int:
    """Normalize a rating to chess.com scale for cross-platform comparisons."""
    if platform == "chess.com":
        return rating
    # lichess: apply tapering offset based on rating level
    if rating <= 1500:
        return rating - 250
    elif rating <= 2000:
        # Linear taper from -250 at 1500 to -150 at 2000
        fraction = (rating - 1500) / 500
        offset = 250 - (fraction * 100)
        return round(rating - offset)
    elif rating <= 2300:
        # Linear taper from -150 at 2000 to -50 at 2300
        fraction = (rating - 2000) / 300
        offset = 150 - (fraction * 100)
        return round(rating - offset)
    else:
        return round(rating - 50)
```

This is a conservative, transparent approximation. The exact numbers are not authoritative — empirical estimates vary. The formula should be disclosed in the UI ("lichess ratings adjusted to approximate chess.com scale") and the constant values should be named constants in the codebase, not magic numbers.

### ELO-Adjusted Skill Formula

```python
# From milestone spec (backlog item 999.5)
# raw_skill = 0.7 * conversion_pct + 0.3 * recovery_pct  (already computed)
# adjusted_skill = raw_skill * avg_normalized_opponent_rating / REFERENCE_RATING
REFERENCE_RATING = 1500  # normalization anchor
adjusted_skill = raw_skill * (avg_normalized_opponent_rating / REFERENCE_RATING)
```

The reference rating of 1500 anchors the adjustment: a player who faces exactly 1500-rated (normalized) opponents gets the same score as raw. Facing stronger opponents inflates the score; weaker opponents deflate it. This is consistent with the performance rating concept (how well did you do given who you faced?).

---

## Opening Risk Metrics: Implementation Notes

### Volatility Formula (MEDIUM confidence — community sources)

Source: Julian's Chess Engine Lab Substack (via jk_182 lichess blog series). The formula computes the RMS of move-by-move expected score changes:

```python
# volatility = sqrt(mean of squared consecutive WP differences)
# WP[k] = win probability after move k (derived from centipawn eval)
def compute_volatility(win_probabilities: list[float]) -> float:
    if len(win_probabilities) < 2:
        return 0.0
    diffs = [win_probabilities[i+1] - win_probabilities[i]
             for i in range(len(win_probabilities) - 1)]
    return (sum(d**2 for d in diffs) / len(diffs)) ** 0.5
```

Win probability from centipawn eval: `WP = 1 / (1 + 10^(-cp / 400))` (standard sigmoid).

**Prerequisite:** Stored eval data per move — only available for games users analyzed on chess.com or lichess. FlawChess already stores `accuracy_white`/`accuracy_black` at game level; per-move eval data is stored in PGN annotations for lichess games with `?evals=true`. Check what's currently stored before designing the pipeline.

### Sharpness (alternative to volatility)

The sharpness formula from the jk_182 lichess blog uses `W^2 + L^2` (squared win and loss probabilities from LC0's WDL output). This requires engine WDL output specifically, not just centipawn eval. Since FlawChess doesn't run an engine, this approach is not directly applicable. Volatility via the RMS formula above is more appropriate given the data available.

### Drawishness

This is simpler than volatility — it's just the draw rate at a position:

```
drawishness = draw_count / total_games_at_position
```

FlawChess already computes this (it's the D in the W/D/L bar). Surfacing it as a named metric in the Opening Statistics tab is a framing/UI decision, requiring no new backend work.

---

## Statistical Methodology Warning

Opening win-rate statistics significantly overstate differences between opening moves when aggregated naively. As documented in the D2D4C2C4 lichess blog post, grouping by average opponent rating (which chess.com and lichess opening explorers do) introduces systematic distortion. FlawChess avoids this problem because it filters by the user's own games and the user's own rating is fixed — the user IS the "single player rating" in the analysis. This is a methodologically superior approach and should be explained to users as part of the opening risk feature documentation.

---

## Sources

- [Performance rating (chess) — Wikipedia](https://en.wikipedia.org/wiki/Performance_rating_(chess)) — HIGH confidence (formula mechanics)
- [Evaluating Sharpness using LC0's WDL — jk_182 / lichess](https://lichess.org/@/jk_182/blog/evaluating-sharpness-using-lc0s-wdl/EXZ3pRoy) — MEDIUM confidence (community blog, not academic standard)
- [Quantifying Volatility of Chess Games — Julian / Chess Engine Lab Substack](https://chessenginelab.substack.com/p/volatility) — MEDIUM confidence (community blog; formula is mathematically sound)
- [Why Opening Statistics Are Wrong — D2D4C2C4 / lichess](https://lichess.org/@/D2D4C2C4/blog/why-opening-statistics-are-wrong/VKNZ1oKw) — MEDIUM confidence (community post, statistically rigorous argument)
- [The Ultimate Chess.com vs Lichess Rating Comparison — attackingchess.com](https://www.attackingchess.com/the-ultimate-chess-com-vs-lichess-rating-comparison/) — LOW confidence (empirical community data; offset varies and is not authoritative)
- [Chess Rating Comparison — ChessGoals.com](https://chessgoals.com/rating-comparison/) — LOW confidence (empirical, good for rough calibration)
- [Aimchess analytics features](https://aimchess.com/) — MEDIUM confidence (feature list from landing page; features may change)
- [ChessMonitor analytics platform](https://www.chessmonitor.com/) — MEDIUM confidence (observed features; no detailed endgame analytics found)

---

*Feature research for: FlawChess v1.8 — advanced analytics (ELO-adjusted endgame skill, opening risk metrics, refined statistics)*
*Researched: 2026-04-04*
