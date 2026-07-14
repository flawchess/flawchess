# Phase 171: Bots Page + Setup Screen + Nav - Research

**Researched:** 2026-07-14
**Domain:** Frontend page-shell integration (React/TS) over already-shipped bot-play machinery (Phases 166–170) + one small backend profile-field addition (FastAPI/Pydantic)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Play-style control + the SEED-100 blocker**

- **D-01** — `blend` ships as a preset-plus-slider control, NOT a discrete mode picker. Same UI shape as the existing `OpponentStrengthFilter` (built on `components/filters/PresetRangeFilter.tsx`: label + info popover + preset button grid + slider + summary), but **single-thumb, not a range slider**: two preset buttons (**Human** → `blend = 0` · **Engine** → `blend = 1`), slider spans `0.05–1.00` in `0.05` steps (excludes 0 — reachable only via the Human preset), default `blend = 0.5`. The slider excludes 0 because `selectBotMove.ts:113-146` is a three-way regime dispatch, not a mix: `blend = 0` runs one Maia policy call with no search; anything `> 0` runs full MCTS. `0 → 0.05` is a cliff (~980 → ~1938 ELO at rung 1500); the rest of the axis is a gentle ramp. An earlier three-discrete-mode design was explicitly REVERSED in favor of this slider — do not restore it.
- **D-02** — Human mode keeps the existing pacing. At `blend = 0` the bot resolves in ~0.09s (168.5 measurement). `chessClock.ts` already has a synthetic minimum think/reveal delay for this case (`computeRevealDelayMs`). Ship on it; tune the constant if UAT says it feels robotic — do not add a new pacing mechanism.
- **D-03** — SEED-100 resolved via the seed's fix (b): document + pin, do NOT race the deadline. Required work: (1) correct the false `chessClock.ts` (~:36-39) comment asserting `deadlineSearch.ts` enforces the D-16 deadline "from OUTSIDE the frozen search core" — true only for `blend > 0`; fix the comment and document the exemption on `BotGameSettings.blend`. (2) Pin the behavior with a test that `blend = 0` never consults `deps.search`. (3) Prove it by mutation — revert the fix and confirm the test fails; grep/symbol-presence is NOT acceptable evidence. Fix (a) — racing `selectBotMove` against the deadline — was considered and REJECTED (degrades to `fallbackMove`, a random legal move, on abort).

**ELO picker + honest labeling**

- **D-04** — Expose the full `MAIA_ELO_LADDER` (600–2600, step 100 — `lib/maiaEncoding.ts:31-58`), not narrowed to Maia's validated 1100–2000 band.
- **D-05** — Keep the word "ELO", carry the honesty in an info popover. The number is a Maia conditioning rung, not a measured strength, and play-style changes real strength by hundreds of points. Setup screen gets a `HelpCircle` info popover stating: this is the rating band whose style the bot imitates, real strength also depends on play-style, calibration is in progress.
- **D-06** — NO per-mode ELO correction. Do not map displayed ELO → rung using the 2026-07-12 harness table (every cell is a clamped bound; anchors mislabeled). That is SEED-104's job.
- **D-07** — Default bot ELO = the user's *lichess-blitz-equivalent* rating, else 1500. Mirrors `hooks/useMaiaEloDefault.ts`'s shipped free-play rule but fixes its input: `profile.current_rating` is the raw platform rating (inflated for chess.com users). Add a lichess-blitz-equivalent field to the `/users/me` profile response, derived server-side from `user_rating_anchors.anchor_rating` — already a blended lichess-equivalent median, and the same number Phase 167 (D-05) trusts to stamp the stored bot game's player rating. One field, no new endpoint. Guests / users with no anchor → `null` → 1500 fallback. This is a UI DEFAULT, not bot adaptation (BOT-03 still holds) — document that in a code comment.
- **D-08** — Fix the analysis board's free-play default in this phase too: point `useMaiaEloDefault`'s free-play branch at the same normalized field. A one-line change riding on D-07; explicitly approved scope.

**Setup screen shape + lifecycle**

- **D-09** — A pre-game screen on `/bots`, not a modal and not a new route. No snapshot → `/bots` renders the setup screen instead of the board; Start mounts `BotsGame` with the chosen settings. Replaces exactly the D-14 stub branch. Composes with the ResumeGate for free.
- **D-10** — Last-used settings are remembered, owner-scoped. Persist (ELO, blend, TC, color) to localStorage under an owner-scoped key, reusing `botGameSnapshot.ts`/`botPendingStore.ts`'s convention. **Separate key** from the in-progress snapshot and the pending-store queue.
- **D-11** — "New game" returns to the SETUP screen, prefilled. Both `GameResultDialog` and `GameResultStrip`'s "New game" action goes back to setup with the last settings pre-selected. This changes today's wiring (`game.newGame()` for an instant same-settings restart).
- **D-12** — Color: White / Black / Random; Random resolves at Start (before the hook mounts) — snapshot and PGN carry the actual color played, never "random".
- **D-13** — Snapshot beats setup; discard falls through to setup (not an auto-started stub game).
- **D-14** — Time controls: the roadmap's lichess presets, default 10+0 rapid. blitz 3+0/3+2/5+0/5+3 · rapid 10+0/10+5/15+10 · classical 30+0/30+20. No bullet. Default 10+0 (over today's 5+3 stub).
- **D-15** — No engine prewarm during setup. 169.5 already makes early plies book moves and prewarms during that window; not worth hoisting `WorkerPool`/`MaiaQueue` construction earlier.

**Nav, guest access, and Library surfacing**

