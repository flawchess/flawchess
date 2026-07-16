# Phase 173: Anchor ladder self-calibration (SEED-101) - Context

**Gathered:** 2026-07-15
**Status:** Ready for planning

<domain>
## Phase Boundary

An offline measurement experiment plus a rating-model fit. Play the calibration
harness's anchors against each other (Maia-argmax rungs 700/1100/1500/1900/2300,
Stockfish Skill 0/3/5/8/10, cross-family games included), fit a logistic /
BayesElo-style rating model over the resulting game graph, and place every anchor
on one common internal scale with measured spacing. Scale fixed arbitrarily at
maia1500 = 1500 — explicitly NOT human ELO. Deliverable includes the executed run
and the answer to "is the Maia-3 argmax ladder compressed like Maia-1's?".
Unblocks SEED-102.

Out of scope: any bot-vs-anchor measurement (SEED-102), the blend 0.05 vs 0.5
hedge probe (SEED-102's locate pass), human-ELO correction (SEED-103), lookup
tables (SEED-104), any change to the bot's own move selection.

</domain>

<decisions>
## Implementation Decisions

The user delegated all four gray areas with one binding directive:
**maximize information per game — do not spend games on pairings that carry
no information.** Every decision below serves that directive.

### Match schedule & game budget
- **D-01: Two-pass adaptive schedule (probe → measure).** Probe pass: ~8 games
  per candidate pair to place anchors provisionally. Measure pass: full games
  budget only on pairs whose probe-predicted score sits in the informative
  0.2–0.8 band. Pairs predicted outside the band are dropped, not played out —
  a 0.95-expected-score pair is wasted CPU (same principle as SEED-102's
  locate-then-measure).
- **D-02: No full round-robin.** Base graph: adjacent Maia rungs (700-1100,
  1100-1500, 1500-1900, 1900-2300), adjacent SF skills (0-3, 3-5, 5-8, 8-10),
  plus cross-family links chosen after the probe pass — each SF anchor vs the
  1–2 Maia rungs nearest its *measured* (not folklore) strength. Long-range
  same-family skip pairs only if the probe shows heavy compression (compressed
  ladder → skips become informative; uncompressed → they're 0.9+ blowouts).
- **D-03: 24 games per measured pair** (SE ≈ ±71 per pair; the joint fit pools
  all pairs so per-anchor precision is materially better). Balanced colors,
  seeded per-game PRNG + opening-book start FENs reused from the existing
  harness (its D-09 machinery).
- **D-04: Connectivity guard.** After pruning, the game graph MUST stay
  connected, and the maia and SF subgraphs MUST be joined by at least 2
  informative cross-family links (they are the whole point — they put both
  ladders on one scale). If a planned cross-family pair probes lopsided,
  re-target to a nearer rung rather than dropping the link.

### Rating model & fit tooling
- **D-05: Python fit script in `scripts/`** (project convention; user is a
  data scientist). Logistic (Bradley-Terry/Elo-curve) maximum-likelihood fit on
  game scores with draws counted as 0.5; identify the scale by fixing
  maia1500 = 1500. No external rating binaries (BayesElo/Ordo) — 10 parameters
  do not justify a new tool dependency.
- **D-06: Uncertainty + residuals are mandatory outputs.** Per-anchor CIs
  (bootstrap over games is fine) and per-pair residuals (observed − predicted
  score). Cross-family residuals reported prominently — large ones are the
  style-confounding signal the seed calls out, not a nuisance to hide.
- **D-07: Dependencies.** prefer numpy-or-stdlib-only. Adding scipy as a dev
  dependency is allowed if it materially simplifies the MLE — planner's call.

### Harness integration
- **D-08: New standalone script** (e.g. `scripts/calibration-anchor-ladder.mjs`),
  NOT a mode flag inside `scripts/calibration-harness.mjs`. The bot harness is
  shaped around bot cells (MCTS bot, `ANCHOR_ELO_WINDOW` pruning, bot-cell
  resume keys) — none of which apply to anchor-vs-anchor. Reuse the lib modules
  (`calibration-anchors.mjs`, `calibration-openings.mjs`, `stockfish-pool.mjs`,
  `calibration-providers.mjs`). Where game-loop/adjudication logic currently
  lives inside calibration-harness.mjs, extract it into `scripts/lib/` with no
  behavior change to the bot harness rather than copy-pasting.
- **D-09: Wire SF skills 8 and 10.** add entries to `SF_SKILL_ELO`
  (explicitly-approximate nominal values, used for labels/ordering only — the
  fit ignores them) so `parseAnchorSpec` accepts `sf8`/`sf10`.
- **D-10: Keep harness conventions.** TSV output in `reports/data/`, seeded
  determinism, opening-book start FENs, the existing adjudication rules
  (eval-threshold + ply cap), and `--resume` support (the run is hours long and
  must survive interruption).

### Output artifact & SEED-102 hand-off
- **D-11: Executing the run is in scope.** The phase goal is the *answer*
  (ladder spacing + compression verdict), not just tooling. Run locally on
  Adrian's machine (resumable); anchor-vs-anchor games have no MCTS in the
  loop, so expect hours, not days.
- **D-12: Three deliverable artifacts.** (1) raw per-game/per-pair TSV in
  `reports/data/`; (2) a committed machine-readable internal-scale table at a
  stable path that SEED-102's harness work can consume (exact shape/location is
  the planner's call); (3) a findings note in `.planning/notes/` following the
  pattern of `2026-07-13-bot-calibration-findings.md`, stating the compression
  verdict and closing 168-RESEARCH.md Open Question 2 as a blocker.
- **D-13: Labeling discipline.** every artifact column/field says
  `internal_rating` (or similar) with an explicit "internal scale — NOT human
  ELO" header note. The SEED-091 caveat carries forward verbatim.

### Claude's Discretion
The user delegated all areas ("you decide") subject to the info-efficiency
directive. Researcher/planner may adjust details (exact probe game counts,
cross-family link placement, artifact file shape, CI method) freely as long as
D-01's no-wasted-games principle and D-04's connectivity guard hold.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Experiment rationale (the WHY — read first)
- `.planning/seeds/SEED-101-anchor-ladder-self-calibration.md` — the seed this phase implements: what to measure, why it's cheap, what it unblocks, caveats.
- `.planning/notes/2026-07-13-bot-calibration-findings.md` — Findings 1–4 from the 2026-07-12 harness run; Finding 2 (Maia ladder compression mechanism) and Finding 4 (games-per-pair noise floor) drive this phase's design; the 4-seed architecture chain at the bottom is the roadmap this phase starts.
- `.planning/seeds/SEED-102-iso-strength-surface-sweep.md` — the direct downstream consumer; its "Harness fixes required first" and grid sections define what the internal-scale artifact must support.

### Code to reuse / touch
- `scripts/calibration-harness.mjs` — existing bot-vs-anchor harness; source of conventions (TSV writer, seeded PRNG + opening/color assignment, adjudication, `--resume`) and of game-loop logic to extract into lib (D-08).
- `scripts/lib/calibration-anchors.mjs` — anchor move-choosers (`maiaArgmaxMove`, `stockfishSkillMove`), `SF_SKILL_ELO` (needs 8/10 entries, D-09), `parseAnchorSpec`, `anchorRatingFor`.
- `scripts/lib/calibration-providers.mjs`, `scripts/lib/stockfish-pool.mjs`, `scripts/lib/calibration-openings.mjs` — Node providers, N-process Stockfish pool, opening book; reuse as-is.
- `frontend/src/lib/maiaEncoding.ts` — `MAIA_ELO_LADDER` (600–2600 step 100; maia700/maia2300 already valid tokens).

### Historical context
- `.planning/milestones/v2.3-phases/168-headless-calibration-harness-spike-gated/168-RESEARCH.md` — Open Question 2 (SF Skill → ELO is folklore); this phase retires it as a blocker for relative work.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The whole `scripts/lib/calibration-*` module family: anchor move-choosers, Stockfish process pool, Node engine providers (Maia ONNX + Stockfish), opening book with UCI prefixes. Anchor-vs-anchor needs no new engine plumbing.
- TSV writer + `--resume` + seeded-PRNG patterns in `calibration-harness.mjs` — proven over the 4.85h 2026-07-12 run.

### Established Patterns
- Anchors set every UCI option immediately before their `go` (shared Stockfish process serves multiple roles — option state persists otherwise). Any new game loop must keep this discipline.
- `parseAnchorSpec` gates SF skills on `skillLevel in SF_SKILL_ELO` — sf8/sf10 are currently rejected; D-09 fixes this at the map, not the parser.
- `scripts/` holds Python maintenance/benchmark tools; the fit script follows that convention (D-05).

### Integration Points
- The internal-scale output artifact is consumed by SEED-102's future harness work (window centering / anchor selection). Keep it machine-readable and at a stable path (D-12).
- `ANCHOR_ELO_WINDOW` pruning and bot-cell resume semantics in the bot harness are explicitly NOT applicable to this phase's script — do not thread through them (D-08).

</code_context>

<specifics>
## Specific Ideas

- User's single directive: "make sure we don't waste time testing combinations
  which don't give us useful information" — encoded as D-01 (probe → measure,
  0.2–0.8 score band gate) and D-02 (no full round-robin).
- The seed's framing to preserve: "The offline harness produces *shape*. It
  does not get to name the units."

</specifics>

<deferred>
## Deferred Ideas

- Blend 0.05 vs 0.5 hedge probe at bot_elo 1900/2300 — SEED-102's locate pass, not this phase.
- Any anchor-window / locate-then-measure fix to the bot-vs-anchor harness — SEED-102 ("Harness fixes required first").
- Human-ELO correction of the internal scale — SEED-103.
- Per-style slider-range lookup tables — SEED-104.

### Reviewed Todos (not folded)
- `172-deferred-review-findings` — frontend gem-sweep review deferrals (Analysis.tsx); unrelated to anchor calibration, stays pending.
- `2026-03-11-bitboard-storage-for-partial-position-queries` — database storage idea; unrelated, stays pending.

</deferred>

---

*Phase: 173-anchor-ladder-self-calibration-seed-101*
*Context gathered: 2026-07-15*
