---
id: SEED-037
status: dormant
planted: 2026-06-04
planted_during: 2026-06-04 split of SEED-010 into Library (SEED-036) + Train (this seed)
lineage: split from SEED-010 (planted 2026-05-01, reworked 2026-06-03); SEED-010 closed
trigger_when: AFTER the Library milestone (SEED-036) ships — Train reuses Library's mistake-detection layer and best-move endpoint — OR when user invokes `/gsd-new-milestone` for Train
scope: milestone (multi-phase)
depends_on: SEED-036 (Library — mistake-detection service + single-position best-move endpoint)
---

# SEED-037: Train — spaced-repetition blunder drills

> **Lineage.** Split out of SEED-010 (now closed) on 2026-06-04. SEED-010's "Deferred extensions → Spaced-repetition blunder training (NEXT milestone)" section is the origin of this seed. The whole-game analysis page it depended on is **SEED-036 (Library)**.

## Why This Matters

This is the **retention play** — the feature that turns FlawChess from an analysis tool into a habit. Analysis tells a user *where* they went wrong; training makes them *stop* going wrong by re-presenting their own blunders on a spaced schedule until the pattern sticks. Aimchess monetizes essentially this at $7.99/mo; FlawChess differentiates on price (free/open) and on training from the user's *own* games rather than generic puzzles.

The mechanism: present the user positions from their recent games where they blundered and ask them to play a better move; if they repeat the blunder or play another weak move, show the original blunder and the better move; re-present the position on a later spaced interval (FSRS).

## When to Surface

- **After SEED-036 (Library) ships.** Train depends on Library's mistake-detection layer (which positions were blunders, with FEN + side + eval-before/after context) and on Library's single-position best-move endpoint (for move grading). Do not start Train before those exist.
- OR when the user invokes `/gsd-new-milestone` for Train.

## Hard dependency on SEED-036 (Library)

Train consumes two things Library builds, neither of which should be rebuilt here:
- **Mistake-detection service** — returns mistake plies with enough context (FEN, side to move, eval before/after) for the trainer to construct a drill directly. Library is required to keep this service cleanly reusable (the SEED-036 seed records this as a data-layer-awareness constraint).
- **Single-position best-move endpoint** (`POST /api/analysis/best-move`) — used for **move grading**: compare the user's chosen move's eval to the blunder and to the best line, evaluated server-side on demand, one position at a time. No client-side Stockfish required for v1. (Client-side engine remains a later option for offline/scale.) Because best move is computed on-demand (not stored), there is **no reimport risk** — the trainer just calls the same endpoint over the same derived mistake plies.

## The `/train-sketch` prototype — ALREADY BUILT

A throwaway clickable prototype exists and is wired up:
- **Route:** `/train-sketch` — an **unlinked public route** (not in any nav), reachable by anyone with the URL once deployed. Registered in `frontend/src/App.tsx` (outside the protected layout, no auth).
- **Code:** `frontend/src/pages/TrainSketch/` — `TrainSketchPage.tsx` (orchestrator), `QueueView.tsx`, `SolveView.tsx`, `FeedbackView.tsx`, `DoneView.tsx`, `EvalBar.tsx`, and `puzzles.ts` (mock/hard-coded data). Reuses the real chessboard component + Tailwind/theme so it's convincing.
- **Purpose:** kickoff artifact for **GM-coach collaboration** — the user plans to recruit an experienced GM coach to co-design the training UX (what actually helps students). The unlinked https URL is shared directly with the coach; no account needed.
- **Design intent (carried over):** build it as a real but **isolated** React route, deliberately diverging from `/gsd-sketch` (standalone HTML), because the prototype must be (a) reachable at a shareable https URL for an external person and (b) convincing via the real board/theme. Mock data only; no training backend exists yet. Self-contained under `frontend/src/pages/TrainSketch/` and clearly throwaway so it deletes cleanly once the design converges.
- **Exposure note:** an unlinked route is still publicly reachable — fine for a mock (no real user data); don't wire it to anything sensitive.
- **Cost note:** each iteration rides the normal prod deploy pipeline (PR `main → production`, `bin/deploy.sh`). Acceptable for a handful of iterations; if it churns a lot, consider a separate static host instead.

## Core training loop (settle with coach BEFORE building the real feature)

The loop must be settled first so we iterate the idea, not the sketch. Loop sketch:

