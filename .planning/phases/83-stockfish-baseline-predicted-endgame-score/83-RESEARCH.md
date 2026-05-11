# Phase 83: Stockfish-baseline predicted endgame score - Research

**Researched:** 2026-05-11
**Domain:** Python sigmoid utility + SQLAlchemy aggregation + React 19/TS 2×2 UI restructure + LLM prompt + benchmark calibration
**Confidence:** HIGH

## Summary

This phase adds a Stockfish-baseline **"Achievable score"** bullet chart inside the existing `EndgameStartVsEndSection` "Where you start" tile. The Lichess winning-chances sigmoid (`1 / (1 + e^(-0.00368208 * cp))`) converts per-game endgame-entry `eval_cp` to expected scores in [0, 1]; mate maps directly to 0/1. Mean is aggregated per user, Wilson-tested vs 50%, and surfaced as a new bullet alongside the existing `endgame_score` bullet (same W+0.5D axis). The tile section restructures into a 2×2 grid: eval / WDL on top, score-axis bullets on bottom — so the achievable-vs-achieved gap reads directly across tiles. All 5 plans ship in-phase: sigmoid util, backend plumbing, UI restructure, `/benchmarks` calibration + `ENTRY_EXPECTED_SCORE_ZONES`, LLM prompt awareness with `_PROMPT_VERSION` bump to `endgame_v25`.

Every integration point is **already established** by Phases 81-82 — Phase 83 is incremental plumbing on top of a working pipeline. The Lichess sigmoid constant is well-documented (Lichess winning-chances method); the project's Wilson chess-score util (`app.services.score_confidence.compute_confidence_bucket`) already powers `endgame_score_p_value`; the SQL query in `endgame_repository.py:803-816` already SELECTs `eval_cp` AND `eval_mate` per row, so Plan 2 does NOT need to extend the SELECT.

**Primary recommendation:** Mirror Phase 82's plan structure (5 waves: backend + UI + prompt + benchmark calibration + UAT). Wave 0 needs zero new infra — every required helper already exists.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Plan Scope (D-01):** Ship all 5 plans in-phase: 3 core (sigmoid util + per-game plumbing + UI restructure) plus the seed's two "optional" plans (Plan 4 = formal `/benchmarks` calibration; Plan 5 = LLM prompt awareness). Reasoning: tile and LLM should agree from day one (Phase 82 D-13 precedent), and cohort band must come from formal calibration for consistency with Phase 82's bands.

**Lichess Sigmoid Conversion:**
- **D-02:** New module `app/services/eval_utils.py` with one constant and two pure functions:
  - `LICHESS_K = 0.00368208` (Lichess accuracy/winning-chances doc — extract as named module-level constant, no magic numbers).
  - `eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white", "black"]) -> float` — sign-flips per `user_color` (mirroring `_classify_endgame_bucket` in `app/services/endgame_service.py:170-204`), returns `1 / (1 + exp(-LICHESS_K * user_eval_cp))`. Domain: signed centipawns. Range: (0, 1), centered at 0.5 when user_eval_cp = 0.
  - `eval_mate_to_expected_score(eval_mate: int, user_color: Literal["white", "black"]) -> float` — returns `1.0` if user is the side mating, `0.0` otherwise. Mate NOT routed through sigmoid.
- **D-03:** Unit tests in `tests/services/test_eval_utils.py` cover: sigmoid centred at 0.5 (eval_cp=0), sign convention for both colors (+100 cp → 0.59 for white-user, 0.41 for black-user), saturation at large evals, mate-for-user → 1.0, mate-against-user → 0.0. Pure module — unit tests, not integration.

**Per-Game Cohort Metric:**
- **D-04:** Mirror existing `entry_eval_mean_pawns` plumbing in `app/repositories/endgame_repository.py:793-841` and `app/services/endgame_service.py:1670-1712`. Per endgame game: compute one expected score (sigmoid for `eval_cp`, 0/1 for `eval_mate`), de-dupe over multi-class entry rows identically to entry-eval. Aggregate per user: mean per-game expected score + n.
- **D-05:** Sig test: project Wilson chess-score util (same path producing `endgame_score_p_value`), tested against 50%. Outputs: `entry_expected_score`, `entry_expected_score_n`, `entry_expected_score_p_value`, `entry_expected_score_ci_low`, `entry_expected_score_ci_high` on `EndgamePerformanceResponse`. Do not editorialize methodology in schema docstrings.
- **D-06:** Cohort filter: `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`. Mate games **included** (mate has defined expected score: 0 or 1) — differs from Phase 81 entry-eval cohort which excluded mate.
- **D-07:** `|eval_cp| < 2000` clip applied for consistency with Phase 82's cohort definition, even though sigmoid saturates around ±800 cp.

**UI: 2×2 Grid Restructure:**
- **D-08:** Add `MiniWDLBar` (endgame-only) to top of "What you do with it" tile. Keep existing "Games with vs without Endgame" table unchanged below. Visual redundancy on WDL is accepted.
- **D-09:** New bullet labelled **"Achievable score"**. Rejected: "Stockfish baseline", "Predicted score", "Ceiling score".
- **D-10:** Popover framing: **"Expected for sub-2300 play to fall below"**: "This is what a 2300+ rated player would score from your endgame-entry positions, via the Lichess winning-chances sigmoid. The Lichess curve is fitted on 2300+ rapid games — scoring below this baseline from positive evals is normal at lower ratings and is not a flaw. Compare against your achieved Endgame score on the right." Never use "underperformance" in user-facing copy.
- **D-11:** New bullet reuses existing `MiniBulletChart`, W+0.5D axis (`[0, 1]`, center 0.5), project's score-zone Wilson-test coloring. Tile-color rule: `(zone != neutral) AND p < 0.05` (Phase 82 D-12). Borderline cases: neutral on tile AND not narrated by LLM.
- **D-12:** All changes localized to `frontend/src/components/charts/EndgameStartVsEndSection.tsx`. Each tile becomes a 2-row stack (no nested grid). Mobile stacking: top-row first, bottom-row second. Existing `lg:grid-cols-2` outer grid stays.
- **D-13:** Top-row chart in "What you do with it" reuses `MiniWDLBar` from `@/components/stats/MiniWDLBar`. Lift import; do NOT reimplement. Input: `data.endgame_wdl.{win_pct, draw_pct, loss_pct}`.

**Cohort Band Source (Plan 4 calibration):**
- **D-14:** `entry_expected_score` cohort band from formal `/benchmarks` calibration. Plan 4 produces `reports/benchmarks-YYYY-MM-DD.md` section with pooled distribution, TC × ELO cells, Cohen's d collapse verdict, recommended bands. Bands lock into `app/services/endgame_zones.py` as `ENTRY_EXPECTED_SCORE_ZONES = ZoneSpec(...)` with `direction="higher_is_better"`.
- **D-15:** Apply editorial-judgement principle (Phase 82 D-08): if IQR is too wide for the metric to land in green/red zones, tighten inside IQR. Decision deferred to Plan 4 execution time.
- **D-16:** Regenerate `frontend/src/generated/endgameZones.ts` via `scripts/gen_endgame_zones_ts.py`. CI fails on drift.

**LLM Prompt Awareness (Plan 5):**
- **D-17:** Add `MetricId = "entry_expected_score"` to Literal slot. New glossary entry in `app/prompts/endgame_insights.md` defines: signed Stockfish-baseline expected score in W+0.5D units, derivation (Lichess sigmoid + mate→0/1), the "2300+ baseline / sub-2300 normally falls below" framing, cohort band from Plan 4, sig-test framing the tile uses (LLM does NOT receive sig-test outcome — narrates by zone, Phase 82 D-06).
- **D-18:** Extend existing `### Subsection: endgame_start_vs_end` block with `entry_expected_score` guidance: LLM should narrate **the gap between `entry_expected_score` and `endgame_score`** as headline diagnostic, with `entry_eval_pawns` as explanatory unit. Example narrations provided in CONTEXT.md. Never "underperformance" framing.
- **D-19:** Findings emitter `_findings_endgame_start_vs_end` gains a third `SubsectionFinding` for `entry_expected_score` — same shape as existing two. Sample-size gate `entry_expected_score_n >= 10`. No `verdict` field.
- **D-20:** Bump `_PROMPT_VERSION` from `endgame_v24` → **`endgame_v25`** with one-line changelog entry.

**Schema Naming:**
- **D-21:** New schema field key is `entry_expected_score`. Companion fields: `entry_expected_score_n`, `entry_expected_score_p_value`, `entry_expected_score_ci_low`, `entry_expected_score_ci_high`. All default to safe empty values (`0.0` / `0` / `None`).

**Methodology — Two CIs, Not Paired Test:**
- **D-22:** Two independent Wilson CIs (not paired test). Two CIs is the right call for visual juxtaposition. Don't editorialize the paired-test asymmetry in user-facing copy.

### Claude's Discretion

- Final wording inside the popover paragraph (D-10): polish during implementation.
- Final ordering of the LLM narration when entry_eval / achievable / endgame_score all fire (D-18): lead with the gap when it is the dominant signal, lead with entry_eval when entry_eval is the dominant signal. Decide during prompt-write.
- Exact placement of the new MiniWDLBar legend / aria-label inside the "What you do with it" tile (D-13): match surrounding tile-1 conventions.

### Deferred Ideas (OUT OF SCOPE)

- Per-eval-bin breakdown ("you score below baseline specifically when entering at +1.0…+2.0")
- Paired sig test of the gap (achievable vs achieved)
- Openings-side expected score (sigmoid emits ~0.50 everywhere)
- Per-ELO `ENTRY_EXPECTED_SCORE_ZONES`
- WDL-in-table consolidation
</user_constraints>

<phase_requirements>
## Phase Requirements

