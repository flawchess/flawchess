---
id: SEED-199
status: dormant
planted: 2026-10-14
planted_during: ad-hoc Umami funnel review after Phase 239 (no phase in flight)
trigger_when: owner wants to raise reach of the analysis sections (Endgames, Library Flaws/Stats, Openings secondary tabs), or any nav/onboarding work; refine the ideas below first, they are NOT implementation-ready
scope: small to medium (sticky subnav + tab styling + nav-dot gating are small; in-content teaser links and post-import copy need design)
---

# SEED-199: Subnav and section discoverability

Status: **ideas need refinement before implementation.** The data below says *where* users drop off;
the suggestions are candidate levers, not decided designs.

Screenshots (gitignored, local only): `temp/subnav-uat/desktop-openings.jpg`, `temp/subnav-uat/desktop-endgames.jpg`.

## Why This Matters

Only a third of users who import games ever open Library Stats, and fewer than 40% ever open Endgames.
These are the analysis surfaces FlawChess is built around. The owner suspected the subnav is not salient
enough; the data suggests the bigger leak is one level up (users never entering a section), with the
non-sticky subnav as a secondary cause.

## Data (Umami joined to prod, pulled 2026-10-14)

Umami identifies sessions with `users.id` as `distinct_id` only since Phase 229 (**2026-10-03**), so the
window is 11 days. Method: identified sessions -> prod `users` (is_guest, has any `games` row), owner (28)
excluded, "reached" = at least one pageview of the path.

**Cohort pitfall (caught by the owner):** a mixed cohort of all identified users showed only 72% visiting
`/library/import`, which is impossible for new signups (registration routes there). Pre-Oct-3 users imported
before identification existed. Use only **users created on/after 2026-10-03 with games**: 72 users
(43 registered, 29 guests); 71/72 (99%) hit Import, the 1 miss came in via Google OAuth.

Reach per page (new-signup cohort, n=72; ★ = section default tab):

| Page | Registered (43) | Guest (29) | All (72) |
|---|---|---|---|
| Library (any) | 100% | 100% | 100% |
| Import | 98% | 100% | 99% |
| ★ Games | 91% | 76% | 85% |
| Flaws | 58% | 38% | 50% |
| Stats | 40% | 24% | 33% |
| Analysis | 70% | 62% | 67% |
| Openings (any) / ★ Explorer | 81% | 38% | 64% |
| Openings Games | 35% | 17% | 28% |
| Openings Stats | 30% | 17% | 25% |
| Openings Insights | 23% | 7% | 17% |
| Train | 77% | 38% | 61% |
| Bots | 44% | 31% | 39% |
| Endgames (any) / ★ Stats | 53% | 14% | 38% |
| Endgames Games | 28% | 3% | 18% |

Conditional on entering a section, about half go on to a secondary tab:

| Entered via default tab | n | Also opened a secondary tab |
|---|---|---|
| Library Games | 61 | 57% (Flaws 57%, Stats 39%) |
| Openings Explorer | 46 | 54% |
| Endgames Stats | 27 | 48% |

Desktop vs mobile conditional rates are similar (desktop n=42, mobile n=30): no mobile-specific gap.

Caveats: small n; 11-day window so late visits are missing (lower bound); a guest's `is_guest` is the
current value. Re-pull with a fixed exposure window (e.g. "reached within 7 days of signup") once a few
weeks of identified data exist, and use that as the baseline for any change here.

## Observations from the UI (dev build, 2026-10-14)

- Desktop: full-width charcoal subnav directly under the top nav. Active tab = solid brown fill; inactive
  tabs = gray text (`oklch(0.708 0 0)`) + icon, no fill, no border. Readable, but inactive tabs look like
  labels rather than buttons, and the bar visually merges with the header.
- Mobile (375 px): 40 px tab row near the top, ~82 px per tab. **Not sticky on any section** (verified by
  walking ancestors for `position: sticky/fixed`). Library Games is ~8,100 px tall and Endgames Stats
  ~6,800 px, so after one scroll the secondary tabs are gone until the user scrolls back up.
  Note: the comment in `LibraryPage.tsx` says "sticky subnav row" but the row is not sticky.
- Naming: top nav says "Opening"/"Endgame" (singular); three different tabs are called "Stats"
  (Library, Openings, Endgames); Openings "Stats" vs "Insights" is not self-explanatory.
- Nav red dots (`useNavIndicators`, `App.tsx` ~line 207): the Endgames dot only appears **after** Openings
  has been visited (`showEndgamesDot = navUnlocked && openingsVisited && !endgamesVisited`), so users who
  skip Openings are never pointed at Endgames (likely contributes to guests' 14%). Dot flags live in
  localStorage per device (`useUserFlag`), so they reappear on every new browser.
- Post-import bot bubble (`importBotBubbleCopy.ts`, EXPLORE_PARTS) links Games, Train, Bots, Openings,
  Endgames, but **not Library Flaws or Stats**.

## Candidate ideas (to refine)

Rough order of expected value per effort:

1. **Sticky subnav** (mobile and desktop) so secondary tabs stay reachable on long pages. Check interplay
   with the Endgames mobile pinned button and the Openings mobile control row.
2. **Inactive-tab affordance**: faint outline or lighter fill so inactive tabs read as buttons.
3. **Ungate the Endgames nav dot** from the Openings visit (show both).
4. **Post-import bubble**: add Flaws and Stats links.
5. **In-content "next" links / teasers**: e.g. at the end of Endgames Stats "See the games behind these
   stats -> Games"; a teaser with a real number ("Your endgame score is 12 points below your overall score
   ->") from Library Games into Endgames. Needs copy and placement design.
6. **Red dots on unvisited subtabs** (owner's idea). Cheap, but: dot fatigue (already up to 3 dots + Train
   badge), per-device localStorage flags, and a dot on a scrolled-away tab does nothing, so only after (1).
   If done, one dot at a time on the next unvisited subtab.
7. **Renaming**: give Library "Stats" a label that says what it contains; consider Openings Stats vs Insights.

Open questions for refinement: what reach is "good" (no baseline yet); whether guests need a different
nudge path than registered users; whether Phase 239's Library Stats redesign changes what the tab should be
called; how to measure impact (fixed-window funnel before/after).

## Breadcrumbs

- `frontend/src/App.tsx` (`useNavIndicators`, `NavDot`, `NavIndicator`, ~lines 193-318)
- `frontend/src/hooks/useUserFlag.ts` (localStorage flags behind the dots)
- `frontend/src/pages/library/LibraryPage.tsx` (desktop + mobile subnav)
- `frontend/src/pages/Openings.tsx` (~line 589 desktop tabs), `frontend/src/pages/Endgames.tsx` (~lines 403, 448)
- `frontend/src/components/ui/tabs.tsx` (`brand` variant styling)
- `frontend/src/components/import/importBotBubbleCopy.ts` (post-import links)
- `frontend/src/lib/analytics.ts` (`identifyUser`; Umami `distinct_id` = `users.id`, Phase 229)
- Related: SEED-198 / Phase 239 (Library Stats redesign), SEED-196 / Phase 238 (Endgame Stats redesign)