> present position → user plays a move on the board → grade vs the single-position best-move endpoint → reveal (original blunder + better line) → schedule next rep (FSRS).

Open loop questions for the coach / discuss-phase:
- One attempt vs retry on a wrong move.
- Hint / give-up affordance.
- Show or hide the eval during solving.
- Daily-queue / streak surface.
- Red herrings (see Deferred / v2 below).

The `/train-sketch` prototype is the vehicle for resolving these with the coach.

## Scheduler — FSRS

Adopt **FSRS** (https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler) rather than rolling our own spaced-repetition math. Needs review-scheduler state per blunder (per user, per position).

## Move grading

Reuse the **single-position best-move endpoint** from SEED-036. v1 of training accepts "did you find a clearly-better move" by comparing the user's chosen move's eval to the blunder and the best line — evaluated server-side on demand, one position at a time. No client-side Stockfish required for v1.

## Name — TBD

Pick before the real feature build (the prototype route stays `/train-sketch` regardless). On-brand candidates lean into "flaws/fixing" (FlawChess — "humans play FlawChess"):
- *Fix / FlawFix*
- *Rematch / Comebacks* (replay your past mistake)
- plain *Train / Drills / Practice* (credible, coach-facing)

The current working name for the top-level page is **Train** (final nav `Import · Openings · Endgames · Library · Train`).

## Why this is a separate milestone, not part of Library

It's a second product pillar — review-scheduler state per blunder, interactive grading UI, progress/streak surface — and bundling it would balloon the Library milestone. Sequencing it right after Library keeps momentum while letting the archive/stats ship first. The data-layer reuse (mistake-detection + best-move endpoint) means Train adds product surface, not a new analysis backend.

## Deferred / v2 of training

### Red herrings

Positions with no clear single best move where the user did NOT err, mixed into the queue to avoid pattern-gaming (the user learning "there's always a tactic here" rather than reading the board). Treat as **training-v2**, not v1.

## Phase Decomposition (rough sketch — planner refines, after coach input)

The decomposition depends heavily on the coach-settled loop, so treat this as provisional:

1. **Drill data model + FSRS scheduler.** Per-user, per-blunder review state; FSRS integration; queue construction from Library's mistake-detection output.
2. **Grading service.** Wrap Library's best-move endpoint into a "was this move clearly better / still a blunder" verdict.
3. **Train page + solve loop (frontend).** Real route (replacing the throwaway sketch's design), board solve interaction, feedback reveal, queue/streak surface — built from the coach-validated prototype.
4. **Progress surface.** Streaks, due-today, retention-over-time.

(May merge/split depending on the loop the coach lands on. Red herrings explicitly deferred to a later phase/milestone.)

## Breadcrumbs

- `frontend/src/pages/TrainSketch/` — the existing clickable prototype (TrainSketchPage, QueueView, SolveView, FeedbackView, DoneView, EvalBar, puzzles.ts). Throwaway; the real feature replaces its design, not necessarily its file layout.
- `frontend/src/App.tsx` — `/train-sketch` route registration (unlinked, public, outside ProtectedLayout).
- **SEED-036 (Library)** — the milestone that must ship first; builds the mistake-detection service and the `POST /api/analysis/best-move` endpoint Train reuses.
- `app/services/eval_utils.py` — `eval_cp_to_expected_score` (Lichess sigmoid); the grading verdict is built on expected-score comparison, same mapping Library uses.
- **FSRS** — https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler
- **lichess-puzzler** — https://github.com/ornicar/lichess-puzzler — reference for turning eval swings into training positions.

## Source / decision log

**2026-06-04 split (user + Claude):**
- SEED-010 split into **SEED-036 (Library)** + **SEED-037 (Train, this seed)**; SEED-010 closed.
- Train owns: spaced-repetition trainer, FSRS scheduler, move grading, GM-coach collaboration, and the already-built `/train-sketch` prototype.

**2026-06-03 origin (carried over from SEED-010 "Deferred extensions"):**
- SR blunder-training is the **next milestone after Library**, FSRS-based, reuses the best-move endpoint, no reimport risk; red herrings are training-v2.
- GM coach to co-design the UX, kicked off with an iterable hosted prototype at the unlinked `/train-sketch` route (real isolated React route with mock data, reusing the real board/theme — not a gsd-sketch HTML file). Core training loop must be settled before building the real feature.
- Training name TBD.
