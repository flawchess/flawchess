---
id: SEED-074
status: dormant
planted: 2026-07-01
planted_during: Design discussion (2026-07-01) clarifying the local-vs-remote blob asymmetry left behind by Phase 146 / SEED-071. While tracing the post-v1.30 import→eval→tag pipeline we confirmed that the remote submit path writes UNGATED (pre-forcing-line-gate) tactic tags into game_flaws and only re-gates them later when tier-4 blob backfill runs. Because tactic tags feed backend statistics AND game-selection filters (not just UI), a display-layer fix is insufficient — the ungated tags must never be persisted as final. Two complementary fixes fell out: A (never persist ungated tags — cheap, data-level) and B (upgraded-worker atomic eval+blob pipeline so remote games are gated at write time, no window at all).
trigger_when: soon — real correctness gap affecting first-contact UX and any stat/filter that keys on tactic_motif. Part A is low-effort / high-value and can ship on its own (or pulled into a quick task) ahead of B. Part B is a medium backend + fleet-worker phase; sequence it after A so A is the graceful-degradation net. Both are safe to defer until the v1.30 corpus backfill settles, but A should not wait long.
scope: |
  Part A — Small backend, classify path only (~5-15 lines + a threaded flag + tests):
    app/services/flaws_service.py::_classify_tactic_gated / _build_flaw_record / classify_game_flaws,
    call sites in app/routers/eval_remote.py::_apply_submit and app/services/eval_drain.py.
    No schema migration.
  Part B — Medium backend + worker phase (new versioned lease+submit endpoint PAIR,
    fleet-worker upgrade, server-authoritative classify with worker-supplied blobs, single
    atomic write): app/routers/eval_remote.py, app/schemas/eval_remote.py,
    app/services/eval_drain.py, app/services/eval_queue_service.py, scripts/remote_eval_worker.py.
    No DB schema/migration (reuses game_flaws.allowed_pv_lines/missed_pv_lines + the existing
    completion markers). No blob-shape or gate-logic change. No STOCKFISH_POOL_SIZE change.
    Reuses the SEED-073 over-cap sentinel for the ~17 fat games (no chunking needed).
---

# SEED-074: Persist only forcing-line-GATED tactic tags — never write ungated tags (A), and gate remote tags at write time via an upgraded-worker atomic eval+blob pipeline (B)

## Why This Matters

The forcing-line tactic gate (v1.30, phases 141–145) is meant to suppress false-positive
tactic motifs by requiring the refutation line to actually be forcing. But **on the remote
eval path the gate does not run at write time** — the game is stamped analyzed with **raw,
ungated** tactic tags in `game_flaws.tactic_motif`, and those tags are only corrected later
when the tier-4 flaw-blob backfill eventually draws the game and runs the D-07 gated retag.

Two problems with that window:

1. **It pollutes data, not just the UI.** Tactic tags are consumed by backend statistics and
   by game-selection filters (tag-based cohort queries), so hiding tags in the frontend does
   nothing — the noisy values are already materialized. A first-contact user (or any stat/
   filter) sees false-positive tactics until the backfill catches up.

2. **The window is now effectively unbounded.** Tier-4 was recency-ordered by a top-N CTE in
   Phase 146 D-01, but that was **replaced by a two-stage Efraimidis–Spirakis lottery** (see
   `_claim_tier4_blob`), so a freshly-analyzed game competes in the same weighted draw as the
   whole old corpus. There is no strong "fresh games gate first" guarantee anymore.

There is also an **undesirable local-vs-remote asymmetry**: the *local* full-drain
(`eval_drain._full_drain_tick`) builds MultiPV-2 blobs INLINE and writes gated tags in the
same tick, so locally-analyzed games are never ungated; only remotely-analyzed games spend
time ungated. Same game, different data quality depending on which consumer processed it.

## Background — how we got here (do not re-litigate)

- **Phase 142 (v1.30)** added inline server-side MultiPV-2 continuation eval on the LIVE
  `/eval/remote/submit` path so the gate could run at submit time.
- That inline engine work (~22·N 1M-node evals for an N-flaw game, on the shared Stockfish
  pool, before the HTTP response) caused **worker ReadTimeouts under load** and contended with
  tier-3 drain (Sentry FLAWCHESS-7Y). See [[SEED-071]].
- **Phase 146 / SEED-071 Option 2** fixed the load by *deferring* blobs: `_apply_submit` now
  forces `blob_map = {}`, applies evals, **raw-classifies** flaws, stamps
  `full_evals_completed_at` + `full_pv_completed_at`, and leaves
  `allowed_pv_lines`/`missed_pv_lines` NULL. The game then matches the tier-4 predicate and
  drains through `/flaw-blob-lease` → worker MultiPV=2 → `/flaw-blob-submit` (D-07 gated
  retag). This solved the load problem but **created the ungated-tag window** this seed closes.

