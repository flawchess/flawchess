# Phase 171: Bots Page + Setup Screen + Nav - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

The Bots **page shell**: the surfaces that turn the already-built bot-play machinery
into a feature a user can find, configure, and finish.

Three deliverables:

1. **Setup screen (PLAY-02)** — replaces the D-14 hardcoded `BOT_GAME_SETTINGS` stub
   branch in `Bots.tsx` with a real pre-game screen: ELO, play-style, color, and a
   lichess-preset time control, then Start.
2. **Nav entry (PLAY-01)** — `/bots` becomes a linked top-level page (desktop nav +
   mobile bottom bar + more-drawer), never import-locked.
3. **Full-loop surfacing (PLAY-10 / SC3 / SC4)** — logged-in users and guests both play
   a complete game; the finished game's arrival in the Library is surfaced on the result
   screen, with the guest not-auto-analyzed caveat.

**Already built, NOT re-opened here:** the clocked board and game loop (169), the opening
book (169.5), localStorage resume + the ResumeGate + the store-once plumbing (170), and
the `POST /bots/games` endpoint incl. guest support and server-side rating derivation
(167). This phase consumes all of it.

**In scope beyond the strict roadmap text (deliberate, decided in discussion):**
- Resolving **SEED-100** (the declared blocker) — see D-03.
- A new **lichess-blitz-equivalent rating field on `/users/me`** (D-07), because the
  setup screen's ELO default needs a converted rating and the frontend cannot currently
  get one.
- Pointing the **analysis board's free-play ELO default** at that same new field (D-08) —
  a one-line fix riding on D-07, explicitly approved as scope.

**Out of scope:** bot personas / style axes (SEED-098, a future milestone), any
re-calibration of the strength map (SEED-101/102/103/104), and any change to how the
bot chooses moves beyond what SEED-100 requires.

</domain>

<decisions>
## Implementation Decisions

### Play-style control + the SEED-100 blocker

