# Phase 175: Board & Filter — Gem/Great Consumption - Context

**Gathered:** 2026-07-16
**Status:** Ready for planning

<domain>
## Phase Boundary

The analysis board and the Library games filter stop recomputing gem/great
client-side and instead read the `game_best_moves` rows that Phase 174 now
stores. On the board, gem/great markers appear instantly for analyzed-game
mainlines — no background sweep, no dependency on device power or live-engine
load. In the Library, "has gem" / "has great" toggles filter games via the
existing flaw/tactic `EXISTS` machinery, composing with every other filter.

**In scope (Phase 175 only):**
- `EvalPoint` gains stored gem/great fields; the board renders them (BOARD-01).
- `useGemSweep.ts` demoted to a free-play-only fallback (BOARD-02).
- "has gem" / "has great" Library game filter (FILT-01).
- Introducing the **"great" tier to the frontend for the first time** (the board
  has only ever rendered gem — `classifyGem`; there is no existing "great"
  concept in the frontend).

**Out of scope:**
- Backend inference/storage — done in Phase 174 (`game_best_moves`,
  `classify_best_move`, the eval-apply candidate-row builder).
- Corpus backfill of existing analyzed games — Phase 176 (BACK-01).
- Retuning the Gem (0.20) / Great (0.50) thresholds — GEMS-07 constants-only
  change, deferred to a post-pipeline calibration.

</domain>

<decisions>
## Implementation Decisions

### Sweep fate + no-stored-data behavior (BOARD-02)
- **D-01:** **Demote `useGemSweep.ts` to a documented free-play-only fallback**,
  do NOT fully delete it. Analyzed-game **mainlines** are driven entirely by the
  stored backend rows (instant, no sweep). The live-engine sweep path is
  retained ONLY for positions with **no stored best-move rows**: off-mainline
  variations the user explores, free-play / pasted-FEN positions, and
  freshly-played bot games not yet analyzed. BOARD-02 resolves as "demoted";
  SEED-107 closes as superseded.
- **D-01a:** Because the mainline no longer sweeps, the deferred **mainline-sweep
  bugs WR-01 / WR-03 / WR-05** (from `172-deferred-review-findings.md`) are moot
  — the sweep should no longer run over mainline plies at all. The retained
  fallback path must still address **WR-06** (wrap the sweep effects'
  `resolveCandidate` + watchdog/fast-fail callbacks in `useCallback([])` to kill
  the latent stale-closure trap) and the IN-01..04 cleanups where they still
  apply to the fallback-only code.

### "Great" marker display (BOARD-01)
- **D-02:** "Great" renders as a **custom SVG icon: a blue circle with a white
  exclamation point** ("!"), mirroring chess.com's Great Move. Gem is unchanged
  (lucide `Gem` icon in `MAIA_ACCENT`).
- **D-02a:** The blue is a **named theme constant** in `frontend/src/lib/theme.ts`
  (e.g. `GREAT_ACCENT`) — never hard-coded (theme.ts rule). Add a `GREAT_GLYPH`
  record analogous to `GEM_GLYPH` (`frontend/src/lib/gemGlyph.ts`) as the single
  source of truth consumed by both the icon component and the board SVG marker,
  so the two never drift.
- **D-02b:** Great appears on **every surface gem does**: the board corner badge
  (`boardMarkers.tsx`), the move-list / variation-tree glyph, the eval-chart
  dot, and the move popover (`UnifiedMovePopover` / `GemMoveBadge` analog). No
  surface is gem-only.

### EvalPoint delivery shape (BOARD-01)
- **D-03:** The backend delivers a **pre-classified tier string** on `EvalPoint`:
  `best_move_tier: 'gem' | 'great' | null`, computed by the authoritative
  `classify_best_move` (`app/services/best_move_candidates.py`). The board
  renders the tier directly — no cp→expected-score sigmoid or margin logic
  shipped to the frontend for the stored path.
- **D-03a:** `EvalPoint` **also carries `maia_prob` (float | null)** for the
  popover detail ("~X% of rating-peers would find this"), matching what the
  current gem popover shows (`maiaProbability` / elo / byOpponent).
- **D-03b:** Rationale: FILT-01 **forces backend classification regardless** (the
  filter `EXISTS` must know the tier in SQL), so reusing that same classifier for
  the board means board and filter agree **by construction** — one classifier,
  one retune surface (backend constants). A stored-corpus threshold retune is
  then a backend-only change with zero frontend redeploy.
