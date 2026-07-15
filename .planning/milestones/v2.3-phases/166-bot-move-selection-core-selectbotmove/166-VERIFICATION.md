---
phase: 166-bot-move-selection-core-selectbotmove
verified: 2026-07-11T19:46:00Z
status: passed
score: 10/10 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 166: Bot Move Selection Core (`selectBotMove`) Verification Report

**Phase Goal:** Pure, provider-agnostic sample↔argmax move-selection blend both the app and the harness reuse — deliver `selectBotMove`.
**Verified:** 2026-07-11T19:46:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `selectBotMove(fen, {elo, blend, budget}, deps, signal?)` resolves to a legal UCI move for every non-terminal position (BOT-01/BOT-04) | ✓ VERIFIED | `selectBotMove.ts:87-128` covers blend=0/mid/1 and both fallback branches; all `selectBotMove.test.ts` cases assert a `/^[a-h][1-8][a-h][1-8][qrbn]?$/` or exact-move match. 12/12 pass. |
| 2 | blend=0 issues exactly one `deps.policy()` call and never invokes `deps.search`/`mctsSearch` (BOT-02, D-03) | ✓ VERIFIED | `selectBotMove.ts:95-99` returns before ever referencing `deps.search`. Test "calls deps.policy exactly once and deps.search zero times" (`selectBotMove.test.ts:86-96`) passes with call-count spies. |
| 3 | blend `b` in [0,1] is a sibling knob to the analysis-board slider, not the policy-temperature transform; b=0 = Human end, b=1 = Stockfish end (D-01) | ✓ VERIFIED | Module header (`selectBotMove.ts:27-32`) documents the D-02 exclusion; code never imports/calls `applyPolicyTemperature`; `budget` construction (line 103-108) never sets `policyTemperature`. |
| 4 | `selectBotMove` is an impure orchestrator; all sampling logic lives in pure, sync, separately-exported helpers `samplePolicy`/`sampleRankedLines`/`argmaxLine`/`fallbackMove` (D-09) | ✓ VERIFIED | `selectBotMove.ts` contains zero sampling/argmax logic — only awaits + 4 `?? fallbackMove(...)` dispatch sites. All four helpers exported sync from `botSampling.ts` with no `async`/Promise. |
| 5 | Randomness enters only via injected `deps.rng: () => number` in [0,1); live app passes `Math.random`, tests/harness pass a seeded PRNG (D-10) | ✓ VERIFIED | `grep -n "Math.random" frontend/src/lib/engine/selectBotMove.ts frontend/src/lib/engine/botSampling.ts` returns no matches — every random draw flows through the injected `deps.rng`/`rng` parameter. |
| 6 | blend=1 returns the deterministic argmax over `RankedLine.practicalScore` with UCI-ascending tie-break, ignoring array order (BOT-01, D-06) | ✓ VERIFIED | `argmaxLine` (`botSampling.ts:84-95`) scans all lines explicitly; test uses an array where index 0 is NOT the max and asserts the true max wins; tie-break test (`d2d4` vs `e2e4`, equal score) asserts ascending pick. |
| 7 | blend in (0,1) softmax-samples over `practicalScore` with sharpness `tau = TAU_MAX*(1-blend)` (BOT-01, D-04/D-05) | ✓ VERIFIED | `selectBotMove.ts:121` computes `tau = TAU_MAX * (1 - settings.blend)`. Independently re-verified at runtime (see Behavioral Spot-Checks) that `blend=0.5` produces the `tau=0.05` distribution, distinguishable from `tau=0.1` — closes the gap flagged by 166-REVIEW.md WR-05 (existing test only recomputed the formula, didn't observe it). |
| 8 | `budget.elo` is built symmetrically as `{w: elo, b: elo}`; the signature has no player-strength slot (BOT-03, D-07) | ✓ VERIFIED | `selectBotMove.ts:103-108`; test captures the budget passed to the search stub and asserts `budget.elo` equals `{w: 1732, b: 1732}` for `settings.elo=1732`. `BotSettings`/`BotMoveDeps` (lines 61-76) have no player-rating field. |
| 9 | An empty/degenerate distribution falls back to a uniform-random legal move; a position with zero legal moves throws (BOT-04/D-13/D-14) | ✓ VERIFIED (within documented D-13 scope) | D-13 (166-CONTEXT.md:110-114) explicitly scopes "degenerate" to `policy() returns {}`, all-zero weights, or empty `RankedLine[]` — all three are tested and pass (`samplePolicy({})`, `samplePolicy({a:0,b:0})`, empty-`rankedLines` fallback). Checkmate FEN throws with a message naming the FEN (D-14). See Anti-Patterns/Known Issues below for a NaN-weight edge case outside this documented scope. |
| 10 | A fixed mulberry32 seed yields the same selected UCI move across repeated runs (SC4, D-11) | ✓ VERIFIED | `botSampling.test.ts` "produces the same stream on repeated construction"; `selectBotMove.test.ts` "is deterministic under a fixed seed" (blend=0.5, two independent runs with `mulberry32(99)` produce identical moves). |

**Score:** 10/10 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/engine/botSampling.ts` | 5 pure exports: `mulberry32`, `samplePolicy`, `sampleRankedLines`, `argmaxLine`, `fallbackMove` + internal `weightedPick` | ✓ VERIFIED | All 5 present and exported (lines 50, 63, 84, 103, 127); `weightedPick` is module-internal (not exported), matches plan. |
| `frontend/src/lib/engine/selectBotMove.ts` | `selectBotMove` orchestrator, `BotSettings`, `BotMoveDeps`, `TAU_MAX`, `TAU_EPSILON` | ✓ VERIFIED | All present and exported (lines 48, 58, 61, 71, 87). |
| `frontend/src/lib/engine/__tests__/botSampling.test.ts` | Covers determinism, degenerate-null, array-order-independence, softmax stability, terminal throw | ✓ VERIFIED | 17 tests, all passing (confirmed via `npx vitest run`). |
| `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` | Covers BOT-01..04, symmetric ELO, fallback, signal | ✓ VERIFIED | 12 tests, all passing. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `selectBotMove.ts` | `botSampling.ts` | `import { samplePolicy, sampleRankedLines, argmaxLine, fallbackMove } from './botSampling'` | ✓ WIRED | Line 45; all four helpers actually invoked in the dispatch logic (lines 98, 117, 123, 126). |
| `selectBotMove.ts` | `mctsSearch.ts` | `import { mctsSearch } from './mctsSearch'`, used as `deps.search ?? mctsSearch` default | ✓ WIRED | Line 44, 102. |
| `argmaxLine`/`sampleRankedLines` | `RankedLine.practicalScore` | explicit field read, never `lines[0]`/`rankScore` shortcut | ✓ WIRED | `grep -n "practicalScore" botSampling.ts` → 5 hits, all in argmax/sampleRankedLines bodies, no bare `lines[0]` best-move shortcut found. |
| `fallbackMove` | `chess.js` | `new Chess(fen).moves({verbose:true})` → `.lan` | ✓ WIRED | Lines 128-135; independently confirmed `.lan` appends the promotion suffix (per 166-REVIEW.md's vendored-source check, matches test regex `[qrbn]?`). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| botSampling.test.ts suite | `npx vitest run src/lib/engine/__tests__/botSampling.test.ts` | 17/17 passed | ✓ PASS |
| selectBotMove.test.ts suite | `npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts` | 12/12 passed | ✓ PASS |
| `tsc -b` type-check | `npx tsc -b` | zero output, exit 0 | ✓ PASS |
| `npm run lint` | ESLint + knip | 0 errors (3 pre-existing `coverage/` warnings, unrelated) | ✓ PASS |
| `npm run knip` | dead-export scan | clean, no findings | ✓ PASS |
| Full frontend suite (run once) | `npm test -- --run` | 1794/1794 passed, 141/141 files | ✓ PASS |
| Independent NaN-weight repro (verifies 166-REVIEW.md WR-01 claim) | ad hoc vitest case: `samplePolicy({a1a2: NaN, b1b2: NaN}, () => 0.01)` | returned `'b1b2'`, not `null` | ✗ CONFIRMS REVIEW FINDING (see Known Issues) |
| Independent tau-formula repro (verifies 166-REVIEW.md WR-05 concern is not a functional gap) | ad hoc vitest case: `blend=0.5` with `rng=()=>0.001` on lines `[a1a2:0.3, b1b2:0.9]` | returned `'b1b2'` — matches the `tau=0.05` prediction, distinguishable from the `tau=0.1` prediction (`'a1a2'`) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BOT-01 | 166-01-PLAN.md | Bot blends raw-Maia sampling (b=0) to argmax practical score (b=1), practical-score-weighted sampling with slider-controlled sharpness in between | ✓ SATISFIED | Truths 1, 6, 7; REQUIREMENTS.md marks Complete. |
| BOT-02 | 166-01-PLAN.md | Full-human end runs exactly one Maia inference per move (no MCTS pass) | ✓ SATISFIED | Truth 2; REQUIREMENTS.md marks Complete. |
| BOT-03 | 166-01-PLAN.md | Bot plays its own configured ELO symmetrically, never adapts to player strength | ✓ SATISFIED | Truth 8; REQUIREMENTS.md marks Complete. |
| BOT-04 | 166-01-PLAN.md | Bot always returns a legal move, falling back gracefully on empty/degenerate policy | ✓ SATISFIED (within documented D-13 scope) | Truths 1, 9; REQUIREMENTS.md marks Complete. See Known Issues for a scope-boundary edge case. |

No orphaned requirements — REQUIREMENTS.md's Phase 166 row lists exactly BOT-01..04, all four also declared in the plan's `requirements:` frontmatter.

### Anti-Patterns Found

No debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) found in any of the 4 modified/created files. No empty-implementation stubs, no hardcoded-empty-data patterns. This is a pure library phase with no UI/render surface, so the props/JSX stub checks do not apply.

### Known Issues (Non-Blocking — from 166-REVIEW.md, independently reproduced)

166-REVIEW.md (code review, status `issues_found`, 5 warnings / 4 info) was generated after the phase's plan-level gates passed and has **not** been acted on by any subsequent commit (git log shows only `docs(166): add code review report` after the two feature commits — no follow-up fix commit exists). I independently reproduced the most significant finding to confirm it is real, not a review false-positive:

- **WR-01 (confirmed by reproduction):** `weightedPick`'s degenerate-distribution guard is `if (total <= 0) return null`, which is `false` for `NaN` (all NaN comparisons are false). `samplePolicy({a1a2: NaN, b1b2: NaN}, () => 0.01)` returns `'b1b2'` instead of `null`, so a policy-normalization defect crossing the Worker boundary would make the bot deterministically play the alphabetically-last policy key rather than triggering the D-13 fallback. **This does not violate must-have truth #9 as literally scoped** — D-13 (166-CONTEXT.md:110-114) explicitly defines "degenerate" as `{}`/all-zero weights/empty `RankedLine[]`, not NaN — but it is a real latent gap in code that Phase 168 (calibration harness) and Phase 169 (play loop) will both import unchanged.
- **WR-02:** `argmaxLine` latches a NaN `practicalScore` as unbeatable if it's the first line scanned (same NaN-comparison hole, `blend=1` path).
- **WR-03:** `sampleRankedLines` has no `tau > 0` precondition; `tau <= 0` produces `Math.exp(NaN)`, which rides the WR-01 hole to return the alphabetically-*worst* move. Currently unreachable via `selectBotMove` (guarded by `TAU_EPSILON`), but `sampleRankedLines` is itself an exported public API (D-09) with no documented guard.
- **WR-04:** `BotSettings.budget` is typed `Omit<SearchBudget, 'elo'>`, which does not exclude `policyTemperature` — a future Phase 169 call site could spread a caller-built budget (e.g., reused from the analysis board's own budget-builder) that includes `policyTemperature` straight through to the search budget, silently defeating the D-02 invariant the module header claims is enforced.
- **WR-05:** The `blend=0.5` "tau=0.05" test asserts `TAU_MAX * (1 - settings.blend) toBeCloseTo(0.05)` — this recomputes the formula rather than observing it through sampling behavior, so it would pass even if the code ignored `blend` entirely. I independently closed this gap at verification time (see Behavioral Spot-Checks) and confirmed the runtime behavior is correct; the test itself remains weak.

None of these five items fail a stated must-have truth as explicitly scoped by the phase's own decision record (D-13/D-14), so they do not block phase-goal achievement. They are flagged here for a deliberate human decision: fix now (cheap, isolated changes per 166-REVIEW.md's suggested patches) vs. accept as tracked follow-up debt before Phase 168/169 build on this code. Given both downstream phases import these modules unchanged and Phase 168 specifically measures bot behavior for calibration, an undetected NaN-driven "always plays the alphabetically-last/worst move" regression would corrupt calibration data silently — recommend fixing WR-01/WR-02/WR-03 as a quick follow-up before Phase 168 starts, rather than carrying it as accepted debt.

### Human Verification Required

None. All must-have truths are directly verifiable via source inspection, unit tests, and independent runtime reproduction; no visual/UX/external-service/real-time behavior is in scope for this pure-library phase.

### Gaps Summary

No gaps against the phase's stated must-haves. All 10 must-have truths verified, all 4 required artifacts present/substantive/wired, all 4 requirement IDs (BOT-01..04) satisfied and correctly reflected in REQUIREMENTS.md, zero debt markers, full test/type/lint gate green (29/29 new tests, 1794/1794 full suite, tsc clean, lint/knip clean).

The phase carries forward 5 unresolved code-review warnings (166-REVIEW.md) as non-blocking, verifier-confirmed known issues — see "Known Issues" above. These represent a real robustness gap outside the phase's explicitly documented D-13/D-14 scope, not a failure of the stated goal, but merit a human decision before Phase 168/169 depend on this code.

---

_Verified: 2026-07-11T19:46:00Z_
_Verifier: Claude (gsd-verifier)_
