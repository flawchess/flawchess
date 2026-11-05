# Phase 245: Analysis Contextual Explain Bar for Flaws (SEED-208) - Context

**Gathered:** 2026-11-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A contextual Explain bar on the Analysis page (game mode). On a mistake or blunder ply (either side), one
click grafts the stored engine line (better line or refutation) into the move list, plays its first move, and
lets the user step through it with the normal Back/Forward controls. Got it closes the line and returns to
the flaw move. Frontend only: it reuses the existing tactic-lines endpoint and the tactic-chip line
machinery. Inaccuracies, free-play / what-if moves, coach prose and LLM text are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Carried forward from SEED-208 (locked in the explore session, not re-discussed)
- **D-01:** One Explain button only. No "Best" button (on the user's own flaws it duplicates Explain's first step) and no "Next" button (`useFastForward` "Jump to next key moment" already does it).
- **D-02:** No coach prose, no LLM. A guided stepper over stored PVs only.
- **D-03:** Contextual bar: under the move list on desktop, directly above the mobile footer on mobile (the footer is at its 5-column limit on a 360px phone). Shown only when the current node is an eligible flaw ply (see D-08) or inside that flaw's Explain line.
- **D-04:** Direction rule (same semantics as the tactic motif badges): the user's own flaw opens the MISSED PV forking at ply-1; the opponent's flaw opens the ALLOWED PV forking at the flaw ply. D-09 adds a fallback.
- **D-05:** Explain grafts the line and plays its first move immediately (unlike chips, which park at the fork node). For the allowed line, "first move" means the refutation: `allowed_moves[0]` is the prepended flaw move itself, which already sits on the main line.
- **D-06:** Back/Forward step through the line (`goForward` already prefers the PV child). There are no separate stepper buttons. While the board is in the line, Explain turns into "Got it", which closes the line (`deleteSubtree` + remove from `openLines`) and returns the board to the flaw move on the main line.
- **D-07:** Leaving the line any other way (move-list click, Jump, eval-chart scrub) keeps it open, like tactic chips; re-entering it shows Got it again. Chip and Explain share the `flawKey(ply, orientation)` line key, so a motif flaw never gets duplicate sidelines.

### Inaccuracy support
- **D-08:** **Inaccuracies are dropped from scope** (this revises the SEED-208/ROADMAP "every flaw including inaccuracies" bullet). `game_flaws` holds mistakes and blunders only (`app/services/library_service.py:457`); inaccuracy markers are synthesized from evals, so `GET /library/flaws/{game_id}/{ply}/tactic-lines` returns 404 for them. The owner chose not to add a backend fallback. Eligible plies are `flaw_markers` entries with `severity` of `mistake` or `blunder`, either side (`is_user` true or false), with or without a motif. The bar is hidden on inaccuracy plies. — **Reversibility:** reversible — adding inaccuracies later means a small backend fallback in `fetch_tactic_lines` (replay `game_positions.move_san` to rebuild the board when there is no `game_flaws` row) plus widening the eligibility check.

### Missing-PV handling
- **D-09:** **Fall back to the other line** when the direction-rule line is null. A user flaw without `missed_moves` opens the ALLOWED line (fork at the flaw ply); an opponent flaw without `allowed_moves` opens the MISSED line (fork at ply-1). The opened orientation is the one actually used, so the line key stays `flawKey(ply, <used orientation>)` and stays shared with that orientation's chip. Motivation: in dev, PV-complete games, about 20% of M/B flaws lack the missed PV, while only about 1% lack the allowed PV.
- **D-10:** **Hide the bar** when neither line exists (both PVs null; typical for games not yet PV-analyzed, where almost every flaw has neither). No disabled button and no tooltip.
- **D-11:** **Prefetch on landing.** When the board's current node is an eligible flaw ply, fire `useTacticLines(gameId, ply)` (TanStack-cached, same query key the Explain click and the chips use, so the click reuses the data). The bar appears only once the response shows at least one non-null line. Don't flash a button that might disappear: the bar stays hidden (no visible placeholder) until the data resolves. Frontend only; there is no `has_pv` flag on `FlawMarker`.

### UAT revision (owner, 2026-11-05): Best + Punish
Overrides D-01, D-04 and D-09, and amends D-06 and D-10. The single Explain button and its hidden direction rule are replaced by two named buttons, offered for either side's flaw:
- **Best** (lucide outline `Star` icon) opens the MISSED line: undo the mistake (fork preview at ply-1), then play the better move.
- **Punish** opens the ALLOWED line: the refutation from the flaw position.
- Both are `brand-outline` (two solid CTAs would break the one-primary rule; making one primary would reintroduce D-04). Order: Best, then Punish (Best starts one ply earlier).
- One usable line: the other button is **disabled**, not hidden, so the row layout is identical on every flaw. Neither usable: the bar stays hidden (D-10 unchanged for that case).
- Headline: the SAN in white (`text-foreground`), then the mistake/blunder move-quality badge icon (as in the move list); no "is a blunder" copy and no ??/? text glyphs.
- **No tactic chips in the bar** (owner, after trying a second row and then inline short chips): the move list's chips already carry them. The unreleased `explain-tactic` Umami target is removed.
- Inside a line (amends D-06): the headline is replaced by **Back/Forward stepper buttons clamped to the line** (Back stops at the fork; Forward from the fork enters this line), then the **sibling line's button** (closes this line, opens the other) and Got it.
- Umami: `explain-open` (never released) is replaced by `explain-best` / `explain-punish`; the switch button fires the same targets. Stepper clicks send nothing (high-frequency stepping).

