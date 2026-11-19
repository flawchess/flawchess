# Feed report: prod / all / pilot

- started: 2026-11-18T22:20:26+00:00
- ended: 2026-11-19T02:47:55+00:00
- stopped because: drained
- window size 500 games, low water 150 games
- work list size: 1056391, feed cursor: 10564
- windows fed (this run): 22, (total): 22
- lines NULLed, missed: 19980, allowed: 16204
- games fed: 8705, completed: 8705, pending: 0
- eval or flaw-set changed (fingerprint mismatch): 0

## Drain rate measured with the fleet as it is

- observed for 4.46 h since the first fed game
- games per hour: 1953.95
- lines per hour: 8121.98
- projected weeks for the remaining work list: 2.62526

## User-visible NULL window per completed game (this run)

Hours from the feed to the poll that saw blobs_completed_at set, so each value is rounded up to the poll interval.

- completed games measured: 8705
- p50: 0.13 h, p95: 0.54 h, max: 2.02 h

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| projected_weeks | 2.62526 | 8 | PASS |
| eval_change_share | 0 | 0.005 | PASS |

## Verdict: PASS
