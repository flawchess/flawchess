# Phase 132: Tier-3 tactic precision hardening via cook.py predicate alignment - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Raise per-motif tactic-tag **precision** toward >0.9 on the held-out TEST split (recall
ungated, precision-first) for the **Tier-3** motifs by faithfully reimplementing
`ornicar/lichess-puzzler`'s `tagger/cook.py` relational predicates — replacing the current loose
`met >= N` voting detectors with cook's exact AND-chain predicates. Same methodology that lifted
Tier-2 in Phase 131; this is its Tier-3 sequel.

**In scope (detector-internal predicate alignment only):**
- Full cook-fidelity port of the six firing/near-firing Tier-3 motifs: `deflection` (0.21 TEST,
  the single biggest FP source at 991 FP), `clearance` (0.37), `capturing-defender` (0.25),
  `attraction` (0.04), `intermezzo` (0.17), `x-ray` (0.00).
- `sacrifice` (cook lines 184–191, a material-diff co-tag, NaN today) is **included** in the
  port-then-suppress sweep (best-effort; likely ends suppressed — D-02).
- Any motif still <0.9 at full cook fidelity is **suppressed** via the existing
  `tactic_confidence` query-suppression lever, not shipped (mirrors Phase 131 D-02/D-11).
- Dev re-backfill of the `game_flaws` tactic columns via `scripts/backfill_tactic_tags.py`
  (real-data validation — D-04).

**Out of scope:**
- **`interference` (1.00 TEST)** — already faithfully ported; lock against regression, **no
  detector work** (it is the existence proof a Tier-3 motif reaches the bar via a faithful port).
- **Dispatch rework** — Phase 131 already inverted dispatch to shallowest-tactic-wins; this phase
  changes detector internals only, never the dispatcher.
- **Tier-1 / Tier-2 motifs** — hardened in Phase 131, untouched here.
- **Prod re-backfill** — tactic tagging is **not yet deployed to prod**, so there are no
  live-wrong-tags to fix and no prod re-backfill runbook (unlike Phase 131 D-12).
- ML (rejected upstream). No new motifs. No dev DB reset. No new puzzle data (CC0 fixtures exist
  for every in-scope motif).

</domain>

<decisions>
## Implementation Decisions

The user delegated all gray-area calls to Claude ("you decide") with two explicit directives:
**port as much as possible with a best-effort attempt**, and **run a dev re-backfill using
`scripts/backfill_tactic_tags.py`**. Decisions below honor those directives and carry forward the
Phase 131 playbook.

### Effort policy — best-effort full port for ALL in-scope motifs
- **D-01:** **Attempt the full cook port for every in-scope Tier-3 motif, suppress any that misses
  0.9 on TEST.** This is Phase 131 D-02 parity, reaffirmed by the user's "port as much as possible"
  directive. Do the complete relational rebuild even for the deeply-broken motifs (attraction 0.04,
  x-ray 0.00, intermezzo 0.17), then measure on the held-out TEST split. The full port is the
  precision **ceiling** — we want to know the real ceiling before suppressing, not pre-suppress on
  assumption. Honest expectation: several of these will plateau below 0.9 and end suppressed; that
  is an accepted, endorsed outcome (Tier-3 is only ~1.8% of tag volume, so a suppressed motif costs
  little). The highest-ROI targets are `deflection` (kill its 991 FP — the biggest single
  false-positive source across the whole detector) and `clearance` (0.37, meaningful volume).

### `sacrifice` scope
- **D-02:** **Include `sacrifice` in the port-then-suppress sweep.** Although it is a material-diff
  *co-tag* (cook lines 184–191), not a geometric motif, and never fires for us today (NaN), the
  best-effort directive and the "know the real ceiling" principle (D-01) argue for porting it and
  measuring rather than excluding by assumption. Likely outcome: ends suppressed. If a faithful
  port proves structurally impossible to score under our single-winner post-dispatch harness (it is
  a co-tag, so it rarely *wins* dispatch), document that and leave it suppressed — do not burn
  effort fighting the harness for a co-tag.

