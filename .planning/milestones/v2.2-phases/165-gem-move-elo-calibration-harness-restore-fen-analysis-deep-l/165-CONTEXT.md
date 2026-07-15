# Phase 165: Gem-move ELO calibration harness + restore ?fen= analysis deep-link - Context

**Gathered:** 2026-07-11
**Status:** Ready for planning
**Source:** SEED-094 (locked in /gsd-explore 2026-07-11) + plan-phase clarifying answers

<domain>
## Phase Boundary

Two deliverables in one phase, both in service of the deferred D-08 ELO-scaled iso-rarity gem ceiling (Phase 163):

1. **Node calibration harness** — a headless, committed, reusable `scripts/` tool that measures, over ~3000 stratified Kaggle "brilliant" moves, the **raw Maia probability of the played move at each ELO rung** {600, 1000, 1400, 1800, 2200, 2600} plus a **single Stockfish C2 grade** per position. Emits a TSV (raw probs + derived gem-at-0.1 booleans + clickable `?fen=` links) and a drop-off summary block.
2. **Restore additive `?fen=<fen>` analysis deep-link** — so the TSV's arbitrary mid-game FEN positions are clickable into `/analysis`. Additive alongside the existing `?line=` param, NOT a revert.

This phase builds the **empirical basis** for the eventual ELO-scaled ceiling. It does NOT change `gemMove.ts`'s `GEM_MAIA_MAX_PROB` — that recalibration is an explicit follow-up seed.
</domain>

<decisions>
## Implementation Decisions

- **D-01 — Harness location & permanence:** Committed, reusable tool in `scripts/` (alongside `scripts/inspect_maia_onnx.mjs`), Node `.mjs`.
  - Parameterized: sample size overridable (`--n`, default **3000**); rungs and input/output paths configurable so the deferred control-set follow-up can reuse it.
- **D-02 — TSV output location:** Write to **`reports/data/`** (e.g. `reports/data/gem-elo-calibration-<timestamp>.tsv`). Browsable in-repo. Consider a sibling summary TSV in the same dir.
- **D-03 — Engine reuse, zero reimplementation drift:** import the **actual** `classifyGem` / `summarizeForGem` / `evalToExpectedScore` and the generated `MISTAKE_DROP` from the frontend — never re-derive (Phase 162/163 single-source discipline); reuse the real engines.
  - **Maia:** `onnxruntime-web` WASM in Node (native `onnxruntime-node` SIGSEGVs on this box; WASM is the same EP the browser uses; proven by `scripts/inspect_maia_onnx.mjs`). Reuse the existing MIT board→tensor encoding + `maskAndSoftmax` path from the frontend (`frontend/src/lib/maiaEncoding.ts` and the Maia worker path) — do NOT hand-roll encoding.
  - **Stockfish:** vendored Stockfish WASM run headless in Node — copy to a non-ESM `.cjs`, drive UCI over stdin/stdout. See memory `project_headless_stockfish_wasm_verification`: illegal `searchmoves` are silently dropped; MultiPV index is an eval rank (key grade maps by `pv[0]`).
  - Planner must resolve how frontend TS is consumed from a Node `.mjs` (tsx / esbuild bundling / direct import) — this is a research item.
- **D-04 — Stratified sampling:** Stratified across the `score` (brilliancy) range so low- and high-brilliancy moves are both represented — do NOT just take the top of the file. Source: `temp/brilliants_no_stalemates.csv` (~22.4M rows; columns `fen,san,site,pieces,score`; FENs are full FENs with move counters → correct side-to-move for both engines).
- **D-05 — TSV schema:** Per move row: `fen`, `san`, `score`, `site`, `c2_pass`, `best_es`, `second_best_es`, `maia_p_600 … maia_p_2600` (6 raw-prob cols), `gem_600 … gem_2600` (6 derived booleans at 0.1 via `classifyGem`), `analysis_url` = `https://flawchess.com/analysis?fen=<url-encoded fen>`.
  - Summary block: gem-detection rate per rung (drop-off curve) + raw-prob distribution per rung (median + a couple of percentiles).
- **D-06 — Additive `?fen=` deep-link:** `?fen=<fen>` loads an arbitrary position as a free-play root; `?line=` stays for start-anchored lines (see `frontend/src/lib/analysisUrl.ts` — `?fen=` was previously removed in favor of `?line=`).
  - Must `encodeURIComponent` the FEN (spaces, `/`). Frontend must decode on load and seed the analysis board at that FEN as root. Add unit tests for build/parse of the `?fen=` param mirroring the existing `?line=` tests.

### Conceptual framing (locked, informational — drives what the harness measures)
- "Brilliant" (wintrcat's flashy-sacrifice score) ≠ "gem" (C1 hard-to-find AND C2 only-good-move). **Do NOT expect perfect overlap** — the disagreement and how it moves with ELO is the signal.
- **C2 is ELO-independent** (a Stockfish eval: best beats runner-up by ≥ `MISTAKE_DROP` in expected score). Only **C1** (the Maia prob) moves across rungs → per position: **1 Stockfish grade + 6 Maia forward passes**.
- **Record RAW probs, not just the boolean.** The raw Maia prob per (move, ELO) is the primary payload; gem-at-0.1 is one derived column. Predicted result: gem-detection rate falls as ELO rises.

### Claude's Discretion
- **Stockfish grading budget:** Pick a depth/movetime + MultiPV faithful to the frontend's grading path without being glacial at 3000 positions. Planner to confirm against the real grading config. [informational]

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Gem logic (single source — import, never re-derive)
- `frontend/src/lib/gemMove.ts` — `classifyGem`, `summarizeForGem`, `GemGrade`, `GEM_MAIA_MAX_PROB`
- `frontend/src/lib/moveQuality.ts` — `evalToExpectedScore` and expected-score conversion
- `frontend/src/generated/flawThresholds.ts` — generated `MISTAKE_DROP`

### Engine reuse
- `scripts/inspect_maia_onnx.mjs` — proven onnxruntime-web-in-Node precedent
- `frontend/src/lib/maiaEncoding.ts` — board→tensor encoding + rung ladder (600–2600, step 100) + `maskAndSoftmax`
- Memory `project_headless_stockfish_wasm_verification` — headless Stockfish WASM UCI driving
- Vendored Stockfish WASM under `frontend/public/engine/` (stockfish-18-lite-single.{js,wasm})

### Deep-link
- `frontend/src/lib/analysisUrl.ts` — URL build/parse helpers (`?line=`, `?game_id=`, `?ply=`)
- `frontend/src/pages/Analysis.tsx` — analysis route entry / param consumption
- `frontend/src/lib/analysisUrl.test.ts` (or `__tests__`) — existing `?line=` unit tests to mirror

### Input data
- `temp/brilliants_no_stalemates.csv` — Kaggle wintrcat brilliant-moves dataset (gitignored)
</canonical_refs>

<specifics>
## Specific Ideas

- ELO rungs are hardcoded {600, 1000, 1400, 1800, 2200, 2600}; all valid on the Maia ladder.
- The harness's headline artifact is the overlap-vs-ELO drop-off curve — make the summary readable.
</specifics>

<deferred>
## Deferred Ideas

- The actual ELO-scaled iso-rarity ceiling in `gemMove.ts` (D-08 proper), derived from this harness's raw-prob distributions — separate follow-up seed. **Not in this phase.**
- Matched control set of ordinary best-moves (recaptures, obvious developing moves) to validate the per-ELO ceiling discriminates — deferred, not rejected.
</deferred>

---

*Phase: 165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l*
*Context gathered: 2026-07-11 from SEED-094 + plan-phase clarifying answers*
