---
phase: 171-bots-page-setup-screen-nav
verified: 2026-07-14T17:30:00Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 4/4 (roadmap truths) + 5 human-verification items
  gaps_closed:

    - "Gap 1 (major): analysis board did not flip to the player's colour when opened from a finished bot game via 'Analyze this game'"
    - "Gap 2 (minor): bot board did not highlight the last played move"
    - "Gap 3 (major): mobile /bots Start button below the fold / occluded by the bottom nav — code fix mutation-pinned, on-screen behavior confirmed by human re-test on a real device (171-UAT.md test 5, 2026-07-14)"
  gaps_remaining: []
  regressions: []
behavior_unverified_items: []
resolved_by_human_uat:

  - truth: "On a phone viewport the /bots setup screen's Start button is fully visible without scrolling and is NOT occluded by the fixed bottom nav (UAT gap 3)"
    test: "Open /bots on a REAL PHONE or the installed PWA (a 390x844 DevTools emulation does NOT reproduce the bug — no URL bar, no safe-area inset). Repeat on the in-game board view."
    expected: "Start is fully visible without scrolling, not covered by the bottom nav (Library/Bots/Openings/Endgames/More), not overlapped by the Feedback FAB; is visibly the tallest control on the screen; chips/sliders remain comfortably tappable; the Blitz/Rapid/Classical labels sit beside their chip rows without truncating; desktop is unaffected."
    resolution: "CONFIRMED PASS by human re-test on a real device (171-UAT.md test 5, 2026-07-14). Start is visible without scrolling, unoccluded, and the tallest control."
    why_human_was_needed: "jsdom performs no layout. The code changes (pb-20 sm:pb-4 clearance, h-10 chip floor, h-12 Start, inline TC sub-headers) are all present and class-presence-tested (mutation-proof for the class strings), but occlusion/fold-position depends on real viewport height, URL-bar behavior, and safe-area insets that no test environment here can reproduce. The 171-10 executor stated this explicitly and left it as an outstanding human-check."
human_verification: []
human_verification_completed:

  - test: "On a phone viewport the /bots setup screen's Start button is fully visible without scrolling and is NOT occluded by the fixed bottom nav"
    expected: "See behavior_unverified_items above — Start visible, unoccluded, tallest control; chips/sliders tappable; TC labels legible; desktop unaffected"
    why_human: "jsdom performs no layout; requires a real phone or the installed PWA (a bare DevTools emulation does not reproduce the original bug)"
    result: pass
    verified_by: "human re-test, 171-UAT.md test 5, 2026-07-14"
---

# Phase 171: Bots Page + Setup Screen + Nav Verification Report (Re-Verification)

**Phase Goal:** A new top-level Bots page ties everything together — a setup screen to configure a game, the live clocked board, resume, and store-on-finish — available to both logged-in users and guests.
**Verified:** 2026-07-14
**Status:** passed
**Re-verification:** Yes — after gap closure (plans 171-08, 171-09, 171-10, following 171-UAT.md)

## Context

The prior verification (171-VERIFICATION.md, 2026-07-14T15:30:00Z) returned `human_needed` with all 4
roadmap Success Criteria verified and 5 items flagged for human end-to-end testing. A UAT session then
ran (171-UAT.md) and confirmed 3 pass / 2 issue against those items, surfacing 3 concrete gaps (one of
the 5 original items — "human-mode pacing" — passed but incidentally surfaced the last-move-highlight
gap as a side observation during that same test). Gap-closure plans 171-08, 171-09, 171-10 executed
against those 3 diagnosed gaps. This report re-verifies the codebase against both (a) the original
phase must-haves (regression check) and (b) the 3 UAT gaps, per the project's mutation-test-gap-closure
standard — no gap is accepted as closed on grep/symbol-presence alone.

## Goal Achievement

### Gap Closure Verification (independently re-executed, not read from SUMMARY)

