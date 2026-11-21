# Feed report: prod / all / full

- started: 2026-11-21T09:52:58+00:00
- ended: 2026-11-21T17:52:20+00:00
- stopped because: stop requested
- window size 800 games, low water 400 games
- work list size: 1056391, feed cursor: 249264
- windows fed (this run): 38, (total): 347
- lines NULLed, missed: 495693, allowed: 401343
- games fed: 209964, completed: 209306, pending: 658
- eval or flaw-set changed (fingerprint mismatch): 0

## Drain rate measured with the fleet as it is

- observed for 67.53 h since the first fed game
- games per hour: 3099.51
- lines per hour: 13236.00
- projected weeks for the remaining work list: 1.30611

## User-visible NULL window per completed game (this run)

Hours from the feed to the poll that saw blobs_completed_at set, so each value is rounded up to the poll interval.

- completed games measured: 25798
- p50: 0.10 h, p95: 0.50 h, max: 4.30 h

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| projected_weeks | 1.30611 | 8 | PASS |
| eval_change_share | 0 | 0.005 | PASS |

## Verdict: PASS
