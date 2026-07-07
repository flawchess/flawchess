---
id: SEED-087
status: dormant
planted: 2026-07-07
planted_during: Phase 157 UAT — FlawChess agreement verdict eval-consistency review (2026-07-07)
trigger_when: whenever the displayed FlawChess/Stockfish evals (line cards + agreement verdict) need to be made mutually consistent — or when making the FC/SF line counts configurable, which forces this reconciliation
scope: medium (a post-settle authoritative eval pass + UCI-lookup wiring; a MultiPV-width/latency measurement; no change to the locked MCTS search core)
source: user UAT observations on live 1000- and 2100-ELO analyses (screenshots); root cause confirmed in code 2026-07-07
depends_on: SEED-082 (FlawChess Engine — this reconciles the evals it displays)
---

# SEED-087: FlawChess Engine displayed-eval provenance & reconciliation

## The problem

The `/analysis` FlawChess card and the agreement verdict display Stockfish evals that come
from **two different Stockfish searches with different configs**, so the same move can be graded
differently by each — and the FlawChess pick can even grade *higher* than Stockfish's own
"objective best" move, which is logically impossible if the evals were comparable.

Two provenance chains (confirmed in code 2026-07-07):

- **FlawChess line evals** (`RankedLine.objectiveEvalCp`, the blue numbers in the FC card) come
  from the MCTS **grading worker pool** (`frontend/src/lib/engine/workerPool.ts`): a
  move-restricted `go depth 14 searchmoves <cands> movetime 2500` with an 8 MB hash. Shallow,
  capped, optimistic — a forced short-horizon search can miss a refutation.
- **Stockfish PV evals** (`engine.pvLines`, the SF card + eval bar) come from the separate
  analysis engine (`frontend/src/hooks/useStockfishEngine.ts`): a free `go movetime 1500` search
  at **MultiPV=2**, default hash. Deeper, authoritative, but only its own top 2 moves.

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

## Already fixed (symptom, not root) — commit e930cd91, Phase 157

The misleading verdict *copy* was patched: the `safe`-tier "nearly the same eval" wording is now
gated on a raw-centipawn check (`NEARLY_SAME_EVAL_CP = 50` in `flawChessVerdict.ts`); above that
gap it says "a safe, practical pick that's far easier to find and play". The false
"always >= 0 by construction" clamp comment was corrected to explain the cross-search
disagreement, and `fcWinPct`/`sfWinPct` were renamed to `…ExpectedScore` (evalToExpectedScore
returns W+½D, not win%). **That stops the prose from lying but does NOT reconcile the numbers** —
the FC card still shows Qc7 at +2.8 next to O-O at +1.3 from different runs. This seed is the
root fix.

## The design — single authoritative run + UCI lookup + searchmoves fallback

The verdict compares exactly two moves, and the SF best is *always* the deep PV#1, so only a
small **set** of moves ever needs deep, mutually-comparable evals: the displayed FC moves
(`MAX_LINES = 2` today) ∪ the SF best. Don't try to back-fill all FC lines by widening the free
run alone (coverage gaps), and don't fire one targeted search per move (doesn't scale).

**Make the free SF MultiPV run the single source of truth.** Every displayed move — SF card, FC
card, verdict — looks up its eval from that one run by UCI. Any move shown in **both** cards then
renders the *same* number by construction (fixes the cross-card discrepancy). The `searchmoves`
pass demotes to a **fallback**, used only for an FC move the free run doesn't cover — and those
are FC-only by definition (outside SF's top-MultiPV), so they never appear in the SF card and
have no cross-card number to disagree with.

```
one free SF run @ MultiPV = N        ← source of truth (also drives the eval bar)
  ├─ SF card:  its top N_sf lines
  ├─ FC card:  each displayed FC move → look up eval in the run by UCI
  │              └─ not covered? → supplementary searchmoves grade (FC-only, deep)
  └─ verdict:  FC pick eval + SF-best eval, both from the run
practical scores (brown badges): still the MCTS expectation — untouched
```

**Configurable, independent line counts fall out for free.** `N_fc` (FC lines) and `N_sf` (SF
lines) can differ; the reconciliation is per-move ("source each displayed move's eval from the
authoritative run"), agnostic to the counts. Shared moves stay identical across cards *provided*
you commit to the single-source-of-truth run rather than two parallel searches — that commitment
is the whole point.

**The one tuning knob:** the free run's `MultiPV` width trades against eval-bar depth (fixed time
budget). Set it to cover `N_sf` plus a margin and let the fallback handle the tail of FC-only
moves. Wider = fewer fallback searches but a shallower eval bar; narrower = more fallbacks.
Needs a latency/depth measurement on real positions before landing.

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

Two natural triggers: (1) any pass to make the FC/SF displayed evals mutually consistent, or
(2) making the line counts (`MAX_LINES`) configurable — that change *forces* this reconciliation,
so do them together. Not urgent on its own now that the verdict copy no longer overclaims
(e930cd91), but the cross-card number discrepancy remains user-visible.

## Breadcrumbs

- `frontend/src/lib/engine/workerPool.ts` — MCTS grading pool (`GRADING_TARGET_DEPTH = 14`,
  `GRADING_MOVETIME_SAFETY_CAP_MS = 2500`, 8 MB hash) → source of `objectiveEvalCp`.
- `frontend/src/hooks/useStockfishEngine.ts` — free analysis engine (`MULTIPV = 2`,
  `MOVETIME_MS = 1500`) → source of `engine.pvLines`.
- `frontend/src/lib/flawChessVerdict.ts` — the verdict classifier; `NEARLY_SAME_EVAL_CP`,
  `objectiveEvalGapCp`, `nearlySameEval` (the e930cd91 copy gate).
- `frontend/src/components/analysis/FlawChessEngineLines.tsx` — FC card, `MAX_LINES = 2`.
- `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` — the verdict prose.
- `frontend/src/pages/Analysis.tsx` — wires both engines; passes `engine.pvLines[0]` as the
  verdict's Stockfish side.

## Notes

Captured 2026-07-07 during Phase 157 UAT. Root cause (two-search eval provenance) confirmed by
code read; the verdict-copy symptom was fixed in the same session (e930cd91), leaving the
displayed-eval reconciliation as the remaining root work this seed tracks.
