---
phase: 87.4-drop-endgame-skill-conversion-elo-timeline
plan: 03
subsystem: llm-prompt
tags: [llm-prompt, conversion-elo, changelog, todo-migration]
requires:
  - .planning/milestones/v1.17-phases/87.4-drop-endgame-skill-conversion-elo-timeline/03-PLAN.md
  - .planning/milestones/v1.17-phases/87.4-drop-endgame-skill-conversion-elo-timeline/01-SUMMARY.md
provides:
  - _PROMPT_VERSION = "endgame_v32" on app/services/insights_llm.py
  - _conversion_elo_per_bucket (renamed from _endgame_elo_per_bucket)
  - _render_conversion_elo_summary_block (renamed from _render_endgame_elo_summary_block)
  - "[summary conversion_elo | ...]" rendered header literal
  - "Conversion ELO Timeline" subsection prose + conversion_elo / conversion_elo_gap glossary entries
  - CHANGELOG.md [Unreleased] entries for Phase 87.4 (Skill drop, Conv ELO rename, display-centering)
  - Migrated folded todo at .planning/todos/done/2026-05-16-conversion-score-gap-display-centering.md
affects:
  - app/services/insights_llm.py
  - app/prompts/endgame_insights.md
  - tests/prompts/test_endgame_insights_prompt.py (new)
  - tests/services/test_insights_llm.py
  - CHANGELOG.md
  - .planning/todos/pending/2026-05-16-conversion-score-gap-display-centering.md → .planning/todos/done/
tech-stack:
  added: []
  patterns:
    - append-only changelog blob with new entry prepended at FRONT (preserves chronological history backwards)
    - grep-style prompt regression tests in tests/prompts/ (no full-file snapshots; tracks specific MUST / MUST NOT substrings)
    - git-mv todo migration (rename detection preserves history at R079)
key-files:
  created:
    - tests/prompts/test_endgame_insights_prompt.py
  modified:
    - app/services/insights_llm.py
    - app/prompts/endgame_insights.md
    - tests/services/test_insights_llm.py
    - CHANGELOG.md
    - .planning/todos/done/2026-05-16-conversion-score-gap-display-centering.md
decisions:
  - "v32 changelog blob prepended at the FRONT of the inline append-only comment on line 68 of insights_llm.py (preserves v31 / v30 / v29 / ... entries verbatim). Length added: ~1.7k chars (one paragraph). Single space separator between v32 and v31 entries; no newline reflow inside the blob."
  - "Skill glossary deletion is a hard delete, not a soft retire — the Skill concept has no successor metric the prompt would point to; Conv ΔES Score Gap is structurally first in _SECTION2_BUCKETS so the LLM naturally leads with it."
  - "Conversion ELO definition wording: 'what your ELO would be if everyone played the way you do when up material' (verbatim from .planning/notes/endgame-skill-dropped-conversion-elo.md LOCKED design). Recenter prose phrased via the user-facing 'Conversion Score Gap' term — the internal `ΔES` / `delta_es` tokens are forbidden in narration per CONTEXT D-10 (TestPromptVersionAndBody::test_prompt_glossary_defines_endgame_type_score_gap regression guard)."
  - "Display-centering todo migrated via `git mv`. Rename detection at R079 preserves the file's prior 8f3e6991 / 94acce20 history. `## Outcome` section appended in-place noting the FE-only scope per D-04 and the moot Skill bullet (concept retired in Plan 01)."
  - "No historical 'Phase 57 Endgame ELO formula' attribution line was kept — the recenter docstring uses 'unchanged Phase 57 formula' without naming the retired metric, so no whitelist regex was needed in the Wave 0 prompt regression test."
metrics:
  duration_minutes: 45
  tasks_completed: 4
  tasks_total: 4
  commits:
    - 6982303d test(87.4-03): add Wave 0 RED tests for v32 prompt + Skill removal
    - eb3ea848 refactor(87.4-03): bump _PROMPT_VERSION to endgame_v32 + rename Conversion ELO helpers
    - 5e36185d refactor(87.4-03): rename Endgame ELO → Conversion ELO + drop Skill glossary in prompt
    - df97082f docs(87.4-03): CHANGELOG entry + migrate folded display-centering todo
    - 9ca8e325 style(87.4-03): ruff-format test_insights_llm.py
  completed_date: 2026-05-16
