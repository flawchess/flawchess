---
created: 2026-04-17T10:10:20.889Z
title: Add visual direction for slide generation
area: docs
files:
  - docs/agentic-engineering-flawchess.md
---

## Problem

The workshop doc currently contains only prose and tables. For a 2-hour talk targeting ~40-60 slides, a Marp/reveal.js/PowerPoint generator will produce text-heavy walls unless the source doc explicitly marks what should be visual. No screenshots, terminal recordings, or diagrams are called out.

## Solution

Add inline visual-direction markers per section, e.g.:

- Section 2 (Vibe vs Agentic): the comparison table → render as two-column slide with icons; the tree diagram → render as actual diagram, not ASCII.
- Section 4.1 (CLAUDE.md): screenshot of the FlawChess CLAUDE.md with highlighted sections.
- Section 4.2 (Skills): terminal recording of the `db-report` skill running end to end.
- Section 4.3 (MCPs): diagram of Claude ↔ MCP servers ↔ external systems.
- Section 5.2 (GSD phases): screenshot of `.planning/` tree + artifact file header.
- Section 5.3 (demo): pre-recorded fallback video reference.
- Section 6 (anti-patterns): code snippets as screenshots with callouts.

Use `> **Visual:** ...` callout blocks or a dedicated `**Visuals**:` subsection per chapter so the slide generator can pick them up deterministically.