- **D-03c:** Frontend `classifyGem` (and a **new `classifyGreat`**) survive ONLY
  for the **live-engine fallback path** (D-01), which has no stored tier and must
  classify live `maia_prob` on the client. The stored path never calls them.

### Filter scoping + layout (FILT-01)
- **D-04:** "has gem" / "has great" are scoped to the **user's own moves** — a
  game qualifies when the USER played a qualifying move. The `EXISTS` subquery
  joins `game_best_moves` on plies where **ply-parity == the game's `user_color`**
  AND `classify_best_move(...) == gem/great`. This matches the existing
  user-scoped flaw/tactic filter pattern and the product's self-analysis meaning
  ("games where I found a brilliancy"), NOT opponent-scouting.
- **D-04a:** `game_best_moves` has no `user_id` / mover column, so mover color is
  derived from ply parity (same as the flaw filter, which scopes both-players'
  `game_flaws` rows by parity-vs-`user_color`). `classify_best_move` needs
  `mover_color` anyway to compute the cp→ES margin, so parity is already required.
- **D-05:** UI is **two independent boolean toggles** ("has gem", "has great")
  placed near the existing flaw/tactic controls in BOTH `FilterPanel` (desktop)
  and `MobileFilterDrawer`. Both toggled on = games with a gem **OR** a great
  (union — matches how the existing flaw-family `EXISTS` unions). Not a single
  cycling 3-state control.
- **D-05a:** The filter must **compose correctly with every other existing game
  filter** (time control, color, rated, opponent type, recency) exactly like the
  flaw/tactic filters — built on `apply_game_filters()` in
  `app/repositories/query_utils.py`, never a parallel filter path.

### Claude's Discretion
- Exact popover copy for great, precise eval-chart dot styling for great, the
  specific new theme accent hex, the `GreatMoveIcon` SVG component name/markup,
  the exact request-param names for the two filter toggles, and whether a
  supporting partial index on `game_best_moves` is warranted for the filter —
  researcher/planner decides within the locked decisions above.

### Folded Todos
- **`172-deferred-review-findings.md`** (`resolves_phase: 175`) — deferred
  frontend gem-sweep code-review findings. Folded per D-01a: WR-01/03/05 (mainline
  sweep) are mooted by demotion; WR-06 (stale-closure effects) + IN-01..04 apply
  to the retained fallback path and should be resolved as the sweep is scoped down.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source & requirements
- `.planning/ROADMAP.md` §"Phase 175" — goal, success criteria, dependency wave B.
- `.planning/REQUIREMENTS.md` §"Board (BOARD)" + §"Game Filter (FILT)" —
  BOARD-01, BOARD-02, FILT-01.
- `.planning/seeds/SEED-108-backend-gem-great-detection.md` — the full locked
  design (D-1…D-5); this phase is its board/filter consumption half.
- `.planning/phases/174-backend-maia-inference-best-move-storage-spike-gated/174-CONTEXT.md`
  — the Phase 174 decisions this phase consumes (D-05 stored-cp convention,
  query-time classification, ELO clamp).

### Backend — stored data + the authoritative classifier
- `app/models/game_best_move.py` — the stored candidate table
  (`maia_prob` REAL, `best_cp`/`second_cp`/`best_mate`/`second_mate` SmallInteger,
  PK `(game_id, ply)`, no `user_id`).
- `app/services/best_move_candidates.py:126-157` — `classify_best_move` (the
  single gem/great/neither classifier) + constants `GEM_MAIA_MAX_PROB` (0.20),
  `GREAT_MAIA_MAX_PROB` (0.50), `MISTAKE_DROP`. Board (D-03) and filter (D-04)
  both use this.
- `app/schemas/library.py:32-45` — `EvalPoint` schema to extend with
  `best_move_tier` + `maia_prob` (D-03).
- `app/repositories/library_repository.py` (~line 920 / 2356) — where `EvalPoint`
  / per-ply board data is assembled; join `game_best_moves` here.
- `app/repositories/query_utils.py` — `apply_game_filters()` + the flaw/tactic
  user-scoped `EXISTS` machinery (lines ~111, ~241-284) to extend for FILT-01
  (D-04/D-05a).

### Frontend — board consumption + marker rendering
- `frontend/src/types/library.ts:105-118` — TS `EvalPoint` (mirror the backend
  schema change).
