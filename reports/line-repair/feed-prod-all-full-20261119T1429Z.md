# Feed report: prod / all / full

- started: 2026-11-19T02:48:00+00:00
- ended: 2026-11-19T14:29:45+00:00
- stopped because: stop requested
- window size 500 games, low water 150 games
- work list size: 1056391, feed cursor: 46064
- windows fed (this run): 71, (total): 93
- lines NULLed, missed: 88444, allowed: 71556
- games fed: 38302, completed: 38050, pending: 252
- eval or flaw-set changed (fingerprint mismatch): 0

## Drain rate measured with the fleet as it is

- observed for 16.15 h since the first fed game
- games per hour: 2355.72
- lines per hour: 9838.29
- projected weeks for the remaining work list: 2.12243

## User-visible NULL window per completed game (this run)

Hours from the feed to the poll that saw blobs_completed_at set, so each value is rounded up to the poll interval.

- completed games measured: 29345
- p50: 0.10 h, p95: 0.37 h, max: 3.65 h

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| projected_weeks | 2.12243 | 8 | PASS |
| eval_change_share | 0 | 0.005 | PASS |

## Verdict: PASS
