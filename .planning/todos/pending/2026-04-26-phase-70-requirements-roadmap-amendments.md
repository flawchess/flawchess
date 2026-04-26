---
created: 2026-04-26T00:00:00.000Z
title: Phase 70 — REQUIREMENTS / ROADMAP / CHANGELOG amendments
area: planning
files:
  - .planning/REQUIREMENTS.md
  - .planning/milestones/v1.13-ROADMAP.md
  - CHANGELOG.md
phase: 70
---

## Why

Phase 70's algorithm was redesigned during a `/gsd-explore` session on 2026-04-26 (see `.planning/phases/70-backend-opening-insights-service/70-DISCUSSION-LOG.md` § "Post-Discussion Redesign"). The locked decisions are captured in CONTEXT.md but the upstream requirements + roadmap + changelog haven't been edited yet. They must land in the same commit as the implementation so future readers don't see a stale spec.

This todo is the executor's checklist — nothing to design, just edits to apply.

## What

Apply these edits **in the same commit as the Phase 70 implementation lands** (do NOT split into a separate prep commit — they're load-bearing on the implementation).

### 1. `.planning/REQUIREMENTS.md`

- **INSIGHT-CORE-02** — rewrite end-to-end. Old: "scan top-N most-played openings per color × per-position next-moves". New: "single SQL transition aggregation per (user, color) over `game_positions` in entry_ply ∈ [3, 16] grouping by `(entry_hash, candidate_san)` with `n_games ≥ 20`". Explicitly note that bookmarks are NOT an algorithmic input.
- **INSIGHT-CORE-04** — change `MIN_GAMES_PER_CANDIDATE` from `10` to `20`.
- **INSIGHT-CORE-05** — change classifier from `score = (W + D/2) / n ≥ 0.60` to:
  - `weakness` if `loss_rate = L/n > 0.55`
  - `strength` if `win_rate = W/n > 0.55`
  - severity tier `major` if qualifying rate `≥ 0.60`, else `minor`.
  Strict `>` boundary at 0.55 (matches `frontend/src/lib/arrowColor.ts`).

### 2. `.planning/milestones/v1.13-ROADMAP.md`

Phase 70 block:

- Success-criterion 2 — rewrite from "scan top-10 most-played openings per color" to "single SQL transition aggregation in entry_ply [3, 16] with `n ≥ 20` per candidate". Drop any mention of bookmarks as input.
- Success-criterion 4 — ranking formula resolution: "sort by (severity desc, n_games desc), cap 5 weaknesses + 3 strengths per color".
- Add a sub-bullet under Phase 70 deliverables: "New Alembic migration adds `ix_gp_user_game_ply` partial composite index on `game_positions(user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17`."

### 3. `CHANGELOG.md` § `[Unreleased]` / `### Changed`

One bullet covering the change. Suggested text:

```
- Phase 70: Opening insights algorithm rewritten from "top-N most-played opening entry scan" to a first-principles single-SQL transition aggregation. Discovers strengths and weaknesses several plies deeper than the prior design (verified against the Caro-Kann Hillbilly Attack worked example). Classifier now uses `win_rate > 0.55` / `loss_rate > 0.55` with a severity tier at `≥ 0.60`, exactly matching the board arrow coloring in `frontend/src/lib/arrowColor.ts`. New `ix_gp_user_game_ply` partial composite index keeps the per-request latency under 1 s even for users with 65k+ games.
```

(Final wording is the executor's call — keep it terse and user-facing per CLAUDE.md changelog rules.)

## Done when

- All three files updated, ty/lint/test pass, single commit lands implementation + amendments together.
- The REQUIREMENTS file's INSIGHT-CORE-02 / INSIGHT-CORE-04 / INSIGHT-CORE-05 wording matches the constants in `app/services/opening_insights_service.py` exactly.
