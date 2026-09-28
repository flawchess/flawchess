# Engine search fixes (Phase 225): report

**Contract:** `reports/engine-search-fixes-225/accept-rule.md`, committed 2026-09-27 before any
gate arm ran. Rendered mechanically by `scripts/engine_search_fixes_verdict.py gates`, whose
frozen constants carry the accept rule's numbers verbatim (D-11). This report cites
`reports/engine-search-fixes-225/verdict.json` and never re-judges a criterion; a disagreement
would go into a separate dated override document (precedent:
`reports/grading-ladder/override-2026-07-31.md`), not into this text. None occurred.

---

## Headline

| Item | Outcome | Why |
|---|---|---|
| Item 2 — round underfill fix (`selectPath`) | **hold** | MQ-2 fails (A2 stop-off has 5 regressions vs A0's 4, confirmed by a fresh-process rerun); calibration's `item2_pass` is `false` |
| Item 1 — root comparability guard (clear-winner stop) | **hold** | Item 2 is held, and item 1 was never measured without item 2 (A21 always includes item 2); calibration's `item1_pass` is `false` regardless |
| Item 3 — findability fallback (`rankScore`) | **independent, ships** | Ships regardless of every bot gate above (D-14); its own D-10a/b/c/d unit tests are green (Plan 225-06) |

D-14 applies: no refit, no recalibration. Item 2 and item 1's code and tests are reverted from
the phase branch (see "D-14 application" below); item 3's code and tests stay.

## Arms

| Arm | SHA | Definition |
|---|---|---|
| A0 | `1b5313b9648d9be1116bb519a1d51e8627f3ec15` | Baseline — the commit that adds `accept-rule.md`; engine code identical to `main`, only harness tooling landed |
| A2 | `a9d5113efed9270d02692c9b97e87508ecc414b2` | A0 + item 2 (round underfill fix) |
| A21 | `27beff12fb22d009b1f30c2b5552ba9cba4aad0e` | A2 + item 1 (root comparability guard) — the ship candidate |
| FINAL | `fd8d9200f3ec68bea2e256e57a8ba77d0d5dbb5d` | A21 + item 3 (findability fallback) |

Content assertions (accept-rule.md §1) all passed: the tooling diff (`scripts/`, `bin/`,
`frontend/package*.json`) between every arm pair was empty; A0's `frontend/src/lib/engine` was
identical to `git merge-base main A0`; A0->A2 was limited to `mctsSearch.ts` and
`__tests__/mctsSearch.roundFill.test.ts`; A2->A21 was limited to `mctsSearch.ts`, `types.ts`,
`botBudget.ts`, `__tests__/mctsSearch.test.ts`, and `useFlawChessEngine.test.tsx`; A21->FINAL left
`mctsSearch.ts`, `types.ts`, and `botBudget.ts` untouched. All four arms passed the harness
self-test after `npm ci` (225-07-SUMMARY.md, Task 1/2).

## D-02 allowance

`ROOT_GUARD_BOOST_ALLOWANCE` **A = 0.04**, guard window **W = marginThreshold 0.05 + A 0.04 =
0.09** — the value every stop-rule run below passes via `--guard-window`. Measured (not the
`0.10` fallback) as the pooled p90 of the root-child value change at first expansion across 4
ELOs x the 16-position set (338 deltas), rounded up to 0.01; per-ELO p90 fell from 0.0382 (1300)
to 0.0262 (2300). Full method, caveats and per-ELO table: `reports/engine-search-fixes-225/d02-allowance.md`.

## Criteria, in the accept rule's evaluation order (§4)

### 1. Validity

Content assertions (above) passed. Every judged throughput/stop/move-quality file matched its
expected position count (16 throughput, 16 stop, 12 move-quality) and no `read_single_tsv` /
`evaluate_*` validity error was raised — `verdict.json`'s `missing` list is empty and
`status` is `complete`. `maia_peak_inflight = 1` and `maia_fifo = true` on every judged
throughput row (confirmed by `evaluate_throughput`, which raises on any inadmissible row rather
than excluding it silently — none was excluded because none was inadmissible).

### 2. T-50 and T-400 (throughput, A2 vs A0) — PASS

| Budget | A0 wall (ms) | A2 wall (ms) | Ratio | Threshold | Result |
|---|---|---|---|---|---|
| 50 | 106,794 | 100,922 | **0.9450** | <= 1.05 | PASS |
| 400 | 758,753 | 723,051 | **0.9529** | <= 1.05 | PASS |

Both ratios are below 1.0 (item 2 lowers wall clock, as expected for a confirmed bug fix), but
neither clears a large win at this ELO/position mix — six of sixteen 50-node positions and six of
sixteen 400-node positions individually read above 1.0 (`positions_above_one`), offset by larger
wins on the peaked positions the bug specifically affects (e.g. 50-node `italian` 0.551, 400-node
`C60` 0.576). `grade_cpu_ratio` (report-only) is 1.0042 (50-node) and 1.0308 (400-node) — grade
CPU is essentially flat, confirming the win (where present) is in dispatch efficiency, not in
Stockfish's own cost.

### 3. MQ-2 (move quality, A2 vs A0, stop rule off) — FAIL

A2 stop-off has **5** regressions against A0 stop-off's **4** (`es(bot_move) - es(correct) <=
-0.05`). The extra regression is a confirmed pass-to-regression flip: position `cBFTV` (A0 plays
the correct `e4c6`, es 0.975, pass; A2 plays `e2g4`, es 0.405, regression). Per RESEARCH Pitfall
8, an unconfirmed flip requires a fresh-process rerun before it counts; `a2/mq-off-rerun`
reproduced `cBFTV`'s flip byte-for-byte (`e2g4`, es 0.405) and every other row identical to the
first `a2/mq-off` run, so the flip is confirmed, not noise. All other 11 positions are identical
between A0 and A2. `MQ_REGRESSION_MARGIN = 0.05` throughout.

### 4. S1 (stop rule, A21) — PASS

A21's max wall clock across the 16-position stop-rule set is **8,343 ms** (position
`middlegame`, a budget-exhaustion row, not an early stop), against the `STOP_RULE_MAX_WALL_MS =
12,100 ms` ceiling (`computeThinkDeadlineMs` at the 5+3 full-clock preset, RESEARCH C-7).

### 5. S2 (stop rule, A21 vs A2) — PASS

A2 has 10 early stops across the 16 positions; A21 also has 10
(`STOP_RULE_MIN_EARLY_STOP_RETENTION = 0.5 x 10 = 5`, and 10 >= 5). The guard does not disable
the clear-winner branch — every position that stopped early under A2 also stopped early under
A21, with a small nodes-at-stop increase where it did (see the report-only table below).

### 6. MQ-1 (move quality, A21 vs A2, stop rule on) — PASS

A21 stop-on has 4 regressions, matching A2 stop-on's 4 exactly (no flip). `analysis_base_regressions`
and `analysis_candidate_regressions` are both 4 too (report-only, `rankedLines[0]`, not the judged
selector).

### 7. Calibration (A21 vs July-21, Phase 199 rule verbatim) — FAILS, branch `decision`

Primary verdict (A21 vs the committed 2026-07-21 curves) **fails**: Maia pooled shift **-97.9**
(se 41.4, threshold ±85.0, outside threshold), SF pooled shift **-40.0** (se 32.9, threshold
±50.0, within threshold). Null control (1100/0.00) is within threshold in both families
(Maia +32.8 vs ±165.0, SF -126.8 vs ±149.0 — comparable to July-21). Shape guard fires at
1500/0.5 (Maia shift -262.0, outside its own CI in the Maia family; the SF family also lands
outside its CI at the same cell, so the guard fires — a genuine both-families excursion, not a
single-family noise case per the accept rule's own noise-floor reasoning).

Because the primary verdict fails, `calibration_branch(primary)` returns **`decision`**
(§4's branch rule), which requires A0 and A2 to be measured against July-21 as well.

| Verdict | Result | Maia pooled shift (se, threshold) | SF pooled shift (se, threshold) | Shape guard |
|---|---|---|---|---|
| a21-vs-july (primary) | fails | -97.9 (41.4, 85.0) — outside | -40.0 (32.9, 50.0) — within | 1500/0.5 |
| a0-vs-july | fails | -71.9 (40.3, 85.0) — within | -81.4 (32.4, 50.0) — outside | 1500/0.5 |
| a2-vs-july | void | -73.5 (42.1, 85.0) — within | +29.2 (32.1, 50.0) — within | 1500/0.5 |
| a2-vs-a0 (attribution) | fails | +4.0 (38.3, 85.0) — within | +117.2 (36.3, 50.0) — outside | none |
| a21-vs-a2 (attribution) | fails | -30.5 (38.2, 85.0) — within | -67.5 (36.5, 50.0) — outside | none |

`a0-vs-july` **fails** (SF family outside its own threshold), so `baseline_drift = true`: the
unchanged baseline (`main`'s engine code, only harness tooling added) already fails the same
parity check against the July-21 curves. Per the accept rule's decision-branch table (with
drift): item 2 passes iff `a2_vs_a0` holds — it does not (fails) — so **item2_pass = false**.
Item 1 passes iff item 2 passes AND `a21_vs_a2` holds — item 2 already fails, so **item1_pass =
false** regardless of `a21_vs_a2`'s own result (which also fails).

`verdict.json`'s `calibration` block records exactly this: `branch: "decision"`,
`baseline_drift: true`, `item2_pass: false`, `item1_pass: false`,
`attribution: {a2_vs_a0: "fails", a21_vs_a2: "fails"}`, `follow_up_seed_recommended: false` (the
field is only meaningful on the `report-only` branch; `decision` always sets it `false`).

## Report-only sections (never decisive, §5)

### D-04 deadline exposure

The fraction of post-`minNodes` snapshots where a non-settled in-window root child exists (a
deadline cut could overrun the guard's window), per arm, pooled across the 16 stop-rule
positions: **A2 0.18, A21 0.18** — identical, since the guard only changes what happens once the
window is settled, not the window's exposure population. Per the accept rule's own caveat, this
metric cannot see `isClosed` through `RankedLine`, so a terminal root child (value exactly 1/0/0.5
at 0 visits) would be a false positive; the 16-position set has none, so 0.18 is the exposure as
measured, not an upper bound needing correction.

### Nodes-at-stop (median / p90)

| Arm | Median | p90 |
|---|---|---|
| A0 (report-only) | 20.0 | 50.0 |
| A2 | 24.5 | 50.0 |
| A21 | 24.5 | 50.0 |

A2 and A21 have identical nodes-at-stop distributions on this 16-position set — the guard
(A2->A21) did not measurably delay any of this set's early stops beyond what the round-underfill
fix (A0->A2) already shifted. The p90 sits at the 50-node ceiling for all three arms, meaning at
least 10% of positions never stop early regardless of arm (matching the `middlegame`/budget rows
above).

### Item-3 ordering table (`analysis_move`, A2 stop-off vs FINAL stop-off, 12 maia-blindness positions)

| id | A2 `analysis_move` | A2 delta | FINAL `analysis_move` | FINAL delta | Changed? |
|---|---|---|---|---|---|
| g687537-p46 | d6d1 | -0.321183 | d6d1 | -0.321183 | no |
| g687537-p48 | d6h6 | 0.000000 | d6h6 | 0.000000 | no |
| qFkqJ | h4f2 | 0.000000 | h4f2 | 0.000000 | no |
| 3pyT9 | c7h2 | 0.000000 | c7h2 | 0.000000 | no |
| Mhfvi | h8g8 | -0.345055 | h8g8 | -0.345055 | no |
| qRvUi | c1h6 | 0.000000 | c1h6 | 0.000000 | no |
| mWhzd | b6b5 | -0.387094 | b6b5 | -0.387094 | no |
| I3vZ1 | f7h7 | 0.000000 | f7h7 | 0.000000 | no |
| WwKKM | h5g5 | -0.475447 | h5g5 | -0.475447 | no |
| cBFTV | e2g4 | -0.570916 | e2g4 | -0.570916 | no |
| RKFRP | f7h6 | 0.000000 | f7h6 | 0.000000 | no |
| zskVk | f7h6 | 0.000000 | f7h6 | 0.000000 | no |

Zero of the 12 maia-blindness positions change their `analysis_move` (`rankedLines[0]`) between
A2 stop-off and FINAL stop-off. This fixture is designed to test move-quality regression, not to
showcase item 3's reordering effect — the qualitative check for item 3 (a handful of winning
positions where a hard-to-find move previously ranked below a much worse findable one, D-10e's
Nb5 case) is covered separately by the D-10c/D-10d unit tests committed in Plan 225-06, not by
this fixture. `analysis_regression` counts (report-only, `rankedLines[0]` vs `es_correct`) are
identical too: A0 4, A2 5 (matching `analysis_candidate_regressions` in `MQ-2`'s block above),
A21/FINAL not separately re-run against this selector since it is informational only.

### Calibration shift in context (never averaged, never used to adjust a threshold)

Phase 199's own pooled shifts (July-21 vs its own 2026-08-01 sweep) were Maia **-57.7**, SF
**-9.9** — both held comfortably inside threshold. Phase 225's A21-vs-July-21 pooled shifts are
Maia **-97.9**, SF **-40.0**: the Maia family has moved roughly 40 internal ELO further negative
since Phase 199's own measurement, and the SF family roughly 30 further negative, though SF still
holds. Since Phase 225's own A0 (unchanged baseline) already fails the same check
(`a0-vs-july` SF -81.4, outside ±50.0), a material share of this incremental shift predates any
Phase 225 code change — this is placed here as context for a future calibration unit, not
attributed to any Phase 225 item.

## D-14 application

Item 2 and item 1 are held. Per D-14 and the plan's revert instruction: every `(225-05)` code
commit (item 1, on top of A2) and every `(225-04)` code commit (item 2) touching `frontend/src`
is reverted from the phase branch, newest first — item 1 was never measured without item 2, so
holding item 2 holds item 1 regardless of item 1's own numbers. Item 3's code and tests
(`(225-06)`) are untouched. See `225-08-SUMMARY.md` for the exact revert commit list and the
`mctsSearch.test.ts` conflict resolution against Plan 225-06's edits.

No refit, no recalibration, and no edit to this accept rule or to
`scripts/engine_search_fixes_verdict.py`'s frozen constants occurred at any point after gate data
existed.

## Follow-up

Both held items get a single follow-up seed (`.planning/seeds/SEED-174-*.md`, item 2 and item 1
together, since item 1 was gated by item 2's own failure) recording the failing criterion (MQ-2's
confirmed `cBFTV` flip; the calibration decision-branch numbers above), the four arm SHAs, and the
note that D-14 forbids a refit as the remedy. Item 4 (non-root candidate cap) and the deferred
flatness/deadline-cut guarding idea are recorded separately in
`.planning/seeds/SEED-173-engine-non-root-candidate-cap.md` per D-15.

*Update 2026-09-28:* SEED-173 and SEED-174 were folded into SEED-171 (item 6 and the "calibration
baseline drift" section) and deleted.
