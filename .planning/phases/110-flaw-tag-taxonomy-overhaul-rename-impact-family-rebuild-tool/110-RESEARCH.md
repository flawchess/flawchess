# Phase 110: Flaw-Tag Taxonomy Overhaul — Research

**Researched:** 2026-06-07
**Domain:** Backend classifier refactor + Alembic alter migration + FastAPI schema/repo churn + React component revert/restore. No external dependencies, no new packages.
**Confidence:** HIGH (every claim verified against current source on `gsd/phase-110…` branch)

This is a **verification report**, not an exploration. CONTEXT.md (D-01..D-07) and `flaw-tag-definitions.md` are authoritative. Below, each target is marked **CONFIRMED** (matches CONTEXT) or **DRIFT** (CONTEXT is slightly off — described). No alternatives are proposed.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** New Alembic **alter** migration drops `is_while_ahead`/`is_result_changing`, adds `is_reversed`/`is_squandered` as `NOT NULL` booleans with `server_default=false`. **No SQL-compute** of new values — existing rows get `false`; correct values come only from re-running `backfill_flaws.py` for users 28 & 44. Do **NOT** edit the `20260606` create migration. `is_miss`/`is_lucky_escape`/`tempo` untouched. Planner discretion on server_default-drop-after-add + downgrade shape.
- **D-02:** Remove the headline impact rate (`result_changing_rate`, "Result-changing" cell) from `FlawStatsBand` entirely. Band loses any aggregate impact number.
- **D-03:** `FlawTagDistribution` keeps impact — add `reversed_rate` + `squandered_rate` to `TagDistribution`; remove `while_ahead_rate` + `result_changing_rate`. `miss_rate`/`lucky_escape_rate`/`phase_histogram` unchanged.
- **D-04:** Add `scripts/gen_flaw_thresholds_ts.py` emitting a `frontend/src/generated/` constants file from `flaws_service.py` thresholds, mirroring `gen_endgame_zones_ts.py` (CI drift check). Popover copy interpolates thresholds from it — no hard-coded `70%`/`85%`/`60%`/`30%`. **Do NOT edit `gen_endgame_zones_ts.py`** and do NOT merge generators.
- **D-05:** Active-filter chip highlight = colored **ring/outline** (`ring-2` + offset in family color) via a new `theme.ts` constant. No size/fill/bold change. Both Games + Flaws cards, desktop + mobile.
- **D-06:** `TagChip` stops being a `<navigate>` trigger; becomes a Radix Popover trigger again. **Restore from Phase 107 git history** (commit `8c5ebc81`), not from scratch. Popover body may use `text-xs`. Whole chip is the trigger (no HelpCircle icon).
- **D-07:** Rebuild `tagDefinitions.ts` — restore `TAG_DEFINITIONS` (prose per tag, thresholds from D-04 generated constants). Canonical `lowercase-with-dash` names on chips + panel. `TAG_LABELS` may stay only for non-chip surfaces (e.g. `FlawFilterControl`) — planner to confirm.

### Claude's Discretion
- Exact `theme.ts` ring constant name/value, ring width/offset.
- Whether `TAG_LABELS` is removed or kept for `FlawFilterControl` button labels.
- Alembic `server_default` drop-after-add + `downgrade` shape.
- Tag-order in `_build_tags` after impact rebuild (doc lists `reversed → squandered → miss → lucky-escape → phase → tempo`).
- Whether `_classify_impact` is one new helper replacing `_is_result_changing` (the `user_result` arg is no longer needed for impact).

### Deferred Ideas (OUT OF SCOPE)
- Unify `gen_*_ts.py` into a generic `gen_ts_constants.py` (backlog, 3+ consumers).
- SQL-compute impact columns for ALL dev users (future all-users refresh).
- The future tactic / error-nature tag family (`chess_detect`).
- Any prod data migration/backfill. Persisting inaccuracies. Changing tempo/opportunity/phase/severity *logic*.
</user_constraints>

---

## Project Constraints (from CLAUDE.md)

These apply to all Phase 110 code:
- **DB:** PostgreSQL/asyncpg only; SQLAlchemy 2.x async (`select()` API); Alembic migrations auto-run on container start.
- **ty:** `uv run ty check app/ tests/` must pass with zero errors. Use `Sequence[str]` (covariant) not `list[str]` for params accepting `list[Literal[...]]`. Add explicit return types.
- **No magic numbers:** new ES thresholds are named constants (`WINNING_LINE_ES`, `LOSING_LINE_ES`, `SQUANDERED_EXIT_ES`).
- **theme.ts constants:** active-filter ring color is a `theme.ts` constant, not inline (D-05).
- **text-sm floor** except hover/tap tooltip bodies (popover body may use `text-xs`, D-06 / CLAUDE.md exception).
- **Mobile + desktop parity:** ring + popover apply to both Games cards and Flaws cards on both layouts.
- **data-testid + ARIA** on all interactive elements; semantic `<button>`/`<span role="button">`.
- **Literal types** for fixed-value fields (`FlawTag`, `TempoTag`).
- **Full local gate before squash-merge to `main`:** `ruff format` + `ruff check --fix` + `ty check` + `pytest -n auto -x` + `(cd frontend && npm run lint && npm test -- --run)`. The Zone drift CI gate now also covers the new generated flaw-thresholds file (see Pitfall 5).
- **No dev DB reset in the plan** — the migration must upgrade the existing dev DB in place (success gate).

---

## Summary

Every claim in CONTEXT.md's code-location map is **CONFIRMED** with only three minor drifts (line numbers shifted, store path, and the `flawThresholds.ts` provenance — all detailed below). The phase is exactly the locked refactor: a behavioral impact-family rebuild in `flaws_service.py`, a forward Alembic alter migration on `game_flaws`, mechanical rename/swap churn across schemas/repos/services/frontend, a TagChip revert-and-restore from Phase 107 git, a new Python→TS generator, and a dev-only backfill of users 28 & 44.

