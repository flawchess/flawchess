# Tactic-tagger review (2026-09-12)

**Scope:** `app/services/tactic_detector.py`, `app/services/forcing_line_gate.py`, the classify path in
`app/services/flaws_service.py`, and the CC0 fixture harness under `tests/scripts/tagger/`.
**Trigger:** user report that sacrifice / clearance (and others) are sometimes missed or tagged when they
should not be. The 2026-09-02 fixture report shows 0.998 micro-precision, so the fixture gate cannot be
where the problem shows.

**Methods** (scripts in `reports/tactic-tagger/review-2026-09-12-scripts/`):

1. **Oracle comparison.** Ran the AGPL reference `lichess-puzzler/tagger/cook.py` (local clone, analysis
   only, nothing copied into the repo) function-by-function against our standalone detectors on all
   26,649 fixture rows (train+test). Also compared cook's recomputed tags with the committed labels.
2. **Real-game replay.** Replayed every tagged flaw in the dev DB (7,610 flaws, 8,324 tags) through the
   detector with diagnostics: material trajectory, PV length, firing ply, and the tagging side's eval at the
   firing node read from the stored MultiPV blob. Hand-reviewed ~80 lines across motifs.
3. **Prod scale check.** Same eval-at-firing statistic via SQL on a 3 % sample of prod `game_flaws`
   (777k allowed / 383k missed tags total), read-only through the existing tunnel.
4. **Fix simulations.** Re-ran the fixtures with candidate detector changes, and re-scored the dev tags
   under candidate gate rules.

---

## 1. Headline

The detector is now a near-perfect clone of cook.py on puzzle lines. **The remaining quality problems are
not in the motif predicates; they are in which lines we run the predicates on.** Puzzles are curated so
the solver is always winning and every move is forcing. Real-game refutation PVs are neither, and the
forcing-line gate does not check the one thing lichess-puzzler always guarantees: that the tagging side is
actually winning where the tactic fires.

| Finding | Evidence | Size |
|---|---|---|
| **Tags fire on lines where the tagging side is losing** (often getting mated). Sacrifice and clearance are dominated by this. | Solver eval at firing node from stored blobs, dev + prod | prod: 78 % of allowed sacrifice, 47 % of clearance, 11 % of all allowed tags |
| **Forcing gate is skipped whenever the pre-flaw position carries `eval_mate`** (mate-ladder flaws). Those are exactly the positions where the opponent's best line "sacrifices" while losing. | `_classify_tactic_gated` skip; `pre_flaw_eval_cp IS NULL` join | prod: 77 % of allowed sacrifice tags, 50 % of clearance; dev: 24 % of all tags |
| **Even when gated, lost positions pass the only-move test trivially** (every alternative loses faster, so the 100 cp gap escape fires). | 222 losing tags in dev were gated and passed, incl. 60/60 missed sacrifices | structural |
| **cook's `sacrifice` is "material down ≥2 at any pov move ≥2"**. One third of cook's own sacrifice puzzles are zwischenzug shapes (deficit recovered on the very next move). In real games these read as nonsense. | fixture: 32 % of cook sacrifices recover next move; dev hand review | ~60k prod tags |
| **cook's `clearance` is weak geometry** (prior pov move vacated a square, a ray piece later crosses it). On engine continuations it matches king retreats, pawn pushes, piece shuffles. | 12/12 dev samples hand-reviewed: 3 real, 9 incidental | ~22k prod tags |
| **Five cook-port divergences** (deflection, fork gate, trapped-piece, discovered-attack, boden edge) plus a dead motif still in dispatch | oracle table (§4) | recall −4 % to −14 % on three motifs; 16 FPs |
| **Missed-orientation asymmetries**: no move stack → intermezzo can't fire at k=2, hanging-piece recapture exclusion off | prod: 188 allowed vs 6 missed intermezzo | recall |
| **discovered-attack stores depth k−1** (odd, defender ply) — 100 % of rows | known WR-02, never fixed | dispatch bias + gate exemption loss |

The fixture gate cannot see any of the first five rows: it contains no losing lines, no capped PVs and no
non-forcing tails.

---

## 2. Real-game evidence

### 2.1 Tagging side's eval at the firing node (prod, 3 % sample, allowed orientation)

Eval read from `allowed_pv_lines[depth]` (odd depths rounded up to the solver node), converted to the
solver's perspective. "losing" = cp < 0 or mate against the solver.

