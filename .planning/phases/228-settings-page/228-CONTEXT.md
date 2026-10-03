# Phase 228: Settings Page — Sound Toggle & Per-Engine Lines/Arrows - Context

**Gathered:** 2026-10-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A `/settings` page (cogwheel entry) holding a sound on/off switch plus per-engine line and arrow
counts for the FlawChess engine and Stockfish. The same settings panel also opens in place as a
sheet from the mobile `/analysis` header and the mobile bot game page. The counts are threaded
through `/analysis` (both engines) and Train free-play / puzzle-reveal cards (Stockfish only), and
the non-primary lines get a translucent per-engine color on both badges and arrows.
Frontend-only. Persistence is localStorage (per device, works for guests).

Locked upstream in SEED-175 / ROADMAP and not re-decided here:

| Setting | Range | Default |
|---|---|---|
| Sound | on/off | on (reuses `useMuted`/`setMuted`, key `flawchess_bot_sound_muted`) |
| FlawChess engine lines | 1-5 | 2 |
| FlawChess engine arrows | 0-3 | 1 |
| Stockfish lines | 1-5 | 2 |
| Stockfish arrows | 0-3 | 1 |

- Lines and arrows are separate per engine. 0 arrows hides that engine's arrows and keeps its card.
- Settings module: typed, `useSyncExternalStore`-based, the same shape as `useMuted` in
  `lib/sounds.ts`, so a later account-sync swap touches only that module.
- Styling: primary line solid. Every non-primary line uses one translucent color per engine
  (blue for Stockfish, gold for FlawChess) on both arrows and card badges. This replaces
  `FLAWCHESS_ENGINE_BADGE_SHADES` and Stockfish's light-blue `SECOND_BEST_ARROW` badge/arrow.
  No eval-proportional transparency.
- Out of scope: search time and thread settings, board colors, piece sets, sound sets.

</domain>

<decisions>
## Implementation Decisions

### Entry placement
- **D-01:** Desktop: an icon-only cogwheel button (lucide `Settings`) in `NavHeader`'s right
  cluster, left of Logout (after the Guest badge and impersonation pill). Needs `aria-label` and
  `title`, and links to `/settings`. Not added to `NAV_ITEMS`.
- **D-02:** Mobile: a "Settings" row with a cogwheel in `MobileMoreDrawer`, above the divider and
  Logout. It links to `/settings`. No cogwheel in the generic `MobileHeader`.
- **D-03:** Mobile `/analysis`: a cogwheel in `AnalysisMobileHeader` next to the "Analysis"
  title. It opens the settings panel in a sheet over the page; it does not navigate away.
- **D-04:** Bot game page, **mobile only**: a cogwheel in the mobile bot game shell (the bottom
  nav is replaced during play), so a user can turn sound off mid-game. It opens the same sheet and
  does not navigate. Navigating away would trigger the `ResumeGate` "Resume game?" overlay on
  return. The planner picks the exact spot in the bot mobile layout. Desktop bot play relies on
  the header cogwheel only.
- **D-05:** No settings shortcut inside the engine cards. The card headers were just slimmed on
  mobile (7ed295414, b4327e5c7).
- **D-06:** The in-context sheets render the **full** `SettingsPanel`, identical to `/settings`
  (Drawer on mobile, matching the existing `components/ui/drawer` usage). There is one panel
  component and no per-surface section variants. Changes apply live underneath the sheet.

### UAT amendment (2026-10-03, owner decision): overlay instead of page
- **D-17:** Supersedes the `/settings` route in D-01, D-02 and D-06. Settings never navigate:
  navigating to `/settings` unmounted the current page (the Train solution screen started the next
  puzzle on return). The desktop header cogwheel (D-01 placement unchanged) opens a modal
  (`SettingsDialogButton`, Radix Dialog) holding the full `SettingsPanel`; the mobile More drawer's
  Settings row (D-02 placement unchanged) closes the drawer and opens the same settings sheet as
  D-03/D-04. The `/settings` route, `pages/Settings.tsx` and its `ROUTE_TITLES` entry are removed
  (587493af7). Both overlays set `aria-modal` and return focus to their cogwheel on close
  (5b3fe98e4). Settings sections render as Cards (104aa7275).
  On mobile `/analysis` the cogwheel sits at the header's top right (`ml-auto`), not next to the
  "Analysis" title as D-03 first said, matching the bot game header (debfd269c).

- **D-07:** Count inputs are segmented toggle groups (`components/ui/toggle-group`): buttons
  `1 2 3 4 5` for lines and `0 1 2 3` for arrows. The sound on/off is a `Switch`.
