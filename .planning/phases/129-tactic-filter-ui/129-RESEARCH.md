# Phase 129: Tactic Filter UI - Research

**Researched:** 2026-06-20
**Domain:** FlawChess library tactic-filter frontend (React 19/TS/Vite) + two NEW backend filter params (FastAPI/SQLAlchemy async)
**Confidence:** HIGH (all claims verified against current source; no external libraries introduced)

## Summary

Phase 129 is overwhelmingly an *extension* phase: the 128 contract already gives the codebase an `orientation: Literal["missed","allowed"]` param threaded end-to-end (router → service → both repository filter sites → `_tactic_cols` resolver), both column sets in every schema, and depth columns (`missed_tactic_depth` / `allowed_tactic_depth`) on `GameFlaw`. The frontend already has the clone targets the UI-SPEC names (`OpponentStrengthFilter` + `opponentStrength.ts`, the "Played as" `ToggleGroup`, `TacticComparisonGrid`, `TacticMotifChip`, the `Accordion` "Endgame Statistics Concepts" pattern), a module-level `useFlawFilterStore`, and a `buildLibraryParams`-based query layer in `useLibrary.ts`. Beta gating is **already done correctly** via `useUserProfile().data.beta_enabled` in both `FlawCard.tsx` and `TacticComparisonGrid.tsx` — the project-memory pitfall does not currently bite, but new code must keep using that source.

The genuinely new work is small and well-bounded: (1) widen the orientation enum to `Literal["either","missed","allowed"]` and add an OR-across-both-column-sets branch at the two filter sites; (2) add a `max_tactic_depth` clause that bounds the active orientation's depth column and exempts mates; (3) make the tactic-comparison endpoint return **both** orientation rates per family and rank top-6 by Missed; (4) wire orientation + depth into the store, `FlawFilterControl`, the chip label, `FlawCard`'s dual-chip logic, and the comparison grid's two-bullet cards + "More Tactics" accordion.

**Primary recommendation:** Wave 1 = backend (extend `TacticOrientation` to 3 values + "either" branch, add depth clause, restructure `fetch_tactic_comparison`/`_compute_tactic_bullets` to dual-orientation + Missed ranking, extend `TacticComparisonResponse` schema). Wave 2 = shared types + frontend wiring (run `tsc -b` at the type boundary). One landmine: the UI-SPEC assumes a per-chip **definition popover on `TacticMotifChip`** that **does not exist** (removed in Phase 126 UAT — definitions live in a shared `<TagLegend>`); D-12 must be satisfied via the existing `TagLegend` path, not a re-added popover.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Depth-bound filtering on tactic flaws | API/Backend (`query_utils` + `library_repository`) | — | Must filter at SQL EXISTS/clause level; frontend only sends `max_tactic_depth` |
| "Either" OR-across-orientation matching | API/Backend (both filter sites) | — | Cross-column-set predicate is a SQL concern |
| Two-orientation comparison rates + Missed ranking | API/Backend (`fetch_tactic_comparison` + `_compute_tactic_bullets`) | — | Aggregation/ranking already server-side (126 D-07); extend in place |
| Orientation/depth filter state | Frontend store (`useFlawFilterStore`) | — | Pure client filter UI state, persisted across SPA nav |
| Chip orientation prefix + dual-chip rendering | Frontend (`TacticMotifChip` label, `FlawCard` caller) | — | Display-only; backend already returns both motif fields |
| Two-bullet cards + "More Tactics" accordion | Frontend (`TacticComparisonGrid`) | — | Presentation of server-ranked data |
| Beta gate | Frontend render-time (`useUserProfile().data.beta_enabled`) | — | 126 D-01: frontend-only gate |

---

## Backend — Current State vs Target

### 1. `app/repositories/query_utils.py` — `apply_game_filters` (Games EXISTS path)

**Current signature (verified, `:74-91`):**
```python
def apply_game_filters(
    stmt, time_control, platform, rated, opponent_type, from_date, to_date, color=None, *,
    opponent_gap_min=None, opponent_gap_max=None,
    flaw_severity=None, flaw_tags=None,
    tactic_families=None, user_id=None,
    orientation: Literal["missed", "allowed"] = "allowed",
) -> Any
```
[VERIFIED: app/repositories/query_utils.py:74-238]

**Tactic clause shape today (`:208-237`):** lazy-imports `FAMILY_TO_MOTIF_INTS` + `_tactic_cols` from `library_repository`; builds `motif_ints` from selected families; if non-empty, resolves `motif_col, _conf_col = _tactic_cols(orientation)` and adds a correlated `EXISTS(select(GameFlaw.ply).where(game_id==Game.id, user_id==user_id, motif_col.in_(motif_ints)))`. **Note:** this Games-EXISTS path does NOT currently gate on confidence (`_conf_col` is discarded), unlike the Flaws-list path which does. [VERIFIED: query_utils.py:208-237]

**`is_opponent_expr` (`:23-51`)** and **`player_only_gate` (`:54-71`)** are the single source of ply-parity; `_PLY_EVEN_MOVER_WHITE = 0`. Do not inline `ply % 2`. [VERIFIED]

