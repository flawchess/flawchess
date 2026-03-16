# Feature Research

**Domain:** Chess opening explorer + analysis UI restructuring
**Researched:** 2026-03-16
**Confidence:** HIGH (established patterns across lichess, chess.com, openingtree.com; confirmed by official docs and source code)

---

> This file covers features for v1.1: Move Explorer and UI restructuring.
> v1.0 features (import, position analysis, bookmarks, game cards, stats) are already shipped.
> Dependencies on v1.0 are noted where relevant.

---

## Feature Landscape

### Table Stakes (Users Expect These)

These are features that any opening/move explorer is expected to have. Missing them makes the product feel incomplete to chess players familiar with lichess Explorer or chess.com Game Explorer.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Move table showing next moves with game count | Every explorer (lichess, chess.com, 365chess) shows this as the primary data | LOW | Query game_positions WHERE full_hash = :current_hash, GROUP BY move_san |
| W/D/L stats per move row | Standard since at least 2015; users explicitly look for this | LOW | Aggregate from existing games.result data; same logic as position-level stats already built |
| Stacked W/D/L bar per move row | Visual pattern users are trained on from chess.com and lichess; text percentages alone feel bare | LOW | CSS bar, same component used in existing position stats panel |
| Click a move row to advance position | Core interaction: click = play that move on the board | LOW | Dispatch move to board state; board already supports this interaction |
| Total game count for current position | Shows sample size; users judge reliability of stats from this | LOW | Sum of all move rows |
| Sorted by frequency (most common first) | Default sort in all explorers; users expect most popular first | LOW | ORDER BY game_count DESC |
| Empty state when no games reach position | Users play into uncommon lines; "no games found" is expected feedback | LOW | Simple conditional render |
| Play moves on board updates explorer | Bidirectional: board drives explorer and explorer drives board | LOW | Board state already drives position query; same mechanism |
| Color filter (as white / as black) | Chess results differ drastically by side; this is the most-used filter | LOW | Already exists in v1.0 filter sidebar; reuse |
| Time control filter | Already in v1.0; users expect consistency across all views | LOW | Reuse existing filter sidebar |
| Reset to starting position | Users need to return to start without page reload | LOW | Clear move history, reset board to initial FEN |
| Dedicated Import page (not modal) | Import from a modal is cramped; power users want a full page with status history and per-platform controls | MEDIUM | Move existing modal content to route /import; show import history, per-platform last-sync timestamps |

### Differentiators (Competitive Advantage)

These align with the core Chessalytics value proposition: position-based analysis of your own games, independent of opening name.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "As white" / "as black" W/D/L split in move table | Lichess explorer shows global W/D/L regardless of who you are; Chessalytics shows YOUR personal result from each move | LOW | Filter game_positions by user's color in the query |
| Move explorer scoped to the user's imported games only | Lichess shows master/all-platform stats; chess.com shows master DB; neither gives club players personal position stats | LOW | Already the architecture — user_id in game_positions ensures this |
| Move explorer shares filter sidebar with Games and Statistics sub-tabs | No other personal chess tool offers a unified filter that updates all views simultaneously | MEDIUM | Shared filter state (React context or URL query params) propagated to all three sub-tab queries |
| Move explorer works for any position reachable from initial position (not just named openings) | Lichess and chess.com explorers degrade past move 20-25 for personal games; Chessalytics has no such limit since it is querying your own indexed positions | LOW | The Zobrist hash approach handles all positions equally; no special handling needed |
| Sub-tab navigation within Openings (Move Explorer / Games / Statistics) | Chess.com analysis has tabs but they are not scoped to a single position+filter state; our tabs share both position and filter | MEDIUM | React Router sub-routes or tab state; position and filter must persist across tab switches |
| SAN stored in game_positions for direct move lookup | Enables single-query move explorer without PGN replay at query time | MEDIUM | Schema change: add move_san column to game_positions; populate at import; add index |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Engine evaluation per move in explorer | Users see it on lichess/chess.com and want it | Requires Stockfish process management (subprocess, async queuing), CPU cost scales with concurrent users, and immediately anchors user expectations toward full engine analysis (blunder detection, evaluation bar). Scope explosion risk. | Defer to v2+. The personal W/D/L data is the differentiator; engine eval undercuts it by making users focus on "best move" instead of "my move". |
| Opening name / ECO code label in explorer | Feels orienting; lichess shows it | Requires maintaining an opening book database or accepting platform naming inconsistency — the exact problem Chessalytics exists to solve. Adds false authority to a naming system the product rejects. | Show move number and SAN only. Position speaks for itself. |
| Link out to sample games from explorer move rows | Nice for context; chess.com shows "notable games" below move table | The Games sub-tab already shows matched games for the position. Duplicating in the move explorer creates two sources of truth. | After clicking a move in explorer (advancing position), switch to Games sub-tab to see games. |
| Tree / branching visualization (visual opening tree) | Openingtree.com does this; looks impressive | Rendering a tree of depth 5+ with W/D/L per branch is a React render performance problem. For club-level game counts (hundreds to low thousands), many branches have 1-2 games and produce misleading statistics. | Flat move table is faster to read, easier to implement, and more honest about sample sizes. |
| Percent score (chess points / max points) instead of W/D/L | Openingtree shows win% = (wins + 0.5×draws) / total | Hides the draw rate, which is important context. A 50% score with 100% draws is very different from 50% wins 0% draws. | Show W, D, L as separate columns. |
| Infinite depth exploration (follow any line arbitrarily deep) | Natural behavior: click move, click next move, explore ad hoc | Already supported by the architecture — each position has a hash and the query works at any depth. Not a feature to avoid; just not special-cased. | This works automatically from the move table + board interaction. No additional work needed. |
| Import status as a modal | Current v1.0 uses modal | Modals block navigation; long imports (100s of games) need a persistent UI. Users want to import and then browse bookmarks. | Dedicated /import page. |

