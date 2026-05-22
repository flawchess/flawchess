---
phase: 93-global-percentile-benchmark-artifact
plan: 01
subsystem: docs/skill
tags: [benchmarks, skill, percentile-cdf, methodology, v1.19]
requires:
  - "ROADMAP.md Phase 93 success criteria"
  - "CONTEXT.md D-01 through D-07 (D-06 revised 2026-05-22)"
  - "SEED-019-global-percentile-annotations-on-endgame-metrics.md"
  - "reports/benchmarks-gap-metrics-percentile-candidacy.md (2026-05-22 pre-flight)"
provides:
  - ".claude/skills/benchmarks/SKILL.md §4 — Global Percentile CDF methodology"
  - "Authoritative breakpoint set: every integer percentile p1..p99 (99 total)"
  - "Per-metric inclusion floors for the 4 in-scope MetricIds"
  - "Per-rating-bucket sanity-check methodology"
  - "reports/global-percentile-cdf-latest.md report layout + rotation rule"
  - "Mechanization handoff to Plan 02 (gen_global_percentile_cdf.py + global_percentile_cdf.py)"
affects:
  - "Phase 93 Plan 02 — script + committed Python artifact reads §4 as source-of-truth"
  - "Phase 94 backend — interpolation helper + chip popover copy traces back to §4"
  - "Phase 95 LLM payload — percentile annotations narrate from §4 methodology"
tech-stack:
  added: []
  patterns:
    - "Subchapter mirrors §3.1.5 / §3.1.6 / §3.2.2 authoring style — short intro, per-subsection blocks, no SQL duplication of Chapter 1 building blocks"
    - "Slim report format (per-metric breakpoint table + per-rating-bucket sanity-check table per metric) — mirrors reports/benchmarks-gap-metrics-percentile-candidacy.md (2026-05-22)"
    - "Report rotation rule mirrors reports/benchmarks-latest.md convention (D-07)"
    - "Audit-trail constants (BENCHMARK_DB_SNAPSHOT_MONTH + per-metric n_users) live in both committed Python source and report header"
key-files:
  created:
    - ".planning/phases/93-global-percentile-benchmark-artifact/93-01-SUMMARY.md"
  modified:
    - ".claude/skills/benchmarks/SKILL.md (+132 lines, Chapter 4 inserted at line 2963 before 'Report file layout')"
decisions:
  - "Per-user inclusion floors kept per-metric (≥30/≥30 for score_gap, ≥20 for achievable_score_gap, ≥20 spans per bucket for the two Section 2 ΔES IDs) — preserves continuity with the 2026-05-22 pre-flight; unified floor was rejected because the four metrics have structurally different per-user denominators (paired games vs spans per eval-entry bucket)."
  - "Report depth: slim format (breakpoint table + one per-rating-bucket sanity-check table per metric) — sufficient for ROADMAP success criterion #3, no per-axis ELO collapse verdicts re-derived here (already in reports/benchmarks-latest.md)."
  - "Audit-trail constants embedded in committed Python source: BENCHMARK_DB_SNAPSHOT_MONTH = \"2026-03\" + per-metric n_users field on each CdfTable. Both also appear in the report header so future recalibrations can verify what cohort the live chips were trained against."
  - "Illustrative SQL snippet retained (one fenced block) showing the 99-element percentile_cont composition for achievable_score_gap — flagged 'composition example, not authoritative' so future readers reach for scripts/gen_global_percentile_cdf.py (Plan 02) as the source-of-truth SQL."
  - "Chip phrasing convention: always 'top X%' (NEVER 'bottom X%'). Documented in the breakpoint-set subsection."
metrics:
  duration: "~25 min (single-task plan, one-pass write)"
  completed: "2026-05-22"
  tasks_completed: 1
  files_modified: 1
  files_created: 1
---

# Phase 93 Plan 01: Global Percentile Benchmark Artifact — Skill Methodology Summary

Extends `.claude/skills/benchmarks/SKILL.md` with a new **Chapter 4 — Global Percentile CDF** documenting the methodology, locked 99-integer-percentile breakpoint set, per-rating-bucket sanity-check tables, and report layout for the global empirical-CDF artifact consumed by Phases 94 (chip + popover) and 95 (LLM payload). The chapter is reproducible from §4 alone — no need to read CONTEXT.md or SEED-019.

## Final placement

- **Chapter 4 inserted at line 2963** of `.claude/skills/benchmarks/SKILL.md`, immediately **before** the existing "Report file layout" section (now at line 3091 post-insertion).
- Total file growth: **+132 lines** (3068 → 3200).
- No existing chapter index at the top of SKILL.md, so no cross-link in a TOC was needed. The "Report file layout" section's chapter inventory was not edited — the new report (`reports/global-percentile-cdf-latest.md`) is documented inline in §4.7 with its own rotation rule rather than appended to the §3.x report inventory, because the global CDF is a separate report file with its own layout, not a subchapter of `benchmarks-latest.md`.

