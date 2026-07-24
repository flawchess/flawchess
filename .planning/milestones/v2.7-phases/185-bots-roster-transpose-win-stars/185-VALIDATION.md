---
phase: 185
slug: bots-roster-transpose-win-stars
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-22
---

# Phase 185 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (`pytest-asyncio`, per-run cloned DB template) + Vitest (jsdom per-file) |
| **Config file** | `pyproject.toml` (backend), `frontend/vite.config.ts` (frontend — no `test:` block, 5s default testTimeout) |
| **Quick run command** | `uv run pytest tests/schemas/test_bots.py tests/routers/test_bots.py -x` / `cd frontend && npx vitest run src/components/bots/__tests__/PersonaGrid.test.tsx src/components/bots/__tests__/PersonaCard.test.tsx` |
| **Full suite command** | `uv run pytest -n auto` / `cd frontend && npm test -- --run` |
| **Estimated runtime** | quick ~10s; full backend ~2–4 min parallel, full frontend ~1 min |

---

## Sampling Rate

- **After every task commit:** Run the scoped quick command for the files touched
- **After every plan wave:** Run full backend (`uv run pytest -n auto`) + full frontend (`npm test -- --run`)
- **Before `/gsd-verify-work`:** Both full suites green, plus `uv run ty check app/ tests/` and frontend `npm run lint` + `npx tsc -b`
- **Max feedback latency:** ~240 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | — | — | — | — | — | — | ⬜ pending |

Behavior map from RESEARCH.md (planner lifts into tasks):

| Behavior | Test Type | Automated Command | File Exists |
|----------|-----------|-------------------|-------------|
| Grid renders 6 rung rows × 4 style columns, header row of 4 style names in accent colors, no row labels | unit (jsdom) | `npx vitest run src/components/bots/__tests__/PersonaGrid.test.tsx` | ❌ W0 (rewrite DOM-order assertion) |
| PersonaCard renders `min(wins,3)` gold + grey-outline stars | unit (jsdom) | `npx vitest run src/components/bots/__tests__/PersonaCard.test.tsx` | ❌ W0 |
| `StoreBotGameRequest.persona_id` accepts None + bounded string; rejects overlong | unit | `uv run pytest tests/schemas/test_bots.py -x` | ❌ W0 |
| `POST /bots/games` persists `persona_id` on create; idempotent resubmit no-op | integration | `uv run pytest tests/routers/test_bots.py -x` | ❌ W0 |
| Win aggregation counts wins only, excludes `persona_id IS NULL` | unit (real DB) | `uv run pytest tests/repositories/ -x -k persona` | ❌ W0 |
| `GET /bots/persona-wins` user-scoped, requires auth | integration | `uv run pytest tests/routers/test_bots.py -x` | ❌ W0 |
| Alembic migration applies cleanly | migration | `uv run alembic upgrade head` (auto via test-DB template refresh) | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Locate/create repository test coverage for the new win-aggregation query (verify where `game_repository` tests live)
- [ ] Fixture/helper seeding a `games` row with `persona_id` set (follow `_make_bot_game_payload` in `tests/routers/test_bots.py`)
- [ ] Framework install: none — pytest and Vitest already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Transposed grid visual check (accent-colored header, tint identity, mobile layout) | — | Visual/responsive judgment | Open /bots in dev, verify 6 rung rows × 4 style columns on desktop and mobile drawer widths |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
