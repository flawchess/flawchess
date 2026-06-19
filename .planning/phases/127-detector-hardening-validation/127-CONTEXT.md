# Phase 127: Detector Hardening & Validation - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Make tactic tags trustworthy. Three deliverables, all on the existing pure-CPU detector (`app/services/tactic_detector.py`), no engine pass:

1. **Depth** — every detector returns the ply at which its motif fires; store a new nullable `tactic_depth` SmallInteger on `game_flaws`.
2. **Validation harness** — read-only scoring of the detector against the lichess CC0 puzzle set (FEN + Moves + Themes), reporting **precision AND recall** per motif.
3. **Precision fix** — kill the deep-scan / loose-pin false positives in `detect_fork` / `detect_pin` (and the loose detectors generally).

De-risks Phases 128 (missed/allowed split) and 129 (filter UI). **Out of scope:** the missed/allowed column rename + second PV pass (128), the depth slider + filter UI (129), any new motifs.

</domain>

<decisions>
## Implementation Decisions

### Precision fix — the core insight (SC#3)
The deep-scan problem splits into two cases the detector can't currently tell apart: **Case A** (a real combination that culminates in a motif several plies deep — correct tag) and **Case B** (an incidental motif in a continuation after the refutation already won — wrong tag). Depth is a *noisy* proxy for wrongness (deep = a mix of A and B), so neither a hard depth-bound nor confidence-decay-by-depth is the right precision mechanism — both would also kill Case-A combinations and gut tier-3 (which is inherently multi-ply).

- **D-01:** **Relevance-gate every non-mate detector** — a detector fires only on a *real* instance (the motif wins material relative to where the line stood / is forcing), not on geometric presence alone. This directly fixes the loose `detect_pin` (`tactic_detector.py:308`, the literal *"pin exists … that's enough"*) and removes Case-B-at-any-depth and phantom-early hits.
- **D-02:** **Dispatch non-mate motifs by earliest depth** — `min(depth)` wins; the existing priority tiers become the **equal-depth tiebreak** only (a move that is simultaneously fork + discovered-attack, or fork + hanging, still resolves by priority). This is adaptive where a hard bound is not: a real deep combination with nothing shallower is still tagged at its true depth; an incidental deep hit loses to a shallower real motif. The relevance gate (D-01) is a *required companion* — without it an early junk hit (loose pin at ply 1) would beat a real deep fork.
- **D-03:** **Mates: keep D-07 dominance AND exempt mate tags from the depth filter.** Depth ≈ difficulty holds for material tactics but breaks for mates (a mate-in-3 is "deep" yet the most legible pattern for a beginner). So a forced mate in the line is always the tag (D-07 unchanged) and mate tags render regardless of the always-on depth filter threshold. The "shallow material win then deeper forced mate" conflict is rare in practice (the engine PV after a material blunder just wins; it rarely plays out a mate from a +9 position inside 12 plies), so keeping D-07 costs little and buys the clean "mates always show" rule.

### Depth semantics (SC#1)
- **D-04:** Store **raw half-move ply index from `flaw_ply+1`** (the detector loop index — already known, currently discarded). The player-facing unit (e.g. "your moves deep" ≈ ⌈ply/2⌉, beginner/intermediate/advanced presets) is a **Phase 129** decision; do NOT bake it into storage.
- **D-05:** Detector contract becomes `(fired, piece, confidence, depth)`; the dispatcher selects `min(depth)` with priority tiebreak. **SC#1's per-detector depth return IS the input depth-first dispatch needs** — the depth work and the precision work are one task, not two tracks.
- **D-06:** Because Phase 129 runs an **always-on** beginner/intermediate/advanced depth filter, stored depth is load-bearing as a difficulty proxy. The harness must validate **depth-vs-puzzle-`Rating` correlation as a first-class output** of SC#2 (promoted from the notes' "bonus sanity check"). If depth doesn't track puzzle difficulty, the presets are meaningless.

