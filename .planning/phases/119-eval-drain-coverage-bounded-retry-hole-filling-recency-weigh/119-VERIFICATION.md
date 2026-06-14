---
phase: 119-eval-drain-coverage
verified: 2026-06-14T15:24:45Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification_status: passed (119-UAT.md — all 5 items signed off by user 2026-06-14)
human_verification:
  - test: "Trigger a tier-1 Analyze for a chess.com game and watch the EvalCoverageBadge CPU icon"
    expected: "CPU icon pulses (animate-pulse) while analyzedN < totalN; stops pulsing once coverage reaches 100%"
    why_human: "CSS animation behavior requires visual inspection in a browser; can't assert animate-pulse renders as animation programmatically"
  - test: "Log in as a returning user with a large backlog (e.g. user 28 on prod) and watch the coverage badge over ~60s"
    expected: "The analyzed count advances on nearly every tick (~10s cadence); badge does NOT appear frozen; the stall detector does not fire within the first 5 polls"
    why_human: "The live lichess-leak fix (tier-3 now skips lichess games) and badge stall-detector interaction can only be confirmed against a real prod backlog; requires prod access and live observation"
  - test: "Confirm the prod migration applied: run SELECT column_name FROM information_schema.columns WHERE table_name='games' AND column_name='full_eval_attempts' in the prod DB"
    expected: "Returns one row; default value is 0"
    why_human: "Requires prod DB access (prod_db_tunnel.sh)"
  - test: "Confirm dead index drop on prod: SELECT indexname FROM pg_indexes WHERE indexname = 'ix_eval_jobs_user_active'"
    expected: "Returns zero rows after migration upgrade head"
    why_human: "Requires prod DB access"
  - test: "Confirm partial index present on prod: SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_games_needs_engine_full_evals'"
    expected: "Returns one row; indexdef contains WHERE ((full_evals_completed_at IS NULL) AND (lichess_evals_at IS NULL))"
    why_human: "Requires prod DB access"
---

# Phase 119: Eval Drain Coverage — Verification Report