## Feature Dependencies

```
[SAN stored in game_positions] (schema + import change)
    └──enables──> [Move explorer table] (single DB query, no PGN replay)

[Move explorer table]
    └──requires──> [Board state drives position hash] (already exists in v1.0)
    └──requires──> [W/D/L aggregation per position] (already exists in v1.0)

[Shared filter sidebar]
    └──requires──> [Sub-tab navigation] (Openings → Move Explorer / Games / Statistics)
    └──enables──> [Consistent filter state across tabs]

[Sub-tab navigation]
    └──requires──> [Merged Openings tab] (replaces separate Analysis + Games tabs)
    └──requires──> [React state or URL param management for active tab]

[Dedicated Import page]
    └──replaces──> [Import modal] (modal can be removed after page exists)
    └──requires──> [Route /import] (new React Router route)

[Move explorer click-to-navigate]
    └──requires──> [Board accepts programmatic move input] (already exists in v1.0)
    └──enhances──> [Games sub-tab] (navigating to a position in explorer shows games for that position)
```

### Dependency Notes

- **SAN in game_positions requires DB wipe**: PROJECT.md already records "DB wipe for v1.1 — No migration needed — reimport after schema change." This is the accepted approach. The SAN column is the only schema-blocking dependency for the move explorer.
- **Sub-tab navigation must preserve position + filter state**: If the user is at e4 e5 Nf3 with blitz filter, switching from Move Explorer to Games tab must show games from that same position with that same filter. This is a React state design constraint, not a backend constraint.
- **Shared filter sidebar is additive**: The filter sidebar already exists in v1.0 for the analysis view. Sharing it across sub-tabs is a state management refactor, not a new backend feature.
- **Dedicated Import page does not block any other v1.1 feature**: It can be built independently and in any order relative to the move explorer.

## MVP Definition

### Launch With (v1.1)

These are the features that constitute the v1.1 milestone as defined in PROJECT.md.

- [ ] Add move_san column to game_positions, populate at import — required for performant move explorer queries
- [ ] Move explorer: flat move table showing SAN, game count, W/D/L counts and %, stacked bar visual
- [ ] Move explorer: click row advances board to that move, table refreshes for new position
- [ ] Move explorer: reset to start position button
- [ ] Sub-tab structure: Openings tab splits into Move Explorer / Games / Statistics sub-tabs
- [ ] Shared filter sidebar: single filter state drives all three sub-tabs
- [ ] Dedicated Import page at /import, replacing import modal

