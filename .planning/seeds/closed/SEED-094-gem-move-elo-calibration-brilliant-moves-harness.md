---
title: Gem-move ELO calibration — brilliant-moves validation harness + restore ?fen= deep-link
trigger_condition: Ready to plan now as a single phase; or surface at next /gsd-new-milestone selection
planted_date: 2026-07-11
source: /gsd-explore session 2026-07-11 (Adrian's Kaggle-dataset proposal + design convergence)
---

# SEED-094: Gem-move ELO calibration harness (+ restore `?fen=` deep-link)

## Motivation

Phase 163 shipped gem-move detection with a **flat** findability ceiling:

```ts
// frontend/src/lib/gemMove.ts
export const GEM_MAIA_MAX_PROB = 0.1; // C1: hard-to-find iff Maia prob <= 0.1, at ANY rung
```

D-08 of Phase 163 explicitly deferred replacing this flat cutoff with an **ELO-scaled
iso-rarity curve** — a per-ELO ceiling, because a 0.1 Maia probability means very different
rarity at 600 than at 2600. This seed builds the **empirical basis** for that curve: a
validation harness that measures, over a large set of known-hard moves, the raw Maia
probability at each ELO rung. The headline artifact is the **overlap-vs-ELO drop-off curve**.

Data source: the Kaggle "brilliant chess moves" dataset (wintrcat), downloaded to
`temp/brilliants_no_stalemates.csv` — ~22.4M rows, columns `fen,san,site,pieces,score`
(`score` = wintrcat's brilliancy score, higher = more brilliant; `site` = lichess game URL).

## Conceptual framing (locked in the explore session)

- **"Brilliant" ≠ "gem".** wintrcat's brilliancy is often a flashy sacrifice; our gem is
  *hard-to-find* (C1) AND *only good move* (C2). A dazzling sac with two winning continuations
  is brilliant but fails C2; a quiet unique saving resource is a gem but never tagged brilliant.
  **We do NOT expect perfect overlap** — the disagreement, and how it moves with ELO, is the
  interesting signal.
- **C2 is ELO-independent.** C2 is a Stockfish eval (best beats runner-up by ≥ `MISTAKE_DROP`
  in expected score); rating doesn't enter it. Only **C1** (the Maia prob) moves across rungs.
  So per position: **1 Stockfish grade + 6 Maia forward passes**. Keeps 3000 positions tractable.
- **Predicted result:** gem-detection should **fall as ELO rises** — a move near-invisible to a
  600 gets non-trivial probability mass from a 2600, so C1 stops firing up the ladder.
- **Record RAW probs, not the boolean.** A gem-at-0.1 boolean has already thrown away the exact
  quantity needed to recalibrate the threshold. The primary payload is the raw Maia prob per
  (move, ELO); gem-at-0.1 is just one derived column.

## Scope decisions (locked)

- **Brilliant-only, raw probs.** No negative/control set of ordinary best-moves in v1. If the
  positive (brilliant) distributions turn out ambiguous — e.g. at 600 *every* move sits under
  0.1, so a flat ceiling is too loose there — a matched control set of easy best-moves
  (recaptures, obvious developing moves) is the natural follow-up. Deferred, not rejected.
- **Sample size:** default **3000** moves, overridable via a script parameter (`--n` / arg).
- **Sampling:** stratified across the `score` range so low- and high-brilliancy moves are both
  represented (don't just take the top of the file).
- **ELO rungs:** {600, 1000, 1400, 1800, 2200, 2600} — all valid points on the Maia ladder
  (600–2600, step 100, per `frontend/src/lib/maiaEncoding.ts`).
- **Output format:** **TSV** (not a markdown table — easier to load/pivot for curve-fitting).

## Harness design

**Headless Node, reusing the real engines — zero reimplementation drift.**

- **Maia:** `onnxruntime-web` WASM in Node, already proven by `scripts/inspect_maia_onnx.mjs`
  (native `onnxruntime-node` SIGSEGVs on this box; WASM is the same EP the browser uses). Reuse
  the existing MIT board→tensor encoding + `maskAndSoftmax` path from the frontend.
- **Stockfish:** vendored Stockfish WASM run headless in Node (see memory
  `project_headless_stockfish_wasm_verification` — copy to a non-ESM `.cjs`, drive UCI over
  stdin/stdout; illegal `searchmoves` are silently dropped; MultiPV index is an eval rank).
- **Gem logic:** import the actual `classifyGem` / `summarizeForGem` / `evalToExpectedScore`
  and the generated `MISTAKE_DROP` — never re-derive them (Phase 162/163 single-source
  discipline).

**Per sampled position:**
1. Grade candidates with Stockfish once → best/2nd-best expected score, C2 pass, `playedIsBest`.
2. Run Maia at each of the 6 rungs → raw prob of the played (brilliant) move.
3. Emit one TSV row.

**TSV columns (per move):**
`fen`, `san`, `score` (brilliancy), `site`, `c2_pass`, `best_es`, `second_best_es`,
`maia_p_600 … maia_p_2600` (6 raw-prob cols), `gem_600 … gem_2600` (6 derived booleans at 0.1),
`analysis_url` = `https://flawchess.com/analysis?fen=<fen>`.

**Summary block** (printed / separate small TSV): gem-detection rate per ELO rung (the drop-off
curve), and the raw-prob distribution per rung (median + a couple of percentiles) so the
iso-rarity ceiling can be eyeballed.

## Sub-deliverable: restore `?fen=` analysis deep-link

Phase 163-era work replaced `?fen=` with `?line=` (comma-separated UCI from the start) because
`line` can seed a navigable main line back to move 1 — see `frontend/src/lib/analysisUrl.ts`
and `frontend/src/pages/Analysis.tsx`. But the brilliant dataset is arbitrary **mid-game FENs**
with no move-list-to-start, so the table's links need direct-snapshot loading.

**Additive, NOT a revert.** `?fen=<fen>` loads an arbitrary position as a free-play root;
`?line=` stays for start-anchored lines. Needs `encodeURIComponent` on the FEN (spaces, `/`).
This is what makes the harness's TSV links clickable — build it in the same phase so the
resource is usable end-to-end.

## Why one phase

The `?fen=` link is the interactive study half of the same resource — the TSV is far less
useful without clickable positions. Fold both into a single phase (likely 2 plans: the Node
harness + the frontend deep-link).

## Open questions for planning

- Where does the harness live? (`scripts/` .mjs alongside `inspect_maia_onnx.mjs`.) Is it a
  committed tool or a one-shot? Lean committed (reusable for the eventual control-set follow-up).
- Stockfish depth/MultiPV budget for C2 grading at 3000 positions — pick a depth that's faithful
  to the frontend's grading without being glacial.
- Where does the TSV land — `reports/` or `temp/`? (`temp/` is gitignored; a `reports/` path
  is browsable but 3000 rows is chunky.)
- Confirm `temp/brilliants_no_stalemates.csv` FENs are full FENs (they are — include move
  counters) so Stockfish + Maia get correct side-to-move.

## Follow-up (separate seed when reached)

- The actual **ELO-scaled iso-rarity ceiling** in `gemMove.ts` (D-08 proper), derived from this
  harness's raw-prob distributions — replacing `GEM_MAIA_MAX_PROB`.
- Optional **control set** of ordinary best-moves to validate the per-ELO ceiling discriminates.
