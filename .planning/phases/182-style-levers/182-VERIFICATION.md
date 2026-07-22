---
phase: 182-style-levers
verified: 2026-07-22T00:20:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 182: Style Levers Verification Report

**Phase Goal:** The bot's play is steerable by style parameters across the full ELO range — distinct opening choices, resign/draw behavior, and move preferences per style — without touching Custom mode or existing invariants (`policyTemperature`, player-derived inputs).
**Verified:** 2026-07-22T00:20:00Z
**Status:** passed
**Re-verification:** No — initial verification (post-code-review-fix state per orchestrator note)

## Context: Verifying Post-Fix State

Per the orchestrator's instruction, this verification targets the CURRENT branch state (`afa80b9b`), which already includes `182-REVIEW.md`'s 2 critical + 3 warning fixes (commits `606141df`..`f811f7e5`). The review itself was read and its claims independently re-derived from source (not trusted at face value) — see per-truth evidence below, all re-confirmed by direct code reading and test execution in this session, not by reading the review's prose alone.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | STYLE-01: each style plays a curated, corpus-validated opening book, wired live into `useBotGame`'s book resolution, gated on `settings.style` | ✓ VERIFIED | `styleOpeningLines.ts` (8 curated sets, corpus-membership tested); `styleBookWeighting` composes over `maiaPolicyWeighting` without changing `BookWeightingFn`'s 2-arg signature (`grep "BookWeightingFn = ("` unchanged); `resolveBookMove` in `useBotGame.ts:392-399` builds the weighting closure only when `style && styleName` resolve, else falls to the default — confirmed by direct read, not review prose |
| 2 | STYLE-02: style-specific draw contempt shifts accept behavior in the DOCUMENTED direction (not just per-formula) | ✓ VERIFIED | Re-derived independently: `drawValue = 0.5 + contempt` in `botDrawGate.ts:119` — Grinder (`contempt=0.15`) → target 0.65 (must be ahead to accept); Wall (`contempt=-0.08`) → target 0.42 (accepts mildly behind). This is the CORRECTED formula (CR-01 fix, commit `606141df`); the pre-fix `0.5 - contempt` inversion no longer present. `botDrawGate.test.ts` contempt tests pass (4/4) |
| 3 | STYLE-02: styled Light/Deep bots can resign via a hysteresis-gated predicate; Human-rung/in-book bots never resign (null sentinel) | ✓ VERIFIED (behavioral) | Hook-level `describe('styled resign wiring (STYLE-02)')` block (3 tests, `useBotGame.test.ts:1953+`) drives a real chess sequence through `renderHook`, asserting: counter increments only on fresh at/below-threshold grades and resets otherwise; `finalizeGame({reason:'resignation'})` fires exactly once the hysteresis floor is reached past `RESIGN_MIN_FULLMOVE`; an unstyled game never reaches the resign branch. All 3 pass. `consecutiveLowScoreTurnsRef` declared beside other latches (line 540), reset in `newGame()` (line 953) |
| 4 | STYLE-02 wiring is not corrupted by a stale async continuation racing `newGame()`/`resign()` | ✓ VERIFIED (behavioral) | CR-02 fix (commit `f2450bf5`): `pool.grade().then()` now checks `controller.signal.aborted` before touching `lastRootPracticalScoreRef`/`consecutiveLowScoreTurnsRef`/`finalizeGame` (`useBotGame.ts:1336`). Regression test `"a stale pool.grade() continuation resolving after newGame() does not mutate resign state for the new game (CR-02)"` passes |
| 5 | STYLE-03: Human-rung (`blend<=0`) personas get prior reweighting via a cheap chess.js move-feature classifier, LIVE in real play (not just unit tests) | ✓ VERIFIED | `classifyMoveFeatures` color-mirrored classifier tested for all 6 features × both colors (`botStyle.test.ts`); `applyStylePriorReweighting` wired into `selectBotMove.ts:133-135` (`blend<=0` branch, gated `settings.style ? ... : rawPolicy`); `settings.style` is threaded from `useBotGame.ts:1227` (`style: settings.style` in the `selectBotMove` config object) — confirmed this is genuinely reachable in a live bot turn, not dead code, per direct read of `runBotTurn` |
| 6 | STYLE-04: Light/Deep-rung personas get additive score shaping + a null-safe variance-preference term from `childScoreSpread`, LIVE in real play | ✓ VERIFIED | `RankedLine.childScoreSpread` computed in `buildRankedLines` (mutation-proof tested in Plan 01 — reverting the call made spread-asserting tests fail); `applyStyleScoreShaping` wired into `selectBotMove.ts:154-156` (search branch, gated); null-safe variance term confirmed (mutation-proof test flips the null guard); `settings.style` reaches the search branch via the same `useBotGame.ts:1227` wire as truth #5 |
| 7 | STYLE-05: style params are new, bot-only, additive fields — never merged into `budget`/`policyTemperature`, never player-derived, `botSampling.ts` stays pure | ✓ VERIFIED | `BotSettings.style?: BotStyleParams` is a sibling field to `budget: Omit<SearchBudget,'elo'\|'policyTemperature'>` (unchanged, `selectBotMove.ts:78`); `git diff --stat 0d740201..HEAD -- frontend/src/lib/engine/botSampling.ts` is empty (file untouched); `BotStyleParams` has no function-typed field (tested, `botStyle.test.ts`); `settings.style`/`BotGameSettings.style` values originate only from `BOT_STYLE_BUNDLES` (Plan 05 static data) or `undefined` — no player-state input threaded anywhere in the diff |
| 8 | Undefined/Custom-mode (no `style`) play is byte-identical to pre-182 behavior at every layer | ✓ VERIFIED | D-03 regression tests at every layer: `selectBotMove.test.ts` (undefined-style baseline derived independently via direct `samplePolicy`/`argmaxLine` calls, not a hardcoded literal); `useBotGame.test.ts` full 71+ pre-existing tests green under `DEFAULT_SETTINGS`; `botDrawGate.test.ts` contempt=0 regression; full frontend suite (2394/2394) green, including all pre-existing analysis-board/Custom-mode consumers |

