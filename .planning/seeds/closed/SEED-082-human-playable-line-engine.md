---
id: SEED-082
status: dormant
planted: 2026-07-04
refined: 2026-07-05 (design discussion — algorithm, architecture, and naming locked)
planted_during: SEED-081 explore/spike session
trigger_when: after SEED-081 ships (needs the Maia inference infra); a later milestone
scope: large (a novel engine — its own milestone)
source: /gsd-explore session 2026-07-04 (user idea); refined in discussion 2026-07-05
depends_on: SEED-081 (Maia inference in the browser)
---

# SEED-082: FlawChess Engine (practical-play engine built on Stockfish and Maia)

A **novel engine** that produces the **best *human-playable* line**, not the best objective
line. It combines Stockfish (objective quality) and Maia (human move probabilities per ELO)
into a search whose objective is **expected practical score**: the line a real player at this
level could actually find and follow, against an opponent who defends like a real human at
*their* level — not an engine-perfect PV full of only-moves nobody at 1400 would see.

This is the practical-play complement to SEED-081: SEED-081 *diagnoses* human play
(per-ELO move distributions, WDL, flaw verdicts); this engine *prescribes* it (the strongest
line you can realistically execute).

## Naming (locked)

Call it the **FlawChess Engine**, framed as *"a practical-play engine built on Stockfish and
Maia."* This claims the right amount: the search and the objective (expected practical score)
are ours; the evaluation components are credited. Precedent: lc0 is an engine even though the
network does the evaluating.

- **Do NOT claim we invented the practical-play engine.** The prior-art survey (below) found
  the core concept — Maia human-model + objective-eval expectimax that plays swindles — is
  already shipped by at least two systems (Polecat, vala-bot). Safe framing is *"a
  practical-play **analysis** engine"* (they are opponent bots; ours is a game-review /
  teaching tool) and, if a novelty hook is wanted, the asymmetric self+opponent rating with
  self-execution modelling — not "novel engine" unqualified.
- Never present output as "best move" unqualified — always "best **practical** move for you."
  Disagreement with Stockfish is intentional and the UI copy must make it look intentional.
- Licensing: **resolved** — FlawChess relicensed MIT → AGPL-3 this milestone (2026-07).
  AGPL-3 is GPLv3-compatible, which covers distributing stockfish.wasm and the Maia weights.

## The algorithm (locked): expectimax value inside MCTS budget allocation

Two earlier candidate designs were rejected in discussion:

- **Multi-PV + filter** — multi-PV only diversifies at the *root*; every continuation is still
  an engine-perfect PV (including perfect opponent defense), so filtering discards lines but
  never *produces* a human-playable continuation. Also invisible: the objectively-second-best
  move that poses a problem the opponent fails 60% of the time — arguably the whole point.
- **Greedy move-by-move (keep the most findable move)** — degenerates into predicting the
  player's modal game, mistakes included. Diagnosis, not recommendation. No lookahead.

The synthesis — each model does what it's good at:

- **Stockfish = quality axis**: shallow evals (depth ~12–16) of candidate children. The
  per-node primitive (Maia top-k candidates graded by Stockfish) is exactly what Phase 151
  builds.
- **Maia = probability axis**: opponent reply *distribution* at opponent ELO; your own
  execution probability at your ELO (asymmetric ELO is structural, not bolted on).

**Practical value, recursively:**

- **Opponent to move**: `V = Σ P_maia(m | opp_ELO) · V(child)` over Maia top-k replies
  (truncate at ~90% cumulative probability, renormalize; typically 3–5 moves).
- **You to move (below root)**: expectation under *your* Maia distribution — you won't have
  the engine over the board; modeling your future self honestly is what prices in "can I
  actually execute this line?"
- **Root**: max over candidates (union of Stockfish multi-PV top-m and Maia top-k), ranked
  by V.
- **Leaves** (depth ~6–10 plies): Stockfish eval → expected score via the **lichess
  eval-to-win% formula** for MVP. Deferred upgrade: fit per-ELO-bucket sigmoids from the
  benchmark DB (positions with evals + known results) — clean, isolated swap later. Known MVP
  limitation: the lichess curve is rating-agnostic, so beyond the search horizon everyone
  converts like an average lichess player; within the horizon realism comes from the explicit
  Maia modeling.

