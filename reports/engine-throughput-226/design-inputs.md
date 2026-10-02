# Phase 226 step-0 design inputs

**Committed:** 2026-09-29, before any arm data exists under `reports/data/engine-throughput-226/gate/`.

This document records **measured inputs**, not decisions. Every value below is transcribed
verbatim from `reports/data/engine-throughput-226/step0/design-inputs.json` (the verdict CLI's
own `design-inputs` subcommand output) or from the committed step-0 TSVs/JSONs it was computed
from. The accept rule (`accept-rule.md`) transcribes these same numbers into its criteria — it
does not re-derive them.

## 1. Provenance

- **Tooling commit T:** `27121e329` or later. Task 1 of Plan 226-07 started from `effcec443`;
  the widened move-quality fixture landed as `fc3086475` (built from `5c2a8deb0`, a
  diagnostic-only stderr-capture change to `scripts/lib/node-engine-providers.mjs`, see 226-07
  Deviations item 1); wall-clock step-0 data was measured from `27121e329` (a revert of two
  stray commits that had landed on this branch, no engine-code change vs `fc3086475`). Every
  tooling commit differs from `main` only in `reports/`, `.planning/`,
  `fixtures/engine/move-quality-226.tsv`, `scripts/engine_throughput_226_verdict.py` and
  `tests/scripts/` — the same set this plan's own prohibitions list.
- **Fixture commit:** `fc3086475` — `fixtures/engine/move-quality-226.tsv`, 60 rows
  (`FIXTURE-CHECK rows=60 ok`): 12 `maia-blindness.tsv` base rows plus 6 rating bands × 8
  lichess CC0 puzzles (1000-1200 … 2000-2200), 0 rejected in every band.
- **Box and load evidence (226-07 SUMMARY):** every wall-clock step-0 run recorded a 1-minute
  load average below 2.0 immediately before launch (range 1.36-1.99 across profiling, content,
  throughput and stop-rule runs). No `remote_eval_worker` process ran during any wall-clock
  measurement. Throughput TSVs carry 32 rows each, `root_split_calls` 0 (the split does not yet
  exist in this tooling commit), and `pool_size` matches the run directory (4/4/2/2 for
  t50-p4/t400-p4/t50-p2/t400-p2).

## 2. Values

Every value below equals the corresponding key in
`reports/data/engine-throughput-226/step0/design-inputs.json`, reproduced by running
`uv run python scripts/engine_throughput_226_verdict.py design-inputs --data-dir
reports/data/engine-throughput-226` (read-only; no `DESIGN-INPUT-ESCALATE` line printed).

| Constant | Value | Protocol formula (step0-protocol.md §7) |
|---|---|---|
| `EXPECTED_MQ_POSITIONS` | 60 | Widened fixture row count (§7: "the widened fixture's row count") |
| `MQ_ALLOWANCE_OFF` | 1 | `max(1, d0)`, stop-off; MQ A0a-vs-A0b run-to-run flip count `d0` = 0 in both stop-off runs (49 pass / 11 regression on both, identical) |
| `MQ_ALLOWANCE_ON` | 1 | `max(1, d0)`, stop-on; `d0` = 0, same identity |
| `CALIBRATION_THRESHOLD_MAIA` | 85.0 | `max(base_threshold, 1.96 × A0b-vs-A0a pooled se)` = `max(85.0, 1.96 × 26.1397) = max(85.0, 51.2338)` → base wins; se floor 51.23 < base 85, no inflation |
| `CALIBRATION_THRESHOLD_SF` | 53.542812708469995 | `max(50.0, 1.96 × 27.3178) = max(50.0, 53.5428)` → se floor wins, threshold inflates from 50.0 to 53.5428 |
| `ROOT_SPLIT_MAX_T50_WALL_RATIO` | 0.97 | `1 - G`, `G = max(0.03, 0.5 × P)` floored to nearest 0.01; `P = 0.05856` (see §2a below); `0.5P = 0.0293 < 0.03` → floor binds, `G = 0.03` |
| `CONTENT_MAX_WARM_MEAN_ABS_DES` | 0.02520619090909091 | `1.5 × warm single-vs-single noise floor (0.016804127...)` |
| `CONTENT_MAX_CLEAR_MEAN_ABS_DES` | 0.016804127272727273 | `1.0 × warm single-vs-single noise floor` (same floor, both content modes bounded by the shipped warm-hash number) |
| `STOP_RULE_MAX_WALL_MS` | 12,100.0 | Carried Phase 225 value (5+3 full-clock think deadline at the tightest common preset); step-0 A0 measured max stop wall was 8,253 ms, comfortably under this ceiling |
| `CANDIDATE_CAP_ARM_ACTIVE` | False | §5: fires iff mean non-root->8-candidate grade-ms share ≥ 0.5 at either budget; measured 0.4626 (50-node) and 0.3595 (400-node), both below 0.5 |