- `frontend/src/lib/gemGlyph.ts` — `GEM_GLYPH` single-source-of-truth pattern to
  mirror for `GREAT_GLYPH` (D-02a).
- `frontend/src/lib/theme.ts` — `MAIA_ACCENT`; add `GREAT_ACCENT` here (D-02a).
- `frontend/src/components/icons/GemIcon.tsx` — sibling for the new blue-"!"
  `GreatMoveIcon` (D-02).
- `frontend/src/components/board/boardMarkers.tsx` — board corner badge (add
  great branch, D-02b).
- `frontend/src/components/analysis/GemMoveBadge.tsx`,
  `frontend/src/components/analysis/UnifiedMovePopover.tsx`,
  `frontend/src/components/analysis/VariationTree.tsx` — move-list glyph + popover
  surfaces (add great, D-02b).
- `frontend/src/pages/Analysis.tsx` — current gem consumption + the
  `useGemSweep` wiring to demote to fallback-only (D-01); `classifyGem` display
  sites (~1233, ~1745) that switch to stored `best_move_tier` for the mainline.
- `frontend/src/lib/gemMove.ts` — `classifyGem` (+ new `classifyGreat`) retained
  for the fallback path only (D-03c).
- `frontend/src/hooks/useGemSweep.ts` — demote to free-play-only fallback (D-01).

### Frontend — filter UI
- `frontend/src/components/filters/FilterPanel.tsx` +
  `frontend/src/components/filters/MobileFilterDrawer.tsx` +
  `frontend/src/components/filters/FlawFilterControl.tsx` — the flaw/tactic toggle
  pattern to mirror for the two new gem/great toggles (D-05).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`classify_best_move`** (`best_move_candidates.py`) — one authoritative
  gem/great classifier; board tier (D-03) and filter EXISTS (D-04) both call it.
- **`GEM_GLYPH` / `gemGlyph.ts`** — the "one record, two consumers" pattern
  (icon component + board SVG marker) to clone as `GREAT_GLYPH` (D-02a).
- **Flaw/tactic `EXISTS` filter machinery** (`query_utils.py`) — user-scoped by
  ply-parity-vs-`user_color`; directly reused for the gem/great filter (D-04).
- **`apply_game_filters()`** — the single filter implementation the new toggles
  compose into (D-05a).

### Established Patterns
- The frontend has **no "great" concept today** — only `classifyGem`. This phase
  introduces it (new icon, theme constant, glyph record, classifier, filter).
- Filters are user-scoped via ply parity (game_flaws stores both players' rows).
- Theme colors with semantic meaning live in `theme.ts`, never hard-coded.

### Integration Points
- Backend: join `game_best_moves` at `EvalPoint` assembly
  (`library_repository.py`); classify with `classify_best_move`; extend
  `apply_game_filters()` for the toggles.
- Frontend: board mainline switches from `useGemSweep` to stored
  `best_move_tier`; sweep retained only where no stored rows exist.

</code_context>

<specifics>
## Specific Ideas

- Great marker = **blue circle, white "!"** (custom SVG), explicitly chess.com's
  Great Move styling. Gem stays the lucide gem in `MAIA_ACCENT`.
- Board and filter must agree by construction — one backend classifier feeds both
  (send the tier string, not raw floats).
- "has gem" means **my** gem, not any gem — the filter surfaces the user's own
  best moments, consistent with the self-analysis product framing.

</specifics>

<deferred>
## Deferred Ideas

- **Gem (0.20) / Great (0.50) threshold calibration against real per-game
  frequency** — GEMS-07 constants-only retune; belongs to a post-pipeline
  calibration, not this phase.
- **Opponent-scouting gem/great filter (any-move scope)** — considered and
  rejected for FILT-01 (D-04 chose user-scoped). If opponent scouting later wants
  it, that is a separate, additive filter option.
- **Corpus backfill of existing analyzed games** → Phase 176 (BACK-01).

### Reviewed Todos (not folded)
- **`2026-03-11-bitboard-storage-for-partial-position-queries.md`** — unrelated
  DB idea (partial-position bitboard queries); keyword-only match, out of scope.
- **`2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`** — an unrelated
  Tailwind axis-label typo (weak "175" keyword match); not part of this phase.

</deferred>

---

*Phase: 175-board-filter-gem-great-consumption*
*Context gathered: 2026-07-16*