| motif | n | avg depth | mate for | ≥ +200 | 0..199 | losing | losing % |
|---|---:|---:|---:|---:|---:|---:|---:|
| hanging-piece | 6419 | 0.00 | 198 | 5497 | 101 | 260 | 4 % |
| mate | 4985 | 2.75 | 4904 | 2 | 0 | 0 | 0 % |
| fork | 3768 | 0.56 | 192 | 3189 | 105 | 66 | 2 % |
| **sacrifice** | 1795 | **5.16** | 31 | 185 | 60 | **1395** | **78 %** |
| pin | 1677 | 0.90 | 105 | 1302 | 47 | 92 | 5 % |
| discovered-attack | 860 | 1.63 | 22 | 723 | 18 | 40 | 5 % |
| **clearance** | 679 | **4.22** | 27 | 171 | 43 | **318** | **47 %** |
| attraction | 480 | 1.14 | 43 | 342 | 19 | 55 | 11 % |
| deflection | 428 | 3.12 | 41 | 266 | 39 | 57 | 13 % |
| discovered-check | 403 | 1.40 | 65 | 276 | 13 | 22 | 5 % |
| skewer | 376 | 3.04 | 62 | 226 | 28 | 38 | 10 % |
| promotion | 308 | 3.54 | 109 | 127 | 28 | 31 | 10 % |
| trapped-piece | 296 | 2.83 | 4 | 212 | 28 | 14 | 5 % |
| intermezzo | 188 | 2.39 | 11 | 93 | 26 | 43 | 23 % |
| capturing-defender | 169 | 2.66 | 3 | 95 | 33 | 17 | 10 % |

Missed orientation (same sample): sacrifice 528 tags, 170 losing (32 %); clearance 333, 51 losing (15 %);
everything else ≤ 5 %. Dev shows the same shape (allowed sacrifice 79 % losing, clearance 47 %).

Sacrifice is the 4th most common allowed tag (7.7 % of ~777k ≈ 60k rows), and 56 % of all losing-line
tags in prod are sacrifice tags.

### 2.2 Why losing lines get tagged

1. **Gate skip.** `_classify_tactic_gated` skips the whole forcing gate when `pre_flaw_eval_cp is None`
   ("mate-adjacent flaw plies carry eval_mate … RESEARCH A1, accepted"). A mate-ladder flaw (the mover had
   mate-in-3 and played a slower win) leaves the *opponent* getting mated; the opponent's best line sheds
   material, so `sacrifice`/`clearance`/`intermezzo` fire and are persisted ungated. Prod: 433 of 561
   sampled allowed sacrifice tags (77 %) have a NULL pre-flaw cp. Dev: 299 of 310 losing allowed sacrifice
   tags were gate-skipped this way.
2. **No winning requirement at the firing node.** lichess-puzzler only emits a puzzle when the solver's
   line is winning (`cook_advantage`, +200 cp floor or mate). Phase 144 (Bug B) exempted the firing node
   from `STILL_WINNING_FLOOR_CP` and now applies it only to the conversion tail. Nothing checks that the
   solver is ahead where the tactic lands.
3. **Only-move test is meaningless when losing.** `is_solver_node_forced` passes on a ≥100 cp gap between
   best and second-best. In a lost position the alternatives usually lose faster, so the gap is large and
   every solver node "is forced". Dev: all 60 losing missed-sacrifice tags were gated and passed.

Typical allowed-sacrifice rows (dev, all with solver eval < −500 or mate against):

```
g819837 ply52  flaw Nxe3+   line: Qxd1+ Kxd1 [g6] Qf8+ Kc7 Qxa8 …     solver: mate in 4 AGAINST
g378077 ply52  flaw Qe2     line: Qxe1+ Qxe1 [h5] Qe4 g5 Kh2 h4 …      solver −749
g655040 ply83  flaw Qa2+    line: Kf3 Qd5+ Ke2 Qb5+ … [Kh3] Q5g7      solver mate in 6 AGAINST, depth 10
```

"You allowed a sacrifice" here means: the opponent was winning, made a mate-ladder mistake, and your
best defence still loses material. That is not a tactic the user allowed.

### 2.3 Sacrifice: the predicate itself

cook: `material_diff(after pov move k) − material_diff(start) ≤ −2` for any pov move k ≥ 2, no opponent
promotion. No recovery, no compensation, no depth limit.

