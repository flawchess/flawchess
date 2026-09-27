# Phase 225: Engine Search Fixes — Root Comparability, Round Underfill & Findability Fallback - Context

**Gathered:** 2026-09-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three search-behavior defects in `frontend/src/lib/engine` (SEED-170), each changing what the
search returns, behind a pre-committed measurement gate:

1. Root comparability before the early stop (bot play only: `stopRule` is set only in
   `hooks/useBotGame.ts`, the analysis budget has none).
2. Round underfill in `selectPath` (perf bug, affects both bot 50/c4 and analysis 400/c4).
3. Findability fallback term in `rankScore` (analysis UI ordering only; bot sampling is
   order-independent: `botSampling.ts` UCI-sorts before the weighted pick and reads
   `practicalScore`, `argmaxLine` scans every line).

Optional item 4 (non-root candidate cap) is **deferred out of this phase** (D-15).

The user delegated every gray area to Claude ("You decide"). The decisions below are Claude's,
with the reasoning recorded so the planner can challenge them with evidence.

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-170-engine-root-comparability-and-round-underfill.md`: mechanisms, harness evidence table, proposed fixes, out-of-scope list
- `.planning/ROADMAP.md` § Phase 225: goal, gate, out-of-scope

### Engine code (the change sites)
- `frontend/src/lib/engine/mctsSearch.ts`: `rootChildValueExtremes`, `stopRuleSatisfied` (~245), `selectPath` (~300), fill loop in `mctsSearch` (~545)
- `frontend/src/lib/engine/deadlineSearch.ts`: D-18 node floor; stays unguarded (D-04)
- `frontend/src/lib/engine/botBudget.ts`: `FLAWCHESS_BOT_STOP_RULE` (margin 0.05, epsilon 0.02, stability 3, minNodes 8), concurrency pin
- `frontend/src/lib/engine/select.ts`: `selectChild` root PUCT, `rootExplorationPriors`, `ROOT_PRIOR_FLOOR`, `C_PUCT`
- `frontend/src/lib/engine/findability.ts` + `__tests__/findability.test.ts`: `rankScore`, `P_REF_ANCHORS`, D-03 regression cases
- `frontend/src/lib/engine/treeCommon.ts`: `buildRankedLines` (~416), `recomputeValue` / `backupRootMax`, `ROOT_CANDIDATE_HARD_CAP` use
- `frontend/src/lib/engine/botSampling.ts`, `selectBotMove.ts`: proof that bot play is rankedLines-order-independent (D-10d)
- `frontend/src/hooks/useBotGame.ts:127`: the only `stopRule` consumer

### Measurement procedure and precedents
- `reports/bot-parity-199/accept-rule.md`, `reports/bot-parity-199/runbook.md`: the five-cell parity check reused verbatim (D-13)
- `reports/grading-ladder/override-2026-07-31.md`: maia-blindness move-quality procedure
- `reports/continuous-dispatch/accept-rule.md`, `reports/continuous-dispatch/apply-order-design.md` §5: accept-rule precedent; the misread "saturated tree" claim (D-09)
- `.planning/milestones/v2.10-phases/198-mctssearch-continuous-dispatch/198-CONTEXT.md`, `.planning/milestones/v2.10-phases/199-bot-re-calibration-sweep-strength-curve-refit/199-CONTEXT.md`: prior decisions on dispatch and calibration
- `scripts/engine-grading-depth-ab.mjs`, `scripts/engine-dispatch-stop-rule.mjs`, `fixtures/engine/maia-blindness.tsv`, `bin/run_persona_calibration_sweep.sh`, `scripts/calibration_parity_verdict.py`

### Documentation to update
- `docs/flawchess-engine-explained-2026-07-06.md`: parity effect + guard scope (D-05)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rootChildValueExtremes` already walks root children once: extend it (or a sibling) to report whether any in-window child is unvisited, rather than a second pass with different semantics.
- `propagateClosure` / `isClosed` (WR-01) is the model for structural, termination-proof flags; the D-07 block flag should follow the same "each node flips at most once per round" argument.
- `scripts/calibration_parity_verdict.py` carries the Phase 199 thresholds as constants, so the calibration verdict is reproducible without re-deriving numbers.

### Established Patterns
- Accept rule before data, never edited, overrides as separate docs (Phases 195/197/198/199).
- Determinism is per concurrency level over the canonical apply order; no wall-clock signal inside `mctsSearch` (the stop rule is node-deterministic by design).
- Engine budget is a node cap, not a time cap. The deadline cut is the only wall-clock path.
- Tests that prove a gap fix must be mutation-checked by reverting the fix.

### Integration Points
- Item 1 is reached only via `useBotGame` (bot budget). Item 2 affects every `mctsSearch` caller (bot + analysis board). Item 3 affects only `buildRankedLines` sort order (analysis board suggestions list).

</code_context>

<specifics>
## Specific Ideas

- Long gate runs (calibration sweep, multi-hour) run inline from the orchestrator (setsid nohup + Monitor), not inside a backgrounded executor subagent. Past runs died that way (Phase 197).
- blend>0 calibration presets have a known wasm "memory access out of bounds" crash about 5-6h in. Wrap the sweep in a resume-on-crash supervisor.
- Browser grade nondeterminism (SEED-130) means harness numbers are the gate basis, not live browser timings.
- CHANGELOG `[Unreleased]` bullets: faster bot/analysis search on narrow positions (item 2), better analysis suggestion ordering in winning positions (item 3), bot early-stop fairness (item 1, only if it ships).

</specifics>

<deferred>
## Deferred Ideas

- **Non-root candidate cap (~6-8) in `truncateAndRenormalize`** (SEED-170 item 4): deferred per D-15. Revisit with its own throughput + calibration arm if deep-node MultiPV cost shows up as a bottleneck after item 2 ships. Record it in SEED-170 (or a new seed) at phase close.
- **Guarding the flatness branch and the deadline cut** (D-03/D-04): revisit only if the deadline-exposure count from the stop-rule measurement is high.
- Still out of scope per roadmap: repetition/game-history awareness, continuous dispatch (SEED-130), cross-FEN Maia batching, grade-cache set-mixing redesign.

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`, `2026-08-29-variation-tree-nested-button.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `172-deferred-review-findings.md`: keyword-match noise, unrelated to engine search.

</deferred>

---

*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Context gathered: 2026-09-27*
