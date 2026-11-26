# Project State: FlawChess

Kept by hand: the current position and the open threads carried forward. Update it together
with a phase's `SUMMARY.md` (see `CLAUDE.md` "Project Management"). The GSD-era state file,
with its accumulated decisions, quick-task log and metrics up to the v2.32 close, is archived
as `milestones/STATE-through-v2.32.md`.

Workflow: vanilla Claude Code on trial since 2026-11-26 (SEED-261122-v4c). Next phase number: 264.

## Current Position

Phase: 252 (Short Engine Line Repair Backfill, standalone, 6/10)
Plan: 252-07 (prod re-walk feed, benchmark line repair alongside, prod retag) and 252-10 (node-0 second-move pass)

Status: v2.30, v2.31 and v2.32 closed 2026-11-26; Phase 252 still executing

Last activity: 2026-11-26 - Closed v2.30 Blunder Check & Facepalm Score (247–251, 253–256), v2.31 Facepalm Refits & Move Quality (257–262) and v2.32 Foldable & Tablet Layouts (263), each tagged on a production forward-port with a GitHub release

Open threads carried forward (not blockers):

- Phase 263 accepted as is: WR-03 score bubble on an exhausted day, out-of-band picks at level about 1000 and 2300+ (263-UAT.md). Band draw at LIMIT 200 runs at 492 ms of a 500 ms budget on prod.

- Phase 261 share acceptance: about a week after the release, run `uv run python scripts/blunder_check/caught_rate.py --db prod --since <release date>` over the prod tunnel; accept when the verdict is accept (n >= 500, 95% interval overlapping [0.18, 0.26]); a fail below 0.18 points to an arm dropped somewhere (Pitfall 1).

- Phase 251 follow-ups: review WR-04 (Start within 600 ms of a settings edit drops the pending save), IN-02 (level options duplicated in three components), IN-03 (stale medal-cap comment); launch-notice copy says "Change the amount on the card" though the size lives in the settings row; owner should know assumption A8 (~3.6% sparse-weekday users who split modes across days can lose that day) and W-06 (puzzles on with no material still needs a warm-up session for the streak); low-urgency `drill_sessions (user_id, session_date)` index; `complete_session` could take `user_id` as defense in depth.

- Phase 246 WR-01: archive query has no `drill_solves` index, revisit near 300k rows.
- Phase 241 follow-ups: suspected bugs (INVENTORY §7.2) verified and captured as SEED-202 (start with the tier-4 lichess flag); §7.1 (50 seed candidates) still awaits an owner pass; review IN-01 (`frontend/CLAUDE.md` names two nonexistent components) open.
- Phase 240 after-change funnel not read yet: compare first-session abandonment against `milestones/v2.26-phases/240-.../240-FUNNEL-BEFORE.md`.
- Train grade audit (SEED-193 follow-up): tooling done 2026-10-09 as `temp/grade-audit/phone_grade_audit.py` (gitignored; reads `drill_solves.phone_grade` over the prod tunnel in a READ ONLY transaction, derives keys with the app's own `answer_key_for`, then a depth-18 spot check with local Stockfish). Run around 2026-10-22: `bin/prod_db_tunnel.sh` then `uv run python temp/grade-audit/phone_grade_audit.py --db prod --sample 300 --workers 8 > temp/grade-audit/report-$(date +%F).txt`. Smoke reading at n=140 records (report-smoke-2026-10-09.txt): server-graded moves 30/30 phone agreement; phone vs d18 31/40, phone `inaccuracy` the weak tier (2/8 confirmed). Too small to act on. Missing records skew toward fast Next presses and slow devices (236 WR-02, deferred).
- Pending reads: Train telemetry and the weekly-leaderboard effect (~2026-10-25, data from 2026-10-05); feedback-ask yield (`feedback.source = 'milestone_ask'` vs `floating_button`); Umami funnels on `train-explore-exit` go flat from release #404 (`train-sideline-fork` replaces it).
- Phase 224 guest levers: all four baselines are now in `reports/growth/guest-activation-baseline-2026-09-17.md` (Lever A metric 2 read 2026-10-03: 459/858 engaged home sessions, 53.5%); post-change readings not yet written up.
- Engine follow-ups: SEED-171 closed with its leftovers listed in `seeds/closed/SEED-171-...md` (cross-FEN Maia batching, non-root candidate cap); real-phone throughput for Phases 226/227 never measured.
- Phase 221: a forced only-move that sheds a piece can read as a sacrifice (game 1459049 ply 21); captured in `.planning/notes/2026-09-13-forced-only-move-tagged-sacrifice.md`, no action requested. Lever if sacrifice noise ever matters: lower `SACRIFICE_CLEARANCE_MAX_DEPTH` (4) and retag.

- TypeScript 7 adopted in Phase 232 (D-01, supersedes Phase 217 D-11) via Microsoft's side-by-side alias: `typescript` is `@typescript/typescript6` (TS6 JS API for typescript-eslint and eslint-plugin-sonarjs) and `@typescript/native` is `typescript@7` (the `tsc` in `npm run build`). Unwind once TS 7.1 ships its API and a typescript-eslint release accepts it (typescript-eslint#10940); never merge Renovate's `typescript-7.x` branch as-is (it installs 7 under the `typescript` name and breaks lint).
- Phase 217 device legs (iOS <16.4 no-SIMD, low-memory OOM, WebGPU adapter) deferred for lack of hardware (`v2.16-phases/217-.../217-UAT.md`).
- Phase 215's `Train.guestGate.test.tsx` full-run flake still deferred (`v2.15-phases/215-.../deferred-items.md`).
- SEED-163 (analytics population excludes bot games) captured 2026-09-04, unscheduled.
- SEED-164 resolved by Phase 220 (deployed 2026-09-11); the `disagreements >= 2` few-days watch on `opening_position_eval` is still open.
- SEED-158 re-scoped 2026-09-06: the iOS OOM half is closed (quick task 260906-p54); what remains is WebGPU failing on capable devices (iPhone 14 Pro iOS 26, Linux Brave/Chrome, a Windows 11 notebook), everyone silently on the wasm fallback. Collect the `[maia-worker]` console fallback lines first.
- Sentry 11 deploy watch (Phase 232): prod bundles `tracesSampleRate` 0.1 (read from the live bundle 2026-10-04), so v11 span streaming and the Web Vitals now built into `browserTracingIntegration` change span volume. After the release that ships Phase 232, check span usage in Sentry Stats and lower `VITE_SENTRY_TRACES_SAMPLE_RATE` in `.prod.env` if quota climbs. Source-map gap captured as SEED-189.

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-22 after Phase 259)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.
Current focus: **v2.30, v2.31 and v2.32 closed 2026-11-26**; phases 247–263 except 252 regrouped into v2.30 Blunder Check & Facepalm Score (247–251, 253–256, releases #464–#491), v2.31 Facepalm Refits & Move Quality (257–262, #492–#506) and v2.32 Foldable & Tablet Layouts (263 + layout quick tasks, #507–#515), each tagged with a GitHub release on a production forward-port. No open milestone. Phase 252 (SEED-261112-s4v) stays active: plans 07–10 (prod re-walk and retag, node-0 pass, benchmark repair, §5 zone refresh) remain, and it closes into whichever milestone is open when it finishes.
