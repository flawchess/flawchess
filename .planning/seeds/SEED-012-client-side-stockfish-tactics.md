---
id: SEED-012
status: dormant
planted: 2026-05-09
planted_during: /gsd-explore session on offloading bulk Stockfish analysis to clients
trigger_when: tactics features come up on roadmap (likely during or after Library milestone — see SEED-036), OR when a user explicitly requests "find missed tactics" / "filter games by missed forks", OR when client-side Stockfish prerequisites land (COOP/COEP audit + iOS Safari verification)
scope: milestone (multi-phase) — eval pipeline + storage + tactics classifier + UI surfaces
---

# SEED-012: Client-side Stockfish for full-game eval coverage + tactics features

## Why This Matters

FlawChess currently slices games by **position** (Zobrist hash → WDL) and by **type** (endgame class). It cannot answer questions of the form "you missed a fork on move 23" or "you find pins 60% of the time but skewers only 30%". Doing so requires per-move engine evals across the entire game library, which the production server cannot afford to compute (a 4-vCPU Hetzner box cannot Stockfish-analyze every imported game; even just endgame entry positions are batched via `backfill_eval.py`).

The unlock is **client-side bulk analysis via `stockfish.wasm`** (Lichess-maintained, NNUE, multi-threaded via SharedArrayBuffer + Web Workers). Modern clients reach ~1–3M nps single-threaded and 4× that with workers. Lichess does exactly this for "Request a computer analysis" — proven pattern.

Once per-move evals exist for a user's library, an entire feature family lights up:

1. **Tactics found/missed by type** — fork, pin, skewer, discovered attack, removing the defender. Needs a separate classifier on top of the engine output (see "Two-layer architecture" below).
2. **Filter games by missed tactics** — "show me games where I missed a fork" — feeds directly into the SEED-036 Library page game-level filter dimension.
3. **Stats by tactic type** — "you find forks 70% of the time, skewers 35%" — natural Insights surface.
4. **Move accuracy / ACPL** — Lichess-style accuracy %, blunder/mistake/inaccuracy classification per move, accuracy timeline.
5. **Opening eval insights** — "your London is +0.4 objectively but you score 40% — execution problem, not preparation."
6. **Time-pressure × accuracy correlation** — combined with existing clock data: "your accuracy collapses below 30s on the clock."

This seed is **the enabler** for SEED-036's deferred tactical-pattern filters and for several Insights surfaces that currently have no data source.

## When to Surface

**Trigger options:**
- During or after the Library milestone (SEED-036), when tactical filters become near-term.
- When a user explicitly asks for missed-tactics features.
- When the prerequisites land (see "Prerequisites" below) — at that point the seed is ready to promote to a milestone via `/gsd-new-milestone`.

**Do not surface yet** — the current calibration/insights/Library work has clearer ROI per engineering hour, and this seed has real prerequisites that should be researched before committing.

## Decisions Locked During Exploration

These are the design choices made during the `/gsd-explore` session on 2026-05-09. They should not be re-litigated unless new information surfaces; future planning should treat them as the starting point.

### 1. Bank everything, not just tactical moments

Store **every per-move eval**, not only the flagged tactical moments. Rationale: the marginal cost of persisting an eval once you've already paid the client-CPU cost is small, and the product roadmap (move accuracy, opening eval insights, time-vs-accuracy, ACPL graphs) keeps growing in directions that all want full eval coverage. Storing only flagged moments locks future features into re-running analysis.

This is a real commitment — it will become the largest table in the system, comparable to or larger than `game_positions`.

### 2. Position-keyed schema, not game-keyed

Evals are deterministic functions of `(position, engine_version, depth)`. Same Zobrist hash → same eval, always. Therefore the storage table is keyed on the position, not the (game, ply) pair:

```
position_evals(
  full_hash       BIGINT,
  sf_version      TEXT,
  depth           SMALLINT,
  eval_cp         INTEGER NULL,
  eval_mate       SMALLINT NULL,
  best_move_uci   TEXT,
  pv_san          TEXT,
  multipv_rank    SMALLINT,  -- 1 for best line; 2-3 if multiPV pass was run
  computed_at     TIMESTAMPTZ,
  computed_by_user_id  -- audit only; not part of key
  PRIMARY KEY (full_hash, sf_version, depth, multipv_rank)
)
```