- **D-08:** Changes apply instantly, with no Save button. Each control writes localStorage on
  change, and subscribers update through `useSyncExternalStore`.
- **D-09:** Three labeled sections, in order: **Sound**, **FlawChess engine**, **Stockfish**.
  Each section gets a short helper line where useful (e.g. "0 arrows hides this engine's arrows,
  the card stays"). One **"Reset to defaults"** button at the bottom resets all five settings
  (including sound back to on).
- **D-10:** Umami: one event per setting change, e.g. `settings-change` with `{setting, value}`,
  fired through `trackEvent()` in `lib/analytics.ts` (not `data-umami-event` on router links).
  It fires on change only, not on page view. Reset fires it once per changed setting, or as a
  single `settings-reset` event, at Claude's discretion.

### Train free-play depth
- **D-11:** Honor the setting at the fixed `MOVETIME_MS = 1500`. Train free-play MultiPV =
  max(SF lines, SF arrows). The user trades depth for breadth by choice, as on lichess. No
  movetime scaling, since search time is out of scope.
- **D-12:** `useStockfishEngine` takes MultiPV as an option instead of the module constant
  `MULTIPV = 2`. The Train solve-screen eval-bar engine (`TrainSolveScreen.tsx` ~1220) stays
  **independent** of the setting at a fixed value, because it only feeds the eval bar. Claude's
  discretion: keep it at 2, or lower it to 1.
- **D-13:** The Stockfish arrow setting governs only the **live engine arrows** in Train
  free-play (`liveBestUci` / pvLines). The puzzle-reveal legend arrows (blue best, green "also
  fine", the game-move arrow) always draw, because they carry puzzle meaning (Phase 200
  sidebar-as-legend contract). The SF lines setting still sets the reveal and free-play
  card rows and the `EngineLinesSkeleton` row count.

### High-count rendering
- **D-14:** On `/analysis`, Stockfish arrows 1..N come from the **same reconciled grading
  ranking** that feeds the SF card, so arrows and card rows always agree. The free-run
  `enginePvLines` serves only as the first-paint fallback before grading lands. Today's loop
  (`reconciledBestUci ?? enginePvLines[i]`) would repeat the best move for i ≥ 1 and must
  change. The free-search MultiPV on `/analysis` then matters only for that fallback.
- **D-15:** Non-primary arrows keep the per-engine width (`FLAWCHESS_ENGINE_ARROW_WIDTH = 1.0`,
  `STOCKFISH_ENGINE_ARROW_WIDTH = 0.5`) and differ only by the translucent engine color. The
  existing width-sorted draw order is unchanged.
- **D-16:** The cards render all N rows at every breakpoint, with no mobile cap. Skeletons show
  N rows.

### Claude's Discretion
- Route gating: `/settings` lives inside `ProtectedLayout` (guests have sessions), without
  `ImportRequiredRoute`. Add `'/settings': 'Settings'` to `ROUTE_TITLES`.
- Exact translucent color values and alpha for the non-primary SF blue and FC gold (UAT-tuned).
  Badge text must stay legible on the translucent fill.
- Settings storage layout: one JSON key vs. per-setting keys, validation/clamping of out-of-range
  stored values, and a fallback to defaults on parse errors. Sound must keep using the existing
  `flawchess_bot_sound_muted` key so the pre-Phase-223 persisted `'1'` values still work.
- Where the per-engine counts are read: hook calls in `useAnalysisEngineLines`,
  `useAnalysisBoardArrows`, `Analysis.tsx` (FC slice ~931), `TrainReveal`, and `useTrainFreePlay`,
  replacing the exported `MAX_LINES` and `ARROW_COUNT` constants.
- Whether `useGameOverlay`'s `SECOND_BEST_ARROW` path is still live anywhere. The 156 UAT
  comment says the analysis board no longer draws it, so retire it or restyle it accordingly.
- Bot mobile cogwheel placement (D-04) and sheet trigger component reuse between D-03 and D-04.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and locked decisions
- `.planning/seeds/SEED-175-settings-page.md`: locked decisions, breadcrumbs, and the
  "Verify in planning" list (FC `rankedLines` reliably yielding up to 5 lines; tests pinning
  `MAX_LINES = 2`, e.g. `FlawChessEngineLines.test.tsx`, should read the setting default).
- `.planning/ROADMAP.md`, Phase 228 entry.

### Frontend rules
- `frontend/CLAUDE.md`: styling/theme tokens, testids, Umami (`trackEvent` for internal
  actions), frontend Sentry.

### Code anchors
- `frontend/src/lib/sounds.ts`: `MUTE_KEY`, `useMuted`, `setMuted`, the module shape to mirror.
- `frontend/src/App.tsx`: `NavHeader` (~314), `MobileHeader` (~383), `AnalysisMobileHeader`
  (~425), `MobileMoreDrawer` (~558), `ROUTE_TITLES`, the `<Routes>` block (~974).
- `frontend/src/components/analysis/EngineLines.tsx`: `MAX_LINES` (38), badge color by rank (~266).
- `frontend/src/components/analysis/FlawChessEngineLines.tsx`: `MAX_LINES` (48), badge shades (~314).
- `frontend/src/hooks/analysis/useAnalysisBoardArrows.ts`: `ARROW_COUNT` (60), `engineArrows` (~343).
- `frontend/src/hooks/analysis/useAnalysisEngineLines.ts`: FC/SF slices (~311, ~350).
- `frontend/src/pages/Analysis.tsx`: `FC_MAX_LINES` slice (~931), `useStockfishEngine` (~531).
- `frontend/src/hooks/useStockfishEngine.ts`: `MOVETIME_MS`, `MULTIPV`, `MAX_NODES`.
- `frontend/src/hooks/useTrainFreePlay.ts` (~227, ~263) and
  `frontend/src/components/train/TrainReveal.tsx` (`MAX_LINES` skeleton ~461).
- `frontend/src/components/train/TrainSolveScreen.tsx` (~1220): the eval-bar engine, which stays
  independent of the setting.
- `frontend/src/lib/theme.ts`: `FLAWCHESS_ENGINE_BADGE_SHADES` (147), `BEST_MOVE_ARROW` (418),
  `FLAWCHESS_ENGINE_ARROW` (426), `SECOND_BEST_ARROW` / `SECOND_BEST_BADGE_TEXT` (432).
- `frontend/src/hooks/useGameOverlay.ts` (~308): remaining `SECOND_BEST_ARROW` user.
- `frontend/src/components/bots/` (`BotGameMobileLayout.tsx`, `ResumeGate.tsx`),
  `frontend/src/components/bots/BotGameMobileBar.tsx`: bot mobile shell for D-04.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useMuted`/`setMuted` (`lib/sounds.ts`): an existing two-way toggle with no production caller
  since Phase 223. It becomes the Sound switch's backing store.
- `components/ui/`: `switch`, `toggle-group`, `drawer`, `dialog`, and `button` cover every control
  and both sheet containers.
- `lib/analytics.ts` `trackEvent()` for the D-10 change events.
- The `EngineLinesSkeleton` `rows` prop already takes a count.

### Established Patterns
- `useSyncExternalStore` plus listener stores keyed in localStorage (`useMuted`, `useUserFlag`).
  Settings must be flat and not email-scoped so guests persist too.
- Arrow draw order is `ChessBoard`'s width sort, not array order. `layerKey` per arrow
  (`fc-${i}`, `sf-${i}`) already supports N arrows.
- Phase 162 D-07/D-12: the top SF arrow follows the global reconciled argmax. D-14 extends the
  same source to arrows 2..N.

### Integration Points
- New route `/settings` and a new `SettingsPanel` component (page plus sheet reuse).
- The `useStockfishEngine` signature gains MultiPV (callers: `Analysis.tsx`, `useTrainFreePlay`,
  `TrainSolveScreen`).
- Theme: new translucent per-engine non-primary tokens replace the shade arrays and
  `SECOND_BEST_*`.

</code_context>

<specifics>
## Specific Ideas

- The user specifically wants sound to be switchable **during a bot game** on mobile without
  leaving the game. That is the motivation for D-04 and the sheet in D-06.
- Lichess is the reference: no eval-proportional arrow transparency, and breadth (MultiPV) costs
  depth at a fixed budget.

</specifics>

<deferred>
## Deferred Ideas

- A "search longer" Stockfish toggle, reconsidered once Phase 226's pool tuning has settled
  (already listed in SEED-175 out of scope).
- Moving the Train reminder settings (`TrainScheduleSettings`, push toggle and hour picker) onto
  the settings page. This is a natural future home, but it is new scope and was not discussed.

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`, `172-deferred-review-findings.md`,
  and `2026-08-29-variation-tree-nested-button.md` matched on keyword noise ("175", "phase"),
  not on scope. They are unrelated to settings.

</deferred>

---

*Phase: 228-settings-page*
*Context gathered: 2026-10-03*
