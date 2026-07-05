---
id: SEED-083
status: promoted
promoted_to: Phase 151.1 (inserted 2026-07-05, v1.32 milestone)
planted: 2026-07-05
planted_during: Phase 151 in-flight (Maia-in-the-browser shipping); planning next Maia-enrichment work
trigger_when: PROMOTED to Phase 151.1 — run /gsd-plan-phase 151.1 to break down
scope: small-medium (one browser-only phase; extends the existing client Stockfish + Maia surfaces, no DB/backend)
source: /gsd-explore session 2026-07-05; maiachess.com reference image; research of CSSLab/maia-platform-frontend
related: SEED-081 (Maia-3 human-move enrichment milestone), SEED-082 (human-playable-line engine), SEED-012 (client-side Stockfish tactics)
---

# SEED-083: Stockfish-graded Maia moves on the Moves-by-Rating chart

Phase 151 added Maia-3 human-move probabilities client-side and renders them as the
**Moves-by-Rating chart** (one probability line per candidate move across the ELO ladder).
Today those lines are colored by **identity/role** (best = green, played = warm, others = a
muted cycling palette) and the line set is capped at **top-6-by-peak ∪ {played, best}**.

The missing half: the chart shows *which moves humans play* but not *how good each one is*.
On-brand for FlawChess ("Engines are flawless, humans play FlawChess"), the whole point is to
make the **human trap** visible — a move many players at your level pick that Stockfish grades
as a mistake. maiachess.com does exactly this: it colors each human move by Stockfish quality.

**This seed: grade each shown Maia move with the existing client Stockfish and recolor the
chart lines by quality (dark-green best → red blunder), and replace the fixed top-6 cap with a
"moves people actually play" candidate set so we stop drawing near-zero-probability clutter.**

Explicitly a follow-on to Phase 151, which locked eval-grading OUT of scope. Browser-only,
ephemeral, zero DB writes — same posture as the rest of the Maia surface.

---

## Locked design decisions (from the /gsd-explore session)

