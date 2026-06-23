---
id: SEED-056
status: resolved
planted: 2026-06-17
renumbered: 2026-06-19 (was SEED-054 — collided with SEED-054-best-move-pv-at-flaw-ply, now closed)
updated: 2026-06-20 (one-time backfill shipped 2026-06-18; drain tail fixed 2026-06-20 — see Status below)
resolved: 2026-06-20 (drain second-pass implemented; both halves of fix option (a) now done)
planted_during: v1.28 Tactic Tagging
trigger_when: RESOLVED — both the one-time historical backfill (2026-06-18) and the always-on drain tail (2026-06-20) are done. Re-open only if prod shows the opening-region engine-game pv gap re-accumulating above a few stragglers per the Why-This-Matters query.
scope: small (drain tail only — the one-time historical backfill was already done)
---

# SEED-056: Opening-region flaws in engine games lose their refutation `pv`

> **Not the same as the closed SEED-054.** This was originally filed as SEED-054 and
> collided with `SEED-054-best-move-pv-at-flaw-ply.md`. That sibling shipped in commit
> `e02107bb` (made the drain engine-eval `flaw_ply` for **lichess** games so the
> "better alternative" blue arrow gets a `best_move`) and is now closed. **This seed is
> a distinct, still-open gap**: it concerns **fresh engine games** losing the refutation
> `pv` via opening-region dedup, which `e02107bb` did not touch (`flaw_engine_plies` is
> still populated only for `is_lichess_eval_game` — `eval_drain.py:1762-1769`). Verified
> still-open in code 2026-06-20 (symbol was renamed `flaw_adjacent_plies` → `flaw_engine_plies`).

## Status — RESOLVED 2026-06-20

Both parts of fix option (a) are now done:

- **(a1) one-time historical backfill — DONE 2026-06-18 (`1df6be08`).** Widened
  `scripts/backfill_best_move_pv.py` to cover the engine-game pv gap (no guest filter). A
  manual, script-only one-shot — it did **not** touch `eval_drain.py`. Cleaned the historical
  ~5,570 stranded flaws to near zero, but the live drain kept re-accumulating: all ~998
  stranded flaws on 2026-06-20 were analyzed *after* the backfill ran (verified 100% in prod),
  confirming a live drain gap, not a backfill remnant.
- **(a2) always-on drain tail — DONE 2026-06-20.** A targeted second engine pass in the drain
  (details below). Closes the live gap so it no longer re-accumulates.

### How the drain tail was fixed (a2)

After the main gather, engine games now pre-classify their flaws from the in-memory gather
results (`_reconstruct_pos_eval` + `classify_game_flaws`, reusing `_post_move_eval` for the
+1 shift), detect any opening-region `{flaw_ply, flaw_ply + 1}` that took an eval-only dedup
transplant (no pv), and run ONE more `evaluate_nodes_with_pv` gather over just those boards —
merged back into `engine_result_map` before the write session, so classify (tactic tagging)
AND the pv write pick it up exactly as for any engine-evaluated ply. The gather stays outside
any session (CLAUDE.md hard rule). Gated on `not is_lichess_eval_game and has_opening_dedup`,
so most ticks skip it entirely.

This solves the chicken-and-egg directly: engine games can't know their flaws before the
gather, so the classify happens *after* it (in-memory), then a small supplementary pass fills
the PVs. Lichess games are unaffected (they still pre-classify up front via
`_flaw_engine_plies`). Code lives next to that symmetric Lichess mechanism by design.

- Code: `app/services/eval_drain.py` — `_reconstruct_pos_eval`, `_missing_flaw_pv_targets`,
  `_fill_engine_game_flaw_pvs`, and the Step 3b call in `_full_drain_tick`.
- Test: `tests/services/test_full_eval_drain.py::TestFlawPv::
  test_engine_game_flaw_pv_recovered_when_refutation_ply_dedups`.
- Changelog: `[Unreleased] → Fixed`, "Opening-move tactics now tag on engine-analyzed games".
- Lands with the Phase 130 branch work (uncommitted as of 2026-06-20).

### Alternative considered and rejected: store `pv` in `opening_position_eval`

The obvious "make the transplant carry the pv" approach (add a `pv` column to the dedup
cache; we already transplant `best_move`, which IS the pv's first move, so pv is dedup-able
in principle — the old "not dedup-able" claim under Root Cause is wrong). **Decided against,
2026-06-20.** Storage is a non-issue (~58 MB across the 1.41M cache rows; avg pv 41 chars,
inline, no TOAST). The real blocker is a **cold-start problem**: pv is stored in
`game_positions` only at flaw plies (3.78M rows), but the cache has a row for *every* opening
position (1.41M) — so the existing cache rows can't be backfilled with pv from existing data,
and dedup is designed to *prevent* re-evaluating them. Adding the column only helps positions
cached *after* the change; existing rows keep producing pv-less transplants. So the cache
column would be a layer *on top of* the second pass, not a replacement, and the redundancy it
would remove is negligible at current volume (~1k second-pass flaws per few days, 1-2 evals
each, against a drain grinding millions of plies). **Re-open only if** (a) pv starts being
consumed for *non-flaw* positions (e.g. continuation lines anywhere on the eval chart — then
you want it cached broadly regardless and the write-back falls out for free), or (b)
second-pass volume grows enough that amortizing the engine cost matters. The clean shape then:
`pv` column + populate-on-demand from the second pass + proactive populate in
`_upsert_opening_cache`.

## Why This Matters

v1.28 Tactic Tagging classifies a flaw's motif from its **refutation `pv`** (SEED-039).
But for **fresh engine games**, opening-region flaws can be registered with **no `pv`**,
so they're invisible to the tagger.

