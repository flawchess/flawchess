---
id: SEED-207
status: promoted
promoted_to: Phase 244
promoted: 2026-11-02
planted: 2026-11-02
planted_during: v2.27 (after Phase 243), /gsd-explore session on Train spaced repetition vs memorization
trigger_when: owner opens the next Train-focused milestone/phase, or a quick task touches the SR ladder (app/services/train_scheduler.py)
scope: small; fits a /gsd-quick or a 1-2 plan phase. Scheduler constants + fail-branch delay + leech threshold, a one-off data migration for in-flight items, three copy strings, scheduler unit tests. No schema change.
priority: high value per effort; directly targets whether Train teaches calculation or rewards recall, and cuts repeat slots for failed items
---

# SEED-207: Train SR ladder rework, test calculation instead of recall

## Why This Matters

Train re-shows a user's own blunder positions on a spaced-repetition ladder. The
owner's hypothesis: many repeats are solved from memory of the previous attempt
(or the reveal screen), not by calculating, and real learning happens when the
player has to calculate. Prod data (below) confirms it: the short-gap repeats
are measurably faster and more accurate than first attempts, and that advantage
fades with time. Standard SRS is tuned for fact retention (language vocab),
where recalling the exact item IS the goal. In chess the item is a vehicle for a
skill (seeing the tactic), so a repeat should come when memory of the specific
answer has faded but understanding should remain.

Intended learning loop: the player uses the reveal/analysis tools on the
solution screen (especially when they score < 3 points). The first retry should
already test whether that work stuck, which needs a delay long enough for the
raw memory of the move to fade.

## Current Ladder (as of 2026-11-02)

`app/services/train_scheduler.py`:
- `LADDER_DAYS = {0: 0, 1: 3, 2: 10}` (streak 0 = next scheduled session)
- `MASTERY_STREAK_THRESHOLD = 3` (3 consecutive correct)
- Fail: streak -> 0, due at the next scheduled session (`next_scheduled_day(today)`)
- Door A `PARK_FAIL_THRESHOLD = 3` (3 fails, never correct); Door B `LEECH_FAIL_THRESHOLD = 6` (lifetime lapses)
- Due dates snap forward to the user's next scheduled weekday (`next_scheduled_day`)

Problem shape: fail -> solution revealed -> retry next session (often the next
day, the most recall-heavy step, see evidence) -> that correct counts toward
mastery. A failed item can be mastered largely from memory.

## Decisions (LOCKED in the explore session)

1. **Correct solve (including the very first attempt) -> retry in 14 days.**
   A correct first attempt counts toward mastery (it is the cleanest
   calculation signal: no memory possible).
2. **Wrong solve (any step) -> retry in 4 days**, streak resets to 0.
3. **Mastered after 2 consecutive correct solves** (was 3). Because of rule 1,
   the mastering solve always comes >= 14 days after the previous correct one.
   Paths: correct -> (14d) correct = mastered (2 solves); fail -> (4d) correct
   -> (14d) correct = mastered (3 solves).
4. **Parking: Door A stays at 3** (never solved). **Door B (leech) 6 -> 4**
   lifetime lapses.
5. **No A/B test.** Too few users (~110 active/month) for user-level power, and
   repeat accuracy is biased by construction (longer gaps -> lower accuracy).
   Ship, then do the post-ship re-check below.

