---
type: quick-task
slug: doc-framing-refresh
date: 2026-04-28
---

# Refresh PROJECT/CLAUDE/README framing to match current homepage

The user-facing framing in `PROJECT.md`, `CLAUDE.md`, and `README.md` has drifted from
what FlawChess actually does. The homepage now leads with Endgame Analytics (with
Endgame ELO timeline + LLM-personalized feedback) and lists Time Management Stats as a
top-level feature. None of these surface in the doc framing.

## Scope

1. `PROJECT.md` — rewrite "What This Is", "Core Value", and "Current State" lead
   sentences to reflect the homepage's 5-feature framing. Leave the Validated
   Requirements list, Key Decisions table, Context, and Constraints untouched —
   they're history, not outdated framing.
2. `CLAUDE.md` — refresh the "Project" blurb and "Key Features" list to match the
   homepage. Leave commands, architecture, server, version control, and coding
   guidelines as-is.
3. `README.md` — refresh "What is FlawChess?" lead and the "Features" bullet list.
   Leave tech stack, getting started, backups, and contributing as-is.

## Out of scope

- MILESTONES.md, ROADMAP.md, STATE.md (already current).
- The accumulated `Validated` requirements list in PROJECT.md (history, not framing).
- Adding new product copy beyond what the homepage already says.

## Acceptance

- The three doc lead sections reference: Opening Explorer & Insights, Endgame
  Analytics (with Endgame ELO + LLM feedback), Time Management Stats, Opening
  Comparison, System Opening Filter.
- No bloat: each feature gets at most one tight bullet.
- Tagline "Engines are flawless, humans play FlawChess" preserved where it appears.