**D-1 — Surface: recolor the chart only.** No new maiachess-style move-list table. Color each
Moves-by-Rating line + its end-of-line SAN label by Stockfish quality. Color now encodes
*quality*, not identity; the SAN labels (already drawn at each line's right end) carry identity,
and played/best emphasis stays as **stroke width** (independent of color). Rationale: FlawChess
deliberately chose a chart-only Human panel in Phase 151; a table is a separate addition we
didn't want.

**D-2 — Candidate set: Maia cumulative-probability ≥ 0.95 ∪ {SF-best}, not fixed top-N.**
Accumulate Maia's sorted moves (at the selected ELO) until 95% of the probability mass is
covered, then force-include the Stockfish best move even if it falls below the cut. This is the
maiachess rule (verified in their source) and directly delivers the user's "don't always show 6,
only the important ones": sharp positions → few lines, quiet positions → more, and the long tail
of ~0% moves disappears. The **coloring** makes the teaching moment (a popular move graded red)
pop by itself — no separate "tempting-blunder" selection heuristic needed. (The 0.95 mass
threshold and whether to also cap at an absolute max line count are plan-time tunables.)

**D-3 — Colors: 5 buckets built on FlawChess's OWN existing thresholds — do NOT copy maiachess's.**
Reuse `frontend/src/lib/liveFlaw.ts` (`evalToExpectedScore` + `classifyLiveSeverity`) and the
generated `flawThresholds.ts` — the same expected-score-drop bands the rest of the product uses.
The user's 5 requested colors map straight onto them:

| Color | Meaning | Rule (expected-score drop vs best) |
|-------|---------|-----------------------------------|
| dark green | best | the Stockfish #1 move (drop ≈ 0) |
| light green | good | clean, non-best (drop < 0.05) |
| yellow | inaccuracy | 0.05 ≤ drop < 0.10 (`INACCURACY_DROP`) |
| orange | mistake | 0.10 ≤ drop < 0.15 (`MISTAKE_DROP`) |
| red | blunder | drop ≥ 0.15 (`BLUNDER_DROP`) |

Only "best" and "good" are new on top of the existing 3 severity bands. Keeping FlawChess's own
thresholds (which have a finer mistake band maiachess lacks) preserves consistency with game
analysis / live-flaw coloring elsewhere in the app. The theme colors belong in `theme.ts`.

**D-4 — Eval acquisition: ONE Stockfish search with `searchmoves` + MultiPV, not N child searches.**
The feasibility crux, resolved by researching CSSLab/maia-platform-frontend. They do NOT
evaluate each candidate's child position separately. They run a single root search and force-feed
the Maia candidate moves via UCI `searchmoves` (+ staged deepening), so every human candidate
gets a real root eval in one search — even moves outside Stockfish's natural top list. For
FlawChess: `go depth N searchmoves <m1 m2 …>` with `MultiPV = |candidates|` → one search, one
eval per shown move, no coverage gap, no per-move floor hack. This collapses the "N searches per
board navigation" cost worry.

---

## maiachess.com internals (research findings, for reference)

From CSSLab/maia-platform-frontend (`src/lib/engine/stockfish.ts`, `useAnalysisController`,
`components/Analysis/MovesByRating.tsx`, `constants/analysis.ts`):

- **Eval:** `Engine.streamEvaluations(fen, …, {maiaCandidateMoves, …})`, default `targetDepth 18`,
  min depth 12. Default strategy `staged-root-probe` (shallow screen → deepen Maia candidates →
  full MultiPV to target → deepen Maia moves to target). Alt strategies `multipv-all`
  (`MultiPV 100`) and `searchmoves-all` (per-move `searchmoves`). Build: `lila-stockfish-web`
  (`sf17`, NNUE), depth-bounded (no nodes/movetime cap). Returns `winrate_loss_vec` (preferred)
  and `cp_relative_vec` (fallback), keyed by move.
- **Candidate set:** Maia policy, sorted, accumulated until **cumulative prob ≥ 0.95** (legal
  moves only). The chart plots every move in that set — no top-N/threshold in the chart itself.
- **Colors:** win-probability loss vs best move — only **3** classes (`good ≥ −0.05`,
  `ok −0.10…−0.05`, `blunder < −0.10`). The dark-green→red gradient is *within-category ranking*
  (index into `COLORS.good[]/ok[]/blunder[]` by rank inside the category), not 5 distinct
  thresholds. "Excellent" (≥+0.05 winrate over weighted avg AND <10% Maia prob) is a separate
  highlight. **FlawChess should use its own 4-band thresholds instead (D-3).**

---

## Open items to resolve at plan time (de-risk before building)

1. **`searchmoves` + high MultiPV on `stockfish-18-lite-single.js`** — confirm the vendored WASM
   build honors `searchmoves` combined with `MultiPV = |candidates|` (standard UCI, low risk but
   unverified on this exact build), and measure **per-board-navigation latency on mobile Safari**
   with Maia inference already running on every nav. This is the one real feasibility check; a
   ~30-min hands-on spike settles it. If latency is bad: cap candidate count, lower depth for the
   grading search, or debounce grading behind the primary position eval.
2. **Current client Stockfish is `MultiPV=2`** (`useStockfishEngine.ts`) — grading needs a second
   analysis mode (higher MultiPV + `searchmoves`) without disturbing the existing eval-bar / engine
   card. Decide: a second worker instance, a mode switch on the existing worker, or a dedicated
   grading pass. The engine-card variation tree must keep its current behavior.
3. **ELO interactivity** — the candidate set is ELO-dependent (95%-mass shifts as you drag the
   selector), so the shown/graded set changes with the ELO slider. Stockfish grades are
   position-only (ELO-independent) and cacheable per move; only the *displayed subset* changes.
   Confirm this feels right and isn't too churny while dragging.
4. **Played move in game mode** — decide whether the user's actually-played move is always shown
   and graded even if it's below the 0.95 cut (it usually won't be — but showing "you played a
   red move here" is the highest-value coaching signal).

## Recommendation

Promote to a **phase** in the next Maia-enrichment milestone (the SEED-081 follow-on). Scope is
one browser-only phase extending existing surfaces (`MovesByRatingChart.tsx`, `useMaiaEngine.ts`,
`useStockfishEngine.ts`, `liveFlaw.ts`, `theme.ts`) — no backend, no DB, no schema change. Start
the phase with open item #1 as a plan-time spike.
