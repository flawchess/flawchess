---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
plan: 02
type: execute
wave: 2
depends_on: ["123-01"]
files_modified:
  - app/schemas/eval_remote.py
  - app/routers/eval_remote.py
  - app/services/eval_queue_service.py
  - tests/test_eval_worker_endpoints.py
autonomous: true
requirements: ["SEED-051-D-2", "SEED-051-D-5", "SEED-051-D-7", "D-02", "D-05", "D-07", "D-09", "D-10"]
nyquist_compliant: true

must_haves:
  truths:
    - "POST /eval/remote/entry-lease (operator-token auth) returns {game_id, ply, fen}[] for pending big-import games, gated by the D-5 backlog existence probe (204 when backlog < threshold)"
    - "POST /eval/remote/entry-submit applies entry evals at the correct ply with NO +1 shift (uses _apply_eval_results), classifies flaws, stamps evals_completed_at, and is idempotent on double-submit"
    - "GET/POST /eval/remote/lease accepts an optional scope param: absent = today's bundled tier-1>2>3 (backward-compat); scope=explicit = tier-1/2 only; scope=idle = tier-3 only"
    - "X-Worker-Id header (advisory only) populates leased_by / entry_eval_leased_by; absent header falls back to 'remote-worker'"
    - "Both new endpoints reject missing/invalid operator token (require_operator_token, unchanged)"
  artifacts:
    - path: "app/routers/eval_remote.py"
      provides: "/entry-lease + /entry-submit endpoints, scope param on /lease, X-Worker-Id label dependency"
      contains: "entry-lease"
    - path: "app/schemas/eval_remote.py"
      provides: "EntryLeasePosition / EntryLeaseResponse / EntrySubmitEval / EntrySubmitRequest / EntrySubmitResponse"
      contains: "EntryLeaseResponse"
    - path: "app/services/eval_queue_service.py"
      provides: "scope: Literal['explicit','idle'] | None param on claim_eval_job"
      contains: "scope"
  key_links:
    - from: "app/routers/eval_remote.py::entry_lease"
      to: "app/services/eval_drain.py::_claim_entry_eval_games"
      via: "shared claim helper from Plan 01"
      pattern: "_claim_entry_eval_games"
    - from: "app/routers/eval_remote.py::entry_submit"
      to: "app/services/eval_drain.py::_apply_eval_results"
      via: "NO-shift entry-ply write path (NOT _apply_full_eval_results)"
      pattern: "_apply_eval_results"
    - from: "app/routers/eval_remote.py::lease"
      to: "app/services/eval_queue_service.py::claim_eval_job"
      via: "scope param pass-through"
      pattern: "scope"
---

<objective>
Add the two batched entry-ply endpoints (`/entry-lease`, `/entry-submit`), the `scope` selector on `/lease`, the D-5 backlog gate, and the `X-Worker-Id` advisory label — all behind the existing operator-token auth.

Purpose: This is the server-side half of the remote fan-out. `/entry-lease` hands a remote worker a batch of FENs (gated so it only fires on big imports, D-5/D-02); `/entry-submit` writes the worker's depth-15 evals through the existing SEED-044 no-shift path. The `scope` param and `X-Worker-Id` are additive-optional so an un-upgraded worker (Plan 03's old binary) keeps working unchanged — zero-coordination rollout.

Output: Entry-ply schemas, two new router endpoints, the `scope` param plumbed through `claim_eval_job`, and the worker-id label dependency.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-CONTEXT.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-RESEARCH.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-PATTERNS.md
@.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-01-SUMMARY.md

# Read these source files first for exact analog shapes:
@app/routers/eval_remote.py
@app/schemas/eval_remote.py
@app/services/eval_queue_service.py
@app/services/eval_drain.py
@tests/test_eval_worker_endpoints.py
</context>

## Artifacts this phase produces (Plan 02 subset)

