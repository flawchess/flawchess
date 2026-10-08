---
quick_id: 261008-ob1
status: complete
commit: b53a2203b
---

# Quick 261008-ob1 Summary: Train re-check also rescues off-key inaccuracy grades

## What changed

- `frontend/src/lib/trainRecheck.ts`: `shouldRecheck` now also fires for an
  off-key, off-runner-up move the 1.5 s grade rated `inaccuracy`, on any keyed
  puzzle type. Sharp/good trigger unchanged; `wrong` never re-checked.
- Tests: unit cases for sharp/soft/herring inaccuracy firing and wrong/key/
  runner-up exclusions; two TrainSolveScreen integration tests with a new
  `ScriptedCpWorker` (1.5 s played search under-reads → 3 s reads good →
  POST `good` + `confirmed`; 3 s still inaccuracy → `inaccuracy` + `resolved`).
- Backend: docstrings only (`SolveRecheck` outcome semantics and the two
  trigger populations; `_disagreement_accepted` note). No schema change.
- CHANGELOG [Unreleased] → Fixed bullet.

## Verification

- Mutation check: removing the inaccuracy branch fails all 5 new tests.
- vitest (2 files, 136 tests) green; eslint, `npm run build`, knip clean.
- ruff, ty, `pytest -k "recheck or resolve_grade or disagreement"` (49 passed).

## Cost

Inaccuracy is ~5.7% of prod solves (266 / 4679, last 30 days); those now wait
for the ~6 s re-check ("Taking a closer look…").
