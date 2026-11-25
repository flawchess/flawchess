# Mobile and foldable layout: status

Goal: every page works well on phones (from iPhone SE, portrait), the Galaxy Z Fold8 cover screen (portrait) and its inner screen (portrait and landscape). Rules, target sizes and the OS-bar gotcha: `frontend/CLAUDE.md`, "Layout Targets". Tick a box only after checking at the **usable** sizes listed there. `[x]` means done and checked in the browser, device checks are listed separately.

Last updated: 2026-11-25

## App frame

- [x] Bottom tab bar instead of the desktop header below 1024px, both orientations (261124-ply)
- [x] Phone text sizes on unfolded foldables (261124-ply)
- [x] Touch-sized buttons, chips, filter toggles and the Train tabs on unfolded foldables: their compact desktop size starts at `lg` instead of `sm`/`md` (2026-11-25). Train drill at 933x617 and 816x528: no page scroll, board unchanged (489px, 436px)
- [x] Target sizes and OS-bar gotcha documented, sizes measured from device screenshots (261125-v4k)
- [x] Header removed on Library and Endgames (owner, 2026-11-25): `MobileTopBar` in `App.tsx`, `HEADERLESS_ROUTES`. Settings is in the More drawer. An impersonating superuser gets the pill in a slim row at the top of the page
- [ ] Header on Train and the Bots list: decision open. It costs 45px and shows the logo, page name and settings cog (also in the More drawer)
- [ ] `short:` (below 560px tall) was meant for phones held sideways but also matches 816x528 and 375x553. Being fixed page by page. Analysis is done (page lock scoped to `short:landscape:`, footer pinned by its own height limit), the Openings top padding and the Train drills are still to check at 816x528

## Analysis

- [x] Phones: header gone, More menu in the bottom bar (261124-w90)
- [x] Foldables and tablets below 1024px: same bottom bar (261124-w90)
- [x] Tab icons hide where the tabs don't fit (261124-w90)
- [x] Inner landscape: board sized to the height above the bar, the mistake strip is no longer cut off, no page scroll (261125-v4k)
- [x] Inner landscape: tab content starts at the board's top edge (261125-v4k)
- [x] Inner landscape: the tabs take all the width the board leaves, no gap between the columns (261125-v4k)
- [x] Portrait: the board is capped by the screen height so the tabs keep room while the strip shows (`lib/analysisTakeoverBoard.ts`). Tab panel height incl. 8px padding, before and after: inner 704x845 141px (unchanged), cover 475x663 50 to 100px, zoomed inner 616x728 24 to 104px, zoomed cover 416x569 10 to 65px, iPhone SE 375x647 126px (unchanged), SE in Safari 375x553 10 to 49px. The last two small ones stop at the 256px board floor
- [x] SE in Safari 375x553: no empty space under the footer (`short:` unlocked the page height in portrait too)
- [x] Zoomed inner landscape 816x528: bar pinned, no page scroll, board 362 to 306px (game mode), tabs 303 to 374px wide. The footer is pinned from 502px of height now (`MID_PINNED_FOOTER_MIN_HEIGHT_PX` in `Analysis.tsx`) instead of `short:`; phones held sideways are unchanged
- [x] Long tactic chips no longer overlap in the move list at 816px wide (the longest one found, "discovered-attack 3", is 156px in a 161px column)

## Bot game

- [x] Arrow and cog row gone, More menu (Back to bots, Settings, Flip board) in the bottom bar (261125-v4k)
- [x] Inner landscape: two columns above the same bar, Resign no longer under the tab bar (261125-v4k)
- [x] Inner portrait: board uses the screen, own name and clock visible (261125-v4k)
- [x] No page scroll during a game at any target size (261125-v4k)
- [x] Avatar and move list aligned with the board edges, long move lists scroll (261125-v4k)

## Bots list and setup

- [x] No horizontal overflow, usable at the target sizes
- [ ] Inner landscape: the list is a narrow centred column, consider using the width
- [ ] Header decision (see App frame)

## Openings

- [x] No header below 1024px
- [x] Inner landscape: board left, tab content right (261124-u98)
- [ ] Inner portrait: board capped at 400px, a third of the width is empty
- [ ] Inner landscape, 816px wide: move table 23px too wide, result bars cut off
- [ ] Stats tab on the inner screen: "Came out worse" / "Came out better" stacked at full width, could sit side by side
- [ ] Re-check the landscape layout at 933x617 and 816x528

## Library (Import, Games, Flaws, Stats)

