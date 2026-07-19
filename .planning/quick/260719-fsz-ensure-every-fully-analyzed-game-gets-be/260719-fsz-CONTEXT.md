# Quick Task 260719-fsz: Ensure every fully-analyzed game gets best/gem move coverage (lichess-eval + guest games) - Context

**Gathered:** 2026-07-19
**Status:** Ready for planning

<domain>
## Task Boundary

Ensure every game we have enough data to classify best/gem (bestmove) moves for actually gets `best_moves_completed_at` stamped and `game_best_moves` rows — closing two coverage holes discovered this session in the best-move (tier-4b) pipeline. Backend-only (`app/services/eval_queue_service.py`, `app/services/eval_apply.py`, `app/services/eval_drain.py`, `app/services/best_move_candidates.py`, plus tests). No Alembic migration (predicate/logic changes only). No frontend.

### The two populations (measured on prod 2026-07-19)

**Population A — guest lichess-eval games (~18,882 across 27 guest users; incl. prod game 1247936):**
`full_pv_completed_at IS NULL`, `lichess_evals_at IS NOT NULL`, `best_moves_completed_at IS NULL`. They have only imported lichess evals, no engine PV pass, so they genuinely need the FULL engine-analysis path. They already match the tier-3 residual lichess-eval fallback (`_claim_tier3_derived`, `eval_queue_service.py` ~lines 539-552) on every condition EXCEPT the inlined `is_guest = false` clause (line 545, QUEUE-08).

**Population B — orphaned non-guest lichess-eval games (~12,643):**
`full_pv_completed_at IS NOT NULL`, `lichess_evals_at IS NOT NULL`, `best_moves_completed_at IS NULL`. They fall in a coverage hole: the minimal tier-4b lane (`_claim_tier4_bestmove`) excludes lichess-eval games (D-03, `lichess_evals_at IS NULL` clause), and the tier-3 residual excludes full_pv-stamped games (`full_pv_completed_at IS NULL` clause). **Neither lane will ever pick them.**

### Root cause of Population B (confirmed)

The heavy path stamps `best_moves_completed_at` ONLY IF `maia_available` (guardrail, `eval_apply.py` ~782-783). Games processed during a Maia-down window got `full_pv`/`full_evals` stamped but `best_moves` skipped; once `full_pv` is set they become permanently ineligible for re-pick. Prod distribution of the 12,643 by `full_evals_completed_at` day: ~72% (9,045) cluster on 2026-06-22/23 (a Maia-down window), but a continuing tail runs through 2026-07-10 (hundreds/day). **So it is both a historical spike AND an ongoing leak** — recurrence prevention is in scope, not optional.

</domain>

<decisions>
## Implementation Decisions

### Scope — fix BOTH populations
Do Population A (guests) AND Population B (non-guest orphans) in this task. (User chose "Both B and guests (A)".)

### Guest data — process them
Guest games are retained long enough that analysis delivers lasting value, so the full engine pass on ~18.9k guest games is worth it. Reverse QUEUE-08 for the lichess-eval residual lane. (User chose "Retained — worth it".)

### Population B fix — unified self-healing lane (NOT a one-off script)
Extend the cheap minimal best-move lane (`_claim_tier4_bestmove` → `_tier4b_minimal_drain_tick`) so it also picks lichess-eval games that have `full_pv_completed_at IS NOT NULL` and `best_moves_completed_at IS NULL`. This drains the existing 12,643 via the cheap lane (reads existing `game_positions` data, NO re-analysis) AND auto-heals any FUTURE Maia-outage orphans — so no separate one-off backfill script and no separate source-fix is needed for the recurrence; the self-healing lane IS the recurrence fix. (User chose "Unified self-healing lane".)

### Population A route — relax the guest clause on the heavy residual lane
Guests in Population A have `full_pv IS NULL` (no engine data yet), so they CANNOT use the minimal lane — they need the heavy `_claim_tier3_derived` residual fallback (full every-ply MultiPV-2 pass). The fix for A is relaxing the inlined `is_guest = false` clause at `eval_queue_service.py:545`.

### Guest orphan self-heal (interaction of A + B)
Once guests are opened to the heavy residual (A), a guest game processed during a future Maia-down window would orphan exactly like Population B. For consistency, the unified minimal lane (B) should also cover guest full_pv-set lichess games so guest orphans self-heal too. NOTE: the minimal tier-4b lane draws its user pick from `_es_weighted_user_pick` (`eval_queue_service.py:322`), which has its own `is_guest = false` filter shared with tier-3 / tier-4-blob. Opening guests to the minimal lane must be done WITHOUT opening guests into the tier-3 / tier-4-blob bulk drains — parameterize the guest filter (add an `include_guests`/predicate arg) rather than flipping the shared literal. **Planner: confirm whether covering guest orphans in the minimal lane is worth the added surface, or whether guest-orphan self-heal is a rare-enough edge to leave the guest minimal-lane predicate closed and rely on Maia being up during guest heavy-path processing. Recommend covering it for consistency, but flag the trade-off.**

