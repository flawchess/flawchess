# Phase 82: LLM prompt awareness of Endgame Start vs End metrics — Research

**Researched:** 2026-05-10
**Domain:** FastAPI/Python backend (LLM insights pipeline) + React/TypeScript frontend (tile-color amendment)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Rename existing `MetricId = "endgame_score"` → `endgame_score_timeline`.
- **D-02:** Rename existing `MetricId = "non_endgame_score"` → `non_endgame_score_timeline`.
- **D-03:** New Tile-2 metric takes the clean name `endgame_score`. Glossary block freshly written — do not carry over v22 wording for the timeline metric.
- **D-04:** Tile-1 metric named `entry_eval_pawns`. New `MetricId` Literal entry; new glossary block.
- **D-05:** New `SubsectionId = "endgame_start_vs_end"`. Maps to `section_id = "overall"`. Order inside `overall`: `overall` → `endgame_start_vs_end` → `score_timeline`.
- **D-06:** `verdict` field on `SubsectionFinding` — REJECTED.
- **D-07:** Sig-test outcome is NOT propagated to the LLM payload. LLM narrates strictly from `zone` + `[near edge]` suffix.
- **D-08 (Tile 1 zone):** `ENDGAME_ENTRY_EVAL_ZONES = ZoneSpec(typical_lower=-0.50, typical_upper=+0.50, direction="higher_is_better")`.
- **D-09 (Tile 1 display):** `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` migrate from ±0.75 to ±0.50.
- **D-10 (Tile 2 zone):** Reuse live shared band `SCORE_BULLET_NEUTRAL_MIN/MAX` (±0.05, i.e. [0.45, 0.55]). No per-ELO registry.
- **D-11:** Per-ELO `ENDGAME_SCORE_ZONES` deferred to future phase.
- **D-12:** Tile color rule: `(value in green/red zone) AND p < 0.05` replaces sig-only Phase 81 D-09 rule.
- **D-13:** Amendment ships in-phase.
- **D-14:** Borderline case: value +0.46 (inside typical, p<0.001) → neutral on tile, not narrated.
- **D-15:** Tile-color logic in `EndgameStartVsEndSection.tsx`. Theme constants from `frontend/src/lib/theme.ts`.
- **D-16:** New `_findings_endgame_start_vs_end(response, window)` helper. Two `SubsectionFinding` items per window. Wired between `_finding_overall` and `_findings_score_timeline`.
- **D-17:** Sample-size gate: `entry_eval_n >= 10` (Tile 1), `endgame_wdl.total >= 10` (Tile 2). Below → empty finding with `value=NaN`, `zone="typical"`, `sample_quality="thin"`, `is_headline_eligible=False`.
- **D-18:** `is_headline_eligible = sample_quality != "thin"`.
- **D-19:** `dimension=None` for both findings.
- **D-20:** `series=None` for both findings.
- **D-21:** `findings_hash` recompute expected. Cache invalidated via `_PROMPT_VERSION` bump.
- **D-22:** Two glossary entries added to `app/prompts/endgame_insights.md`.
- **D-23:** New `### Subsection: endgame_start_vs_end` block in the prompt. "Setup → execution" framing. Cross-link to Time Pressure.
- **D-24:** Update `## Subsection → section_id mapping` table.
- **D-25:** Bump `_PROMPT_VERSION` from `endgame_v22` → `endgame_v23`.

### Claude's Discretion

- Final subsection ordering inside `overall` (D-05 says lead with whichever reads best).
- Plan wave dependency structure.

### Deferred Ideas (OUT OF SCOPE)

- Per-ELO `ENDGAME_SCORE_ZONES` (D-11).
- `verdict` field on `SubsectionFinding` (D-06).
- Per-TC entry-eval bands.
- Distribution/histogram view.
- Pre-endgame eval over time chart.
- LLM cross-section "composure-under-pressure" flag.
</user_constraints>

---

## Summary

Phase 82 wires two already-populated backend fields (`entry_eval_mean_pawns`, `endgame_score_p_value` on `EndgamePerformanceResponse`) through the Endgame Insights LLM pipeline. Phase 81 shipped the visible tiles in production; the LLM currently cannot narrate them because no findings are emitted and no glossary entry exists. Phase 82 closes that gap.

The work is additive on the LLM side — new `MetricId` and `SubsectionId` Literal values, a new `ZoneSpec` entry, a new findings-emitter function, prompt glossary + subsection block additions, and a `_PROMPT_VERSION` bump. The one non-additive change is a MetricId rename (two existing values get `_timeline` suffix) which affects `insights_service.py`, its tests, `endgame_zones.py`, and all test assertions that reference `"endgame_score"` or `"non_endgame_score"` as `metric=` in the `score_timeline` subsection context.

