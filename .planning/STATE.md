---
gsd_state_version: 1.0
milestone: v1.10
milestone_name: Advanced Analytics
status: verifying
last_updated: "2026-04-18T17:44:43.407Z"
last_activity: 2026-04-18
progress:
  total_phases: 15
  completed_phases: 7
  total_plans: 24
  completed_plans: 20
  percent: 83
---

# Project State: FlawChess

## Current Position

Phase: 57 (endgame-elo-timeline-chart) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-04-18

Progress: [██████████] 100% (4/4 v1.9 phases complete)

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.9 UI/UX Restructuring — layout improvements across desktop and mobile

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)

## Accumulated Context

### Roadmap Evolution

- Phase 59 added: Fix Endgame Conv/Even/Recov per-game stats so Conv+Even+Recov game counts sum to Games-with-Endgame total; drop obsolete admin-gated gauges + timeline
- Phase 62 added: Admin user impersonation — superusers can log in as any user, see stats from their perspective, perform any action, with impersonation session ending on logout (no last_login/last_activity updates). New Admin tab hosts impersonation selector and the existing Sentry Error Test section.

### Decisions

- v1.8: Bearer transport for guest JWTs (not CookieTransport) — avoids dual-transport complexity and OAuth redirect issues in Safari/Firefox ETP
- v1.8: Guest as first-class User row with is_guest=True — promotion is single-row UPDATE, no FK migration needed
- v1.8: Register-page promotion flow instead of separate PromotionModal — cleaner UX
- v1.8: Conversion optimization (CONV-01/02/03) deferred to post-launch Future Requirements
- v1.9 roadmap: Old v1.9 Advanced Analytics phases (49-51) renumbered to 52-54 under v1.10; new v1.9 phases start at 49
- v1.9 roadmap: Phase 50 (mobile subtab relocation) depends on Phase 49 — subtab placement TBD, needs discussion before planning
- [Phase 62]: Single auth_backend + ClaimAwareJWTStrategy wrapper — keeps every Depends(current_active_user) call site unchanged
- [Phase 62]: D-04 nested-impersonation rejection enforced indirectly via current_superuser dep (impersonation token resolves to non-superuser target)
- [Phase 62]: D-06 last_login freeze satisfied by construction — manual strategy.write_impersonation_token bypasses UserManager.on_after_login
- [Phase 62-admin-user-impersonation]: shouldFilter=false on cmdk Command is mandatory — disables client-side fuzzy filter so server search results are shown verbatim (T-62-13)
- [Phase 62-admin-user-impersonation]: knip.json ignores shadcn UI component files (command.tsx, popover.tsx, input-group.tsx) — shadcn ships full library surfaces; project-authored code still fully analyzed
- [Phase 62-admin-user-impersonation]: Logout button hidden during impersonation (not kept alongside pill) — pill × is sole logout control per D-20; hiding eliminates two-path confusion
- [Phase 57-endgame-elo-timeline-chart]: Phase 57-01: Inlined _endgame_skill_from_bucket_rows in endgame_service.py as a port of frontend endgameSkill() with a TODO to dedup when Phase 56's backend endgame_skill() lands
- [Phase 57-endgame-elo-timeline-chart]: Phase 57-01: Endgame ELO timeline piggybacks on /api/endgames/overview response (no new router endpoint), matching Phase 52 consolidation
- [Phase 57-endgame-elo-timeline-chart]: Phase 57-02: EndgameEloTimelineSection owns its own loading/error/empty branches; component-level isError UI reaches the LOCKED endgame-elo-timeline-error copy without depending on page-level error branch placement
- [Phase 57-endgame-elo-timeline-chart]: Phase 57-02: flatMap (not React.Fragment) used inside Recharts LineChart children so Recharts 2.15.x React.Children traversal reliably discovers every Line instance; custom legend via ChartLegend content prop owns the endgame-elo-legend-{combo_key} testid on button elements

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions
- **Flesh out Section 1 Milestones in generative AI** (docs) — narrative throughline for BA workshop agentic-engineering doc
- **Flesh out Section 3 FlawChess demo codebase** (docs) — add LOC/table/test counts + screenshot for 8-min workshop slot
- **Flesh out GSD sections 5.1 and 5.2** (docs) — expand why-structure and pick a specific phase for artifact walk-through
- **Fix Section 4 time budget math mismatch** (docs) — subsections sum to 32 min but TOC says 35
- **Resolve Karpathy agentic engineering attribution** (docs) — find primary source or soften the claim before presenting
- **Add visual direction for slide generation** (docs) — screenshots/diagrams/terminal recordings per section
- **Mark slide breaks and separate speaker notes** (docs) — split SLIDE vs SPEAKER NOTES for deterministic deck gen

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)

