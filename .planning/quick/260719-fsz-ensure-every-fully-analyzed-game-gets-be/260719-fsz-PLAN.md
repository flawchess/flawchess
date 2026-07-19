---
phase: quick-260719-fsz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/eval_queue_service.py
  - app/services/eval_drain.py
  - tests/services/test_eval_queue.py
  - tests/services/test_eval_drain.py
autonomous: true
requirements:
  - COVER-A-guest-lichess-residual
  - COVER-B-nonguest-lichess-orphan-tier4b
  - COVER-B2-guest-orphan-selfheal
  - COVER-divergence-guard-parity
must_haves:
  truths:
    - "A guest lichess-eval game with full_pv_completed_at IS NULL is claimable by the tier-3 residual fallback (Population A)."
    - "A non-guest lichess-eval game with full_pv_completed_at IS NOT NULL and best_moves_completed_at IS NULL is claimable by the tier-4b minimal lane (Population B)."
    - "A guest full_pv-set game with best_moves_completed_at IS NULL self-heals through the tier-4b minimal lane (Population B2)."
    - "The tier-3 needs-engine Step-1/Step-2 pick and the tier-4-blob lottery STILL exclude guests (shared _es_weighted_user_pick literal not flipped)."
    - "game_best_moves rows written for a lichess-eval game through the minimal drain store our-Stockfish best_cp (not the stored lichess eval), so the query-time divergence guard is meaningful."
  artifacts:
    - app/services/eval_queue_service.py
    - app/services/eval_drain.py
    - tests/services/test_eval_queue.py
    - tests/services/test_eval_drain.py
  key_links:
    - "tier-3 residual (full_pv IS NULL) and extended tier-4b (full_pv IS NOT NULL) stay DISJOINT on full_pv_completed_at — no double-claim."
    - "include_guests param on _es_weighted_user_pick is passed True ONLY from _claim_tier4_bestmove; tier-3/tier-4-blob keep default False."
    - "_tier4b_minimal_drain_tick sources best_cp from the already-running MultiPV-2 fresh search for lichess games; query-time classify_best_move (library_service/library_repository) is unchanged and already lichess-aware."
---

<objective>
Close two best-move coverage holes so every game we can classify gets `best_moves_completed_at` + `game_best_moves` rows, via runtime self-healing lanes (no backfill script, no migration):

- Population A (~18,882 guest lichess-eval games, full_pv NULL): open the tier-3 residual lichess fallback to guests.
- Population B (~12,643 non-guest lichess-eval orphans, full_pv set / best_moves NULL): extend the minimal tier-4b lane to admit lichess-eval games; also self-heal guest orphans (B2).
- Correctness: make the minimal drain store our-Stockfish `best_cp` for lichess games so the query-time divergence guard is meaningful (resolved open verification — see below).

Purpose: A game that has enough data to classify best/gem moves must eventually get classified. Two lanes silently orphan lichess-eval and guest games forever; this is both a historical spike (Maia-down window) and an ongoing leak.
Output: Predicate + logic changes in eval_queue_service.py and eval_drain.py, plus updated/added tests proving each fix by reversion (mutation discipline).
</objective>

<open_verification_resolution>
## RESOLVED: viable-as-locked (with a required write-time best_cp fix)

The concern was whether `_tier4b_minimal_drain_tick` applies the `is_lichess_eval_game` divergence guard when classifying a lichess-eval game. Findings from the trace:

1. **The minimal drain does NOT classify at all.** `_build_best_move_candidates` (eval_apply.py:1861) stores ONLY raw floats — `maia_prob, best_cp, best_mate, second_cp, second_mate` (confirmed against the `GameBestMove` model: no post_move / no tier column). Gem/great classification — including the `is_lichess_eval_game` divergence guard — happens entirely at QUERY time in `library_service.py:246-261` (board) and the `best_move_tier_sql` SQL twin in `library_repository.py` (filter). Both independently source `is_lichess_eval_game = game.lichess_evals_at is not None` and `post_move_cp = game_positions.eval_cp`. So the classifier is ALREADY correct for drained lichess rows — no `is_lichess_eval_game` needs threading into any classify call in the drain.