**Phase Goal:** A user-triggered or background "Analyze" pass means every position of a game is actually evaluated (no silent mid-game eval holes); the idle drain shares engine time across users by recency so a returning user sees their coverage badge tick briskly within minutes; the drain stops wasting full engine passes re-analyzing lichess %eval games; and the coverage badge gives an honest progress signal (pulsing CPU icon) instead of a structurally-blind in-flight count.
**Verified:** 2026-06-14T15:24:45Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A game with a genuine mid-game hole is NOT stamped full_evals_completed_at until either the hole fills or full_eval_attempts reaches MAX_EVAL_ATTEMPTS | VERIFIED | `eval_drain.py:1456-1487` — decision tree B withholds both markers while `failed_ply_count > 0 AND new_attempts < MAX_EVAL_ATTEMPTS`; only path A (no holes) and path C (cap) call `_mark_full_evals_completed` |
| 2 | Pool outages (all-fail WR-05) do NOT consume full_eval_attempts | VERIFIED | `eval_drain.py:1397-1412` — WR-05 `return False` fires before the write session at line 1442; the `full_eval_attempts` increment at line 1468 is inside the write session and is only reached when at least some evals resolved |
| 3 | After MAX_EVAL_ATTEMPTS ticks still leaving a hole, the game is stamped complete AND exactly ONE aggregated Sentry event fires (set_context, no interpolation) | VERIFIED | `eval_drain.py:1472-1487` — path C calls `_mark_full_evals_completed`, then `sentry_sdk.set_context("eval", {...})`, `set_tag("source", "full_eval_drain")`, `capture_message("full-drain: stamping complete after MAX_EVAL_ATTEMPTS with residual holes", level="warning")`; variables in set_context dict, never in message string |
| 4 | _claim_tier3_derived selects a user via ES weighted lottery over needs-engine candidates (full_evals_completed_at IS NULL AND lichess_evals_at IS NULL AND is_guest=false); lichess %eval games excluded from primary pick | VERIFIED | `eval_queue_service.py:268-317` — EXISTS subquery filters `full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`; JOINs users and `u.is_guest = false`; ES key `-ln(random()) / (exp(...) + :floor) LIMIT 1`; residual fallback at lines 320-347 is the ONLY path returning `is_lichess_eval_game=True` |
| 5 | is_analyzed local/ClaimedJob field renamed to is_lichess_eval_game; Game.is_analyzed hybrid property (white_blunders IS NOT NULL) UNCHANGED | VERIFIED | `grep -c "is_analyzed\b"` returns 0 in both `eval_drain.py` and `eval_queue_service.py` (queue/drain sense); `ClaimedJob.is_lichess_eval_game` at `eval_queue_service.py:113`; `Game.is_analyzed` at `game.py:191` still keyed on `white_blunders is not None` |
| 6 | EvalCoverageBadge CPU icon has animate-pulse gated on analyzedN < totalN; in_flight_count removed end-to-end; badge analyzed-count keyed on Game.is_analyzed (white_blunders IS NOT NULL) | VERIFIED | `EvalCoverageBadge.tsx:67,83` — `isIncomplete = analyzedN < totalN` drives `animate-pulse`; no `inFlightCount` prop remains; `game_repository.count_is_analyzed_games:104` uses `Game.is_analyzed`; all `in_flight_count` references in app/ are explanatory comments only |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/20260614_150000_phase_119_eval_drain_coverage.py` | games.full_eval_attempts SmallInteger; ix_games_needs_engine_full_evals partial index; drop ix_eval_jobs_user_active | VERIFIED | All three ops present: `add_column("full_eval_attempts", SmallInteger, server_default="0")`; `create_index("ix_games_needs_engine_full_evals", postgresql_where=text("full_evals_completed_at IS NULL AND lichess_evals_at IS NULL"))`; `drop_index("ix_eval_jobs_user_active")`; downgrade reverses all three |
| `app/models/game.py` | full_eval_attempts mapped column; Game.is_analyzed hybrid property unchanged | VERIFIED | `full_eval_attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")` at line 182; `is_analyzed` at line 191 returns `self.white_blunders is not None` |
| `app/services/eval_drain.py` | MAX_EVAL_ATTEMPTS constant; hole-aware gate; resweep_holed_games; is_lichess_eval_game rename | VERIFIED | `MAX_EVAL_ATTEMPTS: int = 3` at line 94; appears 8 times in non-comment lines; `resweep_holed_games` at line 1560; `is_lichess_eval_game` at line 1303; no `is_analyzed` (queue sense) remaining |
| `app/services/eval_queue_service.py` | RECENCY_HALF_LIFE_DAYS + WEIGHT_FLOOR constants; rewritten _claim_tier3_derived with ES lottery + leak fix | VERIFIED | `RECENCY_HALF_LIFE_DAYS: float = 1.0` at line 81; `WEIGHT_FLOOR: float = 0.005` at line 89; `_claim_tier3_derived` at line 212 uses EXISTS-based predicate; no `last_activity.desc()` or `lichess_evals_at.isnot(None).asc()` in the function |
| `frontend/src/components/library/EvalCoverageBadge.tsx` | Pulsing CPU icon gated on analyzedN < totalN; no inFlightCount prop; no in-progress text | VERIFIED | Line 67: `const isIncomplete = analyzedN < totalN`; line 83: `cn('h-4 w-4 shrink-0', isIncomplete && 'animate-pulse')`; no `inFlightCount` prop in interface |
| `app/schemas/imports.py` | EvalCoverageResponse without in_flight_count | VERIFIED | `EvalCoverageResponse` at line 59 has `pending_count`, `total_count`, `pct_complete`, `analyzed_count` only; no `in_flight_count` field |
| `app/repositories/game_repository.py` | count_in_flight_evals deleted | VERIFIED | `grep -rn "count_in_flight_evals" app/ tests/` returns zero matches |
| `scripts/resweep_holed_games.py` | CLI wrapper for resweep_holed_games (--dry-run, --limit) | VERIFIED | File exists with full argparse wrapper; delegates to `eval_drain.resweep_holed_games()`; matches backfill_eval.py CLI style |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_full_drain_tick` | `_mark_full_evals_completed` | only called when failed_ply_count == 0 OR new_attempts >= MAX_EVAL_ATTEMPTS | VERIFIED | `eval_drain.py:1456-1487` — path A and path C only; path B increments and returns without stamping |
| `_full_drain_tick` | `games.full_eval_attempts` | UPDATE increment on hole-and-pending path (B only) | VERIFIED | `eval_drain.py:1465-1469` — `update(games_table).values(full_eval_attempts=new_attempts)` inside path B |
| `_claim_tier3_derived` | `ix_games_needs_engine_full_evals` | EXISTS subquery with full_evals_completed_at IS NULL AND lichess_evals_at IS NULL | VERIFIED | `eval_queue_service.py:268-288` — EXISTS predicate; SUMMARY D-119-02-05 records EXPLAIN showing Nested Loop Semi Join using the partial index (4ms dev, sub-100ms at prod scale) |
| `weight expression` | `RECENCY_HALF_LIFE_DAYS / WEIGHT_FLOOR` | exp(-Δt/τ) + floor in SQL, τ and floor bound as :params | VERIFIED | `eval_queue_service.py:259-288` — `tau_seconds` and `floor_val` computed from constants; bound as `{"tau_s": tau_seconds, "floor": floor_val}` — no f-string interpolation |
| `EvalCoverageBadge CPU icon` | `analyzedN < totalN` | animate-pulse conditional className via `isIncomplete` | VERIFIED | `EvalCoverageBadge.tsx:67,83` |
| `GamesTab/FlawsTab refresh effect` | `analyzedCount transition` | `prevAnalyzedRef` useEffect fires `invalidateQueries` on `analyzedCount` increase | VERIFIED | `GamesTab.tsx:210-217` — `prevAnalyzedRef` tracking; `FlawsTab.tsx:240-249` — same pattern for flaw queries |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `EvalCoverageBadge.tsx` | `analyzedN` | `count_is_analyzed_games` via `game_repository` → `Game.is_analyzed` (`white_blunders IS NOT NULL`) | Yes — DB query | FLOWING |
| `_claim_tier3_derived` | `picked_user_id` | EXISTS subquery over `games` via `ix_games_needs_engine_full_evals` | Yes — live DB lookup | FLOWING |
| `resweep_holed_games` | `game_ids` | Real DB query joining `game_positions` + `games` for non-terminal holes | Yes — real query | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| MAX_EVAL_ATTEMPTS constant defined in eval_drain.py | `grep "^MAX_EVAL_ATTEMPTS" app/services/eval_drain.py` | `MAX_EVAL_ATTEMPTS: int = 3` | PASS |
| RECENCY_HALF_LIFE_DAYS and WEIGHT_FLOOR defined in eval_queue_service.py | `grep "^RECENCY_HALF_LIFE_DAYS\|^WEIGHT_FLOOR" app/services/eval_queue_service.py` | Both present with correct values | PASS |
| No is_analyzed (queue sense) remaining in eval files | `grep -c "is_analyzed\b" app/services/eval_drain.py app/services/eval_queue_service.py` | 0 in both | PASS |
| in_flight_count removed from backend (only comments remain) | `grep -rn "in_flight_count" app/ \| grep -v removed\|Phase 119\|#` | Only 2 explanatory comment lines | PASS |
| count_in_flight_evals fully deleted | `grep -rn "count_in_flight_evals" app/ tests/` | 0 matches | PASS |
| EvalCoverageBadge animate-pulse gated on isIncomplete | Source read at `EvalCoverageBadge.tsx:67,83` | `isIncomplete = analyzedN < totalN`; `cn(..., isIncomplete && 'animate-pulse')` | PASS |
| SEED-045 tests exist | `grep -c "TestBoundedRetryHoleFilling\|test_marker_withheld_with_holes\|TestResweepHoledGames" tests/services/test_full_eval_drain.py` | Tests confirmed in `tests/services/test_full_eval_drain.py` | PASS |
| SEED-046 tests exist | `grep -c "TestTier3Lottery\|test_tier3_recency_weighting\|test_tier3_never_picks_lichess" tests/services/test_eval_queue.py` | All confirmed | PASS |