Two big wins:
- **Cross-user sharing** — opening positions are seen by thousands of users; the first user's evals serve everyone. Realistically saves 20–30% of work on the first 10–15 plies, near zero after that.
- **Cross-game dedup within one user** — repeat positions, transpositions, and especially endgame positions reuse evals.

Cost is one join (`game_positions` → `position_evals` on `full_hash`) at query time. Existing hash indexes make this cheap.

Engine upgrades do not invalidate old data — `(sf_version, depth)` is part of the key, so v17 evals coexist with v16 evals and queries pick whichever set is preferred.

### 3. Opt-in, batched, explicit UX

User picks filters ("analyze my last 200 rapid games" or "all bullet games from the past 90 days") and runs that batch only. Closer to the existing import-flow mental model. **Not** background-while-browsing (feels like spyware-fan-noise) and **not** a single "analyze everything" button (multi-day jobs need bounded scope to feel sane).

Implication: **tactics features in the UI must communicate that they only operate on analyzed subsets.** Most filters in Library / Insights will need an "(only analyzed games)" indicator and a CTA to analyze more.

### 4. No eval validation / trust model — explicit non-goal

Clients can fake evals. **We do not validate.** Blast radius is the user's *own* tactics stats — no leaderboard, no shared aggregates, nothing to game. The position-keyed schema does mean one user's bad evals could corrupt another's queries, which is a real concern; mitigation is to scope cross-user sharing to *book/opening* positions (low value to fake) and keep middlegame/endgame evals user-scoped if abuse ever surfaces. Until there's a reason, punt on validation entirely.

This is recorded as an explicit non-goal so it doesn't get reinvented later.

### 5. Two-pass adaptive depth

Uniform depth-18 across all positions is wasteful. The pipeline should:

1. **Skip book** — match first 8–12 plies against the existing `openings` table; book moves don't need eval.
2. **Skip forced moves** — single legal move, or only one non-losing move (cheap legality check first, no engine call).
3. **First pass at d=10–12** (~5× faster than d=18) — flags candidate tactical moments where eval delta exceeds a threshold.
4. **Second pass at d=22 with multiPV=2 or 3** — only on flagged candidates. multiPV is needed for tactic classification (compare what was played vs alternative best lines).

Realistically reduces a first-time analysis from ~16 hours of background CPU per user (uniform d=18, all moves) to **~2–5 hours** for a user with 2k–5k games. Subsequent runs on newly-imported games are minutes per session.

## Two-Layer Architecture

The product feature is **tactics classification**, not raw evals. That decomposes into two layers:

1. **Engine layer (client, `stockfish.wasm`)** — finds *where* a tactic existed: positions where the played move's eval is much worse than the best move, or where mate-in-N was missed. Returns evals + best-line PVs to the server.
2. **Classifier layer (server, stateless)** — given `(position, best_move, played_move, eval_delta, pv)`, decides *what kind* of tactic it was: fork, pin, skewer, discovered attack, removing the defender, etc. This is rule-based or ML-based pattern recognition on the resulting position — not Stockfish's job.

The classifier is computed server-side after evals arrive, ideally as a stateless transform that can be re-run when classifier rules improve, without re-analyzing.

## Prerequisites — Must Research Before Promoting

These need to be answered before this seed can become a milestone. Both are real "could kill the idea" risks.

### Prerequisite 1: iOS Safari + SharedArrayBuffer + COOP/COEP

The multi-threaded `stockfish.wasm` path needs cross-origin isolation headers (`Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Embedder-Policy: require-corp`). iOS Safari is historically the most fragile here. Single-threaded fallback works but is 3–4× slower on phones, exactly where users care most about fans/battery.

