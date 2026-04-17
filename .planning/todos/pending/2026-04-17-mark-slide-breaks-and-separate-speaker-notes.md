---
created: 2026-04-17T10:10:20.889Z
title: Mark slide breaks and separate speaker notes
area: docs
files:
  - docs/agentic-engineering-flawchess.md
---

## Problem

The doc currently mixes two kinds of content without separation: (a) what goes on the slide (title + short bullets) and (b) what the presenter says out loud (speaker notes). Some sections read like slide bullets, others read like a written essay. A slide generator cannot tell the difference, so it will either dump whole paragraphs onto slides or strip context needed for delivery.

## Solution

- Introduce explicit slide-break markers (Marp convention: `---` on its own line, or `## Slide: <title>` headings).
- Split each section into SLIDE content (≤6 bullets, ≤8 words each) and SPEAKER NOTES (the prose currently written).
- Marp supports `<!-- _notes: ... -->` blocks; reveal.js supports `Note:` sections. Pick one convention up front.
- Target cadence: ~40-60 slides for 2 hours → roughly one slide per 2-3 minutes. Section 4 alone should be ~12-15 slides, not one giant slide.
- Do this last — after Sections 1, 3, 5.1, 5.2 are fleshed out and the Karpathy attribution is resolved, so the split reflects final content.
