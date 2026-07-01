# Phase 147: Persist only forcing-line-gated tactic tags (suppress ungated remote-submit tags A + upgraded-worker atomic eval+blob pipeline B) - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure `game_flaws.tactic_motif` is NEVER persisted with raw, ungated (pre-forcing-line-gate)
values that pollute backend statistics and tag-based game-selection filters. The gate (v1.30,
Phases 141–145) suppresses false-positive tactic motifs by requiring the refutation line to be
forcing, but on the remote-submit path the gate does not run at write time — the game is stamped
analyzed with raw ungated tags, only corrected later when tier-4 blob backfill draws the game.
Two complementary fixes close that window:

- **Part A (data-level, ship-first):** on the remote-submit path where blobs are deferred, write
  `tactic_motif = NULL` for cp-based flaws whose forcing-line gate can't yet run — keeping
  mate-adjacent (`pre_flaw_eval_cp IS NULL`) and D-06 `[]`-sentinel raw tags — so values self-heal
  when the tier-4 gated retag lands. A is also B's graceful-degradation net under version skew.
- **Part B (worker pipeline):** a versioned lease+submit endpoint PAIR and an upgraded fat-`app.*`
  fleet worker that submits full-ply evals + MultiPV-2 blobs together; the server runs its own
  authoritative `classify_game_flaws` with those blobs and writes flaws + forcing-line-gated tags
  + completion markers in ONE transaction, eliminating the ungated window at write time. Reuses the
  SEED-073 over-cap sentinel for fat games (no chunking).

**In scope:**
- Part A: thread a `blobs_pending`/`defer_ungated` signal from `_apply_submit` through
  `classify_game_flaws` → `_build_flaw_record` → `_classify_tactic_gated` (~5-15 lines + tests).
- Part A (expanded this session, D-04): a guarded data migration that ALSO suppresses raw cp-tags
  on the pre-Phase-142 old corpus (not just go-forward), with the same carve-outs.
- Part B: new versioned lease+submit endpoint pair, upgraded fleet worker, server-authoritative
  classify with worker-supplied blobs, single atomic write; SEED-073 over-cap sentinel for fat games.

**Out of scope (do not expand):** gate logic / `ONLY_MOVE_WIN_PROB_MARGIN` (consumed, not changed),
blob shape, any new tactic motif, `STOCKFISH_POOL_SIZE` change, retiring the local `_full_drain_tick`
(kept as-is per D-05), retiring tier-4 (it shrinks to backfill-only but is not removed this phase).
New DB schema changes beyond the A suppression data migration (B reuses
`allowed_pv_lines`/`missed_pv_lines` + existing completion markers).

</domain>

<decisions>
## Implementation Decisions

### Phase scope: A + B together
- **D-01: A and B stay in one phase (roadmap as-is).** Not selected for deep discussion → the
  bundled roadmap scope is accepted. A ships first as the graceful-degradation net; B builds the
  atomic pipeline on top. If B proves larger than expected during planning, splitting B into a
  follow-up is acceptable, but the default is one phase.

### Endpoint versioning (B)
- **D-02: New lease + new submit endpoint PAIR (seed lean accepted).** Not selected for deep
  discussion → seed lean stands. B changes the contract (submit carries blobs; completion gates on
  them) and a mixed fleet (old evals-only workers + upgraded evals+blobs workers) runs
  simultaneously across a deploy. A new pair (vs overloading existing endpoints) gives distinct
  schemas with their own `MAX_SUBMIT_EVALS` DoS caps, rollback safety (flip workers back with no
  server redeploy), and avoids server-side shape-sniffing. Old `/lease` + `/submit` stay deprecated,
  removed once the fleet is fully upgraded.

### Old-corpus tag suppression (A) — OVERRIDES seed lean
- **D-03: Suppress the old corpus too — NOT go-forward only.** The seed leaned "go-forward only
  (thread the flag from `_apply_submit`, leave existing rows for tier-4)." User OVERRODE this: also
  suppress raw cp-tags on pre-Phase-142 old-corpus rows now, for a clean "no ungated tags anywhere"
  invariant immediately rather than waiting on tier-4 to drain the whole corpus. This expands Part A
  beyond the ~15-line classify change to include a bulk data mutation.