So: the server already runs ZERO Stockfish on the remote submit path. The remaining work is
not about server load — it is about making the tags **correct at write time** instead of
"raw now, fixed later."

## Verified facts that make this cheap (checked 2026-07-01 against the code)

- **`classify_game_flaws` is pure and deterministic** — `flaws_service.py:875`, no `session`,
  no `await`, no DB. Inputs: `game`, `positions` (with evals), optional `pv_by_ply`,
  `flaw_pv_blobs`. Its transitive deps (`eval_utils`, `forcing_line_gate`, `tactic_detector`,
  `normalization`) are DB-free; the one function used from `openings_service`
  (`derive_user_result`) is pure (called without a session).
- **The fleet worker is already a fat `app.*` client** — `scripts/remote_eval_worker.py`
  imports `app.core.config`, `app.models.*`, `app.services.engine`. It can
  `from app.services.flaws_service import classify_game_flaws` and run the EXACT same code the
  server runs — no duplication, no thin-client rewrite, no divergence-by-construction.
- **The worker already speaks the blob contract** — it has the tier-4 rung today:
  `_handle_flaw_blob_response` / `_eval_flaw_blob_positions` lease FENs, eval at MultiPV=2,
  and POST to `/flaw-blob-submit`. B reuses this machinery, sequenced into the same task.
- **Per-ply MultiPV-2 is NOT wasteful** — every eval is a fixed `_NODES_BUDGET = 1_000_000`
  node search (`engine.py`); `multipv=2` retains 2 root lines from the SAME search (same node
  budget). The expensive part is the per-node re-eval of the continuation line (nodes 1..12 of
  both the allowed and missed lines, `PV_CAP_PLIES = 12`) — that is the "blob," and it is
  genuinely new compute the game sweep never did. (Phase 146 already dropped the remote
  full-ply pass to MultiPV-1; only the local drain still does per-ply MultiPV-2.)
- **Payload size is NOT a blocker for a single game.** SEED-073 quantified per-game walkable
  blob positions across 409,605 prod games: **p99 = 489, p99.9 = 693**, cap
  `MAX_SUBMIT_EVALS = 1024`. Only **17 games (0.0042%, ~1 in 24,000)** exceed the cap (44–78
  flaws, bullet blitz-fests; largest 1,680 = 1.64× cap). B combines full-ply evals + blobs as
  two separately-capped lists, each well under 1024 for essentially every real game. **No
  chunking** — B reuses SEED-073's over-cap sentinel for the fat games. See [[SEED-073]].

---

## Part A — Never persist ungated tactic tags (data-level, ship first)

**Goal:** when a tactic motif is detected but no forcing-line gate can be applied *because the
blob is still pending* (deferred to backfill), write `tactic_motif = NULL` instead of the raw
motif. Then stats/filters keying on `tactic_motif` see "not classified yet" (which they don't
count) rather than a false positive, and the value self-heals when the blob lands and the D-07
gated retag runs. This also becomes B's graceful-degradation net (a flaw whose blob a skewed
worker didn't supply → NULL, not raw).

**Where:** `_classify_tactic_gated` (`flaws_service.py:525`). Today (lines 560–565) the gate
runs only when `motif is not None AND pv_blob is not None AND len(pv_blob) > 0 AND
pre_flaw_eval_cp is not None`; otherwise it **returns the raw motif** (line 573). The remote
submit path hits this with `pv_by_ply` populated (so detection fires) but `pv_blob = None` (no
blob) → raw ungated tag written. A changes that outcome to suppression.

**CRITICAL nuance — do NOT blanket-suppress every no-blob case.** The gate is legitimately
skipped for reasons that are FINAL, not pending, and those tags must be KEPT:

- **`pre_flaw_eval_cp is None` (mate-adjacent flaws)** — carries `eval_mate`, not `eval_cp`;
  the cp-based gate has nothing to compare, so the raw result stands permanently (RESEARCH A1,
  accepted). A blob will never change this. **Keep the raw tag** — suppressing it loses a real
  mate-tactic tag forever.
- **D-06 sentinel `[]`** — blob genuinely could not be assembled (single-legal-move position,
  analysis gap). Not pending; no blob will ever exist. **Keep the raw tag.**
- **Pre-Phase-142 old-corpus rows** — no blob because blobs didn't exist yet; these DO get
  backfilled by tier-4, so suppress-until-backfill is acceptable but is a visible display
  change for old games. Decide explicitly (see open questions).

