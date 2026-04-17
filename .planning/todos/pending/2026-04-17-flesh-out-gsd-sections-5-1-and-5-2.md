---
created: 2026-04-17T10:10:20.889Z
title: Flesh out GSD sections 5.1 and 5.2
area: docs
files:
  - docs/agentic-engineering-flawchess.md:343-344
---

## Problem

Sections 5.1 (Why structure matters) and 5.2 (Phases/roadmap) are each ~1 bullet line for 10+ minutes of combined talk time. The live demo in 5.3 is well specified, but 5.1/5.2 need to sell the structure itself before the demo — otherwise the demo looks like arbitrary ceremony.

## Solution

- 5.1: expand to 3-4 concrete failure modes of unstructured agents (drift, re-implementation, context loss, silent over-engineering) with a one-line example each from FlawChess history.
- 5.2: pick a specific completed phase in `.planning/` and walk its artifact chain: DISCUSS.md → PLAN.md → RESEARCH.md → VERIFICATION.md. Name the phase explicitly in the doc so the slide generator knows which files to reference/screenshot.
- Candidate phases to feature: Phase 59 or 60 (recently completed per ROADMAP), or Phase 61 (test hardening).
- Add a diagram of the four-gate flow (discuss → plan → execute → verify) with what each gate catches.