CONTEXT.md declares no formal `REQ-XX` IDs (phase requirements TBD during `/gsd-discuss-phase` 83); the equivalent locked spec is the D-01..D-22 decision set above. The planner should treat each D-number as a requirement for trace-matrix purposes.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-02 | Create `eval_utils.py` with `LICHESS_K`, `eval_cp_to_expected_score`, `eval_mate_to_expected_score` | Module does not exist (verified). Sign convention via `_classify_endgame_bucket` (`endgame_service.py:169-213`) provides exact mirror. |
| D-03 | Unit tests in `tests/services/test_eval_utils.py` | Test dir exists; sibling `test_eval_confidence.py` provides scaffolding pattern. |
| D-04 | Mirror entry-eval plumbing for expected-score | `_get_endgame_performance_from_rows` (lines 1645-1732) is the exact aggregator; `query_endgame_bucket_rows` already returns one row per game with `(eval_cp, eval_mate, user_color)`. |
| D-05 | Wilson chess-score util reuse for `entry_expected_score_p_value` | Project util is `app.services.score_confidence.compute_confidence_bucket(w, d, losses, n) -> (level, p_value, se)` — but see "Critical methodology note" below: this expects integer (W, D, L, N), not float scores. |
| D-06 | Cohort filter `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`; mate included | SQL already returns both columns; only the Python aggregator changes. |
| D-07 | `|eval_cp| < 2000` clip | Apply in aggregator after sign flip and before sigmoid. |
| D-08 / D-13 | UI restructure + `MiniWDLBar` lift | `MiniWDLBar` is exported from `frontend/src/components/stats/MiniWDLBar.tsx` (independent module — NOT from EndgamePerformanceSection.tsx as CONTEXT.md suggested). Already imported by `EndgamePerformanceSection.tsx:13`. |
| D-09 / D-10 / D-11 | "Achievable score" bullet, popover framing, W+0.5D axis | `MiniBulletChart`, `SCORE_BULLET_CENTER`, `scoreBulletDomain`, `scoreZoneColor`, `clampScoreCi` already exist in `scoreBulletConfig.ts`. |
| D-14 / D-15 / D-16 | `ENTRY_EXPECTED_SCORE_ZONES` + benchmark calibration + regen ts | `ZoneSpec` infra in `endgame_zones.py`; canonical CTE in `.claude/skills/benchmarks/SKILL.md`. |
| D-17 / D-18 / D-19 / D-20 | LLM prompt awareness | `_findings_endgame_start_vs_end` already emits two findings — extend to three. `MetricId` Literal in `endgame_zones.py:30-53`. Prompt subsection at `endgame_insights.md:260-286`. |
| D-21 | New schema fields with safe defaults | Phase 81 D-11 pattern in `app/schemas/endgames.py:107-140`. |
| D-22 | Two independent Wilson CIs | Encoded as two findings + two bullet charts (no paired-test machinery). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

The following directives apply directly to Phase 83 work and MUST be honored by every plan:

| Directive | Source | Relevance |
|-----------|--------|-----------|
| **No `asyncio.gather` on same `AsyncSession`** | CLAUDE.md "Critical Constraints" | The expected-score aggregator runs on the same row stream as entry-eval — no new concurrency. Existing `await query_endgame_bucket_rows(...)` pattern at `endgame_service.py:1769-1779` is sequential and stays sequential. |
| **httpx async only — never `requests`** | CLAUDE.md "Tech Stack" | N/A for this phase (no external HTTP). |
| **ty compliance** | CLAUDE.md "Coding Guidelines" | All new functions must have explicit return types. Use `Literal["white", "black"]` (D-02), not bare `str`. The bucket_rows iterator at `endgame_service.py:1680-1693` already uses `# ty: ignore[unresolved-attribute]` for SQL `Row` attributes — mirror this pattern in the new aggregator. |
| **No magic numbers** | CLAUDE.md "Coding Guidelines" | `LICHESS_K = 0.00368208` extracted as module-level constant (D-02). The `2000 cp` clip threshold and `MIN_N=10` gate must reuse existing named constants (`EVAL_CLIP_MAX_CP` if defined, else lift from Phase 82 location; `MIN_GAMES_FOR_RELIABLE_STATS` for the gate). |
| **Type safety — `Literal["white", "black"]`** | CLAUDE.md "Coding Guidelines" | D-02 names `Literal["white", "black"]` explicitly. |
| **Frontend `data-testid` on interactive elements** | CLAUDE.md "Browser Automation Rules" | The new "Achievable score" bullet, the new `MiniWDLBar` slot, and the new popover trigger all need stable kebab-case testids: `achievable-score-value`, `achievable-score-popover-trigger`, `endgame-wdl-bar` (or similar). Match existing pattern at `EndgameStartVsEndSection.tsx:108-181`. |
| **ARIA labels on icon-only buttons** | CLAUDE.md "Browser Automation Rules" | The new popover trigger inherits from `ScoreConfidencePopover` (already ARIA-compliant). New `MiniWDLBar` is non-interactive (decorative bar) but already has `data-testid="mini-wdl-bar"`. |
| **`noUncheckedIndexedAccess` enabled (frontend)** | CLAUDE.md "Frontend" | Any new Record/array access in `EndgameStartVsEndSection.tsx` must narrow before use. |
| **Knip runs in CI** | CLAUDE.md "Frontend" | Any new exports from `endgameEntryExpectedScoreZones.ts` (or wherever the new zone helper lives) must be imported somewhere — the planner should bake the helper into the same file that imports `endgameEntryEvalZones` to avoid an unused-export warning. Cleanest: regenerated `endgameZones.ts` exports `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX` and a `entryExpectedScoreZoneColor` helper, consumed only by `EndgameStartVsEndSection.tsx`. |
| **Theme constants in `theme.ts`** | CLAUDE.md "Frontend" | Reuse `ZONE_SUCCESS` / `ZONE_DANGER` / `ZONE_NEUTRAL` — no new color constants. |
| **No SQLite in tests, no mocked DB** | CLAUDE.md "Tech Stack" + "Critical Constraints" | Plan 2 integration tests run against live dev Postgres (Docker `localhost:5432`). |
| **PostgreSQL 18 in Docker required** | CLAUDE.md "Commands" | Plan 2 + Plan 4 require `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` and `bin/benchmark_db.sh start` respectively. |
| **Em-dashes sparingly** | CLAUDE.md "Communication Style" | User-facing popover copy (D-10) and the LLM prompt glossary should use commas/periods/parentheses. |
| **No `verdict` field on `SubsectionFinding`** | Phase 82 D-06 (locked, carries forward) | New `entry_expected_score` finding follows the existing 2-finding shape with `zone`, `sample_quality`, `is_headline_eligible`, `dimension=None`. |

## Architectural Responsibility Map

Phase 83 spans 5 architectural tiers — accurate tier assignment matters because the planner must place each task in the correct layer.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Lichess sigmoid math (eval_cp → expected_score) | API / Backend (pure module) | — | Pure function, no I/O. Lives in `app/services/eval_utils.py`. Used by `endgame_service.py` aggregator. |
| Per-game expected-score aggregation (mean + Wilson sig test) | API / Backend (service) | API / Backend (repository) | SQL already returns `(eval_cp, eval_mate, user_color)` per game (verified: `endgame_repository.py:803-816`). Aggregation logic lives in `_get_endgame_performance_from_rows`. NO SQL changes needed for D-04. |
| New schema fields on `EndgamePerformanceResponse` | API / Backend (schema) | — | Pydantic v2 model. Safe defaults (`= 0.0` / `= 0` / `= None`) per Phase 81 D-11 pattern. |
| 2×2 grid UI restructure | Browser / Client | — | `EndgameStartVsEndSection.tsx` is the only file changing for UI. Existing tile container becomes a 2-row stack (top: existing eval / new WDL; bottom: new achievable / existing achieved). |
| Lift `MiniWDLBar` into "What you do with it" tile | Browser / Client | — | `MiniWDLBar` already exists at `@/components/stats/MiniWDLBar` and is imported by `EndgamePerformanceSection.tsx:13`. Cross-component import, not a new component. |
| New "Achievable score" bullet | Browser / Client | — | Reuses `MiniBulletChart` + `scoreBulletConfig.ts` constants. New zone helper for color (generated from `endgameZones.ts`). |
| Frontend zone constants | Browser / Client (generated) | API / Backend (registry) | `app/services/endgame_zones.py` is the source of truth; `frontend/src/generated/endgameZones.ts` regenerates via `scripts/gen_endgame_zones_ts.py`. CI fails on drift. |
| LLM payload extension (`MetricId` literal + finding emitter) | API / Backend (service) | — | `app/services/insights_service.py` `_findings_endgame_start_vs_end` extends from 2 → 3 findings. `MetricId` Literal in `endgame_zones.py`. |
| LLM prompt content (glossary + subsection guidance) | API / Backend (markdown asset) | — | `app/prompts/endgame_insights.md` glossary + subsection block. `_PROMPT_VERSION` in `app/services/insights_llm.py:66`. |
| Benchmark calibration (`/benchmarks` SKILL extension + zone bands) | Operator tooling (skill) | API / Backend (registry) | `.claude/skills/benchmarks/SKILL.md` is a Claude skill, not runtime code. The output is one new `ZoneSpec` entry in `endgame_zones.py` + a regenerated `endgameZones.ts`. |
| Test coverage (unit + integration + RTL + LLM prompt) | API / Backend (unit + integration) + Browser / Client (RTL) | — | Test files already exist for every tier; Phase 83 extends, doesn't reinvent. |

## Standard Stack

### Core