2. **BUT the raw `best_cp` the drain stores would be WRONG for lichess games.** The minimal drain sources `best_cp` from `eval_of_position` = `game_positions.eval_cp`. For a lichess-eval game the full_pv pass deliberately PRESERVES lichess %evals in `game_positions.eval_cp` and writes best_move only (eval_apply.py:607-629). So the drain would store `best_cp = lichess eval`. Meanwhile the atomic-submit path stores `best_cp = worker Stockfish eval` (eval_remote.py:1158, from `body.evals`). At query time `post_move_cp = game_positions.eval_cp = lichess`; with a lichess-sourced `best_cp` the guard compares lichess-to-lichess → `best_es - post_es ≈ 0` → the guard NEVER fires (badge never suppressed), and the C2 margin mixes lichess `best_cp` with Stockfish `second_cp`. That diverges from how the atomic path would have classified the same game.

**Conclusion:** The locked unified-lane is viable, but relaxing the `lichess_evals_at IS NULL` clause alone is NOT sufficient — the drain must additionally, for lichess games, source `best_cp`/`best_mate` from the fresh MultiPV-2 search it ALREADY runs (`res[0]/res[1]`, white-perspective Stockfish, same convention the worker submits). This is clean (~10 lines, no new search, no perspective juggling — `evaluate_nodes_multipv2` already returns white-perspective evals, as the existing `second_cp` use proves). No fallback to a backfill script is needed. Task 2 implements this.

## RESOLVED: D-03 non-contention confirmed

`claim_eval_job` dispatch order: tier-3 residual (`_claim_tier3_derived`) runs first (line 833); tier-4b (`_claim_tier4_bestmove`) only after tier-3 AND tier-4-blob return None (line 864). After the changes:
- tier-3 residual takes `full_pv_completed_at IS NULL AND lichess_evals_at IS NOT NULL`.
- tier-4b takes `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`.
These are DISJOINT on `full_pv_completed_at` (NULL vs NOT NULL) — a game matches at most one lane, so no double-claim/contention is introduced. Confirmed.
</open_verification_resolution>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/quick/260719-fsz-ensure-every-fully-analyzed-game-gets-be/260719-fsz-CONTEXT.md
@app/services/eval_queue_service.py
@app/services/eval_drain.py
@app/services/eval_apply.py
@app/services/best_move_candidates.py
@tests/services/test_eval_queue.py
@tests/services/test_eval_drain.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Open the claim lanes to guest + lichess-eval populations (A, B, B2)</name>
  <files>app/services/eval_queue_service.py</files>
  <action>
Three predicate/param edits plus one honesty fix, all in eval_queue_service.py. All SQL VALUES stay bound via the sa.text params dict — never f-string-interpolated (QUEUE-08). Do NOT touch the shared `is_guest = false` literal at line ~322 directly.

(A) Population A — residual fallback opens to guests. In `_claim_tier3_derived`'s residual fallback `_es_weighted_game_pick` call (~lines 539-552), REMOVE the guest EXISTS clause from `game_where_sql`, leaving only `g.full_pv_completed_at IS NULL AND g.lichess_evals_at IS NOT NULL`. Update the trailing comment: guests are now INCLUDED in this residual lichess-eval lane per Quick 260719-fsz (CONTEXT "Guest data — process them"), a deliberate scoped reversal of QUEUE-08 for THIS lane only. This lane's user pick is game-only (no `_es_weighted_user_pick`), so removing this clause does not affect any other tier. Do NOT re-gate this residual on `best_moves_completed_at IS NULL` (CONTEXT: it routes through the heavy every-ply MultiPV-2 pass, correct only for full_pv-NULL games).