- **D-16** — Nav order: Library · Bots · Openings · Endgames. Bots is never import-locked, so placing it 2nd keeps the two always-enabled items together.
- **D-17** — Bots is NEVER import-locked. `NavHeader`'s lock rule (`locked = to !== '/library' && to !== '/admin' && !navUnlocked`) must exempt `/bots`.
- **D-18** — Mobile: Bots joins the bottom bar (4 items + More = 5 slots). Also add to `MobileMoreDrawer`, `ROUTE_TITLES`, and give `isActive()` a `/bots` branch. Apply every nav change to desktop AND mobile.
- **D-19** — A logged-out visitor at `/bots` keeps redirecting to `/login`. `/bots` stays inside `ProtectedLayout`. "Guest" means the existing guest-account flow (Home's `btn-guest` → guest JWT), which `POST /bots/games` already accepts. Auto-minting a guest session on a tokenless `/bots` visit, and a public "Play as guest / Log in" chooser, are both deferred.
- **D-20** — Post-game: keep the instant Analyze-the-line CTA (client-side deep-link, no dependency on the POST landing); ADD a confirmed "Saved to Library" link once the store confirms, plus the guest not-auto-analyzed caveat for guests only, reusing `EvalCoverageBadge.tsx`/`analysisCoverageCopy.tsx`/`NoAnalysisState.tsx`'s copy pattern. Do NOT put the caveat on the setup screen.

### Claude's Discretion

- ELO picker component — reuse `components/analysis/EloSelector.tsx` if it fits, otherwise build a setup-specific picker over the same `MAIA_ELO_LADDER` constant and clamp rule. The ladder + clamp are locked; the widget is not.
- The "Human preset active" visual convention — resolved in UI-SPEC.md (dimmed slider at `opacity-50`, thumb parked at min 0.05, Human summary line shown instead of a numeric value).
- Exact copy for the ELO info popover, play-style summary line, and "Saved to your Library"/guest-caveat strings — resolved in UI-SPEC.md.

### Deferred Ideas (OUT OF SCOPE)

- Auto-mint a guest session on a tokenless `/bots` visit.
- A public "Play as guest / Log in" chooser at `/bots`.
- Randomized, position-aware bot reveal delays (longer on complex positions, instant on recaptures).
- Named bot personas / the 2D style layer (SEED-098, future milestone).
- An honest, calibrated ELO label (SEED-101 → 102 → 103 → 104 chain).
- Bot personas / style axes, strength-map re-calibration (SEED-101/102/103/104), and any change to how the bot chooses moves beyond what SEED-100 requires.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAY-01 | Bot play lives on a new top-level Bots page (nav sibling of Library · Openings · Endgames), lazy-loaded. | App.tsx nav integration points fully mapped (NAV_ITEMS/BOTTOM_NAV_ITEMS/ROUTE_TITLES/isActive/lock-rule exemptions), file:line cited. Route is already lazy-loaded (`App.tsx:45`) and already exists at `/bots` (`App.tsx:741-754`), just unlinked from nav — Phase 171 only adds the nav entries, no new route work. |
| PLAY-02 | User can start a new game from a setup screen choosing ELO, play-style, color, and a lichess-preset time control. | `Bots.tsx`'s `BOT_GAME_SETTINGS` stub branch (`Bots.tsx:290-345`, `boot.resume === null`) mapped as the exact insertion point; `BotGameSettings` field shapes confirmed (`useBotGame.ts:157-169`); TC-preset-to-seconds conversion table derived and cross-checked against `parse_time_control`'s bucket boundaries (see Common Pitfalls — TC bucket mismatch on 30+0). |
| PLAY-10 | Both logged-in users and guests can play bot games and have their finished games saved. | D-19 guest flow confirmed unaffected (route stays inside `ProtectedLayout`, guest JWT already accepted by `POST /bots/games` per Phase 167 D-13). D-20's "Saved to Library" affordance requires wiring a NEW drain trigger at game-finish time — see Common Pitfalls: "store confirmation only happens on next mount today." |

</phase_requirements>

## Summary

This phase is almost entirely **integration work over already-shipped, already-tested machinery** — no new engine logic, no new persistence layer, one new backend field. The four sub-problems are structurally independent and can be planned as separate waves: (1) the SEED-100 documentation+test fix (2-3 files, no runtime behavior change), (2) the backend `/users/me/profile` field addition (2 files + 1 test file, no migration — `user_rating_anchors` already exists), (3) the setup screen itself (new components + `Bots.tsx` rewiring), (4) the nav entries (`App.tsx`, mechanical, well-precedented by the existing Library/Openings/Endgames triple).

The riskiest area is NOT what CONTEXT.md flags as the blocker (SEED-100 already has 80% of its test coverage shipped — see below) but two things CONTEXT.md does not mention: (a) the TC preset "30+0" that D-14 locks as a "classical" preset computes to the **`rapid`** bucket in the frozen, tested `parse_time_control` boundary rule (`estimated <= 1800 → rapid`), which affects both the stored game's TC-bucket column and which rating anchor is looked up for the player-rating derivation; and (b) `useStoreBotGame`'s store confirmation that D-20's "Saved to your Library" link depends on currently only fires on the **next** `/bots` page mount (`useDrainPendingStore` is called once in `BotsPage`'s mount effect), not immediately when the current game finishes — so as currently wired, the affordance would never appear on the same result screen the user is looking at. Both are real, verified findings from reading the code, not restatements of CONTEXT.md.

