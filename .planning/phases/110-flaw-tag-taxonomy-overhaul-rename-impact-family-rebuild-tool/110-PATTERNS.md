# Phase 110: Flaw-Tag Taxonomy Overhaul — Pattern Map

**Mapped:** 2026-06-07
**Files analyzed:** 3 new + ~22 modified (focus: the 3 new artifacts)
**Analogs found:** 3 / 3 new (all exact); modified files map to in-file precedent (their own sibling lines)

This phase is overwhelmingly **modification of existing files** (rename/swap churn with line numbers already pinned in 110-RESEARCH.md §3–§4). Pattern-mapping effort concentrates on the **three NEW artifacts** (alter migration, `gen_flaw_thresholds_ts.py`, generated `flawThresholds.ts`) plus the few **structural restore/edit sites** where the planner needs the concrete current code. For the mechanical renames, the research grep hit-list is the authoritative map — this file does not duplicate it.

---

## File Classification

### New files (need analog mapping — primary focus)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `alembic/versions/<new>_alter_game_flaws_impact_cols.py` | migration | transform (schema DDL) | `alembic/versions/20260422_014425_24baa961e5cf_add_users_beta_enabled.py` (add-NOT-NULL-with-server_default) + `20260606_151439_a7e0b4796501_add_game_flaws_table.py` (sibling create, literal-types convention) | role-match (no prior drop+add alter) |
| `scripts/gen_flaw_thresholds_ts.py` | script (codegen) | transform (Py→TS) | `scripts/gen_endgame_zones_ts.py` | exact |
| `frontend/src/generated/flawThresholds.ts` | config (generated) | transform output | `frontend/src/generated/endgameZones.ts` | exact |

### Modified files (edit-site → in-file precedent)

| Modified File | Role | Data Flow | Edit Nature | In-file precedent / line refs |
|---------------|------|-----------|-------------|------------------------------|
| `app/services/flaws_service.py` | service | transform | constants + Literals + new `_classify_impact` helper + `_build_tags` order | `_is_unpunished` (L390), existing `FROM_WINNING_ES` (L54); research §1 |
| `app/repositories/game_flaws_repository.py` | repository | CRUD (write path) | 2-line string→column map swap (L109–110) | sibling `is_miss`/`is_lucky_escape` (L107–108) |
| `app/models/game_flaw.py` | model | — | rename 2 boolean columns (L54–55) | sibling `is_miss`/`is_lucky_escape` (L50–51, no server_default) |
| `app/schemas/library.py` | schema | request-response | swap 2 rate fields (L193–213) | sibling `miss_rate`/`lucky_escape_rate` fields |
| `app/repositories/library_repository.py` | repository | CRUD (read/aggregate) | EXISTS clause + `_reconstruct_tags` + 12-tuple | research §3 line list |
| `app/services/library_service.py` | service | transform | `_CHIP_ORDER`, distribution builder, opponent flip | research §3 + §1 (docstring L213) |
| `app/routers/library.py` | router | request-response | `FlawTagFilter` Literal members (L42,43,45) | sibling Literal members |
| `app/repositories/query_utils.py` | utility | — | docstring example only (L51) | comment-only |
| `frontend/src/components/library/TagChip.tsx` | component | event-driven | **revert nav → restore Radix Popover** + add ring | commit `8c5ebc81` (Phase 107) |
| `frontend/src/lib/tagDefinitions.ts` | utility | — | **rebuild `TAG_DEFINITIONS`** map | commit `8c5ebc81` version (adapt imports) |
| `frontend/src/lib/theme.ts` | config | — | **add** active-filter ring constant; rename 2 `FAM_TEMPO_*` (L48,49) | sibling `FAM_*` family colors (L45–54) |
| `frontend/src/hooks/useFlawFilterStore.ts` | hook (store) | — | read-only — selector source for ring match | state shape L6–11 |
| `frontend/src/types/library.ts` | model (types) | — | `FlawTag`/`TempoTag` unions + rate fields | research §4 |
| `frontend/src/components/library/FlawStatsBand.tsx` | component | — | drop impact prop + cell (D-02) | research §4 |
| `frontend/src/components/library/FlawTagDistribution.tsx` | component | — | swap impact RateBarRows + `FAM_*` (D-03) | research §4 |
| `frontend/src/components/filters/FlawFilterControl.tsx` | component | — | `IMPACT_TAGS`/`*_TAGS` + testids | research §4 |
| `.github/workflows/ci.yml` | config (CI) | — | **add** 2nd drift-gate step | sibling Zone drift step (L49–52) |
| `tests/services/test_flaws_service.py` + 8 backend tests | test | — | rewrite/rename + new `TestImpactLadder` | research §8 |
| frontend `__tests__/TagChip.test.tsx` + 5 | test | — | rewrite nav→popover; rename testids | research §8 |

