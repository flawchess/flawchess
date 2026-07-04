---
id: SEED-081
status: dormant
planted: 2026-07-04
planted_during: v1.30 closed / planning next milestone
trigger_when: next /gsd-new-milestone (candidate milestone)
scope: medium (browser-only interactive, ~2 phases; aggregate/DB deferred to a separate future milestone)
source: /gsd-explore session 2026-07-04; spikes 004-006; .planning/research/maia-3-integration.md
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

The verdict is the takeaway; the chart is the evidence.

> **Scope — chart everywhere, verdict on flaws (locked).** The **"Moves by Rating" chart is
> shown for _every_ position** on the analysis board (Maia gives a move distribution for any
> position — it's a general exploration/scouting tool: "how do players at each level handle
> this?", with the game move vs Maia's top move highlighted). The **Pillar A verdict banner**
> (salience × trainability) is an **overlay that only appears when the current move is a flaw**
> — it needs a played-blunder + a best move to classify. So: chart = always; verdict = flaws.

**Pillar B — practical-severity reweighting + Maia eval bar** (from signal 3): Maia's human
win% reframes how bad a flaw really is — a Stockfish −1.5 blunder that Maia says players your
level still hold ~50% from is *not* the same disaster as one that collapses practical chances.
Stockfish eval stays the objective source of truth; Maia WDL adds a *practical* severity lens.
Surface it as a **Maia WDL eval bar on the LEFT of the chessboard**, with the **Stockfish eval
bar on the RIGHT — both shown simultaneously** for **all positions** (not just flaws). The two
bars frame the product thesis on either side of the board: **left = human-practical (Maia WDL),
right = engine-objective (Stockfish)**. "Engines are flawless, humans play FlawChess."

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

- **What we build:** run Maia live in the **analysis board**, re-inferring on every board
  navigation. **For all positions:** render the "Moves by Rating" chart + a Maia WDL eval bar
  on the left of the board. **On flaw moves only:** overlay the salience×trainability verdict
  and the practical-severity reframe. All derived on demand, in-memory. **No DB writes.**
- **Inference location — RESOLVED by spikes 004–006: client-side (in-browser).** Maia-3 runs in
  the browser via **onnxruntime-web** (WASM/WebGPU) — this is the model authors' own shipped
  architecture (maiachess.com), a public **`maia3_simplified.onnx`** already exists, and we
  already ship client-side Stockfish (SEED-012). Zero server load. **Fallback** (only if the
  license nod fails): a **synchronous backend inference endpoint** (PyTorch as-is, arm's-length).
  **Never the remote worker fleet** — it's pull-based batch infra for *precompute*, unfit for
  interactive latency; reusing it would force the parked precompute-every-flaw + DB path.
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
"Apache 2.0" claim in secondary press is wrong — see report). FlawChess is **MIT**. Spike 005
resolved how to stay MIT for the **chosen client-side** path — four conditions:

1. Load the **unmodified** `maia3_simplified.onnx` as a **runtime data asset** via **MIT
   onnxruntime-web** (loading a model *file* through a permissive runtime = data/aggregation,
   not linking AGPL code).
2. **Write our own MIT glue** (board encoding, ELO input, legal-move masking, softmax, chart).
   **Never copy/bundle CSSLab's AGPL inference/encoding JS** — that would combine AGPL *source*
   into the MIT frontend and force it to AGPL.
3. Ship an **attribution + offer-source notice** (link CSSLab repo + AGPL text + the model) and
   cite the Chessformer paper.
4. Keep the model **unmodified** (any fine-tune → §13 publish-source; treat a fork as its own
   AGPL project). Note §13's network clause is largely inert client-side (user runs it locally,
   unmodified).

