# Requirements: FlawChess — v1.28 Tactic Tagging

**Defined:** 2026-06-17
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report. v1.28 extends the flaw taxonomy with a "cause of error" tactic axis: *what kind* of tactical mistake each flaw was, compared against the player's opponents.

**Source:** SEED-039 (tactic-family cause-of-error flaw tags). Decision record: `.planning/notes/tactic-tagging-architecture.md`. Open detector questions: Q-010 (priority order), Q-011 (validation), Q-012 (per-motif `tactic_piece` semantic) in `.planning/research/questions.md`. Domain research skipped — the `/gsd-explore` session produced the equivalent.

## v1 Requirements

Requirements for the v1.28 milestone. Each maps to exactly one roadmap phase.

### Detector

The motif detection engine. Pure CPU — reads the already-stored refutation line; no new Stockfish pass.

- [ ] **TACDET-01**: The system detects a tactic-motif set by naming the pattern in the stored refutation line (`game_positions.pv` at `flaw_ply + 1`), reimplementing `ornicar/lichess-puzzler` `cook.py` heuristics in original code (no AGPL source copied). **The exact motif set is finalized during phase discussion** — provisional MVP starting point: `fork`, `pin`, `skewer`, `hanging-piece`, `back-rank` / `mate`, `double-check` (the cheap, reliable Tier-1 + mate/back-rank set per the architecture note).
- [ ] **TACDET-02**: A flawed move is tagged with at most one `allowed` motif, chosen by a fixed motif **priority order** when the refutation line contains several (the order defines the card's wording; Q-010).
- [ ] **TACDET-03**: The detector is **precision-first** — it tags only when confidence is high and leaves `tactic_motif` NULL otherwise (a false tag biases the you-vs-opponent rate comparison), validated against a hand-labeled per-motif fixture set drawn from our own prod flaws (Q-011).
- [ ] **TACDET-04**: Motif detection runs inside the single classify path — `classify_game_flaws` (eval-drain) and `backfill_flaws.py` (recompute) — for both the player's and the opponent's flaws, with no second engine evaluation.

### Storage

The materialized columns on `game_flaws`.

- [ ] **TACSCH-01**: `game_flaws` gains a nullable `tactic_motif` SmallInteger enum column (at most one motif per flaw; not a bitmask, not a join table), written at classify time (migration).
- [ ] **TACSCH-02**: `game_flaws` gains a nullable `tactic_piece` SmallInteger column (python-chess PieceType) captured broadly with a per-motif semantic (fork=attacker, hanging=victim, pin/skewer=line piece, mate=mating piece; ambiguous cases NULL; Q-012). Stored now; piece-level UI deferred.
- [ ] **TACSCH-03**: Existing `game_flaws` rows are backfilled with motif + piece for all self-eval'd games (those with `full_evals_completed_at` set, ~131k); lichess-eval-only games (no full eval, ~13.6k) keep `tactic_motif = NULL` until full-eval'd via the existing tier-3 idle fleet (no bespoke tooling).

### Comparison Stats

The you-vs-opponent aggregation.

- [ ] **TACCMP-01**: A backend endpoint returns the player's tactic-motif frequencies vs their opponents' as comparable **rates** (normalized per game / per 100 blunders, not raw counts), with the player/opponent split derived at query time via the existing `is_opponent_expr(ply, games.user_color)` helper (no `is_opponent` column).
- [ ] **TACCMP-02**: Each motif comparison carries a significance verdict computed with the project's existing Wilson-based chess-score significance utility (no parallel test invented), with a section-level sample gate below which the comparison is withheld.
- [ ] **TACCMP-03**: The comparison honors all existing game filters (time control, platform, rated, opponent type, recency, color) and severity, consistent with the other Library flaw surfaces.

### Frontend

The user-facing surface. Motif-level only in v1.28 (piece-level deferred).

- [ ] **TACUI-01**: Each flaw card displays its `allowed` motif as a family-colored chip with a definition popover, consistent with the shipped flaw-tag taxonomy chip pattern.
- [ ] **TACUI-02**: A you-vs-opponent **motif** comparison surface (reusing the v1.25 `MiniBulletChart` grid pattern: measure + CI + benchmark zone where available) with per-motif tooltips disclosing definition, sign convention, and the filter interaction.
- [ ] **TACUI-03**: The motif chips and comparison surface render correctly on mobile (responsive at 375px) with `data-testid` + ARIA parity, matching the project's browser-automation rules.

## v2 Requirements

Deferred to a future release. Tracked but not in this roadmap.

### Piece-level analytics

- **TACPIECE-01**: A piece-level you-vs-opponent breakdown (e.g. "you allow *knight* forks 2× more than your opponents"), surfaced only where per-(motif × piece) samples clear the Wilson floor. Data is captured in v1.28 (`tactic_piece`); the UI is deferred because `motif × piece_type` (~6×6 cells) fragments the already-thin per-user samples (Q-007 bimodal, median ~6 analyzed games).

### Standalone missed tactics

- **TACMISS-01**: True standalone `missed-X` detection (a tactic available across several plies where the opponent did *not* newly blunder to allow it — no adjacent opponent `allowed` row). Needs motif detection in the player's own PV and a second axis. Deferred until data shows it is common enough to matter. (The v1.28 `missed` view is already reconstructed for free as a join over adjacent opponent `allowed` rows + the existing `is_miss` tag.)

### Extended motif tiers

- **TACDET-EXT-01**: Tier-3 deep-PV motifs (`deflection`, `interference`, `attraction`, `intermezzo`, `x-ray`, `clearance`, `sacrifice`) and named-mate geometric patterns (`smothered`, `anastasia`, `arabian`, `boden`, …) beyond the MVP set. Deferred — fragile heuristics, lower coaching value per unit effort.

## Out of Scope

| Feature | Reason |
|---------|--------|
| New Stockfish / engine pass for motif detection | The refutation `pv` is already stored at `flaw_ply + 1` for both colors (v1.27); the detector is pure CPU. Adding an engine pass would re-expose the OOM history for no benefit. |
| `is_opponent` stored column / migration | Derivable from ply parity vs `games.user_color` via the tested `is_opponent_expr` helper (FLAWX-03 voided in v1.25). |
| Copying `cook.py` AGPL source | Reimplement the heuristics in original code; FlawChess is a hosted service and AGPL is viral over the network. Using the live lichess tagger's *output* as a reference label is acceptable; copying its *source* is not. |
| Bespoke lichess PV-gap backfill job | The ~13.6k lichess-eval-only games fill `pv` (and thus become taggable) as a side effect of normal full-eval via the existing tier-3 idle fleet. |
| Bitmask / join-table multi-motif storage | One `tactic_motif` per flaw matches the existing one-tag-per-family rule and keeps `GROUP BY` clean. |
| LLM narration of tactic motifs | Out of scope for v1.28; revisit once motif rates are validated in prod. |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TACDET-01 | TBD | Pending |
| TACDET-02 | TBD | Pending |
| TACDET-03 | TBD | Pending |
| TACDET-04 | TBD | Pending |
| TACSCH-01 | TBD | Pending |
| TACSCH-02 | TBD | Pending |
| TACSCH-03 | TBD | Pending |
| TACCMP-01 | TBD | Pending |
| TACCMP-02 | TBD | Pending |
| TACCMP-03 | TBD | Pending |
| TACUI-01 | TBD | Pending |
| TACUI-02 | TBD | Pending |
| TACUI-03 | TBD | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 13 ⚠️ (filled by roadmapper)

---
*Requirements defined: 2026-06-17*
*Last updated: 2026-06-17 after v1.28 milestone definition*