The frontend amendment (Plan 3) is purely a constant-and-logic change in `endgameEntryEvalZones.ts` and `EndgameStartVsEndSection.tsx` — the neutral band tightens from ±0.75 to ±0.50 and the tile-color gate changes from sig-only to `(zone != neutral) AND p < 0.05`. The codegen script `gen_endgame_zones_ts.py` does NOT need to output the new `ENDGAME_ENTRY_EVAL_ZONES` constant because `endgameEntryEvalZones.ts` is a hand-maintained file with its own constants (separate from the auto-generated `endgameZones.ts`).

**Primary recommendation:** Implement in four plans: (1) backend rename + zone + emitter + service tests, (2) prompt update, (3) frontend constant + tile-color amendment + component tests, (4) UAT + CHANGELOG.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `entry_eval_pawns` zone classification | API/Backend | — | `assign_zone` in `endgame_zones.py`; new ZoneSpec entry |
| `endgame_score` zone classification | API/Backend | — | Reuses existing `assign_zone` with new `endgame_score` MetricId entry mapped to `[0.45, 0.55]` |
| LLM findings emission | API/Backend | — | `_findings_endgame_start_vs_end` in `insights_service.py` |
| LLM prompt narration rules | API/Backend | — | `endgame_insights.md` glossary + subsection block |
| Tile neutral-band constant | Frontend | — | `endgameEntryEvalZones.ts` (hand-maintained, not codegen) |
| Tile color rule logic | Frontend | — | `EndgameStartVsEndSection.tsx` — change gate from sig-only to zone×sig |
| Codegen (endgameZones.ts) | Backend script | — | Only runs after `endgame_zones.py` changes; emitter does NOT output the entry-eval band |
| MetricId / SubsectionId Literal | API/Backend | — | `endgame_zones.py` — single source of truth re-exported by `app/schemas/insights.py` |

---

## Standard Stack

This phase uses the project's existing stack — no new dependencies.

| Layer | File / Module | What changes |
|-------|--------------|--------------|
| `app/services/endgame_zones.py` | `MetricId` Literal (line 30), `SubsectionId` Literal (line 51), `ZONE_REGISTRY` (line 125), `SAMPLE_QUALITY_BANDS` (line 241) | Add `entry_eval_pawns`, `endgame_score_timeline`, `non_endgame_score_timeline`, `endgame_start_vs_end`; rename two MetricIds; add ZoneSpec for `entry_eval_pawns` and `endgame_score`; add SAMPLE_QUALITY_BANDS entry for `endgame_start_vs_end` |
| `app/services/insights_service.py` | `_compute_subsection_findings` (line 371) | Insert `_findings_endgame_start_vs_end` call after `_finding_overall`, before `_findings_score_timeline`; rename MetricId usages inside `_findings_score_timeline` |
| `app/services/insights_llm.py` | `_PROMPT_VERSION` (line 66) | Bump to `"endgame_v23"` |
| `app/prompts/endgame_insights.md` | Metric glossary (~line 268), subsection mapping table (~line 330) | Add two glossary entries; add `### Subsection: endgame_start_vs_end` block; update mapping table; update score_timeline emitter-shape description |
| `frontend/src/lib/endgameEntryEvalZones.ts` | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` constants | Change from ±0.75 to ±0.50 |
| `frontend/src/components/charts/EndgameStartVsEndSection.tsx` | `evalIsInColoredZone` / `scoreIsInColoredZone` gate logic | Change tile-color condition from `isConfident(level) && isInColoredZone` to `isInColoredZone && p < 0.05` (or equivalent using the new ±0.50 zone threshold) |
| `tests/services/test_insights_llm.py` | Version assertion, metric-name assertions, subsection-mapping assertions | Update `test_prompt_version_is_v22`, all `"endgame_score"` / `"non_endgame_score"` metric assertions in the `score_timeline` context, mapping table test |
| `tests/services/test_insights_service.py` | `_findings_score_timeline` tests (if any) | Update metric-name assertions |
| `frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` | Constant assertions | Update ±0.75 → ±0.50 |
| `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | Color-zone tests | Update for new tile-color rule; fix prop-forwarding test (neutralMin/Max now ±0.50) |

---

## Architecture Patterns

### System Architecture Diagram

