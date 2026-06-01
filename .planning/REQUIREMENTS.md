# Requirements: FlawChess — v1.20 LLM Statistical Reasoning

**Defined:** 2026-05-22 (original v1.19+v1.20 combined scope); split into v1.20 on 2026-05-27 (commit `dd88ffda`).
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report.

**Milestone goal:** Rework the endgame-insights LLM prompt + payload so it can reason explicitly over the v1.17 statistical-rigor metric set (Endgame Score Gap, Achievable Score Gap, Section 2 ΔES Score Gap family, time-pressure hypothesis tests) and the v1.19 peer-relative percentile annotations, using p-values, confidence interval bounds, and percentiles, with prompt guardrails that prevent narrating small-but-significant findings.

**Source:** `.planning/seeds/SEED-019-global-percentile-annotations-on-endgame-metrics.md` (now partially closed by v1.19) and recent v1.17 statistical-rigor work (Phase 85.1, 86, 87.2, 87.6, 88) that exposed new server-side test statistics not currently surfaced to the LLM. v1.19 ship surfaces per-(metric, ELO anchor, TC) cohort percentiles on the API — this milestone wires those into the LLM payload + prompt.

**Scope discipline:** The requirements below are directional and category-level. Per-phase scope (whether to pass raw CIs vs. derived narration tags, LLM prompt version pivots) is refined in `/gsd:discuss-phase` for Phase 95. Every LLM-* line below is "user-facing behavior X must exist by milestone close" not "Phase 95 ships exactly this design."

## v1 Requirements

### LLM Statistical Reasoning (LLM)

> **Status (2026-06-01): active as v1.23 Phase 102.** Promoted from backlog (was Phase 999.7) via `/gsd-explore`. Scope narrowed this session — percentile-led, p-values out, CI likely out, LLM time-pressure narration added, no new frontend, UAT-dominated. Full locked decisions: `.planning/notes/v1.23-phase-102-endgame-llm-statistical-reasoning.md`. Next: `/gsd-discuss-phase 102`.

Reworks the endgame-insights LLM payload + prompt so the model can reason over the v1.17 statistical-rigor metric set (Endgame Score Gap, Achievable Score Gap, Section 2 ΔES Score Gap family, Time Pressure hypothesis tests) using p-values, confidence intervals, and the v1.19 peer-relative percentile annotations, while preserving the prior decision that the cohort `zone` field — not significance — gates whether a metric is narrated.

