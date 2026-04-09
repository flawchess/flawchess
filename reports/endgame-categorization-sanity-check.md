# Endgame Categorization Sanity Check

**Date:** 2026-03-26
**Dataset:** Hikaru Nakamura, 65,469 games from chess.com
**Methodology:** Compare FlawChess endgame category frequencies against Wikipedia's frequency table (Muller & Lamprecht study), analyze time-control effects, and flag implementation issues.

## 1. Hikaru's Game Distribution

| Time Control | Total Games | Endgame Games | % Reaching Endgame |
|-------------|------------|---------------|-------------------|
| Bullet      | 19,375     | 3,879         | 20.0%             |
| Blitz       | 44,966     | 9,916         | 22.1%             |
| Rapid       | 859        | 215           | 25.0%             |
| Classical   | 269        | 49            | 18.2%             |
| **All**     | **65,469** | **14,059**    | **21.5%**         |

**Observation:** ~78.5% of Hikaru's games never reach our endgame threshold (material < 1500 cp). This is plausible for a super-GM who often wins in the middlegame. Rapid games reach endgame slightly more often (25%), which makes sense — slower time controls allow more careful play and fewer early blunders/resignations.

## 2. Endgame Category Distribution (All Time Controls)

| Category     | Games | % of Endgame | W%   | D%   | L%   | Conversion | Recovery |
|-------------|-------|-------------|------|------|------|------------|----------|
| Minor Piece | 5,390 | 38.3%       | 67.1 | 20.6 | 12.4 | 88.1%      | 68.2%    |
| Rook        | 4,241 | 30.2%       | 68.4 | 19.9 | 11.8 | 89.0%      | 66.8%    |
| Mixed       | 3,687 | 26.2%       | 67.4 | 18.2 | 14.5 | 85.8%      | 68.4%    |
| Pawn        | 467   | 3.3%        | 66.8 | 18.4 | 14.8 | 91.4%      | 57.1%    |
| Queen       | 274   | 1.9%        | 62.0 | 15.7 | 22.3 | 83.8%      | 60.3%    |
| Pawnless    | 0     | 0%          | —    | —    | —    | —          | —        |

## 3. Wikipedia Frequency Comparison

### Mapping Wikipedia Endgame Types to Our Categories

Our classification groups by **piece family** (queen, rook, minor) at the endgame transition point. Pawns alongside a single piece family do NOT create "mixed." Two or more piece families = mixed.

**Key mapping decisions:**

| Wikipedia Type   | Our Category | Reason |
|-----------------|-------------|--------|
| R vs R          | Rook        | Single piece family |
| 2R vs 2R        | Rook        | Still only rooks |
| RB vs RN        | Mixed       | Rook + minor = 2 families |
| R vs B          | Mixed       | Rook + minor = 2 families |
| B vs N          | Minor Piece | Single family (minor) |
| K+pawns vs K    | Pawn        | Only pawns |
| Q vs Q          | Queen       | Single family |
| Q vs R          | Mixed       | Queen + rook = 2 families |

### Aggregated Comparison

Wikipedia percentages normalized to sum to 100% (the original table covers ~53% of all endgame positions):

| Category     | Hikaru (FlawChess) | Wikipedia (normalized) | Difference |
|-------------|-------------------|----------------------|------------|
| Minor Piece | **38.3%**         | 18.0%                | +20.3 pp   |
| Rook        | **30.2%**         | 26.1%                | +4.1 pp    |
| Mixed       | **26.2%**         | 45.5%                | -19.3 pp   |
| Pawn        | 3.3%              | 5.8%                 | -2.5 pp    |
| Queen       | 1.9%              | 4.5%                 | -2.6 pp    |

### Why the Discrepancy? The Threshold Effect

The large gap — especially Minor Piece overrepresented (+20 pp) and Mixed underrepresented (-19 pp) — is **explained by our ENDGAME_MATERIAL_THRESHOLD of 1500 cp:**

1. **Symmetric mixed endgames are above 1500 cp and never trigger endgame entry.**
   - RB vs RN = 500+300+500+300 = 1600 cp (above threshold)
   - RN vs RN = 500+300+500+300 = 1600 cp (above threshold)
   - KRBP vs KRNP = 1900 cp (above threshold)

2. **These positions simplify further before crossing the threshold.** A game that transitions through RB vs RN (1600 cp) and then simplifies to B vs N (600 cp) is classified at the B vs N entry point — i.e., **minor piece**, not mixed.

3. **Queen vs Queen (1800 cp) is ALWAYS above the threshold.** This means our "queen" category only captures asymmetric endgames like Q vs pawns (900-1400 cp). The most common queen endgame (Q vs Q at 1.87% in Wikipedia) is excluded entirely.

