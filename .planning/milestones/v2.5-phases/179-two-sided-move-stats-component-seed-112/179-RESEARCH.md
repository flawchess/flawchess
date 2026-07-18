# Phase 179: Two-sided Move Stats component (SEED-112) - Research

**Researched:** 2026-07-18
**Domain:** Internal full-stack integration (FastAPI/Pydantic schema surfacing + React/TypeScript component extraction). No new external packages, no new libraries, no new infra.
**Confidence:** HIGH — every claim below is grounded in a direct read of the actual source files (line numbers cited), not framework documentation. This is a codebase-archaeology phase, not a "learn a new library" phase.

## Summary

This phase has one genuinely open technical question (CONTEXT.md's D-05 caveat: does the analysis-page payload carry the same both-side `flaw_markers`/`eval_series` data as the Library card?) and this research resolves it definitively: **yes, trivially and exactly** — `/analysis?game_id=X` does not have a separate "analysis payload" at all. It calls `GET /library/games/{game_id}` via `useLibraryGame` (`frontend/src/hooks/useLibrary.ts:263-274`), which returns the **exact same `GameFlawCard` Pydantic model** (`app/schemas/library.py:103`) built by the **exact same `_build_card()` function** (`app/services/library_service.py:471`) that powers the Library list. `AnalysisTagsPanel` already receives a `game: GameFlawCard` prop identical in shape to `LibraryGameCard`'s. There is no schema divergence to reconcile — D-05's backend delta really is just two nullable floats.

The backend change is now fully de-risked: `game.white_accuracy` / `game.black_accuracy` (Phase 178, `app/models/game.py:165-166`) are plain columns on the `Game` ORM object that `_build_card(game: Game, ...)` already has in scope — no new query, no new repository function, no new migration. Add two fields to `GameFlawCard`, pass them through in the one `GameFlawCard(...)` constructor call at `library_service.py:704-733`, done.

The frontend side is where the real work and real design risk live. Both target files already implement a near-identical `FlawRef` discriminated union + click-to-cycle + hover-highlight machinery (confirmed line-for-line below), which is good news for extraction — but three concrete gotchas surfaced during this research that CONTEXT.md does not mention and the planner must account for: (1) the frontend already has a **different, unrelated `MoveQuality` type** (`frontend/src/lib/moveQuality.ts`) sharing the same 7-bucket vocabulary for a completely different live-engine grading feature, with an explicit anti-pattern warning against merging it with `FlawSeverity` — the new Move Stats category type must NOT collide with either; (2) today's gem/great badges are **conditionally hidden when count=0** while severity badges always show 0 — D-03's "all 7 rows always render" is a deliberate behavior change from the current gem/great convention, and `AnalysisTagsPanel`'s current early-return-null-when-empty guard (line 240) directly contradicts D-03 and must be removed; (3) `SeverityBadge.tsx` cannot be deleted — a third file (`FlawCard.tsx`, out of scope) still consumes it for the Flaws-tab singular-flaw display, so only its usage in the two in-scope files gets replaced, while `GemGreatBadge.tsx` becomes fully orphaned and should be deleted.

**Primary recommendation:** Backend: add `white_accuracy: float | None` / `black_accuracy: float | None` to `GameFlawCard`, pass `game.white_accuracy` / `game.black_accuracy` straight through in `_build_card`'s constructor call — no new query, no repository change, no migration (Phase 178's migration already shipped to `main`). Frontend: extract a new `frontend/src/components/library/MoveStats.tsx` (same directory convention as `SeverityBadge.tsx`/`GemGreatBadge.tsx`), unify the existing `severity`/`bestMove` `FlawRef` kinds into a single `{ kind: 'category'; category: MoveStatCategory; side: 'white' | 'black' }` variant sourced by deriving side from ply parity (a new tiny helper alongside `isUserPly`), and delete `GemGreatBadge.tsx` once both call sites migrate.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Accuracy value computation | Database / Storage | — | Already computed and persisted by Phase 178 (`games.white_accuracy`/`black_accuracy`); this phase reads, never computes |
| Accuracy surfacing on card payload | API / Backend | — | `GameFlawCard` Pydantic model + `_build_card()` — thin passthrough, no logic |
| Per-(category × side) count derivation | Browser / Client | — | D-05 locked: computed client-side from `flaw_markers`/`eval_series` already on the payload; no new backend aggregation |
| Move Stats rendering (accuracy strip + table) | Browser / Client | — | New shared React component, two call sites (Library card, Analysis page) |
| Cycling / highlight / filter-ring wiring | Browser / Client | — | Extends existing client-side `FlawRef` + `useFlawFilterStore` machinery, no server round-trip |

## Package Legitimacy Audit

