---
phase: 169-clocked-board-game-loop-usebotgame
verified: 2026-07-13T15:50:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 6
overrides_applied: 1
human_verification: deferred
human_verification_deferred:
  decided_by: user
  decided_on: 2026-07-13
  rationale: "Ship the phase and defer UAT. All 5 code-level must-haves are verified (each fix proven by fail-first mutation test). The 6 outstanding items require a real browser and remain OPEN as tracked verification debt in 169-UAT.md — they were NOT performed. Nothing in this phase is deployed to production by marking it complete."
  open_items: 6
  tracked_in: 169-UAT.md
  clear_by: "/gsd-verify-work 169"
re_verification:
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "SC1 / CR-02 (never-flag clamp): commitMove's `Math.max(0, clockBaseRef.current[mover] - debitMs)` is GONE (useBotGame.ts:414 is now a plain subtraction). A commit-time flag test (`flagIfOutOfTime` → `hasFlaggedOnDebit`) now runs BEFORE `chess.move()` on BOTH move paths — attemptMove:487 (before the move at :491) and runBotTurn:778 (before the move at :786). commitMove's callers were enumerated exhaustively (grep across all of frontend/src): exactly two, both guarded. Proven by fail-first mutation test, not symbol presence — see Behavioral Spot-Checks."
    - "SC2 / CR-01 (hidden-tab pause bypass): all three elapsed-time consumers now route through the single pause-aware `chargeableElapsedMs()` helper (chessClock.ts `computeChargeableElapsedMs`) — the 100ms tick's flag check (useBotGame.ts:621), the bot's committed debit (:770), and the user's move debit (:486). A repo-wide grep for `Date.now()`/`computeElapsedMs` confirms no other clock consumer exists in the bot-game path. Proven by fail-first mutation test."
    - "CR-01 mount-into-hidden-tab sub-bug (found by code review AFTER plan 10, fixed in commit 21bdd932): the mount effect now seeds `pausedAtRef` from the INITIAL `document.visibilityState` (useBotGame.ts:597-609), so a game opened in an already-background tab (which never fires a `visibilitychange` transition) no longer charges background wall-clock time. Commit 21bdd932 is present in HEAD; the fix is correct and covered by a dedicated regression test that fails when the seed line is removed."
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
behavior_unverified_items: []
human_verification:
  - test: "Re-run the /bots browser UAT against the REVERSED clock model (5+3 stub). Play a game to a low clock and let the bot get into time trouble; also let your own clock run out."
    expected: "The bot visibly speeds up as its clock drops (shorter thinks), and CAN lose on time — the result dialog shows 'You won — timeout'. Your own flag also ends the game correctly."
    why_human: "The 2026-07-12 plan-07 sign-off (169-07-SUMMARY.md, checklist point 2) explicitly certified 'bot never flags' — the model that D-15/D-16/D-18 REVERSED on 2026-07-13. The human acceptance gate therefore certified behavior that no longer exists. The code invariant is now proven by tests, but the resulting PACING FEEL (does the deadline band make a 5+3 game play plausibly? is time trouble reachable but not routine? — explicitly Claude's-discretion tuning per 169-CONTEXT.md) has never been observed by a human."
  - test: "Background the tab (switch to another tab / minimize) for ~30s while the bot is thinking, then return. Repeat with the tab backgrounded during your own turn."
    expected: "Neither clock is drained by the hidden interval; no side flags; on return the clocks resume from where they paused."
    why_human: "Real browser background-tab throttling and real Web Worker background execution cannot be reproduced in jsdom — the tests simulate visibilitychange, they do not exercise the actual throttled-interval + backgrounded-worker interaction."
  - test: "Listen for each sound: move, capture, check, game-end, the once-only low-time warning, and the draw-declined blip. Toggle mute, reload the page, confirm mute persisted. If possible, test on iOS Safari."
    expected: "All six events are audible and tonally acceptable; mute silences everything and survives a reload; on iOS the first board tap unlocks audio so bot-initiated sounds play."
    why_human: "Audio playback is mocked in the test suite (vi.mock('@/lib/sounds')). Audibility, tonal fit, and the iOS autoplay-unlock path cannot be verified from code."
  - test: "Move by dragging a piece and by two clicks (source square, then target). Try an illegal move, an off-turn move, and a move while scrolled back in the move list."
    expected: "Both input methods work; illegal/off-turn/off-live-position moves snap back; scroll-back is view-only with a working return-to-live affordance."
    why_human: "Drag/click feel and the board's snap-back animation are visual/interactive; only the callback contract is unit-tested."
  - test: "Reach a game end. Inspect the result dialog, dismiss it, then use the persistent result strip."
    expected: "Dialog shows the correct outcome + reason with win/loss/draw coloring; dismissing reveals the final position; the strip keeps 'Analyze this game' (deep-links to /analysis with the game's moves) and 'New game' reachable."
    why_human: "Rendering, coloring, and dialog-dismiss behavior are visual."
  - test: "Load /bots on a narrow viewport (<1024px) and on desktop."
    expected: "Mobile stacks bot clock above the board, user clock below, then move list + controls; desktop puts the board left and a side column right. Nothing overflows."
    why_human: "Responsive layout is visual (CLAUDE.md mobile-friendly rule)."