- `EntryLeasePosition` / `EntryLeaseResponse` / `EntrySubmitEval` / `EntrySubmitRequest` / `EntrySubmitResponse` — new Pydantic schemas (entry-ply carries NO best_move/pv)
- `POST /eval/remote/entry-lease` — new endpoint (D-07), D-5 backlog-gated
- `POST /eval/remote/entry-submit` — new endpoint (D-07), no-shift write path
- `scope: Literal["explicit", "idle"] | None` — new param on `/lease` and on `claim_eval_job` (D-05)
- `X-Worker-Id` HTTP header → `worker_id_label` dependency → `leased_by` / `entry_eval_leased_by` (D-10)

<tasks>

<task type="auto">
  <name>Task 1: Entry-ply schemas + scope param on claim_eval_job</name>
  <files>app/schemas/eval_remote.py, app/services/eval_queue_service.py</files>
  <read_first>
    @app/schemas/eval_remote.py (LeasePosition/LeaseResponse/SubmitEval/SubmitRequest/SubmitResponse shapes; the `MAX_SUBMIT_EVALS` cap; `Field(ge=0)` on ply).
    @app/services/eval_queue_service.py (`claim_eval_job` structure: sweep → `_claim_queued_job` (tier-1/2) → gate on EVAL_AUTO_DRAIN_ENABLED → `_claim_tier3_derived` (tier-3); the existing `Literal` discipline).
    PATTERNS.md "app/schemas/eval_remote.py" and "app/services/eval_queue_service.py" sections.
    NOTE the real function names: tier-1/2 = `_claim_queued_job` (NOT `_claim_tier1_2_queued`); tier-3 = `_claim_tier3_derived`.
  </read_first>
  <action>
    In `app/schemas/eval_remote.py` add the entry-ply schemas (batched across games, so each row carries `game_id`; entry-ply returns only cp/mate — NO best_move/pv): `EntryLeasePosition {game_id: int, ply: int = Field(ge=0), fen: str}`, `EntryLeaseResponse {positions: list[EntryLeasePosition], leased_at: datetime}`, `EntrySubmitEval {game_id: int, ply: int = Field(ge=0), eval_cp: int | None, eval_mate: int | None}`, `EntrySubmitRequest {sf_version: str, evals: list[EntrySubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)}`, `EntrySubmitResponse {game_ids: list[int], stamped_count: int}`. Reuse the existing `MAX_SUBMIT_EVALS` cap (V5 DoS guard — a 50-game batch × ~3 plies = ~150 < 1024, fits as-is).

    In `app/services/eval_queue_service.py` add `scope: Literal["explicit", "idle"] | None = None` to `claim_eval_job` (use `Literal`, never bare str — CLAUDE.md). Branch: `scope is None` → today's EXACT bundled flow unchanged (tier-1/2 then tier-3) — backward-compat for un-updated workers (RESEARCH Pitfall 4). `scope == "explicit"` → run ONLY `_claim_queued_job`, return None if empty (skip the tier-3 fallthrough). `scope == "idle"` → skip `_claim_queued_job`, run ONLY `_claim_tier3_derived` (still gated by EVAL_AUTO_DRAIN_ENABLED). Keep the commit-then-release short-session discipline intact.
  </action>
  <verify>
    <automated>uv run pytest tests/test_eval_worker_endpoints.py -x && uv run ty check app/schemas/eval_remote.py app/services/eval_queue_service.py</automated>
  </verify>
  <acceptance_criteria>
    Five entry-ply schemas exist with `Field(ge=0)` on ply and the `MAX_SUBMIT_EVALS` cap on the evals list. `claim_eval_job` accepts a typed `scope` param; `scope=None` preserves the exact pre-phase behavior; explicit/idle select single tiers. `ty check` clean. Existing tests still green.
  </acceptance_criteria>
  <done>Schemas + scope param exist and typecheck; scope=None is unchanged behavior.</done>
</task>

