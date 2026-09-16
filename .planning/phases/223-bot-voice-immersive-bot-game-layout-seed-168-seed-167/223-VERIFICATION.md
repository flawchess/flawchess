---
phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167
verified: 2026-09-16T11:15:00Z
status: passed
score: 7/7 must-haves verified (4 via recorded owner override)
covered_files: [".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-01-PLAN.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-01-SUMMARY.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-02-PLAN.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-02-SUMMARY.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-03-PLAN.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-03-SUMMARY.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-04-PLAN.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-04-SUMMARY.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-05-PLAN.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-05-SUMMARY.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-06-PLAN.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-06-SUMMARY.md", ".planning/phases/223-bot-voice-immersive-bot-game-layout-seed-168-seed-167/223-CONTEXT.md", "CHANGELOG.md", "frontend/src/components/board/PlayerBar.tsx", "frontend/src/components/bots/BotDrawOfferActions.tsx", "frontend/src/components/bots/BotGameBubble.tsx", "frontend/src/components/bots/BotGameDesktopLayout.tsx", "frontend/src/components/bots/BotGameMobileBar.tsx", "frontend/src/components/bots/BotGameMobileLayout.tsx", "frontend/src/components/bots/GameControls.tsx", "frontend/src/components/bots/GameResultDialog.tsx", "frontend/src/components/bots/PersonaGrid.tsx", "frontend/src/components/bots/botPlayerRow.ts", "frontend/src/hooks/useBotGameVoice.ts", "frontend/src/lib/botGameCopy.ts", "frontend/src/lib/botLineTrigger.ts", "frontend/src/lib/mobileBoardControls.ts", "frontend/src/lib/sounds.ts", "frontend/src/pages/Bots.tsx"]
covered_digest: "v1:sha256:ad9f2df66cb10f29269b58612123cd9fda201450493ba7aecce1f787116fad0c"
behavior_unverified: 0
overrides_applied: 4
overrides:
  - must_have: "SC3: 'An Attacker persona that sacrifices a piece on purpose does not apologize for it (swing detection is WDL-based, with a named threshold).'"
    reason: "223-06 UAT round (caa1208bc, 2026-09-16): the expected-score sigmoid saturates once a game is decided, so a real 81-ply game with hanging queens fired zero swing lines. Swing detection was moved to bot-POV centipawns (BOT_LINE_SWING_THRESHOLD_CP = 150, clamp BOT_LINE_SWING_CLAMP_CP = 1000), calibrated on a 300-game dev-DB replay (~3.1 swing lines/game). The criterion's actual intent — an Attacker sacrifice never apologizes because the signal is an eval delta, never captured material — is unchanged and verified: resolveSwingKey/isRegretSwing read only swingCp/recoveryCp, never move.captured for direction. This restates BOTVOICE-03 as CONTEXT.md's planning notes already flagged ('BOTVOICE-03 is worded in D-01's terms... flagged here so verify-phase does not read it as scope drift')."
    accepted_by: "Adrian Imfeld (owner, interactive UAT round 5)"
    accepted_at: "2026-09-16"
  - must_have: "SC4: mobile clock strip below the board (white left, black right, material beside each clock) and a measurably wider board, numerically confirmed at 375px."
    reason: "223-06 UAT round 2 (89115c7c6): BotClockStrip (the anonymous clock strip) was deleted; BotGameMobileLayout now renders the same PlayerBar rows the desktop layout and analysis board use, via the shared botPlayerRow.ts resolver — with both breakpoints on screen, one consistent row shape read better than the chess.com-style strip. The board-width win itself was verified by eye at 375x667 by the owner on 2026-09-16 ('looks good, I tested') rather than captured as a before/after pixel number; the chrome removed (two 48px in-page control rows + the draw-banner slot) versus what replaced it (one avatar+bubble row) is documented arithmetically in 223-05-SUMMARY.md as a net ~50-70px gain, and a slot-growth regression found during UAT (09abcebc1) was fixed so the bubble no longer pushes the board down when a line appears."
    accepted_by: "Adrian Imfeld (owner, interactive UAT rounds 2 and 6)"
    accepted_at: "2026-09-16"
  - must_have: "SC6: 'the estimated-rating row [is] still reachable' on the roster page."
    reason: "223-06 UAT round 7 (5caa0454c): the roster's 'Your estimated blitz rating' row, PersonaGrid's currentStrength prop and currentStrengthCopy.ts were removed entirely (not gated, removed) because a bot's calibrated ELO is measured against engines and a human number beside it invited a comparison the two scales do not support. The in-game user player row (BOTVOICE-05) still carries the estimate. The bubble, its engine InfoPopover, and the guest case (no rating row for anyone, guest or signed-in) all hold; only the specific 'rating row reachable' clause is superseded."
    accepted_by: "Adrian Imfeld (owner, interactive UAT round 7)"
    accepted_at: "2026-09-16"
  - must_have: "SC7 / BOTVOICE-07: 'Sound can be muted and unmuted from the settings page, and nowhere else in a game.'"
    reason: "223-06 UAT round 7 (5caa0454c): BoardSoundsSwitch and its tests were deleted, both App.tsx render sites (NavHeader, MobileMoreDrawer) removed, the changelog bullet rewritten to say so plainly. Owner decision: sounds always play for now; a proper disable option is deferred to a later phase. sounds.ts keeps useMuted/setMuted dormant (playSound still honours a pre-existing persisted mute). This criterion is UNMET BY OWNER DECISION, not by defect — plan 03's BoardSoundsSwitch deliverable is fully built and tested (223-03-SUMMARY.md) but was deliberately not shipped in the final tree."
    accepted_by: "Adrian Imfeld (owner, interactive UAT round 7)"
    accepted_at: "2026-09-16"
