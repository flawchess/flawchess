---
phase: 222-train-bot-narrated-onboarding-and-verdicts
verified: 2026-09-13T18:09:40Z
status: passed
score: 7/7 must-haves verified (present + wired); 3 human-verification items closed by owner override, see below
covered_files:
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-01-PLAN.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-01-SUMMARY.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-02-PLAN.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-02-SUMMARY.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-03-PLAN.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-03-SUMMARY.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-04-PLAN.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-04-SUMMARY.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-05-PLAN.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-05-SUMMARY.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-06-PLAN.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-06-SUMMARY.md
  - .planning/phases/222-train-bot-narrated-onboarding-and-verdicts/222-REVIEW.md
  - .planning/seeds/SEED-167-train-sound-toggle-rehoming.md
  - CHANGELOG.md
  - alembic/versions/20260913_144712_7d6bb75aae54_phase_222_train_onboarding_seen.py
  - app/models/train_settings.py
  - app/repositories/train_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - app/services/activity_queries.py
  - app/services/activity_stats.py
  - docs/activity-dashboard.md
  - frontend/src/api/client.ts
  - frontend/src/components/train/TrainBotBubble.tsx
  - frontend/src/components/train/TrainBotStepper.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/trainBubbleState.ts
  - frontend/src/hooks/useTrainOnboarding.ts
  - frontend/src/hooks/useTrainSession.ts
  - frontend/src/index.css
  - frontend/src/lib/personas/personaRegistry.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/trainGuessLabels.ts
  - frontend/src/pages/Home.tsx
  - frontend/src/pages/Train.tsx
  - frontend/src/pages/activity/ActivityPage.tsx
  - frontend/src/pages/activity/render.js
  - frontend/src/types/activity.ts
  - frontend/src/types/train.ts
  - scripts/reset_train_state.py
covered_digest: "v1:sha256:e5b73508e3b083219f911e63d9079bd7a5a0452f1bed3e3d333d04400787f14a"
behavior_unverified: 0
overrides_applied: 1
override:
  by: owner (Adrian Imfeld, ship instruction 2026-09-14 after six live UAT rounds)
  from: human_needed
  to: passed
  reason: |
    UAT items 1-3 accepted for ship. Item 1 (full explanation vs one-liner) was exercised live in UAT
    round 5 on a real account and surfaced the sr_explained latch bug, fixed with a regression test.
    Item 2 (device switch) rests on the server-side onboarding-seen columns (backend-tested); no
    two-device observation this session. Item 3 (superuser funnel card) rests on the dev-DB query
    check plus the ActivityPage unit tests; the superuser render was not screenshot-verified.
    Six UAT rounds (2026-09-13/14, phone screenshots + desktop) fixed every reported issue.
human_verification:
  - test: "Complete a Train session's first-completed-session score screen with at least one missed SR item, on a real account, and observe the full spaced-repetition explanation bubble render; then complete a second session and observe the one-liner variant."
    expected: "First completed session (sr_explained_at NULL, missed items > 0, not warm-up) renders the full D-25 explanation and stamps sr_explained_at exactly once; a later session with sr_explained_at already set renders only the one-liner."
    why_human: "This session's UAT account (t2@test.com) had only warm-up material, so only the warm-up score-bubble variant was observed live; the full-explanation and one-liner variants are covered by component-level unit tests (TrainScoreScreen.test.tsx) but not by an end-to-end browser observation against real solved SR items."
  - test: "Complete the first-session intro stepper on a desktop browser signed into a real account, then open /train on a phone signed into the same account."
    expected: "The intro does not replay on the phone (intro_seen_at is a server-side timestamp, not device-local) — SC5."
    why_human: "Requires two physical devices signed into the same account; this session had no second device available, and this is inherently unobservable by grep/unit test (the server-side persistence itself is unit-tested and migration-verified, but the actual cross-device UX has not been eyeballed)."
  - test: "Open /activity as a superuser, locate the Train sessions section's new funnel card, and move the date-range window before/after a point in time."
    expected: "The card shows both shares (first-session 0-solve, second-session return) with numerator/denominator, and a live all-time line; the windowed numbers change with the selected range while the all-time line holds steady — SC6."
    why_human: "This session's account (t2@test.com) is not a superuser, so the card's actual on-screen rendering was not observed; `fetch_train_funnel` was independently verified against the dev DB at three window sizes (7d/30d/90d) plus all-time, confirming the underlying query is correct and window-sensitive, and the automated `npm run check:activity-layout` harness passed, but the live superuser page render itself is unconfirmed."
