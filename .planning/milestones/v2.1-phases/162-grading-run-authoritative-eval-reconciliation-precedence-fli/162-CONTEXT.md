# Phase 162: Grading-run-authoritative eval reconciliation — precedence flip (SEED-090) - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning
**Source:** SEED-090 (locked design) + discuss session 2026-07-10 (four open points resolved)

<domain>
## Phase Boundary

Make the grading run (`useStockfishGradingEngine`: `searchmoves`-restricted, `movetime 4000`, one coherent MultiPV ranking over every displayed candidate) the **authoritative source for every displayed per-move eval** on `/analysis`, with the free run (`useStockfishEngine`: MultiPV=2, `movetime 1500`) serving only as fast first paint and pre-grading placeholder. This closes the "a move labeled Good shows a higher number than the move labeled Best" bug by construction: the grading union IS the displayed set, and one search feeds every compared number.

Frontend-only, no backend. Both workers stay exactly as configured today — no worker deleted, no MultiPV retune, no new fallback code path, no headless re-measurement gate (Phase 158's depth-parity measurement already covers the grading config, see `useStockfishGradingEngine.ts:39-52`).

**This phase deliberately reverses Phase 158's locked "free run first, grading second" precedence.** The reversal is quality-justified: at movetime 4000 and union size 6-9, the grading run reaches depth parity with or exceeds the free run. Everything else from Phase 158 stands (single UCI-keyed lookup module, `sanToUci` reuse, no MCTS-pool-grade display path, `gradingEnabled = maiaEnabled || flawChessEnabled` gating).

</domain>

<decisions>
## Implementation Decisions

### Locked by SEED-090 (read the seed — it is the design doc)
- **D-01 Precedence flip:** `buildEvalLookup` becomes grading-first; free-run values fill only not-yet-graded moves. A move's number upgrades once (free → grading) then only sharpens within the grading stream.
- **D-02 Union extension:** `unionSans` (Analysis.tsx:796-800) extends with the free run's top-2 root-move SANs, so there is no "uncovered displayed move" and hence no cross-search gap grade. Keep the existing sort+dedup.
- **D-03 Best-label rule:** Best = argmax over reconciled displayed evals, tie-break toward free-run `bestSan`. Stop passing the free-run pin to `classifyMoveQuality` once grading values are in (or pass a grading-derived pin) — keeping the free-run pin would recreate the bug in mirror image.
- **D-04 Stockfish card reads the lookup:** its two PV lines' evals resolve through the reconciled lookup; re-sort the card's 2 lines by reconciled eval. PV move-sequence text stays free-run (display-only divergence accepted).
- **D-05 Depth label:** card headline keeps the free run's depth (it describes the displayed PV lines).
- **D-06 Source C stays display-excluded:** FC card hover previews read the reconciled lookup, never the MCTS pool grade (carried from Phase 158 / SEED-089).

### SF board-arrow alignment (discussed — not covered by the seed)
- **D-07:** The green SF best-move arrow (`engineArrows`, Analysis.tsx:1291-1303, currently raw `engine.pvLines[0].moves[0]`) **follows the reconciled argmax** — the same source as the card's re-sorted line 1 and the chart's Best crown. Arrow, card, chart, and verdict agree by construction; the arrow may jump once when grading lands (~4s), same visual class as the accepted label flips (D-10). The amber FC arrow (practical pick) is untouched.

### Eval bar / headline eval (discussed — seed change 5 resolved as option b)
- **D-08:** Free-run first paint (<100ms unchanged), then the headline/bar **refines once to the reconciled best move's eval** when grading lands. When `gradingEnabled` is false, the bar stays free-run — no special casing beyond the lookup's natural fallback.

### Union-churn restart stance (discussed)
- **D-09:** The free run's top-2 contribution joins the grading union **only after the free run's `bestmove` commits** — day one, not UAT-reactive. This eliminates the restart source this phase itself introduces (2nd PV line reordering mid-free-run). Costs ≤1.5s delay on grading ≤1 extra move (invisible given grade cache + progressive streaming). Maia/FC union churn behavior is unchanged.

### Label-flip flicker stance (discussed)
- **D-10:** **Live argmax per committed reconciled snapshot** — labels, arrow, bar, and numbers re-derive together from each snapshot, so a contradiction is impossible at every instant; near-tie Best/Good flips mid-stream are accepted (same class as depth-climb reordering, rarer now that D-09 gates union churn). **If UAT flags flicker, the remedy is atomic-at-commit (one switch of the whole reconciled map at grading `bestmove`), NEVER a label pin** — pinning the label while grading numbers stream reopens the contradiction window the phase exists to close.

### Anti-circularity note (Claude flagged, no user decision needed)
- **D-11:** `bestSan` (Analysis.tsx:749) stays **free-run-derived where it is a grading-union INPUT** (`selectCandidatesByMass` union contribution, D-09 timing) — the reconciled argmax is downstream of the union, so deriving the union input from it would be circular. Only display consumers (chart crown, labels, arrow, bar, verdict) switch to the reconciled source.

### Claude's Discretion
- Where the argmax/derived-pin logic lives (extend `engineEvalLookup.ts`, a new pure helper, or Analysis.tsx memo) — pick the seam that keeps functions small; pure lib functions preferred for testability.
- How the "free-run bestmove committed" signal threads into the `unionSans` memo (the free-run hook already knows its terminal state).
- Test strategy per project norms (vitest; the seed's verification sketch lists the two mandatory units: precedence flip, and the mirror-image Best-label case).

### Amendment 2026-07-10 (post-research, user-locked)
Research (162-RESEARCH.md) surfaced two ambiguities in D-07/D-11; the user resolved both:

- **D-12 True-global-argmax scope:** The best-move arrow, chart crown, and verdict target the **true global reconciled argmax** over the full reconciled grade map — even when that move is not among the Stockfish card's 2 displayed lines (card stays MULTIPV=2, not widened). Accepted, documented residual edge case: the arrow may point at a move the Stockfish card doesn't list. This fully closes the exd6-outranks-Rad1 scenario; do NOT constrain the argmax to the free run's own top-2.
- **D-13 Verdict re-sourcing:** The agreement verdict's Stockfish side is **re-sourced to the reconciled-argmax move** (constructed from the reconciled best UCI + its lookup eval), not merely the free-run `engine.pvLines[0]` move with a corrected eval. One source of truth for "Best" across the page; the verdict may name a different move than today.
- Research also identified two call sites that bypass the eval lookup today and MUST be brought in scope: `Analysis.tsx` `stockfishLine={engine.pvLines[0]}` (verdict, covered by D-13) and `useGameOverlay.ts`'s raw `engine.evalCp`/`evalMate`/`depth` passthrough (thread the reconciled-best eval derived once in Analysis.tsx per D-08).

### Amendment 2026-07-10 (UAT feedback, user-locked)
UAT test 2 flagged the D-12 residual edge case as unacceptable in practice (Stockfish card headlined Rad1 +4.2 while every other surface named Bc1 +4.3); the user chose the full card re-source:

- **D-14 Card re-source (supersedes the card scope of D-04/D-05/D-12):** The Stockfish card's lines are the **top-2 of the reconciled ranking over the full grading union** (`rankReconciledCandidates`, whose head IS `resolveReconciledBest` — argmax and card ordering agree by construction), with PV move text from the grading run's retained `pv` (MoveGrade gained an optional `pv` field; the grading hook stores `parsed.pv`). Free-run lines with reconciled evals remain only the pre-grading placeholder path, gated on the same WR-01 `reconciledBestUci` signal as the arrow/verdict so all surfaces re-source at the same instant. The headline depth now describes line 1's own grade (via `reconciledBestEval.depth`, free-run depth pre-grading). D-12's "the card may not list the arrow's move" divergence is gone: card line 1, arrow, chart crown, and verdict name the same move whenever grading has landed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source
- `.planning/seeds/SEED-090-grading-run-authoritative-eval-precedence-flip.md` — THE design doc: full change list (1-7), timing profile of the grading trigger chain, accepted trade-offs, verification sketch.
- `.planning/seeds/SEED-089-unify-analysis-stockfish-eval-source.md` — the superseded alternative; contains the full root-cause diagnosis (three independent searches) and the sigmoid-flattening analysis (why coverage-by-rank ≠ coverage-by-label at large evals). Background only — do NOT implement its option 2.

### Prior-phase context
- `.planning/milestones/v2.0-phases/158-flawchess-engine-displayed-eval-provenance-reconciliation-se/158-CONTEXT.md` — the architecture this phase amends; everything there stands EXCEPT the "free run first" precedence direction.

### Code touchpoints
- `frontend/src/lib/engineEvalLookup.ts` — `buildEvalLookup` precedence flip lands here; module docstring (which documents free-run-first as LOCKED) must be rewritten to cite SEED-090/Phase 162.
- `frontend/src/pages/Analysis.tsx` — `bestSan` (~749), `unionSans` (~796), `gradingEnabled` (~806), `evalLookup` (~828), `reconciledRankedLines` (~840), `qualityBySan` + free-run pin (~861-882), `engineArrows` (~1275-1306).
- `frontend/src/hooks/useStockfishGradingEngine.ts` — grading run; lines 39-52 document the Phase 158 depth-parity measurement that justifies the flip. "multipv is an eval rank, key by pv[0]" caveat applies.
- `frontend/src/hooks/useStockfishEngine.ts` — free run; source of the top-2 union extension and the bestmove-commit signal (D-09).
- `frontend/src/lib/moveQuality.ts` — `classifyMoveQuality` (own-top-scorer path already does the argmax) / `selectCandidatesByMass` (D-07 union of playedSan).
- `frontend/src/lib/liveFlaw.ts` — `LICHESS_K ≈ 0.00368` sigmoid + `INACCURACY_DROP` thresholds (label-band math referenced in the seed's diagnosis).
- `frontend/src/lib/flawChessVerdict.ts`, `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` — verdict consumes the lookup (unchanged wiring, values flip with precedence).
- `frontend/src/components/analysis/MovesByRatingChart.tsx`, `MaiaMoveQualityBar.tsx` — chart crown/label consumers of D-03.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engineEvalLookup.ts` is already the single UCI-keyed lookup with both sources as parameters — the flip is a loop-order/precedence change plus docstring rewrite, not a new module.
- `qualityBySan` (Analysis.tsx:861-882) already classifies from reconciled grades; the change is the pin argument (D-03), not the plumbing.
- The grading hook's per-(FEN, SAN) grade cache + progressive `info`-line streaming already mitigate restarts; D-09 builds on that, no new cache needed.

### Established Patterns
- Sort+dedup of `unionSans` (candidatesKey pattern) prevents same-set re-triggers — the D-02 extension must preserve it.
- Phase 151.1 caveat: MultiPV index is an eval rank, key grades by `pv[0]` — applies to any new grading-map consumer.
- Named constants for any new threshold (project rule); pure lib functions + vitest for the lookup/argmax logic.

### Integration Points
- `engineArrows` memo gains a dependency on the reconciled lookup (D-07).
- Eval bar / headline component gains a reconciled-best resolution (D-08) — locate the current eval-bar value source during planning.
- Free-run hook must expose (or already exposes) a bestmove-committed signal for D-09.

</code_context>

<specifics>
## Specific Ideas

- Acceptance smoke (from the seed): on the SEED-089 screenshot position, Stockfish card, FC card prose, and Maia tooltip show identical numbers for Rad1/exd6/Bc1, ordering consistent with labels; rapid game navigation leaves no orphaned grades, restarts converge, card first paint stays <100ms.
- Mandatory unit tests (from the seed): (1) `buildEvalLookup` grading-wins-on-overlap + free-run-fills-gaps; (2) mirror-image Best-label case — grading map where a non-`bestSan` move has the top reconciled eval → it gets `best`, `bestSan` gets `good`.
- Headless Stockfish WASM verification available if needed (vendored `stockfish-18-lite-single.js` in Node as `.cjs`; illegal `searchmoves` silently dropped).

</specifics>

<deferred>
## Deferred Ideas

- SEED-089 (one high-MultiPV pass, single worker) stays open as the fallback architecture — revisit only if mobile CPU/battery cost of two live workers becomes a complaint, and then with the day-one clamp amendment.
- Atomic-at-commit display switching — pre-agreed remedy if UAT flags label/arrow flicker (D-10); not built unless flagged.

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` (WR-01 — `pt-33` invalid Tailwind class on the Score Y-axis label) — chart-styling nit unrelated to eval reconciliation; stays in the todo backlog.

</deferred>

---

*Phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli*
*Context gathered: 2026-07-10*
