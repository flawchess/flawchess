---
phase: quick-261116-mco
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/blunder_check/decaying_mean.py
  - scripts/blunder_check/miss_labels.py
  - tests/scripts/test_decaying_mean.py
  - tests/scripts/test_miss_labels.py
  - tests/scripts/test_facepalm_features.py
  - tests/scripts/test_fit_facepalm.py
autonomous: true
requirements:
  - SEED-261115-agg

estimate:
  tokens: 110000
  raw_tokens: 110000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`miss_labels.py --mode disagreement --append-to <label file>` appends about 60 blind set-8 rows to that file: n continues from the file's max n, set is 8, elo/move/link are filled, the 8 hidden-input columns and the label are empty and there is no comment cell (the shape of the set 7 rows as first appended), and every byte that was in the file before is unchanged."
    - "About 45 rows are disagreement rows (depth-3 input and decaying mean differ by at least DISAGREEMENT_MIN_PAWNS), split into a loss group (23) and a pure-miss group (22), each stratified into spike / early (recovered or gone by depth 3) / late (appears at depth 5 or later) / other; about 15 rows are plain depth-3 pure misses drawn with set 7's size x best-move-tertile cells."
    - "The decaying mean (odd depths 1,3,5,7,9, weights 1, 1/2, 1/4, 1/8, 1/16, normalised over known depths) and the per-depth loss and missed-gain series live in one pure module, scripts/blunder_check/decaying_mean.py; app/services/facepalm_score.py, app/services/blunder_check_rules.py and every FACEPALM_* constant are unchanged."
    - "The key file under gitignored temp/ holds each row's n (as written to the label file), arrays, depth-3 inputs, decaying means, best_prob, pre_spread, group and stratum; the label file holds none of them."
    - "Candidate filters are unchanged: mover rating cap, both stored lines stable (>= MIN_STABLE_LINE_PLIES or mate-ended), games already in the label file (and in the append target) excluded; DB access stays read-only via make_readonly_engine."
    - "Dev rows can never land in reports/blunder-check/facepalm-labels.tsv (--db dev with that append target is refused before Maia or the DB start), and a second set-8 append to the same file is refused with the file unchanged."
    - "facepalm_features.py --labels and fit_facepalm.py accept set-8 rows with an empty label (parsed with label empty; excluded from the fit as unlabelled and listed under Extra rows), and the real-label-file test stays green before and after the prod append."
  artifacts:
    - path: scripts/blunder_check/decaying_mean.py
      provides: "DECAY_DEPTHS, DECAY_RATIO, DECAY_WEIGHTS, loss_series, gain_series, decaying_mean (pure, no I/O)"
      contains: "DECAY_WEIGHTS"
    - path: scripts/blunder_check/miss_labels.py
      provides: "--mode disagreement, --append-to, disagreement_group, stratify_disagreement, append_blind_rows, DISAGREEMENT_SET_ID, stratum quota constants, EXIT_APPEND_REFUSED"
      contains: "append_blind_rows"
    - path: tests/scripts/test_decaying_mean.py
      provides: "series and decaying-mean unit tests incl. depth-3 parity with the shipped loss_feature / missed_feature"
    - path: tests/scripts/test_miss_labels.py
      provides: "classification, draw, byte-identical append, guard and tracer tests"
  key_links:
    - from: scripts/blunder_check/miss_labels.py
      to: scripts/blunder_check/decaying_mean.py
      via: "disagreement_group calls loss_series / gain_series / decaying_mean on MissCandidate.played_material / best_material"
      pattern: "from scripts.blunder_check.decaying_mean import"
    - from: scripts/blunder_check/miss_labels.py
      to: app/services/line_material.py
      via: "build_candidate stores LineFacts.material_array() of both lines on MissCandidate"
      pattern: "material_array\\(\\)"
    - from: scripts/blunder_check/miss_labels.py
      to: reports/blunder-check/facepalm-labels.tsv
      via: "append_blind_rows writes header columns up to and including label, opened in append mode only"
      pattern: "append_blind_rows"
    - from: scripts/blunder_check/miss_labels.py
      to: scripts/blunder_check/facepalm_features.py
      via: "excluded_game_ids(parse_labels) over the exclude files plus the append target"
      pattern: "excluded_game_ids"
---

<objective>
Extend the blind stratified sampler `scripts/blunder_check/miss_labels.py` (it produced label set 7) with a set-8 draw for SEED-261115-agg ("Decided with the owner (2026-11-16)"): about 45 rows where the depth-3 material input and the decaying mean disagree by a pawn or more, plus about 15 plain pure misses, appended blind to the SAME label file `reports/blunder-check/facepalm-labels.tsv` with an `--append-to` option that never touches existing bytes.

