---
phase: "241"
slug: "codebase-cleanup"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-16"
---

# Phase 241 — Validation Strategy

> Reconstructed after execution (State B) from the 70 PLAN/SUMMARY pairs. Phase 241 is comment and naming change only, so the validation contract is "behavior unchanged": every task is gated by the phase toolkit (`tools/cleanup.py scan / diff / absent`) plus the existing backend and frontend suites.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend), plus the phase toolkit `.planning/phases/241-codebase-cleanup/tools/cleanup.py` |
| **Config file** | `pyproject.toml`, `frontend/vite.config.ts` |
| **Quick run command** | `cleanup.py scan --gate --scope scopes/241-NN.txt` / `cleanup.py diff --plan 241-NN` / `cleanup.py absent` + targeted pytest/vitest files |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~80-150 s backend (`-n auto`), ~120 s frontend |

---

## Sampling Rate

- **After every task commit:** the task's `<automated>` verify (toolkit scan/diff/absent + ty/ruff or tsc/eslint + targeted tests)
- **After every plan wave:** full backend + frontend suite on the merged tree (orchestrator post-merge gate; passed after waves 3-9)
- **Before `/gsd-verify-work`:** full CLAUDE.md pre-merge gate (241-70: ruff, ty x2, depth gate, pytest `-n auto` and serial, FE lint/build/vitest/knip, all green)
- **Max feedback latency:** ~150 s

---

## Per-Task Verification Map

One row per plan (153 tasks; every task carries at least one `<automated>` verify, 279 in total).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 241-01-01..01 | 01 | 1 | D-01, D-02, D-03, D-04, D-05 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-01.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-02-01..02 | 02 | 1 | D-10, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-02.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-03-01..02 | 03 | 2 | D-10, D-11, D-12, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-03.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-04-01..02 | 04 | 2 | D-10, D-11, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-04.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-05-01..02 | 05 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-05.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-06-01..02 | 06 | 3 | D-01, D-10, D-11, D-12, D-13, D-15, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-06.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-07-01..02 | 07 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-07.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-08-01..02 | 08 | 3 | D-01, D-03, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-08.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-09-01..02 | 09 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-09.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-10-01..02 | 10 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-10.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-11-01..02 | 11 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-11.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-12-01..02 | 12 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-12.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-13-01..02 | 13 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-13.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-14-01..02 | 14 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-14.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-15-01..02 | 15 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-15.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-16-01..02 | 16 | 3 | D-01, D-03, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-16.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-17-01..02 | 17 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-17.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-18-01..02 | 18 | 3 | D-01, D-04, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-18.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-19-01..02 | 19 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-19.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-20-01..02 | 20 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-20.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-21-01..02 | 21 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-21.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-22-01..02 | 22 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-22.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-23-01..02 | 23 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-23.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-24-01..02 | 24 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-24.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-25-01..02 | 25 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-25.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-26-01..02 | 26 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-26.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-27-01..02 | 27 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-27.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-28-01..02 | 28 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-28.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-29-01..02 | 29 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-29.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-30-01..02 | 30 | 3 | D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-30.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-31-01..02 | 31 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-31.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-32-01..02 | 32 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-32.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-33-01..02 | 33 | 3 | D-01, D-04, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-33.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-34-01..02 | 34 | 3 | D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-34.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-35-01..02 | 35 | 3 | D-01, D-04, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-35.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-36-01..02 | 36 | 3 | D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-36.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-37-01..02 | 37 | 3 | D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-37.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-38-01..02 | 38 | 3 | D-01, D-04, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-38.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-39-01..02 | 39 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-39.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-40-01..02 | 40 | 3 | D-01, D-04, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-40.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-41-01..02 | 41 | 3 | D-01, D-10, D-11, D-12, D-13, D-15, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-41.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-42-01..02 | 42 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-42.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-43-01..02 | 43 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-43.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-44-01..02 | 44 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-44.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-45-01..02 | 45 | 3 | D-01, D-10, D-11, D-12, D-13, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-45.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-46-01..02 | 46 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-46.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-47-01..02 | 47 | 3 | D-01, D-03, D-05, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-47.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-48-01..02 | 48 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-48.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-49-01..02 | 49 | 3 | D-01, D-03, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-49.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-50-01..02 | 50 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-50.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-51-01..02 | 51 | 3 | D-01, D-11, D-12, D-13, D-14, D-15 | per-plan STRIDE register | behavior unchanged (comment/name only) | comment | `cleanup.py scan --gate --scope scopes/241-51.txt` + `cleanup.py diff` + targeted tests | ✅ | ✅ green |
| 241-52-01..03 | 52 | 4 | D-06, D-07, D-08, D-09, D-10, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-52` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-53-01..02 | 53 | 4 | D-06, D-07, D-10, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-53` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-54-01..03 | 54 | 4 | D-06, D-07, D-08, D-09, D-10, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-54` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-55-01..02 | 55 | 4 | D-06, D-07, D-08, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-55` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-56-01..03 | 56 | 4 | D-02, D-06, D-07, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-56` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-57-01..03 | 57 | 4 | D-06, D-07, D-08, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-57` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-58-01..03 | 58 | 4 | D-06, D-07, D-08, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-58` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-59-01..03 | 59 | 4 | D-04, D-06, D-07, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-59` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-60-01..02 | 60 | 4 | D-06, D-07, D-08, D-10, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-60` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-61-01..03 | 61 | 4 | D-06, D-07, D-09, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-61` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-62-01..03 | 62 | 4 | D-06, D-07, D-08, D-09, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-62` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-63-01..03 | 63 | 4 | D-06, D-07, D-09, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-63` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-64-01..03 | 64 | 4 | D-06, D-07, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-64` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-65-01..03 | 65 | 5 | D-06, D-07, D-09, D-10, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-65` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-66-01..03 | 66 | 5 | D-06, D-07, D-16, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-66` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-67-01..03 | 67 | 6 | D-06, D-07, D-09, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-67` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-68-01..02 | 68 | 7 | D-06, D-07, D-09, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-68` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-69-01..02 | 69 | 8 | D-01, D-02, D-05, D-16, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | rename | `cleanup.py absent` + `cleanup.py diff --plan 241-69` + ty/tsc + targeted tests | ✅ | ✅ green |
| 241-70-01..03 | 70 | 9 | D-06, D-08, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17 | per-plan STRIDE register | behavior unchanged (comment/name only) | phase gate | `cleanup.py scan --gate --all-allow` + `diff --all-allow` + `absent` + full pre-merge gate | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (pytest, vitest, and the phase toolkit committed under `tools/`).

---

## Manual-Only Verifications

All phase behaviors have automated verification. Owner judgment calls (not test gaps) are listed in `241-70-SUMMARY.md` § Owner report.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none missing)
- [x] No watch-mode flags (`npm test -- --run`)
- [x] Feedback latency < 150s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-16
