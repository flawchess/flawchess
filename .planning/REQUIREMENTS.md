# Requirements: FlawChess — v1.17 Endgame Stats Card Redesign

**Defined:** 2026-05-12
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report.

**Milestone goal:** Replace three table-driven sections on the Endgames page with the established WDL + ScoreBullet card pattern from `EndgameStartVsEndSection.tsx` / `OpeningStatsCard.tsx`. Two-bullet doctrine (cohort + peer) on Conv/Parity/Recov surfaces preserves the self-calibrating opponent signal as a second bullet alongside the population-relative cohort comparison.

**Source:** `.planning/notes/endgame-stats-card-redesign.md`

## v1 Requirements

### Section 1 — Games with vs without Endgame (SEC1)

Replaces the `EndgamePerformanceSection` table on the Endgames page.

- [ ] **SEC1-01**: User sees two side-by-side cards on lg+ ("Games without Endgame" / "Games with Endgame"), stacked on mobile.
- [ ] **SEC1-02**: Each card shows a WDL bar (W/D/L distribution) for its game subset.
- [ ] **SEC1-03**: Each card shows the chess score `(W + 0.5·D)/n` with a cohort score bullet centered at 0.50, neutral band `[SCORE_BULLET_NEUTRAL_MIN, SCORE_BULLET_NEUTRAL_MAX]`, Wilson CI whiskers, Wilson p-value vs 0.50.
- [ ] **SEC1-04**: A full-width Score Gap footer bullet spans both cards: signed-diff axis (Yes − No), center 0, neutral band `[SCORE_GAP_NEUTRAL_MIN, SCORE_GAP_NEUTRAL_MAX]` from `generated/endgameZones.ts`.
- [ ] **SEC1-05**: Card score row includes an `InfoPopover` explaining the cohort comparison and the rating-tier confound on the cohort frame.
- [ ] **SEC1-06**: Significance gating follows the `EndgameStartVsEndSection` convention — font color painted only when `n ≥ MIN_GAMES_FOR_RELIABLE_STATS` AND `p < 0.05` AND value outside neutral band.
- [ ] **SEC1-07**: The legacy `EndgamePerformanceSection` table component is removed.

### Section 2 — Endgame Metrics (SEC2)

Replaces the `EndgameScoreGapSection` table and its 4-gauge strip with 4 side-by-side cards on lg+, stacked on mobile.

- [ ] **SEC2-01**: User sees 4 cards in order: Conversion, Parity, Recovery, Endgame Skill.
- [ ] **SEC2-02**: Conv / Parity / Recov cards share an identical layout: gauge → percent + games → WDL bar → cohort bullet vs p50 → peer bullet `You − Opp` vs 0.
- [ ] **SEC2-03**: Skill card has no WDL bar and no peer bullet — gauge + percent + cohort bullet vs p50 only.
- [ ] **SEC2-04**: Cohort bullet on each card uses the per-bucket p25/p50/p75 from `reports/benchmarks-2026-05-10.md` §171-177 (already encoded as `FIXED_GAUGE_ZONES.{conversion,parity,recovery}`); bullet neutral band matches gauge band exactly.
- [ ] **SEC2-05**: Cohort bullet sig test is Wilson p-value vs the per-bucket p50; significance gating per the standard convention.
- [ ] **SEC2-06**: Peer bullet uses the opponent's mirror-bucket rate: `Opp Conv = 1 − myRecov` on Conv card, `Opp Recov = 1 − myConv` on Recov card, `Opp Parity = 1 − myParity` on Parity card. Wald-z sig test vs 0 on the difference, gated on `MIN_OPPONENT_BASELINE_GAMES`.
- [ ] **SEC2-07**: Mirror-bucket peer baseline logic (`opponentRate` / `MIRROR_BUCKET` / `MIN_OPPONENT_BASELINE_GAMES`) is preserved (not deleted) and feeds the peer bullets.
- [ ] **SEC2-08**: Skill bullet p-value handling resolved per plan-phase decision (skip sig test on composite, or approximate via component CIs, or compute on raw underlying outcomes).
- [ ] **SEC2-09**: `InfoPopover` on each cohort bullet explains the global p50 frame and the rating-tier confound. `InfoPopover` on each peer bullet explains the filter-responsive mirror-bucket interpretation.
- [ ] **SEC2-10**: The legacy `EndgameScoreGapSection` table and its 4-gauge strip are removed.

### Section 3 — Endgame Type Breakdown (SEC3)

Replaces the section's `EndgameWDLChart` (grouped horizontal-bar overview) and extends `EndgameConvRecovChart` (per-type gauge-only cards) into full cards.

