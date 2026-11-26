---
phase: "263"
slug: "foreign-blunder-fillers"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_total: 30
threats_closed: 30
threats_open: 0
threats_open_non_blocking: 0
asvs_level: 1
block_on: high
created: "2026-11-23"
---

# Phase 263 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register assembled from the `<threat_model>` blocks of plans 01-10 (T-263-SC appears in every plan and is counted once). Mitigations verified by gsd-security-auditor against the code on branch `gsd/phase-263-foreign-blunder-fillers` at `583c9597a` (merge base `a5e743959`), by reading the code and tracing the cited tests. A threat is closed only when the code does what the register says and a test would fail without it.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| solver session -> other users' game rows | Composition, resume, grading and reveal read strangers' games, flaws and positions on the solver's behalf | game id, ply, answer-key blob, PGN (server-side only) |
| server -> client (TrainPuzzle, SolveResponse, PuzzleRevealResponse) | Puzzle and reveal payloads leave the server | FEN, ply, key moves, neutral game facts; never a foreign game id, user id or username |
| client path params -> solve / reveal | `session_id` and `position` are untrusted | resolved only together with the authenticated user id |
| migration -> committed rows | DDL and one DELETE run against live sessions at deploy | untouched open sessions holding retired filler rows |
| resume request -> streak state | A status read can complete a session and credit a day | streak count, freeze level |
| aggregate queries -> boards and admin page | Per-source counts leave the database | counts only |
| pre-deploy client -> new API | Stale PWA bundles keep posting to the new server | legacy filler solves |
| phase branch -> main / production | Last gate before squash-merge and deploy | release integrity |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-263-01 | Information disclosure | `_materialize_session_rows` ComposedPuzzle / TrainPuzzle.game_id | high | mitigate | `_wire_game_id` (train_repository.py:3350) applied on fresh compose (:3309), resume (:2221) and reveal (:5038); stage-two select carries no user id, username or PGN (train_pool.py:1152-1160). Tests: tests/repositories/test_train_foreign.py:171, tests/routers/test_train_foreign.py:139 | closed |
| T-263-02 | Elevation of privilege | `_answer_keys_by_position`, `_classify_and_certify_solve` | high | mitigate | `DrillSolve.user_id == user_id` in the key read (train_repository.py:3472) and in record_solve's select, claim and re-read (:4585, :4646, :4702); owner lookup follows the row's own game id (:3991). Test: tests/routers/test_train.py:2098 | closed |
| T-263-03 | Information disclosure | `foreign_band_candidates_stmt` / `foreign_nearest_candidates_stmt` | high | mitigate | `user_id != solver_id`, `users.is_guest IS false`, chess.com / lichess only (train_pool.py:1119-1121), shared by both statements. Tests: tests/repositories/test_train_foreign.py:88, :131, :435 | closed |
| T-263-04 | Denial of service | `_backfill_foreign_blunders` inside the compose request | medium | mitigate | 0.1% band sample, 0.4% nearest sample (train_foreign.py:33-35); game limit clamped 40..200 (:77-80); two steps (:55-58); served set read once (train_repository.py:2736). Tests: tests/services/test_train_foreign.py:155, tests/repositories/test_train_foreign.py:627, :668, :682, :697. Prod EXPLAIN: see T-263-26 | closed |
| T-263-05 | Tampering | migration b3d5f7a9c264 downgrade | low | mitigate | `DELETE ... WHERE source = 3` precedes the CHECK narrowing (migration :40-44). Test: tests/test_phase_263_migration.py:128 | closed |
| T-263-06 | Information disclosure | trainBotCopy.ts tails and welcome | low | mitigate | Neutral copy (trainBotCopy.ts:304-306, :313-314, :544, :573); TrainPuzzle has no `source` field (schemas/train.py:82-133). Tests: trainBotCopy.test.ts:462, tests/routers/test_train.py:1147 (key-set equality) | closed |
| T-263-07 | Spoofing (misleading UI) | TrainStartScreen D-13 sentence | low | mitigate | Gated on `own_puzzle_count === 0`, `hasGames` and `first_session_done === true` (TrainStartScreen.tsx:405-409). Tests: TrainStartScreen.test.tsx:636-715 (pending query at :695) | closed |
| T-263-08 | Information disclosure | owner-keyed reads in `load_session_puzzles`, `_composition_puzzle_types` | medium | mitigate | Game ids come from the solver's own rows (train_repository.py:2163, :2173-2177); only flaw keys and blobs are read (:2239-2256, :2988-3029). Tests: tests/repositories/test_train_foreign.py:295, :787 | closed |
| T-263-09 | Denial of service | `_mark_session_complete_if_done` with a deleted foreign game | medium | mitigate | Foreign orphans excluded from `remaining` like SR orphans (train_repository.py:4268-4278). Tests: tests/repositories/test_train_foreign.py:320, :351 | closed |
| T-263-10 | Information disclosure | draw statements (D-01) | high | mitigate | Direct statement test over both steps with identical own, guest and stranger games: tests/repositories/test_train_foreign.py:435 | closed |
| T-263-11 | Information disclosure | TrainRevealGameFooter foreign branch | high | mitigate | `useLibraryGame(null)` for a foreign verdict, ForeignGameFooter only (TrainRevealGameFooter.tsx:46-63). Tests: TrainReveal.test.tsx:744, :761 | closed |
| T-263-12 | Information disclosure | TrainSolveScreen Analyze link | high | mitigate | `analyzeOpens` is 'game' only for `sr_item` with a game id (TrainSolveScreen.tsx:915-925); the server sends game id null (T-263-01). Test: TrainSolveScreen.test.tsx:2279 | closed |
| T-263-13 | Spoofing (misattribution) | verdict sentence and tour copy | low | mitigate | "the game move" (trainBotCopy.ts:459), "the Game move" (:684). Tests: trainBotCopy.test.ts:404, :629; TrainSolveScreen.test.tsx:4172 | closed |
| T-263-14 | Tampering (board integrity) | `_ACCURACY_SOURCES` | medium | mitigate | Positive source list (train_leaderboard_repository.py:85-87). Test: tests/repositories/test_train_leaderboard_repository.py:225 | closed |
| T-263-15 | Information disclosure | admin Activity source row | low | accept | see Accepted Risks Log | closed |
| T-263-16 | Information disclosure | `reveal_for_puzzle` / `PuzzleRevealResponse` | high | mitigate | `_foreign_game_info` builds four neutral fields (train_repository.py:4845-4858); game id None (:5038); schema GameInfo (schemas/train.py:57-66). Test pins the exact key sets of the body and of game_info: tests/routers/test_train_foreign.py:192 | closed |
| T-263-17 | Elevation of privilege | reveal IDOR | high | mitigate | Lookup keeps `user_id`, `session_id`, `position` (train_repository.py:4915-4923); 409 gate before any owner read (:4929). Test: tests/routers/test_train.py:2651 | closed |
| T-263-18 | Information disclosure | tactic-lines pointer | low | mitigate | Gate at train_repository.py (`has_tactic_lines = not foreign and ...`). Test: tests/routers/test_train_foreign.py::test_reveal_foreign_reports_owner_game_move_and_type now seeds `missed_tactic_motif` on the stranger's flaw and fails when the gate is removed (b9c05a272, after the audit) | closed |
| T-263-19 | Denial of service | `_mark_session_complete_if_done` with unsolved legacy rows | medium | mitigate | Every unsolved legacy row excluded (train_repository.py:4295). Test: tests/repositories/test_train_legacy_filler.py:97 | closed |
| T-263-20 | Denial of service | Today mount `_resume_session` -> `_wire_source` | high | mitigate | "sharp_filler" arm kept (train_repository.py:3739-3740). Test: tests/repositories/test_train_legacy_filler.py:173 | closed |
| T-263-21 | Tampering | `record_solve` on a legacy filler from a stale client | low | mitigate | Keyless sharp classification (train_repository.py:3876-3886, :3985-3986). Test: tests/repositories/test_train_legacy_filler.py:196 | closed |
| T-263-22 | Repudiation (history integrity) | solved source 2 rows | medium | mitigate | No code path writes source 2; the migration DELETE skips any session with a solve (c4e6a8b0d375 :44-50). Tests: tests/repositories/test_train_repository.py:1325, tests/repositories/test_train_leaderboard_repository.py:204, :225. Note: `sharp_puzzle_id` is dropped from solved rows too (owner-confirmed) | closed |
| T-263-23 | Tampering (data loss) | migration c4e6a8b0d375 | medium | mitigate | DELETE limited to open sessions with zero solves holding an unsolved source 2 row (:44-50); only `drill_solves` cascades. Tests: tests/test_phase_263_migration.py:161 (four negative controls), :205 | closed |
| T-263-24 | Denial of service | migration downgrade with committed rows | low | mitigate | Same statements as T-263-05. Test: tests/test_phase_263_migration.py:128 | closed |
| T-263-25 | Elevation of privilege (streak credit) | lazy completion in `_resume_session` | medium | mitigate | Open session resolved by user id (train_repository.py:1701-1714), `not puzzles and solved_results` (:2328), same completion pair as record_solve (:2329-2334). Test: tests/repositories/test_train_legacy_filler.py:128. Negative test for the "at least one solve" guard added in 16894aa64 (`test_resume_leaves_untouched_session_with_nothing_servable_open`, fails when the guard is dropped) | closed |
| T-263-26 | Denial of service | foreign draw latency on prod | medium | transfer | 263-PROD-EXPLAIN.sql; 263-HUMAN-UAT.md item 4: pass before the squash-merge (201 ms, 146 ms, 337 ms against 0.5 s / 1.5 s). Post-deploy run pending | closed |
| T-263-27 | Denial of service | shared dev DB used by the main checkout | low | mitigate | 263-HUMAN-UAT.md item 5 carries the manual step, warnings and downgrade command; dev DB read at `a7c3e5f9b261` during this audit | closed |
| T-263-28 | Tampering | release integrity | medium | mitigate | Gate results in 263-10-SUMMARY.md (not re-run in this audit); D-03 / D-04 grep gates re-run clean; no code commit since gate commit `081be3b61` | closed |
| T-263-29 | Tampering (streak integrity) | `_stamp_pool_eligibility` after materialize | low | mitigate | Stamp after the session row is written (train_repository.py:3701-3707), guarded on IS NULL (:963-1011). Tests: tests/repositories/test_train_repository.py:3537, :3564, :3585 | closed |
| T-263-SC | Tampering | npm / pip installs | low | accept | see Accepted Risks Log | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-263-01 | T-263-15 | Admin-gated page showing aggregate counts per source only, no user or game identifiers (`fetch_puzzle_difficulty` groups by source) | plan 263-05 threat model | 2026-11-23 |
| AR-263-02 | T-263-SC | No package installed in any plan; `pyproject.toml`, `uv.lock`, `frontend/package.json`, `frontend/package-lock.json` and the `analysis/` manifests are unchanged against merge base `a5e743959` | plans 01-10 threat models | 2026-11-23 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Findings

