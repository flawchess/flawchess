---
type: quick-task-summary
slug: doc-framing-refresh
date: 2026-04-28
status: complete
---

# Refresh PROJECT/CLAUDE/README framing — Summary

Refreshed the user-facing framing in three docs to mirror the homepage's 5-feature
structure. Touched only the lead/intro sections; left history, decisions tables,
architecture, and how-to sections intact.

## Changes

- **`.planning/PROJECT.md`** — rewrote "What This Is" and "Core Value". Now leads
  with the homepage tagline, names all 5 feature areas (Endgame Analytics with
  Endgame ELO + LLM narration, Opening Explorer & Insights with 16-half-move scan,
  Time Management Stats, Opening Comparison, System Opening Filter), and recasts
  Core Value as position-precise WDL across openings + endgames + time pressure
  with personalized LLM commentary. Validated requirements list, Key Decisions
  table, Context, and Constraints unchanged.

- **`CLAUDE.md`** — refreshed "Project" blurb (now mentions openings + endgames +
  time management explicitly) and "Key Features" list. Added Endgame Analytics
  (with `POST /api/insights/endgame` reference) and Time Management Stats; rewrote
  Opening Explorer to mention `POST /api/insights/openings`; kept system opening
  filter, cross-platform import, and PWA. All other sections (commands,
  architecture, server, version control, coding guidelines, Sentry, frontend
  rules) unchanged.

- **`README.md`** — refreshed "What is FlawChess?" lead (drops the
  opening-centric framing for openings + endgames + time management) and the
  "Features" list (now leads with Endgame Analytics, includes Time Management
  Stats, mentions Endgame ELO timeline + LLM-narrated feedback, mentions
  16-half-move opening scan). Tech stack table, getting-started, backups,
  changelog, contributing, license unchanged.

## Out of scope (verified current)

- `MILESTONES.md` — v1.13 entry shipped 2026-04-27; up to date.
- `ROADMAP.md` — v1.13 closed; up to date.
- `STATE.md` — milestone status `completed` at v1.13.

## No commit

Per `CLAUDE.md` "Version Control" rule, working on `main` via `/gsd-quick` does
not auto-commit. Changes left staged in the working tree for the user to review
and commit.