The two highest-value findings for the planner:
1. **`classify_game_flaws` does NOT write to `game_flaws`.** It returns `list[FlawRecord]` (in-memory tags). The materialization writer is `app/repositories/game_flaws_repository.py::flaw_record_to_row` (lines 100–115), which maps the tag strings to the boolean columns. The migration, the repo writer, AND the classifier all change. CONTEXT §"how `classify_game_flaws` writes the impact columns" is slightly off — the classifier emits tags; the *repository* writes columns.
2. **`frontend/src/lib/flawThresholds.ts` existed in Phase 107 but was deleted in Phase 108.** The Phase 107 `tagDefinitions.ts` imported from it. D-04's `gen_flaw_thresholds_ts.py` → `frontend/src/generated/flawThresholds.ts` (or similar) **replaces** that hand-written file with a generated one. The restore is NOT a clean `git checkout` of the 107 files — the import path changes from `@/lib/flawThresholds` (hand-written, gone) to the new generated module, and the constants themselves change (`RESULT_WIN_THRESHOLD`/`RESULT_DRAW_THRESHOLD` → `WINNING_LINE_ES`/`LOSING_LINE_ES`/`FROM_WINNING_ES`/`SQUANDERED_EXIT_ES`).

**Primary recommendation:** Execute strictly in dependency order — backend classifier + constants first, then the repo writer + migration, then schema/repo/service rate churn, then the D-04 generator, then the frontend revert/restore + active-filter ring, then backfill 28 & 44, then grep-clean verification + boundary tests. The grep-clean gate and `ty` gate catch any missed reference.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Impact tag classification (outcome-independent ladder) | API/Backend (`flaws_service.py`) | — | Pure transform over stored ES; never the game result |
| Persisting impact tags as boolean columns | API/Backend (`game_flaws_repository.py`) | Database (alter migration) | Single FlawRecord→row writer (D-10); columns defined by migration |
| Impact-rate aggregation | API/Backend (`library_repository` 12-tuple + `library_service`) | — | SQL `count().filter()` over `game_flaws`, shaped into `TagDistribution` |
| Threshold source of truth → frontend | API/Backend (Python constants) → codegen | Frontend (generated TS) | Python is authoritative; TS is a CI-drift-gated mirror (D-04) |
| Tag chip rendering + definition popover | Frontend (`TagChip.tsx`) | — | Display-only; popover copy interpolates generated thresholds |
| Active-filter match → ring highlight | Frontend (`useFlawFilterStore` ↔ `TagChip`) | — | Store holds active tags; chip subscribes and rings on match |
| Dev data backfill | Script (`backfill_flaws.py`) | API/Backend (`classify_game_flaws`) | Routes through the single classify kernel (D-10) |

---

## Standard Stack

No new packages. Everything is already in the repo. Verification-only table:

| Tool | In repo | Used for in this phase |
|------|---------|------------------------|
| SQLAlchemy 2.x async + Alembic | ✓ | The alter migration + ORM column edits |
| Radix UI (`radix-ui` Popover primitive) | ✓ (used in Phase 107 TagChip) | The restored definition popover (D-06) |
| lucide-react | ✓ | Chip icons (unchanged set) |
| Tailwind `ring-*` utilities | ✓ (built-in) | Active-filter ring (D-05) |
| `useSyncExternalStore` (React built-in) | ✓ | `useFlawFilterStore` (no Zustand) |

**No `npm install` / `uv add` required. Package Legitimacy Audit is N/A — zero external packages introduced.**

---

## Verification Results (CONFIRMED / DRIFT per CONTEXT item)

### 1. Backend classifier — `app/services/flaws_service.py`

| CONTEXT claim | Reality | Status |
|---------------|---------|--------|
| Impact constants block "~54–58" | `FROM_WINNING_ES = 0.85` at **line 54**; `RESULT_WIN_THRESHOLD = 0.70` at **line 57**; `RESULT_DRAW_THRESHOLD = 0.40` at **line 58** | **CONFIRMED** |
| `FlawTag`/`TempoTag` Literals "~76–88" | `FlawTag` Literal at **lines 76–87** (contains `"while-ahead"` L79, `"result-changing"` L80, `"impatient"` L82, `"considered"` L83); `TempoTag` at **line 88** (`Literal["low-clock", "impatient", "considered"]`) | **CONFIRMED** |
| `_classify_tempo` "~298, names only" | At **line 298**. Logic is unchanged by this phase; only the two return strings `"impatient"` (L330) and `"considered"` (L331) rename, plus docstring (L305, L309, L312). The 0/1/2 tempo codes are unaffected | **CONFIRMED** |
| `_is_result_changing` "~396, replaced" | At **lines 396–414**. Signature: `(es_before, es_after, user_result)`. Uses `RESULT_WIN_THRESHOLD`/`RESULT_DRAW_THRESHOLD`, branches on `user_result == "win"` vs draw/loss | **CONFIRMED** |
| `_build_tags` "~440, impact ladder" | At **lines 430–469**. Append order (L447–467): `while-ahead` (L450) → `result-changing` (L453) → `miss` (L455) → `lucky-escape` (L459) → phase (L461) → tempo (L466). Docstring states order at L443 | **CONFIRMED** |
| `classify_game_flaws` "~498, writes impact columns" | At **lines 498–557**. **It does NOT write columns** — it returns `list[FlawRecord]` and the per-flaw `tags` list (L544). `user_result` is derived at L532 via `derive_user_result(game.result, game.user_color)` and threaded into `_build_tags` (L552) | **DRIFT** (see note below) |