### Add After Validation (v1.x)

- [ ] Sort options in move explorer (by frequency, by win rate, by game count) — low complexity but adds noise for v1.1
- [ ] "Opponent's next moves" toggle — show what opponents played from this position, not just the user's moves
- [ ] Position URL sharing — encode current position as URL param so users can share specific analyses

### Future Consideration (v2+)

- [ ] Engine evaluation per move — requires Stockfish integration and multi-user queuing
- [ ] Opening tree visualization — visual branching tree; complex render, misleading at small sample sizes
- [ ] Rating-based filter — filter games by opponent Elo band; dilutes already-small samples
- [ ] Time-series win rate chart — requires data density to be meaningful; V2 once user game volumes are understood

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SAN in game_positions (schema + import) | HIGH (blocks everything else) | LOW | P1 |
| Move explorer table with W/D/L per move | HIGH | LOW | P1 |
| Click-to-navigate in move explorer | HIGH | LOW | P1 |
| Stacked W/D/L bar per move | MEDIUM | LOW | P1 |
| Sub-tab navigation (Move Explorer / Games / Statistics) | HIGH | MEDIUM | P1 |
| Shared filter sidebar across sub-tabs | HIGH | MEDIUM | P1 |
| Dedicated Import page | MEDIUM | MEDIUM | P1 |
| Reset board button in explorer | MEDIUM | LOW | P1 |
| Sort options in move explorer | LOW | LOW | P2 |
| Opponent moves toggle | MEDIUM | MEDIUM | P2 |
| Position URL sharing | LOW | MEDIUM | P3 |
| Engine evaluation per move | HIGH (users want it) | HIGH (scope risk) | P3 |

**Priority key:**
- P1: Must have for v1.1 launch
- P2: Add after core is stable
- P3: Future consideration

## Competitor Feature Analysis

| Feature | lichess Explorer | chess.com Game Explorer | openingtree.com | Chessalytics v1.1 |
|---------|-----------------|------------------------|-----------------|-------------------|
| Move table with game count | Yes (global DB) | Yes (master DB) | Yes (personal games) | Yes (personal games) |
| W/D/L per move | Yes (global) | Yes (master) | Yes (personal, combined score) | Yes (personal, split W/D/L) |
| Stacked W/D/L bar | Yes | Yes | No (text only) | Yes |
| Click move to advance | Yes | Yes | Yes | Yes |
| Personal games database | Yes (player mode) | Yes (my games) | Yes (primary feature) | Yes (primary feature) |
| Position-independent of opening name | No (ECO-named) | No (ECO-named) | No (move-order tree) | Yes (Zobrist hash) |
| Sub-tabs (explorer/games/stats) | No | Separate pages | No | Yes (unified) |
| Shared filter across views | No | No | Partial | Yes |
| Own-pieces-only matching | No | No | No | Yes (v1.0 inherited) |
| Dedicated import page | n/a | n/a | n/a | Yes (v1.1) |
| Engine eval per move | Yes (optional) | Yes | No | No (deferred) |
| Opening name labels | Yes | Yes | No | No (anti-feature) |

## Sources

- [lichess opening explorer source (lila-openingexplorer)](https://github.com/lichess-org/lila-openingexplorer) — confirms move, white/draws/black columns
- [openingtree/openingtree GitHub](https://github.com/openingtree/openingtree) — confirms personal game move tree with W/D/L
- [chess.com Game Explorer help](https://support.chess.com/en/articles/8708732-how-do-i-use-the-game-explorer) — confirms move list, click-to-navigate, stacked bar, notable games panel
- [chess.com Game Explorer overview](https://support.chess.com/en/articles/8615183-what-is-the-game-explorer) — confirms master DB, personal games mode, dropdown database selection
- [lichess forum: opening explorer usage](https://lichess.org/forum/general-chess-discussion/how-do-i-use-the-opening-explorer) — confirms 3-part info: frequency, win rate, engine
- [chess.com forum: percentage bar explanation](https://www.chess.com/forum/view/help-support/what-is-the-bar-with-the-percentages) — confirms white/gray/black stacked bar pattern

---

*Feature research for: Chessalytics v1.1 — Move Explorer and UI Restructuring*
*Researched: 2026-03-16*