Purpose: the refit phase (decaying mean vs first-stable vs depth 3) needs labels on exactly the rows where the rules disagree; only 26 of 199 current rows do. The decaying-mean helper is written so the refit can reuse or move it.

Output: `scripts/blunder_check/decaying_mean.py` (pure helper), the extended sampler, tests, a dev smoke run writing only to `temp/`, and a SUMMARY carrying the exact prod command for the orchestrator. The prod draw itself is NOT part of this plan (it needs `bin/prod_db_tunnel.sh`; the orchestrator runs it).

Hard boundaries for the executor:
- Do not edit `app/services/facepalm_score.py`, `app/services/blunder_check_rules.py`, any FACEPALM_* constant, `scripts/blunder_check/fit_facepalm.py`'s model logic, or `reports/blunder-check/facepalm-labels.tsv`.
- Never append dev rows to the real label file; the dev smoke appends to a copy under `temp/`.
- DB access read-only (`make_readonly_engine`), analysis links never printed (existing rule).
- The refit, the "loses material" gate, WR-01 and WR-03 are the later phase's work, not this plan's.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/seeds/SEED-261115-agg-facepalm-material-across-depths.md
@scripts/blunder_check/miss_labels.py
@tests/scripts/test_miss_labels.py
@app/services/line_material.py

<interfaces>
Existing contracts the executor builds on (extracted at planning time, HEAD 78c3a5aa5):

- `app/services/line_material.py`: `LINE_LOSS_DEPTHS = (1, 3, 5, 7, 9)`; `LINE_MATERIAL_SLOTS = 9`; `material_at_depth(material: Sequence[int | None] | None, depth: int) -> int | None` (1-based depth into a 0-based list); `LineFacts.material_array() -> list[int | None]` (signed, positive = blunderer up; even slots are mid-exchange values); `LineFacts.mate_ply` = 1-based ply after which the BLUNDERER is mated (played line); `LineFacts.opponent_mate_ply` = ply after which the OPPONENT is mated, best move = ply 0 (best line).
- `app/services/blunder_check_rules.py`: `LINE_DEPTH = 3`, `LOSS_CAP = 5`, `MATE_LOSS = 5`, `FACEPALM_MISSED_CAP = 5`, `FACEPALM_MISSED_MATE = 5`, `FACEPALM_MISSED_FLOOR = None` (read-only imports).
- `app/services/facepalm_score.py`: `loss_feature(loss_3, mate_ply, *, loss_floor)` (MATE_LOSS when mate_ply <= LINE_DEPTH, else min(loss_3, LOSS_CAP) raised to loss_floor); `missed_feature(played_3, best_3, best_mate_ply, *, missed_floor, missed_cap, missed_mate)` (missed_mate when best_mate_ply <= LINE_DEPTH; 0.0 when best_3 or played_3 is None; else best_3 - max(0, played_3), floored, capped).
- `scripts/blunder_check/miss_labels.py`: `MissCandidate` (frozen, slots: game_id, ply, mover_rating, move_san, pinned_elo, played_3, best_3, missed, played_mate_ply, best_mate_ply, best_prob, pre_spread, material); `Selected(candidate, stratum)`; `build_candidate(raw, pre_board, played_uci, policy_fn, tally)`; `collect_candidates(rows, *, excluded_games, max_rating, policy_fn, tally)`; `_group_cells(pure, rng)` + `_fill_cells(cells, target, rng)` (set 7 pure-miss cells); `blind_row(n, row)` (uses MISS_SET_ID); `write_blind_tsv`, `write_key`, `summary_line`, `excluded_game_ids(paths)`; constants `MISS_SET_ID = "7"`, `MIN_STABLE_LINE_PLIES = 3`, `MAX_MOVER_RATING = 2000`, `DEFAULT_SAMPLE_SEED = 254`, `DEFAULT_EXCLUDE_LABELS = Path("reports/blunder-check/facepalm-labels.tsv")`, `DEFAULT_KEY_OUT = Path("temp/blunder-check/miss-labels-key.json")`; `_REPO_ROOT` bootstrap.
- `scripts/blunder_check/facepalm_features.py`: `parse_labels(path) -> list[LabelRow]` (csv.DictReader; LabelRow.label is "" for an unlabelled row; reads only n, set, link, label); `DB_TARGETS = ("dev", "prod")`; `EXIT_OK = 0`, `EXIT_MAIA_UNAVAILABLE = 3`.
- `scripts/blunder_check/fit_facepalm.py`: `_opt_float("") -> None`; `_exclusion_reason` returns `REASON_NO_LABEL` for label None; `score_extras` scores every label-None row; `TRAIN_SETS = ("1".."5", "7")`, `TEST_SET = "6"` (set 8 joins the fit only in the refit phase).

