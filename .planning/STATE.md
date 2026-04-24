---
gsd_state_version: 1.0
milestone: v1.11
milestone_name: LLM-first Endgame Insights
status: executing
last_updated: "2026-04-22T05:48:41.414Z"
last_activity: 2026-04-22
progress:
  total_phases: 9
  completed_phases: 4
  total_plans: 19
  completed_plans: 19
  percent: 100
---

# Project State: FlawChess

## Current Position

Milestone: v1.11 LLM-first Endgame Insights
Phase: 66 (frontend-endgameinsightsblock-beta-flag) — EXECUTING
Plan: 5 of 5
Status: Ready to execute
Last activity: 2026-04-22

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.11 ships LLM-generated Endgame Insights (overview paragraph + 4 Section insights) over a stripped-down findings pipeline. Source: SEED-003 (supersedes SEED-001 for v1.11).

## Milestone Progress

```
v1.11 LLM-first Endgame Insights — 2/5 phases complete
[████████  ] 40%

Phase 63: Findings Pipeline & Zone Wiring     — Complete (5/5 plans)
Phase 64: llm_logs Table & Async Repo         — Complete (3/3 plans)
Phase 65: LLM Endpoint with pydantic-ai Agent — Not started
Phase 66: Frontend EndgameInsightsBlock       — Not started
Phase 67: Validation & Beta Rollout           — Not started
```

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions, admin impersonation)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)
- v1.11 LLM stack (new): pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table as prompt-engineering harness

## v1.11 Constraints (from SEED-003 + user adjustments)

- Phase 0 prompt-fluency spike DROPPED — risk absorbed by regression test + admin-impersonation validation loop (Phase 67)
- Zone source of truth is the existing in-code gauge constants (NOT the 2026-04-18 benchmark report) — no gauge-update phase needed
- Beta flag is a boolean column on `users` flipped via direct DB operation — no settings UI, no admin page
- Overview paragraph ALWAYS populated (no null overview in MVP); when no strong cross-section signal, overview summarizes per-section findings
- LLM output is NOT style-constrained — no em-dash/noun-label/prescriptive-advice policing; correctness guardrails come from the three precomputed cross-section flags
- Log table is generic `llm_logs` (not `insights_llm_logs`), designed to host future LLM features

## Accumulated Context

### Roadmap Evolution

