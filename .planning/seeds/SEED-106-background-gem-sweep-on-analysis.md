---
title: Background gem sweep on /analysis (+ opening-book markers, gem threshold raise)
trigger_condition: Next /gsd-new-milestone selection; phase-sized frontend feature + one additive backend field
planted_date: 2026-07-14
source: /gsd-explore session 2026-07-14 (Adrian: "gem moves are easily overlooked, the Maia+Stockfish evaluation has some delay")
supersedes: SEED-092 D-02 (no opening-ply guard) — see D6
---

# SEED-106: Background gem sweep on `/analysis`

## Problem

Gems (Phase 163, SEED-092) resolve **lazily, at the position the user is standing on**.
`gemC1` reads the played move's Maia probability from the cached parent curve, and only on
a C1 pass does an on-demand Stockfish grading worker spin up against the parent FEN
(`Analysis.tsx:1414-1539`). The Maia + Stockfish round-trip has real latency, so a user
stepping briskly through a game blows past gems before they render — and a gem the user
never sees is a feature that does not exist.

Fix: resolve gems for the **whole mainline in the background** while the analysis board is
open, so the move list fills in gem badges ahead of the cursor rather than at it.

## The insight that makes it cheap

A gem requires C2 (played move is the graded best AND beats the runner-up by ≥
`MISTAKE_DROP`). **C2 implies the played move lost ~zero expected score.** So the vast
majority of plies can be eliminated with data the analysis page *already fetches and
currently ignores*: `EvalPoint` (`frontend/src/types/library.ts:98-107`) carries per-ply
`es`, `eval_cp` and `best_move` (the backend's engine best move FROM that position, UCI)
for every ply of an analyzed game. Nothing in `Analysis.tsx` reads `best_move` today.

The sweep is therefore a **free → cheap → expensive cascade**, mirroring the backend's
existing `_hint_flaw_plies` trick (`scripts/remote_eval_worker.py:226`):

1. **Free** — keep only plies where `played === best_move` AND the ply is out of book.
   Pure data, zero engine work. Eliminates most plies.
2. **Cheap** — Maia forward pass on the survivors' parent positions for C1. No search.
3. **Expensive** — Stockfish parent grade (MultiPV over the `selectCandidatesByMass`
   candidate set) on the handful that clear C1. A few passes per game, not eighty.

This is not a new mechanism. `gemByNode` (`Analysis.tsx:1484-1521`) already caches a sticky
per-node resolution — a confirmed `GemDetail` or an explicit `null` miss. The sweep is
"run that same resolution ahead of the cursor instead of at it."

## Locked decisions

- **D1 — A gem is a property of the game, not of the view.** Pin gem classification to
  each **mover's own** Lichess-blitz-normalized rating-at-game-time (the rung Phase 164
  already seeds via `deriveRawDefault` / the `*_lichess_blitz` fields). The Elo slider
  drives only the live exploration overlay, **not** the gem badges.
  *This is a behavior change from shipped code* — today `gemC1` resolves the rung via
  `nearestByElo` against the slider (`Analysis.tsx:1445`), so gems shift when the slider
  moves. Pinning is also what makes a background sweep cacheable at all: otherwise every
  slider nudge invalidates the entire sweep.

- **D2 — Analysis move list only. No persistence, no backend gem store.** Gems never
  appear on Library cards or in stats. Consequence: **no Maia in Python.** Maia exists only
  as ONNX in the browser (`useMaiaEngine.ts`), and C1 is the sole reason gems are a
  frontend feature — everything else about them is backend-shaped already. Keeping gems in
  the client preserves v2.0's zero-server-load property (SEED-082).

- **D3 — Sweep analyzed games only.** No backend evals ⇒ no free prefilter ⇒ no sweep.
  Unanalyzed games keep today's lazy behavior and surface the existing one-click Analyze
  pill instead of burning client CPU.

- **D4 — Prefilter: `played === best_move` AND out of opening book.** Both free.
  Strict `best_move` equality (rather than an es-loss band) fails safe: the backend
  searched deeper than the live grading run, so on the rare disagreement we lose a gem
  rather than invent one. Missing a rare gem is the right way to be wrong.

