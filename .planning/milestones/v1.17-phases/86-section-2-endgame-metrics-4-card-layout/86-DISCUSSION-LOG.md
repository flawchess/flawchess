# Phase 86: Section 2 — Endgame Metrics 4-card layout - Discussion Log

**Date:** 2026-05-14
**Phase:** 86-section-2-endgame-metrics-4-card-layout

This log captures the discussion that produced `86-CONTEXT.md`. It is a human-reference record (audits, retrospectives) and is **not** consumed by downstream agents.

---

## Areas Discussed

User selected three areas from the gray-area menu:
- Skill peer-bullet sig test (SEC2-08)
- Card grid layout (responsive)
- Section header / heading treatment

User skipped:
- Component file structure — Claude defaulted to Phase 85's sibling-component pattern (orchestrator + sibling cards). Recorded as D-07.

---

## Area 1 — Skill peer-bullet sig test (SEC2-08)

### Question 1: Sig-test method
**Options:**
- (a) Wald-z on aggregate diff with empirical trinomial variance (Recommended)
- (b) Propagate component CIs (Wilson → mean)
- (c) Raw-outcome paired/two-sample test on underlying WDL

**User selected:** (a) Wald-z on aggregate diff with empirical variance.

**Notes:** Closed-form, reuses Phase 85.1's trinomial variance pattern, no over-engineering. Independence assumption flagged but acceptable for a heuristic composite.

### Question 2: Math placement (follow-up)
**Options:**
- (a) Frontend-only — reuse existing FE composite
- (b) Backend-first — mirror Phase 85.1
- (c) Hybrid — backend Wilson components, frontend composite

**User selected:** (b) Backend-first, mirror Phase 85.1.

**Notes:** Math lives in `app/services/score_confidence.py` alongside the Phase 85.1 helpers. New fields on `ScoreGapMaterialResponse`. The frontend `endgameSkill()` helper is retired. Acknowledged as a milestone-boundary deviation from "frontend-only refactor" — flag for plan-phase summary.

**Decisions captured:** D-01, D-02, D-03, D-04 in CONTEXT.md.

---

## Area 2 — Card grid layout (responsive)

### Question: Breakpoint grid
**Options:**
- (a) `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` (4 → 2 → 1) (Recommended)
- (b) `grid-cols-1 lg:grid-cols-4` (4 → 1, matches Phase 85 exact pattern)
- (c) `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` (3 → 2 → 1 with Skill wrapping; matches Phase 87 planned)

**User selected:** (a).

**Decisions captured:** D-09 in CONTEXT.md.

---

## Area 3 — Section header / heading treatment

### Question: Header structure
**Options:**
- (a) Drop h3, keep question only (mirrors Phase 85) (Recommended)
- (b) Keep h3 + section-level InfoPopover
- (c) Keep h3, drop InfoPopover

**User selected:** (a), with a custom add-on: "move the section-level InfoPopover to Endgame Metrics and ELO (h2)".

**Notes:** Lifts the bucket-taxonomy + mirror-bucket explainer up to the page-level h2 trigger at `Endgames.tsx:458`. The h2 InfoPopover then covers both Section 2 (Endgame Metrics) and the ELO timeline under the same h2 — they share the Skill metric so the explainer is dual-purpose.

**Decisions captured:** D-10, D-11 in CONTEXT.md.

---

## Closure question

User chose "Proceed to write CONTEXT.md (Recommended)" — skipped further deep-dives into peer-bullet neutral band (POLISH-01, deferred to Phase 88), Skill n-gating policy refinement, and legacy file deletion mechanics. The remaining decisions were locked as Claude's Discretion defaults in CONTEXT.md (D-05..D-08, D-12..D-17).

---

## Scope creep redirected

None this session. No new capabilities were proposed.

---

## Deferred ideas surfaced

- Cell-specific peer-bullet neutral bands → Phase 88 (POLISH-01).
- Gauge sig gating → Phase 88 (POLISH-02).
- Independence-aware Skill diff variance — future iteration; false precision on a heuristic composite.

---

## Claude's Discretion items locked

- Per-MaterialRow diff test computation site (D-06): recommended backend; planner picks.
- Test placement (backend tests in `tests/test_score_confidence.py`; FE tests under `__tests__/`).
- MetricStatPopover per-card copy (D-16): Conv/Parity/Recov/Skill explanations + methodology block.
- Skill card empty-state (D-17): `"Not enough data yet"` per Phase 85 convention.
- Sub-question copy (D-10): "Do you outperform your opponents at converting, holding, and recovering?"
- Component file structure (D-07): sibling-component pattern, mirror Phase 85.

---

*Discussion captured: 2026-05-14*