**Primary recommendation:** Treat this as four small, independently plannable waves (SEED-100 fix → backend field → setup screen → nav), explicitly wire a drain-on-finish trigger for D-20, and treat the TC-bucket mismatch as a documented, accepted quirk (not a bug to fix — `parse_time_control` is frozen, tested, CLAUDE.md-documented behavior from a prior phase) rather than silently letting a tester discover it as a "bug."

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Setup screen (ELO/blend/color/TC pickers) | Browser / Client | — | Pure React state, no server round-trip; settings only leave the browser at Start (into `useBotGame`) and at game-finish (POST). |
| Nav entries (desktop/mobile) | Browser / Client | — | `App.tsx` route/nav tables, no backend involvement. |
| SEED-100 fix (comment + test) | Browser / Client | — | Frontend-only: `chessClock.ts` doc comment, `useBotGame.ts` doc comment, `selectBotMove.test.ts`/possibly `useBotGame.test.ts`. |
| Lichess-blitz-equivalent rating default | API / Backend | Browser / Client | Backend derives+exposes the field (`user_rating_anchors` read); frontend only consumes it as a default value via `useUserProfile()`, already wired. |
| Last-used settings persistence | Browser / Client | — | New localStorage key, same pattern as `botGameSnapshot.ts`/`botPendingStore.ts` — no backend involvement (mirrors those modules' Browser-only design). |
| Store-on-finish + "Saved to Library" confirmation | API / Backend | Browser / Client | `POST /bots/games` (Phase 167, frozen) is the API tier; the frontend tier owns *when* it fires (currently only on next mount — a client-tier gap this phase must close, not a backend change). |
| Guest not-auto-analyzed caveat | Browser / Client | — | Pure copy/conditional render off `profile.is_guest`, already available via `useUserProfile()`. |

## Standard Stack

No new libraries. Every primitive this phase touches already exists in the codebase and is version-pinned by the existing `package.json`/`pyproject.toml`:

### Core (reused, not installed)
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `radix-ui` Slider (via `components/ui/slider.tsx`) | pinned in `package.json` | Single-thumb slider for the play-style control | Already supports single-thumb via `value={[v]}` (confirmed `slider.tsx:20-30` — `_values` derives thumb count from the `value` array length; `EloSelector.tsx:99-107` is a live single-thumb usage example). |
| TanStack Query (`useMutation`/`useQuery`) | pinned in `package.json` | `useStoreBotGame`, `useUserProfile` | Already the store's mutation/query layer app-wide. |
| Pydantic v2 (`BaseModel`) | pinned in `pyproject.toml` | New response field on `UserProfileResponse` | Already the schema layer for `/users/me/profile`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `EloSelector.tsx` as-is | Forking a setup-specific ELO slider | UI-SPEC already resolved this discretion point: reuse as-is (accept the minor "ELO" caption duplication — confirmed `EloSelector.tsx` has NO label-suppression prop, see Common Pitfalls). |
| A new `PlayStyleControl.tsx` sibling of `PresetRangeFilter` | Generalizing `PresetRangeFilter` itself to support single-thumb | UI-SPEC already resolved this: `PresetRangeFilter`'s slider prop is hard-typed to `[number, number]` (`PresetRangeFilterProps.slider.value: [number, number]`, `minStepsBetweenThumbs` required) — a sibling component is less invasive than widening a shared, multi-consumer component's type. |

**Installation:** None — no `npm install` / `uv add` needed this phase.

**Version verification:** N/A — no new packages.

## Package Legitimacy Audit

**Not applicable this phase.** No new npm or pip packages are introduced. UI-SPEC.md confirms: "No new npm dependency, no new shadcn component install needed — every primitive this phase touches... already exists in `components/ui/`." The backend field addition uses only Pydantic v2 and SQLAlchemy 2.x, both already core dependencies.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │  App.tsx (nav tables)                    │
                         │  NAV_ITEMS / BOTTOM_NAV_ITEMS /          │
                         │  ROUTE_TITLES / isActive() /             │
                         │  NavHeader lock-rule exemption           │
                         └───────────────────┬───────────────────────┘
                                              │ Link to="/bots" (never locked)
                                              ▼
                         ┌─────────────────────────────────────────┐
                         │  Bots.tsx :: BotsPage                    │
                         │  useUserProfile() -> ownerKey             │
                         │  readSnapshot(ownerKey) -> boot.resume    │
                         │  useDrainPendingStore(ownerKey).drain()   │◄──┐
                         └───────────────────┬───────────────────────┘   │ (NEW: also
                    boot.resume !== null     │   boot.resume === null    │  fire on
                              │              │                           │  game finish,
                              ▼              ▼                           │  see Pitfall)
                   ┌────────────────┐   ┌───────────────────────────┐   │
                   │ BotsGame        │   │ NEW: SetupScreen           │   │
                   │ (mounted either │   │ ELO / PlayStyle / Color /  │   │
                   │  way; ResumeGate│   │ TC pickers, prefilled from │   │
                   │  overlays until │   │ NEW last-used-settings key │   │
                   │  Resume/Discard)│   └──────────────┬─────────────┘   │
                   └────────┬────────┘                  │ Start           │
                            │                            ▼                │
                            │                  ┌──────────────────┐       │
                            └─────────────────►│ BotsGame (mount)  │       │
                                                │ useBotGame(...)   │       │
                                                └────────┬──────────┘       │
                                                          │ game.outcome    │
                                                          ▼                 │
                                                ┌──────────────────┐        │
                                                │ finalizeGame()    │        │
                                                │ enqueuePendingStore│       │
                                                └────────┬──────────┘       │
                                                          │ (trigger drain) │
                                                          └─────────────────┘
                                                          ▼
                                                ┌──────────────────┐
                                                │ POST /bots/games  │  (Phase 167, frozen)
                                                │ store_bot_game()  │
                                                └────────┬──────────┘
                                                          │ 2xx
                                                          ▼
                                     ┌────────────────────────────────┐
                                     │ GameResultDialog/Strip          │
                                     │ "Saved to your Library" link    │
                                     │ (renders on useStoreBotGame     │
                                     │  status === 'success')          │
                                     │ + guest caveat if is_guest      │
                                     └────────────────────────────────┘
```

### Recommended Project Structure

```
frontend/src/
├── components/bots/
│   ├── PlayStyleControl.tsx      # NEW — sibling of PresetRangeFilter, single-thumb
│   ├── ColorPicker.tsx           # NEW (or inline in SetupScreen) — 3-button chip row
│   ├── TimeControlPicker.tsx     # NEW (or inline) — 3-group chip grid
│   ├── SetupScreen.tsx           # NEW — composes ELO/PlayStyle/Color/TC + Start
│   ├── GameResultDialog.tsx      # MODIFIED — onNewGame rewired, "Saved to Library" row added
│   └── GameResultStrip.tsx       # MODIFIED — same
├── lib/
│   ├── botSetupSettings.ts       # NEW — D-10 last-used-settings localStorage module (sibling of botGameSnapshot.ts)
│   ├── botTimeControlPresets.ts  # NEW — D-14 lichess-preset -> {baseSeconds, incrementSeconds} table
│   └── chessClock.ts             # MODIFIED — D-03 comment fix only
├── hooks/
│   └── useMaiaEloDefault.ts      # MODIFIED — D-08 free-play branch repointed
├── pages/
│   └── Bots.tsx                  # MODIFIED — BOT_GAME_SETTINGS stub deleted, SetupScreen wired into boot.resume===null branch
├── App.tsx                       # MODIFIED — nav entries (D-16/17/18)
└── types/users.ts                # MODIFIED — new field on UserProfile

app/
├── schemas/users.py               # MODIFIED — new field on UserProfileResponse
└── routers/users.py               # MODIFIED — derive + pass the new field (both GET and PUT profile handlers)
```

### Pattern 1: Owner-scoped localStorage module (D-10)

**What:** A new sibling module to `botGameSnapshot.ts`/`botPendingStore.ts` for last-used setup settings, following the exact same shape: SSR guard, try/catch, owner-scoped key (`${PREFIX}${ownerKey ?? 'anon'}`), a type-guard validator, silent-degrade-to-null on any failure.
**When to use:** For the D-10 requirement — read on setup-screen mount to prefill, write on Start.
**Example (pattern from the existing module):**
```typescript
// Source: frontend/src/lib/botGameSnapshot.ts:29-42 (pattern to mirror)
export const BOT_SETUP_SETTINGS_KEY_PREFIX = 'flawchess_bot_setup_settings:';

function settingsKey(ownerKey: string | null | undefined): string {
  return `${BOT_SETUP_SETTINGS_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}
// readSetupSettings/writeSetupSettings follow botGameSnapshot.ts's guard/try-catch
// shape verbatim — NOT botPendingStore.ts's array-queue shape (this is a single
// object, not a bounded queue).
```
Do NOT reuse `BOT_GAME_SNAPSHOT_KEY_PREFIX` or `BOT_PENDING_STORE_KEY_PREFIX` — D-10 explicitly requires a third, separate key.

### Pattern 2: Single-thumb sibling of `PresetRangeFilter` (D-01)

**What:** `PlayStyleControl.tsx` visually matches `PresetRangeFilter`'s shell (label + `InfoPopover` + summary row, preset grid, `Slider`) but is a **new component**, not a prop-variant of `PresetRangeFilter` — that component's `slider` prop is hard-typed to `[number, number]` with a required `minStepsBetweenThumbs` (`PresetRangeFilter.tsx:44-52`), which is a two-thumb-only contract.
**When to use:** For D-01's play-style control specifically; the shape is NOT generically reusable for other single-thumb presets without further generalization (out of scope here).
**Example:**
```typescript
// Source: frontend/src/components/analysis/EloSelector.tsx:99-107 confirms
// components/ui/slider.tsx supports single-thumb via value={[v]}:
<Slider
  min={0.05}
  max={1.00}
  step={0.05}
  value={[blend === 0 ? 0.05 : blend]}  // D-01: thumb parked at min when Human active
  onValueChange={(values) => { const next = values[0]; if (next !== undefined) onChange(next); }}
  thumbLabels={['Play style']}
  className={blend === 0 ? 'opacity-50' : undefined}  // UI-SPEC: dim when Human preset active
/>
```

### Pattern 3: Backend read-only derived profile field (D-07)

**What:** `/users/me/profile` (`app/routers/users.py:68-99` GET, `:102-128` PUT) is a **custom FastAPI router**, NOT a FastAPI-Users-generated route — `UserProfileResponse` is a hand-written Pydantic model built field-by-field in the handler. This resolves the CONTEXT.md-flagged unknown: there is no FastAPI-Users generic-route obstacle to extending the response model.
**When to use:** For D-07's new field.
**Example:**
```python
# Source: app/routers/users.py:68-99 (existing pattern), app/repositories/user_rating_anchors_repository.py:129-175
# Both GET and PUT handlers already call game_repository.get_current_rating_by_platform;
# add one more repository call alongside it:
anchors = await user_rating_anchors_repository.fetch_anchors_for_user(session, user_id=user.id)
blitz_anchor = anchors.get("blitz")  # TimeControlBucket key, NOT a free-text platform key
lichess_blitz_equivalent_rating = blitz_anchor.anchor_rating if blitz_anchor is not None else None
```
`fetch_anchors_for_user` returns a dict keyed by `TimeControlBucket` (`bullet`/`blitz`/`rapid`/`classical`) with ONE row per (user, TC) — D-07 needs specifically the `"blitz"` bucket's `anchor_rating` (the "lichess-blitz-equivalent" the field name promises), not an aggregate across all TCs. A user with only classical/rapid games and zero blitz games gets `None` here — correctly falling to the 1500 fallback per D-07, even though they DO have anchor rows for other buckets. This is the intended "blitz-equivalent" semantic, not a bug — but it means a rapid-only player's default won't reflect their rapid strength, which is a real (if narrow) product tradeoff worth a one-line code comment.

### Pattern 4: Nav-table exemption (D-17)

**What:** The import lock is a render-time boolean computed per nav item, not a route guard (`App.tsx:135` `locked = to !== '/library' && to !== '/admin' && !navUnlocked`). Three near-identical copies of this expression exist (`NavHeader:135`, `MobileBottomBar:300`, `MobileMoreDrawer:386`), each with a SLIGHTLY different left-hand exemption list (`MobileBottomBar`'s omits `/admin` entirely since Admin isn't in `BOTTOM_NAV_ITEMS`).
**When to use:** D-17's exemption must be added to all three, each matching its own existing exemption list (don't copy one verbatim into the others — `NavHeader`/`MobileMoreDrawer` need `&& to !== '/bots'` appended to a 2-clause list, `MobileBottomBar` needs it appended to its 1-clause list).

### Anti-Patterns to Avoid

- **Don't fold the D-10 setup-settings key into `botGameSnapshot.ts`'s key or shape.** D-10 explicitly requires a separate key; `botGameSnapshot.ts`'s `isValidSnapshotShape` requires `pgn`/`whiteClockMs`/etc. fields a settings-only object won't have — reusing the key would break `readSnapshot`'s validator on the very next `/bots` visit (a snapshot-shaped read finding a settings-shaped object would clear it as "corrupt," Sentry-capturing a false positive).
- **Don't thread `tc_preset` as a literal display string ("3+0", "10+5") into `BotGameSettings`/the store request.** `types/bots.ts:22-37`'s own doc comment is an explicit, in-repo warning: sending the minutes-display label directly (instead of converting to base-seconds first) previously caused exactly this bug and was corrected in 170-RESEARCH.md. The setup screen must convert each display preset to `{baseSeconds, incrementSeconds}` via a lookup table BEFORE constructing `BotGameSettings` — see Common Pitfalls below for the exact table.
- **Don't call `game.newGame()` from the result screen's "New game" button anymore (D-11).** Wire "New game" to a callback that unmounts `BotsGame` and shows the setup screen instead (mirroring `BotsPage.handleDiscard`'s `key`-changed remount pattern, `Bots.tsx:329-332`), prefilled from the D-10 last-used-settings key. `useBotGame`'s exposed `newGame()` method itself may become effectively dead from the UI's perspective after this change — flag for the plan whether to keep it (a public hook API, arguably fine to leave unused) or note it as a known no-longer-called export.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Single-thumb preset+slider control | A bespoke slider/preset combo from raw Radix primitives | `PlayStyleControl.tsx` modeled on `PresetRangeFilter.tsx`'s existing shell (label/InfoPopover/summary/preset-grid/Slider composition) | `components/ui/slider.tsx` already handles single- vs dual-thumb via the `value` array length; re-deriving the active/inactive preset-chip styling, the `h-11 sm:h-7` touch-target sizing, and the info-popover wiring from scratch would duplicate `PresetRangeFilter.tsx:90-126` almost verbatim. |
| ELO ladder picker | A new slider bound to `MAIA_ELO_LADDER` | `components/analysis/EloSelector.tsx` (locked by Claude's Discretion resolution in UI-SPEC.md: reuse as-is) | Already derives min/max/step from the ladder, already has a working reset-to-default affordance (`defaultElo`/`onReset` props) that D-07's new default value plugs directly into. |
| Owner-scoped localStorage read/write with corruption recovery | New guard logic | Mirror `botGameSnapshot.ts`'s exact SSR-guard + try/catch + Sentry-once-on-corruption shape | Two Phase 170 modules already solved this; a third bespoke implementation risks re-introducing a bug those modules' RESEARCH/gap-closure rounds already fixed. |
| Guest not-auto-analyzed messaging | New copy/logic | `ANALYSIS_COVERAGE_INFO_COPY` tone (`components/library/analysisCoverageCopy.tsx:13-15`) as the copy model D-20 explicitly cites | Consistency — this is the ONE established place in the app that already explains the guest/auto-analysis tradeoff; a second, differently-worded explanation would confuse a user who's seen both. |

**Key insight:** every "Don't Hand-Roll" item in this phase is "don't re-derive a pattern that Phases 164/167/169/170 already built and tested" — there is no genuinely new UI mechanism in this phase, only new *compositions* of existing ones.

## Common Pitfalls

### Pitfall 1: SEED-100's test may already exist — don't duplicate it, verify + extend it

**What goes wrong:** A plan/executor might assume D-03's "pin the behavior with a test" step means writing a brand-new test from scratch.
**Why it happens:** SEED-100's prose doesn't reference the specific existing test.
**How to avoid:** `frontend/src/lib/engine/__tests__/selectBotMove.test.ts:85-96` ALREADY contains exactly the assertion SEED-100 requires: `describe('selectBotMove — blend=0 (full-human)')` → `it('calls deps.policy exactly once and deps.search zero times', ...)` → `expect(search).toHaveBeenCalledTimes(0)`. This is real, mutation-provable coverage: commenting out `selectBotMove.ts:113-118`'s early-return branch (so `blend <= 0` falls through to the search path) makes this exact test fail with `search` called once instead of zero. **Verified by direct code reading, not by running the mutation** — the plan should still perform the actual revert-and-run mutation proof per project convention (`feedback_mutation_test_gap_closures`), but the test to point the mutation at already exists and does not need to be re-written. What's actually NEW work for D-03: (1) the two comment corrections (`chessClock.ts:36-39`, and a new doc note on `useBotGame.ts:161-162`'s `BotGameSettings.blend` field — NOT `selectBotMove.ts`'s `BotSettings.blend`, which D-03 says is not modified), and (2) explicitly running the mutation-proof recipe as a documented verification step (revert `selectBotMove.ts:113-118`, run `npx vitest run selectBotMove.test.ts -t "blend=0"`, confirm the `toHaveBeenCalledTimes(0)` assertion fails, then re-apply).
**Warning signs:** A plan that says "add a new test file" for this without first grepping `selectBotMove.test.ts` is about to write duplicate coverage.

### Pitfall 2: `useBotGame.test.ts` cannot prove the SEED-100 invariant — it mocks `selectBotMove` entirely

**What goes wrong:** Assuming the hook-level test suite proves the end-to-end wiring (that `buildBotMoveDeps` constructs `createDeadlineSearch` but it's never invoked at blend=0).
**Why it happens:** `useBotGame.test.ts:120-123` mocks `@/lib/engine/selectBotMove` wholesale (`mockSelectBotMove`), and `:129-137` mocks `createDeadlineSearch` as a spy returning `vi.fn()` (never the real wrapped search runner). With `selectBotMove` itself mocked out, the hook-level suite cannot observe whether the REAL `selectBotMove`'s internal regime dispatch would or wouldn't call the wrapped search function — that's structurally invisible from this file.
**How to avoid:** The SEED-100 pin correctly lives at the `selectBotMove.test.ts` unit-boundary level (Pitfall 1), not at the hook level. Do not attempt to add a hook-level "proves the wiring" test unless the plan is prepared to un-mock `selectBotMove` for that one test (a bigger, likely not-worth-it lift given the existing coverage).
**Warning signs:** A hook-level test asserting on `mockCreateDeadlineSearch`'s returned `vi.fn()` being called/not-called is testing the MOCK, not the real invariant.

### Pitfall 3: D-20's "Saved to your Library" affordance has no trigger to observe today

**What goes wrong:** Implementing the `GameResultDialog`/`GameResultStrip` "Saved to your Library" row gated on `useStoreBotGame()`'s mutation `status === 'success'` (per UI-SPEC), but never actually calling that mutation (or an equivalent drain) when the CURRENT game finishes — so the row never appears on the screen the user is looking at.
**Why it happens:** The store-on-finish flow, as shipped by Phase 170, is: `finalizeGame()` → `enqueuePendingStore()` (writes to localStorage only, `useBotGame.ts:610`) → **nothing else happens until the NEXT `/bots` page mount**, where `BotsPage`'s `useDrainPendingStore(ownerKey).drain()` effect (`Bots.tsx:315-322`, gated by `hasDrainedRef`, fires once per mount) POSTs the queued entry. There is currently no code path that drains/stores the just-finished game while the user is still viewing its result screen.
**How to avoid:** This phase needs to add ONE of: (a) call `drain()` again (or a fresh `useStoreBotGame().mutate()`) from an effect keyed on `game.outcome` becoming non-null (so it fires once the current game ends, without waiting for a remount), or (b) accept and explicitly design for "Saved to Library" only appearing after a page revisit (contradicts UI-SPEC's framing of it as a same-screen affordance gated on live mutation status). Option (a) is almost certainly the intended reading of D-20/UI-SPEC given the "renders once `useStoreBotGame`'s mutation status is `success`" framing — the plan should wire a call to `useStoreBotGame()`'s `mutate`/`mutateAsync` (or the existing `useDrainPendingStore`) at the finish transition, and pass the resulting `status` down to `GameResultDialog`/`GameResultStrip`. Note `useDrainPendingStore`'s internal `mutateAsync` doesn't expose per-status data to the caller today (`useStoreBotGame.ts:116-140`) — likely `useStoreBotGame()` itself (not `useDrainPendingStore`) is the right hook to call directly for the just-finished game, since it already returns the full `UseMutationResult` (status/isSuccess/etc, `useStoreBotGame.ts:77-86`).
**Warning signs:** A plan that treats D-20 as "just add a conditional render on `useStoreBotGame().status`" without ALSO adding the missing `.mutate()` call site will ship a feature that silently never activates in manual testing on a fresh browser profile (it would only activate on a SECOND visit to `/bots` after the game already finished, by which point the result dialog is gone).

### Pitfall 4: The "30+0" classical TC preset computes to the `rapid` bucket, not `classical`

**What goes wrong:** Assuming D-14's three labeled groups (Blitz/Rapid/Classical) correspond 1:1 to the backend's three TC-bucket enum values for every preset.
**Why it happens:** `parse_time_control`'s frozen, tested boundary rule is `estimated <= 1800 → rapid`, `estimated > 1800 → classical` (`app/services/normalization.py:96-101`, exhaustively tested and DOCUMENTED as intentional at `tests/test_normalization.py:101-106`: `"""Exactly 1800s -> rapid."""`, and restated in CLAUDE.md's own "Time control bucketing" line). "30+0" → `baseSeconds=1800, incrementSeconds=0` → `estimated = 1800 + 0*40 = 1800` → bucket = **`rapid`**, not `classical`. "30+20" → `estimated = 1800 + 20*40 = 2600` → `classical`, correctly. So of D-14's two "classical" presets, only ONE actually buckets as classical.
**How to avoid:** This is NOT something to fix in Phase 171 — `parse_time_control` is frozen, shared, tested logic outside this phase's scope, and CONTEXT.md does not ask for it to change. But the planner/executor MUST know it, because it has two real, verifiable downstream effects: (1) `store_bot_game_service.store_bot_game` (`app/services/store_bot_game_service.py:76-78`) looks up the player's rating anchor by this SAME bucket — a user who only has classical-rated imported games and picks the "30+0" bot preset will have their rating derived from their `rapid` anchor (possibly `None` if they have no rapid games at all, correctly falling to the null/no-rating-source path per D-05/D-06 of Phase 167, but NOT for the reason a reader would expect from the UI's "classical" label); (2) the stored `games.time_control_bucket` column for that bot game is `rapid`, so it will show up under a "rapid" filter in the Library, not "classical," despite the setup screen having labeled it Classical. Document this as an accepted, known quirk (a one-line code comment at the TC-preset-to-seconds table is the right place) rather than letting it surface as a confusing "bug" during UAT.
**Warning signs:** A UAT tester picking the "30+0" preset and later filtering the Library by "Classical" not finding the game.

### Pitfall 5: `EloSelector.tsx` has no label-suppression escape hatch

**What goes wrong:** Assuming a prop exists to hide `EloSelector`'s own inline "ELO" caption + `EloInfoTooltip` so the setup screen's own D-05 label+popover can stand alone without visual duplication.
**Why it happens:** UI-SPEC.md flagged this as something to "check at plan time." Confirmed by direct read: `EloSelectorProps` (`EloSelector.tsx:18-32`) has exactly `value`, `onChange`, `defaultElo`, `onReset`, `ladder` — no `hideLabel`/`showLabel`/`children` override. The component unconditionally renders its own `<span>ELO</span>` + `EloInfoTooltip()` (`:95-98`) with copy hard-coded for the analysis-board context ("The engines play at this rating... defaults to the mover's rating"), which is wrong for the bot-setup context per D-05.
**How to avoid:** Per UI-SPEC.md's already-resolved discretion: accept the minor duplication (setup screen renders its OWN "Bot strength (ELO)" label + D-05's info popover ABOVE/BESIDE the unmodified `EloSelector`, which will additionally show its own smaller "ELO" caption + a DIFFERENT (wrong-context) tooltip). Do NOT edit `EloSelector.tsx`'s copy — it's shared with `/analysis` and Phase 164's normalized-rating framing is correct there. Do NOT fork the component this phase — `EloSelector.tsx`'s tooltip text is out of scope for D-05.
**Warning signs:** A plan task that edits `EloSelector.tsx`'s copy directly would silently change the `/analysis` page's ELO tooltip too — a scope violation and an untested cross-page regression.

### Pitfall 6: Route-title / notification-dot symmetry — `/bots` intentionally does NOT need a red dot

**What goes wrong:** Copy-pasting the `showOpeningsDot`/`showEndgamesDot` "unvisited" notification-dot pattern onto `/bots` by analogy.
**Why it happens:** Every other unlocked-on-import nav item (`Openings`, `Endgames`) gets a red dot until first-visit. `/bots` is structurally different: it's never import-locked, so the `navUnlocked` gate these dots key off doesn't apply, and UI-SPEC.md explicitly states "Bots carries no 'new content' badge in this phase."
**How to avoid:** Do not add a `showBotsDot`/`useUserFlag(FLAG_BOTS_VISITED, ...)` pattern. This is locked by UI-SPEC, not left to discretion.

## Code Examples

### D-03: chessClock.ts corrected D-16 header comment (illustrative diff)

```typescript
// Source: frontend/src/lib/chessClock.ts:34-39 (current, false for blend=0)
// CURRENT (false at blend=0):
 * D-16: an honest clock with a *fixed* search budget is degenerate ... So the bot
 * manages its clock via `computeThinkDeadlineMs` below, a per-move think deadline
 * derived from its own remaining time, that `deadlineSearch.ts` (plan 08 task 2)
 * enforces from OUTSIDE the frozen search core by cutting the in-flight search and
 * returning its best-so-far result.

// CORRECTED (Phase 171 D-03):
 * D-16: an honest clock with a *fixed* search budget is degenerate ... So the bot
 * manages its clock via `computeThinkDeadlineMs` below, a per-move think deadline
 * derived from its own remaining time, that `deadlineSearch.ts` (plan 08 task 2)
 * enforces from OUTSIDE the frozen search core by cutting the in-flight search and
 * returning its best-so-far result — ONLY WHEN `deps.search` is actually consulted
 * (blend > 0). At `blend = 0` (SEED-100, Phase 171 D-03) `selectBotMove.ts` returns
 * from a single Maia policy sample BEFORE `deps.search` is ever called, so this
 * deadline is computed (`useBotGame.ts` still calls `computeThinkDeadlineMs` and
 * builds `deadlineSearch` unconditionally) but never enforced — a Human-preset bot
 * has an honest, flaggable clock with NO pacing mechanism of its own; its speed is
 * governed entirely by `computeRevealDelayMs`'s reveal-delay floor (D-02) and the
 * measured ~0.09s Maia inference cost, both of which stay well under any realistic
 * blitz/rapid budget (see SEED-100). Pinned by selectBotMove.test.ts's blend=0
 * "deps.search zero times" assertion — do not restore a smaller ad-hoc claim here.
```

### D-07: backend field addition (both handlers)

```python
# Source: app/routers/users.py:68-99, :102-128; app/schemas/users.py:10-32
# app/schemas/users.py — add to UserProfileResponse:
class UserProfileResponse(BaseModel):
    ...
    current_rating: int | None = None
    # D-07 / Phase 171: lichess-blitz-equivalent rating, derived from the user's
    # blitz-bucket user_rating_anchors row (already the blended lichess-equivalent
    # median Phase 167 trusts for bot-game rating derivation). None for guests and
    # users with no blitz-bucket anchor (e.g. rapid/classical-only players) — the
    # frontend falls back to 1500 (D-07). UI-DEFAULT ONLY: never fed into bot move
    # selection (BOT-03) — see useBots setup-screen wiring comment.
    lichess_blitz_equivalent_rating: int | None = None

# app/routers/users.py — both get_profile and update_profile need this added
# alongside the existing `ratings = await game_repository.get_current_rating_by_platform(...)` line:
from app.repositories import user_rating_anchors_repository
...
anchors = await user_rating_anchors_repository.fetch_anchors_for_user(session, user_id=user.id)
blitz_anchor = anchors.get("blitz")
lichess_blitz_equivalent_rating = blitz_anchor.anchor_rating if blitz_anchor is not None else None
# ... then pass lichess_blitz_equivalent_rating=lichess_blitz_equivalent_rating into
# both UserProfileResponse(...) constructions (lines ~84-99 and ~113-128).
```

### D-14: TC preset lookup table (frontend)

```typescript
// NEW file, e.g. frontend/src/lib/botTimeControlPresets.ts
// Source values cross-checked against app/services/normalization.py:58-101
// (parse_time_control) and frontend/src/lib/botGamePgn.ts:112-114 (toBackendTcStr).
export interface TimeControlPreset {
  label: string;           // lichess-style display, e.g. "10+5"
  baseSeconds: number;     // feeds BotGameSettings.baseSeconds directly
  incrementSeconds: number;
  bucket: 'blitz' | 'rapid' | 'classical'; // UI grouping label ONLY — see Pitfall 4:
  // 'classical' here for 30+0 does NOT match the backend's computed tc_bucket
  // (which will be 'rapid' for that one preset — accepted, documented quirk).
}

export const TIME_CONTROL_PRESETS: readonly TimeControlPreset[] = [
  { label: '3+0',  baseSeconds: 180,  incrementSeconds: 0,  bucket: 'blitz' },
  { label: '3+2',  baseSeconds: 180,  incrementSeconds: 2,  bucket: 'blitz' },
  { label: '5+0',  baseSeconds: 300,  incrementSeconds: 0,  bucket: 'blitz' },
  { label: '5+3',  baseSeconds: 300,  incrementSeconds: 3,  bucket: 'blitz' },
  { label: '10+0', baseSeconds: 600,  incrementSeconds: 0,  bucket: 'rapid' },
  { label: '10+5', baseSeconds: 600,  incrementSeconds: 5,  bucket: 'rapid' },
  { label: '15+10',baseSeconds: 900,  incrementSeconds: 10, bucket: 'rapid' },
  { label: '30+0', baseSeconds: 1800, incrementSeconds: 0,  bucket: 'classical' }, // see Pitfall 4
  { label: '30+20',baseSeconds: 1800, incrementSeconds: 20, bucket: 'classical' },
] as const;

export const DEFAULT_TC_PRESET_LABEL = '10+0'; // D-14 default
```

### D-08: useMaiaEloDefault free-play branch fix

```typescript
// Source: frontend/src/hooks/useMaiaEloDefault.ts:42-45, :100-103
// CURRENT MaiaEloProfile shape:
export interface MaiaEloProfile {
  current_rating: number | null;
}
// ...
return profile?.current_rating ?? FREE_PLAY_DEFAULT_ELO;

// AFTER D-08 (mirrors the field D-07 adds to types/users.ts's UserProfile):
export interface MaiaEloProfile {
  current_rating: number | null;
  lichess_blitz_equivalent_rating: number | null;
}
// ...
return profile?.lichess_blitz_equivalent_rating ?? FREE_PLAY_DEFAULT_ELO;
```
Analysis.tsx's `profile` object (from `useUserProfile()`) already structurally satisfies the widened `MaiaEloProfile` interface once `types/users.ts`'s `UserProfile` gains the new field (D-07) — no separate wiring needed at the `Analysis.tsx` call site beyond this one-line change inside the hook.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended new-file names (`PlayStyleControl.tsx`, `botSetupSettings.ts`, `botTimeControlPresets.ts`, `SetupScreen.tsx`) are illustrative, not locked — CONTEXT.md/UI-SPEC.md do not name these files. | Recommended Project Structure | Low — purely a naming choice for the planner; no functional impact if renamed. |
| A2 | Option (a) in Pitfall 3 (calling `useStoreBotGame()` directly at game-finish, in addition to/instead of relying solely on `useDrainPendingStore`) is the correct fix for the missing drain-on-finish trigger. | Common Pitfalls, Pitfall 3 | Medium — if the planner instead wires a second `useDrainPendingStore(ownerKey).drain()` call keyed on `game.outcome`, that also works (it drains the SAME queue, just via a different hook instance) and is arguably more consistent with "the queue is the only path to the server." Either resolves the gap; the choice affects only which mutation's `status` the result-screen components read from. |
| A3 | `blitz_anchor.anchor_rating` (D-07's chosen field) is what CONTEXT.md means by "lichess-blitz-equivalent rating," as opposed to some other blend of the user's anchors across TC buckets. | Pattern 3, Code Examples D-07 | Low — CONTEXT.md D-07 explicitly says "derived server-side from `user_rating_anchors.anchor_rating`" without specifying which bucket; picking `blitz` is the only reading consistent with the field's name and with Phase 164's precedent (`normalize_to_lichess_blitz`). Flagging only because CONTEXT.md doesn't spell out the bucket key explicitly. |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Should `useBotGame`'s `newGame()` export be removed, deprecated, or left as unused-but-public after D-11?**
   - What we know: D-11 says "New game" no longer calls `game.newGame()`; the setup screen becomes the single entry point.
   - What's unclear: whether any other call site (tests, a future feature) still needs direct in-place restart, and whether leaving it unused trips `npm run knip` (hooks are often knip-exempt as public API, but worth a plan-time check).
   - Recommendation: leave it in place (cheap, doesn't block anything), have the plan explicitly note it's no longer called from the UI, and let `npm run knip` be the arbiter during the pre-merge gate.

2. **Does `useDrainPendingStore`'s existing internal `useMutation` (no exposed status) need to be refactored, or is a second `useStoreBotGame()` call the cleaner fix for Pitfall 3?**
   - What we know: `useDrainPendingStore` (`useStoreBotGame.ts:116-140`) has its own private `mutateAsync` with no status exposed to the caller; `useStoreBotGame()` (`:77-86`) returns the full `UseMutationResult`.
   - What's unclear: whether calling BOTH (the mount-time drain AND a finish-time direct store) could double-POST the same game. It should be safe — `store_bot_game` is idempotent on `game_uuid` (Phase 167 D-11, confirmed at `store_bot_game_service.py:57-59`) and `enqueuePendingStore`/`removePendingStore` (`botPendingStore.ts:94-117`) are themselves idempotent — but the plan should explicitly verify this rather than assume it.
   - Recommendation: plan a small dedicated task for "wire a finish-time store call + surface its status to the result screen," with an explicit test asserting no double-row is created (reusing Phase 167's existing idempotency test pattern).

## Environment Availability

Not applicable — this phase has no new external dependencies. All work targets already-running services (dev PostgreSQL via `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`, already a documented CLAUDE.md prerequisite) and already-installed packages.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Frontend framework | Vitest 4.1.7 + @testing-library/react (confirmed `frontend/package.json:13-14,54-69`) |
| Backend framework | pytest + pytest-asyncio, per-run isolated DB (`tests/conftest.py`, CLAUDE.md "Test isolation" section) |
| Config file | `frontend/vite.config.ts` (vitest config colocated); `pyproject.toml`/`pytest.ini`-equivalent for backend |
| Quick run (frontend, one file) | `npx vitest run <path> -t "<name>"` (pattern already used by `useBotGame.test.ts`'s own docstring, e.g. `-t "bot-clock"`) |
| Quick run (backend, one file) | `uv run pytest tests/test_users_router.py -k TestProfileCurrentRating` |
| Full suite (frontend) | `npm test` (`vitest run`) |
| Full suite (backend) | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAY-01 | `/bots` appears in desktop nav, mobile bottom bar, and mobile more-drawer; never shows `aria-disabled`/dimmed regardless of `navUnlocked` | unit (RTL) | new assertions in an `App.test.tsx`-equivalent (none currently exists — see Wave 0 Gap) | ❌ Wave 0 |
| PLAY-01 | `isActive('/bots', pathname)` returns true for `/bots` and any future `/bots/*` sub-route | unit | same file | ❌ Wave 0 |
| PLAY-02 | Setup screen renders ELO/PlayStyle/Color/TC pickers; Start constructs a correct `BotGameSettings` (esp. TC preset → `{baseSeconds, incrementSeconds}` conversion per Pitfall 4's table) | unit (RTL) | `npx vitest run SetupScreen.test.tsx` (new file) | ❌ Wave 0 |
| PLAY-02 | D-12 Random color resolves to a concrete color BEFORE `useBotGame` mounts (never literally "random" in settings/PGN) | unit | same file | ❌ Wave 0 |
| PLAY-02 | D-10 last-used settings persist and prefill on next setup-screen mount, under a key distinct from `botGameSnapshot`/`botPendingStore` | unit | new `botSetupSettings.test.ts` | ❌ Wave 0 |
| PLAY-10 | Guest (`profile.is_guest === true`) can reach `/bots`, play, and finish a game; the guest caveat appears post-finish | unit (guest caveat render logic) + **HUMAN-UAT** (full guest game flow through a real browser, since it spans localStorage + a real POST + auth state) | unit: `GameResultDialog.test.tsx` render-gating assertions; HUMAN-UAT: full click-through | ❌ Wave 0 (unit); HUMAN-UAT always required |
| PLAY-10 | Finished game reaches `/bots/games` and appears in the Library Games tab | integration-ish (mocked `botsApi.storeGame`) + **HUMAN-UAT** (real POST against dev DB, then visually confirm in `/library/games`) | unit: assert `useStoreBotGame`/drain call fires on `game.outcome` transition; HUMAN-UAT: manual | ❌ Wave 0 (unit) |
| D-03/SEED-100 | `blend = 0` never consults `deps.search` (mutation-provable) | unit | `npx vitest run selectBotMove.test.ts -t "blend=0"` | ✅ Exists (`selectBotMove.test.ts:85-96`) — see Pitfall 1 |
| D-07 | `/users/me/profile` returns `lichess_blitz_equivalent_rating`: null with no anchor, correct value with a blitz anchor, null with only non-blitz anchors | unit (backend) | `uv run pytest tests/test_users_router.py -k lichess_blitz` (new test class, pattern at `test_users_router.py:297-368`) | ❌ Wave 0 |
| D-17 | `/bots` nav link is never `aria-disabled` regardless of `navUnlocked` state (zero-game AND guest AND fully-imported states) | unit (RTL) | same `App.test.tsx`-equivalent as PLAY-01 | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** the relevant `-t`/`-k` scoped test file(s) only.
- **Per wave merge:** `npm test` (frontend) + `uv run pytest -n auto` (backend, if the D-07 wave touches backend).
- **Phase gate:** full pre-merge gate per CLAUDE.md before squash-merge to `main` (`ruff format`, `ruff check --fix`, `ty check`, `pytest -n auto -x`, `npm run lint && npm test -- --run`).

### Wave 0 Gaps

- [ ] `frontend/src/App.test.tsx` (or equivalent) — no existing test file covers `NAV_ITEMS`/`BOTTOM_NAV_ITEMS`/lock-rule rendering at all today (confirmed: no `App.test.*` file exists in `frontend/src`). This phase is the natural place to add the FIRST such test, covering both the new `/bots` entries AND (as a byproduct) locking in the existing Library/Openings/Endgames lock-rule behavior so a future nav change doesn't regress it silently.
- [ ] `frontend/src/components/bots/SetupScreen.test.tsx` — new.
- [ ] `frontend/src/lib/botSetupSettings.test.ts` — new (mirror `botGameSnapshot.test.ts`'s existing test shape if that file exists — confirm at plan time).
- [ ] `tests/test_users_router.py` — extend with a `TestProfileLichessBlitzEquivalentRating` class mirroring `TestProfileCurrentRating` (`:297-368`), using `user_rating_anchors_repository.upsert_anchor` (pattern at `tests/services/test_store_bot_game_service.py:21-30`) to seed anchor rows.
- [ ] Framework install: none — Vitest/pytest already configured.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (unchanged) | Existing FastAPI-Users guest/regular JWT flow, untouched by this phase. |
| V3 Session Management | No (unchanged) | — |
| V4 Access Control | Yes (narrow) | The new `lichess_blitz_equivalent_rating` field is read via `current_active_user`'s own `user.id` (`app/routers/users.py:71`, `:106`) — same pattern as the existing `current_rating` field; `fetch_anchors_for_user` already enforces "V4 Information Disclosure mitigation: user_id keyword-only, never from client input" per its own docstring (`user_rating_anchors_repository.py:17-23`). No new access-control surface — this phase reads through an already-hardened repository function. |
| V5 Input Validation | Yes | The setup screen's TC preset, color, and play-style values are all drawn from FIXED, closed sets (9 TC presets, 3 colors, a `[0.05,1.00]` step-`0.05` slider clamped client-side) — no free-text input reaches the backend from this phase's new UI. The existing `StoreBotGameRequest` Pydantic schema (Phase 167, unchanged) already validates the wire payload server-side regardless of what the client sends. |
| V6 Cryptography | No | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A malicious/buggy client sending an out-of-range `blend`/`bot_elo`/`tc_preset` directly to `POST /bots/games`, bypassing the setup screen's UI clamps | Tampering | Already mitigated — `StoreBotGameRequest`'s Pydantic `Field(ge=..., le=...)` bounds (Phase 167, `app/schemas/bots.py`) and `parse_time_control`'s graceful `(None, None)` fallback on unparseable strings are server-side and unaffected by this phase's frontend-only changes. No new server-side validation needed. |
| Cross-account leakage of the new `/users/me/profile` field | Information Disclosure | Already mitigated by the existing `current_active_user` dependency + `fetch_anchors_for_user`'s keyword-only `user_id` contract (see V4 row above) — this phase adds a read through an already-hardened path, introducing no new exposure surface. |

## Sources

### Primary (HIGH confidence — direct code reads this session)
- `frontend/src/lib/engine/selectBotMove.ts` — full file read, regime dispatch confirmed lines 97-147.
- `frontend/src/lib/chessClock.ts` — full file read, false comment at lines 34-51 (specifically 36-39).
- `frontend/src/lib/engine/deadlineSearch.ts` — full file read.
- `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` — full file read, existing SEED-100-relevant test at lines 85-96.
- `frontend/src/hooks/__tests__/useBotGame.test.ts` — lines 1-260 read, mocking shape at lines 118-241.
- `frontend/src/hooks/useBotGame.ts` — lines 1-50, 140-330, 1080-1250 read.
- `.planning/seeds/SEED-100-blend-zero-bot-has-no-pacing-mechanism.md` — full file read.
- `.planning/seeds/SEED-099-commitmove-flag-invariant-by-construction.md` — full file read.
- `app/routers/users.py`, `app/schemas/users.py` — full files read; confirmed custom (non-FastAPI-Users-generated) route.
- `app/repositories/user_rating_anchors_repository.py`, `app/models/user_rating_anchors.py` — full files read.
- `app/services/store_bot_game_service.py` — full file read.
- `app/services/normalization.py` lines 1-100, 535-595 — `parse_time_control`/`normalize_flawchess_game` read.
- `tests/test_normalization.py` (`parse_time_control` boundary tests, grep-confirmed lines 101-113), `tests/services/test_store_bot_game_service.py` lines 1-60.
- `tests/test_users_router.py` lines 290-369 — existing `current_rating` test pattern.
- `frontend/src/pages/Bots.tsx` — full file read.
- `frontend/src/App.tsx` — lines 40-360, 555-756 read.
- `frontend/src/components/bots/GameResultDialog.tsx`, `GameResultStrip.tsx` — full files read.
- `frontend/src/hooks/useStoreBotGame.ts` — full file read.
- `frontend/src/lib/botPendingStore.ts`, `frontend/src/lib/botGameSnapshot.ts` — read (snapshot file partial, lines 1-100).
- `frontend/src/components/filters/PresetRangeFilter.tsx`, `OpponentStrengthFilter.tsx`, `frontend/src/lib/opponentStrength.ts` — full files read.
- `frontend/src/lib/maiaEncoding.ts` lines 1-70 — `MAIA_ELO_LADDER` read.
- `frontend/src/components/analysis/EloSelector.tsx` — full file read.
- `frontend/src/components/ui/slider.tsx` — full file read, single-thumb support confirmed lines 20-30.
- `frontend/src/hooks/useMaiaEloDefault.ts` — full file read.
- `frontend/src/types/users.ts`, `frontend/src/hooks/useUserProfile.ts` — full files read.
- `frontend/src/types/bots.ts` — full file read; the "don't pass a display-label TC string" warning is verbatim in-repo (lines 22-37).
- `frontend/src/components/library/analysisCoverageCopy.tsx`, `EvalCoverageBadge.tsx` — partial reads.
- `frontend/src/pages/library/LibraryPage.tsx` — grep-confirmed `/library/games` route.
- `app/services/library_service.py` lines 662-704 — grep-confirmed flawchess platform included by default in `get_library_games`.
- `.planning/phases/171-bots-page-setup-screen-nav/171-CONTEXT.md`, `171-UI-SPEC.md` — full files read.
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (Phase 171 section + progress table) — read.
- `.planning/STATE.md` — lines 1-227 read.

### Secondary (MEDIUM confidence)
- None — all findings this session were verified by direct code reads against the current working tree, not web search or training-data recall.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, every reused primitive directly read and confirmed.
- Architecture: HIGH — every integration point (Bots.tsx, App.tsx, useBotGame.ts, useStoreBotGame.ts, backend users.py) read in full or targeted excerpt; two non-obvious findings (Pitfalls 3 and 4) surfaced by tracing actual data flow, not assumed.
- Pitfalls: HIGH for Pitfalls 1, 2, 4, 5, 6 (directly verified against code/tests); MEDIUM for Pitfall 3's exact fix mechanism (the GAP is HIGH-confidence-verified, but the best remediation — Assumption A2 — has two viable options).

**Research date:** 2026-07-14
**Valid until:** 30 days (stable internal codebase, no external API/library version risk this phase) — but effectively pinned to the current state of `main` at commit `3df04da5`/`a5e9f610`/`46c53261`/`b906651b` (this branch's parent history); re-verify file:line citations if `main` advances significantly before planning executes.
