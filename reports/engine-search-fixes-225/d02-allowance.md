# D-02 — `ROOT_GUARD_BOOST_ALLOWANCE` measurement

**Date:** 2026-09-27

This is design input, measured and committed before the Phase 225 accept rule and before any
gate arm runs. It answers one question only: how large is the value change a root child
typically takes on its own first expansion, so item 1's clear-winner guard window can be sized
without leaking into positions where a not-yet-visited runner-up would still overtake the
current top move once expanded.

## 1. Value

**`ROOT_GUARD_BOOST_ALLOWANCE` A = 0.04**

Resulting guard window (the number every stop-rule gate run in `accept-rule.md` passes via
`--guard-window`, and the value Plan 225-05 sets as
`FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance`):

**W = marginThreshold 0.05 + A 0.04 = 0.09**

## 2. Method

Ran from the main checkout with engine code at the phase base (tooling commit, no
`frontend/src` changes yet — see `git diff --name-only $(git merge-base main HEAD) HEAD --
frontend/src`, empty at this commit):

```bash
mkdir -p reports/data/engine-search-fixes-225/d02
setsid nohup bash -c 'for ELO in 1300 1500 1900 2300; do
  node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs \
    --dispatch-mode round --no-stop-rule --root-trace --openings 12 --maia-fifo \
    --elo "$ELO" --out-dir reports/data/engine-search-fixes-225/d02 || exit 1
done; echo D02-RUN-COMPLETE' > reports/data/engine-search-fixes-225/d02/run.log 2>&1 &

uv run python scripts/engine_search_fixes_allowance.py allowance \
  --trace-dir reports/data/engine-search-fixes-225/d02 \
  --out-json reports/data/engine-search-fixes-225/d02/allowance.json
```

Tooling commit SHA (`scripts/engine-dispatch-stop-rule.mjs`, Plan 225-01):
`6a69c8786dee765c9544b3ffb6079fff7cebfd25`.

**Position set:** the stop-rule harness's own 16-position set — the 4 built-in canonical
positions (`italian`, `middlegame`, `sharp`, `endgame`) plus `--openings 12` drawn from
`calibration-openings.mjs`'s `OPENING_BOOK` — with `--maia-fifo` (single Maia inference in
flight), 50 nodes (full budget, no stop rule via `--no-stop-rule`), concurrency 4, 8 plies.

**Delta definition:** for each root child, `delta = practicalScore(k) − practicalScore(k−1)`
at the snapshot `k` where that child's `visits` flips from 0 to 1 — its own first expansion.
`onSnapshot` fires after every applied expansion, and a root child is depth 1 (never a dead-end
discovery reached through another child), so this isolates exactly the first-expansion value
change with no engine hook.

**Percentile method:** `statistics.quantiles(values, n=100, method="inclusive")`, i.e. the
same inclusive-percentile convention `engine_search_fixes_verdict.py` uses for its own
node-at-stop percentiles.

**Allowance rule:** pooled p90 across all four ELOs, rounded up to 0.01 (ceiling), when the
pooled sample has at least 30 deltas (`METHOD measured`); otherwise the pre-registered fallback
`0.10` (`METHOD fallback`).

**Result: `METHOD measured`.** The fallback did not fire — the run completed on the first
attempt for all four ELOs (four `engine-root-trace-*.tsv` files, four matching
`engine-dispatch-stop-rule-*.tsv` files, `allowance.json`, all committed in `32a60e018`).

## 3. Per-ELO table

| ELO | n | p50 | p90 | max |
|---|---|---|---|---|
| 1300 | 96 | 0.0153 | 0.0382 | 0.0926 |
| 1500 | 90 | 0.0126 | 0.0355 | 0.0690 |
| 1900 | 80 | 0.0084 | 0.0345 | 0.0534 |
| 2300 | 72 | 0.0035 | 0.0262 | 0.0454 |
| **pooled** | **338** | - | **0.0345** | - |

`pooled_p90` = 0.0344991, rounded up to 0.01 -> **0.04**.

## 4. Caveats

- **Selection bias (RESEARCH C-2).** Only root children that PUCT actually expands are
  sampled — the higher-Q, higher-prior ones. That is exactly the in-window population the
  guard cares about (a child PUCT never visits within 50 nodes is also a child the guard's
  window would rarely need to wait on), so the bias is acceptable for this purpose, but it
  means the table does not describe *every* root child's possible first-expansion swing, only
  the ones the search actually reaches.
- **The boost shrinks with ELO.** p90 falls from 0.0382 at 1300 to 0.0262 at 2300 — the boost
  is the opponent's expected error, which is smaller for a stronger opponent model. One pooled
  value is therefore conservative (wider than needed) at high ELO and may be comparatively
  tight at low ELO. The per-ELO table is recorded here precisely so a future reader can see
  that trade-off rather than only the pooled number.
- **RESEARCH C-1 derivation.** An edge-of-window floor-prior root child (gap at the window
  boundary, `ROOT_PRIOR_FLOOR` renormalized over up to 15 candidates) is first visited around
  node N≈20-25 under root PUCT. This is the population the stop-rule arm's S2 criterion
  (early-stop retention) measures directly — the allowance recorded here is the input, not the
  outcome, of that later measurement.
