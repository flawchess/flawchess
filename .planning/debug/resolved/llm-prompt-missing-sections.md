---
status: resolved
trigger: "LLM insights user_prompt is missing Player profile + endgame_elo_timeline sections, and score_timeline has only summary entries (no series data). LLM hallucinates player_profile in response. Reproduced for user 89 in prod and user 49 in dev via llm_logs table."
created: 2026-05-12T00:00:00Z
updated: 2026-05-12T19:30:00Z
---

## Current Focus

hypothesis: All three observed omissions share a single root cause: user 49 (and likely user 89) have only ~5–9 ISO weeks of activity per (platform, time_control) combo, which sits below several "minimum points" thresholds in the prompt-building pipeline. Each threshold silently drops its block, leaving the LLM with no data and an unconditionally-required `player_profile` output field — so it hallucinates.
test: Inspect `llm_logs.id=73` for user 49 (dev), trace prompt assembly in `app/services/insights_llm.py` + `app/services/insights_service.py`, count actual weekly buckets per combo in `games` table.
expecting: Find one or more threshold gates that drop sections silently while the schema still mandates their derived output fields.
next_action: Decide fix shape (lower thresholds vs. relax schema vs. emit explicit "no data" stub blocks). The cleanest fix is to **always emit a `## Player profile` block** — when no combo qualifies, emit a minimal sentinel block that tells the LLM "no qualifying combo; narrate cautiously / past-tense" — and to **always emit `### Subsection: endgame_elo_timeline`** with a sentinel `[no qualifying combo]` line when sparse. Series gating already has an `[n=… for every point]` precedent for low-info disclosures.

## Symptoms

expected: user_prompt should include `## Player profile` section, full series data under `### Subsection: score_timeline`, and a `### Subsection: endgame_elo_timeline` section
actual: `## Player profile` section is missing entirely; `### Subsection: score_timeline` contains only summary entries (no series); `### Subsection: endgame_elo_timeline` is missing entirely; LLM response_json hallucinates the missing player_profile
errors: No exception — silent data omission. LLM hallucinates plausible content to fill the gap.
reproduction: Query llm_logs table for user_id=89 in prod (or user_id=49 in dev) and inspect the user_prompt and response_json columns
started: Behaviour ships whenever a user has < ~20 weekly buckets per combo (new users; sparse-history users). Predates the current code — has been latent since `compute_player_profile` landed.

## Eliminated

- **Not a prompt-template loop bug.** `_assemble_user_prompt` correctly iterates `_SECTION_LAYOUT` and renders subsection groups in UI order.
- **Not an LLM truncation / context-length issue.** Full prompt fits in ~9.6 KB; response is well-formed JSON; no error in `llm_logs`.
- **Not a filter-context issue.** Same `EndgameTabFindings` data feeds the UI tile rendering correctly; the gap is specifically in `_assemble_user_prompt`'s block-rendering gates, not upstream data fetch.

## Evidence

- timestamp: 2026-05-12T18:00Z
  source: dev DB `llm_logs.id=73` (user_id=49), exported user_prompt to `/tmp/llm_log_73_user_prompt.txt`
  finding: Prompt starts with `## Payload summary` then jumps directly to `## Section: overall`. No `## Player profile` block. No `## Filters` header either (separate, possibly intentional). Inside `## Section: metrics_elo` the layout jumps from the section header to `### Subsection: endgame_metrics` — `endgame_elo_timeline` subsection is absent. `### Subsection: score_timeline` shows summary lines but no `[series ...]` raw-data block.

- timestamp: 2026-05-12T18:05Z
  source: dev DB `games` table for user 49
  finding: `chess.com bullet` = 361 games across 7 ISO weeks; `chess.com blitz` = 211 games across 5 ISO weeks. Earliest game 2026-03-19, latest 2026-05-11. NO lichess games. So the universe of `(platform, time_control)` combos is only two, with at most 5–7 weekly buckets each before the rolling-window prefill and `MIN_GAMES_FOR_TIMELINE=10` gate trim it further.

- timestamp: 2026-05-12T18:10Z
  source: `app/services/insights_service.py:181, 252-362`
  finding: `compute_player_profile` requires each combo to have `>= _PLAYER_PROFILE_MIN_POINTS = 20` weekly points (line 214, 279). With at most 7 weekly buckets per combo, **both combos are skipped**, and the function returns `None` (line 360). The caller `_format_player_profile_block` returns `[]` for None/empty profile (line 436–437) → no `## Player profile` block rendered.

- timestamp: 2026-05-12T18:12Z
  source: `app/services/insights_service.py:780-849`, `SPARSE_COMBO_FLOOR=10` at line 95
  finding: `_findings_endgame_elo_timeline` calls `_series_for_endgame_elo_combo`, which returns `None` for combos with fewer than `SPARSE_COMBO_FLOOR=10` weekly points (line 1241). When it returns None, the outer loop `continue`s (line 824–825) **without emitting any finding** — not even the empty `_empty_finding` placeholder. With user 49's max 7 weekly points per combo, both combos are silently dropped, the `endgame_elo_timeline` subsection has zero findings, and `_assemble_user_prompt`'s "skip empty subsection" branch (line 1702–1704) removes the entire `### Subsection: endgame_elo_timeline` block.