| Library / Helper | Version | Purpose | Why Standard |
|---|---|---|---|
| `app.services.score_confidence.compute_confidence_bucket` | live | Wilson score-test vs 50% — returns `(level, p_value, se)` | Already powers `endgame_score_p_value`; D-05 mandates reuse. **But see "Critical methodology note" below for the tricky bit.** |
| `app.services.score_confidence.wilson_bounds` | live | 95% Wilson CI bounds on `(p, n)` | Used by Phase 81 to compute `entry_eval_ci_low/high_pawns` analog. |
| `MiniBulletChart` | `frontend/src/components/charts/MiniBulletChart.tsx` | Bullet chart with neutral band + CI whiskers | Existing component; same axis (W+0.5D, ±0.25 around 0.5). |
| `MiniWDLBar` | `frontend/src/components/stats/MiniWDLBar.tsx` | 3-segment WDL bar with theme colors | Already exported; signature: `{ win_pct, draw_pct, loss_pct, heightClass? }`. |
| `ScoreConfidencePopover` | `frontend/src/components/insights/ScoreConfidencePopover.tsx` | Popover with level + p_value + score + gameCount | Already used by Tile 2 for `endgame_score`. Reuse for "Achievable score" with the new D-10 copy. |
| `app.services.endgame_zones.ZoneSpec` + `assign_zone` | live | Registry-driven zone classification | Phase 82 D-08 pattern — new `ENTRY_EXPECTED_SCORE_ZONES` registers same way. |
| `scripts/gen_endgame_zones_ts.py` | live | Regenerate frontend zone helpers from Python registry | CI enforces non-drift. |
| Lichess winning-chances sigmoid | math doc | `1 / (1 + e^(-0.00368208 * cp))` | Industry-standard mapping from centipawn eval to 0–1 winning probability, fitted on 2300+ rapid games. [CITED: Lichess accuracy docs] |

### Supporting

| Library | Version | Purpose | When to Use |
|---|---|---|---|
| `math.exp` / `math.log` | stdlib | Sigmoid math | One-liner inside `eval_cp_to_expected_score`. |
| `pytest` 8.x | locked in pyproject.toml | Unit + integration tests | `tests/services/test_eval_utils.py` mirrors `test_eval_confidence.py` shape. |
| `@testing-library/react` | locked in package.json | RTL component tests | Extend `EndgameStartVsEndSection.test.tsx` (currently 379 lines, 16 test cases). |
| `vitest` | locked | Frontend test runner | jsdom environment for RTL. |
| `@testing-library/jest-dom` | locked | DOM matchers | Existing tests already use `screen.getByTestId`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| Lichess sigmoid (`K = 0.00368208`) | Stockfish native `get_wdl_stats()` | Stockfish WDL is more material-aware but requires re-evaluating positions at runtime; we store `eval_cp` from prior backfills. Lichess curve is the standard historical-cp mapping. SEED-014 captured this design decision. **REJECTED** by D-02. |
| Paired sig test (achievable vs achieved) | Two independent Wilson CIs | Paired test is more statistically precise. **REJECTED** by D-22 — visual juxtaposition (two bullet charts) is the actual UX goal; UX value of a single sentence is marginal. |
| Per-eval-bin breakdown | Per-game aggregate | More diagnostic ("you score below baseline specifically at +1.0…+2.0"). **DEFERRED** — too large a UI lift, inconsistent with bullet idiom. |

**No installation needed** — every dependency already exists in the project. New module is `app/services/eval_utils.py` (pure stdlib only).

**Version verification:** All confidence-helper, schema, and registry surfaces verified live in `app/services/score_confidence.py`, `app/schemas/endgames.py`, `app/services/endgame_zones.py` on 2026-05-11. No npm/pypi version checks needed (no new dependencies).

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Plan 1: app/services/eval_utils.py (NEW)                                │
│  ──────────────────────────────────────────                              │
│  LICHESS_K = 0.00368208                                                  │
│  eval_cp_to_expected_score(eval_cp, user_color) -> float                 │
│  eval_mate_to_expected_score(eval_mate, user_color) -> float             │
└──────────────────────────────────────────────────────────────────────────┘
                              │ (pure function)
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Plan 2: backend aggregator (existing file extensions)                   │
│  ─────────────────────────────────────────────────────                   │
│                                                                          │
│  endgame_repository.py:793-841 ── (existing) ──>  bucket_rows            │
│      one row per game: (eval_cp, eval_mate, user_color, ...)             │
│                                                                          │
│  endgame_service.py:1645-1732                                            │
│      _get_endgame_performance_from_rows                                  │
│        ┌─ EXISTING entry-eval aggregator (1680-1712)                     │
│        │     eval_sum, eval_sumsq, eval_n over signed cp                 │
│        │     -> entry_eval_mean_pawns, entry_eval_p_value, CI            │
│        └─ NEW expected-score aggregator                                  │
│              For each bucket row:                                        │
│                if eval_mate is not None:                                 │
│                  ex = eval_mate_to_expected_score(...)                   │
│                  if ex == 1.0: ex_wins += 1                              │
│                  elif ex == 0.0: ex_losses += 1                          │
│                elif eval_cp is not None and |eval_cp| < 2000:            │
│                  ex = eval_cp_to_expected_score(eval_cp, user_color)     │
│                  ex_sum += ex; ex_n += 1                                 │
│                                                                          │
│              For Wilson sig test vs 50% on a FLOAT mean (not (W,D,L)):   │
│                see "Critical methodology note" below                     │
│                                                                          │
│              -> entry_expected_score, entry_expected_score_n,            │
│                 _p_value, _ci_low, _ci_high                              │
└──────────────────────────────────────────────────────────────────────────┘
                              │ (Pydantic v2)
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  app/schemas/endgames.py:107-140 (extend)                                │
│  ────────────────────────────────────────                                │
│  class EndgamePerformanceResponse:                                       │
│    ... existing 7 fields ...                                             │
│    entry_expected_score: float = 0.0                                     │
│    entry_expected_score_n: int = 0                                       │
│    entry_expected_score_p_value: float | None = None                     │
│    entry_expected_score_ci_low: float | None = None                      │
│    entry_expected_score_ci_high: float | None = None                     │
└──────────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌────────────────────────────┐    ┌─────────────────────────────────────┐
│  Plan 3: UI restructure    │    │  Plan 5: LLM payload extension       │
│  ─────────────────────     │    │  ──────────────────────────         │
│  EndgameStartVsEndSection  │    │  insights_service.py:443-502        │
│    (2×2 grid)              │    │   _findings_endgame_start_vs_end    │
│                            │    │   extend from 2 → 3 findings        │
│  Tile 1: "Where you start" │    │                                      │
│   ┌──────────────────────┐ │    │  endgame_zones.py:30-53             │
│   │ Endgame entry eval   │ │    │   MetricId Literal += "entry_       │
│   │ (existing bullet)    │ │    │     expected_score"                  │
│   ├──────────────────────┤ │    │   ZONE_REGISTRY +=                  │
│   │ Achievable score NEW │ │    │     ENTRY_EXPECTED_SCORE_ZONES      │
│   │ (new bullet)         │ │    │                                      │
│   └──────────────────────┘ │    │  endgame_insights.md                │
│                            │    │   glossary entry "entry_expected_   │
│  Tile 2: "What you do      │    │     score"                           │
│           with it"         │    │   subsection block extended         │
│   ┌──────────────────────┐ │    │                                      │
│   │ Win/Draw/Loss NEW    │ │    │  insights_llm.py:66                 │
│   │ (lifted MiniWDLBar)  │ │    │   _PROMPT_VERSION = "endgame_v25"   │
│   ├──────────────────────┤ │    │                                      │
│   │ Endgame score        │ │    └──────────────────────────────────────┘
│   │ (existing bullet)    │ │
│   └──────────────────────┘ │
└────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Plan 4: Benchmark calibration (offline operator skill)                  │
│  ─────────────────────────────────────────────────────                  │
│  /benchmarks SKILL extension:                                            │
│    extend .claude/skills/benchmarks/SKILL.md "Section 3"-style block     │
│    with entry_expected_score per-(user, color) distribution              │
│    canonical CTE pattern (lichess_username join, status='completed',     │
│    equal-footing, sparse-cell exclusion)                                 │
│                                                                          │
│  Output: reports/benchmarks-YYYY-MM-DD.md with new section               │
│       -> ENTRY_EXPECTED_SCORE_ZONES bands locked in endgame_zones.py    │
│       -> uv run python scripts/gen_endgame_zones_ts.py                  │
│       -> frontend/src/generated/endgameZones.ts updates                  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Critical Methodology Note — Wilson Test on a Float Mean

**This is the single most important research finding for Plan 2.**

D-05 says "use the project's existing Wilson chess-score util, tested against 50%, exactly mirroring `endgame_score_p_value` plumbing." But there's a subtlety: `compute_confidence_bucket(w, d, losses, n)` expects an **integer** (W, D, L, N) tuple and computes the score internally as `(W + 0.5·D) / N`. The expected-score metric is the **mean of N floats in [0, 1]**, not a count of {0, 0.5, 1} outcomes.

Two paths exist for sig-testing a float mean vs 0.5:

**Path A — fabricate an equivalent (W, D, L, N) triple.** Map each per-game expected score `x ∈ [0, 1]` to `(w_x, d_x, l_x)` such that `w_x + 0.5·d_x = x`. The natural choice is `w_x = x`, `d_x = 0`, `l_x = 1 - x` (i.e. treat each game as contributing `x` to wins and `1-x` to losses, no draws). Then sum across games:
- `W_total = Σ x_i` (float)
- `D_total = 0`
- `L_total = Σ (1 - x_i)`
- `N = ex_n` (integer)
- `score = W_total / N = mean_x` ✓

The catch: `compute_confidence_bucket` signature is `tuple[int, int, int, int]`. Passing floats will fail ty checks. **The cleanest implementation** is to inline the Wilson computation rather than call `compute_confidence_bucket` directly — but D-05 says "do not introduce parallel statistical machinery." The reconciliation: factor the Wilson math in `score_confidence.py` into a shared helper that accepts `(score: float, n: int)` and have both the existing integer-tuple caller and the new float-mean caller route through it. The Wilson null-test depends only on `score` and `n` (line 141-143 of `score_confidence.py`: `se_null = sqrt(0.5*0.5/n); z = (score - 0.5)/se_null; p = erfc(|z|/sqrt(2))`).

