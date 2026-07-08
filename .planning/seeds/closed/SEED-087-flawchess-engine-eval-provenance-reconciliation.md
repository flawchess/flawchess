---
id: SEED-087
status: promoted (→ Phase 158, 2026-07-07)
planted: 2026-07-07
planted_during: Phase 157 UAT — FlawChess agreement verdict eval-consistency review (2026-07-07)
trigger_when: whenever the displayed FlawChess/Stockfish/Maia evals (line cards + agreement verdict + Maia chart) need to be made mutually consistent — or when making the FC/SF line counts configurable, which forces this reconciliation
scope: medium (a post-settle authoritative eval pass + UCI-lookup wiring across THREE surfaces + a shared fallback grading run; a MultiPV-width/latency measurement; no change to the locked MCTS search core)
source: user UAT observations on live 1000- and 2100-ELO analyses (screenshots); root cause confirmed in code 2026-07-07; third provenance chain (Maia card) confirmed 2026-07-07
depends_on: SEED-082 (FlawChess Engine — this reconciles the evals it displays)
---

# SEED-087: FlawChess Engine displayed-eval provenance & reconciliation

## The problem

The `/analysis` page displays Stockfish evals on **three surfaces** — the FlawChess card, the
Stockfish card (+ agreement verdict), and the Maia card (chart tooltip + move-quality bar) —
and they come from **three different Stockfish searches with different configs**, so the same
move can be graded differently by each. The FlawChess pick can even grade *higher* than
Stockfish's own "objective best" move, which is logically impossible if the evals were
comparable.

Three provenance chains (confirmed in code 2026-07-07):

- **FlawChess line evals** (`RankedLine.objectiveEvalCp`, the blue numbers in the FC card) come
  from the MCTS **grading worker pool** (`frontend/src/lib/engine/workerPool.ts`): a
  move-restricted `go depth 14 searchmoves <cands> movetime 2500` with an 8 MB hash. Shallow,
  capped, optimistic — a forced short-horizon search can miss a refutation.
- **Stockfish PV evals** (`engine.pvLines`, the SF card + eval bar) come from the separate
  analysis engine (`frontend/src/hooks/useStockfishEngine.ts`): a free `go movetime 1500` search
  at **MultiPV=2**, default hash. Deeper, authoritative, but only its own top 2 moves.