So A needs to distinguish "blob **pending** (deferred, will arrive)" from "blob **not
applicable** (final)". Thread an explicit signal (e.g. a `blobs_pending: bool` /
`defer_ungated: bool` param) from the call site that KNOWS blobs are deferred
(`eval_remote.py::_apply_submit`, which passes `blob_map = {}`), through
`classify_game_flaws` → `_build_flaw_record` → `_classify_tactic_gated`. Only when
`blobs_pending` is true AND detection fired AND no blob is present AND `pre_flaw_eval_cp is not
None` (i.e. the gate *would* apply once the blob arrives) → return `(None, None, None, None)`.
The local full-drain path (blobs present inline) and the mate-adjacent/sentinel cases are
unaffected.

**Acceptance (A):**
- Remote `_apply_submit` no longer writes a non-NULL `tactic_motif` for any cp-based flaw whose
  blob is deferred; those rows carry NULL until the gated retag fills them.
- Mate-adjacent flaws (`pre_flaw_eval_cp IS NULL`) and D-06 `[]` sentinels KEEP their raw tags.
- Local full-drain output unchanged (blobs already present → gated as before).
- Tier-4 / `/flaw-blob-submit` D-07 gated retag still fills the real gated tag when the blob
  arrives.
- Test: a synthetic remote submit with a detectable-but-non-forcing cp flaw writes NULL (not
  the raw motif); a mate-adjacent flaw writes its raw motif; after a subsequent blob submit the
  cp flaw carries the correctly-gated tag.

---

## Part B — Upgraded-worker atomic eval+blob pipeline (gate at write time, no window)

**Goal:** an upgraded worker analyzes a game end-to-end — full-ply evals + MultiPV-2 blobs —
and submits them together in ONE package. The server runs its OWN authoritative
`classify_game_flaws` with the worker-supplied blobs and writes flaws + gated tags +
completion markers in a single transaction. No round-trip, no orphan state, no ungated window.

**Why worker-side blobs work now (see verified facts):** classify is pure and the worker is a
fat `app.*` client. The worker can classify LOCALLY purely as a *hint* — to learn which plies
are flaws so it knows which continuation lines to blob — then compute the blobs and submit
evals + blobs. It does NOT need a server round-trip to learn the flaw set.

**Trust boundary — keep the SERVER authoritative for semantics.** Do NOT let the worker's
classification be the source of truth (a lagging-deploy worker would silently write wrong
flaws/tags). The worker submits only **raw engine outputs**: full-ply evals + per-flaw-line
blobs, both keyed by ply. The server:
1. Runs its own `classify_game_flaws` on its own `game_positions` + the submitted evals
   (cheap, pure, zero Stockfish).
2. Passes the submitted blobs into that classify so the forcing-line gate fires.
3. Writes flaws + gated tags + `allowed_pv_lines`/`missed_pv_lines` + `full_evals_completed_at`
   + `full_pv_completed_at` in ONE transaction.

**Graceful degradation under version skew** (this is where A pays off):
- A blob for a ply the server does NOT consider a flaw → dropped.
- A flaw the server found but the worker did NOT blob (skew, or over-cap) → A writes NULL, and
  tier-4 backfills it later. No corruption, no orphan.

**New versioned endpoint PAIR (agreed).** B changes the contract (submit now carries blobs;
completion is gated on them), and a mixed fleet — old workers submitting evals-only, upgraded
workers submitting evals+blobs — will run simultaneously across a deploy. So add a **new lease
+ new submit** pair rather than overloading the existing endpoints:
- New workers poll the new lease (claims a game for the full eval+blob pipeline; may carry
  hints later) and POST the atomic evals+blobs package to the new submit.
- Old `/lease` + `/submit` stay as deprecated, removed once the fleet is fully upgraded.
- Distinct schemas keep their own `MAX_SUBMIT_EVALS` DoS-guard caps; gives rollback safety
  (flip workers back without a server redeploy) and avoids server-side shape-sniffing.

**Fat games:** reuse the SEED-073 over-cap sentinel — a game whose walkable blob positions
exceed `MAX_SUBMIT_EVALS` gets `[]` sentinels (keeps its existing/ungated-or-A-NULL tags),
never blocks. No chunking.

**Consequence — tier-4 shrinks to a backfill-only role.** Because B is atomic all-or-nothing,
there is **no orphan case for new games**, so tier-4 (`/flaw-blob-lease` + `/flaw-blob-submit`)
is needed ONLY to drain the **pre-B old corpus** (games already stamped complete with NULL
blobs). Once that corpus is drained, tier-4 and its endpoints can retire too. End-state
endpoint map: new lease+submit (happy path) → old lease+submit (removed post-upgrade) →
flaw-blob-lease+submit (retire when old corpus drained).