### 2a. `P` derivation (ROOT_SPLIT_MAX_T50_WALL_RATIO)

`P` = (sum of single-call root grade ms − sum of split root grade ms, over the 16 throughput
positions, Clear-Hash prototype content run) ÷ (sum of A0 T-50 pool-4 ladder wall ms).

- Single-call sum (16 throughput positions, `content/clear/*.tsv`, `single_ms`): **8,904.8 ms**.
- Split-call wall sum (same 16 positions, `split_wall_ms`): **3,072.9 ms**.
- Numerator (single − split): **5,831.9 ms**.
- A0 T-50 pool-4 ladder wall sum (`throughput/t50-p4/*.tsv`, `depth == "ladder"` rows, 16
  positions): **99,597.0 ms**.
- `P = 5,831.9 / 99,597.0 = 0.05856`.
- `0.5 × P = 0.02928`, below the 0.03 floor, so `G = 0.03` and
  `ROOT_SPLIT_MAX_T50_WALL_RATIO = 1 - 0.03 = 0.97`, matching the committed value exactly.

**Open Question 2 (minimum candidates per shard)** is answered from the same clear-content run:
total shard CPU (`split_cpu_ms`) summed over the 16 throughput positions is **8,221.0 ms**
against a single-call CPU sum of **8,904.8 ms** — a ratio of **0.923**. The split costs *less*
total CPU than one single-call grade, not more, so no minimum-candidates-per-shard guard is
warranted on CPU-cost grounds at this stage.

## 3. Calibration null (D-09, D-10)

**A0b-vs-A0a (criterion basis; `calibration/verdict-a0b-vs-a0a.json`), verdict `holds`, no
`shape_guard_triggered` cells:**

| Family | Pooled shift | Pooled se | se floor (1.96×se) | Base threshold | Threshold used | Model check fired | Null control (shift / se / threshold) |
|---|---|---|---|---|---|---|---|
| Maia | +0.350 | 26.140 | 51.234 | 85.0 | 85.0 (base wins) | No | +12.295 / 60.190 / 165.0 — within |
| SF | +11.479 | 27.318 | 53.543 | 50.0 | 53.543 (se floor wins) | No | +86.907 / 59.986 / 149.0 — within |

Both families' null-control cells (human1100, blend 0.00) land comfortably inside their Phase
199 validity thresholds, and the pooled null shift itself is small relative to its own se in
both families (Maia 0.01 se from zero; SF 0.42 se from zero). The powered thresholds above carry
no escalation and no model-check firing — the A0a/A0b in-session null behaves as the power model
predicted.

**A0a-vs-July-21 (report-only; `calibration/verdict-a0a-vs-july.json`), verdict `void`,
`shape_guard_triggered` at `(1500, 0.5)`:**

| Family | Pooled shift | Pooled se | Null control (shift / se / threshold / within?) |
|---|---|---|---|
| Maia | −46.473 | 36.419 | −45.304 / 73.051 / 165.0 / within |
| SF | −17.892 | 27.442 | **−177.393** / 69.358 / 149.0 / **NOT within** |

