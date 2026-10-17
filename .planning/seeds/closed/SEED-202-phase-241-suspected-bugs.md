---
id: SEED-202
status: code-fixed; item 1 data repaired on prod; item 2 data repair pending owner decision
planted: 2026-10-17
planted_during: owner review of the Phase 241 audit's suspected bugs (INVENTORY §7.2), after the v2.25–v2.27 close
trigger_when: next session; start with item 1 (tier-4 lichess flag). Owner is not yet sure how big a deal items 1 and 2 are, so measure impact before sizing the fix
scope: small; a series of /gsd-quick tasks (items 3-8 fit one batch, e.g. /gsd-quick-batch)
---

# SEED-202: Phase 241 suspected bugs (verified 2026-10-17)

## Resolution (2026-10-17)

All eight code fixes landed on `main` (three commits after de3a44df7) and shipped in PR #427 (production 5672b194c).
Item 1's data repair ran on prod on 2026-10-17. Open: the data repair for item 2.

- **Item 1, measured on prod.** Prod runs the drain (`../../../docker-compose.yml` defaults `EVAL_AUTO_DRAIN_ENABLED` to true).
  Footprint check: compare `game_positions.eval_cp` at ply n-1 with the n-th `[%eval]` in the PGN (lichess
  storage is post-move, so the n-th eval maps to row n-1). Non-guest lichess-eval games with blobs done: 97,174;
  **about 4,000 match less than 50%** (Jun 85, Jul 2,167, Aug 459, Sep 303, Oct 988 by `full_evals_completed_at`
  month). The 2026-10-09/10 sample: 645 overwritten (near-equal engine values, aligned), 18 shifted one ply
  (the separate known convention issue), 4,769 ok. The damaged games still carry `lichess_evals_at`, so the app
  treats them as lichess-eval games while their evals and flaws come from our engine. Opening-cache donations
  from them are real engine evals of real positions, so they are probably harmless (not checked further).
  2,458 non-guest lichess-eval games were still tier-4-pending; with the fix they now take the
  preserve-evals path.
- **Item 1 data repair: DONE (2026-10-17).** We chose a provenance fix over restoring the lichess evals: the
  stored evals are real engine evals, consistent with the stored best moves, PVs and flaws, so
  `scripts/fix_lichess_eval_provenance.py` NULLs `lichess_evals_at` on the overwritten games, which then count
  as analyzed by us. The lichess evals remain in the PGN. The prod scan (11:54 UTC, after the tier-4 fix was
  deployed) flagged 3,586 games across 229 users (the shifted-one-ply control is excluded). The owner ran
  `apply --db prod --execute`. Spot check: 40 of 40 sampled ids now have `lichess_evals_at IS NULL`. The scan
  file, which `restore` needs, is `temp/lichess-provenance-fix/flagged-games.json` (gitignored, local only).
  We rejected switching lichess games to our own evals: it would mean recomputing about 109k analyzed games,
  because our per-ply evals are not stored for them.
- **Item 2.** Normalization now writes `*_imported`. Existing 15,289 rows still need the repair described below
  (owner sign-off: it changes what Library shows for unanalyzed games).
- **Item 7.** Removing the dead branch also makes a start-position bookmark (empty `moves`) load the start position
  from the Stats chart instead of leaving the board where it was.
- **Item 8.** Fixed with `(pointer: coarse)` as proposed. Still not verified on touchscreen hardware.

Source: `../../milestones/v2.27-phases/241-codebase-cleanup/241-INVENTORY.md` §7.2 (13 entries, 11 distinct).
Already fixed in v2.27: §7.2 #3 (NULL `sample_pair`, 07dd60fb4), #6 (Tactic Depth highlight), #8 (auth-route
401 redirect). #10 was not a bug, #11 duplicates #9. The eight below were re-checked against code on
2026-10-17 (after the Phase 241 renames, so line numbers are current); items 1 and 2 also against prod.
Item numbers here are this seed's order; the INVENTORY number is in brackets.

## 1. Tier-4 blob claim hard-codes `is_lichess_eval_game=False` (INVENTORY #2) — HIGH, check first

- `app/services/eval_queue_service.py:1091`: the bundled `scope=None` path of `claim_eval_job` returns
  `ClaimedJob(tier=TIER_BLOB_BACKFILL, is_lichess_eval_game=False)` with the comment "resolved in the
  /flaw-blob-lease handler". But the in-process drain also calls `claim_eval_job(worker_id=WORKER_ID_SERVER_POOL)`
  with `scope=None` (`app/services/eval_drain.py:1338`) and trusts `claimed.is_lichess_eval_game`
  (`eval_drain.py:1345`); only tier-4b re-derives it (`eval_drain.py:1171`, and the tier-4b claim at
  `eval_queue_service.py:1058` resolves it from the row).
