# Mobile and foldable layout: status

Goal: every page works well on phones (from iPhone SE, portrait), the Galaxy Z Fold8 cover screen (portrait) and its inner screen (portrait and landscape). Portrait tablets (iPads at 810 to 834px wide, about 4% of sessions, far more than foldables) fall in the same phone frame below 1024px, so the foldable work carries over to them; 820x1180 is a useful extra check size. Rules, target sizes and the OS-bar gotcha: `frontend/CLAUDE.md`, "Layout Targets". Tick a box only after checking at the **usable** sizes listed there. `[x]` means done and checked in the browser, device checks are listed separately.

Last updated: 2026-11-26

## App frame

- [x] Bottom tab bar instead of the desktop header below 1024px, both orientations (261124-ply)
- [x] Phone text sizes on unfolded foldables (261124-ply)
- [x] Touch-sized buttons, chips, filter toggles and the Train tabs on unfolded foldables: their compact desktop size starts at `lg` instead of `sm`/`md` (2026-11-25). Train drill at 933x617 and 816x528: no page scroll, board unchanged (489px, 436px; board sizes since changed by the Train side column floor, see Train)
- [x] Target sizes and OS-bar gotcha documented, sizes measured from device screenshots (261125-v4k)
- [x] Header removed on Library and Endgames (owner, 2026-11-25): `MobileTopBar` in `App.tsx`, `HEADERLESS_ROUTES`. Settings is in the More drawer. An impersonating superuser gets the pill in a slim row at the top of the page
- [x] Tablets from 1024px wide (iPads in landscape, iPad Pro) get the desktop frame with compact controls. Considered gating touch sizes on `pointer: coarse` instead of width; not pursued for now (2026-11-26), revisit only if small targets turn up at 1180x820
- [x] More drawer (2026-11-26): Logout was drawn below the screen edge in landscape (8 superuser rows, no overflow handling under the 80vh cap). Nav links now sit in a grid, 2 columns in portrait and 4 in landscape, that scrolls on its own, with Settings and Logout in a pinned footer row below a divider. Superuser drawer (8 links) fits without scrolling at every target size plus 844x390 and 667x375 (grid 188px in portrait, 92px in landscape), no clipped labels
- [x] Header removed on Train and the Bots list too (owner, 2026-11-26): added to `HEADERLESS_ROUTES`. Train tabs start 8px from the top at 375x553 and 24px at 816x528, the Bots list bubble 16px at 375x553; no horizontal overflow. Admin and Activity keep the header
- [x] `short:` (below 560px tall) was meant for phones held sideways but also matches 816x528 and 375x553. Fixed page by page: Analysis (page lock scoped to `short:landscape:`, footer pinned by its own height limit), Library and Endgames (header gone). Checked 2026-11-26 at 816x528: Openings (subnav 8px from the top, no page overflow) and the blunder check drill (no page scroll, board 388px, side column scrolls inside its frame)

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
- [ ] Two-column layout on short windows (e.g. 1000x594): the board is held by the height, not by the tabs (board 372px, tabs 508px; the width would allow about 518px). The player bars and the pinned footer take about 220px. Idea, not pursued: player names and clocks beside the board when the window is short (about 80px more board)
- [x] Move info strip (owner, 2026-11-26): the strip under the board (Explain bar) now describes every move in the two-column layout (768 to 1199px) and on desktop, not only mistakes and blunders. Its height was already kept free on every move there, which left an empty gap under the board. Non-flaw moves show the move, the board's badge and a word (Best move, Good move, Great move, Gem, Book move, Inaccuracy, Mistake); flaws with tactics or a facepalm score keep their headline; Best / Punish buttons only where lines exist (`lib/moveInfo.ts`). Phones keep the flaw-only strip. Strip height constant from move to move: 54px at 1000x594 (board 372px unchanged), 53px on desktop

## Bot game