* Fixture: of 5,118 cook-sacrifice puzzles, **1,655 (32 %) recover the deficit on the very next pov move**
  (opponent captures, pov inserts a check/threat, pov recaptures). cook and lichess call these
  "sacrifice"; users call them zwischenzugs. 45 % of fixture sacrifices fire on the last pov move of the
  puzzle line; in a 12-ply engine PV that last move is the cap.
* Prod: average depth 5.16 (fork 0.56, pin 0.90). 65 % of dev sacrifice tags fire at depth ≥ 4, i.e. two
  or more full moves into the engine continuation. Under depth-primary dispatch, sacrifice can only win
  when nothing shallower fired, so it is by construction the residual "material swing that matched no
  geometry".
* Hand review of the 58 dev allowed-sacrifice tags whose solver eval is ≥ +200 or mate: roughly half are
  real (Bxh6 gxh6 Rd1; Rxh5 gxh5 Qxh5 → mate; Rh3 queen trap) and half are delayed recaptures
  (`Nh4 Nxh4 [Bb4+] Bd2 Bxd2+ Qxd2 Qxh4`, `Re3 Rxe3 [Rf1+] Kh2 Bxe3`).

Simulation on the 697 dev sacrifice tags: requiring solver eval ≥ +100 (or mate for) at the firing node
**and** the deficit still present after the next pov move leaves **54 survivors**; sampled survivors are
genuine sacrifices (queen sac Qxg2, exchange sacs leading to mate, Bxf6 gxf6 Qh5 fxe5 Qxh7+ …). On the
fixture the persistence rule alone drops 32 % of cook's sacrifice rows, so the harness would report lower
recall on purpose.

### 2.4 Clearance

cook: pov moves a ray piece to an empty square; the prior pov move came from that square or from a
square on the ray; the prior move went to an empty square or landed in a bad spot; not a promotion; some
check bookkeeping. Nothing requires the cleared line to be *used*.

Dev hand review, 12 random allowed-clearance tags: 3 real (`Na6+ Ka8 [Qc7]`, `Rc8→g8+ … [c8=Q]`,
`d4 Ne2 [Bb3]`), 9 incidental: king steps off a square and a rook/queen retreats to it (`Kh1 … Kg2 e3
[Rh1]`, `Kd1 c4 [Qd2]`, `Kh4 Qd3 [Rg4]`), pawn advances and a rook occupies the vacated square (`f5 Rh2
[Rf6]`), knight moves and the bishop takes its square (`Nxe6 fxe6 [Bg5]`), bishop retreats and the queen
takes its square (`Bh8 Rac7 [Qf6]`). Half the sample had the solver losing.

Clearance has the same "residual" property as sacrifice: average depth 4.2, 51 % at depth ≥ 4.

### 2.5 Other real-game findings

* **Missed orientation has no move stack.** `_detect_tactic_for_flaw("missed")` builds
  `chess.Board(fen)` bare, so (a) `detect_intermezzo`'s k=2 branch always returns False and (b)
  `detect_hanging_piece`'s recapture exclusion never runs. Prod: 188 allowed vs 6 missed intermezzo
  (31×); dev: 33 of 302 missed hanging-piece tags are plain recaptures cook would exclude. The opponent's
  previous move is available (`positions[n-1].move_san`, `fen_map[n-1]`).
* **discovered-attack depth is k−1 on 100 % of rows** (361/361 dev, all odd). Known since 131-REVIEW
  WR-02, never fixed. Effects: (1) in depth-primary dispatch a discovered attack at k=2 reports depth 1 and
  beats a fork/skewer at the same k; (2) `_is_forced_mate_firing` reads a defender placeholder on slim
  blobs, so the mate exemption is lost; (3) the UI depth/difficulty is one ply too shallow.