```
EndgameOverviewResponse.performance
  ├── entry_eval_mean_pawns  ──────────────────────────────────────────────┐
  ├── entry_eval_n                                                         │
  └── endgame_wdl.{wins,draws,losses,total}  ──────────────────────────── │──┐
                                                                           │  │
                              _findings_endgame_start_vs_end(response,w)  │  │
                                ├── Tile 1: assign_zone("entry_eval_pawns", entry_eval_mean_pawns)  ←──┘
                                └── Tile 2: assign_zone("endgame_score", score)  ←───────────────────────┘
                                         ↓
                         SubsectionFinding(subsection_id="endgame_start_vs_end", ...)
                                         ↓
                     _compute_subsection_findings (after _finding_overall)
                                         ↓
                           EndgameTabFindings.all_time_findings
                           EndgameTabFindings.last_3mo_findings
                                         ↓
                        _assemble_user_prompt (insights_llm.py)
                                         ↓
                   ### Subsection: endgame_start_vs_end (in user prompt)
                           [summary entry_eval_pawns] — zone, sample_quality
                           [summary endgame_score] — zone, sample_quality
                                         ↓
                              LLM → EndgameInsightsReport
```

### Component Responsibilities

| Component | File | Responsibility in Phase 82 |
|-----------|------|-----------------------------|
| `endgame_zones.py` | `app/services/` | MetricId rename; new Literal entries; new ZoneSpec registrations; new SubsectionId; new SAMPLE_QUALITY_BANDS entry |
| `insights_service.py` | `app/services/` | New `_findings_endgame_start_vs_end` emitter; update `_findings_score_timeline` MetricId usages; wire new emitter into `_compute_subsection_findings` |
| `insights_llm.py` | `app/services/` | Bump `_PROMPT_VERSION` to `endgame_v23` |
| `endgame_insights.md` | `app/prompts/` | New glossary entries; new subsection block; updated mapping table; updated score_timeline description |
| `endgameEntryEvalZones.ts` | `frontend/src/lib/` | Tighten ±0.75 → ±0.50 |
| `EndgameStartVsEndSection.tsx` | `frontend/src/components/charts/` | Tile-color rule amendment |
| `endgameZones.ts` | `frontend/src/generated/` | Regen ONLY if `endgame_zones.py` changes add output; current codegen script does NOT emit `entry_eval_pawns` zone — no regen needed |

---

## Critical Line-Number Corrections (CONTEXT.md vs Live Code)

CONTEXT.md's line numbers are close but researchers should use these verified figures:

| CONTEXT.md says | Actual location (VERIFIED) |
|-----------------|---------------------------|
| `MetricId` Literal at line 30 | **Line 30** — confirmed |
| `SubsectionId` Literal at line 51 | **Line 51** — confirmed |
| `ZoneSpec` dataclass at line 75 | **Line 75** — confirmed |
| `_findings_score_timeline` at lines 432–567 | **Lines 432–567** — confirmed |
| `_compute_section_findings` | The actual function name is `_compute_subsection_findings` at **line 371** |
| `_findings_overall_score_gap` | The actual function name is `_finding_overall` (singular, returns one finding) at **line 403** |
| `insights_llm.py` line 66 — `_PROMPT_VERSION` | **Line 66** — confirmed: `_PROMPT_VERSION = "endgame_v22"` |
| `app/schemas/insights.py` line 150 — `SubsectionFinding` | Confirmed at line ~171 (schema imports MetricId/SubsectionId from endgame_zones via re-export) |