**Open questions:**
- Does iOS Safari (current version) actually work with `stockfish.wasm` multi-threaded? Or fall back to single-threaded?
- What breaks on `flawchess.com` if we set COOP/COEP site-wide? Any third-party embeds (auth providers, image hosts, analytics) that would need `crossorigin` attributes or move behind a proxy?
- Can we scope COOP/COEP to a single sub-route (e.g. `/analyze`) instead of site-wide?

A research-spike (`/gsd-spike`) on this is the right next step before any planning.

### Prerequisite 2: Tactics classifier prior art

Building a tactic classifier from scratch is its own multi-week project. Open-source prior art exists:
- `lila-tactics` (Lichess) — Scala, but the heuristics are documented and portable.
- `chess-tactics` / `chess-tactics-classifier` — npm and PyPI packages of varying quality.
- Lichess Tactical Trainer dataset — labeled positions by tactic type, usable as training data or as a test set.

**Open questions:**
- What's the cleanest open-source primitive to vendor or port?
- Heuristic vs ML classifier — what's the accuracy floor for heuristics on the common patterns (fork/pin/skewer)?
- License compatibility with FlawChess (AGPL implications from Lichess code).

A research pass before planning would save a lot of churn.

## Storage & Compute Budget — Rough Estimates

For sizing decisions and gut-check on viability.

**Storage:**
- ~50 half-moves per game × ~30 bytes per eval row (eval_cp + best_move_uci + pv_san + version metadata) ≈ 1.5 KB per game.
- 1M games (current production order of magnitude) × 1.5 KB ≈ **1.5 GB raw**, perhaps 3 GB with indexes and multiPV expansion.
- With position-keyed dedup, realistically 30–50% smaller for the opening prefix and shared endgames.
- **Manageable on the current Hetzner box** (75 GB NVMe, currently using a small fraction). Not a blocker.

**Client compute (first run, per user, 2k–5k games):**
- Naive uniform d=18: 16+ hours background CPU.
- With book skipping + forced-move skipping + two-pass adaptive depth: **2–5 hours**, spread across multiple sessions.
- Subsequent runs on newly imported games: minutes.
- Phone (single-threaded fallback): 4× slower; explicitly advise desktop for first run.

**Server compute:**
- Classifier is stateless and cheap (rule-based on board state). Negligible.
- Receiving and persisting eval batches: I/O bound, comparable to the existing import pipeline.

## What This Seed Does NOT Cover

- **Server-side analysis fallback** — for users who never run client analysis, no evals exist. That's fine; tactics features are explicitly opt-in. Do not silently fall back to a server-side queue; that's the failure mode this seed is designed to avoid. **⚠️ Being reconsidered (2026-06-09) — see the server-side continuous-but-preemptible analysis amendment below. This non-goal was set when the box was 4-vCPU; the box is now CPX42 (8 vCPU / 16 GB) and SEED-040 surfaced that eval coverage is the gating bottleneck for the entire flaw-comparison feature.**
- **Real-time analysis during play** — out of scope. FlawChess is post-game analytics, not a play platform.
- **Cloud eval API integration** (chessdb.cn, lichess cloud eval, etc.) — possible future optimization for the opening prefix, but adds external-dependency risk. Not part of v1 of this seed.
- **Self-validation against tactical puzzles** — interesting product surface but separate from the pipeline.

## Amendment (2026-06-09): server-side continuous-but-preemptible analysis — reconsidering non-goal #1

Surfaced during the [[SEED-040-flaw-stats-opponent-comparison]] exploration. A Q-007
prod probe showed eval coverage is the **gating bottleneck** for the whole flaw-stats
opponent-comparison feature: per-user analyzed-game counts are strongly bimodal (median
6, only ~37–51 of 103 active users clear plausible floors), because **chess.com exposes
no Stockfish evals via its API** and lichess only when the user enabled analysis.

That reframes the client-only stance. The original non-goal #1 rejected a server-side
queue on a 4-vCPU box that genuinely couldn't afford it. The box is now CPX42 (8 vCPU /
16 GB), and the failure mode the non-goal feared (on-demand server analysis blocking the
API) is avoidable with a **continuous-but-preemptible drain** rather than an on-demand
fallback.