Real label file shape (`reports/blunder-check/facepalm-labels.tsv`, 230 rows, ends with "\n", n runs 1-20 then 31-240):
header `n set elo move link engine_drop expected_loss reply_loss practical_loss played_prob reply_spread line_loss3 mate3 label comment` (tab-separated, 15 columns). Set 7 rows as first appended (commit bad64bbe6) are 14 fields: n, 7, elo, move, link, then 9 tabs (8 empty hidden columns and the empty label), no comment cell, e.g. row 191 = `191<TAB>7<TAB>1778<TAB>Qe3<TAB>https://flawchess.com/analysis?game_id=499686&ply=62` followed by 9 tab characters. The owner later filled the label and, on 15 rows, added a comment (15 fields).
</interfaces>
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Tracer: decaying-mean helper -> disagreement classification -> set-8 draw -> byte-identical append to a label-file copy</name>
  <files>scripts/blunder_check/decaying_mean.py, scripts/blunder_check/miss_labels.py, tests/scripts/test_decaying_mean.py, tests/scripts/test_miss_labels.py</files>
  <read_first>scripts/blunder_check/miss_labels.py, tests/scripts/test_miss_labels.py, app/services/line_material.py, app/services/facepalm_score.py (lines 181-222 only: loss_feature, missed_feature), scripts/blunder_check/facepalm_features.py (parse_labels at lines 348-365)</read_first>
  <behavior>
    test_decaying_mean.py (weights 1, .5, .25, .125, .0625 sum to 1.9375):
    - DECAY_DEPTHS == (1, 3, 5, 7, 9) and DECAY_WEIGHTS == (1.0, 0.5, 0.25, 0.125, 0.0625), derived from DECAY_RATIO == 0.5.
    - decaying_mean of a constant series is that constant; {1: 2, 3: 4, others None} gives (2 + 0.5*4) / 1.5 = 2.6667 (normalised over known depths only); all None gives None.
    - loss_series: played odd slots -3, 0, 0, 0, 0 gives {1: 3, 3: 0, 5: 0, 7: 0, 9: 0}; material -9 caps at LOSS_CAP (5); positive material gives 0; played_mate_ply 2 gives MATE_LOSS at depths 3, 5, 7, 9 and the material value at depth 1; a None slot gives None.
    - gain_series: played all 0, best 9-slot array 1,1,1,1,10,10,1,1,1 gives {1: 1, 3: 1, 5: 5, 7: 1, 9: 1} (capped at FACEPALM_MISSED_CAP); best_mate_ply 4 gives FACEPALM_MISSED_MATE at depths 5, 7, 9; played slot None at a depth with a known best slot gives None there; played +2 and best +5 gives 3 (best - max(0, played)); best behind played gives 0 (floored).
    - Depth-3 parity with the shipped features for several known rows: loss_series(...)[3] == loss_feature(-played_3, mate_ply, loss_floor=0), and gain_series(...)[3] == max(0.0, missed_feature(played_3, best_3, best_mate_ply, missed_floor=None, missed_cap=FACEPALM_MISSED_CAP, missed_mate=FACEPALM_MISSED_MATE)).
    test_miss_labels.py (9-slot arrays built from 5 odd values, even slots copying the previous odd value):
    - disagreement_group, loss group: played odd -3,0,0,0,0 -> ("loss", "loss_early") (mean 1.548 vs 0); 0,0,-5,-5,-5 -> ("loss", "loss_late") (1.129 vs 0); 0,-3,0,0,0 -> ("loss", "loss_spike") (0.774 vs 3); 0,-3,-3,-3,-3 -> ("loss", "loss_other") (1.452 vs 3); 0,0,-4,-4,-4 -> None (0.903 < 1).
    - disagreement_group, miss group (played all 0): best odd 3,0,0,0,0 -> miss_early; 0,3,0,0,0 -> miss_spike; 0,3,3,3,3 -> miss_other; best odd 0,0,0,0,0 with best_mate_ply 4 -> miss_late; the seed's queen-trade best line 1,1,1,1,10,10,1,1,1 -> None (capped spike at depth 5 moves the mean only 0.516).
    - A row with a loss whose only disagreement is the gain (played odd -1 x5, best odd 0,3,3,3,3) -> None.
    - build_candidate on the existing MISS_FEN fixture: in the default mode it is unchanged; in mode "disagreement" it is kept (depth-3 pure miss) and carries played_material / best_material equal to the LineFacts.material_array() of both lines.
    - Tracer end to end: a fake pool with at least one candidate per loss and miss stratum plus depth-3 pure misses goes through stratify_disagreement, write_key and append_blind_rows into a tmp copy of the real label file filtered to sets 1-7; afterwards the new bytes start with the old bytes exactly, each appended line has n = old max n + 1, +2, ..., set "8", elo/move/link filled, then exactly 9 tab characters and nothing else (14 fields, no comment cell), parse_labels returns those rows with label "", and the key file maps the same n values to the hidden inputs and strata.
  </behavior>
  <action>
