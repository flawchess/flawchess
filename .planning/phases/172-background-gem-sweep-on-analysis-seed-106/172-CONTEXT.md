# Phase 172: Background Gem Sweep on Analysis (SEED-106) - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning
**Source:** Synthesized from `.planning/seeds/SEED-106-background-gem-sweep-on-analysis.md` (D-01–D-08 locked in the `/gsd-explore` session of 2026-07-14, amended the same day by commits `2c4f846b`, `232eae5c`, `d2c7a7e0`, `caa6e843`)

<domain>
## Phase Boundary

Gems (Phase 163, SEED-092) currently resolve **lazily, at the position the user is standing
on**: `gemC1` reads the played move's Maia probability from the cached parent curve, and only
on a C1 pass does an on-demand Stockfish grading worker spin up against the parent FEN
(`Analysis.tsx:1414-1539`). The Maia + Stockfish round-trip has real latency, so a user
stepping briskly through a game blows past gems before they render. **A gem the user steps
past before it renders is a feature that does not exist.**

This phase resolves gems for the **whole mainline in the background** while the analysis board
is open, so the move list fills in gem badges *ahead of* the cursor rather than *at* it.

Four deliverables:

1. **Background sweep with a free → cheap → expensive cascade** (D-04) — free prefilter on data
   the page already fetches and ignores, then Maia C1 on the survivors, then a Stockfish parent
   grade on the few that clear C1.
2. **Yield-to-cursor scheduling** (D-05) — **the real work of this phase.** The sweep must never
   starve the live free-run / grading engines for the node the user is actually looking at.
3. **Gem rung pinned to the mover's own rating** (D-01) — a behavior change from shipped code,
   and the precondition that makes a sweep cacheable at all.
4. **Opening-book markers + the raised gem threshold** (D-06, D-07, D-08) — one additive, computed-on-read
   backend field (`opening_ply_count`) that earns itself twice: it gates the sweep and it marks
   theory plies on every surface where gems already render.

**Scope shape:** frontend sweep + display, plus one additive (schema-only) backend field.
**No migration, no backfill, no eval-pipeline change, no new backend dependency, no Maia in Python.**

**Out of scope:**
- Persisting gems (no backend gem store, no Library-card or stats surfacing) — D-02.
- Sweeping user **variations** — mainline only.
- Sweeping **unanalyzed** games — they keep today's lazy behavior — D-03.
- Measuring real-game gem frequency before shipping (explicit call, 2026-07-14): D-07's ratios
  come from the existing Phase 165 harness TSV; absolute rates get judged in UAT on real games.

**The gating question for any plan is contention (D-05), not compute.**

</domain>

<decisions>
## Implementation Decisions

### The gem rung (behavior change)

- **D-01 — A gem is a property of the game, not of the view.** Pin gem classification to each
  **mover's own** Lichess-blitz-normalized rating-at-game-time (the rung Phase 164 already
  seeds via `deriveRawDefault` / the `*_lichess_blitz` fields). The Elo slider drives only the
  live exploration overlay, **not** the gem badges.
  *This is a behavior change from shipped code* — today `gemC1` resolves the rung via
  `nearestByElo` against the slider (`Analysis.tsx:1445`), so gems shift when the slider moves.
  Pinning is also what makes a background sweep cacheable at all: otherwise every slider nudge
  invalidates the entire sweep.
  **Both movers matter** — each ply is classified against *the player who made it*, not against
  a single per-game rung.

### Scope fence: where gems live

- **D-02 — Analysis move list only. No persistence, no backend gem store.** Gems never appear on
  Library cards or in stats. Consequence: **no Maia in Python.** Maia exists only as ONNX in the
  browser (`useMaiaEngine.ts`), and C1 is the sole reason gems are a frontend feature —
  everything else about them is backend-shaped already. Keeping gems in the client preserves
  v2.0's zero-server-load property (SEED-082).

### What gets swept, and when

- **D-03 — Sweep analyzed games only, but trigger on analysis becoming ready.** No backend evals
  ⇒ no free prefilter ⇒ no sweep. Unanalyzed games keep today's lazy behavior and surface the
  existing one-click Analyze pill instead of burning client CPU.
  **Amended 2026-07-14 (Adrian):** "analyzed" is **not** a one-shot check at mount. A bot game
  opened while its tier-1 analysis runs in the background (the live-updating analysis board from
  quick `260714-rj5`) must be swept **the moment the evals arrive**. The sweep therefore keys off
  analysis readiness as a **transition**, not a mount-time boolean — otherwise the single most
  likely game to be opened mid-analysis (a game the user just played against a bot) is exactly
  the one that never gets swept. A game must not stay stuck in lazy mode for the session just
  because it was unanalyzed when the board mounted.

### The cascade