### `x-ray` depth risk (folded into D-01)
- **D-03:** **Attempt `x-ray`'s full port; suppress honestly if it plateaus.** TP-depth is 8.0 vs
  `PV_CAP_PLIES=12`. cook runs on a *curated puzzle solution*; we run on a *raw Stockfish PV* that
  can diverge from cook's clean relational chains deep in the line, so x-ray may stay <0.9
  regardless of port fidelity. Per D-01 we still attempt the full port and let TEST decide —
  full-port-then-suppress handles it honestly. **Flagged wasted-effort risk:** if early porting
  shows the PV-divergence ceiling is real and unrecoverable, the planner/executor may cut x-ray
  short and suppress rather than over-invest. Best-effort, not infinite-effort.

### Harness scoring basis
- **D-05:** **Keep post-dispatch winner scoring as the sole shipping gate.** Confirmed:
  `scripts/tactic_tagger_report.py:193` scores the post-dispatch single winner from
  `detect_tactic_motif` (theme-intersection multi-label credit), NOT standalone detector firing.
  Since Phase 131 already shipped shallowest-wins dispatch, the post-dispatch number IS what users
  see — the correct precision-first gate. **Consequence to state explicitly:** deep Tier-3 motifs
  (depth 2.3–8.0) only win dispatch when nothing shallower fires, so their measured volume is small
  (~1.8% of all tags) and per-motif TEST precision can be noisy at small n. This **bounds the ROI
  ceiling** of the whole phase and should be stated up front. A standalone-firing diagnostic view
  is permitted *during tuning* to isolate predicate quality from dispatch effects, but it is NOT a
  shipping gate — the gate stays post-dispatch.