---

# Phase 87.4 Plan 03: LLM payload + prompt + CHANGELOG update Summary

Bumped `_PROMPT_VERSION` from `endgame_v31` to `endgame_v32` with a v32
changelog entry prepended at the FRONT of the inline append-only blob;
renamed every `endgame_elo` / `endgame_skill` identifier and prose mention
in both `app/services/insights_llm.py` and `app/prompts/endgame_insights.md`
to the Conversion ELO equivalents; deleted the Endgame Skill glossary entry
and metric-table row from the prompt; added a CHANGELOG `[Unreleased]`
entry narrating the three Phase 87.4 deliveries (Skill drop, Conv ELO
Timeline rename, Conv/Parity/Recov display-centering); and migrated the
folded display-centering todo from `pending/` to `done/` via `git mv`
with an `## Outcome` section appended.

The v32 entry narrates Skill removal end-to-end, the `endgame_elo_*`
→ `conversion_elo_*` rename, Conv ΔES Score Gap structurally promoted to
the primary Section 2 finding, the affine recenter formula
`s = clamp(0.5 + α·(conv_ΔES − PIVOT), 0.05, 0.95)` with `PIVOT = -0.0474`,
and the FE display-shift triple (Conv -0.055, Parity 0, Recov +0.06).

## Tasks

### Task 1 — Wave 0 RED tests

New `tests/prompts/test_endgame_insights_prompt.py` with seven grep-style
assertions on `app/prompts/endgame_insights.md`:

- `test_no_endgame_skill_text` — case-insensitive "endgame skill" + literal
  "endgame_skill" both absent.
- `test_no_endgame_elo_timeline_id` — legacy subsection id absent.
- `test_no_endgame_elo_gap_id` — legacy metric id absent.
- `test_conversion_elo_timeline_subsection_present` — new heading prose.
- `test_conversion_elo_timeline_id_present` — new subsection id wires up.
- `test_conversion_elo_gap_id_present` — new metric id present.
- `test_no_endgame_elo_phrase_in_prose` — case-insensitive "endgame elo"
  absent (no whitelisted Phase 57 attribution line — see Decision 5).

Extended `tests/services/test_insights_llm.py` with a new
`TestPhase874PromptVersion` class:

- `test_prompt_version_is_v32` — `insights_llm._PROMPT_VERSION == "endgame_v32"`.
- `test_non_fractional_metrics_renamed` — `conversion_elo_gap` in
  `_NON_FRACTIONAL_METRICS`, `endgame_elo_gap` absent.
- `test_no_endgame_skill_payload_field` — `inspect.getsource(insights_llm)`
  contains no quoted-string `"endgame_skill"` /
  `"section2_score_gap_skill"` / `"endgame_skill_rate_mean"` literals (bare
  identifiers inside the v32 changelog narrative are intentionally exempt
  — the assertion targets quoted strings only).

RED state confirmed at commit `6982303d`: 8 of 10 new assertions fail
(the 2 passing tests are the renamed-constants checks Plan 01 had already
made green). Tasks 2-3 turn the remaining 8 GREEN.

### Task 2 — insights_llm.py v32 bump + identifier renames

**Prompt version bump.** Changed the `_PROMPT_VERSION` literal on line 68
of `app/services/insights_llm.py` from `"endgame_v31"` to `"endgame_v32"`
and prepended a new v32 entry at the FRONT of the existing inline comment
blob. The v32 entry narrates Skill removal end-to-end, the
`endgame_elo_timeline` → `conversion_elo_timeline` rename, the
`endgame_elo_gap` → `conversion_elo_gap` rename, the Conv ΔES Score Gap
promotion to primary Section 2 finding, the affine recenter formula,
`PIVOT = -0.0474`, the Conversion ELO definition, and the FE
display-shift triple. Format: `# v32 (260516 Phase 87.4 ...): ... v31
(260515 Phase 87.2 ...): ...` — single space separator between the v32
and v31 entries; no newline reflow inside the blob; v31 and all prior
entries preserved verbatim.

**Helper renames.**
- `_endgame_elo_per_bucket` → `_conversion_elo_per_bucket`.
- `_render_endgame_elo_summary_block` → `_render_conversion_elo_summary_block`.
- Callsite inside `_render_subsection_block` updated in lockstep.
- Rendered header literal `"[summary endgame_elo"` →
  `"[summary conversion_elo"`.

