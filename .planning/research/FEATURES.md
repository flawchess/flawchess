# Feature Research: FlawChess Engine (v2.0)

**Domain:** Practical-play / opponent-modeling chess analysis engine (client-side, built on Stockfish + Maia)
**Researched:** 2026-07-05
**Confidence:** MEDIUM-HIGH (prior-art source code read directly; UI conventions verified against this codebase; some Polecat internals inferred from partial file fetches)

## 0. Prior Art: Source Read (Polecat + vala-bot)

The seed (SEED-082) requires reading the actual source of the two closest systems before building, not just their marketing pages. Both were fetched and read directly.

### Polecat — github.com/subcreation-studio/Polecat (bradleylovell.com/polecat)

Read: `expectimax.py`, `expectimaxtree.py` (tree node/expansion logic), `maia_player_model.py`, `config.py`, `README.md`, plus the project page.

**Confirmed from source:**
- **Algorithm:** genuine expectimax (not MCTS), with several alternate search modes present in the repo (`stochastic_uct.py`, `fixed_stoch_uct.py`, `aggro_fixed_stoch_uct.py`) but the shipped default is `expectimax.py`. Node expansion (`expectimaxtree.py`) prunes children below a `position_probability_cutoff` — a fixed-width, probability-gated expansion, not a node-budget-driven MCTS allocator.
- **Expected-value recursion:** at opponent-to-move nodes it's a textbook weighted sum — `expected_value += child.local_probability * expectiminimax(child, depth-1, ...)` — structurally identical to what SEED-082 designs, confirming the core recursive shape is not novel.
- **Leaf conversion:** `heuristic = (evaluation + 1.0) / 2.0` — a linear remap of a `[-1, 1]` engine evaluation to `[0, 1]`, **not a calibrated sigmoid**. This is materially cruder than the lichess eval→win% sigmoid SEED-082 plans for MVP1 — a real, confirmed differentiation point, not just an assumption.
- **Rating handling:** **no ELO parameter in the search code at all.** `config.py` hardcodes a single opponent-matched Maia weights file (e.g. `maia-1700.pb.gz`) selected by the user editing the config before running — a fixed, single-sided skill model. Polecat's own (engine) side plays via the strong evaluator (Leela weights / Stockfish), unconstrained by any rating. **No asymmetric self-rating, no self-execution-probability modeling** — confirms the seed's read.
- **Search depth:** "shallow" is qualitative in the README; no explicit ply/node budget documented in the fetched files. Not a live analysis tool — it's an offline experiment harness (`trial.py`, `show_example_game.py`) that plays full games against a Maia opponent model and reports summary stats (51.6 vs 53.5 half-moves to mate vs a 1700-Maia), not a per-position UI.
- **Endgame behavior:** explicitly defers to Stockfish once it reaches "overwhelming advantage" — an engineering shortcut Polecat needed (it has no dedicated conversion phase of its own), not directly relevant to an analysis tool.

**Confidence:** MEDIUM — read via WebFetch against raw GitHub source files (not cached training data), cross-checked across 4 files + README + project page; some files (e.g. exact depth constant) were only partially retrievable through the fetch tool's summarization, so treat "no depth budget found" as absence-of-evidence in what was retrievable, not proof none exists.

### vala-bot — github.com/Avo-k/vala (bot: lichess.org/@/vala-bot)

Read: `README.md`, `search.py` (core EV logic), lichess bot profile page.