- timestamp: 2026-05-12T18:18Z
  source: `app/services/insights_llm.py:1646-1650, 1565-1573, 1366-1380`
  finding: For `score_timeline`, the all_time series is computed AS NORMAL (raw `f.series` is non-None) but then C2 (line 1377) filters out all points with `bucket_start >= today − 90d`. Since user 49 has only ~2 months of data, **every all_time point gets dropped** → retained list is empty. However, `all_time_series_pairs` is built BEFORE filtering (line 1646–1650 keys on `f.series is not None`), so the (metric, subsection) pair is in the set. Then C5 (line 1565–1573) suppresses the `last_3mo` series block because its pair is in `all_time_series_pairs`. Net effect: both windows have data internally, but neither renders a `[series ...]` block. This is consistent across all three timeline subsections (`score_timeline`, `clock_diff_timeline`, `endgame_elo_timeline`) for short-history users — the prompt shows the same pattern for `### Subsection: clock_diff_timeline` in user 49's log (line 82–86): summary only, no series.

- timestamp: 2026-05-12T18:22Z
  source: `app/schemas/insights.py:333`
  finding: `player_profile: str = Field(..., min_length=1, max_length=800)` — the LLM's output schema **requires** a non-empty player_profile. The system prompt at `app/prompts/endgame_insights.md:8` reinforces this with "Lead with the combo named by the `[anchor-combo ...]` tag — quote its current Elo and recent trajectory." When the `## Player profile` block is absent from the user prompt, the LLM has no anchor data but must still emit the field. **It hallucinates.**

- timestamp: 2026-05-12T18:25Z
  source: `/tmp/llm_log_73_response.json`
  finding: The hallucinated `player_profile` for user 49 reads: "You are an intermediate player showing a clear discrepancy between phase-specific skills. Your opening and middlegame performance is highly effective, allowing you to maintain a competitive presence even as you enter the endgame phase from slightly disadvantaged or equal positions. Your trajectory suggests a stable intermediate skill level that is currently being tested by technical execution and time management requirements in late-game scenarios. You are a developing player on a learning arc where rounding out technical endgame knowledge will be essential for further rating growth." — no Elo numbers, no platform/TC names, fully invented from non-existent anchor data. Generic enough to look plausible but ungrounded — exactly the failure mode the `[anchor-combo]` machinery was designed to prevent.

## Resolution

### Root cause

Three independent silent-drop gates in the prompt builder all trip for short-history users (typically < ~20 weekly buckets per (platform, time_control) combo), while the LLM output schema unconditionally requires `player_profile`:

1. **`_PLAYER_PROFILE_MIN_POINTS = 20`** (`app/services/insights_service.py:214`) — when no combo clears this, `compute_player_profile` returns `None` and the `## Player profile` block is omitted entirely. The schema still mandates a non-empty `player_profile` output field, so the LLM hallucinates one.
2. **`SPARSE_COMBO_FLOOR = 10`** (`app/services/insights_service.py:95`) — combos below this floor are skipped without an `_empty_finding` placeholder (`_findings_endgame_elo_timeline:823-825`). When every combo is sparse, the whole `### Subsection: endgame_elo_timeline` disappears.
3. **Pre-filter `all_time_series_pairs` set** (`app/services/insights_llm.py:1646-1650`) — keyed on raw `f.series is not None`, not on whether the C2-trimmed series has any retained points. So for users whose entire history is inside the last 90 days, the all_time series filters to empty but its pair is still in the set, which makes C5 suppress the last_3mo series too. The summary block ends up describing buckets that the LLM never gets to read.

The bug is that these three thresholds were tuned for users with many months of history, and they fail-quiet for new users instead of fail-loud (either with sentinel blocks or by raising/skipping the LLM call). The schema then forces fabrication.

### Fix direction

Three layered fixes, smallest-blast-radius first:

**A. Make `all_time_series_pairs` reflect post-filter reality (smallest fix, addresses score_timeline / clock_diff_timeline / endgame_elo_timeline series omission).** Build the set by applying the same C2/A4/C6 filter chain `_retained_series_for_summary` uses, and only register the pair when retained points >= 1. That way, when the all_time series is C2-trimmed to empty, C5 will no longer suppress the last_3mo series. This is a localized change in `_assemble_user_prompt` and doesn't require schema or threshold changes.