<task type="auto">
  <name>Task 2: /entry-lease + /entry-submit endpoints, scope on /lease, X-Worker-Id label</name>
  <files>app/routers/eval_remote.py</files>
  <read_first>
    @app/routers/eval_remote.py (`/lease`+`/submit` endpoints, `_build_lease_positions`, `_apply_submit`, `require_operator_token`, the `X-Operator-Token` Header(alias=...) pattern, `_WORKER_ID_REMOTE`, the SF-version gate in `/submit`).
    @app/services/eval_drain.py (`_claim_entry_eval_games` from Plan 01; `_collect_eval_targets_from_db`, `_load_pgns_for_games`; `_apply_eval_results` [NO shift], `_classify_and_insert_flaws`, `_mark_evals_completed`; the `ENTRY_LEASE_*` constants).
    PATTERNS.md "app/routers/eval_remote.py" section (full endpoint structure + the D-5 probe + the no-shift write path) and the Anti-Patterns table.
  </read_first>
  <action>
    Add a `worker_id_label` dependency reading `X-Worker-Id` via `Header(alias="X-Worker-Id", default=None)`, returning `x_worker_id or _WORKER_ID_REMOTE` (D-10 — advisory ONLY, never used for authz/ownership; absent → "remote-worker" backward-compat). Wire this label into the full-ply `/lease` claim (replacing the hardcoded `_WORKER_ID_REMOTE` so `eval_jobs.leased_by` becomes per-worker) and into the new entry endpoints.

    Add an optional `scope: Literal["explicit", "idle"] | None = None` query param to `/lease`, pass it through to `claim_eval_job(scope=...)`. Keep `response_model=None` and the existing `Response | LeaseResponse` return. Absent scope → today's exact bundled response.

    Add `POST /entry-lease` (D-07), `Depends(require_operator_token)`:
    1. D-5 backlog existence probe FIRST (RESEARCH Pattern 5): `SELECT 1 FROM games WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 1 OFFSET :offset` with `offset = ENTRY_LEASE_BACKLOG_THRESHOLD - 1` (= 299; OFFSET is THRESHOLD-1, RESEARCH Pitfall 6 — bind as a param, NO f-string). If `scalar_one_or_none() is None` → return `Response(status_code=204)` (worker falls to scope=idle). The server pool does NOT run this probe (D-02 — gate is remote-lease-only).
    2. `game_ids = await _claim_entry_eval_games(session, worker_id_label, ENTRY_LEASE_BATCH_SIZE, ENTRY_LEASE_TTL_SECONDS)`; commit the claim; if empty → 204.
    3. Derive `{game_id, ply, fen}` via `_collect_eval_targets_from_db(session, game_ids, pgn_map)` + `target.board.fen()` (D-2 — server derives, worker never parses PGN). Return `EntryLeaseResponse`. Mirror the read-session-then-close discipline of the existing endpoints (commit the claim before returning; never gather on an open session).

    Add `POST /entry-submit` (D-07), `Depends(require_operator_token)`:
    1. SF-version gate FIRST (copy the `/submit` version-check verbatim).
    2. Group submitted evals by `game_id`. For each game, RE-DERIVE the `_EvalTarget`s server-side from `game_id` (so ply/endgame_class stay server-controlled — Pitfall 1; the worker payload can only set eval_cp/eval_mate for plies the server chose). Zip the worker's `{ply: (eval_cp, eval_mate)}` onto the re-derived targets by ply.
    3. Apply via `_apply_eval_results` (NO +1 shift — CRITICAL: do NOT use `_apply_full_eval_results`, which shifts; that is the full-ply `/submit` path) → `_classify_and_insert_flaws` → `_mark_evals_completed`. The completion stamp is the permanent lease release (queue predicate `evals_completed_at IS NULL` stops matching); optionally NULL `entry_eval_lease_expiry` for a clean in-flight view. Return `EntrySubmitResponse`.

    Sentry: capture non-trivial exceptions in the new endpoints (set_context with game_ids/worker label, never embed variables in the message). Skip expected validation ValueErrors.
  </action>
  <verify>
    <automated>uv run pytest tests/test_eval_worker_endpoints.py -x && uv run ty check app/routers/eval_remote.py</automated>
  </verify>
  <acceptance_criteria>
    `/entry-lease` and `/entry-submit` exist, both behind `require_operator_token`. `/entry-lease` runs the OFFSET=THRESHOLD-1 probe before claiming and returns 204 when backlog is shallow. `/entry-submit` uses `_apply_eval_results` (no shift), not `_apply_full_eval_results`. `/lease` accepts `scope` and passes it through; absent scope is unchanged. `X-Worker-Id` label defaults to "remote-worker". `ty check` clean.
  </acceptance_criteria>
  <done>Both endpoints + scope param + worker-id label exist, auth-gated, no-shift write path, D-5 probe wired; ty clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Endpoint tests — entry-lease/submit, gate, scope, worker-id</name>
  <files>tests/test_eval_worker_endpoints.py</files>
  <read_first>
    @tests/test_eval_worker_endpoints.py (existing lease/submit tests + auth tests; `test_submit_applies_post_move_shift` [INVERT for entry — assert NO shift]; `test_submit_idempotent`; `test_submit_stamps_full_evals_completed_at` [check `evals_completed_at`]; `TestTier1Claiming` + `_seed_eval_job` for the scope tests; `_make_client`, `_patch_router_session`, the extended `_insert_game(evals_completed_at=None)`).
    PATTERNS.md "tests/test_eval_worker_endpoints.py" section + the RESEARCH §Test Map rows.
  </read_first>
  <behavior>
    - entry_lease: with ≥ threshold pending games (evals_completed_at=None), POST /entry-lease (valid token) returns 200 with a non-empty `positions` list of `{game_id, ply, fen}`.
    - entry_lease_gate: with exactly THRESHOLD-1 pending games → 204; with exactly THRESHOLD pending → 200 (off-by-one boundary, Pitfall 6).
    - entry_lease_auth: missing/invalid operator token → 403/401 (T-123-auth).
    - entry_submit_no_shift: submit an eval for a game and assert it lands at `ply` (NOT `ply-1`) — the inverse of the full-ply shift test.
    - entry_submit_stamps: after a complete entry-submit, `evals_completed_at IS NOT NULL` for the game.
    - entry_submit_idempotent: double entry-submit is safe (no error, no duplicate flaws).
    - scope: `scope=explicit` returns only tier-1/2 work; `scope=idle` returns only tier-3; absent scope = bundled (use `_seed_eval_job` / TestTier1Claiming analogs).
    - worker_id: `X-Worker-Id: box1` populates `entry_eval_leased_by`/`leased_by` = "box1"; absent header → "remote-worker".
  </behavior>
  <action>
    Add the above tests to `tests/test_eval_worker_endpoints.py`, reusing existing fixtures (no new conftest infra). Use the extended `_insert_game(evals_completed_at=None)` for pending games. For the gate test, insert exactly THRESHOLD-1 then THRESHOLD pending games and assert the 204/200 boundary. For scope tests, mirror `TestTier1Claiming`'s `_seed_eval_job` setup. For worker_id, send the `X-Worker-Id` header on the lease call and read back the leased_by column. Tear down inserted rows.
  </action>
  <verify>
    <automated>uv run pytest tests/test_eval_worker_endpoints.py -k "entry or scope or worker_id" -x</automated>
  </verify>
  <acceptance_criteria>
    All new tests pass: entry-lease payload + auth, the THRESHOLD-1/THRESHOLD gate boundary, entry-submit no-shift + stamps + idempotent, scope selection (explicit/idle/absent), and X-Worker-Id population + fallback.
  </acceptance_criteria>
  <done>Entry-lease/submit, D-5 gate boundary, scope, and worker-id all covered by green automated tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| remote worker → /entry-lease, /entry-submit | Untrusted operator-token-authenticated client crosses into the server's claim + write path |
