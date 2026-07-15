---
phase: 171-bots-page-setup-screen-nav
reviewed: 2026-07-14T15:38:57Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - frontend/src/lib/analysisUrl.ts
  - frontend/src/lib/analysisUrl.test.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
  - frontend/src/pages/Bots.tsx
  - frontend/src/pages/__tests__/Bots.test.tsx
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/hooks/__tests__/useBotGame.test.ts
  - frontend/src/components/bots/SetupScreen.tsx
  - frontend/src/components/bots/__tests__/SetupScreen.test.tsx
  - frontend/src/components/bots/chipStyles.ts
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: resolved
---

# Phase 171: Code Review Report

**Reviewed:** 2026-07-14T15:38:57Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Supersession note

This review **supersedes** the prior `171-REVIEW.md` (dated 2026-07-14, 9 findings
against plans 01-07). That review's findings were all fixed — see
`171-REVIEW-FIX.md` (9/9 fixed, 6 Info items deliberately deferred). This review
covers **only** the gap-closure diff from plans 171-08/09/10 (`git diff
e9df4e97..HEAD`), per the scoping instructions for this run. Do not re-open the
01-07 findings; they are out of scope here and already resolved.

## Summary

Reviewed the three UAT gap-closure plans: (08) the `?orientation=` URL param and
its wiring from the bot Analyze CTA into a single collapsed `autoOrientation`
effect on `Analysis.tsx`; (09) `useBotGame`'s `fenAtPly` → `replayToPly` rename
that now also derives `lastMove` from `viewedPly`; (10) the setup-screen bottom-nav
clearance + mobile density pass.

All three plans' core claims check out under direct mutation testing (not just
inspection): reverting the `useBotGame.ts` `lastMove` derivation to the live tail
turns the anti-stale-highlight test red; reverting `Analysis.tsx`'s single
`autoOrientation` value back to the old isGameMode-only source turns the new
`?orientation=black` test red; the CSS specificity claim behind
`[&_[data-slot=slider]]:min-h-10` was independently verified against the actual
built CSS output (`min-height` on the `[data-slot=slider]` descendant selector
does win over the shared primitive's `min-h-11`, regardless of source order).
`parseAnalysisOrientationParam` is a pure strict-equality allowlist — it cannot
throw on any input, matching the tolerant-parsing convention the plan cites.
`Openings.tsx:570`'s single-arg call to `buildAnalysisLineUrl` still compiles
unchanged (verified via `tsc -b`, which the frontend `build` script runs).

No Critical/blocker-level defects found. One genuine test-coverage gap
(mutation-verified, not just inspected) and one visual-layout risk that jsdom
cannot catch; two Info-level documentation completeness notes.

## Warnings

### WR-01: `BotsGame`'s new `pb-20 sm:pb-4` bottom-nav clearance is untested — mutation-verified gap

**File:** `frontend/src/pages/Bots.tsx:360` (the `BotsGame` root `className`)
**Issue:** 171-10-SUMMARY.md's own coverage table (D1) claims "`SetupScreen`'s
root and `BotsGame`'s root both carry `pb-20 sm:pb-4`... matching the app's
established... pattern", but cites only
`SetupScreen.test.tsx#...the setup-screen root carries pb-20 sm:pb-4...` as the
verification. There is no equivalent assertion anywhere in `Bots.test.tsx` for
the `bots-page` root.

Confirmed by mutation testing (not just grep): reverting
`className="mx-auto flex max-w-5xl flex-col gap-4 p-4 pb-20 sm:pb-4"` back to
`"mx-auto flex max-w-5xl flex-col gap-4 p-4"` in `Bots.tsx` leaves the entire
`Bots.test.tsx` suite green (17/17 passing). The class is correctly applied
today, but nothing in the test suite would catch a future regression that
silently drops it — the exact "half-invariant" shape (fix applied at one site,
pinned only at the other) the project's own mutation-test-gap-closure memory
warns about.
**Fix:** Add a test mirroring the `SetupScreen.test.tsx` one, e.g. in
`Bots.test.tsx`:
```ts
it('the bots-page root carries pb-20 sm:pb-4 so the bottom nav never occludes the board/controls', async () => {
  renderBots();
  await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
  const className = screen.getByTestId('bots-page').className;
  expect(className).toContain('pb-20');
  expect(className).toContain('sm:pb-4');
});
```

### WR-02: `TcBucketGroup`'s fixed `w-20 shrink-0` label column has no overflow/wrap guard for "Classical"

**File:** `frontend/src/components/bots/SetupScreen.tsx:169`
**Issue:** The inline sub-header restructuring (`flex items-center gap-2`, label
`w-20 shrink-0`) fixes the label column to 80px with `shrink-0` (so the chip
grid can never compress it) but no `whitespace-nowrap`/`truncate`/`overflow-hidden`
on the `<p>`. "Classical" (9 characters) at `text-sm` is close to the 80px
budget on real device fonts; if it doesn't fit on one line, the default
`white-space: normal` will wrap it to two lines, growing that row's height
above the `h-10` (40px) chip row height it's meant to align with — a visible
misalignment jsdom cannot detect (no real layout) and that the plan's own
`human_judgment: true` gate for this task does not specifically call out
(it asks about "labels don't truncate" but the density-pass code has no
truncation mechanism to rely on — if it doesn't fit, it wraps, not truncates).
**Fix:** Add `whitespace-nowrap` (and optionally `overflow-hidden truncate`) to
the label `<p>`, or verify at plan-verification time (already flagged as
human/device-required) and drop `shrink-0` in favor of `min-w-0 truncate` if
"Classical" turns out to be borderline on real devices.

## Info

### IN-01: `analysisUrl.ts`'s module doc comment undersells `?orientation=`'s actual scope

**File:** `frontend/src/lib/analysisUrl.ts:21-25`
**Issue:** The doc comment says `?orientation=white|black` is "an OPTIONAL param
on the `?line=` free-play entry point", but `Analysis.tsx`'s `autoOrientation`
derivation (`isGameMode ? ... : urlOrientation`) applies it to **all** free-play
sub-modes uniformly — including the `?fen=` snapshot entry point and the bare
start position, not just `?line=`. This isn't a bug (the broader behavior is
arguably more correct/consistent), just an inaccurate scope claim in the
comment that could mislead a future reader into thinking `?fen=&orientation=`
is unsupported.
**Fix:** Reword to "an OPTIONAL param on any free-play entry point (`?line=`,
`?fen=`, or bare start)".

