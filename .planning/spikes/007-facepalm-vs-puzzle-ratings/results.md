# Spike 007 results

Puzzles: 26464, Elo features-elo1500.tsv. Verdict: {'threshold': -0.3, 'loss_view_rho': -0.237, 'miss_view_rho': -0.567, 'verdict': 'PARTIAL'}

## all (n = 26464)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.618 | -0.296 | 19068 | 0.7205 |
| composite, loss view, played prob fixed | - | -0.666 | -0.362 | 19068 | 0.7205 |
| composite, miss view | - | -0.642 | -0.508 | 26464 | 1.0 |
| composite, miss view, carried forward | - | -0.641 | -0.509 | 26464 | 1.0 |
| loss, depth 3 | - | -0.621 | -0.344 | 26462 | 0.9999 |
| loss, decaying mean (shipped) | - | -0.623 | -0.412 | 26462 | 0.9999 |
| loss, first stable | - | -0.629 | -0.353 | 26462 | 0.9999 |
| missed, depth 3 | - | -0.347 | -0.335 | 26464 | 1.0 |
| missed, decaying mean (shipped) | - | -0.591 | -0.384 | 26464 | 1.0 |
| missed, decaying mean, carried forward | - | -0.59 | -0.385 | 26464 | 1.0 |
| missed, first stable | - | -0.602 | -0.374 | 26464 | 1.0 |
| reply spread (shipped) | + | 0.365 | 0.285 | 26464 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.492 | -0.415 | 26464 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | -0.079 | -0.063 | 26464 | 1.0 |
| pre-blunder spread | ? | 0.054 | 0.039 | 26464 | 1.0 |
| solver moves (length baseline) | + | 0.606 | -0.001 | 26464 | 1.0 |

## primary: non-mate, solver moves <= 2 (n = 9072)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.237 | -0.237 | 5733 | 0.6319 |
| composite, loss view, played prob fixed | - | -0.321 | -0.321 | 5733 | 0.6319 |
| composite, miss view | - | -0.567 | -0.567 | 9072 | 1.0 |
| composite, miss view, carried forward | - | -0.567 | -0.567 | 9072 | 1.0 |
| loss, depth 3 | - | -0.403 | -0.403 | 9070 | 0.9998 |
| loss, decaying mean (shipped) | - | -0.374 | -0.374 | 9070 | 0.9998 |
| loss, first stable | - | -0.38 | -0.38 | 9070 | 0.9998 |
| missed, depth 3 | - |  | 0.0 | 9072 | 1.0 |
| missed, decaying mean (shipped) | - | -0.4 | -0.4 | 9072 | 1.0 |
| missed, decaying mean, carried forward | - | -0.4 | -0.4 | 9072 | 1.0 |
| missed, first stable | - | -0.4 | -0.4 | 9072 | 1.0 |
| reply spread (shipped) | + | 0.253 | 0.253 | 9072 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.451 | -0.451 | 9072 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | -0.032 | -0.032 | 9072 | 1.0 |
| pre-blunder spread | ? | 0.012 | 0.012 | 9072 | 1.0 |
| solver moves (length baseline) | + | 0.007 | -0.0 | 9072 | 1.0 |

## non-mate (n = 18839)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.299 | -0.149 | 11451 | 0.6078 |
| composite, loss view, played prob fixed | - | -0.374 | -0.217 | 11451 | 0.6078 |
| composite, miss view | - | -0.453 | -0.427 | 18839 | 1.0 |
| composite, miss view, carried forward | - | -0.452 | -0.43 | 18839 | 1.0 |
| loss, depth 3 | - | -0.389 | -0.243 | 18837 | 0.9999 |
| loss, decaying mean (shipped) | - | -0.353 | -0.28 | 18837 | 0.9999 |
| loss, first stable | - | -0.377 | -0.233 | 18837 | 0.9999 |
| missed, depth 3 | - | 0.151 | -0.119 | 18839 | 1.0 |
| missed, decaying mean (shipped) | - | -0.376 | -0.304 | 18839 | 1.0 |
| missed, decaying mean, carried forward | - | -0.378 | -0.309 | 18839 | 1.0 |
| missed, first stable | - | -0.408 | -0.309 | 18839 | 1.0 |
| reply spread (shipped) | + | 0.165 | 0.185 | 18839 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.336 | -0.349 | 18839 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | -0.009 | -0.031 | 18839 | 1.0 |
| pre-blunder spread | ? | -0.021 | 0.008 | 18839 | 1.0 |
| solver moves (length baseline) | + | 0.403 | 0.0 | 18839 | 1.0 |