4. **Our "mixed" category only captures asymmetric multi-family positions below 1500 cp:**
   - KRB vs K (800 cp) — mixed
   - KQ vs KR (1400 cp) — mixed
   - KR vs KB (800 cp) — mixed

**Verdict:** The discrepancy is not a bug — it's a direct consequence of our threshold-based entry point classification. We measure "what simplified endgame did you actually play," not "what piece configuration occurred during the game." This is a defensible design choice, but users should understand this nuance.

### Recommendation: Consider the Threshold Trade-off

The 1500 cp threshold was recently lowered from 2600 cp (which captured late middlegame). The current value is good for capturing "true" endgames. However, it creates a blind spot:

- **Captured well:** R vs R, B vs N, KP vs K — classic endgames
- **Missed entirely:** Q vs Q, RB vs RN, RN vs RN — material-rich endgames that many players think of as "endgames"
- **Edge case:** Games that simplify from mixed to single-family are classified by the simpler form

If the goal is to match player intuition about "endgame types," a higher threshold (~2000-2200 cp) would capture more mixed and queen endgames. But this would also introduce noise from late middlegame positions. The current 1500 is a reasonable conservative choice.

## 4. Time Control Analysis

### Category Distribution by Time Control

| Category     | Bullet | Blitz | Rapid  | Classical |
|-------------|--------|-------|--------|-----------|
| Minor Piece | 37.7%  | 38.5% | 40.9%  | 46.9%     |
| Rook        | 30.0%  | 30.2% | 31.2%  | 32.7%     |
| Mixed       | 26.3%  | 26.3% | 25.1%  | 14.3%     |
| Pawn        | 3.9%   | 3.1%  | 1.9%   | 4.1%      |
| Queen       | 2.2%   | 1.9%  | 0.9%   | 2.0%      |

**Observation:** Category distribution is remarkably stable across bullet and blitz. Minor piece and rook endgames dominate at all time controls. Rapid and classical samples are too small for reliable conclusions (215 and 49 games respectively).

### Draw Rates by Time Control

| Category     | Bullet D% | Blitz D% | Rapid D% |
|-------------|-----------|----------|----------|
| Minor Piece | 17.0      | 21.6     | 38.6     |
| Rook        | 12.9      | 22.2     | 40.3     |
| Mixed       | 15.5      | 18.8     | 38.9     |
| Pawn        | 17.8      | 19.1     | 0.0*     |
| Queen       | 9.5       | 18.2     | 50.0*    |

*Sample sizes too small (4 and 2 games).

**Finding:** Draw rates roughly double from bullet to blitz and double again to rapid. Rook endgame draws show the clearest pattern: 12.9% (bullet) -> 22.2% (blitz) -> 40.3% (rapid). This is consistent with chess theory — rook endgames are known for their drawish tendencies, which manifest more in slower play.

### Recovery Rates: Do We See More Recoveries in Bullet?

| Category     | Bullet Recov% | Blitz Recov% | Rapid Recov% |
|-------------|--------------|-------------|-------------|
| Minor Piece | 69.7         | 68.2        | 46.7        |
| Rook        | 60.5         | 69.4        | 63.6        |
| Mixed       | 63.7         | 70.2        | 72.0        |
| Pawn        | 55.6         | 57.9        | —           |
| Queen       | 62.9         | 58.9        | —           |

**Surprising finding: Recovery rates are NOT higher in bullet.** In fact, for rook and mixed endgames, blitz recovery rates are higher than bullet (69.4% vs 60.5% for rook, 70.2% vs 63.7% for mixed). This may be because:

1. **Bullet is too fast for recovery.** Even a super-GM has limited time to find saving resources with <1 minute on the clock.
2. **Blitz is the sweet spot for comebacks.** Enough time to find tricks, but opponents still make inaccuracies.
3. **Hikaru effect.** As a speed chess specialist, Hikaru may convert advantages more cleanly in bullet, reducing his opponents' recovery chances (and symmetrically, his own recoveries when behind).

### Win Rates by Time Control (Hikaru-Specific)

| Category     | Bullet W% | Blitz W% | Rapid W% |
|-------------|-----------|----------|----------|
| Minor Piece | 70.6      | 66.1     | 47.7     |
| Rook        | 73.6      | 66.6     | 52.2     |
| Mixed       | 68.2      | 67.5     | 46.3     |
| Queen       | 69.0      | 58.8     | 50.0*    |

**Hikaru wins more in faster time controls.** His bullet win rate in rook endgames (73.6%) is 7pp higher than blitz (66.6%) and 21pp higher than rapid (52.2%). This confirms the well-known pattern that stronger players benefit more from faster time controls.

## 5. Implementation Issues Found