- **Maia card evals** (`qualityBySan`, the evals in the Moves-by-Rating chart tooltip and the
  move-quality bar's classification input) come from a **third, independent grading worker**
  (`frontend/src/hooks/useStockfishGradingEngine.ts`, Phase 151.1): its own
  searchmoves-restricted MultiPV search over `shownSans` with the *same* depth-14 / 2500 ms cap
  as the pool but a different candidate set, MultiPV width, and hash — so it agrees with
  neither of the other two except by coincidence. Wired in `Analysis.tsx` (`grading` →
  `qualityBySan`).

## The observations that triggered this

- **2100 ELO (2026-07-07).** Verdict: "Objectively O-O (+1.3). But FlawChess plays Qc7 (+2.8)
  — nearly the same eval…". Qc7's **+2.8** (pool grade) is *higher* than O-O's **+1.3** (SF PV),
  yet O-O is called objectively best. The two engines genuinely disagree about Qc7 because the
  pool grades it on a shallow restricted search the free deeper search doesn't corroborate.
- **Evidence the scales otherwise agree:** the same screenshot grades O-O at **+1.4** (pool, FC
  card line 2) vs **+1.3** (SF PV) — near-identical. So `searchmoves` restriction itself is NOT
  the skew; the depth/hash **cap** is. A restricted search at proper depth agrees with the free
  PV. This rules out "different configs = different scales" as the framing — it's a depth
  artifact on specific forced moves, not a systematic offset.
- The same discrepancy already shows **across cards today**: a move in both the SF card and the
  FC card renders different numbers (O-O +1.3 vs +1.4).
- **Three-way pattern confirming three sources (2026-07-07 UAT):** exd5 renders +1.3 in the FC
  card but +1.1 in *both* the Maia and SF cards; Bc5 renders +0.9 in *both* the FC and Maia
  cards but +0.8 in the SF card. Pairwise agreement flips per move — exactly what three
  independent searches produce (coincidental agreement), and what no two-source model explains.

## Already fixed (symptom, not root) — commit e930cd91, Phase 157

The misleading verdict *copy* was patched: the `safe`-tier "nearly the same eval" wording is now
gated on a raw-centipawn check (`NEARLY_SAME_EVAL_CP = 50` in `flawChessVerdict.ts`); above that
gap it says "a safe, practical pick that's far easier to find and play". The false
"always >= 0 by construction" clamp comment was corrected to explain the cross-search
disagreement, and `fcWinPct`/`sfWinPct` were renamed to `…ExpectedScore` (evalToExpectedScore
returns W+½D, not win%). **That stops the prose from lying but does NOT reconcile the numbers** —
the FC card still shows Qc7 at +2.8 next to O-O at +1.3 from different runs. This seed is the
root fix.

## The design — single authoritative run + UCI lookup + ONE shared searchmoves fallback

The set of moves needing deep, mutually-comparable evals is small: the displayed FC moves
(`MAX_LINES = 2` today) ∪ the SF best ∪ the Maia card's `shownSans`. Don't try to back-fill
them by widening the free run alone (coverage gaps), and don't fire one targeted search per
move (doesn't scale).

**Make the free SF MultiPV run the single source of truth.** Every displayed move — SF card, FC
card, Maia card, verdict — looks up its eval from that one run by UCI. Any move shown on two or
more cards then renders the *same* number by construction (fixes the cross-card discrepancy).

**The fallback must be ONE shared run, not per-card.** The original sketch gave each uncovered
FC move its own searchmoves grade, but most displayed FC moves are *also* in the Maia card's
candidate set (high Maia mass is roughly what makes a move a FlawChess pick) — so per-card
fallbacks would still let the FC and Maia cards disagree with *each other* even after both stop
disagreeing with the SF card. Instead: `useStockfishGradingEngine` already IS a
searchmoves-restricted MultiPV grading run; promote it to the single shared fallback by (a)
unioning the displayed FC moves into its candidate set (`shownSans ∪ displayed FC moves`), and
(b) raising its budget to analysis-grade depth (the depth-14 / 2500 ms cap is the proven skew
source). Then every displayed eval resolves by strict precedence: **authoritative free run
first, shared grading run second.**

```
one free SF run @ MultiPV = N              ← source of truth (also drives the eval bar)
one shared grading run (searchmoves over shownSans ∪ FC displayed moves, analysis-grade depth)
  ├─ SF card:   its top N_sf lines (free run by definition)
  ├─ FC card:   each displayed FC move → lookup: free run ▸ shared grading run
  ├─ Maia card: each shown candidate  → lookup: free run ▸ shared grading run
  └─ verdict:   FC pick eval + SF-best eval, both via the same lookup
practical scores (brown badges): still the MCTS expectation — untouched
MCTS pool grades (workerPool.ts): stop being a display source entirely — internal to the search
```

Two wiring details the implementation must handle:

- **Gating.** `useStockfishGradingEngine` is currently gated on `maiaEnabled`. As the shared
  fallback it must run when *either* Maia or the FlawChess Engine needs display evals
  (`maiaEnabled || flawChessEnabled`), with the candidate union reflecting which consumers are
  active.
- **Quality buckets classify from the reconciled eval.** The Maia move-quality bar's 5-bucket
  classification (`classifyMoveQuality`) currently reads the grading run's raw grades. It must
  classify from the same reconciled (post-lookup) evals it displays, or a move's number and its
  severity color can disagree at bucket boundaries.

**Configurable, independent line counts fall out for free.** `N_fc` (FC lines) and `N_sf` (SF
lines) can differ; the reconciliation is per-move ("source each displayed move's eval via the
lookup"), agnostic to the counts. Shared moves stay identical across cards *provided* you commit
to the single lookup rather than parallel searches — that commitment is the whole point.

**The one tuning knob:** the free run's `MultiPV` width trades against eval-bar depth (fixed time
budget). Set it to cover `N_sf` plus a margin and let the shared grading run handle the tail.
Wider = smaller fallback candidate set but a shallower eval bar; narrower = more moves resolved
by the fallback. The grading run's own width-vs-depth trade (its MultiPV = candidate-union size)
needs the same latency/depth measurement on real positions before landing.

**Why `searchmoves` fallback is safe:** proven by the O-O +1.4 ≈ +1.3 agreement above —
restricting which moves are searched doesn't skew the eval; only the depth/hash cap did. Grade
the fallback moves at analysis-grade depth/hash (NOT the pool's depth-14 / 8 MB cap).

## Scope boundary (keep it cheap and non-disruptive)

This is a **display/verdict overlay** — a post-settle re-grade/lookup for the 2-3 shown moves. Do
NOT touch the internal MCTS leaf grades: the practical-score *ranking* is the backed-up
expectation, not `objectiveEvalCp`, so re-grading for display won't perturb rankings or the
locked Phase 153 search core, and stays cheap (one restricted search per settled position, off
the eval-bar critical path).

**Distinct deeper concern, explicitly out of scope:** this fixes the *displayed/compared* evals.
It does NOT address whether the shallow internal pool grades ever mis-*rank* the practical pick
(a move whose shallow leaf value is optimistic could top the ranking wrongly). That's a separate
question about search-internal grade fidelity — flag it, don't fold it in here.

## Relationship to other seeds

- **SEED-085** (root-findability): about which move the engine *selects*. Orthogonal — SEED-087
  is about the *evals it displays* for whatever it selected. In the 2100 case findability was
  fine (Qc7 is the modal move); only the eval provenance was wrong.
- **SEED-082**: the engine this reconciles.

## When to surface

Surfaced 2026-07-07: promoted to **Phase 158** at user request after the three-source pattern
(exd5/Bc5) was confirmed on live analyses. Original triggers were (1) any pass to make the
FC/SF displayed evals mutually consistent, or (2) making the line counts (`MAX_LINES`)
configurable, which forces this reconciliation.

## Breadcrumbs

- `frontend/src/lib/engine/workerPool.ts` — MCTS grading pool (`GRADING_TARGET_DEPTH = 14`,
  `GRADING_MOVETIME_SAFETY_CAP_MS = 2500`, 8 MB hash) → source of `objectiveEvalCp`.
- `frontend/src/hooks/useStockfishEngine.ts` — free analysis engine (`MULTIPV = 2`,
  `MOVETIME_MS = 1500`) → source of `engine.pvLines`.
- `frontend/src/hooks/useStockfishGradingEngine.ts` — the THIRD searcher (Phase 151.1), same
  depth-14 / 2500 ms constants as the pool; becomes the shared fallback run.
- `frontend/src/pages/Analysis.tsx` — wires all three engines; `shownSans` (candidate set),
  `grading` → `qualityBySan` (~line 718-740); passes `engine.pvLines[0]` as the verdict's
  Stockfish side.
- `frontend/src/lib/moveQuality.ts` — `classifyMoveQuality` / `selectCandidatesByMass` (the
  Maia-card classification that must switch to reconciled evals).
- `frontend/src/components/analysis/MaiaHumanPanel.tsx`, `MovesByRatingChart.tsx`,
  `MaiaMoveQualityBar.tsx` — the Maia display surfaces consuming `qualityBySan` /
  `engineTopLines`.
- `frontend/src/lib/flawChessVerdict.ts` — the verdict classifier; `NEARLY_SAME_EVAL_CP`,
  `objectiveEvalGapCp`, `nearlySameEval` (the e930cd91 copy gate).
- `frontend/src/components/analysis/FlawChessEngineLines.tsx` — FC card, `MAX_LINES = 2`.
- `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` — the verdict prose.

## Notes

Captured 2026-07-07 during Phase 157 UAT. Root cause (multi-search eval provenance) confirmed
by code read; the verdict-copy symptom was fixed in the same session (e930cd91). Amended later
the same day: the Maia card (`useStockfishGradingEngine`, Phase 151.1) is a THIRD independent
searcher — confirmed by the exd5/Bc5 pairwise-agreement flip — and the fallback design was
upgraded from per-card searchmoves grades to ONE shared grading run (candidate union, strict
lookup precedence), because per-card fallbacks would leave the FC and Maia cards disagreeing
with each other. Promoted to Phase 158 in the same session.