**Not applicable.** This phase adds zero new npm/PyPI packages. All work is new first-party code (a Pydantic model field, a React component) plus edits to existing first-party files. No `package-legitimacy check` run needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — Canonical accuracy only, else "—" (no `_imported` fallback).** The strip shows a number only when we computed it uniformly (Phase 178 canonical `white_accuracy`/`black_accuracy`). NULL → muted "—", never `*_accuracy_imported`.
- **D-02 — Accuracy % is the only headline number; ACPL is NOT surfaced.**
- **D-03 — All 7 rows render always; zero cells shown as a muted 0/"–".**
- **D-04 — Best/Good get new circular badge icons** consistent with the existing Gem/Great icons + severity glyphs. Reuse category colors from `theme.ts`.
- **D-05 — Backend delta is minimal: add per-color accuracy to the payloads; derive the 14 counts client-side from existing fields.** Do NOT add explicit per-side count objects to the API unless the planner finds a concrete blocker.
- **D-06 — Mobile collapsed default = accuracy strip + the USER's 3 severity counts (I/M/B).** Tap to expand the full two-sided 7-row table. Analysis board always shows the full table.
- **D-07 — Unanalyzed game (`analysis_state === 'no_engine_analysis'`): no strip, no table** — show the existing analyze pill. Analyzed-but-NULL-accuracy still renders the full table with a "—" strip.
- **D-08 — Opponent positive tiers are deliberately surfaced here**, reversing the user-scoped `isUserPly` badge behavior for THIS surface only.
- **D-09 — Cycling is per (category × side)**, up to 14 clickable targets. Extend the `FlawRef` discriminated union with a `side`/`color` dimension. Click new cell → jump to first ply; re-click → advance + wrap; different cell → reset. Hover a cell dims non-matching eval-chart markers. Zero cells are inert.
- **D-10 — The global flaw filter (`useFlawFilterStore`) stays user-scoped** and emphasizes only the player-side cell of the matching row. Opponent cells independently clickable for cycling but never targeted by the global filter. `outlinedPlies` behaves as today. (Library only.)
- **D-11 — Tactic motif chips + context tags STAY** as a chip section; desktop card sized to the miniboard height (~225px) beside the board.

### Claude's Discretion

- Exact `FlawRef` union shape for the side dimension, and whether to finally extract the shared `MoveStats` component vs keep the two files' "trivially safe copies" convention.
- Whether the analysis payload already exposes `flaw_markers` + `eval_series` identically to the library card (D-05 caveat) — **RESOLVED by this research: yes, byte-identically, same schema, same builder function.**
- `LibraryGameCard.tsx` is 1271 lines. Refactor-on-sight applies to any function touched, but scope the extraction to this phase's plan — flag, don't sprawl.

### Deferred Ideas (OUT OF SCOPE)

- Surfacing ACPL anywhere in the UI (D-02).
- Falling back to `*_imported` accuracy for coverage (D-01).
- Running the Phase 178 prod accuracy/ACPL backfill (operator step, not gated in this phase).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md requirement IDs are mapped to this phase — `.planning/REQUIREMENTS.md` in this repo covers the **v2.4 Backend Gem & Great Detection** milestone (GEMS/BOARD/FILT/BACK, all already Complete/Done). Phase 179 belongs to the **v2.5 Move Statistics** milestone (STATE.md), which was scoped directly from SEED-112 without a separate requirements-definition step — CONTEXT.md's `## Implementation Decisions` (D-01..D-11) is the authoritative requirement source for this phase; the planner should treat each D-id as a requirement line item.
</phase_requirements>

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-side per-category counts | A new backend aggregation endpoint/field | Client-side reduction over `game.flaw_markers` (filter `is_user`/derived side + `severity`) and `game.eval_series` (filter `best_move_tier`) | D-05, confirmed by this research: both fields already carry BOTH sides' full data for every analyzed game (see Code Examples below) — a new API surface would just duplicate data already on the wire |
| Category → color/icon mapping | New color tokens | `theme.ts`: `SEV_BLUNDER`/`SEV_MISTAKE`/`SEV_INACCURACY` (severities), `MAIA_ACCENT` (gem), `GREAT_ACCENT` (great), and **`MOVE_QUALITY_BEST`/`MOVE_QUALITY_GOOD`** (already exist — dark/light green, `theme.ts:456-457`) | All 7 category colors are already defined; D-04 only needs two new **icon shapes**, not new colors |
| Accuracy-strip cell background (white/dark) | A new "player color" theme token | `EVAL_BAR_WHITE`/`EVAL_BAR_BLACK` (`theme.ts:68-69`, aliasing `EVAL_CHART_AREA_WHITE_AHEAD`/`BLACK_AHEAD`) or `BOARD_LIGHT_SQUARE`/`BOARD_DARK_SQUARE` (`theme.ts:8-9`) | The app already has an established white/black visual convention for player-color surfaces (the eval bar); reuse it instead of inventing a third white/black pair |
| Mover-color-from-ply derivation | A new ad-hoc `ply % 2` inline check | New tiny helper alongside `isUserPly` in `frontend/src/lib/plyOwnership.ts` (e.g. `moverColorAtPly(ply): 'white' | 'black'`) | `isUserPly` only answers "is this the user's ply", not "which color is this ply" — no existing frontend helper answers the latter (backend has `mover_is_white_at_ply` / `mover_color_for_ply`, no frontend twin) |

