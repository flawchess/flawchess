---
id: SEED-070
status: dormant
planted: 2026-06-29
planted_during: /gsd-explore session on tactic-tag noise in real games. The fixture report looks excellent (~0.998 precision) but real-game tags for clearance/sacrifice/capturing-defender are noisy because the detector is puzzle-validated and run over non-forced real-game PVs. Full design captured in notes/tactic-forcing-line-gate.md.
trigger_when: at the next milestone boundary — run /gsd-new-milestone for v1.30 and use this seed + notes/tactic-forcing-line-gate.md as the starting context. This is milestone-sized (5 phases), NOT a single phase.
scope: Large — backend engine + analysis pipeline + DB migration + worker infra + offline re-tagger + corpus backfill. New JSONB storage on game_flaws; MultiPV=2 eval pass; an "only-move" forcing-line gate on the detector.
---

# SEED-070: Forcing-line gate for tactic tagging (v1.30 milestone)

## Why This Matters

The tactic tagger is validated entirely on lichess puzzles (forced lines, tactic = the point)
but deployed over the engine's best PV in **ordinary real-game positions**, where the line
often isn't forced. Result: clearance / sacrifice / capturing-defender (and others) get tagged
**too deep / disconnected**, **wrong-labeled** from incidental geometry in the non-forced tail,
or **trivially** — all from one root. The fixture report can't see this (no non-forced tail).

The fix is an **"only-move" forcing-line gate** modeled on lichess-puzzler: only credit a motif
whose firing node is a clear best move (win-prob margin over second-best), checked **at solver
nodes only** (defender ambiguity is fine — handles branch-then-reconverge), plus already-winning
/ still-winning rejection filters. To make threshold tuning cheap, **persist the MultiPV results**
so re-tagging is a pure offline re-derivation (no engine).

Full design — constants (0.35 win-prob margin ≡ lila's 0.7), solver-only rationale, filters,
JSONB storage schema, the user-28 dev-vs-prod experiment, open knobs, and the AGPL boundary —
is in **`notes/tactic-forcing-line-gate.md`**. Read it first when promoting this seed.

## Proposed phase breakdown (milestone-sized)

1. **Storage schema** — `game_flaws` JSONB columns `allowed_pv_lines` / `missed_pv_lines`
   (per-node best/second evals + second-best UCI) + Alembic migration. Small, isolated, ships
   first. (Sidecar `game_flaw_pv_lines` is the fallback if game_flaws must stay narrow.)
2. **MultiPV eval pass** — extend `engine.py` / the analysis pipeline to compute + persist
   per-node best/second evals (MultiPV=2); wire into remote worker infra. The expensive
   capability. Decide node budget + solver-only-vs-every-node here.
3. **Offline re-tagger** — consume stored MultiPV; implement the solver-node only-move gate
   (`p(best) − p(second) > ~0.35` via `eval_utils.LICHESS_K`), the already-winning (+300cp) /
   still-winning (+200cp) floors, length rules. The cheap, `/loop`-tunable detector pass.
4. **Validation** — user-28 dev (old + new logic on the **same** fresh MultiPV evals, to
   isolate the gate from `eval_cp` non-determinism) vs prod-28 sanity ref. Tune the margin;
   measure noise removed **and** good tags killed (false negatives).
5. **Corpus backfill + ship** — run the fleet, re-tag, roll out the gated tags.

## Cross-References

- `notes/tactic-forcing-line-gate.md` — the load-bearing design note (read first).
- `reports/tactic-tagger/tactic-tagger-2026-06-23.md` — the fixture report that motivated this.
- `notes/tactic-tagger-cook-alignment.md`, `SEED-064` — prior cook-alignment / precision work
  (AGPL boundary: prose not source; clone at `/home/aimfeld/Projects/Python/lichess-puzzler`).
- `SEED-039`, `SEED-058`, `SEED-065` — adjacent tactic features that interact with the gate.
