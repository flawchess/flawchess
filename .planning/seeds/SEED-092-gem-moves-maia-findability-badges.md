---
title: Gem moves — Maia-findability move badges on /analysis (frontend-only)
trigger_condition: Next /gsd-new-milestone selection; phase-sized frontend feature
planted_date: 2026-07-10
source: /gsd-explore session 2026-07-10 (Adrian's chess.com "great move" idea, refined into a Maia-native concept)
---

# SEED-092: Gem moves — Maia-findability move badges

Positive counterpart to the flaw glyphs (`??`/`?`/`?!`): badge the rare move that is both
the engine's clearly-only good move AND hard for a human at the player's rating to find.
Named **"Gem"** (deliberately NOT "Great"/"Brilliant" — chess.com users have firm priors:
Brilliant = sacrifice, Great invites 1:1 comparison with their different classifier).
Pure frontend feature on `/analysis`; no cross-game statistics, no backend changes.

## Detection rule (two conditions, both required)

- **C1 — hard to find:** Maia policy probability of the played move ≤ `GEM_MAIA_MAX_PROB`
  (~3% starting point) at the **rating-matched** Maia model. ELO-adaptivity is free: the
  probability is already conditioned on rating, and the app's `MAIA_ELO_LADDER` spans
  600-2600 step 100 (as on maiachess.com; see `lib/maiaEncoding.ts` / `useMaiaEngine.ts`),
  covering essentially all user ratings.
- **C2 — only good move:** expected score of the played move minus the best *alternative*
  ≥ `MISTAKE_DROP` (0.10, from `@/generated/flawThresholds`). Uses the existing
  `evalToExpectedScore` sigmoid (`lib/liveFlaw.ts`) — no new math. C2 implicitly requires
  the move to be the engine best (no alternative can out-score it), so no separate
  "is best" condition. Reads as: *"every alternative would have been at least a mistake."*

**Free-lunch guards (verify in tests, don't hand-code):**
- Sigmoid saturation suppresses already-decided positions (gap between +800cp and +400cp
  is negligible in es space) — no explicit "already winning" guard needed.
- Forced recaptures / only-legal-moves have high Maia probability → excluded by C1 — no
  recapture heuristic needed.

**Open tunables for UAT:**
- Exact `GEM_MAIA_MAX_PROB` cutoff (3% is a starting point; consider tying to
  `pRefForElo` from `lib/engine/findability.ts` instead of a flat cutoff).
- Best-try-in-a-lost-position (es 0.05 → 0.20 vs alternatives at 0.05) qualifies under
  these rules. Chesskit excludes still-losing moves; leaning toward KEEPING them (finding
  the only defensive resource deserves celebration), but taste call.
- Min-depth stability gate: only classify once the grading/free run reaches a minimum
  depth, and cache per ply, so badges don't flicker as MultiPV reorders.

## Coverage: lazy, per visited position (locked)

No background full-game sweep. As the user steps through a game, the existing MultiPV=2
free run (`useStockfishEngine`, MULTIPV=2) + grading run already produce best/second-best
expected scores, and `useMaiaEngine` produces the move probabilities. Badge appears once
data for the visited ply is available; move list fills in progressively. Cache grades per
ply across navigation.

## Surfaces (all Maia-violet, `MAIA_ACCENT` from theme.ts)

- Board corner marker + move-list glyph: violet circle, white `!` — extends the
  `SEVERITY_GLYPH`/`boardMarkers` pattern. Note `FlawSeverity` is negative-only; Gem is
  a parallel positive tier — extend `MoveQuality` (6th bucket overriding "best") rather
  than widening `FlawSeverity`.
- `MovesByRatingChart`: qualifying move's probability curve rendered in `MAIA_ACCENT`
  instead of its quality-bucket color, plus tooltip label. (The rising-with-ELO curve is
  itself the visual justification for the badge.)
- Tooltip/popover copy: short, e.g. "Gem — players at your rating almost never find this."

## Research: how OSS "game review" clones define Great (2026-07-10)

All gate on best-vs-second gap + played == best; none use a policy-network obviousness
filter — the Maia gate is novel among them.

| Project | Core rule | Guards |
|---|---|---|
| WintrCat/freechess (`src/lib/analysis.ts`) | played = BEST, gap to 2nd ≥ 150cp, previous opponent move was a BLUNDER, cp-only (no mates) | not a hanging-piece capture; blunders downgraded when eval ≥ +600 / ≤ −600 |
| GuillaumeSD/Chesskit (`moveClassification.ts`, "Perfect") | winPctDiff ≥ −2, then outcome-flip across 50% with gain > 10 OR only-good-move gap > 10 winPct | no simple recaptures, not losing after move (winPct < 50), alternative not already > 97 |
| en-croissant (`src/utils/annotation.ts`) | played = top MultiPV move AND winChance(best) − winChance(2nd) > 10 AND gained > 5 vs two plies ago | lichess sigmoid (same K as ours) |

Chess.com itself: rating-conditioned Expected Points model, no public thresholds; no
credible quantitative reverse-engineering exists beyond these clones. Chesskit's 10 winPct
== our `MISTAKE_DROP` exactly, which is why C2 reuses it.