**Insertion point for new emitter in `_compute_subsection_findings`:**
```python
# CURRENT ORDER (lines 384–393):
findings.append(_finding_overall(response, window))
findings.extend(_findings_score_timeline(response, window))      # ← insert BEFORE this
...

# TARGET ORDER:
findings.append(_finding_overall(response, window))
findings.extend(_findings_endgame_start_vs_end(response, window))  # ← NEW
findings.extend(_findings_score_timeline(response, window))
...
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zone classification for `entry_eval_pawns` | Custom threshold logic | `assign_zone("entry_eval_pawns", value)` via `ZONE_REGISTRY` + `ZoneSpec` | Already works for all existing metrics; just add the entry |
| Zone classification for `endgame_score` | Separate function | Same `assign_zone` with new `endgame_score` entry bound to `[0.45, 0.55]` | New MetricId literal slot replaces the old `endgame_score` no-op band |
| Empty window handling | Custom NaN check | `_empty_finding("endgame_start_vs_end", window, metric)` — already exists | Canonical pattern for all emitters |
| Sample quality | Inline threshold | `sample_quality("endgame_start_vs_end", sample_size)` after adding the key to `SAMPLE_QUALITY_BANDS` | Single-source bands, per-subsection honesty |
| `[near edge]` prompt suffix | New vocabulary | Existing prompt mechanism — already instructs LLM on borderline narration | The `[near edge]` tag is already produced by `insights_llm.py` for values near zone boundaries |

---

## Common Pitfalls

### Pitfall 1: Codegen regeneration — entry_eval_pawns is NOT in the generated file

**What goes wrong:** Developer adds `ENDGAME_ENTRY_EVAL_ZONES` to `endgame_zones.py` and expects `gen_endgame_zones_ts.py` to output it into `endgameZones.ts`.

**Why it happens:** The gen script has a hardcoded list of what to emit (FIXED_GAUGE_ZONES, ENDGAME_SKILL_ZONES, NEUTRAL_PCT_THRESHOLD, NEUTRAL_TIMEOUT_THRESHOLD, SCORE_GAP_NEUTRAL_MIN/MAX, PER_CLASS_GAUGE_ZONES). It reads `ZONE_REGISTRY["endgame_skill"]` and `ZONE_REGISTRY["score_gap"]` directly — it does not emit every ZONE_REGISTRY entry automatically.

**How to avoid:** The `ENDGAME_ENTRY_EVAL_ZONES` constant in `endgame_zones.py` is backend-only — it feeds `assign_zone` in the LLM pipeline. The frontend neutral band lives in `endgameEntryEvalZones.ts` (hand-maintained). These are two different sources for two different purposes. Do NOT add the entry-eval band to the gen script. [VERIFIED: `scripts/gen_endgame_zones_ts.py` full source; `frontend/src/generated/endgameZones.ts` current output]

**Warning signs:** CI fails with "endgameZones.ts drift" after adding a new ZONE_REGISTRY entry without running `gen_endgame_zones_ts.py`. Only run regen if the gen script itself is updated to output new constants.

### Pitfall 2: MetricId rename breaks `assign_zone` calls in `_findings_score_timeline`

**What goes wrong:** After renaming `"endgame_score"` → `"endgame_score_timeline"` in the `MetricId` Literal, the `assign_zone("endgame_score", ...)` calls inside `_findings_score_timeline` (lines 528, 543) use a string literal that no longer exists in `ZONE_REGISTRY`.

**Why it happens:** `assign_zone` does a dict lookup on `ZONE_REGISTRY[metric_id]` — if the MetricId is removed from the registry without updating the call site, it raises `KeyError` at runtime (not caught by `ty` because `assign_zone` takes `MetricId`).

**How to avoid:** The rename must be applied to (a) the `Literal["endgame_score"]` slot in `MetricId`, (b) the `ZONE_REGISTRY["endgame_score"]` key, (c) both `assign_zone("endgame_score", ...)` calls in `_findings_score_timeline`, and (d) both `metric="endgame_score"` SubsectionFinding constructors in `_findings_score_timeline`. All four must be updated atomically in Plan 1. [VERIFIED: `app/services/insights_service.py` lines 522–565]

**Warning signs:** `ty check` will flag unrecognized Literal values; `pytest tests/services/test_insights_service.py` will catch any remaining old-name assertions.

### Pitfall 3: `test_prompt_version_is_v22` test is a hard assertion — fails until bumped

**What goes wrong:** Any plan that updates the prompt but defers the `_PROMPT_VERSION` bump will cause `test_prompt_version_is_v22` in `test_insights_llm.py` (line 207) to fail.

**Why it happens:** The test asserts `insights_llm._PROMPT_VERSION == "endgame_v22"` — if Plan 2 changes the prompt before Plan 1 or independently, the test fails until bumped.

**How to avoid:** Bump `_PROMPT_VERSION` to `"endgame_v23"` in the same commit as the prompt changes (Plan 2). Update the test assertion in the same plan. [VERIFIED: `tests/services/test_insights_llm.py` line 207]

### Pitfall 4: Test assertions for `metric="endgame_score"` in `score_timeline` context

**What goes wrong:** After the rename, any test building a `SubsectionFinding(subsection_id="score_timeline", metric="endgame_score")` or asserting `"[summary endgame_score]"` in the score_timeline context will fail because `"endgame_score"` no longer appears in the `score_timeline` subsection.

**Why it happens:** `test_insights_llm.py` has many such assertions (lines 233, 270, 355, 361, 424, etc.) — all written against v22 naming.

**How to avoid:** Plan 1 must update all `score_timeline`-context assertions to `"endgame_score_timeline"` / `"non_endgame_score_timeline"`. Separately, Plan 2 adds new `"endgame_start_vs_end"`-context assertions for the new metrics. [VERIFIED: `tests/services/test_insights_llm.py` grep output]

### Pitfall 5: Frontend test prop-forwarding assertion fails after band tightening

**What goes wrong:** `EndgameStartVsEndSection.test.tsx` line 281 asserts `neutralMin: -0.75, neutralMax: 0.75` are passed to `MiniBulletChart`. After tightening to ±0.50, this assertion breaks.

**Why it happens:** The test was written against Phase 81's ±0.75 constants. [VERIFIED: `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` lines 280–282]

**How to avoid:** Plan 3 updates both the constant in `endgameEntryEvalZones.ts` and the matching assertion in the test. Also update `endgameEntryEvalZones.test.ts` lines 17–18 (asserts exact values). Also update the test at line 199 that asserts "significant but inside the neutral band" with `entry_eval_mean_pawns: 0.5` — at ±0.50, value 0.5 is ON the boundary (returns `ZONE_SUCCESS`), so the test input should be changed to e.g. `0.4` to remain inside.

**Warning signs:** `npm test` failures on `EndgameStartVsEndSection.test.tsx` and `endgameEntryEvalZones.test.ts` after Plan 3 constants change.

### Pitfall 6: Tile-color rule amendment changes existing test semantics

**What goes wrong:** The existing test "Tile 1 value text is unstyled when significant but inside the neutral band" (line 189) uses `entry_eval_mean_pawns: 0.5, p_value: 0.001`. Under the NEW rule `(value in zone) AND p < 0.05`, `0.5` sits exactly on the boundary of the ±0.50 zone (`>= NEUTRAL_MAX` → `ZONE_SUCCESS`), so the color WOULD show. The test input must be updated to a value clearly inside the band (e.g. `0.4`) to remain a valid "neutral" test case.

**Why it happens:** The test was calibrated for the Phase 81 sig-only rule with ±0.75 band. The Phase 82 rule change + band tightening interact at the boundary values.

**How to avoid:** When updating the tile-color logic in Plan 3, audit every test case in `EndgameStartVsEndSection.test.tsx` against the new (zone × sig) gate with ±0.50 boundaries.

### Pitfall 7: `SAMPLE_QUALITY_BANDS` must include `"endgame_start_vs_end"`

**What goes wrong:** `sample_quality("endgame_start_vs_end", n)` raises `KeyError` at runtime if `"endgame_start_vs_end"` is not added to `SAMPLE_QUALITY_BANDS`.

**Why it happens:** `sample_quality()` does a direct dict lookup on `SAMPLE_QUALITY_BANDS[subsection_id]`.

**How to avoid:** Plan 1 adds `"endgame_start_vs_end": (10, 50)` (same gate as `time_pressure_at_entry`, reasonable for a two-finding section; planner may adjust). [VERIFIED: `app/services/endgame_zones.py` lines 241–256]

---

## Code Examples

### Pattern: New ZoneSpec entry (VERIFIED from endgame_zones.py)

```python
# In ZONE_REGISTRY dict, after existing score_gap entry:
"entry_eval_pawns": ZoneSpec(
    typical_lower=-0.50,
    typical_upper=0.50,
    direction="higher_is_better",
),
# endgame_score replaces the old no-op [0, 1] band:
"endgame_score": ZoneSpec(
    typical_lower=0.45,  # SCORE_NEUTRAL_LOW = SCORE_BULLET_CENTER + SCORE_BULLET_NEUTRAL_MIN
    typical_upper=0.55,  # SCORE_NEUTRAL_HIGH = SCORE_BULLET_CENTER + SCORE_BULLET_NEUTRAL_MAX
    direction="higher_is_better",
),
```

Note: The live `SCORE_BULLET_CENTER = 0.5`, `SCORE_BULLET_NEUTRAL_MIN = -0.05`, `SCORE_BULLET_NEUTRAL_MAX = 0.05` → `[0.45, 0.55]`. [VERIFIED: `frontend/src/lib/scoreBulletConfig.ts` lines 11, 15–16]

### Pattern: MetricId rename — three places in endgame_zones.py (VERIFIED)

```python
# BEFORE (lines 39–40):
MetricId = Literal[
    "score_gap",
    "endgame_score",          # ← rename to "endgame_score_timeline"
    "non_endgame_score",      # ← rename to "non_endgame_score_timeline"
    "endgame_skill",
    ...
    "win_rate",
]

