# Phase 174: Backend Maia Inference + Best-Move Storage (spike-gated) - Research

**Researched:** 2026-07-16
**Domain:** Python ONNX inference port + backend eval-pipeline plumbing (FastAPI/SQLAlchemy/Stockfish)
**Confidence:** MEDIUM — the encoding port itself is HIGH confidence (a prior verified repro exists in
this exact codebase's history); the eval-apply insertion point is MEDIUM/LOW because it surfaces a
real gap in SEED-108's "zero extra Stockfish cost" premise (see Pitfall 1 below) that CONTEXT.md's
locked decisions do not address.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Four SEED-108 "Open Questions" were resolved in this discussion. Everything in the "Carried
forward" section below is already locked by SEED-108's `/gsd-explore` session and is NOT
re-litigated.

**Spike-gate — parity tolerance & fail path (SC1, GEMS-04)**
- **D-01:** Parity is defined by **tier-stability + a loose epsilon**, not a tight raw-probability
  match. The gate passes iff every fixture ply lands in the **same gem / great / neither tier** on
  both the Python and client sides, with raw `maia_prob` within a loose band (~±0.02 — final number
  set by the researcher from measured drift). Rationale: the tiers are coarse buckets (Gem ≤ 0.20,
  Great (0.20, 0.50]), so tier agreement is what actually protects stored classification; benign
  CPU-vs-WebGPU float drift that never flips a tier is acceptable.
- **D-02:** **Fail path** if the port cannot meet the gate: the phase **pauses for re-scope**.
  Falling back to Maia-on-workers (a worker-protocol change) stays a *documented escape hatch*,
  explicitly NOT auto-taken. Do not ship mismatched stored data.

**ONNX InferenceSession lifecycle & prod RAM (GEMS-03)**
- **D-03:** The Maia `InferenceSession` is **eager-loaded at FastAPI lifespan startup**, mirroring
  the established Stockfish engine lifecycle (`start_engine()`/`stop_engine()` at
  `app/main.py:96,140`). Add a `start_maia()`/`stop_maia()` pair called from the same lifespan; one
  process-wide session.
- **D-03a (guardrail):** The eager load must be a **no-op when onnxruntime is not installed** —
  deps are group-isolated (GEMS-06/D-08) and a backend image without the inference group must not
  crash at boot. (Remote workers run `scripts/remote_eval_worker.py`, not the FastAPI app, so the
  lifespan never fires there — but keep the guard defensive.)
- **D-03b (guardrail):** The plan MUST measure steady-state backend RSS against the documented OOM
  history before enabling in prod. One ~44 MB session is small next to the 6-subprocess Stockfish
  pool, but the 4 GB backend container is OOM-sensitive.

**ELO clamping for out-of-band movers (GEMS-05)**
- **D-04:** Clamp the pinned lichess-blitz-equivalent rating to **[600, 2600]**, mirroring the
  frontend `MAIA_ELO_LADDER` bounds / `clampToLadderBounds` exactly, so backend-stored `maia_prob`
  and the live board agree for the same position. **Correction to framing:** the "validated
  1100–2000 band" cited in SEED-108/CLAUDE.md is Maia-3's *validated draw-rate sweep sub-band*, not
  the clamp bounds — the frontend ladder is the full 600–2600 (21 rungs, step 100; 600–1000 and
  2100–2600 are documented extrapolation the model still accepts). Backend clamps to the same
  600–2600 the board uses. A row is still stored for clamped movers (maia_prob is populated at the
  clamped rung).

**Storage column types (GEMS-01, D-4)**
- **D-05:** Persist **raw Stockfish centipawns as ints** (`best_cp`, `second_cp`, plus mate flags),
  exactly as `second_best_map` already holds them (`(cp, mate, uci)`) — NOT pre-converted
  expected-score floats. The cp→expected-score conversion (via the existing sigmoid) + mate
  handling stays **query-time in one place**, keeping the C1/C2 margins fully retunable with zero
  re-analysis and matching `game_positions.eval_cp`. `maia_prob` remains a float. This is the column
  set from SEED-108 D-4's own example (`… maia_prob, best_cp, second_cp`); GEMS-01's literal "as
  floats" wording means "continuous values, never a boolean flag", satisfied by storing `maia_prob`
  as a float.
- **D-05a:** The `best_es − second_es ≥ INACCURACY_DROP (0.05)` candidate gate still computes
  expected-score **at write time** (to decide whether to store the row + run Maia) — storing cp does
  not remove the write-time ES computation; it only keeps the *persisted* value retunable.

### Claude's Discretion

- Exact column names/types of the new table beyond the cp/maia_prob decision (e.g. mate
  representation, whether to denormalize `fen`/`best_move`), the uv group name, the parity-fixture
  corpus source, and the precise eval-apply insertion point — the researcher/planner decides these
  within the locked decisions above.

### Deferred Ideas (OUT OF SCOPE)

- **Great-ceiling (0.50) + gem-ceiling (0.20) calibration against real per-game frequency** —
  belongs to the milestone's Future Requirements / a post-pipeline retune (GEMS-07 makes it a
  constants-only change; do not calibrate in 174).
- **Board/EvalPoint consumption, `useGemSweep.ts` retirement, Library gem/great filter** → Phase 175.
- **Corpus backfill via tier-4 lottery** → Phase 176.
- `172-deferred-review-findings.md` — explicitly `resolves_phase: 175`; belongs to Phase 175.
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — unrelated DB idea, out of scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GEMS-01 | New `game_best_moves` sibling table, floats never a boolean, unique `(game_id, ply)` | See "New Table + Migration" below; mirrors `app/models/game_flaw.py` and `app/models/bot_game_settings.py`'s `CheckConstraint` pattern |
| GEMS-02 | Candidate row only when out-of-book AND played == SF best AND `best_es − second_es ≥ INACCURACY_DROP (0.05)` | `find_opening_ply_count` (`app/services/opening_lookup.py:123`) gives the out-of-book test; `INACCURACY_DROP` already lives in `app/services/flaws_service.py:46`; see Pitfall 1 for the second-best-availability gap that gates this |
| GEMS-03 | Backend Maia-3 scoring during eval-apply, one-time session load, workers stay pure Stockfish | `apply_full_eval` (`app/services/eval_apply.py:1687`) is the ONE shared write-session body both `_full_drain_tick` (local) and `_apply_atomic_submit` (remote-worker HTTP submit) call — this is the single insertion point that guarantees "every newly analyzed game" without touching worker code |
| GEMS-04 | Python 12-plane encoding port passes fixture-based parity vs client outputs | A verified prior repro exists: `.planning/notes/2026-07-10-flawchess-engine-self-execution-analysis.md` (Python + onnxruntime==1.20.1, root distribution matched UI to 0.01%) — HIGH confidence starting point |
| GEMS-05 | Maia inference uses pinned lichess-blitz-equivalent rating, clamped [600,2600] | `normalize_to_lichess_blitz()` (`app/services/chesscom_to_lichess.py:318`) + `is_correspondence_time_control()` is the exact server-side function already used for this same rating in `library_service.py:567-589`; `clampToLadderBounds` logic to port from `useMaiaEloDefault.ts:101` |
| GEMS-06 | onnxruntime + numpy isolated behind a uv group/extra so worker image stays lean | Both `Dockerfile` and `Dockerfile.worker` currently run identical `uv sync --locked --no-dev` with no `--extra`/`--group` flag — a new opt-in `[dependency-groups]` entry is naturally excluded unless the backend Dockerfile adds `--group <name>` |
| GEMS-07 | Query-time Gem/Great classification from stored floats + `MISTAKE_DROP` | `eval_cp_to_expected_score()` (`app/services/eval_utils.py`, `LICHESS_K=0.00368208`) is byte-identical to the frontend's `evalToExpectedScore` sigmoid; `MISTAKE_DROP`/`GEM_MAIA_MAX_PROB` already exist server-side (`flaws_service.py:47`) / client-side (`gemMove.ts:35`) |