| Region (engine games) | Flaws (2026-06-17) | Missing `pv` (2026-06-17) | Flaws (2026-06-20) | Missing `pv` (2026-06-20) |
|---|---|---|---|---|
| Engine region (`flaw_ply+1 > 20`) | 674,751 | 0.1% | 1,624,992 | 4 (0.00%) |
| **Opening dedup region (`flaw_ply+1 ≤ 20`)** | 160,331 | **3.5% (5,570)** | 351,208 | **0.28% (~998)** |

These flaws are correctly **registered** (detection is `eval_cp`/`eval_mate`-only and
survives dedup) — they just have no refutation line to classify.

The 2026-06-17 → 2026-06-20 drop is the one-time backfill (see Status), **not** a drain
fix. All ~998 stranded flaws on 2026-06-20 come from games analyzed **after** the backfill
ran (`full_evals_completed_at >= 2026-06-18 20:35`, verified 100% in prod) — i.e. it's
continuous re-accumulation from the still-open drain gap, not a backfill remnant.

## Root Cause

> **Correction (2026-06-20):** pv IS position-intrinsic and dedup-able in principle — we
> already transplant `best_move`, which is the pv's first move. The real reason a transplant
> carries no pv is simply that the dedup cache (`opening_position_eval`) doesn't *store* one
> (it stores eval_cp/eval_mate/best_move only), and `game_positions` stores pv only at flaw
> plies — see the rejected-alternative note in Status for why we didn't add a cache column.

`pv` is captured only by an actual engine pass at `flaw_ply+1` via `evaluate_nodes_with_pv`.
A dedup transplant returns `pv_string = None` (`_resolve_full_eval`, `eval_drain.py:383-385`),
and pv is written only from engine results (the flaw pv write — `if pv_string is None:
continue`, `eval_drain.py:824`).

The drain protects flaw-adjacent plies by excluding them from dedup (`dedup_hashes`,
`eval_drain.py:1774-1778`, `t.ply not in flaw_engine_plies`) — **but `flaw_engine_plies`
is computed only for `is_lichess_eval_game`** (`eval_drain.py:1762-1769`). Lichess games carry
%evals, so flaws are pre-knowable before the engine pass. **Fresh engine games can't know
their flaws until after the eval pass** (chicken-and-egg), so the set is empty, and an
opening blunder at ply N where N+1 ≤ DEDUP_MAX_PLY (20) gets a dedup transplant and loses
its pv. (The a2 fix closes this by pre-classifying *after* the gather — see Status.)

The 3.5% (not higher) is because positions right after a blunder are relatively unusual,
so they less often have a same-hash engine eval to transplant from — most get a real
engine pass anyway. But ~5.5k flaws today, growing, fall in the gap.

## Pre-existing, and inherited (not caused) by [[SEED-053-opening-eval-dedup-cache-table]]

This gap exists **today** with the current self-join dedup. The proposed eval cache
(SEED-053) is a pure drop-in for the same lookup — same dedup decisions, same gap. It
neither creates nor worsens this. They surface together because both touch the
opening-region dedup path; fix this one if/when full opening tactic-tag coverage matters.

## Fix Options (when triggered)

- **(a) Targeted pv backfill (recommended).** After flaw detection, for any flaw whose
  `flaw_ply+1` got a dedup transplant (no pv), run one engine `evaluate_nodes_with_pv` at
  that position and write the pv. Cheap once you have the flaw list (and cheaper still if
  SEED-053's cache makes the surrounding lookups free). **Split into: (a1) a one-time
  backfill of the existing stranded flaws — DONE in `1df6be08` (2026-06-18) — and (a2) a
  small always-on tail in the drain — DONE 2026-06-20 (see Status).** Both halves shipped;
  no periodic backfill re-run is needed anymore.
- **(b) Second micro-pass in the drain.** After detecting flaws, re-engine the
  opening-region `flaw_ply+1` positions before write. Simpler control flow but couples
  flaw detection into the same tick.
- Either way: detection is unaffected — this is purely about capturing the refutation line
  for the motif classifier.

## Scope Estimate

**Small.** A targeted re-eval of a known, bounded set of flaw positions. No schema change.
The one-time backfill of the existing ~5.5k flaws is operationally tiny; the always-on
tail is a few lines in the drain's flaw-write path.

## Breadcrumbs

- `app/services/eval_drain.py:1762-1769` — `flaw_engine_plies` (lichess-only branch; the
  `if is_lichess_eval_game:` gate is the root of the gap). Renamed from `flaw_adjacent_plies`.
- `app/services/eval_drain.py:1774-1778` — `dedup_hashes` excludes `flaw_engine_plies` (empty
  for engine games, so opening-region flaw plies still get a pv-less dedup transplant).
- `app/services/eval_drain.py:843` — `_flaw_engine_plies` helper (renamed from `_flaw_adjacent_plies`).
- `app/services/eval_drain.py:798-824` — flaw pv write (`if pv_string is None: continue` at 824).
- `app/services/eval_drain.py:365,383-385` — `_resolve_full_eval` (dedup hit returns pv=None).
- [[SEED-039-tactic-family-cause-of-error-flaw-tags]] — the consumer of the refutation pv.
- [[SEED-053-opening-eval-dedup-cache-table]] — same dedup path; surfaces together.

## Notes

Found while analyzing the SEED-053 cache design 2026-06-17. The user correctly noted that
flaw *registration* is eval-only and survives caching; this seed captures the one half
that does **not** — the pv needed for *tagging*. Verified empirically with the prod query
above (game_flaws ⋈ game_positions at flaw_ply+1, engine games only).