### Claude's Discretion
- Bar copy, visuals, icon, dark-theme tokens: decided in `/gsd-ui-phase 245` (UI-SPEC). The owner did not pick a headline style (e.g. "Rc5 is a blunder"); leave that to the UI-SPEC.
- Deep-link tactic auto-open (`tacticOrientationAtPly`, `initialTactic`): **keep unchanged**. A deep link to a user tactic ply still auto-opens the missed line parked at the fork. Because the board is then inside an open line, the bar naturally shows Got it there. Don't extend auto-open to non-motif flaws.
- Umami event names (follow the existing kebab-case `data-umami-event` convention in `frontend/src/lib/analytics.ts`, e.g. `analysis-explain-open` / `analysis-explain-close`) and testids (follow `frontend/CLAUDE.md`).
- What the bar shows at a missed line's fork node (ply-1, a main-line node) when the user steps Back out of the line. Follow `findFocusedFlaw` semantics unless the UI-SPEC says otherwise.
- Interaction with fast-forward (`fastForward.isRunning`): hide or ignore the bar while the Jump animation runs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and locked decisions
- `.planning/seeds/SEED-208-analysis-explain-button.md` — locked decisions, chess.com reference observations, reuse map, breadcrumbs
- `.planning/ROADMAP.md` §"Phase 245" — goal and scope (its inaccuracy bullet is superseded by D-08)

### Frontend rules
- `frontend/CLAUDE.md` — styling, testids, Umami, frontend Sentry rules
- `frontend/src/lib/analytics.ts` — Umami tracking conventions

### Backend contract (read-only, no change expected)
- `app/repositories/library_repository.py` `fetch_tactic_lines` (~line 2266) — PV anchoring, `allowed_moves[0]` = flaw move prepend, null semantics
- `app/services/library_service.py` (~lines 200-420, 457) — how `flaw_markers` are built (both colours, inaccuracies synthesized from evals, M+B-only `game_flaws`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/pages/Analysis.tsx`: `handlePvChipClick` (~1776, toggle/open by `flawKey`), `openLines` / `pendingFlaw` state (~440), `findFocusedFlaw` (~292, fork-node equality OR subtree containment), `focusedPvLine` (~554), the `fetchFlaw = pendingFlaw ?? focusedFlaw` → `useTacticLines` wiring (~565), mobile footer `analysis-mobile-footer` (~2580).
- `frontend/src/hooks/useAnalysisBoard.ts`: `goForward` (~362) prefers the PV child; `insertPvLine`, `deleteSubtree`.
- `frontend/src/hooks/useLibrary.ts` `useTacticLines` — the prefetch in D-11 reuses this query.
- `frontend/src/lib/tacticOrientation.ts` + `forkPlyForOrientation` — fork ply per orientation.
- The graft effect in `useAnalysisRouteSeeding` / Analysis.tsx: records `pendingFlaw` into `openLines` once tactic-line data arrives. Explain needs one extra step after the graft: play (navigate to) the first move of the line.

### Established Patterns
- Flat sibling lines: opening one line never closes another, and the same key toggles.
- `findFocusedFlaw` and similar control flow live in module-scope pure functions because of the React Compiler memoization lint.
- Nesting depth ≤ 4 (eslint `max-depth`). `Analysis()` is an accepted complexity residual, so put the bar's logic in a hook (e.g. `useExplainBar`) plus a small component rather than growing `Analysis()`.

### Integration Points
- Desktop: below the move list in the analysis tabs column (`components/analysis/AnalysisTabs.tsx`).
- Mobile: a new row directly above `analysis-mobile-footer`; `BoardControls` itself stays 5-column.

</code_context>

<specifics>
## Specific Ideas

- Modelled on chess.com Game Review's Explain → Got it flow (observed 2026-11-05, details in SEED-208), minus the coach bubble and the Best/Next buttons.

</specifics>

<deferred>
## Deferred Ideas

- Explain for inaccuracies: needs the small `fetch_tactic_lines` fallback described in D-08. Possible follow-up seed if users ask.
- Explain for free-play / what-if moves graded live by `useLiveMoveFlaw` (no stored PV). Out of scope per ROADMAP.

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`, `2026-08-29-variation-tree-nested-button.md`: generic keyword matches, unrelated to this phase.

</deferred>

---

*Phase: 245-analysis-explain-bar*
*Context gathered: 2026-11-05*