**DRIFT — the impact-column writer is in the repository, not the classifier.** `classify_game_flaws` builds in-memory `FlawRecord` dicts whose `tags` list contains the strings. The string→column mapping lives in `app/repositories/game_flaws_repository.py::flaw_record_to_row` lines **109–110**:
```python
"is_while_ahead": "while-ahead" in tags,
"is_result_changing": "result-changing" in tags,
```
These two lines become `"is_reversed": "reversed" in tags` / `"is_squandered": "squandered" in tags` (D-01).

**Dead-code map after the outcome-independent rebuild** — every call site that passes `user_result` *into impact*:
- `_is_result_changing(es_before, es_after, user_result)` (L396) — the whole function dies; impact no longer reads the result.
- `_build_tags(..., user_result, ...)` (L437, called L452) — `user_result` is **still needed** by `_is_unpunished` (L458, lucky-escape end-of-game rule at L390). Do **NOT** drop the `user_result` param from `_build_tags`; only the impact branch stops using it.
- `classify_game_flaws` (L532) still derives `user_result` for lucky-escape. **Keep it.**
- `library_service.py::_build_opponent_flaw_tags` (L211–230) flips `user_result` to the opponent's perspective specifically "so while-ahead / result-changing are mover-relative" (docstring L213). After the rebuild, impact no longer depends on `user_result`, so the impact tags become identical regardless of perspective — but the function must still flip for `_is_unpunished`. Update the **docstring** (L213) and verify `_USER_FRAMED_TAGS` (L69 — `{"miss", "lucky-escape"}`) does not need to gain the impact tags (it should NOT; impact is mover-framed and fine for opponent dots).

**New constants required (per `flaw-tag-definitions.md` §Threshold reference + D-01/CONTEXT §3):**
- Keep `FROM_WINNING_ES = 0.85` (now `squandered` entry).
- Add `WINNING_LINE_ES = 0.70` (`reversed` entry — repurposes old `RESULT_WIN_THRESHOLD` value).
- Add `LOSING_LINE_ES = 0.30` (`reversed` exit — new).
- Add `SQUANDERED_EXIT_ES = 0.60` (`squandered` exit — new).
- Remove `RESULT_WIN_THRESHOLD` (0.70) and `RESULT_DRAW_THRESHOLD` (0.40).

