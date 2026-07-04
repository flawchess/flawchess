---
id: SEED-081
status: dormant
planted: 2026-07-04
planted_during: v1.30 closed / planning next milestone
trigger_when: next /gsd-new-milestone (candidate milestone)
scope: medium (browser-only interactive, ~2 phases; aggregate/DB deferred to a separate future milestone)
source: /gsd-explore session 2026-07-04; .planning/research/maia-3-integration.md
---

# SEED-081: Maia-3 human-move enrichment of flaws (per-ELO trap/fix probabilities + practical WDL)

Integrate **Maia-3** (CSSLab "Chessformer", human move-prediction engine) as a second,
human-modeling engine alongside Stockfish. Where Stockfish answers *"what is objectively
best,"* Maia answers *"what would a player at THIS rating actually do here."* That second
question is the missing half of coaching and is directly on-brand: **"Engines are flawless,
humans play FlawChess."**

For each of the user's flaws, one cheap Maia inference at the flaw's decision node — with the
player conditioned on their **rating at game time** (`games.white_rating`/`games.black_rating`,
never the frozen snapshot rating) — yields a **full per-ELO probability curve for every legal
move** (this is Maia's real superpower — the whole rating ladder in a single pass, not a point
estimate) plus a **WDL value**. From that curve we derive:

1. **Trap salience** — `P(blunder move | your ELO)`. How magnetic the mistake is *for you*.
2. **Trainability** — `P(blunder | your ELO) − P(blunder | top ELO)`. How much of the error
   **skill eliminates** (an *endpoint* difference, deliberately NOT a local slope — see the
   coupling/curve-shape note below).
3. **Maia WDL** — the human value-head's practical win/draw/loss for the position, which can
   diverge sharply from the Stockfish eval.