---

# Phase 223: Bot Voice & Immersive Bot Game Layout Verification Report

**Phase Goal:** Give the 24 Bots personas a voice during the game and on the roster, and rebuild the game screen so the voice has room.
**Verified:** 2026-09-16T11:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Method

Read all 6 PLAN.md/SUMMARY.md pairs, 223-CONTEXT.md and the ROADMAP.md Phase 223 block in
full. Cross-referenced every claim in the summaries against the actual code at HEAD
(`f1f8c274c`, one docs-only commit ahead of the frontend-gate-verified `5caa0454c`).
Re-ran the phase's own targeted vitest files rather than the full suite (already proven
green at `5caa0454c` per 223-06-SUMMARY.md's Self-Check and this session's own re-runs
below), re-ran the `Bots.tsx` complexity-25 gate, ran `npm run knip`, and grepped for
retired symbols/testids to confirm every deletion claimed in the summaries actually
happened on disk. Plan 06 was closed through six owner-decision UAT rounds
(`223-06-SUMMARY.md` § Deviations); those six deviations are treated as intended outcomes
per this verification's brief, not gaps, and the four that literally contradict ROADMAP
success-criterion wording are recorded as accepted overrides above.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1–7)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| SC1 | Every one of the 24 personas has a line for every trigger; missing entry is a compile error; copy test rejects overlong lines. | ✓ VERIFIED | `botGameCopy.ts` — `BOT_LINE_TABLES: Record<BotLineKey, Record<PersonaId, string>>`, 10 keys × 24 personas = 240 authored lines (compile-time exhaustive: TypeScript, not just a test, rejects a missing persona). `botGameCopy.test.ts` (21 cases) enforces `BOT_LINE_MAX_CHARS=64`, no em-dash, no calculation/foresight claim, no insult, no numeric disclosure, no cross-table duplication — re-ran, 76/76 pass across the 4 copy/trigger/voice/bubble test files. Note: the `'player-threat'` trigger was dropped in UAT (see Anti-Patterns/Deviations); the remaining 9 triggers are still fully exhaustive over all 24 personas. |
| SC2 | No line reveals engine knowledge the board does not already show; lines fire only after the bot's own move and clear on the player's next move. | ✓ VERIFIED | `botLineTrigger.ts`'s locked precedence chain (terminal > draw-offer > swing > first-capture > game-start) reads only already-latched board-truth facts; `useBotGameVoice.ts` clears `botLine` on `mover === userColor` and only sets it from the bot's own grade/commit seam. A swing against the bot now LATCHES and settles only when the player captures, the position recovers, or it does not — never spoken on the bot's own (spoiler) grade. Unit-tested: `useBotGameVoice.test.ts` (11 cases incl. neutralised-threat-class latch/settle behavior), `botLineTrigger.test.ts` (21 cases). |
| SC3 | An Attacker persona that sacrifices a piece on purpose does not apologize (swing detection is WDL-based, named threshold). | ✓ VERIFIED (override — see frontmatter) | `resolveSwingKey`/`isRegretSwing` in `botLineTrigger.ts` read only `swingCp`/`recoveryCp` (a bot-POV clamped centipawn eval delta, `BOT_LINE_SWING_THRESHOLD_CP=150`), never `move.captured`, for direction — the sacrifice-safety property holds. Signal is centipawns, not WDL/expected-score, per an owner UAT correction (see override entry); the criterion's actual intent is preserved and tested (`botLineTrigger.test.ts`'s named Attacker-sacrifice case). |
| SC4 | 375px viewport: top bar, bubble row, board, clock strip, fixed four-action bar, no main nav, no scrolling; board measurably wider. | ✓ VERIFIED (override — see frontmatter) | `BotGameMobileLayout.tsx`: back-arrow top bar (`bots-back` testid) → `bubble` → board flanked by two `PlayerBar` rows → `usePublishMobileBoardControls` takeover. `BotGameMobileBar.tsx` renders exactly Resign/Back/Forward/Flip (`board-btn-resign`, `board-btn-back`, `board-btn-forward`, `board-btn-flip`), confirmed via `App.tsx`'s `MobileBottomBar` branch replacing the main nav. `Bots.test.tsx`/`App.test.tsx`/`BotGameMobileBar.test.tsx` (139 tests across 5 files, re-run, all pass) assert no main nav, no in-page control rows, no mute control anywhere. The "clock strip" literal wording and the numeric board-width measurement are superseded by an owner UAT decision (override entry); the row-shape unification and the qualitative width confirmation are both recorded. |
| SC5 | Desktop shows `PlayerBar` rows above/below the board and the bubble in the side column; the bot's draw offer is accepted/declined from the bubble on both breakpoints. | ✓ VERIFIED | `BotGameDesktopLayout.tsx`: `PlayerBar` above and below the board (ordered by `flipped`), `BotGameBubble` at the top of the side column above `moveList`, `BotDrawOfferActions` (testids `btn-accept-bot-draw`/`btn-decline-bot-draw`, preserved verbatim from the retired banner) wired into the bubble's `actions` slot — the SAME `drawOfferActionsOrUndefined` element is passed into both `BotGameDesktopLayout` and `BotGameMobileLayout` from `Bots.tsx`, so both breakpoints share one implementation. `Bots.test.tsx` asserts the actions render inside `bot-game-bubble` on both layouts. Live browser observation of the offer itself did not occur in UAT (the bot's offer gate needs a near-dead-equal position past move 30, which did not arise) — wiring is unit-tested on both breakpoints per 223-06-SUMMARY.md D3, which this verification accepts per its brief rather than treating as a gap. |
| SC6 | Roster page opens with a bot bubble instead of the prose card; engine popover and estimated-rating row still reachable; guests see the bubble without the rating row. | ✓ VERIFIED (override — see frontmatter) | `PersonaGrid.tsx`'s `BotWelcomeCard` replaces `HumanLikeOpponentsCard`'s prose paragraph with a `TrainBotBubble` (`bots-welcome-bubble` testid) hosting `rosterHost()`'s rotating per-persona greeting + `ROSTER_HUMAN_LIKE_LINE`, with the `InfoPopover` engine explainer inline at the end of the copy — all confirmed by `PersonaGrid.test.tsx` (re-run, pass). The rating row was removed for everyone (owner decision, override entry above), so the guest-sees-no-rating-row clause holds trivially. |
| SC7 | Sound can be muted/unmuted from a settings surface, and nowhere else in a game. | ✗ UNMET BY OWNER DECISION (override — see frontmatter) | `BoardSoundsSwitch.tsx` and its test, built and fully tested in plan 03 (223-03-SUMMARY.md), were deleted in the plan-06 UAT rounds along with both `App.tsx` render sites. `grep -rn "BoardSoundsSwitch\|board-btn-mute\|settings-board-sounds" frontend/src --include='*.ts' --include='*.tsx'` (excluding `__tests__`) returns nothing — confirmed on disk. Sounds always play; disable is deferred to a later phase per an explicit, recorded owner decision. Not a defect; recorded as an accepted override, not counted as a failing truth. |

**Score:** 7/7 truths verified (3 verified directly, 4 verified via a recorded owner override that supersedes literal ROADMAP wording without changing the underlying intent — see frontmatter `overrides`).

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `frontend/src/lib/botGameCopy.ts` | 10-key exhaustive copy tables + roster rotation | ✓ VERIFIED | Exists; 10 `BotLineKey` values, all 24-persona-exhaustive (compile-time + `botGameCopy.test.ts`). |
| `frontend/src/lib/botLineTrigger.ts` | Full locked precedence resolver | ✓ VERIFIED | Exists; guard-clause-only body, no `else`; 21 passing tests. |
| `frontend/src/hooks/useBotGameVoice.ts` | Bubble-state sub-hook | ✓ VERIFIED | Exists; wires latches, pacing, terminal/draw-offer effects; 11 passing tests. |
| `frontend/src/components/bots/BotGameBubble.tsx` | Fixed-height presentational bubble | ✓ VERIFIED | Exists; `min-h-12`/`min-h-10` fixed slot, no timer/transition/animation (`grep` confirms 0 occurrences), persona-less draw-offer form. |
| `frontend/src/components/bots/BotGameMobileLayout.tsx` / `BotGameMobileBar.tsx` / `BotDrawOfferActions.tsx` | Mobile layout, 4-action bar, draw-offer actions | ✓ VERIFIED | All exist; four-action bar (Resign/Back/Forward/Flip) confirmed by testids; `BotDrawOfferActions` shared by both breakpoints. |
| `frontend/src/components/bots/BotGameDesktopLayout.tsx` / `botPlayerRow.ts` | Desktop layout, shared row resolver | ✓ VERIFIED | Both exist; `resolvePlayerRow` used by both breakpoints (no divergence between mobile/desktop row logic). |
| `frontend/src/components/board/PlayerBar.tsx` | Additive `ratingLabel`/`clockActive`/`clockUrgent` props | ✓ VERIFIED | Additive per `223-06-SUMMARY.md`; `PlayerBar.test.tsx` re-run, passes; pre-existing 4 render sites untouched per the plan's own diff gate. |
| `frontend/src/components/settings/BoardSoundsSwitch.tsx` | SEED-167 settings switch | ✗ DELETED (owner decision) | Built in plan 03, fully tested, then deleted in plan 06 UAT. Confirmed absent on disk. Not a gap — see SC7 override. |
| `frontend/src/lib/botThreat.ts`, `BotClockStrip.tsx`, `ClockDisplay.tsx`, `currentStrengthCopy.ts`, `BotDrawOfferBanner.tsx` | Retired components | ✓ CONFIRMED DELETED | All absent on disk; `npm run knip` exits 0 (no dangling exports); no non-test source file references any of their retired testids/symbols. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `useBotGameMoves.commitMove` | `useBotGameVoice` | `onMoveCommitted(move, mover)` clearing the line on `mover === userColor` | ✓ WIRED | Confirmed in `useBotGameVoice.ts`; test "clears the line when the player's own move is committed" passes. |
| `useBotGameEngineDispatch` grade continuation | `useBotGameVoice` | `onBotMoveGraded(previousScore, score, ply)`, previous score read before the ref overwrite | ✓ WIRED | `grep -n` line-order check confirmed by 223-01-SUMMARY.md and re-inspected; exactly one `.grade(` call site in the file. |
| `botGameCopy.BOT_LINE_TABLES` | `BotGameBubble` | `botLineCopy(key, personaId)` | ✓ WIRED | Direct import chain confirmed by reading `BotGameBubble.tsx`. |
| `Bots.tsx`'s shared `bubble`/`drawOfferActions` elements | `BotGameDesktopLayout` + `BotGameMobileLayout` | Pre-built elements passed as props to both layouts | ✓ WIRED | Confirmed: single `drawOfferActionsOrUndefined()` call site feeds both `<BotGameDesktopLayout>` and the mobile bubble, so testids `btn-accept-bot-draw`/`btn-decline-bot-draw` exist in exactly one component shared by both breakpoints. |
| `trainBotCopy.LANDING_ROTATION_EPOCH`/`LANDING_HOST_IDS` | `botGameCopy.rosterHost()` | Shared rotation primitives, not two independent copies | ✓ WIRED | Confirmed in `botGameCopy.ts`; `botGameCopy.test.ts`'s 24-day full-cycle agreement test passes. |
| `useBotGame.botDrawOffer`/`outcome` | `useBotGameVoice` | Draw-offer and terminal effects, independent of the grade seam | ✓ WIRED | Confirmed; `git diff` on `useBotGame.ts`'s voice-hook call site (per 223-04-SUMMARY.md) shows no unrelated change. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Copy/trigger/voice/bubble unit suite | `npx vitest run src/lib/__tests__/botGameCopy.test.ts src/lib/__tests__/botLineTrigger.test.ts src/hooks/__tests__/useBotGameVoice.test.ts src/components/bots/__tests__/BotGameBubble.test.tsx` | 4 files / 76 tests pass | ✓ PASS |
| Page/roster/App/PlayerBar/mobile-bar integration suite | `npx vitest run src/pages/__tests__/Bots.test.tsx src/components/bots/__tests__/PersonaGrid.test.tsx src/App.test.tsx src/components/board/__tests__/PlayerBar.test.tsx src/components/bots/__tests__/BotGameMobileBar.test.tsx` | 5 files / 139 tests pass | ✓ PASS |
| `BotsGame` complexity ceiling | `npx eslint --no-inline-config --rule 'complexity: ["error", 25]' src/pages/Bots.tsx` | exit 0, measured 17 (per 223-06-SUMMARY.md), `eslint.config.js` unedited | ✓ PASS |
| Dead-export gate | `npm run knip` | exit 0, no unused exports | ✓ PASS |
| Retired symbol/testid leakage | `grep -rn "BoardSoundsSwitch\|board-btn-mute\|settings-board-sounds\|player-threat\|botThreat\|BotDrawOfferBanner" frontend/src --include='*.ts' --include='*.tsx'` (excl. `__tests__`) | no matches in production source (only explanatory doc comments in `botLineTrigger.ts`/`botGameCopy.ts`/`useBotGameVoice.ts` naming the retired trigger) | ✓ PASS |
| Debt markers | `grep -rn "TBD\|FIXME\|XXX"` over the 8 core new/modified files | no matches | ✓ PASS |

Full workspace test suite was NOT re-run (per this verification's brief): 223-06-SUMMARY.md's Self-Check records it green at HEAD `5caa0454c` (266 files / 4287 tests), and HEAD `f1f8c274c` is exactly one docs-only commit ahead of that (`git log --oneline 5caa0454c..HEAD` shows only the SUMMARY-closing docs commit).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| BOTVOICE-01 | 01, 02 | Every persona has an authored line for every trigger; compile-error exhaustiveness; two-line copy budget | ✓ SATISFIED | 10-key exhaustive tables (9 after the player-threat trigger was dropped in UAT, still fully exhaustive over 24 personas), `botGameCopy.test.ts`. |
| BOTVOICE-02 | 01, 04 | Board-truth rule: no line reveals unpunished/uncashed/unexecuted engine knowledge; clears on player move | ✓ SATISFIED | `botLineTrigger.ts` precedence chain + latch/settle model in `useBotGameVoice.ts`. |
| BOTVOICE-03 | 04 | Swing direction from a named eval-delta threshold, never material; Attacker sacs never apologize | ✓ SATISFIED (restated in cp, see SC3 override) | `resolveSwingKey`, `BOT_LINE_SWING_THRESHOLD_CP`. |
| BOTVOICE-04 | 05 | 375px mobile: top bar, bubble, board, clock strip, 4-action bar, wider board | ✓ SATISFIED (clock-strip wording superseded, see SC4 override) | `BotGameMobileLayout.tsx`, `BotGameMobileBar.tsx`. |
| BOTVOICE-05 | 05, 06 | Desktop `PlayerBar` rows + bubble; draw offer from the bubble on both breakpoints | ✓ SATISFIED | `BotGameDesktopLayout.tsx`, `BotDrawOfferActions.tsx`. |
| BOTVOICE-06 | 02 | Roster bubble replaces prose card; popover + rating row reachable; guest sees bubble with no rating row | ✓ SATISFIED (rating row removed for everyone, see SC6 override) | `PersonaGrid.tsx`'s `BotWelcomeCard`. |
| BOTVOICE-07 | 03, 05 | Sound mutable from settings, nowhere else in a game | ✗ UNMET BY OWNER DECISION (see SC7 override) | `BoardSoundsSwitch` built (plan 03) then deleted (plan 06 UAT). |

No orphaned requirements: `.planning/phases/.../223-01-PLAN.md` lines 108-116 mint BOTVOICE-01..07 and every ID appears in at least one plan's `requirements` frontmatter (cross-checked against all 6 plans' frontmatter directly).

### Anti-Patterns Found

None blocking. No `TBD`/`FIXME`/`XXX` markers in any of the phase's core new/modified files. All six 223-06 UAT deviations are recorded, git-committed, and accounted for in the overrides above or in the Observable Truths evidence column — none are silent or undocumented.

### Human Verification Required

None. Per this verification's brief, the two items with no live-browser capture (the bot's draw offer never fired live in UAT because its gate condition — near-dead-equal past move 30 — did not arise; the 375px board-width win was owner-verified by eye without a recorded numeric before/after) are both recorded owner-verified/code-evidenced per 223-06-SUMMARY.md and are treated as resolved for this phase, not as outstanding checkpoints.

### Gaps Summary

None. All ROADMAP success criteria either hold as literally written or hold under a
recorded, git-committed owner deviation from the interactive UAT rounds that closed plan
06 — SC7 (the sounds settings switch) is the one criterion genuinely unmet, and it is
unmet by explicit, recorded owner decision (sounds always play for now; a disable option
is deferred to a later phase), not by defect. Phase goal — giving the 24 personas a voice
during the game and on the roster, and rebuilding the game screen so the voice has room —
is achieved and verified against the actual codebase.

---

_Verified: 2026-09-16T11:15:00Z_
_Verifier: Claude (gsd-verifier)_