**New impact ladder (from `flaw-tag-definitions.md` L84–85, most-severe-wins, at most one):**
- `reversed`: `es_before >= WINNING_LINE_ES (0.70)` AND `es_after <= LOSING_LINE_ES (0.30)`.
- `squandered`: `es_before >= FROM_WINNING_ES (0.85)` AND `es_after <= SQUANDERED_EXIT_ES (0.60)`, **only when not `reversed`**.
- `_build_tags` appends at most one (Claude's-discretion: a single `_classify_impact(es_before, es_after) -> Literal["reversed","squandered"] | None` helper replacing `_is_result_changing`; no `user_result` arg).

> ⚠ Boundary convention note: the doc says reversed exit is "30% or below" (`<=`) and squandered exit "60% or below" (`<=`), whereas the **old** `_is_result_changing` used strict `<` on the exit. The new ladder is **inclusive** on the exit (`<=`) per the doc prose ("dropped to 30% or below"). The entry is `>=` (inclusive) in both old and new. The planner must spec `>=` entry / `<=` exit and the boundary tests must pin this (see Tests §).

### 2. DB model + migration — `app/models/game_flaw.py`, alembic

| CONTEXT claim | Reality | Status |
|---------------|---------|--------|
| Impact columns "lines 54–55" | `is_while_ahead` at **L54**, `is_result_changing` at **L55**, both `Boolean, nullable=False`, **no `server_default`** | **CONFIRMED** |
| `is_miss`/`is_lucky_escape` | **L50–51**, `Boolean, nullable=False`, **no `server_default`** | **CONFIRMED** |
| `es_before`/`es_after` "59–60" | **L59–60**, `Float, nullable=False` | **CONFIRMED** |
| `tempo` SmallInteger | **L44**, `SmallInteger, nullable=True` (`0=low-clock,1=impatient,2=considered`) | **CONFIRMED** |
| Alembic head + `20260606` create revision | Head **IS** `a7e0b4796501` (file `20260606_151439_a7e0b4796501_add_game_flaws_table.py`), `down_revision = "f4d88c3659c6"`. Verified no migration has `a7e0b4796501` as down_revision | **CONFIRMED** |

**New migration's `down_revision` MUST be `"a7e0b4796501"`.**

**Critical model detail:** the `is_miss`/`is_lucky_escape`/`is_while_ahead`/`is_result_changing` columns carry **no `server_default` in the ORM model**, yet the create migration (`20260606…` L49–52) also created them with **no server_default**. The only column in `game_flaws` with a server_default is `fen` (`server_default=""`, create migration L56). So D-01's "drop the server_default afterward to match `is_miss`/`is_lucky_escape`" is correct: the standard add-NOT-NULL pattern adds `server_default=sa.text("false")` so existing rows get a value, then **drops** the server_default so the new columns match the existing impact-column convention (model has none).

**Precedent migration for the add-NOT-NULL pattern:** `alembic/versions/20260422_014425_24baa961e5cf_add_users_beta_enabled.py`:
```python
op.add_column(
    "users",
    sa.Column("beta_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
)
```
That precedent does NOT drop the server_default afterward — for Phase 110 the planner should add the drop to match the no-server_default convention of the sibling impact columns (D-01 planner discretion). Pattern:
```python
def upgrade() -> None:
    op.drop_column("game_flaws", "is_while_ahead")
    op.drop_column("game_flaws", "is_result_changing")
    op.add_column("game_flaws", sa.Column("is_reversed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("game_flaws", sa.Column("is_squandered", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    # Drop server_default so new cols match sibling no-default convention (D-01).
    op.alter_column("game_flaws", "is_reversed", server_default=None)
    op.alter_column("game_flaws", "is_squandered", server_default=None)

def downgrade() -> None:
    op.drop_column("game_flaws", "is_squandered")
    op.drop_column("game_flaws", "is_reversed")
    op.add_column("game_flaws", sa.Column("is_result_changing", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("game_flaws", sa.Column("is_while_ahead", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.alter_column("game_flaws", "is_result_changing", server_default=None)
    op.alter_column("game_flaws", "is_while_ahead", server_default=None)
```
Literal column types only (project rule, stated in the create migration header L26–27) — do not import live app constants.

**Migration upgrades dev DB without reset (success gate):** the conftest test-template auto-refreshes when the live Alembic head differs from the template's stored `alembic_version` (CLAUDE.md §Test isolation), so `pytest` after adding the migration self-heals. For the dev DB itself, `uv run alembic upgrade head` applies the alter forward. **No `bin/reset_db.sh`** — confirmed safe because the alter is a forward op on an existing table (no create-migration edit).

### 3. API schemas + repos/services — exhaustive grep hit list (the grep-clean gate)

> Success criterion #1: after the phase, **zero** matches for `while-ahead`/`while_ahead`/`is_while_ahead`, `result-changing`/`result_changing`/`is_result_changing`, `impatient`, `considered` in `app/` and `frontend/src/`.

**`while_ahead` / `is_while_ahead` / `while-ahead` (rename → `reversed` family OR drop):**
| File:Line | Context |
|-----------|---------|
| `app/schemas/library.py:201,213` | `while_ahead_rate` docstring + field — **drop** (D-03), add `reversed_rate`/`squandered_rate` |
| `app/repositories/game_flaws_repository.py:109` | `"is_while_ahead": "while-ahead" in tags` — writer, → `is_reversed` |
| `app/repositories/library_repository.py:111,112,115,116,164,181,182,395,430,448` | EXISTS impact-family clause + `_reconstruct_tags` + 12-tuple aggregate + comments |
| `app/services/flaws_service.py:54,79,443,450` | constant comment, Literal, `_build_tags` docstring + append |
| `app/routers/library.py:42` | `FlawTagFilter` Literal member |
| `app/models/game_flaw.py:54` | column |
| `app/services/library_service.py:213,240,252,263,264,505,522,537,592` | opponent-flag docstring, `_CHIP_ORDER`, `_curate_chips_from_rows`, `_build_tag_distribution` |

**`result_changing` / `is_result_changing` / `result-changing` (rename → split into `reversed`/`squandered` OR drop):**
| File:Line | Context |
|-----------|---------|
| `app/schemas/library.py:193,206,210` | `result_changing_rate` docstring + field + comment — **drop** (D-03) |
| `app/repositories/library_repository.py:111,112,117,118,164,183,184,395,427,445` | EXISTS clause + `_reconstruct_tags` + 12-tuple |
| `app/repositories/query_utils.py:51` | docstring example `["low-clock", "result-changing"]` — **comment only**, update |
| `app/repositories/game_flaws_repository.py:110` | writer, → `is_squandered` |
| `app/routers/library.py:43,119` | Literal member + docstring |
| `app/models/game_flaw.py:55` | column |
| `app/services/flaws_service.py:80,396,443,452,453` | Literal, `_is_result_changing` def, `_build_tags` |
| `app/services/library_service.py:213,241,252,265,266,502,519,529,589,673,713` | docstring, `_CHIP_ORDER`, distribution builder, 12-tuple consumer |

**`impatient` (rename → `hasty`):**
| File:Line | Context |
|-----------|---------|
| `app/services/flaws_service.py:82,88,305,309,312,330` | Literal, `TempoTag`, `_classify_tempo` return + docstring |
| `app/repositories/game_flaws_repository.py:29,30` | `_TEMPO_INT` map key + comment (key string → `"hasty"`, int code 1 unchanged) |
| `app/repositories/library_repository.py:96,97,394,425,443` | tempo OR-family + 12-tuple |
| `app/routers/library.py:45` | `FlawTagFilter` Literal member |
| `app/models/game_flaw.py:43` | tempo code comment |
| `app/services/library_service.py:243,472,500,526,587,671,711` | `_CHIP_ORDER`, `_TEMPO_TAGS`, distribution builder |

**`considered` (rename → `unrushed`) — ⚠ FALSE POSITIVES, do NOT touch these:**
- `app/services/position_classifier.py:70` — prose ("position is considered backrank sparse")
- `app/services/stats_service.py:43` — prose ("to be considered")
- `frontend/src/lib/primaryTc.ts:7` — prose
- `frontend/src/components/library/EvalChart.tsx:12` — prose ("previously considered")
- `frontend/src/components/filters/FilterPanel.tsx:76` — prose ("considered part of")

**Real `considered` tag refs (rename → `unrushed`):** same files as `impatient` above, plus `app/repositories/library_repository.py:426` and the `frontend` files in §4.

**Theme color constants that embed the old tempo names (rename):**
- `frontend/src/lib/theme.ts:48` `FAM_TEMPO_IMPATIENT` → `FAM_TEMPO_HASTY`
- `frontend/src/lib/theme.ts:49` `FAM_TEMPO_CONSIDERED` → `FAM_TEMPO_UNRUSHED`
- Consumers: `frontend/src/components/library/FlawTagDistribution.tsx:94,95` (`FAM_TEMPO_IMPATIENT`/`FAM_TEMPO_CONSIDERED`).

### 4. Frontend — current state vs CONTEXT

| CONTEXT claim | Reality | Status |
|---------------|---------|--------|
| `types/library.ts` `FlawTag`/`TempoTag` "~14–30" | `FlawTag` union **L14–24** (`'impatient'` L16, `'considered'` L17, `'while-ahead'` L20, `'result-changing'` L21); `TempoTag` **L30** | **CONFIRMED** |
| `TagDistribution` rate fields "~136–149" | **L142–150**: `result_changing_rate` L144, `while_ahead_rate` L149. Swap both → `reversed_rate`/`squandered_rate` (D-03) | **CONFIRMED** |
| `tagDefinitions.ts` rebuild | Currently has **only** `TAG_LABELS` (title-cased, L17–28). `TAG_DEFINITIONS` was **removed in Phase 108** (file header L4–6 says so). Restore `TAG_DEFINITIONS` (D-07) | **CONFIRMED** |
| `TagChip.tsx` is a navigate trigger | **CONFIRMED** — L1 `useNavigate`, L90/L102 `navigate('/library/flaws?tag=...')`, `<button onClick>`. Revert target = `git show 8c5ebc81:frontend/src/components/library/TagChip.tsx` (Radix Popover, `<span role="button">`, hover/tap) | **CONFIRMED** |
| `FlawStatsBand` drop impact stat | **L57–139**: takes `result_changing_rate` prop (L61, L83), renders "Result-changing" cell (L124–136, `data-testid="stat-cell-result-changing"`). Remove prop + cell (D-02) | **CONFIRMED** |
| `FlawTagDistribution` swap impact | **L178** destructures `while_ahead_rate`/`result_changing_rate`; **L233–236** renders "While-ahead"/"Result-changing" RateBarRows. Swap to `reversed_rate`/`squandered_rate` (D-03) | **CONFIRMED** |
| `FlawFilterControl`, `FlawStatsPanel` | `FlawFilterControl.tsx:31` `IMPACT_TAGS = ['result-changing', 'while-ahead']` + icons L39–40; `FlawStatsPanel.tsx:181` passes `result_changing_rate` to band (remove, D-02), L193–194 passes `tag_distribution` to distribution | **CONFIRMED** |
| `theme.ts` ring constant | Not present yet — add new constant (D-05 discretion). `FAM_*` family colors confirmed L45–54 | **CONFIRMED (to add)** |
| `useFlawFilterStore` path | **DRIFT:** lives at `frontend/src/hooks/useFlawFilterStore.ts`, **not** `frontend/src/store/`. State shape: `{ severity: ('blunder'|'mistake')[], tags: FlawTag[] }` (L6–11). Active-filter match source = `state.tags` array. Selector: `const [flawFilter] = useFlawFilterStore()` then `flawFilter.tags.includes(tag)` | **DRIFT (path)** |

**TagChip call sites (D-05 "both surfaces"):**
- Games cards: `frontend/src/components/results/LibraryGameCard.tsx:317` (`<TagChip tag={tag} gameId={game.game_id} />`).
- Flaws cards: `frontend/src/pages/library/FlawsTab.tsx:117` (`<TagChip tag={tag} gameId={flaw.game_id} />`).
- Both must show the active-filter ring. `LibraryGameCard` does NOT currently subscribe to `useFlawFilterStore` — TagChip itself should subscribe (cleanest: TagChip reads the store internally and rings on `flawFilter.tags.includes(tag)`), avoiding prop drilling through both call sites. `FlawsTab` already imports the store (L23).

### 5. Phase 107 TagChip popover — concrete restore ref

- **Pre-108 commit:** `8c5ebc81` ("feat(107): Games subtab frontend…"). Phase 108 commit `d810e599` swapped to navigation.
- **Restore command:** `git show 8c5ebc81:frontend/src/components/library/TagChip.tsx` (full content captured below in Code Examples).
- **Popover body shape (107):** Radix `PopoverPrimitive.Root/Trigger/Portal/Content`, `side="top"`, `sideOffset={4}`, body `<span className="font-bold">{TAG_LABELS[tag]}</span>: {TAG_DEFINITIONS[tag]}`, content classes include `text-xs text-background bg-foreground` + Radix open/close animations. Trigger is `<span role="button" tabIndex={0}>` with hover (100ms timeout) on desktop and tap-toggle on mobile.
- **⚠ Restore is NOT a clean checkout.** The 107 chip:
  1. Imported `{ TAG_DEFINITIONS, TAG_LABELS } from '@/lib/tagDefinitions'` — `TAG_DEFINITIONS` must be rebuilt (D-07).
  2. The 107 popover copy used `TAG_LABELS[tag]` (title-cased "While ahead") for the bold heading. **D-07 + CONTEXT §specifics require the bold heading to be the canonical `lowercase-with-dash` tag string** (e.g. **`reversed`**), not the title-cased label. So the restored body becomes `<span className="font-bold">{tag}</span>: {TAG_DEFINITIONS[tag]}`.
  3. 107 `tagDefinitions.ts` imported thresholds from `@/lib/flawThresholds` (hand-written, now deleted) — repoint to the D-04 generated module.
  4. D-06 says the chip becomes the popover trigger again — but the **active-filter ring** (D-05) is new, layered on top of the restored chip.

### 6. Generator precedent — `scripts/gen_endgame_zones_ts.py`

- **Structure (CONFIRMED):** module imports authoritative Python constants (L30–41), `_format_*` helpers build literal strings, `_render()` returns the full TS source as one string (L178–314), `main()` (L317–337) supports `--check` (drift, exits 1) and write mode. Output: `frontend/src/generated/endgameZones.ts` (L43). Header comment: `// AUTO-GENERATED — do not edit by hand.` (L187).
- **CI drift gate location (CONFIRMED):** `.github/workflows/ci.yml:49–52`:
  ```yaml
  - name: Zone drift check
    run: |
      uv run python scripts/gen_endgame_zones_ts.py
      git diff --exit-code frontend/src/generated/endgameZones.ts
  ```
  No Makefile / pre-commit gate (none found) — **CI yaml is the only drift gate.**
- **Action for D-04:** add `gen_flaw_thresholds_ts.py` mirroring this (import `WINNING_LINE_ES`, `LOSING_LINE_ES`, `FROM_WINNING_ES`, `SQUANDERED_EXIT_ES`, plus the tempo constants the popover copy needs: `TIME_PRESSURE_CLOCK_FRACTION`, `TIME_PRESSURE_CLOCK_ABS_SECONDS`, `HASTY_MOVE_FRACTION`, `HASTY_MOVE_ABS_SECONDS`), output to `frontend/src/generated/flawThresholds.ts`. **Add a second `git diff --exit-code` line (or a new CI step) for the new generated file** — the existing step only checks `endgameZones.ts`. Do NOT edit `gen_endgame_zones_ts.py` (D-04).

### 7. Backfill — `scripts/backfill_flaws.py`

- **CONFIRMED:** `--db {dev|benchmark|prod}` (required, L68–73), `--user-id` (L74–80), `--dry-run` (L81–86), `--limit` (L87–92). Routes through `classify_game_flaws` (L184) + `delete_flaws_for_game` + `flaw_record_to_row` + `bulk_insert_game_flaws` (L218–227), delete-then-insert idempotent recompute (L216–217), batched 100/commit (L56).
- **Exact invocation for users 28 & 44 (dev):**
  ```bash
  uv run python scripts/backfill_flaws.py --db dev --user-id 28
  uv run python scripts/backfill_flaws.py --db dev --user-id 44
  ```
  (Optionally `--dry-run` first to count.) Requires dev DB up: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`, and the migration applied (`uv run alembic upgrade head`).

### 8. Tests — files to update + where to add boundary tests

**Backend tests asserting deprecated names (must update):**
- `tests/services/test_flaws_service.py` — `TestAttributionTags` (class at L750, docstring L751 names "while-ahead, result-changing"). `test_while_ahead_tag_when_es_before_above_threshold` (L762), `test_no_while_ahead_tag…` (L776), `test_result_changing_on_loss_crossing_draw_threshold` (L963), `test_no_result_changing_when_does_not_cross_boundary` (L981) — **rewrite as `reversed`/`squandered` ladder tests.** `TestConstants` (L102) asserts `FROM_WINNING_ES == 0.85` (L127–129) — keep, add asserts for `WINNING_LINE_ES`/`LOSING_LINE_ES`/`SQUANDERED_EXIT_ES`, remove `RESULT_WIN_THRESHOLD`/`RESULT_DRAW_THRESHOLD` import (L18). `TestTempoTags` (L627), `test_impatient_when_fast_move…` (L637) — rename to `hasty`.
- `tests/test_library_repository.py`, `tests/test_flaws_materialization.py`, `tests/test_library_router.py`, `tests/test_flaw_predicate.py`, `tests/test_game_flaws_model.py`, `tests/services/test_library_service.py`, `tests/services/test_eval_chart_service.py`, `tests/test_backfill_flaws.py` — all reference deprecated names (grep confirmed). Update column/tag assertions.

**Frontend tests asserting deprecated names (must update):**
- `frontend/src/components/library/__tests__/TagChip.test.tsx` — **largest rewrite.** Currently asserts navigation (`mockNavigate` L77/L79/L54, `chip-while-ahead-12` L75–79, aria `Filter flaws by tag:` L99). After D-06 revert: assert popover open on hover/tap + body text; after D-05: assert ring class on active-filter match.
- `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx` — `filter-flaw-tag-while-ahead`/`-result-changing`/`-impatient`/`-considered` testids (L81–86, L112–127).
- `frontend/src/pages/library/__tests__/FlawsTab.test.tsx`, `GamesTab.test.tsx`, `frontend/src/api/__tests__/client.test.ts` — `?tag=result-changing` deep-link + tag arrays.

**Where to add NEW classifier boundary tests (success criterion #2):** in `tests/services/test_flaws_service.py`, a new `TestImpactLadder` class (or extend `TestAttributionTags`). Required cases (boundary convention `>=` entry / `<=` exit):
- `reversed`: `es_before=0.70, es_after=0.30` → `reversed` (both boundaries inclusive). `es_before=0.69` → no `reversed`. `es_after=0.31` → no `reversed`.
- `squandered`: `es_before=0.85, es_after=0.60` → `squandered`. Exclusion: `es_before=0.90, es_after=0.25` → `reversed` only (most-severe wins, `squandered` suppressed).
- **No-impact gap (deliberate):** `es_before=0.78, es_after=0.45` → **no impact tag** (the doc's named example, L80 of `flaw-tag-definitions.md`). This is the key gap test — 78% is below the 85% squandered entry and the 45% exit is above the 30% reversed exit, and 78% is above 70% reversed entry but exit 45% > 30%, so neither fires.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Threshold values in TS popover copy | Hand-typed `flawThresholds.ts` | `gen_flaw_thresholds_ts.py` generated module (D-04) | The 107 hand-written file drifted and was deleted; CI drift gate enforces parity |
| Popover component | Custom tooltip | Restore Radix `PopoverPrimitive` from `8c5ebc81` | Already built, accessible, animated; D-06 says restore not rebuild |
| FlawRecord→column mapping | New writer | Existing `flaw_record_to_row` (single D-10 path) | All write paths share it; touch two lines (109–110) |
| Filter store | New store/Zustand | Existing `useFlawFilterStore` (`useSyncExternalStore`) | Already the active-filter source of truth |
| Migration boilerplate | From scratch | Copy `24baa961e5cf` add-NOT-NULL pattern | Established repo precedent |

---

## Common Pitfalls

### Pitfall 1: Treating `classify_game_flaws` as the column writer
**What goes wrong:** Editing only `flaws_service.py` and expecting `game_flaws` columns to change. **Avoid:** also edit `game_flaws_repository.py:109–110` (the actual writer) and the migration. Three coordinated edits.

### Pitfall 2: Dropping `user_result` from `_build_tags` / `classify_game_flaws`
**What goes wrong:** The impact rebuild makes `user_result` unused *for impact*, tempting removal. But `_is_unpunished` (lucky-escape) still needs it (end-of-game rule). **Avoid:** keep the param threaded; only delete `_is_result_changing`.

### Pitfall 3: `considered` false positives in grep-clean
**What goes wrong:** Blindly sed-replacing `considered` corrupts unrelated prose in `position_classifier.py`, `stats_service.py`, `primaryTc.ts`, `EvalChart.tsx`, `FilterPanel.tsx`. **Avoid:** rename only the tag-literal occurrences (the files listed under `impatient` in §3); the grep-clean gate must scope to tag contexts, not raw word.

### Pitfall 4: Boundary direction mismatch (exit inclusive vs strict)
**What goes wrong:** Reusing the old `_is_result_changing` strict-`<` exit logic. The new doc says "30% or below" / "60% or below" = `<=`. **Avoid:** spec `>=` entry, `<=` exit; pin in boundary tests.

### Pitfall 5: Forgetting the second CI drift gate
**What goes wrong:** Adding `gen_flaw_thresholds_ts.py` but not wiring its `git diff --exit-code` into `ci.yml`. The generated file then silently drifts. **Avoid:** add a new line/step in `.github/workflows/ci.yml` for `frontend/src/generated/flawThresholds.ts` (the existing step at L49–52 only covers `endgameZones.ts`).

### Pitfall 6: Editing the `20260606` create migration
**What goes wrong:** Forces a dev-DB reset (checksum mismatch on an already-applied migration). **Avoid:** forward alter migration only (D-01, explicit).

### Pitfall 7: Restored popover bold heading uses title-case
**What goes wrong:** Clean checkout of 107 chip uses `TAG_LABELS[tag]` ("While ahead") in the bold heading. CONTEXT §specifics requires the canonical `lowercase-with-dash` tag string. **Avoid:** bold heading = `{tag}` literal, not `TAG_LABELS[tag]`.

---

## Code Examples

### Phase 107 TagChip restore target (`git show 8c5ebc81:frontend/src/components/library/TagChip.tsx`)
Key structure to restore (adapt per Pitfall 7 + add D-05 ring):
```tsx
// Source: commit 8c5ebc81 (Phase 107)
import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
// ...icons + FAM_* theme imports + TAG_DEFINITIONS from tagDefinitions...
export function TagChip({ tag, gameId }: TagChipProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleMouseEnter = () => { hoverTimeout.current = setTimeout(() => setOpen(true), 100); };
  const handleMouseLeave = () => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); setOpen(false); };
  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span role="button" tabIndex={0}
          aria-label={`Tag: ${tag} — ${TAG_DEFINITIONS[tag]}`}
          data-testid={`chip-${tag}-${gameId}`}
          onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}
          /* + D-05 ring class when flawFilter.tags.includes(tag) */ >
          <Icon className="h-3 w-3 shrink-0" />{tag}
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content side="top" sideOffset={4}
          data-testid={`tag-popover-${tag}-${gameId}`}
          className="z-50 max-w-xs rounded-md bg-foreground px-3 py-1.5 text-xs text-background /* +animations */">
          <span className="font-bold">{tag}</span>: {TAG_DEFINITIONS[tag]}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
