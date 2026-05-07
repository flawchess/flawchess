---
id: SEED-011
status: dormant
planted: 2026-05-07
planted_during: /gsd-explore session on Openings tab chart layout (Moves vs Stats vs Insights)
trigger_when: phase 80.1 (transpositions in Move Explorer + Opening Insights) has shipped
scope: quick-task (`/gsd-quick`) — single-phase UI rework
---

# SEED-011: Add score bullet chart to Openings → Stats and Insights tabs

## Decision

Show **WDL + Score bullet + Eval bullet** in the Stats and Insights tabs of the Openings page.
Moves tab keeps its current **WDL + Score bullet** layout (no eval bullet there).

| Tab | WDL | Score bullet | Eval bullet |
|---|---|---|---|
| Moves | yes | yes (current) | no (current — keep) |
| Stats | yes | yes (current) | **yes — ADD** |
| Insights | yes | yes (current) | **yes — ADD** |

## Why

- **Score and eval are complementary, sometimes contradictory** — e.g. score is poor but eval at MG entry is ~0.0. That contradiction is the highest-value diagnostic moment: "the opening isn't the problem, post-opening play is." Surfacing both lets the user see this.
- **Moves tab stays as-is** — the user is staring at a specific position. Score = outcomes from this exact position. Eval at MG entry is averaged across descendant positions, so it's conceptually one level removed from what's on the board. Less coherent there.
- **Stats and Insights are aggregate views** — each card represents an opening (or a finding within one), not a specific position. Both diagnostic dimensions matter. In Insights, the finding's headline is already score-anchored ("Score 38% after [move]"), so the eval bullet acts as the contradiction-detector that makes the finding actionable.

## Implementation notes (for the eventual `/gsd-quick`)

### Bullet bar color: neutral light grey (NOT zone-colored)

The bar itself should render in **light grey** (high contrast against the dark zone bands behind it). Currently the bar is filled with the zone color of where it lands, which makes the bar do double duty (position + verdict). Following Tufte / Stephen Few bullet-chart conventions, the bar is a neutral data indicator and the **colored zone bands behind it** carry the qualitative verdict. Cleaner separation, easier to read both bullets side by side.

This is a change to the shared `MiniBulletChart` component (or a new `barColor='neutral'` mode). The Endgame surfaces that use `MiniBulletChart` today should be checked — if they expect the colored-bar look, gate the change behind a prop rather than flipping the default.

### Do NOT tint the eval bar a different color from the score bar

Tempting idea: render eval bullet's bar in a different hue (e.g. steel-blue) so it visually telegraphs "engine." Rejected because:
- Tinting one bar but not the other subtly signals "the colored one matters more" — both metrics are equally valid.
- Color budget is finite; it's already spent on zone semantics (danger/neutral/good). Spending it again on metric-type dilutes both signals.
- Iconography + row labels + tick labels carry the score/eval distinction with plenty of channel headroom.

If a steel-blue "engine flavor" accent feels worth keeping, apply it to the **Cpu icon glyph itself**, not the bar. That tints the meta-label, leaves the data neutral.

### Distinguishing score from eval bullets — the actual channel inventory

Beyond icons, the score and eval rows already differ along several axes — they don't all need to be loud, but they're additive:

- **Row icon**: `Cpu` for eval (precedent: commit 450d9bb0). Score row icon: `User` / `Users` / `Trophy` (pick whichever the design system already uses for "your performance").
- **Row label**: "Score" vs "Engine eval" or "Eval".
- **Value format**: "38%" vs "+0.2" — already differs.
- **Baseline tick label**: "50%" vs "0.0" / per-color asymmetry baseline — already differs.
- **CI rendering scale**: percent vs pawns — already differs intrinsically.
- **Fixed row order**: score above eval, always. Predictable scanning.

That's six channels. The bar color does not need to be the seventh.

### Card border-left color: score-zone (across all three tabs)

Today the cards disagree:
- `OpeningStatsCard.tsx`: `borderLeftColor = hasMgEval ? evalZoneColor(opening.avg_eval_pawns) : 'transparent'` (eval-zone)
- `OpeningFindingCard.tsx`: `borderLeftColor = scoreZoneColor(finding.score)` (score-zone)

