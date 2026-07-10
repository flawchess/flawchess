---
title: Unify the analysis-page Stockfish eval source so all cards agree (kill the separate grading run)
trigger_condition: When next doing analysis-page engine/eval work, or when a user reports cross-card eval inconsistency (a move labeled "Best" showing a lower eval than a move labeled "Good")
planted_date: 2026-07-10
source: /gsd-explore session 2026-07-10 (Adrian's screenshot: Stockfish card Rad1 +4.2 "best" vs FlawChess/Maia cards exd6 +4.3, Bc1 +4.5)
---

# SEED-089: Unify the analysis-page Stockfish eval source

> **2026-07-10 — superseded as the preferred design by SEED-090** (grading-run-authoritative
> precedence flip). A critical review found two load-bearing claims below don't hold: the
> "uncovered ⇒ never Good" guarantee fails at saturated evals (the sigmoid's Good band is
> ~85cp wide at +4.2 — the screenshot's own regime), and the gap fallback fires routinely
> (played blunders are usually outside top-K), so the deferred clamp would be mandatory day
> one. See SEED-090 for details. This seed stays open only as the fallback architecture if
> the dual-worker CPU/battery cost of SEED-090 ever becomes unacceptable — and if revived,
> it must ship the monotone clamp from day one. Plan ONE of the two, not both.

## The problem (user-visible)

On `/analysis`, the three engine cards disagree on the objective (blue) Stockfish eval for the
same move, and the disagreement can **invert the ranking**:

- **Stockfish card** ("Stockfish 18, Depth 19"): `Rad1 (+4.2)` shown as the best move.
- **FlawChess Engine card**: prose says "Objectively `Rad1 (+4.2)`. But for a human at 1811 ELO
  here, FlawChess plays `exd6 (+4.3)`" — i.e. the move it calls *not* objectively best shows a
  **higher** eval than the move it calls best.
- **Maia card tooltip**: `exd6 FlawChess +4.3 95%`, `Bc1 Good +4.5 2%`, `Rad1 Best +4.2 1%` — a
  move labeled "Good" (`Bc1 +4.5`) outranks the move labeled "Best" (`Rad1 +4.2`).

This is confusing and looks broken: "best" should never show a lower number than "good".

## Root cause (diagnosed in the explore session)

The page runs **three independent Stockfish searches** (plus the Maia net), and different cards
read per-move evals from different searches:

| Source | Where | Search config | Feeds |
|---|---|---|---|
| **A — free run** | `frontend/src/hooks/useStockfishEngine.ts` (`MULTIPV=2`, `go movetime 1500 nodes 2000000`) | full-width, top-2, node-capped | Stockfish card (Rad1 +4.2, Rfe1 +3.9) |
| **B — grading run** | `frontend/src/hooks/useStockfishGradingEngine.ts` (`MultiPV = union size`, `go movetime 4000 searchmoves <ucis>`) | `searchmoves`-restricted over the union of shown Maia candidate SANs | Maia card per-move evals |
| **C — MCTS pool grade** | `frontend/src/lib/engine/workerPool.ts` (`go depth 14 searchmoves <ucis> movetime 2500`) via `mctsSearch.ts` / `useFlawChessEngine.ts` | depth-14, drives the engine's move *choice* | FlawChess card per-ply hover previews |

`Analysis.tsx` (lines ~816-902) already tries to reconcile **A + B** via
`frontend/src/lib/engineEvalLookup.ts` `buildEvalLookup(...)` with **free-run-first precedence**
(engineEvalLookup.ts:40-60):

- `reconciledRankedLines` (Analysis.tsx:840-851) swaps each FC line's `objectiveEvalCp` for the
  reconciled lookup value.
- `qualityBySan` (Analysis.tsx:861-882) rebuilds the grade map through the same lookup, then
  `classifyMoveQuality` — driving the Maia line colors and Best/Good labels. The "Best" label
  comes from the **free run's `bestSan`** (Analysis.tsx:871), NOT from comparing the reconciled
  numbers, so the label and the numbers can contradict.
- `engineTopLines` (Analysis.tsx:895-902) pins the FC pick atop the Maia tooltip.

**Why the numbers still diverge:** the reconciliation is free-run-first, so:

- `Rad1` is in the free run's top-2 → resolves to **Source A** (+4.2).
- `exd6` / `Bc1` are **not** in the free run's top-2 → fall back to **Source B**, a *separate*
  Stockfish search at a different budget/depth/scope → +4.3 / +4.5.

Two differently-configured Stockfish searches never agree to the last centipawn (±0.1-0.3 cp),
so a side move can land a hair above the labeled-best move. This is **structural, not a tuning
bug** — `useStockfishGradingEngine.ts:39-52` documents that a prior phase already bumped the
grading movetime to 4000ms to *reduce* this skew; it can't be eliminated while two searches feed
the cards.

### Free run vs grading run depth — is one deeper? (unresolved, competing effects)

Not designed so either dominates; it's uncontrolled and position-dependent:

- **Pushes grading (B) deeper:** ~2.7× the time (4000 vs 1500ms) and `searchmoves` restricts it
  to only the candidate roots instead of all ~30 legal moves.
- **Pushes grading shallower:** `MultiPV = union` forces an exact score for every candidate line;
  high MultiPV weakens alpha-beta pruning → shallower per-line depth for a fixed budget.
- **Free run (A) wildcard:** also `nodes 2000000`-capped, so its "Depth 19" may be node-bound,
  not time-bound.

A headless measurement (run the vendored Stockfish WASM in Node on this exact position under both
configs, compare reached depth + eval for Rad1/exd6/Bc1) was **offered but not yet run** — do this
in the plan phase to confirm the unified pass holds acceptable depth. See the
`headless-stockfish-wasm-verification` memory for the harness recipe.

## Solutions discussed

The right architecture is **one pass = one source of truth**: a single Stockfish search grades
every displayed move; all cards read per-move evals from that one map. This eliminates Source B
and makes the ordering invariant ("nothing labeled Good outranks Best") hold **by construction**.

Two ways to guarantee the displayed union is covered by that single pass:

1. **`searchmoves = top-2 ∪ Maia candidates`** — grade exactly what's displayed, no wasted lines.
   - Cost: **serializes** the Stockfish search behind Maia inference (you can't build the
     searchmoves set until Maia returns its candidate list; today the free run and Maia run in
     **parallel**). Also a chicken-and-egg wrinkle: to include the "top-2 objective moves" you
     already need to know them (needs a cheap seed search or trust high MultiPV to surface them).
2. **High MultiPV, full-width, no `searchmoves`** (e.g. `MultiPV≈8`) — Stockfish returns its own
   top-K keyed by move; every card looks up its move in that map. Stays fully **parallel** with
   Maia, simplest.
   - Risk: a Maia candidate that is a genuine human blunder can fall **outside** the top-K → no
     eval; needs a fallback.

Both share the same **budget/depth tradeoff**: MultiPV over 6-8 lines at a fixed `movetime` is
shallower than the current `MultiPV=2` free run (MultiPV weakens pruning). Either accept a lower
displayed depth than today's "Depth 19", or raise movetime (slower card). This is the empirical
unknown the headless measurement should settle.

## Decision (explore session, both agreed)

**Pick: high-MultiPV, full-width, parallel, with a post-hoc gap-only targeted grade as the
fallback for the rare uncovered Maia move.**

Precedence for a displayed move's blue objective eval:

> **unified free MultiPV=K pass** (primary — all good/top moves + Stockfish's own top-K) →
> **targeted `searchmoves` grade** over just the Maia candidates absent from the unified map

Reasoning:
- **Simpler** than a full searchmoves pass — no seed search, no whole-union build every time.
- **Keeps the Stockfish card fast** — the primary pass stays parallel with Maia, no serialization
  penalty on first paint. A full searchmoves union would couple the card's start time to Maia
  inference for no proportional gain.
- **The fallback is post-hoc and gap-only** — it runs *after* both the unified pass and Maia have
  returned, over just the 1-2 genuinely-uncovered moves, not the whole union. Common case
  (all candidates in top-K): **zero** extra Stockfish calls. This is what keeps it from being a
  mini-resurrection of old Source B (which always graded the whole union and serialized).
- **Guaranteed coverage** — every displayed Maia candidate always has a blue eval. This is why we
  keep a real fallback rather than a "show nothing" terminal render.
- **Correctness by construction** near the top — the Stockfish card's "best" and every card's
  per-move eval for good moves come from the *same* pass, so the label/number contradiction cannot
  occur for a covered move. Derive Best/Good labels from that map's ranking (drop the separate
  free-run `bestSan`). Uncovered moves are, by construction, eval-lossy enough to be labeled
  Inaccuracy/Mistake (never "Good"), so a fallback-graded number on them can't invert the
  Best/Good region.
- **Match the fallback grade's config to the unified pass** (comparable depth/budget) so its
  numbers sit on the same scale. Exactness doesn't matter for bad moves, but matching depth avoids
  gratuitous cross-search wobble.

### Considered and dropped: reuse Source C (MCTS pool grade) for uncovered moves

Tempting because Source C already grades human-likely moves the MCTS explored, so it would cover
most gaps at **zero** extra cost and seemed to let us delete the fallback entirely. **Dropped**
because Source C coverage is *also* not guaranteed (a shown Maia candidate with low policy weight
can be MCTS-pruned → no Source C grade). Since we need a real fallback anyway to *guarantee* every
candidate is covered, adding Source C as an intermediate display tier stops earning its keep: it
would introduce a third eval provenance and a third depth flavor into the display for marginal
savings on an already-rare call. Cleaner to keep two tiers (unified → targeted gap grade) and
leave Source C purely internal.

## Implementation sketch (for the plan phase — not decided in detail)

- Raise `useStockfishEngine.ts` to a higher MultiPV (tune K; start ~8) and have **all** cards read
  objective evals from its output map. **Delete `useStockfishGradingEngine.ts` (Source B)** and its
  reconciliation branch.
- Simplify `engineEvalLookup.ts` / `Analysis.tsx:816-902`: `buildEvalLookup` becomes a single-map
  lookup over the free run; `reconciledRankedLines` / `qualityBySan` / `engineTopLines` all key off
  it; `classifyMoveQuality`'s Best/Good comes from this map's ordering, not free-run `bestSan`.
- **Fallback path** for a Maia candidate absent from the unified map: a **post-hoc, gap-only
  targeted `searchmoves` grade** fired after the unified pass + Maia return, over just the
  uncovered moves, at a config comparable to the unified pass. Common case = zero extra calls.
  Cards read `unified map ∪ targeted map`.
- Re-check the depth/`movetime` budget so the Stockfish card's displayed depth doesn't visibly
  regress (headless measurement first).
- **Residual low-list wobble (do NOT pre-build a guard):** a fallback-graded move could show a hair
  above the worst *covered* move (both clearly bad). If UAT ever flags it, the cheap fix is to clamp
  an uncovered move's displayed eval to not exceed the worst covered eval. Speculative — leave out
  until observed.

## Source C is display-excluded

**Source C** (the MCTS pool grade at depth 14) **stays internal** — the FlawChess engine needs it
to make its move *choice* during search — but it no longer feeds any displayed eval. The FC card's
per-ply hover-preview evals (currently `modalStats[].objectiveEvalCp` from Source C) **switch to the
unified map + targeted fallback** too, so no card ever shows a Source C number. This closes the
"third number in the hover preview" thread cleanly.