### Recently Resolved

- MMOB-01 (subtab placement TBD) resolved 2026-04-10: unified row holding Tabs | color toggle | bookmark | filter inside sticky wrapper but outside the board collapse region — see `.planning/phases/50-mobile-layout-restructuring/50-CONTEXT.md`

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260406-rzt | Guide new users post-import: success CTA, pulsing bookmark dot, improved empty state | 2026-04-06 | 4dbdea0 | [260406-rzt-guide-new-users-post-import-success-cta-](./quick/260406-rzt-guide-new-users-post-import-success-cta-/) |
| 260408-snn | Implement Opponent Strength filter (Any/+100/±100/-100) on Openings and Endgames pages | 2026-04-08 | ac883c6 | [260408-snn-implement-opponent-strength-filter-with-](./quick/260408-snn-implement-opponent-strength-filter-with-/) |
| 260411-fcs | Add Reset Filters button, deferred-apply hint, and pulsing modified indicator across filter panels | 2026-04-11 | c106fc9 | [260411-fcs-add-reset-filters-button-deferred-apply-](./quick/260411-fcs-add-reset-filters-button-deferred-apply-/) |
| 260411-ni2 | Global Reset (except color), uniform modified-dot via FILTER_DOT_FIELDS, secondary button, Openings mobile drawer cleanup | 2026-04-11 | 595bd3b | [260411-ni2-global-reset-filters-matchside-exempt-fr](./quick/260411-ni2-global-reset-filters-matchside-exempt-fr/) |
| 260411-p1c | Prototype Option A mobile layout for Opening Explorer (settings column + slim control row + underline tabs) | 2026-04-11 | b5b0c31 | [260411-p1c-prototype-option-a-mobile-layout-for-ope](./quick/260411-p1c-prototype-option-a-mobile-layout-for-ope/) |
| 260412-fis | Implement last_login defaults and last_activity tracking | 2026-04-12 | 2beabd3 | [260412-fis-implement-last-login-defaults-and-last-a](./quick/260412-fis-implement-last-login-defaults-and-last-a/) |
| 260413-pwv | Rename material buckets ahead/equal/behind → conversion/even/recovery + apply 4-ply preservation | 2026-04-13 | 9f24d5c | [260413-pwv-implement-conversion-even-recovery-label](./quick/260413-pwv-implement-conversion-even-recovery-label/) |
| 260413-qg0 | Apply Openings Stats responsive layout (desktop row / mobile stacked) to endgame WDL sections | 2026-04-13 | b399ac9 | [260413-qg0-apply-same-desktop-mobile-layout-from-op](./quick/260413-qg0-apply-same-desktop-mobile-layout-from-op/) |
| 260413-qq0 | Move Endgame Score Difference into Games with vs without Endgame as bullet chart and rename labels | 2026-04-13 | e4e2768 | [260413-qq0-move-endgame-score-difference-into-games](./quick/260413-qq0-move-endgame-score-difference-into-games/) |
| 260414-83b | Fix endgame tab code review: dedup timeline subquery, validate _INT_TO_CLASS lookup, replace row-index brittleness | 2026-04-14 | d4f975c | [260414-83b-fix-endgame-tab-code-review-dedup-timeli](./quick/260414-83b-fix-endgame-tab-code-review-dedup-timeli/) |
| 260414-ae4 | Apply 6-ply (3-move) endgame threshold uniformly across endgames tab; update info popovers and concepts section | 2026-04-14 | 0b50fe1 | [260414-ae4-for-all-analyses-on-the-endgames-tab-con](./quick/260414-ae4-for-all-analyses-on-the-endgames-tab-con/) |
| 260414-pv4 | Fix time pressure queries to use whole-game endgame rule (not per-class spans) + update endgame concepts docs | 2026-04-14 | f5dfee4 | [260414-pv4-fix-time-pressure-queries-to-use-whole-g](./quick/260414-pv4-fix-time-pressure-queries-to-use-whole-g/) |
| 260414-smt | Split time_control into base_time_seconds + increment_seconds; fix time pressure denominator to per-game base time; switch primary metric to % of base time with >2x clamp | 2026-04-14 | bc8b372 | [260414-smt-split-time-control-into-base-time-second](./quick/260414-smt-split-time-control-into-base-time-second/) |
| 260414-u88 | Aggregate time controls in Time Pressure vs Performance chart (drop tabs), relabel axes, clamp y-axis to 0.2–0.8 | 2026-04-14 | 08d86b1 | [260414-u88-aggregate-time-controls-in-time-pressure](./quick/260414-u88-aggregate-time-controls-in-time-pressure/) |
| 260415-uq9 | Add You vs Opp / Opp vs You / Diff / bullet-chart columns to Results by Endgame Type (desktop table + mobile cards) | 2026-04-15 | (uncommitted) | [260415-uq9-endgame-type-score-columns](./quick/260415-uq9-endgame-type-score-columns/) |
| 260416-pkx | Aggregate time pressure chart data in backend (pool across TCs); drop frontend aggregateSeries; add game-count symmetry test | 2026-04-16 | aa1bc56 | [260416-pkx-aggregate-time-pressure-data-in-backend-](./quick/260416-pkx-aggregate-time-pressure-data-in-backend-/) |
| 260416-r3n | Change Score to Score % consistently across endgame tab copy and info popovers | 2026-04-16 | 0b022b1 | [260416-r3n-change-score-to-score-consistently-acros](./quick/260416-r3n-change-score-to-score-consistently-acros/) |
| 260416-vcx | Switch per-type "Win Rate by Endgame Type" chart to weekly buckets (avg win rate per ISO week) to cut backend compute | 2026-04-16 | b208b31 | [260416-vcx-use-weekly-datapoints-with-median-win-ra](./quick/260416-vcx-use-weekly-datapoints-with-median-win-ra/) |
| 260416-w3q | Add weekly rolling-100 clock-diff timeline chart below Time Pressure at Endgame Entry table | 2026-04-16 | 6729143 | [260416-w3q-clock-diff-timeline-chart](./quick/260416-w3q-clock-diff-timeline-chart/) |
| 260417-br7 | Fix pytest warnings (JWT key length + httpx cookies) | 2026-04-17 | (uncommitted) | [260417-br7-fix-pytest-warnings-jwt-key-length-httpx](./quick/260417-br7-fix-pytest-warnings-jwt-key-length-httpx/) |
| 260418-nlh | Add Endgame Skill composite gauge (simple average of Conv/Parity/Recovery, 45-55 blue neutral) | 2026-04-18 | 021b4ac | [260418-nlh-add-endgame-skill-metric-as-simple-avera](./quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/) |

---
Last activity: 2026-04-18 - Completed quick task 260418-nlh: Add Endgame Skill composite gauge
| 2026-04-10 | fast | Match Global Stats mobile filter button size to Endgames | done |
| 2026-04-10 | ship | Phase 51 shipped — PR #42 merged into main | done |
| 2026-04-11 | fast | Preserve Openings board position across main tab navigation | ✅ |
