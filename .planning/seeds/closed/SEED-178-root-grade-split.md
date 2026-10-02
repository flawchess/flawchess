---
id: SEED-178
status: closed. Resolved by the 2026-10-02 owner override in Phase 226 (shipped; reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md)
promoted_to: null
planted: 2026-10-01
planted_during: v2.19, Phase 226 plan 226-13 (verdict applied, root split held)
trigger_when: SEED-176 is resolved in favor of shipping AND someone decides the Clear-Hash content bound or the split's content change needs a different treatment; otherwise when bot-move latency is the priority
scope: medium (code exists at arm A21S; the blocker is a content criterion, not engineering)
---

# SEED-178: Root grade split across idle Stockfish workers (held: Clear-Hash content bound)

## Why This Matters

Round 1 always has exactly one expansion (the root), so 3 of 4 Stockfish workers idle during the
most expensive grade. `EngineProviders.gradeRoot` / `WorkerPool.gradeRoot` fan the candidates out
across live idle slots and merge before the single cache write; any failed or aborted shard
discards the whole grade. The win is Stockfish-bound, so it does not shrink when Maia gets faster
(WebGPU).

## Phase 226 result

From `reports/engine-throughput-226/verdict.json` (rendered in
`reports/engine-throughput-226/report.md`):

- **Clear-Hash content: 0.020923 against the 0.016804 bound (fail).** The prototype measured 0.0209
  at step 0 and the real pool implementation reproduces it. Warm content passes (0.015479 against
  0.025206). Root argmax flip rate 7.89% clear, 5.26% warm (report-only).
- Determinism pass. T-50 ratio 0.9694 against 0.97 (pass, margin 0.0006). Other throughput
  configs 0.6347 / 0.7520 / 0.9501 raw (pass, but dominated by A21's CPU drift; the
  CPU-normalized split gain is about 4% at t50-p4 and about 0 at 400 nodes).
- MQ off and on both net -1 (regression-to-pass: `cBFTV`, `Dj8iG`), inside allowance.
- Calibration (report-only): Maia +15.2 +- 27.4, SF +30.7 +- 27.2 pooled, within thresholds. The
  (1500, 0.5) cell reads Maia +75, SF -102 (opposite signs): the Phase 199 CI-overlap guard fires
  (parity verdict "fails"), the pre-registered powered z-guard does not (Maia z 1.58, SF z 2.03).
- Also held by the stacked rule (underfill held).

## What to do

The Clear-Hash bound equals 1.0 x the warm single-vs-single noise floor (0.0168), so it asks the
split to change content no more than the shipped warm hash already does, while measured under
Clear Hash. Two honest options: accept that the split changes content by about 0.0209 mean |des|
(more than the warm-hash noise, still small) via a dated override, or narrow the split (for
example fewer shards, or merge ordering that matches single-call MultiPV noise) and re-measure.
The expected gain is small (about 4% of bot-move wall at 50 nodes after CPU normalization), so
"measured, not worth shipping" is a legitimate outcome here.

## Breadcrumbs

- Arm A21S commit `f6c1f7a5452389d744d61e51f284a026d5cea5f4`; the four arm commits were reverted in
  `719fdfe60`, `de1a589b0`, `d87765a94`, `51c6c5550`. `rootSplit.ts` and its test were created by
  `2f5c4aad3` (reverted in `51c6c5550`).
- `reports/engine-throughput-226/report.md`, `verdict.json`, `design-inputs.md` (sections 2a, 6)
- `frontend/src/lib/engine/workerPool.ts`, `workerPoolDispatch.ts`, `workerPoolState.ts`,
  `mctsSearch.ts` (`dispatchExpansion`), `hooks/useFlawChessEngine.ts`,
  `hooks/useBotGameEngineDispatch.ts`
- `scripts/engine-root-split-content.mjs` (content instrument, single-candidate fix `b79a39538`)
- SEED-171 (parent, item 1), SEED-176 (prerequisite), SEED-130 (warm-hash determinism)