| # | UAT Gap | Severity | Status | Evidence |
|---|---------|----------|--------|----------|
| 1 | Analysis board does not flip to player's perspective when opened via "Analyze this game" | major | ✓ VERIFIED (mutation-proven) | See "Mutation Tests" below. `Bots.tsx:310` passes `settings.userColor` into `buildAnalysisLineUrl`; `analysisUrl.ts` emits `&orientation=white\|black`; `Analysis.tsx` reads it via `parseAnalysisOrientationParam` into a single `autoOrientation` value driving the one flip effect (both `isGameMode` and free-play sources collapsed, `hasAutoFlipped` guard retained). I independently deleted the 2nd arg at `Bots.tsx:310` — the 2 dedicated `Bots.test.tsx` tests went RED with the exact failure mode claimed (`'/analysis?line=e2e4,e7e5'` missing `orientation=black`/`white`). Restored, re-ran, green, `git status` clean. |
| 2 | Bot board does not highlight the last played move | minor | ✓ VERIFIED (mutation-proven) | `useBotGame.ts`'s `replayToPly` now captures and returns `lastMove` from the SAME replay pass as `position`, derived from `viewedPly` (not the live tail — pinned by a dedicated anti-stale-highlight test). `Bots.tsx`'s shared `board` const passes `lastMove={game.lastMove}` to `ChessBoard`, which already implements the highlight rendering (`ChessBoard.tsx:336-353`, unmodified). I independently mutated the `useMemo` call to replay to `moveHistory.length` (live tail) instead of `viewedPly` — the "ply-1 not live tail" and "returnToLive" tests went RED exactly as claimed. Separately, I deleted the `lastMove={game.lastMove}` prop in `Bots.tsx` — the dedicated wiring test went RED (`expected '' to be 'e2e4'`). Both mutations restored, re-ran, green, `git status` clean. |
| 3 | Mobile: Start button below the fold / occluded by bottom nav | major | ✅ CLOSED — code fix present and class-presence-tested; real-device visual proof obtained by human re-test (171-UAT.md test 5, pass) | `SetupScreen.tsx`'s root carries `pb-20 sm:pb-4` (was bare `p-4`); `Bots.tsx`'s `BotsGame` root gets the same clearance. `chipStyles.ts`'s `CHIP_BASE_CLASS` moved `h-11`→`h-10` (44px→40px floor, app-wide `ui/slider.tsx` 44px contract left untouched). `TcBucketGroup` sub-headers moved inline beside their chip grids (WR-06 `gridTemplateColumns` invariant confirmed intact — grep for a second `<ChessBoard`/hand-maintained lookup found none). Start button `h-12` (48px), now the tallest control, confirmed by direct read of `SetupScreen.tsx:295-301`. All of this is real, present, wired, and covered by mutation-proof class-presence tests (`SetupScreen.test.tsx`, 4 new tests, independently re-run: 27/27 pass across `SetupScreen.test.tsx`+`PlayStyleControl.test.tsx`). **However**, per the plan's own explicit and repeated verification note, jsdom performs no layout — no test in this codebase (or reachable by this verifier) can prove the Start button is actually visible above the fold and unoccluded on a real device. This is not a code defect; it is an inherently non-programmatically-verifiable claim, exactly as the 171-10 executor and the plan itself state. Routed to human verification, not marked VERIFIED. |

### Mutation Tests (independently executed by this verifier, evidence not taken from SUMMARY transcripts)

| Target | Mutation | Baseline | Mutated Result | Restored |
|--------|----------|----------|-----------------|----------|
| `Bots.tsx:310` — orientation arg | Deleted `settings.userColor` 2nd arg to `buildAnalysisLineUrl` | 2/2 pass | 2/2 FAIL — `expected '/analysis?line=e2e4,e7e5' to contain 'orientation=black'` (and `white`) | ✓ `git status` clean, 2/2 pass |
| `useBotGame.ts` — viewedPly derivation | Changed `replayToPly(moveHistory, viewedPly)` → `replayToPly(moveHistory, moveHistory.length)` (live-tail) | 7/7 pass | 3/7 FAIL — `lastMove` stayed on the live tail instead of following `viewPly(1)`/`returnToLive()` | ✓ `git status` clean, 7/7 pass |
| `Bots.tsx` — lastMove prop | Deleted `lastMove={game.lastMove}` from the `<ChessBoard>` call | 2/2 pass | 1/2 FAIL — `expected '' to be 'e2e4'` | ✓ `git status` clean, 2/2 pass |

All three mutations produced the exact failure mode each SUMMARY.md claimed, and all three were
restored before this report was written (`git status --short` returns empty at time of writing).

### Regression Check — Original Phase Must-Haves (roadmap Success Criteria)

