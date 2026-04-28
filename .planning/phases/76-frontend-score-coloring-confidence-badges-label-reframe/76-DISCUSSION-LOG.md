# Phase 76: Frontend — score-based coloring, confidence badges, label reframe - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 76-frontend-score-coloring-confidence-badges-label-reframe
**Areas discussed:** Confidence on moves-list rows, Section title + severity card copy, Confidence badge visual style, Explainer popover scope + content

---

## Confidence on moves-list rows

### Q1 — Compute site

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend computes locally (Recommended) | Port the trinomial Wald formula to TS using win_pct/loss_pct/game_count. No backend change. | |
| Backend extends moves payload | Add confidence (and p_value) to NextMoveEntry by extending query_top_openings_sql_wdl + the schema. Single source of truth. | ✓ |
| Shared helper module, frontend-only | Same as locally but extracted into frontend/src/lib/confidence.ts | |

**User's choice:** Backend extends moves payload.
**Notes:** User chose single source of truth over scope tightness. This expanded the phase to include backend work.

### Q2 — Payload fields

| Option | Description | Selected |
|--------|-------------|----------|
| confidence only | Add only `confidence: 'low' | 'medium' | 'high'`. | |
| confidence + p_value (Recommended) | Mirror the OpeningInsightFinding contract exactly. | ✓ |
| confidence + score | Add confidence plus a precomputed score. | |

### Q3 — Compute location

| Option | Description | Selected |
|--------|-------------|----------|
| SQL (Wald formula in HAVING/SELECT) | Push the formula into SQL. | |
| Python post-aggregation, shared helper (Recommended) | Extract Phase 75's `_compute_confidence` into a reusable function, call it on each row after SQL returns. | ✓ |
| Inline duplicate in repository | Re-implement the formula next to query_top_openings_sql_wdl. | |

### Q4 — Helper home

| Option | Description | Selected |
|--------|-------------|----------|
| Stay in opening_insights_service.py, import where needed | Minimal move; circular-import risk. | |
| Promote to opening_insights_constants.py | Constants module is at the import boundary. | |
| New module `app/services/score_confidence.py` (Recommended) | Pure helper, no deps. Both insights and moves explorer import from it. | ✓ |

---

## Section title + severity card copy

### Q1 — Initial pass (REJECTED by user — full course-correction)

Initial AskUserQuestion offered three section-title styles, three severity-in-card styles, and three number-cue choices. User declined to answer and reframed:

> "I think we don't need extra copy or change the existing copy. Once we add confidence indicators/badges to weakness/strength cards and sort higher confidence cards on top, we're justified in claiming these are actual weaknesses/strengths."

This effectively descopes INSIGHT-UI-04 (soften labels per SEED-008) — the calibration is carried by the badge + sort, not by softer copy.

### Q2 — Confirm: keep titles + prose verbatim

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — keep titles, keep prose, re-derive X% on frontend (Recommended) | Re-derive loss_rate/win_rate from W/D/L/N counts. | |
| Yes on titles, but switch card prose to score % | Card text moves to 'You score X% as White after...' to match the metric driving classification + tint. | ✓ |
| Backend re-adds loss_rate/win_rate to the schema | Avoid frontend re-derivation. | |

