---
phase: 101
slug: frontend-major-dependency-upgrades
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-31
---

# Phase 101 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
>
> This is a dependency-upgrade maintenance phase: no new application code, no new
> test infrastructure. Validation is the **existing full local gate**, run once per
> cluster merge (D-06), plus **human visual UAT** for the recharts 3 cluster (D-01).
> The gate already exercises every requirement — there is no Wave 0 to build.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (frontend) + pytest (backend, unaffected) |
| **Config file** | `frontend/vitest.config.ts` / `frontend/vite.config.ts` (existing) |
| **Quick run command** | `( cd frontend && npm run lint && npm test -- --run )` |
| **Full suite command** | `uv run ruff format --check app/ tests/ && uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -n auto -x && ( cd frontend && npm run lint && npm test -- --run && npm run build && npm run knip )` |
| **Estimated runtime** | ~3–5 min full gate (frontend build dominates) |

---

## Sampling Rate

- **After every task (dep bump within a cluster):** Run the relevant frontend sub-gate (`npm run lint` / `npm test -- --run` / `npm run build` / `tsc -b`) for the surface that bump touches.
- **After every cluster (= one wave):** Run the **full local gate** (backend + frontend) before the cluster's squash-merge to `main` (D-06).
- **Before merge of recharts cluster:** Full gate green **and** human visual UAT signed off (D-01).
- **Max feedback latency:** < 300 s (full gate).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| C1 lucide-react 1.x | 01 | 1 | criterion 1,2,3 | — | N/A | gate | `( cd frontend && npm run build && npm test -- --run && npm run lint )` | ✅ | ⬜ pending |
| C1b shadcn 4.9.0 (D-04) | 01 | 1 | criterion 1 | — | N/A | gate | `( cd frontend && npm run build && npm run lint )` | ✅ | ⬜ pending |
| C2 Vite 8 + plugin-react 6 | 01 | 2 | criterion 1,2,3 | — | N/A | gate | `( cd frontend && npm run build && npm run dev (smoke) && npm test -- --run )` | ✅ | ⬜ pending |
| C3 jsdom 29 (+@types/node held) | 01 | 3 | criterion 1,2,3 | — | N/A | gate | `( cd frontend && npm test -- --run )` | ✅ | ⬜ pending |
| C4 eslint 10 + plugins (D-05) | 01 | 4 | criterion 1,2,3,5 | — | N/A | gate | `( cd frontend && npm run lint )` | ✅ | ⬜ pending |
| C5 typescript 6 | 01 | 5 | criterion 1,2,3,5 | — | N/A | gate | `( cd frontend && npx tsc -b && npm run build )` | ✅ | ⬜ pending |
| C6 recharts 3 | 01 | 6 | criterion 1,2,3,4 | — | N/A | gate + UAT | `( cd frontend && npm run build && npm test -- --run )` + human visual UAT | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure (Vitest + the full local gate + `npm run build`/`knip`) covers all phase requirements. No Wave 0 test-stub work — this phase builds no new application behavior.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| recharts 3 charts render correctly | criterion 4 (D-01) | recharts is user-facing; a green build does not prove visual correctness. Tooltips, gradients, multi-axis grids, and gauges can silently break while compiling clean. | Claude prepares a concrete checklist (MiniBulletChart, WDLChartRow, ScoreChart, ScoreGapByTimePressureChart, gauges, custom tooltips/gradients) + the exact local URL/routes; user eyeballs on desktop and a mobile-width viewport and gives the verdict before the cluster merges. |

---

## Validation Sign-Off

- [x] All tasks map to the existing full local gate (automated) or human UAT (recharts only, justified)
- [x] Sampling continuity: full gate runs at every cluster merge — no cluster merges ungated
- [x] No Wave 0 needed (no new code/infra)
- [x] No watch-mode flags (`npm test -- --run`, not `test:watch`)
- [x] Feedback latency < 300s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
