---
phase: 82
plan: 04
status: complete
completed: 2026-05-10
---

# Plan 82-04 Summary

Final-mile verification + documentation for Phase 82.

## What was delivered

**Task 1 — Manual UAT (checkpoint:human-verify):** ran live `/endgames` insights against dev DB. Initial run surfaced a regression: `endgame_score` (the new MetricId from Plan 82-01) was missing from the user prompt logged in `llm_logs`; only `endgame_score_timeline` showed. Triaged to two backend bugs in `app/services/insights_llm.py`:

1. `_SECTION_LAYOUT` (line 1266) listed only `overall` and `score_timeline` under `section_id="overall"`. The new `_findings_endgame_start_vs_end` emitter (Plan 82-01) was producing findings, but `_assemble_user_prompt` filtered them out because the section layout did not include the subsection. Fix: insert `("subsection", "endgame_start_vs_end")` between the `overall` scalar block and `score_timeline`.
2. `_format_zone_bounds` was filtering the now-stale `endgame_score` / `non_endgame_score` MetricIds. Those were renamed to `_timeline` variants in Plan 82-01, so the new `endgame_score` (which has a calibrated [0.45, 0.55] band) was inadvertently muted. Fix: update the skip list to `("endgame_score_timeline", "non_endgame_score_timeline")`.

Regression test added: `TestPromptAssembly::test_endgame_start_vs_end_findings_render_in_prompt` exercises `_assemble_user_prompt` against an `endgame_start_vs_end` payload and asserts both findings render under the subsection header. Fix shipped as `fix(82-02): wire endgame_start_vs_end into _SECTION_LAYOUT and unblock zone bounds`.

Re-ran UAT post-fix; user confirmed the prompt now contains:

```
### Subsection: endgame_start_vs_end
[summary entry_eval_pawns]
  all_time: ... zone=typical (typical -50 to +50), quality=rich
  last_3mo: ... zone=typical (typical -50 to +50), quality=rich  shift=-47
[summary endgame_score]
  all_time: ... zone=typical (typical +45 to +55), quality=rich [near edge]
  last_3mo: ... zone=typical (typical +45 to +55), quality=rich [near edge]  shift=-0, within-noise
```

Inline zone bounds render correctly for both metrics; `[near edge]` triggers as expected for the borderline endgame_score.

**Task 2 — CHANGELOG entry:** added three bullets under `## [Unreleased]`:

- One under `### Added`: "Endgame Insights LLM narrates 'Endgame Start vs End' tiles" describing the new subsection, setup→execution framing, Time-Pressure cross-link, and `endgame_v23` cache bump.
- Two under `### Changed`: tile color rule + neutral band tightening; MetricId rename of timeline metrics.

All Plan 04 acceptance grep checks pass:
- `grep -F 'Phase 82' CHANGELOG.md` → 3 hits
- `grep -F 'endgame_start_vs_end' CHANGELOG.md` → 2 hits
- `grep -F 'endgame_v23' CHANGELOG.md` → 1 hit
- `grep -F '±0.5' CHANGELOG.md` → 1 hit

## UAT scenario verdicts

| Scenario | Verdict | Notes |
|----------|---------|-------|
| A — Both findings narrated | pass (post-fix) | Initial run failed: `endgame_score` missing from prompt. Root-caused to `_SECTION_LAYOUT` and fixed; re-run shows both `[summary entry_eval_pawns]` and `[summary endgame_score]` blocks emit correctly. |
| B — Tile color agrees with LLM | pass | `[near edge]` tag triggers on borderline endgame_score (+47% with band [+45, +55]); tile reads neutral. D-14 keystone behavior preserved. |
| C — No regression on Conv/Parity/Recovery | pass | `endgame_metrics` section and per-bucket Conv/Recov narration unchanged. |
| D — Cache invalidation | pass | `_PROMPT_VERSION = "endgame_v23"` bumped; v22 caches auto-invalidate. |
| E — Time Pressure cross-link | pass (in-prompt) | New subsection block instructs the LLM to cross-link `[low-time-gap]` when entry-eval and endgame-score diverge. Live LLM output not separately re-tested but prompt contents verified. |

## Deferred follow-ups

None. The `_SECTION_LAYOUT` regression caught during UAT was fixed in-phase; no prompt-wording follow-ups deferred.

## Pointer to milestone close

The Phase 82 entries land under `## [Unreleased]` in `CHANGELOG.md`. v1.16 milestone close (`/gsd-complete-milestone`) will rename that block to a versioned section per the per-milestone changelog rule in `CLAUDE.md`.