- **D-04 — Prefilter: `played === best_move` AND out of opening book.** Both free.
  The insight that makes the sweep cheap: a gem requires C2 (played move is the graded best AND
  beats the runner-up by ≥ `MISTAKE_DROP`), and **C2 implies the played move lost ~zero expected
  score**. So the vast majority of plies can be eliminated with data the analysis page *already
  fetches and currently ignores*: `EvalPoint` (`frontend/src/types/library.ts:98-107`) carries
  per-ply `es`, `eval_cp` and `best_move` (the backend's engine best move FROM that position,
  UCI) for every ply of an analyzed game. **Nothing in `Analysis.tsx` reads `best_move` today.**
  Strict `best_move` equality (rather than an es-loss band) **fails safe**: the backend searched
  deeper than the live grading run, so on the rare disagreement we lose a gem rather than invent
  one. Missing a rare gem is the right way to be wrong.
  This mirrors the backend's existing `_hint_flaw_plies` trick (`scripts/remote_eval_worker.py:226`).

  The three tiers:
  1. **Free** — keep only plies where `played === best_move` AND the ply is out of book. Pure
     data, zero engine work. Eliminates most plies.
  2. **Cheap** — Maia forward pass on the survivors' parent positions for C1. No search.
  3. **Expensive** — Stockfish parent grade (MultiPV over the `selectCandidatesByMass` candidate
     set) on the handful that clear C1. A few passes per game, not eighty.

- **D-05 — Cascade + contention.** Reuse the existing isolated gem-grading worker and the
  `gemByNode` sticky cache (`Analysis.tsx:1484-1521` already caches a sticky per-node resolution:
  a confirmed `GemDetail` or an explicit `null` miss). The sweep is "run that same resolution
  ahead of the cursor instead of at it."
  **The sweep MUST yield to the position the user is actually looking at — never starve the live
  free-run / grading engines for the current node.** The page must not feel slower than it does
  today. This is the phase's main failure mode: a sweep that competes with the live engines makes
  the page feel *worse* while nominally fixing the complaint.

### Opening book

- **D-06 — `opening_ply_count`, computed on-read. No column, no migration, no backfill.**
  `opening_lookup.py` builds a SAN trie from `app/data/openings.tsv` (3,642 lines) as a
  module-level singleton (`_TRIE`, line 89), walks to the deepest match, and **throws the depth
  away** — `find_opening` returns only `(eco, name)`. The walk is a few dozen dict lookups on an
  already-loaded trie, and the game-detail payload already ships `moves: list[str]`
  (`app/schemas/library.py:129`), so the depth is simply computed when the game is opened and
  returned as an additive field. Persisting it would buy nothing and cost a migration plus a
  backfill over a large prod table.
  **Two implementation details:** `find_opening` takes a **PGN** and normalizes to SAN internally,
  so the detail path wants a `find_opening_from_moves(moves)` variant rather than re-parsing the
  stored PGN; and the loop tracks `last_result` but not *its* depth, so it needs an index carried
  alongside.
  **Rejected alternatives:** a persisted `games.opening_ply_count` column (migration + backfill
  for a value that is free to recompute); shipping the trie to the frontend as a generated table
  (bundle cost in a mobile-first PWA to answer one boolean per ply); and a fixed ply threshold
  (wrong in both directions — kills real gems in sharp early lines, waves through theory in long
  ones).
  Revisit only if book depth is ever needed in a SQL filter or aggregate — nothing in this phase
  needs that.
  **This supersedes SEED-092's D-02 ("no opening-ply guard").** Rationale: at low ratings a
  memorized theory move has low Maia probability, so C1 cannot distinguish preparation from
  insight. C2 suppresses most book positions (they usually have several playable moves), but not
  all — and a badge for memorization cheapens the currency.

### The threshold

- **D-07 — Raise `GEM_MAIA_MAX_PROB` from 0.10 to 0.20** (`gemMove.ts:25`). "Hard to find" becomes
  "fewer than 1 in 5 rating-peers would play it."
  Measured against the Phase 165 calibration TSV
  (`reports/data/gem-elo-calibration-2026-07-11T14-07-34-084Z.tsv`, 3,000 positions × 6 rungs),
  the raise multiplies gem frequency by **1.35× at Maia-600, rising to ~1.8× at 2200–2600**. It
  loosens things most for strong players, who are currently starved (a 2600-rung player clears C1
  on only 2.9% of even the C2-qualifying positions), and it *narrows* the Elo skew: the
  600-vs-2600 gem-rate ratio falls from 3.8× to 2.9×. So the raise runs **opposite** to SEED-092's
  low-Elo badge-inflation worry, not with it.
  **Caveat for anyone re-reading that TSV:** its sample is enriched (21.8% of positions pass C2,
  nowhere near a real-game rate), so the **absolute** frequencies are inflated and only the ratios
  transfer.

### Marker precedence