**Docstring + comment renames** (no behavior change).
- `_proximity_hint` docstring updated to reference `conversion_elo_gap`.
- `_render_series_block` docstring updated to reference
  `conversion_elo_gap` variant.
- Within-noise-ELO inline comment updated to reference `conversion_elo_gap`.
- v11 trend-flat-threshold-ELO comment updated to reference the renamed
  `[summary conversion_elo]` block.
- Caller-site v11 comment for the conversion_elo_timeline subsection
  consolidated with a Phase 87.4 D-06 note about the rename lockstep.

**Plan 01 leftover.** Plan 01 had already renamed all *quoted-string*
literals (`"endgame_elo_timeline"`, `"endgame_elo_gap"`,
`"endgame_skill"`, `"section2_score_gap_skill"`) and the user-facing
sentinel copy (`"no Endgame ELO trajectory available yet"` →
`"no Conversion ELO trajectory available yet"`) in this file. Plan 03's
job in this file was the prompt-version bump + identifier renames at the
Python-symbol layer. The remaining `grep -n endgame_elo app/services/insights_llm.py`
hits are explanatory comments referencing the rename — these are
intentional historical context for future readers and do not appear as
quoted-string code literals.

**Test updates** (consequence of the v32 bump + helper renames; not new
behavior).
- `test_prompt_version_is_v31` → `test_prompt_version_is_v32` (Phase 83
  class) and `test_prompt_version_bumped_to_v31` →
  `test_prompt_version_bumped_to_v32` (Phase 87.2 class). The latter
  also gained Phase 87.4 substring assertions (v32 entry present, Skill
  removal narrative present, affine recenter formula present,
  "Conversion ELO" present).
- The "Phase 87.2 cache key" test now expects `endgame_v32` on the
  response-report `prompt_version` field and the log-row
  `response_json["prompt_version"]`.
- `test_endgame_elo_summary_emitted_before_gap_summary` →
  `test_conversion_elo_summary_emitted_before_gap_summary` (header
  literal change `"[summary endgame_elo"` →
  `"[summary conversion_elo"`).
- `test_endgame_elo_summary_skipped_when_actual_elo_missing` →
  `test_conversion_elo_summary_skipped_when_actual_elo_missing` (same
  header literal change).

### Task 3 — endgame_insights.md prompt rename + Skill glossary drop

**Metric glossary table** (around L83–L90):
- Deleted the `endgame_skill` row entirely.
- Renamed `endgame_elo` → `conversion_elo`; updated the label column from
  "Endgame ELO" → "Conversion ELO".
- Renamed `endgame_elo_gap` → `conversion_elo_gap`; updated the label
  column from "Endgame ELO gap" → "Conversion ELO gap".

**Near-edge marker rule** (L99): renamed the `endgame_elo_gap` reference
to `conversion_elo_gap`.

**Series-block rules** (L132 / L138 / L140-L144):
- Renamed `endgame_elo_timeline` → `conversion_elo_timeline` in the
  three-subsection list.
- Updated the per-row pairing rule to use `conversion_elo_timeline` and
  reframed the "endgame skill composite" prose as "Conversion ELO
  composite (their conversion strength is not keeping pace with their
  overall rating climb)".
- Renamed the "absolute Endgame ELO" sentence to "absolute Conversion ELO"
  and gave it the new definition framing (LOCKED-design wording).
- Renamed pairing-rule prose to use "Conversion ELO" / `conversion_elo_gap`.

**Stale-combo rule** (L152): renamed `endgame_elo_gap` → `conversion_elo_gap`.

**Cross-section stories rule** (L190 / L193):
- "Composure-under-pressure bottleneck": replaced the `endgame_skill`
  typical-or-strong condition with "typical-or-strong Conv/Parity/Recov
  rates" (the underlying signal is the three buckets' zones, not the
  retired composite).
- "Skill lagging rating growth" → "Conversion lagging rating growth";
  identifier rename in lockstep.

**Multiple-combo rule** (L251–L259): renamed heading + body from
"Endgame ELO" to "Conversion ELO" throughout; reframed the
learning-arc cross-reference as "conversion strength is lagging rating
growth" rather than "endgame skill is lagging rating growth".

