---
id: 260510-ugj
slug: llm-endgame-prompt-scope-last-3-month-la
description: "LLM endgame prompt: scope last-3-month language and exclude stale-series recent stats"
status: ready
mode: quick
---

# Quick Task 260510-ugj — LLM endgame prompt: scope last-3-month language

## Problem

The endgame insights LLM sometimes quotes `last_3mo` numbers using vague present-tense anchors ("currently sitting at X%", "recently at X%", "now at X%"). The user reads those numbers off the narrative but cannot find them on the dashboard, because the dashboard's headline gauges show `all_time` aggregates — the `last_3mo` value is a different number. The current prompt explicitly *legalises* "Currently sitting at X%" and "Stable at X% over the recent window" in the within-noise legal-frames list, which is exactly the source of the mismatch.

Separately, when a series is `stale: ...` (last bucket >183 days behind newest payload activity), the existing rule says "treat that window as historical — do not frame it as present-day performance" but stops short of forbidding the LLM from quoting the stale window's value at all. The user wants stale-series last-3-month data kept out of the narrative entirely.

## Goal

Tighten `app/prompts/endgame_insights.md` so:

1. **Quoting any `last_3mo` numeric value requires an explicit "last 3 months" anchor.** Vague temporal framings are forbidden for `last_3mo` values: "currently", "recently", "lately", "of late", "now", "today", "at the moment", "the recent window", "right now". Vague present-tense anchors remain acceptable when quoting `all_time` aggregates (those are what the dashboard gauges show).
2. **Stale-series numbers are not narratable.** When a window line carries `stale: ...`, the narrative MUST NOT cite that window's `mean` (or any other numeric field). Stale combos/series may be referenced qualitatively in past tense ("previously played", "historically ranged") but no specific value from the stale window appears in the narration. This explicitly covers the "last 3 months data of stale series" case.

Cache must invalidate on the next request, so bump `_PROMPT_VERSION` in `app/services/insights_llm.py` (`endgame_v23` → `endgame_v24`) with a short rationale comment.

## Tasks

### Task 1 — Update prompt + bump version

**Files:**
- `app/prompts/endgame_insights.md`
- `app/services/insights_llm.py` (only `_PROMPT_VERSION` constant on line 66)

**Action:**

A. In `app/prompts/endgame_insights.md`, replace the "Legal frames when `within-noise` is present" list (lines ~56-60) so it no longer endorses vague temporal anchors:

  - Drop:  `✓ "Currently sitting at X%"` and `✓ "Stable at X% over the recent window"`.
  - Keep:  `✓ "Recent value (last 3 months): X%"` and `✓ "Over the last 3 months: X% (typical over the window)"`.
  - Add at least one more legal frame that pairs an explicit window anchor with a stable framing, e.g. `✓ "Stable over the last 3 months at X%"` and `✓ "All-time aggregate sits at X% (the gauge value)"` so the LLM has a clean way to quote the `all_time` mean too.

B. Add a new top-level rule section directly after "Within-noise rule" titled `## Anchoring window references — last_3mo vs all_time` that says (in prose, second-person voice the prompt already uses, no bullets-of-bullets):
  - When citing a `last_3mo` value, the sentence MUST contain an explicit "last 3 months" anchor (or "in the last 3 months" / "over the last 3 months" / "across the last 3 months"). The user cannot see `last_3mo` aggregates on the dashboard — naming a value without the window anchor leaves them hunting for a number that isn't there.
  - Forbidden anchors when quoting a `last_3mo` value: "currently", "recently", "lately", "of late", "now", "today", "at the moment", "the recent window", "right now", "presently". Use them only when quoting an `all_time` aggregate (the gauge value).
  - When citing an `all_time` mean, prefer "all-time" / "overall" / "across all games" anchors, or simply quote the value without a temporal anchor. Vague present-tense framings ("currently", "today") are acceptable here because the dashboard gauges *are* the `all_time` aggregate.
  - If you only want to mention the metric without a window comparison, prefer the `all_time` value (gauge value) so the narration matches what the user sees.

C. Strengthen the existing "Stale combos" rule on the line that currently reads `Stale combos: when a window line carries 'stale: ...', treat that window as historical — do not frame it as present-day performance.` (around line 141). Replace with stronger wording: when a window line carries `stale: ...`, do NOT cite that window's `mean` (or any numeric field — `n`, `trend`, `std`, bucket counts) in the narrative. Reference the combo qualitatively in past tense ("previously played", "historically ranged at this level") if it adds context, otherwise omit. This rule applies to BOTH the `all_time` and `last_3mo` window lines of a stale series — even when only the `all_time` line is marked stale, the corresponding `last_3mo` data is also treated as not-narratable (it's the same series). The existing "Idle-combo rule (hard)" in the Player profile section is unchanged — it already covers `last_3mo: no data` for combos.

D. In `app/services/insights_llm.py`, bump `_PROMPT_VERSION` from `"endgame_v23"` to `"endgame_v24"` and prepend a short v24 rationale to the trailing comment (keep the v14-v23 history). Suggested phrasing for the v24 fragment:
  `v24 (260510-ugj): tightened last_3mo narration anchors — quoting any last_3mo value now requires an explicit "last 3 months" framing, and the within-noise legal-frames list no longer endorses vague "currently sitting at X%" / "over the recent window" forms that confused users by naming numbers absent from the dashboard. Stale-series rule strengthened: stale window numbers (mean, n, trend, std) must not appear in the narrative at all — past-tense qualitative reference only.`

**Verify:**
- `grep -n "Currently sitting at X%" app/prompts/endgame_insights.md` returns no hits (line removed).
- `grep -n "over the recent window" app/prompts/endgame_insights.md` returns no hits (line removed).
- `grep -n "Anchoring window references" app/prompts/endgame_insights.md` returns the new section header.
- `grep -n "do NOT cite that window" app/prompts/endgame_insights.md` returns the strengthened stale rule.
- `grep -n "_PROMPT_VERSION" app/services/insights_llm.py` shows `endgame_v24`.
- `uv run ty check app/` passes (no signature changes, but sanity check).
- Existing tests still pass: `uv run pytest tests/test_insights_llm_thinking.py tests/test_insights_router.py -q` — these are markdown/version-aware and may or may not need updating; if any test asserts on the old version string or the removed legal frames, update the assertion to match the new wording.

**Done when:**
- Prompt edits applied, `_PROMPT_VERSION` bumped, ty + pytest pass for the two test files above (and any others that touched prompt strings).

## must_haves

- Prompt explicitly forbids vague temporal anchors ("currently", "recently", "now", "today", "lately", "of late", "the recent window", "at the moment", "right now", "presently") for `last_3mo` values.
- Prompt requires explicit "last 3 months" anchor whenever a `last_3mo` numeric value appears in the narration.
- Prompt's stale rule forbids citing any numeric field of a `stale: ...` window in the narrative.
- `_PROMPT_VERSION` bumped so cached LLM reports are invalidated on next request.