Considered and rejected:
- "Skip the 3-day step, master after 2" (owner's first idea): folded into the
  above, but with 14d instead of 10d for the mastering step.
- "Stretch to 7/14 days": only moves recall-repeats later, doesn't address the
  fail-retry path.
- "5 days regardless of first outcome": a correct first attempt then masters at
  5d, where the speed-up from memory is still fully present (see table 3).
- Fail retry 5d: 4 vs 5 is inside the noise; 4 chosen for throughput and
  retention (due dates snap forward to the next scheduled day, so a nominal 4
  is effectively 4-6).

## Implementation Sketch

- `train_scheduler.py`: replace the ladder with explicit named constants, e.g.
  `CORRECT_RETRY_DAYS = 14`, `FAIL_RETRY_DAYS = 4`, `MASTERY_STREAK_THRESHOLD = 2`,
  `LEECH_FAIL_THRESHOLD = 4`. The fail branch currently uses
  `next_scheduled_day(today, ...)` (offset 0); it becomes
  `next_scheduled_day(today + FAIL_RETRY_DAYS, ...)`. Brand-new items must still
  be due immediately for their first attempt. Check where new items get their
  initial `due_date` (`train_pool.py` / `train_repository.py`) so that path
  does not pick up the new fail delay.
- Update the module docstring, the `apply_result` docstring and the Door B
  rationale comment. The "6, not Anki's 8" rationale and "alternation caps the
  streak at 1" reasoning change: with 2-in-a-row mastery, alternation can no
  longer trap an item the same way.
- `drill_item.py` docstring mentions "3 ... spaced-correct solves" and "6".
- Tests: `tests/services/test_train_scheduler.py` (ladder offsets, mastery at 2,
  door B at 4, fail delay snaps to a scheduled weekday).
- Copy (no client logic reads the thresholds, prose only):
  - `frontend/src/pages/Home.tsx:69` ("next session, then after three days, then ten, until you've solved it three times")
  - `frontend/src/lib/trainBotCopy.ts:521` `MASTERED_TAIL` ("Three in a row, so this one is retired.")
  - `frontend/src/components/train/TrainStatsCard.tsx:39-41` `MASTERED_EXPLAINER` / `PARKED_EXPLAINER` (+ the comment at :34)
  - grep for any other "three"/"3 times"/"10 days" Train copy, incl. bot lines and the reveal tour
- Changelog entry under `[Unreleased]`.

### Migration of in-flight items (one-off, decide in planning)

Active items under the old ladder (prod snapshot 2026-11-02: 2,984 active,
1,235 mastered, 159 parked):
- old streak 2 -> new streak 1 (next correct masters); old streak 1 -> 1; 0 -> 0.
- Due dates: an item now at streak 1 must not become masterable on an old
  3-day schedule (that would be a recall-driven mastery). Push due_date to at
  least (last correct solve date + 14d); failed items to at least (last fail +
  4d). The last solve date comes from `drill_solves`.
- Door B: recommend NO retroactive parking. Items with fail_count >= 4 park at
  their next lapse (`apply_result` only checks on a fail anyway).
- Mastered/parked rows unchanged.

## Prod Evidence (2026-11-02, SR items only, `drill_solves.source = 0`)

~9.6k SR solves, 217 users. Think time = `telemetry.guess_ms + telemetry.move_ms`
(present on ~8.4k solves). Gap = time since the previous attempt on the same item.

**Table 1: accuracy and median time-to-correct by previous outcome and gap**

| Attempt | Accuracy | Median think (correct) | n |
|---|---|---|---|
| First attempt (no memory possible) | 60.6% | 31.3s | 3,616 |
| After correct, 2-5d (the 3-day step) | 81.7% | 22.8s | 1,386 |
| After correct, 6-14d | 70.5% | 33.0s | 139 |
| After correct, 15d+ | 63.3% | 47.6s | 30 |
| After fail, 0-1d (next session) | 66.3% | 19.5s | 926 |
| After fail, 2-5d | 54.0% | 33.9s | 150 |
| After fail, 6-14d | 39.3% | 29.7s | 28 |

Caveat: raw gaps are confounded by user (a 6-14d gap on a 3-day step means
skipped sessions). Tables 2 and 3 control for that.

**Table 2: after a FAIL, normalized to each user's own first-attempt baseline**
(users with >= 5 first attempts with telemetry)

| Days since fail | n | Accuracy vs user's first-attempt rate | Think time vs user's median first attempt |
|---|---|---|---|
| 1 | 1,136 | +14.4 pts | 0.62x |
| 2 | 155 | +7.7 pts | 0.75x |
| 3 | 78 | -1.3 pts | 0.88x |
| 4 | 28 | +7.6 pts | 1.01x |

-> The recall advantage after a fail is gone by day 3-4. Basis for the 4-day fail retry.

**Table 3: after a CORRECT first attempt, same item, think time vs that item's own first solve**

| Days since first solve | n | Accuracy | Think time vs own first solve (median) |
|---|---|---|---|
| 3-4 | 658 | 81.2% | 0.73x |
| 5-7 | 110 | 80.0% | 0.75x |
| 8-11 | 19 | 78.9% | 1.03x |
| 12-19 | 12 | 75.0% | 1.19x |

-> Memory of a self-found solution lasts about a week and is gone by 8-11 days.
Basis for 14 days on the correct path (margin above ~10). Thin rows at long
gaps (the old ladder rarely produced them).

Interpretation: self-found solutions are remembered roughly twice as long as
solutions that were only shown on the reveal, which justifies asymmetric delays.
This matches the generation effect from memory research, but that link is the
session's prior knowledge and was not source-checked (unresolved: unverifiable).

**Table 4: parking-relevant accuracy after prior fails**

| Prior history | Gap | Accuracy | n |
|---|---|---|---|
| Never correct, 1 fail | < 2d | 66.3% | 926 |
| Never correct, 1 fail | >= 2d | 51.1% | 190 |
| Never correct, 2 fails | < 2d | 62.5% | 272 |
| Never correct, 2 fails | >= 2d | 47.5% | 80 |
| Ever correct, 1-4 lapses | >= 2d | 79-84% | ~2,100 |

-> Under spaced retries, never-solved items fail more often, so Door A (3)
will fire about 2x as often as today (rough estimate: ~13% -> ~26% of
first-failed items). Accepted: the player saw the solution twice and still
couldn't find it once memory faded. Part of today's survival is recall.

**Leech-door math** (constant per-attempt success p, ignoring Door A): P(>= k
lapses before mastery) is approximately (1 - p^m)^k with m = streak needed.

| Item | Old (m=3), k=6 | New (m=2), k=6 | New (m=2), k=4 |
|---|---|---|---|
| Coin flip (p=0.5) | 45% | 18% | 32% |
| 80% item (p=0.8) | ~1% | ~0% | 1.7% |

-> With 2-in-a-row mastery, Door B at 6 almost never fires. 4 keeps "a
coin-flip item retires with fair odds, a usually-solved item almost never".
Calendar time to 4 lapses with 4d/14d gaps is ~2 months.

**Throughput and retention context**
- SR slots that are first attempts: Aug 50%, Sep 44%, Oct 30%. 70% of Oct SR
  slots were repeats.
- User activity span after first solve (users who started > 30 days ago, n=228):
  >= 5d 36%, >= 14d 25%, >= 19d 22%, >= 28d 17%. Longer correct-path delays
  than 14d would mean even fewer users ever reach a mastering solve.
- Solves to master an item: old ladder 3 (first correct) / 4+ (first fail);
  new ladder 2 (first correct) / 3+ (first fail).

## Research (explore-session research pass, opus-tier researcher, 2026-11-02)

Claims below come from fetched pages and are quoted as data, not instructions.

Admitted (survived a refute pass, primary source read):

DATA_q7kx2mpa_START
- Retrieval practice transfers (d = 0.40 across 192 effect sizes), but strongest
  when the test response matches the trained response ("response congruency"),
  weakest for problem-solving with worked examples, and after publication-bias
  correction often no positive transfer absent the moderators. Re-showing the
  identical position maximizes congruency, i.e. it mostly measures recall of that
  item. Source: Pan & Rickard 2018, Psychological Bulletin 144(7),
  doi:10.1037/bul0000151 (https://sc-pan.github.io/pdf/PR_2018.pdf).
- Interleaved (mixed) practice: 60% vs 89% (blocked) during practice, but 63%
  vs 20% on novel problems a week later (d = 1.34); no problem was repeated
  across sessions. Source: Rohrer & Taylor 2007, Instructional Science
  35:481-498.
- Expanding vs equal spacing barely matters at long retention intervals; the
  delay before the first retrieval drives long-term retention (expanding = equal
  at 8 weeks). Caveat: word-pair/fact material. Sources: Karpicke & Roediger
  2007, JEP:LMC 33:704-719; Kang, Lindsey, Mozer & Pashler 2014, Psychonomic
  Bulletin & Review (doi:10.3758/s13423-014-0636-z).
DATA_q7kx2mpa_END

Unresolved (do not treat as settled):

DATA_v3n9tr1c_START
- Testing effect for complex / high-element-interactivity problem solving:
  van Gog & Sweller 2015 (Educational Psychology Review 27:247) say it shrinks
  or vanishes; Karpicke & Aue 2015 and Rawson 2015 dispute it in the same issue.
  Reason: source-vs-prior conflict, only secondary summaries read.
- Woodpecker Method (Smith & Tikkanen, Quality Chess 2018), deliberate
  repetition of the SAME puzzle set in shrinking cycles: support is the authors'
  anecdote; critics (zwischenzug.substack.com, lichess blog by CheckRaiseMate)
  attribute gains to memorization. No controlled repeated-vs-new puzzle study
  found. Reason: non-authoritative sources.
- Design levers with no primary chess validation found: same-motif position from
  another game, fast-correct response time as a recall flag, board mirroring,
  starting one ply earlier. Lichess's puzzle dashboard offers "replay failed
  puzzles" without SR scheduling (feature description only, not efficacy
  evidence). Reason: unverifiable.
DATA_v3n9tr1c_END

How the research shaped the decisions: congruency (Pan & Rickard) says an
identical-position repeat is mostly a recall test, so delays should outlast the
memory of the answer. Kang et al. say the first-retrieval delay is the lever
that matters most, which singles out the old next-session fail retry.

## Follow-ups (not in this seed's scope)

1. **Post-ship re-check (~1 month after deploy, cheap).** Re-run the Table 2
   and Table 3 queries. The new ladder fills exactly the thin long-gap buckets
   (4d after fail, 14d after correct). Check that think-time ratios at those
   gaps are ~1.0x (memory faded) and watch Door A/B park rates and the
   first-attempt share of SR slots. Adjust 4/14 if the curves disagree.
2. **Same-motif mastery check (bigger lever, own phase).** Instead of repeating
   the identical position for the mastering solve, serve a different position
   with the same tactic motif (from the user's other games, the cross-user
   herring pool, or the sharp-filler set). Directly addresses response
   congruency and interleaving. Building blocks already exist: tactic motif
   tagging (`app/services/tactic_detector.py`), the global herring pool,
   `SHARP_FILLER`. Open questions: motif-tag confidence gate, how mastery maps
   to "item" vs "motif", and whether to keep the identical-position retry at
   all after a fail. Capture as its own seed when this one is promoted.
3. Optional signal: fast-correct (think ratio well below the user's baseline)
   as a "likely recall" flag that withholds mastery credit. Unvalidated, see the
   unresolved ledger.

## Breadcrumbs

- `app/services/train_scheduler.py` (LADDER_DAYS, MASTERY_STREAK_THRESHOLD,
  PARK_FAIL_THRESHOLD, LEECH_FAIL_THRESHOLD, apply_result, next_scheduled_day)
- `app/models/drill_item.py` (status/streak/due_date/fail_count/ever_correct, docstring)
- `app/models/drill_solve.py` (correct_move, solved_at, telemetry JSONB with guess_ms/move_ms)
- `app/services/train_pool.py`, `app/repositories/train_repository.py` (item creation, composition, mastered/parked counts)
- `tests/services/test_train_scheduler.py`
- `frontend/src/pages/Home.tsx:69`, `frontend/src/lib/trainBotCopy.ts:521`, `frontend/src/components/train/TrainStatsCard.tsx:34-41`
- `.planning/seeds/closed/SEED-037-train-spaced-repetition-blunder-drills.md` (original SR design)

### Evidence queries (prod, read-only)

Table 2 (after fail, user-normalized) and Table 3 (same-item think ratio) were
computed with window functions over `drill_solves` partitioned by
`(user_id, game_id, ply)` ordered by `solved_at`, `source = 0`,
`game_id IS NOT NULL`, think = `(telemetry->>'guess_ms')::int + (telemetry->>'move_ms')::int`.
Table 2 baseline = per-user first-attempt accuracy and median think (users with
>= 5 first attempts). Table 3 = attempt 2 of items whose attempt 1 was correct,
ratio `think_2 / think_1` over correct attempt-2 solves, bucketed by
`solved_at - first solved_at`.