**Score:** 8/8 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/engine/types.ts` | `RankedLine.childScoreSpread: number \| null` | ✓ VERIFIED | Field present, doc-commented, required (not optional), type-checks |
| `frontend/src/lib/engine/treeCommon.ts` | `computeChildScoreSpread` helper wired into `buildRankedLines` | ✓ VERIFIED | Mutation-proof tested |
| `frontend/src/lib/botDrawGate.ts` | `contempt` param + `wouldBotResign` + resign constants | ✓ VERIFIED | Sign-corrected post-review; `RESIGN_MIN_FULLMOVE`/`RESIGN_HYSTERESIS_TURNS` present, doc reframed (WR-03 fix) |
| `frontend/src/lib/engine/styleOpeningLines.ts` | 8 curated per-style×color `ReadonlySet<string>` + `styleLinesFor` | ✓ VERIFIED | Corpus-membership test passes (all 30 curated lines are genuine openings.tsv prefixes) |
| `frontend/src/lib/engine/botStyle.ts` | `BotStyleParams`, classifier, 3 pure transforms | ✓ VERIFIED | No function fields; unnormalized reweighting; null-safe clamped shaping; floor-respecting book factory |
| `frontend/src/lib/engine/botStyleBundles.ts` | 4 named `BotStyleParams` bundles + `BOT_STYLE_BUNDLES` | ✓ VERIFIED | Zero `[ASSUMED]` tags remain; identity assertions (contempt signs, feature multipliers) pass |
| `scripts/style-lever-measurement.mjs` | D-11 headless measurement script | ✓ VERIFIED | Re-run live in this session (`--n 10`) — produces a fresh TSV with correctly-signed per-style deltas, imports live `@/lib/engine/botStyle` exports (no reimplementation, grep-confirmed) |
| `frontend/src/lib/engine/selectBotMove.ts` | `BotSettings.style?` + 2 guarded regime hooks | ✓ VERIFIED | Byte-identical when undefined; `Omit<SearchBudget,'elo'\|'policyTemperature'>` unchanged |
| `frontend/src/hooks/useBotGame.ts` | `BotGameSettings.style?` + book/contempt/resign wiring + CR-01/CR-02 fixes | ✓ VERIFIED | All three seams confirmed live and gated; both review-flagged bugs confirmed fixed in current source |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `buildRankedLines` | `RankedLine.childScoreSpread` | `computeChildScoreSpread(child)` | ✓ WIRED | Mutation-proof tested |
| `wouldBotAcceptDraw` | accept decision | `drawValue = 0.5 + contempt` | ✓ WIRED (corrected) | Sign verified correct per documented per-style intent |
| `useBotGame` grade callback | `wouldBotResign` → `finalizeGame` | hysteresis ref + `controller.signal.aborted` staleness guard | ✓ WIRED | Hook-level behavioral tests pass; CR-02 staleness guard present |
| `resolveBookMove` | `selectBookMove` | `styleBookWeighting(styleLinesFor(...), history, bookBoost)` closure, gated on `style && styleName` | ✓ WIRED | Source-verified; default `maiaPolicyWeighting` path unaffected when style absent |
| `selectBotMove` blend<=0 | `applyStylePriorReweighting` | `settings.style ? ... : rawPolicy` | ✓ WIRED | Reachable from `useBotGame.ts:1227`'s `style: settings.style` |
| `selectBotMove` search branch | `applyStyleScoreShaping` | `settings.style ? ... : snapshot.rankedLines` | ✓ WIRED | Same reachability as above |
| `useBotGame.ts` | `selectBotMove` | `style: settings.style` in the search config object | ✓ WIRED | Confirmed at `useBotGame.ts:1227` — this is the link that makes STYLE-03/04 live rather than test-only |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `applyStylePriorReweighting` input | `rawPolicy` | live `deps.policy(fen, elo, side)` Maia call in `selectBotMove`, invoked from real `useBotGame` turns | Yes | ✓ FLOWING |
| `applyStyleScoreShaping` input | `snapshot.rankedLines` | live `search(fen, budget, deps, ...)` (MCTS/expectimax), invoked from real `useBotGame` turns | Yes | ✓ FLOWING |
| resign/draw score | `lastRootPracticalScoreRef` | live `pool.grade(fen, [uci])` Stockfish worker call on the actually-played move | Yes | ✓ FLOWING |
| book weighting | `moveHistorySan` | `chess.history()` off the live board (not a fresh empty-history `Chess(fen)`) | Yes | ✓ FLOWING |

No hollow/disconnected props found — every style lever's input traces to a live engine call, not a static/empty fallback.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| tsc project-wide type check | `npx tsc -b --noEmit` | zero errors | ✓ PASS |
| Style-specific unit + regression suite | `npx vitest run src/lib/__tests__/botDrawGate.test.ts src/hooks/__tests__/useBotGame.test.ts src/lib/engine/` | 349/349 passing | ✓ PASS |
| Full frontend suite | `npm test -- --run` | 2394/2394 passing (175 files) | ✓ PASS |
| Lint | `npm run lint` | 0 errors (3 pre-existing unrelated `coverage/` warnings) | ✓ PASS |
| Dead-export check | `npm run knip` | clean | ✓ PASS |
| `botSampling.ts` purity | `git diff --stat 0d740201..HEAD -- frontend/src/lib/engine/botSampling.ts` | empty | ✓ PASS |
| `policyTemperature` exclusion intact | `grep -n "Omit<SearchBudget" frontend/src/lib/engine/selectBotMove.ts` | still excludes `'elo' \| 'policyTemperature'` | ✓ PASS |
| No module-level mutable hysteresis state | `grep -nE "^(let\|var) " botDrawGate.ts`, `grep -nE "^(let\|var\|const) [a-zA-Z]+ = 0" useBotGame.ts \| grep -v useRef` | no matches | ✓ PASS |
| CR-01 targeted regression | `npx vitest run src/lib/__tests__/botDrawGate.test.ts -t "contempt"` | 4/4 passing | ✓ PASS |
| CR-02 targeted regression | `npx vitest run src/hooks/__tests__/useBotGame.test.ts -t "CR-02"` | 1/1 passing | ✓ PASS |
| Styled resign wiring targeted regression | `npx vitest run src/hooks/__tests__/useBotGame.test.ts -t "styled resign wiring"` | 4/4 passing | ✓ PASS |
| D-11 measurement script re-run | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/style-lever-measurement.mjs --n 10` | fresh TSV written, correctly-signed per-style deltas | ✓ PASS |
| Backend untouched | `git diff --stat 0d740201..HEAD -- app/` | 0 files | ✓ PASS |

