---
created: 2026-04-17T10:10:20.889Z
title: Fix Section 4 time budget math mismatch
area: docs
files:
  - docs/agentic-engineering-flawchess.md:27-35
---

## Problem

The TOC in the workshop doc allocates 35 minutes to Section 4 (Claude Code building blocks), but the subsection times sum to 32 minutes: 4.1(5) + 4.2(5) + 4.3(5) + 4.4(5) + 4.5(3) + 4.6(3) + 4.7(3) + 4.8(3) = 32. Either the total is wrong or one of the subsections is under-allocated. This also throws off the "Total: ~108 min" figure.

## Solution

- Decide whether to bump Section 4 total down to 32 min (and recover 3 min for buffer) or bump one subsection up (4.1 CLAUDE.md is the most natural candidate for +3 min — it anchors the whole Section 4 framing).
- Recompute the "Total: ~108 min content + 12 min buffer" line to match.
- Trivial fix, but worth doing before slide generation so the time budgets on the agenda slide are consistent.