**Path B — narrate the metric as "mean of x ∈ [0,1] values" and use a different test (Welch t-test vs 0.5).** This is what Phase 81 did for `entry_eval_p_value` — Wald-z one-sample test of mean vs 0 cp (`compute_eval_confidence_bucket` in `eval_confidence.py`). The expected-score metric is structurally similar: a per-user mean over per-game continuous values. The argument against: D-05 explicitly says "Wilson chess-score util" and "exactly mirroring the existing `endgame_score_p_value` plumbing."

**Recommended approach (HIGH confidence, but flag to user for review):** Path A — refactor `score_confidence.py` to expose a new internal helper `wilson_score_test(score: float, n: int) -> tuple[float, float]` returning `(p_value, se_null)`, used by both `compute_confidence_bucket` (existing) and a new `compute_score_confidence_bucket_from_float(score: float, n: int)` (new). The user expressed preference for honoring memory `feedback_wilson_chess_score.md` ("use project's existing Wilson-based util; don't editorialize methodology") which Path A honors literally — the underlying test math is identical to `endgame_score_p_value`'s test math; only the score-input mechanism differs.

The planner should explicitly call out this refactor in Plan 2's task list (it's not zero-effort) and flag it as the methodology decision the user should sanity-check during Plan 2 review. Alternative framing for the planner: "Plan 2 includes a small refactor in `score_confidence.py` to factor the Wilson-test-vs-0.5 math into a shared helper that accepts either a `(W, D, L, N)` tuple or a `(mean, N)` pair."

[VERIFIED: read of `app/services/score_confidence.py:87-162` confirms the test math depends only on `(score, n)`, not on the integer (W, D, L) breakdown.]

### Recommended Project Structure

```
app/services/
├── eval_utils.py             # NEW: Plan 1 — Lichess sigmoid + mate→0/1
├── endgame_service.py        # MODIFY: Plan 2 — aggregator extension
├── score_confidence.py       # MODIFY: Plan 2 — factor Wilson math (see methodology note)
├── endgame_zones.py          # MODIFY: Plan 4 — MetricId += "entry_expected_score" + ZoneSpec
├── insights_service.py       # MODIFY: Plan 5 — extend finding emitter 2 → 3 findings
└── insights_llm.py           # MODIFY: Plan 5 — _PROMPT_VERSION = "endgame_v25"

app/repositories/
└── endgame_repository.py     # NO CHANGE (SQL already returns eval_cp + eval_mate)

app/schemas/
└── endgames.py               # MODIFY: Plan 2 — 5 new fields on EndgamePerformanceResponse

app/prompts/
└── endgame_insights.md       # MODIFY: Plan 5 — glossary + subsection extensions

scripts/
└── gen_endgame_zones_ts.py   # RUN (Plan 4): regenerate ts after zone registry update

frontend/src/components/charts/
├── EndgameStartVsEndSection.tsx        # MODIFY: Plan 3 — 2×2 grid restructure
└── EndgamePerformanceSection.tsx       # NO CHANGE (the "Games with vs without" table)

frontend/src/components/stats/
└── MiniWDLBar.tsx            # NO CHANGE — already exported, lift import

frontend/src/lib/
├── endgameEntryEvalZones.ts            # NO CHANGE
├── scoreBulletConfig.ts                # NO CHANGE
└── theme.ts                            # NO CHANGE

frontend/src/generated/
└── endgameZones.ts           # REGENERATE: Plan 4 — auto-gen output

tests/services/
├── test_eval_utils.py        # NEW: Plan 1 — unit tests
├── test_score_confidence.py  # MODIFY: Plan 2 — add tests for refactored helper
└── test_insights_service.py  # MODIFY: Plan 5 — extend _findings_endgame_start_vs_end tests

tests/
├── test_endgame_service.py   # MODIFY: Plan 2 — integration tests for new aggregator
└── test_endgames_router.py   # MODIFY (optional): Plan 2 — wire-format assertion

frontend/src/components/charts/__tests__/
└── EndgameStartVsEndSection.test.tsx   # MODIFY: Plan 3 — extend 16 → ~22 test cases

frontend/src/pages/__tests__/
└── Endgames.startVsEnd.test.tsx        # MODIFY: Plan 3 — page-integration tests
```

### Pattern 1: Sign Convention for User-Perspective Eval (Plan 1 must mirror exactly)

Source: `app/services/endgame_service.py:169-213` (`_classify_endgame_bucket`).

```python
# Verified: app/services/endgame_service.py:195-204
sign = 1 if user_color == "white" else -1

if eval_mate is not None:
    # Mate score: a positive value means the side that is to-move has mate,
    # but the raw white-perspective convention treats eval_mate > 0 as white winning.
    user_eval: int = sign * (1_000_000 if eval_mate > 0 else -1_000_000)
elif eval_cp is not None:
    user_eval = sign * eval_cp
```

**Implication for Plan 1 (`eval_utils.py`):**
- `eval_cp_to_expected_score`: sign flip `signed_cp = (1 if user_color == "white" else -1) * eval_cp`, then `1 / (1 + math.exp(-LICHESS_K * signed_cp))`.
- `eval_mate_to_expected_score`: user is the side mating iff `(eval_mate > 0 and user_color == "white") or (eval_mate < 0 and user_color == "black")`. Return `1.0` in that case, else `0.0`.

### Pattern 2: Per-Game Aggregation over `bucket_rows` (Plan 2 mirrors lines 1680-1693)

Source: `app/services/endgame_service.py:1680-1693`.

```python
# VERIFIED PATTERN — existing entry-eval aggregator
for row in bucket_rows:
    if row.eval_mate is not None:    # ty: ignore[unresolved-attribute]
        continue                      # mate-EXCLUDED per Phase 81 D-07
    if row.eval_cp is None:           # ty: ignore[unresolved-attribute]
        continue                      # NULL eval excluded
    sign = 1 if row.user_color == "white" else -1
    signed_cp = float(sign * row.eval_cp)
    eval_sum += signed_cp
    eval_sumsq += signed_cp * signed_cp
    eval_n += 1
```

**Plan 2 expected-score aggregator (next to entry-eval one, same loop or sibling loop):**

```python
# NEW: Plan 2 — per Phase 83 D-04, D-06, D-07
from app.services.eval_utils import (
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)

EVAL_CLIP_MAX_CP = 2000  # D-07 — Phase 82 parity (named constant, no magic number)

ex_sum = 0.0
ex_n = 0
for row in bucket_rows:
    if row.eval_mate is not None:    # D-06 — mate INCLUDED here (unlike entry-eval)
        ex = eval_mate_to_expected_score(row.eval_mate, row.user_color)
        ex_sum += ex
        ex_n += 1
    elif row.eval_cp is not None:
        if abs(row.eval_cp) >= EVAL_CLIP_MAX_CP:  # D-07
            continue
        ex = eval_cp_to_expected_score(row.eval_cp, row.user_color)
        ex_sum += ex
        ex_n += 1
    # both NULL → skip per D-06 cohort filter
```

### Pattern 3: Empty Finding via `_empty_finding` helper (Plan 5)

Source: `app/services/insights_service.py:443-502` (existing `_findings_endgame_start_vs_end`).

```python
# VERIFIED — extend to 3 findings
def _findings_endgame_start_vs_end(response, window):
    perf = response.performance

    # Tile 1 — entry eval (EXISTING)
    n_eval = perf.entry_eval_n
    if n_eval < 10:
        tile1 = _empty_finding("endgame_start_vs_end", window, "entry_eval_pawns")
    else:
        ...

    # Tile 2 — endgame score vs 50% (EXISTING)
    total = perf.endgame_wdl.total
    if total < 10:
        tile2 = _empty_finding("endgame_start_vs_end", window, "endgame_score")
    else:
        ...

    # Tile 3 — entry expected score vs 50% (NEW, Plan 5)
    n_ex = perf.entry_expected_score_n
    if n_ex < 10:
        tile3 = _empty_finding("endgame_start_vs_end", window, "entry_expected_score")
    else:
        ex = perf.entry_expected_score
        ex_quality = sample_quality("endgame_start_vs_end", n_ex)
        tile3 = SubsectionFinding(
            subsection_id="endgame_start_vs_end",
            parent_subsection_id=None,
            window=window,
            metric="entry_expected_score",
            value=ex,
            zone=assign_zone("entry_expected_score", ex),
            trend="n_a",
            weekly_points_in_window=0,
            sample_size=n_ex,
            sample_quality=ex_quality,
            is_headline_eligible=ex_quality != "thin",
            dimension=None,
        )

    return [tile1, tile2, tile3]
```

### Pattern 4: 2×2 Grid Tile Layout (Plan 3)

Each tile's existing single `<div class="grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">` (single row of label-row + chart) wraps into a two-row vertical stack:

```jsx
<div className="charcoal-texture rounded-md p-4" data-testid="tile-entry-eval">
  <h3 className="text-base font-semibold mb-2">Where you start</h3>
  <div className="flex flex-col gap-4">  {/* NEW: 2-row stack inside the tile */}
    {/* Row 1 — Endgame entry eval (existing label-row + bullet) */}
    <div className="grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
      ... existing entry-eval markup ...
    </div>
    {/* Row 2 — Achievable score (NEW) */}
    <div className="grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
      <span>Achievable score: ...</span>
      <ScoreConfidencePopover ... />
      <MiniBulletChart value={data.entry_expected_score}
                       center={SCORE_BULLET_CENTER}
                       neutralMin={ENTRY_EXPECTED_SCORE_NEUTRAL_MIN}
                       neutralMax={ENTRY_EXPECTED_SCORE_NEUTRAL_MAX}
                       domain={scoreBulletDomain()}
                       ... />
    </div>
  </div>
</div>
```

