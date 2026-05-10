---
id: 260510-ugj
slug: llm-endgame-prompt-scope-last-3-month-la
phase: quick
plan: "260510-ugj"
subsystem: llm-insights
tags: [prompt-engineering, endgame-insights, cache-invalidation]
key-files:
  modified:
    - app/prompts/endgame_insights.md
    - app/services/insights_llm.py
decisions:
  - Kept new "Anchoring window references" section in second-person voice matching the prompt's existing style
  - Stale rule covers both all_time and last_3mo window lines of the same series to prevent partial quoting
metrics:
  completed: 2026-05-10
  tasks: 1
  files: 2
---

# Quick Task 260510-ugj: LLM Endgame Prompt — Scope last-3mo Language

## Overview

Tightened the endgame insights LLM system prompt so the model must always pair a `last_3mo` numeric value with an explicit "last 3 months" anchor phrase. The root cause was that the within-noise legal-frames list explicitly endorsed "Currently sitting at X%" and "Stable at X% over the recent window" — both of which quote a `last_3mo` number without naming the window, leaving users unable to find the value on the dashboard (which shows `all_time` aggregates). The stale-combo rule was also strengthened from a framing advisory ("treat as historical") to a hard prohibition on citing any numeric field from a stale window.

`_PROMPT_VERSION` bumped from `endgame_v23` to `endgame_v24` to invalidate cached LLM reports on the next request.

## Diff Summary

### `app/prompts/endgame_insights.md`

**Removed from "Legal frames when `within-noise` is present":**
```
- ✓ "Currently sitting at X%"
- ✓ "Stable at X% over the recent window"
```

**Added to "Legal frames when `within-noise` is present":**
```
- ✓ "Stable over the last 3 months at X%"
- ✓ "All-time aggregate sits at X% (the gauge value)"
```

**Added new section** immediately after the within-noise rule block (line 64 in the updated file):
```
## Anchoring window references — last_3mo vs all_time
```
This section forbids the following anchors when quoting a `last_3mo` value: "currently", "recently", "lately", "of late", "now", "today", "at the moment", "the recent window", "right now", "presently". It also clarifies that vague present-tense anchors are acceptable when quoting `all_time` aggregates.

**Replaced stale combos rule** (line 151 in updated file): original one-sentence advisory replaced with a full-paragraph hard prohibition that forbids citing any numeric field (`mean`, `n`, `trend`, `std`, bucket counts) from a stale window. The new rule explicitly covers both `all_time` and `last_3mo` window lines of the same series.

### `app/services/insights_llm.py`

**Line 66:** Changed `_PROMPT_VERSION` from `"endgame_v23"` to `"endgame_v24"`. Prepended v24 rationale fragment to the existing trailing comment block (v14-v23 history preserved unchanged).

## Test Results

```
uv run ty check app/ tests/
  → All checks passed!

uv run pytest tests/test_insights_llm_thinking.py tests/test_insights_router.py -q
  → 24 passed in 1.97s
```

No test assertions on the old prompt version string or the removed legal frames were found. All 24 tests passed without modification.

## Verification Checks

1. `grep "Currently sitting at X%" app/prompts/endgame_insights.md` → 0 hits (PASS)
2. `grep "over the recent window" app/prompts/endgame_insights.md` → 0 hits (PASS)
3. `grep "Anchoring window references" app/prompts/endgame_insights.md` → 1 hit at line 64 (PASS)
4. `grep "do NOT cite that window" app/prompts/endgame_insights.md` → 1 hit at line 151 (PASS)
5. `grep "endgame_v24" app/services/insights_llm.py` → 1 hit at line 66 (PASS)
6. `uv run ty check app/ tests/` → exit 0 (PASS)
7. `uv run pytest tests/test_insights_llm_thinking.py tests/test_insights_router.py -q` → 24 passed, exit 0 (PASS)

## Deviations from Plan

None. The plan was followed exactly:
- Actions A, B, C, D all executed as specified.
- No tests needed updating (none asserted on the removed legal frames or the old version string).
- The new section uses second-person voice and concrete ✓/✗ framing consistent with the surrounding prompt style where applicable.

## Commit

`2a13c2e7` — `docs(prompt): scope last-3mo language in endgame insights LLM prompt (260510-ugj)`
