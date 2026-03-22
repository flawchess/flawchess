---
phase: quick
plan: 260322-jem
subsystem: docs
tags: [readme, docs, open-source]
dependency_graph:
  requires: []
  provides: [professional-readme]
  affects: []
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - README.md
decisions:
  - Use 4 best screenshots (board-and-move-explorer, win-rate-over-time, filters, position-bookmarks)
  - Plain markdown images (no HTML table layout) per plan spec
  - Self-Hosting env var table with required vs optional distinction
metrics:
  duration: 58s
  completed: 2026-03-22
---

# Quick Task 260322-jem: Professional Open-Source README Summary

**One-liner:** Full README rewrite with CI badge, 4 inline screenshots, Self-Hosting section, and expanded Contributing guidelines.

## What Was Done

Rewrote README.md from 117 lines to 178 lines with professional open-source quality:

1. **CI badge** added as first badge, linked to GitHub Actions workflow (`ci.yml/badge.svg`)
2. **Screenshots** section replaced "Screenshots coming soon" with 4 inline images using relative paths (`frontend/public/screenshots/`)
3. **Getting Started** (renamed from "Local Development") with optional-service note for Google OAuth and Sentry
4. **Self-Hosting** section (new) — Docker Compose production deployment with env var table, Caddy auto-TLS note, Alembic auto-migration note
5. **Contributing** expanded with Ruff/ESLint style guidance and issues-first workflow
6. All existing sections preserved: Features, Tech Stack, Architecture, License, Links

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: Rewrite README.md | fdaa9ca | feat(260322-jem): professional open-source README with CI badge and screenshots |

## Self-Check: PASSED

- README.md exists and is 178 lines (under 200-line limit)
- CI badge URL present: `github.com/flawchess/flawchess/actions/workflows/ci.yml/badge.svg`
- 4 screenshot paths present: `frontend/public/screenshots/*.png`
- Self-Hosting section present
- No "coming soon" placeholder text
- Commit fdaa9ca verified in git log