**The idea:** run Stockfish on the prod server **continuously** (up to ~6 of 8 cores),
disengaging fast whenever higher-priority work arrives, draining a **priority queue**
ordered by:
1. **Active users** — recent `last_activity` first (analysis serves who's actually here).
2. **More recent games** — recency matches what users view.
3. **Longer time controls** — higher analysis value, and bullet rarely has lichess evals
   anyway. Prefer longer-TC games that *lack* existing evals.

**Why it's attractive vs the client path:** works for ALL users with no client action,
is centrally trustworthy (sidesteps non-goal #4's fake-eval concern), and can reuse the
same position-keyed `position_evals` schema (Decision #2) so server and client work share
one dedup'd store. The two paths are complementary, not exclusive.

**Capacity — Stockfish was NOT the OOM cause (correcting an earlier draft of this
amendment).** The FLAWCHESS-3Q / 2026-03 / 2026-05 OOM-kills were **import memory
pressure**: oversized and concurrent game imports, import batch size, and SQLAlchemy
connection-pool exhaustion against host RAM. The 2026-05-21 incident involved no Stockfish
at all (pure chess.com import fetch + connection fan-out). So the box can dedicate **~6 of
8 cores to a constantly-running analysis drain** — not a single timid niced worker.

**The binding requirement is fast preemption, not low utilization:**
- **Yield immediately to higher-priority work** — uvicorn request handling, Postgres
  load, and especially the **import-time eval pass** (analysis must never compete with an
  active game import, which is where the real memory pressure lives). Implement via cgroup
  CPU quota / a load-or-import signal that pauses or scales down the workers within
  seconds, then resumes when clear.
- **Bound total memory so a concurrent import + workers + Postgres coexist within RAM** —
  this is the actual OOM lesson. Modest per-worker hash, capped worker count, headroom for
  import + Postgres. Core count is not the constraint; combined memory footprint is.
- **Adaptive depth (Decision #5) applies** — book/forced-move skipping + two-pass depth to
  keep per-game cost low.

**Status:** captured as an option to evaluate when the eval-pipeline milestone is scoped;
not yet a locked decision. It does not replace the client-side path — they can coexist
(server backfills the long tail; client handles a user's on-demand "analyze my last 200").
Promote/decide via `/gsd-new-milestone` or a focused `/gsd-discuss-phase` when SEED-040 or
tactics features go near-term.

## Amendment (2026-06-12): server-first v1 locked — /gsd-explore session decisions

Explored in a dedicated `/gsd-explore` session (user pushed this up the priority list as
the unlock for SEED-039 tactic tags and SEED-037 Train). The 2026-06-09 amendment's
"reconsidering" is now resolved: **non-goal #1 is reversed. v1 is server-side.** The
client-side path is deferred, not dead — see D-8.

### What already exists (the v1 delta is smaller than this seed assumed)

- `app/services/eval_drain.py` — a continuous background drain (Phase 91) already
  evaluates games with `evals_completed_at IS NULL`, with OOM-hardened short-transaction
  session discipline. Today it only targets ~2–3 plies/game (middlegame entry + endgame
  span entries).
- `app/services/engine.py` — `EnginePool` whose Stockfish processes run under
  **SCHED_IDLE**: the kernel preempts them instantly when uvicorn/Postgres want CPU. The
  "fast preemption" requirement from the 2026-06-09 amendment is already implemented at
  the kernel level.

The v1 work is therefore: an **all-ply target collector**, a **priority queue** replacing
the D-11 LIFO id-DESC pick, a **node-budget search** call, and the hybrid demand UX.

### Locked decisions (2026-06-12)

- **D-1 — Server-first v1; client path deferred.** Reverses non-goal #1.
- **D-2 — Coverage bar: full per-ply analysis of *recent games for active users*,** not
  the full library. Tactic features must show "(only analyzed games)" indicators + a CTA
  (decision #3's implication stands).
- **D-3 — Hybrid demand model.** Automatic window (last ~100–200 games) queued on import
  completion / user activity, so features light up by themselves; plus an explicit
  "analyze more" UX with progress (reuse the import-job mental model).
- **D-4 — Queue tiers + fairness.** Tier 1 explicit requests > tier 2 automatic windows >
  tier 3 idle backlog drain (cores never sit idle). **Round-robin per user within a
  tier** (one game each, cycle) so concurrent users all see steady progress;
  most-recent-game-first within a user.
- **D-5 — Storage: fill `game_positions.eval_cp/eval_mate` directly.** Supersedes
  decision #2's position-keyed `position_evals` table *for the server path* — that
  design was motivated by untrusted client writers and cross-user sharing; with the
  server as sole writer, the existing columns (already read by the flaw classifier and
  all stats) win. Dedup at compute time: before each engine call on **ply ≤ 20 only**,
  an indexed lookup by `full_hash` copies any existing server eval (hit rates collapse
  after the opening prefix). The position-keyed table may return if/when client workers
  land.
- **D-6 — Search budget: single pass, fixed 1,000,000 nodes/position, NNUE, multiPV=1
  (Lichess parity).** Supersedes decision #5's two-pass adaptive depth for the server
  drain. Researched 2026-06-12: lichess "Request a computer analysis" runs on fishnet
  volunteer clients at exactly this budget (lila `Work.scala`: `manualRequest =
  1_000_000` nodes; ~depth 20–23 in middlegames; judgements at winning-chances delta
  ≥0.3/0.2/0.1; accuracy formula at lichess.org/page/accuracy). **This is a calibration
  requirement, not a quality preference:** `game_flaws` rows and the Phase 114
  flaw-delta benchmark zones are computed from lichess %evals, which ARE fishnet
  1M-node evals. Depth-15 evals for chess.com games would put a shallower-eval
  population against zones calibrated on deeper evals. 1M nodes puts both platforms on
  one scale, and users can verify against lichess's own review.
- **D-7 — PV capture for SEED-039, no second pass.** The refutation line SEED-039 needs
  is the PV of the position *after* the flawed move — a position the all-ply pass
  analyzes anyway, and `analyse()` returns the PV alongside the score. Persist the PV
  for flaw-adjacent plies, discard the rest. (Planning detail: skip book plies except
  the *last* book position — the first non-book move needs an eval-before.)
- **D-8 — Pluggable-worker queue (the fishnet model).** Design the v1 queue so a worker
  is "anything that leases a job and posts back evals". The server `EnginePool` is the
  only v1 worker; the later client-side path (this seed's original stockfish.wasm idea)
  becomes browsers leasing jobs from the *same* queue into the *same* storage — not a
  second pipeline. This resolves the original client-vs-server question as "both,
  sequenced".

### Throughput (napkin — pending Q-008 benchmark)

~60 evaluated plies/game × 1M nodes at ~0.7–1.5M nps/core ≈ **1–2 min core-time per
game** → ~4–8k games/day on ~6 SCHED_IDLE cores. Initial catch-up for ~100 active users
× 200 recent games ≈ a week; one user's 200-game window ≈ 1–2 h; per-import increments
are minutes. Q-008 in `.planning/research/questions.md` pins the real number on the
CPX42 and sizes the automatic window.

**Status: promote-ready.** Prerequisite 1 (COOP/COEP / iOS Safari) is no longer a v1
blocker (client path deferred); prerequisite 2 (classifier prior art) was resolved by
SEED-039 (cook.py reimplementation). Promote via `/gsd-new-milestone` when prioritized.

## Cross-References

- **SEED-040** (flaw-stats opponent comparison) — the feature whose eval-coverage need
  surfaced this amendment; SEED-040 consumes the coverage this pipeline produces.
- **SEED-036** (Library milestone, split from SEED-010) — explicitly defers tactical-pattern filters until "Stockfish eval coverage or a client-side eval pipeline makes those reliable." This seed *is* that pipeline.
- `scripts/backfill_eval.py` — existing server-side backfill of endgame entry positions only. Stays as-is; the client-side path covers the rest.
- `app/repositories/query_utils.py` — existing shared filter layer; tactical filters added here.
