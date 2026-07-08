# Phase 153: Pure Search Core (Guardrail + Backup + MCTS + Fallback) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 153-Pure Search Core (Guardrail + Backup + MCTS + Fallback)
**Areas discussed:** Selection policy, Root candidate union interface, Score semantics + RankedLine shape, Budget + snapshot contract

---

## Selection policy

### Q1: Budget-allocation rule for select.ts

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic PUCT (Recommended) | Walk from root via argmax Q + c·P·√N/(1+n), canonical tie-break, expand landed leaf | ✓ |
| Greedy prior-path expansion | Expand frontier node with highest product of path priors; no exploration term | |
| Value-weighted prior path | Path-prior × root-candidate value; best-first, tunnel-vision risk | |

### Q2: PUCT Q-term at non-root (all-expectation) nodes

| Option | Description | Selected |
|--------|-------------|----------|
| Chance-node-aware (Recommended) | Q-based UCB only at root; below root allocate by prior mass only (no Q term) | ✓ |
| Root-perspective Q everywhere | Uniform formula; biases refinement toward good-for-us replies | |
| Side-to-move negamax Q | Treats chance nodes as adversarial; contradicts expectation semantics | |

### Q3: Which children the backup expectation ranges over

| Option | Description | Selected |
|--------|-------------|----------|
| Full top-k set, best estimate (Recommended) | Subtree expectation if expanded, sigmoid(shallowEval) otherwise; no mass dropped | ✓ |
| Expanded subtrees only, renormalized | Literal roadmap-SC2 reading; drops mass, undefined at 1 visit | |
| Full set + unexpanded penalty | Pessimism haircut on shallow values; extra unprincipled knob | |

**Notes:** Clarifies ROADMAP SC2's "expectation over expanded children" wording; fixture must mix expanded + unexpanded children.

### Q4: Sequential vs parallel-ready core loop

| Option | Description | Selected |
|--------|-------------|----------|
| Parallel-ready core now (Recommended) | budget.concurrency in-flight expansions, virtual-visit marking; determinism at concurrency=1 + one concurrency=2 test | ✓ |
| Strictly sequential in 153 | Simplest loop; likely reopens mctsSearch.ts in Phase 154 | |

---

## Root candidate union interface

### Q1: How SF MultiPV root candidates enter the pure core

| Option | Description | Selected |
|--------|-------------|----------|
| extraRootMoves input (Recommended) | Optional extraRootMoves: string[] on SearchRunner; providers stay {policy, grade} | ✓ |
| Third provider method | rootCandidates(fen) on EngineProviders; awkward hook-state layering | |
| Defer union to Phase 155 | Maia-only root now; changes a declared-stable interface later | |

### Q2: Root exploration prior for SF-injected ~0-probability candidates

| Option | Description | Selected |
|--------|-------------|----------|
| Floor-boosted Maia prior (Recommended) | P_root = max(P_maia, ROOT_PRIOR_FLOOR) renormalized, exploration term only; values keep true priors | ✓ |
| Uniform root prior | Equal exploration weight at root; discards Maia's allocation signal | |
| True Maia prior, no floor | Honest but starves SF-injected moves of visits | |

---

## Score semantics + RankedLine shape

### Q1: Internal representation of practicalScore

| Option | Description | Selected |
|--------|-------------|----------|
| Expected score 0–1 (Recommended) | Native evalToExpectedScore space; display formatting is Phase 155's decision | ✓ |
| Pawn-equivalent centipawns | Matches "+0.9" copy literally; inverse-sigmoid roundtrip in core | |
| Store both fields | Redundant derivable field in the contract | |

### Q2: ELO parameterization in SearchBudget

| Option | Description | Selected |
|--------|-------------|----------|
| Color-keyed eloByColor (Recommended) | budget.elo = {w, b}; ELO picked purely from side-to-move color | ✓ |
| yourElo/opponentElo + convention | Perspective convention threaded through nodes; inversion-prone | |

### Q3: Move notation in core interfaces

| Option | Description | Selected |
|--------|-------------|----------|
| UCI throughout core (Recommended) | Matches maskAndSoftmax + pv[0]-keyed protocol; SAN only at display time | ✓ |
| SAN throughout core | As research examples sketched; per-node SAN generation + worse sort key | |

---

## Budget + snapshot contract

### Q1: What counts as one "node" toward maxNodes

| Option | Description | Selected |
|--------|-------------|----------|
| One expansion event (Recommended) | One policy() + one batched grade() = 1 node | ✓ |
| Per-candidate grade count | Finer cost model; budgets stop being comparable | |
| Tree nodes created | Tracks memory, not compute | |

### Q2: Where anytime-snapshot throttling lives

| Option | Description | Selected |
|--------|-------------|----------|
| Emit every expansion; hook throttles (Recommended) | No wall-clock in core; ENGINE-07 asserts full emission sequence | ✓ |
| Core throttles by node count | Hard-codes UI cadence into pure core | |
| Core throttles by wall clock | Date.now() in core breaks sequence determinism | |

### Q3: Engine ~90% mass truncation vs chart's 0.95

| Option | Description | Selected |
|--------|-------------|----------|
| Separate engine constant (Recommended) | POLICY_MASS_THRESHOLD ≈ 0.90 in lib/engine, independent of moveQuality.ts | ✓ |
| Reuse the chart's 0.95 | Couples search branching to a display constant | |

---

## Claude's Discretion

- Exact values of `c_puct`, `ROOT_PRIOR_FLOOR`, `POLICY_MASS_THRESHOLD`, `maxPlies` default (within 6–10)
- Virtual-visit/pending mechanics, tree data structures, async completion-loop structure
- Terminal-position (mate/stalemate) handling and mate-score representation in MoveGrade
- fallbackExpectimax internals (must reuse backup.ts behind the identical SearchRunner)

## Deferred Ideas

None from this discussion. Todo matches reviewed and not folded: WR-01 Tailwind score-axis label (cosmetic, unrelated), bitboard partial-position storage (backend, unrelated).
