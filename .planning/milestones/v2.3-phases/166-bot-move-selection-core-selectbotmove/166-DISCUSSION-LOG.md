# Phase 166: Bot Move Selection Core (`selectBotMove`) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-11
**Phase:** 166-bot-move-selection-core-selectbotmove
**Areas discussed:** Slider→mode mapping, Blend sharpness curve, API surface & harness reuse, Fallback & determinism

---

## Slider → mode mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Two regimes at center | 0.5–2.0 temperature slider IS the play-style slider; human half no-MCTS sampling the temperature-reshaped policy, Stockfish half MCTS + practical-score sampling | |
| Blend param, temp pinned | Slider is a blend `b∈[0,1]`; Maia inference always raw (temp=1); human end raw-Maia sample, Stockfish end argmax, between MCTS + sharpening; temperature dropped from selection | ✓ |
| Continuous double-duty | Slider drives both temperature and blend across 0.5–2.0; MCTS everywhere except the exact human endpoint | |

**User's choice:** Blend param, temp pinned (Model 2).
**Notes:** Chosen after working through the temperature-for-sampling subtlety. The `applyPolicyTemperature` transform's "Stockfish end = stronger" polarity only holds in the analysis *ranking* pipeline (reshaped policy is a prior; Stockfish grading + findability rescue the surfaced strong move). In a raw-*sampling* path the polarity inverts: flattening (T>1) samples rare human moves that skew toward blunders → noisier/weaker, not more engine-like. Using temperature for sampling would produce a non-monotonic (U-shaped) strength curve that breaks Phase 168 calibration. Raw Maia (T=1) is the canonical ELO-faithful human. User explicitly did not want a sub-Maia "loose/noisy" flatten setting.

---

## Blend sharpness curve

| Option | Description | Selected |
|--------|-------------|----------|
| Softmax temperature | `P ∝ exp(score/τ)`, `τ` decreasing as `b→1`; `τ→0` at `b=1` = argmax; handles scores clustered near 0.5; exact τ(b) harness-tunable | ✓ |
| Power weighting | `P ∝ score^γ`, γ rising with b; simpler/bounded but crushes near-0 scores and less controllable near 0.5 | |
| Argmax not pure at b=1 | keep a sliver of sampling at b=1 to avoid exploitable determinism; contradicts SC1 | |

**User's choice:** Softmax temperature — with a concrete default curve locked now (not left vague).
**Notes:** User questioned whether the calibration harness was needed at all and whether it needs user data. Clarified: the Phase 168 anchor harness is engine-vs-anchor self-play (raw Maia rungs + Stockfish skill levels), offline, zero users — distinct from the data-hungry user-results curve fitting, which is explicitly deferred to a later milestone. User then directed: lock a concrete default curve now, don't capture a revisit note. Locked: `τ(b) = TAU_MAX·(1−b)`, `TAU_MAX = 0.10`; `b=1` short-circuits to pure argmax (guard `τ≤ε`). Harness-refinable without a signature change.

---

## API surface & harness reuse

| Option | Description | Selected |
|--------|-------------|----------|
| Internal default, injectable | `selectBotMove` imports `mctsSearch` as the default `deps.search`; optional so tests can stub canned RankedLines; harness uses the real search | ✓ |
| Fully injected | `search` a required dep; max decoupling but every call site wires it and the harness could diverge from the app | |
| Hard-wired internal | `mctsSearch` fixed, not injectable; simplest signature but blend logic only testable via full search path | |

**User's choice:** Internal default, injectable.
**Notes:** Best-of-both — the harness cannot accidentally pass a search that diverges from the app's, while unit tests can still stub the search to test the pure blend/sampling logic on canned inputs. Confirmed the impure-orchestrator + pure-helpers split (`samplePolicy`, `sampleRankedLines`, `argmaxLine`, `fallbackMove`) and the `settings = {elo, blend, budget}` / `deps = {policy, grade, rng, search?}` shape.

---

## Fallback & determinism

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform-random legal | legal moves from FEN (chess.js), UCI-asc sort, pick uniformly via injected rng; terminal position (no legal moves) throws | ✓ |
| First legal (UCI-asc) | deterministically return the first legal move; maximally predictable but always the same dull move | |
| Best-effort then legal | argmax of any positive-weight prior first, else uniform-random legal; blurs the clean degenerate boundary | |

**User's choice:** Uniform-random legal move.
**Notes:** RNG interface (`deps.rng: () => number`), seeded `mulberry32` for tests/harness, and UCI-ascending cumulative-walk sampling were presented as locked recommendations and accepted implicitly alongside this choice. A no-legal-moves position is treated as a caller/precondition bug (game loop must detect end states first) → throw; SC5's "return a legal move rather than throw" governs a *degenerate policy*, not a terminal position.

---

## Claude's Discretion

- Exact module names/paths under `frontend/src/lib/engine/` (or a new `bot/` subdir).
- The `ε` threshold for the argmax short-circuit and the chess.js move-generation call shape.
- The `TAU_MAX = 0.10` default is locked but explicitly harness-refinable in Phase 168.

## Deferred Ideas

None — discussion stayed within phase scope. (User-results strength curve fitting remains out of this milestone per SEED-091 decision #3; the anchor harness needs no user data.)