**Decision: standardize on score-zone for the border-left.** Reasons:
- Consistency across Moves, Stats, Insights tabs — Moves rows already tint by score zone.
- Score is the "what actually happened" metric — that's what users scan for in a list.
- Eval doesn't lose its channel: it still has its own bullet row, Cpu icon, and the eval-text color tinting (line 73 in `OpeningStatsCard.tsx`).

This means changing `OpeningStatsCard.tsx` to use `scoreZoneColor` for the left border (using the same reliability gating as the score bullet uses, so a low-confidence score doesn't paint a misleading border).

### Drop the "Score X% after [move]" prose in Insights cards

`OpeningFindingCard.tsx` currently renders a prose line like "Score 38% after 2.c4" (lines 106–113). With a dedicated score bullet row, the "Score 38%" half becomes redundant (value is shown in the bullet row's value text). The "after 2.c4" half is **not** redundant — it's the move anchor in textual form, and the only other place it surfaces is as an arrow on the mini board.

Refactor:
- Drop the "Score X%" prefix entirely.
- Render the move anchor (e.g. "after 2.c4") as a **small caption directly under the miniboard** — keeps it tightly co-located with the arrow it describes, so the visual + textual move anchor read as a single unit.
- This frees a row of vertical space, which the new score bullet row consumes.

### Card layout: use the mobile layout on desktop too

Today's desktop card likely puts the miniboard on one side and the stats column on the other (side-by-side), which constrains horizontal width for the bullet rows. With three bullet rows now in play, that horizontal squeeze hurts.

**Decision: adopt the mobile layout on desktop as well** — opening name spans the full card width on top, miniboard sits below it, then the bullet rows stack vertically beneath the miniboard's caption. This gives the bullet rows the full card width on every viewport and unifies the responsive code path (one layout instead of two).

Implications:
- Cards become taller and narrower-feeling on desktop. Confirm this still feels reasonable on the Stats and Insights tab grids (likely fine — Insights already uses 1-column or narrow-column layouts).
- The "always apply changes to mobile too" CLAUDE.md rule becomes easier to honor because there's now only one card layout to maintain.

### Three-row bullet layout

- Stack vertically on every viewport (was already mobile-first; now mobile-only is the canonical form).
- Each bullet row: icon + label + value (text) + bullet bar (neutral light grey bar over colored zone bands).
- Keep row height tight; three short rows is workable.
- Confirm the shared `MiniBulletChart` component handles the smaller vertical-stack rendering, or accept a `compact` prop.

### Files likely touched

- `frontend/src/components/stats/OpeningStatsCard.tsx` — add score bullet row, switch border-left to score-zone, gate by score reliability
- `frontend/src/components/insights/OpeningFindingCard.tsx` — add score bullet row (eval bullet already there), drop the "Score X%" prose prefix while preserving the "after [move]" anchor
- `frontend/src/components/charts/MiniBulletChart.tsx` — neutral light-grey bar mode (default or prop-gated), optional icon slot for the leading row glyph
- `frontend/src/lib/scoreBulletConfig.ts` / `frontend/src/lib/openingStatsZones.ts` — verify zone-band rendering still works with neutral bar
- `frontend/src/pages/Openings.tsx` — wire score data through to Stats card if not already passed
- Tests: `OpeningStatsCard.test.tsx`, `MiniBulletChart.test.tsx`, related visual snapshot tests if any
- Audit other `MiniBulletChart` consumers (Endgame surfaces — `EndgamePerformanceSection`, `EndgameScoreGapSection`, `EndgameClockPressureSection`) to confirm the neutral-bar change is gated and doesn't regress them

## Out of scope

- Reworking the Moves tab — explicitly stays as-is (WDL + Score only).
- Changing the zone color palette or score/eval domains.
- Adding a third metric or new chart type.

## Trigger

Once phase 80.1 ships and Adrian wants to schedule this, invoke `/gsd-quick` with this seed as context.