- [ ] **SEC3-01**: User sees 5 per-type cards in a 3-col grid on lg+, 2-col on sm, 1-col on mobile: rook, minor_piece, pawn, queen, mixed (pawnless hidden per `HIDDEN_ENDGAME_CLASSES`).
- [ ] **SEC3-02**: Each per-type card has side-by-side Conv + Recov gauges, a WDL bar, Conv cohort bullet, Recov cohort bullet, Conv peer bullet (`You − Opp` vs 0), Recov peer bullet (`You − Opp` vs 0), and a Games deep-link `/endgames/games?type=…`.
- [ ] **SEC3-03**: Cohort bullets use the per-type p25/p50/p75 from `PER_CLASS_GAUGE_ZONES[<class>].{conversion,recovery}`. Per-type explicit p50 must be available (either already in codegen or via `gen_endgame_zones_ts.py` / `app/services/endgame_zones.py` extension — confirm in plan-phase).
- [ ] **SEC3-04**: Peer bullets use the per-type mirror class baseline; gated on `MIN_OPPONENT_BASELINE_GAMES` per type. Sparse-n indicator shown when threshold not met.
- [ ] **SEC3-05**: Mobile-density check on real device performed during execute. Fallback path: drop the per-type peer bullets and keep only cohort bullets on Section 3 if scroll bloat is unacceptable.
- [ ] **SEC3-06**: The legacy `EndgameWDLChart` component is removed (used only in this section); cross-type comparison is reconstructable by scanning the per-card WDL bars.
- [ ] **SEC3-07**: `EndgameConvRecovChart` is extended into the full per-type card shell (no separate gauge-only chart component remains).

### Data Plumbing (DATA)

Frontend-only milestone, but two payload/codegen items need confirmation.

- [ ] **DATA-01**: Explicit per-type cohort p50 values are exposed to the frontend for Section 3 bullets (either already present in `PER_CLASS_GAUGE_ZONES` or added via `gen_endgame_zones_ts.py` / `endgame_zones.py` extension).
- [ ] **DATA-02**: Mirror-bucket peer rates (`opponentRate` for Conv / Parity / Recov in Section 2 and per-type in Section 3) are exposed on the `/api/endgames/overview` response payload (audit existing schema; extend only if not already present).

### Polish & Calibration (POLISH)

- [ ] **POLISH-01**: Peer bullet neutral band decision resolved per plan-phase — reuse `SCORE_GAP_NEUTRAL_MIN/MAX` across Conv / Parity / Recov, or introduce dedicated `CONV_DIFF_NEUTRAL_*` / `RECOV_DIFF_NEUTRAL_*` from the benchmarks `(myRate − mirrorRate)` distribution.
- [ ] **POLISH-02**: Gauge significance gating decision resolved per plan-phase — keep gauge always-colored and bullet font-gated (current convention), or extend gating to the gauge for visual consistency.
- [ ] **POLISH-03**: All `data-testid`, ARIA labels, and semantic HTML applied per CLAUDE.md browser automation rules.
- [ ] **POLISH-04**: Mobile parity verified at 375px for all three sections.

## v2 Requirements (deferred)

### Future Iteration

- **FUT-01**: Parity peer bullet redundancy review — demote to compact `You X% · Opp Y% · Diff +Z%` text row or drop, after v1.17 ships.
- **FUT-02**: Section 1 cards peer text row (compact `You X% · Opp Y% · Diff +Z%`) if cohort-only reads thin after v1.17 ships.
- **FUT-03**: Section 1 / `EndgameStartVsEndSection` deduplication — the "Endgame Yes" card's Score bullet duplicates the existing "What you do with it" tile bullet. Locked for v1.17.
- **FUT-04**: Cell-specific (rating × TC) cohort baselines — replace global p50/p25/p75 with per-cell anchors. Requires benchmarks-skill rework and per-cell `gen_endgame_zones_ts.py` extension.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend stat changes | Conv/Parity/Recov rates, cohort bands, WDL aggregates, score-gap, per-type, mirror-bucket rates all already exist on the response schema |
| New statistical methods | Reuses existing Wilson CI / p-value / `scoreConfidence` / `wilsonBounds` / `computeScoreConfidence` infra |
| Benchmark refresh | Uses the existing 2026-05-10 percentile table |
| Cell-specific cohort baselines | Deferred — a benchmarks-skill rework, not a frontend refactor |
| Removing `EndgameStartVsEndSection` despite Section 1 duplication | Locked for v1.17 to iterate on the layout; revisit after seeing the build |
| Per-class endgame Skill metric | Skill is a global composite only; per-class Skill is not specified in source notes |

## Traceability

Empty — populated by gsd-roadmapper during phase mapping.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated during roadmap creation) | | |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 0
- Unmapped: 30 (pending roadmap)

---
*Requirements defined: 2026-05-12*
*Source: `.planning/notes/endgame-stats-card-redesign.md`*