1. Create `scripts/blunder_check/decaying_mean.py`, a pure module (no I/O, no DB, no Maia) with a docstring naming SEED-261115-agg and stating that the later refit phase may reuse or move it. Constants: `DECAY_DEPTHS` = `LINE_LOSS_DEPTHS` imported from `app.services.line_material` (odd depths only: even slots are mid-exchange values, Phase 254 D-17); `DECAY_RATIO: float = 0.5` (fixed by the owner, not fitted); `DECAY_WEIGHTS` derived as DECAY_RATIO to the power of each depth's index. Functions with explicit types:
   - `loss_series(played_material, played_mate_ply) -> dict[int, int | None]`: per depth d in DECAY_DEPTHS, MATE_LOSS when played_mate_ply is not None and played_mate_ply <= d; else read the slot with `material_at_depth`; None when unknown; else min(LOSS_CAP, max(0, -material)).
   - `gain_series(played_material, best_material, best_mate_ply) -> dict[int, int | None]`: per depth, FACEPALM_MISSED_MATE when best_mate_ply is not None and best_mate_ply <= d; else None when either slot is unknown; else min(FACEPALM_MISSED_CAP, max(0, best - max(0, played))).
   - `decaying_mean(series: Mapping[int, int | None]) -> float | None`: sum of weight x value over known depths divided by the sum of those depths' weights; None when no depth is known.
   Import LOSS_CAP, MATE_LOSS, FACEPALM_MISSED_CAP, FACEPALM_MISSED_MATE from `app.services.blunder_check_rules` read-only. Note in the docstring that the per-depth gain is floored at 0 per the owner's spec while the shipped missed term has FACEPALM_MISSED_FLOOR None; that difference is the refit's to settle.