---

# Phase 169: Clocked Board Game Loop (useBotGame) Verification Report

**Phase Goal:** The user plays a full clocked game against the bot on a live client-side board that handles dual clocks, bot pacing, all end conditions, resign/draw offers, and move sounds.
**Verified:** 2026-07-13
**Status:** human_needed
**Re-verification:** Yes — fourth round, after gap-closure plans 08/09/10 plus the orchestrator-applied CR-01 mount fix (commit 21bdd932).

## Verification method note (why this round is different)

The two previous rounds of this phase both passed grep/symbol-presence checks while the runtime
invariant did not hold. This round does **not** rely on symbol presence for SC1 or SC2. Both were
verified by:

1. **Exhaustive control-flow enumeration** — every caller of `commitMove`, `flagIfOutOfTime`,
   `chargeableElapsedMs`, and every `Date.now()`/`computeElapsedMs` reader in the frontend tree
   was listed by grep and read, not sampled.
2. **Fail-first mutation testing** — each fix was individually reverted in the working tree, the
   suite re-run, and the specific failing tests recorded. A test suite that stays green when the
   bug is reintroduced proves nothing; these do not. The working tree was restored to HEAD
   afterwards (`git status` clean, `tsc -b` exit 0, 25/25 useBotGame tests green again).

## Goal Achievement

### Observable Truths