```

### New impact classifier (replacing `_is_result_changing`)
```python
# app/services/flaws_service.py — outcome-independent, no user_result arg
def _classify_impact(es_before: float, es_after: float) -> Literal["reversed", "squandered"] | None:
    """Most-severe-wins impact ladder (flaw-tag-definitions.md). At most one tag."""
    if es_before >= WINNING_LINE_ES and es_after <= LOSING_LINE_ES:
        return "reversed"
    if es_before >= FROM_WINNING_ES and es_after <= SQUANDERED_EXIT_ES:
        return "squandered"
    return None
```

---

## State of the Art

| Old (current code) | New (this phase) | Source |
|--------------------|------------------|--------|
| `while-ahead` impact tag (state, ≥85% entry only) | removed | `flaw-tag-definitions.md` §Deprecated L107 |
| `result-changing` (outcome-dependent, reads game result) | split into `reversed` (70→30) + `squandered` (85→60), outcome-independent | ibid L108, L84–85 |
| `impatient` / `considered` tempo | `hasty` / `unrushed` | ibid L105–106 |
| Hand-written `frontend/src/lib/flawThresholds.ts` | Generated `frontend/src/generated/flawThresholds.ts` (D-04) | CONTEXT D-04 |
| `TagChip` navigates to `/library/flaws?tag=` | `TagChip` Radix popover (restored) | CONTEXT D-06 |

**Stale doc warning (already flagged in CONTEXT):** both `flaw-tag-definitions.md` (L146–147) and `flaw-tag-naming.md` (L54–57) claim "no DB migration — tags computed on the fly." That is **STALE** — Phase 108 materialized tags into `game_flaws`. There **IS** a migration this phase (D-01). Follow CONTEXT/ROADMAP, not the notes' "no migration" lines.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | Boundary convention is `>=` entry / `<=` exit (inclusive exit) | §1 Pitfall 4 | If the planner intends strict `<` exit (matching old code), the 30%/60% boundary tests flip. Doc prose ("or below") supports `<=`; confirm in plan. |

**All other claims are VERIFIED against current source.**

## Open Questions

1. **Generated TS module filename/path for D-04.** The 107 hand-written file was `frontend/src/lib/flawThresholds.ts`; the generator precedent writes to `frontend/src/generated/`. Recommendation: `frontend/src/generated/flawThresholds.ts` (matches the generated-dir convention; the old `@/lib/flawThresholds` import path is free since the file was deleted). Planner to confirm exact name so `tagDefinitions.ts` imports correctly.
2. **`TAG_LABELS` retention (D-07 discretion).** `FlawFilterControl.tsx` does NOT currently use `TAG_LABELS` (it renders icons + raw tag strings via its own `TAG_ICONS`/`*_TAGS` arrays). So `TAG_LABELS` has **no remaining consumer** once chips/panel use the literal tag string — knip (CI) will flag it as dead. Recommendation: **remove `TAG_LABELS` entirely** unless the planner finds a genuine non-chip human-label surface. (Verify with `npm run knip` after the change.)

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (Docker) | migration + backfill | assume ✓ (CLAUDE.md) | PG 18 | start via compose |
| `uv` / Python 3.13 | classifier, migration, generator, backfill | ✓ | 3.13 | — |
| Node/npm + Vite | frontend build/test/knip | ✓ | Vite 7 | — |
| Users 28 & 44 with analyzed games in dev DB | backfill repopulate | unverified | — | If a user has no analyzed games, backfill writes 0 rows (not an error) — verify with `--dry-run` first |

**No external network dependencies. No new packages.**

## Validation Architecture

> nyquist_validation: included (config key not explicitly false).

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (per-run-DB isolation, xdist) |
| Backend quick run | `uv run pytest tests/services/test_flaws_service.py -x` |
| Backend full suite | `uv run pytest -n auto` |
| Frontend framework | vitest (`npm test`) |
| Frontend run | `(cd frontend && npm test -- --run)` |
| Generator drift | `uv run python scripts/gen_flaw_thresholds_ts.py --check` |

### Phase Requirements → Test Map
| Behavior | Test type | Command | Exists? |
|----------|-----------|---------|---------|
| `reversed` ladder boundary (70/30) | unit | `pytest tests/services/test_flaws_service.py::TestImpactLadder -x` | ❌ Wave 0 (new class) |
| `squandered` ladder boundary (85/60) | unit | same | ❌ Wave 0 |
| No-impact gap (78→45) | unit | same | ❌ Wave 0 |
| `hasty`/`unrushed` rename | unit | `pytest tests/services/test_flaws_service.py::TestTempoTags -x` | ✅ (update L637) |
| `is_reversed`/`is_squandered` column write | integration | `pytest tests/test_flaws_materialization.py -x` | ✅ (update) |
| Migration upgrades dev DB | implicit | conftest template auto-refresh on `pytest` | ✅ |
| TagChip popover restore + ring | unit | `frontend …/__tests__/TagChip.test.tsx` | ✅ (rewrite) |
| Grep-clean gate | manual/CI | `grep -rn 'while-ahead\|result-changing\|impatient\|<tag>considered' app/ frontend/src` → scoped to tag contexts | ❌ Wave 0 (add to plan verification) |

### Wave 0 Gaps
- [ ] New `TestImpactLadder` class in `tests/services/test_flaws_service.py` (70/30, 85/60, 78→45 gap, most-severe-wins).
- [ ] `scripts/gen_flaw_thresholds_ts.py` + generated file + CI drift step.
- [ ] Grep-clean verification step (scoped, excluding the 5 false-positive prose lines).

### Sampling Rate
- Per task: `uv run pytest tests/services/test_flaws_service.py -x` (or the touched test file).
- Per wave merge: `uv run pytest -n auto` + `(cd frontend && npm run lint && npm test -- --run)` + both `gen_*_ts.py --check`.
- Phase gate: full suite green + grep-clean + `ty check` zero errors + `npm run knip` clean.

## Security Domain

Not applicable in the traditional sense — no new endpoints, auth, input parsing, or crypto. The only security-adjacent surface is the existing user-scoping on `game_flaws` reads/writes (EXISTS predicates carry `user_id`, delete scoped to `(game_id, user_id)`), which this phase preserves unchanged. ASVS V5 (input validation) is already covered by the `FlawTagFilter` Literal at the HTTP boundary (`routers/library.py:39`) — when renaming Literal members, the FastAPI 422-rejection of unknown tags continues to apply automatically.

## Sources

### Primary (HIGH — verified against current source on branch)
- `app/services/flaws_service.py` (full read)
- `app/models/game_flaw.py`, `app/repositories/game_flaws_repository.py` (full read)
- `app/repositories/library_repository.py`, `app/services/library_service.py`, `app/schemas/library.py`, `app/routers/library.py`, `app/repositories/query_utils.py` (targeted reads + grep)
- `alembic/versions/20260606_151439_a7e0b4796501_add_game_flaws_table.py`, `…20260422…24baa961e5cf_add_users_beta_enabled.py` (full read); head verified via down_revision grep
- `frontend/src/components/library/TagChip.tsx`, `tagDefinitions.ts`, `types/library.ts`, `FlawStatsBand.tsx`, `FlawTagDistribution.tsx`, `FlawFilterControl.tsx`, `theme.ts`, `hooks/useFlawFilterStore.ts` (reads + grep)
- `git show 8c5ebc81:…/TagChip.tsx`, `…/tagDefinitions.ts`, `…/flawThresholds.ts` (Phase 107 restore targets)
- `scripts/gen_endgame_zones_ts.py`, `scripts/backfill_flaws.py` (full read); `.github/workflows/ci.yml` (drift gate)
- `.planning/phases/110…/110-CONTEXT.md`, `.planning/notes/flaw-tag-definitions.md`, `.planning/notes/flaw-tag-naming.md`

## Metadata

**Confidence breakdown:**
- Verification of CONTEXT code map: HIGH — read every cited file, line numbers reconciled.
- Migration pattern: HIGH — precedent found, head confirmed.
- Frontend restore: HIGH — exact pre-108 commit + content retrieved; one adaptation flagged (Pitfall 7).
- Boundary convention: MEDIUM — A1 assumption (`<=` exit per doc prose; confirm in plan).

**Research date:** 2026-06-07
**Valid until:** stable until the branch advances — re-verify line numbers if `flaws_service.py` or `library_service.py` are edited before planning.
