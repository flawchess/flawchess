# Feed report: prod / all / full

- started: 2026-11-21T09:18:14+00:00
- ended: 2026-11-21T09:45:23+00:00
- stopped because: stop requested
- window size 800 games, low water 400 games
- work list size: 1056391, feed cursor: 218864
- windows fed (this run): 4, (total): 309
- lines NULLed, missed: 432484, allowed: 350235
- games fed: 184159, completed: 183508, pending: 651
- eval or flaw-set changed (fingerprint mismatch): 0

## Drain rate measured with the fleet as it is

- observed for 59.41 h since the first fed game
- games per hour: 3088.69
- lines per hour: 13125.62
- projected weeks for the remaining work list: 1.35825

## User-visible NULL window per completed game (this run)

Hours from the feed to the poll that saw blobs_completed_at set, so each value is rounded up to the poll interval.

- completed games measured: 2997
- p50: 0.13 h, p95: 7.37 h, max: 11.82 h

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| projected_weeks | 1.35825 | 8 | PASS |
| eval_change_share | 0 | 0.005 | PASS |

## Verdict: PASS