**Target changes (D-05/D-08):**
- Widen `orientation` to `Literal["either","missed","allowed"]` (default `"allowed"` to preserve existing callers; the Flaws/comparison callers will pass `"either"` when the toggle is Either).
- Add a `max_tactic_depth: int | None = None` keyword param (Claude's-discretion name per CONTEXT; `max_tactic_depth` recommended for naming symmetry with `opponent_gap_max`).
- **"either" branch:** when `orientation == "either"`, the EXISTS predicate becomes `or_(missed_motif.in_(ints) & <depth/mate clause on missed_depth>, allowed_motif.in_(ints) & <depth/mate clause on allowed_depth>)`. `_tactic_cols` returns one pair today — for "either" you need BOTH pairs; either extend `_tactic_cols` to accept `"either"` (returning a list of pairs) or add a sibling helper. Recommend a new `_tactic_orientation_pairs(orientation) -> list[tuple[motif_col, conf_col, depth_col]]` returning 1 pair for missed/allowed and 2 for either, so all three sites share it.
- **Depth + mate exemption:** depth bound is `depth_col <= max_tactic_depth`, but **OR'd with the mate-membership escape** so mates always pass: `(depth_col <= max_depth) | motif_col.in_(MATE_MOTIF_INTS)`. The `mate` family ints already exist in `FAMILY_TO_MOTIF_INTS["mate"]` (`library_repository.py:85-95`) — reuse that list as the exemption set (do NOT introduce a new constant). [VERIFIED: FAMILY_TO_MOTIF_INTS["mate"]]

### 2. `app/repositories/library_repository.py` — second filter site + comparison

**`build_flaw_filter_clauses` (`:157-250`) current signature:**
```python
def build_flaw_filter_clauses(
    severity, tags, tactic_families=(), orientation: TacticOrientation = "allowed",
) -> list[ColumnElement[bool]]
```
Tactic clause (`:244-248`): `motif_col, conf_col = _tactic_cols(orientation); clauses.append(motif_col.in_(motif_ints) & (conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN))`. **This site DOES gate on confidence** (≥70). [VERIFIED: library_repository.py:244-248, :58]

**`TacticOrientation` alias (`:49`):** `Literal["missed", "allowed"]` — **this is the single type alias** imported by `query_utils` (lazy) and `library_service`. Changing it to 3 values updates all three layers at once. [VERIFIED]

**`_tactic_cols` (`:122-135`):** branches `missed`→missed cols, else allowed cols. Returns `(motif_col, conf_col)`. Does NOT return the depth column today — depth must be added to its return or a sibling resolver added. [VERIFIED]

**`_TACTIC_CHIP_CONFIDENCE_MIN = 70` (`:58`)** — reuse unchanged for both orientations and the depth filter (D-08). [VERIFIED]

**Both filter sites must change in lockstep** (confirmed): `query_utils.apply_game_filters` (Games EXISTS) and `build_flaw_filter_clauses` (Flaws list + `flaw_exists_from_table`). The Flaws list calls `build_flaw_filter_clauses` via `query_flaws` (`:410`); `query_flaws` signature has `orientation: TacticOrientation = "allowed"` (`:378`) and no depth param yet — add `max_tactic_depth` there and thread to the clause builder. [VERIFIED: library_repository.py:364-410]

**Chip read path (`:519-547`):** `query_flaws` builds `FlawListItem` rows surfacing BOTH `allowed_*` and `missed_*` motif fields when `confidence >= _TACTIC_CHIP_CONFIDENCE_MIN`. The orientation toggle does NOT need to change which fields are *returned* (both come back); the frontend `FlawCard` decides which chip(s) to *render* (D-11). So the read path likely needs no change — only the *filter* clause does. Confirm during planning whether under "Missed"/"Allowed" the list should also suppress the other orientation's chip server-side or purely client-side (CONTEXT D-11 reads as client-side; keep both fields in the payload). [VERIFIED: library_repository.py:519-547]

### 3. Depth columns + units (calibration)

`GameFlaw.missed_tactic_depth` / `allowed_tactic_depth` are `Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)`. [VERIFIED: app/models/game_flaw.py:90,94]

**Units:** stored depth is **raw half-move ply / loop index into the PV** (127 D-04). `allowed_tactic_depth` is the loop index within the flaw_ply+1 PV; `missed_tactic_depth` is the index within the flaw_ply PV (one ply earlier) — the 128 D-05 one-ply baseline offset. [VERIFIED: game_flaw.py:76-86]

**Calibration basis (127):** `reports/tactic-tagger/tactic-tagger-2026-06-20.md` — Depth-vs-Rating Pearson r=0.322 (n=7765); immediate motifs sit shallow (hanging-piece ≈ 0, fork/double-check ≈ 1 half-move), mating nets run deeper; "near-zero counts beyond 8" supports `DEPTH_SLIDER_MAX`. [VERIFIED: tactic-tagger-2026-06-20.md:90,98]

**⚠ Unit-mismatch caution for the planner:** the UI-SPEC `tacticDepth.ts` constants (`DEPTH_PRESET_BEGINNER_MAX=2`, `DEPTH_PRESET_INTERMEDIATE_MAX=6`) are described both as "half-plies" and as full-move presets ("1 move", "≤3 moves"). D-03 says player unit = full moves (⌈ply/2⌉), storage = half-move ply, UI converts. **Decision the planner must lock:** is the value sent to the backend `max_tactic_depth` a half-move ply (compared directly to the SmallInteger column) or a full-move count (backend doubles it)? Cleanest: keep the API param in **half-moves** (matches the stored column with zero conversion at the SQL layer) and convert to "moves deep" labels purely in the frontend. The UI-SPEC's `2`/`6` are already half-move values (≈1 / ≈3 full moves), consistent with that choice. Verify against the 128 one-ply offset: a single threshold on the active orientation's own depth column is correct because each orientation's depth is self-consistent; the offset only matters if you ever compared the two columns to one shared number (you don't — the filter bounds the *active* column).