# ZONE_REGISTRY (lines 143–151):
# rename keys "endgame_score" → "endgame_score_timeline"
# rename keys "non_endgame_score" → "non_endgame_score_timeline"
# repurpose "endgame_score" for the new ±5pp calibrated band (D-10)
```

### Pattern: New emitter — mirrors `_findings_score_timeline` structure (VERIFIED)

```python
def _findings_endgame_start_vs_end(
    response: EndgameOverviewResponse,
    window: Window,
) -> list[SubsectionFinding]:
    """endgame_start_vs_end -> TWO findings (entry_eval_pawns, endgame_score).

    Phase 82 (D-16): wire Phase 81 entry_eval and endgame_score into the
    LLM payload. Both are single-aggregate, no series, no dimension (D-19,
    D-20). Empty-window convention matches all existing non-timeline emitters.
    """
    perf = response.performance

    # Tile 1 — entry eval
    n_eval = perf.entry_eval_n
    if n_eval < 10:  # D-17 gate
        tile1 = _empty_finding("endgame_start_vs_end", window, "entry_eval_pawns")
    else:
        quality = sample_quality("endgame_start_vs_end", n_eval)
        tile1 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="entry_eval_pawns",
            value=perf.entry_eval_mean_pawns,
            zone=assign_zone("entry_eval_pawns", perf.entry_eval_mean_pawns),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=n_eval,
            sample_quality=quality,
            is_headline_eligible=quality != "thin",
            dimension=None,
        )

    # Tile 2 — endgame score vs 50%
    total = perf.endgame_wdl.total
    if total < 10:  # D-17 gate
        tile2 = _empty_finding("endgame_start_vs_end", window, "endgame_score")
    else:
        score = (perf.endgame_wdl.wins + 0.5 * perf.endgame_wdl.draws) / total
        quality = sample_quality("endgame_start_vs_end", total)
        tile2 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="endgame_score",
            value=score,
            zone=assign_zone("endgame_score", score),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=total,
            sample_quality=quality,
            is_headline_eligible=quality != "thin",
            dimension=None,
        )

    return [tile1, tile2]
