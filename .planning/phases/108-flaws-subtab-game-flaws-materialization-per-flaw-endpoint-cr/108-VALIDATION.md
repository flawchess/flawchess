---
phase: 108
slug: flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase 108 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend, async) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest), `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_<target>.py` |
| **Full suite command** | `uv run pytest -n auto -x` then `( cd frontend && npm run lint && npm test -- --run )` |
| **Estimated runtime** | ~20 s backend (parallel), ~30 s frontend |

---

## Sampling Rate

- **After every task commit:** Run the relevant `uv run pytest tests/test_<target>.py` (or `npm test -- --run <file>` for frontend tasks)
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full backend suite + frontend lint/test must be green; `uv run ty check app/ tests/` zero errors
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Filled in by the planner against the final task IDs. Skeleton below maps the major validation seams identified in RESEARCH.md "Validation Architecture".

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 108-01-* | 01 | 1 | D-02/D-03/D-10 game_flaws schema + migration | — | user-scoped rows, FK CASCADE on user/game delete | unit | `uv run pytest tests/test_game_flaws_model.py` | ❌ W0 | ⬜ pending |
| 108-02-* | 02 | 2 | D-10/D-03 classify→row mapping + import hook | — | FlawRecord tags → typed boolean columns round-trip; M+B-only | unit | `uv run pytest tests/test_flaws_materialization.py` | ❌ W0 | ⬜ pending |
| 108-03-* | 03 | 3 | D-02/D-03 shared predicate builder + EXISTS | T (filter injection) | OR-within-family / AND-across-family + EXISTS user scoping | unit | `uv run pytest tests/test_flaw_predicate.py` | ❌ W0 | ⬜ pending |
| 108-04-* | 04 | 4 | D-02/D-03 Games migration to game_flaws | — | Games endpoints read game_flaws, parity with prior output | integration | `uv run pytest tests/test_library_service.py` | ✅ | ⬜ pending |
| 108-05-* | 05 | 5 | D-05/D-07/D-08/D-03 per-flaw list endpoint | T (IDOR) | GET /library/flaws returns only requesting user's flaws, paginated | integration | `uv run pytest tests/test_library_router.py` | ✅ | ⬜ pending |
| 108-06-* | 06 | 3 | D-09/D-10 backfill script + reclassify recompute | T (filter injection) | `backfill_flaws.py --db dev --user-id 28` populates rows batched | unit+manual | `uv run pytest tests/test_backfill_flaws.py` + see Manual-Only | ❌ W0 | ⬜ pending |
| 108-07-* | 07 | 6 | D-04/D-06/D-07/D-08 Flaws subtab UI | — | filter control + miniboard list render, deep-link populates filter | component | `npm test -- --run FlawsTab` | ❌ W0 | ⬜ pending |
| 108-08-* | 08 | 7 | D-01/D-04/D-05 Games reconciliation + chip deep-link | — | TagChip navigates to /library/flaws?tag={TAG}; shared panel-hosted control | component | `npm test -- --run LibraryGameCard` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_game_flaws_model.py` — model + FK CASCADE + composite PK stubs
- [ ] `tests/test_flaws_materialization.py` — classify_game_flaws → game_flaws row mapping (tags → typed columns), M+B-only filtering
- [ ] `tests/test_flaw_predicate.py` — shared WHERE-clause builder: OR-within-family, AND-across-family, single-flaw EXISTS, user scoping
- [ ] `frontend` FlawsTab + Flaw-filter control test stubs (vitest + testing-library)
- [ ] Existing `tests/test_library_service.py` / `tests/test_library_router.py` extended for the migrated Games path + new /library/flaws endpoint (infrastructure already present)

*Per-flaw endpoint and Games-migration tests reuse existing library test infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `backfill_flaws.py` populates dev rows correctly | D-09 | Runs against the live dev DB, batched; verifying row counts/content is an out-of-band script run, not a unit test (project norm: no dev DB reset gating) | `uv run python scripts/backfill_flaws.py --db dev --user-id 28`, then confirm `game_flaws` row count > 0 for user 28 and counts match the live `classify_game_flaws` path for a sampled game |
| Prod backfill / all-users recompute | D-09 | Explicitly out-of-band, run by user; NOT gated for phase completion | Documented in plan; user runs manually post-merge |
| Flaws subtab visual parity + mobile drawer | D-06/UI-SPEC | Visual fidelity vs UI-SPEC and Phase 107 tokens | HUMAN-UAT: load /library/flaws, verify miniboard list, filter control, mobile drawer, chip deep-link landing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
