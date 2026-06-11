---
phase: 115
slug: you-vs-opponent-comparison-api-bullet-grid-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 115 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (backend) / `frontend/vitest.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/<file>::<test>` (single) |
| **Full suite command** | `uv run pytest -n auto` (backend) / `cd frontend && npm test -- --run` (frontend) |
| **Estimated runtime** | backend ~60-120s (`-n auto`), frontend ~20-40s |

---

## Sampling Rate

- **After every task commit:** Run the relevant single test file (`uv run pytest tests/<file>` or `npm test -- --run <file>`)
- **After every plan wave:** Run `uv run pytest -n auto` (backend waves) / `npm test -- --run` (frontend waves)
- **Before `/gsd-verify-work`:** Full backend + frontend suites green, `ruff`/`ty`/`npm run lint`/`knip` clean
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · Planner/executor fills this map from the PLAN tasks.*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements (pytest + vitest already configured). New test files will be added per plan.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bullet-grid visual layout (family grouping, 3-col desktop / 1-col mobile, inverted-color zones) | FLAWUI-01, FLAWUI-04, FLAWUI-06 | Visual/responsive correctness not fully assertable in unit tests | Open Library → Stats tab on desktop + mobile viewport; confirm family headers, 3/1 columns, inverted color (success LEFT of band), zero-event placeholder, below-floor CTA |
| Tooltip prose correctness (definition, sign convention, caveats) | FLAWUI-02, FLAWUI-03 | Copy quality is editorial | Hover each bullet popover; confirm definition + sign convention + tempo/severity/filter caveats per D-15 |
| Dev `game_flaws` basis matches §5 zone basis (A2 pre-execution check) | FLAWCMP-03 | Data-freshness check, not code | Confirm dev `game_flaws` reflects mate-ladder + recalibrated thresholds (else reclassify/backfill before UAT) |

*Remaining phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