**Acceptance (B):**
- An upgraded worker leases a game, evals full-ply, computes MultiPV-2 blobs for the flaws it
  classified locally, and submits evals+blobs in one request.
- The server writes flaws + forcing-line-gated tags + completion markers atomically; the game
  is NEVER in an analyzed-but-ungated state (verify `tactic_motif` is gated the instant
  `full_evals_completed_at` is set for games processed by the new path).
- Old workers on the old endpoints still function unchanged during rollout.
- Fat games (> `MAX_SUBMIT_EVALS`) sentinel cleanly (SEED-073 path), no 500, no re-pick loop.
- Local full-drain (`_full_drain_tick`) behavior unchanged (already gated inline) — or,
  optionally, unify it onto the same write path (see open questions).

---

## Open questions for plan-phase

1. **A / old-corpus display:** should A also suppress raw tags on pre-Phase-142 rows (blob
   pending via tier-4), or only on the go-forward remote submit path? Suppressing changes what
   users see for already-imported games until backfill completes. Leaning: only go-forward
   (thread the flag from `_apply_submit`), leave existing rows for tier-4 to retag in place.
2. **B lease reuse vs new lease:** is a fully new lease endpoint warranted, or can the new
   worker reuse the existing full-ply `/lease` and only the SUBMIT be new? A new lease is
   cleaner for versioning/hints and rollback; a shared lease is less surface. Agreed lean = new
   pair, but confirm at plan time.
3. **Should the local full-drain be retired or kept?** With B, remote workers gate at write
   time. The local `_full_drain_tick` still exists (started in `main.py:81`) and still builds
   blobs inline. Keep it as local spare-capacity fallback, or retire to remove the asymmetry
   entirely once the fleet is reliable? (Local is not a request path, so it never had the
   timeout problem — no urgency to change it.)
4. **Worker "hint" classify cost:** the local classify on the worker is pure/cheap relative to
   40+ engine evals, but confirm it has the data it needs (it has PGN + plies from the lease
   and computes the evals itself; it must build lightweight `GamePosition`-like objects to call
   `classify_game_flaws`). Verify no hidden DB dependency sneaks in via `derive_user_result`.
5. **Schema/version tag on submit:** include a classifier/schema version in the new submit so
   the server can detect and reject/relabel skewed workers rather than silently trusting blob
   keys.

## Pointers (verified 2026-07-01)

- Remote submit (deferral origin): `app/routers/eval_remote.py::_apply_submit` — `blob_map = {}`
  at ~255–261, classify call ~281–283, completion stamps ~288–309.
- Deferred blob path: `eval_remote.py::flaw_blob_lease` (~725), `::flaw_blob_submit` (~913),
  `::_apply_flaw_blob_submit` (~789, D-07 gated retag).
- Tactic gate (Part A site): `app/services/flaws_service.py::_classify_tactic_gated` (525–573),
  `::_build_flaw_record` (~576), `::classify_game_flaws` (875, pure).
- Blob builders (Part B reference): `eval_drain.py::_build_flaw_multipv2_blobs` (1161),
  `::_walk_pv_boards` (1098), `::_build_line_blobs` (1125), `::_run_multipv2_pass` (1316),
  `::_batch_update_flaw_pv_lines` (1282), `::_build_flaw_blob_lease_positions` (1332).
- Local inline path (asymmetry): `eval_drain.py::_full_drain_tick` (2318), Step 3d blobs
  (2509–2514), write + classify (2538–2554).
- Engine: `app/services/engine.py::evaluate_nodes_multipv2` (608), `_NODES_BUDGET` /
  `PV_CAP_PLIES` (99 / 104).
- Tier-4 lottery (ES, replaced the CTE): `app/services/eval_queue_service.py::_claim_tier4_blob`.
- Schemas / caps: `app/schemas/eval_remote.py` — `MAX_SUBMIT_EVALS = 1024` (10),
  `FlawBlobLeaseResponse` / `FlawBlobSubmitRequest` (116 / 143).
- Fleet worker (fat app.* client): `scripts/remote_eval_worker.py` — rungs (~243–286),
  `_handle_full_ply_response` (~291), `_handle_flaw_blob_response` (~370),
  `_eval_flaw_blob_positions` (~128).
- Both drains started: `app/main.py` (78 entry-ply, 81 full-drain).

## Cross-refs

- [[SEED-071]] — why the remote path defers blobs at all (Phase 142 inline eval → ReadTimeouts
  → Option 2 deferral). This seed closes the ungated-window side effect that deferral created.
- [[SEED-073]] — fat-game `/flaw-blob-lease` over-cap sentinel; B reuses it, so B needs no
  chunking. Also confirms the single-game payload distribution (p99 489, p99.9 693 < 1024).