---

## Pattern Assignments (NEW artifacts — concrete code to copy)

### 1. `alembic/versions/<new>_alter_game_flaws_impact_cols.py` (migration, schema DDL)

**Analogs:** `24baa961e5cf` (add-NOT-NULL pattern) + `a7e0b4796501` (sibling `game_flaws` create, literal-types-only convention).

**`down_revision` MUST be `"a7e0b4796501"`** (the verified current head — no migration currently has it as down_revision; research §2).

**Add-NOT-NULL-with-server_default precedent** (`24baa961e5cf`):
```python
op.add_column(
    "users",
    sa.Column("beta_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
)
```
That precedent does **not** drop the server_default. For Phase 110, ADD the drop so the new columns match the sibling impact-column convention (`is_miss`/`is_lucky_escape` carry NO server_default in both the model and the create migration; research §2). Full skeleton (D-01, planner discretion confirmed):
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

**Hard rules (from `a7e0b4796501` header convention + project rules):**
- Literal `sa.*` column types only — do NOT import live app constants into the migration.
- Do NOT touch `is_miss` / `is_lucky_escape` / `tempo` / `es_before` / `es_after`.
- Do NOT edit the `20260606` create migration (forces a dev-DB reset — Pitfall 6).
- No `bin/reset_db.sh` gating: `uv run alembic upgrade head` applies forward on the existing dev DB; conftest template auto-refreshes for pytest.

---

### 2. `scripts/gen_flaw_thresholds_ts.py` (codegen script, Py→TS)

**Analog:** `scripts/gen_endgame_zones_ts.py` (exact structural mirror). Copy this skeleton 1:1 and substitute the flaw thresholds.

**Module docstring + sys.path bootstrap** (`gen_endgame_zones_ts.py` lines 1–28):
```python
"""Generate frontend/src/generated/flawThresholds.ts from flaws_service.py constants.
...
Usage (drift check — exits 1 if generated output differs from the committed file):
    uv run python scripts/gen_flaw_thresholds_ts.py --check
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
```

**Authoritative-constant import** (analog lines 30–41) — import the flaw thresholds the popover copy needs (research §6):
```python
from app.services.flaws_service import (  # noqa: E402
    WINNING_LINE_ES,       # reversed entry (0.70)
    LOSING_LINE_ES,        # reversed exit (0.30)
    FROM_WINNING_ES,       # squandered entry (0.85)
    SQUANDERED_EXIT_ES,    # squandered exit (0.60)
    # + tempo constants the popover interpolates:
    # TIME_PRESSURE_CLOCK_FRACTION, TIME_PRESSURE_CLOCK_ABS_SECONDS,
    # HASTY_MOVE_FRACTION, HASTY_MOVE_ABS_SECONDS  (confirm exact names in flaws_service.py)
)

_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "flawThresholds.ts"
```