- Tier-4's predicate (`full_evals_completed_at IS NOT NULL AND blobs_completed_at IS NULL`) does not exclude
  lichess-eval games. For one, the drain would build a terminal donor (`include_terminal=not is_lichess_eval_game`,
  `eval_drain.py:1385`), use the opening dedup cache, write engine post-move evals over the lichess %evals and
  donate them to `opening_position_eval` (`update_opening_cache=not is_lichess_eval_game`, `eval_drain.py:1564`).
  Same failure family as the poisoned opening cache (see memory `project_opening_cache_poisoned_legacy_evals`).
- Prod 2026-10-17: tier-4-eligible games = 10,437 non-guest non-lichess, 203 guest non-lichess, **2,421 non-guest
  lichess-eval**, 5,363 guest lichess-eval (guests are probably excluded by the tier-4 user lottery; check).
- **Impact is NOT measured.** First answer: does the server-pool drain actually reach tier 4 in prod (tier-3 must be
  empty, `EVAL_AUTO_DRAIN_ENABLED`), and have any lichess-eval games already been processed by it? Look for a
  footprint: lichess-eval games with `blobs_completed_at` set by the server pool whose `game_positions.eval_cp`
  no longer matches the lichess %evals in the PGN, and opening-cache rows donated from them.
- Fix: derive the flag from `Game.lichess_evals_at` via `derive_is_lichess_eval_game` (as the tier-4b branch
  does), or re-derive in `_full_drain_tick`. Regression test must fail when the fix is reverted (memory
  `feedback_mutation_test_gap_closures`). Mind tier-4 lottery test isolation (memory `project_eval_lottery_test_isolation`).
  If damage exists, repair is a separate step.

## 2. Platform accuracy/ACPL lands in the canonical computed columns (INVENTORY #1) — MEDIUM

- `app/services/normalization.py:308` (chess.com `accuracies`) and `:481` (lichess `analysis` accuracy/acpl) fill
  `NormalizedGame.white_accuracy/black_accuracy/white_acpl/black_acpl`; import inserts `model_dump()` unchanged, so
  they reach `games.white_accuracy` etc. `app/models/game.py:180-198` documents those as our lichess-formula values,
  NULL until computed, and `*_imported` as the platform values. No code writes `*_imported`
  (only the Phase 178 migration copied old values).
- Prod 2026-10-17: **15,289 games** carry platform values in the canonical columns without our evals
  (chess.com 14,257, lichess 1,032); `*_imported` was last written at game id 1,715,981 (max id ~3.09M), so every
  later import lost the platform value once our compute overwrote it.
- Effects: Library shows the platform's accuracy as ours for unanalyzed games (`library_service.py:773` serves
  `white_accuracy`); the validation/comparison signal in `*_imported` stopped growing in July.
- Fix: map the platform values to `*_imported` in normalization (schema fields renamed accordingly). Data repair for
  existing rows (move to `*_imported`, NULL the canonical columns where `full_evals_completed_at IS NULL`) changes what
  Library shows for unanalyzed games: owner sign-off needed. Values already overwritten by our compute cannot be
  recovered without re-fetching.

## 3-8. Small frontend items (one batch)

3. **`MoveStats.tsx:373` (INVENTORY #5):** the mobile expand toggle hard-codes `data-testid="move-stats-expand-toggle"`
   instead of `tid('move-stats-expand-toggle', gameId)`; duplicates across Library cards. Update any test selectors.
4. **`ResumeGate.tsx:109` (INVENTORY #4):** identity line shows `${plyCount} moves` but `plyCount` is `liveGamePly`
   (half-moves). Show full moves (`Math.ceil(plyCount / 2)`) or say plies.
5. **`types/activity.ts` (INVENTORY #9/#11):** `ActivityStatsPayload` lacks `guest_train`, which
   `app/services/activity_queries.py:120` sends and `pages/activity/render.js` reads. Type drift only.
6. **`lib/engine/ortRuntimeSource.ts:74-77` (INVENTORY #13):** the size fallbacks say 1.29.0 (13,961,845 /
   25,749,873); the vendored 1.27.0 files are 13,479,978 / 24,254,953 bytes. Update values and doc comments
   (progress placeholder only).
7. **`pages/openings/useOpeningsHandlers.ts:63-69` (INVENTORY #12):** the `else if (mostPlayedData)` "default chart
   entry" branch is dead (chart entries are always real bookmarks since default entries were removed). Remove it
   and the now-unused `mostPlayedData` param if nothing else needs it.
8. **`components/move-explorer/MoveExplorer.tsx:49` (INVENTORY #7):** `IS_TOUCH = 'ontouchstart' in window` is true
   on touchscreen laptops, so a mouse click there only highlights a move row. Plausible, not verified on hardware.
   Candidate: `matchMedia('(pointer: coarse)')`, the pattern `ChessBoard.tsx` documents.

## Not in this seed

INVENTORY §7.1 (50 seed candidates) still needs its own owner pass.