### 4. `app/schemas/library.py` — comparison response shape (D-13)

**Today `TacticBullet` (`:362-382`)** carries a SINGLE orientation's stats per family: `family, you_rate, opp_rate, delta, ci_low, ci_high, p_value, you_events, opp_events, zone_lo, zone_hi, has_zone`. `TacticComparisonResponse` (`:385-398`): `bullets: list[TacticBullet], analyzed_n, analyzed_gate, below_gate`. [VERIFIED]

**Target (D-13 — both orientations per family):** two clean options for the planner:
- **(A) Two bullets per family with an `orientation` tag** — add `orientation: Literal["missed","allowed"]` to `TacticBullet`; return up to 12 bullets (6 families × 2). Frontend groups by family. Minimal schema churn; reuses the entire existing `TacticBullet`/CI machinery.
- **(B) A family-grouped wrapper** — new `TacticFamilyComparison { family, missed: TacticBullet, allowed: TacticBullet }`. Cleaner client grouping but bigger schema + frontend type rewrite.
Recommend **(A)** — it preserves the existing `_compute_tactic_bullets` aggregation almost entirely (run it once per orientation), changes one field, and the frontend groups by `family`. Ranking (D-14) then selects the top-6 *families* by their Missed bullet's rate, emitting both bullets per selected family.

### 5. `app/services/library_service.py` + `app/routers/library.py` — ranking (D-14)

**`_compute_tactic_bullets` (`:1245-1327`):** computes per-family deltas/CI for ONE orientation's rows, ranks by significance-then-volume, caps at 6. [VERIFIED]

**`fetch_tactic_comparison` (`library_repository.py:1488-...`):** builds 12 COUNT FILTER columns (6 families × player/opp) for ONE orientation via `_tactic_cols(orientation)` (`:1557`). [VERIFIED]

**`get_tactic_comparison` (service `:1330-1412`)** + router (`:212-253`): router has NO `orientation` query param today (the comparison always uses the service default `"allowed"`). [VERIFIED]