### IN-02: `Analysis.tsx`'s top-of-file JSDoc "Modes" section was not updated for `?orientation=`

**File:** `frontend/src/pages/Analysis.tsx:24-32`
**Issue:** The page-level doc comment enumerates every URL param this page
consumes (`?line=`, `?fen=`, `?game_id=&ply=`) and their precedence, but
`?orientation=` — a new, permanently-supported param added by this plan — is
absent from that list. A reader skimming only the top-of-file doc (the page's
main entry point for understanding its URL contract) would miss it entirely;
it's only documented inline at the two usage sites (searchParams read, effect).
**Fix:** Add one line to the "Modes" paragraph, e.g. "`?orientation=white|black`
additively orients the free-play board (171 UAT gap 1); game mode always
orients from `gameData.user_color` instead."

---

_Reviewed: 2026-07-14T15:38:57Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---

## Resolution

All 4 findings fixed in commit `fix(171): close code-review findings on gap-closure plans`.

- **WR-01** — fixed. Added the missing `pb-20 sm:pb-4` assertion for the `bots-page` root in `Bots.test.tsx`, and mutation-verified it: stripping the class from `Bots.tsx` turns the new test red, restoring it turns it green. The two-site clearance invariant is now pinned at both sites.
- **WR-02** — fixed. `whitespace-nowrap` added to the `TcBucketGroup` label. Not test-provable (jsdom performs no layout); folded into the gap-3 real-device re-test.
- **IN-01** — fixed. `analysisUrl.ts` doc now states `?orientation=` applies to any free-play entry point (`?line=`, `?fen=`, bare start), not only `?line=`.
- **IN-02** — fixed. `?orientation=` added to the `Analysis.tsx` top-of-file Modes/URL-contract doc.

Full frontend gate after the fixes: `tsc -b` clean, eslint 0 errors, knip clean, 2154/2154 tests passing.

