---
phase: 241-codebase-cleanup
reviewed: 2026-10-16T21:30:16Z
depth: standard
files_reviewed: 195
files_reviewed_list:
  - app/core/ip_rate_limiter.py
  - app/core/opponent_strength.py
  - app/models/game.py
  - app/repositories/game_flaws_repository.py
  - app/repositories/game_repository.py
  - app/repositories/library_repository.py
  - app/repositories/openings_repository.py
  - app/repositories/stats_repository.py
  - app/repositories/train_leaderboard_repository.py
  - app/repositories/train_repository.py
  - app/repositories/user_import_settings_repository.py
  - app/routers/auth.py
  - app/routers/eval_remote.py
  - app/routers/users.py
  - app/schemas/library.py
  - app/services/accuracy_acpl.py
  - app/services/best_move_candidates.py
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/eval_apply.py
  - app/services/eval_drain.py
  - app/services/eval_entry.py
  - app/services/flaws_service.py
  - app/services/import_service.py
  - app/services/insights_llm.py
  - app/services/insights_service.py
  - app/services/library_service.py
  - app/services/normalization.py
  - app/services/opening_insights_service.py
  - app/services/openings_service.py
  - app/services/score_confidence.py
  - app/services/stats_service.py
  - app/services/tactic_detector.py
  - app/services/train_leaderboard.py
  - .claude/skills/tactic-tagger-report/SKILL.md
  - frontend/CLAUDE.md
  - frontend/src/App.test.tsx
  - frontend/src/App.tsx
  - frontend/src/components/admin/LeaderboardMedalsDemo.tsx
  - frontend/src/components/admin/__tests__/TrainReminderTestCard.test.tsx
  - frontend/src/components/analysis/AnalysisBoardStage.tsx
  - frontend/src/components/analysis/AnalysisPlayerBar.tsx
  - frontend/src/components/analysis/AnalysisTabs.tsx
  - frontend/src/components/analysis/AnalysisTagsPanel.tsx
  - frontend/src/components/analysis/EngineLines.tsx
  - frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
  - frontend/src/components/analysis/FlawChessEngineLines.tsx
  - frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/board/ChessBoard.tsx
  - frontend/src/components/board/__tests__/ChessBoard.arrowOpacity.test.ts
  - frontend/src/components/bots/BotDrawOfferActions.tsx
  - frontend/src/components/bots/PersonaGrid.tsx
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
  - frontend/src/components/charts/PositionResultsPanel.tsx
  - frontend/src/components/charts/__tests__/EndgameScoreOverTimeChart.test.tsx
  - frontend/src/components/endgames/EndgameStatsTab.test.tsx
  - frontend/src/components/endgames/EndgameStatsTab.tsx
  - frontend/src/components/endgames/stats/OverallSection.tsx
  - frontend/src/components/endgames/stats/rankedMetrics.ts
  - frontend/src/components/endgames/stats/TypeTable.tsx
  - frontend/src/components/endgames/useEndgameInsightsState.ts
  - frontend/src/components/EvalCoverageHeader.tsx
  - frontend/src/components/filters/OpponentStrengthFilter.tsx
  - frontend/src/components/insights/EndgameInsightsBlock.tsx
  - frontend/src/components/insights/EvalConfidencePopover.tsx
  - frontend/src/components/insights/EvalConfidenceTooltip.tsx
  - frontend/src/components/insights/OpeningFindingCard.test.tsx
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/components/insights/ScoreConfidencePopover.tsx
  - frontend/src/components/insights/ScoreConfidenceTooltip.tsx
  - frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx
  - frontend/src/components/insights/__tests__/ScoreConfidenceTooltip.test.tsx
  - frontend/src/components/library/analysisCoverageCopy.ts
  - frontend/src/components/library/EvalChart.tsx
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/library/TacticMotifChip.tsx
  - frontend/src/components/library/TacticMotifGroup.tsx
  - frontend/src/components/library/TagChip.tsx
  - frontend/src/components/library/__tests__/TacticMotifChip.test.tsx
  - frontend/src/components/move-explorer/MoveExplorer.tsx
  - frontend/src/components/position-bookmarks/BookmarkMiniBoard.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
  - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
  - frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/stats/__tests__/EvalCpuPlaceholder.test.tsx
  - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
  - frontend/src/components/__tests__/EvalCoverageHeader.test.tsx
  - frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx
  - frontend/src/components/train/__tests__/TrainRevealActionBar.test.tsx
  - frontend/src/components/train/__tests__/TrainReveal.test.tsx
  - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
  - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/__tests__/useTrainReminderSlot.test.tsx
  - frontend/src/components/train/TrainInstallQr.tsx
  - frontend/src/components/train/TrainLeaderboardCard.tsx
  - frontend/src/components/train/TrainLineChips.tsx
  - frontend/src/components/train/TrainReminderResurfaceBanner.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/useTrainReminderSlot.tsx
  - frontend/src/hooks/analysis/__tests__/useAnalysisEngineLines.test.ts
  - frontend/src/hooks/analysis/useAnalysisEngineLines.ts
  - frontend/src/hooks/analysis/useAnalysisGemMarkers.ts
  - frontend/src/hooks/__tests__/useBotGame.test.ts
  - frontend/src/hooks/__tests__/useBotGameVoice.test.ts
  - frontend/src/hooks/__tests__/useEvalCoverage.test.tsx
  - frontend/src/hooks/__tests__/useInstallPrompt.test.ts
  - frontend/src/hooks/__tests__/useResultDialogHold.test.ts
  - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
  - frontend/src/hooks/useBotGameDrawOffer.ts
  - frontend/src/hooks/useBotGameMoves.ts
  - frontend/src/hooks/useBotGameSnapshot.ts
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/hooks/useBotGameVoice.ts
  - frontend/src/hooks/useChessGame.ts
  - frontend/src/hooks/useEndgames.ts
  - frontend/src/hooks/useEvalCoverage.ts
  - frontend/src/hooks/useGameOverlay.ts
  - frontend/src/hooks/useGemSweep.ts
  - frontend/src/hooks/useInstallPrompt.ts
  - frontend/src/hooks/useLibrary.ts
  - frontend/src/hooks/useOpeningInsights.ts
  - frontend/src/hooks/usePushCapability.ts
  - frontend/src/hooks/useReminderResurface.ts
  - frontend/src/hooks/useResultDialogHold.ts
  - frontend/src/hooks/useStats.ts
  - frontend/src/hooks/useTrainPuzzleTelemetry.ts
  - frontend/src/hooks/useTrainRevealTree.ts
  - frontend/src/hooks/useTrainSettings.ts
  - frontend/src/hooks/useTrainTour.ts
  - frontend/src/lib/animatedScroll.ts
  - frontend/src/lib/arrowColor.test.ts
  - frontend/src/lib/arrowColor.ts
  - frontend/src/lib/botGameCopy.ts
  - frontend/src/lib/confetti.ts
  - frontend/src/lib/engine/maiaWorkerHost.ts
  - frontend/src/lib/engine/__tests__/maiaQueue.test.ts
  - frontend/src/lib/engine/__tests__/maiaWorkerHost.test.ts
  - frontend/src/lib/opponentStrength.ts
  - frontend/src/lib/push.ts
  - frontend/src/lib/reminderSlotState.ts
  - frontend/src/lib/scoreBulletConfig.ts
  - frontend/src/lib/__tests__/botGameCopy.test.ts
  - frontend/src/lib/__tests__/trainBotCopy.test.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/trainPhoneGrade.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/Bots.tsx
  - frontend/src/pages/Import.tsx
  - frontend/src/pages/library/LibraryPage.tsx
  - frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx
  - frontend/src/pages/openings/OpeningsMobileDrawers.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/openings/useOpeningsChartData.ts
  - frontend/src/pages/openings/useSidebarState.ts
  - frontend/src/pages/__tests__/Bots.test.tsx
  - frontend/src/pages/__tests__/Endgames.filterVisibility.test.tsx
  - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
  - frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx
  - frontend/src/pages/__tests__/Import.feedbackAsk.test.tsx
  - frontend/src/pages/__tests__/Import.pasteHandoff.test.tsx
  - frontend/src/pages/__tests__/Import.queuedState.test.tsx
  - frontend/src/pages/__tests__/Import.stateMachine.test.tsx
  - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
  - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
  - frontend/src/__tests__/noEndgameSkillString.test.tsx
  - scripts/tactic_tagger_report.py
  - tests/repositories/test_game_repository_zero_pending.py
  - tests/repositories/test_train_leaderboard_repository.py
  - tests/scripts/tagger/precision_floors.py
  - tests/scripts/tagger/test_detector_precision.py
  - tests/services/test_eval_apply.py
  - tests/services/test_eval_drain.py
  - tests/services/test_flaws_service.py
  - tests/services/test_import_service.py
  - tests/services/test_insights_llm.py
  - tests/services/test_opening_insights_service.py
  - tests/services/test_score_confidence.py
  - tests/services/test_tactic_detector.py
  - tests/services/test_train_leaderboard.py
  - tests/test_eval_worker_endpoints.py
  - tests/test_flaw_predicate.py
  - tests/test_import_service.py
  - tests/test_library_repository.py
  - tests/test_library_router.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 241: Code Review Report

