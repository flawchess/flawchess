# Blunder check caught rate by facepalm-score band

Target: prod; since: all time; generated: 2026-11-23; windows: 468
Score source: rescored by the current FACEPALM_* model over the snapshot inputs (legacy windows: live score).
Score versions: not split (--rescore bands every snapshotted window by the current model, so there is one version).

## Exploration share

7 exploration of 75 ended blunder windows with a recorded arm: share 9.3%, 95% CI 4.6-18.0%.

Verdict: **insufficient**. Rule: insufficient below 500 windows, accept when the 95% interval overlaps [0.18, 0.26], fail when it lies entirely outside.

## Caught rate by score band

Rate is caught over reached (caught + missed); false alarms happen before the blunder and are listed beside each row, never in the denominator.

### Arm: exploration

| Band | Origin | Reached | Caught | Rate | 95% CI | False alarms |
|---|---|---|---|---|---|---|
| below 0.3 | own | 0 | 0 | n/a | n/a | 0 |
| 0.3-0.5 | own | 1 | 0 | 0% | 0-79% | 0 |
| 0.5-0.6 | own | 1 | 1 | 100% | 21-100% | 0 |
| 0.6-0.7 | own | 0 | 0 | n/a | n/a | 0 |
| 0.7-0.8 | own | 0 | 0 | n/a | n/a | 0 |
| 0.8-0.9 | own | 0 | 0 | n/a | n/a | 1 |
| 0.9-1.0 | own | 1 | 1 | 100% | 21-100% | 0 |
| below 0.3 | foreign | 2 | 0 | 0% | 0-66% | 0 |
| 0.3-0.5 | foreign | 0 | 0 | n/a | n/a | 0 |
| 0.5-0.6 | foreign | 0 | 0 | n/a | n/a | 0 |
| 0.6-0.7 | foreign | 1 | 0 | 0% | 0-79% | 0 |
| 0.7-0.8 | foreign | 0 | 0 | n/a | n/a | 0 |
| 0.8-0.9 | foreign | 0 | 0 | n/a | n/a | 0 |
| 0.9-1.0 | foreign | 0 | 0 | n/a | n/a | 0 |
| below 0.3 | all | 2 | 0 | 0% | 0-66% | 0 |
| 0.3-0.5 | all | 1 | 0 | 0% | 0-79% | 0 |
| 0.5-0.6 | all | 1 | 1 | 100% | 21-100% | 0 |
| 0.6-0.7 | all | 1 | 0 | 0% | 0-79% | 0 |
| 0.7-0.8 | all | 0 | 0 | n/a | n/a | 0 |
| 0.8-0.9 | all | 0 | 0 | n/a | n/a | 1 |
| 0.9-1.0 | all | 1 | 1 | 100% | 21-100% | 0 |

Unscored windows (exploration): 0

### Arm: main

| Band | Origin | Reached | Caught | Rate | 95% CI | False alarms |
|---|---|---|---|---|---|---|
| below 0.3 | own | 0 | 0 | n/a | n/a | 0 |
| 0.3-0.5 | own | 0 | 0 | n/a | n/a | 0 |
| 0.5-0.6 | own | 0 | 0 | n/a | n/a | 0 |
| 0.6-0.7 | own | 1 | 1 | 100% | 21-100% | 0 |
| 0.7-0.8 | own | 5 | 2 | 40% | 12-77% | 0 |
| 0.8-0.9 | own | 13 | 8 | 62% | 36-82% | 0 |
| 0.9-1.0 | own | 16 | 11 | 69% | 44-86% | 2 |
| below 0.3 | foreign | 0 | 0 | n/a | n/a | 0 |
| 0.3-0.5 | foreign | 1 | 1 | 100% | 21-100% | 0 |
| 0.5-0.6 | foreign | 0 | 0 | n/a | n/a | 0 |
| 0.6-0.7 | foreign | 2 | 1 | 50% | 9-91% | 0 |
| 0.7-0.8 | foreign | 6 | 2 | 33% | 10-70% | 0 |
| 0.8-0.9 | foreign | 7 | 4 | 57% | 25-84% | 0 |
| 0.9-1.0 | foreign | 15 | 9 | 60% | 36-80% | 0 |
| below 0.3 | all | 0 | 0 | n/a | n/a | 0 |
| 0.3-0.5 | all | 1 | 1 | 100% | 21-100% | 0 |
| 0.5-0.6 | all | 0 | 0 | n/a | n/a | 0 |
| 0.6-0.7 | all | 3 | 2 | 67% | 21-94% | 0 |
| 0.7-0.8 | all | 11 | 4 | 36% | 15-65% | 0 |
| 0.8-0.9 | all | 20 | 12 | 60% | 39-78% | 0 |
| 0.9-1.0 | all | 31 | 20 | 65% | 47-79% | 2 |

Unscored windows (main): 0

### Arm: legacy

| Band | Origin | Reached | Caught | Rate | 95% CI | False alarms |
|---|---|---|---|---|---|---|
| below 0.3 | own | 13 | 4 | 31% | 13-58% | 1 |
| 0.3-0.5 | own | 13 | 3 | 23% | 8-50% | 3 |
| 0.5-0.6 | own | 13 | 6 | 46% | 23-71% | 2 |
| 0.6-0.7 | own | 19 | 10 | 53% | 32-73% | 5 |
| 0.7-0.8 | own | 22 | 8 | 36% | 20-57% | 3 |
| 0.8-0.9 | own | 33 | 20 | 61% | 44-75% | 3 |
| 0.9-1.0 | own | 56 | 35 | 62% | 49-74% | 8 |
| below 0.3 | foreign | 4 | 3 | 75% | 30-95% | 0 |
| 0.3-0.5 | foreign | 11 | 5 | 45% | 21-72% | 1 |
| 0.5-0.6 | foreign | 18 | 6 | 33% | 16-56% | 6 |
| 0.6-0.7 | foreign | 15 | 6 | 40% | 20-64% | 1 |
| 0.7-0.8 | foreign | 25 | 12 | 48% | 30-67% | 1 |
| 0.8-0.9 | foreign | 35 | 18 | 51% | 36-67% | 1 |
| 0.9-1.0 | foreign | 71 | 50 | 70% | 59-80% | 10 |
| below 0.3 | all | 17 | 7 | 41% | 22-64% | 1 |
| 0.3-0.5 | all | 24 | 8 | 33% | 18-53% | 4 |
| 0.5-0.6 | all | 31 | 12 | 39% | 24-56% | 8 |
| 0.6-0.7 | all | 34 | 16 | 47% | 31-63% | 6 |
| 0.7-0.8 | all | 47 | 20 | 43% | 30-57% | 4 |
| 0.8-0.9 | all | 68 | 38 | 56% | 44-67% | 4 |
| 0.9-1.0 | all | 127 | 85 | 67% | 58-75% | 18 |

Unscored windows (legacy): 0