(B) Population B — tier-4b admits lichess-eval games. In `_claim_tier4_bestmove` REMOVE `AND g.lichess_evals_at IS NULL` from BOTH the Stage-1 `candidate_exists_sql` (~line 715) and the Stage-2 `game_where_sql` (~line 732), leaving `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL` (Stage-2 keeps the `g.user_id = :picked_user` clause). Update the docstring's "Predicate" paragraph and the "The `lichess_evals_at IS NULL` clause is load-bearing (D-03)" note: the two lanes stay disjoint on `full_pv_completed_at` (NULL for the residual vs NOT NULL here), so admitting full_pv-SET lichess games does not reintroduce tier-3 contention (Quick 260719-fsz).

(B2) Guest orphan self-heal — parameterize the shared user-pick guest filter. Add `include_guests: bool = False` to `_es_weighted_user_pick`'s signature. In its SQL, replace the hardcoded `WHERE u.is_guest = false` line with a conditionally-composed fragment: emit `WHERE u.is_guest = false AND EXISTS (...)` when `include_guests` is False (default, unchanged behavior) and `WHERE EXISTS (...)` when True. Compose this only from the fixed literals already trusted here — no request/user input (QUEUE-08 injection note still holds; add a one-line comment). Pass `include_guests=True` from `_claim_tier4_bestmove`'s Stage-1 `_es_weighted_user_pick` call ONLY. Do NOT change the tier-3 Step-1 call or the tier-4-blob Stage-1 call — they keep the default and still exclude guests. Stage-2's `_es_weighted_game_pick` has no guest filter, so once a guest user is picked their full_pv-set best_moves-NULL games flow.

(HONESTY) In `claim_eval_job`, the `TIER_BESTMOVE_BACKFILL` branch (~line 872) hardcodes `is_lichess_eval_game=False` with the comment "correct by construction (predicate excludes lichess-eval games)" — that comment is now FALSE. Resolve it correctly: after `_claim_tier4_bestmove` returns `(game_id4b, user_id4b)`, run the same cheap `select(Game.lichess_evals_at).where(Game.id == game_id4b)` PK lookup the tier-1/2 path uses (~lines 283-285) and set `is_lichess_eval_game` from it. Update the comment. NOTE: the minimal drain resolves this flag itself from the game row (Task 2), so this field is observability-only for tier-4b — but leaving a stale `False` with a now-false comment is a landmine, so fix it.
  </action>
  <verify>
    <automated>uv run ruff check app/services/eval_queue_service.py && uv run ty check app/services/eval_queue_service.py</automated>
  </verify>
  <done>Residual fallback has no guest clause; tier-4b has no `lichess_evals_at IS NULL` clause in either stage; `_es_weighted_user_pick` takes `include_guests` (default False) passed True only by `_claim_tier4_bestmove`; the tier-4b ClaimedJob resolves `is_lichess_eval_game` from the game row. ruff + ty clean.</done>
</task>

<task type="auto">
  <name>Task 2: Store our-Stockfish best_cp for lichess games in the minimal drain (divergence-guard parity)</name>
  <files>app/services/eval_drain.py</files>
  <action>
In `_tier4b_minimal_drain_tick` (~lines 664-819), make the stored `best_cp`/`best_mate` our-Stockfish for lichess-eval games so the query-time divergence guard is meaningful and matches the atomic-submit path.

Resolve the flag from the game row already read in the short read session (~line 721): `is_lichess_eval_game = game.lichess_evals_at is not None`. No signature change (the claim does not pass it in for tier-4b, line 865).

