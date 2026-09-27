# FlawChess DB Report — 2026-09-27

- **DB**: prod
- **Snapshot taken**: 2026-09-27T04:25Z (queries ran over ~40 min)
- **Sections run**: sanity (Checks A–D, plus extended integrity checks E–K)

## 3. Sanity Checks

### Check A — Flaw counts: `games` oracle columns vs `game_flaws`

`flaws_but_all_counts_null` = **0** on every platform.

| platform | counts present | both match | match rate | mistake mismatch | blunder mismatch | mistakes oracle/gf | blunders oracle/gf |
|---|---|---|---|---|---|---|---|
| chess.com | 491,389 | 490,661 | 99.85% | 629 | 481 | 1,447,731 / 1,448,632 (+0.06%) | 2,214,672 / 2,215,131 (+0.02%) |
| lichess | 238,402 | 237,140 | 99.47% | 1,010 | 548 | 694,729 / 695,816 (+0.16%) | 1,054,366 / 1,054,768 (+0.04%) |
| flawchess | 758 | 758 | 100% | 0 | 0 | 1,977 / 1,977 | 2,900 / 2,900 |
| pgn | 20 | 20 | 100% | 0 | 0 | 61 / 61 | 42 / 42 |

The lichess rate fell from 99.74% (09-16) to 99.47%, and lichess mismatches doubled (452 → 1,010). That drop is transient and explained:

| lichess population | n | mismatch |
|---|---|---|
| lichess-provenance, full eval **pending** | 20,310 | **746** (3.7%) |
| lichess-provenance, full eval done | 62,713 | 15 (0.02%) |
| engine-analysed | 155,357 | 501 (0.32%) |

The 20k pending games are almost all from the 2026-09-25/26 import burst (see Check H). While pending, their oracle columns hold lichess's own judgment counts and `game_flaws` holds our classifier's output, so two independent classifiers disagree as expected. Once the drain completes a game, the oracle is re-derived by our classifier and agreement returns to 0.02%.

The engine-side residue (728 chess.com + 501 lichess = 1,229 games) is **frozen legacy**: every one of them had its full eval in June 2026 (imported April–June). There are zero mismatches on anything evaluated since. That points to a classifier-threshold change in June where one side was re-derived and the other was not. A one-off `rederive` over those 1,229 games would bring engine agreement to 100%.

**Verdict: PASS** (NULL gap 0, aggregates within 0.2%).

### Check B — Eval coverage vs oracle presence (Flaws Timeline gate)

| platform | games ≥90% coverage | ge90_but_oracle_null | oracle present |
|---|---|---|---|
| chess.com | 483,308 | 0 | 483,308 |
| lichess | 235,883 | 0 | 235,883 |
| flawchess | 739 | 0 | 739 |
| pgn | 20 | 0 | 20 |

**Verdict: PASS** by the query as written. However, the query is blind to the bug in Check E: it divides by all positions (the pre-260615-rb1 denominator), so short games never reach 0.90 and get excluded before the oracle check. See Check E.

### Check C — Opening cache vs lichess median

| n_checked | n_bad (gate) | n_gross (>150cp) | n_disagreed | n_unconfirmed | cache rows |
|---|---|---|---|---|---|
| 34,251 | **0** | 33 | 337 | 593,263 (20.8%) | 2,846,931 |

`n_gross` 19 → 33 while `n_checked` grew 34%, which is in line with population growth. It is well under the 2x jump threshold.

`n_disagreed` went from 28 to 337. That rise is almost entirely one burst: 229 rows written 2026-09-19 17:06 → 09-20 21:29, spread across 199 different source games, all Stockfish 18 one-source candidates that are still unconfirmed. On every other day, 0–24 rows per day disagree. Because the rows come from 199 different games rather than one bad game, the likely cause is a batch of positions re-reached by a differently-configured worker. The contradicted candidates were correctly not promoted, so the two-source mechanism did its job. Worth a glance at which worker(s) submitted that day, but it is not poison: `n_bad` is 0.

The unconfirmed share rose from 7.3% to 20.8%. That follows from the import burst (~500k new cache rows in two weeks, each starting as a one-source candidate), which is expected.

**Verdict: PASS.**