### Anti-Patterns Found

None. Scanned all 9 phase-modified source files (`types.ts`, `treeCommon.ts`, `botDrawGate.ts`, `styleOpeningLines.ts`, `botStyle.ts`, `botStyleBundles.ts`, `selectBotMove.ts`, `useBotGame.ts`, `style-lever-measurement.mjs`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/stub patterns — zero debt markers, zero empty implementations. The two incidental "placeholder" string matches are benign prose (a UI-display ellipsis comment and a variable-naming comment), not stub code.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| STYLE-01 | 03, 04, 05, 07 | Style-specific opening book per persona | ✓ SATISFIED | Curated + corpus-validated data (03), composing factory (04), tuned bundles (05), live wiring gated on `settings.style` in `resolveBookMove` (07) |
| STYLE-02 | 02, 05, 07 | Style-specific draw contempt + resign policy | ✓ SATISFIED | Pure predicates (02), tuned per-style knobs (05), live hook wiring + hysteresis ref + 2 post-review bug fixes (07, confirmed present in current source) |
| STYLE-03 | 04, 06, 07 | Human-rung prior reweighting via chess.js classifier | ✓ SATISFIED | Classifier + pure transform (04), guarded hook in `selectBotMove` (06), `settings.style` threaded from `useBotGame` making it reachable in live play (07) |
| STYLE-04 | 01, 04, 06 | Light/Deep-rung score shaping + variance preference | ✓ SATISFIED | `childScoreSpread` signal (01), pure shaping transform (04), guarded hook in `selectBotMove` (06), live via the same STYLE-03 threading (07) |
| STYLE-05 | 04, 06 | Style params are bot-only, additive, never `policyTemperature`/player-derived; `botSampling.ts` pure | ✓ SATISFIED | Structural separation from `budget` (06), no-function-field `BotStyleParams` (04), `botSampling.ts` diff empty (verified independently this session) |

**Note on REQUIREMENTS.md staleness:** `.planning/REQUIREMENTS.md`'s traceability table (last updated 2026-07-21, before Plans 06/07 and the code-review fix pass landed on 2026-07-22) still marks STYLE-03 and STYLE-05 `Pending` and STYLE-01/02/04 `Complete`. Per-plan SUMMARY frontmatter tells the same partial-delivery story chronologically (each plan correctly deferred marking a requirement complete until the wiring that makes it *live* landed), but the code as it stands on `HEAD` delivers all 5 requirements per the evidence above. This is a documentation lag, not a code gap — flagged for whoever runs `/gsd-ship` or the next `/gsd-progress` to sync `REQUIREMENTS.md`'s traceability table, but it does not block this phase's goal achievement, which is assessed against the codebase per this agent's mandate.

### Human Verification Required

None. Every truth in this phase is either a structural/data invariant (grep/type-checkable) or a state-transition/behavioral invariant with a passing, non-trivial automated test (mutation-proofed in the executor's own verification work, independently re-run and re-confirmed against source in this session — not accepted on SUMMARY.md's word). The one item CR-02's own fix log flagged for "human verification" (an async/control-flow class of fix) has a concrete, currently-green regression test that exercises exactly the failure sequence described in the review (stale `pool.grade()` resolving after `newGame()`) — re-run in this session and confirmed passing, satisfying the same bar this agent would otherwise ask a human to confirm manually.

### Gaps Summary

No gaps found. All 5 requirement IDs (STYLE-01 through STYLE-05) are satisfied in the current codebase. The 2 critical + 3 warning issues surfaced by `182-REVIEW.md` (contempt sign inversion, stale-continuation resign corruption, a duplicated comment block, a misleading doc comment, a vestigial "shared default" framing) were independently re-verified as fixed by direct source inspection in this session, not by trusting the review's own Fix Log — the corrected formula, the staleness guard, and their respective regression tests were all read and re-executed directly.

The only non-blocking observation is the stale `.planning/REQUIREMENTS.md` traceability table described above (documentation lag, not code gap).

---

*Verified: 2026-07-22T00:20:00Z*
*Verifier: Claude (gsd-verifier)*