2. In `scripts/blunder_check/miss_labels.py` add named constants: `DrawMode = Literal["misses", "disagreement"]`; `DISAGREEMENT_SET_ID: str = "8"`; `DISAGREEMENT_MIN_PAWNS: float = 0.5` (threshold on |depth-3 value - decaying mean|); `SPIKE_MIN_PAWNS: int = 1` (peak height); `LOSS_STRATUM_QUOTAS` = loss_spike 6, loss_early 6, loss_late 6, loss_other 5 (23); `MISS_STRATUM_QUOTAS` = miss_spike 6, miss_early 5, miss_late 6, miss_other 5 (22); `PLAIN_MISS_TARGET: int = 15`. Group and stratum names are `Literal` types, never bare str (CLAUDE.md).
3. Extend `MissCandidate` with `played_material` and `best_material` (tuples of 9 `int | None`, default empty tuple so the existing set-7 test helpers keep working). `build_candidate` gains a keyword `mode: DrawMode = "misses"`: always store `facts.material_array()` / `best_facts.material_array()`; in "misses" mode the keep rule stays exactly as today (PURE_TYPE or MIXED_TYPE); in "disagreement" mode keep a row when its depth-3 material type is PURE_TYPE or `disagreement_group(...)` is not None (both reach the single Maia policy call, so every kept row has best_prob and pre_spread as set 7 did). `collect_candidates` passes `mode` through. The stable-line, rating and excluded-game filters are untouched.
4. Pure classification (testable on arrays): `series_shape(series)` returns, with this precedence: "spike" when an interior odd depth d in (3, 5, 7) with both odd neighbours known exceeds the larger neighbour by at least SPIKE_MIN_PAWNS; "early" when depth 1 > 0 and depth 3 == 0 (loss recovered / gain gone by depth 3); "late" when depths 1 and 3 are both 0 (the value only appears at depth 5 or later); else "other". `disagreement_group(played_material, played_mate_ply, best_material, best_mate_ply)` returns ("loss", loss_<shape of the loss series>) when the depth-3 loss is known and |loss[3] - decaying_mean(loss)| >= DISAGREEMENT_MIN_PAWNS; else ("miss", miss_<shape of the gain series>) when every known odd-depth loss is 0, the depth-3 gain is known and |gain[3] - decaying_mean(gain)| >= DISAGREEMENT_MIN_PAWNS; else None (a losing row whose only disagreement is the gain is not drawn; say so in the docstring). The "other" strata and the symmetric miss strata are planner discretion beyond the owner's named shapes (recovered by 3, appears at 5+, spikes); document that in a comment.
5. `stratify_disagreement(candidates, *, plain_target, seed)` returning a new frozen dataclass (rows, shortfall, unfilled per group, supply per stratum): sort by (game_id, ply), `random.Random(seed)`, pool disagreement candidates by stratum (computed from the arrays via disagreement_group), shuffle each pool, take each stratum's quota; then draw `plain_target` plain pure misses from the depth-3 PURE_TYPE candidates not already chosen, reusing `_group_cells` / `_fill_cells` exactly as set 7 (stratum = the set-7 cell label, group "plain"); finally shuffle all rows so the order never reveals a stratum. In this task a short stratum stays short (borrowing comes in Task 2).
6. Generalise `blind_row` with a `set_id` keyword (default MISS_SET_ID). Extend `write_key` with keyword `numbers` (the n values to key by; default 1..N) and an extended entry for set-8 rows: set, group, stratum, played_material, best_material, played_mate_ply, best_mate_ply, loss_3, loss_decay, gain_3, gain_decay, best_prob, pre_spread, material_type. Set-7 entries keep exactly today's keys (the existing exact-dict test must pass unchanged).
7. `append_blind_rows(rows, path, *, set_id) -> list[int]`: read the target's header line; require n, set, elo, move, link and label with link before label, else raise `AppendRefused` (a ValueError subclass); parse the existing rows with csv; next n = max existing n + 1; build each line by walking the header columns up to and including `label`: n, set, elo (mover_rating), move (move_san), link (LINK_TEMPLATE) get values, every other column (the hidden inputs and the label) is empty, columns after label (comment) are omitted, which reproduces the set 7 shape (14 fields, 9 tabs after the link). Open the file in append mode only (never rewrite); prefix a single newline only when the existing bytes do not end with one; return the assigned n values.
8. CLI wiring (thin, completed in Task 2): add `--mode` (choices from DrawMode, default "misses") and `--append-to PATH` in an argparse mutually exclusive group with `--out` (one of them required). In disagreement mode `_run` uses stratify_disagreement with `--pure-misses` as the plain target (PLAIN_MISS_TARGET when not given; keep 40 as the misses-mode default via a None default resolved per mode), then write_key with the n values, then append (or write the blind sheet for `--out`). Misses mode must behave byte-for-byte as before.
9. Tests: create `tests/scripts/test_decaying_mean.py` and extend `tests/scripts/test_miss_labels.py` per `<behavior>` (write each test first and watch it fail, then implement). For the tracer fixture, copy the header and every line of `reports/blunder-check/facepalm-labels.tsv` whose set cell is 1-7 byte-for-byte into tmp_path (so the test stays valid after the prod append adds set 8). Extend `test_help_exits_zero` to require `--append-to` and `--mode` in the help text.
  </action>
  <verify>
    <automated>uv run pytest tests/scripts/test_decaying_mean.py tests/scripts/test_miss_labels.py -x -q && git diff --quiet 78c3a5aa5 -- app/ reports/blunder-check/facepalm-labels.tsv</automated>
  </verify>
  <done>Both test files pass, including the tracer test proving a byte-identical prefix and 14-field set-8 rows read back by parse_labels with an empty label; `--help` lists --mode and --append-to; misses-mode tests are unchanged and green; app/ and the real label file are untouched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Expand the draw: borrowing and shortfall, summary, append guards, mode defaults, docstring</name>
  <files>scripts/blunder_check/miss_labels.py, tests/scripts/test_miss_labels.py</files>
  <read_first>scripts/blunder_check/miss_labels.py (as left by Task 1)</read_first>
  <behavior>
    - With ample supply in every stratum and enough plain pure misses, stratify_disagreement returns 60 rows: 23 loss rows matching LOSS_STRATUM_QUOTAS, 22 miss rows matching MISS_STRATUM_QUOTAS, 15 plain rows spread over the set-7 cells; shortfall empty, unfilled all 0.
    - A loss_late pool with 2 rows: loss_late takes 2, borrows 4 from the same group's spare rows (loss_other first, then the other loss strata in quota order), each borrowed row keeps its own stratum label; shortfall reports {"loss_late": 4}; the loss group still totals 23.
    - A group with too little supply in total stays short and is reported in unfilled (never padded from the other group or from the plain misses).
    - A candidate is never drawn twice (a chosen disagreement row is not in the plain pool).
    - Same seed and the same pool in reversed order give identical rows; a different seed gives a different order.
    - append_blind_rows twice with set "8" on the same file: the second call raises AppendRefused and the file bytes equal the bytes after the first call.
    - A target without a trailing newline: new bytes start with old bytes, followed by one newline and the appended lines.
    - A target whose header lacks `label`: AppendRefused, file unchanged.
    - main(["--db", "dev", "--mode", "disagreement", "--append-to", <absolute path of reports/blunder-check/facepalm-labels.tsv>]) returns EXIT_APPEND_REFUSED without starting Maia (monkeypatch maia_engine.start_maia to fail the test if called) and the real file's bytes are unchanged.
    - summary for a disagreement draw names supply per stratum, rows written per stratum, shortfall and unfilled per group, and contains no link.
  </behavior>
  <action>