* **`self-interference` (int 14) is still in `_TIER3_REGISTRY`.** It fires standalone on 613 fixture
  rows (cook's `self_interference` is already folded into our `interference`), so it can win depth-primary
  dispatch and persist a motif that maps to no family and never renders. Prod sample: 4 rows ≈ 130 total.
  One fixture row is stolen the same way.
* **Ungated tags still exist**: 273 of 5,602 dev allowed tags have no blob (pre-Phase-142 rows), and 160
  of 788 missed mates.
* **Every real-game PV is capped at 12 plies** (`PV_CAP_PLIES`), so all tier-3 scanners run over six
  engine moves of continuation. Puzzle lines are 3–7 plies. The scanners were validated on the short
  distribution only.

---

## 3. Fixture harness: what it does and does not measure

* **Precision is saturated because it measures cook replication.** Dispatch-winner vs cook's own
  recomputed tags: every shipped motif agrees with cook on ≥ 99 % of wins. The 2026-09-02 numbers are
  real, but "P(test)=1.000 for sacrifice" only says our `sacrifice` fires where cook's fires.
* **Label drift is small except for one theme.** cook's recompute matches the committed labels within
  ~1 % for every theme except `discoveredCheck`: cook (this clone) never emits it (`TagKind` lacks it);
  only 1,585 of 2,854 labelled rows satisfy `cook.discovered_check`. Our `discovered-check` port is
  therefore validated against a label whose source is not cook (likely lila-side or crowd voting), which
  explains its 0.95 precision and the unexplained FN mass. Also `underPromotion` has 24 labels cook
  rejects (mating non-knight promotions).
* **The train/test split protects against one failure mode only** (overfitting predicates to puzzles). It
  cannot detect the real-game failure modes above; a green gate after any of the fixes below is
  necessary, not sufficient.

---

## 4. Cook-port divergences (fixture oracle, standalone detector vs cook function)

| motif | both | cook only | ours only | cause | fix |
|---|---:|---:|---:|---|---|
| deflection | 1844 | **297** | 0 | promotion branch: we require `same_file AND from∈attacks(orig)`; cook accepts `square∈attacks(orig) OR (promotion AND …)`. All 297 are promotion lines (`d1=Q`, `c8=Q`). | restore the OR |
| fork | 2864 | **130** | 0 | our D-01 "relevance gate" (`material_at_end < material_at_start → skip`) is not cook. All 130 are sac-then-mate lines. Removing it reproduces cook exactly; FP vs label goes 21→32, all 11 on rows where cook itself fires and voters removed the label. | delete the gate |
| trapped-piece | 956 | **107** | 0 | documented "precision-first" deviation: immobile attacked piece → not trapped. Reverting to cook (immobile ⇒ trapped) reproduces cook exactly with **0 new FPs vs label**. | revert |
| discovered-attack | 2732 | 0 | **16** | cook `return False` on the first pov recapture (kills the detector); ours `continue`s and fires later. 16 FPs vs label. | mirror cook |
| boden / double-bishop | 602 / 5 | – | 6 wins as double-bishop that cook calls boden | file comparison edge when a bishop sits on the king's file | trivial |
| self-interference (14) | 562 | 2 | 51 | dead motif, see §2.5 | remove from registry |
| promotion | 5331 | 30 | 0 | cook `promotion` includes non-queen promotions and mating under-promotions; ours splits | fine (mates win anyway) |
| capturing-defender | 896 | 3 | 0 | cook's checkmate branch not ported | fine (tier 1 wins) |
| named-mate order | – | – | – | ours: … arabian → boden → dovetail → **back-rank** → mate; cook: smothered → **back-rank** → anastasia → … | no disagreement observed; note only |

Everything else (hanging-piece, pin, skewer, double-check, discovered-check, attraction, intermezzo,
x-ray, interference, clearance, sacrifice, en-passant, under-promotion, all named mates) matches cook on
every row.

---

## 5. Recommendations (prioritised)

### P1 — Require the tagging side to be winning at the firing node (highest impact, small change)

In `apply_forcing_line_filter` / `_classify_tactic_gated`:

1. Read the solver-perspective eval at the firing node (`line[depth rounded to even]`; use `bm` then
   `b`). Require **mate for the solver, or cp ≥ floor**. Suggested floors: `STILL_WINNING_FLOOR_CP` (+200)
   for tier-3 and move-type motifs, `0` (not losing) for tier-1/2 geometric motifs. Rationale: lichess-
   puzzler never produces a puzzle from a losing line; a fork that wins a piece while still lost is
   arguably still coachable, a "sacrifice" while lost never is.
2. **Never skip the gate because `pre_flaw_eval_cp` is None.** Derive the already-winning reject from
   `eval_mate` (mate for the solver before the flaw ⇒ already winning ⇒ reject unless the tag is a mate),
   and run the rest of the gate on the blob as usual. Also apply the node-0 eval check so a losing
   refutation is rejected even when the blob is missing (fall back to `positions[n+1].eval_cp` /
   `eval_mate`).

Expected effect (dev simulation, floor +100): −324 of 551 allowed sacrifice, −69 of 161 clearance, −21 of
64 intermezzo, −24 of 109 deflection, −44 of 1213 hanging-piece, −24 of 923 fork. Prod: roughly 2,500 of
every 23,000 allowed tags.

Then re-run `scripts/retag_flaws.py` (offline, no engine) over prod.

### P2 — Tighten `sacrifice` beyond cook

* **Persistence:** the deficit must still be ≥ 2 after the *next* pov move (or the line ends). This drops
  the delayed-recapture shape (32 % of cook's own sacrifice puzzles) that users read as nonsense. Combined
  with P1 the 697 dev sacrifice tags shrink to 54, and the survivors are real sacrifices.
* **Depth cap** for sacrifice and clearance (≤ 4): both are tier-3 residuals with average depth > 4; a
  material swing two full moves into an engine continuation is not the point of the refutation.
* Document this as a deliberate divergence from cook in `precision_floors.py`; fixture recall will drop
  and the report should say why.

### P3 — Strengthen or suppress `clearance`

cook's predicate is not usable on engine continuations. Either suppress it (it is 2.9 % of allowed tags
and the hand review found ~25 % real), or add: the vacating move is not a king or pawn move; the ray
piece's move gives check or attacks a higher-value/hanging piece (the cleared line is *used*); depth ≤ 4;
P1 winning floor. Re-measure on the fixture (cook clearance puzzles satisfy "line is used" almost by
construction) and on a hand-labelled real-game sample before shipping.

### P4 — Port fixes (fixture-verified, zero precision cost)

1. Deflection promotion OR-branch (+297 recall).
2. Remove fork's D-01 relevance gate (+130).
3. Revert trapped-piece empty-escape deviation (+107).
4. Discovered-attack: `return` instead of `continue` on a recapture (−16 FPs).
5. Remove `self-interference` from `_TIER3_REGISTRY` (keep the int for existing rows).
6. Fix discovered-attack depth to `k` and re-tune the one hand-confirmed fixture the WR-02 note mentions.
7. Boden/double-bishop file-comparison edge.

All of these are one-line changes; the floors already lock against regression.

### P5 — Missed-orientation parity

Build `board_before` in `_detect_tactic_for_flaw("missed")` from `fen_map[n-1]` plus the opponent's move
so the move stack carries the previous move, exactly as the allowed pass does. Decide explicitly whether
cook's recapture exclusion should apply to "missed hanging-piece" (a missed recapture is a real flaw but a
different message); today it applies to one orientation by accident.