The SF family's null-control cell alone (blend 0.00 — a code path the underfill fix, the guard
and the root split never touch) drifted −177.4 against the July-21 curves, more than the 149-Elo
Phase 199 validity threshold. That single fact renders the entire A0a-vs-July comparison `void`
per §3's rule ("a void comparison answers nothing about whether a real shift occurred") — it says
nothing about item 2 or item 1, only that the July-21 baseline is not currently comparable to a
fresh session's sweep, independent of any engine change.

**Does this explain Phase 225's own A0 drift (−81.4 SF vs July-21, ~2.5 se)?** The in-session
null measured here (A0b vs A0a) has SF pooled se 27.3 — narrower than −81.4/27.3 ≈ 3.0 se, so
Phase 225's drift is *not* explained by ordinary same-session sampling noise alone. But the
comparison Phase 225 made was never a same-session comparison: it was an arm-vs-July-21
comparison, exactly the kind this session's own A0a-vs-July run just showed to be void on an
**unmodified** code path (the null-control cell moved −177.4, over three times the −53.5 powered
SF threshold, with zero engine change). Two independent same-vs-July measurements, taken two
months apart, produced SF null-control shifts of very different magnitude (−177.4 here vs
whatever Phase 225's own null-control read, not re-derived here) while measuring literally the
same code. That is direct evidence that same-vs-July comparisons carry a large,
non-reproducible, cross-session component (consistent with F-7's citation of Stockfish's
time-seeded skill-picker PRNG, and with Phase 199's own note that the July-21 curves were fit
under a materially different engine configuration). Phase 225's −81.4 SF drift is therefore
**most plausibly attributable to this same cross-session non-comparability, not to a real
strength effect from the round-underfill fix** — but because the comparison method itself is
void, this is an explanation of *why the July comparison cannot be trusted*, not a proof that
−81.4 was pure sampling noise in a narrow single-session sense. This is exactly why D-09 forbids
judging any arm against July-21: every calibration criterion in `accept-rule.md` compares
exclusively against this session's own A0a.

## 4. D-13: `cBFTV` trace explanation

**Traces read:** `reports/data/engine-throughput-226/step0/trace/{a0-c1,a0-c2,a0-c4,a2cand-c4}/`
(expansions + snapshots TSVs), on fixture id `cBFTV` and the 11 other `maia-blindness.tsv` rows
as controls (`WwKKM`, `g687537-p48`, `I3vZ1`, and 8 more).

### 4a. TRACE-ANOMALY lines exist at A0 — and not on `cBFTV`

`engine-search-trace.mjs`'s `detectAnomalies` flags a `duplicate-expansion` anomaly whenever the
same root-to-leaf UCI path is graded twice in one row's search. Recounting directly from the
committed expansions TSVs (grouping by `(id, leaf_fen)` within each trace and summing
`occurrence_count - 1` per group) reproduces the exact `TRACE-ANOMALY` counts 226-07-SUMMARY
recorded from the original run's stdout:

| Trace | Duplicate-expansion count (recomputed) | 226-07 SUMMARY count |
|---|---|---|
| a0-c1 | 16 | 16 |
| a0-c2 | 17 | 17 |
| a0-c4 | 12 | 12 |
| a2cand-c4 | 14 | 14 |

**Every single duplicate group across all four traces belongs to one of three control rows —
`WwKKM`, `g687537-p48`, `I3vZ1` — repetition/perpetual-check tactical shuffles where a queen or
rook oscillates near a king.** `cBFTV` itself has **zero** duplicate-leaf-FEN occurrences in any
of the four traces (every `leaf_fen` for `cBFTV` in every trace is unique; verified by grouping
the expansions TSVs on `(id, leaf_fen)` restricted to `id == cBFTV`). The duplicate groups for
the three control rows are structurally identical across A0 (c1, c2, c4) and the A2 candidate
(c4) — same FEN groups, same order of magnitude of repeat counts, present **before any A2
commit exists** (A0 is tooling-only, no `mctsSearch.ts` change). This is a pre-existing property
of these three specific positions (position-repetition/perpetual-check structure), not a defect
introduced by the round-underfill fix.

Per `step0-protocol.md` §6, a literal reading of "any `TRACE-ANOMALY` line" as the bug signature
would misattribute this pre-existing A0 behaviour to item 2. Because this departs from that
literal text, a dated override document records the evidence and the resulting classification:
`reports/engine-throughput-226/override-2026-09-29-d13-trace-anomaly.md`.

### 4b. The `e4c6`-below-`e2g4` mechanism (root_lines snapshots)

Root position (from `fixtures/engine/maia-blindness.tsv`):
`3rk2r/2q2pp1/p4b1p/1pp5/4B1b1/1P6/P3QRPP/4R2K w k - 0 24` — the `e4c6` non-capturing bishop
sacrifice offering itself to enable a delayed mate, vs `e2g4` (themes: `doubleCheck mateIn3
sacrifice`, rating 1324; cf. `reports/grading-ladder/override-2026-07-31.md`, which already
documents this exact position flipping between `e4c6` and `e2g4` as a *known* grading-ladder
sensitivity, prior to this phase).

In **A0 at concurrency 4** (`a0-c4`), the crossover happens at round 12 (expansion_index 36,
node 37/50): before it, `e4c6` leads with 5 visits at practicalScore 0.6688; the round-12
expansion grades leaf `4rk1r/2q2pp1/p1B2b1p/1pp5/6b1/1P6/P4RPP/4R2K w - - 0 26` (depth 10, 2
candidates: `e1e8:#1` — a found mate — and `c6e8:-419`), and `e4c6`'s visits move to 6 with its
practicalScore dropping to 0.6161, below `e2g4`'s concurrent 0.6463 (25 visits). `e2g4` stays
ahead for the remainder of the 50-node budget.

In the **A2 candidate at concurrency 4** (`a2cand-c4`), the identical leaf FEN
(`4rk1r/2q2pp1/p1B2b1p/1pp5/6b1/1P6/P4RPP/4R2K w - - 0 26`) is graded at round 9 (expansion_index
33, node 34/50) with essentially the same grades (`e1e8:#1`, `c6e8:-437`), producing the same
qualitative drop (`e4c6` visits 5→6, score 0.6640→0.6105, falling below `e2g4`'s 0.6340 at 24
visits).

**Round-size sequences (cBFTV only, computed from the expansions TSVs' `round` column):**

| Trace | Round sizes | Total rounds |
|---|---|---|
| a0-c1 | `1,1,1,1,...,1` (50× 1) | 50 |
| a0-c2 | `1,2,2,1,2,2,2,2,2,2,2,2,2,2,2,1,2,2,2,2,2,1,2,2,2,2,2` | 27 |
| a0-c4 | `1,4,2,1,3,4,4,3,3,4,3,4,1,4,4,1,4` | 17 |
| a2cand-c4 | `1,4,4,4,4,4,4,4,4,4,4,4,4,1` | 14 |

The A0 c=4 baseline **underfills rounds repeatedly** — round sizes 1, 2 and 3 appear seven times
out of 17 rounds, exactly the round-underfill defect item 2 fixes. The A2 candidate fills every
round to the full concurrency of 4 except the root (round 0, size 1 by construction — F-1) and
the final leftover round (50 − 1 − 4×12 = 1 node). Because the same 50-node budget is now spread
over 14 denser rounds instead of 17 sparser ones, the *identical* leaf expansion that landed at
round 12/node 37 in A0 lands at round 9/node 34 in the A2 candidate — three rounds earlier, but
carrying the exact same grades. This is the underfill fix's intended effect (denser rounds,
fewer of them) reproducing itself faithfully in the trace, not a change in what gets graded.

**Classification: side effect, not a bug.** All three of `step0-protocol.md` §6's bug signatures
are checked and none holds for `cBFTV` itself:

1. **TRACE-ANOMALY line** — none on `cBFTV` in any trace (§4a); the only anomalies present belong
   to three pre-existing control positions and appear identically at A0 before any A2 code
   exists (the override document above records why this is not counted against item 2).
2. **Blocked-node persistence across rounds** — not directly observable in A0 (A0's tooling
   commit predates `isBlocked`), but the A2-candidate round-size sequence above shows every
   round filled to the full concurrency (bar the root and the final leftover), which is exactly
   the behaviour the fix is supposed to produce and is inconsistent with a node staying
   incorrectly blocked into a later round (a persistent block would show up as further
   underfilled rounds, which are absent after round 1 in `a2cand-c4`).
3. **Stalled root visits with a selectable leaf still available** — `e4f5`'s visit count freezes
   at 1 from round 4 onward in **both** `a0-c4` and `a2cand-c4` (identical stalling pattern,
   present at A0 too), consistent with ordinary best-first-search deprioritization of a
   low-value line rather than a scheduling stall introduced by A2.

The drop traces to specific expansions (the leaf above) whose grades are legitimate Stockfish
output at the depth-10 floor (`GRADING_DEPTH_FLOOR = 10`) — the shallower grade at that node sees
`e1e8` mate but averages in `c6e8`'s poor line, consistent with RESEARCH Pattern 3's leading
hypothesis ("a d10-floor grade at a node that misses [the full value of] a forced mating line").
Per §6's side-effect branch: **item 2 proceeds to gate measurement unchanged — no code fix is
required in `mctsSearch.ts` before A2 re-enters the gate.**

Separately (owner information only, no seed filed, no fix made): the pre-existing
`duplicate-expansion` pattern on `WwKKM`/`g687537-p48`/`I3vZ1` — the same leaf reached via the
identical root-to-leaf path graded twice within one search — is itself worth a future look as a
possible small throughput inefficiency (re-grading nodes that were already graded costs Stockfish
CPU for no new information), independent of whether the round-underfill fix ships. It is
unrelated to `cBFTV` and unrelated to items 1/2/3 of this phase.

## 5. D-17: candidate-cap arm activation

Per-run non-root->8-candidate grade-ms shares (`profile/profile-{50,400}-run{1,2}.json`,
`totals.nonRootGt8Share`):

| Budget | Run 1 | Run 2 | Mean |
|---|---|---|---|
| 50 nodes | 0.46595 | 0.45933 | **0.46264** |
| 400 nodes | 0.35949 | 0.35945 | **0.35947** |

Both budget means are below the 0.5 activation threshold (§5), so `CANDIDATE_CAP_ARM_ACTIVE =
False`. The arm chain for this phase stops at **A21S** — there is no A21SC.

## 6. D-16: root-split content, throughput and stop-rule inputs

- **P, G and the T-50 ratio bar:** see §2a. `P = 0.05856`; `G = max(0.03, 0.5P) floored = 0.03`
  (floor binds — the measured split gain at 50 nodes is small enough that half of it falls below
  the 0.03 floor); `ROOT_SPLIT_MAX_T50_WALL_RATIO = 0.97`.
- **Warm noise floor:** single-vs-single mean |Δes| on two differently-warmed engines = **0.0168**
  (`warm_noise_floor` in design-inputs.json). This is the SAME number used for both content
  bounds (§2): `CONTENT_MAX_CLEAR_MEAN_ABS_DES = 1.0×` it (0.0168), `CONTENT_MAX_WARM_MEAN_ABS_DES
  = 1.5×` it (0.0252).
- **Clear-Hash split-vs-single content (prototype, all 76 positions — 16 throughput + 60 MQ
  fixture roots):** mean |Δes| **0.0209**, p95 **0.0785** (226-07 SUMMARY). This **exceeds** the
  0.0168 Clear-Hash bound derived above — see the finding below.
- **Warm split-vs-single content (same 76 positions):** mean |Δes| **0.0149** — comfortably
  under the 0.0252 warm bound.
- **Root argmax-flip rate:** 6/76 = **7.9%**, identical under Clear-Hash and warm measurement
  (computed from `root_argmax_flip` in both content TSVs). Report-only per §5 of the accept
  rule.
- **Total shard CPU vs single CPU (Open Question 2):** see §2a — split total CPU is 92.3% of
  single-call CPU across the 16 throughput positions; no minimum-candidates-per-shard guard
  needed.
- **Finding — the prototype split already exceeds the Clear-Hash content bound.** Measured
  0.0209 against a derived bound of 0.0168 (1.0× the warm noise floor, per §7's rule that the
  split may not change content more than the shipped warm hash already does, even under
  Clear-Hash measurement). Unless the pool-source split (A21S's real implementation, not the
  prototype `split_root.mjs`) differs materially from the prototype, **A21S is likely to fail
  its Clear-Hash content criterion** when it reaches the gate. It passes comfortably under warm
  measurement (0.0149 vs 0.0252). This is recorded here as a measured fact per this plan's
  prohibition against choosing numbers by judgment — the accept rule transcribes the bound as
  measured, and whether A21S ships is decided at gate time, not here.

## 7. D-08: app premise

RESEARCH F-3 (App pool topology): the analysis board and the bot game each own a separate
`WorkerPool`, never shared, and neither pool is touched by any other engine consumer (gem sweep
and the eval bar use independent `useStockfishGradingEngine`/`useStockfishEngine` instances that
compete for CPU but never hold a pool slot). Within a single pool, the "whole pool idle at round
1" premise is **usually true but not always**:

- **Analysis pool:** a new search aborts the previous one and calls `pool.stopAll()` then starts
  immediately; some slots can still be `'stopping'` (awaiting `bestmove` for the abort) when
  round 1's grade call is issued. The Maia policy call before it (60-140 ms, longer if the Maia
  worker is mid-inference) usually covers that gap, but not always.