- **D5 — Cascade + contention.** Reuse the existing isolated gem-grading worker and the
  `gemByNode` sticky cache. The sweep MUST yield to the position the user is actually
  looking at — never starve the live free-run/grading engines for the current node.

- **D6 — `games.opening_ply_count` (new nullable SmallInteger).** `opening_lookup.py`
  builds a SAN trie from `app/data/openings.tsv` (3,642 lines), walks to the deepest match,
  and **throws the depth away** — it returns only `(eco, name)`. Persist that depth,
  expose it on the game-detail payload. Backfill is pure SAN replay through the trie: no
  engine, no eval-pipeline load. Rejected alternatives: shipping the trie to the frontend
  as a generated table (bundle cost in a mobile-first PWA to answer one boolean per ply),
  and a fixed ply threshold (wrong in both directions — kills real gems in sharp early
  lines, waves through theory in long ones).
  **This supersedes SEED-092's D-02 ("no opening-ply guard").** Rationale: at low ratings a
  memorized theory move has low Maia probability, so C1 cannot distinguish preparation from
  insight. C2 suppresses most book positions (they usually have several playable moves),
  but not all — and a badge for memorization cheapens the currency.

- **D7 — Raise `GEM_MAIA_MAX_PROB` from 0.10 to 0.20** (`gemMove.ts:25`). "Hard to find"
  becomes "fewer than 1 in 5 rating-peers would play it."
  Measured against the Phase 165 calibration TSV
  (`reports/data/gem-elo-calibration-2026-07-11T14-07-34-084Z.tsv`, 3,000 positions ×
  6 rungs), the raise multiplies gem frequency by **1.35× at Maia-600, rising to ~1.8× at
  2200–2600**. It loosens things most for strong players, who are currently starved (a
  2600-rung player clears C1 on only 2.9% of even the C2-qualifying positions), and it
  *narrows* the Elo skew: the 600-vs-2600 gem-rate ratio falls from 3.8× to 2.9×. So the
  raise runs opposite to SEED-092's low-Elo badge-inflation worry, not with it.
  Caveat for anyone re-reading that TSV: its sample is enriched (21.8% of positions pass
  C2, nowhere near a real-game rate), so the **absolute** frequencies are inflated and only
  the ratios transfer.

- **D8 — Opening-book markers in the move list.** `opening_ply_count` earns its migration
  twice: it gates the sweep (D4) and marks every ply ≤ `opening_ply_count` as theory.
  **Open call for the phase:** marker precedence. Today it is severity > gem
  (`VariationTree.tsx:59-69`, one move never renders two badges). A book move can never be
  a gem (D4 skips it), but it *can* be an inaccuracy — ECO includes plenty of dubious
  gambits — so the book marker must either sit below severity or coexist with it in a
  single marker.

## Risks / open items for the phase

- **Worker contention (D5)** is the main failure mode: a sweep that competes with the live
  engines makes the page feel *worse* while nominally fixing the complaint.
- **`LIVE_EVAL_CACHE_MAX` is 256** (`Analysis.tsx:120`). Comfortable for one game's
  mainline (~200 plies at worst), but it is a shared budget — check eviction behavior on a
  long game once variations are also populating caches, or a move-8 gem can be gone by the
  time the user reaches move 60.
- **Mainline only.** No sweeping of user variations.
- Real-game gem frequency is deliberately **not** being measured first (explicit call,
  2026-07-14). D7's ratios came from the existing harness TSV; absolute rates will be
  judged in UAT on real games.

## Scope shape

Frontend sweep + display, plus one additive backend field:
- Backend: capture trie depth in `opening_lookup.py`, `games.opening_ply_count` column +
  migration + backfill, expose on the game-detail payload.
- Frontend: pin gem rung to the mover's seeded rating (D1), background sweep with the
  free/cheap/expensive cascade (D4/D5), raise `GEM_MAIA_MAX_PROB` (D7), book markers in
  `VariationTree` (D8).
