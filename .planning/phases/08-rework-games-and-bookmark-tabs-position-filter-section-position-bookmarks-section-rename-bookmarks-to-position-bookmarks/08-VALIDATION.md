---
phase: 8
slug: rework-games-and-bookmark-tabs-position-filter-section-position-bookmarks-section-rename-bookmarks-to-position-bookmarks
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | Rename DB table | integration | `uv run pytest -x` | ✅ | ⬜ pending |
| 08-01-02 | 01 | 1 | Rename backend model/repo/router/schemas | unit | `uv run pytest -x` | ✅ | ⬜ pending |
| 08-02-01 | 02 | 1 | Rename frontend types/hooks/components | manual | N/A | ❌ | ⬜ pending |
| 08-02-02 | 02 | 1 | Move charts to components/charts/ | manual | N/A | ❌ | ⬜ pending |
| 08-03-01 | 03 | 2 | Three collapsible sections layout | manual | N/A | ❌ | ⬜ pending |
| 08-03-02 | 03 | 2 | Remove Bookmarks tab/route | manual | N/A | ❌ | ⬜ pending |
| 08-03-03 | 03 | 2 | Load bookmark in-place | manual | N/A | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

No new test files required — this is a rename/restructure with no new logic. Existing tests targeting bookmark endpoints will need path updates from `/bookmarks` to `/position-bookmarks`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Position filter section open by default | UI layout | Browser visual state | Open Dashboard, verify Position filter section is expanded |
| Position bookmarks section collapsed by default | UI layout | Browser visual state | Open Dashboard, verify Position bookmarks section is collapsed |
| More filters section collapsed by default | UI layout | Browser visual state | Open Dashboard, verify More filters section is collapsed |
| Load bookmark replays moves in-place | In-place load | Requires chess board interaction | Create bookmark, collapse/expand Position bookmarks, click Load, verify board shows saved position |
| Nav has 4 tabs (no Bookmarks) | Tab removal | Browser visual check | Verify navigation shows: Games, Openings, Rating, Global Stats |
| Openings page WinRateChart renders | Chart relocation | Visual rendering | Navigate to Openings, verify chart renders correctly |
| Drag-and-drop reorder works | DnD preserved | Interaction test | Drag bookmark cards in Position bookmarks section, verify order persists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
