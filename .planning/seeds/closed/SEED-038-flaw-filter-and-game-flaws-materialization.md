---
id: SEED-038
status: dormant
planted: 2026-06-06
planted_during: /gsd-explore session on Games-tab tag ambiguity (Phase 107 in progress)
trigger_when: BEFORE planning the Flaws subtab phase (SEED-036 Phase 4 / "Flaws subtab frontend") — this seed locks the cross-tab Flaw-filter UX and the `game_flaws` materialization the Flaws tab and tag-combo filtering both depend on
scope: phase (filter UX + new derived table + backfill); feeds the Flaws-subtab phase under SEED-036
depends_on: SEED-036 (Library milestone — Flaws subtab, deep-link target, flaw classification service in app/services/flaws_service.py)
relates_to: SEED-036 (this seed refines its Flaws-tab design and adds the materialization layer it implies)
---

# SEED-038: Cross-tab Flaw filter + `game_flaws` materialization

> **Origin.** `/gsd-explore` on 2026-06-06. The Games-tab tag chips today aggregate tags across *all* a game's flaws (blunders + mistakes, ignoring inaccuracies), which is ambiguous: a game with 2 blunders tagged `low-clock, considered, result-changing` doesn't tell you whether the result-changing blunder happened under low clock, or whether those are two separate moves. This seed resolves that ambiguity and designs the storage layer that makes precise, paginable flaw filtering and tag-combination stats efficient.

## Problem

Game-level tag aggregation loses the flaw→tag association. You can't tell, from the card, which flaw carried which tag. SEED-036 already flagged this ("Games tab kept only a boolean severity filter to avoid cross-row-match ambiguity") and designed the Flaws tab as the precise, one-row-per-flaw surface. This seed makes the resolution concrete and unifies filtering across both tabs.

## Locked UX decisions (from the explore session)

1. **Games-card chips are teasers / doorways, not precise claims.** A chip means "this game contains a flaw of this kind, somewhere." Ambiguity is acceptable *by design* because the chip's job is discovery: clicking it deep-links into the Flaws tab (`/library/flaws?game_id={ID}&tag={TAG}`) where the precise per-flaw breakdown lives. We do **not** crowd the Games card with per-flaw tag groupings, and we do **not** remove chips.

2. **One shared "Flaw filter" control in the sidebar, surfaced in both the Games and Flaws tabs.** Same control, same predicate builder, both tabs. This is a dedicated flaw filter button (severity × tag families), distinct from the existing game-metadata FilterPanel.

3. **Single-flaw EXISTS semantics — the make-or-break decision.** The filter predicate is evaluated **per flaw**, identically in both tabs:
   - **Flaws tab:** show flaws that satisfy the entire combo.
   - **Games tab:** show games that contain **at least one flaw** satisfying the *entire* combo (`EXISTS`), NOT games that have flaw A with tag X and a *different* flaw B with tag Y. This eliminates the cross-row ambiguity completely. "result-changing + low-clock" always means *one move* that was both.
   - Rationale: the coarse any-flaw match is simpler to describe as "game-level tags" but reintroduces the exact ambiguity we're fixing. EXISTS keeps the chip-as-teaser model honest — clicking through lands on the flaw that actually matched.

4. **Family-aware boolean logic: OR within a tag family, AND across families.** Families: severity × tempo × opportunity × impact × phase. Tempo tags (`low-clock` / `impatient` / `considered`) are mutually exclusive *within a flaw*, so a combo like `low-clock + considered` is unsatisfiable by a single flaw — the UI/predicate must treat within-family selections as OR and across-family as AND.

## Materialization: `game_flaws` table