| # | Truth (amended SC) | Status | Evidence |
|---|-------|--------|----------|
| 1 | Live board, dual Fischer clocks, drag/click, turn-gated; bot paces via a per-move think deadline from its remaining time, reveal delay floors fast moves, honest real-elapsed debit — **the bot CAN lose on time** (D-15/D-16/D-18) | ✓ VERIFIED | **Invariant traced, not grepped.** `commitMove` (useBotGame.ts:400-464) has exactly TWO callers in the entire tree (`attemptMove`:497, `runBotTurn`:800). Both call `flagIfOutOfTime(mover, elapsed)` BEFORE `chess.move()` (:487 before :491; :778 before :786) and return early on `true`. The zero-clamp is gone — :414 is a plain `clockBaseRef.current[mover] - debitMs`; `applyIncrementMs`'s `Math.max(0,…)` is now only reachable with a positive operand (guaranteed by the preceding flag test), so it can no longer forgive an overrun. Deadline: `computeThinkDeadlineMs` (chessClock.ts:211) → `createDeadlineSearch` → `deps.search` (useBotGame.ts:723-724), monotonically shrinking in `remainingMs`. Reveal delay clamped to the same deadline (:744). **Mutation-proven:** reintroducing the clamp + neutering the flag test fails exactly the 2 commit-path flag tests. |
| 2 | Wall-clock (Date.now()-delta) model, accurate across backgrounding, pauses while hidden — **the pause reaches the value actually DEBITED** on commit, not just the display (D-20) | ✓ VERIFIED | All three elapsed consumers route through the single `chargeableElapsedMs()` helper: tick flag check (:621), bot committed debit (:770), user move debit (:486). `computeChargeableElapsedMs` (chessClock.ts:172) freezes elapsed at `pausedAtMs` when a pause is in progress. Repo-wide grep confirms no other `Date.now()`/`computeElapsedMs` reader exists in the bot-game path. `pausedAtRef` is correct at every entry point: hide transition (:671, idempotent against Safari's duplicate event), resume (:672-676), commit/newGame re-baseline (`resetTurnAnchor`:327-331), **and MOUNT** (:608 — the commit-21bdd932 fix, seeding from the initial `visibilityState` so a game opened in an already-hidden tab is not flagged). **Mutation-proven:** a pause-unaware elapsed read fails 5 tests; removing the mount seed alone fails exactly the mount-into-hidden-tab test. |
| 3 | Every end condition — checkmate, stalemate, threefold, 50-move, insufficient material, flag-on-time — plus a result screen with outcome+reason and Analyze/New game | ✓ VERIFIED | `botGameEnd.ts` + `botGameEnd.test.ts` cover all 5 board conditions exhaustively; flag-on-time now has TWO real detectors (the 100ms tick :643-654, ungated by color, and the commit-path `flagIfOutOfTime`). `GameResultDialog`/`GameResultStrip` render outcome+reason with WDL coloring and both actions (`btn-analyze-game`/`btn-new-game`, `strip-btn-*`); wired in `Bots.tsx`:96-102, 235-244. `finalizeGame`'s `outcomeRef` latch (:360) keeps the first outcome, with a passing regression test for the stale-draw-accept-vs-checkmate race. |
| 4 | The user can resign and can offer/accept a draw against the bot | ✓ VERIFIED | `resign()` (:528), `offerDraw()` (:561) + the draw-resolution effect (:545-559) pass the resign-draw suite. `GameControls.tsx` wires a two-step resign confirm dialog (`board-btn-resign` → `board-btn-resign-confirm`) and the throttled draw offer; the cooldown tooltip mounts only when the cooldown is actually active, and `Bots.tsx`:110-111 derives both props from the hook's real gates (no hardcoded `false`). |
| 5 | Move/capture/check/game-end sounds with a working mute control; per-move `[%clk]` (both colors) in the PGN | ✓ VERIFIED | `sounds.ts` vendors the AGPLv3+ lila set (9 clips in `public/sound/`, incl. the two D-09 extras), mute persisted to localStorage (`setMuted`/`useMuted`), iOS `unlockAudio` on first gesture. `annotateClock` is called from `commitMove` for EVERY move regardless of mover (:420) → both colors. `botGamePgn.test.ts` passes, and the backend round-trip test (`tests/test_bot_pgn_clk_roundtrip.py`) passes against python-chess. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/chessClock.ts` | Honest math, no never-flag clamp; `computeChargeableElapsedMs` + `hasFlaggedOnDebit` (D-15/D-20) | ✓ VERIFIED | Both new helpers exported and unit-tested; the 5 deleted synthetic-debit/never-flag symbols return zero hits tree-wide. |
| `frontend/src/lib/engine/deadlineSearch.ts` | Deadline-cut `SearchRunner`, node floor from `FLAWCHESS_BOT_STOP_RULE.minNodes` | ✓ VERIFIED | `createDeadlineSearch` + `BOT_MIN_SEARCH_NODES` present, tested; frozen engine core untouched. |
| `frontend/src/hooks/useBotGame.ts` | Game-loop hook on the honest clock + deadline + pause-aware elapsed | ✓ VERIFIED | Exists, substantive (877 lines), imported/used by `Bots.tsx`. Both headline invariants now hold — mutation-proven. |
| `frontend/src/components/bots/*.tsx` (5 files) | Clocks, move list, controls, result dialog + strip | ✓ VERIFIED | All present, wired by `Bots.tsx`, `data-testid` + `aria-label` per CLAUDE.md. |
| `frontend/src/pages/Bots.tsx` + `App.tsx` | Lazy `/bots` route, unlinked from nav, hardcoded 5+3 stub (D-14) | ✓ VERIFIED | `lazy(() => import('./pages/Bots'))`, route at App.tsx:742, no nav link. |
| `frontend/public/sound/` + `sounds.ts` | Vendored lila sfx + mute persistence | ✓ VERIFIED | 9 clips present; README attribution section exists. |
| `.planning/REQUIREMENTS.md` traceability | Rows must reflect reality (the previous round found them FALSE) | ✓ VERIFIED | Lines 94-100 now correctly credit Plan 10 for the CR-01/CR-02 closures; the previously-false "Plan 09 fixes it" prose is corrected. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `computeThinkDeadlineMs` | `selectBotMove` | `buildBotMoveDeps` → `createDeadlineSearch` → `deps.search` | ✓ WIRED | useBotGame.ts:205-212, 723-724; asserted by the "wires the D-16 think deadline" test (exact deadline + `BOT_MIN_SEARCH_NODES` floor). |
| `pausedAtRef` | tick flag check | `chargeableElapsedMs()` | ✓ WIRED | :621. Mutation-proven (2 tick tests fail without it). |
| `pausedAtRef` | bot committed debit | `chargeableElapsedMs()` | ✓ WIRED | :770. Mutation-proven (the "commits WHILE STILL HIDDEN" debit test fails without it). |
| `pausedAtRef` | user move debit | `chargeableElapsedMs()` | ✓ WIRED | :486. |
| MOUNT (`document.visibilityState`) | `pausedAtRef` | mount-effect seed | ✓ WIRED | :608 (commit 21bdd932). Mutation-proven. |
| `hasFlaggedOnDebit` | `chess.move()` (both paths) | `flagIfOutOfTime` before commit | ✓ WIRED | attemptMove :487→:491; runBotTurn :778→:786. Callers enumerated exhaustively. |
| `useBotGame` | `Bots.tsx` → `ChessBoard` | `onPieceDrop` (drag) + `onSquareClick` (2-click) | ✓ WIRED | ChessBoard.tsx:305-327 routes click-to-move through the same `onPieceDrop` contract. |
| `useBotGame.pgn` | backend `normalize_flawchess_game` | STORE-02 `[%clk]` gate | ✓ WIRED | `tests/test_bot_pgn_clk_roundtrip.py` passes (actual POST is Phase 171 scope). |

### Data-Flow Trace (Level 4)

Not applicable — entirely client-side, in-memory state (chess.js instance + React state + `Date.now()` reads). No API/DB source to trace.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 7 phase-169 frontend suites | `npx vitest run useBotGame chessClock deadlineSearch botGameEnd botGamePgn botDrawGate sounds` | 88/88 pass (7 files) | ✓ PASS |
| Backend PGN `[%clk]` round-trip | `uv run pytest tests/test_bot_pgn_clk_roundtrip.py -q` | 1 passed | ✓ PASS |
| Type check | `npx tsc -b` | exit 0 | ✓ PASS |
| **Mutation A (SC1/CR-02)** — reintroduce `Math.max(0, …)` clamp in commitMove AND neuter `hasFlaggedOnDebit` | patch + `npx vitest run useBotGame.test.ts` | **2 failed** — "a bot search resolving after its clock has already run out flags the bot… commits NO move" + "a user move attempted after their own clock has already run out…" | ✓ PASS (bug IS caught) |
| **Mutation B (SC2/CR-01)** — make `chargeableElapsedMs` pause-unaware (raw now-minus-anchor) | patch + rerun | **5 failed** — the "commits WHILE STILL HIDDEN debits only pre-hide time" debit test, both "tick cannot flag while hidden" tests, the mount-into-hidden test, the duplicate-hidden-event test | ✓ PASS (bug IS caught) |
| **Mutation C (CR-01 mount sub-bug)** — remove the `document.visibilityState === 'hidden'` mount seed (i.e. revert commit 21bdd932) | patch + rerun | **1 failed** — "a game mounting into an ALREADY-hidden tab charges no background time and never flags" | ✓ PASS (bug IS caught) |
| Working tree restored | `git status --porcelain` + rerun | clean (only pre-existing untracked `reports/data/*.tsv`); 25/25 green | ✓ PASS |

The two CR-02 tests are constructed with `vi.setSystemTime()` and **no timer advance**, so the 100ms
tick provably cannot be the flag detector — only the commit path can see the jump. This is what makes
them a real test of the invariant rather than a re-test of the tick.

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` probes exist in this repo and none are declared by any 169 plan.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|-------------|--------------|--------|----------|
| PLAY-03 | 169-01/04/05/09/10 | Live board, dual clocks, Fischer increment, drag/click, turn-gate | ✓ SATISFIED | Turn-gate + view-only gates verified in `attemptMove`; drag AND click-to-move both route through `onPieceDrop`; increment applied on every commit. |
| PLAY-04 | 169-01/04/08/09/10 | Wall-clock accuracy across backgrounding; pause reaching the committed debit | ✓ SATISFIED | Truth 2 — mutation-proven. |
| PLAY-05 | 169-01/04/08/09 | Bot paces replies via a think budget derived from its remaining clock, degrading gracefully | ✓ SATISFIED | `computeThinkDeadlineMs` shrinks monotonically with remaining time; deadline-cut search returns best-so-far (D-17). See non-blocking WR-02 for the `blend <= 0` exemption. |
| PLAY-06 | 169-02/04/09/10 | All end conditions incl. flag-on-time | ✓ SATISFIED | Truth 3; flag-on-time now enforced at the commit path, not left to a tick race. |
| PLAY-07 | 169-02/04/05/09 | Resign + offer/accept draw | ✓ SATISFIED | Truth 4. |
| PLAY-08 | 169-03 | Move/capture/check/game-end sounds + mute | ✓ SATISFIED | Truth 5 (audibility → human verification). |
| PLAY-09 | 169-02/04/06 | Result screen with Analyze/New game | ✓ SATISFIED | Truth 3 (rendering → human verification). |

No orphaned requirements: all 7 IDs (PLAY-03..09) declared across the 10 plan frontmatters match REQUIREMENTS.md's phase-169 mapping rows exactly. REQUIREMENTS.md lines 23-29 (`[x]`) and 94-100 (traceability prose) are now both accurate — the previous round found the prose false; Plan 10 corrected it.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX` debt markers in any file touched by this phase | — | Clean |
| — | — | No `TODO`/`HACK`/`PLACEHOLDER` in `useBotGame.ts`, `Bots.tsx`, or `components/bots/*` | — | Clean |

### Non-Blocking Findings (169-REVIEW.md — deliberately OUT of success-criteria scope)

These are **not** phase failures and must not block Phase 170. Recorded here so they are not lost.
The one Critical (CR-01) is **RESOLVED** (commit 21bdd932, verified above).

**Warnings (8 open):**

| ID | File | Issue | Recommended timing |
|----|------|-------|--------------------|
| WR-01 | `useBotGame.ts:400-418` | The CR-02 invariant is enforced by **comment, not construction** — a future `commitMove` caller that forgets `flagIfOutOfTime` silently reintroduces the never-flag behavior (negative remaining → `applyIncrementMs`'s `Math.max(0,…)` absorbs it). This invariant has now regressed twice. Fix: fold the flag test into `commitMove`, or `throw` in DEV on an overrun debit. | **Recommended before Phase 171** — cheapest possible insurance on the invariant that consumed three closure rounds. |
| WR-02 | `useBotGame.ts:205-212`, `selectBotMove.ts:112-118` | At `blend <= 0` (full-human regime) `selectBotMove` returns before `deps.search` is consulted, so the D-16 deadline is computed and **thrown away** — that bot has an honest flaggable clock with no pacing mechanism. Not shipped today (`Bots.tsx` hardcodes `blend: 0.5`), but Phase 171 surfaces `blend` as a user-facing slider. | **Must resolve in Phase 171** (before blend becomes user-settable). |
| WR-03 | `useBotGame.ts:220-222, 282-283` | The hook silently ignores post-mount `settings` changes (clock base captured in refs/initial state). | Phase 171 (setup screen changes settings). |
| WR-04 | `useBotGame.ts` `attemptMove`/`resign`/`offerDraw` | These gate on the `outcome` render-closure **state**, not the `outcomeRef` latch — a narrow stale-closure race. (The draw-vs-checkmate race IS closed; this is the residue.) | Low priority. |
| WR-05 | `GameControls.tsx` | Resign stays enabled after the game has ended. | Cosmetic. |
| WR-06 | `tests/test_bot_pgn_clk_roundtrip.py` | Asserts against a hand-transcribed PGN literal, not the frontend's actual `pgn()` output — cannot detect drift. | Test-quality. |
| WR-07 | `Bots.tsx` `useIsDesktop` | Layout swap remounts the whole game subtree on any resize across 1024px (would reset a live game). | **Worth fixing** — a desktop user rotating/resizing mid-game loses the game. |
| WR-08 | `useBotGame.ts` hidden-tab pause | The pause is a user-controllable clock stop, and these games get stored with `[%clk]` — a user can farm "fast" clock times by backgrounding. | Design question for Phase 171 (stored-game integrity). |

**Info (7 open):** IN-01 duplicated audio-unlock guards; IN-02 four positionally-identical layout params; IN-03 global arrow-key listener swallows arrows inside dialogs; IN-04 `ClockDisplay` `aria-live` only while thinking; IN-05 `setMuted` silently no-ops without localStorage; IN-06 `deadlineSearch` records node count after `onSnapshot`; IN-07 `runBotTurn` captures `chessRef.current` while `commitMove` re-reads it.

### Human Verification — DEFERRED BY USER DECISION (2026-07-13), NOT PERFORMED

> **Read this before trusting `status: passed`.** The frontmatter status was flipped from
> `human_needed` to `passed` on 2026-07-13 by explicit user decision ("ship the phase and defer
> UAT") so the phase could close and Phase 170 could proceed. **No human has played the game.**
> The 5/5 must-have score covers the *code-level* invariants only — each proven by fail-first
> mutation testing, which is genuine — but the six browser items below were **not** executed and
> remain **open verification debt**, tracked in `169-UAT.md` (status: `testing`, 6 pending) and
> surfaced by `/gsd-audit-uat` and `/gsd-progress`.
>
> The sharpest of the six: the pacing constants (`BOT_MOVES_TO_GO`, `BOT_THINK_INCREMENT_SHARE`,
> the [800ms, 15s] clamp) are explicitly "tuned by feel", and the clock model *reversed* on
> 2026-07-13 (D-15/D-16/D-18) — so whether a 5+3 game actually paces plausibly is, as of this
> writing, an untested assumption. Clear with `/gsd-verify-work 169` before this reaches users.

### Human Verification Required (deferred — see note above)

**The phase's human acceptance gate is STALE.** Plan 169-07 (`autonomous: false`) was signed off on
**2026-07-12**, and its checklist point 2 explicitly certified *"bot clock ticks down live, thinking
dot pulses, reveal delay floors fast moves, **bot never flags**"* — the exact model that
169-CONTEXT.md's Decision Amendments (D-15/D-16/D-18, **2026-07-13**) reversed the very next day.
Plans 08/09/10 then rewrote the clock model, the pacing mechanism, and the hidden-tab handling.
**No human has observed the shipped behavior.** The code invariants are now proven by tests; the
browser experience is not.

1. **Re-run the /bots UAT against the reversed clock model.**
   Test: play a 5+3 game, push the bot into time trouble, and let your own clock run out.
   Expected: the bot visibly speeds up as its clock drops and CAN lose on time ("You won — timeout"); your own flag ends the game too.
   Why human: the deadline band constants (`BOT_MOVES_TO_GO`, `BOT_THINK_INCREMENT_SHARE`, the [800ms, 15s] clamp) are explicitly Claude's-discretion "tuned by feel" — whether a 5+3 game *paces plausibly* and time trouble is *reachable but not routine* is a judgment only a human playing the game can make.

2. **Hidden-tab behavior in a real browser.**
   Test: background the tab ~30s during the bot's think, and again during your own turn.
   Expected: neither clock drains; no side flags.
   Why human: real background-tab interval throttling + real backgrounded Web Worker execution cannot be reproduced in jsdom.

3. **Sounds are actually audible + mute persists.**
   Test: hear move, capture, check, game-end, the once-only low-time warning, the draw-declined blip; toggle mute; reload; ideally test iOS Safari.
   Expected: all six audible and tonally acceptable; mute survives reload; iOS unlocks on first tap.
   Why human: `@/lib/sounds` is mocked in every test.

4. **Drag + click-to-move feel and snap-back.**
   Test: drag a piece; move by two clicks; try illegal, off-turn, and scrolled-back moves.
   Expected: both input paths work; invalid moves snap back; scroll-back is view-only with return-to-live.
   Why human: interaction feel and animation are not code-observable.

5. **Result screen rendering.**
   Test: reach a game end; inspect the dialog; dismiss; use the strip.
   Expected: correct outcome + reason with WDL coloring; Analyze deep-links to /analysis with the moves; New game restarts.
   Why human: visual.

6. **Mobile layout.**
   Test: load /bots below 1024px and on desktop.
   Expected: correct stacking, nothing overflows (CLAUDE.md mobile-friendly rule).
   Why human: visual. (Note WR-07: resizing across the 1024px breakpoint mid-game currently remounts and resets the game — expect this if you resize while testing.)

### Gaps Summary

**No gaps.** Both invariants that failed the previous three rounds now hold, and — critically — they
hold *by demonstration, not by assertion*: each was individually reverted in the working tree and the
suite caught it every time (2, 5, and 1 failing tests respectively). The tests are constructed so the
100ms tick provably cannot be the detector (`vi.setSystemTime` with no timer advance), which is
precisely the hole the earlier "bot flags" and "hidden-tab" tests left open.

What changed materially since the last verification:
- **CR-02 closed:** the never-flag clamp is deleted from `commitMove`; the flag test runs before
  `chess.move()` on both paths; `commitMove`'s callers are exactly two and both are guarded.
- **CR-01 closed:** all three elapsed consumers route through one pause-aware helper, and
  `pausedAtRef` is now correct at every entry point — including MOUNT, the sub-bug that code review
  caught after plan 10 and commit 21bdd932 fixed (a 5+3 game opened in a background tab was
  previously already lost on time before the user looked at it).
- **REQUIREMENTS.md traceability corrected** — the previously-false "Plan 09 fixes it" prose now
  credits Plan 10 accurately.

The phase does not proceed to `passed` because the human acceptance gate certified a clock model that
was reversed the following day. The remaining work is not code — it is a human sitting in front of
`/bots` and confirming the six items above. Recommend closing WR-01 (make the CR-02 invariant
structural rather than comment-enforced) at the same time, since that invariant has now regressed
twice and is the single highest-leverage line of defense against a fourth round.

---

_Verified: 2026-07-13_
_Verifier: Claude (gsd-verifier)_