**`_render()` returns the full TS source as one string** (analog lines 178–314) — the exact bytes emitted are what is committed; CI `git diff --exit-code` blocks drift. Header convention (analog lines 187–189):
```python
def _render() -> str:
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: app/services/flaws_service.py\n"
        "// Regenerate with: uv run python scripts/gen_flaw_thresholds_ts.py\n"
        "\n"
        f"export const WINNING_LINE_ES = {WINNING_LINE_ES};\n"
        f"export const LOSING_LINE_ES = {LOSING_LINE_ES};\n"
        f"export const FROM_WINNING_ES = {FROM_WINNING_ES};\n"
        f"export const SQUANDERED_EXIT_ES = {SQUANDERED_EXIT_ES};\n"
        # + tempo constants...
    )
```
NOTE the flat-scalar shape: unlike `endgameZones.ts` (registry objects with `_format_*` helpers), the flaw file is ~4–8 flat `export const` scalars, so no `_format_*` helpers are needed — just f-string interpolation in `_render()`. This shape difference is exactly why D-04 rejected merging the two generators.

**`main()` with `--check` drift mode** (analog lines 317–337) — copy verbatim, only the variable names change:
```python
def main() -> None:
    check_mode = "--check" in sys.argv
    content = _render()
    if check_mode:
        if not _OUTPUT.exists():
            print(f"DRIFT: {_OUTPUT.relative_to(_REPO_ROOT)} does not exist.", file=sys.stderr)
            sys.exit(1)
        existing = _OUTPUT.read_text(encoding="utf-8")
        if existing != content:
            print(f"DRIFT: ... Run `uv run python scripts/gen_flaw_thresholds_ts.py` ...", file=sys.stderr)
            sys.exit(1)
        print(f"OK: {_OUTPUT.relative_to(_REPO_ROOT)} is up to date.")
    else:
        _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        _OUTPUT.write_text(content, encoding="utf-8")
        print(f"Wrote {_OUTPUT.relative_to(_REPO_ROOT)}")

if __name__ == "__main__":
    main()
```

**Do NOT edit `gen_endgame_zones_ts.py`** (D-04). New file is independent.

---

### 3. `frontend/src/generated/flawThresholds.ts` (generated config)

**Analog:** `frontend/src/generated/endgameZones.ts`.

**Header block to mirror** (analog lines 1–3) — three-line AUTO-GENERATED banner, source path, regenerate command:
```ts
// AUTO-GENERATED — do not edit by hand.
// Source: app/services/flaws_service.py
// Regenerate with: uv run python scripts/gen_flaw_thresholds_ts.py
```

**Export shape** — flat scalar exports (analog lines 32–37 show the scalar pattern; flaw file is purely this, no `Record`/object literals):
```ts
export const WINNING_LINE_ES = 0.7;
export const LOSING_LINE_ES = 0.3;
export const FROM_WINNING_ES = 0.85;
export const SQUANDERED_EXIT_ES = 0.6;
// + tempo scalars
```

**Consumer:** `tagDefinitions.ts` imports from `@/generated/flawThresholds` (NOT the deleted `@/lib/flawThresholds`) and interpolates thresholds into definition prose — no hard-coded `70%`/`85%`/`60%`/`30%` (D-04/D-07). The endgameZones consumer-import pattern (`import { ... } from "@/lib/theme"` at analog L5) is the equivalent import-from-generated convention.

**Created by the generator, not by hand** — the planner must run `uv run python scripts/gen_flaw_thresholds_ts.py` to produce it, then commit. CI re-runs and diffs.

---

## Modified-file edit-site excerpts (structural, where the planner needs current code)

### `app/repositories/game_flaws_repository.py` — the REAL impact-column writer (L107–115)