**Notes:** User chose score prose to keep the metric consistent end-to-end (matches feedback_llm_prompt_design.md rule #5: percent-rate metrics on the same scale across UI surfaces).

### Q3 — Sort order

| Option | Description | Selected |
|--------|-------------|----------|
| Confidence DESC, then effect-size DESC (Recommended) | high → medium → low buckets, ties broken by score gap. | ✓ |
| Effect-size DESC, then confidence DESC | Keep current ordering; confidence as tiebreaker. | |
| Severity DESC, then confidence DESC, then effect-size | Three-level sort. | |

### Q4 — Score prose form

| Option | Description | Selected |
|--------|-------------|----------|
| 'You score X% as White after 1.e4 c5' — same form both sections (Recommended) | Same verb regardless of section. | ✓ |
| Section-specific verb — 'underperform' / 'overperform' | Stronger framing. | |
| Score with delta-from-baseline — 'You score X% (−5pp from 50%)' | Surfaces effect-size in prose. | |

### Q5 — Sort site

| Option | Description | Selected |
|--------|-------------|----------|
| Backend in compute_insights (Recommended) | One source of truth; matches backend tests. | ✓ |
| Frontend in OpeningInsightsBlock before render | Zero backend change. | |

---

## Confidence badge visual style

### Q1 — Indicator render

| Option | Description | Selected |
|--------|-------------|----------|
| Small grey text in parens, all three levels visible (Recommended) | ' (low)' / ' (medium)' / ' (high)'. | |
| Small grey text in parens, only (low) and (medium) | (high) silent default. | |
| Tinted pill badge | low=red/medium=amber/high=green. | |
| Neutral grey pill, label-only | Small grey rounded badge. | |

**User's choice (Other / freeform):**
> "Small grey text without parens, in a separate table column between Games and Results. On mobile, we might need to hide this column. Mute rows which have fewer than 10 games or have low confidence"

### Q2 — Mute spec

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse existing UNRELIABLE_OPACITY = 0.5 (Recommended) | Extend the trigger to ALSO fire when confidence === 'low'. | ✓ |
| New muted-row tint distinct from <10-games | Two separate visual states. | |
| Mute = grey text + suppress the row severity tint | Don't lower opacity; neutralize tint and grey out text. | |

### Q3 — Card style

| Option | Description | Selected |
|--------|-------------|----------|
| Same plain grey text inline next to score prose (Recommended) | 'You score 38% as White after 1.e4 c6  low'. | |
| Plain grey text inline AND mute low-conf cards | Same plus 0.5 opacity on low-conf cards. | |
| Plain grey text on card, but no muted opacity on card | No opacity dim on cards. | |

**User's choice (Other / freeform):**
> "Add a new line after 'You score ..' which says 'Confidence: low/medium/high'. Mute cards with low confidence at 0.5 opacity. Explain confidence in a hover tooltip over the Confidence indicator"

### Q4 — Tooltip content

| Option | Description | Selected |
|--------|-------------|----------|
| Short level-specific copy (Recommended) | low='small sample, treat as a hint'; medium='enough games to trust the direction'; high='sample is large enough to trust the magnitude'. | ✓ |
| Same explainer content as the section-title ?-popover | Single source of copy. | |
| Show the raw stats: 'half-width ±Y%, n=N, p=Z' | SEED-007 explicitly rejected raw p-values. | |

### Q5 — Mobile column behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Hide entirely on mobile (Recommended) | Mute rule still fires. | |
| Show as suffix on the games count: '12 · low' | Compact. | |
| Keep the column visible on mobile too | Don't hide. | |

**User's choice (Other / freeform):**
> "Let's keep the column visible with a short 'Conf' title and low/med/high labels"

---

## Explainer popover scope + content

### Q1 — Initial placement

| Option | Description | Selected |
|--------|-------------|----------|
| Single ? at the Opening Insights block level (Recommended) | One InfoPopover at the top of OpeningInsightsBlock; would add a block-level title. | ✓ (later overridden) |
| One ? on each of the 4 section titles | Per the roadmap text. | |
| Single ? at the block level + Move Explorer 'Conf' column header tooltip | Two surfaces. | |

### Q2 — Content

| Option | Description | Selected |
|--------|-------------|----------|
| Score + sample-size + confidence framing in plain language (Recommended) | Three short paragraphs covering metric, gate, confidence. | ✓ |
| Just score + effect-size; defer confidence to the per-card tooltip | Tighter scope. | |
| FAQ-style: Why these lines? Why not others? What's a good confidence? | Three Q·A pairs. | |

### Q3 — Block title text

| Option | Description | Selected |
|--------|-------------|----------|
| 'Opening Insights' (Recommended) | Matches component name + Stats subtab vocabulary. | ✓ (later voided) |
| 'Opening Insights — strengths and weaknesses' | More descriptive. | |
| No new block title | Inline ? floats above the first section. | |

### Q4 — Copy draft

| Option | Description | Selected |
|--------|-------------|----------|
| Draft A — score-first (Recommended) | Score is (W + ½D)/N; finding shows up at ≥5% from 50%; confidence = sample-size cue. | ✓ |
| Draft B — user-first / 'what this is for' | Lead with user goal, then the math. | |
| Let me write it myself | Placeholder. | |

### Q5 — Final placement override

User course-corrected the placement decision in the final summary turn:

> "Actually don't introduce a new block-level title, since the other tabs also don't have it. Use 4 section popover icons instead"

This voids Q3 and overrides Q1 from "single block-level ?" to "four per-section ?-icons sharing the same Draft A copy via a single constant."

---

## Claude's Discretion

- Pixel width of the "Conf" column on mobile (responsive Tailwind classes) — pick something that works at 375px combined with Move + Games + WDL columns.
- Choice between `Tooltip` and a custom span for the per-card confidence tooltip.
- Score-prose rounding edge cases (e.g. score=0.499 displayed as "50%" while classified as weakness).
- Whether to also add a small InfoPopover or title-tooltip on the Conf column header — section-title popover already covers framing.
- `getSeverityBorderColor` helper simplification after the score-based migration lands.

## Deferred Ideas

- **`getSeverityBorderColor` simplification** — read directly from score buckets after D-12 lands.
- **Calibrating `low / medium / high` bucket boundaries against real data** — carries over from Phase 75; revisit after Phase 76 ships with telemetry.
- **Extending the confidence cue to other chart surfaces (WinRateChart, EndgameTimelineChart)** — out of scope for v1.14.
- **Surfacing raw p-value or half-width to power users** — explicitly rejected in design note.
- **LLM narration over opening findings** — future seed beyond v1.14.
