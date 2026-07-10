# Phase 159: FlawChess Engine policy temperature + root-move findability (SEED-085) - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the FlawChess Engine recommend the best move the user will *plausibly find* ("best you'll likely find", not "best if you can find it"). Three deliverables, all committed by SEED-085:

1. **Thread B (the real fix):** bring `P_you(X)` into the root ranking so a ~5%-findable tail move (Nb5 @600, Qb8 @1000) can no longer top the list. Ranking-layer only — the per-move practical score `V(X)`, the Phase 153 search core, backup rule, and leaf grades are untouched.
2. **Thread A (complementary knob):** a Maia policy-temperature parameter exposed as a UI slider directly below the ELO slider (>1 flattens toward more human fallibility, <1 sharpens toward Stockfish, 1 = today). The findability weighting reads `P_you` from the temperature-adjusted distribution so the two compose.
3. **Ride-along:** the agreement-verdict copy ("far easier to find and play") is gated on the pick's actual Maia probability so the prose can never contradict the Maia chart rendered beneath it.

Hard boundary from SEED-085: the ranking must NOT collapse into raw `P·V` (the rejected greedy modal-move engine — "what you'll most likely play" is not a recommendation).

</domain>

<decisions>
## Implementation Decisions

### Findability mechanism (Thread B)
- **D-01 (LOCKED):** Root ranking sorts by `rankScore = min(1, P_you/P_ref) · V(X)` — a saturating linear findability factor. **β is fixed at 1** (no exponent; documented as a future one-liner if calibration ever needs a sharper knee).
  - Rejected raw `P^β·V`: P spans orders of magnitude while V doesn't, so the workable β window is narrow and position-dependent (in the 600-ELO case, β ∈ ~(0.15, 0.25) — outside it the 57% Mistake Rxf2 wins). Every miscalibration fails toward the greedy modal engine.
  - Rejected hard floor: needs an explicit empty-set fallback branch, and moves pop in/out of the ranking discontinuously while dragging the ELO/temperature sliders.
  - The saturation is the load-bearing property: any move at or above `P_ref` gets factor 1, so **the modal move can never be boosted above its own V** — the greedy failure mode is impossible by construction, not calibrated away.