**Key insight:** Every piece of data the new component's 7×2 table needs is already computed and shipped on the wire today — the phase is a pure UI/derivation exercise plus two schema fields, not a new-computation exercise. Resist the urge to add backend aggregation "for cleanliness"; D-05 explicitly rejects it, and this research found no correctness reason to override that.

## Architecture Patterns

### Current Data Flow (confirmed, both surfaces already share it)

```
Library Games list                    Analysis page (?game_id=X)
GET /library/games                    useLibraryGame(gameId)
        │                                      │
        ▼                                      ▼
library_service.get_library_games     library_service.get_library_game
        │                                      │
        └──────────────┬───────────────────────┘
                        ▼
              _build_card(game: Game, flaw_rows, is_analyzed,
                          positions, active_eval_status, ...)
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
   _build_eval_series()   severity_counts (user-only,
   → eval_series (BOTH      oracle I + game_flaws-derived M/B)
     sides, best_move_tier)
   → flaw_markers (BOTH
     sides, is_user flag)
                        │
                        ▼
              GameFlawCard (Pydantic) ── IDENTICAL response_model
                        │                for both endpoints
        ┌───────────────┴────────────────┐
        ▼                                ▼
LibraryGameCard.tsx                AnalysisTagsPanel.tsx
(game: GameFlawCard)               (game: GameFlawCard)
   own FlawRef union                  own FlawRef union
   own severityPlies/                 own severityPlies/
   bestMovePlies/cycling              bestMovePlies/cycling
   (near-identical duplicate logic)   (near-identical duplicate logic)
```

Both `LibraryGameCard.tsx:915-956` (`severityBadges`/`bestMoveBadges` derivation) and `AnalysisTagsPanel.tsx:264-297` (inline render) independently:
1. Filter `game.flaw_markers` by `is_user` to get I/M/B plies/counts (user only, today).
2. Filter `game.eval_series` by `best_move_tier === 'gem' | 'great'` + `isUserPly` to get gem/great plies/counts (user only, today).
3. Maintain their own `cycle`/`highlight` state and `pliesForRef`/`handleActivate` dispatch over a locally-declared `FlawRef` union.

This phase's job is to (a) widen step 1/2 to also collect the **opponent** side (drop the `is_user`/`isUserPly` filter, replace with a per-marker/per-point side derivation), and (b) extract steps 1-3 into one shared component/hook consumed by both files.

### Recommended Project Structure

```
frontend/src/
├── components/library/
│   ├── MoveStats.tsx          # NEW — shared component (accuracy strip + 7-row table)
│   ├── SeverityBadge.tsx      # KEPT — FlawCard.tsx (Flaws tab) still uses it, showCount=false
│   ├── GemGreatBadge.tsx      # DELETE once LibraryGameCard.tsx + AnalysisTagsPanel.tsx migrate
│   └── __tests__/
│       ├── MoveStats.test.tsx        # NEW
│       └── GemGreatBadge.test.tsx    # DELETE (component deleted)
├── lib/
│   └── plyOwnership.ts        # ADD moverColorAtPly(ply) helper alongside isUserPly
├── types/
│   └── library.ts             # ADD white_accuracy/black_accuracy to GameFlawCard
├── components/results/LibraryGameCard.tsx   # swap severityBadges/bestMoveBadges + local FlawRef for <MoveStats>
└── components/analysis/AnalysisTagsPanel.tsx # swap inline severity/gem-great render + local FlawRef for <MoveStats>
```

Backend:
```
app/
├── schemas/library.py        # ADD white_accuracy/black_accuracy: float | None to GameFlawCard
└── services/library_service.py  # _build_card(): pass game.white_accuracy/black_accuracy through
```

### Pattern 1: Unified FlawRef `category` kind (recommendation for D-09)

**What:** Both existing files' `FlawRef` unions have `{ kind: 'severity'; severity: FlawSeverity }` and `{ kind: 'bestMove'; tier: BestMoveTier }` as two separate variants (`LibraryGameCard.tsx:180-186`, `AnalysisTagsPanel.tsx:34-43`) because severity comes from `flaw_markers` and tier comes from `eval_series` — different source fields, hence different ref kinds historically. For the new 7×2 grid, collapse these into ONE variant carrying a unified 7-value category plus the new side dimension:

```typescript
// New shared category union — NOT FlawSeverity (which must stay 3-valued per
// backend contract) and NOT the unrelated frontend-only MoveQuality type
// (lib/moveQuality.ts, a different live-engine-grading concept that happens
// to share bucket names — do not import/reuse/merge with it).
type MoveStatCategory = 'gem' | 'great' | 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';
type MoveStatSide = 'white' | 'black';

type FlawRef =
  | { kind: 'category'; category: MoveStatCategory; side: MoveStatSide }
  | { kind: 'tag'; tag: FlawTag }
  | { kind: 'motif'; motif: string; orientation: TacticChipOrientation };
```

