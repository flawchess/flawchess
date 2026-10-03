# 227-08 tripwire debug (2026-10-02)

## Symptom
Round-mode MQ tripwire at tooling commit d07a6d0df vs Phase 226 a21s (grade depth 18, `--maia-fifo --hash warm`):
stop-off 2/60 rows differ (cBFTV, Mhfvi picks), stop-on 5/60 (cBFTV pick; GZOoY, W7T4K, mWhzd, zskVk node counts).

## Bisect (all round mode, this box)
| Run | Result vs a21s |
|---|---|
| Pre-phase tooling 5747916, full 60 rows, both stop modes | 0 diffs (a21s still reproduces) |
| 227 tooling without `--maia-fifo` (stop-on) | same 4 node diffs; cBFTV matched this time |
| 227 tooling, signal forwarding disabled (6-row subset) | same diffs, cBFTV flipped again |
| 227 tooling, Maia on the main thread (6-row subset) | 0 diffs |
| 227 tooling `--hash clear`, worker vs main-thread Maia (6 rows, and a repeat) | identical, repeatable |

## Cause
227-01 moved harness Maia off the event loop (D-18). Grades now complete while Maia infers, so pool engine
assignment (first free by index) and each engine's warm-hash history depend on timing. Under `--hash warm` a
grade's value depends on that history, so round mode stops being bit-reproducible run to run. The 226 harness was
reproducible only because the blocking main-thread Maia froze the event loop during inference. Worker inference
itself is faithful (identical under `--hash clear`). The browser app has the same timing-dependent warm-hash
behaviour. Signal forwarding (227-04) and `--maia-fifo` are not causes.

## Owner direction
Bit-identical results are not required with concurrent Maia inference; very similar is good enough.

## Resolution
- Judged D-18 check: `--hash clear`, worker vs `--maia-main-thread` on the 60-row fixture, both stop modes:
  **TRIPWIRE PASS, 0 diffs** (`tripwire/parity-clear/`, tooling commit cef88fd87).
- Report-only similarity, warm hash vs a21s (`tripwire/mq-off`, `tripwire/mq-on`):

| Mode | picks changed | pass | mean es_bot | mean nodes |
|---|---|---|---|---|
| stop-off a21s / 227 | 0 / 2 of 60 | 49 / 48 | 0.8079 / 0.7995 | 50 / 50 |
| stop-on a21s / 227 | 0 / 1 of 60 | 50 / 49 | 0.8196 / 0.8101 | 9.28 / 10.07 |

## Required follow-up for 227-09 (accept rule)
`_check_round_determinism` in `scripts/engine_dispatch_227_verdict.py` raises INVALID on any round-repeat
disagreement ("226: 0 of 60"). Under warm hash with worker Maia, round repeats WILL disagree on some positions
(227-04 measured cBFTV flipping in about 8-11% of repeats), so the judged MQ cells would always be INVALID.
227-09 must replace that rule (report the disagreement rate instead of failing, or judge MQ at `--hash clear`)
and the twin's tripwire docstring ("226 a21s bit-identical") must point at the parity check above.