**Glossary definitions** (L428–L443):
- Deleted the `endgame_skill` paragraph in full.
- Rewrote the `endgame_elo` glossary → `conversion_elo`: "what your ELO
  would be if everyone played the way you do when up material" (LOCKED
  design verbatim); replaced the inline formula with a prose description
  of the affine recenter against the Conversion Score Gap (no internal
  `ΔES` token — see Decision 3); preserved the chart-headline-value /
  primary-narration-value rule.
- Rewrote the `endgame_elo_gap` glossary → `conversion_elo_gap`:
  `conversion_elo − actual_elo`; preserved the zone-interpretation
  rule and the series-row `gap=` + `elo=` framing.

**Section mapping table** (L472): renamed `endgame_elo_timeline` →
`conversion_elo_timeline`.

**`metrics_elo` coverage floor rule** (L492):
- Dropped "Endgame Skill AND" — rule now reads "all three buckets"
  (Conv/Parity/Recov).
- Renamed "Endgame ELO per-combo bullets" → "Conversion ELO per-combo
  bullets".

### Task 4 — CHANGELOG entry + folded todo migration

**CHANGELOG.md `[Unreleased]`** — appended three new bullets, grouped
into the existing `### Changed` and `### Removed` subsections:

`### Changed`:
- "Phase 87.4: Endgame ELO Timeline renamed to Conversion ELO Timeline.
  The timeline is now fed by the Conversion Score Gap (Phase 87.2) routed
  through a frozen affine recenter into the unchanged Phase 57 formula.
  Conversion ELO answers: what your ELO would be if everyone played the
  way you do when up material. LLM Insights prompt updated end-to-end;
  prompt version bumps `endgame_v31` → `endgame_v32` so prior cached
  reports regenerate with the new framing. See
  `.planning/notes/endgame-skill-dropped-conversion-elo.md` for the full
  rationale."
- "Phase 87.4: Conversion, Parity, and Recovery Score Gap bullets are now
  display-centered on the typical-population result. A display-only
  affine shift is applied to each bullet (Conversion −0.055, Recovery
  +0.06, Parity 0) so a player at the cohort midpoint renders at the
  chart center instead of the top of the band. Underlying LLM zone bands,
  cohort thresholds, and zone-color cutoffs are unchanged."

`### Removed`:
- "Phase 87.4: Endgame Skill concept dropped end-to-end. No composite
  definition (arithmetic mean, percentile composite, rate aggregate)
  survived scrutiny on cohort de-confounding, individual absolute-skill
  interpretation, per-window temporal stability, and the Phase 57
  median-coincide invariant. The Endgame Skill card, the Skill Score Gap
  card, the `endgame_skill` / `section2_score_gap_skill` LLM payload
  findings, and the Endgame Skill glossary entries in the LLM prompt are
  all removed. The Conversion ELO Timeline now stands in as the headline
  composite measure of endgame strength. See
  `.planning/notes/endgame-skill-dropped-conversion-elo.md` for the full
  rationale."

No prior released section modified.

**Folded todo migration**:
- `git mv .planning/todos/pending/2026-05-16-conversion-score-gap-display-centering.md
  .planning/todos/done/...` — git rename detection at R079 (79% similarity)
  preserves the file's prior 8f3e6991 / 94acce20 history.
- Appended `## Outcome` section in-place recording: completion in Phase
  87.4 (Plan 02 frontend rewire), uniform shift across Conv/Parity/Recov
  per CONTEXT.md D-03, FE-only per D-04, link to 02-SUMMARY.md, and a
  note that the "Skill bullet" referenced in the original scope notes
  became moot when Phase 87.4 dropped Endgame Skill end-to-end.