### 5.1 UI Filter Bug (Observed)

**Severity:** Needs investigation

When clicking the "Bullet" time control filter button on the Endgames page, the displayed statistics did not change from the "all" baseline. The API correctly returns different data per time control (verified via direct API calls), so the issue is in the frontend filter state management.

The filter uses a toggle pattern where clicking a button when all are active deselects that one button (e.g., clicking Bullet with all selected should show everything EXCEPT bullet). This means the numbers should change from 14,059 total to ~10,180 total. They didn't. The code flow (FilterPanel -> useState -> useDebounce -> useEndgameStats -> TanStack Query) looks correct on inspection. This warrants manual testing and debugging.

### 5.2 Missing "Total Games" Context

**Severity:** High (UX gap)

The endgame stats API (`EndgameStatsResponse`) only returns categorized endgame games. There is no field for:
- Total games in library
- Total games reaching endgame
- Percentage of games that reach endgame

Users see "5,390 minor piece endgame games" with no context that this represents only 8.2% of their total 65,469 games. Adding a summary line like *"14,059 of 65,469 games (21.5%) reached an endgame phase"* would significantly improve comprehension.

### 5.3 Pawnless Category: Empty but Displayed?

**Severity:** Low

The "pawnless" category (bare kings K vs K) had 0 games for Hikaru. This is expected — games with bare kings would be auto-drawn. The backend handles this correctly (returns the category with zeros). The frontend should gracefully show or hide zero-game categories. Currently, pawnless is not visible in the UI (possibly filtered out by sorting — 0 games sorts last, and if the chart only shows top N, it may be cut).

### 5.4 No Minimum Sample Size Warning

**Severity:** Medium

Categories with very small sample sizes (e.g., Classical has 1 queen endgame game showing 100% win rate) are displayed without any statistical health warning. Consider adding a "small sample" indicator when a category has fewer than, say, 10 games.

### 5.5 Queen vs Queen Endgames Excluded by Threshold

**Severity:** Medium (design limitation)

Q vs Q (the most common queen endgame at 1.87% in literature) has material count of 1800 cp, which is above the 1500 threshold. Our "queen" category captures only asymmetric queen endgames (Q vs pawns, etc.). This means the queen category is significantly underrepresented compared to player expectations. Worth noting in the info tooltip or documentation.

### 5.6 Data Truncation in API Responses

**Severity:** Low (tooling issue, not user-facing)

When fetching multiple time controls in a single JavaScript call via the Chrome extension, response data was truncated at ~1000 characters. This is a tooling limitation of the Chrome MCP bridge, not a backend issue. The API returns complete data when called individually.

## 6. Overall Assessment

### Is Our Categorization Plausible?

**Yes, with caveats.** The category ranking (Minor Piece > Rook > Mixed > Pawn > Queen) differs from the Wikipedia reference (Mixed > Rook > Minor Piece > Pawn > Queen), but this is fully explained by our 1500 cp threshold design. At this threshold, symmetric multi-family endgames have already simplified into single-family endgames, shifting games from "mixed" into "minor piece" and "rook."

The relative ordering of Rook > Pawn > Queen and the approximate magnitudes are consistent with chess theory. The time-control patterns (more draws at slower speeds, higher Hikaru win rate at faster speeds) are consistent with expectations.

### Do We Need Adjustments?

| Adjustment | Recommendation | Priority |
|-----------|---------------|----------|
| Raise threshold to ~2000 cp | **Consider but don't rush.** Would capture Q vs Q and symmetric mixed endgames. Trade-off: also captures late middlegame noise. | Medium |
| Add "total games" context | **Yes.** Essential for user comprehension. | High |
| Add sample-size warnings | **Yes.** Prevents misinterpretation of small samples. | Medium |
| Note Q vs Q exclusion | **Yes.** Add tooltip explaining what the threshold captures. | Low |
| Fix time-control filter UI | **Yes.** Investigate and fix the filter state update issue. | High |

### Recommended Follow-Up: Test With a Weaker Player

Hikaru is not representative of the average chess player. His 67-70% win rate across all endgame types reflects elite skill. Key questions for weaker players:

1. **Does the endgame reach rate increase?** Weaker players may resign less early, leading to more games reaching the endgame phase.
2. **Are recovery rates more balanced?** Hikaru's consistently high recovery rates (~60-70%) may be anomalous.
3. **Is the category distribution similar?** The distribution should be roughly consistent across skill levels if the classification is correct, though weaker players may have more pawn endgames (from piece trades).
4. **Does the "mixed" category grow?** If weaker players simplify less cleanly, they might enter the endgame phase with more piece families still on the board.

Importing games from a 1200-1500 rated player would provide a valuable contrast dataset.
