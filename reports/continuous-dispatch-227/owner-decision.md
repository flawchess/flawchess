# Phase 227 owner decision

**Date:** 2026-10-03

**Decision:** ship

**Basis:** The owner chose "Ship" from the evidence in `report.md` and `verdict.json`. The mechanical outcome is
`ship-eligible` (all judged criteria pass: D-01 and D-03 in both move-quality cells, the D-17 ship bar on `stop-p4`,
pool-2 no-regression, and the D-07 WebGPU point at 0.676) and `refit_if_shipped` is `no-refit` (calibration parity
holds in both families).

**Follows or departs from the mechanical outcome:** follows it in full. No override document is needed, and the accept
rule is unchanged.

**What this triggers (Plan 227-13):** flip `FLAWCHESS_DISPATCH_MODE` to `'continuous'`, no refit, smoke-test the shipped
engine in the dev build, record the device UAT, update the changelog and docs, remove the dev bench tool.
