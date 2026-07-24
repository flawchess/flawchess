---
phase: 184-persona-calibration-strength-honesty
plan: 04
type: execute
completed: 2026-07-23
status: complete
requirements: [CAL-04, CAL-05]
---

# Phase 184 Plan 04 Summary — Operator Persona-Calibration Sweep + Refit

> Reconstructed at v2.7 milestone close (2026-07-24). The plan's HUMAN-UAT
> checkpoint (operator overnight sweep) and the follow-on refit were carried out
> directly by the operator plus a gap-fill quick task rather than a formal
> executor pass, so no SUMMARY was written at the time. This documents what
> actually shipped, verified against the committed artifacts.

## What was done

- **Operator overnight sweep (D-09 HUMAN-UAT gate).** The ~24-persona-cell sweep
  ran via `bin/run_persona_calibration_sweep.sh` under `bin/preset-supervisor.sh`
  (supervised resume-on-crash, per the Phase 180 model), producing the real
  measured aggregate `reports/data/persona-calibration-cells.tsv` (241 rows, **24
  distinct `persona_id` row-groups** — no Pitfall-1 collision).
- **Refit + regenerate.** `calibration_persona_fit.py` + `gen_persona_calibration.py`
  regenerated `reports/data/persona-calibration.json` (**24 entries**) and
  `frontend/src/generated/personaCalibration.ts` from the real ledger, replacing
  the Plan-02 bootstrap values. `PERSONA_CALIBRATION_MEASURED` flipped to `true`,
  so the ELO disclosure popover now reads as measured rather than provisional.
- **Gap fill (CAL-04b).** A follow-up pass (commit `813acd0a`, "fix(calibration):
  fill ~800 and ~1200 persona strength gaps") closed the weakest-rung measurement
  gaps and re-regenerated both artifacts; the schedule check + generator were
  updated alongside.

## Requirements

- **CAL-04 — satisfied.** Every persona's labeled ELO is measured on the internal
  anchor scale from the real sweep ledger with per-persona style offsets absorbed
  by the fit (not the bootstrap `approx_blitz = rung` placeholder).
- **CAL-05 — satisfied.** Labels honor the honesty constraints: no label exceeds
  ~1800 (D-07 ceiling clamp), the 800 rung carries its measured/extrapolated
  floor value with the D-06 acknowledgment popover, and within-style columns are
  weakly monotone (D-04 PAVA).

## Verification (at close)

- `reports/data/persona-calibration-cells.tsv`: 24 distinct persona groups.
- `reports/data/persona-calibration.json`: 24 entries; drift-clean working tree.
- `frontend/src/generated/personaCalibration.ts`: committed, `PERSONA_CALIBRATION_MEASURED = true`.
- Landed to production via PR #274 (persona strength calibration fix) and
  reflected in quick 260722-ucc (bot games stored with persona name + calibrated ELO).

## Deviation from plan

The plan expected a single one-shot refit gated on the operator "approved"
signal. In practice the sweep + refit landed across a direct operator run plus the
CAL-04b gap-fill commit. Substance matches the plan's success criteria; only the
process (and this retroactive SUMMARY) differ.

## Self-Check: PASSED (reconstructed)