- **D-08 — Opening-book markers, precedence `severity > gem > book`.**
  `opening_ply_count` earns itself twice: it gates the sweep (D-04) and it marks every ply ≤
  `opening_ply_count` as theory.
  Today the rule is severity > gem (`VariationTree.tsx:59-69`, `resolveMarkerIcon`) — one move
  never renders two badges. **Book slots in at the bottom: severity overrides the book icon.** A
  book move can still be an inaccuracy (ECO includes plenty of dubious gambits), and in that case
  the user needs to see the flaw, not the reassurance that it was theory.
  Gem-vs-book never actually arises — D-04 skips book plies before they can be classified — but the
  chain is stated in full so the ordering is unambiguous.
  Applies on **every surface** where gems already render, not just the move list: the
  `VariationTree` marker **and** the board corner marker (`boardMarkers.tsx`).

### Claude's Discretion

- The scheduler's concrete shape (idle-callback vs. explicit priority queue vs. abortable
  batches), as long as D-05's yield-to-cursor invariant holds and is provable.
- How the sweep's progress is (or is not) surfaced in the UI — no spinner was specified.
- Test strategy and where the seams are cut, subject to the project's normal gates.
- The exact name/signature of the `find_opening_from_moves` variant.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The seed (authoritative — supersedes any paraphrase in this file)
- `.planning/seeds/SEED-106-background-gem-sweep-on-analysis.md` — D-01–D-08 locked, risks, scope shape.

### Gem machinery (shipped — Phases 163/164/165)
- `frontend/src/lib/gemMove.ts` — `GEM_MAIA_MAX_PROB` (line 25, → 0.20 per D-07), C1/C2 predicates.
- `frontend/src/pages/Analysis.tsx` — lazy gem resolution (1414-1539), `gemC1` rung via
  `nearestByElo` against the slider (1445 — D-01 changes this), `gemByNode` sticky cache
  (1484-1521), `LIVE_EVAL_CACHE_MAX = 256` (line 120).
- `frontend/src/components/analysis/VariationTree.tsx` — `resolveMarkerIcon` (59-69), today
  severity > gem; D-08 appends book.
- `frontend/src/components/analysis/boardMarkers.tsx` — the board corner marker (D-08 applies here too).
- `frontend/src/hooks/useMaiaEngine.ts` — Maia ONNX in the browser (the only Maia there is; D-02).

### The free prefilter's data source
- `frontend/src/types/library.ts:98-107` — `EvalPoint` (`es`, `eval_cp`, `best_move`). `best_move`
  is fetched today and read by nothing.
- `scripts/remote_eval_worker.py:226` — `_hint_flaw_plies`, the backend's existing precedent for
  this same free → cheap → expensive shape.

### Opening book (D-06)
- `app/services/opening_lookup.py` — SAN trie singleton `_TRIE` (line 89); `find_opening` walks to
  the deepest match and discards the depth.
- `app/data/openings.tsv` — 3,642 lines, the trie's source.
- `app/schemas/library.py:129` — game-detail payload already ships `moves: list[str]`;
  `opening_ply_count` is additive here.

### Rating normalization (D-01)
- Phase 164 (SEED-093) — `deriveRawDefault` / the `*_lichess_blitz` fields that seed the rung.

### Calibration data (D-07)
- `reports/data/gem-elo-calibration-2026-07-11T14-07-34-084Z.tsv` — 3,000 positions × 6 rungs.
  **Enriched sample: ratios transfer, absolute frequencies do not.**

</canonical_refs>

<specifics>
## Specific Ideas

- The sweep is not a new mechanism — it is the *existing* per-node gem resolution run ahead of the
  cursor instead of at it. Reuse `gemByNode` and the isolated gem-grading worker rather than
  building a parallel path.
- The cascade's economics: "a few Stockfish passes per game, not eighty."
- Success looks like badges appearing *ahead of* the cursor as the user steps forward.

</specifics>

<deferred>
## Deferred Ideas

- Sweeping user variations (mainline only this phase).
- Persisting gems / surfacing them outside `/analysis` (D-02 — explicitly rejected, not merely deferred).
- Measuring real-game gem frequency before shipping (explicit call: judge it in UAT).
- A persisted `games.opening_ply_count` column — revisit only if book depth is ever needed in a SQL
  filter or aggregate.

</deferred>

<risks>
## Risk Summary

- **Worker contention (D-05)** is the main failure mode: a sweep that competes with the live engines
  makes the page feel *worse* while nominally fixing the complaint. This is the phase's gating
  question.
- **`LIVE_EVAL_CACHE_MAX` is 256** (`Analysis.tsx:120`). Comfortable for one game's mainline (~200
  plies at worst), but it is a **shared** budget — check eviction behavior on a long game once
  variations are also populating caches, or a move-8 gem can be gone by the time the user reaches
  move 60.
- **D-01 is a behavior change against shipped code** — gems stop moving with the Elo slider. Any test
  or UAT expectation that assumed slider-linked gems is now wrong on purpose.

</risks>

---

*Phase: 172-background-gem-sweep-on-analysis-seed-106*
*Context synthesized 2026-07-14 from SEED-106 (seed-express path, user-approved)*