- [x] No horizontal overflow from 375px
- [x] Inner landscape: phone frame up to 1024px (Filters buttons and drawers instead of the filter strip). Content width 798 to 886px at 933x617, 681 to 769px at 816x528. Stats: the TC switch and Filters row sits above the sections there, they start 44 to 56px lower
- [x] Games and Flaws: counts, Filters and Tags in one sticky row (`LibraryMobileFilterBar`). First card top, before and after: 375x647 253 to 169px, 375x553 208 to 124px, inner portrait 215 to 169px
- [x] Game card from 600px, analyzed games: board left, info, eval chart and accuracy right (`TWO_COLUMN_BOARD_SIZE`). Board 130 to 304px at 704x845, 933x617 and 816x528 (232px at 616x728), card height 594 to 538px in portrait and 530px in landscape (798 to 570px at 616x728)
- [x] Flaws, inner landscape: two cards per row (`trainside:grid-cols-2`), tags at full width below the board, Analyze beside it. Card, before and after: 933x617 886px wide and 285px tall to 435px and 341px, 816x528 769px and 285px to 377px and 309 to 331px (168px board instead of 200px). List of 20 cards: 6381 to 3931px and 6336 to 3588px page height. Checked with the longest tags, names and clocks; other sizes unchanged
- [x] Flaw card redesign, all widths (2026-11-25), replaces the flaw card layouts above: one layout, severity and move in the header, clock, opponent, date and the tags beside the board, Analyze at full width below. The eval swing is gone. Board sized from the card width (`useFlawBoardSize`; 152 to 216px). Grid as in Endgames Games but with a 340px minimum, 24 per page: one card per row at 375x647, 616x728 and 704x845, two at 933x617, 816x528 and 1024px, three at 1280px. Phones get a smaller board (168px instead of half the screen at 375px). Tags can end below the board on the narrowest cards: 32px on 5 of 24 cards at 375px wide (2px on 7 more), 8px on one at 816x528, none at the other sizes
- [x] Header removed below 1024px, the page starts 45px higher (already gone at 816x528, `short:`)
- [ ] 320px wide (first iPhone SE): tabs and the analyzed badge overflow. Only if 320px becomes a target

## Endgames

- [x] No horizontal overflow
- [x] Same split as Library, moved to 1024px
- [x] Games: the endgame type dropdown sits in the Filters row. First game top, before and after: 375x647 412 to 352px, 933x617 348 to 340px
- [x] Games: up to three cards per row, sized by the list width (`auto-fill`, 320px minimum, `GameCardList` `multiColumn`). 704x845, 933x617 and 816x528 two per row, 616x728 and phones one, 1024px two, 1280px and up three (the filter panel overlays the list). Page height at 933x617 4296px for 20 games to 3040px for 24
- [x] Header removed below 1024px, the page starts 45px higher (already gone at 816x528, `short:`)

## Train

- [x] Drills: side layout in landscape, header hidden, compact bubble, bottom bar on reveals (261124-ply)
- [x] Portrait: board capped by the screen height (84b9c5096)
- [x] Landscape: the solution screens (blunder check, personalized puzzles) use the bottom bar (2026-11-25): Start, Back, Fwd, Analyze, Next, as in portrait. The controls row and the Analyze / Next footer leave the side column, the game info moves into it. From 500px tall (`TRAIN_BAND_BAR_MIN_HEIGHT_PX`), phones held sideways and desktop are unchanged. The bar's height is kept free during the drill, so the board doesn't resize: blunder check 487px and puzzles 489px at 933x617, 436px at 816x528, the same before and during the solution. Flip is gone there, as in portrait
- [x] Solutions, bottom bar: Next is a filled column in the same icon-over-label shape as the others, instead of a 32px pill (2026-11-25)
- [ ] "Flaw fixed!" banner was squashed at 816x528: fixed (`shrink-0`), re-check in the browser
- [ ] Landscape: a puzzle solution with the "Flaw fixed!" banner or a long verdict is taller than the screen, the page scrolls (751px at 933x617). The actions stay in the bar, but the board scrolls away. The side column could scroll on its own, as it does below 560px
- [ ] Re-check the drills at the usable sizes (checked at DevTools preset heights so far)
- [ ] Today, Leaderboard, Archive: header decision (see App frame)

## Not checked yet

- [ ] Home, Welcome, Auth, Privacy
- [ ] Filter drawers, settings sheet, dialogs on small heights
- [ ] Activity and Admin (superuser only, low priority)

## Device checks (Galaxy Z Fold8)

- [x] Bot game portrait, cover and inner
- [ ] Bot game landscape after the alignment change
- [ ] Analysis landscape after the strip and tab changes
- [ ] Train solutions, inner landscape: bottom bar, board size
- [ ] Library game cards, inner portrait and landscape
- [ ] Library flaw cards, inner landscape
- [ ] Analysis landscape with a larger display zoom: is the 306px board big enough?
- [ ] Analysis portrait after the board cap, cover and inner: is the board still big enough?
- [ ] Installed app on a real iPhone (notch and home bar insets): Analysis, bot game, Library and Endgames (top inset without the header)