**Target (D-13/D-14):** call the per-game fetch **twice** (once `orientation="missed"`, once `"allowed"`) OR extend `fetch_tactic_comparison` to emit 24 COUNT columns (6 families × player/opp × 2 orientations) in one query. The two-query approach is simpler and reuses `_compute_tactic_bullets` unchanged (call it per orientation, tag bullets with orientation). **Ranking:** D-14 selects top-6 families by **Missed `you_rate` descending** (was: largest significant gap). Align tie-break/volume fallback with the existing `_sort_key` (Claude's discretion). The router does NOT need a new orientation query param (the grid always shows both, D-09); keep the endpoint's existing game-metadata params.

**Performance note:** the service already early-gates on `analyzed_n < TACTIC_COMPARISON_GATE` before the expensive per-game query. Two orientation fetches double that cost — acceptable (both are post-gate). Prefer a single 24-column query if profiling shows the double round-trip matters; not required for correctness.

---

## Frontend — Current State vs Target

### Clone target: `OpponentStrengthFilter.tsx` + `lib/opponentStrength.ts`
[VERIFIED: full read]. The idiom to clone single-handle: `derivePreset(value)` (matches range to preset or null), `presetToRange`, `sliderToRange`/`rangeToSlider`, `formatRangeSummary`, preset chips as `grid grid-cols-N gap-1 mb-3` with `h-11 sm:h-7` and `aria-pressed`, slider in `px-1.5` with `thumbLabels`, summary `text-toggle-active` when non-default. For depth, the "range" collapses to a single `maxMoves: number | null` (Advanced=`null`=no cap, slider at MAX). Build `lib/tacticDepth.ts` mirroring this shape (preset record, `derivePreset(maxMoves)`, `presetToMax`, `sliderToMax`/`maxToSlider`, `formatDepthSummary`, `depthToQueryParam`). Reuse `Slider` + `InfoPopover` primitives unchanged.

### Clone target: "Played as" ToggleGroup (`FilterPanel.tsx:265-286`)
[VERIFIED]. Exact pattern: `<ToggleGroup type="single" value=... onValueChange={(v)=>{ if(!v) return; update(...) }} variant="outline" size="sm" className="w-full">` with three `<ToggleGroupItem className="min-h-11 sm:min-h-0 flex-1 text-sm">`. The empty-string guard (`if (!v) return`) is the deselect-prevention the UI-SPEC interaction contract requires. Clone verbatim with values `either/missed/allowed`.

### Store: `useFlawFilterStore.ts`
[VERIFIED: full read]. `FlawFilterState = { severity, tags, tacticFamilies }`; `DEFAULT_FLAW_FILTER` all-empty; `isFlawFilterNonDefault` = tags non-empty OR severity length===1 OR tacticFamilies non-empty. Module-level `useSyncExternalStore`, no Zustand.
**Target:** add `tacticOrientation: 'either'|'missed'|'allowed'` (default `'either'`), `tacticDepthPreset` (default `'intermediate'`), `tacticDepthMax: number | null` (default = intermediate's half-move value). Update `DEFAULT_FLAW_FILTER`, and `isFlawFilterNonDefault` to add `filter.tacticOrientation !== 'either'` and `filter.tacticDepthPreset !== 'intermediate'` (per D-02 the depth filter is always-on, so "non-default" means *not Intermediate*, NOT *set*). **Watch:** `FlawsTab.tsx:45` defines a local `NO_FLAW_FILTER` literal and `:94` reconstructs from URL params — both must include the new fields or TS will error (good — `tsc -b` catches it). Pending-vs-applied filter pattern in `FlawsTab` (`pendingFlawFilter`/`appliedFilters`) must carry the new fields through both the desktop (`:289`) and mobile-drawer (`:504`) `FlawFilterControl` instances. [VERIFIED: FlawsTab.tsx:45,94,213,289,504]

### Query threading: `useLibrary.ts` + `api/client.ts`
[VERIFIED]. `buildLibraryParams(filters, severity, tags)` (`:23`) builds the shared param object. `useLibraryFlaws` (`:176-193`) adds `tactic_family` + offset/limit and keys on `['library-flaws', params, tacticFamily, offset, limit]`. `useTacticComparison` (`:135-151`) keys on `['library-tactic-comparison', params, tacticFamilies]`.
`api/client.ts`: `getFlaws` accepts `tactic_family?: string[]` (`:329`); `getTacticComparison` accepts `tactic_families?: string[]` (`:303`).
**Target:** thread `tactic_orientation` + `max_tactic_depth` into `getFlaws` params AND into the `useLibraryFlaws` **query key** (so changing orientation/depth refetches). The comparison hook does NOT take orientation (grid shows both). **Critical:** the new filter values MUST be added to the query key array or TanStack will serve stale data — current keys already include `params` + `tacticFamily`; append the two new values (or fold orientation/depth into the params object).

### Chip: `TacticMotifChip.tsx` — ⚠ UI-SPEC discrepancy
[VERIFIED: full read]. The current chip has **NO definition popover** — Phase 126 UAT removed it; definitions surface via a shared `<TagLegend>` rendered once below the chip row (`FlawCard.tsx:289-298`). The chip's `aria-label` is `` `Tactic: ${motif} — ${definition}` `` and `data-testid` is `chip-tactic-${motif}-${flawId}`. The component takes `motif, flawId, onHover?, onActivate?` — **no `orientation` prop yet**.
**Target (D-10):** add optional `orientation?: 'missed'|'allowed'`; when set, render label `` `${orientation}: ${motif}` ``, aria-label `` `Tactic: ${orientation} ${motif} — ${definition}` `` (space, not colon, in aria), data-testid `chip-tactic-${orientation}-${motif}-${flawId}`. Color/icon/size unchanged. **D-12 is satisfied by the chip + existing `TagLegend`, NOT by re-adding a per-chip popover** — the UI-SPEC's "definition popover" language is stale relative to the shipped 126 code. Plan/UI-checker should treat the `TagLegend` path as the narration surface and prefix the tactic-motif entries passed to `TagLegend` with orientation too (so the legend explains "missed: fork" / "allowed: fork").

### Caller: `FlawCard.tsx` dual-chip (D-11)
[VERIFIED: :278-298]. Today renders ONE chip: `userProfile?.beta_enabled && flaw.allowed_tactic_motif != null && <TacticMotifChip motif={flaw.allowed_tactic_motif} ...>`. Beta source = `useUserProfile().data` (correct). `TagLegend` is fed `[flaw.allowed_tactic_motif]`.
**Target:** branch on `flawFilter.tacticOrientation`: Missed→missed chip only, Allowed→allowed chip only, Either→both when both non-null (one when one). Pass `orientation` to each chip and to the `TagLegend` motif list. `FlawCard` does not currently receive `flawFilter` — it must be threaded from `FlawsTab` (or read the store directly; prefer prop to keep the card pure). Apply to BOTH the list-row card and the single-game card path (D-12 mobile parity).

### Grid: `TacticComparisonGrid.tsx` (D-13/D-14)
[VERIFIED: full read]. Today: self-fetches via `useTacticComparison(filters, flawFilter, [])`, beta-gates, renders one `Card` per bullet with a single `TacticBulletRow` (label + delta + popover + `MiniBulletChart`). Cards rendered in server order (no client re-sort). Uses `TACTIC_COMPARISON_FAMILIES`, `TACTIC_FAMILY_COLORS`, `TACTIC_FAMILY_ICON`, `isTacticDeltaSignificant`, `tacticDeltaZoneColor`.
**Target:** group the (now 12) bullets by `family`; render two `TacticBulletRow`s per card ("Missed {Family}" / "Allowed {Family}", `text-sm text-muted-foreground` labels per UI-SPEC). Take server's top-6 families; render remaining families inside an `Accordion` "More Tactics" using the exact `Endgames.tsx:390-397` pattern (`charcoal-texture rounded-md overflow-hidden border-none`, `<AccordionTrigger band>`, `<AccordionContent className="p-4">`). Reuse the same `FamilyCard` renderer for both top-6 and overflow (no compact variant — CONTEXT discretion). The existing `MiniBulletChart` + zero-event placeholder logic is per-bullet and carries over unchanged.

### Types: `types/library.ts` (`:240-322`)
[VERIFIED]. `FlawListItem` (`:240-247`) and `FlawMarker` (`:104-118`) already expose both `allowed_*`/`missed_*` motif+confidence. `TacticBullet` (`:297`) + `TacticComparisonResponse` (`:321`) mirror the backend. **Target:** mirror whatever backend schema choice is made (recommend adding `orientation` to `TacticBullet` per option A). This is the **shared-type boundary** → run `npx tsc -b` (or `npm run build`) before integrating, because `npm run lint`/`npm test` do NOT type-check (esbuild strips types — project memory `frontend_run_tsc_build`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Single-handle depth slider + preset snapping | New slider component | Clone `OpponentStrengthFilter` idiom + `Slider` primitive | Identical interaction already shipped & tested |
| Tri-state orientation toggle | Custom button group | Clone "Played as" `ToggleGroup` (`FilterPanel.tsx:265-286`) | Empty-deselect guard + mobile sizing already solved |
| Collapsible "More Tactics" | Custom disclosure | `Accordion`/`AccordionTrigger band` (`Endgames.tsx:390-397`) | Shared charcoal-texture pattern |
| Orientation column selection in SQL | String-interpolated column names | Extend `_tactic_cols` / closed `Literal` enum | T-128-05: never interpolate caller input into SQL |
| Mate exemption set | New constant of mate ints | `FAMILY_TO_MOTIF_INTS["mate"]` | Already the canonical mate-motif list |
| Per-family CI/ranking | New stats code | `_compute_tactic_bullets` per orientation | Wald-z CI + ranking already implemented |
| Tactic chip definitions | Re-add per-chip popover | Existing shared `<TagLegend>` | 126 UAT removed per-chip popovers by design |

**Key insight:** every NEW surface in this phase has an existing twin in the codebase. The risk is divergence (re-implementing instead of cloning), not novelty.

---

## Common Pitfalls

### Pitfall 1: Re-adding a `TacticMotifChip` definition popover
**What goes wrong:** Following the UI-SPEC literally re-introduces a per-chip popover that 126 UAT deliberately removed.
**How to avoid:** D-12 narration = chip label + shared `TagLegend`. Pass orientation-prefixed motifs to `TagLegend`. **Warning sign:** any new Popover/Radix import inside `TacticMotifChip.tsx`.

### Pitfall 2: Depth-unit confusion (half-move vs full-move)
**What goes wrong:** Sending a "moves deep" full-move value to a `max_tactic_depth` that compares against the half-move `*_tactic_depth` column halves the effective filter.
**How to avoid:** keep the API param in half-moves (matches the column 1:1); convert to "moves deep" labels only in the frontend. Document the chosen unit in both the param docstring and `tacticDepth.ts`.

### Pitfall 3: Forgetting the second filter site or the Games-EXISTS confidence gap
**What goes wrong:** Updating `build_flaw_filter_clauses` but not `apply_game_filters` (or vice-versa) → inconsistent filtering between Games and Flaws tabs. Also note the Games-EXISTS path does NOT gate tactic confidence today while the Flaws path does — keep that asymmetry intentional or fix it deliberately.
**How to avoid:** both sites + `query_flaws` + `fetch_tactic_comparison` resolve columns through the same helper; add depth/either there once.

### Pitfall 4: Stale TanStack data after orientation/depth change
**What goes wrong:** new filter values not in the query key → no refetch.
**How to avoid:** append `tactic_orientation` + `max_tactic_depth` to the `useLibraryFlaws` query key (or fold into `params`).

### Pitfall 5: `isFlawFilterNonDefault` mis-reads always-on depth as always-narrowing
**What goes wrong:** treating "depth filter set" as non-default lights the filter dot permanently.
**How to avoid:** non-default = `tacticDepthPreset !== 'intermediate'` and `tacticOrientation !== 'either'` (D-02).

### Pitfall 6: Missing the shared-type `tsc -b` gate
**What goes wrong:** `npm run lint`/`npm test` pass (esbuild strips types) but the build breaks on the changed `types/library.ts`.
**How to avoid:** run `npx tsc -b` / `npm run build` before integrating (project memory).

---

## Runtime State Inventory

Not a rename/refactor/migration phase. **No data migration required** — `missed_tactic_depth` / `allowed_tactic_depth` columns already exist and are populated (127/128 backfill, prod re-backfill is an out-of-scope runbook step). No stored-key, OS-state, secret, or build-artifact changes. The "either" enum widening is a code-only change to a `Literal` alias (no DB enum — the column is `SmallInteger`). **None found in all five categories** — verified: depth columns exist on `GameFlaw`; `TacticOrientation` is a Python `Literal`, not a PG enum; no new env vars or secrets.

---

## Validation Architecture

> Nyquist validation is **enabled** (`config.json` workflow.nyquist_validation = true).

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + per-run Postgres DB (`flawchess_test_<pid>` / `_gw*`), `-n auto` local |
| Backend quick run | `uv run pytest tests/test_query_utils.py tests/test_library_repository.py tests/test_library_router.py -x` |
| Backend full suite | `uv run pytest -n auto` |
| Frontend framework | Vitest |
| Frontend quick run | `cd frontend && npm test -- --run src/lib/__tests__/tacticDepth.test.ts` (new; tests live in __tests__/ subdirs) |
| Frontend full | `cd frontend && npm run lint && npm test -- --run` |
| Type gate | `cd frontend && npx tsc -b` (NOT covered by lint/test) |

### Phase Requirements → Test Map
| Behavior | Test Type | Automated Command | File |
|----------|-----------|-------------------|------|
| Depth bound on active orientation's column | unit (repo) | `uv run pytest tests/test_library_repository.py -k depth` | extend test_library_repository.py |
| Mate exemption (mates pass regardless of depth) | unit (repo) | same `-k mate_exempt` | extend test_library_repository.py |
| "either" OR across both column sets | unit (repo + query_utils) | `uv run pytest tests/test_query_utils.py -k either` | extend test_query_utils.py |
| Comparison returns BOTH orientation rates per family | integration (router) | `uv run pytest tests/test_library_router.py -k tactic_comparison` | extend test_library_router.py |
| Top-6 ranked by Missed + overflow families present | unit (service) | `uv run pytest -k compute_tactic_bullets` | service-level test |
| `tacticDepth.ts` derivePreset/presetToMax/sliderToMax round-trip | unit | vitest | NEW `src/lib/__tests__/tacticDepth.test.ts` |
| Chip label/aria/testid prefixing | component | vitest | extend `TacticMotifChip.test.tsx` |
| Dual-chip rendering rules (D-11) | component | vitest | extend `FlawCard.test.tsx` |
| `isFlawFilterNonDefault` treats Either/Intermediate as default | unit | vitest | NEW store test |
| Two-bullet cards + More Tactics accordion | component | vitest | extend `TacticComparisonGrid.test.tsx` |

Existing backend test files (`tests/test_query_utils.py`, `tests/test_library_repository.py`, `tests/test_library_router.py`) and frontend test files all exist — extend, don't create. **Frontend tests live in `__tests__/` subdirs, NOT co-located** (revision correction 2026-06-20): `src/components/library/__tests__/TacticMotifChip.test.tsx`, `src/components/library/__tests__/FlawCard.test.tsx`, `src/components/library/__tests__/TacticComparisonGrid.test.tsx`, `src/components/filters/__tests__/FlawFilterControl.test.tsx`, `src/pages/library/__tests__/FlawsTab.test.tsx`. The two NEW frontend tests also go in `__tests__/` subdirs: `src/lib/__tests__/tacticDepth.test.ts`, `src/hooks/__tests__/useFlawFilterStore.test.ts`. [VERIFIED: find]

### Sampling Rate
- **Per task commit:** the relevant quick-run subset (backend file(s) or vitest file).
- **Per wave merge:** full backend `uv run pytest -n auto` + `npm run lint && npm test -- --run` + `npx tsc -b`.
- **Phase gate:** full suite green + `tsc -b` clean before verify.

### Wave 0 Gaps
- [ ] `frontend/src/lib/__tests__/tacticDepth.test.ts` — preset/slider derivation round-trips
- [ ] Store-default test for new `tacticOrientation`/`tacticDepthPreset` fields in `isFlawFilterNonDefault`
- [ ] Framework install: none needed (pytest + vitest already configured)

### Backstop / hard-to-cover edges
- **Visual/mobile parity at 375px** (SC#4) — not unit-testable; HUMAN-UAT or `gsd-ui-review`.
- **Beta-gated visibility** — component tests can mock `useUserProfile`; end-to-end beta toggle is UAT.
- **Two-orientation aggregation correctness vs real data distribution** — covered by a small seeded fixture (player/opp/mixed-orientation flaws) asserting counts; exhaustive distribution is observational, not property-tested.

---

## Sequencing / Dependency Risk

**Recommended wave ordering:**
1. **Wave 1 — Backend (no frontend dependency):**
   - 1a. Widen `TacticOrientation` to 3 values (`library_repository.py:49`); add "either" branch + `max_tactic_depth` + mate exemption at both filter sites (`query_utils.apply_game_filters`, `build_flaw_filter_clauses`) and thread through `query_flaws`. Backend tests.
   - 1b. Extend `TacticBullet`/`TacticComparisonResponse` schema (option A: add `orientation`); dual-orientation `fetch_tactic_comparison` + Missed-ranked `_compute_tactic_bullets`; service/router pass-through. Router/service tests.
2. **Wave 2 — Shared types + frontend (depends on Wave 1 schema):**
   - 2a. Mirror schema in `types/library.ts`; add `tactic_orientation`/`max_tactic_depth` to `api/client.getFlaws` + `useLibraryFlaws` key. **Run `npx tsc -b` here.**
   - 2b. `lib/tacticDepth.ts` + `TacticDepthFilter.tsx`; store fields; `FlawFilterControl` orientation toggle + depth section (both desktop + mobile drawer); `FlawsTab` pending/applied wiring.
   - 2c. `TacticMotifChip` orientation prop + `FlawCard` dual-chip + `TagLegend` prefixing.
   - 2d. `TacticComparisonGrid` two-bullet cards + More Tactics accordion.

**Landmines:**
- **`tsc -b` gate** at the type boundary (2a) — non-negotiable; lint/test won't catch type drift.
- **Beta-gating source** — keep `useUserProfile().data.beta_enabled` (already correct in `FlawCard`/`TacticComparisonGrid`); do NOT switch to `useAuth().user` (always-null `beta_enabled`, project memory).
- **Schema-frontend coupling** — Wave 2 cannot start type changes until Wave 1's schema choice is locked. Decide option A vs B in planning, before either wave.
- **Both filter sites + query key** — three SQL sites and one query key must all gain the new params or filtering/refetch silently diverges.
- **UI-SPEC popover staleness** — D-12 via `TagLegend`, not a re-added chip popover.

---

## State of the Art

| Old Approach | Current Approach | When | Impact |
|--------------|------------------|------|--------|
| Single-orientation tactic filter (`allowed` default) | 3-value `either/missed/allowed` enum | Phase 129 | "either" = OR across both column sets at filter sites |
| Comparison grid: one bullet/family, ranked by gap | Two bullets/family, ranked by Missed | Phase 129 D-13/D-14 | Schema gains orientation dimension; 126 D-07 ranking reframed |
| Per-chip definition popover | Shared `TagLegend` | Phase 126 UAT | UI-SPEC text stale; D-12 uses TagLegend |

**Deprecated/outdated:** UI-SPEC's "definition popover on TacticMotifChip" — superseded by the 126 `TagLegend` pattern.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | API `max_tactic_depth` should be in half-moves (matches column 1:1) | Backend §3, Pitfall 2 | If full-moves chosen, backend must double — filter off by 2x if mismatched |
| A2 | Schema option A (orientation-tagged bullets) is preferred over a family-grouped wrapper | Schema §4 | Option B needs larger frontend type rewrite; either works |
| A3 | Comparison can run `_compute_tactic_bullets` twice (per orientation) vs one 24-col query | Service §5 | Double query is post-gate; acceptable unless profiling says otherwise |
| A4 | Under Missed/Allowed the Flaws list still returns both motif fields; client suppresses the other chip (D-11 client-side) | Backend §2 chip read | If server-side suppression intended, read path needs a change |
| A5 | Mate exemption uses `FAMILY_TO_MOTIF_INTS["mate"]` as the exemption set | Backend §1 | If a broader/narrower mate set intended, planner adjusts |
| A6 | `FlawCard` receives `flawFilter` via prop (not direct store read) | Frontend FlawCard | Either works; prop keeps card pure |

## Open Questions (RESOLVED)

1. **Depth API unit (half-move vs full-move).** RESOLVED — **API param `max_tactic_depth` is in half-moves** (1:1 with the `*_tactic_depth` SmallInteger column, zero SQL-layer conversion). The player-facing slider/label unit is **full moves** per D-03 (the slider operates in full moves and a `sliderToMax` conversion maps the full-move slider position to the half-ply value sent to the API). See plan `129-02` task 1 for the locked full-move-UI ↔ half-ply-API contract, and Pitfall 2.
2. **Comparison: two queries vs one 24-column query.** RESOLVED — **two queries** for simplicity (A3); both are post-gate so the cost is acceptable. Revisit only if profiling shows the double round-trip matters.
3. **Single-game flaw card path for dual-chip (D-12).** RESOLVED — **the single-game card path DIVERGES; it does NOT reuse `TacticMotifChip` the same way `FlawCard` does, and the orientation-prefix / dual-chip work is intentionally scoped to `FlawCard` only.**

   **Investigated render sites** (`grep TacticMotifChip` + `*_tactic_motif`, VERIFIED):
   - `frontend/src/components/library/FlawCard.tsx:278-279,289-298` — the Flaws-tab list-row card. **This is the only site that gets the orientation prefix + dual-chip + orientation-prefixed `TagLegend` work (plan 129-02 task 3).** It renders one chip per *flaw*, so a single orientation context (the Flaws-tab toggle) applies cleanly.
   - `frontend/src/components/results/LibraryGameCard.tsx:286-296,347-354,628-649` — the single-game view (opened via the FlawCard "Game" modal and the Games tab). It is **structurally different**: it aggregates *unique* `allowed_tactic_motif` values across the whole game (`tacticMotifs` memo), and the chips drive **click-to-cycle + hover highlighting** on the eval chart (`motifPlies`, `highlightedPlies`, `onHover`/`onActivate`). It is per-game, not per-flaw, and has **no orientation toggle** in its context (the orientation toggle is a Flaws-tab filter, D-06/D-09).
   - `frontend/src/components/library/EvalChart.tsx:638-893` — the eval-chart tooltip inside the single-game view; same per-game `allowed_tactic_motif` aggregation, same lack of orientation context.

   **Decision:** D-12's "single-game flaw card" requirement is about the *narration mechanism* (chip + shared `TagLegend`, no inline sentence) — which `LibraryGameCard`/`EvalChart` **already satisfy**. D-10's orientation **prefix** (`missed:`/`allowed:`) is only meaningful where the orientation toggle defines a single active orientation; the single-game view has no such toggle and aggregates per-game, so **the prefix is intentionally NOT applied to `LibraryGameCard` / `EvalChart`** in Phase 129. They keep their current unprefixed `allowed_tactic_motif` chips (`TacticMotifChip` with no `orientation` prop — fully backward-compatible since the prop is optional). No new files, no scope surprise: the orientation-prefix change is `FlawCard.tsx` only. Plan `129-02` `files_modified` is therefore correct as-is (it lists `FlawCard.tsx`, not `LibraryGameCard.tsx`/`EvalChart.tsx`). Carrying the orientation prefix into the per-game cycle/hover machinery (keying `motifPlies`/`highlightedPlies` on a prefixed label) would be a real refactor with no decision behind it — out of scope (flag as a future seed if ever wanted).

## Environment Availability

No new external dependencies. All shadcn primitives (Slider, ToggleGroup, Accordion, InfoPopover) already installed (Phase 126). Backend adds no packages. Dev DB (Docker Postgres) required for backend tests (already in workflow).

## Project Constraints (from CLAUDE.md)

- `query_utils.apply_game_filters` is the single filter source — extend there, never duplicate.
- Routers thin (HTTP only); branching/aggregation in service layer.
- No magic numbers — depth thresholds as named constants in `tacticDepth.ts`.
- `Literal[...]` for fixed value sets (orientation enum); `Sequence[str]` for list params; explicit return types; `ty check` zero errors.
- Theme color constants only in `theme.ts` (no new tokens, D-10); min `text-sm` (chip `text-xs` is the documented exception).
- `data-testid` + ARIA + semantic HTML on all new interactive elements; mobile parity at 375px.
- Beta gate via `useUserProfile().data.beta_enabled`.
- Run `npx tsc -b` before integrating shared-type changes.
- Sentry `capture_exception` in non-trivial backend except blocks (the comparison service already does this).
- No em-dashes in UI copy.

## Sources

### Primary (HIGH confidence — read this session)
- `app/repositories/query_utils.py` (full) — apply_game_filters, is_opponent_expr, tactic clause
- `app/repositories/library_repository.py` (:1-410, :1488-1580) — build_flaw_filter_clauses, _tactic_cols, TacticOrientation, FAMILY_TO_MOTIF_INTS, query_flaws, fetch_tactic_comparison
- `app/models/game_flaw.py` — depth columns + units
- `app/schemas/library.py` (full) — FlawListItem, TacticBullet, TacticComparisonResponse
- `app/services/library_service.py` (:1245-1413) — _compute_tactic_bullets, get_tactic_comparison
- `app/routers/library.py` (:205-253) — tactic-comparison endpoint
- `frontend/src/lib/opponentStrength.ts`, `components/filters/OpponentStrengthFilter.tsx`, `FilterPanel.tsx:258-292`
- `frontend/src/hooks/useFlawFilterStore.ts`, `hooks/useLibrary.ts` (:125-194), `api/client.ts` (:293-340)
- `frontend/src/components/library/TacticMotifChip.tsx` (full), `TacticComparisonGrid.tsx` (full), `FlawCard.tsx:270-298`
- `frontend/src/types/library.ts` (:95-322), `pages/Endgames.tsx:385-400`, `pages/library/FlawsTab.tsx` (grep)
- `reports/tactic-tagger/tactic-tagger-2026-06-20.md` — depth-vs-Rating r=0.322 calibration

## Metadata

**Confidence breakdown:**
- Backend signatures/clauses: HIGH — read current source line-by-line
- Frontend clone targets: HIGH — full reads of every named component
- Schema target shape: MEDIUM — two valid options; recommendation given (A2)
- Depth unit decision: MEDIUM — recommendation given, needs planner lock (A1)

**Research date:** 2026-06-20
**Valid until:** ~2026-07-20 (stable internal code; revisit if 127/128 contracts change)
