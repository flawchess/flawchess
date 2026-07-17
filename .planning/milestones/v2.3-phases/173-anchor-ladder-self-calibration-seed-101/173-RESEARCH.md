# Phase 173: Anchor ladder self-calibration (SEED-101) - Research

**Researched:** 2026-07-15
**Domain:** Offline pairwise-comparison rating estimation (Bradley-Terry/Elo MLE) over a Node.js game-playing harness, consumed by a Python fit script
**Confidence:** MEDIUM-HIGH (game-loop reuse and harness conventions are HIGH — read directly from source; the rating-model math is HIGH, standard statistics; the adaptive probe/measure scheduling algorithm and artifact shape are MEDIUM — CONTEXT.md leaves the exact mechanics to Claude's discretion)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

The user delegated all four gray areas with one binding directive:
**maximize information per game — do not spend games on pairings that carry
no information.** Every decision below serves that directive.

**Match schedule & game budget**
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

**Rating model & fit tooling**
- **D-05: Python fit script in `scripts/`** (project convention; user is a
  data scientist). Logistic (Bradley-Terry/Elo-curve) maximum-likelihood fit on
  game scores with draws counted as 0.5; identify the scale by fixing
  maia1500 = 1500. No external rating binaries (BayesElo/Ordo) — 10 parameters
  do not justify a new tool dependency.
- **D-06: Uncertainty + residuals are mandatory outputs.** Per-anchor CIs
  (bootstrap over games is fine) and per-pair residuals (observed − predicted
  score). Cross-family residuals reported prominently — large ones are the
  style-confounding signal the seed calls out, not a nuisance to hide.
- **D-07: Dependencies:** prefer numpy-or-stdlib-only. Adding scipy as a dev
  dependency is allowed if it materially simplifies the MLE — planner's call.

**Harness integration**
- **D-08: New standalone script** (e.g. `scripts/calibration-anchor-ladder.mjs`),
  NOT a mode flag inside `scripts/calibration-harness.mjs`. The bot harness is
  shaped around bot cells (MCTS bot, `ANCHOR_ELO_WINDOW` pruning, bot-cell
  resume keys) — none of which apply to anchor-vs-anchor. Reuse the lib modules
  (`calibration-anchors.mjs`, `calibration-openings.mjs`, `stockfish-pool.mjs`,
  `calibration-providers.mjs`). Where game-loop/adjudication logic currently
  lives inside calibration-harness.mjs, extract it into `scripts/lib/` with no
  behavior change to the bot harness rather than copy-pasting.
- **D-09: Wire SF skills 8 and 10:** add entries to `SF_SKILL_ELO`
  (explicitly-approximate nominal values, used for labels/ordering only — the
  fit ignores them) so `parseAnchorSpec` accepts `sf8`/`sf10`.
- **D-10: Keep harness conventions:** TSV output in `reports/data/`, seeded
  determinism, opening-book start FENs, the existing adjudication rules
  (eval-threshold + ply cap), and `--resume` support (the run is hours long and
  must survive interruption).

**Output artifact & SEED-102 hand-off**
- **D-11: Executing the run is in scope.** The phase goal is the *answer*
  (ladder spacing + compression verdict), not just tooling. Run locally on
  Adrian's machine (resumable); anchor-vs-anchor games have no MCTS in the
  loop, so expect hours, not days.
- **D-12: Three deliverable artifacts:** (1) raw per-game/per-pair TSV in
  `reports/data/`; (2) a committed machine-readable internal-scale table at a
  stable path that SEED-102's harness work can consume (exact shape/location is
  the planner's call); (3) a findings note in `.planning/notes/` following the
  pattern of `2026-07-13-bot-calibration-findings.md`, stating the compression
  verdict and closing 168-RESEARCH.md Open Question 2 as a blocker.
- **D-13: Labeling discipline:** every artifact column/field says
  `internal_rating` (or similar) with an explicit "internal scale — NOT human
  ELO" header note. The SEED-091 caveat carries forward verbatim.

### Claude's Discretion

The user delegated all areas ("you decide") subject to the info-efficiency
directive. Researcher/planner may adjust details (exact probe game counts,
cross-family link placement, artifact file shape, CI method) freely as long as
D-01's no-wasted-games principle and D-04's connectivity guard hold.

### Deferred Ideas (OUT OF SCOPE)

- Blend 0.05 vs 0.5 hedge probe at bot_elo 1900/2300 — SEED-102's locate pass, not this phase.
- Any anchor-window / locate-then-measure fix to the bot-vs-anchor harness — SEED-102 ("Harness fixes required first").
- Human-ELO correction of the internal scale — SEED-103.
- Per-style slider-range lookup tables — SEED-104.
</user_constraints>

## Summary

This phase has no code in production to write — it is a bespoke offline measurement tool
plus one executed run. The work splits cleanly into two languages joined by a TSV: a
**Node.js game-playing harness** (`scripts/calibration-anchor-ladder.mjs`) that plays
anchor-vs-anchor games and writes a raw per-game ledger, and a **Python fit script**
(`scripts/calibration-anchor-fit.py`) that reads that ledger and fits a joint
Bradley-Terry/Elo rating model over the resulting pairwise-comparison graph.

The Node side is a genuine extraction exercise, not new engineering: everything needed
(anchor movers, Stockfish pool, opening book, TSV conventions, seeded RNG, adjudication
rules) already exists in `scripts/lib/calibration-*.mjs`, built and proven by Phase 168 /
168.5. The only game-loop logic that does not already exist as a reusable function is
`playGame()` inside `calibration-harness.mjs` itself, which is hard-wired to one bot mover
+ one anchor mover. D-08 requires extracting its terminal/adjudication logic into
`scripts/lib/` so a *symmetric* two-anchor-mover game loop can reuse it without
copy-pasting or behavior-changing the existing bot harness.

The Python side is genuinely new but is standard, well-understood statistics: fitting
ratings for ~10 anchors (5 Maia rungs + 5 Stockfish skills) over a few hundred pairwise
games is small enough that the classical **Zermelo/MM iteration** (the same fixed-point
algorithm underlying BayesElo/Ordo, D-05 explicitly rules those tools out as unnecessary
here) converges in a few dozen iterations using only `math`/`statistics`/stdlib — no numpy
or scipy required. This session's dependency-legitimacy check flagged both packages `SUS`
on a metadata heuristic (no indexed download count / repo URL via the registry API this
tool used) that is a known false positive for foundational scientific-Python packages —
but since a pure-stdlib implementation is both simpler and adequate at this scale, the
recommendation is to **not add either dependency** and treat D-07's numpy/scipy allowance
as unnecessary rather than exercising it.

**Primary recommendation:** Extract `calibration-harness.mjs`'s terminal/adjudication game
loop into a new `scripts/lib/calibration-game-loop.mjs` module generalized over two
movers (not a fixed bot+anchor pair); build `calibration-anchor-ladder.mjs` on top of it
with a two-stage probe→measure scheduler; fit ratings in pure-Python stdlib via Zermelo/MM
iteration with the maia1500=1500 scale fix, bootstrap CIs, and per-pair residuals; emit
the three D-12 artifacts with the D-13 "internal scale, NOT human ELO" label on every one.

## Architectural Responsibility Map

This phase is an offline CLI tool pipeline, not a web application — the standard
browser/SSR/API/DB tiers don't apply. The equivalent boundary here is
data-generation vs. data-analysis vs. downstream-consumption.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Playing anchor-vs-anchor games, adjudication, TSV emission | Node harness (`scripts/calibration-anchor-ladder.mjs` + `scripts/lib/`) | — | Owns the only stateful/slow resource (Stockfish/Maia engines); must be resumable (D-11) |
| Probe→measure pair scheduling (D-01/D-02/D-04) | Node harness | Python fit (informs which pairs to re-target) | Scheduling decisions gate which games get played — must happen before/during play, in the same process that drives the engines |
| Bradley-Terry/Elo MLE fit, CIs, residuals | Python fit script (`scripts/calibration-anchor-fit.py`) | — | D-05 locks this to Python; pure statistics over a static TSV, no engine access needed |
| Internal-scale artifact (consumed by future SEED-102 harness code) | Committed file in `scripts/lib/` or `reports/data/` | Node harness (SEED-102, future phase) | Must be trivially importable/parseable by a future Node script — shape choice should favor the Node consumer, not the Python producer |
| Compression-verdict findings note | `.planning/notes/` | — | Documentation artifact, not runtime code |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Node.js built-in `child_process`/`fs`/`node:assert` | Node 24.14.0 (confirmed installed) [VERIFIED: `node --version` this session] | Game-loop orchestration, TSV I/O, check-script assertions | Already the entire toolchain for `calibration-harness.mjs`; zero new deps |
| Python stdlib `math`, `random`, `statistics`, `csv`/manual TSV parsing, `json`, `argparse` | Python 3.13.12 (confirmed installed) [VERIFIED: `python3 --version` this session] | Zermelo/MM rating fit, bootstrap CI, residuals, artifact emission | Sufficient for a ~10-parameter MLE over a few hundred games — no numerical library needed at this scale |
| `scripts/lib/calibration-anchors.mjs`, `calibration-openings.mjs`, `stockfish-pool.mjs`, `calibration-providers.mjs`, `node-engine-providers.mjs` | Already in repo (Phase 168/168.5) [VERIFIED: read directly this session] | Anchor move-choosers, N-process Stockfish pool, opening book, Node `EngineProviders` adapter, Maia/Stockfish bring-up | D-08 explicitly requires reuse; these are the exact modules the bot harness already depends on |
| `frontend/src/lib/engine/botSampling.ts` (`mulberry32`, `fallbackMove`) | Already in repo | Seeded per-game PRNG, degenerate-policy fallback move | Existing D-09 determinism machinery the harness already relies on |
| `frontend/src/lib/maiaEncoding.ts` (`MAIA_ELO_LADDER`) | Already in repo | Validates the 5 Maia anchor rungs are real ladder members | `parseAnchorSpec` already gates on ladder membership |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | 2.5.1 resolves via `uv pip install --dry-run` [VERIFIED: uv dry-run resolution this session] | Vectorized matrix ops for an alternative Newton-Raphson fit | Only if the planner wants a Hessian-based fit instead of Zermelo/MM iteration — NOT recommended, see Package Legitimacy Audit |
| `scipy.optimize` | resolves similarly [ASSUMED — not independently version-checked, same registry as numpy] | `minimize`/`fmin` as an off-the-shelf MLE solver | Only if hand-rolled Zermelo/MM iteration turns out to converge poorly (unlikely at this scale) — NOT recommended |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure-stdlib Zermelo/MM iteration | numpy + Newton-Raphson with analytic Hessian | Faster convergence per iteration but adds a dependency, and at ~10 parameters the difference is immaterial (Zermelo/MM converges in well under 100 iterations for graphs this small) |
| Pure-stdlib Zermelo/MM iteration | `scipy.optimize.minimize` (BFGS/L-BFGS) on the negative log-likelihood | Robust general-purpose optimizer, but overkill for a well-conditioned convex problem this small, and adds a dependency the legitimacy check flagged `SUS` |
| Pure-stdlib Zermelo/MM iteration | An external rating binary (BayesElo, Ordo) | D-05 explicitly rejects this — 10 parameters don't justify a new tool dependency, and it would be a second, opaque implementation of the same math |
| Hand-rolled bootstrap loop | numpy vectorized resampling | Bootstrap resampling over ~10 anchors × a few hundred games in pure Python is fast enough (thousands of resamples in well under a second) that vectorization buys nothing perceptible |

**Installation:**
```bash
# No new dependencies recommended. If the planner overrides D-07's discretion
# and wants numpy/scipy anyway:
uv add --group dev numpy scipy
```

**Version verification:** `uv pip install --dry-run numpy` resolved `numpy==2.5.1` against
the live PyPI index this session [VERIFIED: uv dry-run resolution]. No existing scientific
Python dependency is in `pyproject.toml` today — `dependencies` and the `dev`
`dependency-groups` are FastAPI/SQLAlchemy/testing-only, confirmed by reading the file
directly this session.

## Package Legitimacy Audit

> Included per protocol even though the recommendation is to add **zero** new packages.
> Documented here so the planner doesn't waste a cycle re-investigating if D-07's scipy
> allowance is later exercised.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| numpy | PyPI | latest release 2026-07-04 (registry metadata) | not indexed by this session's check tool | not indexed by this session's check tool | [SUS] (heuristic false positive — see note) | Not added; NOT recommended (stdlib-only fit is sufficient and simpler) |
| scipy | PyPI | latest release 2026-06-19 (registry metadata) | not indexed by this session's check tool | not indexed by this session's check tool | [SUS] (heuristic false positive — see note) | Not added; NOT recommended |

**Note on the SUS verdicts:** `gsd-tools query package-legitimacy check` flagged both
packages `SUS` with reasons `too-new` / `unknown-downloads` / `no-repository`. This is a
metadata-source limitation, not a real signal: the check reads a package's *most recent
release date* as "package age" (numpy/scipy both ship frequent point releases, so the
latest version always looks "new") and the registry API queried here does not surface
weekly-download counts or repo URLs for either package. numpy and scipy are two of the
most widely-used, longest-established packages in the Python ecosystem — this is
training-data knowledge, not verified via an authoritative source this session, so it is
still tagged `[ASSUMED]` per the provenance rule even though the SUS verdict is almost
certainly a false positive. Existence and installability were independently confirmed via
`uv pip install --dry-run` against the live registry [VERIFIED: uv dry-run this session].

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** numpy, scipy — both are recommended-against
anyway (stdlib suffices), so no `checkpoint:human-verify` gate is needed unless the
planner overrides D-07's discretion and adds one of them; in that case, add the gate.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │  scripts/calibration-anchor-ladder.mjs   │
                    │  (new, D-08 standalone script)           │
                    └───────────────┬───────────────────────────┘
                                    │ orchestrates
                    ┌───────────────▼───────────────────────────┐
                    │  Probe→Measure scheduler (D-01/D-02/D-04)  │
                    │  1. Build candidate pair graph:            │
                    │     adjacent-maia + adjacent-SF +          │
                    │     initial cross-family guesses           │
                    │     (folklore SF_SKILL_ELO -> nearest rung)│
                    │  2. Probe pass: ~8 games/pair               │
                    │  3. Score gate: keep pairs in [0.2, 0.8]    │
                    │     drop/re-target lopsided pairs           │
                    │  4. Connectivity check (D-04) before        │
                    │     finalizing prunes                       │
                    │  5. Measure pass: extend surviving pairs    │
                    │     to 24 total games                        │
                    └───────┬─────────────────────┬───────────────┘
                            │ per-ply moves        │ per-ply moves
              ┌─────────────▼───────────┐  ┌───────▼──────────────┐
              │ Anchor mover (side A)   │  │ Anchor mover (side B) │
              │ maiaArgmaxMove /        │  │ maiaArgmaxMove /       │
              │ pool.skillMove          │  │ pool.skillMove         │
              │ (calibration-anchors,   │  │ (reused verbatim,      │
              │  reused verbatim)       │  │  D-08)                 │
              └─────────────┬───────────┘  └───────┬──────────────┘
                            │                       │
                    ┌───────▼───────────────────────▼───────┐
                    │ scripts/lib/calibration-game-loop.mjs  │
                    │ (NEW — extracted from                  │
                    │  calibration-harness.mjs's playGame,    │
                    │  generalized to 2 arbitrary movers,     │
                    │  D-08 "no behavior change" requirement) │
                    │  - terminal-state classification         │
                    │  - adjudication eval + sustain tracking   │
                    │  - ply cap                                │
                    │  - seeded RNG + opening-book start FEN     │
                    └───────┬───────────────────────────────────┘
                            │ (backed by, reused as-is)
              ┌─────────────▼──────────────────────────────┐
              │ stockfish-pool.mjs (N-process pool)          │
              │ node-engine-providers.mjs (Maia+SF bring-up) │
              │ calibration-providers.mjs (eval/grade)       │
              │ calibration-openings.mjs (opening book)      │
              └───────────────────────────────────────────────┘
                            │ writes
              ┌─────────────▼──────────────────────────────┐
              │ reports/data/anchor-ladder-<ts>.tsv          │
              │ (raw per-game ledger — D-12 artifact 1)      │
              │ reports/data/anchor-ladder-<ts>-pairs.tsv    │
              │ (per-pair aggregate, human-readable)         │
              └─────────────┬──────────────────────────────┘
                            │ read by
              ┌─────────────▼──────────────────────────────┐
              │ scripts/calibration-anchor-fit.py (NEW)      │
              │  1. Load games, build graph, verify          │
              │     connectivity (defensive re-check of D-04)│
              │  2. Fold draws as 0.5/0.5 (D-05)               │
              │  3. Zermelo/MM iterative MLE fit               │
              │  4. Fix scale: maia1500 := 1500                │
              │  5. Bootstrap CI per anchor (D-06)              │
              │  6. Per-pair residuals, cross-family flagged   │
              │     prominently (D-06)                          │
              │  7. Compression verdict: measured adjacent-     │
              │     rung deltas vs nominal 400-pt steps          │
              └─────────────┬───────────────┬──────────────┘
                            │               │
              ┌─────────────▼──────┐  ┌─────▼─────────────────────┐
              │ Internal-scale      │  │ .planning/notes/           │
              │ artifact (D-12 #2)  │  │ <date>-anchor-ladder-      │
              │ — machine-readable, │  │ self-calibration-          │
              │ consumed by future  │  │ findings.md (D-12 #3)      │
              │ SEED-102 Node work  │  │ — compression verdict,     │
              │                     │  │ closes 168-RESEARCH.md OQ2 │
              └─────────────────────┘  └─────────────────────────────┘
```

### Recommended Project Structure

```
scripts/
├── calibration-anchor-ladder.mjs      # NEW — D-08 standalone script (Node orchestrator)
├── calibration-anchor-fit.py          # NEW — D-05 Python rating-model fit
├── calibration-harness.mjs            # UNCHANGED behavior; playGame's game-loop body
│                                       #   moves into lib/calibration-game-loop.mjs (D-08)
└── lib/
    ├── calibration-game-loop.mjs      # NEW — extracted, mover-agnostic game loop
    ├── calibration-anchors.mjs        # touched only for D-09 (SF_SKILL_ELO 8/10 entries)
    ├── calibration-openings.mjs       # reused as-is
    ├── calibration-providers.mjs      # reused as-is
    ├── stockfish-pool.mjs             # reused as-is
    ├── node-engine-providers.mjs      # reused as-is
    ├── calibration-game-loop.check.mjs  # NEW — mirrors calibration-pruning.check.mjs's
    │                                     #   synthesized-fixture structural-check style
    └── calibration-anchor-schedule.check.mjs  # NEW — probe/measure gate + connectivity
                                                #   guard, pure logic, no engines (mirrors
                                                #   calibration-elo.check.mjs style)

tests/
└── scripts/
    └── test_calibration_anchor_fit.py  # NEW — pytest, mirrors tests/scripts/
                                          #   test_backfill_eval.py precedent for testing
                                          #   scripts/*.py; covers Zermelo/MM convergence,
                                          #   scale-fix, draw handling, disconnected-graph
                                          #   guard, bootstrap CI sanity

reports/data/
├── anchor-ladder-<timestamp>.tsv          # raw per-game ledger (D-12 #1)
└── anchor-ladder-<timestamp>-pairs.tsv    # per-pair aggregate (mirrors existing
                                            #   main+summary two-tier TSV convention)

.planning/notes/
└── <date>-anchor-ladder-self-calibration-findings.md  # D-12 #3
```

### Pattern 1: Extract, don't copy-paste, the game loop (D-08)

**What:** `calibration-harness.mjs`'s `playGame()` currently hard-codes "white/black
determined by `botIsWhite`, one side calls `selectBotMove`, the other calls
`playAnchorMove`". Extract everything EXCEPT that one dispatch line — terminal
classification (`classifyTerminalResult`), adjudication (`updateSustainState`,
`evaluateNonTerminalCutoffs`, `adjudicatedResult`), `applyUciMove`, and the overall
ply loop shape — into `scripts/lib/calibration-game-loop.mjs` as a function taking two
arbitrary async move-choosers (`moverWhite(fen, gameRng) => uci`,
`moverBlack(fen, gameRng) => uci`), keyed by color rather than bot-vs-anchor role.

**When to use:** Any future harness that needs the same "play one game to a
terminal/adjudicated/capped result" shape with different movers on each side — this
phase (two anchors) is the second consumer after the bot harness (bot + one anchor),
which is exactly the generalization signal that justifies extracting now rather than
copy-pasting a near-duplicate `playGame`.

**Example (shape, not literal code — mirrors the existing file's structure):**
```javascript
// scripts/lib/calibration-game-loop.mjs
export async function playTwoMoverGame({
  Chess, pool, moverWhite, moverBlack, startFen, gameRng, onPly,
}) {
  await pool.newGameAll();
  const chess = new Chess(startFen);
  const sustainState = { side: null, count: 0 };
  let ply = 0;
  for (;;) {
    const fen = chess.fen();
    const whiteToMove = fen.split(' ')[1] !== 'b';
    const mover = whiteToMove ? moverWhite : moverBlack;
    const uci = await mover(fen, gameRng);
    applyUciMove(chess, uci);
    ply++;
    onPly?.({ ply, mover: whiteToMove ? 'white' : 'black', uci });
    const terminal = classifyTerminalResultForWhite(chess);
    if (terminal !== null) return { ...terminal, plies: ply, moveUcis: [] /* accumulate as needed */ };
    const cutoff = await evaluateNonTerminalCutoffsForWhite({ pool, fen: chess.fen(), ply, sustainState });
    if (cutoff !== null) return { ...cutoff, plies: ply };
  }
}
```
`calibration-harness.mjs`'s own `playGame` becomes a thin wrapper: `moverWhite`/
`moverBlack` derived from `botIsWhite` (one is `selectBotMove`, the other
`playAnchorMove`), calling into the same shared loop — the bot harness's own tests/checks
(`calibration-determinism.check.mjs`, `calibration-pruning.check.mjs`) must still pass
unchanged, proving "no behavior change" (D-08).

### Pattern 2: Zermelo/MM iteration for the joint fit (D-05)

**What:** The classical fixed-point algorithm for Bradley-Terry MLE (Zermelo 1929;
generalized as an MM algorithm by Hunter 2004). For each anchor `i` with strength
`π_i = 10^(rating_i / 400)`:

```
π_i^(k+1) = W_i / Σ_{j≠i} n_ij / (π_i^(k) + π_j^(k))
```

where `W_i` is anchor `i`'s total wins (with draws split 0.5/0.5, D-05) across every
pair it played, and `n_ij` is the number of games played between `i` and `j`. Iterate
until the largest relative change across all `π_i` falls below a small tolerance
(e.g. `1e-9`), then convert back to rating scale (`rating_i = 400 * log10(π_i)`) and
shift every rating by a constant so `rating_maia1500 == 1500` (the scale-fixing point,
D-05). This is monotonically convergent (Hunter 2004) and needs no matrix inversion —
pure Python loops over ~10 anchors and a few hundred games converge in well under a
second.

**When to use:** Any pairwise-comparison MLE fit small enough that iteration count
(not per-iteration cost) dominates runtime — true here (10 anchors, <15 pairs typically
active after pruning).

**Example:**
```python
# scripts/calibration-anchor-fit.py (shape)
def fit_bradley_terry(win_counts: dict[tuple[str, str], float], anchors: list[str],
                       tol: float = 1e-9, max_iter: int = 10_000) -> dict[str, float]:
    """win_counts[(i, j)] = i's wins vs j (draws pre-split 0.5/0.5, D-05)."""
    strength = {a: 1.0 for a in anchors}
    total_wins = {a: sum(win_counts.get((a, b), 0.0) for b in anchors if b != a) for a in anchors}
    for _ in range(max_iter):
        new_strength = {}
        for i in anchors:
            denom = sum(
                (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0))
                / (strength[i] + strength[j])
                for j in anchors if j != i and (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0)) > 0
            )
            new_strength[i] = total_wins[i] / denom if denom > 0 else strength[i]
        max_rel_change = max(abs(new_strength[a] - strength[a]) / strength[a] for a in anchors)
        strength = new_strength
        if max_rel_change < tol:
            break
    return strength  # convert to 400*log10(pi) scale, then fix maia1500 := 1500
```

### Pattern 3: Two-tier TSV (raw ledger + aggregate) — existing project convention

**What:** Every prior calibration harness in this repo (168's `calibration-harness.mjs`,
165's `gem-elo-calibration.mjs`) writes a primary durable results TSV plus a derived
`-summary.tsv` sibling. Mirror this: a per-game raw ledger (every game's
`anchor_a, anchor_b, winner, plies, opening, seed, moveUcis...`) as the primary durable
artifact (WR-01/D-06-style incremental durability — one line written the instant a game
finishes, so a killed run's completed games are never lost), plus a per-pair aggregate
(`anchor_a, anchor_b, games, score_a, ...`) derived at the end of each pair's games.

**When to use:** This is the natural granularity for D-12 artifact 1 ("raw
per-game/per-pair TSV") — write BOTH, since the fit script needs per-game rows (draws
must be identifiable per-game, not just folded into an aggregate score) but a human
skimming the run wants the pair-level view.

### Anti-Patterns to Avoid

- **Reimplementing the anchor movers:** `maiaArgmaxMove`/`stockfishSkillMove` already
  exist and are unit-tested via the existing `.check.mjs` files. Anchor-vs-anchor games
  call the SAME functions for both sides (just with different `anchorSpec`s) — never
  branch on "is this the harness's bot" inside the anchor movers themselves.
- **Confusing this fit with the existing `calibration-elo.mjs` advisory estimate:** the
  D-05 `invertAnchorElo`/`combineAnchorEstimates` functions solve a DIFFERENT problem
  (weighted-mean single-anchor inversion for one bot cell against several KNOWN-rating
  anchors). SEED-101's fit is a full joint MLE where NO anchor's rating is assumed
  known in advance except the one fixed scale point. Do not reuse or extend
  `calibration-elo.mjs` for this — it is the wrong math for a joint fit.
- **Letting folklore SF_SKILL_ELO values leak into the fit as ground truth:** they exist
  ONLY to pick which Maia rung to probe first against a given SF skill (a scheduling
  heuristic). The fit itself must never treat any SF anchor's rating as known — it is
  exactly what is being measured.
- **A full round-robin:** explicitly rejected by D-02. Resist the temptation to "just
  play everything" for simplicity — it defeats the entire information-efficiency
  directive the user gave.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pairwise-comparison MLE rating fit | An ad hoc gradient-descent loop on a hand-derived log-likelihood | Zermelo/MM fixed-point iteration (Pattern 2) | Well-known closed-form convergent algorithm; a hand-rolled gradient descent needs a learning-rate schedule and convergence tuning that MM iteration avoids entirely |
| Graph connectivity check (D-04) | A bespoke reachability heuristic | Stdlib BFS/Union-Find over the (anchor, anchor) edge set built from games-played>0 pairs | Standard graph algorithm, a few lines, no library needed; verify it structurally (unit test with a synthesized disconnected fixture) rather than trusting a scheduling heuristic to "probably" keep it connected |
| Bootstrap confidence intervals | A parametric normal-approximation CI on the fitted ratings | Nonparametric bootstrap: resample games with replacement per pair, refit via Zermelo/MM, collect the empirical percentile distribution of each anchor's rating (D-06 explicitly names this as acceptable) | Normal-approximation CIs assume asymptotic regularity that a ~10-parameter fit over a few hundred games may not satisfy cleanly, especially near the pruned/lopsided edges of the graph; bootstrap is safer and just as cheap at this scale |
| Small-sample degenerate-score handling | A new continuity-correction constant | The SAME pattern already in `calibration-elo.mjs`'s `SCORE_CLAMP_EPSILON_DIVISOR` clamp (though applied inside the joint fit differently — see Pitfalls) | Established, already-reviewed pattern in this codebase for exactly this class of problem |

**Key insight:** Every piece of this phase's math (pairwise rating MLE, graph
connectivity, bootstrap CI, degenerate-score handling) is standard statistical practice
with decades of prior art. The only genuinely new engineering is the probe→measure
scheduling loop (D-01/D-02/D-04), which is bespoke because it encodes this specific
project's information-efficiency directive — that part should be hand-built, deliberately,
per CONTEXT.md's discretion grant.

## Common Pitfalls

### Pitfall 1: Non-identifiability from a disconnected game graph
**What goes wrong:** If pruning (D-01's 0.2–0.8 gate) accidentally isolates a subgraph
(e.g. all Maia rungs connected to each other, all SF skills connected to each other, but
zero surviving cross-family links), the Zermelo/MM iteration still numerically
"converges" — but the two subgraphs' ratings are only defined relative to each other
WITHIN each subgraph; the offset between the Maia scale and the SF scale is
arbitrary/undefined, not measured. The fit will silently produce a plausible-looking but
meaningless combined table.
**Why it happens:** D-01's per-pair pruning decision is local (does THIS pair's probe
score sit in 0.2-0.8); nothing about that rule guarantees GLOBAL connectivity, let alone
D-04's stronger "at least 2 informative cross-family links" requirement.
**How to avoid:** Enforce D-04 as an explicit, separate, post-pruning check — after the
probe pass decides which pairs to drop, before finalizing the measure-pass plan, run a
connectivity check (BFS/Union-Find) and count cross-family edges. If either check fails,
apply D-04's stated fallback ("re-target to a nearer rung rather than dropping the
link") rather than proceeding. Re-verify connectivity again on the Python fit side as a
defensive, fail-loud assertion before fitting (belt-and-suspenders — the Node scheduler
and the Python fit are two different programs, and one should never silently trust the
other got this right).
**Warning signs:** A cross-family anchor's bootstrap CI is enormous relative to
same-family anchors; the compression verdict looks suspiciously clean/self-consistent
within each family but the maia-vs-SF alignment doesn't match any of the probe evidence.

### Pitfall 2: Degenerate per-pair scores blow up the fit
**What goes wrong:** A pair that goes 24-0 (or 8-0 in the probe pass, before the 0.2-0.8
gate catches it) makes that pair's contribution to the Zermelo/MM iteration try to push
one anchor's strength toward infinity relative to the other.
**Why it happens:** The joint MLE for Bradley-Terry, like the single-anchor inversion in
`calibration-elo.mjs`, is only well-defined for genuinely mixed evidence. A perfect sweep
carries real information ("A is much stronger than B") but no FINITE point estimate
without some form of regularization or a countervailing edge in the graph.
**How to avoid:** In a well-designed graph (D-01's 0.2-0.8 gate for the MEASURE pass
should mean pairs that make it into the joint fit are never lopsided at 24 games), this
should rarely occur for measure-pass pairs. It CAN still occur if a probe-pass sweep
(8-0) is used to decide a "won_cutoff"/"lost_cutoff"-style pruning (mirroring the
existing bot harness's D-15 mechanism) without ever collecting more data on that edge —
in that case, either exclude 0-game-equivalent lopsided pairs from the fit's edge set
entirely (rely on other paths through the graph for those anchors' placement) or apply
the same continuity-correction clamp pattern already used in `calibration-elo.mjs`
(`epsilon = 1 / (2 * games)`) to the raw win-count before feeding it into Zermelo/MM.
**Warning signs:** The iteration fails to converge within `max_iter`, or produces a
rating for one anchor that is wildly outside the plausible range implied by its other
edges.

### Pitfall 3: Reusing folklore Stockfish-skill Elo as if it were measured
**What goes wrong:** `SF_SKILL_ELO` (0:1320, 3:1750, 5:2200, both existing entries
explicitly flagged "documented-APPROXIMATE... no authoritative Stockfish-18-specific
table exists" in the source comment) is easy to reach for when writing the fit script,
since it is right there and looks like ground truth.
**Why it happens:** It is the only pre-existing rating table for SF anchors in the repo,
and D-09 requires extending it with sf8/sf10 entries anyway.
**How to avoid:** `SF_SKILL_ELO` (and its extended sf8/sf10 entries — this session
proposes 2600/2800 as round, order-of-magnitude, explicitly `[ASSUMED]` continuations of
the existing table's spacing pattern, since community-reported tables for these levels
vary wildly by Stockfish version/hardware/methodology, see Assumptions Log) is used ONLY
for: (a) `parseAnchorSpec`'s ladder-membership gate, (b) the scheduler's INITIAL guess of
which Maia rung to probe a given SF skill against. The joint fit's actual rating for
every SF anchor comes SOLELY from played games — never seed the fit's initial `π_i` or
any prior from this table in a way that could bias convergence toward the folklore value
(a symmetric neutral initialization, e.g. `π_i = 1.0` for all anchors, avoids this).
**Warning signs:** The fitted SF anchor ratings suspiciously match the folklore table
almost exactly despite the seed's own hypothesis that the whole point is these values
are wrong/unverified.

### Pitfall 4: `--resume` semantics differ from the bot harness and need re-deriving
**What goes wrong:** The bot harness's `--resume` (SEED-097) fast-forwards a single
global `gameIndex` through completed `(botElo, botBlend, anchor)` CELLS, in a FIXED grid
known up front. This phase's schedule is ADAPTIVE (D-01/D-02) — the set of pairs to play
is not fully known until after the probe pass runs, and a killed run might be
interrupted mid-probe, mid-decision, or mid-measure.
**Why it happens:** Copy-pasting the existing `--resume` validation logic
(`loadPriorSweep`) assumes a static `gridKeys` set computed up front from CLI flags —
that invariant does not hold here.
**How to avoid:** Design the resumable unit as "one (anchor_a, anchor_b) pair's played
games so far", not "one grid cell". On `--resume`, replay the SAME probe→measure
decision logic from the raw per-game ledger (Pattern 3) — since every played game is
durably logged with its pair identity, the scheduler can reconstruct "how many games has
this pair played, and was the probe-gate decision already made" purely by re-reading the
ledger, rather than needing a separate persisted schedule-state file. This still needs
the SAME seeded-RNG-continuation care the existing harness has (D-09-style): the global
`gameIndex`/opening-cycling counter must fast-forward through exactly the games already
played, in the same order, or resumed games will not be byte-reproducible.
**Warning signs:** A resumed run schedules a probe pass for a pair that was already
measured before the interruption (wasting exactly the games D-01 exists to save), or
plays a different opening/color sequence than an uninterrupted run would have for the
same seed.

### Pitfall 5: Wilson-CI (frontend) vs bootstrap-CI (Python fit) — don't cross-import
**What goes wrong:** `wilsonBounds` (frontend `scoreConfidence.ts`, reused by
`calibration-elo.mjs`) is a closed-form CI for a SINGLE binomial proportion. It is not a
substitute for a bootstrap CI over a JOINT multi-parameter MLE fit, and there is no
straightforward way to import a TypeScript function into a Python script anyway.
**Why it happens:** "Trust the established Wilson stat method" is a strong, correct
project convention (per project memory) for single-proportion confidence — but D-06
explicitly calls for CIs on the FITTED RATINGS, which are a nonlinear transform of many
pooled binomial outcomes, not a single proportion.
**How to avoid:** Use the nonparametric bootstrap-over-games approach for the Python
fit's per-anchor CIs (D-06 explicitly sanctions this), implemented independently in
Python — this is not a violation of the Wilson-method convention, since that convention
applies to single win-rate confidence displays (e.g. the frontend's percentile chips),
not to a joint rating-model fit.
**Warning signs:** An attempt to import or re-derive `wilsonBounds` inside the Python
fit script, or to report the per-anchor rating CI as if it were a single-proportion CI
on that anchor's aggregate win rate against all opponents pooled (that would ignore the
JOINT structure of the fit and misrepresent uncertainty).

## Code Examples

### Reading the raw per-game TSV in Python (stdlib, no csv-library edge cases needed)
```python
# Tab-separated, one header row — mirrors every existing TSV convention in this repo.
def load_games(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        return [dict(zip(header, line.rstrip("\n").split("\t"))) for line in f if line.strip()]
```

### Connectivity + cross-family-edge check (D-04, stdlib BFS)
```python
def check_connectivity(pairs: set[tuple[str, str]], anchors: list[str]) -> None:
    adjacency: dict[str, set[str]] = {a: set() for a in anchors}
    for a, b in pairs:
        adjacency[a].add(b)
        adjacency[b].add(a)
    visited = {anchors[0]}
    frontier = [anchors[0]]
    while frontier:
        node = frontier.pop()
        for neighbor in adjacency[node] - visited:
            visited.add(neighbor)
            frontier.append(neighbor)
    if visited != set(anchors):
        unreached = set(anchors) - visited
        raise RuntimeError(f"Anchor graph is disconnected — unreached: {sorted(unreached)}")

    cross_family_edges = [
        (a, b) for a, b in pairs
        if a.startswith("maia") != b.startswith("maia")  # one maia, one sf
    ]
    if len(cross_family_edges) < 2:
        raise RuntimeError(f"D-04 violated: only {len(cross_family_edges)} cross-family link(s), need >= 2")
```

## State of the Art

Not applicable in the usual "library X replaced by library Y" sense — this is a bespoke
internal measurement tool, not a consumer-facing library integration. The one relevant
"state of the art" note: BayesElo and Ordo are the standard external tools for this exact
problem in the wider chess-engine-testing community, and D-05 has already made the
deliberate decision NOT to use them (10 parameters don't justify the dependency,
Zermelo/MM iteration is the same underlying algorithm implemented directly).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SF_SKILL_ELO` extensions for sf8/sf10 (proposed: 2600, 2800) are reasonable order-of-magnitude continuations of the existing table's spacing | Pitfall 3 / D-09 | Low — CONTEXT.md/SEED-101 both state these values are for labels/ordering only and the fit ignores them; if wrong, only the scheduler's initial cross-family pairing guess (which D-04 already has a re-targeting fallback for) is mildly less efficient |
| A2 | numpy/scipy's `SUS` legitimacy verdict is a metadata-tool false positive, not a real supply-chain risk | Package Legitimacy Audit | Low — the recommendation is to add neither package, so this assumption has no execution impact; flagged for the record only |
| A3 | Zermelo/MM iteration converges reliably in pure Python for a ~10-anchor, few-hundred-game graph without numerical-stability issues | Architecture Patterns, Pattern 2 | Medium — if the pruned/measured graph ends up smaller or more lopsided than expected, convergence could be slow or the iteration could need the Pitfall 2 regularization; mitigated by the D-04 connectivity guard and D-01's 0.2-0.8 gate, both of which push toward well-conditioned data |
| A4 | Reusing games already played in the probe pass toward the 24-game measure-pass total (rather than playing a fresh, separate 24) is the more information-efficient design, consistent with D-01's directive | Architecture Patterns, Pattern 1 diagram; Open Questions | Low-Medium — either design is defensible; CONTEXT.md doesn't specify. If the planner chooses "fresh 24" instead, total game count roughly doubles for surviving pairs with no accuracy benefit |
| A5 | The internal-scale artifact (D-12 #2) should be a Node/JS-importable module (mirroring the existing `SF_SKILL_ELO` pattern) rather than a plain JSON/TSV file, to be maximally consumable by SEED-102's future harness code | Architectural Responsibility Map, Project Structure | Low — CONTEXT.md explicitly defers this shape decision to the planner; either format is machine-readable, this is a convenience recommendation only |

**If this table is empty:** N/A — see rows above.

## Open Questions (RESOLVED)

1. **Does the measure pass extend a pair's existing probe games to 24 total, or play a
   fresh 24 games on top?**
   - RESOLVED: Plan 173-02 Task 2 (measure pass) — extends each surviving pair from its
     8 probe games to 24 total, reusing the probe games as the first 8 and continuing the
     same seeded RNG/opening sequence (never a fresh 24), per D-01's info-efficiency
     directive.
   - What we know: D-01 says probe pass ~8 games, D-03 says 24 games per measured pair;
     the info-efficiency directive strongly favors reusing the probe games as the first
     8 of the 24 (discarding real, already-played data would be the exact kind of waste
     D-01 exists to prevent).
   - What's unclear: CONTEXT.md never states this explicitly either way.
   - Recommendation: extend (reuse probe games as the first 8 of 24), continuing the
     SAME seeded-RNG/opening-cycling sequence for that pair rather than restarting it —
     see Assumption A4.

2. **Exact shape/location of the D-12 artifact #2 (internal-scale table).**
   - What we know: it must be machine-readable, at a stable path, consumable by
     SEED-102's future harness work; D-13 requires the "internal scale — NOT human ELO"
     label on it.
   - What's unclear: CONTEXT.md explicitly defers this to the planner.
   - Recommendation: a small JS module (e.g. `scripts/lib/calibration-internal-scale.mjs`
     exporting a plain object keyed by anchor label, mirroring the existing
     `SF_SKILL_ELO` export pattern) as the primary consumable artifact for future Node
     code, PLUS a sibling JSON/TSV for human/Python readability — see Assumption A5.
   - RESOLVED: Plan 173-04 Task 2 — dual artifact adopted: `scripts/lib/calibration-internal-scale.mjs`
     (`export const INTERNAL_RATING`, the stable Node path for SEED-102) PLUS
     `reports/data/anchor-ladder-internal-scale.json` (human/Python-readable sibling with
     CIs + residuals), both carrying the D-13 caveat.

3. **Exact probe-pass game count and initial cross-family pairing candidates.**
   - What we know: D-01 says "~8 games"; D-02 says cross-family links are "chosen after
     the probe pass — each SF anchor vs the 1–2 Maia rungs nearest its measured (not
     folklore) strength", which is circular for the FIRST probe round (nothing is
     measured yet).
   - What's unclear: what seeds the very first cross-family pairing guess.
   - Recommendation: use the existing (explicitly-approximate) `SF_SKILL_ELO` folklore
     values ONLY to pick the initial candidate Maia rung(s) to probe each SF skill
     against (Pitfall 3 already documents this as a scheduling-only use, never a fit
     input); re-target per D-04's explicit fallback if that initial guess probes
     lopsided.
   - RESOLVED: Plan 173-02 Task 1 (`buildCandidateGraph`) — seeds each SF anchor's
     initial cross-family candidates from its nearest `SF_SKILL_ELO` folklore rung
     (scheduling-only, per Pitfall 3 and D-09), with D-04's re-target fallback in Task 2
     for lopsided probes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Game-playing harness | ✓ | 24.14.0 [VERIFIED this session] | — |
| Python 3.13 + uv | Rating-model fit script | ✓ | 3.13.12 / uv 0.10.9 [VERIFIED this session] | — |
| Vendored Stockfish WASM (`stockfish-18-lite-single.js/.wasm`) | Anchor SF-skill moves, adjudication | ✓ | present in `frontend/public/engine/` [VERIFIED this session] | — |
| Vendored Maia ONNX model (`maia3_simplified.onnx`) | Anchor Maia-argmax moves | ✓ | present in `frontend/public/maia/` [VERIFIED this session] | — |
| CPU cores (for `--stockfish-procs`) | Throughput of the multi-hour run | ✓ | 16 cores [VERIFIED this session] | — |
| numpy/scipy | Optional alternative fit implementation | not installed | — | Not needed — stdlib Zermelo/MM iteration is the recommended path (see Standard Stack) |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:** numpy/scipy (not installed) — fallback is the
recommended stdlib-only implementation, not a degraded feature.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Node side) | Node built-in `node:assert/strict`, run as standalone `.check.mjs` scripts (existing project convention — NOT vitest; these need no browser/DOM harness) |
| Framework (Python side) | pytest (existing project convention; `tests/scripts/test_backfill_eval.py` is the direct precedent for testing a `scripts/*.py` file) |
| Config file | none needed for `.check.mjs` (run directly via `node --import ./scripts/lib/frontend-alias-hook.mjs <file>`); pytest config already exists in `pyproject.toml` |
| Quick run command | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-game-loop.check.mjs` / `uv run pytest tests/scripts/test_calibration_anchor_fit.py` |
| Full suite command | `uv run pytest -n auto` (backend, includes the new test file) + manually running each new `.check.mjs` (these are not currently wired into any npm/CI script — confirmed no `.check.mjs` invocation exists in `package.json` or `.github/workflows/` this session — they are developer-invoked verification tools, consistent with the existing ones) |

### Phase Requirements → Test Map

No `REQUIREMENTS.md` entries map to this phase (SEED-101 backlog work, phase requirement
IDs are "TBD (none mapped)" per the phase description). The CONTEXT.md decisions (D-01
through D-13) are the closest equivalent to requirements for this phase; mapped below.

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-04 | Connectivity guard rejects a disconnected/insufficiently-cross-linked graph | unit | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k connectivity -x` | ❌ Wave 0 |
| D-05 | Zermelo/MM fit converges to the expected ratings on a synthetic fixture with known ground-truth strengths | unit | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k fit_converges -x` | ❌ Wave 0 |
| D-05 | Scale fix pins `maia1500 == 1500` exactly | unit | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k scale_fix -x` | ❌ Wave 0 |
| D-05 | Draws fold to 0.5/0.5 correctly (not dropped, not double-counted) | unit | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k draws -x` | ❌ Wave 0 |
| D-06 | Bootstrap CI produces a finite, sane-width interval for a well-conditioned fixture | unit | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k bootstrap -x` | ❌ Wave 0 |
| D-06 | Per-pair residuals computed correctly, cross-family pairs flagged | unit | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k residuals -x` | ❌ Wave 0 |
| D-08 | Extracted game loop produces byte-identical results to the pre-extraction bot harness on a fixed seed (no behavior change) | integration | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs` (existing check — must still pass unchanged after extraction) | ✅ (pre-existing) |
| D-09 | `parseAnchorSpec('sf8')`/`parseAnchorSpec('sf10')` no longer throw | unit | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchors.check.mjs` (new, mirrors `calibration-elo.check.mjs` style) | ❌ Wave 0 |
| D-01/D-02 | Probe→measure gate correctly keeps [0.2,0.8]-band pairs and drops/re-targets others on a synthesized fixture | unit | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchor-schedule.check.mjs` (new) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** run the relevant `.check.mjs`/`pytest -k <keyword>` for the piece
  just built — the real multi-hour engine run is NOT part of this cadence.
- **Per wave merge:** full `uv run pytest -n auto` + all new `.check.mjs` files run once.
- **Phase gate:** the actual D-11 execution (the real, hours-long anchor-vs-anchor run
  producing the D-12 artifacts) is a distinct, separately-tracked step — it is the
  phase's actual deliverable, not a test, and should be run only after every unit-level
  check above is green (running the real multi-hour sweep against buggy fit/schedule
  code would waste exactly the CPU-hours D-01 exists to conserve).

### Wave 0 Gaps

- [ ] `tests/scripts/test_calibration_anchor_fit.py` — covers D-04, D-05, D-06 (new file)
- [ ] `scripts/lib/calibration-game-loop.check.mjs` — structural check for the extracted
      game loop, mirroring `calibration-pruning.check.mjs`'s synthesized-fixture style
      (new file)
- [ ] `scripts/lib/calibration-anchor-schedule.check.mjs` — covers D-01/D-02/D-04's
      probe/measure gate + connectivity guard as pure logic (new file)
- [ ] A small synthetic-fixture module or inline test data with KNOWN ground-truth
      anchor strengths and a hand-computable expected fit result, so the Zermelo/MM
      convergence test has a real correctness oracle (not just "did it converge to
      SOMETHING") — needed before D-05's fit-converges test can be written meaningfully

## Security Domain

`workflow.nyquist_validation` is `true` in `.planning/config.json`; `security_enforcement`
is absent from `workflow`, so per protocol it is treated as enabled. This phase is a
locally-run, developer-invoked CLI tool with no network-facing surface, no user input
beyond CLI flags typed by Adrian himself, no auth/session, no persistence to the
production database, and no PII. Most ASVS categories are structurally not applicable.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local CLI tool |
| V3 Session Management | no | No sessions — stateless CLI invocations |
| V4 Access Control | no | Single local operator (Adrian), no multi-user boundary |
| V5 Input Validation | yes (minimal) | CLI flag parsing — reuse the existing harness's `requireFlagValue`/`parsePositiveIntFlag`/`parseIntList` validation discipline (fail loudly on malformed `--anchors`/`--games-per-probe`/etc. flags) rather than silently defaulting |
| V6 Cryptography | no | No cryptographic operations anywhere in this pipeline |

### Known Threat Patterns for {stack}

Not applicable — this is an offline, local, single-operator measurement tool with no
external attack surface (no network listener, no untrusted input source, no shared
credentials). The one general-purpose discipline worth carrying over from the existing
harness: CLI flag parsing should fail loudly on malformed input (WR-02 discipline,
already established in `calibration-harness.mjs`) rather than silently coercing bad
input into a default — this is a correctness/reproducibility concern for a research tool,
not a security boundary.

## Sources

### Primary (HIGH confidence)
- `scripts/calibration-harness.mjs`, `scripts/lib/calibration-anchors.mjs`,
  `scripts/lib/calibration-providers.mjs`, `scripts/lib/stockfish-pool.mjs`,
  `scripts/lib/calibration-openings.mjs`, `scripts/lib/node-engine-providers.mjs`,
  `scripts/lib/calibration-elo.mjs`, `scripts/lib/frontend-alias-hook.mjs` — read
  directly this session, exact contracts and conventions confirmed
- `scripts/lib/calibration-elo.check.mjs`, `calibration-pruning.check.mjs` — read
  directly this session, confirmed the `.check.mjs` testing convention
- `frontend/src/lib/maiaEncoding.ts` (`MAIA_ELO_LADDER`) — read directly this session
- `pyproject.toml`, `tests/scripts/test_backfill_eval.py` (existence confirmed via
  find) — confirmed no existing numpy/scipy dependency and the `tests/scripts/`
  precedent for testing `scripts/*.py` files
- `uv pip install --dry-run numpy` — confirmed numpy resolves to 2.5.1 against the
  live PyPI registry this session
- `.planning/seeds/SEED-101-anchor-ladder-self-calibration.md`,
  `.planning/notes/2026-07-13-bot-calibration-findings.md`,
  `.planning/seeds/SEED-102-iso-strength-surface-sweep.md`,
  `.planning/milestones/v2.3-phases/168-headless-calibration-harness-spike-gated/168-RESEARCH.md`
  — read directly this session, canonical references per CONTEXT.md

### Secondary (MEDIUM confidence)
- WebSearch on Bradley-Terry model MLE / Zermelo iteration — general web search,
  cross-checked against training-data knowledge of the algorithm (Hunter 2004 MM
  algorithm generalization); the specific fixed-point formula quoted matches standard
  references
- `gsd-tools query package-legitimacy check` — tool-verified verdict (SUS) for
  numpy/scipy, interpreted with the false-positive caveat documented in the Package
  Legitimacy Audit

### Tertiary (LOW confidence)
- WebSearch on Stockfish Skill Level 8/10 → Elo — multiple inconsistent
  community-reported tables found (picochess groups, lichess forum posts), none
  authoritative for Stockfish 18 at these specific levels; used only to sanity-check
  the proposed sf8/sf10 folklore extension is in a plausible ballpark, not as a
  verified value (see Assumptions Log A1)

## Metadata

**Confidence breakdown:**
- Standard stack / harness reuse: HIGH — every reused module was read directly from
  source this session; the extraction requirement (D-08) is unambiguous from the code
- Rating-model math (Zermelo/MM, bootstrap CI, connectivity): HIGH — standard, decades-old
  statistical methodology, not project-specific or fast-moving
- Probe→measure scheduling algorithm design: MEDIUM — CONTEXT.md deliberately leaves the
  exact mechanics to Claude's discretion; this document proposes a specific, reasoned
  design but the planner should treat the scheduling details (not the D-01/D-02/D-04
  constraints themselves) as adjustable
- Package legitimacy (numpy/scipy): MEDIUM — existence/version verified via uv, but the
  SUS verdict interpretation relies on training-data knowledge of these packages' actual
  standing, tagged ASSUMED per provenance rule; moot given the stdlib-only recommendation
- SF Skill 8/10 nominal Elo values: LOW — explicitly flagged as folklore-tier and
  irrelevant to the actual fit (CONTEXT.md's own words)

**Research date:** 2026-07-15
**Valid until:** 60 days (this phase's dependencies are all internal, already-frozen
project artifacts — vendored engine binaries, existing lib modules, Python/Node
toolchain — nothing here is expected to move faster than the project's own release
cadence)
