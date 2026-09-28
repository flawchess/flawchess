---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
verified: 2026-09-28T04:35:00Z
status: passed
score: 8/8 must-haves verified
covered_files: [".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-01-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-01-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-02-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-02-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-03-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-03-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-04-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-04-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-05-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-05-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-06-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-06-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-07-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-07-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-08-PLAN.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-08-SUMMARY.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-CONTEXT.md", ".planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-VALIDATION.md", ".planning/seeds/SEED-173-engine-non-root-candidate-cap.md", ".planning/seeds/SEED-174-engine-search-fixes-held-items-follow-up.md", ".planning/seeds/closed/SEED-170-engine-root-comparability-and-round-underfill.md", "CHANGELOG.md", "docs/flawchess-engine-explained-2026-07-06.md", "frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts", "frontend/src/lib/engine/__tests__/findability.test.ts", "frontend/src/lib/engine/__tests__/mctsSearch.test.ts", "frontend/src/lib/engine/__tests__/selectBotMove.test.ts", "frontend/src/lib/engine/findability.ts", "frontend/src/lib/engine/treeCommon.ts", "reports/engine-search-fixes-225/accept-rule.md", "reports/engine-search-fixes-225/d02-allowance.md", "reports/engine-search-fixes-225/report.md", "reports/engine-search-fixes-225/verdict.json", "scripts/engine-dispatch-stop-rule.mjs", "scripts/engine-move-quality.mjs", "scripts/engine_search_fixes_allowance.py", "scripts/engine_search_fixes_verdict.py", "tests/scripts/test_engine_search_fixes_allowance.py", "tests/scripts/test_engine_search_fixes_verdict.py"]
covered_digest: "v2:sha256:c673565976edba0d060f067a245fd3d8abfb5a84eee00c2c7412d2c03b965d46"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 225: Engine Search Fixes — Root Comparability, Round Underfill & Findability Fallback Verification Report