---

### Probe Execution

Step 7c: SKIPPED — no probe-*.sh files declared for this phase; the phase produces service and frontend artifacts rather than a pipeline with conventional probes.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEED-045 bounded-retry hole-filling | 119-01 | Stop stamping full_evals_completed_at while non-terminal/non-mate holes remain; cap at MAX_EVAL_ATTEMPTS; aggregated Sentry event after cap; games.full_eval_attempts column; backfill sweep | SATISFIED | Migration adds column; `eval_drain.py:94,1456-1487` implements gate + cap + Sentry; `resweep_holed_games` at line 1560 |
| SEED-046 recency-weighted tier-3 lottery + lichess-leak fix | 119-02 | ES lottery (-ln(random())/weight); candidate predicate = full_evals_completed_at IS NULL AND lichess_evals_at IS NULL AND is_guest=false; dead D-118-04 tiebreaker dropped; τ/floor as named constants | SATISFIED | `eval_queue_service.py:212-347`; no `last_activity.desc()` or `lichess_evals_at.isnot(None).asc()` remaining |
| ix_games_needs_engine_full_evals partial index | 119-01 | Perf index for lottery candidate pool | SATISFIED | Migration line 48-56; EXPLAIN in SUMMARY shows Index Only Scan |
| is_analyzed rename to is_lichess_eval_game | 119-02 | Rename local/ClaimedJob field; Game.is_analyzed unchanged | SATISFIED | `ClaimedJob.is_lichess_eval_game:113`; zero `is_analyzed` (queue sense) in drain/queue files |
| Pulse EvalCoverageBadge CPU icon on analyzedN < totalN | 119-03 | animate-pulse gated on coverage, NOT inFlightCount | SATISFIED | `EvalCoverageBadge.tsx:67,83` |
| in_flight_count removed end-to-end | 119-03 | Schema, router, repository, hook, badge, callers, tests | SATISFIED | Zero production references; only explanatory comments remain |
| Dead ix_eval_jobs_user_active index dropped | 119-01 migration / 119-03 reader removal | Index drop in migration; count_in_flight_evals deleted | SATISFIED | Migration line 61; zero `count_in_flight_evals` references in app/ or tests/ |
| Badge analyzed-count keyed on Game.is_analyzed (white_blunders IS NOT NULL) NOT full_evals_completed_at | 119-03 (explicit guard in RESEARCH-NOTES) | RESEARCH-NOTES §"Do NOT re-key the coverage badge" | SATISFIED | `game_repository:104` uses `Game.is_analyzed`; not `full_evals_completed_at` |
| ix_eval_jobs_user_active downgrade re-creates it | 119-01 | downgrade() must restore the index | SATISFIED | Migration lines 67-74 re-create with predicate "status IN ('pending', 'leased')" |