| worker payload → DB write | Worker-supplied eval_cp/eval_mate + X-Worker-Id label cross into stored rows |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-123-01 | Spoofing | /entry-lease, /entry-submit auth | mitigate | Both endpoints go through `Depends(require_operator_token)` exactly like /lease and /submit — constant-time `hmac.compare_digest`, fail-closed (403 when unconfigured), 401 on wrong token. No new auth surface. (Load-bearing control.) |
| T-123-02 | Tampering | sa.text claim + D-5 probe | mitigate | Every value in `_claim_entry_eval_games` and the OFFSET probe is bound as a `:param` (ttl, worker_id, batch, offset) — no f-string interpolation (project Security rule; mirror `_claim_queued_job`). |
| T-123-03 | Spoofing | X-Worker-Id header | accept | Advisory observability label only — never used for authz or ownership. Owner is re-derived from the game row server-side (eval_remote.py existing pattern). A spoofed worker-id can only mislabel a leased_by column; the operator token is the real gate. |
| T-123-04 | Tampering | worker submits evals for a game it didn't lease | mitigate | Server re-derives `_EvalTarget`s from `game_id` (ply/endgame_class server-controlled); the worker payload can only set eval_cp/eval_mate for plies the server chose. Idempotent ON CONFLICT DO NOTHING flaw insert + completion-stamp re-write make any overlap correctness-safe. |
| T-123-05 | Denial of Service | oversized /entry-submit body | mitigate | `EntrySubmitRequest.evals` capped at `MAX_SUBMIT_EVALS` (`Field(max_length=...)`) — same DoS guard as /submit. |
| T-123-06 | Tampering | server + remote double-evaluating the same game | mitigate | The shared `_claim_entry_eval_games` (Plan 01) uses `FOR UPDATE SKIP LOCKED` + the lease predicate so server and remote partition disjoint batches; TTL reclaims crashes; completion stamp ends the lease. |
| T-123-07 | Tampering | wrong-version Stockfish evals submitted | mitigate | SF-version gate at the top of /entry-submit (copied verbatim from /submit) rejects mismatched `sf_version`. |
| T-123-SC | Tampering | npm/pip/cargo installs | n/a | No packages installed this phase (RESEARCH Package Legitimacy Audit: not applicable). |
</threat_model>