```

### Pattern: Tile-color rule amendment in EndgameStartVsEndSection.tsx (VERIFIED)

```typescript
// BEFORE (Phase 81 D-09, sig-only):
const evalIsInColoredZone = evalZoneHex !== ZONE_NEUTRAL;
const evalShowZoneFontColor = isConfident(evalLevel) && evalIsInColoredZone;

// AFTER (Phase 82 D-12, zone × sig):
// isConfident(evalLevel) checks p < 0.05 via deriveLevel() already.
// The gate is: value outside ±0.50 band AND p < 0.05.
// Since evalZoneHex now uses the ±0.50 constants (D-09 amendment),
// no logic change needed beyond the constant tightening — the existing
// gate `isConfident(level) && isInColoredZone` naturally implements
// (value_in_zone) AND (p<0.05) once the zone thresholds are ±0.50.
```

Note: `isConfident(level)` returns true when `level` is `'medium'` or `'high'`, which corresponds to `p < 0.05`. `endgameEntryEvalZoneColor` returns `ZONE_SUCCESS/ZONE_DANGER` when `|value| >= 0.50` (after the constant update). The D-12 semantics are exactly satisfied by updating the threshold constant — no structural logic change required. [VERIFIED: `EndgameStartVsEndSection.tsx` lines 67–71, `endgameEntryEvalZones.ts` lines 36–40, `endgameEntryEvalZones.test.ts` line 17]

---

## Prompt Fixture Locations

No external fixture files (e.g. JSON snapshots) exist for the LLM prompt tests. All prompt-body assertions in `test_insights_llm.py` operate by:

1. Reading `app/prompts/endgame_insights.md` directly from disk (e.g. `TestPromptVersionAndBody.test_prompt_file_does_not_contain_removed_framing_rule` at line 210 opens the file with `Path(__file__).resolve().parents[2] / "app" / "prompts" / "endgame_insights.md"`).
2. Constructing `SubsectionFinding` objects inline and calling `_assemble_user_prompt` or `_render_series_block`.

There are no `tests/fixtures/insights/` snapshot files. [VERIFIED: `find` on tests/ — only `tests/seed_fixtures.py`]

**Implication:** "Updating prompt fixtures" in Plan 2 means updating the inline `SubsectionFinding` construction in test methods, updating the string-in-body assertions, and updating `test_prompt_version_is_v22`. No separate fixture files need creating.

---

## Codegen Impact Assessment

The `gen_endgame_zones_ts.py` script currently outputs:
- `FIXED_GAUGE_ZONES` (from `BUCKETED_ZONE_REGISTRY`)
- `ENDGAME_SKILL_ZONES` (from `ZONE_REGISTRY["endgame_skill"]`)
- `NEUTRAL_PCT_THRESHOLD`, `NEUTRAL_TIMEOUT_THRESHOLD`
- `SCORE_GAP_NEUTRAL_MIN`, `SCORE_GAP_NEUTRAL_MAX` (from `ZONE_REGISTRY["score_gap"]`)
- `PER_CLASS_GAUGE_ZONES`

It does NOT output `endgame_score` or `non_endgame_score` zone bands (the current no-op [0, 1] bands have no FE consumer — the frontend `scoreZoneColor` uses `scoreBulletConfig.ts` directly). After the rename, the old keys disappear from `ZONE_REGISTRY` and the new `endgame_score` entry takes the ±5pp calibrated band, but the gen script still does not reference `ZONE_REGISTRY["endgame_score"]` — so **no codegen changes are needed** unless a future phase wants to export this band.

**HOWEVER:** Any change to `endgame_zones.py` will be checked for drift by CI (`git diff --exit-code frontend/src/generated/endgameZones.ts` after re-running the script). Since the gen script doesn't reference the renamed keys, the generated output will NOT change — CI drift check will pass without re-running. [VERIFIED: `scripts/gen_endgame_zones_ts.py` full source]

---

## Runtime State Inventory

Not applicable — this is an additive feature phase with no renames of persistent identifiers, user IDs, or stored data. `findings_hash` will change (different MetricId values in the findings list) but this is expected and handled by cache invalidation via `_PROMPT_VERSION` bump.

---

## Environment Availability

No external dependencies beyond the project's own stack. All required tools (`uv`, `npm`, `pytest`, `ty`) are pre-existing. The dev database (for UAT in Plan 4) requires `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (uv run pytest) |
| Frontend framework | Vitest |
| Backend quick run | `uv run pytest tests/services/test_insights_service.py tests/services/test_insights_llm.py -x` |
| Backend full suite | `uv run pytest` |
| Frontend quick run | `npm test -- --run frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` |
| Frontend full suite | `npm test` |
| Type check | `uv run ty check app/ tests/` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| MetricId rename compiles (Literal update) | type | `uv run ty check app/ tests/` | ✅ existing |
| `_findings_score_timeline` emits `endgame_score_timeline` / `non_endgame_score_timeline` | unit | `uv run pytest tests/services/test_insights_llm.py -k "score_timeline" -x` | ✅ existing (needs update) |
| `_findings_endgame_start_vs_end` emits two findings (populated + empty cases) | unit | `uv run pytest tests/services/test_insights_service.py -k "endgame_start_vs_end" -x` | ❌ Wave 0 |
| `_prompt_version_is_v23` | unit | `uv run pytest tests/services/test_insights_llm.py -k "prompt_version" -x` | ✅ existing (needs update) |
| Mapping table includes `endgame_start_vs_end` row | unit | `uv run pytest tests/services/test_insights_llm.py -k "mapping_table" -x` | ✅ existing (needs extension) |
| `entry_eval_pawns` zone classification | unit | `uv run pytest tests/test_endgame_zones.py -k "entry_eval" -x` | ❌ Wave 0 |
| Tile-1 NEUTRAL at ±0.50 boundary | unit | `npm test -- --run frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` | ✅ existing (needs update) |
| Tile-color rule: zone×sig vs old sig-only | unit | `npm test -- --run frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | ✅ existing (needs update) |

### Wave 0 Gaps

- [ ] `tests/services/test_insights_service.py` — add `TestFindingsEndgameStartVsEnd` class covering: populated tiles (both n≥10), empty tiles (both n<10), mixed sparse (one tile empty), zone classification (entry_eval in strong/weak/typical, endgame_score in strong/weak/typical).
- [ ] `tests/test_endgame_zones.py` — add test for new ZoneSpec entries: `assign_zone("entry_eval_pawns", ...)` at ±0.50 boundaries and `assign_zone("endgame_score", ...)` at ±0.45/0.55 boundaries.

---

## Security Domain

No new external inputs, no authentication changes, no new API endpoints. Phase 82 is backend-internal (service layer) and frontend-constant changes only. ASVS input validation: both `entry_eval_mean_pawns` (float) and `endgame_wdl.total` (int) are already validated by Pydantic at the API boundary (Phase 81). No new security surface.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SAMPLE_QUALITY_BANDS["endgame_start_vs_end"] = (10, 50)` is a reasonable band (same as `time_pressure_at_entry`) | Code Examples | LLM quality labels `thin`/`adequate`/`rich` may be miscalibrated for this subsection — but this is editorially adjustable post-ship with no schema impact |
| A2 | The `endgame_score` ZoneSpec `[0.45, 0.55]` is the right representation for "reuse SCORE_BULLET_NEUTRAL_MIN/MAX" | Code Examples | The frontend uses `SCORE_NEUTRAL_LOW = SCORE_BULLET_CENTER + SCORE_BULLET_NEUTRAL_MIN = 0.5 + (-0.05) = 0.45` — verified against `scoreBulletConfig.ts`. Value `[0.45, 0.55]` is correct. |