**Confirmed from source:**
- **Algorithm:** level-synchronous expectimax, explicitly **not MCTS**. Two-stage pipeline: a cheap depth-1 "trigger screen" (~0.3s) flags positions with exploitation upside, then a full expectimax only runs on flagged positions (~1–1.6s via a parallel `PatriciaPool` of engine subprocesses). This lazy/gated-search structure is a genuinely different engineering approach from SEED-082's always-on MCTS and is worth stealing as a perf idea even though the core algorithm differs.
- **Engine backbone:** **Patricia 5** (an aggressive NNUE alpha-beta engine), not Stockfish. Supplies MultiPV candidates and leaf centipawns.
- **Opponent model:** Maia-3 / "Chessformer" (PyTorch) supplies `P(reply | position, elo)` at interior nodes; **shallow nodes use the Lichess Opening Explorer API** (real human reply frequencies, rated-filtered) instead of Maia — realizing an idea attributed to Thomas Ahle's "chess-openings-expectimax" concept. This opening-book-as-cheap-oracle idea is a genuinely useful implementation shortcut not in SEED-082's design.
- **ELO handling:** exactly one rating knob — `human_elo` (a UCI option, 600–2600, or 0 to auto-track the opponent's live Lichess rating) — feeds Maia's *reply* distribution only. **Vala's own moves are selected via `pool.map_best_move()` at full engine strength, with no ELO constraint on its own future play.** This is the single most load-bearing finding for the novelty question: **neither closest system models its own future execution probability at its own rating.** SEED-082's asymmetric self+opponent design (querying Maia at the *player's own* ELO for the player's own future nodes, not just the opponent's) is corroborated as unclaimed by both systems actually read.
- **Leaf conversion:** EV is computed directly on the **centipawn scale** (`_to_root_pov()` just flips sign by side to move) — no win% sigmoid at all in the core loop. Confirms SEED-082's lichess-sigmoid leaf conversion is a genuine (if modest) refinement over both prior systems, neither of which calibrates eval→expected-score.
- **Risk dials:** `risk_cp` (max objective concession allowed) and `margin_cp` (minimum EV uplift required to deviate from engine-best) are explicit, tunable, user-facing knobs — this is the cleanest existing example of "how do you decide whether to play a swindle" and directly informs how FlawChess should frame the objective-vs-practical score pair (i.e., always show the concession size, not just the two scores in isolation).
- **UCI-line output convention:** per-move info tags candidates as `solid` / `trig` / `BAIT` / `mate`, alongside eval-loss (cp) and EV swing (before→after). This is a good precedent for the FlawChess "why this is the practical pick" copy — swindle-worthy lines should always disclose the cp they cost.
- **Status:** actively developed bot (2,263 blitz games as of research date), not a static research artifact — the closest thing to a live production analog of what SEED-082 builds, even though it's a *player* not an *analysis tool*.

**Confidence:** MEDIUM — same caveats as Polecat (WebFetch summarization of raw source, not a full manual read of every file); the ELO-asymmetry finding is corroborated independently across the README EV formula, the search.py fetch, and the UCI-option description, so treat that specific finding as higher confidence than the rest.

### Novelty verdict (both systems read)

**Confirmed, not just asserted from the seed:** the core concept — Maia opponent model + engine eval in an expectimax search that deliberately plays engine-suboptimal "trap" moves — is shipped twice already (Polecat as an offline research harness, vala-bot as a live Lichess bot). FlawChess Engine is **not** a novel algorithm class and copy must never claim otherwise.

**What genuinely differs, confirmed by source (not assumption):**
1. **Asymmetric self-rating.** Neither Polecat nor vala models the *player's own* future moves through Maia at the *player's own* ELO. Both play their own side at full engine strength. SEED-082's design — querying Maia at your ELO for your future nodes, opponent ELO for opponent nodes — is the one substantive unclaimed hook, now corroborated by two independent source reads instead of one prior-art survey.
2. **Calibrated leaf conversion.** Polecat uses a linear `(eval+1)/2` remap; vala uses raw centipawns. Neither calibrates eval→expected-score. SEED-082's lichess sigmoid (and its deferred per-ELO-bucket upgrade) is a real, if modest, improvement.
3. **It's an analysis tool, not an opponent bot.** Both prior systems *play* games against humans. FlawChess Engine *analyzes* a position/game for a human to study — output is a displayed line + score pair on a board UI, never an autonomous move. This reframes the "not novel" concern: the correct positioning is "practical-play **analysis**," a use case neither prior system addresses at all (confirms seed framing).
4. **MCTS-in-expectimax-clothing vs textbook expectimax.** Both prior systems are textbook depth-limited expectimax (Polecat) or level-synchronous two-stage expectimax (vala). SEED-082's MCTS-with-custom-backup is a different search-allocation strategy justified by the node-budget economics of a client-side WASM engine (Stockfish eval costs 50–300ms in-browser vs a native engine's microseconds) — a legitimately different engineering constraint, not a claimed algorithmic novelty.

**Caution:** this is a fast-moving 2024–2026 research area (Maia-2, ALLIE, player-specific Maia-2+MCTS all postdate Polecat). Do not state "asymmetric self-rating is novel" in any public-facing copy without re-checking immediately before ship; treat it internally as "unclaimed by the two closest systems as of 2026-07," not "provably first."

**Sources:**
- [Polecat project page](https://bradleylovell.com/polecat)
- [Polecat repo](https://github.com/subcreation-studio/Polecat)
- [Polecat expectimax.py](https://raw.githubusercontent.com/subcreation-studio/Polecat/main/expectimax.py)
- [Polecat expectimaxtree.py](https://raw.githubusercontent.com/subcreation-studio/Polecat/main/expectimaxtree.py)
- [Polecat maia_player_model.py](https://raw.githubusercontent.com/subcreation-studio/Polecat/main/maia_player_model.py)
- [Polecat config.py](https://raw.githubusercontent.com/subcreation-studio/Polecat/main/config.py)
- [vala-bot lichess profile](https://lichess.org/@/vala-bot)
- [vala repo](https://github.com/Avo-k/vala)
- [vala README](https://raw.githubusercontent.com/Avo-k/vala/main/README.md)
- [vala search.py](https://raw.githubusercontent.com/Avo-k/vala/main/vala/search.py)
- [Patricia engine](https://github.com/Adam-Kulju/Patricia)
- [Maia Chess](https://github.com/CSSLab/maia-chess)

## Feature Landscape

### Table Stakes (Users Expect These)

For an *analysis* surface layering a new engine mode onto an existing eval-bar/arrow board (the FlawChess `/analysis` page already ships Stockfish + Maia), these are the baseline expectations a practical-play mode must clear or it reads as broken/incomplete rather than novel.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Displayed practical line (modal path) on the board | Every engine line tool (lichess/chess.com analysis) shows *a line*, not just a score; a bare number with no moves is not "analysis" | MEDIUM | Reuse existing PV-arrow + move-list rendering patterns already in `useAnalysisBoard.ts` |
| Live/anytime refinement (line updates as it "thinks") | Both Stockfish and Maia already refine live on this exact page (`useStockfishEngine`, MultiPV 2, 1500ms/2M-node budget); a new mode that freezes or spinners would regress the page's established feel | MEDIUM | MCTS is anytime-native per SEED-082; the worker pool needs a node-eval priority queue favoring current-best root lines |
| Board arrows matching the existing visual language | Page already has Stockfish top-2, tactic, and next-move arrow layers with distinct theme.ts colors; a fourth layer must slot into that system, not invent a new one | LOW | `theme.ts` constants (`BEST_MOVE_ARROW`, `SECOND_BEST_ARROW` precedent) — add `FLAWCHESS_ENGINE_ARROW` + `_SECOND` following the same naming/opacity convention |
| Toggle to show/hide the layer | Every existing arrow layer on this page is user-toggleable (Stockfish, tactic, next-move); an engine layer that can't be hidden breaks the established interaction model | LOW | Follows existing toggle pattern already in `Analysis.tsx` |
| Objective score alongside the practical score | Stockfish's eval bar already anchors "how good is this position, objectively" on this exact page; removing that reference point while adding a practical score would be confusing, not additive | LOW | Score **pair**, not replacement — "objectively +3.0, practically +0.9 for you" per seed |
| Works in both free analysis AND game review | Milestone scope explicitly requires both surfaces; Stockfish/Maia already work on both | MEDIUM | Game review adds the played-move arrow (existing) for the "what you played vs what was practically best" comparison loop |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Objective-vs-practical score pair with plain-language "why" | No competitor (lichess, chess.com, maiachess.com, Polecat, vala-bot) shows this pair for a human student; it's the single clearest "aha" of the whole milestone | MEDIUM | Copy must always attribute the gap ("...because 14...Rd7!! is only found by 8% at your level") — never a bare number pair |
| Swindle/trap ranking that "falls out for free" | The search's own math surfaces a line where an inferior-by-Stockfish move is objectively worse but practically better because the likely human reply loses; competitors (vala-bot) treat this as their headline feature for *play*, nobody surfaces it as *pedagogy* | LOW (given MVP1 search) | No dedicated trap-finder UI needed for MVP1 — it emerges automatically as "practically best" outranking "objectively best" in the modal line; defer dedicated UI (branch-point display) to Ambitious tier per seed |
| "What you played vs what was practically best for you" game-review loop | Existing Played-move arrow already does the "what you played" half; pairing it with the new FlawChess-Engine arrow's "what a player at your level should realistically try" closes a loop no competitor offers (Stockfish-only game review shows "what was objectively best," which is often unfindable and demoralizing) | LOW (composition of two existing pieces) | This is the differentiator that actually uses BOTH new and existing infra — highest leverage-per-line-of-code item in the milestone |
| Asymmetric self+opponent rating (if shipped, even undisclosed as "novel") | Confirmed unclaimed by both prior-art systems (see §0); makes "practically best FOR YOU" literal rather than aspirational — a 1400 and a 2000 get genuinely different modal lines for the same position even against the same opponent | HIGH | This is the SEED-082 "locked" design, not optional — but do not market it as "novel," market the *analysis-tool* framing instead |
| Live-refining top-n root lines (anytime search) | lichess/chess.com show a static best line that either completes or doesn't; MCTS's adaptive allocation means the practical line visibly sharpens in real time, matching the page's existing Stockfish live-refine feel | MEDIUM | Already an established UX pattern on this exact page (Stockfish MultiPV) — extending it, not inventing it |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Dedicated trap-finder / branch-point UI in MVP1 | "Show me all the traps in this position" feels like the natural companion to the swindle-ranking insight | Real scope: needs its own interaction design (how do you present *multiple* opponent-reply branches without cluttering one board?), plus its own testing/UAT surface. Explicitly deferred in the seed's "Ambitious" tier | Ship MVP1 with the modal line only; the swindle behavior is still visible (an inferior-by-Stockfish move ranked #1 practically *is* the trap-finder, just without dedicated branch UI) |
| Per-ELO leaf sigmoids fit from the benchmark DB | "The lichess sigmoid is rating-agnostic past the search horizon — surely per-ELO curves are more accurate" | Real, but it's an isolated, clean swap behind the same leaf-eval interface — no reason to block MVP1 ship on a benchmark-DB fitting exercise that has its own research/validation cost | Ship the lichess sigmoid for MVP1 (seed already scopes this as a deferred, isolated upgrade) |
| Time-pressure conditioning (clock→temperature / clock→ELO-offset) | Natural next question once you see "practical for you" — surely it should also account for "practical for you with 10 seconds left" | Maia is out-of-distribution for low-clock moves by construction (training data filtered these); doing this right needs its own clock→parameter calibration project against the benchmark DB, not a quick bolt-on | MVP stays clock-free per seed; flagged as the first post-MVP extension, potentially the most defensible "genuinely novel" axis (no published work found conditioning per-move human prediction on remaining clock) |
| SharedArrayBuffer multithreaded Stockfish for deeper root grading | "More threads = faster = better" is the default performance instinct | Requires COOP/COEP cross-origin isolation; COOP `same-origin` severs `window.opener`, breaking the existing Google OAuth popup flow. Fixable but it's a site-wide deployment decision, not an engine feature, and only helps *root* multi-PV grading, not the many-shallow-leaves workload this search actually does | Pool of 2-4 single-threaded workers (already the seed's locked architecture) — near-linear speedup for the actual (many independent shallow evals) workload with zero deployment blast radius |
| Feeding search results back to "sharpen" Maia's prior mid-search | Seems like free accuracy — "if the search found a good line, shouldn't Maia learn from it?" | This is the confirmed pitfall from both the KDD 2020 Maia paper and the 2026 Maia-2+MCTS paper: wrapping Maia in search to refine Maia's *own* output measurably degrades its human-move-prediction accuracy (5-10pp) | Use Maia's static single-forward-pass policy as fixed expectimax weights, always; never re-query Maia with search-adjusted context |
| Deep explicit search (15+ plies) to show "impressive" long practical lines | More depth looks more thorough/impressive in a demo | Maia's probability estimation error compounds multiplicatively along the line, and deep positions look increasingly engine-flavored (out of the human-game distribution Maia was trained on) — a depth-16 "practical" line is more likely to be a compounded-error artifact than a real insight | Keep explicit search shallow (6-10 plies per seed), let the calibrated leaf sigmoid absorb everything beyond the horizon |
| App-level Zobrist/transposition caching for the practical-play search | FlawChess's entire identity is Zobrist-hash position matching — reusing that infra here feels natural | Positions diverge too fast under this search's branching (opponent-reply fan-out at every ply) for a transposition table to pay off; stockfish.wasm's own internal TT already gives partial reuse for free | Skip app-level caching entirely (seed already locked this decision) |
| Server-side / hybrid search loop | Could offload heavy compute from mobile devices | Client-server round-trip per node evaluation is latency-miserable for an anytime, live-refining UX; also breaks the milestone's "zero server load, no persistence" architecture and the URL-only analysis-state pattern (v1.29 D-4) | Client-side only: browser Maia inference + stockfish.wasm pool, exactly as locked |

## Feature Dependencies

```
Phase 151 primitive (Maia top-k graded by Stockfish, root only)
    └──requires──> MCTS search loop w/ custom Maia-weighted backup  [MVP1 core]
                       └──requires──> Modal-path line display + score pair  [MVP1 core]
                                          └──requires──> FlawChess-Engine arrow layer (top-2)  [MVP1 core]

Live in-browser Stockfish (v1.29, shipped) ──enhances──> Worker-pool leaf grading (2-4 threads)
Client-side Maia inference (SEED-081, v1.32, undeployed) ──requires──> asymmetric self+opponent ELO querying

Played-move arrow (existing, game review only) ──enhances──> "what you played vs practically best" loop
Moves-by-Rating chart hover (existing) ──substitutes-for──> dedicated Maia arrow layer (seed explicitly drops this 4th layer)

Trap-finder / branch-point UI [Ambitious] ──requires──> Modal-path line display + score pair  [MVP1 core]
Per-ELO leaf sigmoids [Ambitious] ──requires──> benchmark DB eval+outcome data (already exists, v1.12+)
Time-pressure conditioning [Ambitious] ──requires──> clock→ELO-offset / clock→temperature calibration (own mini-project)
SAB multithreading [Ambitious] ──conflicts──> existing Google OAuth popup flow (COOP same-origin severs window.opener)
```

### Dependency Notes

- **MCTS search requires the Phase 151 primitive:** the per-node "Maia top-k graded by Stockfish" step is the atomic unit MCTS expands at every node — it must exist and be stable before the tree/backup logic can be built on top.
- **Modal-path display requires the search to exist:** there is nothing to render until at least one full expectimax-in-MCTS pass produces a ranked line; UI work cannot meaningfully start in parallel with the search's core algorithm, though arrow *plumbing* (adding a 4th layer slot) can.
- **The Played-move arrow enhances but does not gate the new arrow layer:** it already exists (game review only) and simply gains a new pedagogical partner; no new dependency to build.
- **The Moves-by-Rating chart substitutes for a dedicated Maia arrow layer:** this is a locked scope-reduction (seed explicitly says "no dedicated Maia arrow layer... Maia moves stay reachable by hovering the chart"), not a technical dependency — flagging it here so the roadmap doesn't accidentally re-add a 4th arrow layer as "obviously needed."
- **SAB multithreading conflicts with the existing OAuth flow:** any phase considering this must either scope Google-login isolation changes into the same phase or explicitly exclude SAB from that phase's scope — this is a genuine architectural conflict, not just added complexity.
- **Per-ELO leaf sigmoids and time-pressure conditioning both depend on the benchmark DB**, which is a stable, already-shipped asset (v1.12+) — these are lower-risk "Ambitious" items specifically because their data dependency is already satisfied; they're deferred for scope reasons, not readiness reasons.

## MVP Definition

### Launch With (v1 = MVP1, per seed's phasing)

Minimum viable product — what's needed to validate the concept works and reads as a coherent feature, not a research toy.

- [ ] MCTS search with custom Maia-weighted backup (opponent ELO at opponent nodes, your ELO at your future nodes, max at root) over the Phase 151 primitive — the algorithmic core; without it there's no engine, just the existing Phase 151 one-ply grading
- [ ] Stockfish.wasm worker pool (2-4 single-threaded instances) grading leaves in parallel — required for the search to complete in a usable wall-clock time in-browser
- [ ] Lichess eval→win% sigmoid at leaves (depth 6-10 plies) — the minimum viable leaf calibration; a raw-cp or linear remap (both prior systems' approach) would visibly under-perform on the exact "practical score" number this feature is built to show
- [ ] Modal-path line display with objective-vs-practical score pair — this IS the feature; without the pair, there is nothing differentiating this from the existing Stockfish eval bar
- [ ] Live-refining top-n root lines (anytime emission as MCTS visits accumulate) — matches the established page feel (Stockfish already live-refines here); a static "wait then show" result would be a UX regression from the existing bar
- [ ] FlawChess Engine top-2 board arrow layer, toggleable, distinct theme color — the headline visual deliverable per the milestone description
- [ ] Works on both free analysis and game review surfaces — explicit milestone scope, not optional
- [ ] Game review: played-move arrow (existing) + FlawChess-Engine arrow both on by default — closes the "what you played vs practically best for you" loop, the differentiator with the best build-cost/value ratio in the whole milestone

### Add After Validation (v1.x / "Ambitious" tier per seed)

Features to add once MVP1's core concept is validated with real users.

- [ ] Dedicated trap-finder / branch-point UI ("if instead ...Qxb2, played 30% of the time, then...") — trigger: users ask "why is this the practical line" often enough that the score-pair tooltip isn't enough
- [ ] Per-ELO leaf sigmoids fit from the benchmark DB (replacing the global lichess curve) — trigger: MVP1's global sigmoid is shown to systematically mis-rank practical scores at rating extremes (very low/very high ELO)
- [ ] SAB-multithreaded root grading — trigger: node-budget is shown to be the binding constraint on practical-line quality at the current 2-4-worker pool size, AND the OAuth-popup conflict has an accepted resolution

### Future Consideration (v2+ beyond this milestone)

Features to defer until this milestone's core concept has product-market validation.

- [ ] Time-pressure conditioning (clock→temperature, clock→ELO-offset calibrated from own DB) — defer: needs its own calibration mini-project against imported clock data; the seed flags this as possibly the most defensible "genuinely novel" axis, so it deserves a dedicated milestone rather than a rushed bolt-on
- [ ] Maia-2 dual-skill-attention adoption (replacing independent per-rating Maia-1 models with Maia-2's `Q* = Q + (e_a ⊕ e_o)W` skill-aware attention) — defer: an infra swap under the existing Maia layer, worth revisiting once MVP1's asymmetric-rating design is validated and if Maia-2 weights become available for client-side inference

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| MCTS + custom Maia-weighted backup | HIGH | HIGH | P1 |
| Stockfish.wasm worker pool (2-4 threads) | HIGH | MEDIUM | P1 |
| Lichess eval→win% leaf sigmoid | MEDIUM | LOW | P1 |
| Modal-path line + objective/practical score pair | HIGH | MEDIUM | P1 |
| Live-refining top-n lines (anytime) | HIGH | MEDIUM (native to MCTS) | P1 |
| FlawChess Engine arrow layer (top-2, toggleable) | HIGH | LOW (existing arrow infra) | P1 |
| Game-review played-vs-practical loop | HIGH | LOW (composition of existing pieces) | P1 |
| Trap-finder / branch-point UI | MEDIUM | HIGH | P2 |
| Per-ELO leaf sigmoids (benchmark DB fit) | MEDIUM | MEDIUM | P2 |
| SAB multithreaded root grading | LOW-MEDIUM | HIGH (blocked on OAuth conflict) | P3 |
| Time-pressure conditioning | MEDIUM-HIGH (novelty potential) | HIGH (own calibration project) | P3 |

**Priority key:**
- P1: Must have for MVP1 launch
- P2: Should have, "Ambitious" tier, add when validated
- P3: Nice to have, own future milestone

## Competitor / Prior-Art Feature Analysis

| Feature | Polecat | vala-bot | FlawChess Engine (planned) |
|---------|---------|----------|------------------------------|
| Search algorithm | Textbook expectimax, probability-cutoff pruned | Level-synchronous two-stage expectimax (trigger screen + full search) | MCTS with custom Maia-weighted expectimax backup (adaptive depth allocation under a small node budget) |
| Objective engine | Leela Chess Zero weights / Stockfish (comparison only) | Patricia 5 (aggressive NNUE alpha-beta) | Stockfish.wasm (client-side) |
| Opponent model | Single fixed Maia weights file, user-configured | Maia-3/Chessformer at interior nodes; Lichess Opening Explorer at shallow nodes | Maia (client-side, existing v1.32 infra), single model reused for both sides |
| Self-rating modeling | None — engine side plays at full strength | None — vala plays via `pool.map_best_move()` at full strength | **Asymmetric**: your ELO for your own future-node queries, opponent ELO for opponent-node queries |
| Leaf eval→score conversion | Linear remap `(eval+1)/2` | Raw centipawns, no conversion | Lichess sigmoid (calibrated eval→win%), MVP; per-ELO fit deferred |
| Output surface | Offline experiment harness (plays full games, reports aggregate stats) | Live Lichess bot (plays real games) | Analysis tool (displayed line + score pair on an existing board UI) |
| Trap/swindle exposure | Emergent in gameplay outcome only | Explicit UCI tag (`BAIT`) + EV-swing reporting | Emergent in the modal line's ranking, no dedicated UI in MVP1 (deferred) |
| Risk/deviation transparency | Not exposed | `risk_cp` / `margin_cp` dials, per-move info line | Objective-vs-practical score pair with plain-language attribution (planned analog of vala's transparency, aimed at a learner not an operator) |

## UI/UX Conventions Assessed

Reviewed against the FlawChess codebase (`useAnalysisBoard.ts`, `useStockfishEngine.ts`, `lib/theme.ts`, `lib/arrowColor.ts`, `components/analysis/MovesByRatingChart.tsx`) rather than assumed from the seed alone — the arrow-layer system SEED-082 designs is largely an extension of an already-shipped pattern, not new infrastructure.

- **Arrow-layer precedent already shipped (v1.29, Phase 136-138):** the `/analysis` board already renders a Stockfish best-move arrow (`BEST_MOVE_ARROW`) and second-best arrow (`SECOND_BEST_ARROW`), plus a distinct "next move" hint arrow (`NEXT_MOVE_ARROW`, deliberately thinner/more translucent so it reads as a subtle hint layered under the wider engine arrows) and tactic-line arrows (`tacticArrows.ts`). Each layer has its own named color constant in `theme.ts` and its own opacity/width tuning — this is the established idiom the new FlawChess-Engine layer must follow, not invent.
- **"Disagreement with Stockfish looks intentional" is a solved problem in this codebase already**, not a new UI challenge: the existing move-quality-bar / tactic-arrow system already shows a "best" move and a distinct "second-best" or "missed" move side by side with different hues (blue for engine-best, lighter blue for second-best, red/orange family for flaw-severity). The pattern to reuse for the FlawChess-Engine layer is the same one: a clearly distinct hue (not a shade of Stockfish's blue) plus copy that names *why* two arrows disagree (score-pair + attribution), never a bare unlabeled arrow.
- **Live-refinement UX precedent:** `useStockfishEngine` already implements the anytime pattern the new engine needs — debounced auto-analysis (150ms rapid-step coalescing), a `movetime`/node-cap dual budget (1500ms wall-clock / 2M nodes), and a two-layer stale-eval guard to avoid flickering results mid-search. The MCTS search's live emission should reuse this exact worker-state-machine shape (idle/thinking/stopping) rather than a new one.
- **Maia display precedent:** Maia is surfaced via `MovesByRatingChart.tsx` and `MaiaMoveQualityBar.tsx` as a hover/chart interaction, not a permanent board arrow — this is exactly the seed's locked decision to drop a dedicated 4th Maia arrow layer, and it's confirmed as the existing, working pattern rather than a new compromise.
- **maiachess.com's "played move" arrow claim could not be independently confirmed** from the marketing page content (it did not expose implementation detail); this is a LOW-confidence citation in the seed and should be verified by visiting the live maiachess.com analysis UI directly before repeating the claim in any phase-level design doc.
- **Neither Polecat nor vala-bot offer any analysis-tool UI to draw from** — both are play-only (offline harness / live bot), so the "how to display a practical line to a learner" question has no direct prior-art answer; FlawChess's existing Stockfish/tactic arrow system is the only real precedent available, which raises this milestone's UI risk slightly (there's no external UI benchmark to copy, only this app's own conventions to extend consistently).

## Sources

- [Polecat project page](https://bradleylovell.com/polecat) — MEDIUM confidence
- [Polecat repository](https://github.com/subcreation-studio/Polecat) — MEDIUM confidence, source read directly
- [vala-bot Lichess profile](https://lichess.org/@/vala-bot) — MEDIUM confidence
- [vala repository](https://github.com/Avo-k/vala) — MEDIUM confidence, source read directly
- [Patricia engine](https://github.com/Adam-Kulju/Patricia) — LOW confidence (not directly read, referenced by vala)
- [Maia Chess](https://github.com/CSSLab/maia-chess) — LOW confidence (not directly read this session)
- [maiachess.com](https://maiachess.com) — LOW confidence (page content did not expose UI implementation detail; treat as unresolved for the "played move arrow" precedent claim in SEED-082, worth re-verifying by visiting the live analysis UI rather than the marketing page)
- FlawChess codebase (`frontend/src/hooks/useAnalysisBoard.ts`, `useStockfishEngine.ts`, `lib/theme.ts`, `lib/arrowColor.ts`, `components/analysis/MovesByRatingChart.tsx`) — HIGH confidence, direct repo read, confirms the existing arrow-layer/toggle/live-refine conventions this milestone must extend
- `.planning/seeds/SEED-082-human-playable-line-engine.md` — locked design source for this milestone

---
*Feature research for: FlawChess Engine (v2.0 milestone)*
*Researched: 2026-07-05*