### P6 — A real-game gate next to the fixture gate

The fixture gate is necessary but blind to every finding in §2. Add a small hand-labelled real-game set
(~150 tags stratified by motif and orientation, drawn from prod with `retag_flaws.py`, labelled
real/incidental/wrong) and score it in the report alongside the fixture. SEED-064 deferred exactly this;
the data now shows it is where the errors live. Cheap interim proxy: add a "solver eval at firing node"
column to `tactic_tagger_report.py` computed from the dev DB blobs.

### P7 — Harness hygiene

* Document that `discoveredCheck` labels are not cook output; consider scoring `discovered-check` against
  `discoveredAttack ∪ discoveredCheck` or against cook's recomputation.
* Record in `precision_floors.py` that the oracle comparison script exists and what "matches cook" means
  for each motif, so future "precision passes" do not re-introduce non-cook gates (D-01 fork gate,
  trapped-piece exclusion) that cost recall for no measured gain.

---

## 6. Reproduction

```bash
# 1. Oracle comparison (needs the local lichess-puzzler clone; ~3 min)
uv run python reports/tactic-tagger/review-2026-09-12-scripts/oracle_compare.py

# 2. Dev-DB replay with diagnostics (dev Postgres up; ~1 min)
uv run python reports/tactic-tagger/review-2026-09-12-scripts/dev_probe.py
```

Prod numbers came from read-only SQL on `game_flaws TABLESAMPLE SYSTEM (3)` via the prod tunnel; the
queries are reproducible from the eval-at-firing expression in §2.1 (`allowed_pv_lines -> (depth + depth % 2)`,
solver is white iff `ply % 2 = 1` for allowed, `ply % 2 = 0` for missed).
