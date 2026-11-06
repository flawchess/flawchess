---
id: SEED-261106-gw8
status: dormant
planted: 2026-11-06
planted_during: v2.27, phase 244 (/gsd-explore session)
trigger_when: when Train page navigation, the Train landing, or mastered/parked puzzle browsing is next prioritized
scope: phase (frontend routing and layout split, plus one backend list endpoint)
---

# SEED-261106-gw8: Train subnav split (Today / Leaderboard / Archive)

## Why This Matters

The Train landing stacks the streak card, schedule, leaderboard and pool tiles in one column, and the mastered and parked puzzles are only counts: users can't see or open them. Splitting the page gives each part room and turns those counts into a browsable archive. It is also the base for the later retry feature (SEED-261106-q92) and a Stats tab.

## When to Surface

**Trigger:** when Train page navigation, the Train landing, or mastered/parked puzzle browsing is next prioritized.

## Scope Estimate

**One phase.** Routing and layout split, new card and list UI, and one backend list endpoint. No migration expected.

## Decisions

### Tabs

| Tab | URL | Content |
|---|---|---|
| Today | `/train` (must keep working for reminders, PWA and nav) | Streak card with Start button, rank line, full schedule card |
| Leaderboard | `/train/leaderboard` | Existing `TrainLeaderboardCard` |
| Archive | `/train/archive` | Mastered and Parked puzzle lists |

Archive keeps its name permanently. Statistics get a separate fourth **Stats** tab later rather than a rename. Library already has four tabs, and "Stats" matches the label on Openings and Endgames.

### Today

- **Rank line:** add something like "#4 this week" to the streak card, linking to Leaderboard. Moving the leaderboard off the landing reduces exposure, and it may be a motivator.
- **Schedule card:** remove the collapsible and show the full card. The collapsed summary ("Mo–Fr · 6 puzzles · 16:00") goes away with it. The "Next session" line on the completed state must remain.
- **Points today:** this tile leaves with `TrainStatsCard` and needs a new home, probably the streak card.

### Archive

- **Toggle:** Mastered / Parked with counts and the existing explainer popovers in the labels, replacing `TrainStatsCard`.
- **List:** 20 per page with the existing `Pagination` component, newest first. Tab and page live in the URL so browser back from Analysis returns to the same spot.
- **Filters:** none in v1. A tactic motif filter is the first candidate later.
- **Card:** a new small `TrainPuzzleCard` built on `LazyMiniBoard`, not `FlawCard`, which draws played-move and best-move arrows and carries severity and tag UI.
- **Card layout:** horizontal, board left, details and buttons right. One column on phones, two on desktop, matching the Library Flaws tab.
- **Card content:** the pre-mistake position with no arrows on both Mastered and Parked, because retry is planned. Analyze button via `buildGameAnalysisUrl(game_id, ply)`. Reserve space for a later Retry button.

### Later Stats tab candidates

- Split of puzzles across mastered, parked and active
- Weakest tactic motifs among parked puzzles
- Mastered mistakes no longer repeated in real games

Never list active puzzles with an Analyze button: seeing the solution before the next review defeats spaced repetition.

## Implementation Traps

- **Train page side effects:** `TrainPage` calls `POST /train/sessions` on mount (`useTrainSession`) and starts the grading engine (`useTrainGradingEngine`). Leaderboard and Archive must not sit under it, or viewing them would create a session and load the engine. Use a thin layout with those hooks moved to the Today route.
- **Subnav visibility:** hide it during solve, score and restored-reveal views, because the phone board is sized to the viewport.
- **Medal dialog:** `TrainMedalDialogHost` should move to the layout, or a deep link to Leaderboard won't show medals.
- **Sort order:** `drill_items` has no `mastered_at` or `parked_at`. Sort by the latest `drill_solves.solved_at` per puzzle, which assumes status only changes on a solve. Verify all write paths during planning.
- **Count mismatches:** `mastered_count` and `parked_count` count `drill_items` without joining `game_flaws`, and reclassified flaws can lose their `game_flaws` row while the drill item stays (lazy eviction). A list using an inner join would show fewer cards than the tab count, so the list must tolerate a missing flaw row or the counts must change.
- **Ownership:** mastered and parked rows are always the user's own games (filler and herring solves have no SR bookkeeping), so Analyze via `game_id` is safe.
- **Empty states:** a guest with no games gets empty lists. Leaderboard and Archive need their own empty states, since `TrainEmptyBody` only covers the landing.
- **Project rules:** URL-routed tabs need no Umami event because their pageview covers it; the Mastered/Parked toggle does if it isn't URL-routed. Add `data-testid` to all new interactive elements. Apply the subnav to desktop and mobile, following the Endgames and Openings `TabsList variant="brand"` pattern.

## Not Verified

Per-user mastered and parked list sizes in prod: the prod DB tunnel was down during exploration. The pagination default doesn't depend on it.

## Breadcrumbs

- `frontend/src/pages/Train.tsx`: session and engine hooks, loop state
- `frontend/src/components/train/TrainStartScreen.tsx`: landing states and card order
- `frontend/src/components/train/TrainStatsCard.tsx`: tiles and explainer copy to move
- `frontend/src/components/train/TrainScheduleSettings.tsx`: collapsible, summary and "Next session" line
- `frontend/src/components/train/TrainLeaderboardCard.tsx`: card to move
- `frontend/src/components/library/FlawCard.tsx`: layout reference, not for reuse
- `frontend/src/pages/library/FlawsTab.tsx`: `PAGE_SIZE` and `Pagination` wiring
- `frontend/src/pages/Endgames.tsx`, `frontend/src/pages/Openings.tsx`: subnav pattern
- `frontend/src/lib/analysisUrl.ts`: `buildGameAnalysisUrl`
- `app/models/drill_item.py`: lifecycle and anchoring rationale
- `app/models/drill_solve.py`: `solved_at`
- `app/repositories/train_repository.py`: status counts
