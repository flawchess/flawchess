---
phase: 110
slug: flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase 110 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend, per-run isolated PostgreSQL DB) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) · `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_flaws_service.py` (or the touched test file) |
| **Full suite command** | `uv run pytest -n auto` then `( cd frontend && npm run lint && npm test -- --run )` |
| **Estimated runtime** | backend ~20s (parallel) · frontend ~15s |

---

## Sampling Rate

- **After every task commit:** Run the touched test file (`uv run pytest <nodeid>` or `npm test -- --run <file>`)
- **After every plan wave:** Run `uv run pytest -n auto` (backend waves) / `npm test -- --run` (frontend waves)
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` + frontend lint/knip must be green
- **Max feedback latency:** 30 seconds (single-file run)

---

## Per-Task Verification Map

> Filled by the planner per task. Phase 110 has no new REQ IDs (refactor/rename driven by the taxonomy note); requirement column references the roadmap success criteria SC-1..SC-6.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 110-01-01 | 01 | 1 | SC-2 (impact ladder boundaries) | — | N/A (no auth/data-exposure surface) | unit | `uv run pytest tests/test_flaws_service.py` | ✅ | ⬜ pending |

---

## Wave 0 Requirements

- Existing infrastructure covers all phase work. Backend uses the per-run isolated DB (conftest auto-refreshes the template on the new Alembic head). Frontend uses vitest.
- New tests to add (not Wave-0 blockers — co-located with their plan):
  - [ ] `tests/test_flaws_service.py` — impact-ladder boundary cases: `reversed` 70→30, `squandered` 85→60 (most-severe wins), and the deliberate no-impact gap (e.g. 78%→45%), outcome-independence (same ES swing, different `user_result`, same impact tag).
  - [ ] Frontend `TagChip` test — popover renders `tag-name` bold + definition; active-filter ring applied when tag matches `useFlawFilterStore`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dev-DB backfill repopulates users 28 & 44 | SC-4 | Mutates the live dev DB (not the test DB); cannot run in the isolated test harness | After migration, run `uv run python scripts/backfill_flaws.py --db dev --user-id 28` and `--user-id 44`; spot-check `game_flaws` rows have `is_reversed`/`is_squandered` populated and no `is_while_ahead`/`is_result_changing` columns |
| Hover/tap popover + active-filter ring on desktop AND mobile | SC-5, SC-6 | Visual/interaction parity across breakpoints; not assertable headlessly | Open Library → Games and Flaws cards; hover/tap a chip → popover with `tag-name: definition`; set an active Flaw filter → matching chips show the ring on desktop and mobile widths |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