## Decisions Made

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Prepend v32 entry at FRONT of inline blob | Established append-only blob pattern (D-08): newer entries land first; older entries unmodified. | ✓ v31 and all prior entries preserved verbatim. |
| Hard delete the Skill glossary entry, no soft retire | The Skill concept has no successor metric the prompt would point to. Conv ΔES Score Gap is structurally first in `_SECTION2_BUCKETS` so the LLM naturally leads with it without a glossary entry. | ✓ Wave 0 grep test asserts zero references. |
| Phrase the recenter prose without internal `ΔES` token | CONTEXT D-10 forbids `ΔES` / `delta_es` in user-facing narration; the existing `test_prompt_glossary_defines_endgame_type_score_gap` test enforces it. Use the user-facing "Conversion Score Gap" term instead. | ✓ Prompt prose readable to LLM, conceptually faithful to the affine recenter, no forbidden tokens. |
| No "Phase 57 Endgame ELO formula" historical attribution line | The recenter glossary uses "unchanged Phase 57 formula" without naming the retired metric. Cleaner; no whitelist regex needed in the Wave 0 prompt regression test. | ✓ `test_no_endgame_elo_phrase_in_prose` is a strict-no-exception assertion. |
| Reword cross-section bottleneck story | The original "endgame_skill typical-or-strong" condition referenced the retired composite. Rewrote to "typical-or-strong Conv/Parity/Recov rates" — the underlying signal is the three buckets' zones. | ✓ Cross-section story preserved; condition no longer references a deleted metric. |
| `git mv` for todo rename (not delete + add) | Preserves file history (git log --follow shows R079 rename). CLAUDE.md Version Control rule. | ✓ Rename detected; history intact. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocker] Existing pytest assertions on `endgame_v31`**

- **Found during:** Task 2 ty/pytest sweep.
- **Issue:** Five existing assertions in `tests/services/test_insights_llm.py`
  asserted `_PROMPT_VERSION == "endgame_v31"` (lines 214, 372, 452, 2656,
  2681), plus the test class name `test_prompt_version_is_v31` /
  `test_prompt_version_bumped_to_v31`. Plan Task 2 acceptance criteria
  required `pytest -x` to be green, which is incompatible with leaving
  these v31 assertions in place. Plan 03's purpose is the v32 bump.
- **Fix:** Renamed the two test methods to `test_prompt_version_is_v32` /
  `test_prompt_version_bumped_to_v32`; updated the assertion bodies to
  `"endgame_v32"`; extended the bumped-version test with Phase 87.4
  substring assertions (Skill removal, affine recenter formula,
  Conversion ELO terminology); updated the two cache-key / log-row
  assertions to expect `"endgame_v32"`.
- **Files modified:** `tests/services/test_insights_llm.py`.
- **Commit:** `eb3ea848` (Task 2).

**2. [Rule 3 — Blocker] Existing tests referenced the old
`"[summary endgame_elo` header literal**

- **Found during:** Task 2 pytest sweep.
- **Issue:** Two tests in `TestV6Enrichments`
  (`test_endgame_elo_summary_emitted_before_gap_summary` and
  `test_endgame_elo_summary_skipped_when_actual_elo_missing`) asserted
  the old `"[summary endgame_elo | platform=..."` and
  `"[summary endgame_elo |"` substrings in the rendered prompt.
  Task 2's header literal rename
  (`"[summary endgame_elo"` → `"[summary conversion_elo"`) broke them.
- **Fix:** Renamed both test methods to use `conversion_elo` in the
  test name and updated all header-substring assertions to use the new
  `"[summary conversion_elo"` literal. Preserved every other test
  assertion in lockstep (the weighted-mean number, the bucket count,
  the no-zone / no-quality rule).
- **Files modified:** `tests/services/test_insights_llm.py`.
- **Commit:** `eb3ea848` (Task 2).

**3. [Rule 1 — Bug] Glossary prose initially used the forbidden `ΔES`
token**

- **Found during:** Task 3 pytest sweep.
- **Issue:** The first pass at the `conversion_elo` glossary entry used
  the formula `s = clamp(0.5 + α · (conv_ΔES − PIVOT), 0.05, 0.95)` and
  named the metric "Conversion ΔES Score Gap". This made
  `test_prompt_glossary_defines_endgame_type_score_gap` fail — CONTEXT
  D-10 forbids `ΔES` / `delta_es` in user-facing narration outside an
  explicit "Forbidden" / "Incorrect" / "Do not use" list. The reference
  exception bypass would have polluted the glossary with a non-rationale
  caveat; the cleaner fix is to drop the internal token.