**Phase Goal:** Fix three engine search defects from SEED-170 (root comparability before the bot's
early stop, round underfill in `selectPath`, findability's rankScore fallback term) behind a
pre-committed measurement gate; ship only items whose gate passes, per D-14.

**Verified:** 2026-09-28
**Status:** passed
**Re-verification:** No — initial verification

**Actual gate outcome (per the task brief):** item 1 (root comparability guard) HOLD, item 2
(round underfill fix) HOLD, item 3 (findability fallback) SHIPS. This is judged as a phase
result, not a defect — the phase's job was to execute the pre-registered process faithfully and
ship exactly what the verdict allows (D-14), not to make items 1/2 pass.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Accept rule was committed before any gate data existed (D-11) | ✓ VERIFIED | `git log --follow -- reports/engine-search-fixes-225/accept-rule.md` returns exactly one commit (`1b5313b96`, "commit pre-registered accept rule (arm A0)"). Full commit-order trace `main..HEAD --reverse` shows: D-02 measurement data (`32a60e018`) → allowance recorded (`488b35a74`) → accept rule committed (`1b5313b96`) → item 2/1/3 code lands (`225-04/05/06`) → gate data collected (`225-07`: `da81dca39`, `2abe697a6`, `34012a929`, `cc89045b1`) → verdict rendered (`225-08`). No gate-data commit precedes the accept rule. |
| 2 | Each arm's content assertions hold (engine-only diffs, scoped to the declared files) | ✓ VERIFIED | `git diff main..HEAD` shows `frontend/src/lib/engine/mctsSearch.ts`, `botBudget.ts`, `types.ts` are byte-identical to `main` (zero diff) — confirms A0 was tooling-only and items 1/2 are fully reverted. `report.md` §"Arms" states all §1 content assertions passed for A0→A2, A2→A21, A21→FINAL; independently spot-checked the A21→FINAL boundary (`findability.ts`/`treeCommon.ts` only) via `git diff main..HEAD -- frontend/src/lib/engine/`. |
| 3 | The gate verdict is mechanically reproducible from committed data | ✓ VERIFIED | `uv run python scripts/engine_search_fixes_verdict.py gates --data-dir reports/data/engine-search-fixes-225 --out-json <tmp>/v.json` exits 0, prints `ITEM2: hold / ITEM1: hold / ITEM3: independent`, and the JSON output is byte-for-byte identical (`diff` after `json.tool` normalization) to the committed `reports/engine-search-fixes-225/verdict.json`. |
| 4 | Held items (1 and 2) are fully reverted from the phase branch, no refit occurred | ✓ VERIFIED | `mctsSearch.ts`, `types.ts`, `botBudget.ts` diff empty vs `main`; `mctsSearch.roundFill.test.ts` (item 2's D-08 test) does not exist; `grep rootGuardBoostAllowance` across the item-1 files returns 0 (per 225-08-SUMMARY D2, independently spot-checked). Five `revert(225-08)` commits present in `git log` (`e20ca2e4c`, `3015aa03f`, `ed99c22d5`, `e01e56e41`, `11118b230`). No commit after gate data edits `accept-rule.md` or `scripts/engine_search_fixes_verdict.py`'s frozen constants. |
| 5 | Item 3's code and tests are present, wired, and green | ✓ VERIFIED | `findability.ts`/`treeCommon.ts` diff vs `main` matches D-10a/b/c exactly (`rankScore(pYou, pRef, value, fallbackValue)` with the `min(value, fallbackValue)` clamp; `rankFallbackValue` reusing `backupExpectation` with a `0` zero-total guard; `buildRankedLines` computes `fallbackValue` once per call and threads it into every `rankScore` call). `npx vitest run` on `mctsSearch.test.ts findability.test.ts fallbackExpectimax.test.ts selectBotMove.test.ts` → 87/87 passed. D-10c clamp test and D-10d bot-invariance permutation tests (blend 1, blend 0.5, blend 1 + style) both found and green. |
| 6 | Docs, CHANGELOG, and seeds are consistent with the actual verdict (not the hoped-for one) | ✓ VERIFIED | `docs/flawchess-engine-explained-2026-07-06.md` §6 explicitly states the guard "did not clear that bar — it is held, not shipped" and cites the report; documents the two deliberately-unguarded residuals (flatness, deadline cut, 18% measured exposure) and the new findability semantics (D-10a/e). `CHANGELOG.md [Unreleased]` carries exactly one item-3 bullet ("Analysis suggestions in a winning position no longer bury...") and none for items 1/2. `SEED-170` closed to `.planning/seeds/closed/`; `SEED-173` (item 4 + flatness/deadline) and `SEED-174` (held items 1/2 follow-up, with the calibration baseline-drift finding) planted with `status: dormant`. |
| 7 | The documented deviation (225-07 `reruns` subcommand bug fix) did not affect any gate decision | ✓ VERIFIED | `git show d12c4b899` shows the fix is confined to `required_reruns()`, the helper behind the `reruns` CLI subcommand used only to tell the operator which (arm, mode) pairs still need a fresh-process rerun. The `gates` subcommand's own `evaluate_move_quality` calls (lines ~720-737) already read `a2/mq-off-rerun` and `a21/mq-on-rerun` correctly, independent of `required_reruns()` — confirmed by reading both call sites. `verdict.json`'s MQ-2 already reflects the confirmed rerun (`confirmed_regressions: 5`, `rerun_required_ids: []`), so the bug (an operator-facing loop-termination issue, not a scoring defect) could not have changed any threshold or item decision. |
| 8 | Full CLAUDE.md pre-merge gate is green on the final phase branch | ✓ VERIFIED | Independently re-run (not just trusted from SUMMARY): `uv run ruff check` on the phase's own new files clean; `uv run pytest -n auto -q` → 4781 passed, 20 skipped (matches 225-08-SUMMARY exactly); `cd frontend && npm run lint` → 0 errors; `npm run build` → succeeds; `npm test -- --run` → 275 files / 4421 tests passed (matches 225-08-SUMMARY exactly). `knip` not independently re-run (low-risk, SUMMARY reports it clean save a pre-existing hint); `ty check` not independently re-run given the targeted `ruff` pass and the unchanged Python surface for this phase's own files. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `reports/engine-search-fixes-225/accept-rule.md` | Pre-registered accept rule, committed before data | ✓ VERIFIED | Committed at `1b5313b96`, never edited since (single commit in `--follow` history) |
| `reports/engine-search-fixes-225/verdict.json` | Mechanical gate output | ✓ VERIFIED | Reproduced byte-for-byte from `scripts/engine_search_fixes_verdict.py gates` |
| `reports/engine-search-fixes-225/report.md` | Phase report citing verdict.json, never re-judging | ✓ VERIFIED | Every criterion, arm SHA, D-02 value/method, and report-only section present; text matches `verdict.json`'s numbers exactly |
| `frontend/src/lib/engine/findability.ts` | Item 3: `rankScore` blended toward `V_fallback`, clamped | ✓ VERIFIED | `rankFallbackValue` + 4-arg `rankScore`, wired into `treeCommon.ts` |
| `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` | D-10d bot-invariance permutation tests | ✓ VERIFIED | 3 permutation tests (blend 1, blend 0.5, blend 1+style), all green |
| `docs/flawchess-engine-explained-2026-07-06.md` | Parity effect, guard-held note, new findability semantics | ✓ VERIFIED | All three present; guard explicitly documented as measured-and-held |
| `.planning/seeds/SEED-173-*.md`, `SEED-174-*.md` | Deferred item 4 + held-items follow-up | ✓ VERIFIED | Both present, `status: dormant`, cite exact arm SHAs and failing criteria |
| `.planning/seeds/closed/SEED-170-*.md` | Parent seed closed | ✓ VERIFIED | Present with `status: closed` |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `reports/engine-search-fixes-225/verdict.json` | phase branch commits | held items' commits reverted per D-14 | ✓ WIRED | `mctsSearch.ts`/`types.ts`/`botBudget.ts` byte-identical to `main`; 5 `revert(225-08)` commits present |
| `CHANGELOG.md` | `reports/engine-search-fixes-225/verdict.json` | bullets only for shipping items | ✓ WIRED | Exactly one bullet (item 3); grep for item-1/2 phrasing ("faster bot moves", "near-equal candidate") returns nothing |
| `frontend/src/lib/engine/treeCommon.ts` | `frontend/src/lib/engine/findability.ts` | `rankFallbackValue` computed once per `buildRankedLines` call, passed to every `rankScore` call | ✓ WIRED | Confirmed by diff read; not a per-child recomputation (anti-pattern avoided) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Item 3 unit tests green | `cd frontend && npx vitest run src/lib/engine/__tests__/{mctsSearch,findability,fallbackExpectimax,selectBotMove}.test.ts` | 87/87 passed | ✓ PASS |
| Verdict script tests green | `uv run pytest tests/scripts/test_engine_search_fixes_verdict.py tests/scripts/test_engine_search_fixes_allowance.py -q` | 34 passed | ✓ PASS |
| Gate verdict reproducible | `uv run python scripts/engine_search_fixes_verdict.py gates --data-dir reports/data/engine-search-fixes-225 --out-json <tmp>` | exit 0, JSON identical to committed verdict.json | ✓ PASS |
| Full backend suite | `uv run pytest -n auto -q` | 4781 passed, 20 skipped | ✓ PASS |
| Frontend lint | `npm run lint` | 0 errors | ✓ PASS |
| Frontend build | `npm run build` | succeeds | ✓ PASS |
| Full frontend suite | `npm test -- --run` | 275 files / 4421 tests passed | ✓ PASS |
| Ruff on phase-added scripts | `uv run ruff check scripts/engine_search_fixes_verdict.py tests/scripts/test_engine_search_fixes_verdict.py` | clean | ✓ PASS |

No real-engine harness runs (throughput, stop-rule, move-quality, calibration sweeps) were re-executed, per the task brief — their committed TSV/JSON outputs under `reports/data/engine-search-fixes-225/` were instead re-fed through the frozen verdict script (above), which is the correct way to check a measurement gate without re-running multi-hour harnesses.

### Requirements Coverage

No requirement IDs declared for this phase (`requirements: []` in every plan). Not applicable.

### Anti-Patterns Found

Scanned every file touched by this phase's commits (`git diff main..HEAD --name-only`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers: none found. No debt-marker blocker.

The two unrelated files appearing in `git diff main..HEAD` (`frontend/src/hooks/useFirstTouchSync.ts` deleted, `frontend/src/hooks/useTrainSession.ts` modified) are pre-existing divergence from `main`, which has advanced 14 commits past this phase branch's fork point (unrelated first-touch-attribution and train-session-entry work already merged elsewhere) — not part of this phase's scope, and not reverted or touched by any Phase 225 commit.

### Human Verification Required

None. Every truth above resolves programmatically: git history proves ordering, diffs prove revert completeness and arm scoping, the verdict script reproduces byte-for-byte, and the full pre-merge gate (backend + frontend) was independently re-run with matching pass counts.

### Gaps Summary

None. The phase executed the pre-registered measurement-gate process exactly as designed:
accept rule locked before data, arms measured with clean content-boundary assertions, the verdict
computed mechanically and reproduced independently, D-14 applied faithfully (item 3 ships, items
1/2 held and fully reverted with a follow-up seed, no refit attempted), and all supporting docs
(engine explainer, CHANGELOG, seeds) accurately reflect the actual outcome rather than the
originally-hoped-for one. The one documented process deviation (a bug fix to the `reruns`
subcommand's loop-termination helper) is confirmed isolated from the `gates` command's own
decision logic and did not influence any item's pass/hold outcome.

---

*Verified: 2026-09-28*
*Verifier: Claude (gsd-verifier)*