**When to use:** This is the natural seam — `pliesForRef`/`handleActivate`/`sameFlawRef` in both files already dispatch on `ref.kind`, so collapsing two kinds into one that also carries `side` is a mechanical, low-risk extension of an existing pattern rather than a new pattern.

**Note on `side` semantics:** `side` should be the literal board color (`'white' | 'black'`), NOT `'user' | 'opponent'` — the accuracy strip's D-02 spec ("cell background = player color, white bg = white, dark bg = black") needs the literal color for styling, while "is this the user's column" (needed for D-10's filter-ring, which stays user-scoped) is a *separate* derived boolean (`side === game.user_color`). Keep these as two distinct concerns: `side` for column identity/color, a `isOwnSide = side === game.user_color` check wherever D-10's ring logic is applied. "Player always on the left" (SEED-112 point 2) means column ORDER is user-relative even though `side` itself is color-absolute — the component must reorder its two columns based on `game.user_color`, not always render white-then-black.

### Pattern 2: Per-side count derivation (client-side, D-05)

**What:** Both severity counts and tier counts derive from a single pass over already-fetched data — no new hook, no new fetch.

```typescript
// Source: app/schemas/library.py:80-93 (FlawMarker), confirmed both-sides via
// library_service.py:300-308 ("Flaw markers from the mover-POV kernel dict
// (both colors, D-01/D-02)" — all_moves = _run_all_moves_pass(positions) is
// NOT filtered by user_color; is_user is a label, not a filter).
function severityCountsBySide(markers: FlawMarker[]): Record<MoveStatSide, Record<FlawSeverity, number>> {
  const out = { white: { inaccuracy: 0, mistake: 0, blunder: 0 },
                black: { inaccuracy: 0, mistake: 0, blunder: 0 } };
  for (const m of markers) {
    const side = moverColorAtPly(m.ply); // even ply = white, odd = black
    out[side][m.severity]++;
  }
  return out;
}

// Source: app/schemas/library.py:32-64 (EvalPoint.best_move_tier), confirmed
// both-sides via library_service.py:244-283 (mover_color_for_ply(pos.ply) used
// unconditionally, not gated on game.user_color — the eval_series entry for
// EVERY ply gets a tier classification regardless of who moved).
function tierCountsBySide(points: EvalPoint[]): Record<MoveStatSide, Record<'gem' | 'great' | 'best' | 'good', number>> {
  const out = { white: { gem: 0, great: 0, best: 0, good: 0 },
                black: { gem: 0, great: 0, best: 0, good: 0 } };
  for (const p of points) {
    if (p.best_move_tier == null) continue;
    out[moverColorAtPly(p.ply)][p.best_move_tier]++;
  }
  return out;
}
```

### Anti-Patterns to Avoid

