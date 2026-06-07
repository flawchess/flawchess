# Phase 109: Per-Card Expected-Score Eval Chart (Games subtab) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 109-per-card-expected-score-eval-chart-games-subtab
**Areas discussed:** Inaccuracy detection, Inaccuracy tooltip tags, Inline payload shape, `game_flaws` materialization scope (architecture Q&A), Scope expansion — both players' flaws, Tooltip player/opponent label, Dot density

> Context: the frontend/visual contract was fully locked by `109-UI-SPEC.md`
> (created the same day via `/gsd-ui-phase`), which explicitly stated "no user
> input required" for its scope. Discussion therefore targeted only the backend
> builder semantics the UI-SPEC left open.

---

## Inaccuracy detection (D-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse mover-POV kernel | Detect inaccuracies via flaws_service's mover-POV drop logic (severity==inaccuracy, [0.05, 0.10)), filtered to the user's plies. Consistent with B/M, correct for black, zero drift. ROADMAP "white-perspective" wording treated as loose. | ✓ |
| Literal white-perspective drop | Implement a white-perspective ES-drop exactly as the ROADMAP reads. Diverges from B/M detection and is wrong for the black player. | |

**User's choice:** Reuse mover-POV kernel (Recommended).
**Notes:** Grounded by inspecting `flaws_service._run_all_moves_pass` — it already computes per-ply severity (incl. inaccuracy) from the mover's POV for both colors; `game_flaws` just persists M+B only (Phase 108 D-03).

---

## Inaccuracy tooltip tags (D-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Severity only, no tags | Inaccuracy tooltip shows "Inaccuracy" + eval, no tag list. No clock/attribution tag-enrichment pass for inaccuracies. B/M keep stored tags. | ✓ |
| Compute tags on the fly too | Run tag enrichment for inaccuracy plies to match B/M tooltips. More work per game, needs clock data; tags were never designed for inaccuracies. | |

**User's choice:** Severity only, no tags (Recommended).

---

## Inline payload shape & precision (D-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Typed EvalPoint[] + rounded ES, trust gzip | Ship the UI-SPEC's EvalPoint[] array-of-objects, round ES ~3 dp, rely on HTTP gzip. Planner verifies the gzipped delta is negligible. | ✓ |
| Columnar arrays | Parallel arrays (plies[]/es[]/eval_cp[]/eval_mate[]), mapped on the frontend. Smaller uncompressed but diverges from the UI-SPEC typed contract. | |
| Let the planner decide after measuring | Defer entirely to the plan after measuring the real payload delta. | |

**User's choice:** Typed EvalPoint[] + rounded ES, trust gzip (Recommended).

---

## `game_flaws` materialization scope (architecture Q&A — no question tool)

User asked two architecture questions mid-discussion: (1) "Would it be better to
also materialize inaccuracies in `game_flaws`?" (2) "How about materializing the
opponent's blunders and mistakes?" Recommendation given both times: **keep
`game_flaws` narrow** — governing principle is "materialize only what must be
indexed/filtered at query time; derive per-game display on the fly." Inaccuracies
and opponent flaws are per-game display for the chart (recompute is ~free,
FEN-free), and materializing would multiply rows, pollute the M+B-only Flaws
semantics, require a discriminator column + migration (opponent), and trigger an
all-users backfill. **User confirmed: "yes, keep it narrow."** Revisit only when
a cross-game filter/query consumer appears (SEED-037 Train; opponent-scouting).

## Scope expansion — show both players' flaws (owner-directed)

User added a requirement: show the **opponent's** B/M/I on the chart too, with
**unfilled circles for the opponent, filled circles for the player**, and
opponent B/M tooltips also showing tags. Accepted as an owner-directed scope
change (amends ROADMAP/LIBG-10 "dots = your flaws only"). Architecture impact:
served on the fly via the both-color kernel + FEN-free `_build_tags`; `game_flaws`
still NOT expanded (consistent with "keep it narrow" — display ≠ cross-game query).

## Tooltip player/opponent label

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — label "You" / "Opponent" | Tooltip severity line reads "You · Blunder" / "Opponent · Mistake"; unambiguous on hover since fill style isn't visible in tooltip text. | ✓ |
| No — severity + tags only | Rely on dot fill style for attribution; cleaner copy but ambiguous in isolation. | |

**User's choice:** Yes — label "You" / "Opponent" (Recommended).

## Dot density

| Option | Description | Selected |
|--------|-------------|----------|
| Keep all, tune sizes/opacity in implementation | Show every flaw both players; UI-SPEC/executor tunes radii + opacity for legibility. | ✓ |
| Opponent inaccuracies droppable if cluttered | Always show player B/M/I + opponent B/M; opponent inaccuracies optional. | |
| Let the UI-SPEC re-evaluate density | Defer density strategy to a UI-SPEC update. | |

**User's choice:** Keep all, tune sizes/opacity in implementation (Recommended).

## Claude's Discretion

- N+1 avoidance: single batched `game_positions` query for all 20 paginated games.
- Builder seam: reuse `flaws_service` helpers vs a lean local ES-series builder.
- Recharts Scatter-vs-custom-dot for flaw dots (UI-SPEC executor-validated fallback).
- Missing-eval plies: emit `es: null`; line breaks (`connectNulls={false}`, UI-SPEC).

## Resolved conflicts (no user question — clear call)

- **D-06 (ply-0 phase line):** ROADMAP/LIBG-10 imply a line at the opening
  (ply 0); the newer 109-UI-SPEC says ply 0 is implicit and gets no line (a line
  at the leftmost pixel is invisible). Resolved in favor of the UI-SPEC — at most
  two transition lines (middlegame, endgame).

## Deferred Ideas

- Materializing inaccuracies / opponent flaws in `game_flaws` — kept narrow
  (D-10); revisit only for a cross-game filter/query consumer.
- Analysis detail viewer + on-demand best-move endpoint — separate later phases (SEED-036).
- Columnar wire format — only if D-05's gzipped measurement shows a regression.
- Tags on inaccuracy dots — dropped (D-03); could return on user demand.
- `109-UI-SPEC.md` amendment for the dual-marker scheme — fold into the plan or
  re-run `/gsd-ui-phase 109`.
