---
quick_id: 261122-kos
slug: fix-forced-mate-eval-row-and-mate-in-1-s
mode: quick
date: 2026-11-22
---

# Quick 261122-kos: Forced-mate flag reads the wrong eval row; mate in 1 stripped by the gate

Follow-up to quick 261122-jsf, from a read-only review of user 28's 36,087 prod flaws replayed offline
through the real classifier.

## Problems

1. `_detect_tactic_for_flaw` (`app/services/flaws_service.py`) derives `has_forced_mate` from the row one
   ply too late: `positions[n + 1]` for allowed, `positions[n]` for missed. `positions[N]` holds the eval
   AFTER move N, so the refutation line (starts after the flaw move) belongs to `positions[n]` and the
   missed line (starts before the flaw move) to `positions[n - 1]`. Same off-by-one as the earlier
   `pre_flaw_eval_cp` fix. The flag only matters for lines capped before the mating move (mates in 7+).
   Evidence on complete mate lines: the old row matches the line's mate distance in 54 of 2,747 cases, the
   corrected row in 2,738.
2. `apply_forcing_line_filter` (`app/services/forcing_line_gate.py`) rejects a forced mate whose only
   solver node has no stored second move: the trailing only-move strip empties the line, nothing is left
   to check, and the gate returns False (prod game 1459222 ply 15, `Qxf7#`).

## Tasks

1. Fix both indices in `_detect_tactic_for_flaw`, with bug-fix comments.
2. In `apply_forcing_line_filter`, when the stripped line has no relevant solver node and the firing node
   is a forced mate, check forcedness on the unstripped line.
3. Tests: update the two POV tests that encoded the old row, add two off-by-one regression tests, a
   mate-in-1-without-second test and a non-mate control. Mutation-check. Recount the tag changes offline.
   `CHANGELOG.md` bullet.

## Out of scope

The opening-node missing-second-move data gap (to be discussed), the Phase 252 blob re-walk, the retag run.