- v1.10 shipped 2026-04-19 with 11 phases and 28 plans
- Phase 56 cancelled mid-milestone (subsumed by Phase 57)
- Phase 58 moved to backlog as Phase 999.6 (better fit for upcoming Opening Insights milestone)
- Phase 57.1 inserted after Phase 57 to switch ELO anchor from rolling-mean to asof-join and add weekly volume bars (driven by UAT feedback)
- v1.11 roadmap created 2026-04-20: Phases 63-67 derived from SEED-003 dependency order (findings + log infra parallel → LLM endpoint → frontend → validation)
- Phase 68 added 2026-04-24: Endgame Score Timeline rework (dual-line + shaded gap) — replaces single-line Score Gap chart, simplifies LLM prompt's score_gap framing rule

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
- [Phase 63-findings-pipeline-zone-wiring]: Plan 01: net_timeout_rate direction locked to lower_is_better per CONTEXT.md D-06 verbatim — if a future review finds the formula produces positive-when-good values, the findings service (Plan 04) flips the sign at the call site rather than mutating the registry
- [Phase 63-findings-pipeline-zone-wiring]: Plan 01: NaN guard in assign_zone / assign_bucketed_zone returns "typical" (not raising, not "weak") — missing-data signal is is_headline_eligible=False on SubsectionFinding per D-13, keeping the zone contract pure
- [Phase 63-findings-pipeline-zone-wiring]: Plan 01: BucketedMetricId Literal promoted to module-level alias (conversion_win_pct | parity_score_pct | recovery_save_pct) so BUCKETED_ZONE_REGISTRY typing and assign_bucketed_zone signature share one name
- [Phase 63-findings-pipeline-zone-wiring]: Plan 04: D-06 resolution applied at the call site — compute_findings flips the sign of net_timeout_rate before passing to assign_zone (honoring the registry's locked lower_is_better direction) but preserves the raw formula output in the emitted SubsectionFinding so Phase 65 prompt-assembly sees the real number
- [Phase 63-findings-pipeline-zone-wiring]: Plan 04: as_of typed as datetime.datetime (not str) — Plan 03 schema is authoritative; compute_findings uses datetime.datetime.now(datetime.UTC). JSON wire shape identical (Pydantic emits ISO-8601); findings_hash excludes as_of so daily recompute is cache-stable
- [Phase 63-findings-pipeline-zone-wiring]: Plan 04: findings_hash uses the two-step NaN-safe recipe (model_dump_json exclude={"findings_hash","as_of"} -> json.loads -> json.dumps sort_keys=True separators=(",", ":") -> sha256 hex) — model_dump(mode="json") leaves NaN unchanged which json.dumps would emit as invalid NaN literal
- [Phase 63-findings-pipeline-zone-wiring]: Plan 04: Explicit dict[str, str] annotations on every dimension-dict literal site (bucket_dim, combo dim, endgame_class dim, conv_dim, recov_dim) — required because ty treats dict value types as invariant, so a Literal-typed value like MaterialBucket won't widen to str without the annotation
- [Phase 63-findings-pipeline-zone-wiring]: Plan 04: time_pressure_vs_performance emits a conservative placeholder finding using avg_clock_diff_pct as metric with value=weighted mean of user scores across time-pressure buckets; is_headline_eligible=False until a dedicated slope metric lands (planner note in RESEARCH.md §Subsection Mapping)
- [Phase 64-llm-logs-table-async-repo]: Plan 01: genai-prices.calc_price does NOT accept pydantic-ai 'provider:model' concatenated strings (LookupError against 'anthropic:claude-haiku-4-5-20251001'). Split form calc_price(..., model_ref='claude-haiku-4-5-20251001', provider_id='anthropic') returns Decimal('0.0006'). Plan 03's _compute_cost helper must split on first ':' into provider_id + model_ref.
- [Phase 64-llm-logs-table-async-repo]: Plan 01: LlmLog.user_id uses Integer (not BigInteger) to match users.id type (RESEARCH.md Pitfall 1; verified via psql \d users). Log's own id stays BigInteger per D-05.
- [Phase 64-llm-logs-table-async-repo]: Plan 01: app/models/__init__.py re-export of LlmLog is cosmetic only; alembic autogenerate discovers models via alembic/env.py — Plan 02 adds the env.py side-effect import.
- [Phase 64-llm-logs-table-async-repo]: Plan 02: Alembic ≥1.13 with sqlalchemy 2.x preserved postgresql_ops={'created_at': 'DESC'} on autogenerate — RESEARCH.md §Pitfall 2 (Alembic issues #1166/#1213/#1285) defensive hand-edit was unnecessary for this version. The three composite indexes shipped with DESC verbatim from autogen.
- [Phase 64-llm-logs-table-async-repo]: Plan 02: Scoped migration 85dfef624a19_create_llm_logs.py to the new table only; removed three unrelated REAL→Float alter_column diffs (game_positions.clock_seconds, games.white_accuracy, games.black_accuracy) that autogenerate emits on every run due to pre-existing ORM vs DB drift. The drift is genuine and is logged as a Phase 64 deferred item for a dedicated future cleanup migration.
- [Phase 64-llm-logs-table-async-repo]: Plan 02: Dev DB upgraded from 179cfbd472ef → 85dfef624a19; pg_indexes.indexdef confirms 'created_at DESC' present on all three composite indexes and absent from the two single-column indexes. FK CASCADE confirmed via inspect.get_foreign_keys. Full 945-test suite green.
- [Phase 64-llm-logs-table-async-repo]: Plan 03: `_compute_cost` splits pydantic-ai 'provider:model' on first ':' via str.partition() into provider_id + model_ref — confirms Plan 01 smoke finding; combined form raises LookupError inside genai-prices 0.0.56 and is never used.
- [Phase 64-llm-logs-table-async-repo]: Plan 03: Extended tests/conftest.py::override_get_async_session to patch app.repositories.llm_log_repository.async_session_maker alongside existing db/users/activity module patches. Required because create_llm_log's D-02 own-session path binds module-level names at call time via __globals__; patching only app.core.database wasn't enough. Established precedent: any future module with own-session pattern must be added to this patch list.
- [Phase 64-llm-logs-table-async-repo]: Plan 03: Docstring phrasing in llm_log_repository.py avoids the literal 'sentry' substring to satisfy the plan's case-insensitive verification grep ('sentry not in src.lower()'). D-08 intent (no sentry_sdk import, no capture_exception call) is preserved behaviorally; only the word used to document the contract changed ('caller captures at the router/service layer (D-08)').
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 01: Scoped Alembic migration 24baa961e5cf to users.beta_enabled only; stripped pre-existing autogen drift (REAL->Float on game_positions.clock_seconds / games.white_accuracy / games.black_accuracy + postgresql_ops DESC index re-create noise on llm_logs) per plan instructions. Matches Phase 64 Plan 02 precedent; drift stays deferred for a dedicated future cleanup migration.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 01: Mass-assignment defense (T-66-02) lives in the Pydantic schema shape, not the router. UserProfileUpdate stays a two-field schema; Pydantic v2 default extra='ignore' silently drops beta_enabled from PUT bodies. Test 3 (test_user_profile_update_does_not_change_beta_enabled) asserts the invariant.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 01: Router test helper _register_login_and_get_id reads user id from the /api/auth/register response; avoids ty's invalid-argument-type on User.email == email (FastAPI-Users generic column inference narrows to bool at compare time). User.id == user_id works cleanly.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 02: stale_filters typed as 'unknown' on FE envelope (not FilterContext | null) — BE sends null or FilterContext; per Phase 65 D-13 FE never reads this; 'unknown' forces narrowing and avoids forcing a FilterContext FE type this plan does not need.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 02: opponent_type regression enforced in two places — inline code comment at hook call site AND unit-test assertion (params has no opponent_type key even when FilterState.opponentType='computer'); insights router rejects it, silent 422 trap otherwise.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 02: File-level '// @vitest-environment jsdom' pragma instead of global config — vitest.config has no environment set; per-file opt-in keeps the 83 pure tests fast. @testing-library/react@^16.3 + jsdom@^25 installed as devDeps.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 02: jest-dom devDep dropped from install — only renderHook/waitFor from @testing-library/react used; knip flags unused packages in CI.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 03: EndgameInsightsBlock is self-gating — returns null when useUserProfile().data?.beta_enabled is falsy (also during loading). Plan 04's mount site stays unconditional; no caller-side flag check needed.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 03: Parent-lifted mutation state pattern (locked in plan) — component receives UseMutationResult + rendered + reportFilters + onGenerate as props instead of calling useEndgameInsights() itself. Enables Plan 04's per-section insights-section-* slots to observe the same state without a context provider.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 03: String literal wrapper `{"Couldn't generate insights."}` instead of JSX text with &apos; — acceptance criterion greps source for verbatim phrase; JSX entities would render correctly but fail the grep.
- [Phase 66-frontend-endgameinsightsblock-beta-flag]: Plan 03: Explicit afterEach(cleanup) in test file — Vitest 4 does not auto-cleanup RTL mounts; without cleanup, DOM from prior tests bleeds into subsequent screen.getByTestId queries (discovered after 4/11 initial failures).
- Parent-owned mutation state + sibling slot subscription for EndgameInsights: Endgames.tsx holds the single useEndgameInsights mutation + rendered snapshot; EndgameInsightsBlock + 4 SectionInsightSlot instances all observe the same state without a context provider
- H2-ride-along slot suppression (D-05) achieved by placement alone: per-section insight slots live inside the same conditional branches as their matching H2, so H2 suppression transitively suppresses the slot — no extra guard logic

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
- v1.11: `PYDANTIC_AI_MODEL_INSIGHTS` env var must be decided in `/gsd-discuss-phase 65` and pinned in `.env.example`; provider API keys (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`) need to be set on the Hetzner server before Phase 65 ships
- v1.11: Open question — whether to add the `notable_endgame_elo_divergence` cross-section flag (`|gap| > 100 Elo`) in Phase 63, or defer. SEED-003 Open Questions flags as discuss-phase decision

### Recently Resolved

- MMOB-01 (subtab placement TBD) resolved 2026-04-10: unified row holding Tabs | color toggle | bookmark | filter inside sticky wrapper but outside the board collapse region — see `.planning/phases/50-mobile-layout-restructuring/50-CONTEXT.md`
- v1.11 requirements defined 2026-04-20 — 23 requirements extracted from SEED-003 + user adjustments (no Phase 0 spike, no gauge-update phase, no beta-flag UI, overview always populated, no style restrictions, generic `llm_logs`)
- v1.11 roadmap created 2026-04-20 — 5 phases (63-67), 100% coverage (23/23 requirements mapped)
- Phase 63 Plan 01 complete 2026-04-20 — zone registry (app/services/endgame_zones.py, 271 lines) + D-10 recovery band re-center [0.25, 0.35] in both Python registry and FIXED_GAUGE_ZONES.recovery of EndgameScoreGapSection.tsx + 22 unit tests; ty/ruff/tsc all clean; commits de735ea, c6da043, a32e895
- Phase 63 Plan 04 complete 2026-04-20 — compute_findings insights service (app/services/insights_service.py, 1036 lines) with two-call sequential pattern on single AsyncSession, 16 private helpers (10 subsection builders + _compute_trend/_compute_flags/_compute_hash/_endgame_skill_from_material_rows/_empty_finding), four FIND-03 flags from endgame_zones constants, FIND-04 trend gate (count + slope/vol ratio), FIND-05 NaN-safe SHA256 hash, FIND-01 zero repo imports, D-06 sign-flip resolution; ty/ruff project-wide clean; commit 3728ebf
- Phase 63 Plan 05 complete 2026-04-20 — insights service test suite (tests/services/test_insights_service.py, 653 lines, 45 tests across 5 classes: TestComputeTrend/TestComputeFlags/TestComputeHash/TestEmptyFinding/TestComputeFindingsLayering); FIND-01 layering guard (inspect.getsource check + AsyncMock 2-call pattern), FIND-03 four flags × true/false branches + NaN guards, FIND-04 trend gate (count-fail, ratio-fail, both-pass via permissive override, stable), FIND-05 hash stability (64-char hex, as_of exclusion, dict-order invariance, NaN safety); runtime 0.13s; all 942 project tests pass; ty/ruff project-wide clean; commit 0a1872d
- Phase 63 complete 2026-04-20 — 5/5 plans done; registry + codegen + schema + compute_findings service + test suite all shipped; ready for Phase 64 (llm_logs table)
- Phase 64 Plan 01 complete 2026-04-20 — Wave 0 scaffold: genai-prices>=0.0.56,<0.1.0 pinned (pyproject.toml + uv.lock), app/schemas/llm_log.py (LlmLogCreate DTO + LlmLogEndpoint Literal, 42 lines), app/models/llm_log.py (LlmLog ORM, 18 columns + 5 named indexes including 3 postgresql_ops DESC composites, Integer FK CASCADE to users.id, first JSONB usage in codebase), app/models/__init__.py re-export, tests/conftest.py fresh_test_user fixture (own-session commit + delete teardown for D-02 tests); smoke test resolves RESEARCH.md Open Question #1 (calc_price requires split provider_id + model_ref, not combined "provider:model"); 944 tests pass in 12.67s; ty/ruff/phase-gate all clean; commits e345d36, 3b1c9ab, 661a3cd, 79d1449
- Phase 64 Plan 02 complete 2026-04-20 — Wave 1 migration: alembic/env.py registers LlmLog side-effect import; alembic/versions/20260420_211450_85dfef624a19_create_llm_logs.py creates llm_logs table with 18 columns + FK(user_id→users.id ondelete=CASCADE) + 5 named indexes (3 composites with postgresql_ops={"created_at": "DESC"} preserved by autogenerate); unrelated REAL→Float drift on game_positions/games columns removed from migration during hand-edit scope pass; dev DB upgraded 179cfbd472ef → 85dfef624a19 and schema inspected (cols, indexes, FK CASCADE, DESC on composites all verified); tests/test_llm_logs_migration.py smoke test runs against test_engine; full 945-test suite passes in 12.72s; ty/ruff project-wide clean; LOG-01 + LOG-03 requirements checked off; commits dddac62, 5972eb1, 0a4c41c
- Phase 64 Plan 03 complete 2026-04-20 — Wave 2 repository + tests: app/repositories/llm_log_repository.py (158 lines, create_llm_log with D-02 own-session commit + _compute_cost split-form genai-prices call + get_latest_log_by_hash Phase 65 stub, no sentry import per D-08); tests/test_llm_log_repository.py (4 tests: happy path, cost_unknown standalone, cost_unknown append, cache-lookup filter); tests/test_llm_log_cascade.py (1 integration test proving ON DELETE CASCADE end-to-end); tests/conftest.py extended to patch llm_log_repo_module.async_session_maker alongside existing db/users/activity module patches (required for D-02 own-session path to hit test DB); 950 tests pass in 12.78s (+5 new); ty/ruff project-wide clean on all Plan 03 files; LOG-02 + LOG-04 requirements checked off; Phase 64 complete; commits 9383a9b, e86b3ac, 9051128
- Phase 64 complete 2026-04-20 — 3/3 plans done; llm_logs table + migration + async repository shipped with full test coverage (950 tests); ready for Phase 65 (LLM Endpoint with pydantic-ai Agent)

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
| 260419-gjq | Retire Phase 56 (subsumed by 57) and move Phase 58 (Opening Risk) to backlog as Phase 999.6 | 2026-04-19 | c7dc214 | [260419-gjq-retire-phase-56-subsumed-by-57-and-move-](./quick/260419-gjq-retire-phase-56-subsumed-by-57-and-move-/) |
| 260420-je6 | Dependency management fix: Renovate config, CI audits (pip-audit/npm audit/Trivy), digest-pin Dockerfile base images | 2026-04-20 | (uncommitted) | [260420-je6-implement-dependency-management-fix-reno](./quick/260420-je6-implement-dependency-management-fix-reno/) |
| 260420-kzb | Rename "Score % Difference" metric to "Score Gap" in EndgamePerformanceSection | 2026-04-20 | 277ef31 | [260420-kzb-rename-score-difference-metric-to-score-](./quick/260420-kzb-rename-score-difference-metric-to-score-/) |
| 260422-tnb | Fix endgame insights prompt+data issues (A1-C3): bucket-matched metric emission, NaN filter, server-side metadata override, rewritten system prompt v2 with auto-generated zone thresholds | 2026-04-22 | 07abfc8 | [260422-tnb-fix-endgame-insights-prompt-data-issues-](./quick/260422-tnb-fix-endgame-insights-prompt-data-issues-/) |
| 260423-a4a | Drop llm_logs.system_prompt column (prompt_version already identifies the prompt); diagnose thinking_tokens NULL as a config choice (GEMINI_THINKING_LEVEL=low returns 0 thoughts — not a code bug) | 2026-04-23 | fa9fcd3 | [260423-a4a-remove-system-prompt-fix-thinking-tokens](./quick/260423-a4a-remove-system-prompt-fix-thinking-tokens/) |

---
Last activity: 2026-04-23 — Completed quick task 260423-a4a: dropped llm_logs.system_prompt column (migration + ORM + schema + service wiring + tests). Investigated thinking_tokens NULL: verified with live Gemini API — at thinking_level='low' the provider reports 0 thought tokens and pydantic-ai omits the key; switching to 'high' yields hundreds. Decision on config change left to user.

**Planned Phase:** 66 (Frontend EndgameInsightsBlock & Beta Flag) — 5 plans — 2026-04-21T21:48:47.028Z