### Check D — Opening bounce rate (engine games, plies 2–19, 1-in-16 sample on `game_id % 16 = 0`)

| n_checked | n_bounce_any | bounce_pct_any | n_band | n_bounce_band | bounce_pct_band |
|---|---|---|---|---|---|
| 710,098 | 4,519 | **0.636%** | 8,937 | 1,700 | **0.239%** |

This is flat against 09-16 (0.633% / 0.240%) and at the cache-free floor (0.618% / 0.235%).

**Verdict: PASS.**

---

### Extended checks (ad hoc, not yet in the skill)

#### Check E — Short checkmate games never get oracle columns or flaws ⚠️ BUG

**1,014 games** have `full_evals_completed_at` set but NULL oracle columns, NULL accuracy and zero `game_flaws` (920 chess.com, 93 lichess, 1 flawchess). They are still accruing: the latest was evaluated 2026-09-26. Every one of them:
- has `ply_count` 4–9 and `termination = checkmate` (1,014 of the 1,024 ≤9-ply checkmate games; all other short terminations have their oracle),
- is missing exactly one eval, on row `ply_count - 1`.

Cause: under the post-move shift, row `ply_count - 1` holds the eval of the position after the last move. When that position is checkmate, the engine gives no score, so the row stays NULL. `_compute_eval_coverage` (`app/services/flaws_service.py:298`) already excludes the terminal row from the denominator (fix 260615-rb1), but it does not exclude this second unevaluable row for mated games. A 7-ply mate (e.g. Scholar's mate) therefore scores 6/7 = 0.857 < `EVAL_COVERAGE_MIN` 0.90, so `count_game_severities` returns a `reason` and `write_oracle_counts` silently skips the UPDATE (`app/services/eval_apply.py:1370`). Longer mated games lose the same row but still clear 0.90, which is why only ≤9-ply games are affected.

Impact: these are the games with the most obvious blunder (getting mated in 2–5 moves). They are missing from the Flaws Timeline, have no flaws/drills, and per the 260615-rb1 note the frontend "Analyze" state likely never resolves for them.

Fix options: (a) treat a checkmate/stalemate final position as evaluated, either by writing `eval_mate = 0` on the pre-terminal row the same way the terminal row sometimes carries it today (972 rows have `eval_mate = 0` on the terminal row), or (b) subtract a second unevaluable row from the coverage denominator when the final board is game-over. Either fix then needs a one-off re-derive of the 1,014 games.

Also: Check B's query should use `count(*) - 1` as its denominator to match `_compute_eval_coverage`, and it should add a "full_evals set but oracle NULL, ply_count NOT NULL" probe. That probe is what surfaced this bug.

#### Check F — `games` field invariants

| check | count | assessment |
|---|---|---|
| played_at in future / before 2000 | 0 / 0 | ✅ |
| played_at NULL | 8 | pgn uploads without a date, benign |
| imported_at < played_at | 877 | all `flawchess` bot games (played_at = game end), benign |
| ply_count NULL (= result_fen NULL) | 1,660 | zero-move games (abandoned/timeout/resign before move 1), no positions. Benign. |
| TC bucket vs seconds mismatch | 0 | ✅ bucketing rule holds on all 867,683 games |
| TC seconds NULL | 24,634 | daily/correspondence (bucketed classical) + 2,162 unbucketed chess.com + 20 pgn, benign |
| rating NULL | 5,835 | lichess (5,393) + bot/pgn, benign |
| rating out of range | 13 | chess.com rating 0 (10 games) or 1 (3). Minor: these should probably be NULL so they can't leak into ELO bucketing |
| accuracy out of 0–100, negative ACPL/counts | 0 / 0 / 0 | ✅ |
| partial oracle (some colors/severities NULL, not others) | 0 | ✅ |
| self-play (white = black username) | 2 | pgn uploads, benign |
| non-standard `initial_fen` | 819 | chess.com from-position games; 80 have `full_evals_completed_at` set with 0 evals / no oracle (never analyzable), benign |

#### Check G — Eval pipeline column consistency

| check | count | assessment |
|---|---|---|
| PV / best-moves done without full eval | 0 / 0 | ✅ |
| blobs done without full eval | 135 | lichess-provenance + oracle-from-import games, benign |
| full eval set but oracle NULL | 2,211 | = 1,014 short checkmates (Check E) + 1,141 zero-move games + 56 non-standard-start games |
| oracle set, full eval NULL | 20,462 | fresh lichess-provenance imports pending the drain (Check A), transient |
| full_eval_attempts ≥3 and unfinished | 0 | ✅ (max attempts 4) |
| expired `entry_eval_lease_expiry` | 495,245 | column is not cleared on completion; expired = free by predicate. Benign cosmetic |

#### Check H — Positions and flaws structure

`game_positions` (866,023 games): user_id mismatch 0, min ply ≠ 0: 0, duplicate plies 0, ply gaps 0, max ply ≠ `ply_count` 0, row count ≠ `ply_count + 1` 0, NULL `move_san` exactly once per game (terminal) everywhere, cp+mate both set 0. |cp| > 10,000 on 104 rows, all lichess-provenance (lichess's own large cp), benign. ✅

`game_flaws` (5,419,606 rows): user_id mismatch 0, bad severity 0, ply out of range 0, motif without confidence 0, confidence out of range 0, empty FEN 0. ✅

Backlog note: 2026-09-25/26 saw an import burst of **~143k games over two days (88k + 55k), from 40–50 users per day** (vs typically <10k/day). About 115k games are pending full eval. At the current ~720 games/h (≈140 lichess-provenance + ≈580 engine) that backlog takes roughly a week to drain. This is not an integrity problem, but it explains the lichess match-rate dip in Check A and the unconfirmed-cache rise in Check C.

#### Check I — Queues and jobs

- `import_jobs`: 1,513 completed, 44 failed, 0 stale (>6h running). Failures are almost all "user not found" (typos/URLs pasted as usernames) plus 3 old DB errors from March–May. Benign.
- `eval_jobs`: 2,244 tier-1 completed, none pending or stale, no expired leases.

#### Check J — Users

1,043 users (558 guests), inactive 0, login-before-created 0.
- `games_purged_at` set but games present: 6, all re-imported after the purge (games imported minutes after `games_purged_at`) except one early account from 2026-04-06 whose `games_purged_at == created_at`. Benign.
- `lifetime_games_imported` < current game count: 117 users. The gap is bot/pgn games, which the counter does not count, for all but that same 2026-04-06 account (0 lifetime vs 5,723 games; predates the counter). Benign legacy.
- 72 guests idle >90 days, none with games.

#### Check K — Derived and auxiliary tables

All zero: drill_items without matching flaw, drill_items user ≠ game owner, completed sessions without timestamp or completed before start, percentiles outside 0–100, `maia_prob` outside 0–1, best-move ply out of range, bot settings on non-bot games, bot games without settings, cache rows confirmed with <2 sources, cache rows with both cp and mate. `opening_position_eval` rows with no eval at all: 39 (minor, likely mate-only positions stored as NULL/NULL; unchecked).

## Summary

- **One real bug:** 1,014 games (and counting) that end in checkmate within 9 plies are fully evaluated but never classified, so they have no oracle, no flaws, no drills and no Timeline entry. The cause is the mated final position's missing eval, which `_compute_eval_coverage` does not exclude. The fix is small (treat the game-over position as evaluated) plus a re-derive of those games. The skill's Check B cannot see it; worth amending the query.
- **Everything else holds.** Checks A–D PASS, structural invariants on 47M+ positions and 5.4M flaws are all zero, the TC bucketing rule holds on every game, and there are no stale jobs.
- **Explained drifts:** the lichess match-rate dip (99.74 → 99.47%) is 746 mismatches in ~20k fresh lichess-analysed imports still pending the drain; completed games agree at 99.98%. The 337 cache `disagreements` are mostly a single 09-19/20 burst of 229 unconfirmed candidates across 199 games (not promoted, `n_bad` 0).
- **Optional cleanups:** re-derive 1,229 June-era engine games whose oracle and `game_flaws` disagree (frozen since June); NULL out chess.com rating 0/1 on 13 games.
- **Operational:** a ~143k-game import burst on 09-25/26 left ~115k games in the full-eval backlog, which will take about a week at the current throughput.
