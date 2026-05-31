# Phase 94: Backend & Frontend Percentile Annotations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 94-backend-frontend-percentile-annotations
**Areas discussed:** Chip styling + popover trigger

---

## Gray Area Selection

Five gray areas were presented; the user selected one for discussion.

| Area | Description | Selected |
|------|-------------|----------|
| Reliability gate per metric | Reuse global PVALUE_RELIABILITY_MIN_N=10, or per-metric floors | |
| Median-band + Conversion tail rendering | Neutral "≈ average" band; Conversion right-tail suppression / cap / honest | |
| Chip styling + popover trigger | Chip-as-trigger vs HelpCircle; color treatment; placement; shape | ✓ |
| Schema field naming + placement | `{metric}_percentile` placement on response schemas | |

The first three open-ended decisions defaulted to the SEED-019 / ROADMAP path (literal-render near median, Conversion always rendered with improvement-focus framing as mitigation, `PVALUE_RELIABILITY_MIN_N = 10` as default gate). The schema-naming decision defaulted to the existing `_p_value` / `_ci_*` field-naming pattern.

---

## Chip Styling + Popover Trigger

Four sub-questions resolved.

### Q1 — How should the popover open on the chip?

| Option | Description | Selected |
|--------|-------------|----------|
| Chip is the trigger | Tap/hover the chip itself opens the popover. No HelpCircle. | ✓ |
| Chip + adjacent HelpCircle | Chip is decorative; HelpCircle next to it opens the popover (existing MetricStatPopover pattern). | |
| Both — chip and HelpCircle | Both tappable; belt-and-braces. | |

**User's choice:** Chip is the trigger.
**Notes:** D-01 captures this. The chip carries semantic meaning so it reads as a tappable primary element rather than decorative metadata.

### Q2 — Color treatment for the chip background/text?

| Option | Description | Selected |
|--------|-------------|----------|
| Linear gradient across percentile | Smooth color interpolation. | |
| Banded zones (3–4 buckets) | Red <p25, neutral p25–p75, green >p75. Discrete tiers. | ✓ (modified) |
| Single theme color | All chips share one neutral color. | |

**User's choice:** Banded zones (theme red <p25, neutral p25–p75, green >p75) PLUS a lucide `Flame` icon for top tiers — 1 flame at top 10%, 2 flames at top 5%, 3 flames at top 1%.
**Notes:** D-02 (color bands) and D-03 (flame icons) capture this. The flame tier thresholds (p90 / p95 / p99) are honest at the current cohort's tail resolution per SEED-019 / Phase 93 D-06.

### Q3 — Chip placement relative to the metric value on the 4 rows?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline, right after the value | Value and chip on a single line, chip tied to value. | |
| Inline, right-aligned on the row | Value left, chip floats to row's right edge. | ✓ |
| Below the value as a subtitle | Chip on a second line below the value. | |

**User's choice:** Inline, right-aligned on the row.
**Notes:** D-05 captures this. Mobile parity: wrap to next line at narrow widths is acceptable; planner decides the exact wrap behavior.

### Q4 — Should the chip be visually distinct or render as plain colored text?

| Option | Description | Selected |
|--------|-------------|----------|
| Pill/badge with colored background | Rounded background fill in the banded color, contrasting text. | ✓ |
| Plain colored text — no background | Just text in the banded color plus flames. | |
| Outlined chip | Border in banded color, transparent background, colored text. | |

**User's choice:** Pill/badge with colored background.
**Notes:** D-04 captures this. Theme drives both background and text colors (no hard-coded values per PCTL-05).

---

## Claude's Discretion

The user did NOT discuss these gray areas; they default to the ROADMAP / SEED-019 / REQUIREMENTS path documented in CONTEXT.md:

- Reliability gate per metric → reuse `PVALUE_RELIABILITY_MIN_N = 10` as default (D-10). Planner can argue for stricter per-metric floors with reasoning.
- Median-band rendering → render "top 50%" literally; no neutral band (D-07).
- Conversion ΔES right-tail handling → render always; the improvement-focus popover framing is the mitigation (D-09).
- Schema field naming → `{metric_id}_percentile` nullable float, on the existing schemas next to sibling `_p_value` / `_ci_*` fields (D-11).
- Exact theme constant names, pill padding/opacity/contrast values, flame stacking layout, chip component file location, popover copy strings, and Vitest assertions are planner-discretion within the locked decisions and project memories (`feedback_popover_copy_minimalism.md`, `feedback_benchmark_source_of_truth.md`).

## Deferred Ideas

None new this session — all deferred items already captured in CONTEXT.md `<deferred>` come from SEED-019 / Phase 93. No scope creep proposed during this discussion.
