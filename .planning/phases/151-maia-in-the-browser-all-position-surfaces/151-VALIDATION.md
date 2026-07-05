---
phase: 151
slug: maia-in-the-browser-all-position-surfaces
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-05
---

# Phase 151 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) + pytest 8.x (backend, only for the /users/me/profile field in Plan 03) |
| **Config file** | frontend/vitest.config.ts / pyproject.toml |
| **Quick run command** | `cd frontend && npm test -- --run` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run && npm run build` (+ `uv run ty check app/ tests/ && uv run pytest -n auto tests/test_users.py` when Plan 03 is in the wave) |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` command (frontend vitest / backend pytest as applicable)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 151-01-01 | 01 | 1 | MAIA-01 (supply chain) | manual (checkpoint) | N/A — blocking-human package-legitimacy gate before `npm install onnxruntime-web` | ⬜ pending |
| 151-01-02 | 01 | 1 | MAIA-01, MAIA-06 | build + static | `cd frontend && npm run build && node -e "<sw.js precache excludes .onnx/ort-wasm*.wasm>"` | ⬜ pending |
| 151-01-03 | 01 | 1 | MAIA-01, MAIA-06 | integration + manual | `node scripts/inspect_maia_onnx.mjs && grep -viE '^\s*(#|//|\*)' 151-MAIA-CONTRACT.md \| grep -qiE 'WDL\|policy'` | ⬜ pending |
| 151-02-01 | 02 | 1 | LIC-01 | static | `head -3 LICENSE \| grep -qi 'AFFERO' && grep -qi 'AGPL' README.md && ! grep -q 'license-MIT' README.md` | ⬜ pending |
| 151-02-02 | 02 | 1 | LIC-02 | unit (vitest) | `cd frontend && npm test -- --run src/components/analysis/__tests__/MaiaAttribution.test.tsx && npm run lint` | ⬜ pending |
| 151-03-01 | 03 | 1 | MAIA-04 | unit (pytest) | `uv run ty check app/ && uv run pytest -n auto tests/test_users.py -x` | ⬜ pending |
| 151-03-02 | 03 | 1 | MAIA-04 | type-check | `cd frontend && npx tsc -b && npm run lint` | ⬜ pending |
| 151-04-01 | 04 | 2 | MAIA-03 | unit (vitest) | `cd frontend && npm test -- --run src/lib/__tests__/maiaEncoding.test.ts` | ⬜ pending |
| 151-04-02 | 04 | 2 | MAIA-02, MAIA-06, D-09 | static + build | `cd frontend && node -e "<numThreads=1 forced; never >1; webgpu+requestAdapter present>" && npm run build` | ⬜ pending |
| 151-04-03 | 04 | 2 | MAIA-04, MAIA-05, SURF-05 | unit (mock worker) | `cd frontend && npm test -- --run src/hooks/__tests__/useMaiaEngine.test.ts && npx tsc -b` | ⬜ pending |
| 151-05-01 | 05 | 3 | SURF-04 | unit (vitest) | `cd frontend && npm test -- --run src/components/analysis/__tests__/EvalBar.test.tsx && npx tsc -b` | ⬜ pending |
| 151-05-02 | 05 | 3 | SURF-01, SURF-02, SURF-03 | unit (vitest) | `cd frontend && npm test -- --run src/components/analysis/__tests__/MovesByRatingChart.test.tsx && npx tsc -b` | ⬜ pending |
| 151-05-03 | 05 | 3 | SURF-04, D-06 | unit (vitest) | `cd frontend && npm test -- --run src/components/analysis/__tests__/EloSelector.test.tsx && npm run lint && npm run knip` | ⬜ pending |
| 151-06-01 | 06 | 4 | MAIA-04, D-07 | unit (vitest) | `cd frontend && npm test -- --run src/hooks/__tests__/useMaiaEloDefault.test.ts && npx tsc -b` | ⬜ pending |
| 151-06-02 | 06 | 4 | SURF-04, SURF-05, MAIA-04, MAIA-05 | build + integration | `cd frontend && npx tsc -b && npm run lint && npm run build` | ⬜ pending |
| 151-06-03 | 06 | 4 | LIC-02, D-03 | build + integration | `cd frontend && npx tsc -b && npm run lint && npm run knip && npm run build` | ⬜ pending |
| 151-06-04 | 06 | 4 | VALID-01, MAIA-06 | manual (checkpoint) | N/A — live calibration eyeball + device size/latency measurement → 151-MAIA-MEASUREMENTS.md | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. Flips during execution.*