The outer `lg:grid-cols-2` (two tiles side-by-side) stays unchanged. Mobile collapse: vertical stack inside each tile preserves the top-row-first order (D-12).

### Anti-Patterns to Avoid

- **Embedding `0.00368208` as a magic number anywhere outside `eval_utils.py`** — extract as `LICHESS_K`; CLAUDE.md "No magic numbers" rule applies.
- **Re-implementing the sigmoid inline** — every call site goes through `eval_cp_to_expected_score()`. If a future caller needs the sigmoid output for a different sign convention, add a `user_color` arg variant rather than copying the math.
- **Routing mate through the sigmoid** — a mate-in-3 with `|eval_cp| ≈ 2900` would map to ~0.999, not 1.0. D-02 explicit: mate has its own helper.
- **Hand-coding zone thresholds on the frontend** — every zone band lives in `endgame_zones.py` and flows to `endgameZones.ts` via the codegen script. CI fails on drift.
- **Computing `entry_expected_score_p_value` independently of the project Wilson util** — D-05 explicit. The methodology refactor (factor Wilson into a `(score, n)` helper) is the right path; do not introduce a parallel SciPy-based test.
- **Reimplementing `MiniWDLBar`** — D-13 explicit: lift import from `@/components/stats/MiniWDLBar`. (CONTEXT.md said "import from `EndgamePerformanceSection.tsx`" — that's where it's *imported* but not where it's *defined*. The actual import path is `@/components/stats/MiniWDLBar`.)
- **Pairing two CIs into a single sentence** — D-22 explicit: visual juxtaposition is the UX, no `gap_p_value` in the schema.
- **Saying "underperformance" in user-facing copy** — D-10 explicit. Use "Achievable" / "gap" / "ceiling for sub-2300 play".

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Wilson score test vs 50% | New SciPy `binomtest` call | `compute_confidence_bucket` (refactored to accept float means via factored helper — see methodology note) | D-05 mandate; existing test math is correct and gated on N≥10. |
| Wilson 95% CI bounds | Hand-derived formula | `wilson_bounds(score, n)` in `score_confidence.py:57-84` | Already used by Phase 81 for entry-eval CIs; well-tested. |
| Lichess sigmoid | Inline `math.exp` | New `eval_cp_to_expected_score` in `eval_utils.py` | One source of truth; sign convention bug-prone (Phase 82 had the exact same trap). |
| Mate handling | Routing mate through sigmoid | New `eval_mate_to_expected_score` helper | Mate must map directly to 0/1, not 0.999. |
| Zone classification | Inline `if value >= threshold` | `assign_zone(metric_id, value)` | Registry-driven; CI gates frontend/backend agreement. |
| Per-tile color logic | New `isInColoredZone && isConfident` ternary | Lift the existing `evalShowZoneFontColor` / `scoreShowZoneFontColor` pattern from `EndgameStartVsEndSection.tsx:71-92` | Phase 82 D-12 rule already implemented for two tiles — the third bullet reuses it verbatim. |
| WDL bar | New component | `MiniWDLBar` from `@/components/stats/MiniWDLBar` | D-13 mandate; already used in `EndgamePerformanceSection`. |
| Popover for the new bullet | New popover component | `ScoreConfidencePopover` | Same shape (score + level + p_value + gameCount); only the popover body copy changes (D-10). |
| Benchmark CTE | Hand-written SQL | Canonical CTE in `.claude/skills/benchmarks/SKILL.md` "Standard CTE — `selected_users`" | Plan 4 must use `lichess_username` join + `bic.status='completed'` + equal-footing — every other CTE has been bitten by these (memory: `project_benchmark_outliers_unfiltered.md`). |

**Key insight:** Every primitive Phase 83 needs already exists in this codebase. The phase is plumbing + framing, not new infrastructure. The single nontrivial methodology question — Wilson test on a float mean — has a clean refactor path (factor existing math into a shared helper). Everything else is "extend the pattern Phase 81/82 established."

## Runtime State Inventory

Phase 83 has no rename / refactor / migration semantics. It is purely additive:

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | None — no schema migration, no data backfill. New fields default-empty on response. | None |
| Live service config | None — no service config touched. | None |
| OS-registered state | None. | None |
| Secrets/env vars | None. | None |
| Build artifacts | `frontend/src/generated/endgameZones.ts` regenerates from `endgame_zones.py`. Commit the regenerated file. CI fails on drift. | Plan 4: `uv run python scripts/gen_endgame_zones_ts.py && git add frontend/src/generated/endgameZones.ts` |

**Cache invalidation:** `_PROMPT_VERSION` bump (`endgame_v24` → `endgame_v25`) automatically invalidates any LLM response cached against `endgame_v24` keys. Findings-hash changes when a new metric is emitted, also invalidating cache. Both are automatic — no manual cache flush.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.13 + uv | All plans | ✓ (project env) | locked | — |
| PostgreSQL 18 dev DB | Plan 2 integration tests | ✓ (Docker) | 18 | `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| PostgreSQL 18 benchmark DB | Plan 4 calibration | ✓ (Docker) | 18 | `bin/benchmark_db.sh start` |
| Node 20 + npm | Plan 3 frontend tests | ✓ (project env) | locked | — |
| Stockfish backfilled `eval_cp` on prod | Plan 2 manual UAT | ✓ as of v1.15 cutover (PR #78) | n/a | — |
| Benchmark DB ingest (`bic.status='completed'`) | Plan 4 CTE filter | ✓ — same dataset Phase 82 used | 2026-03 dump | — |
| Lichess sigmoid math reference | Plan 1 docstring | ✓ — public domain | n/a | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Common Pitfalls

### Pitfall 1: Sign-flip bug in mate handling

**What goes wrong:** Mate-for-user returns 0.0 instead of 1.0 (or vice versa).
**Why it happens:** `eval_mate` is white-perspective; mate-positive means white has mate. For a black user, a positive `eval_mate` means *the opponent has mate against the user* — expected score should be 0.0, not 1.0.
**How to avoid:** `eval_mate_to_expected_score(eval_mate, user_color)` returns `1.0` iff `(eval_mate > 0 and user_color == "white") or (eval_mate < 0 and user_color == "black")`. Cover both colors explicitly in unit tests.
**Warning signs:** Test cases asserting `eval_mate_to_expected_score(+5, "black") == 0.0` and `eval_mate_to_expected_score(-5, "white") == 0.0`. If either flips, the sign convention is wrong.

### Pitfall 2: Wilson on float mean rejected by ty

**What goes wrong:** `compute_confidence_bucket(W, D, L, N)` expects `tuple[int, int, int, int]`. Passing `(ex_sum, 0, ex_n - ex_sum, ex_n)` with `ex_sum: float` fails ty.
**Why it happens:** The existing util's signature predates this use case.
**How to avoid:** Factor the Wilson-vs-0.5 math into a private `_wilson_score_test(score: float, n: int) -> tuple[float, float]` returning `(p_value, se_null)`. Both `compute_confidence_bucket` and the new `compute_score_confidence_from_mean(score, n)` call it.
**Warning signs:** A ty error `Type "float" is not assignable to parameter "w" of type "int"` in `_get_endgame_performance_from_rows`. Don't suppress with `# ty: ignore` — refactor instead.

### Pitfall 3: NULL eval cohort drift

**What goes wrong:** `entry_expected_score_n != entry_eval_n` on the same user, looking like a bug.
**Why it happens:** D-06 includes mate games in the expected-score cohort; D-07 of Phase 81 (mirrored in the existing aggregator) excludes them. By construction `entry_expected_score_n >= entry_eval_n`.
**How to avoid:** Document the divergence in the schema docstring on `entry_expected_score_n`. Add an integration test that asserts `entry_expected_score_n == entry_eval_n + mate_game_count` on a fixture with known mate distribution.
**Warning signs:** User reports "Endgame entry eval shows N=145, Achievable score shows N=152" and worries about a bug. Document the 7-mate-game difference in the popover or accordion. (May be worth flagging to user; CONTEXT.md does not pin a UI affordance for this.)

### Pitfall 4: Sigmoid saturation hiding mate signal

**What goes wrong:** A position with `eval_cp = +1900` maps to `expected_score ≈ 0.999`, hiding the qualitative difference from a mate (`expected_score = 1.0`).
**Why it happens:** Sigmoid is asymptotic; large `|eval_cp|` saturates near 0/1 long before mate magnitude.
**How to avoid:** D-07's `|eval_cp| < 2000` clip excludes the tail. Mate is routed through the separate mate helper (D-02). Sigmoid never sees `|eval_cp| > 2000` post-clip.
**Warning signs:** Unit test `eval_cp_to_expected_score(2500, "white")` returning something — this should never happen because the aggregator clips before calling the helper. The helper itself should NOT clip (single responsibility); the aggregator does.

### Pitfall 5: Frontend zone helper drift

**What goes wrong:** New `ENTRY_EXPECTED_SCORE_ZONES` lands in `endgame_zones.py` but `frontend/src/generated/endgameZones.ts` is not regenerated; CI fails.
**Why it happens:** `gen_endgame_zones_ts.py` is a hand-run script — easy to forget after editing the registry.
**How to avoid:** Plan 4's last task: `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` should be a no-op after staging the regenerated file. Commit both the Python and TS changes in the same commit.
**Warning signs:** CI error `frontend/src/generated/endgameZones.ts differs from generator output`.

### Pitfall 6: WDL duplication confusing users

**What goes wrong:** The lifted `MiniWDLBar` in "What you do with it" shows the same data as the endgame row in the "Games with vs without Endgame" table below.
**Why it happens:** D-08 accepts this redundancy by design (rejected: restructure the table to lift the endgame row out — would break the table's endgame-vs-non-endgame comparison). User-facing visual duplication is intentional and reviewed.
**How to avoid:** No code fix needed. If a UAT reviewer flags it, refer to D-08 — accepted.
**Warning signs:** PR review comments like "isn't this the same data as the table?" Yes. By design. Phase 83 D-08.

### Pitfall 7: LLM narrating with "underperformance" framing

**What goes wrong:** The LLM picks up on "below the achievable score" and writes "You're underperforming the Stockfish baseline by 11 points."
**Why it happens:** Without explicit framing guidance, the LLM defaults to the most common interpretation of a gap.
**How to avoid:** D-10 + D-18 framing must be explicit in the prompt: "The Lichess curve is fitted on 2300+ rapid games — scoring below this baseline from positive evals is normal at lower ratings and is not a flaw." Include this caveat in BOTH the glossary entry and the subsection block. Add it to the list of forbidden words / phrases in the prompt's "Within-noise" / "Tone" sections.
**Warning signs:** During Plan 5 UAT, the LLM output contains the words "underperform", "underperformance", "fall short", "missing the mark", "below your potential". Tighten prompt text.

### Pitfall 8: Mobile collapse breaks the 2×2 affordance

**What goes wrong:** On mobile, the four sub-rows stack in DOM order — but if the order is (tile1 row1, tile1 row2, tile2 row1, tile2 row2), the user reads (eval, achievable, WDL, achieved) which is correct chronologically but breaks the "bottom-row comparison" affordance because the two score bullets are not adjacent.
**Why it happens:** Tile-level mobile collapse comes from the outer `lg:grid-cols-2` → `grid-cols-1` switch. The 2×2 affordance is desktop-only.
**How to avoid:** Accept the desktop-only affordance. Mobile users get four stacked rows in chronological order (D-12: "Mobile stacking: top-row first, bottom-row second"). The popover on the achievable bullet (D-10) explicitly tells mobile users "Compare against your achieved Endgame score on the right" — but on mobile that wording is wrong. Either reword to "Compare against your achieved Endgame score below" (works on both) or leave as-is and accept minor desktop bias.
**Warning signs:** Mobile UAT shows the popover text references "on the right" but the achieved score is below.

## Code Examples

Verified patterns from this codebase.

### Sigmoid math (Plan 1 reference)

```python
# NEW: app/services/eval_utils.py
"""Lichess winning-chances sigmoid — Stockfish eval to expected score in [0, 1].

Source: Lichess accuracy / winning-chances documentation.
Scaling constant K = 0.00368208 (fitted on 2300+ rapid games).
"""
import math
from typing import Literal

# Lichess accuracy / winning-chances sigmoid scale.
# Source: Lichess accuracy documentation.
# Maps centipawn eval to winning chance in (0, 1):
#   expected_score = 1 / (1 + exp(-K * cp))
LICHESS_K: float = 0.00368208


def eval_cp_to_expected_score(
    eval_cp: int,
    user_color: Literal["white", "black"],
) -> float:
    """Convert white-perspective centipawn eval to user-perspective expected score.

    Domain: signed integer centipawns (white-perspective as stored in
    GamePosition.eval_cp). Range: open interval (0, 1), centered at 0.5
    when user_eval_cp = 0.

    Sign convention mirrors `_classify_endgame_bucket` in
    app/services/endgame_service.py:169-213.
    """
    sign = 1 if user_color == "white" else -1
    user_eval_cp = sign * eval_cp
    return 1.0 / (1.0 + math.exp(-LICHESS_K * user_eval_cp))


def eval_mate_to_expected_score(
    eval_mate: int,
    user_color: Literal["white", "black"],
) -> float:
    """Map forced-mate score to expected score 0.0 or 1.0.

    Mate is NOT routed through the sigmoid — a mate-in-3 with |eval_cp| ≈ 2900
    would map to ~0.999 via sigmoid, masking the qualitative certainty.

    Sign convention mirrors `_classify_endgame_bucket`: positive eval_mate
    means white has a forced mate; negative means black has one.
    """
    user_is_mating = (eval_mate > 0 and user_color == "white") or (
        eval_mate < 0 and user_color == "black"
    )
    return 1.0 if user_is_mating else 0.0
```

### Unit test scaffolding (Plan 1)

```python
# NEW: tests/services/test_eval_utils.py
"""Unit tests for app/services/eval_utils.py.

D-03: cover sigmoid centred at 0.5 (eval_cp=0), sign convention for both
colors, saturation at large evals, mate-for-user → 1.0, mate-against-user → 0.0.
"""
import math
import pytest

from app.services.eval_utils import (
    LICHESS_K,
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)


class TestSigmoid:
    def test_centered_at_zero(self):
        """eval_cp=0 → 0.5 for both colors."""
        assert eval_cp_to_expected_score(0, "white") == pytest.approx(0.5, abs=1e-9)
        assert eval_cp_to_expected_score(0, "black") == pytest.approx(0.5, abs=1e-9)

    def test_sign_convention_white(self):
        """+100 cp white-perspective is +100 for white user → ≈0.591."""
        # Expected: 1/(1+exp(-0.00368208 * 100)) = 0.5910...
        expected = 1.0 / (1.0 + math.exp(-LICHESS_K * 100))
        assert eval_cp_to_expected_score(100, "white") == pytest.approx(expected)
        assert eval_cp_to_expected_score(100, "white") > 0.5

    def test_sign_convention_black(self):
        """+100 cp white-perspective is -100 for black user → ≈0.409."""
        expected = 1.0 / (1.0 + math.exp(LICHESS_K * 100))
        assert eval_cp_to_expected_score(100, "black") == pytest.approx(expected)
        assert eval_cp_to_expected_score(100, "black") < 0.5
        # Symmetry: white_user(+100) + black_user(+100) == 1.0
        assert (
            eval_cp_to_expected_score(100, "white")
            + eval_cp_to_expected_score(100, "black")
            == pytest.approx(1.0)
        )

    def test_saturation_high(self):
        """+1500 cp saturates near 1.0 for white user."""
        assert eval_cp_to_expected_score(1500, "white") > 0.99
        assert eval_cp_to_expected_score(1500, "white") < 1.0

    def test_saturation_low(self):
        """-1500 cp saturates near 0.0 for white user."""
        assert eval_cp_to_expected_score(-1500, "white") < 0.01
        assert eval_cp_to_expected_score(-1500, "white") > 0.0


class TestMate:
    def test_mate_for_white_user(self):
        """Positive eval_mate, white user → 1.0 (user is mating)."""
        assert eval_mate_to_expected_score(5, "white") == 1.0
        assert eval_mate_to_expected_score(1, "white") == 1.0

    def test_mate_against_white_user(self):
        """Negative eval_mate, white user → 0.0 (user is mated)."""
        assert eval_mate_to_expected_score(-5, "white") == 0.0

    def test_mate_for_black_user(self):
        """Negative eval_mate, black user → 1.0 (user is mating)."""
        assert eval_mate_to_expected_score(-3, "black") == 1.0

    def test_mate_against_black_user(self):
        """Positive eval_mate, black user → 0.0 (user is mated)."""
        assert eval_mate_to_expected_score(3, "black") == 0.0
```

### Wilson refactor (Plan 2 reference — see methodology note)

```python
# MODIFY: app/services/score_confidence.py
# Factor out the Wilson-vs-0.5 math so it accepts either (W, D, L, N)
# or (score, N). Backward compat: compute_confidence_bucket signature unchanged.

def _wilson_score_test_vs_half(score: float, n: int) -> tuple[float, float]:
    """Return (p_value, se_null) for Wilson score-test of H0: score == 0.5.

    Pure math — no bucketing, no edge-case clamp. Callers gate on n < 1.
    """
    se_null = math.sqrt(SCORE_PIVOT * (1.0 - SCORE_PIVOT) / n)
    z = (score - SCORE_PIVOT) / se_null
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return p_value, se_null


def compute_score_confidence_from_mean(
    score: float, n: int
) -> tuple[Literal["low", "medium", "high"], float, float]:
    """Return (confidence_bucket, p_value, _se) for a (mean_score, N) pair.

    Used when the per-game score is a float in [0, 1] (not a {0, 0.5, 1}
    outcome). Mirrors compute_confidence_bucket's gating: n < 10 → low.
    """
    if n <= 0:
        return "low", 1.0, 0.0
    p_value, _se_null = _wilson_score_test_vs_half(score, n)
    if n < CONFIDENCE_MIN_N:
        return "low", p_value, 0.0
    if p_value < CONFIDENCE_HIGH_MAX_P:
        return "high", p_value, 0.0
    if p_value < CONFIDENCE_MEDIUM_MAX_P:
        return "medium", p_value, 0.0
    return "low", p_value, 0.0
```

The existing `compute_confidence_bucket` would also internally call `_wilson_score_test_vs_half` after computing `score = (W + 0.5*D) / N`, so the math is single-sourced.

### Frontend tile interior 2-row stack (Plan 3 reference)

The full restructured `EndgameStartVsEndSection.tsx` is large; the new "Achievable score" row inside Tile 1 follows the existing pattern at lines 114-150:

```tsx
{/* Row 2 of Tile 1 — Achievable score (NEW) */}
{showAchievableChart ? (
  <div className="grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
    <span className="flex items-center gap-1 text-sm tabular-nums w-full">
      <span className="text-muted-foreground">Achievable score:</span>
      <span
        className="ml-auto font-semibold"
        style={achievableColor ? { color: achievableColor } : undefined}
        data-testid="achievable-score-value"
      >
        {`${(data.entry_expected_score * 100).toFixed(1)}%`}
      </span>
      <ScoreConfidencePopover
        level={achievableLevel}
        pValue={data.entry_expected_score_p_value ?? 1}
        score={data.entry_expected_score}
        gameCount={data.entry_expected_score_n}
        testId="achievable-score-popover-trigger"
        // Body copy override for D-10 framing — popover currently shows
        // generic "Wilson test vs 50%"; planner: add an optional `bodyCopy`
        // prop to ScoreConfidencePopover or create a thin wrapper.
      />
    </span>
    <div className="min-w-0 tabular-nums">
      <MiniBulletChart
        value={data.entry_expected_score}
        center={SCORE_BULLET_CENTER}
        neutralMin={ENTRY_EXPECTED_SCORE_NEUTRAL_MIN}
        neutralMax={ENTRY_EXPECTED_SCORE_NEUTRAL_MAX}
        domain={scoreBulletDomain()}
        ciLow={clampScoreCi(data.entry_expected_score_ci_low ?? 0)}
        ciHigh={clampScoreCi(data.entry_expected_score_ci_high ?? 1)}
        barColor="neutral"
        ariaLabel={`Achievable score: ${(data.entry_expected_score * 100).toFixed(1)}%`}
      />
    </div>
  </div>
) : (
  <p className="text-sm text-muted-foreground py-2">Not enough data yet</p>
)}
```

Note: The existing `ScoreConfidencePopover` displays generic "Wilson test vs 50%" copy. D-10 requires explicit "Expected for sub-2300 play to fall below" framing. The planner has two options:
1. Add an optional `bodyCopy?: ReactNode` prop to `ScoreConfidencePopover` and use it only for the achievable score bullet.
2. Wrap `ScoreConfidencePopover` with a thin `AchievableScorePopover` that overrides the body block.

Option 2 is cleaner — no churn in the existing popover; localizes the D-10 wording to one new file.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Discrete eval thresholds for Conv/Recov (`±100 cp`) | Continuous sigmoid (smooth in eval magnitude) | Phase 83 introduces continuous; Conv/Recov stays discrete | Both coexist — Conv/Recov answers "how do you handle clearly winning / losing positions", expected-score answers "how close to optimal play do you score on average". Not redundant. |
| Wilson on `(W, D, L, N)` integer tuple | Wilson on `(score, N)` float pair | Plan 2 refactor (proposed) | Single math source; expected-score and endgame-score reuse identical test. |
| LLM narrates 2 findings in `endgame_start_vs_end` | LLM narrates 3 findings | Plan 5 (Phase 83) | Narration centers on the achievable-vs-achieved gap as headline (D-18). |
| Tile uses sig-only coloring | Tile uses `(zone != neutral) AND p < 0.05` | Phase 82 D-12 (already shipped) | New "Achievable score" bullet inherits the same gate. |

**Deprecated/outdated:** None for Phase 83 — strictly additive on top of Phase 82.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `compute_confidence_bucket` can be cleanly refactored to factor out a `(score, n)` helper without breaking existing callers | "Critical methodology note" + Plan 2 | LOW — math is self-contained at `score_confidence.py:140-143`; existing 6 callers all use `(w, d, l, n)` signature unchanged. |
| A2 | Lichess constant `K = 0.00368208` is the correct fit for 2300+ rapid games | "Standard Stack" + "Code Examples" | LOW — value is publicly documented; SEED-014 cites Lichess accuracy doc. |
| A3 | The mate-game count typically differs from the entry-eval cohort by 0-5 games per user | Pitfall 3 | LOW — order-of-magnitude estimate from `app/services/endgame_service.py:1683` comment ("excluded ~5 games per typical user"). Concrete number depends on the user. |
| A4 | `ScoreConfidencePopover` is OK to wrap or extend with the D-10 framing | "Code Examples" (Plan 3 reference) | LOW — popover is a leaf component; wrapper pattern is established (see `BulletConfidencePopover` adjacent). |
| A5 | The `_PROMPT_VERSION` bump invalidates all cached LLM responses automatically | "Runtime State Inventory" | LOW — `_PROMPT_VERSION` is part of the cache key (`insights_llm.py:1892` etc.). Confirmed by Phase 82 ship. |

All Assumptions Log entries are LOW-risk and are flagged for sanity-check during Plan 1 + Plan 2 review, not as blockers.

## Open Questions

1. **`ScoreConfidencePopover` body-copy override mechanism**
   - What we know: D-10 requires "Expected for sub-2300 play to fall below" framing; existing popover shows generic Wilson-test copy.
   - What's unclear: New optional `bodyCopy` prop vs. a thin wrapper component.
   - Recommendation: Wrapper component `AchievableScorePopover`. Localizes D-10 wording; zero risk to the existing tile-2 popover.

2. **Should the popover surface `n` divergence vs entry-eval cohort?**
   - What we know: D-06 says mate INCLUDED in the achievable-score cohort. Phase 81 D-07 says mate EXCLUDED in entry-eval. So `entry_expected_score_n >= entry_eval_n`.
   - What's unclear: Will users notice and worry about the count divergence between the two bullets in the same tile?
   - Recommendation: Add one line in the popover ("Based on N games, including mate") to defuse the question. The planner can include this in Plan 3 task list and validate in Plan 3 UAT.

3. **Mobile-collapse popover wording**
   - What we know: D-10 popover copy includes "on the right" — geographically wrong on mobile.
   - What's unclear: Is "Compare against your achieved Endgame score nearby" acceptable, or should we go viewport-aware?
   - Recommendation: Use "below" — both desktop and mobile have the "achieved" bullet below the "achievable" bullet (because Tile 2 is below Tile 1 on mobile; and on desktop the bottom-row achieved bullet is below the top-row achievable bullet within Tile 1's stack — no wait, they're in DIFFERENT tiles on desktop, side-by-side at the bottom row). Reword to "Compare against your achieved Endgame score in the other tile" — works on both.

4. **Plan 4 cohort filter for benchmark expected-score**
   - What we know: Canonical CTE uses `lichess_username` join, `status='completed'`, equal-footing. Filters: `eval_cp NOT NULL OR eval_mate NOT NULL`, `|eval_cp| < 2000`.
   - What's unclear: Should Plan 4 use the same `is_endgame` game filter as Phase 82 §3 (only games reaching `ENDGAME_PLY_THRESHOLD`)? Yes — that's the same population the tile aggregates from.
   - Recommendation: Mirror Phase 82 §3 SQL exactly; just replace the eval-mean computation with the sigmoid + mate→0/1 conversion. Document in the new SKILL.md section as "Section X — Stockfish-baseline expected score at endgame entry".

5. **Plan 4 zone band — pooled IQR vs editorial tightening**
   - What we know: Phase 82 D-08 editorially tightened entry-eval from ±0.75 to ±0.50.
   - What's unclear: What's the expected per-(user, color) p25/p75 for `entry_expected_score`? Without running the benchmark, hard to predict — but the sigmoid is steep around 0 cp, so a ±10 cp baseline shift maps to roughly ±0.04 score points. Sigmoid of pooled p25/p75 of ±55 cp eval (from `reports/benchmarks-2026-05-10.md` §3) ≈ `[0.450, 0.550]`. The cohort band will probably land right around the live `[0.45, 0.55]` `endgame_score` band — confirm with actual benchmark run.
   - Recommendation: Plan 4 task includes "compute pooled p25/p75 of `entry_expected_score`; recommend band; if IQR is narrower than ±0.05, tighten editorially so meaningful patterns surface (memory `feedback_zone_band_judgement.md`)."

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Backend framework | pytest 8.x + pytest-asyncio (uv) |
| Backend config file | `pyproject.toml` (locked) |
| Backend quick run | `uv run pytest tests/services/test_eval_utils.py -x` |
| Backend full suite | `uv run pytest` |
| Frontend framework | vitest + @testing-library/react (jsdom) |
| Frontend config file | `frontend/vite.config.ts` |
| Frontend quick run | `cd frontend && npm test -- EndgameStartVsEndSection` |
| Frontend full suite | `cd frontend && npm test` |
| Type checks | `uv run ty check app/ tests/` + `cd frontend && npm run lint && npx tsc --noEmit` |
| Drift check | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| D-02 | Sigmoid centered at 0.5 | unit | `uv run pytest tests/services/test_eval_utils.py::TestSigmoid::test_centered_at_zero -x` | Wave 0 (NEW) |
| D-02 | Sign convention both colors | unit | `uv run pytest tests/services/test_eval_utils.py::TestSigmoid::test_sign_convention_{white,black} -x` | Wave 0 (NEW) |
| D-02 | Saturation at large eval | unit | `uv run pytest tests/services/test_eval_utils.py::TestSigmoid::test_saturation_{high,low} -x` | Wave 0 (NEW) |
| D-02 | Mate-for-user → 1.0 | unit | `uv run pytest tests/services/test_eval_utils.py::TestMate::test_mate_for_{white,black}_user -x` | Wave 0 (NEW) |
| D-02 | Mate-against-user → 0.0 | unit | `uv run pytest tests/services/test_eval_utils.py::TestMate::test_mate_against_{white,black}_user -x` | Wave 0 (NEW) |
| D-04 / D-05 / D-06 / D-07 | Per-game aggregator emits `entry_expected_score*` fields | integration (live dev DB) | `uv run pytest tests/test_endgame_service.py -k expected_score -x` | Wave 0 (NEW test cases on existing file) |
| D-05 | Wilson refactor; `compute_confidence_bucket` math unchanged | unit | `uv run pytest tests/services/test_score_confidence.py -x` | ✅ existing (extend with refactor-equivalence cases) |
| D-21 | Schema default values when n=0 | unit | `uv run pytest tests/test_endgames_router.py -k expected_score -x` | ✅ existing (extend) |
| D-08 | `MiniWDLBar` renders in "What you do with it" tile | RTL component | `cd frontend && npm test -- EndgameStartVsEndSection -t "wdl-bar"` | Wave 0 (extend `EndgameStartVsEndSection.test.tsx`) |
| D-09 / D-10 / D-11 | "Achievable score" bullet renders with right testid + zone color gate | RTL component | `cd frontend && npm test -- EndgameStartVsEndSection -t "achievable"` | Wave 0 (extend) |
| D-12 | 2×2 layout: DOM order entry-eval → achievable → wdl → achieved | RTL component | `cd frontend && npm test -- EndgameStartVsEndSection -t "DOM order"` | Wave 0 (extend) |
| D-12 | Mobile collapse preserves chronological order | RTL component | `cd frontend && npm test -- Endgames.startVsEnd -t "mobile"` | ✅ existing |
| D-14 | `ENTRY_EXPECTED_SCORE_ZONES` registered in `endgame_zones.py` | unit | `uv run pytest tests/services/test_endgame_zones.py -x` | ✅ existing (extend) |
| D-16 | `endgameZones.ts` drift check | CI smoke | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | manual (no test needed; CI runs `git diff --exit-code`) |
| D-17 / D-19 | `_findings_endgame_start_vs_end` emits 3 findings | unit | `uv run pytest tests/services/test_insights_service.py::TestFindingsEndgameStartVsEnd -x` | ✅ existing (extend with `entry_expected_score` cases) |
| D-18 | LLM prompt subsection mentions `entry_expected_score` | unit | `uv run pytest tests/services/test_insights_llm.py -k prompt_v25 -x` | Wave 0 (extend existing) |
| D-20 | `_PROMPT_VERSION == "endgame_v25"` | unit | `uv run pytest tests/services/test_insights_llm.py -k prompt_version -x` | Wave 0 (extend existing) |
| D-22 | Visual juxtaposition: two bullets, no `gap_p_value` field | manual UAT | dev-DB live insight request; eyeball the rendered tile | manual-only |
| D-10 | Popover D-10 framing (no "underperformance") | RTL component | `cd frontend && npm test -- EndgameStartVsEndSection -t "popover copy"` | Wave 0 (extend; or add new test for `AchievableScorePopover` wrapper) |

### Sampling Rate

- **Per task commit:** `uv run ty check app/ tests/ && uv run pytest tests/services/test_eval_utils.py tests/services/test_score_confidence.py -x` (~10 seconds)
- **Per wave merge:** `uv run pytest && cd frontend && npm test && npm run lint && npm run knip && npm run build` (~3 minutes)
- **Phase gate:** Full backend suite + frontend suite green + `uv run python scripts/gen_endgame_zones_ts.py` no-op + manual UAT (dev DB live insight request, visual verification of 2×2 grid + LLM narration includes "achievable" framing without "underperformance") before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/services/test_eval_utils.py` — NEW. Covers D-02, D-03 (sigmoid identities + mate → 0/1).
- [ ] `tests/test_endgame_service.py` — EXTEND. Add `class TestExpectedScoreAggregation` with: mate-included counting, NULL-eval skip, |eval_cp|≥2000 clip, Wilson p-value plumbing, CI bound math.
- [ ] `tests/services/test_score_confidence.py` — EXTEND. Add `test_wilson_score_test_vs_half_equivalence` asserting refactored helper produces identical p-values as `compute_confidence_bucket` on integer (W, D, L, N) inputs.
- [ ] `tests/services/test_endgame_zones.py` — EXTEND. Add `ENTRY_EXPECTED_SCORE_ZONES` registration test + `assign_zone("entry_expected_score", value)` dispatch test.
- [ ] `tests/services/test_insights_service.py` — EXTEND. The existing `_findings_endgame_start_vs_end` test block (lines 715-910) is extended from 2-tile shape to 3-tile shape with mirror cases for `entry_expected_score`.
- [ ] `tests/services/test_insights_llm.py` — EXTEND. Add prompt-version assertion + glossary-line assertion for `entry_expected_score`.
- [ ] `tests/test_endgames_router.py` — EXTEND. Wire-format snapshot for `entry_expected_score*` fields on `EndgamePerformanceResponse`.
- [ ] `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — EXTEND. Add ~6 new test cases for the 2×2 grid: WDL bar rendering, achievable-score bullet, zone-color gate on achievable-score, 4-row DOM order, popover testids.
- [ ] `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` — EXTEND. Add page-integration test for mobile collapse order of the 4-row stack.

Framework install: none — all dependencies already installed.

## Security Domain

> `security_enforcement` is absent in `.planning/config.json` — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | N/A — this phase touches the `GET /api/endgames/performance` endpoint which is already authenticated (FastAPI-Users JWT). No new endpoints. |
| V3 Session Management | no | N/A — no new auth flow. |
| V4 Access Control | no | N/A — endpoint already enforces `current_user` from FastAPI-Users dependency. New fields are scoped to the authenticated user's own games via existing `user_id` filter in `endgame_repository.py`. |
| V5 Input Validation | low | Pydantic v2 validates request shape; no new request inputs from the user (all fields on the response are derived from existing query). |
| V6 Cryptography | no | N/A. |
| V8 Data Protection | low | New schema fields are aggregated scalars (mean expected score, n, p_value, CI bounds) — no raw eval values exposed in the response. The user already has access to their own games' eval data via other endpoints, so no data-classification change. |
| V12 Files and Resources | no | N/A. |
| V14 Configuration | no | N/A. |

### Known Threat Patterns for FastAPI + React + asyncpg stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| SQL injection on new aggregator | Tampering | None — the new aggregator is a pure-Python loop over already-fetched `bucket_rows`. No new SQL written. SQL parameter binding handled by SQLAlchemy 2.x async (existing `apply_game_filters`). |
| Mass assignment via Pydantic | Tampering | Response-only schema fields — never a request input. Pydantic v2 strict mode (project default) blocks unknown fields on input. |
| Information disclosure via new fields | Information disclosure | All new fields are derived from the user's own data already accessible via this endpoint. No new data class introduced. |
| LLM prompt injection via new metric | Tampering | The new `entry_expected_score` value flows through `_findings_endgame_start_vs_end` → `SubsectionFinding` → `endgame_insights.md` prompt. The value is a clamped float in [0, 1] — no string user input enters the prompt. Existing prompt-injection mitigations (no raw user PGN, no user usernames in LLM payload) carry forward. |
| Cache poisoning via prompt version | Tampering | `_PROMPT_VERSION` bump (`endgame_v24` → `endgame_v25`) is a code change requiring commit + deploy. Cache key is server-controlled. |

No new attack surface introduced by Phase 83. All changes flow through existing authenticated, parameterized, validated paths.

## Sources

### Primary (HIGH confidence — VERIFIED by codebase read on 2026-05-11)

- `/home/aimfeld/Projects/Python/flawchess/app/services/endgame_service.py:160-220` — `_classify_endgame_bucket` sign-flip pattern. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/services/endgame_service.py:1645-1732` — `_get_endgame_performance_from_rows` aggregator (the EXACT function Plan 2 extends). [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/repositories/endgame_repository.py:770-870` — `query_endgame_bucket_rows` SQL (already returns `(eval_cp, eval_mate, user_color)` per game — Plan 2 does NOT extend SELECT). [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/services/score_confidence.py:57-162` — `wilson_bounds`, `compute_confidence_bucket`, `_wilson_score_test_vs_half` (the proposed refactor target). [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/services/insights_service.py:443-502` — `_findings_endgame_start_vs_end` emitter (extend from 2 → 3 findings in Plan 5). [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/services/endgame_zones.py:30-280` — `MetricId` Literal, `SubsectionId` Literal, `ZoneSpec`, `ZONE_REGISTRY`, `SAMPLE_QUALITY_BANDS`. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/services/insights_llm.py:66` — `_PROMPT_VERSION = "endgame_v24"` (current; Plan 5 bumps to `endgame_v25`). [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/prompts/endgame_insights.md:260-388` — existing `### Subsection: endgame_start_vs_end` block + glossary + mapping table. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/app/schemas/endgames.py:107-141` — `EndgamePerformanceResponse` with Phase 81 D-11 defaults pattern. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/EndgameStartVsEndSection.tsx` (full file, 206 lines) — Plan 3 target. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/stats/MiniWDLBar.tsx` (full file, 53 lines) — confirmed lift target with `{win_pct, draw_pct, loss_pct, heightClass?}` signature. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/lib/scoreBulletConfig.ts` (full file, 53 lines) — `SCORE_BULLET_CENTER`, `scoreBulletDomain`, `scoreZoneColor`, `clampScoreCi`. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/lib/endgameEntryEvalZones.ts` — exports `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS = ±0.5`, `endgameEntryEvalZoneColor`. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/scripts/gen_endgame_zones_ts.py` — codegen pattern; Plan 4 follows. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/.claude/skills/benchmarks/SKILL.md` (1319 lines) — canonical CTE `selected_users` with `bic.status='completed'`. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/reports/benchmarks-2026-05-10.md:220-290` — §3 EG-entry-eval, the Phase 82 calibration that Plan 4 mirrors. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/tests/services/test_insights_service.py:715-910` — existing tests for `_findings_endgame_start_vs_end` (Plan 5 extends from 2-tile to 3-tile cases). [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` (379 lines, 16 test cases) — Plan 3 extends. [VERIFIED]
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` — Plan 3 page-integration tests. [VERIFIED]

### Secondary (MEDIUM confidence)

- Lichess winning-chances method documentation — sigmoid `1 / (1 + e^(-0.00368208 * cp))`. [CITED via SEED-014 + Phase 83 CONTEXT.md D-02; matches widely-used Lichess accuracy method]

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primitive verified live in the codebase.
- Architecture: HIGH — Phase 83 follows Phase 81/82 patterns; verified file-by-file.
- Pitfalls: HIGH — derived from observed Phase 82 traps + the Wilson-float-mean methodology question (Pitfall 2) which is the one genuine design question.

**Research date:** 2026-05-11
**Valid until:** 2026-06-10 (30 days — stable codebase, no upstream deps changing).