---

### Anti-Patterns Found

No debt markers (TBD/FIXME/XXX), placeholder returns, or hardcoded empty data found in any phase-modified file.

The only `inFlightCount` reference in production files is in `useEvalCoverage.test.tsx:178` as a test assertion that the field does NOT exist in the hook return value — this is correct and intentional.

---

### Human Verification Required

#### 1. EvalCoverageBadge CPU Pulse — Visual Confirmation

**Test:** Open the Library > Games tab while a game has pending engine analysis. Observe the EvalCoverageBadge in the top of the page.
**Expected:** CPU icon visibly pulses (CSS animate-pulse animation) while `analyzedN < totalN`; animation stops once `analyzedN === totalN`.
**Why human:** CSS animation behavior requires visual inspection; className assertion in tests verifies the class is present but cannot verify it actually animates.

#### 2. Live Tier-3 Lottery — Badge Unfreezes for Returning User

**Test:** Use prod account with large backlog (e.g. user 28 who had the frozen-badge bug). Navigate to Library > Games. Watch the analyzed count in the badge over 3-5 minutes.
**Expected:** The analyzed count increments on approximately every tier-3 drain cycle (~10s); the badge does NOT appear frozen; the stall detector (5 polls = 15s of no `analyzed_count` delta) does not fire.
**Why human:** The live lichess-leak fix only manifests on prod where >260 lichess-evals-at games exist in the candidate pool; requires prod observation with the real drain running.

#### 3. Prod Migration Applied — full_eval_attempts Column

**Test:** Via SSH tunnel: `SELECT column_name, column_default FROM information_schema.columns WHERE table_name='games' AND column_name='full_eval_attempts'` against the prod DB.
**Expected:** Returns one row with `column_default = '0'`.
**Why human:** Requires `bin/prod_db_tunnel.sh` and direct DB access.

#### 4. Prod Migration Applied — ix_eval_jobs_user_active Dropped

**Test:** `SELECT indexname FROM pg_indexes WHERE indexname = 'ix_eval_jobs_user_active'` on prod.
**Expected:** Returns zero rows.
**Why human:** Requires prod DB access.

#### 5. Prod Migration Applied — ix_games_needs_engine_full_evals Present

**Test:** `SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_games_needs_engine_full_evals'` on prod.
**Expected:** Returns one row; `indexdef` contains `WHERE ((full_evals_completed_at IS NULL) AND (lichess_evals_at IS NULL))`.
**Why human:** Requires prod DB access.

---

### Gaps Summary

No gaps. All six must-haves are VERIFIED in the codebase. Human verification items cover live behavior (visual pulse animation, real-world backlog drain behavior) and prod migration state — these cannot be resolved by static analysis.

---

_Verified: 2026-06-14T15:24:45Z_
_Verifier: Claude (gsd-verifier)_