## mate (n = 7625)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.444 | -0.263 | 7617 | 0.999 |
| composite, loss view, played prob fixed | - | -0.528 | -0.339 | 7617 | 0.999 |
| composite, miss view | - | -0.555 | -0.401 | 7625 | 1.0 |
| composite, miss view, carried forward | - | -0.555 | -0.401 | 7625 | 1.0 |
| loss, depth 3 | - | -0.395 | -0.109 | 7625 | 1.0 |
| loss, decaying mean (shipped) | - | -0.4 | -0.115 | 7625 | 1.0 |
| loss, first stable | - | -0.396 | -0.11 | 7625 | 1.0 |
| missed, depth 3 | - | -0.402 | -0.182 | 7625 | 1.0 |
| missed, decaying mean (shipped) | - | -0.414 | -0.148 | 7625 | 1.0 |
| missed, decaying mean, carried forward | - | -0.414 | -0.148 | 7625 | 1.0 |
| missed, first stable | - | -0.414 | -0.148 | 7625 | 1.0 |
| reply spread (shipped) | + | 0.465 | 0.334 | 7625 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.507 | -0.382 | 7625 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | 0.08 | 0.082 | 7625 | 1.0 |
| pre-blunder spread | ? | -0.062 | -0.092 | 7625 | 1.0 |
| solver moves (length baseline) | + | 0.502 | 0.005 | 7625 | 1.0 |

## solver moves = 1 (n = 3555)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.194 | -0.194 | 3553 | 0.9994 |
| composite, loss view, played prob fixed | - | -0.283 | -0.283 | 3553 | 0.9994 |
| composite, miss view | - | -0.289 | -0.289 | 3555 | 1.0 |
| composite, miss view, carried forward | - | -0.289 | -0.289 | 3555 | 1.0 |
| loss, depth 3 | - | -0.018 | -0.018 | 3553 | 0.9994 |
| loss, decaying mean (shipped) | - | -0.018 | -0.018 | 3553 | 0.9994 |
| loss, first stable | - | -0.018 | -0.018 | 3553 | 0.9994 |
| missed, depth 3 | - | -0.043 | -0.043 | 3555 | 1.0 |
| missed, decaying mean (shipped) | - | -0.043 | -0.043 | 3555 | 1.0 |
| missed, decaying mean, carried forward | - | -0.043 | -0.043 | 3555 | 1.0 |
| missed, first stable | - | -0.043 | -0.043 | 3555 | 1.0 |
| reply spread (shipped) | + | 0.284 | 0.284 | 3555 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.289 | -0.289 | 3555 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | 0.07 | 0.07 | 3555 | 1.0 |
| pre-blunder spread | ? | -0.056 | -0.056 | 3555 | 1.0 |
| solver moves (length baseline) | + |  |  | 3555 | 1.0 |

## solver moves = 2 (n = 12122)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.406 | -0.406 | 8785 | 0.7247 |
| composite, loss view, played prob fixed | - | -0.455 | -0.455 | 8785 | 0.7247 |
| composite, miss view | - | -0.627 | -0.627 | 12122 | 1.0 |
| composite, miss view, carried forward | - | -0.627 | -0.627 | 12122 | 1.0 |
| loss, depth 3 | - | -0.507 | -0.507 | 12122 | 1.0 |
| loss, decaying mean (shipped) | - | -0.5 | -0.5 | 12122 | 1.0 |
| loss, first stable | - | -0.503 | -0.503 | 12122 | 1.0 |
| missed, depth 3 | - | -0.399 | -0.399 | 12122 | 1.0 |
| missed, decaying mean (shipped) | - | -0.484 | -0.484 | 12122 | 1.0 |
| missed, decaying mean, carried forward | - | -0.484 | -0.484 | 12122 | 1.0 |
| missed, first stable | - | -0.484 | -0.484 | 12122 | 1.0 |
| reply spread (shipped) | + | 0.341 | 0.341 | 12122 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.503 | -0.503 | 12122 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | -0.071 | -0.071 | 12122 | 1.0 |
| pre-blunder spread | ? | 0.038 | 0.038 | 12122 | 1.0 |
| solver moves (length baseline) | + |  |  | 12122 | 1.0 |

## solver moves = 3 (n = 7904)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.096 | -0.096 | 5091 | 0.6441 |
| composite, loss view, played prob fixed | - | -0.169 | -0.169 | 5091 | 0.6441 |
| composite, miss view | - | -0.332 | -0.332 | 7904 | 1.0 |
| composite, miss view, carried forward | - | -0.336 | -0.336 | 7904 | 1.0 |
| loss, depth 3 | - | -0.003 | -0.003 | 7904 | 1.0 |
| loss, decaying mean (shipped) | - | -0.245 | -0.245 | 7904 | 1.0 |
| loss, first stable | - | -0.018 | -0.018 | 7904 | 1.0 |
| missed, depth 3 | - | -0.214 | -0.214 | 7904 | 1.0 |
| missed, decaying mean (shipped) | - | -0.239 | -0.239 | 7904 | 1.0 |
| missed, decaying mean, carried forward | - | -0.227 | -0.227 | 7904 | 1.0 |
| missed, first stable | - | -0.215 | -0.215 | 7904 | 1.0 |
| reply spread (shipped) | + | 0.138 | 0.138 | 7904 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.288 | -0.288 | 7904 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | -0.049 | -0.049 | 7904 | 1.0 |
| pre-blunder spread | ? | 0.017 | 0.017 | 7904 | 1.0 |
| solver moves (length baseline) | + |  |  | 7904 | 1.0 |