1. Borrowing in stratify_disagreement, modelled on set 7's `_borrow`: a stratum that cannot fill its quota takes spare rows from the same group's other strata, the group's `*_other` stratum first, then the remaining strata in quota-declaration order; each borrowed row keeps the stratum it was drawn from (as set 7 does); record `shortfall[stratum]` = rows its own supply could not give and `unfilled[group]` = rows no stratum of the group could give. Plain misses keep set 7's `_fill_cells` shortfall/unfilled handling, merged into the same result under group "plain". Never pad one group from another.
2. Add `disagreement_summary_line(tally, draw)` (or extend summary_line with a mode switch): rows read, dropped per reason, stable, by depth-3 material type, supply per stratum, rows written per stratum, shortfall, unfilled per group. Print it in `_run` for disagreement mode; never print analysis links (existing rule).
3. Guards in `_run`, all checked BEFORE `maia_engine.start_maia` and before any DB connection, each returning a new named constant `EXIT_APPEND_REFUSED: int = 7` with a one-line stderr message (no paths of game data, no links): (a) `--db dev` with an `--append-to` path that resolves to `_REPO_ROOT / DEFAULT_EXCLUDE_LABELS` (dev rows must never land in the real label file); (b) the append target missing or its header failing the Task 1 header check; (c) the target already holding rows of the draw's set id (no double append; the operator restores the file with git before a rerun). Wrap the actual append in try/except AppendRefused -> EXIT_APPEND_REFUSED as well. Add the `--append-to` path to the excluded label files so its games are never redrawn.
4. Mode defaults (named constants): `DISAGREEMENT_SAMPLE_SEED: int = 261116` used when `--seed` is not given in disagreement mode (set 8 should come from a different TABLESAMPLE than set 7's seed 254; misses mode keeps DEFAULT_SAMPLE_SEED); `DEFAULT_DISAGREEMENT_KEY_OUT: Path = Path("temp/blunder-check/set8-key.json")` used when `--key-out` is not given in disagreement mode (set 7's key file must not be overwritten). Keep `--mixed` misses-mode only and say so in its help.
5. Update the module docstring: what set 8 draws and why (SEED-261115-agg, owner decision 2026-11-16), the strata and their precedence, the arithmetic consequence of the cap 5 and threshold 1 (an early loss or gain qualifies from 2 pawns, a depth-3 spike from 2 pawns, a late one only at the cap 5 held from depth 5 through 7, a spike at depth 5 or 7 alone never, so the seed's queen-trade example 1,1,1,1,10,10,1,1,1 is not a disagreement row), the append contract (append-only, set-7 row shape, n continues, double append refused, dev guard), and usage lines for the dev smoke (append to a copy under temp/) and the prod run. Keep every function at nesting depth <= 3 and well under the 100-line guidance; split by pipeline stage if a function grows.
6. Tests per `<behavior>`, written first. Keep every existing set-7 test unchanged and green.
  </action>
  <verify>
    <automated>uv run pytest tests/scripts/test_miss_labels.py tests/scripts/test_decaying_mean.py -x -q && git diff --quiet 78c3a5aa5 -- app/ reports/blunder-check/facepalm-labels.tsv</automated>
  </verify>
  <done>Borrowing, shortfall and unfilled reporting, summary line, the three append guards (dev + real file, bad header, existing set id) and the mode defaults are implemented and covered by tests; the guard test proves the real file is byte-identical and Maia never starts; existing set-7 tests pass unchanged.</done>
</task>

<task type="auto">
  <name>Task 3: Downstream tolerance of unlabelled set-8 rows, dev smoke on a temp copy, lint and type gates</name>
  <files>tests/scripts/test_facepalm_features.py, tests/scripts/test_fit_facepalm.py</files>
  <read_first>tests/scripts/test_facepalm_features.py (lines 120-180), tests/scripts/test_fit_facepalm.py (lines 560-700: write_synthetic_facts and test_facts_schema_run_prints_every_model_constant), scripts/blunder_check/fit_facepalm.py (lines 318-343 and 838-863)</read_first>
  <precondition>The dev database is up (`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`) and the maia-inference group is installed (`uv sync --group maia-inference`).</precondition>
  <action>
1. Real-label-file test: `test_parse_labels_on_the_real_label_file` asserts 230 rows and set ids exactly 1-7, so the orchestrator's prod append would turn it red. Change it so it holds before and after the append: the rows of sets 1-7 number EXPECTED_LABEL_ROWS (230, comment the meaning), the set ids include 1-7 and are a subset of 1-8, decided labels stay within {"1", "0", "0.5"}, and every set-8 row (if any) has a game_id and ply parsed from its link. Keep the first-row assertion.
2. fit_facepalm tolerance: planning found it already tolerates empty labels (`_opt_float("")` -> None -> REASON_NO_LABEL, scored by `score_extras`). Prove it for set 8 with a test in `tests/scripts/test_fit_facepalm.py`: write the synthetic facts table with the existing helper, append three rows copied from the extra row with n 241-243, set "8" and an empty label, run `fit_facepalm.main` on it like `test_facts_schema_run_prints_every_model_constant` does, assert exit 0, that the three rows are counted under the no-label exclusion (via load_features + split_usable) and that the report's "Extra rows" section names rows 241-243. Only if this fails, fix fit_facepalm.py minimally (skip or report unlabelled rows), with a comment at the fix site; the model logic and FACEPALM_* constants stay untouched.
3. facepalm_features tolerance: the Task 1 tracer test already shows parse_labels returns set-8 rows with label "". Confirm `gather_labels` passes them through unchanged (the existing multi-file test covers the code path; add an assertion only if not covered). Fix facepalm_features.py only if a set-8 empty-label row fails.
4. Dev smoke (real DB, real Maia, read-only), writing only under temp/: copy `reports/blunder-check/facepalm-labels.tsv` to `temp/blunder-check/set8-smoke-labels.tsv`, then run `uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db dev --mode disagreement --sample-percent 50 --max-rating 3000 --append-to temp/blunder-check/set8-smoke-labels.tsv --key-out temp/blunder-check/set8-smoke-key.json` (set 7's 100% dev smoke took about 5 minutes; 50% keeps this one inside the 10-minute tool limit; run it in the background if needed). Record the summary line. Dev holds few users, so shortfall is expected and fine. Then check the copy's prefix is byte-identical to the real file, that the appended lines have 14 fields with set 8 and empty hidden cells and label, and that the real file has no diff.
5. Gates: `uv run ruff format scripts/blunder_check tests/scripts`, `uv run ruff check scripts/blunder_check tests/scripts`, `uv run --group maia-inference ty check app/ tests/ scripts/` (zero errors; the group avoids the 3 phantom errors of a fresh worktree), and the four test files below.
6. SUMMARY (`.planning/quick/261116-mco-facepalm-label-set-8-sampler-disagreemen/261116-mco-SUMMARY.md`) must contain, verbatim and copy-pasteable, the prod commands for the orchestrator: start the tunnel with `bin/prod_db_tunnel.sh`, then `uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db prod --mode disagreement --append-to reports/blunder-check/facepalm-labels.tsv --key-out temp/blunder-check/set8-key-2026-11-16.json 2>&1 | tee temp/blunder-check/set8-prod-2026-11-16.log`; how to read the summary line; the rerun recipe if a group is unfilled (`git checkout -- reports/blunder-check/facepalm-labels.tsv`, then rerun with a larger `--sample-percent`, since a second append is refused); that the defaults are seed 261116 and sample 0.5% (set 7's 0.5% prod draw read 8,719 rows, 5,787 stable); that the appended rows plus the key are committed by the orchestrator (key stays in temp/, never committed); the dev smoke summary line; and the arithmetic note from the docstring (which strata are scarce under cap 5 / threshold 1) so the owner can judge the late and spike yield.
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/scripts/test_decaying_mean.py tests/scripts/test_miss_labels.py tests/scripts/test_facepalm_features.py tests/scripts/test_fit_facepalm.py -q && uv run ruff check scripts/blunder_check tests/scripts && uv run ruff format --check scripts/blunder_check tests/scripts && uv run --group maia-inference ty check app/ tests/ scripts/ && cmp -n "$(stat -c %s reports/blunder-check/facepalm-labels.tsv)" reports/blunder-check/facepalm-labels.tsv temp/blunder-check/set8-smoke-labels.tsv && git diff --quiet 78c3a5aa5 -- app/ reports/blunder-check/facepalm-labels.tsv</automated>
  </verify>
  <done>All four test files pass, ruff and ty are clean, the dev smoke exited 0 and its temp copy starts with the real file's exact bytes, the real label file and app/ are unchanged since 78c3a5aa5, and the SUMMARY holds the prod command, the rerun recipe and the dev smoke summary line.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| sampler -> committed label file | An operator script appends to a version-controlled file that holds 230 owner labels and comments |
| sampler -> prod/dev database | Read-only reads of games, flaws and stored lines through the prod tunnel or the dev DB |
| key file -> labelling sheet | Hidden inputs must not reach the owner while labelling (blind design) |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-mco-01 | Tampering | append_blind_rows on reports/blunder-check/facepalm-labels.tsv | high | mitigate | Append mode only, never a rewrite; tracer test asserts the new bytes start with the old bytes exactly; header check before writing; second append of set 8 refused with the file unchanged (test) |
| T-mco-02 | Tampering | dev rows in the real label file | medium | mitigate | `--db dev` plus an append target resolving to the real file returns EXIT_APPEND_REFUSED before Maia or the DB start (test via main); the dev smoke appends to a temp/ copy and the verify step proves the real file has no diff |
| T-mco-03 | Information disclosure | hidden inputs leaking into the blind rows | medium | mitigate | Appended rows carry only n, set, elo, move, link with every hidden column and the label empty (14-field shape test); scores, arrays and strata go only to the key file under gitignored temp/; final shuffle hides the stratum order |
| T-mco-04 | Tampering | database writes from the sampler | low | mitigate | Unchanged `make_readonly_engine` (read-only transactions, statement timeout, one connection); no new SQL |
| T-mco-05 | Information disclosure | analysis links in logs | low | mitigate | Summary line lists counts only; links are written to the label file and never printed (existing rule kept, summary test asserts no link) |
| T-mco-SC | Tampering | npm/pip/cargo installs | low | accept | No package is installed or added by this plan; uv uses the existing lockfile groups |
</threat_model>

<verification>
- `uv run pytest -n auto tests/scripts/test_decaying_mean.py tests/scripts/test_miss_labels.py tests/scripts/test_facepalm_features.py tests/scripts/test_fit_facepalm.py` passes.
- `uv run ruff check scripts/blunder_check tests/scripts` and `uv run ruff format --check scripts/blunder_check tests/scripts` are clean; `uv run --group maia-inference ty check app/ tests/ scripts/` reports zero errors.
- `git diff --quiet 78c3a5aa5 -- app/ reports/blunder-check/facepalm-labels.tsv` (no score, constant or label-file change).
- Dev smoke exited 0; `temp/blunder-check/set8-smoke-labels.tsv` starts with the real file's exact bytes and its appended rows are 14-field set-8 rows with empty hidden cells and label.
- `git diff --stat 78c3a5aa5` touches only the files in files_modified (plus fit_facepalm.py / facepalm_features.py only if Task 3 found a real failure, documented in the SUMMARY).
</verification>

<success_criteria>
- One command (`--mode disagreement --append-to reports/blunder-check/facepalm-labels.tsv`) draws about 60 blind rows (23 loss-disagreement, 22 miss-disagreement, 15 plain pure misses) and appends them as set 8 in the set-7 row shape with continuing n, without changing an existing byte.
- The decaying mean and the per-depth series exist once, in `scripts/blunder_check/decaying_mean.py`, with named weights, ratio, threshold and quotas; the shipped score is untouched.
- Shortfall and unfilled rows are reported per stratum and group, never silently padded.
- Downstream fit tooling treats set-8 rows with an empty label as unlabelled, and the real-label-file test survives the prod append.
- The SUMMARY gives the orchestrator a copy-pasteable prod command and a rerun recipe.
</success_criteria>

<output>
Create `.planning/quick/261116-mco-facepalm-label-set-8-sampler-disagreemen/261116-mco-SUMMARY.md` when done
</output>