**Reviewed:** 2026-10-16T21:30:16Z
**Depth:** standard
**Files Reviewed:** 195
**Status:** issues_found

## Summary

Scope was the 195 files touched by the `refactor(naming)` commits, reviewed as a rename diff (`21860f63d..HEAD`), per the orchestrator's scope note.

Method:

- Built a comment- and docstring-blind token diff (TypeScript via the compiler's AST, Python via `tokenize`, JSDoc and docstrings dropped) of every file against `21860f63d`, including the ten renamed files at their old paths. About 850 hunks, each read.
- Extracted all single-identifier renames (about 240) and grepped the whole tree (app, tests, scripts, frontend, `.claude`, docs) for every old name. All are gone, including from strings, `__all__`, `vi.mock` paths and patch targets. The `vi.mock` paths in tests resolve to the renamed modules.
- Checked each potentially risky rename for shadowing, wire or persistence leaks, and renamed keys with a stale consumer:
  - `window` to `windowSize`: the wire field `score_gap_timeline_window` is untouched, and the mock and consumer keys match.
  - `game_dict` to `game`, `openingName` to `opening`, `live` to `liveEval`: no collision.
  - `timeControl` and `platform` to plurals: query keys and request bodies carry identical values. The API payload keys `time_control` and `platform` are unchanged.
  - `isPending` to `hasPendingEvals`: every `useEvalCoverage` mock was updated.
  - `bot_elo` to `bot_rating` in `normalization.py`: the wire field `bot_elo` in `schemas/bots.py` is untouched.
  - `eg_*` and `ne_*` to `a_*` and `b_*`: all callers pass positional args.
  - `flawId` to `gameId`: the `chip-tactic-*` testid format is unchanged, and the value passed was always `game_id`.
  - `_import_scope_expanded` to `import_scope_expanded`: the `__all__` entry and callers are consistent.
- No testid, Umami attribute, storage key, Literal value, Pydantic field or generated-file name moved (D-15 and D-17 hold). The tests lost no `it` or `test` cases. The single added test is the one for the `fix(insights)` commit.
- Verified a sample of rewritten comments that assert facts against the code:
  - three scalar MetricIds, `gaps_by_bucket` "not consumed", nine named-mate motifs, `useTrainReminderSlot` JSX, the `heightClass` values, the 0.28 alpha, the `IMPORT_EXEMPT_ROUTES` reference.
  - All matched.
- No rename changed behavior, and I found none that is wrong or misleading. One comment cluster left next to a renamed identifier now contradicts the code (WR-01). Two minor items follow.

## Warnings

### WR-01: Comments and test names still call the neutral arrow "blue" after `DARK_BLUE` became `NEUTRAL_ARROW_COLOR` (grey `#6B7280`)

**File:** `frontend/src/components/board/ChessBoard.tsx:61,140,168,192`; `frontend/src/lib/arrowColor.test.ts:10,98,102,106`; `frontend/src/components/board/__tests__/ChessBoard.arrowOpacity.test.ts:20,29,31`

**Issue:** The rename commit (`2e377754c`) exists because the constant is grey (`ARROW_NEUTRAL = '#6B7280'`, `theme.ts:408`). It fixed the stale "blue" wording in `arrowColor.ts` ("render blue arrows" became "grey arrows", "green > red > blue" became "green > red > grey"). It touched `ChessBoard.tsx` and both test files but left the same wording behind:

- `ChessBoard.tsx:61` says "color-based default (blue low-emphasis vs the standard opacity)".
- `ChessBoard.tsx:140` says "Blue arrows (in-between zone OR low-data OR low-confidence) render much fainter".
- `ChessBoard.tsx:168` says "(blue arrows render much fainter at rest...)".
- `ChessBoard.tsx:192` says "green > red > blue > grey (low-data)". This is also factually wrong: `arrowSortKey` has exactly three tiers, green=0, red=1, `NEUTRAL_ARROW_COLOR`=2, and anything else gets 3. In-between and low-data arrows are the same grey constant, so there is no separate "blue" tier before a "grey (low-data)" tier.
- The test titles and a local variable still say blue: `arrowColor.test.ts` ("low-data → blue", "blue color from getArrowColor ..."), and `ChessBoard.arrowOpacity.test.ts` (`const blue = resolveArrowOpacity(arrow({ color: NEUTRAL_ARROW_COLOR }))` and two titles).

A reader looking for "the blue arrows" next to a constant named `NEUTRAL_ARROW_COLOR` that resolves to grey is the failure the phase set out to remove. Several Engine arrows (Stockfish) really are blue, so "blue" in this file is now ambiguous, not just stale.

**Fix:** Replace "blue" with "neutral grey" in the four `ChessBoard.tsx` comments. Make line 192 read "green > red > neutral grey > any other color". Rename the test local `blue` to `neutral`, and change the `arrowColor.test.ts` titles from "→ blue" and "blue color from getArrowColor" to "→ neutral grey" and "neutral color from getArrowColor".

## Info

### IN-01: `frontend/CLAUDE.md` still lists two components that do not exist, on the line the phase edited

**File:** `frontend/CLAUDE.md:13`
**Issue:** The rename pass updated `WdlConfidenceTooltip` to `ScoreConfidenceTooltip` on this line, but the same line names `MetricStatPopover` and `AchievableScorePopover`. Neither identifier exists anywhere under `frontend/src` (only `metric-info-popover.tsx` and `info-popover.tsx` do). Pre-existing, but it is the exact sentence the rename commit edited, so the list now reads as verified when it is not.
**Fix:** Drop the two stale names or point them at the real components (`InfoPopover` / `metric-info-popover`). For example: `` `ScoreConfidenceTooltip`, `EvalConfidenceTooltip`, the `InfoPopover` family, etc. ``

### IN-02: A behavior-changing fix and a new test landed inside a phase documented as comment, docstring, test-name and rename only

**File:** `app/services/opening_insights_service.py:640-647`, `tests/services/test_opening_insights_service.py:1722-1781` (commit `07dd60fb4`)
**Issue:** Commit `07dd60fb4` (`fix(insights): skip NULL sample_pair ...`) adds an `if r.sample_pair is not None` guard and a regression test. I checked it and it is correct. The raw-row loop guarded `sample_pair` only after the unguarded `r.sample_pair[1]` list comprehension had already run, so an all-custom-start group raised `TypeError`. The test constructs exactly that row and asserts the sample list and surviving rows, so reverting the guard fails it.

However, `241-70-SUMMARY.md` states the phase "is proven comment-docstring-test-name-and-rename-only" and lists the allowed residue. This commit is not mentioned in either place. The CHANGELOG already has the matching `[Unreleased]` line, so the user-facing side is covered. Anyone squash-merging on the strength of the SUMMARY's "no code change" claim will not see that one real code change is in the range.
**Fix:** Name `07dd60fb4` in the squash-merge message or in the 241-70 owner report as the one intentional behavior change (crash fix, with regression test). No code change needed.

---

_Reviewed: 2026-10-16T21:30:16Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