- **D-02:** `P_ref(ELO)` curve (anchors and interpolation shape) is **fully Claude's discretion**. Only the qualitative shape is fixed (aggressive at 600, near-off at master) plus three locked regression cases (see D-03).
- **D-03 (acceptance regression cases, from live observations):**
  - Nb5 (5% @600, currently "Best") must NOT top the ranking.
  - Qxf2 (9% @600, Good) must win at 600 — i.e. the fix must not overshoot into recommending Rxf2 (57%, Mistake).
  - Qb8 (@1000, tail move outside the chart's plotted set) must not top the ranking.
- **D-04:** FC card display unchanged: the badge keeps showing the practical score `V`; ordering silently uses `rankScore`. No new markers/UI for demoted moves. (Divergence between sort order and badge is only possible for below-`P_ref` moves, which rarely reach the shown top lines.) The existing popover copy may mention findability weighting.

### Temperature scope (Thread A)
- **D-05:** Temperature applies to the **user's side only** (`P_you`); the opponent's policy stays raw Maia at the ELO setting. Rationale: flattening the opponent has the *opposite* effect (a fallible opponent misses refutations, making sharp moves look better) — a both-sides dial would partially cancel itself. Two knobs rejected as more UI than the seed asked for.
- **D-06:** The temperature-adjusted distribution feeds **the MCTS search policy AND the findability `P_you`** (they compose, per SEED-085). The Maia "Moves by Rating" chart keeps showing **raw** Maia data — it is a measurement of real humans, not a model artifact.
- **D-07:** Temperature is applied **BEFORE** the 0.9-mass candidate truncation (`truncateAndRenormalize`): T>1 puts real mass on tail moves so they genuinely enter the searched set. The fixed visit budget spreads thinner; a named hard cap on root candidate count may guard pathological flatness (Claude's discretion).

### Slider UX
- **D-08:** Range **0.5–2.0, log-symmetric** around the default **1.0** (1.0 at the visual center; halving and doubling are equal steps). Session-only state, default 1.0 on every page load — matches the ELO slider's existing behavior (no localStorage, no URL param). Position: directly below the ELO slider (locked by SEED-085; the ELO slider lives below the Maia card since 155 UAT and drives both engines).
- **D-09:** Plain-language labeling: a label like "Play style" / "Fallibility" with endpoint captions ("Sharper" ↔ "More human"); the numeric T value shown subtly. "Temperature" jargon stays out of the primary copy.

### Verdict copy gating (ride-along)
- **D-10:** The findability claim ("far easier to find and play") requires BOTH: `P_you(FC pick)` exceeds `P_you(SF best)` by a named margin, AND the pick is inside the chart's plotted candidate set (`selectCandidatesByMass` output) — so the chart visibly backs the words by construction.
- **D-11:** When the gate fails, the safe-tier prose falls back to wording the evals actually support (nearly as good / safer follow-ups) with no findability claim — one extra copy variant, per SEED-085's "say what it can back".
- **D-12:** The gate reads **raw Maia at the selected ELO** — the same distribution the chart displays, so non-contradiction with the chart is exact. Temperature stays a search-internal modeling dial (at T≠1 an adjusted-P gate could contradict the raw chart, reintroducing the original defect).

### Claude's Discretion
- `P_ref(ELO)` anchors and interpolation shape (D-02).
- The temperature transform itself (standard `p^(1/T)` renormalized or equivalent) and where it's implemented in the pipeline (provider vs search layer), subject to D-06/D-07.
- Named hard cap on root candidate count under extreme flattening (D-07).
- Slider styling/step count, following the ELO slider's look; desktop + mobile parity per project rules.
- The named margin in the verdict gate (D-10) and exact fallback wording (D-11), following the popover-copy-minimalism norm.
- Whether `ROOT_PRIOR_FLOOR` / exploration behavior needs any adjustment — not discussed; the fix is ranking-layer, so the floor can stay as-is unless research finds a reason.
- Test strategy, subject to project norms (vitest, pure lib functions preferred; the three D-03 cases become regression tests in whatever form fits).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design sources
- `.planning/seeds/SEED-085-engine-policy-temperature-and-low-elo-realism.md` — the full design: both threads, the confirmed code mechanism, the three-target table (rank by V / rank by P·V / best findable V), rejected alternatives, Thread A+B composition requirement.
- `docs/flawchess-engine-explained-2026-07-06.md` — plain-language engine explainer; §5 (truncation, exploration floor) and §8 (deliberate limits) are the context for where temperature slots in.
- SEED-082 (`.planning/seeds/` or `closed/`) — the engine's root=max rationale, the designed-but-unbuilt temperature knob for time pressure, and the explicitly rejected "predict the modal move" design that D-01's saturation guards against.

### Code touchpoints — search core (Phase 153, locked; ranking layer is the only mutable part)
- `frontend/src/lib/engine/select.ts` — `POLICY_MASS_THRESHOLD = 0.9` truncation (temperature applies before it, D-07), `ROOT_PRIOR_FLOOR = 0.10` (the mechanism that let 5% moves win), PUCT selection.
- `frontend/src/lib/engine/treeCommon.ts` — `buildRankedLines` (~line 144): the pure-`practicalScore` sort that D-01 replaces with `rankScore`; `RankedLine` shape.
- `frontend/src/lib/engine/backup.ts` — `backupRootMax`; consumes plain renormalized priors, never floor-boosted ones (unchanged).
- `frontend/src/lib/engine/mctsSearch.ts` — `providers.policy(leaf.fen, budget.elo[leaf.side], leaf.side)` call site (~line 296).
- `frontend/src/lib/engine/fallbackExpectimax.ts` — second `policy()` consumer; must receive the same temperature treatment for parity.
- `frontend/src/lib/engine/maiaQueue.ts` — the real `EngineProviders.policy()` implementation; `(fen, elo)`-keyed cache (a temperature param affects cache keying if applied at this layer).
- `frontend/src/lib/engine/types.ts` — `EngineProviders.policy` signature, `SearchBudget.elo: { w, b }` (D-05 self-only means the temperature parameter is side-aware).

### Code touchpoints — hook and UI
- `frontend/src/hooks/useFlawChessEngine.ts` — passes `elo: { w: elo, b: elo }`; where the temperature param threads in; `extraRootMoves` intentionally unset for the real engine.
- `frontend/src/pages/Analysis.tsx` — wires engines and sliders; `useMaiaEloDefault` usage (~line 499).
- `frontend/src/hooks/useMaiaEloDefault.ts` — the session-only default-with-user-override pattern D-08 mirrors.
- `frontend/src/components/analysis/MaiaHumanPanel.tsx` — the card the ELO slider sits below (slider moved out in 155 UAT).
- `frontend/src/lib/moveQuality.ts` — `selectCandidatesByMass` (0.95-mass ∪ {SF-best}, cap 5): the plotted set D-10's gate checks membership in. Do NOT conflate with the search's 0.9 truncation.
- `frontend/src/lib/flawChessVerdict.ts` — verdict classifier (`SHARP_DROP_THRESHOLD`, `NEARLY_SAME_EVAL_CP`); D-10's gate and D-11's fallback tier land here.
- `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` — the "far easier to find and play" prose.
- `frontend/src/components/analysis/FlawChessEngineLines.tsx` — FC card (`MAX_LINES = 2`), badge display (D-04).

### Related prior phase
- `.planning/phases/158-flawchess-engine-displayed-eval-provenance-reconciliation-se/158-CONTEXT.md` — reconciled displayed evals; the verdict work here must consume the Phase 158 lookup, not reintroduce an independent eval source.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useMaiaEloDefault.ts` — the exact session-only default-with-user-override-precedence pattern the temperature slider state should copy (D-08).
- `truncateAndRenormalize` / `rootExplorationPriors` (`select.ts`) — the layered-transforms pattern (distinct functions in sequence, never conflated); the temperature transform should be another such pure layer.
- The three D-03 regression positions exist as real observed FENs/screenshots (600 and 1000 ELO analyses, 2026-07-06/07) — the planner should recover the FENs for fixture tests if available, else construct equivalent P/V configurations synthetically via the fake-provider test pattern in `__tests__`.

### Established Patterns
- Engine core is deterministic with canonical ascending-UCI tie-breaks everywhere (ENGINE-07) — the new `rankScore` sort must keep the tie-break.
- Named constants for every threshold (project rule) — `P_ref` curve anchors, verdict gate margin, candidate hard cap all need names.
- Pure lib functions + vitest for engine logic; UI changes need desktop + mobile parity and `data-testid`s.

### Integration Points
- `buildRankedLines` (`treeCommon.ts`) is the single seam for D-01 — both `mctsSearch` and `fallbackExpectimax` snapshot through it, so the findability factor lands once and covers both engines. It will need access to the root's (temperature-adjusted) renormalized priors, which live on the root node's children as `prior`.
- `policy()` flows: `maiaQueue.policy(fen, elo, side)` → `mctsSearch`/`fallbackExpectimax` → `truncateAndRenormalize`. Temperature must reach both consumers identically; if applied inside `maiaQueue`, the `(fen, elo)` cache key must gain T (or T applies post-cache).
- The verdict gate (D-10) needs `P_you` per UCI at the selected ELO plus the plotted candidate set — both already computed for the Maia chart in `Analysis.tsx` / `moveQuality.ts`; wire them into `classifyFlawChessVerdict` rather than recomputing.

</code_context>

<specifics>
## Specific Ideas

- The three-target table from SEED-085 is the north star (keep it in the plan):
  ```
  rank by V(X)   → Nb5  (Best, 5%)      ← too Stockfish   ✗
  rank by P·V(X) → Rxf2 (Mistake, 57%)  ← too Maia        ✗
  best FINDABLE V → Qxf2 (Good, 9%)     ← target          ✓
  ```
- Product framing shift (deliberate, from the seed): oracle → coach. "Best move within your reach."
- Slider endpoint captions: "Sharper" ↔ "More human" (or equivalent plain language; final copy at Claude's discretion per D-09).

</specifics>

<deferred>
## Deferred Ideas

- Explicit two-track "findable vs ideal" arrows / teaching surface — rated below the chosen approach in SEED-085; only revive if a distinct teaching surface is wanted.
- Per-side temperature knobs (self + opponent) for time-pressure modeling — SEED-082's original vision; D-05 chose self-only for this phase.
- Played-move vs recommended comparison — already captured as SEED-086.
- "Hard to find" marker on demoted-but-shown FC moves — rejected for this phase (D-04, zero new UI); could revisit if users are confused.

### Reviewed Todos (not folded)
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — keyword false-positive (database storage; unrelated to engine ranking).
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — keyword false-positive (benchmark report chart label; unrelated).

</deferred>

---

*Phase: 159-flawchess-engine-policy-temperature-root-move-findability-se*
*Context gathered: 2026-07-07*
