# Phase 225: Engine Search Fixes (Root Comparability, Round Underfill, Findability Fallback) - Research

**Researched:** 2026-09-27
**Domain:** In-repo TypeScript search engine (`frontend/src/lib/engine`) plus Node/Python measurement harnesses (`scripts/`, `bin/`)
**Confidence:** HIGH for code sites, harness mechanics, and the underfill reproduction. MEDIUM for the D-01 PUCT visit-timing derivation (analytical, from verified constants, not measured). MEDIUM-LOW for the calibration-gate baseline question (a judgement call that needs the user).

## Summary

All three change sites exist exactly where CONTEXT.md says, and the baseline is green: 61/61 tests across `mctsSearch`, `findability`, and `fallbackExpectimax`, `calibration_parity_verdict.py --self-test` OK, stop-rule harness `--self-test` OK. I reproduced the round-underfill bug this session with a no-repo-change Node probe (real `mctsSearch`, fake providers, italian FEN, 50 nodes, c=4): flat gives 14 rounds, a two-candidate peaked policy gives 20, a one-candidate peaked policy gives 37 (`1,4,1,1,1,1,4,1,2,3,1,...`). The probe measures round size as the run length of consecutive `policy()` calls between `onSnapshot` events. That is deterministic and independent of the event loop, so D-08's permanent test should use it.

Four findings change the plan beyond what CONTEXT.md anticipated:

1. **Item 3 breaks two existing tests beyond `findability.test.ts`, and it reverses Phase 159's showcase behavior.** The `mctsSearch.test.ts` and `fallbackExpectimax.test.ts` "demotes the low-prior/high-V move" tests fail under D-10a: e2e4 goes from 0.511 to 0.787 against e2e3 at 0.591. The `findability.test.ts` @1000 D-03 case also flips as soon as the fixture's `V_fallback` exceeds 0.467, which a roughly equal position produces. Keeping it would need `pRef(1000)` above 0.133, which is above `pRef(600)` = 0.12 and breaks the monotonic anchor test. So "retune minimally" is not available. This is a user decision, not a planner retune.
2. **The maia-blindness runner is not in the repo.** The 2026-07-31 procedure used an uncommitted adaptation of `scripts/engine-wdl-leaf-quality.mjs`, recoverable from `b1764a83^`. That script scores `rankedLines[0]`, the findability-sorted analysis pick, not the bot's `argmaxLine` pick. It also runs without `stopRule`, so as written it cannot see item 1 at all, and it is contaminated by item 3. The phase needs a committed runner with an explicit selector and a stop-rule mode.
3. **D-01's guard delays the stop; it does not only admit prompt visits.** Every root child is unvisited at node 1, including the top one, so the existing test `clear-winner ... nodesEvaluated toBe(1)` must change. Terminal root children are never visited (`selectPath` filters `isClosed`), so the guard must count `isClosed` as settled, or a mate-in-1 root stalls the stop forever. By derivation, an in-window child at the far edge of the window with the floor prior is only picked around N≈20-25, not promptly.
4. **The Phase 199 calibration budget is already partly consumed.** Phase 199's Maia pooled shift against the July-21 curves was already −57.7 against a ±85 threshold. Engine and ORT changes have landed since the `b59f3b2b` sweep (onnxruntime 1.29, 8XN fixes), so "A0" is not the Phase 199 run. Reusing the rule verbatim answers "are the labels still right". It does not answer "did items 1 and 2 shift strength". The accept rule must pre-register what happens if A21 fails.

**Primary recommendation:** Land harness tooling first and treat that commit as the A0 base, so every arm worktree carries identical scripts. Take the D-02 measurement from the stop-rule harness's `onSnapshot` stream (no engine hook needed), then commit the accept rule. After that, implement item 2, then item 1, then item 3 as separate commits whose SHAs define A2 and A21. Run every multi-minute measurement inline from the orchestrator under `setsid nohup` plus Monitor, never inside an executor subagent.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

