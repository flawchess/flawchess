# Phase 110: Flaw-Tag Taxonomy Overhaul - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
**Areas discussed:** Migration data handling, Panel impact surfacing, Frontend threshold source, Active-filter highlight, Distribution scope

---

## Migration data handling (game_flaws impact columns)

| Option | Description | Selected |
|--------|-------------|----------|
| SQL-compute in migration | Populate is_reversed/is_squandered in the migration via pure SQL from stored es_before/es_after (outcome-independent ladder). All users correct immediately, no script. | |
| Add false + script backfill | Add NOT NULL booleans with server_default=false; recompute via backfill_flaws.py for users 28 & 44. Others stay false/stale. Matches roadmap success criterion #4. | ✓ |

**User's choice:** Add false + script backfill.
**Notes:** Claude surfaced that, unlike the old outcome-dependent result-changing, the new ladder is purely a function of es_before/es_after (both already stored on game_flaws), so a SQL UPDATE in the migration could have populated all users for free. User chose the simpler scoped path; SQL-compute recorded in CONTEXT as a future all-users-refresh option.

---

## Flaw-Stats panel — impact surfacing (band)

| Option | Description | Selected |
|--------|-------------|----------|
| Two separate rates | reversed_rate + squandered_rate as distinct band stats; headline = reversed_rate. | |
| Single combined impact rate | One impact_rate = reversed OR squandered. | |
| Drop impact rate from band | Remove the headline impact stat from FlawStatsBand entirely; impact only via chips/distribution. | ✓ |

**User's choice:** Drop impact rate from band.

---

## FlawTagDistribution scope (clarifying follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep impact in distribution | Add reversed_rate + squandered_rate to TagDistribution and render both; remove while_ahead_rate/result_changing_rate. | ✓ |
| Drop impact everywhere in panel | Remove impact rates from TagDistribution with no replacement; impact only as per-card chips. | |

**User's choice:** Keep impact in distribution.
**Notes:** Band stays high-level (severity/counts), distribution carries the full per-tag breakdown including impact.

---

## Frontend threshold source (popover interpolation)

| Option | Description | Selected |
|--------|-------------|----------|
| Generated TS from Python | New scripts/gen_flaw_thresholds_ts.py → frontend/src/generated/, CI drift check. | ✓ |
| Hand-written TS mirror | Small lib constants object, manual sync. | |
| Expose via API | Return thresholds in an API response. | |

**User's choice:** Generated TS — focused generator, do NOT merge into gen_endgame_zones_ts.py.
**Notes:** User raised whether to merge into a generic gen_ts_constants.py absorbing gen_endgame_zones_ts.py. Claude recommended against for this phase (different output shapes — zone registry vs ~4 flat scalars; pulls an unrelated CI-gated surface into the blast radius; generic abstraction earns its keep at 3+ consumers). User confirmed the focused-generator approach; the unify-the-generators refactor is captured as a backlog item for when a 3rd generator exists.

---

## Active-filter chip highlight

| Option | Description | Selected |
|--------|-------------|----------|
| Ring/outline | Colored ring in the family color; no size/layout change. | ✓ |
| Bolder fill + weight | Stronger background fill + bold text. | |
| Ring + bold (both) | Combine ring outline and bold text. | |

**User's choice:** Ring/outline.
**Notes:** Via a new theme.ts constant; applies to Games + Flaws cards, desktop + mobile.

---

## Claude's Discretion

- Exact theme.ts ring constant name/value, width/offset.
- Whether TAG_LABELS is fully removed or retained for FlawFilterControl button labels.
- Alembic server_default drop-after-add and downgrade shape.
- Tag order in _build_tags after the impact rebuild.
- Whether _classify_impact is one new helper replacing _is_result_changing (user_result no longer needed for impact).

## Deferred Ideas

- Unify the gen_*_ts.py scripts into a generic gen_ts_constants.py (revisit at 3+ consumers).
- SQL-compute the impact columns for ALL dev users in a future all-users refresh (leveraging stored es_before/es_after).
- The future tactic / error-nature tag family (chess_detect) — out of scope.

## Resolved conflict noted

- flaw-tag-definitions.md claims "no DB migration — pure code + docs"; this is stale (predates Phase 108's game_flaws materialization). Roadmap correctly mandates a forward alter migration. Downstream agents follow the roadmap.
