---
phase: 20
slug: rename-branding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_chesscom_client.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_chesscom_client.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | BRAND-01 | smoke/grep | `grep -ri chessalytics . --include="*.py" --include="*.ts" --include="*.tsx" --include="*.html" --include="*.toml" --include="*.md" --include="*.json" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=".planning/milestones" --exclude-dir=".planning/quick" --exclude-dir=".planning/research"` | N/A — shell | ⬜ pending |
| 20-01-02 | 01 | 1 | BRAND-01 | unit | `uv run pytest tests/test_chesscom_client.py -x` | ✅ | ⬜ pending |
| 20-01-03 | 01 | 1 | BRAND-02 | manual | Install PWA on phone; check app icon label | N/A — manual | ⬜ pending |
| 20-01-04 | 01 | 1 | BRAND-03 | smoke | `ls frontend/public/icons/` | N/A — shell | ⬜ pending |
| 20-01-05 | 01 | 1 | BRAND-04 | smoke | `git remote -v` | N/A — shell | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed.

- The User-Agent test in `tests/test_chesscom_client.py` will be updated in-place (not a new file)
- Grep-based smoke checks use standard shell commands
- No new test framework installation required

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PWA shows "FlawChess" name on phone install | BRAND-02 | Requires real device PWA install | 1. Run `npm run build` 2. Serve frontend 3. Install PWA on phone 4. Verify app name shows "FlawChess" |
| Git remote points to flawchess org | BRAND-04 | User-executed repo transfer | 1. User transfers repo on GitHub 2. Run `git remote set-url origin git@github.com:flawchess/flawchess.git` 3. Verify with `git remote -v` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