### Validation harness (SC#2, SC#5)
- **D-07:** **Committed stratified fixture.** A one-time `scripts/` selector reads the full CC0 lichess puzzle download, samples N puzzles per motif-theme (stratified also by Rating band for the depth-vs-difficulty check), and emits a committed fixture (~hundreds of rows). The CI test runs **offline** against the fixture: deterministic, reproducible, fast, no network. The selector is re-runnable to refresh.
- **D-08:** **Precision blocks, recall reports.** Per-motif **precision** floor is a hard CI gate (build fails if a shipped motif mis-tags above tolerance). **Recall** is measured and printed but **non-blocking** — low recall just means conservative under-tagging, which is acceptable ("leave NULL rather than mis-tag"); false positives bias the you-vs-opponent comparison and must block.
- **D-14 (LOCKED, user directive):** The harness/tagger tests live in a **separate directory excluded from the default pytest run**, exactly like the benchmark tests — they run the detector over hundreds of puzzles and are slow by design. Add a parallel `addopts` ignore to `pyproject.toml` (`[tool.pytest.ini_options]`, currently `--ignore=tests/scripts/benchmarks`) for the new dir, e.g. `tests/scripts/tagger/` (planner confirms exact name; keep it parallel to `tests/scripts/benchmarks`). They are **run on demand and in CI with an explicit path** (the explicit path overrides the ignore) — so the D-08 precision gate is a dedicated CI step targeting that path, **not** part of the default `uv run pytest -n auto` suite. This matches the established "exclude slow tests by directory" convention. The directory creation and the `--ignore=` entry must land **together** in Phase 127 (don't add a dangling ignore for a non-existent dir).
- **D-09:** **Tiered precision floor.** Core 8 + geometric + mates get a high blocking floor (≈ ≥0.90 — confirm exact bar during planning). **Tier-3 fuzzy motifs ship only if they clear the floor** against the puzzle set; any that don't are **suppressed** (stored-but-unsurfaced / NULL at query time via the existing `tactic_confidence` query-suppression lever) until a later phase hardens them. The harness's per-motif bars apply to the motifs we *claim to ship*.
- **D-10:** **Multi-label theme matching.** Lichess themes are multi-label — credit a precision hit when our motif is *in* the puzzle's theme set. Maintain an explicit motif→lichess-theme map and an **explicit list of motifs with no lichess equivalent** (e.g. `capturing-defender`, `self-interference`) marked unvalidated — same status as today's query-suppressed set.
- **D-11:** **No AGPL `cook.py` (SC#4).** Use the CC0 puzzle *data* only; the puzzle labels were generated by cook.py but the published dataset is CC0. Record this boundary in the harness docstring. The Phase 124 detector was reimplemented from plain-English pseudocode — keep it that way.
- **D-12:** **Supersede the circular fixtures (SC#5).** The CI precision/recall numbers come from the independent puzzle set, not the self-labeled `tests/services/test_tactic_detector.py` fixtures (which were bucketed by the detector itself — vacuous bars, recall never measured). Document the circularity as superseded.

### Re-backfill scope
- **D-13:** **Dev re-backfill in-phase; prod deferred to a runbook.** The precision fix makes the ~131k existing tags *actively wrong* (not merely depth-NULL), and those tags are already live in the Phase 126 comparison UI — so "do nothing" leaves known-wrong tags rendering. Phase 127's gate includes re-running the corrected detector over the tagged games **on dev** (this is also the real-data validation of the fix, beyond fixtures). **Prod** re-backfill is a documented runbook step executed outside the phase gate, mirroring Phase 125's D-01 deferral. New drains pick up the corrected code automatically. (No dev DB *reset* — backfill runs against the existing dev DB.)

### Claude's Discretion
- Exact precision floor value(s) per tier (D-09 says ≈0.90 for core; confirm during planning against measured fixture numbers).
- Fixture sample size N per motif-theme and Rating-band stratification granularity (D-07).
- The precise form of the relevance/forcing gate per detector (D-01) — material-delta vs forcing-line membership vs both; planner's call, validated by the harness precision delta (SC#3).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design notes (the source of this phase — read first)
- `.planning/notes/tactic-detector-precision-gaps.md` — the deep-scan / loose-pin / circular-fixture problem record; lichess CC0 vs AGPL cook.py boundary; key code line refs.
- `.planning/notes/missed-vs-allowed-tactic-design.md` — depth-as-difficulty rationale; how 127 depth feeds 128/129; player-facing unit deferral.
- `.planning/notes/tactic-tagging-architecture.md` — locked decisions: single `tactic_motif` column, `tactic_confidence` as query-time precision knob, motif set + tiers, named-mate fine-grained capture, severity gate, D-07 priority/mate dominance.

### Detector + integration code
- `app/services/tactic_detector.py` — `detect_fork:243`, `detect_pin:308` (the two named offenders), `detect_tactic_motif:1227` (dispatcher; tier order; returns 3-tuple today, becomes 4-tuple). Tier registries `_NAMED_MATE_REGISTRY` / `_GEOMETRIC_REGISTRY` / `_TIER3_REGISTRY`.
- `app/services/engine.py:99` — `PV_CAP_PLIES = 12` (PV depth; not a constraint).
- `app/services/flaws_service.py` — `classify_game_flaws`, `_run_all_moves_pass` (both colors), `_detect_tactic_for_flaw` (Phase 124/125 integration point — depth + gate land here).
- `scripts/backfill_flaws.py` — runs `classify_game_flaws`; the dev re-backfill path (D-13).
- `app/models/game_flaw.py` — add `tactic_depth` (nullable SmallInteger) alongside `tactic_motif` / `tactic_piece` / `tactic_confidence`.
- `app/repositories/query_utils.py:23` — `is_opponent_expr` (perspective; used by 128/129, not 127).
- `tests/services/test_tactic_detector.py` — the self-labeled fixtures superseded by the harness (D-12).
- `pyproject.toml` §`[tool.pytest.ini_options]` (lines ~35-42) — `addopts = "--ignore=tests/scripts/benchmarks"`; the harness dir gets a parallel `--ignore=` (D-14).
- `tests/scripts/benchmarks/` — the directory-exclusion precedent the harness dir mirrors.

### External data (not committed wholesale)
- lichess puzzle database — `database.lichess.org/#puzzles` (CC0): `PuzzleId, FEN, Moves, Rating, …, Themes`. Source for the one-time selector (D-07); only a stratified sample is committed.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`tactic_confidence` query-suppression** — already the mechanism for "tag→NULL at query time" (`AND tactic_confidence >= t`). D-09 suppresses sub-floor tier-3 motifs through this lever; no new suppression machinery needed.
- **Per-detector loop indices** — `detect_fork` already iterates `for i in range(0, len(moves), 2)`; the index *is* the depth (D-04/D-05). Depth extraction is near-free; the work is propagating it through the 4-tuple contract and the dispatcher.
- **`scripts/backfill_flaws.py` + `classify_game_flaws`** — the existing recompute path; the dev re-backfill (D-13) reuses it, no new script.

### Established Patterns
- **Detector = pure CPU, reads stored `pv` at `flaw_ply+1`**, `pov = board_after_flaw.turn`. No engine, no OOM exposure. Hardening stays inside this contract.
- **Single tag per flaw, clean `GROUP BY tactic_motif`** — the dispatch change (D-02) must preserve "exactly one winning motif"; it changes *which* motif wins, not the cardinality.
- **Nullable SmallInteger tactic columns on `game_flaws`** (`tactic_motif`/`tactic_piece`/`tactic_confidence`) — `tactic_depth` follows the same precedent (NULL on pre-existing rows until re-backfilled).

### Integration Points
- Detector signature change ripples: every `detect_*` → 4-tuple; the dispatcher `detect_tactic_motif` selection logic; the caller in `flaws_service._detect_tactic_for_flaw`; the `game_flaws` write path; an Alembic migration for `tactic_depth`.
- Harness is a new read-only test in a **default-excluded directory** (`tests/scripts/tagger/`, parallel to `tests/scripts/benchmarks/`) + `scripts/` selector + committed fixture. CI runs the precision gate as a **dedicated step with an explicit path** (overrides the `--ignore`), not the default suite (D-14). `pyproject.toml` `[tool.pytest.ini_options].addopts` gains a second `--ignore=` for the new dir.

</code_context>

<specifics>
## Specific Ideas

- The user plans an **always-on depth filter** with beginner / intermediate / advanced presets (Phase 129) — this is *why* mates must be filter-exempt (D-03) and why depth must be calibrated against puzzle Rating (D-06). The presets/thresholds themselves are 129, but they constrain what 127 stores and validates.
- A wrong, *visible* tag erodes trust in a stats product more than a missing one — the governing value behind precision-first gating (D-08) and the in-phase dev re-backfill (D-13).

</specifics>

<deferred>
## Deferred Ideas

- **Player-facing depth unit + beginner/intermediate/advanced thresholds** — Phase 129 (depth slider UI).
- **Prod re-backfill execution** — runbook step after 127 ships (D-13); lichess-only coverage fills in over time via the existing tier-3 idle fleet.
- **Hardening currently-suppressed tier-3 motifs** so they pass the precision floor and can be surfaced — future phase (D-09 ships them suppressed-until-validated).
- **Re-ranking by confidence** (drop fork below 0.8 so an also-detected pin wins) — explicitly rejected in the architecture note; would require multi-motif storage. Not revisited.

None of the above is in 127 scope.

</deferred>

---

*Phase: 127-detector-hardening-validation*
*Context gathered: 2026-06-19*