### Re-backfill scope
- **D-04:** **Dev re-backfill via `scripts/backfill_tactic_tags.py`; no prod re-backfill.** The
  user named this purpose-built script (over Phase 131's `backfill_flaws.py`): it refreshes ONLY
  the 8 tactic columns through the same `_detect_tactic_for_flaw` kernel the live drain uses
  (parity guaranteed), in PK-ordered pages loading only each flaw's ply / ply+1 positions, and
  UPDATEs only rows whose tags changed — far cheaper than a full delete-and-reinsert flaw rebuild.
  This doubles as the real-data validation of the port beyond the CC0 fixtures. **No prod
  re-backfill** — tagging is not in prod, so there are no live-wrong-tags (the key divergence from
  Phase 131 D-12). **No dev DB reset.** The CC0 puzzle fixture harness remains the authoritative
  precision signal either way.

### Carried forward from Phase 131 (LOCKED — do not re-litigate)
- **TEST + ΔP gate, never TRAIN** (131 D-11): a motif ships only if it clears >0.9 puzzle precision
  on the held-out TEST split; recall is ungated (whatever falls out). Use
  `scripts/tactic_tagger_report.py --check-goals` (raise GOALS to precision 0.9 for in-scope Tier-3
  motifs) as the measurement/regression harness.
- **AGPL boundary** (131 D-10): reimplement every predicate from plain-English pseudocode; copy NO
  `cook.py` source (AGPL-3.0). A Tier-3 extension of the cook-alignment note (per-motif pseudocode
  for deflection/clearance/attraction/intermezzo/x-ray/capturing-defender/sacrifice) likely needs
  authoring as a research deliverable — the existing note covers Tier 1+2 only.
- **Suppression mechanism** (131 D-02): reuse the existing `tactic_confidence` query-suppression
  lever; no new suppression machinery.
- **Shallowest-wins dispatch** (131 D-05/D-06/D-07): already shipped; this phase consumes it and
  must NOT change it. Single tag per flaw, clean `GROUP BY tactic_motif` — preserve cardinality.
- **`interference` regression lock** (1.00 TEST): assert its floor; no detector edits.

### Claude's Discretion
- Per-motif suppression vs ship decision — driven by the TEST number at full port; no pre-judgment.
- Whether/how to surface a standalone-firing diagnostic during tuning (D-05) — planner's call.
- Exact effort cutoff for x-ray if the PV-divergence ceiling proves real (D-03).
- TRAIN/TEST split mechanics and ΔP reporting format — already established in the Phase 127/131
  harness; reuse as-is.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source — read first
- `.planning/notes/tactic-tagger-cook-alignment.md` — cook↔ours index convention + the shared
  utility ports. **Covers Tier 1+2 only** — its "Not covered here" section explicitly defers Tier-3
  (cook.py lines 184–820, sequence-relational). A Tier-3 per-motif pseudocode extension likely needs
  authoring during research.
- `.planning/phases/131-tactic-precision-hardening-cook-alignment/131-CONTEXT.md` — the proven
  playbook: full-port-then-suppress (D-02), TEST+ΔP gate (D-11), AGPL boundary (D-10),
  shallowest-wins dispatch (D-05/06/07), `tactic_confidence` suppression lever.

### Prior tactic phases (decisions that constrain this phase)
- `.planning/phases/127-detector-hardening-validation/127-CONTEXT.md` — depth semantics, the
  validation harness, precision-blocks / recall-reports (D-08), tiered precision floor (D-09),
  multi-label theme matching (D-10), AGPL boundary (D-11), dev-in-phase re-backfill (D-13).
- `.planning/notes/tactic-tagging-architecture.md` — single `tactic_motif` column,
  `tactic_confidence` as the query-time precision knob, motif set + tiers, severity gate, dispatch
  dominance.

### Detector + integration code
- `app/services/tactic_detector.py` — `detect_deflection` (loose "3 of 5" voting),
  `detect_attraction`, `detect_intermezzo`, `detect_x_ray`, `detect_clearance`,
  `detect_capturing_defender`, `detect_sacrifice`, `detect_interference` (the 1.00 lock),
  `_TIER3_REGISTRY`, `detect_tactic_motif` (the shallowest-wins dispatcher — read, do not edit).
- `app/services/flaws_service.py` — `_detect_tactic_for_flaw` kernel (shared by live drain and the
  re-backfill script — parity source of truth).
- `app/services/engine.py` — `PV_CAP_PLIES = 12` (the x-ray depth-risk ceiling, D-03).
- `app/models/game_flaw.py` — `allowed_tactic_*` / `missed_tactic_*` columns (8 total).

### Validation tooling
- `scripts/tactic_tagger_report.py` — `--check-goals` mode (raise GOALS to 0.9 for in-scope Tier-3
  motifs, recall ungated); scores the **post-dispatch winner** at line 193 (D-05); `/tactic-tagger-report`
  skill for the full per-motif table.
- `scripts/backfill_tactic_tags.py` — the dev re-backfill path (D-04); tactic-columns-only refresh
  via the `_detect_tactic_for_flaw` kernel, PK-ordered pages, change-only UPDATEs.
- `reports/tactic-tagger/tactic-tagger-2026-06-22.md` — the precision baseline this phase improves on
  (deflection 0.21 / clearance 0.37 / capturing-defender 0.25 / intermezzo 0.17 / attraction 0.04 /
  x-ray 0.00 / interference 1.00 / sacrifice NaN on TEST).
- lichess CC0 puzzle fixture (already committed; `database.lichess.org/#puzzles`) — ground truth.
  No new puzzle data needed (n(test): deflection 501, attraction 677, intermezzo 324, x-ray 274,
  clearance 334, capturing-defender 285, interference 257, sacrifice 1377).

### AGPL reference (read for pseudocode, never copy source)
- `/home/aimfeld/Projects/Python/lichess-puzzler/tagger/cook.py` + `util.py` — the oracle. Tier-3
  predicates live at lines 184–820. Reimplement from prose/pseudocode; copy no source (D-10 / 131 D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`scripts/backfill_tactic_tags.py`** — purpose-built tactic-columns-only re-backfill (D-04); no
  new script needed, and cheaper than `backfill_flaws.py`.
- **`tactic_confidence` query-suppression lever** — the existing "tag→NULL at query time" mechanism;
  failing Tier-3 motifs suppress through it, no new machinery.
- **`scripts/tactic_tagger_report.py --check-goals`** — measurement/regression harness already
  exists; this phase raises GOALS for the in-scope Tier-3 motifs and drives precision against it.
- **`detect_interference` (1.00 TEST)** — a faithfully-ported Tier-3 motif; the structural template
  / existence proof for what a correct relational Tier-3 port looks like.
- **Shared utility ports from Phase 131** (ray-aware `is_defended`, `is_in_bad_spot`, `king_values`)
  — already in the detector; Tier-3 predicates can reuse them rather than reimplementing.

### Established Patterns
- **Detector = pure CPU, reads stored `pv` at `flaw_ply+1`**, `pov = board_after_flaw.turn`. No
  engine call inside the detector; Tier-3 hardening stays inside this contract.
- **Single tag per flaw, clean `GROUP BY tactic_motif`** — the port must preserve "exactly one
  winning motif" cardinality; it changes *which* motif fires, not how many.
- **Slow detector/harness tests live in the default-excluded `tests/scripts/tagger/` directory**
  (Phase 127 D-14); the precision gate is a dedicated CI step, not part of `uv run pytest -n auto`.

### Integration Points
- Tier-3 detectors are leaves under the shallowest-wins dispatcher — they only ever WIN on puzzles
  where no shallower (Tier-1/2/hanging) tactic fires. Improving a Tier-3 predicate reduces its
  *false wins* (FP); it cannot raise volume beyond what dispatch allots (~1.8% of tags) — D-05.
- The `_detect_tactic_for_flaw` kernel is shared by the live eval drain and
  `backfill_tactic_tags.py`; parity is guaranteed by construction, so the dev re-backfill (D-04)
  validates exactly what prod will compute when tagging eventually deploys.

</code_context>

<specifics>
## Specific Ideas

- Governing product value (inherited from Phase 131): a wrong, *visible* tag erodes trust in a
  stats product more than a missing one. Precision-first; recall ungated. Every Tier-3 motif that
  can't honestly reach 0.9 is suppressed, not shipped.
- The single highest-value target is **`deflection`** — at 0.21 TEST it is the biggest single
  false-positive source in the entire detector (991 FP). Killing its over-firing is the phase's
  clearest win even if several sibling motifs end suppressed.
- ROI realism is built into the scope: Tier-3 is ~1.8% of tag volume and several motifs are deeply
  broken (x-ray 0.00, attraction 0.04). The win condition is an **honest** detector — correct tags
  shipped, hopeless ones suppressed — not a green number on every row.

</specifics>

<deferred>
## Deferred Ideas

- **Prod re-backfill / prod deployment of tactic tagging** — out of scope; tagging is not in prod.
  When it deploys, new drains pick up the corrected Tier-3 code automatically.
- **A hand-labeled prod-flaw precision set** — the CC0 puzzle fixture stays the ground truth
  (carried from Phase 131); not in scope.
- **SEED-058** (new tactic motifs / lichess coverage), **SEED-062** (tactic-comparison orientation
  basis) — separate seeds, not this phase.
- **Adding a standalone-firing precision view as a permanent harness gate** — only a tuning-time
  diagnostic per D-05; promoting it to a shipping gate is out of scope unless evidence demands it.

### Reviewed Todos (not folded)
None reviewed — same tactic-precision domain as Phase 131, where the todo matcher surfaced only
generic keyword false-positives unrelated to tactic precision.

</deferred>

---

*Phase: 132-tier-3-tactic-precision-hardening-via-cook-py-predicate-alig*
*Context gathered: 2026-06-23*