- **Fix:** Rewrote the recenter prose to use the user-facing term
  "Conversion Score Gap" and described the recenter in words ("affine
  recenter of the windowed Conversion Score Gap" + "when the windowed
  Conversion Score Gap sits at the population median, the recenter
  returns `s = 0.5` and Conversion ELO equals actual ELO"). The
  mathematical content is preserved without the internal jargon.
- **Files modified:** `app/prompts/endgame_insights.md`.
- **Commit:** `5e36185d` (Task 3).

**4. [Rule 1 — Bug] ruff format wanted single-line collapses on two
asserts**

- **Found during:** post-Task 3 broad-suite quality gate.
- **Issue:** Two `assert ..., ("...")` blocks I introduced wrapped over
  multiple lines (line length comfortably under the 100-column limit)
  but ruff format wanted the single-line form. Plus a trailing blank
  line at EOF.
- **Fix:** `uv run ruff format tests/services/test_insights_llm.py`.
  Pure whitespace change; no behavior delta.
- **Files modified:** `tests/services/test_insights_llm.py`.
- **Commit:** `9ca8e325` (post-Task 4).

## Authentication Gates

None — backend prompt + docs change; no external services touched.

## Verification

- `uv run ty check app/ tests/` — clean.
- `uv run ruff check .` — clean.
- `uv run ruff format --check app/services/insights_llm.py
  app/prompts/endgame_insights.md tests/services/test_insights_llm.py
  tests/prompts/test_endgame_insights_prompt.py` — clean for the files
  Plan 03 touched. (47 unrelated repo-wide format issues are pre-existing
  and out of scope per the SCOPE BOUNDARY rule.)
- `uv run pytest tests/prompts/ tests/services/test_insights_llm.py
  tests/services/test_insights_service.py
  tests/services/test_insights_service_series.py
  tests/services/test_endgame_zones.py
  tests/services/test_conversion_elo_recenter.py
  tests/schemas/test_endgames_schema.py tests/test_endgame_service.py`
  — **553 passed in 1.70s**. No regressions.
- Final acceptance grep sweep:
  - `! grep -iE "endgame skill|endgame_skill|endgame_elo_timeline|endgame_elo_gap|endgame elo" app/prompts/endgame_insights.md` — zero matches.
  - `grep -q "Conversion ELO Timeline" app/prompts/endgame_insights.md` — match.
  - `grep -q "conversion_elo_timeline\|conversion_elo_gap" app/prompts/endgame_insights.md` — matches.
  - `grep -q '_PROMPT_VERSION = "endgame_v32"' app/services/insights_llm.py` — match.
  - `grep -c "v31 (260515 Phase 87.2" app/services/insights_llm.py` — 1 (v31 entry preserved).
  - `grep -iE "phase 87\.4|conversion elo timeline" CHANGELOG.md` — 3 hits in `[Unreleased]`.
  - `test ! -f .planning/todos/pending/2026-05-16-conversion-score-gap-display-centering.md` — true.
  - `test -f .planning/todos/done/2026-05-16-conversion-score-gap-display-centering.md` — true.
  - `git log --diff-filter=R --follow` shows R079 rename — confirmed `git mv` was used.

## Final v32 Blob Position + Length

- **Position:** prepended at the FRONT of the inline `# v… (… ): …` comment
  on `app/services/insights_llm.py` line 68. Reads: `_PROMPT_VERSION =
  "endgame_v32"  # v32 (260516 Phase 87.4 Conversion ELO rewire): …
  v31 (260515 Phase 87.2 Section 2 ΔES Score Gap family): … v30 …`.
- **Length added:** ~1,680 characters (one paragraph, includes the formula,
  the PIVOT value, the display-shift triple, the dual-label terminology
  rule). No newline reflow inside the blob; single space separator
  between v32 and v31 entries.

## CHANGELOG Entry Bullets (verbatim)

`### Changed`:
- **Phase 87.4: Endgame ELO Timeline renamed to Conversion ELO Timeline.**
  The timeline is now fed by the Conversion Score Gap (Phase 87.2) routed
  through a frozen affine recenter into the unchanged Phase 57 formula.
  Conversion ELO answers: what your ELO would be if everyone played the
  way you do when up material. LLM Insights prompt updated end-to-end;
  prompt version bumps `endgame_v31` → `endgame_v32` so prior cached
  reports regenerate with the new framing. See
  `.planning/notes/endgame-skill-dropped-conversion-elo.md` for the full
  rationale.
- **Phase 87.4: Conversion, Parity, and Recovery Score Gap bullets are
  now display-centered on the typical-population result.** A display-only
  affine shift is applied to each bullet (Conversion −0.055, Recovery
  +0.06, Parity 0) so a player at the cohort midpoint renders at the
  chart center instead of the top of the band. Underlying LLM zone bands,
  cohort thresholds, and zone-color cutoffs are unchanged.

`### Removed`:
- **Phase 87.4: Endgame Skill concept dropped end-to-end.** No composite
  definition (arithmetic mean, percentile composite, rate aggregate)
  survived scrutiny on cohort de-confounding, individual absolute-skill
  interpretation, per-window temporal stability, and the Phase 57
  median-coincide invariant. The Endgame Skill card, the Skill Score Gap
  card, the `endgame_skill` / `section2_score_gap_skill` LLM payload
  findings, and the Endgame Skill glossary entries in the LLM prompt are
  all removed. The Conversion ELO Timeline now stands in as the headline
  composite measure of endgame strength. See
  `.planning/notes/endgame-skill-dropped-conversion-elo.md` for the full
  rationale.

## Todo Migration Confirmation

```
$ git log --follow --name-status --pretty=format:'%h %s' -3 \
    .planning/todos/done/2026-05-16-conversion-score-gap-display-centering.md
df97082f docs(87.4-03): CHANGELOG entry + migrate folded display-centering todo
R079    .planning/todos/pending/...md   .planning/todos/done/...md

8f3e6991 docs: retract 87.3 percentile composite; insert phase 87.4 Conversion ELO (#102)
M       .planning/todos/pending/...md

94acce20 Phase 87.2: Section 2 — eval-based ΔES Score Gap bullets (#98)
A       .planning/todos/pending/...md
```

`R079` = git detected a rename with 79% similarity. The file's prior
history (M at 8f3e6991, A at 94acce20) is preserved through `--follow`.

## Test Result Summary

| Suite | Tests | Result |
|-------|-------|--------|
| `tests/prompts/test_endgame_insights_prompt.py` | 7 | ✓ all pass |
| `tests/services/test_insights_llm.py` | 96 | ✓ all pass |
| `tests/services/test_insights_service.py` | 68 | ✓ all pass |
| `tests/services/test_insights_service_series.py` | 18 | ✓ all pass |
| `tests/services/test_endgame_zones.py` | 41 | ✓ all pass |
| `tests/services/test_conversion_elo_recenter.py` | 9 | ✓ all pass |
| `tests/schemas/test_endgames_schema.py` | 4 | ✓ all pass |
| `tests/test_endgame_service.py` | 310 | ✓ all pass |
| **Total** | **553** | **✓ 553 passed in 1.70s** |

## Known Stubs

None.

## Threat Flags

None. Pure prompt + payload + documentation update. No new untrusted
surfaces. The `_PROMPT_VERSION` bump invalidates prior cached LLM reports
(T-87.4-LLM-01 `mitigate` per plan threat model — documented intentional
behavior). No new dependencies, no new network calls, no new auth surface.

## Self-Check: PASSED

- `app/services/insights_llm.py:_PROMPT_VERSION = "endgame_v32"` — present at line 68.
- `app/services/insights_llm.py::_conversion_elo_per_bucket` — present (renamed).
- `app/services/insights_llm.py::_render_conversion_elo_summary_block` — present (renamed).
- `app/services/insights_llm.py:"[summary conversion_elo"` header literal — present.
- `app/prompts/endgame_insights.md` — case-insensitive grep for `endgame skill`,
  `endgame_skill`, `endgame_elo_timeline`, `endgame_elo_gap`, `endgame elo` — zero matches.
- `app/prompts/endgame_insights.md` — "Conversion ELO Timeline", `conversion_elo_timeline`,
  `conversion_elo_gap` all present.
- `CHANGELOG.md [Unreleased]` — Phase 87.4 bullets in `### Changed` and `### Removed`.
- `.planning/todos/pending/2026-05-16-conversion-score-gap-display-centering.md`
  — absent.
- `.planning/todos/done/2026-05-16-conversion-score-gap-display-centering.md`
  — present with `## Outcome` section.
- `tests/prompts/test_endgame_insights_prompt.py` — created.
- Commits exist: `6982303d`, `eb3ea848`, `5e36185d`, `df97082f`, `9ca8e325`.
