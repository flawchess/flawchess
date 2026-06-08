# Phase 110: Flaw-Tag Taxonomy Overhaul — Rename, Impact-Family Rebuild, Tooltip Restore & Active-Filter Highlight - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Bring the **entire flaw-tag stack** (backend literals/constants/columns, the
`game_flaws` DB table, API schemas, repositories/services, and frontend
types/components) into line with the finalized taxonomy in
`.planning/notes/flaw-tag-definitions.md`. Six asks, fixed by the roadmap:

1. **Tempo rename** (pure label/Literal change): `impatient` → `hasty`,
   `considered` → `unrushed`. `_classify_tempo` logic and the `game_flaws.tempo`
   0/1/2 SmallInteger codes are unchanged — only labels, the `TempoTag` Literal,
   comments, and docstrings change.
2. **Impact-family rebuild** (a **behavioral** classifier change, not a rename):
   drop `while-ahead` entirely; replace outcome-dependent `result-changing` with
   the **outcome-independent two-rung ladder** `reversed` (ES ≥70% → ≤30%) /
   `squandered` (ES ≥85% → ≤60%, when not `reversed`), most-severe wins, at most
   one impact tag. Computed only from ES-before/after, never the game result.
3. **Constant churn** (`flaws_service.py`): keep `FROM_WINNING_ES` (0.85,
   `squandered` entry); add `WINNING_LINE_ES` (0.70), `LOSING_LINE_ES` (0.30),
   `SQUANDERED_EXIT_ES` (0.60); remove `RESULT_WIN_THRESHOLD` /
   `RESULT_DRAW_THRESHOLD`.
4. **Canonical chip names**: render `lowercase-with-dash` tag strings on chips
   and in the panel, replacing title-cased `TAG_LABELS`.
5. **Restore definition popovers**: hover/tap a tag chip opens a Radix popover
   (**`tag-name`** bold + `": "` + definition, thresholds interpolated from
   constants — no hard-coded `85%`/`70%`). Reverts the Phase 108 D-05
   chip-as-navigation change.
