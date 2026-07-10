# Phase 153: Pure Search Core (Guardrail + Backup + MCTS + Fallback) - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A worker-free, fully deterministic TypeScript search core in `frontend/src/lib/engine/` behind a stable `position + budget → ranked root lines` interface (`SearchRunner`), unit-tested exclusively against fabricated `EngineProviders` — no WASM, no ONNX, no Web Workers, no React anywhere in this phase. The two highest-risk pieces of the design (the Maia-prior-weighted expectimax backup and the asymmetric side-to-move-keyed ELO routing) are proven correct with hand-computed fixtures before any real provider exists. `fallbackExpectimax.ts` ships alongside behind the identical interface.

Requirements: ENGINE-01..07. UI, real workers, and hooks are Phases 154–157.

</domain>

<decisions>
## Implementation Decisions

### Selection policy (select.ts)
- **D-01 Deterministic PUCT, chance-node-aware:** The tree has exactly one max node: the root. Selection at the ROOT uses Q-based UCB: `argmax Q(c) + c_puct · P_root(c) · √N(root)/(1+n(c))`. At ALL non-root nodes (all expectation/chance nodes under the locked backup rule) the Q term is dropped: `argmax P̂(c) · √N(node)/(1+n(c))` — refine what dominates the expectation. Ties broken by canonical UCI-string order. `c_puct` is a named tunable constant. No Dirichlet noise anywhere.
- **D-02 Backup expectation ranges over the FULL truncated top-k set:** with best-estimate child values: a child with its own subtree contributes its backed-up expectation; a subtree-less child contributes `sigmoid(shallowEval)` from the batched grade() done at its parent's expansion. No probability mass is ever dropped. **This clarifies ROADMAP.md Phase 153 SC2's "expectation over expanded children" wording — do not implement a renormalized expanded-subtrees-only expectation.** The hand-computed SC2 fixture must mix expanded and unexpanded children in one case.
- **D-03 Parallel-ready core loop now:** The orchestrator issues up to `budget.concurrency` expansions concurrently; selection marks in-flight nodes (pending/virtual-visit state) so it never re-picks them. The ENGINE-07 bit-identical determinism suite runs at `concurrency=1`; add one `concurrency=2` fake-provider test proving the ranking is still deterministic with ordered providers. Rationale: Phase 154's 2–4-worker pool needs multiple grade() calls in flight; restructuring the loop mid-154 would violate the spirit of ENGINE-06.

### Root candidate union (SearchRunner interface)
- **D-04 `extraRootMoves?: string[]` parameter on the SearchRunner signature.** Root children = Maia top-k ∪ extraRootMoves, all graded in the same batched grade() call; deeper nodes remain Maia-top-k-only. `EngineProviders` stays exactly `{policy, grade}`. Phase 155's hook will feed the already-running `useStockfishEngine` MultiPV `pv[0]` moves; Phase 153 tests pass literal arrays. The interface is final from day one (ENGINE-06).
- **D-05 Floor-boosted root exploration prior:** `P_root(c) = max(P_maia(c), ROOT_PRIOR_FLOOR)` renormalized over the root candidate set (floor a named constant, ~0.10), used ONLY in the root PUCT exploration term — otherwise an SF-injected candidate with ~0 Maia probability would never receive subtree visits and its practical score would stay a single shallow eval. backup.ts expectations use true renormalized Maia priors everywhere (the floor never touches values), and ranking is by V (root = max), so scores are never distorted — only visit allocation.