**Why a new table (not columns on `game_positions`).** A flaw maps to exactly one ply (the user's move) and flaws are a sparse subset (~5–15% of user moves) of `game_positions` rows. Adding flaw columns to the hot, largest table would be mostly-NULL bloat. A dedicated derived table stays tiny and keeps the positions table lean. Flaws are computed on-the-fly today in `app/services/flaws_service.py` (`classify_game_flaws`); this table materializes that output so the predicate can be pushed into SQL with pagination instead of recomputing every game's flaws per filtered query.

```python
class GameFlaw(Base):
    __tablename__ = "game_flaws"
    # composite PK mirrors game_positions; one flaw per (user, game, ply)
    user_id:  FK(users.id,  ondelete="CASCADE")   # PK
    game_id:  FK(games.id,  ondelete="CASCADE")   # PK
    ply:      SmallInteger                          # PK

    # severity — ordered SmallInteger so `severity >= MISTAKE` works
    severity: SmallInteger    # 1=mistake, 2=blunder  (see "inaccuracies" decision)

    # tag families as typed columns (NOT a bitmask, NOT TEXT[])
    tempo:    SmallInteger | None   # 0=low-clock, 1=impatient, 2=considered, NULL=no clock data
    phase:    SmallInteger          # 0/1/2 — denormalized from game_positions for query locality
    is_miss:             bool       # opportunity family
    is_lucky_escape:     bool       # opportunity family (blunders only)
    is_while_ahead:      bool       # impact family
    is_result_changing:  bool       # impact family

    # display / stats payload (avoids re-parsing PGN to render a Flaws-tab card)
    es_before: float
    es_after:  float
    move_san:  str
```

**Why typed columns over a bitmask or `TEXT[]`+GIN:**
- Mutually-exclusive families (tempo, phase, severity) are naturally one column each; a single nullable `tempo` enforces "≤1 tempo tag per flaw" at the schema level, and OR-within-family becomes `tempo IN (0,1)`.
- Stats-panel aggregation (incl. arbitrary tag-combinations) is a single-pass `COUNT(*) FILTER (WHERE …)` — no `unnest`.
- Most ty/Pydantic-friendly: columns map to `Literal` enums, matching the project's type-safety norms.
- Bitmask wins only on compactness (irrelevant — the table is tiny) and loses indexability. `TEXT[]`+GIN is the fallback **only** if the tag taxonomy is expected to churn frequently (avoids a migration per new additive tag); families are currently stable (last renamed 2026-06-05), so columns are clearer.

### Query patterns (all become trivial, push-down SQL)

**Games EXISTS filter** (`result-changing` blunder under `low-clock`):
```sql
SELECT g.* FROM games g
WHERE g.user_id = :uid AND <game-level filters>
  AND EXISTS (SELECT 1 FROM game_flaws f
              WHERE f.user_id=g.user_id AND f.game_id=g.id
                AND f.severity = 2 AND f.is_result_changing AND f.tempo = 0)
ORDER BY g.played_at DESC LIMIT :limit OFFSET :offset;
```

**Flaws tab** — drop the EXISTS wrapper; `SELECT f.*` joined to game metadata, `ORDER BY g.played_at, f.ply`. **Identical predicate** — share one WHERE-clause builder between the two endpoints so the cross-tab unification is enforced in code, not by convention.

**Stats panel** — single scan, arbitrary tag-combinations:
```sql
SELECT COUNT(*) FILTER (WHERE severity=2)                       AS blunders,
       COUNT(*) FILTER (WHERE tempo=0)                          AS low_clock,
       COUNT(*) FILTER (WHERE is_result_changing AND tempo=0)   AS rc_under_low_clock
FROM game_flaws f JOIN games g ON … WHERE f.user_id=:uid AND <filters>;
```

**Indexes:** PK `(user_id, game_id, ply)` covers the EXISTS join. Add `(user_id, severity)` for the common scan. Per-user flaw counts are bounded (thousands), so Postgres can btree on `user_id` and filter the rest in memory — no per-boolean partial indexes unless profiling demands them.

## Two open sub-decisions (resolve at plan time)

1. **Inaccuracies in the table?** They're ~2–3× more numerous and the chips already ignore them. **Recommendation:** store mistakes+blunders only as rows; if the stats panel needs an inaccuracy count, keep it as a cheap per-game aggregate, not a row per inaccuracy. (Alternative: store all three for a single source of truth, accepting the row growth.) The Flaws tab can default its severity filter to M+B regardless.
2. **Freshness / recompute.** `game_flaws` is a derived cache. Populate during import + the eval backfill pass (hook into `classify_game_flaws`), and recompute via a new `scripts/backfill_flaws.py` whenever flaw thresholds change (they last changed 2026-06-05). Coordinate with the existing `scripts/reimport_games.py` and `scripts/reclassify_positions.py`. No new live-query cost — classification already runs server-side today; this just persists its output.

## Relationship to SEED-036

SEED-036 designs the Flaws subtab (one card per flaw, rich severity × tag multi-select, deep-link target from Games chips) and notes the deep-link URL shape. This seed (a) locks the cross-tab shared-filter UX with single-flaw EXISTS semantics and family-aware logic, and (b) adds the `game_flaws` materialization the Flaws tab and tag-combo stats both need to be efficient and paginable. When the Flaws-subtab phase is planned, fold these decisions in rather than re-deriving them.