No threat flags were raised in any of the ten SUMMARY files. Findings from this audit:

**Closed after the audit**

- **T-263-18 test gap (low), closed in b9c05a272.** The fix was to Seed `missed_tactic_motif` on the stranger's flaw in `tests/routers/test_train_foreign.py::test_reveal_foreign_reports_owner_game_move_and_type`, so that `has_tactic_lines is False` fails when the `not foreign` gate is removed.

**Informational**

- **Wrong premise in the plan and code comments.** `GET /api/library/games/{game_id}` and `GET /api/library/flaws/{game_id}/{ply}/tactic-lines` are intentionally not owner-scoped (app/routers/library.py:141-167, :438-463). The docstring at train_repository.py:4886-4887, the comment at :5021-5022 and 263-CONTEXT.md describe the tactic-lines endpoint as scoped to the signed-in user. The mitigations hold, but the nulled wire `game_id` is the only control between a foreign puzzle and the stranger's full game card.
- **T-263-25.** The missing negative test for the `solved_results` guard was added in 16894aa64 (validation audit).
- **T-263-04 / T-263-26.** The prod EXPLAIN used `game_limit = 40`. The 200 cap (shortfall of 25 or more) is unmeasured. Each statement was run once, not twice.
- **T-263-16.** `game_info.played_at` was a full timestamp on the wire; truncated to the date in 101afecb1 (review WR-02), with a test.
- **Unregistered, low.** The draw excludes games owned by the solver (train_pool.py:1119), not games the solver played in that the opponent imported. Blunder check has the same property.
- **Pre-existing, out of phase scope.** Red-herring rows still send another user's `game_id` on compose, resume and reveal.

**Process items (not counted in threats_open):** post-deploy prod EXPLAIN (T-263-26); full pre-merge gate at the squash-merge (T-263-28); manual dev DB upgrade before the browser walk-through (T-263-27).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-23 | 30 | 29 | 0 blocking, 1 non-blocking (T-263-18, low) | gsd-security-auditor (ASVS L1, block_on high) |
| 2026-11-23 | 30 | 30 | 0 | orchestrator, after fix commits b9c05a272 (T-263-18 test) and 101afecb1 (played_at date only); revert-and-fail observed by the fixer |

Targeted tests run during the audit (all passed): `tests/routers/test_train_foreign.py::test_reveal_foreign_game_info_names_nobody`, `::test_foreign_puzzle_wire_has_no_game_id`, `tests/repositories/test_train_foreign.py::test_draw_excludes_guest_and_solver_games`, `tests/test_phase_263_migration.py::test_untouched_open_sessions_with_unsolved_legacy_filler_are_deleted`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-23