Sampling-continuity check: no run of 3 consecutive tasks lacks an automated verify — the only two manual-only tasks (151-01-01, 151-06-04) are each flanked by automated ones.

---

## Wave 0 Requirements

The primary deterministic, fully-unit-testable surface of this phase is the **glue math in
`maiaEncoding.ts`** (Plan 04 Task 1) — it is pure and needs no real ONNX session:

- [ ] `frontend/src/lib/__tests__/maiaEncoding.test.ts` — board→tensor encoding (12-dim planes, side-to-move flip), legal-move masking (illegal from→to never present), softmax (sums to 1.0 ± 1e-6 over legal moves only; single-legal-move → 1.0), and `expectedScore` = W + 0.5·D ({1,0,0}→1, {0,0,1}→0, {0,1,0}→0.5), plus `MAIA_ELO_LADDER` matching the confirmed contract range.

Secondary deterministic surfaces (also created within their owning plans, not pre-scaffolded):
- [ ] `frontend/src/hooks/__tests__/useMaiaEngine.test.ts` — mock-worker lifecycle/debounce/stale-guard/cache/tab-hide (Plan 04 Task 3)
- [ ] `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` — ELO default derivation + user-override precedence (Plan 06 Task 1)
- [ ] `frontend/src/components/analysis/__tests__/{MaiaAttribution,MovesByRatingChart,EloSelector}.test.tsx` and extended `EvalBar.test.tsx` (Plans 02/05)
- [ ] `tests/test_users.py` additions — current_rating resolution (white/black most-recent, no-games→null) (Plan 03)

Real-ONNX integration (`useMaiaEngine.integration.test.ts`) is attempted via `onnxruntime-node` if
a Node path is feasible; otherwise it is documented as a browser-manual check, not silently skipped.

---

## Manual-Only Verifications

| Behavior | Task | Requirement | Why Manual | Test Instructions |
|----------|------|-------------|------------|-------------------|
| onnxruntime-web / -node package legitimacy ([SUS] false-positive) | 151-01-01 | MAIA-01 / supply chain | Human provenance judgment before install (not auto-approvable) | Verify npmjs publisher=Microsoft, license MIT, repo microsoft/onnxruntime, empty postinstall; approve, then `npm install` |
| ONNX tensor I/O contract confirmed against reference client | 151-01-03 | MAIA-01 | The inspection script prints metadata, but confirming policy layout (64×64 vs 4096) + WDL order vs the CSSLab client is a hands-on judgment | Run `scripts/inspect_maia_onnx.mjs`, cross-check names/shapes against maia-platform-frontend encoding, record in 151-MAIA-CONTRACT.md |
| Maia calibration eyeball across representative positions | 151-06-04 | VALID-01 | Subjective judgment (measure-and-judge per D-10, not a hard gate) | Navigate representative positions; compare Maia bar/curves to intuition + Stockfish across 2–3 ELO settings; confirm WDL sign/order (bar not flipped) |
| Download size + per-position latency (desktop + mobile) | 151-06-04 | MAIA-06 / VALID-01 | Device-dependent measurement | Measure model download size, cold-load, and single-call + ELO-sweep latency on desktop and phone (WASM vs WebGPU); confirm `crossOriginIsolated === false` and no unsupported-op errors → 151-MAIA-MEASUREMENTS.md |

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify or are documented manual-only with a Wave-0/checkpoint rationale
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 surface identified (maiaEncoding glue math) and owned by Plan 04 Task 1
- [x] No watch-mode flags (all vitest commands use `--run`)
- [x] Feedback latency < 90s
- [ ] `nyquist_compliant: true` — flips during execution once Wave 0 tests exist and pass
- [ ] `wave_0_complete: true` — flips when maiaEncoding.test.ts is green

**Approval:** pending (planner-reviewed; flips during execution)