## solver moves >= 4 (n = 2883)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.022 | -0.028 | 1639 | 0.5685 |
| composite, loss view, played prob fixed | - | -0.099 | -0.106 | 1639 | 0.5685 |
| composite, miss view | - | -0.178 | -0.185 | 2883 | 1.0 |
| composite, miss view, carried forward | - | -0.18 | -0.185 | 2883 | 1.0 |
| loss, depth 3 | - | -0.036 | -0.039 | 2883 | 1.0 |
| loss, decaying mean (shipped) | - | -0.1 | -0.076 | 2883 | 1.0 |
| loss, first stable | - | -0.044 | -0.046 | 2883 | 1.0 |
| missed, depth 3 | - | -0.053 | -0.047 | 2883 | 1.0 |
| missed, decaying mean (shipped) | - | -0.086 | -0.073 | 2883 | 1.0 |
| missed, decaying mean, carried forward | - | -0.088 | -0.07 | 2883 | 1.0 |
| missed, first stable | - | -0.069 | -0.055 | 2883 | 1.0 |
| reply spread (shipped) | + | 0.128 | 0.145 | 2883 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.172 | -0.184 | 2883 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | -0.053 | -0.056 | 2883 | 1.0 |
| pre-blunder spread | ? | 0.028 | 0.038 | 2883 | 1.0 |
| solver moves (length baseline) | + | 0.158 | -0.002 | 2883 | 1.0 |

## hangingPiece (n = 989)

| term | expected | rho | rho, length partialled out | n scored | coverage |
|---|---|---|---|---|---|
| composite, loss view | - | -0.389 | -0.17 | 940 | 0.9505 |
| composite, loss view, played prob fixed | - | -0.499 | -0.238 | 940 | 0.9505 |
| composite, miss view | - | -0.417 | -0.355 | 989 | 1.0 |
| composite, miss view, carried forward | - | -0.417 | -0.355 | 989 | 1.0 |
| loss, depth 3 | - | -0.493 | -0.139 | 989 | 1.0 |
| loss, decaying mean (shipped) | - | -0.459 | -0.171 | 989 | 1.0 |
| loss, first stable | - | -0.478 | -0.14 | 989 | 1.0 |
| missed, depth 3 | - | -0.301 | -0.387 | 989 | 1.0 |
| missed, decaying mean (shipped) | - | -0.381 | -0.212 | 989 | 1.0 |
| missed, decaying mean, carried forward | - | -0.381 | -0.213 | 989 | 1.0 |
| missed, first stable | - | -0.399 | -0.183 | 989 | 1.0 |
| reply spread (shipped) | + | 0.268 | 0.298 | 989 | 1.0 |
| ln P(punishing move) (Findable / best-move term) | - | -0.291 | -0.299 | 989 | 1.0 |
| ln P(blunder) (played term, not testable) | ? | -0.21 | -0.071 | 989 | 1.0 |
| pre-blunder spread | ? | 0.167 | 0.114 | 989 | 1.0 |
| solver moves (length baseline) | + | 0.672 | -0.011 | 989 | 1.0 |

## Cross-validated linear model of the rating

| features | R^2 | RMSE | rho |
|---|---|---|---|
| length only | 0.383 | 476.6 | 0.562 |
| ln P(punishing move) only | 0.199 | 542.9 | 0.492 |
| reply spread only | 0.094 | 577.5 | 0.365 |
| reply spread + ln P(punishing move) | 0.207 | 540.2 | 0.488 |
| loss + reply spread (shipped loss-view pair) | 0.43 | 458.2 | 0.648 |
| loss + ln P(punishing move) | 0.476 | 439.0 | 0.69 |
| loss + reply spread + ln P(punishing move) | 0.477 | 438.8 | 0.69 |
| shipped terms (loss, spread, missed, ln P(punish)) | 0.49 | 433.2 | 0.698 |
| shipped terms + length | 0.541 | 410.8 | 0.735 |
| shipped terms + length + extras | 0.583 | 391.7 | 0.763 |

## Elo sensitivity (n = 6000 shared puzzles)

| term | base | features-elo1100.tsv | features-elo1900.tsv |
|---|---|---|---|
| composite, loss view | -0.614 | -0.604 | -0.627 |
| composite, miss view, carried forward | -0.641 | -0.623 | -0.655 |
| reply spread (shipped) | 0.366 | 0.314 | 0.414 |
| ln P(punishing move) (Findable / best-move term) | -0.491 | -0.471 | -0.508 |
| ln P(blunder) (played term, not testable) | -0.092 | -0.147 | -0.008 |
