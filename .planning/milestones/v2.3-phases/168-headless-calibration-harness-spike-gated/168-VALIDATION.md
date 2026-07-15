---
phase: 168
slug: headless-calibration-harness-spike-gated
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-11
---

# Phase 168 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend `@/` imports) + Node `.mjs` script self-checks |
| **Config file** | `frontend/vitest.config.ts` (parity/unit); scripts run under `node --import ./scripts/lib/frontend-alias-hook.mjs` |
| **Quick run command** | `cd frontend && npm test -- --run <parity-or-math-spec>` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run` |
| **Estimated runtime** | ~30–90 seconds (excludes the throughput spike, which is a manual harness run) |

---

## Sampling Rate

- **After every task commit:** Run the relevant `npm test -- --run <spec>`
- **After every plan wave:** Run the full frontend lint + test suite
- **Before `/gsd-verify-work`:** Full suite green + spike report emitted
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 168-01-01 | 01 | 1 | CAL-02 | — / — | N/A | parity | `cd frontend && npm test -- --run calibration-parity` | ❌ W0 | ⬜ pending |
| 168-02-01 | 02 | 1 | CAL-03 | — / — | N/A | manual | spike throughput report to `reports/data/` | ❌ W0 | ⬜ pending |
| 168-03-01 | 03 | 2 | CAL-01 | — / — | N/A | unit | `cd frontend && npm test -- --run elo-inversion` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · exact task IDs finalized by the planner.*

---

## Wave 0 Requirements

- [ ] Parity spec (`gem-parity`-style) that imports live `selectBotMove` and asserts no reimplementation — covers CAL-02
- [ ] ELO-inversion math unit test (property-based: monotonicity + known-anchor round-trip) — covers CAL-01 estimate
- [ ] Seeded-opening reproducibility check (same `--seed` → identical opening FEN sequence)

*Vitest infrastructure already exists in `frontend/`; no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spike throughput (moves/sec + projected full-grid wall-clock) in the most expensive cell | CAL-03 | Requires a real WASM inference + Stockfish run; wall-clock-bound, not deterministic | Run the spike sub-command; confirm it prints moves/sec and a go/no-go recommendation |
| Full grid → strength-map TSV emitted to `reports/data/` | CAL-01 | End-to-end multi-hour sweep; validated by inspecting the durable TSV + sibling summary | Run the harness with cheap defaults; confirm main TSV + `-summary.tsv` with per-row durability |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