The fresh MultiPV-2 gather (~lines 782-793) already runs `evaluate_nodes_multipv2(t.board)` for every `search_target` and returns a 7-tuple whose `res[0]/res[1]` are the WHITE-perspective best cp/mate (same convention the existing `second_cp = res[4]/res[5]` use stores). Currently `res[0]/res[1]/res[2]` (the fresh best) are discarded. For a lichess-eval game ONLY, after the `second_best_map` loop, OVERRIDE `engine_result_map[t.ply]` for each searched target with `(res[0], res[1], stored_best_move_by_ply.get(t.ply), None)` — replacing the stored-lichess `best_cp`/`best_mate` with fresh Stockfish while KEEPING the stored best_move as the identity key (index 2), so `_build_best_move_candidates`'s played==best candidate test (`entry[2] != t.move_uci`) is unchanged. For engine games, leave `engine_result_map` untouched (its stored eval IS our Stockfish — behavior identical to today).

Add a bug-fix comment at the override site: for a lichess-eval game `game_positions.eval_cp` holds LICHESS %eval (the full_pv pass preserves it, eval_apply.py:607-629), so without this override the stored `best_cp` would be lichess and the query-time divergence guard (library_service.py:246-261, which reads `post_move_cp = game_positions.eval_cp`) would compare lichess-to-lichess and never fire — over-badging. Fresh Stockfish `best_cp` matches the atomic-submit path (eval_remote.py:1158, worker `body.evals`).

Known residual edge (note in the comment, do NOT expand scope): a candidate ply that `_build_best_move_candidates` finds but that is absent from `search_targets` would fall to the builder's own Pitfall-1 fallback and keep lichess `best_cp`; this is the same rare Sentry-tagged (`source="drain-local"`) fallback path that already exists, and lease candidates ⊇ builder candidates by construction (both keyed on played==stored_best), so it is not expected to fire.

Everything else in the tick is unchanged: still touches only `game_best_moves` + `best_moves_completed_at`, never `game_flaws` (S-06/D-02), still stamps only when `maia_engine.is_maia_available()` (Phase 176 D-01 guardrail), still ONE `asyncio.gather` with no session open.
  </action>
  <verify>
    <automated>uv run ruff check app/services/eval_drain.py && uv run ty check app/services/eval_drain.py</automated>
  </verify>
  <done>For a lichess-eval game the minimal drain overrides `engine_result_map` best_cp/best_mate from the fresh MultiPV-2 search's `res[0]/res[1]`, keeps the stored best_move as identity key, and leaves engine games unchanged. ruff + ty clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Update changed-semantics tests + add positive coverage (mutation discipline)</name>
  <files>tests/services/test_eval_queue.py, tests/services/test_eval_drain.py</files>
  <behavior>
    - Residual fallback: a GUEST lichess-eval game (full_pv NULL, lichess_evals_at set) IS now returned by `_claim_tier3_derived` with is_lichess_eval_game=True (Population A). Reverses the old `test_residual_fallback_excludes_guest_backlog_game` (~1207).
    - tier-4b: a NON-GUEST lichess-eval game (full_pv set, best_moves NULL, lichess_evals_at set) IS now picked by `_claim_tier4_bestmove` (Population B). Reverses the old tier-4b lichess-exclusion assertions (~2036-2369, incl. ~2207/2218).
    - tier-4b: a GUEST full_pv-set best_moves-NULL game IS picked (Population B2, include_guests=True).
    - Non-regression: `_es_weighted_user_pick` default (tier-3 needs-engine Step-1, tier-4-blob Stage-1) STILL excludes guests — keep/repoint `test_excludes_guests` (~2107) and `test_tier4_excludes_guests` (~1713) to assert the shared literal is NOT flipped (a guest is not picked by tier-3 needs-engine / tier-4-blob).
    - Disjointness: with a residual-eligible guest game AND a tier-4b-eligible game present, each is claimed by its own lane (no double-claim); tier-3 preempts (dispatch order).
    - Divergence-guard parity (drain): a lichess-eval game drained via `_tier4b_minimal_drain_tick` stores `game_best_moves.best_cp` from the fresh Stockfish search, NOT the stored lichess `game_positions.eval_cp`. Assert best_cp equals the mocked `evaluate_nodes_multipv2` best (res[0]) and differs from the seeded lichess eval; assert an engine game still stores the stored eval unchanged.
  </behavior>
  <action>