### Score semantics + interface shape (types.ts)
- **D-06 `practicalScore` is expected score 0–1** from the root side-to-move's perspective — the native space of `evalToExpectedScore` and of all backup math; SEED-082's stated unit ("expected points, comparable to WDL"). The core never converts to pawn units. How Phase 155 renders "objectively +3.0, practically +0.9 for you" (percentage, pawn-equivalent via inverse sigmoid, delta) is a free presentation decision over the raw `{practicalScore, objectiveEvalCp}` pair.
- **D-07 Color-keyed ELOs:** `budget.elo = { w: number, b: number }`. The core selects the ELO for every policy() call purely from the node's side-to-move color — the ENGINE-04 keying rule becomes structural, leaving no place for the depth-parity inversion pitfall. The yourElo/opponentElo → color mapping is resolved once, in the Phase 155 hook, where `user_color` is known. The ENGINE-04 oracle test asserts per-call `(fen side-to-move → elo)` pairs for both root colors.
- **D-08 UCI notation throughout the core:** `policy()` returns UCI-keyed probabilities (what `maskAndSoftmax` already emits), `grade()` takes/returns UCI moves (what the pv[0]-keyed worker protocol already speaks), `RankedLine.rootMove`/`modalPath` carry UCI. Canonical tie-break key = UCI string. SAN conversion happens only at display time (Phase 155), same as `EngineLines` today. (Supersedes the SAN field names sketched in `.planning/research/ARCHITECTURE.md`'s example interfaces.)

### Budget + snapshot contract
- **D-09 One "node" = one expansion event:** one policy() call plus one batched grade() call over that node's truncated top-k. `nodesEvaluated += 1` per expansion; `budgetExhausted` at `nodesEvaluated ≥ maxNodes`. Keeps SEED-082's "few hundred node evaluations" arithmetic meaningful and maps 1:1 to wall-clock cost drivers.
- **D-10 Core emits `onSnapshot` after EVERY completed backup; throttling is the caller's job:** No wall-clock (`Date.now()`) anywhere in `lib/engine/`. The Phase 155 hook applies the ~10Hz/`RAPID_STEP_DEBOUNCE_MS`-style batching. The ENGINE-07 test can therefore assert the FULL snapshot emission sequence is bit-identical across runs, not just the final output.
- **D-11 Separate engine mass-truncation constant:** a new named constant in `lib/engine` (e.g. `POLICY_MASS_THRESHOLD = 0.90`, per ENGINE-02's ~90%), independent of `moveQuality.ts`'s `CUMULATIVE_MASS_THRESHOLD = 0.95`. Search branching factor and chart display set are different concerns and must tune independently.

### Claude's Discretion
- `c_puct`, `ROOT_PRIOR_FLOOR`, `POLICY_MASS_THRESHOLD`, and the `maxPlies` default (within the locked 6–10 band) — exact values as named tunable constants, revisited post-UAT.
- Virtual-visit/pending-marker mechanics, tree data structures, and how the async completion loop is structured.
- Terminal-position handling (mate/stalemate before the depth cutoff), mate-score representation in `MoveGrade`, and fixture design details — flagged by the research as Phase 153 researcher territory.
- `fallbackExpectimax.ts` internals, as long as it reuses `backup.ts` and implements the identical `SearchRunner` (locked by ENGINE-06/SC5).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked design (algorithm + scope)
- `.planning/seeds/SEED-082-human-playable-line-engine.md` — the locked algorithm (expectimax-inside-MCTS, custom backup, asymmetric ELO), prior-art verdict, and the confirmed "never feed search results back into the Maia prior" pitfall
- `.planning/REQUIREMENTS.md` — ENGINE-01..07 (this phase) + explicit Out of Scope table (no transposition cache, no persistence, no "best move" unqualified framing)
- `.planning/ROADMAP.md` — Phase 153 goal + 5 success criteria (note: SC2's "expectation over expanded children" is clarified by D-02 above)

### v2.0 research (read before planning)
- `.planning/research/ARCHITECTURE.md` — module layout (`lib/engine/{types,guardrail,backup,select,mctsSearch,fallbackExpectimax,leafScore}.ts` + `__tests__/`), patterns 1–5, anti-patterns 1–3, data flows (note: its SAN-based example signatures are superseded by D-08 UCI)
- `.planning/research/SUMMARY.md` — build-order rationale, critical pitfalls 2/3/4 (backup degeneration, ELO inversion, arrival-order nondeterminism) — all three are THIS phase's test targets
- `.planning/research/PITFALLS.md` — full pitfall list with prevention guidance

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/liveFlaw.ts` → `evalToExpectedScore()` (line 36): the lichess eval→win% sigmoid — `leafScore.ts` is a thin wrapper, no new formula (ENGINE-05)
- `frontend/src/lib/moveQuality.ts` → `selectCandidatesByMass()` + `CUMULATIVE_MASS_THRESHOLD = 0.95`: the truncation *pattern* to mirror — but the engine defines its own separate ~0.90 constant (D-11)
- `frontend/src/lib/maiaEncoding.ts` → `MAIA_ELO_LADDER` (600–2600 step 100), `maskAndSoftmax`: fabricated providers should emit distributions shaped like the real ones (UCI-keyed, normalized over legal moves)
- `chess.js@1.4.0` (already a dependency): legal-move generation and child-FEN derivation inside the core; UCI↔board plumbing

### Established Patterns
- `frontend/src/hooks/useStockfishGradingEngine.ts` (Phase 151.1): the per-node primitive the core's `grade()` contract mirrors — batched `searchmoves`-restricted MultiPV, **pv[0]-keyed results (never multipv-rank-keyed)**; Phase 154 generalizes this protocol, so the `MoveGrade` shape should stay compatible
- Vitest is the existing frontend test runner — `lib/engine/__tests__/` needs zero new test infrastructure
- `noUncheckedIndexedAccess` is enabled — tree/child index access must be narrowed
- Knip runs in CI — every new export must be imported somewhere (the fallback runner is imported by its own tests, which satisfies this)

### Integration Points
- `frontend/src/lib/engine/` is a NEW nested subsystem (deliberately the one nested exception under flat `lib/`); nothing else imports it in this phase — Phase 154 implements `EngineProviders` for real, Phase 155 consumes `SearchRunner`
- The `SearchRunner` signature (including `extraRootMoves`, `budget.elo` color keying, snapshot-every-backup emission) is the frozen contract Phases 154–157 build against

</code_context>

<specifics>
## Specific Ideas

- The whole design in one sentence (SEED-082): "expectimax semantics living inside MCTS budget allocation" — root = max, everything else = Maia-weighted expectation.
- Selection formula as locked in discussion: root `argmax Q(c) + c_puct·P_root(c)·√N/(1+n(c))`; non-root `argmax P̂(c)·√N(node)/(1+n(c))` (no Q term below root — refine what dominates the expectation; root UCB picks the candidate, prior-driven descent then naturally deepens the modal line).
- ENGINE-07's determinism guarantee is strengthened by D-10: assert the full snapshot *sequence*, not just the final ranking, is bit-identical.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Trap-finder UI, per-ELO sigmoids, time-pressure conditioning, SAB multithreading, and Maia-2 adoption are already formally deferred in REQUIREMENTS.md → Future Requirements.)

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — cosmetic chart fix; keyword match only ("score"), unrelated to a pure TS search core
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — backend/database long-range idea, unrelated to this client-side phase

</deferred>

---

*Phase: 153-Pure Search Core (Guardrail + Backup + MCTS + Fallback)*
*Context gathered: 2026-07-05*