- **Bot pool:** a post-commit one-off `.grade(fen, [uci])` for the resign/draw score is normally
  a cache hit, but misses when the root grade never completed (deadline cut) or the move was a
  `fallbackMove`; it then occupies a slot during the user's think time, and a fast reply can
  leave round 1 seeing 3 idle slots instead of 4 (`FLAWCHESS_BOT_CONCURRENCY = 4`, but
  `computePoolSize()` can size the pool to 2/3/4 by device).

**Design consequence:** the app sizes its root-split fan-out from **live idle-and-ready slots at
call time** (`k = min(idle_slots, candidateUcis.length, ROOT_SPLIT_MAX_SHARDS)`), never from a
fixed concurrency constant — this already absorbs `'stopping'` slots, the bot's busy one-off, and
not-yet-ready slots. The harness premise (all engines free at round 1, because every harness
awaits `Promise.all` per round and plays positions/games strictly sequentially) **holds
unconditionally** and is why harness bit-identity per concurrency level (D-08's determinism
scope) is preserved: the harness's own `gradeRoot` gains a tripwire that records whenever
`freeCount() !== size` at call time, so any future harness change that violates this premise is
caught immediately rather than silently producing a smaller split than intended.

## 8. Phase 227 inputs

The D-03 warm-arm (no-Clear-Hash) determinism check: 4 games, 60 total plies recorded, **0
differing** (`abs_des == 0` on every row of
`warm-arm/calibration-determinism-warm-2026-09-28T11-52-32-512Z.tsv`). This is the shipped
round-mode warm-hash noise floor Phase 227's D-06 will scale by its own factor `k` to set the
continuous-dispatch divergence tolerance — this phase measures the floor and hands it off; it
does not fix `k` or implement the tolerance itself (D-01, D-05, D-07 are Phase 227 scope).

---

*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Recorded: 2026-09-29*