- **Merging the new category type into `FlawSeverity`:** `moveQuality.ts:20-22` has an explicit, load-bearing comment: *"FlawSeverity (types/library.ts) is the cross-stack contract mirroring the backend's severity enum and must NOT be extended with 'best'/'good'"* — this is precedent from a prior phase (151.1) hitting exactly this temptation and rejecting it. `FlawSeverity` stays 3-valued (`inaccuracy | mistake | blunder`); the new 7-valued category is its own type.
- **Confusing the new category type with the existing frontend-only `MoveQuality` type** (`lib/moveQuality.ts:37`): same 7 bucket *names* (`'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder' | 'gem' | 'great'`), but a completely different data source (live client-side Stockfish/Maia grading for the free-play engine feature, not `game_best_moves`/`game_flaws`). Do not import one where the other belongs — they are structurally identical but semantically unrelated. The colors (theme.ts `MOVE_QUALITY_*`) are fine to share; the *types* are not.
- **Re-deriving inaccuracy count from `game.severity_counts.inaccuracy`:** that field is user-scoped only (no black/white split) and its I value is oracle-sourced for imported-but-unanalyzed data paths — see Pitfall 1 below for the full provenance chain. The new table must read inaccuracy counts from `flaw_markers` like every other category, not mix in `severity_counts`.
- **Hiding zero-count rows** (today's `bestMoveBadges` convention, `LibraryGameCard.tsx:945`: `.filter((tier) => bestMovePlies[tier].length > 0)`): D-03 requires all 7 rows always render. Do not port this filter into the new component.

## Common Pitfalls

### Pitfall 1: Two different "inaccuracy count" provenances that happen to agree today — but the agreement is not enforced by any test

**What goes wrong:** `game.severity_counts.inaccuracy` (used by today's `SeverityBadge` count) is sourced from `game.white_inaccuracies`/`game.black_inaccuracies` (`library_service.py:547-550`), an "oracle" column on the `Game` model. That column has **two independent write paths**: (1) `app/services/normalization.py:481-482` — platform-reported values at import time (chess.com/lichess's own analysis, when present); (2) `app/services/eval_apply.py:1053-1088` — OUR OWN kernel classification (`count_game_severities`, which internally calls the exact same `_run_all_moves_pass` that `flaw_markers` uses) at full-analysis completion, which **overwrites** whatever import set. Since `analysis_state === 'analyzed'` (the gate for showing any severity data) requires eval coverage on `game_positions`, which in turn requires the eval-apply pipeline to have run, path (2) always wins for any game this new table would actually render for — so `flaw_markers`-derived inaccuracy counts and `severity_counts.inaccuracy` are the SAME kernel run today, just computed at two different times (write-time vs read-time) over presumably-identical `positions`.
**Why it happens:** Two intentionally separate code paths (`flaws_service.count_game_severities` for the persisted oracle column, `library_service._build_eval_series`'s `all_moves` for the live per-request `flaw_markers`) both wrap the same underlying kernel (`_run_all_moves_pass`) but are never asserted equal by a test.
**How to avoid:** For this phase, derive ALL 7 categories × 2 sides from `flaw_markers`/`eval_series` only (per D-05) — do not read `severity_counts` at all in the new component. This is actually **more correct** than today's mixed approach (which reads counts from one source and cycle-plies from another) and removes the theoretical divergence risk entirely, since the new table's I/M/B counts and its cycling machinery will both read the identical `flaw_markers` array.
**Warning signs:** If a future change ever recomputes `game_positions` for an already-`analyzed` game (e.g. a re-analysis backfill) without re-running `count_game_severities`, the two sources could genuinely diverge — not a Phase 179 concern, but worth a one-line code comment at the derivation site referencing this pitfall so a future reader doesn't "helpfully" swap back to `severity_counts` for the I count.

### Pitfall 2: D-03's "always render 7 rows" contradicts the current early-return-null guard in `AnalysisTagsPanel.tsx`

**What goes wrong:** `AnalysisTagsPanel.tsx:240` has `if (game.analysis_state !== 'analyzed' || (markers.length === 0 && !hasBestMovePlies)) return null;` — an analyzed game with genuinely zero flaws AND zero gem/great plies (a "flawless" game) currently renders **nothing at all** on `/analysis`. D-03 requires the Move Stats table to always render its 7 rows (with 0s) for any analyzed game, and D-07 only suppresses the whole component for `analysis_state !== 'analyzed'`. This means the new component's mount condition must drop the `markers.length === 0 && !hasBestMovePlies` clause entirely — a flawless/all-zero analyzed game should now show the accuracy strip + a table of all zeros, not nothing.
**Why it happens:** The current gate predates D-03/D-11's "always show a stable 7-row layout" requirement; it was written when the panel only existed to show non-empty badge rows.
**How to avoid:** New mount condition should be simply `game.analysis_state === 'analyzed'` (mirrors D-07 exactly) — no markers/tiers emptiness check. Tactic chip section (D-11, unchanged) can keep its own internal empty-state handling independently.
**Warning signs:** A UAT pass on a genuinely flaw-free analyzed game (rare but should exist in the corpus) is the concrete test case — confirm the new table renders with all-zero rows instead of vanishing.

### Pitfall 3: `SeverityBadge.tsx` has a third consumer outside this phase's scope — cannot be deleted

**What goes wrong:** `frontend/src/components/library/FlawCard.tsx:349-354` (the Flaws-subtab per-flaw card, explicitly out of scope for Phase 179) renders `<SeverityBadge severity={flaw.severity} count={1} showCount={false} />` for its singular-flaw display. `GemGreatBadge.tsx` has no such third consumer — `grep` confirms only `LibraryGameCard.tsx` and `AnalysisTagsPanel.tsx` import it.
**Why it happens:** `SeverityBadge` was designed as a general-purpose count pill from Phase 106/175, reused beyond the two files this phase touches.
**How to avoid:** Delete `GemGreatBadge.tsx` (+ its test file) once both call sites migrate to `MoveStats`. Keep `SeverityBadge.tsx` untouched — Phase 179 only removes its usage from `LibraryGameCard.tsx`/`AnalysisTagsPanel.tsx`, not the component itself. Run `npm run knip` after the migration to confirm no other orphaned exports.
**Warning signs:** `npm run knip` failing on `GemGreatBadge.tsx` if it's left behind unused; a broken Flaws-tab card if `SeverityBadge.tsx` is deleted by mistake.

### Pitfall 4: Desktop layout target (~225px matching miniboard height) is underspecified relative to the existing eval-chart placement

**What goes wrong:** SEED-112 point 4 says the Move Stats card "sits beside the board" at ~225px height with "tactic motif chips... filling the gap below the eval chart" — but today's desktop layout (`LibraryGameCard.tsx:1174-1268`) has the eval chart occupying the space directly beside the severity badges (both inside the same flex row, right column, beside the board). It is not specified in CONTEXT.md or SEED-112 exactly how the eval chart, the new ~225px Move Stats card, and the board are arranged relative to each other on desktop (side-by-side three-up? chart above stats? stats replaces the badge column only, chart stays where it is?).
**Why it happens:** SEED-112 explicitly calls this a "tight fit" / UI-phase detail, and CONTEXT.md defers exact layout to planning.
**How to avoid:** Flag for the planner to resolve via a UI-spec/sketch step (or explicit planning-time decision) before writing frontend tasks — this is a genuine open design question, not a research gap. This research did NOT find a hidden layout precedent to infer from.
**Warning signs:** A plan that writes desktop layout tasks without an explicit wireframe/measurement decision risks a mid-implementation redesign.

## Code Examples

### Both-sides `flaw_markers` construction (confirms D-05 for severities)

```python
# Source: app/services/library_service.py:300-308
# Flaw markers from the mover-POV kernel dict (both colors, D-01/D-02).
# The kernel skips plies with missing eval — no entry -> no marker.
entry = all_moves.get(pos.ply)
if entry is None:
    continue
mover_color, severity, es_before, es_after = entry
if severity is None:
    continue
is_user = mover_color == game.user_color
```
`all_moves = _run_all_moves_pass(positions)` (line 188) iterates every ply of the game regardless of mover — `is_user` is a derived label on an already-both-sided dict, not a filter.

### Both-sides `eval_series[].best_move_tier` construction (confirms D-05 for tiers)

```python
# Source: app/services/library_service.py:244-283 (abridged)
best_row = best_moves_by_ply.get(pos.ply) if best_moves_by_ply else None
if best_row is not None:
    tier = classify_best_move(
        best_row.maia_prob, best_row.best_cp, best_row.best_mate,
        best_row.second_cp, best_row.second_mate,
        mover_color_for_ply(pos.ply),   # <-- computed for the ACTUAL mover, no user_color gate
        ...
    )
    if tier != "neither":
        best_move_tier = tier
...
if best_move_tier is None and pos.move_san is not None and pos.ply >= opening_ply_count:
    if pos.ply in identity_plies:
        best_move_tier = "best"
    else:
        entry_for_tier = all_moves.get(pos.ply)
        if entry_for_tier is not None and entry_for_tier[1] is None:
            best_move_tier = "good"
```
Every `EvalPoint` in `eval_series` gets a tier classification attempt regardless of `game.user_color` — confirmed both-sided.

### Single builder, single schema, both endpoints (confirms D-05's overall premise)

```python
# Source: app/routers/library.py:137-164
@router.get("/games/{game_id}", response_model=GameFlawCard)
async def get_library_game(...) -> GameFlawCard:
    """Return a single GameFlawCard for any game, by id (analysis-page view).
    ...
    Quick 260717-agv: intentionally NOT owner-scoped. Any authenticated user may
    inspect any game by url (e.g. /analysis?game_id=640125) ...
    """
    card = await library_service.get_library_game(session, game_id=game_id)
```
```python
# Source: app/services/library_service.py:805-813
return _build_card(
    game, flaw_rows, is_analyzed, positions, active_map.get(game_id),
    tactic_flaw_rows=tactic_flaw_rows,
    best_moves_by_ply=best_moves_by_ply,
)
```
Same `_build_card` (line 471) that `get_library_games` (list endpoint) calls per-row. There is exactly one `GameFlawCard(...)` construction site in the whole codebase (`library_service.py:704`).

### The backend delta, in full

```python
# app/models/game.py:165-166 (already exists, Phase 178, migrated to main)
white_accuracy: Mapped[float | None] = mapped_column(REAL, nullable=True)
black_accuracy: Mapped[float | None] = mapped_column(REAL, nullable=True)

# app/schemas/library.py — ADD inside GameFlawCard (near severity_counts):
white_accuracy: float | None = None
black_accuracy: float | None = None

# app/services/library_service.py:704 — ADD to the GameFlawCard(...) call:
white_accuracy=game.white_accuracy,
black_accuracy=game.black_accuracy,
```
No repository change needed — `query_filtered_games` (`library_repository.py:1732`) already does `select(Game)` (full entity, no `load_only`), and `get_library_game`'s single-row path uses `session.get(Game, game_id)` (also full entity). Both already load the two new columns automatically.

### Existing FlawRef union (both files, to be unified)

```typescript
// frontend/src/components/results/LibraryGameCard.tsx:180-186
type FlawRef =
  | { kind: 'tag'; tag: FlawTag }
  | { kind: 'severity'; severity: FlawSeverity }
  | { kind: 'motif'; motif: string; orientation: TacticChipOrientation }
  | { kind: 'bestMove'; tier: BestMoveTier };
```
```typescript
// frontend/src/components/analysis/AnalysisTagsPanel.tsx:34-43 — byte-identical shape,
// declared separately per the file's explicit "trivially safe copies, not shared
// extractions" convention (line 24-25 docstring).
```

## State of the Art

Not applicable in the "library/framework evolved" sense — this is a same-repo, same-sprint integration. The one relevant "state of the art" fact: Phase 178 (shipped, on `main`, migration applied — `alembic/versions/20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py`) already delivers the canonical accuracy columns this phase surfaces. No further backend computation work is needed or in scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Desktop layout target (chart vs. Move Stats card vs. board arrangement) is not fully specified and needs an explicit planning/UI-spec decision | Pitfall 4 | Low — flagged, not assumed; the planner is expected to resolve this before writing frontend layout tasks, not this research |
| A2 | A "muted 0/–" zero-cell rendering can reuse existing `text-muted-foreground`-style Tailwind conventions rather than a new theme token | Don't Hand-Roll / D-03 | Low — cosmetic only, easily adjusted at implementation time, no architectural risk |
| A3 | Percent formatting for the accuracy strip (rounding convention, e.g. `Math.round()` vs 1 decimal) has no established precedent elsewhere in the frontend (grep found no existing accuracy/percent formatter) | Summary | Low — purely a display-polish decision, not a data-correctness one |

**All other claims in this research are `[VERIFIED]` via direct source-code reads with file:line citations** — the domain is 100% first-party code, so "verification" here means "read the actual implementation," which was done exhaustively for every claim in the Summary, D-05 resolution, and Pitfalls sections.

## Open Questions

1. **Exact desktop layout arrangement (board / Move Stats card / eval chart / chips)**
   - What we know: Move Stats card target ≈225px tall, beside the board (SEED-112 pt.4); chips "fill the gap below the eval chart" (implies eval chart persists somewhere); D-11 says chips stay.
   - What's unclear: whether the eval chart moves to a new position, shrinks, or stays exactly where it is while Move Stats takes over the current badge-column's space.
   - Recommendation: resolve via a short UI-spec/sketch step or explicit CONTEXT-amendment before frontend task-writing; do not let the plan silently invent a layout.

2. **Mobile-collapsed "user's 3 severity counts" (D-06) — display format**
   - What we know: collapsed default = accuracy strip + user's I/M/B counts; tap expands to full 7×2 table.
   - What's unclear: whether the collapsed state reuses the existing `SeverityBadge` pill row verbatim (cheap, consistent) or is a new compact row inside `MoveStats` itself (cleaner ownership, more work). Given `SeverityBadge.tsx` stays in the codebase for `FlawCard.tsx` anyway, reusing it for the collapsed state is a legitimate option Claude's Discretion should consider — but it also means the "replace badge rows" framing in the phase description is only ~90% true for mobile-collapsed.
   - Recommendation: decide at plan time; either is technically sound given `SeverityBadge.tsx` is not being deleted.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest (async, `pytest-xdist` via `-n auto`) |
| Backend config | `pyproject.toml` / `tests/conftest.py` (per-run cloned DB template) |
| Frontend framework | Vitest |
| Frontend config | no dedicated `test:` block in `vite.config.ts` (project default) |
| Quick run command (backend) | `uv run pytest tests/services/test_library_service.py -x` |
| Quick run command (frontend) | `npm test -- --run MoveStats` (once the new test file exists) |
| Full suite command (backend) | `uv run pytest -n auto` |
| Full suite command (frontend) | `npm test -- --run` |

### Phase Requirements → Test Map

| D-id | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| D-01 | Accuracy shows canonical value or muted "—" when NULL, never `*_accuracy_imported` | unit | `npm test -- --run MoveStats` | ❌ Wave 0 |
| D-01/backend | `GameFlawCard` carries `white_accuracy`/`black_accuracy` sourced from `game.white_accuracy`/`black_accuracy` | unit | `uv run pytest tests/services/test_library_service.py -x` | ✅ existing file, ❌ new test case (extend `_seed_db_game` with `white_accuracy`/`black_accuracy` params per `tests/services/test_library_service.py:751-771`) |
| D-03 | All 7 rows always render, zero as muted 0 | unit | `npm test -- --run MoveStats` | ❌ Wave 0 |
| D-05 | 14 counts correctly derived from `flaw_markers`+`eval_series` for both sides | unit | `npm test -- --run MoveStats` | ❌ Wave 0 |
| D-06 | Mobile collapsed vs expanded toggle | unit | `npm test -- --run LibraryGameCard` | ✅ existing file, extend |
| D-07 | Unanalyzed game shows no strip/table, only analyze pill | unit | `npm test -- --run MoveStats` / existing `LibraryGameCard.test.tsx` | ✅/❌ mixed |
| D-08 | Opponent positive tiers surfaced (reversing normal `isUserPly` scoping) | unit | `npm test -- --run MoveStats` | ❌ Wave 0 |
| D-09 | Per-(category × side) cycling, wrap, reset-on-different-cell | unit | `npm test -- --run MoveStats` | ❌ Wave 0 |
| D-10 | Global filter ring only on player-side cell | unit | `npm test -- --run LibraryGameCard` | ✅ existing file, extend |

### Sampling Rate

- **Per task commit:** targeted file (`uv run pytest tests/services/test_library_service.py -x` and/or `npm test -- --run MoveStats`)
- **Per wave merge:** `uv run pytest -n auto` (backend) + `npm run lint && npm test -- --run` (frontend)
- **Phase gate:** full pre-merge gate per CLAUDE.md before squash-merge to `main`

### Wave 0 Gaps

- [ ] `frontend/src/components/library/__tests__/MoveStats.test.tsx` — new file, covers D-01/D-03/D-05/D-07/D-08/D-09
- [ ] Extend `tests/services/test_library_service.py`'s `_seed_db_game` helper (line 751) with `white_accuracy`/`black_accuracy` params
- [ ] Extend `frontend/src/components/results/__tests__/LibraryGameCard.test.tsx` for D-06 (collapse/expand) and D-10 (filter ring on player cell only)
- [ ] Extend `frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx` for the removed empty-state early-return (Pitfall 2) and D-08 opponent-tier display

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth changes; `current_active_user` dependency unchanged on both endpoints |
| V3 Session Management | No | Unchanged |
| V4 Access Control | No (unchanged, pre-existing) | `GET /library/games/{game_id}` is deliberately NOT owner-scoped (`app/routers/library.py:145-148`, documented intentional — opponent scouting/sharing); this phase adds no new data class that changes that calculus. `white_accuracy`/`black_accuracy` are per-game aggregate floats, no more sensitive than the ratings/usernames already exposed on the same endpoint |
| V5 Input Validation | No new input | No new query params, no new request body; the two new response fields are read-only server-computed floats |
| V6 Cryptography | N/A | No crypto surface |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Internal hash leakage (V5, CLAUDE.md rule) | Information Disclosure | Confirmed: `white_accuracy`/`black_accuracy` are plain floats, not derived from or adjacent to any `*_hash` column — no new disclosure surface |
| IDOR via `game_id` on the non-owner-scoped single-game endpoint | Information Disclosure | Pre-existing, explicitly accepted design (Quick 260717-agv docstring, `library.py:145-148`) — out of scope to revisit here; this phase does not change the authorization model, only adds two fields to an already-broadly-readable payload |

No new threat surface identified. This phase is additive-read-only on the backend and purely presentational on the frontend.

## Sources

### Primary (HIGH confidence — direct source reads)
- `app/schemas/library.py` (GameFlawCard, EvalPoint, FlawMarker definitions)
- `app/services/library_service.py` (`_build_card`, `_build_eval_series`, `get_library_game`, `get_library_games`)
- `app/routers/library.py` (both `/games` and `/games/{game_id}` endpoints)
- `app/models/game.py` (Phase 178 accuracy/ACPL columns, lines 162-183)
- `app/services/accuracy_acpl.py` (`AccuracyAcplResult` dataclass)
- `app/services/flaws_service.py` (`count_game_severities`, `_run_all_moves_pass` usage)
- `app/services/eval_apply.py` (severity-count write path, lines 1053-1088)
- `app/services/normalization.py` (import-time inaccuracy write path, lines 481-482)
- `frontend/src/hooks/useLibrary.ts` (`useLibraryGame`, confirms analysis page uses the library single-game endpoint)
- `frontend/src/api/client.ts:395-396` (`getGame` → `/library/games/${gameId}`)
- `frontend/src/pages/Analysis.tsx:2986-3000` (`tagsPanel` — confirms `gameData: GameFlawCard` passed to `AnalysisTagsPanel`)
- `frontend/src/components/results/LibraryGameCard.tsx` (full FlawRef/cycling/highlight/render-body read)
- `frontend/src/components/analysis/AnalysisTagsPanel.tsx` (full read)
- `frontend/src/components/library/SeverityBadge.tsx`, `GemGreatBadge.tsx`, `FlawCard.tsx` (usage-site confirmation)
- `frontend/src/lib/theme.ts` (all color constants inventoried)
- `frontend/src/lib/severityGlyph.ts`, `plyOwnership.ts`, `moveQuality.ts` (icon/glyph/type-collision vocabulary)
- `frontend/src/components/icons/GemIcon.tsx`, `GreatMoveIcon.tsx`
- `frontend/src/hooks/useFlawFilterStore.ts`
- `tests/services/test_library_service.py` (`_seed_db_game` fixture shape)
- `alembic/versions/20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py` (migration already applied confirmation)
- `.planning/phases/179-two-sided-move-stats-component-seed-112/179-CONTEXT.md`
- `.planning/seeds/SEED-112-two-sided-move-stats-component.md`
- `.planning/STATE.md`

### Secondary (MEDIUM confidence)
- None used — this phase required no external documentation lookup (no new libraries/APIs).

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new stack elements
- Architecture (D-05 resolution): HIGH — traced the full call chain from both endpoints to a single shared builder function and Pydantic model, byte-for-byte confirmed
- Pitfalls: HIGH — each pitfall is grounded in a specific line-cited code read, not inference
- Layout open question (Pitfall 4 / A1): explicitly flagged as unresolved, not guessed at

**Research date:** 2026-07-18
**Valid until:** No expiry concern — this is a same-repo research pass; valid until the underlying files change (re-research if Phase 178's accuracy columns, `_build_card`, or the two target components are touched by an intervening phase before 179 executes).
