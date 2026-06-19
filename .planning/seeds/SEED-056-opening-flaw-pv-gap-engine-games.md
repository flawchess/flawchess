---
id: SEED-056
status: dormant
planted: 2026-06-17
renumbered: 2026-06-19 (was SEED-054 — collided with SEED-054-best-move-pv-at-flaw-ply, now closed)
planted_during: v1.28 Tactic Tagging
trigger_when: before claiming full tactic-tag coverage in v1.28 (or whenever opening-region flaw tagging coverage matters) — engine games silently drop the refutation pv on ~3.5% of opening-region flaws, so those flaws are registered but un-taggable
scope: small
---

# SEED-056: Opening-region flaws in engine games lose their refutation `pv`

> **Not the same as the closed SEED-054.** This was originally filed as SEED-054 and
> collided with `SEED-054-best-move-pv-at-flaw-ply.md`. That sibling shipped in commit
> `e02107bb` (made the drain engine-eval `flaw_ply` for **lichess** games so the
> "better alternative" blue arrow gets a `best_move`) and is now closed. **This seed is
> a distinct, still-open gap**: it concerns **fresh engine games** losing the refutation
> `pv` via opening-region dedup, which `e02107bb` did not touch (`flaw_engine_plies` is
> still populated only for `is_lichess_eval_game` — `eval_drain.py:1748`). Verified
> still-open in code 2026-06-19.

## Why This Matters

v1.28 Tactic Tagging classifies a flaw's motif from its **refutation `pv`** (SEED-039).
But for **fresh engine games**, opening-region flaws can be registered with **no `pv`**,
so they're invisible to the tagger. Measured in prod 2026-06-17:

| Region (engine games) | Flaws | Missing `pv` |
|---|---|---|
| Engine region (`flaw_ply+1 > 20`) | 674,751 | 0.1% |
| **Opening dedup region (`flaw_ply+1 ≤ 20`)** | 160,331 | **3.5% (5,570 flaws)** |

These flaws are correctly **registered** (detection is `eval_cp`/`eval_mate`-only and
survives dedup) — they just have no refutation line to classify.

## Root Cause

`pv` is **not** position-intrinsic and **not** dedup-able: it's captured only by an actual
engine pass at `flaw_ply+1` via `evaluate_nodes_with_pv`. A dedup transplant returns
`pv_string = None` (`eval_drain.py:373`), and pv is written only from engine results
(`eval_drain.py:745` — `if pv_string is None: continue`).

The drain protects flaw-adjacent plies by excluding them from dedup
(`eval_drain.py:1643`, `t.ply not in flaw_adjacent_plies`) — **but `flaw_adjacent_plies`
is computed only for `is_lichess_eval_game`** (`eval_drain.py:1629`). Lichess games carry
%evals, so flaws are pre-knowable before the engine pass. **Fresh engine games can't know
their flaws until after the eval pass** (chicken-and-egg), so the set is empty, and an
opening blunder at ply N where N+1 ≤ DEDUP_MAX_PLY (20) gets a dedup transplant and loses
its pv.

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
  SEED-053's cache makes the surrounding lookups free). Can run as a one-time backfill for
  the existing ~5.5k stranded flaws + a small always-on tail in the drain.
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

- `app/services/eval_drain.py:1628-1635` — `flaw_adjacent_plies` (lichess-only branch).
- `app/services/eval_drain.py:779` — `_flaw_adjacent_plies` helper.
- `app/services/eval_drain.py:719-766` — flaw pv write (`pv` at `flaw_ply+1`, D-117-02).
- `app/services/eval_drain.py:363-373` — `_resolve_full_eval` (dedup returns pv=None).
- [[SEED-039-tactic-family-cause-of-error-flaw-tags]] — the consumer of the refutation pv.
- [[SEED-053-opening-eval-dedup-cache-table]] — same dedup path; surfaces together.

## Notes

Found while analyzing the SEED-053 cache design 2026-06-17. The user correctly noted that
flaw *registration* is eval-only and survives caching; this seed captures the one half
that does **not** — the pv needed for *tagging*. Verified empirically with the prod query
above (game_flaws ⋈ game_positions at flaw_ply+1, engine games only).