This is the actual string→column write path (NOT `classify_game_flaws`, which only returns in-memory `FlawRecord` tags — research finding #1 / Pitfall 1). Current code:
```python
        "is_miss": "miss" in tags,
        "is_lucky_escape": "lucky-escape" in tags,
        "is_while_ahead": "while-ahead" in tags,          # L109 → "is_reversed": "reversed" in tags
        "is_result_changing": "result-changing" in tags,  # L110 → "is_squandered": "squandered" in tags
        "es_before": flaw["es_before"],
        "es_after": flaw["es_after"],
```
Only L109–110 change. The `is_miss`/`is_lucky_escape` lines above are the in-file precedent for the exact `"<tag>" in tags` idiom.

### `app/services/flaws_service.py` — new impact helper (replaces `_is_result_changing`)

`_is_result_changing` (L396–414, signature `(es_before, es_after, user_result)`) is fully deleted. Replace with an outcome-independent helper (no `user_result` arg — research §1 Code Examples):
```python
def _classify_impact(es_before: float, es_after: float) -> Literal["reversed", "squandered"] | None:
    """Most-severe-wins impact ladder (flaw-tag-definitions.md). At most one tag."""
    if es_before >= WINNING_LINE_ES and es_after <= LOSING_LINE_ES:
        return "reversed"
    if es_before >= FROM_WINNING_ES and es_after <= SQUANDERED_EXIT_ES:
        return "squandered"
    return None
```
**Boundary convention:** `>=` entry / `<=` exit (inclusive exit per doc prose "or below"; differs from old strict `<` — Pitfall 4 / Assumption A1). Pin in boundary tests.

**KEEP `user_result` threaded through `_build_tags` (L437) and `classify_game_flaws` (L532)** — `_is_unpunished` (lucky-escape, L390/L458) still needs it. Only the impact branch stops reading it (Pitfall 2).

### `frontend/src/components/library/TagChip.tsx` — restore target

**Restore from commit `8c5ebc81`** (Phase 107 Radix Popover), NOT a rebuild (D-06). Retrieve with:
```
git show 8c5ebc81:frontend/src/components/library/TagChip.tsx
```
**Restore is NOT a clean checkout** — 4 adaptations (research §5 / Pitfall 7):
1. `TAG_DEFINITIONS` must be rebuilt in `tagDefinitions.ts` (D-07).
2. Bold heading = `{tag}` (canonical lowercase-with-dash literal), NOT `TAG_LABELS[tag]` (title-case) — Pitfall 7.
3. `tagDefinitions.ts` thresholds import repoints `@/lib/flawThresholds` (deleted) → `@/generated/flawThresholds` (new D-04 module).
4. Layer the new D-05 active-filter ring on top of the restored chip.

107 structure to restore (research Code Examples): `PopoverPrimitive.Root/Trigger(asChild)/Portal/Content`, trigger is `<span role="button" tabIndex={0}>` with 100ms hover-open + tap-toggle, `side="top" sideOffset={4}`, body classes include `text-xs text-background bg-foreground` (popover `text-xs` is allowed per CLAUDE.md tooltip exception), body: `<span className="font-bold">{tag}</span>: {TAG_DEFINITIONS[tag]}`.

### `frontend/src/hooks/useFlawFilterStore.ts` — active-filter ring source (D-05)

Path is `hooks/`, NOT `store/` (research DRIFT §4). State shape `{ severity: ('blunder'|'mistake')[], tags: FlawTag[] }`. Selector for the ring match:
```ts
const [flawFilter] = useFlawFilterStore();
const isActive = flawFilter.tags.includes(tag);
```
**TagChip subscribes internally** (cleanest — avoids prop-drilling through both call sites: `LibraryGameCard.tsx:317` Games cards and `FlawsTab.tsx:117` Flaws cards). Ring applies on both surfaces, desktop + mobile.

### `frontend/src/lib/theme.ts` — ring constant + tempo renames

ADD a new active-filter ring constant (D-05 discretion: name/value/width/offset; `ring-2` + offset in family color). Sibling `FAM_*` family colors at L45–54 are the placement precedent. RENAME L48 `FAM_TEMPO_IMPATIENT` → `FAM_TEMPO_HASTY`, L49 `FAM_TEMPO_CONSIDERED` → `FAM_TEMPO_UNRUSHED` (consumers: `FlawTagDistribution.tsx:94,95`).

### `.github/workflows/ci.yml` — second drift gate (Pitfall 5)

Existing Zone drift step (L49–52):
```yaml
- name: Zone drift check
  run: |
    uv run python scripts/gen_endgame_zones_ts.py
    git diff --exit-code frontend/src/generated/endgameZones.ts
```
ADD a parallel step (new step OR a second 2-line block) for the flaw generator:
```yaml
- name: Flaw thresholds drift check
  run: |
    uv run python scripts/gen_flaw_thresholds_ts.py
    git diff --exit-code frontend/src/generated/flawThresholds.ts
```
The existing step only covers `endgameZones.ts` — without this, the new generated file silently drifts.

---

## Shared Patterns

### Python→TS codegen + CI drift gate
**Source:** `scripts/gen_endgame_zones_ts.py` (`--check` mode, `_render()` single-string emit, AUTO-GENERATED 3-line header) + `.github/workflows/ci.yml:49–52` (`git diff --exit-code`).
**Apply to:** `gen_flaw_thresholds_ts.py` + its CI step. Python constants are authoritative; TS is the drift-gated mirror. Local gate per CLAUDE.md runs both `gen_*_ts.py --check` at wave merge.

### Single classify kernel (one write path)
**Source:** `classify_game_flaws` (`flaws_service.py`, D-10) → `flaw_record_to_row` (`game_flaws_repository.py:100–115`) → `bulk_insert_game_flaws`.
**Apply to:** import hook, `reimport_games.py`, `reclassify_positions.py`, `backfill_flaws.py` all route through this kernel — updating the impact ladder + the 2 writer lines propagates everywhere. No second write path.

### Literal types at the HTTP + classifier boundary
**Source:** `routers/library.py` `FlawTagFilter` Literal (auto-422 on unknown tags); `flaws_service.py` `FlawTag`/`TempoTag` Literals.
**Apply to:** every renamed tag (`reversed`/`squandered`/`hasty`/`unrushed`) must update the Literal members in BOTH the service and the router; `frontend/src/types/library.ts` mirrors them. Grep-clean gate (success criterion #1) catches misses.

### theme.ts constants, mobile+desktop parity
**Source:** CLAUDE.md + sibling `FAM_*` colors (`theme.ts:45–54`).
**Apply to:** the active-filter ring color is a `theme.ts` constant, never inline (D-05). Both Games cards and Flaws cards, both layouts (CLAUDE.md mobile rule).

### Sibling no-server_default column convention
**Source:** `game_flaw.py:50–51` (`is_miss`/`is_lucky_escape`, no `server_default`) + create migration `a7e0b4796501`.
**Apply to:** the new `is_reversed`/`is_squandered` columns — model carries no `server_default`; the migration adds one transiently then drops it (D-01).

---

## No Analog Found

None. Every new file has an exact or strong precedent in the codebase:

| File | Reason it still maps |
|------|----------------------|
| Alter migration (drop+add) | No prior drop-then-add alter exists, but `24baa961e5cf` (add-NOT-NULL) + `a7e0b4796501` (sibling create) fully cover the two halves; research §2 supplies the verified skeleton. |

---

## Metadata

**Analog search scope:** `scripts/`, `alembic/versions/`, `frontend/src/generated/`, `frontend/src/components/library/`, `frontend/src/hooks/`, `frontend/src/lib/`, `app/services/`, `app/repositories/`, `app/models/`, `.github/workflows/`.
**Files scanned (direct reads this session):** `gen_endgame_zones_ts.py`, `endgameZones.ts` (head), `game_flaws_repository.py` (writer block). All other line refs verified in 110-RESEARCH.md (HIGH confidence, full reads on branch).
**Pattern extraction date:** 2026-06-07