- [ ] **LLM-01**: The endgame-insights payload exposes per-metric **percentile** fields for the v1.17/v1.19/v1.21 metric set, alongside the existing `zone` + `sample_quality` fields. Existing metrics retain their current shape; the additions are non-breaking optional fields. **Scope narrowed (/gsd-explore 2026-06-01):** percentile is the committed addition; **p-values are explicitly OUT** (redundant with the zone band, conflicts with `feedback_llm_significance_signal`); **CI bounds are likely OUT** (the existing `sample_quality` / `within-noise` / `[near edge]` markers already cover precision/hedging) — final CI call locked at discuss-phase. See `.planning/notes/v1.23-phase-102-endgame-llm-statistical-reasoning.md`.
- [ ] **LLM-02**: The endgame-insights system prompt teaches the LLM to reason over CIs and percentiles explicitly — e.g. "your value sits at X with 95% CI [Y, Z], placing you in the top P% of same-rated peers" — without re-licensing the small-but-significant narration pattern that motivated `feedback_llm_significance_signal.md`. The cohort `zone` field remains the gate for whether a metric is narrated at all; CIs and p-values inform *how* the narration is phrased once a zone-driven decision to narrate has been made.
- [ ] **LLM-03**: The prompt preserves `feedback_llm_significance_signal` — the cohort `zone` field remains the sole gate on *whether* a metric is narrated; percentile annotations inform only *how* a zone-opened narration is phrased and must NOT act as a second significance signal (do not narrate a "typical"-zone metric because its percentile is extreme). **Session lean (/gsd-explore 2026-06-01):** approach (a) — no parallel p-value/CI significance fields in the payload; percentile-only enrichment under the zone gate. Final lock at Phase 102 `/gsd-discuss-phase`, rationale recorded in the decision log.
- [ ] **LLM-04**: The endgame-insights prompt narrates the Phase 85.1 / 87.2 / 87.6 / 88 metrics with the new statistical depth where the existing prompt has either silence or generic templating — at least Section 1 Endgame Score Gap & Eval Score Gap (overall), Section 2 Eval Score Gap family (per-phase + per-sequence-type), and **Time Pressure**. Time-pressure narration covers the three page surfaces (/gsd-explore 2026-06-01): **Score Gap by Remaining Time** (the per-bucket decomposition Phase 88.1 stripped from the payload — the genuine add), **Clock Gap**, and **Net Flag Rate**. Verify which of these are already in the payload at plan time rather than trusting prior-agent claims.
- [ ] **LLM-05**: Where peer-relative percentile annotations (v1.19 PCTL/TPCTL/PRPCR) are emitted on in-scope metrics, the LLM payload includes them and the prompt teaches the model to weave the percentile into narration naturally — using the cohort framing ("vs other ~{anchor}-rated players") not global-pool framing — without doubling up on the cohort zone signal.
- [ ] **LLM-06**: The endgame-insights prompt version bumps cleanly (current is `endgame_v35`); cache invalidation is automatic via the `_PROMPT_VERSION` cache key. Backwards compatibility with older cached reports is preserved (do not retroactively invalidate prior reports beyond the prompt-version cache mechanism already in place).
- [ ] **LLM-07**: **UAT is the primary verification for this phase, not an afterthought** (/gsd-explore 2026-06-01 — user flagged Phase 102 as UAT-dominated). Budget for multiple UAT passes against real production users (the same `endgame_v23` → `endgame_v35` cadence used in v1.16 / v1.17), verifying the rework lands an observable narration improvement across a representative sample — short-history users, sparse-section users, and full-history users included.

## Future Requirements

- Tier-4 per-type breakdown percentiles (per-class Conv / Recov / Score / Score Gap) — deferred unless per-user samples deepen materially. Captured in SEED-019 §Tier 4.
- Opening insights percentile annotations and LLM reasoning rework — candidate for a future Opening Insights v2 milestone.

## Out of Scope

- A separate "verdict" field on LLM payloads alongside `zone` — prior decision (`feedback_llm_significance_signal.md`) stands. Phase 95 resolves the tension via prompt guardrails on raw CIs/p-values, not via a parallel verdict signal.
- Tactics / per-move-quality narration — gated on client-side Stockfish or eval coverage expansion (SEED-012), out of v1.20 scope.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LLM-01 | Phase 102 (v1.23) | Pending |
| LLM-02 | Phase 102 (v1.23) | Pending |
| LLM-03 | Phase 102 (v1.23) | Pending |
| LLM-04 | Phase 102 (v1.23) | Pending |
| LLM-05 | Phase 102 (v1.23) | Pending |
| LLM-06 | Phase 102 (v1.23) | Pending |
| LLM-07 | Phase 102 (v1.23) | Pending |

**Coverage:** 7/7 v1 requirements mapped to Phase 999.7 (backlog — see ROADMAP). No orphans. The active v1.22 Maintenance milestone (Phases 100, 101) is standalone test-infra + dependency maintenance with no formal requirement IDs.

**Prior milestone (v1.19) closure:** PCTL-01..10 + TPCTL-01..07 + PRPCR-01..09 (26 requirements) all shipped 2026-05-27; archived at `.planning/milestones/v1.19-REQUIREMENTS.md`. The v1.19 ship surfaces per-(metric, ELO anchor, TC) cohort percentile fields on the endgames API which this milestone's LLM-05 consumes.
