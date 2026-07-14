---
phase: 171-bots-page-setup-screen-nav
fixed_at: 2026-07-14T15:20:00Z
review_path: .planning/phases/171-bots-page-setup-screen-nav/171-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 171: Code Review Fix Report

**Fixed at:** 2026-07-14
**Source review:** `.planning/phases/171-bots-page-setup-screen-nav/171-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 9
- Fixed: 9
- Skipped: 0
- Info findings (6): out of scope (`fix_scope: critical_warning`), untouched — see below

**Verification gate (all green, run after the last commit):**
- `npx tsc -b` — clean
- `npm run lint` — 0 errors (3 pre-existing warnings, all in generated `coverage/` artifacts, not phase files)
- `npm run knip` — clean
- `npm test -- --run` — **164 files, 2122 tests, all passing**
- Backend gate not run: **no backend file was touched** (see WR-04 for why the backend half was deliberately deferred).

## Fixed Issues

### CR-01: Finish-time store POST retries forever on HTTP 401 (BLOCKER)

**Files modified:** `frontend/src/hooks/useStoreBotGame.ts`, `frontend/src/hooks/__tests__/useStoreBotGame.test.ts`, `frontend/src/pages/__tests__/Bots.test.tsx`
**Commit:** `4f0910ab`
**Applied fix:** Removed the unbounded `if (status === STATUS_UNAUTHORIZED) return true;` branch from `shouldRetryStore`, so a 401 is now bounded at `MAX_STORE_RETRIES` like every other non-422 failure. The durable retry is the D-13 next-visit drain (which keeps the pending entry on a 401), so the in-flight loop bought nothing. Also corrected `useDrainPendingStore`'s docstring, which justified itself by citing the now-removed unbounded branch.

**Confirmed the bug was real, not theoretical.** With the fix reverted, the new production-call-site test records **763 calls** to `POST /bots/games` where 3 are expected. Both new tests go red on revert:
- `useStoreBotGame.test.ts` — predicate now pins the bound (`shouldRetryStore(10, axiosError(401)) === false`).
- `Bots.test.tsx` — the missing 401 test at the production call site: asserts a frozen call count of `MAX_STORE_RETRIES + 1` **and** that the pending entry survives for the next-visit drain.

**Note on the test's own honesty:** a naive "wait 300ms, assert count is frozen" probe would have **passed even with the bug**, because TanStack's default backoff (1s, 2s, 4s…) puts the 4th call well outside that window. The test therefore pins `retryDelay` to 10ms in the test QueryClient, so the freeze probe spans ~30 would-be retry windows and an unbounded loop cannot hide inside it.

### WR-01: `readSetupSettings` validated types but not value ranges

**Files modified:** `frontend/src/lib/botSetupSettings.ts`, `frontend/src/lib/__tests__/botSetupSettings.test.ts`
**Commit:** `6520af0a`
**Applied fix:** `isValidSetupSettingsShape` now range-checks `botElo` against the `MAIA_ELO_LADDER` bounds and `blend` against `HUMAN_BLEND..ENGINE_BLEND` (bounds derived, not literals). Out-of-range values are corruption and take the existing clear-and-Sentry path, instead of flowing through to `selectBotMove` (negative `tau` above blend 1) and then a backend 422 — which the drain reads as "remove the entry", silently destroying the finished game. NaN/Infinity are rejected by the same comparisons. Tests cover both out-of-range directions per field, NaN, and the inclusive boundary values.

### WR-02: `resolveDefaultBotElo` hard-coded `step = 100`

**Files modified:** `frontend/src/lib/botSetupSettings.ts`, `frontend/src/lib/__tests__/botSetupSettings.test.ts`
**Commit:** `1a76929c`
**Applied fix:** Replaced the arithmetic snap with a nearest-rung **search** over `MAIA_ELO_LADDER`. This needs no step constant at all and is correct for a non-uniform ladder, so it cannot drift from the ladder whose bounds the same function derives. Ties resolve upward (`<=`) to preserve the existing round-half-up behaviour (1650 → 1700, an existing test). The new test pins the **invariant** (`result ∈ MAIA_ELO_LADDER` for every rating across and beyond the ladder) rather than the arithmetic — the property `EloSelector`'s prop contract actually requires.

### WR-03: `useBotGame.newGame` dead in production; the comment asserting knip guards it is false

**Files modified:** `frontend/src/pages/Bots.tsx`
**Commit:** `96c9837b`
**Applied fix:** Took the reviewer's second option (honest comment) rather than deleting the API, deliberately:
- `newGame` has substantial dedicated coverage in `useBotGame.test.ts` (book reset, uuid re-mint, live reset, pending-store non-clobber) and a plausible near-term caller (an in-place "rematch"). Deleting a hook API mid-milestone is a scope expansion beyond the reviewed defect.
- The actual defect is the **false guard claim** — the "half-invariant" shape the project's own memory warns about. The comment now states plainly that knip cannot see a property of a hook's return object, that `newGame` has no production caller, and that **nothing enforces this**. It also points at the guard that genuinely exists: `Bots.test.tsx`'s `expect(fakeGame.newGame).not.toHaveBeenCalled()` on both result surfaces.

If the team prefers deletion, that is a clean follow-up; this fix removes the misinformation either way.

### WR-04: `profile.current_rating` orphaned frontend-wide

**Files modified:** `frontend/src/hooks/useMaiaEloDefault.ts`, `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts`
**Commit:** `45874722`
**Applied fix (the reviewer's stated minimum):** dropped `current_rating` from `MaiaEloProfile`, so it is no longer a required field that nothing reads. This also makes D-08's repoint enforced by the **type**: the raw (chess.com-inflated) rating is no longer visible to the hook, so a future edit cannot silently read it back. `Analysis.tsx` still passes a full `UserProfile` (structural typing — verified by `tsc -b`). The tests still supply `current_rating` at **runtime** as a decoy on a widened shape, so they keep proving an inflated raw rating never leaks into the derived default.

**Deliberately deferred (not skipped — a decision, not a bug):** removing the `current_rating` **wire field** plus `_primary_current_rating` and the two `get_current_rating_by_platform(...)` calls in `app/routers/users.py`. The reviewer explicitly frames this as "decide deliberately whether the wire field stays… removing it is a contract change". It is a public response field on `GET/PUT /users/me/profile`; dropping it is an API contract change that needs product sign-off, and it is outside the phase's scope (CLAUDE.md: "Do not add unplanned features, refactors, or improvements outside the current GSD phase scope. If something seems needed but isn't in the plan, flag it"). **Flagging it here:** the field currently costs one extra DB round-trip per profile GET **and** per profile PUT for zero frontend readers. Worth a follow-up quick task.

### WR-05: Chip styling duplicated between `SetupScreen` and `PlayStyleControl`

**Files modified:** `frontend/src/components/bots/chipStyles.ts` (new), `frontend/src/components/bots/SetupScreen.tsx`, `frontend/src/components/bots/PlayStyleControl.tsx`
**Commit:** `0286f3af`
**Applied fix:** Hoisted `CHIP_BASE_CLASS` / `CHIP_ACTIVE_CLASS` / `CHIP_INACTIVE_CLASS` into a new `components/bots/chipStyles.ts`; both components import them. Kept out of `theme.ts` on purpose: these are layout/state utility classes composed over existing semantic tokens (`toggle-active`, `inactive-bg`), not new colour **values** — `theme.ts` owns the token values these classes reference.

### WR-06: `TC_BUCKET_GRID_COLS` hard-coded column counts with nothing enforcing the invariant

**Files modified:** `frontend/src/components/bots/SetupScreen.tsx`
**Commit:** `9f880196`
**Applied fix:** Deleted the lookup entirely and derived the track count from the bucket's own preset count (the reviewer's second option — it *cannot* drift, whereas a test pinning the lookup only detects drift after the fact). Uses an inline `gridTemplateColumns: repeat(N, minmax(0, 1fr))` because Tailwind cannot generate class names from a runtime value.

**Status: fixed — worth one human glance.** This is the only fix with a visual surface that no test asserts (no existing test pins `grid-cols-4`). `tsc`, lint and the full suite are green and the rendered track count is provably `presets.length`, but a quick look at the Blitz/Rapid/Classical chip rows on `/bots` during UAT would close it out.

### WR-07: The nav lock expression triplicated in `App.tsx` with divergent clause lists

**Files modified:** `frontend/src/App.tsx`
**Commit:** `44d0ff5b`
**Applied fix:** Extracted `IMPORT_EXEMPT_ROUTES` (a `ReadonlySet`) + `isNavLocked(to, navUnlocked)`, used at all three sites (`NavHeader`, `MobileBottomBar`, `MobileMoreDrawer`). No behaviour change: the bottom bar's missing `/admin` clause was latent (`/admin` is not in `BOTTOM_NAV_ITEMS`), not live. `App.test.tsx` — which exists specifically to catch the "patch one site, miss the other two" failure mode — stays green (16 tests).

### WR-08: A failed profile fetch silently degraded the page to the shared `anon` bucket

**Files modified:** `frontend/src/pages/Bots.tsx`, `frontend/src/pages/__tests__/Bots.test.tsx`
**Commit:** `ef0d5bfe`
**Applied fix:** `useUserProfile()` is now consumed as `{ data, isLoading, isError }`. `isError` gates **both** the boot effect and the mount-drain (so neither runs under a fallback `anon` key), and renders the standard CLAUDE.md error copy. The error branch is placed **before** the `boot === null` loading branch — on error the boot effect never runs, so the page would otherwise sit on "Loading…" forever.

Regression test asserts the error branch renders, that a snapshot parked in the anon bucket is **never** consumed by a logged-in user whose profile fetch failed, and that the drain never fires. Reverting the branch turns it red.

## Not Fixed (out of scope)

The 6 Info findings (IN-01…IN-06) were **not** touched: `fix_scope` for this run is `critical_warning`. None are defects; recording them so they are not lost:

- **IN-01** — `PlayStyleControl` missing an explicit `: ReactElement` return type (CLAUDE.md type-safety rule). Genuinely worth doing; it is a one-liner in a file this run already touched for WR-05, and was left alone only to keep each commit scoped to exactly one finding.
- **IN-02** — stale `BotsGameProps.onDiscard` prop doc (still says "remounts a fresh game"; D-13 lands on the setup screen).
- **IN-03** — duplicated 11-line comment paragraph in `useBotGame.commitMove` (copy-paste residue).
- **IN-04** — `SetupScreen` is data entry but not a `<form>` (Browser Automation Rules; Enter does not submit).
- **IN-05** — unreachable triple fallback in `SetupScreen.buildSettings`.
- **IN-06** — `NAV_ITEMS` and `BOTTOM_NAV_ITEMS` are byte-identical in `App.tsx`.

IN-01 through IN-03 and IN-06 are mechanical; a follow-up `/gsd-quick` could clear all six cheaply.

---

_Fixed: 2026-07-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