<verification>
- `uv run pytest tests/test_eval_worker_endpoints.py -x` green (existing + new entry/scope/worker-id tests).
- `uv run ty check app/ tests/` clean.
- Auth: `/entry-lease` and `/entry-submit` both reject missing/invalid operator token.
- No-shift: entry-submit test asserts eval lands at `ply`, not `ply-1`.
- Gate boundary: THRESHOLD-1 → 204, THRESHOLD → 200.
- Grep guard: `_apply_full_eval_results` does NOT appear in the `/entry-submit` handler (`grep -v '^#' app/routers/eval_remote.py | grep -c _apply_full_eval_results` unchanged from baseline — entry-submit must use `_apply_eval_results`).
</verification>

<success_criteria>
- Two batched entry-ply endpoints behind operator-token auth.
- D-5 backlog gate (OFFSET = THRESHOLD-1) governs /entry-lease only (server pool unaffected, D-02).
- /entry-submit uses the no-shift write path (_apply_eval_results) + idempotent stamp.
- scope param: absent = bundled (backward-compat), explicit/idle = single tier.
- X-Worker-Id populates leased_by columns; absent → "remote-worker".
- All threats have a disposition; auth threat T-123-01 mitigated via require_operator_token.
</success_criteria>

<output>
Create `.planning/phases/123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-/123-02-SUMMARY.md` when done.
</output>