---

# Phase 222: Train Bot-Narrated Onboarding & Verdicts Verification Report

**Phase Goal:** Stop Train losing 57% of first-timers before their first move and half of
the rest after one session, by making the Bots personas the permanent narrated voice of
Train across the guess prompt, the verdict, and the score screen, with server-side
seen-state and funnel metrics on the activity dashboard.

**Verified:** 2026-09-13T18:09:40Z
**Status:** passed (owner override, see frontmatter)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP SC1–SC7)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: A first-time user cannot reach a silent failure — the first puzzle opens with the bot intro stepper, guess buttons sit inside the last bubble, and a piece dropped before the guess visibly nudges the bubble and swaps its copy | ✓ VERIFIED | `resolveIntroState`/`TrainBotStepper` wiring in `TrainSolveScreen.tsx`; `handlePieceDrop` still `return false` on an unguessed drop while bumping `nudgeNonce` (grep-confirmed, unit tests in `TrainSolveScreen.test.tsx` "drop-before-guess nudge" + "first-session intro stepper" describe blocks, 302/302 passing in this session's targeted re-run); live browser UAT (222-06-SUMMARY Device UAT #2, #3) confirms the pulse/copy-swap on both the regular prompt and during the intro after a defect fix (commit `3c8287c22`) |
| 2 | SC2: Every puzzle shows the guess prompt inside a bot bubble; the board is fully visible above it at 375px with the longest first-session copy loaded | ✓ VERIFIED | One `<TrainBotBubble` mount inside `columnRef` confirmed by grep; live 375×667 UAT initially FAILED (bubble 612px, Next at y=852) and was fixed in `3c8287c22`/`bdc4a0fb4` (6-step intro, `STEPPER_COPY_MAX_CHARS` budget, mobile bottom-bar gutter), re-verified PASSED (board 240px, bubble 220px, Next/guess row at y=461–509, bar at 606) |
| 3 | SC3: Every reveal shows an outcome-matched bot line with inline point pills ending in the return date for SR items, and a no-return variant for herring/sharp-filler; the copy never comments on the user | ✓ VERIFIED | `renderVerdictBubbleBody`/`verdictClauseParts`/`resolveBubblePersona` in `TrainSolveScreen.tsx`; D-15/D-16 status-before-date truth table unit-tested in `trainBotCopy.test.ts` (mastered/parked with a stale `due_date`, `sharp_filler`/`red_herring` warm-up, missing-`source` degrade-to-no-tail) — re-run in this session, all passing; copy strings in `trainBotCopy.ts` contain no em-dash and no second-person judgment (spot-checked against D-21's rules) |
| 4 | SC4: The score screen states what returns and when before the reminder ask; the first completed session gets the full spaced-repetition explanation, later ones a single line | ✓ VERIFIED (present + wired); 2 of 4 copy variants not observed live | `TrainScoreScreen.tsx`'s bubble sits above `train-score-button-row` (grep-confirmed); `showsFullExplanation` gate + `stamp('sr_explained')` unit-tested (8 tests, "the score bubble (D-25)"); live UAT confirmed only the warm-up variant (t2@test.com has no own-blunder material) — see human_verification |
| 5 | SC5: The explanation-seen state is stored server-side and survives a device switch | ✓ VERIFIED (server-side persistence); device-switch leg deferred | Three nullable `DateTime(timezone=True)` columns confirmed on `train_settings` via the Alembic revision and model; `POST /train/onboarding/{step}` is guest-gated/first-write-wins/caller-scoped (8/8 router tests re-run, passing); no device-switch observation was made this session — see human_verification |
| 6 | SC6: Both funnel metrics have a recorded baseline and a repeatable query, so the post-change reading is a single run | ✓ VERIFIED (query); dashboard render not observed live | `fetch_train_funnel` re-run against the dev DB this session's SUMMARY at 7d/30d/90d/all-time (windowed numbers move, all-time holds); `trf-*` DOM-id seam present on both `render.js` and `ActivityPage.tsx` (grep-confirmed); 2 funnel-specific backend tests re-run, passing; superuser page render not observed — see human_verification |
| 7 | SC7: Bot copy is authored per outcome bucket with a few variants, never per persona; the stern/friendly/smart sets derive from a temperament field | ✓ VERIFIED | `personaRegistry.ts` carries `temperament:` on 24 entries (`grep -c` returns 25 including the interface field); `BY_TEMPERAMENT` built via `Object.values(PERSONA_REGISTRY).reduce(...)`, never a hand-maintained id list (grep-confirmed) |

**Score:** 7/7 truths present and wired; SC4/SC5/SC6 each carry one legitimately deferred human-observation leg (not fabricated as passed).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/trainBotCopy.ts` | Pure copy tables/resolvers (D-22..D-25) | ✓ VERIFIED | Exists, no `import ... from 'react'`, exports `pickBot`/`introCopy`/`verdictCopy`/`returnPhrase`/`walkthroughCopy`/`scoreBubbleCopy`; unit-tested |
| `frontend/src/components/train/trainBubbleState.ts` | Six-state precedence resolver | ✓ VERIFIED | Exists, `resolveBubbleState` exported, guard-clause style |
| `frontend/src/components/train/TrainBotBubble.tsx` | Presentational chat-row | ✓ VERIFIED | Exists, `ring`/`nudgeNonce`/`actions` props confirmed |
| `frontend/src/components/train/TrainBotStepper.tsx` | Forward-only stepper | ✓ VERIFIED | Exists, `nextTestId` extension confirmed, no `TrainLineStepper` import |
| `frontend/src/hooks/useTrainOnboarding.ts` | Stamp mutation hook | ✓ VERIFIED | `setQueryData(TRAIN_SETTINGS_QUERY_KEY` confirmed, no `invalidateQueries` |
| `app/models/train_settings.py` | 3 nullable timestamptz columns | ✓ VERIFIED | Confirmed via Alembic revision + model read |
| `app/schemas/train.py` | `OnboardingStep`, extended `TrainSettingsResponse`/`SolvedResult` | ✓ VERIFIED | `TrainSettingsUpdate` untouched (grep confirms no onboarding column names inside it) |
| `app/routers/train.py` | `POST /train/onboarding/{step}` | ✓ VERIFIED | 8/8 dedicated tests re-run passing this session |
| `app/repositories/train_repository.py` | `stamp_onboarding_step`, widened `_resume_session` | ✓ VERIFIED | First-write-wins guard, `_ONBOARDING_COLUMNS` dict confirmed |
| `app/services/activity_queries.py` | `fetch_train_funnel` | ✓ VERIFIED | Bound parameters only (`CAST(:cutoff AS date)`), no f-string SQL for this query (grep confirmed) |
| `frontend/src/pages/activity/render.js` / `ActivityPage.tsx` | Funnel card, `trf-*` DOM-id seam | ✓ VERIFIED | All 5 `trf-*` ids present on both sides |
| `.planning/seeds/SEED-167-train-sound-toggle-rehoming.md` | Follow-up seed, not promoted | ✓ VERIFIED | Exists, names `Bots.tsx`, absent from `ROADMAP.md` |
| `CHANGELOG.md` | Unreleased bullets, house voice | ✓ VERIFIED | 5 Train bullets under Unreleased covering intro, drop feedback, narrated verdict, actions-in-bubble, session summary; no file paths/D-NN/TRAINBOT-NN/testid strings found |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `personaRegistry.ts` `temperament` | `trainBotCopy.ts` `BY_TEMPERAMENT` | `Object.values().reduce()` | ✓ WIRED | Grep-confirmed, no hand-maintained id list |
| `trainBubbleState.resolveBubbleState()` | Single `<TrainBotBubble>` mount | `TrainSolveScreen`'s `columnRef` | ✓ WIRED | Exactly one `<TrainBotBubble` occurrence inside the measured board column |
| `trainGuessLabels.GUESS_LABELS`/`GUESS_CALL_LABELS` | Guess buttons / reveal header | Direct import | ✓ WIRED | `TrainReveal.tsx:1246` renders `GUESS_CALL_LABELS[guess]`; `Home.tsx`'s retired "critical move" marketing line confirmed rewritten (commit `118f12dd3`) |
| `api/client.ts trainApi.stampOnboarding` | `useTrainOnboarding` | `queryClient.setQueryData` | ✓ WIRED | Confirmed via grep in `useTrainOnboarding.ts` |
| `useTrainSettings().data.intro_seen_at` | `resolveIntroState` → bubble intro arm | Direct prop threading | ✓ WIRED | CR-01 fix confirmed present (failed fetch degrades to regular prompt, not a silent block) |
| `TrainSolveScreen` walkthrough state | `TrainReveal.walkthroughLinesRing` | One boolean prop (renamed from the planned `walkthroughStep` int, documented deviation) | ✓ WIRED | `walkthroughLinesRing` confirmed in `TrainReveal.tsx` props and ring application site; `TrainReveal.test.tsx` asserts the ring appears/doesn't per the flag |
| `fetch_train_funnel` | `Payload['train_funnel']` → `ActivityStatsPayload.train_funnel` → `render.js` `TRAINFUN` → `#trf-*` DOM ids | Sequential `await` in `build_payload` | ✓ WIRED | Confirmed end to end via grep at every hop |
| `useTrainSession.solvedOutcomes` | `TrainScoreScreen` bubble | `Train.tsx` prop threading | ✓ WIRED | `scoreBubbleCopy` unit-tested against both a seeded (resume) and a live-appended outcome array |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Onboarding endpoint contract (403 guest, 422 unknown step, first-write-wins, IDOR-scoped, etc.) | `uv run pytest tests/routers/test_train.py -q -k onboarding` | 8 passed | ✓ PASS |
| Funnel query cohort logic | `uv run pytest tests/test_admin_activity_stats.py -q -k funnel` | 2 passed | ✓ PASS |
| Core Train frontend surface (intro, nudge, verdict, score bubble, walkthrough, copy tables, bubble-state precedence) | `npx vitest run` on all 8 phase-touched test files | 302 passed | ✓ PASS |
| CR-01 regression (failed `/train/settings` fetch does not block the guess UI) | `npx vitest run -t "a failed settings fetch"` | 1 passed | ✓ PASS |
| `TrainSolveScreen` complexity ceiling | `npx eslint --no-inline-config --rule 'complexity: ["error", 67]' src/components/train/TrainSolveScreen.tsx` | exit 0, measured 61 | ✓ PASS |
| `TrainReveal` complexity unchanged | `npx eslint --no-inline-config --rule 'complexity: ["error", 1]'` | 68 (unchanged from pre-phase baseline) | ✓ PASS |
| Dead exports | `npm run knip` | 0 unused exports | ✓ PASS |
| Gate files untouched | `git diff --stat -- frontend/eslint.config.js frontend/package.json frontend/package-lock.json pyproject.toml uv.lock` | empty | ✓ PASS |

### Probe Execution

Not applicable — this phase declares no `scripts/*/tests/probe-*.sh` probes in any PLAN/SUMMARY, and it is not a migration/tooling phase in the probe-convention sense (it uses ordinary pytest/vitest suites, already exercised above). Skipped per the "no probes declared" branch.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|-------------|--------|----------|
| TRAINBOT-01 | 01, 04 | First-timer never hits a silent failure | ✓ SATISFIED | Intro stepper + drop nudge implemented and tested |
| TRAINBOT-02 | 01, 04, 07(06) | Guess prompt in bot bubble on every puzzle, board visible at 375px | ✓ SATISFIED | Bubble wiring + UAT-fixed 375px layout |
| TRAINBOT-03 | 01, 04 | Outcome-matched verdict bubble with pills + return statement | ✓ SATISFIED | `verdictCopy`/`returnPhrase`, unit-tested truth table |
| TRAINBOT-04 | 01, 02, 06(05) | Score screen states return before reminder ask | ✓ SATISFIED (2 of 4 variants live-unverified) | `scoreBubbleCopy` wired to `solvedOutcomes`; see human_verification |
| TRAINBOT-05 | 02, 04, 05, 06 | Server-side seen state, survives device switch | ✓ SATISFIED (device-switch leg deferred) | 3 columns, stamp endpoint, first-write-wins |
| TRAINBOT-06 | 03 | Both funnel metrics on the activity dashboard | ✓ SATISFIED (superuser render unobserved) | `fetch_train_funnel` + dashboard card wired |
| TRAINBOT-07 | 01 | Bot copy per outcome bucket, temperament-derived casting | ✓ SATISFIED | `temperament` field, `BY_TEMPERAMENT` |
| TRAINBOT-08 | 01 | "Only one"/"Several" vocabulary everywhere | ✓ SATISFIED | `GUESS_LABELS`/`GUESS_CALL_LABELS`, Home.tsx updated |
| TRAINBOT-09 | 04, 07(06) | Actions inside verdict bubble; mute toggle retired + follow-up seed | ✓ SATISFIED | `board-btn-mute` absent from Train's own files; `SEED-167` recorded |
| TRAINBOT-10 | 05(06) | First-reveal three-step Hilda walkthrough | ✓ SATISFIED | `walkthroughCopy`/`walkthroughLinesRing`, unit + live UAT confirmed on both viewports |

No orphaned requirements — all ten TRAINBOT-01..10 IDs declared in at least one plan's `requirements` frontmatter, and all are traced to committed code and tests above. (Note: the phase's task brief said "success criteria SC1-SC6" but ROADMAP.md's Phase 222 section actually enumerates SC1 through **SC7** — all seven were verified above; this looks like a minor drafting slip in the dispatch instructions, not a gap in the roadmap itself.)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`placeholder` found in any of the 17 core phase-touched source files | — | none |
| `frontend/src/lib/trainBotCopy.ts:170-177` vs `TrainSolveScreen.tsx:326-332` | — | WR-01 (222-REVIEW.md): verdict clause text computed twice by two independently-maintained functions (`verdictClause` vs `verdictClauseParts`); currently agree, nothing enforces it | ⚠️ Warning (advisory, non-blocking) | Drift risk on a future copy edit, not a current defect |
| `app/services/activity_queries.py:337-343` / `docs/activity-dashboard.md:117-121` | — | WR-02 (222-REVIEW.md): `completed_count` doesn't verify the cohort's own *first* session was the one completed; doc phrasing slightly overstates precision | ⚠️ Warning (advisory, non-blocking) | Documentation-precision gap, not a functional bug (matches `fetch_train`'s own existing definition) |
| `docs/activity-dashboard.md:129` | — | IN-01: stale "~16 queries" note after 2 more funnel queries landed | ℹ️ Info | Cosmetic doc staleness |
| `frontend/src/hooks/useTrainOnboarding.ts` / `TrainSolveScreen.tsx:1505-1507` | — | IN-02: `stamp('reveal_walkthrough')` has no `isPending` guard against a double-click; harmless given server-side first-write-wins | ℹ️ Info | Avoidable extra network round-trip only |

All four review findings are non-blocking (2 warnings, 2 info) per 222-REVIEW.md's own severity classification; the one CRITICAL finding (CR-01) was resolved in commit `bdc4a0fb4` with a regression test, independently re-run and confirmed passing in this verification.

### Human Verification Required

### 1. Score screen's full-explanation and one-liner variants on real solved SR material

**Test:** Complete a Train session's score screen with at least one missed SR item on a
real (non-warm-up) account, observe the full spaced-repetition explanation bubble; then
complete a second session and observe the one-liner variant.
**Expected:** First completed session with `sr_explained_at === null` and missed items > 0
renders the full D-25 explanation and stamps the timestamp exactly once; a later session
renders only the one-liner.
**Why human:** This session's UAT account had only warm-up puzzles; only that variant was
observed live. The other two variants are unit-tested at the component level but not
end-to-end browser-observed.

### 2. Phone-handoff device switch (SC5)

**Test:** Complete the first-session intro stepper on desktop, then open `/train` on a
phone signed into the same account.
**Expected:** The intro does not replay — `intro_seen_at` is server-side, not device-local.
**Why human:** Requires two physical devices signed into the same account; unavailable in
this session. The server-side persistence mechanism itself is migration- and unit-tested.

### 3. Activity dashboard funnel card, live superuser render (SC6)

**Test:** Open `/activity` as a superuser, locate the new Train funnel card, and move the
date-range window.
**Expected:** Both shares render with numerator/denominator and a live all-time line; the
windowed numbers move with the range while the all-time line holds steady.
**Why human:** This session's account is not a superuser. `fetch_train_funnel` was
independently re-verified against the dev DB at 7d/30d/90d/all-time windows (numbers move
correctly, all-time holds), and the automated `npm run check:activity-layout` harness
passed, but the actual on-screen card render was not eyeballed.

### Gaps Summary

No gaps. All ten TRAINBOT requirements are implemented, wired, and covered by passing unit
and integration tests re-run independently in this verification (302 frontend tests across
the phase's 8 core test files, 8 onboarding router tests, 2 funnel tests — all passing).
The phase's own CR-01 blocker (a persistent settings-fetch error silently hiding the guess
UI) was found by the phase's own code review and fixed with a regression test before this
verification ran; the fix was independently re-confirmed here. The remaining code-review
findings (WR-01, WR-02, IN-01, IN-02) are advisory/informational and do not block goal
achievement. The phase's own SUMMARY.md files are honest about three legitimately deferred
human-observation legs (SC4's two non-warm-up score-bubble variants, SC5's phone handoff,
SC6's superuser dashboard render) — none of these were fabricated as "passed" by inference,
and none indicate a code defect; they indicate device/account constraints in this session
that a human with the right test accounts can close quickly.

---

_Verified: 2026-09-13T18:09:40Z_
_Verifier: Claude (gsd-verifier)_