**Displayed line** = modal path (your chosen moves + opponent's most likely replies), with
branch points ("if instead ...Qxb2, which 30% of opponents play, then...").

This formulation **dissolves the old open questions**:

- *Findability aggregation* (product/min/geomean): gone — findability enters as a proper
  expectation. A line needing a move you find 8% of the time contributes 8% of the brilliant
  continuation plus 92% of what you'd actually play instead.
- *Quality × findability combination*: gone — one scalar, expected practical score, in units
  users already know (expected points, comparable to WDL everywhere else in FlawChess).
- *Rank/flag, don't discard*: falls out for free — "objectively +3.0, practically +0.9 for
  you, because 14...Rd7!! is found by 8% at your level." Teaching moment surfaced, nothing
  silently deleted.
- **Emergent killer feature**: trap/swindle finding — the search naturally ranks an
  objectively inferior move above the "best" move when the opponent's likely replies lose.
  Strongest differentiation from every existing analysis tool.

**Search = MCTS, started in v1 (decision reversed from "keep for v2").** Node-budget
arithmetic decided it: a wasm Stockfish eval at useful depth costs ~50–300ms, so a
seconds-scale budget yields only a few hundred node evaluations. At that budget,
uniform-depth expectimax wastes most nodes on lines dead at ply 2; MCTS's adaptive
allocation (main line 10+ plies deep, junk abandoned immediately) is the difference between
usable and toy. Realtime refinement is also native to MCTS. Run it in a deliberately boring
configuration:

- No Dirichlet noise, deterministic tie-breaking, fixed node budgets in tests → reproducible.
- **Custom backup rule** (where we diverge from textbook PUCT): non-root nodes back up the
  Maia-prior-weighted expectation over expanded children (opponent ELO at opponent nodes,
  your ELO at your future nodes); root stays max. This is the expectimax semantics living
  inside MCTS budget allocation — the whole design in one sentence.
- **Guardrail**: search lives behind a small interface (position + budget in; ranked root
  moves with lines out; supports incremental emission). If MCTS tuning becomes a time sink, a
  depth-limited expectimax is recoverable in a day behind the same interface.

## Architecture (locked): client-side everything

- Maia inference in the browser (SEED-081 infra) + **stockfish.wasm**, zero server load.
  Natural fit with a live analysis page (SEED-066). A browser↔server search loop was rejected
  as latency-miserable.
- **Parallelism: pool of 2–4 single-threaded Stockfish workers**, each grading a different
  leaf — near-linear speedup, embarrassingly parallel, matches our many-shallow-evals
  workload (unlike lichess's one-deep-search workload). No SharedArrayBuffer needed.
  - **SAB multithreading deferred**: needs COOP/COEP cross-origin isolation, and COOP
    `same-origin` severs `window.opener` — breaks popup OAuth (we have Google sign-in).
    Solvable (scope headers to the analysis route, or COEP `credentialless`) but it's a
    deployment-level decision with blast radius beyond the engine. Only genuinely helps deep
    multi-PV grading of the root.
  - Pool size capped by memory (each instance loads its own NNUE net).
- **No app-level Zobrist/transposition caching** — positions diverge too fast to pay off;
  stockfish.wasm's internal TT gives partial reuse for free.
- **Anytime requirement**: quick top-n lines immediately, refined live as the search deepens.
  Native to MCTS (emit ranked root children + modal lines as visits accumulate). The worker
  pool needs a node-evaluation priority queue favoring the currently-best root lines.

## UI (locked): four arrow layers

Board arrows, toggleable layers with distinct colors (constants in `theme.ts`):

1. **Played move** — the move actually played in the game (maiachess.com does this; lichess
   and chess.com don't). Only exists in game review, not free analysis. Pedagogically central:
   "what you played" vs "what was practically best for you" is the engine's whole loop.
2. **FlawChess Engine top-2** — live-refining.
3. **Maia top-2** — single forward pass: instant, static (no depth dimension to refine).
4. **Stockfish top-2** — live-refining.

Defaults: game review = played + FlawChess Engine on; Maia + Stockfish off as "show your
work" layers.

## MVP phasing

1. **MVP0 = Phase 151 (in progress)**: Maia candidates graded by Stockfish at the root — the
   per-node primitive.
2. **MVP1**: MCTS on top of that primitive, single position, modal-path display with the
   objective-vs-practical score pair, live-refining top-n lines + arrows. Already novel.
3. **Ambitious**: branch-point display, trap-finder surfacing ("best practical try"),
   per-ELO leaf sigmoids from the benchmark DB, time-pressure modeling (below),
   SAB-multithreaded root grading.

## Time control & time pressure (designed extension, post-MVP)

Maia conditions on rating only, and its training pipeline filtered out low-clock moves
(verify against the integrated model's card), so bullet scrambles are out of distribution by
construction. Rather than waiting for a clock-conditioned Maia, model time pressure with two
knobs on the existing model, **calibrated from our own database**:

- **Effective-ELO offset**: under time pressure, query Maia at a reduced rating (a 1700 with
  10 seconds plays like a much weaker player).
- **Temperature on the policy distribution**: time-pressure play is *noisier*, not just
  weaker — flatten the distribution so low-probability blunders gain mass.
- **Calibration**: we import per-move clocks (lichess `%clk`, chess.com `clk` — the
  time-management feature is built on them). Fit clock→temperature and clock→ELO-offset
  curves by maximizing Maia's likelihood of actually-played moves at each remaining-clock
  level. Turns a hand-wave into a calibrated model; a data asset maiachess-style tools don't
  exploit.
- The search accommodates this structurally: every node already queries Maia with
  side-specific parameters (rating), so side-specific (clock, TC) is more parameters, not a
  redesign. You-in-time-trouble vs opponent-with-time is asymmetric parameters again.
- Optional refinement: flatter leaf sigmoid (worse conversion) under time pressure.

MVP stays clock-free; this is the first post-MVP extension (the calibration is its own
mini-project).

## Prior art (surveyed 2026-07-05, deep-research)

**Verdict:** the core concept is NOT novel — Maia-human-model + objective-eval expectimax
that plays deliberate swindles is already shipped. But no system found matches the full
planned design; the asymmetric **self+opponent** per-side rating (player's own future moves
self-modelled at the player's ELO as an execution-probability constraint) plus a
rating-calibrated leaf sigmoid appears unclaimed (absence-of-evidence, not proven novel —
this is a fast-moving 2024–2026 area, re-check before any public novelty claim).

**Closest existing systems (both open source — read their code before building):**

- **Polecat** (bradleylovell.com/polecat) — the on-the-nose hit: literally **Maia +
  Stockfish** in a *shallow expectimax tree* whose explicit goal is practical play vs humans
  ("predict their behavior and provoke mistakes"). Beat Stockfish at mating a 1700-Maia
  opponent faster (51.6 vs 53.5 half-moves). Its public page does **not** document asymmetric
  per-side ELO, self-execution probability, or a calibrated sigmoid. *(Unverified lead — this
  claim fell outside the adversarially-verified set; confirm by reading the repo.)*
- **vala-bot** (lichess.org/@/vala-bot) — live Lichess bot: *"Expectimax engine: Patricia 5
  search guided by a Maia-3 opponent model. Objectively sound moves, deliberate swindles when
  the human model says you'll bite."* Uses Patricia (aggressive NNUE alpha-beta), **not**
  Stockfish; no evidence of asymmetric ELO or self-execution. Verified real bot. Proves the
  swindle concept is an explicit, marketed goal elsewhere — so ours is "intentional," not
  novel.

**Adjacent art (each covers one ingredient, none the whole):**

- **Maia-2** (NeurIPS 2024) — already conditions move prediction on **both** active-player
  and opponent skill via skill-aware attention (`Q* = Q + (e_a ⊕ e_o)W`). A ready-made
  component for our asymmetric per-side rating — prefer it over independent per-rating Maia-1
  models. But it does no search and has no practical-score objective.
- **ALLIE** (ICLR 2025) — human-transformer + **time-adaptive MCTS** (search depth ∝ how long
  a human would think), 49-Elo skill gap across 1000–2600. Self-play fidelity, not opponent
  exploitation; no Maia, no Stockfish. The time-adaptive-depth idea is directly relevant to
  our time-pressure extension.
- **Player-specific Maia-2 + MCTS** (arXiv 2605.11893, 2026) — Maia-2 policy as PUCT prior,
  value head as Q. But single-agent stylistic fidelity, no Stockfish, no asymmetry.
- **lc0 WDL contempt** (v0.30.0, 2023) — nearest mainstream "practical vs objective" knob, but
  a **scalar Elo rescale** of the WDL head, not a per-move human model or a search over human
  replies. (Do not cite a `WDLEvalObjectivity` knob — that specific claim was refuted.)
- **Trappy minimax** (Gordon & Vollmer, 2000s) — deliberately plays inferior swindles, but
  defines traps from iterative-deepening *score shape* with **no opponent model**. Our
  Maia-probability-driven trap signal is the stronger version of the same objective.

**Reusable machinery (steal):** eval→win% calibration is well-trodden — Stockfish `WDL_model`
(`win_rate(x)=1/(1+exp(-(x-a)/b))`, material-conditioned) and the lichess sigmoid
(constant `0.00368208`). Novelty rests on the *asymmetric per-side rating*, not on sigmoid
calibration, so lean on these and don't reinvent the curve.

**Critical pitfall (confirmed 3-0):** **MCTS degrades Maia's human-move accuracy** — the KDD
2020 Maia paper does *no* tree search at test time because 10 rollouts cost 5–10pp of
prediction accuracy; the 2026 Maia-2+MCTS paper independently saw move accuracy drop when
MCTS was added. **Nuance that likely saves our design:** that degradation is measured when
MCTS *wraps Maia to produce Maia's own prediction*. We use Maia's **static policy as fixed
expectimax weights** and never re-search to alter its distribution — so the pitfall may not
transfer. But it is a hard warning: never feed search results back to "sharpen" the Maia
prior, and treat compounding Maia probabilities over multi-ply expectimax as its own
distributional-drift risk (reinforces keeping depth shallow).

## Open questions (remaining)

- **Model error compounds with depth** — every Maia probability has estimation error, and
  the recursive value multiplies those errors along a line; simultaneously, deep-tree
  positions look decreasingly like real human-game positions (engine-flavored sequences), so
  Maia drifts out of distribution exactly where errors accumulate. Consequence: keep explicit
  search shallow (6–10 plies), let the leaf sigmoid absorb the rest; don't trust
  impressive-looking depth-16 practical lines.
- **Read Polecat + vala-bot source** before building — sharpens the novelty verdict on our
  one distinctive feature (asymmetric self+opponent rating) and surfaces implementation
  pitfalls for free.
- **Time-pressure conditioning may be a genuinely novel axis** — the survey found no
  published work conditioning *per-move* human prediction on remaining clock (ALLIE
  conditions search *depth* on think-time, not the move distribution). If real, our
  clock→temperature / clock→ELO-offset calibration (see time-pressure section) is a
  defensible novelty hook where "practical-play engine" is not.
- **Leaf calibration granularity** — does the eval→expected-score sigmoid need per-ELO
  empirical outcome tables (benchmark DB) rather than one global curve, and does asymmetry
  need separate player-side vs opponent-side calibration? Deferred with the sigmoid-fitting
  work, but flagged here as a real design fork.

## When to Surface

**Trigger:** a later milestone, **after SEED-081 ships** (this reuses its Maia inference
layer; building it before Maia exists is out of order). Not the next milestone.

## Breadcrumbs

- Depends on SEED-081 (`.planning/seeds/SEED-081-*`) — Maia inference + per-ELO move
  distributions; spikes 004–006 established client-side Maia feasibility.
- Phase 151 (Stockfish-graded Maia moves) builds the per-node primitive (Maia top-k graded
  by Stockfish) this engine composes into a tree.
- Existing Stockfish multipv / PV infra (`app/services/engine.py`, `game_positions.pv`).
- Related: SEED-081 (diagnose ↔ this prescribes), SEED-066 (live engine analysis page).

## Notes

Captured 2026-07-04 from the SEED-081 explore session. Refined 2026-07-05 in a design
discussion that locked: the naming, the expectimax-inside-MCTS algorithm (with custom
Maia-weighted backup), client-side-everything with a single-threaded worker pool, the
lichess eval-to-score formula for MVP, no app-level caching, the anytime/live-refinement
requirement, and the four arrow layers.