</phase_requirements>

## Summary

The parity-spike core (GEMS-04) is lower-risk than SEED-108 assumed: this exact codebase already
has a **verified** headless Python reproduction of Maia-3 inference (`onnxruntime==1.20.1`,
encoding mirrored from `maia-worker.js`/`maiaEncoding.ts`) that matched the live UI's root
distribution to 0.01% (`.planning/notes/2026-07-10-flawchess-engine-self-execution-analysis.md`).
That note also records a **hard version constraint**: `onnxruntime>=1.22` segfaults on the vendored
model. Pin `onnxruntime==1.20.1` (not latest) unless a spike task re-validates a newer version first.

The storage, lifecycle, and ELO-clamping decisions are all well-precedented in this codebase:
`app/services/eval_utils.py` already has the byte-identical cp→ES sigmoid the frontend uses,
`app/services/chesscom_to_lichess.py:normalize_to_lichess_blitz()` already computes the exact pinned
rating GEMS-05 needs (used today by `library_service.py` for the same purpose), and
`app/models/bot_game_settings.py` is a clean recent example of the `CheckConstraint`
sibling-table pattern to mirror.

The one genuine, previously-undocumented risk this research surfaces (**Pitfall 1**, below): SEED-108's
"zero extra Stockfish cost" claim (`second_best_map` is "already computed at nearly every ply") is
only true for games evaluated by the **local** `_full_drain_tick` lane. Games claimed by a
**remote worker** (the majority of tier-1 traffic, since local drain and remote workers race for the
same `claim_eval_job` queue via `SKIP LOCKED`) only carry second-best data for the worker's own
locally-hinted *flaw* plies (Phase 146 D-03 intentionally dropped per-ply second-best from the
worker's full-ply MultiPV-1 pass) — never for non-flaw "played == best" plies, which is exactly the
population GEMS-02's candidate gate needs. `apply_full_eval` is still the right insertion point
(it's the ONE function both lanes funnel through, in-process on the backend), but the candidate-row
builder must be prepared to run a **targeted, backend-owned** `evaluate_nodes_multipv2` call for any
"out-of-book, played == best" ply whose second-best is missing — a small, bounded extra Stockfish
cost on the backend's own pool (not a worker-protocol change, so D-3/GEMS-03/GEMS-06 stay satisfied),
not the literal zero-cost SEED-108 described.

**Primary recommendation:** Build the parity spike FIRST as a standalone script (pin
`onnxruntime==1.20.1`, reuse the verified encoding from the 2026-07-10 note), gate all further work
on it per D-02. Slot Maia inference + candidate-row assembly into a new helper called from inside
`apply_full_eval` (or immediately before it, mirroring `_build_flaw_multipv2_blobs`'s
session-closed-then-gather pattern), sourcing second-best from `second_best_map` where available and
falling back to a bounded, backend-owned `evaluate_nodes_multipv2` call where it is not.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Board→tensor encoding port | API/Backend | — | Pure Python transform, no I/O; mirrors `maiaEncoding.ts` |
| Maia-3 ONNX inference | API/Backend | — | D-3 locked: backend process only, NOT remote workers |
| Stockfish best/second-best eval | API/Backend | — | Already owned by `app/services/engine.py`'s `EnginePool`; remote workers are a second Stockfish-only executor of the SAME backend-owned protocol, not a distinct tier |
| Candidate-row gate + storage | API/Backend | Database/Storage | Gate logic (pure) runs in the backend process; the row itself persists to Postgres via a new sibling table |
| Query-time Gem/Great classification | Database/Storage (query) | API/Backend (read endpoint) | GEMS-07 is explicitly query-time — SQL/ORM read path, not a stored column |
| Parity fixture corpus + tolerance | API/Backend (spike script) | — | Standalone verification script, not a runtime service |
| uv dependency isolation | Build/CDN (Docker image composition) | — | Docker image contents, not runtime behavior |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `onnxruntime` | **`==1.20.1`** `[VERIFIED: PyPI registry — cp313 manylinux wheel exists]` | Runs `maia3_simplified.onnx` server-side (CPUExecutionProvider) | This exact pin is the ONLY version verified against the vendored model in this codebase — `.planning/notes/2026-07-10-flawchess-engine-self-execution-analysis.md` records `onnxruntime>=1.22` **segfaults** on this specific model file. `[VERIFIED: project note, cross-checked against PyPI for wheel availability]` |
| `numpy` | `>=1.21.6` (onnxruntime 1.20.1's own floor) `[VERIFIED: PyPI registry — onnxruntime 1.20.1 requires_dist]` | Tensor construction (`tokens[64,12]`, `elo_self`/`elo_oppo` float32 arrays) fed to the ONNX session | Required transitive dep of onnxruntime; also the natural array type for the encoding port |

**Do NOT** install latest `onnxruntime` (1.27.0 as of this research) without first re-running the
spike against it — the segfault note is specific to the vendored `maia3_simplified.onnx` file, and
onnxruntime's op-kernel set changes across major-ish releases. If a later plan step wants to
upgrade past 1.20.1, that upgrade itself needs the same fixture-parity gate re-run (D-01/D-02),
not just a green `import onnxruntime`.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `chess` (python-chess) | Already a core dependency (`>=1.10.0`) | Legal-move enumeration + SAN↔UCI for the policy-vocab masking/softmax step (mirrors `maskAndSoftmax` in `maiaEncoding.ts`) | Every inference call — no new dependency needed here |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `onnxruntime` (CPU) | `onnxruntime-gpu` | No GPU in the prod container (Hetzner CPX42, no GPU); CPU-only is correct and matches the client's WASM fallback path numerically more closely than WebGPU would |
| Eager-load-at-lifespan (D-03, locked) | Lazy-load on first candidate ply | Rejected by locked decision D-03 — mirrors Stockfish's own eager pattern; lazy-load would add unpredictable per-game latency spikes to eval-apply |

**Installation:**
```bash
# NOT plain `uv add` — must land in the new isolated group (see GEMS-06 section below), e.g.:
uv add --group maia-inference "onnxruntime==1.20.1" numpy
```

**Version verification performed:**
- `onnxruntime==1.20.1` — confirmed present on PyPI with `cp313-manylinux_2_27_x86_64` wheels
  (2024-11-21 upload). `[VERIFIED: PyPI registry query]`
- `numpy` latest is `2.5.1` on PyPI as of this research; onnxruntime 1.20.1 only requires
  `numpy>=1.21.6`, so the current lockfile-resolved numpy (whatever `uv add` picks) is expected to
  satisfy it without a separate pin. `[VERIFIED: PyPI registry query]`

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `onnxruntime` | PyPI | 1.20.1 released 2024-11-21; package itself is a long-established Microsoft project | Very high (tens of millions/week across all versions) | github.com/microsoft/onnxruntime | OK | Approved — already vendored client-side as `onnxruntime-web` in this exact codebase (same publisher) |
| `numpy` | PyPI | Foundational scientific-Python package, 15+ years | Extremely high | github.com/numpy/numpy | OK | Approved |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

Both packages are well-known, already-precedented (the project already depends on
`onnxruntime-web`, the sibling JS package, from the same publisher/org). No `checkpoint:human-verify`
gate is needed for these two specifically, though the version PIN (1.20.1, not latest) should be
called out explicitly in the plan so a future dependency-bump PR doesn't silently regress past the
segfault boundary.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │   Local full-ply drain (in-process)      │
                         │   `_full_drain_tick` (eval_drain.py)     │
                         │   claim_eval_job() ──► evaluate_nodes_   │
                         │   multipv2() for EVERY ply (full SF      │
                         │   second-best coverage)                  │
                         └───────────────────┬───────────────────────┘
                                              │
   ┌──────────────────────────────────────┐  │   both call the SAME
   │ Remote worker fleet (own process)     │  │   shared write-session
   │ scripts/remote_eval_worker.py         │  │   function ──────────┐
   │ claim_eval_job() via /lease HTTP ──►  │  │                      │
   │ _eval_positions() = MultiPV-1 ONLY    │  │                      ▼
   │ (no per-ply second-best, Phase 146    │  │        ┌─────────────────────────────┐
   │ D-03) + local flaw-HINT MultiPV-2     │──┼───────►│  apply_full_eval()           │
   │ for hinted plies only, via            │  │        │  (eval_apply.py:1687)        │
   │ /atomic-submit HTTP                   │  │        │  ONE shared write-session    │
   └────────────────────────────────────────┘ │        │  body — runs IN THE BACKEND  │
                                               │        │  PROCESS regardless of which │
                                               │        │  lane produced the SF evals  │
                                               │        └──────────────┬────────────────┘
                                               │                       │
                                               │         ┌─────────────▼─────────────────┐
                                               │         │ NEW: candidate-row builder      │
                                               │         │ (called from/near               │
                                               │         │ apply_full_eval, mirrors         │
                                               │         │ _build_flaw_multipv2_blobs'      │
                                               │         │ session-closed-then-gather       │
                                               │         │ pattern)                         │
                                               │         │                                  │
                                               │         │ 1. out-of-book test               │
                                               │         │    (find_opening_ply_count)       │
                                               │         │ 2. played == best_move test       │
                                               │         │ 3. second-best: from              │
                                               │         │    second_best_map OR a           │
                                               │         │    TARGETED extra backend         │
                                               │         │    evaluate_nodes_multipv2 call   │
                                               │         │    (Pitfall 1)                    │
                                               │         │ 4. ES gate: best_es - second_es   │
                                               │         │    >= INACCURACY_DROP (0.05)      │
                                               │         │ 5. mover's pinned lichess-blitz    │
                                               │         │    ELO (normalize_to_lichess_      │
                                               │         │    blitz), clamped [600,2600]      │
                                               │         │ 6. Maia-3 inference (backend-owned │
                                               │         │    ONNX session, eager-loaded at   │
                                               │         │    lifespan startup — start_maia())│
                                               │         └──────────────┬─────────────────────┘
                                               │                        │
                                               │                        ▼
                                               │            INSERT game_best_moves row
                                               │            (game_id, ply, maia_prob,
                                               │             best_cp, second_cp, ...)
                                               │            ── same write_session, same
                                               │               commit as the rest of
                                               │               apply_full_eval ──
                                               ▼
                              (worker protocol UNTOUCHED — D-3)

                         ─── Query time (GEMS-07, out of this phase's UI scope) ───
             SELECT ... FROM game_best_moves
             WHERE maia_prob <= 0.20                       -- Gem
                OR maia_prob BETWEEN 0.20 AND 0.50          -- Great
             -- best_cp/second_cp → eval_cp_to_expected_score() at read time
```

### Recommended Project Structure

```
app/
├── services/
│   ├── maia_encoding.py       # NEW — Python port of maiaEncoding.ts (pure, no I/O)
│   ├── maia_engine.py         # NEW — mirrors engine.py's start/stop lifecycle for the ONNX session
│   ├── eval_apply.py          # MODIFIED — new candidate-row builder called from/near apply_full_eval
│   └── eval_drain.py          # UNCHANGED protocol-wise; may gain a helper for the targeted extra SF call
├── models/
│   └── game_best_move.py      # NEW — sibling table, mirrors game_flaw.py
scripts/
└── maia_parity_spike.py       # NEW — standalone fixture-based parity gate (GEMS-04, run BEFORE
                                #       any other task per D-02)
alembic/versions/
└── <timestamp>_add_game_best_moves_table.py   # NEW migration
```

### Pattern 1: Session-closed-then-gather (mirror `_build_flaw_multipv2_blobs`)

**What:** Open a short read session, load what's needed, close it, do all CPU/engine work (including
any Maia inference and any targeted extra Stockfish `evaluate_nodes_multipv2` calls) with **no
session open**, then open the write session late.

**When to use:** Any new step inserted into the `_full_drain_tick` / `apply_full_eval` pipeline —
this is a hard project rule (CLAUDE.md: never `asyncio.gather` on an open `AsyncSession`), and this
exact pattern is already used for the structurally analogous `_build_flaw_multipv2_blobs`
(`app/services/eval_apply.py:1208-1316`).

**Example:**
```python
# Source: app/services/eval_apply.py:1208-1316 (pattern to mirror), condensed
async with async_session_maker() as session:
    flaw_result = await _classify_with_overlay(game_id, session, overlay=True, pos_eval=pos_eval)
# session closed — now safe to gather
continuation_results = await asyncio.gather(
    *(engine_service.evaluate_nodes_multipv2(b) for b in gather_boards)
)
```

### Pattern 2: Stockfish lifecycle mirror for `start_maia`/`stop_maia` (D-03)

**What:** A process-wide, eager-loaded singleton, mirroring `start_engine()`/`stop_engine()`.

**Example:**
```python
# Source: app/services/engine.py:223-241 (pattern to mirror)
_pool: EnginePool | None = None

async def start_engine() -> None:
    global _pool
    if _pool is not None:
        return
    pool = EnginePool(size=_read_pool_size())
    await pool.start()
    _pool = pool

async def stop_engine() -> None:
    global _pool
    if _pool is None:
        return
    try:
        await _pool.stop()
    finally:
        _pool = None
```

For Maia, the equivalent must be a **no-op when `onnxruntime` isn't importable** (D-03a):

```python
# NEW app/services/maia_engine.py — sketch, not final
_session: "onnxruntime.InferenceSession | None" = None  # type: ignore[name-defined]

async def start_maia() -> None:
    global _session
    try:
        import onnxruntime  # deferred import — group-isolated, may not be installed (D-03a)
    except ImportError:
        logger.info("maia_engine: onnxruntime not installed — Maia inference disabled")
        return
    if _session is not None:
        return
    _session = onnxruntime.InferenceSession(
        _MODEL_PATH, providers=["CPUExecutionProvider"]
    )

async def stop_maia() -> None:
    global _session
    _session = None
```

Wire into `app/main.py`'s lifespan alongside `start_engine()`/`stop_engine()` (lines 96, 140):
```python
# Source: app/main.py:93-96, 139-140 — insertion points
await start_engine()
await start_maia()   # NEW
...
finally:
    await stop_engine()
    await stop_maia()  # NEW (order: stop after engine, or independently — no cross-dependency)
```

### Pattern 3: Reuse the existing cp→ES sigmoid verbatim (GEMS-07)

**What:** `app/services/eval_utils.py`'s `eval_cp_to_expected_score()` is byte-identical (same
`LICHESS_K = 0.00368208`) to the frontend's `evalToExpectedScore`. Do NOT re-derive this — import
and reuse it, exactly as `flaws_service.py` already does.

```python
# Source: app/services/eval_utils.py:34-63
LICHESS_K: float = 0.00368208

def eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white", "black"]) -> float:
    sign = 1 if user_color == "white" else -1
    return 1.0 / (1.0 + math.exp(-LICHESS_K * sign * eval_cp))
```
Mate handling: mirror `flaws_service.py`'s `MATE_CP_EQUIVALENT = 1000` "Option B" convention
(map mate to ±1000cp BEFORE the sigmoid) — do NOT use `eval_mate_to_expected_score` (hard 0/1),
which is for endgame span averaging, not per-ply drop math.

### Pattern 4: Reuse the existing lichess-blitz-equivalent rating derivation (GEMS-05)

```python
# Source: app/services/library_service.py:553-576, calling
# app/services/chesscom_to_lichess.py:318 normalize_to_lichess_blitz + normalization.py's
# is_correspondence_time_control
is_correspondence = is_correspondence_time_control(game.time_control_str)
is_flawchess = game.platform == "flawchess"
white_rating_lichess_blitz = (
    game.white_rating
    if is_flawchess
    else (
        normalize_to_lichess_blitz(
            game.white_rating, cast(Platform, game.platform),
            cast(TimeControlBucket, game.time_control_bucket),
            is_correspondence=is_correspondence,
        )
        if game.white_rating is not None and game.time_control_bucket is not None
        else None
    )
)
```
Then apply D-04's clamp (port of `useMaiaEloDefault.ts:101` `clampToLadderBounds` +
`maiaEncoding.ts:40-46` ladder bounds):
```python
MAIA_ELO_LADDER_MIN = 600
MAIA_ELO_LADDER_MAX = 2600

def clamp_to_ladder_bounds(rating: float) -> float:
    return min(MAIA_ELO_LADDER_MAX, max(MAIA_ELO_LADDER_MIN, rating))
```
Fallback chain (`*_lichess_blitz ?? raw`) matches `deriveRawDefault` exactly (`useMaiaEloDefault.ts:118-133`)
for game-mode: `white_rating_lichess_blitz ?? white_rating` (and black analog), keyed by mover color
(ply parity: `"white" if ply % 2 == 0 else "black"`, per `flaws_service.py:379,464,550-551`).

### Anti-Patterns to Avoid

- **Re-deriving the cp→ES sigmoid or the ELO ladder/clamp from scratch:** both already exist
  server-side or have a direct, literal client-side source to port — re-deriving risks silent drift
  from the live board (exactly the failure D-04 exists to prevent).
- **Running Maia inference on the remote worker:** explicitly rejected by D-3 / Out of Scope table
  in REQUIREMENTS.md. Do not add any Maia code to `scripts/remote_eval_worker.py` or
  `Dockerfile.worker`.
- **Treating `second_best_map` as universally populated:** true only for the local drain lane — see
  Pitfall 1.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| cp → expected-score conversion | A new sigmoid function | `app/services/eval_utils.py:eval_cp_to_expected_score` | Already the single source of truth other flaw/gem code paths use; a second implementation would drift |
| Mate-to-ES handling | A new mate-cp-equivalent constant | `flaws_service.py`'s `MATE_CP_EQUIVALENT = 1000` "Option B" pattern | Matches the frontend's `evalToExpectedScore` mate-before-sigmoid convention exactly |
| Rating normalization (chess.com→lichess-blitz) | A new rating-conversion table/function | `app/services/chesscom_to_lichess.py:normalize_to_lichess_blitz` | Complex ChessGoals-table-based conversion already implemented, tested, and used for this exact purpose (Phase 164/167) |
| Out-of-book ply detection | A new opening-book walker | `app/services/opening_lookup.py:find_opening_ply_count` | Already computed on-read from the same trie the client's book markers use (Phase 172); walks `GamePosition.move_san` (SAN, same dialect) |
| Engine process lifecycle (start/stop, no-op-if-absent guard) | A bespoke Maia session manager | Mirror `app/services/engine.py`'s `start_engine`/`stop_engine` singleton pattern (D-03, locked) | Established, battle-tested pattern already in this codebase for the exact same "long-lived native process behind a FastAPI lifespan" problem |
| ONNX board encoding | A fresh from-scratch reverse-engineering of the tensor contract | Port `frontend/src/lib/maiaEncoding.ts` + the VERIFIED prior Python repro in `.planning/notes/2026-07-10-...md` | The contract (12-plane order, mirror-on-black, vocab 4352, raw ELO floats) is already confirmed twice — once via `151-MAIA-CONTRACT.md`'s real-ONNX inspection, once via the 2026-07-10 headless Python repro matching the UI to 0.01% |

**Key insight:** almost every piece of math/lookup this phase needs (sigmoid, ELO normalization,
opening-book depth, PV/second-best plumbing, engine process lifecycle) already exists somewhere in
this codebase in verified, tested form. The actual net-new code is narrow: the encoding port itself,
the ONNX session wrapper, the new table, and the candidate-row assembly glue.

## Runtime State Inventory

Not applicable — this phase is a greenfield addition (new table, new service module, new
dependency group), not a rename/refactor/migration of existing state. Skipped per the trigger
condition in the research protocol.

## Common Pitfalls

### Pitfall 1: `second_best_map` is NOT universally populated — SEED-108's "zero extra cost" claim only holds for the local drain lane

**What goes wrong:** GEMS-02's candidate gate needs `best_cp`/`second_cp` for EVERY out-of-book ply
where `played == best_move`, not just flaw plies. SEED-108's Key Cost Insight claims this is already
computed "at nearly every ply" for free, citing `eval_drain.py:790`
(`evaluate_nodes_multipv2` on every `engine_target`). That citation is correct **only for the local
`_full_drain_tick` lane**. The remote-worker lane (`scripts/remote_eval_worker.py`) was intentionally
changed in **Phase 146 D-03** to full-ply **MultiPV-1 only** (`_eval_positions`, no per-ply
second-best) — the code comment says so explicitly: *"reduced to MultiPV-1 ... now that per-ply
second-best was dropped from SubmitEval."* The worker still computes MultiPV-2, but ONLY for plies
its own **local flaw hint** (`_hint_flaw_plies`, itself explicitly a HINT the server does not trust,
T-147-03) selects — i.e. plies the worker's un-authoritative local guess thinks are mistakes/blunders,
never for "played == best" plies (a best move is definitionally never a flaw, so the worker's hint
never selects it for a MultiPV-2 pass).

**Why it happens:** `_full_drain_tick` (in-process on the backend) and the remote worker fleet
(`scripts/remote_eval_worker.py`, off-box) both call the SAME `claim_eval_job()` priority queue with
`SELECT ... FOR UPDATE SKIP LOCKED` semantics (`app/services/eval_queue_service.py`) — they race for
the same tier-1/2/3 jobs. Whichever lane wins the race for a given game determines whether that
game's non-flaw plies get real second-best data. Since the project runs a multi-worker remote fleet
specifically to offload the backend's own Stockfish pool, a substantial fraction (plausibly the
majority) of newly-imported games' full-ply pass will be claimed by remote workers and arrive at
`apply_full_eval` (via `_apply_atomic_submit` in `eval_remote.py`) with `AtomicSubmitEval.second_cp`
non-null ONLY for the worker's flaw-hinted plies.

**How to avoid:** The candidate-row builder (wherever it's inserted relative to `apply_full_eval`)
must NOT assume `second_best_map`/`AtomicSubmitEval` second-best coverage is complete. For each
out-of-book, played==best-move ply lacking a second-best value, issue a **targeted, backend-owned**
`engine_service.evaluate_nodes_multipv2(board)` call (same pool `start_engine()` already manages,
SCHED_IDLE so it won't starve API latency) — bounded to just that subset of plies (typically a
minority of a game's total plies: only plies where the player found the engine's own top choice).
This is NOT a worker-protocol change (D-3/GEMS-06 stay satisfied: the worker is untouched, the extra
Stockfish `go` happens on the backend's own already-running pool) but IS extra Stockfish cost beyond
what SEED-108 described as free — the plan must budget for it (rough sizing: 10-20 out-of-book
best-move plies/game per SEED-108's own inference-volume estimate, each a normal ~1M-node
`evaluate_nodes_multipv2` call, same cost class as a flaw eval).

**Warning signs:** If the plan proceeds as if `second_best_map`/the submitted evals fully cover every
ply, prod will show a systematic under-count of candidate rows for remote-worker-evaluated games
specifically (a silent, hard-to-notice data-quality gap, not a crash) — worth an explicit
verification query post-launch (candidate-row rate should not differ materially between games whose
`full_eval_attempts`/heartbeat metadata indicates local vs remote-worker origin, if such a signal is
retained; if not, this is worth adding as a lightweight diagnostic).

### Pitfall 2: onnxruntime version regression — pin 1.20.1, do not take "latest"

**What goes wrong:** A routine dependency bump (`uv lock --upgrade`) silently jumps `onnxruntime`
past `1.22`, which — per a DIRECT prior repro in this project
(`.planning/notes/2026-07-10-flawchess-engine-self-execution-analysis.md`) — **segfaults** on the
vendored `maia3_simplified.onnx` model specifically.

**Why it happens:** Nothing in a routine `uv lock --upgrade` run would surface this; a segfault in a
background eval-apply pass (not a request-serving path) may not even be obviously attributed to the
dependency bump in prod logs.

**How to avoid:** Pin `onnxruntime==1.20.1` exactly (not `>=1.20.1`) in the new dependency group.
Document the segfault history inline in `pyproject.toml`'s comment or the model-loading code. Any
future bump must re-run the fixture parity spike (GEMS-04's gate) before merging, not just confirm
`import onnxruntime` succeeds.

### Pitfall 3: `find_opening_ply_count` needs a SAN move list — confirm it's cheaply reconstructable at eval-apply time

**What goes wrong:** The out-of-book test (`find_opening_ply_count(moves: list[str])`,
`app/services/opening_lookup.py:123`) takes tokenized SAN moves (the same dialect `openings.tsv`
uses). At read time (`library_service.py`), this list comes from the already-materialized
`GameFlawCard.moves` payload. At eval-apply time, no such list is pre-built — it must be derived from
either the game's PGN (already loaded as `pgn_text` in both `_full_drain_tick` and
`_apply_atomic_submit`) or from `GamePosition.move_san` per ply (already a persisted column,
`app/models/game_position.py:141`).

**Why it happens:** The two call sites (query-time vs eval-apply-time) have different natural data
shapes available — reusing the read-time helper naively could add an extra DB round-trip or PGN
re-parse.

**How to avoid:** `_collect_full_ply_targets` (shared by both eval-apply lanes) already walks the PGN
via `chess.pgn` to build `_FullPlyEvalTarget` objects — the SAN move list is derivable from that same
walk (or from the `targets[i].board.move_stack` / `GamePosition.move_san` values already in memory)
with no extra I/O. Confirm at plan time which of these two sources is cheapest given the existing
target-collection code, rather than adding a fresh query.

### Pitfall 4: mover color / played-move UCI derivation — reuse the established ply-parity convention

**What goes wrong:** A fresh, subtly-different mover-color or played-move derivation could disagree
with the rest of the flaw/gem pipeline at the boundary (e.g. an off-by-one on which ply is "white to
move").

**Why it happens:** `GamePosition.ply` is 0-indexed with ply 0 = the initial position (white to
move); the played move FROM that ply's position is stored in `GamePosition.move_san` at that same
ply. The established convention (`flaws_service.py:379,464,550-551`) is
`"white" if ply % 2 == 0 else "black"`.

**How to avoid:** Reuse this exact parity rule; do not re-derive from `chess.Board.turn` on a
freshly-constructed board unless it's the SAME board object already walked via
`_collect_full_ply_targets` (which is authoritative). The played move's UCI (needed to compare against
`best_move`, itself already UCI) is `target.board.parse_san(move_san).uci()` on the pre-move board, or
directly available if `_FullPlyEvalTarget`/PGN walk already tracks the pushed move.

### Pitfall 5: prod RSS budget — verify empirically, don't just trust the "~44 MB" estimate

**What goes wrong:** SEED-108/D-03b flags this as a guardrail but the "~44 MB" figure is the ONNX
**model file size on disk**, not necessarily the InferenceSession's steady-state RSS (ONNX Runtime
sessions typically allocate additional working memory for intermediate tensors, arena allocators, and
thread pools beyond the raw weight bytes).

**Why it happens:** File size and runtime RSS are different numbers; assuming they're equal risks an
under-budgeted RAM estimate against a container that has already OOM-killed multiple times in prod
history (per CLAUDE.md's documented OOM incidents).

**How to avoid:** D-03b already mandates measuring steady-state RSS before enabling in prod — do this
via a local `docker stats` or `/proc/<pid>/status` check with the session loaded and idle, then again
under a representative inference burst (10-20 calls back-to-back, matching one game's candidate
volume), and compare against the existing accounting in `app/services/engine.py`'s own RAM comment
block (lines ~120-141) which already budgets the 4 GB container down to the byte for the Stockfish
pool. Any Maia RSS number must be added to that same budget, not treated as a separate/ignorable
line item.

## Code Examples

### Existing cp→ES sigmoid to reuse verbatim (GEMS-07)
```python
# Source: app/services/eval_utils.py:34-63
LICHESS_K: float = 0.00368208

def eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white", "black"]) -> float:
    sign = 1 if user_color == "white" else -1
    return 1.0 / (1.0 + math.exp(-LICHESS_K * sign * eval_cp))
```

### Existing out-of-book depth lookup (GEMS-02)
```python
# Source: app/services/opening_lookup.py:123-149 (signature + return contract)
def find_opening_ply_count(moves: list[str]) -> int:
    """Return the 1-based ply depth of the deepest known-opening match in moves.
    Returns 0 if no match. A ply p is "out of book" iff p >= find_opening_ply_count(moves)."""
```

### Client-side 12-plane encoding to port (GEMS-04) — confirmed contract
```typescript
// Source: frontend/src/lib/maiaEncoding.ts:29,147-188 (the confirmed contract to port to Python)
// 12-plane order: white P,N,B,R,Q,K (0-5), black p,n,b,r,q,k (6-11)
// square index: s = row*8 + file, row = rank-1 (a1=0, h8=63)
// Black to move -> mirror piece placement (flip ranks, swap case) BEFORE encoding
// tokens[squareIndex(sq) * 12 + planeIdx] = 1.0 (square-major flat layout)
```
The VERIFIED prior Python repro (`.planning/notes/2026-07-10-...md`) already implements this
port and validated it to 0.01% against the live UI — locate/recover that script (or its author's
scratch files, if not committed) as the starting point rather than re-deriving from the TS source
alone.

### Client-side WDL/expected-score collapse (GEMS-04, model output side)
```typescript
// Source: frontend/src/lib/maiaEncoding.ts:272-291
// logits_value output order is [Loss, Draw, Win] (index 0,1,2) — NOT W/D/L.
// expectedScore(wdl) = wdl.win + 0.5 * wdl.draw
```
Note: `maia_prob` (the value this phase stores) is the **policy** probability of the played move
(post `maskAndSoftmax` over `logits_move`), NOT the WDL expected score — confirm this distinction
explicitly in the plan, since both a policy prob and a WDL-derived ES exist in the client code and
only the former is what `classifyGem`'s C1 check (`gemMove.ts:53`) consumes.

### Sibling-table pattern to mirror (GEMS-01)
```python
# Source: app/models/bot_game_settings.py (CheckConstraint pattern) +
# app/models/game_flaw.py (composite-key sibling-table pattern) — combine both
class GameBestMove(Base):
    __tablename__ = "game_best_moves"
    __table_args__ = (
        UniqueConstraint("game_id", "ply", name="uq_game_best_moves_game_ply"),
        # + any CheckConstraint for a mate-representation enum, per planner's discretion
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    maia_prob: Mapped[float] = mapped_column(REAL, nullable=False)
    best_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    best_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    second_cp: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    second_mate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Client-side ephemeral gem sweep (`useGemSweep.ts`, Phase 172) | Backend-stored candidate rows, query-time classification | This phase (174) | Gems/greats become device-independent, persistent, filterable — the entire reason for this milestone |
| Remote worker full-ply pass at MultiPV-2 | Remote worker full-ply pass at MultiPV-1 (Phase 146 D-03) | 2026-06-xx (Phase 146) | Directly causes Pitfall 1 — the second-best data this phase needs is no longer universally available from the worker submission path |

**Deprecated/outdated:**
- SEED-108's framing of the runner-up eval as "already computed at nearly every ply ... pure
  plumbing, no extra Stockfish `go`" — accurate for the local drain lane only; superseded by
  Pitfall 1's finding for the remote-worker lane.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `.planning/notes/2026-07-10-...md` Python parity script (or its logic) is recoverable/reconstructable as the GEMS-04 spike's starting point — the note describes it but the research did not locate a committed `.py` file implementing it | Summary, Code Examples | If the original script isn't recoverable, the spike must be rebuilt from the note's description + `maiaEncoding.ts`, which is still HIGH confidence (contract is written down) but costs more spike time than assumed |
| A2 | Remote-worker-evaluated games are the MAJORITY of tier-1 (new-game) traffic, not a minority | Pitfall 1, Summary | If local `_full_drain_tick` actually wins most tier-1 races in practice (e.g. remote workers are usually busy with tier-3/4 backfill instead), Pitfall 1's targeted-extra-Stockfish-call cost is smaller than estimated — still correct to implement defensively, but the plan's cost/scale estimate should be measured (e.g. a quick prod query on `eval_jobs`/heartbeat `worker_id` distribution for recent tier-1 claims) rather than assumed `[ASSUMED]` |
| A3 | `_FullPlyEvalTarget`/the PGN walk already used by both `_full_drain_tick` and `_apply_atomic_submit` gives cheap access to a SAN move list suitable for `find_opening_ply_count` without extra I/O | Pitfall 3 | If not, an extra PGN re-parse or DB round-trip is needed — minor cost, not a design blocker |
| A4 | onnxruntime's `InferenceSession` steady-state RSS for this specific ~44 MB model is materially close to the file size (not, say, 3-5x it from arena allocation) | Pitfall 5, Standard Stack | If RSS is much higher than expected, D-03b's own mandated empirical measurement step catches it BEFORE prod enablement — this is a measurement task the plan must include, not a fact to trust blindly |
| A5 | `is_correspondence` for a `Game` row is derived via `is_correspondence_time_control(game.time_control_str)` (a function call) rather than a persisted column, matching `library_service.py`'s usage — no `Game.is_correspondence` column was found during this research | Architecture Patterns Pattern 4 | If a column with that name is added later, the derivation call site should be updated to match; low risk, cosmetic |

**If this table is empty:** N/A — see entries above.

## Open Questions (RESOLVED at planning)

> All three resolved during Phase 174 planning (2026-07-16). Resolutions recorded inline below.

1. **Should the targeted "fill missing second-best" Stockfish call (Pitfall 1) be a synchronous part
   of eval-apply, or deferred to a later pass?**
   - **RESOLVED:** Synchronous, per the recommendation. Plan 174-05 implements the bounded backend-owned
     `evaluate_nodes_multipv2` fallback inline in the eval-apply path and budgets the real Stockfish cost;
     actual added-call volume is to be measured in a dev-DB dry run during execution.
   - What we know: `apply_full_eval` already runs `asyncio.gather` over engine calls before its write
     session opens (established pattern); adding a bounded extra gather for missing second-best plies
     fits the same shape.
   - What's unclear: the exact latency/throughput impact at prod scale (how many out-of-book
     best-move plies per game typically lack second-best under the remote-worker lane) — needs
     measurement, not just estimation.
   - Recommendation: implement synchronously (simpler, one commit, matches D-05a's "gate computed at
     write time" framing) and measure actual added Stockfish call volume in a dev-DB dry run before
     considering deferral.

2. **Where exactly does the parity spike script live, and does it become a permanent regression
   test or a throwaway spike artifact?**
   - What we know: D-01/D-02 require a fixture-based parity test that GATES all further work; Phase
     168 (`onnxruntime-node` feasibility spike) is the precedent for "spike-first, pause if it fails."
   - What's unclear: whether the parity check should also become a committed CI-gated regression test
     (protecting against future onnxruntime/model-file changes) or remain a one-time spike artifact.
   - Recommendation: keep it as a committed `scripts/`-level script (not deleted after the spike
     passes) given Pitfall 2's version-regression risk — cheap insurance against a future dependency
     bump silently breaking parity.
   - **RESOLVED:** Permanent, committed. Plan 174-01 keeps `scripts/maia_parity_spike.py` + its fixture
     corpus committed as a standing regression guard (not a throwaway artifact).

3. **Exact final tolerance epsilon for D-01's "loose band ~±0.02"** — CONTEXT.md explicitly defers
   this to "the researcher from measured drift." This research did not have a running onnxruntime
   environment available to measure actual CPU-vs-WebGPU drift empirically (no GPU/browser harness in
   this research session). Recommendation: the spike task itself (GEMS-04, first task of the phase)
   must measure real drift on the fixture corpus and set the final epsilon from that data, not from
   this research's ±0.02 starting estimate.
   - **RESOLVED:** Deferred into execution by design. Plan 174-01's must_haves require the final epsilon
     to be derived empirically from measured drift and recorded in the spike script + fixtures, not left
     at the ±0.02 placeholder.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `onnxruntime` (Python) | GEMS-03/04 backend inference | Not yet installed in this repo's `uv.lock` | Target `==1.20.1` `[VERIFIED: PyPI wheel exists for cp313]` | None — this is the phase's core new dependency; D-02's pause-for-rescope IS the fallback if the spike fails |
| `frontend/public/maia/maia3_simplified.onnx` model file | Backend must load the SAME model bytes the client uses | ✓ already vendored at `frontend/public/maia/maia3_simplified.onnx`, SHA-256 pinned in `frontend/public/maia/README.md` | 45,683,686 bytes, SHA-256 `405bf76c...` | The backend should either read this exact vendored file (path reference, e.g. via a build step or a symlink/copy into the backend image) or vendor a second identical copy under `app/` — planner's discretion, but MUST be byte-identical (same SHA-256) to avoid a silent parity drift source |
| Stockfish pool (`STOCKFISH_PATH`, `EnginePool`) | Pitfall 1's targeted extra `evaluate_nodes_multipv2` calls | ✓ already running (`start_engine()` at lifespan startup) | pinned `sf_18` per `Dockerfile` | N/A — already a hard dependency of the existing pipeline |
| Docker/prod container RAM budget (4 GB backend `mem_limit`) | D-03b RSS guardrail | ✓ (existing prod constraint, documented in CLAUDE.md) | — | If Maia RSS overruns the budget: D-03's fallback escape hatch is Maia-on-workers (explicitly not auto-taken, human decision) |

**Missing dependencies with no fallback:**
- `onnxruntime==1.20.1` must be installed and pass the parity spike — this is the phase's own D-02
  gate, not an external blocker.

**Missing dependencies with fallback:**
- None beyond the above.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + `pytest-asyncio` (existing backend suite) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/services/test_maia_encoding.py -x` (new file) |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GEMS-04 | Python encoding port matches client output within tier+epsilon tolerance | fixture-based parity script + unit test | `uv run python scripts/maia_parity_spike.py` then `uv run pytest tests/services/test_maia_encoding.py -x` | ❌ Wave 0 — new file, gate for all further work per D-02 |
| GEMS-01 | New table constraints (FK cascade, unique key) hold | integration (DB) | `uv run pytest tests/models/test_game_best_move.py -x` | ❌ Wave 0 |
| GEMS-02 | Candidate gate: out-of-book AND played==best AND ES-drop >= 0.05 | unit (pure function, no DB) | `uv run pytest tests/services/test_eval_apply.py::test_candidate_gate -x` | ❌ Wave 0 — extend existing `test_eval_apply.py` |
| GEMS-03 | `start_maia`/`stop_maia` no-op when onnxruntime absent (D-03a) | unit | `uv run pytest tests/services/test_maia_engine.py::test_noop_without_onnxruntime -x` | ❌ Wave 0 |
| GEMS-05 | ELO clamp [600,2600] + `*_lichess_blitz ?? raw` fallback matches frontend | unit | `uv run pytest tests/services/test_maia_engine.py::test_elo_clamp -x` | ❌ Wave 0 |
| GEMS-06 | `uv sync` on worker group excludes onnxruntime/numpy | integration (build-time check, could be a CI script) | manual: `uv sync --locked --no-dev` (worker Dockerfile's exact invocation) then `python -c "import onnxruntime"` must FAIL | ❌ Wave 0 — likely a shell assertion in CI rather than a pytest test |
| GEMS-07 | Query-time Gem/Great reclassification from stored floats is a pure constants change | unit | `uv run pytest tests/services/test_game_best_move_classification.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** targeted test file for the task (e.g. `uv run pytest tests/services/test_maia_encoding.py -x`)
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** Full suite green before `/gsd-verify-work`; additionally, the GEMS-04 parity spike
  script must have been run and its pass/fail outcome recorded BEFORE any task after it starts (D-02
  hard gate)

### Wave 0 Gaps

- [ ] `scripts/maia_parity_spike.py` — the GEMS-04 gate itself, must run FIRST
- [ ] `tests/services/test_maia_encoding.py` — encoding-port unit tests (independent of the ONNX
      session — pure tensor/index math, testable without onnxruntime installed)
- [ ] `tests/services/test_maia_engine.py` — lifecycle no-op guard (D-03a) + ELO clamp/derivation
- [ ] `tests/models/test_game_best_move.py` — new table constraints
- [ ] `tests/services/test_eval_apply.py` extension — candidate gate logic + the Pitfall-1 fallback
      path (missing second-best triggers a targeted extra engine call)
- [ ] Framework install: `uv add --group maia-inference "onnxruntime==1.20.1" numpy` (only affects
      the backend image per GEMS-06)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase adds no new user-facing endpoint; storage/inference is entirely backend-internal (eval-apply pipeline) |
| V3 Session Management | No | Same as above |
| V4 Access Control | No | No new API surface in this phase (query-time reads are Phase 175's concern) |
| V5 Input Validation | Yes | The ONNX model's inputs are entirely server-derived (board state from `GamePosition`, ELO from `Game.white_rating`/`black_rating`) — no direct user-controlled input reaches the tensor construction, so this is low-risk, but the mover's rating value SHOULD still be clamped (D-04) before being cast to float32 to avoid a malformed/extreme rating value reaching the model |
| V6 Cryptography | No | N/A — no secrets, no crypto in this phase |
| V12 File/Resource Integrity | Yes | The vendored `.onnx` model file's SHA-256 is already pinned (`frontend/public/maia/README.md`); if the backend loads its OWN copy of this file (rather than referencing the frontend's), verify the SHA-256 matches at load time or in a startup assertion, so a future accidental frontend model-file update doesn't silently desync backend inference from client inference |

### Known Threat Patterns for this phase's stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Supply-chain: a compromised/regressed `onnxruntime` PyPI release | Tampering | Exact version pin (`==1.20.1`, not a range), verified via `uv.lock` hash-pinning (already the project's standard practice for all deps) |
| Resource exhaustion: uncontrolled ONNX session memory growth under load | Denial of Service | D-03b's mandated RSS measurement before prod enablement; the session is a fixed-size singleton (no per-request session creation), so growth risk is bounded by design, not by runtime guards |
| Model-file integrity drift (backend and frontend silently loading different bytes) | Tampering (data integrity) | SHA-256 pin cross-check at backend startup (see V12 above) — not currently a THREAT per se (no external attacker vector, both files are project-controlled), but a real correctness/parity risk this phase must guard against structurally |

## Sources

### Primary (HIGH confidence)
- This codebase, direct file reads: `app/services/eval_apply.py`, `app/services/eval_drain.py`,
  `app/services/engine.py`, `app/main.py`, `app/models/game_flaw.py`, `app/models/game_position.py`,
  `app/models/bot_game_settings.py`, `app/services/eval_utils.py`, `app/services/flaws_service.py`,
  `app/services/chesscom_to_lichess.py`, `app/services/opening_lookup.py`, `app/services/library_service.py`,
  `app/models/game.py`, `pyproject.toml`, `Dockerfile`, `Dockerfile.worker`,
  `scripts/remote_eval_worker.py`, `app/schemas/eval_remote.py` — all read directly this session.
- `frontend/src/lib/maiaEncoding.ts`, `frontend/public/maia/maia-worker.js`,
  `frontend/public/maia/README.md`, `frontend/src/lib/gemMove.ts`,
  `frontend/src/hooks/useMaiaEloDefault.ts` — the canonical client sources named in CONTEXT.md,
  read directly.
- `.planning/notes/2026-07-10-flawchess-engine-self-execution-analysis.md` — a VERIFIED prior
  Python + `onnxruntime==1.20.1` headless Maia-3 repro in THIS project, matching the live UI to
  0.01%, including the explicit `onnxruntime>=1.22 segfaults` finding.
- `.planning/seeds/SEED-108-backend-gem-great-detection.md` — the locked design source.
- `.planning/phases/174.../174-CONTEXT.md` — the locked decisions for this phase.
- PyPI registry queries (`pypi.org/pypi/onnxruntime/1.20.1/json`, `.../onnxruntime/json`,
  `.../numpy/json`) — `[VERIFIED: PyPI registry]` for version/wheel-availability claims.

### Secondary (MEDIUM confidence)
- `.planning/milestones/v2.3-phases/168-headless-calibration-harness-spike-gated/168-RESEARCH.md`
  and its `STACK.md`/`PITFALLS.md` — the Phase 168 precedent for "spike-gated Maia-in-a-headless-
  runtime" feasibility work (a different runtime — Node/`onnxruntime-node` — but the same
  spike-first methodology this phase mirrors per D-01/D-02).

### Tertiary (LOW confidence)
- None — this research relied on direct codebase reads and one verified project note rather than
  general web search, given the domain is almost entirely internal-codebase-specific.

## Metadata

**Confidence breakdown:**
- Standard stack (onnxruntime pin): HIGH — directly verified via a prior in-project repro plus a
  PyPI registry check for wheel availability.
- Architecture / eval-apply insertion point: MEDIUM — `apply_full_eval` as the shared insertion
  point is HIGH confidence (directly read code proves both lanes call it); the exact shape of the
  candidate-row builder and its relationship to Pitfall 1's targeted extra Stockfish call is a
  genuine open design question for the planner, not a fully resolved pattern.
- Pitfalls: HIGH for Pitfall 1 and 2 (both are directly evidenced by reading the actual worker code
  and a project note, not inference); MEDIUM for Pitfalls 3-5 (plausible risks, not yet empirically
  confirmed at prod scale).

**Research date:** 2026-07-16
**Valid until:** ~30 days for the architectural/plumbing findings (stable internal codebase
patterns); the `onnxruntime==1.20.1` pin recommendation should be re-verified if this phase's
execution is delayed more than a few weeks, since PyPI version availability and the segfault
boundary are external facts that could shift.