**On the "legal nod" (low stakes — don't over-worry it).** Condition 1's "model-as-data ≠
linking" reading is untested, but for a **free, already-open-source** project the practical
risk is small: the worst case isn't liability, it's "the Maia-touching frontend is effectively
AGPL for anyone *redistributing our code*" — and FlawChess's source is public anyway, and
CSSLab distributes Maia precisely for tools like this. No formal lawyer is needed; it's a
**license-posture choice**, made at build time. Three ways to make it a non-issue (pick one):

- **(a) Relicense FlawChess to AGPL-3.0 — recommended, cleanest.** Zero ambiguity (AGPL-in-AGPL
  is fine); it's exactly what lichess and Maia themselves use. Only downside: more restrictive
  for third parties reusing *our* code — which barely matters for a hosted product whose value
  is the service, not a library.
- **(b) Keep MIT, ship under the reasonable interpretation** + the offer-source notice
  (conditions 1–4). Worst case is a licensing-purity nuance for redistributors, not a liability
  event.
- **(c) Server-side arm's-length** — sidestep entirely: run Maia as a **separate, unmodified
  process** (like our GPL Stockfish via `python-chess`); never `import maia3` in-process. Costs
  server CPU/RAM + a round-trip; only worth it to keep MIT pristine.

Not a blocker — decide (a)/(b)/(c) when the milestone starts. Full analysis: spike 005 +
`.planning/research/maia-3-integration.md`.

## Suggested phase shape (for /gsd-new-milestone to refine)

Browser-only, client-side inference. No DB writes. ~2 phases.

1. **Maia in the browser + all-positions surfaces** — load `maia3_simplified.onnx` (smallest
   Maia-3) via **onnxruntime-web** in a Web Worker, lazy-loaded only when the analysis board
   opens (never in the initial bundle); our own MIT glue for board→tensor encoding, ELO input,
   legal-move masking, softmax; ephemeral session cache; attribution notice. Re-run on every
   board navigation and surface, **for every position**: the **"Moves by Rating" chart**
   (Recharts — per-move probability lines over ELO, player's-ELO `ReferenceLine` marker, game
   move vs Maia-top emphasized, top-N-by-peak ∪ {game move, best} cap) and a **Maia WDL eval
   bar on the left of the board**. Chart shape/cap already prototyped — spike 006. Ships
   standalone value; validates Maia quality live across all positions.
2. **Flaw overlay — Pillars A + B verdict** — when the current move **is a flaw**, overlay the
   salience×trainability **verdict banner** (Growth edge / Even masters fall for this / lapse /
   above your level) on the chart, and apply the WDL **practical-severity** reframe to the flaw.
   The chart + eval bar from Phase 1 are already there for all positions; this phase adds the
   flaw-specific *interpretation* on top. Still no persistence.

**Out of scope (separate future milestone, DB-gated):** Pillar C aggregate weakness rollup,
`game_flaws` schema, flaw-node backfill, history-wide stats/LLM narration. Only revisit after
Phase 1–2 prove Maia quality is trustworthy enough to justify persisting.

## Spike findings (spikes 004–006, 2026-07-04 — `.planning/spikes/`)

Feasibility is settled; the milestone starts de-risked.

- **004 VALIDATED — client-side Maia-3 works.** maiachess.com runs Maia in-browser via
  onnxruntime-web (WASM/WebGPU); a public **`maia3_simplified.onnx`** already exists (no need to
  export Chessformer ourselves). Rating-conditioned output gives exactly the per-ELO curve. The
  arch (encoder transformer + GAB + 64×64 attention policy head + mean-pooled WDL head) exports
  cleanly (the ONNX exists). Biggest technical unknown removed.
- **005 PARTIAL — license viable, needs a nod.** Client-side AGPL bundling is not a kill; it's
  shippable under the 4 conditions in the Legal section, resting on the untested
  "model-as-data ≠ linking" reading → get a one-paragraph legal confirmation. Server-side
  arm's-length is the safe-harbor fallback.
- **006 VALIDATED — the chart reproduces.** Prototype (`.planning/spikes/006-.../index.html`)
  renders the Ne4 hump + O-O mirror, the you-are-here marker, the top-N-by-peak ∪ {blunder,best}
  cap, and the verdict+chart pairing. Production port to Recharts (already a dep) is mechanical.

**Remaining hands-on items (do first in Phase 1, could not be done in-sandbox):**
1. Obtain `maia3_simplified.onnx` (locate in maia-platform-frontend / its CDN); confirm exact
   **input encoding** (board planes + how ELO is fed) and **output tensor layout** (policy
   64×64 vs flat; WDL order).
2. Measure **download size** + **per-position latency** (WASM vs WebGPU, desktop **and phone** —
   PWA is mobile-first) and the cost of an ELO **sweep** for the full curve vs a single batched
   call. Pick the model size accordingly.
3. Confirm onnxruntime-web loads it with no unsupported-op errors.

## Open feasibility questions (largely closed by the spikes)

Tracked in `.planning/research/questions.md` (Q-013…Q-016). Status after spikes 004–006:
**Q-013** (per-move probability extraction) — *mechanism confirmed* (the ONNX policy head gives
it); remaining = the tensor-I/O contract in hands-on item 1. **Q-016** (model-size vs
latency) — *narrowed* to hands-on item 2 (start smallest). **Q-014** (Maia-WDL ↔ Stockfish
comparability) and **Q-015** (ELO range / low-rating calibration / is the value head
ELO-conditioned) — *still open*, best answered by eyeballing live output in Phase 1 (the
quality gate), not desk research.

## When to Surface

**Trigger:** next `/gsd-new-milestone`. No hard code prerequisite. Being browser-only with
**client-side** inference it does **not** touch `game_flaws`, the eval/worker write path, or
prod server CPU/RAM at all — fully independent of the in-flight pipeline work (Phase 149
retire/prune, SEED-080 consolidation). The real constraints are client-side: **model download
size** and **in-browser latency on mobile** (PWA is mobile-first). The only non-code decision
is a **license posture** (relicense to AGPL / keep MIT under the reasonable reading / server-side
arm's-length — see Legal section) — low-stakes for a free OSS project, decided at build time.

## Breadcrumbs

- **Spikes 004–006** (`.planning/spikes/`, MANIFEST.md) — client-side feasibility VALIDATED,
  license PARTIAL/conditional, chart prototype (`006-moves-by-rating-chart/index.html`).
- `.planning/research/maia-3-integration.md` — license + technical integration report
  (AGPL, PyTorch/UCI, 5M/23M/79M, WDL value head)
- Maia-3: https://github.com/CSSLab/maia3 · weights https://huggingface.co/UofTCSSLab
- **Reference client impl** (authors run Maia in-browser via onnxruntime-web):
  https://github.com/CSSLab/maia-platform-frontend — source the `maia3_simplified.onnx` +
  its board/ELO encoding here.
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