*(All D-01..D-15 are Claude's decisions made under full user delegation ("You decide"). CONTEXT.md states they are open to evidence-backed challenge by the researcher/planner. Copied verbatim.)*

### Item 1: Visit guard on the clear-winner stop

Scouting found the seed's "guard all root children, costs up to ~15 of 50 nodes" framing
understates the cost. The guard only blocks the stop, it does not force visits. Root PUCT
(`select.ts`, `C_PUCT` 1.4, `ROOT_PRIOR_FLOOR` 0.1 renormalized over up to 15 candidates) gives a
never-visited low-prior child an exploration term around 0.2-0.25 at N=8. So a child that is
clearly worse in Q is never visited, and "all children visited" never becomes true in exactly the
clear-winner positions the branch exists for. Guard-all would therefore mostly disable the
clear-winner stop. The plain within-margin guard is leaky the other way: it tests unboosted
values, and the first-expansion boost (the opponent's expected error) can exceed the 0.05 margin.

- **D-01:** Guard a **boost-aware window**: the clear-winner branch of `stopRuleSatisfied` may
  fire only when every root child with `topValue - child.value <= marginThreshold +
  ROOT_GUARD_BOOST_ALLOWANCE` has been visited (`visits >= 1`; a root child closed as a dead end
  (terminal) counts as satisfied since its value is exact). Children inside that window are near
  the top in Q, so root PUCT visits them promptly and the guard does not stall the search. No
  value corrections, no blend terms (roadmap constraint holds: the allowance only sizes the guard
  set, it never touches a value).
- **D-02:** `ROOT_GUARD_BOOST_ALLOWANCE` is a named constant (next to `FLAWCHESS_BOT_STOP_RULE` in
  `botBudget.ts` or as a field on `BotStopRule`, planner's call) set from a **measured**
  distribution: the root-child value change at first expansion (post minus pre) across the
  `scripts/engine-dispatch-stop-rule.mjs` position set at the bot ELO range, take roughly p90.
  This is design input, measured and committed (value + method in the phase report) **before**
  the accept rule is committed and before any gate arm runs. If the instrumentation turns out
  impractical, fall back to `0.10` (2x margin) and record that as the method.
- **D-03:** The **flatness branch stays unchanged** (seed + roadmap). Note the residual exposure
  in the doc (D-05) rather than guarding it: flatness requires every child within 0.02 of each
  other, and stopping on a near-tie is low-stakes.
- **D-04:** **No guard on the deadline cut** (`deadlineSearch.ts`). The deadline is wall-clock
  time pressure. The guard could overrun it by several rounds and make the bot flag, and
  `botBudget.ts` already documents a deadline-cut bot as intentionally weaker. Instead, the
  stop-rule measurement reports (report-only, not a gate criterion) how often a deadline cut fires
  with an unvisited in-window root child.
- **D-05:** Document the parity effect in `docs/flawchess-engine-explained-2026-07-06.md`: first
  expansion of an opponent-to-move node raises the value (opponent expected error), own-node
  expansion lowers it, alternating by depth; the root max compares boosted and unboosted children;
  what the D-01 guard fixes and what it deliberately leaves (flatness, deadline cut).

### Item 2: Round underfill in `selectPath`

- **D-06:** Fix as seeded. A non-root node reached with zero selectable children is blocked for
  the rest of the round and the walk restarts from the root; flags cleared after the round's
  `Promise.all`. Root with no selectable child still returns null (fill loop breaks as today).
  Round structure, canonical apply order, and the module header's determinism scope stay
  unchanged. Independent of the rejected continuous dispatch (Phase 198 / SEED-130).
- **D-07:** Use a **separate per-round block flag** (e.g. `isBlocked` plus a per-round list to
  clear), not an overload of `isPending`, which means "dispatched this round" and is read at apply
  time. Exact name and placement are Claude's discretion.
- **D-08:** The throwaway harness becomes a **permanent unit test**: real `mctsSearch`, fake
  providers, 50 nodes / concurrency 4, peaked non-root policy (the one-candidate 92% and
  two-candidate 55/37% shapes), asserting every round except the budget tail dispatches
  `concurrency` grades. Run the revert-the-fix mutation check (restore `return null` / `break`
  and confirm the test fails) per the project's mutation-test rule. Existing determinism tests
  must stay green unchanged.
- **D-09:** Add a fix-site comment in `selectPath` noting that `reports/continuous-dispatch/apply-order-design.md`
  §5 misread this path as the saturated-tree case. Do not edit that historical report.

### Item 3: Findability fallback

The seeded formula `f*V + (1-f)*V_fallback` breaks the module's core invariant: for a move with
`V < V_fallback` and low findability, it pulls rankScore **up** toward the average, so a
hard-to-find blunder ranks near the mean. The module header's whole argument is that rankScore
can only demote, never promote.

- **D-10a:** `rankScore = f * V + (1 - f) * min(V, V_fallback)`, with `f = min(1, P/Pref)` as
  today. Properties: `f = 1` gives exactly V; rankScore <= V always; a move worse than the
  fallback is not penalized for findability (it sorts by its own V, which is already low). Update
  `findability.ts`'s header to state the new invariant and why the clamp exists.
- **D-10b:** `V_fallback = sum(prior_i * value_i)` over root children, using `child.prior` (the
  renormalized Maia prior, the same `pYou` rankScore already reads), **not**
  `rootExplorationPrior`. Computed once per `buildRankedLines` call. Guard: empty root or zero
  total prior gives `V_fallback = 0`, which reduces the formula to today's `f*V` (no NaN).
- **D-10c:** Keep `P_REF_ANCHORS` unchanged unless a D-03 regression case in
  `findability.test.ts` fails under the new formula. If one fails, retune anchors minimally and
  record the before/after anchors and the failing case in the phase summary. Add a unit case for
  the clamp (a low-prior move with V below V_fallback must not rank above a findable move with
  higher V).
- **D-10d:** Bot-invariance test: same search snapshot, old vs new rankScore, `selectBotMove`
  picks the identical move for a fixed rng (proves item 3 does not touch bot play).

### Item 4: Non-root candidate cap

- **D-15:** **Deferred, not in this phase.** It is a third bot-strength change: it would need its
  own calibration arm for attribution, and item 2's throughput win reduces the urgency. Its benefit
  (MultiPV cost at high-T deep own-nodes) is unmeasured. Captured under Deferred Ideas.

### Measurement gate

- **D-11:** Accept rule committed at `reports/engine-search-fixes-225/accept-rule.md` **before any
  gate data** (after the D-02 design measurement), never edited after; overrides only as separate
  override docs (Phase 195/197/198/199 pattern). Include a machine-readable twin if a verdict
  script is involved.
- **D-12:** **Stacked arms** for attribution, since item 3 does not touch bot trees:
  - `A0` baseline (current `main`)
  - `A2` = + item 2
  - `A21` = + item 2 + item 1 (the ship candidate)
  Item 2 is attributed by A2 vs A0, item 1 by A21 vs A2.
- **D-13:** Per-criterion arms:
  - Throughput: `scripts/engine-grading-depth-ab.mjs`, A0 vs A2, bot 50/c4 and analysis 400/c4,
    wall clock + grade CPU. Expect a large win on peaked positions; no pass threshold beyond "no
    regression", since the fix is a confirmed bug.
  - Move quality: `fixtures/engine/maia-blindness.tsv` (12 positions, d20, §4b 0.05 margin) per
    `reports/grading-ladder/override-2026-07-31.md`, at A0, A2, A21; must not regress.
  - Stop rule: `scripts/engine-dispatch-stop-rule.mjs` nodes-at-stop distribution, A2 vs A21. The
    accept rule fixes a numeric ceiling (e.g. a p95 think-time or nodes-at-stop bound derived from
    `computeThinkDeadlineMs` at the bot's typical clock) before data. Also reports the D-04
    deadline-exposure count (report-only).
  - Calibration: **reuse the Phase 199 parity check verbatim**: same five cells (incl. the
    `1100/0.00` null control), same three criteria and thresholds, `scripts/calibration_parity_verdict.py`,
    against the same committed curves, per `reports/bot-parity-199/runbook.md`. Run on **A21
    first**. Only if it fails or shows a notable shift, run A2 to attribute between items 1 and 2.
  - Analysis ordering (item 3): qualitative check on a handful of winning positions where a
    hard-to-find move previously ranked below a much worse findable one, plus the D-10c/D-10d
    unit tests.
- **D-14:** **On a failed gate, do not refit.** A refit (or a full 24-persona recalibration) is out
  of scope. Ship only the items whose arms pass (e.g. item 2 alone if A2 passes and A21 fails),
  hold the failing item, and record a follow-up seed. Item 3 ships independently of the bot gates.

### Claude's Discretion
- The user delegated all four gray areas (guard scope, findability formula, item 4, measurement
  design). Everything in D-01..D-15 is Claude's call and open to evidence-backed challenge by the
  researcher/planner.
- Naming and placement of the block flag (D-07) and the allowance constant (D-02).
- Exact stop-rule ceiling number in the accept rule (D-13), fixed before data.

### Deferred Ideas (OUT OF SCOPE)
- **Non-root candidate cap (~6-8) in `truncateAndRenormalize`** (SEED-170 item 4): deferred per D-15. Revisit with its own throughput + calibration arm if deep-node MultiPV cost shows up as a bottleneck after item 2 ships. Record it in SEED-170 (or a new seed) at phase close.
- **Guarding the flatness branch and the deadline cut** (D-03/D-04): revisit only if the deadline-exposure count from the stop-rule measurement is high.
- Still out of scope per roadmap: repetition/game-history awareness, continuous dispatch (SEED-130), cross-FEN Maia batching, grade-cache set-mixing redesign.
</user_constraints>

## Project Constraints (from CLAUDE.md)

- **Pre-merge gate (mandatory before the squash-merge to `main`):** `uv run ruff format app/ tests/ scripts/ analysis/`, `uv run ruff check . --fix`, `uv run ty check app/ tests/ scripts/`, `uv run --project analysis --with ty ty check analysis/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`, `uv run pytest -n auto -x`, `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )`. This applies even though the phase is frontend-only. [VERIFIED: CLAUDE.md]
- **No magic numbers.** The guard allowance, block logic constants, and any harness thresholds get named constants. [VERIFIED: CLAUDE.md]
- **Nesting depth ≤ 4** (eslint `max-depth` gates `npm run lint`). `selectPath`'s restart branch must stay within it. [VERIFIED: frontend/CLAUDE.md]
- **`noUncheckedIndexedAccess`**: narrow every index access. [VERIFIED: frontend/CLAUDE.md]
- **`npm run lint`/`npm test` do not type-check.** Run `npm run build` (tsc -b) after changing the `BotStopRule` type. [VERIFIED: frontend/CLAUDE.md]
- **Knip in CI.** New exports must be imported somewhere. Keep helpers module-private. [VERIFIED: frontend/CLAUDE.md]
- **Comment bug fixes at the fix site** (D-09's `selectPath` comment satisfies this for item 2). [VERIFIED: CLAUDE.md]
- **Changelog:** add `[Unreleased]` bullets at merge. [VERIFIED: CLAUDE.md]
- **GSD scope discipline:** do not add unplanned work. Item 4 and deadline guarding stay deferred. [VERIFIED: CLAUDE.md]
- **Em-dashes sparingly** in prose, docs, and commit messages. [VERIFIED: CLAUDE.md]
- **Project memory binding here:** never add per-file vitest timeouts (project-wide in `vite.config.ts`); mutation-prove every gap fix by reverting it; run long measurements from the orchestrator, not a backgrounded executor; do not re-suggest the 24-persona recalibration; when a pre-committed gate fails, check what it holds fixed before escalating; `gh pr checks --watch` is not a CI gate. [CITED: MEMORY.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Item 1 visit guard | Browser / Client (`mctsSearch.ts` `stopRuleSatisfied`) | Offline harness (`calibration-harness.mjs` imports the same code) | The search runs in the browser. The Node harness imports the live TS through the `@/` alias hook, so there is one implementation. |
| Guard allowance constant | Browser / Client (`types.ts` `BotStopRule` + `botBudget.ts`) | — | `FLAWCHESS_BOT_STOP_RULE` is the single definition shared by the app and the harness (botBudget.ts header). |
| Item 2 round fill | Browser / Client (`mctsSearch.ts` `selectPath` + fill loop) | — | Affects every `mctsSearch` caller: bot and the analysis board. |
| Item 3 ranking | Browser / Client (`treeCommon.ts` `buildRankedLines` + `findability.ts`) | — | Sort-only. It affects both runners (`mctsSearch`, `fallbackExpectimax`) through the shared `buildRankedLines`. |
| Throughput / stop-rule / move-quality gates | Offline Node harness (`scripts/*.mjs`) | — | Browser grade nondeterminism (SEED-130) makes the harness the gate basis. |
| Calibration verdict | Offline Python (`scripts/calibration_parity_verdict.py`) | Node harness under `bin/preset-supervisor.sh` | Existing Phase 199 pipeline. |
| Backend / DB | — | — | Nothing in this phase touches the backend. |

## Verified Change Sites (exact, read this session)

### `frontend/src/lib/engine/mctsSearch.ts`

- `rootChildValueExtremes(root)` at **lines 198-221**. Builds `entries: { uci, value }[]` from `root.children` in one pass, then computes top, runner-up (`-Infinity` for one child), min, and max. Returns `{ argmaxUci, topValue, runnerUpValue, minValue, maxValue } | null`. [VERIFIED: mctsSearch.ts:198-221]
- `stopRuleSatisfied(root, rule, nodesEvaluated, state)` at **lines 245-260**. Verbatim body:
  ```ts
  const extremes = rootChildValueExtremes(root);
  if (!extremes) return false;
  state.stableCheckCount = extremes.argmaxUci === state.stableArgmaxUci ? state.stableCheckCount + 1 : 1;
  state.stableArgmaxUci = extremes.argmaxUci;
  if (nodesEvaluated < rule.minNodes || state.stableCheckCount < rule.stabilityWindow) return false;
  return (
    extremes.topValue - extremes.runnerUpValue >= rule.marginThreshold ||
    extremes.maxValue - extremes.minValue <= rule.epsilonThreshold
  );
  ```
  [VERIFIED: mctsSearch.ts:245-260]
- `selectPath(root: EngineNode, maxPlies: number): EngineNode[] | null` at **lines 287-327**. Line 293 is `if (root.isPending || root.isClosed) return null;`. The candidate filter at lines 309-311 is `if (!child.isPending && !child.isClosed) candidates.push(child);`. Line 312 is `if (candidates.length === 0) return null; // every child dispatched this round or fully searched`. At the root, `SelectionChild` carries `q: c.value` and `rootExplorationPrior` (lines 314-320). [VERIFIED: mctsSearch.ts:287-327]
- `EngineNode` interface at lines 95-110 has `isPending`, `isClosed`, and `rootExplorationPrior`. `createRoot` (112-140) and `createChildNode` (142-179) set a **terminal child to `isExpanded = true; isClosed = true`** at creation (lines 172-177). [VERIFIED: mctsSearch.ts:95-179]
- Fill loop at **lines 549-583**. `const path = selectPath(root, budget.maxPlies); if (path === null) break;` (553-554). The dead-end branch (558-573) bumps visits and calls `propagateClosure`. The pending marker is set at 581. `toExpand.length === 0` means the tree is fully searched (585-592). Dispatch uses `Promise.all(... dispatchExpansion ...)` (597-599). The apply loop (601-618) calls `stopRuleSatisfied` once per applied expansion (612) and has an early-stop break at 617. [VERIFIED: mctsSearch.ts:542-619]
- `applyExpansion` at lines 342-405. Visits bump along the whole path **at apply time** (line 404). [VERIFIED]

**Consequence (verified from code, not in CONTEXT.md):** because terminal and closed children are filtered out of `selectPath` (309-311) and never receive an apply-time bump, **a terminal root child keeps `visits === 0` forever**. Root children closed by the WR-04 degenerate close or the 8XN-7 empty-grade close are also never visited. The D-01 guard must therefore treat `child.isClosed` as settled, not only `child.isTerminal`. Otherwise a mate-in-1 root (terminal top child, value 1) can never clear-winner-stop.

### `frontend/src/lib/engine/select.ts`
- `POLICY_MASS_THRESHOLD = 0.9` (line 21), `C_PUCT = 1.4` (line 24), `ROOT_PRIOR_FLOOR = 0.1` (line 32). [VERIFIED: select.ts:21,24,32]
- `selectChild(children, parentVisits, isRoot)` (114-139). At the root: `score = q + C_PUCT * rootExplorationPrior * sqrt(N)/(1+n)`. Off the root: `prior * sqrt(N)/(1+n)`. Canonical UCI tie-break. [VERIFIED: select.ts:114-139]

### `frontend/src/lib/engine/botBudget.ts` and `types.ts`
- `FLAWCHESS_BOT_MAX_NODES = 50` (44), `FLAWCHESS_BOT_MAX_PLIES = 8` (47), `FLAWCHESS_BOT_CONCURRENCY = 4` (50), and the stop rule at lines 53-58:
  ```ts
  export const FLAWCHESS_BOT_STOP_RULE: BotStopRule = {
    marginThreshold: 0.05,
    epsilonThreshold: 0.02,
    stabilityWindow: 3,
    minNodes: 8,
  };
  ```
  [VERIFIED: botBudget.ts:44-58]
- `interface BotStopRule { marginThreshold: number; epsilonThreshold: number; stabilityWindow: number; minNodes: number; }` at types.ts:57-66. `SearchBudget.stopRule?: BotStopRule` at 83. [VERIFIED: types.ts:57-84]
- **BotStopRule literal construction sites** that must add any new required field: `mctsSearch.test.ts:963`, `:993`, `:1019`. `useFlawChessEngine.test.tsx:46-47` asserts margin and epsilon ≥ 0; extend it for the allowance. [VERIFIED: grep]
- `stopRule` consumers: `hooks/useBotGame.ts:127` (app), `scripts/calibration-harness.mjs:598` (the calibration harness, which is why item 1 is calibration-relevant), `scripts/engine-dispatch-stop-rule.mjs`, `scripts/lib/calibration-determinism.check.mjs`, and two `engine_disagreement_study` scripts. [VERIFIED: grep]

### `frontend/src/lib/engine/findability.ts`
- `P_REF_ANCHORS` (lines 32-39): `[600, 0.12], [1000, 0.08], [1400, 0.05], [1800, 0.03], [2200, 0.015], [2600, 0.005]`. [VERIFIED: findability.ts:32-39]
- `rankScore(pYou: number, pRef: number, value: number): number` (73-76): `if (pRef <= 0) return value; return Math.min(1, pYou / pRef) * value;` [VERIFIED: findability.ts:73-76]

### `frontend/src/lib/engine/treeCommon.ts`
- `buildRankedLines(root, rootElo)` (415-447). `pRef` is computed once. The sort key is `rankScore(child.prior, pRef, child.value)` (line 440), with a canonical UCI tie-break. It is shared by `buildSnapshot` (484-492), so **both** `mctsSearch` and `fallbackExpectimax` get item 3 automatically. [VERIFIED: treeCommon.ts:415-492]
- **Root priors do not sum to 1.** `mergeExtraRootMoves` (147-168) adds injected priors on top of an already-renormalized set, and `applyRootCandidateHardCap` (170-190) slices to `ROOT_CANDIDATE_HARD_CAP` (= 15, policyTemperature.ts:56) **without renormalizing**. Illegal-candidate drops in `applyExpansion` also remove mass. So `V_fallback` must be the prior-weighted **mean** `Σ p·v / Σ p`, not the raw sum. `backupExpectation` in backup.ts:43-47 already implements exactly that normalization, with a `totalPrior === 0 → 0.5` guard. [VERIFIED: treeCommon.ts:147-190, backup.ts:43-47]

### `frontend/src/lib/engine/deadlineSearch.ts`
- `BOT_MIN_SEARCH_NODES = FLAWCHESS_BOT_STOP_RULE.minNodes` (line 58). The deadline cut is enforced from outside by aborting an inner signal from `onSnapshot` once `nodesEvaluated >= minNodes`. It stays unchanged (D-04). [VERIFIED: deadlineSearch.ts]

### Bot order-independence (D-10d premise): confirmed
- `botSampling.ts` `weightedPick` sorts `[...entries]` by UCI before the cumulative walk (line 33). `sampleRankedLines` reads `practicalScore`. `argmaxLine` scans every line. `selectBotMove.ts` feeds `snapshot.rankedLines` (or `applyStyleScoreShaping(...)`, a per-line `.map`, botStyle.ts:286-296) only into these. [VERIFIED: botSampling.ts:32-113, selectBotMove.ts, botStyle.ts:286-296]
- The bot's draw and resign gate score comes from a **separate** `grade()` of the chosen move (`useBotGameEngineDispatch.ts:493-496`), not from `rankedLines` order. [VERIFIED]
- Order-dependent consumers that item 3 **does** change are all on the analysis page: `pages/Analysis.tsx:892` (FlawChess arrow = `rankedLines[0]`), `:931` and `:1867`, `hooks/analysis/useAnalysisEngineLines.ts:311` (`slice(0, FC_MAX_LINES)`, which also changes **which** lines are visible, not only their order), `components/analysis/FlawChessEngineLines.tsx:441`, and `lib/flawChessVerdict.ts` (the aligned/safe/sharp verdict compares `rankedLines[0]` against Stockfish #1, so more winning positions will read "aligned"). `useTrainGradingEngine.ts:544`'s `lines[0]` is Stockfish PV lines, **not** affected. [VERIFIED: grep + read]

## Challenges to D-01..D-15 (evidence-backed)

### C-1 (D-01): "Children inside that window are near the top in Q, so root PUCT visits them promptly" is only partly true
Derivation from verified constants. An unvisited root child gets exploration `C_PUCT·P_root·√N`. With 15 root candidates at the floor, `P_root ≈ 0.1/Σfloored`, which is 0.05-0.067. At N=8 that is `1.4·0.05·2.83 ≈ 0.20`. The top child (say `P_root` 0.25, n=5) carries `1.4·0.25·2.83/6 ≈ 0.165`. So an unvisited child with Q gap `g` beats the top only when `g < 0.20 − 0.165 ≈ 0.035` at N=8. The unvisited bonus grows with √N while the top's bonus shrinks with n. A child at the far edge of a 0.15 window (margin 0.05 + allowance 0.10) with the floor prior is first picked around **N≈20-25**. [ASSUMED: analytical derivation from VERIFIED constants; not measured]

Implications for the plan:
- The guard **delays** clear-winner stops in positions with a low-prior in-window runner-up. It does not disable them (N≈25 < 50). The stop-rule arm will measure how often.
- Item 2 interacts favorably. When a root subtree blocks mid-round, the restarted walk moves to the next root child in PUCT order, so rounds widen at the root and in-window children get visited sooner. That is another reason A21 is measured on top of A2, never alone.
- **Every root child is unvisited at node 1, including the top.** The existing test `mctsSearch.test.ts:950-976` ("clear-winner ... `expect(snapshot.nodesEvaluated).toBe(1)`") **will fail** under the guard. It must be rewritten as an intended behavior change (e.g. assert early-stop fires at the first node count where every in-window child is settled). The flatness test (978-1005) and the min-nodes test (1007-1027) stay green. The min-nodes test fires via flatness because every value ties at 0.5. [VERIFIED: test read + guard semantics]

**Keep D-01's window guard, but amend it in three ways:** (a) "settled" = `visits >= 1 || isClosed`, not `isTerminal`; (b) the top child is in its own window (gap 0) and must be settled too; (c) the window is `topValue − child.value <= marginThreshold + allowance`, correctly sized. An unvisited child with gap `g` and future boost `b` threatens the stop exactly when `g − b < margin`.

### C-2 (D-02): the measurement is practical and needs no engine hook
`RankedLine` already carries `visits` and `practicalScore` (= `child.value`) for every root child (treeCommon.ts:429-436), and `onSnapshot` fires after **every** applied expansion (mctsSearch.ts:616). A root child's `visits` goes 0→1 exactly at its own first expansion, because it is the leaf of that path. Root children are depth 1, so they are never dead-end discoveries. A terminal root child is never visited at all. So in the snapshot stream, `delta = practicalScore(k) − practicalScore(k−1)` for the child whose visits flipped 0→1 at snapshot k is exactly the first-expansion change. [VERIFIED: code path read]

- Run **without** `stopRule` (full 50 nodes, c=4) so more root children get expanded. With the stop rule the sample truncates at 8-24 nodes.
- ELOs: the four exposed calibration-cell ELOs, **1300, 1500, 1900, 2300**. The boost is the opponent's expected error, so it shrinks with ELO. Report per-ELO p50/p90/max plus the pooled p90. Recommendation: set the allowance to the **pooled p90, rounded up to 0.01**, and record the per-ELO table.
- Positions: the stop-rule harness's own 16-position set (4 built-in + `--openings 12`) with `--maia-fifo`, which mirrors `reports/continuous-dispatch/accept-rule.md` §1.
- Selection bias caveat for the report: only children that PUCT actually expands are sampled, i.e. the higher-Q, higher-prior ones. Those are the in-window population the guard cares about, so the bias is acceptable. State it anyway.
- Cost: about 110 s of search per ELO run (the 2026-07-31 ladder rows sum to 109 s over 16 positions at 50 nodes), so roughly 8-10 min for four ELOs. Over the 10-min Bash cap, so run under `setsid nohup` plus Monitor. [VERIFIED: reports/data/engine-grading-depth-ab-2026-07-31T13-46-35-696Z.tsv, ladder rows sum wall 109 s]

### C-3 (D-10a/D-10c): the clamp is correct, but "retune minimally" will not work
The clamp properties hold (verified algebra): `rankScore = V` when `V <= Vfb`; otherwise `rankScore = f·V + (1−f)·Vfb ∈ [Vfb, V]`. So `min(V, Vfb) <= rankScore <= V`. Moves below `Vfb` sort by their own V, and every move above `Vfb` outranks every move below it. The D-10c clamp test is guaranteed to pass.

What CONTEXT.md did not anticipate. I computed these this session (scratch script, Lichess K = 0.00368208, the same constant as `liveFlaw.ts`):

| Existing test | Old rankScore | New rankScore (D-10a) | Outcome |
|---|---|---|---|
| `mctsSearch.test.ts` 444-497 "demotes the low-prior/high-V move" (@600; e2e4 prior 0.066 V 0.929; e2e3 prior 0.934 V 0.591; Vfb 0.613) | e2e4 0.511 < e2e3 0.591 | e2e4 **0.787** > e2e3 0.591 | **FAILS** (e2e4 now first) |
| `fallbackExpectimax.test.ts` 285-303 (same fixture) | same | same | **FAILS** |
| `fallbackExpectimax.test.ts` 305-323 "identical sequence as mctsSearch" | — | both runners share `buildRankedLines` | passes |
| T=2 composition tests (`mctsSearch.test.ts` 574-614, `fallbackExpectimax.test.ts` 388-419) | assert e2e4 first at T=2 | e2e4 first already at T=1 | assertion passes, **comment premise ("reverses the T=1 winner") becomes false**. Rewrite the comment or the test. |
| `findability.test.ts` @600 (Nb5 5%/0.6, Qxf2 9%/0.57, Rxf2 57%/0.35, rest 29% unspecified) | Qxf2 wins | Qxf2 wins for any `V_rest < 0.87` (at `V_rest` 0.5: Qxf2 0.534 vs Nb5 0.498) | passes at any plausible Vfb |
| `findability.test.ts` @1000 (Qb8 5%/0.6 vs chart candidate 30%/0.55; pRef 0.08, f = 0.625) | Qb8 0.375 < 0.55 | `0.375 + 0.375·Vfb`, which is > 0.55 iff **Vfb > 0.467**. With the unspecified 65% mass at `V_rest` > 0.418, Vfb > 0.467 | **FAILS at any roughly equal Vfb (≈0.5 gives 0.5625)** |

[VERIFIED: computed this session from the fixture values in the test files and the D-10a formula]

- The `rankScore` signature must change (a 4th `fallbackValue` argument, or a precomputed arg). Every `findability.test.ts` case then needs an explicit `V_fallback`. **Pin those fixture values from a stated rule before running** (recommendation: unlisted prior mass valued at 0.5 neutral). Otherwise the pass/fail of the D-03 cases is a free parameter the test author chooses.
- Keeping @1000 by retuning needs `f·0.6 + (1−f)·0.52 < 0.55`, i.e. `f < 0.375`, i.e. `pRef(1000) > 0.133`. That exceeds `pRef(600) = 0.12` and breaks the existing "monotonically non-increasing" test, so it would drag the whole curve up. That is not a minimal retune.
- **This is the semantic change the seed asked for** ("at V~0.95 a hard-to-find winning move ... ranks below a 0.6 move"). But it also reverses Phase 159's showcase behavior (its fixture and the docs' Nb5 story), and it relaxes findability in near-equal positions (the @1000 case). **Recommendation: surface this to the user before implementing item 3**, with three options. (a) Accept: rewrite the two "demotes" tests to the new semantics, and restate the @1000 case to a V gap where findability still wins, e.g. Qb8 0.6 vs chart 0.58. (b) Ship item 3 with an anchor re-derivation (a larger change). (c) Hold item 3. This is a checkpoint, not a planner decision.

### C-4 (D-10b): normalize V_fallback, reuse `backupExpectation`
Because root priors do not sum to 1 (see the change-site notes), `Σ prior·value` is biased by the cap and injection. Use the prior-weighted **mean**. `backupExpectation(children)` (backup.ts:43-47) is that function. Its zero-total guard returns 0.5, while D-10b wants 0. Implement a tiny helper in `findability.ts` or `treeCommon.ts` that sums once and returns 0 when `totalPrior === 0`, or call `backupExpectation` after an explicit `totalPrior === 0` check. Don't hand-roll a third expectation formula with different semantics.

### C-5 (D-13 move quality): the runner does not exist, and its selector matters
- `reports/grading-ladder/override-2026-07-31.md` "Reproducing this run": `scripts/engine-wdl-leaf-quality.mjs` was deleted by `b1764a83` and "is recoverable at `b1764a83^`". The actual run used an uncommitted "purpose-built adaptation". [VERIFIED: override-2026-07-31.md; `git show b1764a83^:scripts/engine-wdl-leaf-quality.mjs` exists, 492 lines]
- That script's `runArm` returns `snapshot.rankedLines[0]?.rootMove`, the **findability-sorted** pick, and builds `budget = { maxNodes, maxPlies, concurrency, elo }` with **no `stopRule`**. [VERIFIED: b1764a83^:scripts/engine-wdl-leaf-quality.mjs]
- Consequences: (1) run verbatim, A21 ≡ A2 (item 1 is invisible without `stopRule`); (2) the metric moves with item 3 (not a bot metric); (3) the bot at blend=1 plays `argmaxLine(practicalScore)`, not `rankedLines[0]`.
- **Recommendation:** add `scripts/engine-move-quality.mjs` (single arm, "whatever `mctsSearch` is live"). Adapt the fixture loader, the §4a integrity precheck (chess.js legality before spawning engines), `gradeChosenMoves` (one independent depth-18 MultiPV grade, `evalToExpectedScore`), and `REGRESSION_MARGIN = 0.05` from `b1764a83^`, with:
  - `--stop-rule on|off` (on = `FLAWCHESS_BOT_STOP_RULE`; off = the 2026-07-31 procedure),
  - both selectors emitted per row: `bot_move` (`argmaxLine(snapshot.rankedLines)`, imported from `botSampling.ts`) and `analysis_move` (`rankedLines[0]`), each with `es`, `delta vs correct_move`, and a verdict,
  - a `--self-test` (parseArgs plus fixture integrity) mirroring `engine-dispatch-stop-rule.mjs`.
  - Judged by the accept rule: `bot_move`, stop-rule off for A2 vs A0, on for A21 vs A2. `analysis_move` is report-only and gives item 3 a quantitative signal, since these 12 positions are exactly "hard-to-find winning sacrifice" positions.

### C-6 (D-13 calibration): "verbatim against the same committed curves" answers a different question than attribution
- Phase 199 result against July-21: Maia pooled **−57.7** (threshold ±85), SF pooled −9.9 (±50). SF exposed cells 1300/0.05 (−101.7) and 2300/0.5 (+174.4) were already outside their committed CIs, in one family only. [VERIFIED: reports/bot-parity-199/report.md]
- Engine-affecting commits since the `b59f3b2b` sweep include `463b93de7` (onnxruntime 1.29 native+web), `9064ab922` / `d323a5379` / `e55b26a93` (8XN fixes), and the Maia threading and iOS releases. So neither July-21 nor the 199 run equals today's A0. [VERIFIED: `git log b59f3b2b..HEAD -- frontend/src/lib/engine/`]
- A21-vs-July is the right **product** question: the shipped labels come from the July fit, per the SEED-133 memory note. But it cannot attribute a failure to items 1/2 versus pre-existing drift. Per the memory note on proxy gates, a failure must first be checked against what the gate holds fixed.
- **Recommendation for the accept rule (pre-registered):**
  1. PRIMARY: A21 five cells against `reports/data/bot-curves-internal-scale.json`, verbatim thresholds (the D-13 gate).
  2. REPORT-ONLY: the same A21 cells against the Phase-199 sweep's fitted cells, as incremental-shift context. The confound is stated.
  3. PRE-REGISTERED FAIL/VOID BRANCH: run **A0 and A2** (not A2 alone). If A0 also fails against July-21, the failure is pre-existing drift, not the items. The item decision then uses the same three criteria with the A0 fit as the "old" side. This needs a small converter that fits A0's `*-cells.tsv` via the script's own `fit_new_cells` and writes `{"cells": [...]}` for `--old-json`. The script's `--old-json` is already a CLI arg; only the thresholds are frozen. [VERIFIED: calibration_parity_verdict.py:522-564, 306-327]
  4. D-14 applies to the outcome: no refit.

### C-7 (D-13 stop rule): the time ceiling is structurally non-binding; pre-register early-stop retention instead
- `stopRule` can only **shorten** a search: nodes-at-stop ≤ `maxNodes` = 50, the calibrated full budget. So "stays inside the think deadline" is bounded by full-budget cost. In the 2026-07-31 stop-rule TSV the slowest full-budget position was 8,366 ms harness wall. [VERIFIED: reports/data/engine-dispatch-stop-rule-round-2026-07-31T13-21-35-133Z.tsv]
- `computeThinkDeadlineMs(remainingMs, incrementMs) = max(0, min(clamp(remaining/30 + inc·0.7, 800, 15000), remaining − 300))` (chessClock.ts:223-228). Constants: `BOT_MOVES_TO_GO = 30`, `BOT_THINK_INCREMENT_SHARE = 0.7`, `BOT_THINK_DEADLINE_MIN_MS = 800`, `BOT_THINK_DEADLINE_MAX_MS = 15000`, `BOT_MOVE_OVERHEAD_MS = 300`. [VERIFIED: chessClock.ts:97-131,223-228]
- Full-clock deadlines by preset (`DEFAULT_TC_PRESET_LABEL = '10+0'`, botTimeControlPresets.ts): **10+0 → 15,000 ms** (default), **5+3 → 12,100 ms**, 3+2 → 7,400 ms, 3+0 → 6,000 ms, 15+10 and above → 15,000 ms. [VERIFIED: arithmetic on verified constants]
- 2026-07-31 A0-like distribution (N=16, round mode, maia-fifo): 9/16 early-stop at 8, 8, 9, 11, 12, 12, 15, 16, 24 nodes; 7/16 ran to 50 (budget); median 20. That TSV predates ORT 1.29 and 8XN, so A0 must be re-measured. [VERIFIED: TSV read]
- **Recommended pre-registered criteria** (Claude's discretion per CONTEXT.md; fix before data):
  - **S1 (hard ceiling, from the deadline):** A21 max harness `wall_ms` over the 16 positions ≤ **12,100 ms** (the 5+3 full-clock deadline, the tightest common-preset deadline that is not already binding at A0). Expected to pass. It is a sanity bound.
  - **S2 (the real risk, from D-01's own premise):** A21 early-stop count ≥ **50%** of A2's early-stop count. The guard must not effectively disable the clear-winner branch.
  - **Report-only:** median and p90 nodes-at-stop per arm; D-04 deadline exposure, defined as the count and fraction of post-`minNodes` snapshots where a non-settled in-window root child exists, per position. The exposure metric cannot see `isClosed` through `RankedLine`, so a terminal root child (value exactly 1/0/0.5 with `visits` 0) is a known false positive. The 16-position set has none.

## Standard Stack

No new packages. Everything is in-repo.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vitest | 5.0.0 | Unit tests for `mctsSearch` / `findability` / `selectBotMove` | Project test runner (observed in this session's run output) [VERIFIED: `npx vitest run` banner] |
| Node | v24.19.0 | Runs harnesses with native TS type-stripping plus `scripts/lib/frontend-alias-hook.mjs` | Existing harness mechanism [VERIFIED: `node --version`] |
| onnxruntime-web (via `frontend/node_modules`) | as pinned in frontend | Maia inference in the harnesses (`createMaiaSession({backend:'wasm'})` is the default) | App-faithful. The Phase 199 sweep used it. [VERIFIED: scripts/lib/node-engine-providers.mjs:74-96] |
| Stockfish 18 lite single (vendored `frontend/public/engine/*`, git-tracked) | 18 | Grading in the harnesses | Same binary as the browser [VERIFIED: `git ls-files frontend/public/engine`] |
| uv + Python 3.14 | — | `calibration_parity_verdict.py` (stdlib only) | Existing [VERIFIED: self-test ran] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| wasm Maia backend in the calibration arms | `backend: 'native'` (onnxruntime-node 1.21.1) | Avoids the OOB crash and is about 2x faster, **but** "NEVER mix backends within one study dataset". July-21 and 199 were wasm, so the arms must stay wasm. [VERIFIED: node-engine-providers.mjs:57-72] |
| New `rounds` instrumentation in `mctsSearch` | P/S event run-length from providers + `onSnapshot` | No production code needed; deterministic. [VERIFIED: probe this session] |

**Installation:** none. Each arm worktree needs `( cd frontend && npm ci )`. The Maia `.onnx` and Stockfish wasm are git-tracked. [VERIFIED: git ls-files]

## Package Legitimacy Audit

No external packages are installed by this phase. The audit is not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────── mctsSearch round loop ─────────────────┐
root FEN ─────► │ FILL: while slots < c                                   │
                │   selectPath(root) ──► zero selectable at NON-root?     │
                │        │                  └─► [ITEM 2] block node,      │
                │        │                      push to round list,       │
                │        │                      restart from root         │
                │        ├─ root has none ─► break (tree searched/pending)│
                │        ├─ dead end ─► bump visits, propagateClosure     │
                │        └─ leaf ─► mark isPending, add to round          │
                │ CLEAR block flags (end of fill / after Promise.all)     │
                │ DISPATCH: Promise.all(policy → [T reshape] → truncate   │
                │           → [root: merge/cap] → grade @ ladder depth)   │
                │ APPLY (canonical order): create children, recompute,    │
                │   backup to root (max) ─► stopRuleSatisfied?            │
                │       clear-winner ∧ [ITEM 1] all in-window root        │
                │       children settled (visits≥1 ∨ isClosed)            │
                │       ∨ flatness (unchanged) ─► early-stop              │
                │   onSnapshot(buildSnapshot)                             │
                └──────────────────────────┬──────────────────────────────┘
                                           ▼
                    buildRankedLines: sort by [ITEM 3] rankScore(P, pRef, V, Vfb)
                           │                                  │
             analysis page (arrow, lines, verdict)    bot: selectBotMove → argmaxLine /
             ORDER-DEPENDENT                          UCI-sorted softmax (ORDER-INDEPENDENT)
                                           ▲
       deadlineSearch (bot only, wall clock): aborts inner signal once nodes ≥ 8 (UNCHANGED, D-04)
```

### Recommended file touch list
```
frontend/src/lib/engine/
├── mctsSearch.ts            # items 1 + 2 (selectPath restart, block flags, guard in stopRuleSatisfied), header update
├── types.ts                 # BotStopRule gains required allowance field
├── botBudget.ts             # FLAWCHESS_BOT_STOP_RULE gains the D-02 value (+ method note)
├── findability.ts           # item 3 formula + header invariant rewrite
├── treeCommon.ts            # buildRankedLines computes V_fallback once
└── __tests__/
    ├── mctsSearch.test.ts         # rewrite clear-winner + findability tests; add guard tests
    ├── mctsSearch.roundFill.test.ts (new, or a describe block)  # D-08
    ├── findability.test.ts        # new signature, pinned Vfb, clamp case
    ├── fallbackExpectimax.test.ts # rewrite the "demotes" test
    └── selectBotMove.test.ts      # D-10d order-invariance
frontend/src/hooks/useFlawChessEngine.test.tsx   # allowance >= 0 assertion
scripts/engine-dispatch-stop-rule.mjs            # --no-stop-rule, --root-trace, --guard-window (tooling commit = A0)
scripts/engine-move-quality.mjs (new)            # maia-blindness runner (tooling commit = A0)
scripts/<converter> (only if the fail branch fires) # A0 cells -> {"cells":[...]} for --old-json
reports/engine-search-fixes-225/{d02-allowance.md, accept-rule.md, report.md}
docs/flawchess-engine-explained-2026-07-06.md    # D-05 + §6 findability paragraph (item 3)
CHANGELOG.md
```

### Pattern 1: Round-scoped block flag (item 2, D-06/D-07)
**What:** `EngineNode.isBlocked: boolean` plus a local `blocked: EngineNode[]` owned by the round. `selectPath(root, maxPlies, blocked)`: the candidate filter becomes `!child.isPending && !child.isClosed && !child.isBlocked`. On zero candidates at a **non-root** node: `node.isBlocked = true; blocked.push(node); path = [root]; node = root; continue;`. At the root, return null. Clear with `for (const n of blocked) n.isBlocked = false; blocked.length = 0;`.
**Termination:** a blocked node is filtered at its parent, so it can never be reached again in the round and never re-blocked. The root is never blocked. Each restart blocks one distinct node, so restarts are bounded by tree size. Mirror the `propagateClosure` / WR-01 "each node flips at most once" argument in the fill-loop comment at 545-548.
**Clear point:** flags are read only by `selectPath`, which is called only from the fill loop. Clearing right after the fill loop (before `Promise.all`) is behaviorally identical to D-06's "after Promise.all" and keeps the invariant local. If Promise.all rejects, the search throws either way. Planner's call.
**Why zero-candidates can only mean pending or blocked:** any node whose children are all closed is closed itself by `propagateClosure`, and every closure path calls it (dead-end branch 571, `applyExpansion` 352/388). At round start there are no pending or blocked nodes, so `toExpand.length === 0` still means "fully searched". [VERIFIED: mctsSearch.ts:270-276, 342-405, 558-592]
**Nesting:** `function → for(;;) → if (candidates.length === 0) → if (node.isRoot)` is depth 3, which satisfies eslint `max-depth` 4.

### Pattern 2: Guard inside the existing single pass (item 1)
Extend `rootChildValueExtremes`'s `entries` to carry `settled: child.visits >= 1 || child.isClosed`. After `topValue` is known, compute `hasUnsettledInWindow = entries.some(e => !e.settled && topValue - e.value <= window)`, where `window = rule.marginThreshold + rule.<allowance>`. The clear-winner disjunct becomes `margin >= threshold && !hasUnsettledInWindow`. Leave the stability-state update unconditional (lines 253-254) so the stability semantics do not change.

### Pattern 3: Allowance as a required `BotStopRule` field
Put it on the rule object, not as a free constant imported into `mctsSearch.ts`. `FLAWCHESS_BOT_STOP_RULE` is the single definition imported by both `useBotGame` and `calibration-harness.mjs` (botBudget.ts header). A required field makes any literal that omits it a `tsc -b` error, the same "structurally impossible desync" argument the header makes. Update the three test literals and the `useFlawChessEngine.test.tsx` bound assertion.

### Pattern 4: Tooling commit = A0 base; arms as detached worktrees
```bash
# after tooling lands on gsd/phase-225 (A0), item 2 (A2), item 1 (A21):
git worktree add ../flawchess-225-a0  <A0_SHA>
git worktree add ../flawchess-225-a2  <A2_SHA>
git worktree add ../flawchess-225-a21 <A21_SHA>
( cd ../flawchess-225-a0/frontend && npm ci )   # repeat per worktree
```
The harness alias hook resolves `@/` relative to its own location, and `node-engine-providers.mjs` resolves `REPO_ROOT` from `import.meta.url`, so each worktree measures its own engine. `bin/preset-supervisor.sh` does `cd "$(dirname "$0")/.."`, so it runs in the worktree too. Output lands in **the worktree's** `reports/data/...`; copy it into the main checkout before committing. [VERIFIED: frontend-alias-hook.mjs header, node-engine-providers.mjs:35-39, preset-supervisor.sh:37]
Worktrees avoid the shared-checkout HEAD race (memory note). Do not switch branches in the main checkout during runs.

### Anti-Patterns to Avoid
- **Overloading `isPending` as the block flag.** `applyExpansion` resets `isPending` (lines 350, 381). A blocked interior node was never dispatched, so its flag would never clear. D-07 is right.
- **Non-erasable TypeScript in engine files** (`enum`, `namespace`, parameter properties). The Node harnesses load `.ts` through native type-stripping, and a non-erasable construct breaks every gate run. [CITED: frontend-alias-hook.mjs header "A future non-erasable edit ... would break type-stripping"]
- **Running wall-clock-sensitive harnesses concurrently** (throughput, stop-rule wall) with each other or with a calibration sweep. CPU contention corrupts the numbers.
- **Launching calibration cells without `PRESET_SUPERVISOR_ANCHORS`**, or with the bare harness. The runbook §6 forbids both.
- **Measuring the move-quality gate via `rankedLines[0]`** for bot arms (C-5).
- **Loosening an existing test to make it pass.** The clear-winner and "demotes" test rewrites are intended behavior changes. Say so in the test comment and the plan.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Prior-weighted mean for V_fallback | a new loop with different normalization | `backupExpectation` math (backup.ts:43-47) with a zero-total → 0 wrapper | Root priors don't sum to 1 (cap, injection) |
| Maia-blindness runner | a from-scratch script | adapt `b1764a83^:scripts/engine-wdl-leaf-quality.mjs` (fixture loader, §4a integrity, `gradeChosenMoves`, `REGRESSION_MARGIN`) + `scripts/lib/stockfish-pool.mjs` | Keeps the 2026-07-31 procedure's grading semantics identical |
| Engine bring-up in harnesses | new spawn / session code | `createMaiaSession`, `createStockfishPool`, `makeNodeProviders`, `resetMaiaRunMemo` | Shared pool heals dead engines (SEED-145 bug) |
| Round counting in D-08 | instrumentation inside `mctsSearch` | P/S run lengths from the fake `policy()` + `onSnapshot` | Deterministic; zero production change |
| Crash resume for blend>0 cells | a new supervisor | `bin/preset-supervisor.sh` (fast-crash guard, `--resume`) | Existing and proven in Phase 199 (4.5 h, no crash) |
| Parity arithmetic | re-deriving thresholds | `scripts/calibration_parity_verdict.py` constants (85.0 / 50.0 / 165.0 / 149.0) | Frozen twin of the 199 accept rule |
| Bot move pick in the move-quality runner | re-implementing argmax | import `argmaxLine` from `@/lib/engine/botSampling` | Single definition of the bot's blend=1 pick |

## Runtime State Inventory

Not a rename or migration phase. The one runtime concern: **Cloudflare edge cache of `/engine/*` and `/maia/*`** (memory note) is irrelevant because no vendored runtime asset changes. Engine TS ships in the hashed Vite bundle. Nothing to migrate. [VERIFIED: file touch list contains no `frontend/public/*`]

## Common Pitfalls

### Pitfall 1: The guard's "settled" test uses `isTerminal`
**What goes wrong:** a mate-in-1 root child (value 1, top) is never visited, so the clear-winner stop never fires in a trivially won position.
**How to avoid:** `settled = visits >= 1 || isClosed`. Unit test: `MATE_IN_1_FEN` with a stop rule (minNodes 1, stability 1) must still early-stop at node 1. Mutation: drop the `isClosed` clause and confirm the test fails.

### Pitfall 2: The existing stop-rule test silently "fixed" by loosening
**What goes wrong:** `nodesEvaluated toBe(1)` is changed to `toBeLessThan(maxNodes)` with no guard semantics asserted.
**How to avoid:** assert the exact first node count where every in-window child is settled, and add a separate test where an **out-of-window** unvisited child does **not** block the stop.

### Pitfall 3: Arms that differ in tooling as well as engine
**What goes wrong:** harness flags are added after the A0 SHA, so A0 cannot run the same command.
**How to avoid:** commit tooling first; A0 := the tooling SHA (engine byte-identical to `main`). Record all three SHAs in the accept rule (A2/A21 as "the commits that land item 2 / item 1", filled into the report).

### Pitfall 4: Long runs dying inside an executor subagent
**What goes wrong:** Phase 197 wave 2 lost a measurement when the backgrounded child died with the agent.
**How to avoid:** measurement tasks are orchestrator-inline (`setsid nohup ... &` + Monitor; SIGTERM the node PID to stop). Commit before starting. Bash caps at 10 min. [CITED: MEMORY.md project_executor_backgrounded_runs_die, project_orchestrator_long_operator_runs]

### Pitfall 5: D-10c fixture V_fallback chosen after seeing the result
**What goes wrong:** the @1000 case passes or fails depending on an unstated Vfb.
**How to avoid:** pin a rule (e.g. unlisted mass at 0.5) in the plan before running, and escalate a failure (C-3) instead of tuning.

### Pitfall 6: Calibration verdict read without the baseline context
**What goes wrong:** A21 fails vs July-21 because of pre-existing drift (Maia pooled already −57.7 in Phase 199, plus ORT 1.29 since), and item 1 gets blamed.
**How to avoid:** C-6's pre-registered fail branch (run A0 + A2). The null control catches ORT-level drift in Maia-only play.

### Pitfall 7: Harness output lands in the worktree and is lost
**How to avoid:** a final task copies `reports/data/engine-search-fixes-225/**` and `sweep-225-*` from each worktree into the main checkout before `git worktree remove`.

### Pitfall 8: Maia-blindness near-boundary flips from warm-hash noise
The harness self-reproducibility is 0.013984 in es (D-07 of Phase 195). The 0.05 margin is 3.6x that. The 2026-07-31 re-runs reproduced exactly, but pre-register anyway: a position that flips pass→fail gets exactly one fresh-process re-run and counts only if it reproduces. [CITED: override-2026-07-31.md]

## Code Examples

### D-08 permanent round-fill test (verified shape; the probe ran this session)
```ts
// Source: scratch probe run 2026-09-27 via node --import ./scripts/lib/frontend-alias-hook.mjs
// Round size = run length of consecutive policy() calls between onSnapshot events.
const events: ('P' | 'S')[] = [];
const policy: EngineProviders['policy'] = async (fen) => {
  events.push('P');
  const ucis = legalUcisSorted(fen);                // chess.js, never hand-enumerated
  if (fen === ROOT_FEN) return uniform(ucis);       // flat root
  return peaked(ucis, [0.92]);                      // or [0.55, 0.37]; truncation keeps 1 (or 2)
};
const snap = await mctsSearch(ROOT_FEN,
  { maxNodes: 50, maxPlies: 8, concurrency: 4, elo: { w: 1500, b: 1500 } },
  { policy, grade: makeVariedGrade() }, () => events.push('S'), freshSignal());
const rounds = runLengthsOfP(events);               // e.g. [1, 4, 4, ..., 4, 1]
expect(rounds.slice(1, -1).every((n) => n === 4)).toBe(true);
expect(rounds.reduce((a, b) => a + b, 0)).toBe(snap.nodesEvaluated);
```
Observed on current code (italian FEN, `r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4`): flat `14 rounds 1,4×12,1`; two-candidate `20 rounds 1,4,2,2,2,4,2,4,...`; one-candidate `37 rounds 1,4,1,1,1,1,4,1,2,3,...`. With the one-candidate shape at 400 nodes the tree exhausts at 106 nodes (15 root chains × 7 + root), so keep D-08 at 50 nodes. [VERIFIED: probe output this session]
Mutation check: restore `if (candidates.length === 0) return null;` and confirm the test fails.

### Item 3 formula
```ts
// findability.ts: D-10a
export function rankScore(pYou: number, pRef: number, value: number, fallbackValue: number): number {
  if (pRef <= 0) return value;
  const f = Math.min(1, pYou / pRef);
  return f * value + (1 - f) * Math.min(value, fallbackValue);
}
```
Note: `rankScore` is not imported anywhere outside the engine (`botSampling.ts` and `policyTemperature.ts` only mention it in comments). A signature change touches only `treeCommon.ts` and the tests. [VERIFIED: grep]

### Stop-rule harness onSnapshot tracer (D-02 + D-04)
```js
// engine-dispatch-stop-rule.mjs, replacing () => {} when --root-trace is set
let prev = new Map(); // uci -> { visits, value }
const onSnapshot = (s) => {
  for (const line of s.rankedLines) {
    const p = prev.get(line.rootMove);
    if (p && p.visits === 0 && line.visits >= 1) {
      firstExpansionDeltas.push({ position, elo, uci: line.rootMove, pre: p.value, post: line.practicalScore });
    }
  }
  prev = new Map(s.rankedLines.map((l) => [l.rootMove, { visits: l.visits, value: l.practicalScore }]));
  // D-04 exposure (report-only): s.nodesEvaluated >= minNodes && some unvisited line within window of the top
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stop-rule A0 distribution from 2026-07-31 | Must re-measure | ORT 1.29 (`463b93de7`), 8XN fixes (2026-09-27) | Do not reuse the 07-31 TSV as A0 |
| Maia-blindness runner `engine-wdl-leaf-quality.mjs` | Deleted in `b1764a83`; the 07-31 run was an uncommitted adaptation | 2026-07-31 | A committed runner is a phase deliverable |
| `rankScore = min(1,P/Pref)·V` | `f·V + (1−f)·min(V, Vfb)` | this phase | Reverses the Phase 159 showcase fixture (C-3) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | In-window low-prior root children are first visited around N≈20-25 (PUCT derivation) | C-1 | Guard could delay stops more or less than expected. The S2 early-stop-retention criterion measures it directly. |
| A2 | Allowance = pooled p90 of first-expansion deltas across ELOs 1300/1500/1900/2300 | C-2 | A too-small window leaks; too large delays stops. Both are visible in the stop-rule arm. |
| A3 | Pinning unlisted fixture prior mass at V=0.5 for the findability tests is the fair rule | C-3 | Changes whether @600/@1000 pass; must be user-visible |
| A4 | S1 = 12,100 ms and S2 = 50% early-stop retention are the right pre-registered stop-rule numbers | C-7 | Wrong bar, but it is fixed before data, and overrides go in separate docs |
| A5 | Throughput runtime: ~5.5 min (bot 50) + ~34 min (analysis 400) per arm, from the 2026-07-31 TSV sums; current code is similar | Environment | Schedule only |
| A6 | Calibration A21 run ≈ 4.5 h wall with five concurrent cells on this 16-core box (Phase 199: 21:58→02:25, no crash) | Environment | Schedule only; crash resume is automatic |
| A7 | The user wants item 3's semantics despite reversing Phase 159's fixture | C-3 | Shipping a UX change the user did not intend. **Needs confirmation.** |

## Open Questions (RESOLVED)

1. **Does the user accept item 3's reversal of Phase 159's findability behavior?** (C-3) **RESOLVED** by D-10e (user accepted; tests rewritten in Plan 225-06).
   - Known: D-10a makes e2e4 (+7, 6.6% prior) outrank e2e3 (+1, 93% prior) at 600, and flips the @1000 D-03 case at any near-equal V_fallback.
   - Unclear: whether "hard-to-find winning move now ranks first at 600" is desired.
   - Recommendation: a checkpoint (`checkpoint:decision`) before the item 3 implementation task, with options (a) accept and rewrite the tests, (b) anchor re-derivation, (c) hold item 3. Item 3 is independent of the bot gates, so the other items proceed either way.
2. **Calibration primary baseline: July-21 (label question) or A0 (attribution question)?** (C-6) **RESOLVED** by D-13 (amended): July-21 primary + pre-registered A0+A2 fail branch.
   - Recommendation: July-21 primary per D-13, plus the pre-registered A0+A2 fail branch.
3. **Move-quality judged selector** (C-5) **RESOLVED** by D-13 (amended): `argmaxLine` judged, `rankedLines[0]` report-only. (Original: recommend `argmaxLine` for the bot arms, with `rankedLines[0]` report-only.)
4. **Allowance value:** **RESOLVED procedurally** by Plan 225-03's D-02 measurement (fallback 0.10). Originally: unknown until the D-02 run. Fallback 0.10 per D-02 if the tracer fails.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | all harnesses | ✓ | v24.19.0 | — |
| frontend/node_modules | harnesses + vitest | ✓ (main checkout; `npm ci` per worktree) | vitest 5.0.0 | — |
| Maia ONNX / Stockfish wasm | harnesses | ✓ git-tracked | Stockfish 18 lite | — |
| uv / Python | parity verdict | ✓ | self-test OK | — |
| CPU cores | 5 concurrent calibration cells | ✓ | nproc = 16 | Two groups (runbook §2) |
| git worktree | arms | ✓ (one unrelated worktree already exists: `flawchess-260927-ajg`) | — | — |

**Runtime budget (sequential unless noted):** D-02 ≈ 10 min · throughput A0+A2 ≈ 80 min (never concurrent with other runs) · stop-rule A0/A2/A21 ≈ 3 × 2 min (+ exposure trace) · move-quality A0/A2/A21 × {stop on, off} ≈ 6 × 3 min · calibration A21 ≈ 4.5 h (five cells in parallel) · conditional A0 + A2 ≈ 4.5 h more (can run together, ~10 single-core processes). Everything over 10 min goes through `setsid nohup` + Monitor from the orchestrator. [VERIFIED: 2026-07-31 TSV wall sums; 199 run.log timestamps]

**Exact commands (to pin in the accept rule, run from each arm worktree root):**
```bash
# Throughput (judge depth=ladder rows only; flat d14 rows are informational)
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 50  --depths 14 --ladder --procs 4 --plies 8 --elo 1500 --openings 12 --maia-fifo --out-dir reports/data/engine-search-fixes-225/<arm>
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-grading-depth-ab.mjs \
  --nodes 400 --depths 14 --ladder --procs 4 --plies 8 --elo 1500 --openings 12 --maia-fifo --out-dir reports/data/engine-search-fixes-225/<arm>
# Stop rule (--dispatch-mode is a required LABEL only; always "round" here)
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs \
  --dispatch-mode round --openings 12 --maia-fifo --out-dir reports/data/engine-search-fixes-225/<arm>
# Calibration (per runbook §1, five blocks, with a 225-specific PRESET_SUPERVISOR_DIR, e.g. reports/data/sweep-225-a21-light1300)
# Verdict (from the main checkout)
uv run python scripts/calibration_parity_verdict.py --old-json reports/data/bot-curves-internal-scale.json \
  --new-cells-tsv <each of 5 -cells.tsv> --out-json reports/data/engine-search-fixes-225-verdict-a21.json
```
[VERIFIED: flags read from engine-grading-depth-ab.mjs:1-90, engine-dispatch-stop-rule.mjs:47-62, runbook.md §1, calibration_parity_verdict.py:522-545]
Throughput note: `engine-grading-depth-ab.mjs` sets no `stopRule` (it runs the full budget), which correctly isolates item 2. Its `top_move` column is `rankedLines[0]` (item-3-sensitive, informational). [VERIFIED: engine-grading-depth-ab.mjs:603-617]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 5.0.0 (frontend); Node self-test harness checks; Python stdlib self-test |
| Config file | `frontend/vite.config.ts` `test` block (project-wide `testTimeout`/`hookTimeout`; no per-file timeouts) |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/findability.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts src/lib/engine/__tests__/selectBotMove.test.ts` (baseline 61 tests in 0.8 s for the first three) |
| Full suite command | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` (+ the backend pre-merge gate before the squash-merge) |

### Phase Requirements → Test Map
| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| D-06/D-08 | Every non-tail round dispatches `c` expansions under one- and two-candidate peaked policies | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` | ❌ Wave 0 |
| D-06 mutation | Reverting the restart makes D-08 fail | mutation (manual revert + rerun) | same command, with the fix reverted | — |
| D-06 determinism | Peaked fixture at c=2 bit-identical under two jitters | unit | same file | ❌ Wave 0 |
| D-06 regression | Existing ENGINE-07 determinism tests unchanged and green | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "ENGINE-07"` | ✅ |
| D-01 | Unsettled in-window child blocks the clear-winner stop; settles, then stops | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "stop rule"` | ✅ (rewrite + additions) |
| D-01 | Unvisited out-of-window child does not block | unit | same | ❌ Wave 0 |
| D-01 | Terminal (closed) top child counts as settled (`MATE_IN_1_FEN` stops at node 1) | unit + mutation | same | ❌ Wave 0 |
| D-03 | Flatness branch unchanged (existing test green) | unit | same | ✅ |
| D-02 | Allowance ≥ 0 and present on `FLAWCHESS_BOT_STOP_RULE` | unit | `npx vitest run src/hooks/useFlawChessEngine.test.tsx` | ✅ (extend) |
| D-10a | rankScore bounds: `min(V,Vfb) ≤ rs ≤ V`; f=1 gives exactly V; pRef ≤ 0 gives V | unit | `npx vitest run src/lib/engine/__tests__/findability.test.ts` | ✅ (extend) |
| D-10b | Vfb normalized by total prior; zero total gives 0 (no NaN) | unit | same (or treeCommon.test.ts) | ❌ Wave 0 |
| D-10c | Clamp case + D-03 cases with pinned Vfb | unit | same | ✅ (rewrite) |
| D-10d | `selectBotMove` identical pick for any permutation of `rankedLines` (blend 1, blend 0.5 with fixed rng, with/without style) | unit | `npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts` | ❌ Wave 0 |
| item 3 runners | Both runners emit identical order (existing) | unit | `npx vitest run src/lib/engine/__tests__/fallbackExpectimax.test.ts` | ✅ |
| tooling | Stop-rule harness parseArgs incl. new flags | self-test | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs --self-test` | ✅ (extend) |
| tooling | Move-quality runner parseArgs + fixture integrity (corrupt-row proof) | self-test | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test` | ❌ Wave 0 |
| arm preflight | Harness still type-strips the modified engine | check | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-parity.check.mjs` and `.../calibration-ledger-schema.check.mjs` in each worktree | ✅ |
| verdict | Parity arithmetic | self-test | `uv run python scripts/calibration_parity_verdict.py --self-test` | ✅ |
| gates | Throughput / stop-rule / move-quality / calibration | measurement (orchestrator-inline) | commands in Environment Availability | — |

### Sampling Rate
- **Per task commit:** the quick run command (under 5 s).
- **Per wave merge:** `cd frontend && npm test -- --run && npm run lint && npm run build`.
- **Phase gate:** the full CLAUDE.md pre-merge gate green, and the accept-rule verdicts rendered, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts`: D-08 (written RED against current code first, which reproduces the probe's 37-round result)
- [ ] Guard tests (out-of-window, closed-top) in `mctsSearch.test.ts`
- [ ] D-10d permutation test in `selectBotMove.test.ts`
- [ ] `scripts/engine-move-quality.mjs` + `--self-test`
- [ ] Stop-rule harness `--no-stop-rule`, `--root-trace`, `--guard-window` flags + self-test cases

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so it is enabled. The surface is minimal: a client-side search algorithm with no auth, network, or persistence changes.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | marginal | Provider UCIs already contained (WR-07 deterministic drop). New numeric paths guard NaN (the zero-total prior guard). |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Non-terminating selection loop (restart never ends) freezes the analysis tab or bot | Denial of Service | Structural termination: each restart blocks a distinct node that can never be re-reached in the round; root never blocked. Cover with the D-08 test at a fully-blocked round. |
| NaN/Infinity in `rankScore` corrupting the sort | Tampering (integrity) | Zero-total-prior guard gives Vfb = 0; `pRef ≤ 0` guard kept. |

## Sources

### Primary (HIGH confidence, read this session)
- `frontend/src/lib/engine/{mctsSearch,select,botBudget,types,findability,treeCommon,deadlineSearch,botSampling,selectBotMove,botStyle,backup,policyTemperature}.ts`
- `frontend/src/lib/chessClock.ts:97-228`, `frontend/src/lib/botTimeControlPresets.ts`
- `frontend/src/lib/engine/__tests__/{mctsSearch,findability,fallbackExpectimax}.test.ts`
- `scripts/engine-dispatch-stop-rule.mjs`, `scripts/engine-grading-depth-ab.mjs`, `scripts/calibration_parity_verdict.py`, `scripts/lib/node-engine-providers.mjs`, `bin/preset-supervisor.sh`, `git show b1764a83^:scripts/engine-wdl-leaf-quality.mjs`
- `reports/bot-parity-199/{accept-rule,runbook,report}.md`, `reports/grading-ladder/override-2026-07-31.md`, `reports/continuous-dispatch/{accept-rule,apply-order-design}.md`
- `reports/data/engine-dispatch-stop-rule-round-2026-07-31T13-21-35-133Z.tsv`, `reports/data/engine-grading-depth-ab-2026-07-31T13-46-35-696Z.tsv`, `...T14-22-08-625Z.tsv`, `reports/data/sweep-199-*/run.log`
- Probes run this session: underfill P/S run-length probe (scratchpad), findability formula computations (scratchpad), vitest baseline, both self-tests.

### Secondary / Tertiary
- None. No external library documentation was needed; the phase is entirely in-repo.

## Metadata

**Confidence breakdown:**
- Change sites / signatures: HIGH (read with line numbers)
- Item 2 mechanism + test observable: HIGH (reproduced)
- Item 3 test impact: HIGH (computed from fixtures)
- D-01 visit timing: MEDIUM (derivation)
- Gate design recommendations: MEDIUM (judgement; the numbers are pre-registration proposals)

**Research date:** 2026-09-27
**Valid until:** 2026-10-27, or until any engine commit lands on `main`