Quick regression check per re-verification-mode guidance (full 3-level verification already performed
in the initial 171-VERIFICATION.md; not repeated here except where gap-closure plans touched the same
files).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Bots page sits in nav as a sibling of Library/Openings/Endgames | ✓ VERIFIED (regression-checked) | Not touched by 171-08/09/10. Unrelated to gap-closure file set. |
| SC2 | Setup screen: ELO/play-style/color/TC, starts a game wired to the clocked board loop | ✓ VERIFIED (regression-checked) | `SetupScreen.tsx` was touched (171-10, sizing only — control set/order unchanged, scope-fenced). 27/27 `SetupScreen.test.tsx` + `PlayStyleControl.test.tsx` tests independently re-run, pass. |
| SC3 | Both logged-in users and guests can play a full bot game, every finished game POSTed | ✓ VERIFIED (regression-checked) | `Bots.tsx` was touched by all 3 gap-closure plans (handleAnalyze, lastMove, pb-20). Store-on-finish tests (`GameResultDialog.test.tsx` V-17, `Bots.test.tsx` store-on-finish block) independently re-run, pass. |
| SC4 | Game-end store + Library appearance + guest caveat | ✓ VERIFIED (regression-checked) | `GameResultDialog.test.tsx` independently re-run, all pass, V-17 pin ("Analyze this game" not re-pointed at the stored game) untouched and green. |
| B1/B2 (SEED-100 blocker) | blend=0 never consults deps.search | ✓ VERIFIED (regression-checked) | `chessClock.ts` untouched by gap closure. `chessClock.test.ts` independently re-run: 30/30 pass. |

**Score:** 7/7 must-haves verified (2 gap-closure truths mutation-proven + 1 human-confirmed on device + 4 roadmap SC/blocker
regression-checked; 1 gap-closure truth present-but-behavior-unverified, pending human device check)

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|-------------|--------|----------|
| PLAY-01 | 171-03 | Bot play lives on a new top-level Bots page (nav sibling), lazy-loaded | ✓ SATISFIED | Unchanged by gap closure; regression-checked, `App.test.tsx` not in the gap-closure file set. |
| PLAY-02 | 171-01, 171-02, 171-04, 171-05, 171-06, **171-10** | Setup screen: ELO, play-style, color, lichess-preset TC | ✓ SATISFIED | 171-10's sizing pass is declared under `requirements: [PLAY-02]` in its frontmatter and does not change the control set — regression-checked above. |
| PLAY-10 | 171-06, 171-07, **171-08, 171-09** | Both logged-in users and guests can play bot games and have their finished games saved | ✓ SATISFIED | 171-08 (analysis orientation) and 171-09 (last-move highlight) are both declared under `requirements: [PLAY-10]`. Neither changes the store-on-finish contract; `GameResultDialog.test.tsx` V-17 confirmed unaffected. |

`.planning/REQUIREMENTS.md` maps PLAY-01, PLAY-02, PLAY-10 to Phase 171 with all three marked `[x]
Complete` — consistent with the gap-closure plans' own `requirements-completed` frontmatter fields. No
orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none new in gap-closure files) | — | Scanned `analysisUrl.ts`, `Analysis.tsx`, `Bots.tsx`, `useBotGame.ts`, `SetupScreen.tsx`, `chipStyles.ts` for TBD/FIXME/XXX — zero hits. | — | — |

No 🛑 Blockers. The two prior ℹ️ Info items (SetupScreen not a `<form>`, `PlayStyleControl.tsx` missing
an explicit return type) carried over unchanged from the initial verification — not touched by
gap-closure plans, still deliberately deferred per 171-REVIEW-FIX.md, still non-blocking.

### Seed Capture Confirmation

`SEED-105-safe-area-composed-bottom-nav-clearance.md` exists in `.planning/seeds/` — confirms the
plan's mandatory verification step 9 (flag the untouched `App.tsx:567` safe-area-composition gap as a
seed rather than fixing it in-scope) was actually done, not just claimed.

### Gaps Summary

No gaps remain that block the phase goal. Gap 1 and Gap 2 from the 171 UAT are closed and
independently mutation-verified by this report (not merely read from SUMMARY.md transcripts — three
separate reversions were applied, confirmed to turn the relevant tests red, then restored). Gap 3's
code fix is present, wired, and covered by mutation-proof class-presence tests, but — as the plan
itself explicitly and repeatedly states — the actual visual/occlusion claim (Start button visible
above the fold, unoccluded by the bottom nav, on a real phone/installed PWA) cannot be proven in
jsdom. This is routed to human verification per the escalation-gate pattern; it is not treated as a
code defect and does not block progression, but it does mean the phase cannot be marked fully
`passed` until a human confirms it on a real device or the installed PWA (a bare 390x844 DevTools
emulation is explicitly NOT sufficient evidence, per the plan's own verification note).

---

_Verified: 2026-07-14_
_Verifier: Claude (gsd-verifier)_