> **Design note — why not `P(fix | ELO)` as a second independent axis (resolved in-session):**
> Maia's per-ELO output is a **softmax over legal moves** (`Σ P(move|ELO)=1`), so `P(blunder)`
> and `P(fix)` are *not independent* — they compete for one probability budget (raise one,
> the other's ceiling drops). A 2×2 on those two axes mis-bins. **And the curve is often
> non-monotonic**: real example — `Ne4` at 1500 sits on the *rising* flank of a hump that
> peaks ~1700–1800 then decays to ~8% at 2600 (mirrored by `O-O` *dipping* exactly where
> `Ne4` peaks — the coupling made visible). A *local* gradient at 1500 reads positive and
> would wrongly file this learnable trap as "objectively hard." The **endpoint** trainability
> metric (your level vs the ceiling) is immune to hump/U/monotone shape and correctly flags
> `Ne4` as a growth-edge trap. Store the whole curve; derive salience + trainability from it.

## Why This Matters

Every engine site annotates individual blunders with objective eval. None of them tell you
*whether a player like you should have found the move*, or *how badly the mistake hurt your
practical chances vs the objective ones*. FlawChess is a **stats platform over the user's
whole history** — that's the unlock: aggregate these per-flaw signals to surface **systematic,
level-relative weaknesses** no objective engine can express.

## The three product pillars (all from the same per-flaw Maia inference)

**Pillar A — salience × trainability quadrant per flaw** (from signals 1 + 2, robust to
non-monotonic curves):

```
                       trainability LOW              trainability HIGH
                       (top tail stays high)         (skill eliminates it)
salience HIGH    objectively hard / maybe not      GROWTH EDGE — drill this
                 a real human blunder → don't      (you're in the danger band;
                 nag                                stronger players grow out of it)
salience LOW     not your problem right now (you rarely err here)
```

Pillar A ships as **two paired surfaces**, verdict + visual:

- **Verbal verdict** — the plain-language quadrant call ("Growth edge — drill this", "Even
  masters fall for this", "You rarely err here"), derived from salience × trainability.
- **"Moves by Rating" chart** — a multi-line chart replicating the Maia screenshot: x = ELO
  (full ladder), y = Maia probability, one line per candidate move, with **the player's ELO
  marked by a vertical reference line** ("you are here") and the **played blunder move** and
  **best move** emphasized. This is what makes the verdict legible — you *see* you're at the
  peak of the hump while masters have grown out of it.
  - **Line cap (locked):** show **top-N moves by peak probability across the ELO range**
    (default N ≈ 6, like the Maia site), **always unioned with the played blunder move and the
    engine-best move** even if they fall outside the top-N. Keeps noisy 15–20-legal-move
    positions legible without ever hiding the two moves the verdict is about.
  - Frontend: Recharts (already in use), colors from `theme.ts`, WDL-consistent styling.
    Computed live from the same single Maia pass, so it's free and needs no persistence.

The verdict is the takeaway; the chart is the evidence. Show both together in the board / flaw
detail.

**Pillar B — practical-severity reweighting** (from signal 3): Maia's human win% reframes how
bad a flaw really is. A Stockfish −1.5 blunder that Maia says players your level still hold
~50% from is *not* the same disaster as one that collapses practical chances. Stockfish eval
stays the objective source of truth; Maia WDL adds a *practical* severity lens.

**Pillar C — aggregate weakness rollup (DEFERRED, DB-GATED — NOT in this seed's scope)**: the
original aspiration was to roll Pillars A + B across the user's whole history via
`apply_game_filters()` to surface systematic gaps — e.g. *"you commit high-trainability traps
2× the Maia baseline for your level."* **This is out of scope here.** It is *impossible*
without persisting Maia signals (you cannot aggregate values that only existed live in a
browser session), which directly conflicts with the "nothing Maia-related in the DB" rule
below. Pillar C therefore requires a **separate future decision** to persist Maia data
(schema + flaw-node backfill) — worth revisiting only *after* the browser feature proves
Maia's calibration is trustworthy enough to aggregate on. Parked, not deleted.

## Architecture decision — locked in the explore session

**Browser-only. Nothing Maia-related is stored in the DB in this seed's scope.**

- **What we build:** run Maia live in the **analysis board** only, computing Pillars **A** and
  **B** **for the position currently on the board / the flaw being viewed**. The per-ELO curve,
  the salience×trainability quadrant, and the WDL practical-severity lens are all derived on
  demand and rendered in the board / flaw detail. **No DB writes.**
- **Inference location — TBD by SPIKE-001 (see below).** Preferred: **client-side** (in-browser
  ONNX/WASM, like the existing client-side Stockfish, SEED-012) — zero server load, but needs a
  Chessformer→ONNX export path (unproven) and a resolved AGPL-in-MIT-frontend license question.
  Fallback: a **synchronous backend inference endpoint** (PyTorch runs as-is, clean arm's-length
  AGPL). **Not the remote worker fleet** — that's pull-based batch infra for *precompute*, unfit
  for interactive latency; reusing it would force the parked precompute-every-flaw + DB path.
- **Cache is EPHEMERAL and board-session-scoped only.** No persistence of any kind. Rationale
  (locked): (a) cross-user hit rate outside opening theory is low — positions are too diverse
  to make a persistent hash cache pay off; (b) we will be **experimenting with different Maia
  model sizes** (5M/23M/79M), so any persisted artifact keyed to a not-yet-chosen model is a
  migration liability. Also acts as the **quality gate**: validate Maia's calibration by
  eyeballing real positions live *before* anyone considers persisting it.
- **Aggregate stats (Pillar C) are explicitly NOT built here** — see Pillar C above. They would
  require persisting Maia signals, which is a separate future decision, deliberately outside
  this seed.

**If Pillar C is ever pursued (separate future milestone):** it would need a flaw-node backfill
(one Maia forward pass per `game_flaws` decision node — flaws are a *small subset* of positions,
so far lighter than the Stockfish eval backfill) plus schema to store the per-ELO curve +
derived signals. Maia policy is a single **deterministic** forward pass (raw policy vector, not
a sampled move — no cross-machine non-determinism to design around), so such a backfill would be
low-risk *if* the persist decision is made. That decision is not made here.

## Legal / integration constraint (non-negotiable)

Maia-3 code **and** weights are **AGPL-3.0** (verified against the repo `LICENSE`; the
"Apache 2.0" claim in secondary press is wrong — see report). FlawChess is **MIT**. Integrate
**at arm's length**: run Maia as a **separate, unmodified UCI process / inference service** —
identical governance to how we already run GPL-3.0 Stockfish via `python-chess`. **Never
`import` the `maia3` package in-process into the FastAPI backend** (that makes the served
backend a combined work and AGPL §13 would force the whole backend to AGPL). Keep it
unmodified (any fine-tune triggers §13 publish-source obligations). Attribute + cite the
Chessformer paper. Full analysis: `.planning/research/maia-3-integration.md`.

## Suggested phase shape (for /gsd-new-milestone to refine)

Browser-only. No DB writes. ~2 phases.

1. **Maia serving + interactive board** — arm's-length Maia UCI/inference service (start 5M or
   23M on CPU), analysis-board integration showing the per-ELO move-probability curve + Maia
   WDL for the current position, ephemeral session cache, attribution. Ships standalone value;
   validates quality.
2. **Live per-position Pillars A + B** — compute the salience×trainability quadrant and the WDL
   practical-severity lens **live** for the position on the board / the flaw being viewed.
   Render the paired **verbal verdict + "Moves by Rating" chart** (Recharts, per-move
   probability lines over ELO, player's-ELO marker, blunder/best emphasized) plus the WDL
   severity lens in the board and flaw detail. Still no persistence.

**Out of scope (separate future milestone, DB-gated):** Pillar C aggregate weakness rollup,
`game_flaws` schema, flaw-node backfill, history-wide stats/LLM narration. Only revisit after
Phase 1–2 prove Maia quality is trustworthy enough to justify persisting.

## Open feasibility questions (must resolve before/early in the milestone)

Tracked in `.planning/research/questions.md` (Q-013…Q-016): per-move probability extraction
from Maia's policy head at arbitrary positions/ELOs; Maia-WDL ↔ Stockfish-eval comparability;
Maia-3 ELO range & low-rating calibration + whether the value head is ELO-conditioned;
model-size vs latency/accuracy tradeoff for the interactive board and the eventual backfill
cost. A `/gsd-spike` against the real `maia3` API is the natural way to close Q-013/Q-014
before committing.

## When to Surface

**Trigger:** next `/gsd-new-milestone`. No hard code prerequisite. Being browser-only it does
**not** touch `game_flaws` or the eval/worker write path, so it's largely independent of the
in-flight pipeline work (Phase 149 retire/prune, SEED-080 consolidation) — the main shared
concern is worker CPU/RAM headroom for the Maia inference service (see memory
`project_prod_oom_cause_and_stockfish_capacity`).

## Breadcrumbs

- `.planning/research/maia-3-integration.md` — license + technical integration report
  (AGPL arm's-length pattern, PyTorch/UCI, 5M/23M/79M, WDL value head)
- Maia-3: https://github.com/CSSLab/maia3 · weights https://huggingface.co/UofTCSSLab
- Existing grain to reuse: `game_flaws` (both players' flaws, per ply — memory
  `game_flaws_both_players_scope`), rating-at-game-time basis (memory
  `eval_completion_columns` / benchmark rating-lag note), `apply_game_filters()`,
  Stockfish-as-separate-UCI precedent, LLM insight infra.
- Related seeds: SEED-037 (spaced-repetition blunder drills — Pillar A quadrant is a natural
  drill-selection signal), SEED-012/066 (client-side / live engine analysis — Maia could ride
  the same board surface).

## Notes

Captured 2026-07-04 from a `/gsd-explore` session. Design model (three signals, quadrant,
aggregate-leads layering, practical-severity, interactive-first + ephemeral cache,
arm's-length AGPL) was decided interactively with the user and is locked above.