- **D-04: Deliver the old-corpus suppression as an Alembic DATA migration** (runs automatically on
  deploy via `deploy/entrypoint.sh`), NOT a standalone `scripts/backfill_*.py` and NOT reactive-only.
  - **Carve-outs are MANDATORY and identical to the go-forward path:** only suppress rows where
    `allowed_pv_lines IS NULL` (truly pending, blob will arrive) AND `pre_flaw_eval_cp IS NOT NULL`
    (cp-based gate applies) AND `tactic_motif IS NOT NULL`. KEEP mate-adjacent
    (`pre_flaw_eval_cp IS NULL`) raw tags (gate has nothing to compare — final, not pending). KEEP
    D-06 `[]`-sentinel rows (`allowed_pv_lines = '[]'`, a real empty JSONB array distinct from SQL
    NULL — blob genuinely never assemblable, final). The `[]`-vs-NULL distinction is load-bearing
    (see the asyncpg JSONB-null memory: Python `None` → `null::jsonb`, `[]` → empty array; SQL
    `IS NULL` only matches truly-omitted rows).
  - **Idempotent + self-healing:** the guarded UPDATE can re-run harmlessly, and tier-4 D-07 fills
    the correctly-gated tag when each blob lands.
  - **PLANNER CONSTRAINT (flagged this session):** `game_flaws` is high-cardinality and migrations
    run on backend container startup. A single unbatched `UPDATE ... WHERE allowed_pv_lines IS NULL`
    across the whole table could hold locks and stall container startup. Batch the UPDATE
    (chunked by id range or `LIMIT`-loop) and confirm the predicate uses the existing partial index
    on `allowed_pv_lines` so the migration doesn't sequential-scan the table. Measure against a prod
    row-count estimate before shipping.

### Local full-drain fate (B)
- **D-05: Keep `_full_drain_tick` as-is (seed lean accepted).** The local full-drain
  (`eval_drain.py:2318`, started in `main.py:81`) already builds MultiPV-2 blobs inline and writes
  gated tags in the same tick — it was never a request path, so it never had the timeout problem
  (no SEED-071/FLAWCHESS-7Y exposure). Leave it untouched as local spare-capacity fallback. Smallest
  B footprint, no rollout risk. Retiring it to remove the local-vs-remote asymmetry is captured as a
  deferred idea, gated on observing the fleet gate reliably in prod.

### Claude's Discretion (planner/researcher decide within the above)
- **Q5 (classifier/schema version tag on the new submit) — deferred to planner.** Whether the new
  submit carries a classifier/schema version so the server can detect/reject/relabel version-skewed
  workers. User chose to leave it to the planner: the server-authoritative re-classify (server runs
  its own `classify_game_flaws` on its own `game_positions`) plus A's NULL graceful-degradation net
  already bound the blast radius, so a version tag is a robustness nicety, not load-bearing. Planner
  decides whether to include it.
- **Q4 (worker hint-classify data availability) — research verification.** The worker classifies
  locally purely as a HINT (to learn which plies are flaws → which continuation lines to blob); the
  server stays authoritative. Researcher must VERIFY the worker can build lightweight
  `GamePosition`-like objects and call `classify_game_flaws` with NO hidden DB dependency sneaking in
  via `derive_user_result` (seed asserts `derive_user_result` is pure/session-free — confirm).