6. **Drop chip → Flaws deep-links** (direct consequence of #5).
7. **Active-filter highlight**: a chip whose tag matches an active cross-tab
   Flaw filter (`useFlawFilterStore`) gets a distinct emphasis, desktop + mobile.

**Dev-only data backfill**: re-run `scripts/backfill_flaws.py` for **users 28 &
44** in the dev DB. No prod migration/backfill (v1.24 unshipped; `game_flaws`
absent/empty in prod).

**Out of scope**: the future tactic / error-nature tag family; any prod data
migration or backfill; persisting inaccuracies in `game_flaws` (D-03 from 108
stands); changing tempo/opportunity/phase/severity *logic*; refactoring
unrelated `gen_*_ts.py` generators (backlog — see Deferred).

</domain>

<decisions>
## Implementation Decisions

### Migration & data (game_flaws impact columns)
- **D-01 (add-false + script backfill, NOT SQL-compute):** The new Alembic
  **alter** migration drops `is_while_ahead` / `is_result_changing` and adds
  `is_reversed` / `is_squandered` as `NOT NULL` booleans with
  `server_default=false`. It does **not** compute the new values in SQL. Existing
  rows get `false`; correct values come from re-running
  `scripts/backfill_flaws.py` for users 28 & 44. Other dev users' impact columns
  stay `false`/stale until manually re-backfilled — acceptable (dev-only, v1.24
  unshipped), and it matches roadmap success criterion #4.
  - *Tradeoff noted & rejected:* the new ladder is outcome-independent and
    `es_before`/`es_after` are already stored on `game_flaws`, so a pure-SQL
    `UPDATE` in the migration **could** have populated all users correctly with no
    script. User chose the simpler add-false + scoped-backfill path; the
    SQL-compute option is recorded here in case a future all-users refresh is
    wanted.
  - Do **NOT** edit the `20260606` `game_flaws` create migration — a forward
    alter migration only (editing create would force a disallowed dev-DB reset).
  - `is_miss` / `is_lucky_escape` columns and the `tempo` SmallInteger codes are
    untouched.
  - **Planner discretion:** standard alembic add-NOT-NULL-with-server_default then
    optionally drop the server_default afterward (to match `is_miss`/
    `is_lucky_escape` which carry no server_default), plus a working `downgrade`.

### Flaw-Stats panel impact surfacing
- **D-02 (drop the band's headline impact stat):** Remove the headline impact
  rate from `FlawStatsBand` entirely (currently shows `result_changing_rate` as
  the "W3" stat). The band loses any aggregate impact number.
- **D-03 (keep impact in the distribution):** `FlawTagDistribution` (the tag-rate
  breakdown) **keeps** impact: add `reversed_rate` + `squandered_rate` to the
  `TagDistribution` schema and render both; remove `while_ahead_rate` and
  `result_changing_rate`. The distribution is the natural home for aggregate tag
  rates; the band stays high-level (severity/counts), the distribution carries
  the full per-tag picture. `miss_rate` / `lucky_escape_rate` / `phase_histogram`
  unchanged.

### Definition-popover threshold source (frontend)
- **D-04 (focused generator, do NOT merge):** Add a small
  `scripts/gen_flaw_thresholds_ts.py` that emits a `frontend/src/generated/`
  constants file from the `flaws_service.py` thresholds, mirroring the existing
  `scripts/gen_endgame_zones_ts.py` pattern (CI drift check, re-run after editing
  the Python constants). The popover copy interpolates the threshold numbers from
  this generated file — no hard-coded `70%`/`85%`/`60%`/`30%` in TS strings.
  - **`gen_endgame_zones_ts.py` is left untouched.** Merging the two into a
    generic `gen_ts_constants.py` was considered and **rejected for this phase**:
    different output shapes (zone registry vs ~4 flat scalars), it pulls an
    unrelated CI-gated surface into this phase's blast radius, and the abstraction
    only earns its keep at 3+ consumers. Captured as a backlog refactor (see
    Deferred).

### Active-filter chip highlight
- **D-05 (ring/outline):** A chip whose tag matches an active filter in
  `useFlawFilterStore` gets a **colored ring/outline** (e.g. `ring-2` + ring
  offset in the family color), via a new `theme.ts` constant. No size/layout
  change, no background-fill swap, no bold. Applies on **both** Games cards and
  Flaws cards, **desktop and mobile**. Non-matching chips unchanged.

### Restore popover / drop deep-links (mechanical, locked by roadmap)
- **D-06:** `TagChip` stops being a `<navigate>` trigger to
  `/library/flaws?tag=…` and becomes a Radix Popover trigger again. Phase 107
  shipped `TagChip` as a display-only Popover trigger before Phase 108 Plan 08
  (D-05) replaced it with navigation — **restore from that 107 implementation /
  git history** rather than rebuilding from scratch. The popover body may use
  `text-xs` per the CLAUDE.md tooltip exception. Whole chip is the hover/tap
  trigger (no separate HelpCircle icon).
- **D-07:** Rebuild `tagDefinitions.ts` — restore a `TAG_DEFINITIONS` map
  (definition prose per tag, thresholds interpolated from the D-04 generated
  constants). Canonical `lowercase-with-dash` names replace title-cased
  `TAG_LABELS` on chips and panel (`TAG_LABELS` may stay only where a non-chip
  surface genuinely needs a human label, e.g. `FlawFilterControl` — planner to
  confirm; the chip/panel display uses the literal tag string).
  - **D-07 amendment (Phase 110 UAT, 2026-06-08):** The user opted to also use
    canonical `lowercase-with-dash` names in `FlawFilterControl` *and* surface tag
    definitions there on hover. `TAG_LABELS` therefore has zero consumers and was
    removed entirely. Every tag surface (chips, panel, filter control) now renders
    the raw tag string; the filter buttons reuse the TagChip hover-popover pattern
    (Radix `Popover.Anchor` so click still toggles the filter; hover is desktop-only
    per the CLAUDE.md tooltip-parity exception).

### Claude's Discretion
- The exact `theme.ts` ring constant name/value and ring width/offset.
- Whether `TAG_LABELS` is fully removed or retained for `FlawFilterControl`
  button labels (the roadmap names canonical lowercase-with-dash on chips/panel;
  the filter-control buttons are a separate surface).
- Alembic `server_default` drop-after-add and `downgrade` shape (D-01).
- Tag-order in `_build_tags` after the impact rebuild (the doc lists
  `reversed → squandered → miss → lucky-escape → phase → tempo`; impact still
  appends at most one of reversed/squandered).
- Whether `_classify_impact` is one new helper replacing `_is_result_changing`
  (the `user_result` arg is no longer needed for impact — outcome-independent).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Authoritative taxonomy (read first — supersedes Phase 105/106 names)
- `.planning/notes/flaw-tag-definitions.md` — the **single source of truth** for
  this phase: tooltip-ready definitions for every tag, the outcome-independent
  impact ladder (`reversed` 70→30 / `squandered` 85→60, most-severe wins), the
  tempo renames, the threshold reference table (constant names + values +
  shipped/proposed status), and the Deprecated/renamed table.
  - **⚠ Resolved conflict:** this note's "Implementation status" + the
    `while-ahead` removal row claim **"no DB migration — pure code + docs."**
    That is **STALE** — it predates Phase 108, which materialized these tags into
    the `game_flaws` table. There **IS** a forward Alembic migration this phase
    (drop `is_while_ahead`/`is_result_changing`, add `is_reversed`/`is_squandered`
    — D-01). **Follow the ROADMAP, not the note's "no migration" line.**
- `.planning/notes/flaw-tag-naming.md` — the prior (Phase 106/107) rename layer
  this builds on; useful for the `low-clock`/`miss`/`lucky-escape`/phase naming
  and the tag→family mapping. The impact + tempo-residual renames in
  `flaw-tag-definitions.md` supersede this note's impact rows.

### Roadmap (the locked scope & success criteria)
- `.planning/ROADMAP.md` §"Phase 110" (≈ lines 226–264) — the 7-item scope, the 6
  success criteria (grep-clean, classifier boundary tests, migration upgrades dev
  DB without reset, 28/44 repopulated, canonical names + popover, active-filter
  emphasis), and the explicit out-of-scope list.

### Phase 108 contract (the materialization this phase migrates)
- `.planning/phases/108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr/108-CONTEXT.md`
  — the `game_flaws` materialization, D-05 (chip-as-nav, **reverted here**), D-09
  (`backfill_flaws.py` `--db`/`--user-id` pattern), D-10 (one-classify-path
  freshness: import hook / reimport / reclassify / backfill all call
  `classify_game_flaws`).
- `.planning/seeds/SEED-038-flaw-filter-and-game-flaws-materialization.md` — locks
  the `game_flaws` schema, single-flaw `EXISTS` semantics, the shared
  WHERE-clause predicate builder, OR-within / AND-across family logic.

### Backend (the rename/rebuild targets)
- `app/services/flaws_service.py` — impact constants (lines ~54–58),
  `FlawTag`/`TempoTag` Literals (~76–88), `_classify_tempo` (~298, names only),
  `_is_result_changing` (~396, **replaced** by an outcome-independent impact
  helper), `_build_tags` (~440, impact ladder), `classify_game_flaws` (~498).
- `app/models/game_flaw.py` — the impact boolean columns (lines 54–55) the
  migration alters; `es_before`/`es_after` (59–60) already stored.
- `app/schemas/library.py` — `TagDistribution` (line ~184): drop
  `while_ahead_rate`/`result_changing_rate`, add `reversed_rate`/`squandered_rate`
  (D-03).
- `app/repositories/game_flaw_repository` / `library_repository`,
  `app/services/library_service.py`, `app/services/stats_service.py`,
  `app/repositories/query_utils.py` — EXISTS predicates + tag aggregation that
  reference the impact booleans / rate computation.

### Frontend (types/components)
- `frontend/src/types/library.ts` — `FlawTag` / `TempoTag` (lines ~14–30),
  `TagDistribution` rate fields (~136–149).
- `frontend/src/lib/tagDefinitions.ts` — rebuild `TAG_DEFINITIONS` + canonical
  names (D-07).
- `frontend/src/components/library/TagChip.tsx` — revert to Popover trigger +
  add active-filter ring (D-05/D-06).
- `frontend/src/components/library/FlawStatsBand.tsx` — drop headline impact stat
  (D-02); `FlawTagDistribution.tsx` — swap impact rates (D-03);
  `FlawFilterControl.tsx`, `FlawStatsPanel`.
- `frontend/src/lib/theme.ts` — add the active-filter ring constant (D-05).
- `frontend/src/store/` — `useFlawFilterStore` (active-filter match source).

### Generation precedent
- `scripts/gen_endgame_zones_ts.py` — the Python→TS generator + CI-drift pattern
  `scripts/gen_flaw_thresholds_ts.py` mirrors (D-04). Do **not** edit it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`classify_game_flaws`** (`flaws_service.py`) — the single classification
  kernel (D-10): import hook, `reimport_games.py`, `reclassify_positions.py`, and
  `backfill_flaws.py` all call it, so updating the impact ladder here propagates
  everywhere with no second write path.
- **Phase 107 `TagChip` popover implementation** — recoverable from git history
  (107 shipped it as a display-only Radix Popover trigger before 108 D-05 swapped
  in navigation). Restore rather than rebuild (D-06).
- **`scripts/backfill_flaws.py`** — already accepts `--db {dev|benchmark|prod}`
  and `--user-id` (Phase 108 D-09); re-run for 28 & 44 (D-01 backfill).
- **`gen_endgame_zones_ts.py`** — copy its structure for the new thresholds
  generator (D-04).
- **`es_before`/`es_after` already on `game_flaws`** — the new impact ladder is
  computable from stored columns (enabled the rejected SQL-compute option; still
  useful for any future all-users refresh).

### Established Patterns
- Python→TS codegen with a CI drift gate (`gen_endgame_zones_ts.py` →
  `frontend/src/generated/endgameZones.ts`). New thresholds file follows it.
- Theme constants live in `theme.ts` (CLAUDE.md) — the active-filter ring color
  is a `theme.ts` constant, not inline (D-05).
- Apply every change to **both desktop and mobile** chip surfaces (CLAUDE.md
  mobile rule) — the active-filter ring and the popover restore both touch Games
  cards + Flaws cards on both layouts.
- `text-xs` is permitted in the popover body (CLAUDE.md tooltip exception).
- Forward-only Alembic alter migration that upgrades an existing dev DB without a
  reset (no editing the create migration; no `bin/reset_db.sh` gating —
  per-project norm).

### Integration Points
- New Alembic migration (alter `game_flaws`): drop 2 impact booleans, add 2
  (D-01).
- `useFlawFilterStore` ↔ `TagChip` — the active-filter match drives the ring
  (D-05); chips on both Games and Flaws cards subscribe.
- `TagChip` stops calling `useNavigate`; becomes a Popover trigger (D-06) — check
  no caller relied on the navigation side effect.

</code_context>

<specifics>
## Specific Ideas

- **Grep-clean is a success gate:** no `while-ahead`/`while_ahead`/
  `is_while_ahead`, `result-changing`/`result_changing`/`is_result_changing`,
  `impatient`, or `considered` may remain in `app/` or `frontend/src/` when done
  (roadmap success criterion #1).
- **Classifier boundary tests required:** unit tests must cover the ladder
  boundaries (70/30 and 85/60) and the deliberate no-impact gap (e.g. 78%→45%
  carries no impact tag — roadmap success criterion #2).
- **Popover copy format:** **`tag-name`** (bold) + `": "` + definition, every
  threshold interpolated from the generated constants (D-04/D-07).
- Active-filter emphasis = ring/outline only (D-05), not bold or fill.

</specifics>

<deferred>
## Deferred Ideas

- **Unify the `gen_*_ts.py` scripts** into a generic `gen_ts_constants.py`
  (absorbing `gen_endgame_zones_ts.py`, the new flaw-thresholds generator, and
  any future Python→TS exports behind a shared `_emit_ts_module()` helper +
  single CI drift gate). Rejected for Phase 110 (scope creep into an unrelated
  CI-gated surface; abstraction earns its keep at 3+ consumers). Revisit as a
  standalone refactor when a third generator appears. (D-04.)
- **SQL-compute the impact columns for ALL dev users** in a future all-users
  refresh, leveraging stored `es_before`/`es_after` — the outcome-independent
  ladder makes this trivial. Not needed now (D-01 backfills only 28/44).
- **The future tactic / error-nature tag family** (`chess_detect`) — out of
  scope (roadmap + taxonomy note); cause-of-error naming is reserved for it.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool*
*Context gathered: 2026-06-07*