**B. Always emit `## Player profile`, even when sparse.** When `compute_player_profile` returns `None` (or all combos are below the 20-point floor), emit a sentinel block — for example:
```
## Player profile
[anchor-combo] none — fewer than 20 weekly buckets across all combos; narrate using current platform/TC list only, do NOT invent Elo numbers
[summary actual_elo | platform=chess.com, time_control=bullet]
  all_time: games=361, weeks=7, current=<latest_rating>, mean=<wk-mean>, min=<min>, max=<max>, quality=sparse
  last_3mo: games=361, weeks=7, mean=<wk-mean>, quality=sparse
```
This requires `compute_player_profile` to relax its floor for "anchor-only" rendering (or a parallel "sparse profile" builder) AND a small prompt-template addendum telling the LLM how to narrate from a `quality=sparse` block (no trend claims, no "Elo of X over the year" framing, plain present-tense "you play at ~<rating>" allowed). The output schema stays unchanged because the field is still populated from real data.

**C. Always emit `### Subsection: endgame_elo_timeline` with a sentinel finding when every combo is sparse.** Either route through `_empty_finding` (which the existing pipeline knows how to render) or add a dedicated "no qualifying combo" line. This stops the whole subsection from vanishing from `## Section: metrics_elo`.

If the team wants a one-line stopgap before the full fix: **A alone** would fix two of the three symptoms (series blocks reappear). The hallucinated `player_profile` requires B. C is cosmetic but completes the story.

Recommended sequencing: A first (localized, low-risk, fixes the most-impactful UX bug — series data going to the LLM), then B (medium-touch — touches prompt template, schemas, and an LLM-prompt-version bump), then C if regression telemetry shows it's worth the churn.

### Fix (APPLIED 2026-05-12 — all three fixes shipped together as _PROMPT_VERSION endgame_v27)

E2E verification against user 49 in dev confirms all three sections now render correctly:
- `## Player profile` block emits `[anchor-combo] sparse-history` tag + per-combo `quality=sparse` blocks with real Elo numbers (chess.com bullet current=2416, chess.com blitz current=2324) — LLM no longer has to hallucinate the player_profile output field.
- `### Subsection: endgame_elo_timeline` renders the sentinel `[no qualifying combo — every (platform, time_control) combo has fewer than 10 weekly buckets; no Endgame ELO trajectory available yet]` line.
- `### Subsection: score_timeline` now emits `[series endgame_score_timeline, last_3mo, weekly]` + `[series non_endgame_score_timeline, ...]` + `[series score_gap, ...]` blocks with all 7 retained weekly buckets.

Tests added: `TestSparseHistoryFixes` (4 tests) in `tests/services/test_insights_llm.py` and `TestComputePlayerProfile` (5 tests) in `tests/services/test_insights_service.py`. Full backend suite (1,360 tests) passes; `ruff`, `ty` clean.

### Original fix plan (preserved for posterity)

Files that will change for fix A:
- `app/services/insights_llm.py` — change `all_time_series_pairs` construction at lines 1646–1650 to apply the C2/A4/C6 filter chain (extract a helper or inline the filter) and only register pairs where retained_points >= 1. Also re-examine line 1500–1517 to make sure summary-line `buckets=` count matches whether `[series]` actually renders below it (currently they can diverge).

Files that will change for fix B:
- `app/services/insights_service.py` — add a sparse-fallback branch in `compute_player_profile` (or split into `compute_player_profile_strict` and `compute_player_profile_sparse`) that returns a per-combo summary with `quality=sparse` when no combo clears the 20-point floor but at least one combo has games.
- `app/services/insights_llm.py:_format_player_profile_block` — render `quality=sparse` blocks with a clear `[no-trend-data]` tag and a sentinel `[anchor-combo]` line so the LLM knows not to invent trend numbers.
- `app/prompts/endgame_insights.md` — add a "Sparse profile" subsection under "Player profile — calibrate tone to skill level" explaining what the LLM may and may not say when only sparse blocks are present.
- Bump `_PROMPT_VERSION` to `endgame_v27` to bust the LLM-response cache.

Files that will change for fix C:
- `app/services/insights_service.py:_findings_endgame_elo_timeline` — when every combo is sparse, emit one `_empty_finding("endgame_elo_timeline", window, "endgame_elo_gap")` so the subsection renders with an explicit "no qualifying combo" line rather than vanishing.

### Tests

For fix A: a `_assemble_user_prompt` unit test where the input findings carry an all_time series that becomes empty after C2 trimming. Assert the last_3mo `[series]` block IS emitted.

For fix B: a `compute_player_profile` test with two combos of 7 weekly points each (below `_PLAYER_PROFILE_MIN_POINTS`). Assert the function returns a non-None sparse profile and the rendered block contains the sentinel `[anchor-combo] none` marker.

For fix C: a `_findings_endgame_elo_timeline` test where every combo has < `SPARSE_COMBO_FLOOR` points. Assert the result contains exactly one `_empty_finding` per window, not an empty list.

End-to-end: trigger the endgame insights endpoint for user 49 in dev, confirm the new `user_prompt` contains all three sections and the LLM response stops hallucinating Elo claims.

### Specialist hint

python — the bug is in Python service layer logic (silent filter gates + schema/prompt mismatch); no React, no SQL, no concurrency. Consider routing to `python-expert-best-practices-code-review` for the fix patch.