- Exact `blobs_pending`/`defer_ungated` parameter name and threading; the migration's batching
  strategy and chunk size; the new endpoint schema shapes and their `MAX_SUBMIT_EVALS` caps; the
  new worker's lease→eval→blob→submit loop, poll cadence, and back-pressure; whether the worker's
  full-ply pass stays MultiPV-2 or drops to MultiPV-1 (Phase 146 Claude's-discretion carryover);
  dev-first end-to-end validation gate before any prod change.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec & decided approach (authoritative)
- `.planning/seeds/SEED-074-gated-tags-at-write-time.md` — the phase spec: Part A / Part B design,
  the "verified facts that make this cheap" (checked 2026-07-01 against code), the CRITICAL nuance
  on which no-blob cases to KEEP vs suppress, acceptance criteria for A and B, and the 5 open
  questions (Q1 resolved as D-03/D-04 override; Q2 as D-02; Q3 as D-05; Q4/Q5 as discretion above).
- `.planning/ROADMAP.md` §"Phase 147" — the phase goal.

### Prior-phase context (locked, do not re-decide)
- `.planning/phases/146-offload-live-submit-forcing-line-continuation-eval-to-the-re/146-CONTEXT.md`
  — SEED-071 Option 2 deferral (the origin of the ungated window this phase closes): remote submit
  runs zero server Stockfish, forces `blob_map = {}`, raw-classifies, stamps both completion markers,
  leaves blobs NULL; recency-ordered tier-4 lottery (D-01); the fleet worker already speaks the
  flaw-blob contract and is a fat `app.*` client (D-04). Phase 147 builds directly on this.
- `.planning/phases/145-corpus-backfill-rollout/145-CONTEXT.md` — tier-4 lottery, token-keyed
  flaw-blob lease/submit schema, per-game gated D-07 retag, D-06 sentinel `[]` for un-fillable flaws.
  B reuses this machinery; the new endpoint pair (D-02) sits alongside it.
- `.planning/phases/142-multipv-2-engine-pass-eval-drain-remote-worker/142-CONTEXT.md` — locked blob
  shape (`b/bm/s/sm/su`, white-perspective cp); the "leave blobs NULL" backward-compat path.
- `.planning/phases/143-offline-re-tagger/143-CONTEXT.md` — `_classify_tactic_gated`, engine-free
  retag from blobs.
- `.planning/notes/tactic-forcing-line-gate.md` — gate design source. **AGPL boundary:
  heuristics/constants/names only — copy NO lichess-puzzler source.**

### Code surfaces (verified in SEED-074, 2026-07-01)
- `app/services/flaws_service.py` — `_classify_tactic_gated` (525–573; the Part A site — today
  returns raw motif at line 573 when no blob), `_build_flaw_record` (~576), `classify_game_flaws`
  (875, PURE/deterministic — no session, no await, no DB; the server + worker both call it).
- `app/routers/eval_remote.py` — `_apply_submit` (blob_map = {} ~255–261, classify ~281–283,
  completion stamps ~288–309; the go-forward Part A call site), `flaw_blob_lease` (~725),
  `flaw_blob_submit` (~913), `_apply_flaw_blob_submit` (~789, D-07 gated retag). Part B adds the
  new lease+submit pair here.
- `app/schemas/eval_remote.py` — `MAX_SUBMIT_EVALS = 1024` (~10), `FlawBlobLeaseResponse` /
  `FlawBlobSubmitRequest` (~116 / ~143). Part B adds new versioned request/response schemas with
  their own caps.
- `app/services/eval_drain.py` — blob builders reused as B's reference:
  `_build_flaw_multipv2_blobs` (1161), `_walk_pv_boards` (1098), `_build_line_blobs` (1125),
  `_run_multipv2_pass` (1316), `_batch_update_flaw_pv_lines` (1282),
  `_build_flaw_blob_lease_positions` (1332); local inline path (D-05, keep unchanged):
  `_full_drain_tick` (2318), Step 3d blobs (2509–2514), write+classify (2538–2554).
- `app/services/eval_queue_service.py` — `_claim_tier4_blob` (the two-stage ES lottery; tier-4
  shrinks to backfill-only under B but is not removed).
- `app/services/engine.py` — `evaluate_nodes_multipv2` (608), `_NODES_BUDGET` (~99, 1M nodes),
  `PV_CAP_PLIES` (~104, 12).
- `scripts/remote_eval_worker.py` — the fat `app.*` fleet worker to upgrade (B): rungs (~243–286),
  `_handle_full_ply_response` (~291), `_handle_flaw_blob_response` (~370),
  `_eval_flaw_blob_positions` (~128). B adds a new-lease→eval+blob→new-submit path.
- `app/main.py` — both drains started (78 entry-ply, 81 full-drain; D-05 keeps full-drain).

### Ops
- `bin/prod_db_tunnel.sh` — required for any `--db prod` observability (forwards `localhost:15432`).
- `deploy/entrypoint.sh` — runs Alembic migrations on backend container startup (relevant to the
  D-04 data migration's batching/lock concern).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`classify_game_flaws` is pure and deterministic** — no session, no await, no DB (verified
  SEED-074). Both the server (authoritative) and the upgraded worker (hint only) can call the EXACT
  same code, so B has no thin-client rewrite or divergence-by-construction.
- **The fleet worker is already a fat `app.*` client** — imports `app.core.config`, `app.models.*`,
  `app.services.engine`; can `from app.services.flaws_service import classify_game_flaws` directly.
- **The entire Phase-145 tier-4 server side** — flaw-blob lease/submit, `_build_flaw_blob_lease_positions`,
  per-game gated retag — exists and is reused; B adds the new endpoint pair + upgraded worker path.
- **D-06 `[]` sentinel (SEED-073 over-cap)** — reused verbatim for B's fat games; no chunking.

### Established Patterns
- Predicate-driven, idempotent-by-construction tier-4 lottery (`job_id=None`, self-dedupes on
  `allowed_pv_lines IS NULL`). The A data migration reuses the same predicate shape.
- Server-authoritative semantics: the worker submits only raw engine outputs (evals + blobs keyed by
  ply); the server re-runs classify with those blobs and gates. Skewed-worker blobs for a non-flaw
  ply → dropped; a flaw the worker didn't blob → A writes NULL, tier-4 backfills. No corruption.
- No `asyncio.gather` on an open `AsyncSession`; read-session-closed-before-CPU (CLAUDE.md).
- `# ty: ignore[rule-name]` with rule name; explicit return types; `Literal[...]` over bare `str`.

### Integration Points
- Part A go-forward: thread `blobs_pending` from `_apply_submit` → `classify_game_flaws` →
  `_build_flaw_record` → `_classify_tactic_gated`; suppress only when `blobs_pending AND motif
  detected AND no blob AND pre_flaw_eval_cp IS NOT NULL`.
- Part A old-corpus: Alembic data migration, batched, guarded predicate matching the go-forward
  carve-outs, partial-index-aware.
- Part B: new lease+submit endpoints in `eval_remote.py` + new schemas in `eval_remote.py` schemas;
  new worker path in `remote_eval_worker.py`; server atomic write (flaws + gated tags +
  `allowed_pv_lines`/`missed_pv_lines` + both completion markers) in one transaction.
- No new EnginePool, no `STOCKFISH_POOL_SIZE` change. Only DB change is the A suppression migration.

</code_context>

<specifics>
## Specific Ideas

- The core correctness invariant this phase enforces: **`tactic_motif` is either correctly
  forcing-line-gated or NULL — never raw/ungated — the instant a game is stamped analyzed.** A
  achieves this by suppression + self-heal; B achieves it atomically at write time with no window.
- User explicitly wants the invariant to hold for ALREADY-IMPORTED games too, not just go-forward
  (D-03 override) — hence the bulk Alembic migration rather than the seed's narrower go-forward-only
  lean. The trade-off (changes what users see for old games until tier-4 catches up) was accepted
  deliberately in favor of the clean invariant.
- Keep the trust boundary: worker classification is a HINT only; the server re-classifies
  authoritatively. A lagging-deploy worker can never silently write wrong flaws/tags.

</specifics>

<deferred>
## Deferred Ideas

- **Retire `_full_drain_tick` (local full-drain).** Removing it would give a single write path and
  zero local-vs-remote asymmetry, but it's out of B's core scope and removes a fallback. Kept this
  phase (D-05); revisit as its own cleanup once the fleet gate is observed reliable in prod.
- **Retire tier-4 + its endpoints entirely.** Under B (atomic all-or-nothing for new games) tier-4
  is needed ONLY to drain the pre-B old corpus; once that's drained, `/flaw-blob-lease` +
  `/flaw-blob-submit` and the old `/lease` + `/submit` pair can retire. Not this phase — end-state
  endpoint cleanup, gated on the old corpus fully draining.
- **Worker full-ply pass MultiPV-2 → MultiPV-1.** Phase 146 carryover optimization; research-confirm
  no remaining second-best consumer before reducing. May land opportunistically in B or its own
  follow-up.
- None of the above is scope creep — discussion stayed within the "gate tags at/never-after write
  time" boundary.

</deferred>

---

*Phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated*
*Context gathered: 2026-07-01*