## Chapter structure (8 subsections)

1. **Intro paragraph** — what §4 produces (per-metric empirical CDF over the 4 chipped ΔES metrics, global-pooled, committed at `app/services/global_percentile_cdf.py`, mechanized by `scripts/gen_global_percentile_cdf.py` from Plan 02). What it does NOT produce (Recovery, raw % gauges) with D-02 rationale inline. Downstream consumer = Phase 94 backend; explicit "no client-side code, no TS mirror, no codegen" callout per D-01.
2. **In-scope metrics** — 4 `MetricId` literals from `app/schemas/endgames.py`: `score_gap`, `achievable_score_gap`, `section2_score_gap_parity`, `section2_score_gap_conv`. Each bullet carries the subchapter cross-link (§3.1.5/§3.1.6/§3.2.2) and the per-user inclusion floor.
3. **Canonical CTE — inherited from §1** — cites the Chapter 1 building blocks (Standard CTE / sparse-cell exclusion / equal-footing filter / game-time ELO bucketing) by reference; no SQL duplication. Explicitly states the pooled distribution is **global** (not per-cell) because the chip phrasing requires a single CDF.
4. **Breakpoint set** — contains the literal phrase `every integer percentile from p1 through p99` (positive verification gate). Lists the labels explicitly (`p1, p2, p3, ..., p97, p98, p99 — 99 breakpoints total`). Rationale for bounded tails (n ≈ 2000 cohort, ±5pp SE on deep-tail breakpoints) and integer-only steps (chip phrasing operates on whole-percent precision). Chip phrasing convention: always "top X%". Superseded-breakpoint footnote covers the earlier 19-breakpoint tail-densified set and the intermediate 15-breakpoint p1..p99-with-half-steps draft, marking them "out of scope / earlier draft / deferred".
5. **Per-rating-bucket sanity-check methodology** — 5-row table per metric (rating bucket / n_users / median / skew / kurtosis), keyed on game-time ELO buckets `800/1200/1600/2000/2400` (sparse `(2400, classical)` excluded). Conversion-ΔES skew ≈ −0.95 + excess kurt ≈ +1.42 documented as expected, not a data bug.
6. **Expected report shape** — slim format: header block (DB + snapshot + n_users + methodology notes) + per-metric 99-row breakpoint table + per-metric 5-row sanity-check table + per-metric `n_users` header line. Display formatting per §1 rule (pp with one decimal).
7. **Mechanization & rotation rule** — Plan 02's `scripts/gen_global_percentile_cdf.py` is named as the source-of-truth SQL; safety guard pattern (refuses to run unless `DATABASE_URL` contains `flawchess_benchmark` AND `:5433`) mirrors `scripts/backfill_eval.py --db benchmark`. DB → Python regen is a manual recalibration step (no CI gate). Report rotation rule for `reports/global-percentile-cdf-latest.md` documented (D-07): archive prior dated report in place, never mutate an existing archive.
8. **Illustrative SQL snippet** — single fenced block showing the 99-element `percentile_cont(ARRAY[0.01, ..., 0.99])` composition for `achievable_score_gap`. Flagged as "composition example, not authoritative" so future readers reach for `gen_global_percentile_cdf.py`.

## Resolved discretion decisions

| Discretion item | Resolution | Rationale |
|---|---|---|
| #2 Per-user inclusion floor per metric | **Per-metric floors kept** (≥30/≥30 for `score_gap`, ≥20 for `achievable_score_gap`, ≥20 spans per bucket for the two Section 2 ΔES IDs) | Preserves continuity with `reports/benchmarks-gap-metrics-percentile-candidacy.md` (2026-05-22). Unified floor rejected — the four metrics have structurally different per-user denominators (paired games vs spans per eval-entry bucket). |
| #3 Report depth | **Slim format** (breakpoint table + one per-rating-bucket sanity-check table per metric) | Sufficient for ROADMAP success criterion #3; rich pre-flight-style layout (per-axis ELO collapse verdicts) is already in `benchmarks-latest.md` and would be duplicated work. |
| #4 Audit-trail constants in committed Python | **Yes** — `BENCHMARK_DB_SNAPSHOT_MONTH = "2026-03"` (str) + per-metric `n_users: int` on each `CdfTable`. Both also surface in the report header. | Small cost, real benefit for future recalibrations (Phase 94 chips trained on a known cohort; an unexplained chip shift in a later release traces back to a snapshot-month bump). |

## Breakpoint-set evolution (audit trail)

The final set is **99 integer percentiles (p1..p99)**. This is the **third** breakpoint set considered for Phase 93:

1. **Earlier draft (SEED-019, 2026-05-20):** 19-breakpoint *tail-densified* set including `p0.1, p0.5, p2.5, p97.5, p99.5, p99.9` for honest "top 0.1%" rendering at the deep tails.
2. **Intermediate draft (CONTEXT.md D-06, original):** 15-breakpoint `p1..p99 with half-steps` — added `p2.5, p97.5` shoulders but dropped the `p0.1 / p99.9` deep extremes.
3. **Final (CONTEXT.md D-06 revised 2026-05-22, ROADMAP success criterion #5):** 99 integer percentiles `p1, p2, ..., p99`. Sub-percent steps dropped because chip phrasing operates on whole-percent precision ("top 3%", not "top 2.5%"). Deep-tail breakpoints (p0.1 / p99.9) dropped because n ≈ 2000 gives ±5pp sampling SE at the deep tails — they would swing on single outliers and the cohort-rebuild cost is out of v1.19 scope.

The audit trail is preserved in §4.4 of the new chapter as a "Superseded breakpoint sets" footnote so a future maintainer who finds an earlier note proposing `p2.5` doesn't reintroduce it.

## Cross-references to Plan 02

The new §4 names Plan 02's deliverables in three places so the methodology → mechanization handoff is explicit:

- **Intro paragraph** — `scripts/gen_global_percentile_cdf.py` named as the script counterpart; `app/services/global_percentile_cdf.py` named as the committed Python artifact (sibling of `endgame_zones.py`, NOT a graft).
- **§4.7 Mechanization & rotation rule** — full description of the script's safety guard (mirrors `scripts/backfill_eval.py --db benchmark`), the typed `Mapping[MetricId, CdfTable]` registry pattern (mirrors `endgame_zones.ZONE_REGISTRY`), and the two audit-trail constants embedded in the committed source.
- **§4.8 Illustrative SQL snippet** — flagged as "composition example, not authoritative — the authoritative SQL lives in `scripts/gen_global_percentile_cdf.py`".

## Verification — all 6 grep gates pass

| # | Gate | Expected | Actual |
|---|------|---------:|-------:|
| 1 | `grep -c "^## 4\. Global Percentile CDF" SKILL.md` | `==1` | `1` |
| 2 | rotation-rule prose mentions `global-percentile-cdf-latest.md` (non-heading) | `>=1` | `5` |
| 3 | both Section 2 IDs `section2_score_gap_(conv\|parity)` mentioned in body | `>=2` | `3` |
| 4 | `achievable_score_gap` mentioned in body | `>=1` | `17` |
| 5 | literal phrase `every integer percentile from p1 through p99` | `>=1` | `1` |
| 6 | sub-percent / extreme-tail mentions outside `supersed\|out of scope\|deferred\|earlier draft` context | `==0` | `0` |

Gate 6 initially tripped on two "Rationale for …" sub-bullets that mentioned `p0.1 / p99.9 / p2.5 / p97.5` without the allow-list keywords; fix was to reframe the rationale lines to use **out of scope** (`deep-tail breakpoints … out of scope`, `half-percent shoulders … out of scope`) so the audit-trail footnote and the rationale lines both pass the negative grep. Auto-fix logged here as `[Rule 1 - Bug]` style adjustment (verification-gate-driven), no scope expansion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree base predates the plan-creating commit**

- **Found during:** Initial file read at execution start.
- **Issue:** The worktree was created on a base commit (`1a7a8e59`) that predates the plan-creating commit (`6949dd0c`). As a result, `.planning/phases/93-global-percentile-benchmark-artifact/93-01-PLAN.md` does not exist in the worktree's tree, and `.planning/phases/` does not exist at all.
- **Fix:** Read the plan file content from `main` via `git show main:.planning/phases/93-global-percentile-benchmark-artifact/93-01-PLAN.md` and the CONTEXT.md from the same ref. Created `.planning/phases/93-global-percentile-benchmark-artifact/` directory in the worktree to host this SUMMARY.md.
- **Files modified:** none in addition (directory creation only).
- **Commit:** SUMMARY.md commit (next, after this file lands).
- **Why this is Rule 3 not Rule 4:** the plan content was fully recoverable from `main` and the work could proceed without re-planning; this is a worktree-base configuration quirk, not an architectural decision.

### Auto-added critical functionality

None. Pure documentation edit — no missing error handling, validation, or correctness gates apply.

### Architectural changes

None.

## Known Stubs

None. The chapter does not add UI components, data fetchers, or placeholders — it documents methodology that Plan 02 will mechanize and that Phase 94 will consume.

## Self-Check

- [x] `.claude/skills/benchmarks/SKILL.md` exists and contains `## 4. Global Percentile CDF` at line 2963
- [x] Commit `0d5f226a` exists in `git log`
- [x] All 6 verification gates pass

## Self-Check: PASSED
