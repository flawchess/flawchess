---
title: Missed vs allowed tactic — schema & narration design
date: 2026-06-19
context: /gsd-explore session after Phase 126 UAT
status: design record, feeds Phases 127–129
---

# Missed vs allowed tactic — schema & narration design

Captured during a `/gsd-explore` session (2026-06-19). Settles how the tactic feature
distinguishes *"your blunder allowed the opponent a tactic"* from *"you missed a tactic you
could have played,"* now that SEED-054 stores the pre-blunder PV. Feeds Phases 127–129.

## The two orthogonal axes (don't conflate them)

**Axis 1 — who made the flaw** (player vs opponent): already free via
`is_opponent_expr(ply, user_color)` (`query_utils.py:23`, tested). No storage.

**Axis 2 — which PV the tactic comes from:**
- `flaw_ply+1` PV = the **refutation** (tactic that punishes the flaw). Owner = the non-mover.
  *This is the existing Phase 124 column.*
- `flaw_ply` PV = the **"instead-of"** line (tactic the mover should have played). Owner = the
  mover. *This is the SEED-054 data* (commit `e02107bb`, 2026-06-18; backfill running +
  newly-drained games store it).

## Decision — dual mover-relative column sets, NO `tactic_pov` column

A `tactic_pov` discriminator is **redundant**: orientation is determined by the column
source, and user-perspective is determined by `is_opponent_expr`. Both derivable.

Split the tactic columns on `game_flaws` into two **mover-relative** sets (relative to the
flaw-maker):

- `missed_tactic_motif / missed_tactic_piece / missed_tactic_confidence / missed_tactic_depth`
  — from `flaw_ply` PV; the flaw-maker missed this.
- `allowed_tactic_motif / allowed_tactic_piece / allowed_tactic_confidence / allowed_tactic_depth`
  — from `flaw_ply+1` PV; the flaw-maker allowed this to the other side.

A flaw can have **neither / one / both** populated (you can miss a fork *and* allow a skewer
on the same move).

### Narration = column set × `is_opponent_expr`

| flaw owner | column | user sees |
|---|---|---|
| player   | `missed_*`  | "you missed a fork" |
| player   | `allowed_*` | "you allowed a skewer" |
| opponent | `allowed_*` | "a fork was available to you" (opponent allowed *you*) |
| opponent | `missed_*`  | "opponent missed a fork" (scouting only — probably not surfaced) |

## Migration is mostly a rename — existing tags survive

The Phase 124/125 columns **are** the refutation, so they become `allowed_*`:
- Rename: `tactic_motif → allowed_tactic_motif`, `tactic_piece → allowed_tactic_piece`,
  `tactic_confidence → allowed_tactic_confidence` (backfilled tags preserved).
- New: `allowed_tactic_depth` (NULL on old rows; filled on next drain/backfill — depth needs
  a detector re-run).
- New: `missed_tactic_*` (all new — fresh detector pass on the `flaw_ply` PV, gated on
  SEED-054 coverage, which is filling in now).

## Open decision for Phase 128 planning — inline columns vs child table

8 inline columns vs a child `game_flaw_tactics(ply, orientation ∈ {missed,allowed}, motif,
piece, confidence, depth)` (0–2 rows/flaw). Lean **inline** — matches the existing wide
`game_flaws` pattern (`tempo`, `phase`, `is_miss` are inline) and avoids a join for just two
orientations. The child table only earns its keep with a foreseeable third PV source. Decide
when planning 128.

## Depth as difficulty (slider)

`*_tactic_depth` = ply at which the motif fires (the detector loop index — already known,
just discarded today). Powers a difficulty slider (beginner 1–2, advanced deeper) and also
mitigates the deep-scan false positives in [[tactic-detector-precision-gaps]]. Decide
half-moves vs "your moves deep" for the player-facing unit when planning.

## Phase mapping

- **127** — detector hardening & validation: return depth from all detectors, store depth,
  lichess CC0 validation harness, fix deep-scan/loose-pin precision. De-risks everything.
- **128** — missed-opportunity tagging: rename to `allowed_*`, add `missed_*`, second detector
  pass on `flaw_ply` PV, backend filter/schema, inline-vs-child-table decision.
- **129** — tactic filter UI: motif × pov (missed/allowed via `is_opponent_expr`) × depth slider.