</decisions>

<specifics>
## Specific Ideas / Load-bearing constraints (from this session's code trace)

- **DO NOT re-gate the tier-3 residual fallback on `best_moves_completed_at IS NULL`.** That residual returns `TIER_IDLE_BACKLOG` and routes through the FULL every-ply MultiPV-2 engine pass + full flaw reclassification (`_classify_and_fill_oracle`, diff/upsert on `game_flaws`) — re-grinding already-analyzed games and churning flaw rows. It is the correct path for full_pv-NULL games (Population A), the WRONG path for full_pv-SET games (Population B).

- **The minimal lane is the right home for full_pv-SET games.** `_claim_tier4_bestmove` (`eval_queue_service.py` ~666-734) gates on `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL AND lichess_evals_at IS NULL`, routes via `TIER_BESTMOVE_BACKFILL` to `_tier4b_minimal_drain_tick` (`eval_drain.py` ~664-819), touches ONLY `game_best_moves` + `best_moves_completed_at`, never reads/writes `game_flaws` (S-06/D-02 isolation). The change for B is relaxing its `lichess_evals_at IS NULL` clause to admit lichess-eval games.

- **D-03 rationale check.** The `lichess_evals_at IS NULL` exclusion on tier-4b exists to keep it from contending with the 174-07 residual fallback over lichess-eval games. But the two lanes are DISJOINT on `full_pv`: the residual only takes `full_pv IS NULL` lichess games; the extended tier-4b would only take `full_pv IS NOT NULL` lichess games. They do not overlap, so admitting full_pv-SET lichess games to tier-4b should not reintroduce contention. Planner must confirm this reasoning against the current claim-priority order in `claim_eval_job` (`eval_queue_service.py` ~800-883).

- **OPEN VERIFICATION (load-bearing):** Confirm the minimal `_tier4b_minimal_drain_tick` classifier applies the lichess `is_lichess_eval_game` divergence guard (`best_move_candidates.py` ~180-198, `classify_best_move`) correctly when it processes a lichess-eval game. The minimal lane was built for engine games (is_lichess_eval_game=False by construction, `eval_queue_service.py:872`). If the minimal handler does NOT thread `is_lichess_eval_game=True` / does not apply the divergence guard, best/gem classification on lichess-eval games would be WRONG. This must be verified and, if missing, wired through — this is the single riskiest part of the unified-lane approach. If it cannot be made correct in the minimal lane, fall back to a targeted backfill script for the existing 12,643 + a source fix, and FLAG for re-discussion.

- **No migration.** All changes are SQL predicate + Python logic + tests. Do not create an Alembic revision.

- **Backfill is runtime, not a script.** The existing 12,643 (B) drain automatically via the extended minimal lane at the lowest idle rung; the 18,882 (A) drain via the heavy residual at the lowest idle rung. No `scripts/backfill_*.py` needed. Both are opportunistic, no ETA.

- **Verify with prod game 1247936** (guest, lichess, full_pv NULL) as the canonical Population A example. A canonical Population B example: any non-guest game with `lichess_evals_at IS NOT NULL AND full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`.

- **Tests to update/add:** `tests/services/test_eval_queue.py` — `test_excludes_guests` (~2107), `test_residual_fallback_excludes_guest_backlog_game` (~1207), `test_tier4_excludes_guests` (~1713) and the tier-4b lichess-exclusion assertions (~2036-2369) will change semantics. Add: (1) tier-4b minimal lane picks a full_pv-set lichess-eval game; (2) residual fallback now admits a guest full_pv-NULL lichess game; (3) divergence-guard correctness on a lichess-eval game through the minimal lane. Prove each gap fix by reverting it and confirming the test fails (per project mutation-test discipline).

</specifics>

<canonical_refs>
## Canonical References

- `app/services/eval_queue_service.py` — claim lanes (`_claim_tier3_derived` residual ~539-561; `_claim_tier4_bestmove` ~666-734; `_es_weighted_user_pick` guest filter line 322; `claim_eval_job` dispatch ~800-883)
- `app/services/eval_drain.py` — handlers (`_tier4b_minimal_drain_tick` ~664-819; heavy `_full_drain_tick` ~822-1081; tier dispatch ~864)
- `app/services/eval_apply.py` — completion stamping (`apply_completion_decision` ~714-823; `_mark_best_moves_completed` ~696-711; maia_available guardrail ~782-783)
- `app/services/best_move_candidates.py` — `classify_best_move` + `is_lichess_eval_game` divergence guard (~160-203)
- CLAUDE.md — backend rules (ty compliance, Sentry capture in except blocks, no asyncio.gather on one AsyncSession, Literal types, pre-merge gate)
- Prior decisions referenced: QUEUE-08 (guest exclusion from automatic bulk analysis), D-02/D-03 (tier-4b isolation + lichess exclusion), SEED-109 (residual marker broadened to full_pv), S-06 (tier-4b flaw isolation)

</canonical_refs>