- **D-01 — `blend` ships as a preset-plus-slider control, NOT a discrete mode picker.**
  Same UI shape as the existing `OpponentStrengthFilter` (which is built on
  `components/filters/PresetRangeFilter.tsx`: label + info popover + preset button grid +
  slider + summary), but **single-thumb, not a range slider**:
  - **Two preset buttons:** **Human** → `blend = 0` · **Engine** → `blend = 1`.
  - **Slider spans `0.05 – 1.00` in `0.05` steps** — i.e. the slider covers ONLY the
    continuous search regime. `blend = 0` is reachable *only* via the Human preset.
  - **Default: `blend = 0.5`** (today's hardcoded stub value — shipped behavior unchanged).

  **Why the slider excludes 0** (this is the load-bearing part — do not "simplify" it back
  to a 0–1 slider): `selectBotMove.ts:113-146` is a **three-way regime dispatch, not a
  mix**. `blend = 0` runs one Maia policy call with **no search at all**; anything `> 0`
  runs full MCTS and samples the *Stockfish* practical score at `tau = 0.1 × (1 − blend)`.
  So `0 → 0.05` is a **cliff** (harness: ~980 → ~1938 at rung 1500, i.e. ≈ +950 ELO),
  while the whole remaining 95% of the axis is a gentle ramp (0.5 → 1 bought only
  +154/+198/+375). Putting 0 on the slider would advertise a smooth continuum that does
  not exist. Putting it on a **button** is honest: it is a different regime, not a slider
  position.

  ⚠ **An earlier decision in this same session chose three discrete modes
  (Human/Balanced/Sharp) and was REVERSED by the user in favour of the slider above.**
  The reversal is deliberate. Do not "restore" the discrete picker.

- **D-02 — Human mode keeps the existing pacing.** At `blend = 0` the bot resolves in
  ~0.09s (168.5 measurement, cited in `chessClock.ts:63-64`). `chessClock.ts` already has
  a synthetic minimum think/reveal delay built for exactly this case. Ship on it. If UAT
  says it feels robotic, **tune that constant** — do not add a new pacing mechanism
  (per-move randomized delays were considered and rejected as out of scope for a page-shell
  phase).

- **D-03 — SEED-100 resolved via the seed's fix (b): document + pin, do NOT race the deadline.**
  The Human preset makes `blend = 0` user-reachable, which is exactly what
  SEED-100 blocks on. Required work:
  1. **Correct the false comment.** `chessClock.ts` (~:36-39) asserts `deadlineSearch.ts`
     enforces the D-16 think deadline "from OUTSIDE the frozen search core". That is true
     only for `blend > 0`. Fix the comment, and document the exemption on
     `BotGameSettings.blend`.
  2. **Pin the behavior with a test** that `blend = 0` never consults `deps.search`
     (the D-16 deadline is computed and correctly unused).
  3. **Prove it by mutation** — revert the fix and confirm the test fails. Symbol presence
     / grep is NOT acceptable evidence here (see memory `feedback_mutation_test_gap_closures`;
     Phase 169 burned three rounds on exactly this failure shape, and SEED-100 says so
     explicitly).

  **Fix (a) — racing `selectBotMove` against the deadline — was considered and REJECTED.**
  At `blend = 0` a deadline abort has no partial result to fall back on, so it degrades to
  `fallbackMove` (a **random legal move**), trading a non-existent flag risk for a real
  strength hole. The measurement (~0.09s/move; even 20× slower on a phone is ~1.8s against
  a 3+0 budget of ~4.5s/move) is what makes fix (b) legitimate rather than an excuse —
  SEED-100 required exactly this measurement before allowing (b).

### ELO picker + honest labeling

- **D-04 — Expose the full `MAIA_ELO_LADDER`** (600–2600, step 100 — `lib/maiaEncoding.ts:31-58`),
  the same constant the analysis board's `EloSelector` uses. Not narrowed to Maia's
  validated 1100–2000 band: beginners and strong players are exactly the users this
  feature exists for, and `maiaEncoding.ts` already documents the extrapolation caveat.

- **D-05 — Keep the word "ELO", carry the honesty in an info popover.** The number is a
  **Maia conditioning rung**, not a measured strength, and the play-style changes real
  strength by hundreds of points (rung 1500 plays ≈980 at blend 0, ≈1938 at blend 0.5).
  The setup screen gets a `HelpCircle` info popover (existing `MetricStatPopover`-family
  pattern; `text-xs` is permitted inside popover bodies per CLAUDE.md) stating: this is the
  rating band whose **style** the bot imitates, real strength also depends on the play-style
  setting, and calibration is still in progress.

- **D-06 — NO per-mode ELO correction.** Do not map displayed ELO → rung using the
  2026-07-12 harness table. **Every cell in that table is a clamped bound**, the anchors are
  themselves mislabeled (Maia rung ≠ human ELO; the ladder is compressed ~3.3×; search-less
  anchors inflate the blend>0 end), and "correcting" with it manufactures precision we do
  not have. That is SEED-104's job, once SEED-101/102/103 land.

- **D-07 — Default bot ELO = the user's lichess-blitz-equivalent rating, else 1500.**
  Mirrors `hooks/useMaiaEloDefault.ts`'s shipped free-play rule (`FREE_PLAY_DEFAULT_ELO = 1500`,
  clamped to the ladder) but fixes its input: `profile.current_rating` is the **raw platform
  rating** from the user's most recent game (`game_repository.get_current_rating_by_platform`),
  which is inflated for chess.com users.
  - **Add a lichess-blitz-equivalent field to the `/users/me` profile response**, derived
    server-side from `user_rating_anchors.anchor_rating` — already a **blended
    lichess-equivalent median**, and already the number Phase 167 (D-05) trusts to stamp the
    stored bot game's player rating. One field, no new endpoint; the Bots page already calls
    `useUserProfile()`.
  - **Guests / users with no anchor → `null` → 1500 fallback.**
  - **This is a UI DEFAULT, not bot adaptation.** BOT-03 ("the bot's move distribution
    reflects only its own configured ELO and never shifts on any player-strength input")
    still holds: the value is user-visible, user-overridable, and fixed for the game. Say so
    in a code comment so a future reviewer does not flag it as a BOT-03 violation.

- **D-08 — Fix the analysis board's free-play default in this phase too.** Once `/users/me`
  exposes the normalized rating, point `useMaiaEloDefault`'s **free-play branch** at it (its
  game-mode branch is already normalized via Phase 164's `white_rating_lichess_blitz`). A
  one-line change riding on D-07; explicitly approved as scope so the two ELO surfaces agree.

### Setup screen shape + lifecycle

- **D-09 — A pre-game screen on `/bots`, not a modal and not a new route.** No snapshot →
  `/bots` renders the setup screen **instead of** the board; **Start** mounts `BotsGame` with
  the chosen settings. This replaces exactly the D-14 stub branch that 170 left in place, and
  composes with the ResumeGate for free (see D-13). A modal-over-the-board was rejected: the
  hook would have to mount with placeholder settings and remount on Start, throwing the warm
  pool away anyway.

- **D-10 — Last-used settings are remembered, owner-scoped.** Persist (ELO, blend, TC, color)
  to localStorage under an owner-scoped key, reusing 170's `botGameSnapshot` key convention
  (`lib/botGameSnapshot.ts`, `lib/botPendingStore.ts`). A returning user lands on setup with
  their config prefilled and can just hit Start. **Separate key from the in-progress snapshot
  and from the pending-store queue** (170 D-05/D-12 keep those distinct; do not fold settings
  into either).

- **D-11 — "New game" returns to the SETUP screen, prefilled.** Both `GameResultDialog` and
  `GameResultStrip`'s "New game" action goes back to setup with the last settings pre-selected
  (one tap to rematch, but ELO/style/TC/color are right there). This makes the setup screen the
  **single entry point for every new game**, so there is no second start path to keep honest.
  Note this changes today's wiring, where "New game" calls `game.newGame()` for an instant
  same-settings restart.

- **D-12 — Color: White / Black / Random; Random resolves at Start.** `useBotGame` needs a
  concrete `userColor` at mount, so Random is resolved to a real color **before** the hook
  mounts — the snapshot and the exported PGN therefore carry the actual color played, never
  "random".

- **D-13 — Snapshot beats setup; discard falls through to setup.** With a snapshot present the
  ResumeGate wins (170 D-04 unchanged, gate overlays a mounted-but-not-live game so the
  engines warm behind it). **Discard** (170 D-05) now falls through to the **setup screen**
  rather than auto-starting a stub game.

- **D-14 — Time controls: the roadmap's lichess presets, default 10+0 rapid.**
  blitz 3+0 / 3+2 / 5+0 / 5+3 · rapid 10+0 / 10+5 / 15+10 · classical 30+0 / 30+20. **No
  bullet.** Default **10+0** (chosen over today's 5+3 stub: a first bot game on a phone has
  more headroom, and rapid gives the bot's pacing the most slack).

- **D-15 — No engine prewarm during setup.** 169.5 already makes the first plies book moves
  (near-instant, no search) and prewarms the pool **during** that book window; the bot also has
  a full clock at move 1. Hoisting `WorkerPool` / `MaiaQueue` construction out of `useBotGame`
  to warm earlier is real surgery on a hook that just survived three gap-closure rounds — not
  worth it for a masked cold start.

### Nav, guest access, and Library surfacing

- **D-16 — Nav order: Library · Bots · Openings · Endgames.** Bots sits **second**. It is
  never import-locked (see D-17), so placing it 2nd keeps the two always-enabled items together
  and the two import-gated items grouped at the end — for a zero-game or guest user the nav
  reads `Library | Bots | dim | dim` instead of interleaving enabled and dimmed items.

- **D-17 — Bots is NEVER import-locked.** `NavHeader`'s lock rule (`locked = to !== '/library'
  && to !== '/admin' && !navUnlocked`, where `navUnlocked = games > 0 && tier1`) must exempt
  `/bots`. Guests and zero-game users are precisely the audience for free bot play (SC3), and
  the route is already deliberately outside `ImportRequiredRoute`.

- **D-18 — Mobile: Bots joins the bottom bar (4 items + More).** `BOTTOM_NAV_ITEMS` goes from 3
  to 4; with the existing More button that is 5 slots, the standard mobile ceiling. Also add it
  to `MobileMoreDrawer` (it renders `NAV_ITEMS`) and to `ROUTE_TITLES`, and give `isActive()` a
  `/bots` branch. **Apply every nav change to desktop AND mobile** (CLAUDE.md: "Always apply
  changes to mobile too").

- **D-19 — A logged-out visitor at `/bots` keeps redirecting to `/login`.** `/bots` stays inside
  `ProtectedLayout`. "Guest" means the **existing guest-account flow** (Home's `btn-guest` →
  guest JWT), which `POST /bots/games` already accepts (167 D-13). SC3 is met: guests *can* play
  and their games *are* saved. Auto-minting a guest session on a tokenless `/bots` visit, and a
  public "Play as guest / Log in" chooser at `/bots`, were both considered and **deferred** (see
  Deferred Ideas) — neither belongs in a phase already carrying a blocker.

- **D-20 — Post-game: keep the instant Analyze-the-line CTA; ADD a confirmed Saved-to-Library link + the guest caveat.**
  - **"Analyze this game" keeps its current behavior** — `buildAnalysisLineUrl(game.moveHistory)`,
    an immediate client-side deep-link with **no dependency on the POST having landed**.
    Re-pointing it at the stored Library game was rejected: the store is queued and may still be
    pending (offline, 401-retry), so the primary CTA would sometimes have nothing to point at.
  - **Once the store CONFIRMS**, the result surface (`GameResultDialog` / `GameResultStrip`)
    shows a **"Saved to your Library"** affordance linking to the Library Games tab.
  - **Guests additionally get the not-auto-analyzed caveat there** (SC4), reusing the existing
    copy pattern from `components/library/EvalCoverageBadge.tsx` /
    `components/library/analysisCoverageCopy.tsx` / `NoAnalysisState.tsx` — guests can analyze a
    game on demand, they just do not get automatic background analysis. **Do not** put this
    caveat on the setup screen (rejected: it is a downer before the game, and SC4 asks for it at
    game end).

### Amendment (added 2026-07-14, post-RESEARCH)

- **D-21 — Store the finished game ON FINISH, not on next mount.** RESEARCH.md Pitfall 3 found
  that D-20's "once the store CONFIRMS" has **no signal to observe today**: Phase 170 wired
  `finalizeGame()` → `enqueuePendingStore()` (localStorage only, `useBotGame.ts:610`), and the
  actual POST fires only on the **next** `/bots` mount via `useDrainPendingStore`
  (`Bots.tsx:315-322`). As shipped, a "Saved to your Library" row gated on mutation status would
  never appear on the result screen the user is looking at.

  **Resolution (user decision):** add an effect keyed on `game.outcome` becoming non-null that
  calls `useStoreBotGame().mutate()` for the just-finished game, and thread its status down to
  `GameResultDialog` / `GameResultStrip` so D-20's affordance (and the SC4 guest caveat) gate on
  a real `isSuccess`. `useStoreBotGame()` is the right hook (not `useDrainPendingStore`) because
  it already returns the full `UseMutationResult` (`useStoreBotGame.ts:77-86`).

  **The localStorage pending-queue stays** as the offline / 401-retry durability fallback — this
  is an *additional* store trigger, not a replacement for 170's plumbing.

  ⚠ **Double-POST is the risk this decision creates and the plan MUST close it:** the next
  `/bots` mount's drain must not re-POST a game already stored on finish. Dedupe/clear the
  pending entry on store success. A test must pin "finish → store → remount → no second POST".

### Claude's Discretion

- **ELO picker component** — reuse `components/analysis/EloSelector.tsx` if it fits the setup
  screen's layout, otherwise build a setup-specific picker over the same `MAIA_ELO_LADDER`
  constant and the same clamp rule. The ladder + clamp are locked; the widget is not.
- **The "Human preset active" visual convention** — with `blend = 0` the slider thumb has no
  valid position (the slider starts at 0.05). How that reads (dimmed track, summary text like
  "Human — plays on instinct, no calculation", thumb parked at min) is a UI-phase call.
- **Exact copy** for the ELO info popover, the play-style summary line, and the "Saved to your
  Library" / guest-caveat strings.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The blocker (read FIRST)
- `.planning/seeds/SEED-100-blend-zero-bot-has-no-pacing-mechanism.md` — the declared Phase 171
  blocker. D-03 resolves it via the seed's fix (b). Its "Verification note" (prove by mutation,
  not by grep) is binding.
- `.planning/seeds/SEED-099-commitmove-flag-invariant-by-construction.md` — the sibling
  invariant ("the bot can lose on time" is enforced by comment, not construction); named as a
  see-also on the Phase 171 roadmap blocker line.

### Why the ELO label cannot be trusted (drives D-05 / D-06)
- `.planning/notes/2026-07-13-bot-calibration-findings.md` — the four findings behind D-01/D-05/D-06:
  blend is a regime dispatch not a mix (Finding 1), Maia rung ELO ≠ human ELO and the error is not
  a constant offset (Finding 2), every harness cell clamped (Finding 3), 10 games/cell is ±110 ELO
  (Finding 4). **Read this before writing any ELO copy.**
- `reports/data/calibration-harness-2026-07-12T16-34-46-551Z*.tsv` — the raw 3×3 (rung × blend) run
  the note interprets. Bounds, not measurements.

### Prior-phase contracts this phase consumes
- `.planning/phases/170-localstorage-resume/170-CONTEXT.md` — the ResumeGate (D-04), discard-confirm
  (D-05), single-slot snapshot (D-07), the separate pending-store key (D-12), and the explicit
  170/171 boundary ("170 owns the store plumbing, 171 owns the surfaces").
- `.planning/phases/167-backend-store-on-finish/167-CONTEXT.md` — `POST /bots/games` accepts guests
  (D-13), the server derives the player rating from `user_rating_anchors` (D-05/D-06/D-07 — the same
  anchor D-07 here now surfaces on `/users/me`), and the Library Games tab must opt IN to `flawchess`
  games (D-03).
- `.planning/phases/169.5-bot-opening-book/` — the book window + engine prewarm that D-15 relies on.

### Future work this phase must NOT pre-empt
- `.planning/seeds/SEED-098-bot-personas-playstyle-layer.md` — named personas / the 2D
  (aggression × complexity) style layer are a **future milestone**. Its "Caveats" section
  independently confirms D-01's regime-split reasoning.
- `.planning/seeds/SEED-101..104` — the anchor-ladder → iso-strength → lichess-ground-truth →
  inversion-table chain that will eventually make an honest ELO label possible. D-06 defers to it.

### Requirements
- `.planning/REQUIREMENTS.md` — PLAY-01, PLAY-02, PLAY-10 (this phase); BOT-03 (the bot is
  non-adaptive — constrains D-07).
- `.planning/ROADMAP.md` § "Phase 171" — goal, SC1–SC4, and the blocker line.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/filters/PresetRangeFilter.tsx` — the label + info-popover + preset-grid +
  slider + summary shell that `OpponentStrengthFilter` is built on. **D-01's play-style control is
  this same shape, single-thumb.** Read `components/filters/OpponentStrengthFilter.tsx` +
  `lib/opponentStrength.ts` as the worked example (presets ↔ slider value ↔ derived active preset).
- `frontend/src/lib/maiaEncoding.ts` — `MAIA_ELO_LADDER` (600–2600 / step 100) + the extrapolation
  caveat comments that D-05's popover copy should reflect.
- `frontend/src/hooks/useMaiaEloDefault.ts` — the shipped "you are here" ELO default (clamp-to-ladder,
  user-override-wins-permanently). D-07 mirrors its rule; D-08 fixes its free-play input.
- `frontend/src/components/analysis/EloSelector.tsx` — an existing ladder picker (discretionary reuse).
- `frontend/src/components/library/EvalCoverageBadge.tsx`, `analysisCoverageCopy.tsx`,
  `NoAnalysisState.tsx` — the established guest "not analyzed automatically / sign up / analyze on
  demand" copy + CTA pattern D-20 reuses.
- `frontend/src/lib/botGameSnapshot.ts` + `lib/botPendingStore.ts` — the owner-scoped localStorage key
  convention D-10 follows (with its own, separate key).

### Established Patterns
- **Nav lives in `App.tsx`, not a component file** — `NAV_ITEMS`, `BOTTOM_NAV_ITEMS`, `ADMIN_NAV_ITEM`,
  `ROUTE_TITLES`, `isActive()`, `NavHeader`, `MobileBottomBar`, `MobileMoreDrawer` are all defined
  there (~:65-380). Every nav change touches several of them — D-18.
- **The import lock is a render-time rule, not a route guard** (`locked = to !== '/library' && to !==
  '/admin' && !navUnlocked` inside `NavHeader`). D-17 adds `/bots` to that exemption; the route itself
  is already outside `ImportRequiredRoute`.
- **`Bots.tsx` is already split** into `BotsPage` (owner scope, snapshot detection, pending-store drain)
  and `BotsGame` (mounts `useBotGame`). D-09's setup screen slots into `BotsPage`'s "no snapshot" branch;
  `BotsGame` is untouched except that its `settings` now come from setup instead of the stub const.
- **`useBotGame` owns its providers** — `createWorkerPool()` / `createMaiaQueue()` are constructed inside
  the hook's own mount effect (`useBotGame.ts:761-775`), which is exactly why D-15 says no pre-mount warm.
- **`data-testid` on every interactive element**, kebab-case, component-prefixed (CLAUDE.md) — the setup
  screen's pickers, presets, slider, and Start button all need them.

### Integration Points
- `frontend/src/pages/Bots.tsx` — `BOT_GAME_SETTINGS` (the D-14 stub const, ~:45-51) is **deleted**; the
  `boot.resume === null` path renders setup instead of starting a game.
- `frontend/src/App.tsx` — `NAV_ITEMS`, `BOTTOM_NAV_ITEMS`, `ROUTE_TITLES`, `isActive()`, and the
  `NavHeader` lock rule.
- `frontend/src/components/bots/GameResultDialog.tsx` / `GameResultStrip.tsx` — "New game" rewires to
  setup (D-11); the "Saved to your Library" + guest caveat land here (D-20).
- `frontend/src/hooks/useStoreBotGame.ts` — the store confirmation D-20's Library link waits on.
- `app/routers/users.py` + `app/schemas/users.py` — the new lichess-blitz-equivalent profile field
  (D-07), sourced via `user_rating_anchors_repository` (the same path `store_bot_game_service` uses).
- `frontend/src/lib/chessClock.ts` — the false D-16 header comment to correct (D-03) and the synthetic
  reveal delay Human mode rides (D-02).
- `frontend/src/lib/engine/selectBotMove.ts` — **not modified**; D-03 documents and pins its blend-0
  regime rather than changing it.

</code_context>

<specifics>
## Specific Ideas

- **The play-style control should look like the opponent-strength filter.** User's words: "use a
  continuous slider with 0.05 steps. Add the 2 preset buttons on top of it. Same UI as for the opponent
  strength slider (except that this is not a range slider)." → `PresetRangeFilter` shape, single thumb,
  `[Human] [Engine]` buttons above a 0.05–1.00 slider. See D-01 for why 0 is a button, not a slider stop.
- **The ELO default must be lichess-blitz converted.** User caught that `profile.current_rating` is the
  raw platform rating: "make sure the user's rating is converted to lichess blitz. Like we do for the
  analysis board's ELO slider." That turned out to expose a real half-conversion on the analysis board's
  free-play path → D-07 + D-08.

</specifics>

<deferred>
## Deferred Ideas

- **Auto-mint a guest session on a tokenless `/bots` visit** — would make `flawchess.com/bots` a
  shareable, zero-friction funnel. Rejected for this phase (D-19): minting accounts on route visit is a
  real behavior change with abuse/analytics implications. Worth a seed if bot play gets a marketing push.
- **A public "Play as guest / Log in" chooser at `/bots`** — the middle path (keeps the deep-link useful
  without silently creating accounts). Costs a new public route surface outside `ProtectedLayout`.
- **Randomized, position-aware bot reveal delays** (longer on complex positions, instant on recaptures)
  so Human mode's tempo reads as human. Rejected as a new mechanism in a page-shell phase (D-02); revisit
  if UAT says the bot feels robotic.
- **Named bot personas / the 2D style layer** — already captured as
  `.planning/seeds/SEED-098-bot-personas-playstyle-layer.md` (future milestone). The `blend` slider
  shipped here is a **strength** dial, not a style dial; SEED-098 is where real playstyle lives.
- **An honest, calibrated ELO label** — SEED-101 → SEED-102 → SEED-103 → SEED-104. Until that chain
  lands, D-05's popover hedge is the honest answer and D-06 forbids faking it.

</deferred>

---

*Phase: 171-Bots Page + Setup Screen + Nav*
*Context gathered: 2026-07-14*