- [x] Arrow and cog row gone, More menu (Back to bots, Settings, Flip board) in the bottom bar (261125-v4k)
- [x] Inner landscape: two columns above the same bar, Resign no longer under the tab bar (261125-v4k)
- [x] Inner portrait: board uses the screen, own name and clock visible (261125-v4k)
- [x] No page scroll during a game at any target size (261125-v4k)
- [x] Avatar and move list aligned with the board edges, long move lists scroll (261125-v4k)

## Bots list and setup

- [x] No horizontal overflow, usable at the target sizes
- [ ] Inner landscape: the list is a narrow centred column, consider using the width
- [x] Header removed below 1024px (2026-11-26), the page starts 45px higher

## Openings

- [x] No header below 1024px
- [x] Inner landscape: board left, tab content right (261124-u98)
- [x] Subnav (Moves, Games, Stats) on top at full width in landscape too (owner, 2026-11-26), not at the top of the right column. The height-fitted board loses its 48px: about 483 to 435px at 933x617 (483 inferred from the 48px shift, not measured), 380 to 362px at 816x528 (there it was partly width-bound)
- [x] Portrait from 600px (inner screen, zoomed inner, portrait tablets): the opening name and move list sit in a column beside the board (`useIsOpeningLineBesideBoard`), the move list fills the board's height. Board 400px, column 212px at 704x845 (table top 630 to 527px, 7 moves above the bar); board 344px at 616x728 (table top 615 to 471px, 0 to 5 moves); 400px and 312px at 820x1100. Phones and the cover screen keep the stacked line
- [x] Inner landscape, 816px wide: move table fits (Games and Score columns 4.25rem each, were 5.5rem and 4.5rem). Results bar 81px at 816x528 (was 23px short of its 80px minimum), 128px at 933x617; no cell overflow at 375, 616, 816, 933 and 1280px
- [x] Landscape windows 640 to 800px wide: the move table no longer overflows. The content column's floor is 40% of the row or 19.25rem, whichever is wider (was 40%: 63px cut off at 640x500); the board shrinks instead (228px at 640x500). No table or page overflow from 360 to 1440px wide at 375, 500 and 800px tall
- [ ] Stats tab on the inner screen: "Came out worse" / "Came out better" stacked at full width, could sit side by side
- [x] Re-checked the landscape layout at 933x617 and 816x528 (2026-11-26): subnav on top, board 435px and 362px, move table fits, no horizontal overflow

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
- [x] Landscape: the solution screens (blunder check, personalized puzzles) use the bottom bar (2026-11-25): Start, Back, Fwd, Analyze, Next, as in portrait. The controls row and the Analyze / Next footer leave the side column, the game info moves into it. From 500px tall, now 450px (`TRAIN_BAND_BAR_MIN_HEIGHT_PX`, see below), phones held sideways and desktop are unchanged. The bar's height is kept free during the drill, so the board doesn't resize: blunder check 487px and puzzles 489px at 933x617, 436px at 816x528 (388px since the side column floor change below), the same before and during the solution. Flip is gone there, as in portrait
- [x] Side column floor 272 to 336px (owner, 2026-11-26, `TRAIN_SIDE_COLUMN_WIDTH_CLASS`), and the line chips' move wraps under its eval when the chip is too narrow (`TrainLineChips`), so nothing is cut off (at 816x528 even Rac8 was cut off in the 288px column). In a 107px chip, moves up to 4 characters with a normal eval stay on one line (chip 68px tall), longer ones wrap (94px). A 392px floor was tried first and dropped: it cost the board too much (816x528 436 to 332px). Boards now: 933x617 487px (unchanged), 816x528 436 to 388px, 761x472 349px, 667x375 319 to 255px; 852x393, 740x360 and desktop unchanged. No page overflow or page scroll
- [x] Bottom tab bar during the drills in landscape from 450px tall (owner, 2026-11-26): it was hidden during every side-layout drill, although from 500px tall its height was kept free anyway (empty strip). `TRAIN_BAND_BAR_MIN_HEIGHT_PX` 500 to 450, so a 761x472 window (board width-bound) also gets the bar and the bottom-bar solutions. Phones held sideways (about 440px tall at most) still drop it. Tab bar top: 933x617 556px under a board ending at 537, 816x528 467 (board ends 400), 761x472 411 (board ends 361)
- [x] Blunder check, short side layout (816x528): the settings button stuck out 6px past the side scroller and gave it a horizontal scrollbar; the scroller clips horizontal overflow now
- [x] Solutions, bottom bar: Next is a filled column in the same icon-over-label shape as the others, instead of a 32px pill (2026-11-25)
- [x] "Flaw fixed!" banner was squashed at 816x528: fixed (`shrink-0`). Checked 2026-11-26 with the real banner (solve response forced to mastered): 98px tall at 816x528 and at every portrait size, the reveal scrolls inside its frame at 816x528 (610px of content in 388px), board 388px, no page scroll
- [x] Landscape band with the bottom bar: the puzzle solution column scrolls inside a frame as tall as the board (`useIsTrainFramedSide`, as below 560px tall), so a long verdict or the "Flaw fixed!" banner no longer scrolls the page. 933x617 with a 76px stand-in for the banner: page 617px tall (was 688px), board 489px and the bar unchanged. The game info line at the column's foot now needs a scroll when the column is full
- [x] Re-check the drills at the usable sizes (2026-11-26). Blunder check drill at 933x617, 816x528, 761x472, 852x393, 667x375, 740x360: no page scroll or horizontal overflow. Puzzle drill and solution at 933x617 and 816x528 (board 388px, tab bar 67px under the board, no page scroll). Puzzle drill in portrait: no horizontal overflow; 375x647, 616x728 and 704x845 don't scroll; 375x553, 475x663 and 416x569 scroll 34, 9 and 59px (phones are not capped by height on purpose, see below)
- [x] Blunder check solution in landscape (2026-11-26): 933x617 not framed but fits (panel 491px beside a 525px board, content 491px, no page scroll); 816x528 framed (498px of content in 388px), no page scroll. Framing at 933x617 only if a longer verdict turns up
- [ ] Puzzle drill, zoomed cover screen 416x569: the guess buttons end 18px under the bottom bar until the page scrolls (board 384px full width, bubble 132px). Same at 375x553 minus the overlap (buttons end 7px above the bar). Already so on `main`: the portrait cap (`STACKED_BOARD_ROW_CAP_CLASS`) keeps phones width-bound. Owner call: cap phones too (smaller board) or accept the scroll
- [ ] Framed side column with a classic desktop scrollbar (Linux/Windows Chrome, window below 1024px wide and under about 620px tall): the scrollbar takes 15px of the 336px column and clips the edge of the Game line chip, since the panel inside keeps the 336px floor. Overlay scrollbars (phones, foldables, macOS) are not affected
- [x] Today, Leaderboard, Archive: header removed below 1024px (2026-11-26), the page starts 45px higher

## Not checked yet

- [x] Auth (/login) in landscape (2026-11-26): logo and tagline move into a left column beside the Sign In / Register card from 640px wide (`sm:landscape:`). The stacked page was ~780px tall, so the card ran past the fold on landscape tablets, the Fold and 1280x800. Now no page scroll at 933x617, 1024x700, 1180x740, 1280x800; 816x528 and 852x360 scroll 28px (only the "Create one" line). Portrait: 80px logo beside the title and tagline instead of above them; 375x647 no longer scrolls (was 780px tall), and at 375x553 (Safari) the Log In button ends at 548px, above the fold
- [ ] Home, Welcome, Privacy; Forgot/Reset password pages (same stacked logo, smaller card)
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
- [ ] Openings inner portrait: opening line beside the board; landscape: subnav on top, board size
- [ ] Train landscape: 336px side column, wrapped line chips, the tab bar during the drill
- [ ] Analysis inner landscape: the move info strip on every move
- [ ] Installed app on a real iPhone (notch and home bar insets): Analysis, bot game, Library, Endgames, Train and the Bots list (top inset without the header)