Update the tests whose semantics changed and add positive coverage for the newly-covered populations. Reuse the existing `_make_game` helper (supports full_pv_completed_at / lichess_evals_at / best_moves_completed_at) and the existing guest-user creation pattern from `test_excludes_guests`. For the drain test, follow the `evaluate_nodes_multipv2` / `is_maia_available` / `score_move` mocking already used in test_eval_drain.py (seed `game_positions` with a distinct lichess `eval_cp` and a `best_move` matching the played move so a candidate is produced; mock the fresh search to return a clearly-different best cp).

MUTATION DISCIPLINE (per project rule "prove a gap fix by reverting it"): for EACH of the three predicate/param changes and the drain best_cp override, after the test passes, REVERT the corresponding production change locally and confirm the specific new/updated test FAILS, then restore. Do not accept grep/symbol-presence as proof. In particular the drain best_cp test MUST fail when Task 2's override is removed (i.e. it must distinguish lichess-sourced from Stockfish-sourced best_cp, not merely assert a row exists).

Remove any now-dead exclusion assertions rather than leaving contradictory expectations; knip/ty/ruff must stay clean.
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/services/test_eval_queue.py tests/services/test_eval_drain.py -x</automated>
  </verify>
  <done>Updated exclusion tests reflect the new inclusion semantics; positive tests cover Populations A, B, B2, lane disjointness, and drain best_cp parity; each fix demonstrably fails its test when reverted; full targeted suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SQL predicate composition (claim lanes) | Query SHAPE composed from fixed trusted literals; all VALUES bound via sa.text params (QUEUE-08). |
| Guest data exposure to analysis lanes | Deliberately opening guest games to the tier-3 residual + tier-4b lanes (CONTEXT-locked "process guests"). |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fsz-01 | Tampering (SQL injection) | new `include_guests` conditional fragment in `_es_weighted_user_pick` | medium | mitigate | Compose only from fixed in-code literals; no request/user input; all numeric values stay bound via the params dict (QUEUE-08). Covered by ty + existing queue tests. |
| T-fsz-02 | Information disclosure | guest games entering analysis lanes | low | accept | Intentional per CONTEXT ("Guest data — process them"); guests remain excluded from tier-3 needs-engine + tier-4-blob bulk drains (shared literal not flipped) — verified by retained `test_excludes_guests` / `test_tier4_excludes_guests`. |
| T-fsz-03 | Denial of service (contention) | extended tier-4b vs tier-3 residual double-claim | low | mitigate | Lanes disjoint on `full_pv_completed_at`; tier-3 preempts in dispatch order — asserted by the disjointness test. |
</threat_model>

<verification>
Full local pre-merge gate before integrating (CLAUDE.md):

```
uv run ruff format app/ tests/
uv run ruff check app/ tests/ --fix
uv run ty check app/ tests/
uv run pytest -n auto -x
```

No migration (predicate/logic only). No frontend. No backfill script — the existing 12,643 (B) and 18,882 (A) drain opportunistically through the lanes at the lowest idle rung.
</verification>

<success_criteria>
- Guest lichess-eval full_pv-NULL games are claimable by the tier-3 residual (A).
- Non-guest AND guest lichess-eval full_pv-SET best_moves-NULL games are claimable by tier-4b (B, B2).
- tier-3 needs-engine + tier-4-blob still exclude guests.
- The minimal drain stores Stockfish `best_cp` for lichess games (divergence-guard parity), engine games unchanged.
- Every production change is proven by reversion (mutation discipline).
- ruff + ty + full backend suite green.
</success_criteria>

<output>
Create `.planning/quick/260719-fsz-ensure-every-fully-analyzed-game-gets-be/260719-fsz-SUMMARY.md` when done.
</output>