**If this table is empty of HIGH-RISK items:** Both assumptions are low-risk editorial choices confirmed by code inspection.

---

## Open Questions

1. **`SAMPLE_QUALITY_BANDS` band choice for `endgame_start_vs_end`**
   - What we know: existing bands range from (10, 40) for elo_timeline to (50, 200) for overall.
   - What's unclear: whether (10, 50) vs (20, 100) better matches the expected n distribution for users who reach endgame.
   - Recommendation: use (10, 50) matching `time_pressure_at_entry` — both are per-game aggregate sections with similar expected sample sizes. Adjust in a follow-up if LLM over-narrates thin windows.

2. **Score_timeline prompt description update scope**
   - What we know: `app/prompts/endgame_insights.md` line 125 describes the score_timeline three-metric shape using `endgame_score` and `non_endgame_score`. After the rename, this description must be updated to `endgame_score_timeline` and `non_endgame_score_timeline`.
   - What's unclear: whether the v23 changelog summary in `_PROMPT_VERSION` line already covers this or needs an explicit mention.
   - Recommendation: update the line-125 description block in Plan 2 as part of the prompt update. The D-25 changelog text mentions the rename explicitly.

---

## Sources

### Primary (HIGH confidence)
- `app/services/endgame_zones.py` — full file read; all Literal, ZoneSpec, registry, and SAMPLE_QUALITY_BANDS structures verified.
- `app/services/insights_service.py` — lines 1–567 read; `_compute_subsection_findings` structure and `_findings_score_timeline` implementation verified.
- `app/services/insights_llm.py` — line 66 `_PROMPT_VERSION` verified.
- `app/prompts/endgame_insights.md` — lines 1–363 read; glossary section, mapping table, and score_timeline description verified.
- `frontend/src/components/charts/EndgameStartVsEndSection.tsx` — full file read; tile-color logic and constants imports verified.
- `frontend/src/lib/endgameEntryEvalZones.ts` — full file read; ±0.75 constants and `endgameEntryEvalZoneColor` function verified.
- `frontend/src/generated/endgameZones.ts` — full file read; codegen output scope verified.
- `scripts/gen_endgame_zones_ts.py` — full file read; what the script exports verified.
- `tests/services/test_insights_llm.py` — key sections read; metric-name assertions and prompt-version test located.
- `tests/services/test_insights_service.py` — key sections read; no existing `endgame_start_vs_end` tests confirmed.
- `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — full file read; ±0.75 prop assertion locations identified.
- `frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` — full file read; ±0.75 constant assertions identified.
- `app/schemas/endgames.py` — `EndgamePerformanceResponse` fields `entry_eval_mean_pawns`, `entry_eval_n`, `entry_eval_p_value`, `endgame_score_p_value`, `endgame_wdl` confirmed present.
- `frontend/src/lib/scoreBulletConfig.ts` — `SCORE_BULLET_CENTER = 0.5`, `SCORE_BULLET_NEUTRAL_MIN = -0.05`, `SCORE_BULLET_NEUTRAL_MAX = 0.05` verified.

---

## Metadata

**Confidence breakdown:**
- Exact file/line locations: HIGH — all read directly from live code
- MetricId rename scope: HIGH — all call sites in `_findings_score_timeline` verified
- Test churn scope: HIGH — all affected assertions located
- Codegen non-impact: HIGH — gen script source fully verified
- SAMPLE_QUALITY_BANDS choice: LOW (editorial, not technical)

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (stable codebase; prompt version bumps may change prompt line numbers)
