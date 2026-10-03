---
phase: 229-umami-identify-feature-events
plan: 08
subsystem: analytics
status: complete
tags: [frontend, analytics, umami, bots, docs, gate, uat]

requires: [229-03, 229-04, 229-05, 229-06, 229-07]
provides:
  - "Bot feature events: action bot-resume, bot-discard, bot-rematch, bot-new-game, analyze, bot-draw-decline, bot-return-live"
  - "frontend/CLAUDE.md feature-event rule and identity notes"
  - "CHANGELOG [Unreleased] analytics/privacy and Umami 3.4.0 bullets"
  - "229-VALIDATION.md final statuses, gate record, browser UAT and post-deploy scripts"
affects: []

actuals:
  tokens: 22000
  tasks: 3
  commits: 3
plan_head_before: 0aafe4349fc895fa98e85159643d584c9b290f01
plan_head_after: 68e29d9a3a19d4e838a4e281bcc96678a86673b0

tech-stack:
  added: []
  patterns:
    - "Tracking fires inside the click handler after the existing callback"

key-files:
  created: []
  modified:
    - frontend/src/components/bots/ResumeGate.tsx
    - frontend/src/components/bots/GameResultDialog.tsx
    - frontend/src/components/bots/BotDrawOfferActions.tsx
    - frontend/src/components/bots/MoveListPanel.tsx
    - frontend/src/components/bots/__tests__/GameResultDialog.test.tsx
    - frontend/src/components/bots/__tests__/ResumeGate.test.tsx
    - frontend/CLAUDE.md
    - CHANGELOG.md
    - .planning/notes/active-engagement-time-tracking.md
    - .planning/phases/229-umami-identify-feature-events/229-VALIDATION.md

key-decisions:
  - "bot-resume, bot-discard, bot-rematch and bot-new-game are all tracked: none of their handlers writes to the backend"
  - "Accept on a draw offer stays untracked (the drawn result is DB-known); Decline is tracked"

requirements-completed: [D-05, D-06, D-12, D-15, D-17]

coverage:
  - id: C1
    description: "Bot Resume, confirmed Discard, Rematch, New opponent, Analyze, draw Decline and Return to live send typed action events; first Discard click, Cancel and a busy Analyze send nothing"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultDialog.test.tsx#GameResultDialog feature events (Phase 229)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/ResumeGate.test.tsx#ResumeGate feature events (Phase 229)"
        status: pass
    human_judgment: false
  - id: C2
    description: "Full pre-merge gate (backend + frontend incl. knip) green; all 11 legacy events still emitted"
    verification:
      - kind: command
        ref: "ruff, ty, check_function_size, pytest -n auto -x, npm run lint/build/test/knip"
        status: pass
    human_judgment: false
  - id: C3
    description: "Inventory events, guest identify, impersonation skip and logout reset in a real browser"
    human_judgment: true
    rationale: "Browser UAT is run by the orchestrator via claude-in-chrome; script is in 229-VALIDATION.md"
  - id: C4
    description: "Post-deploy: Umami 3.4.0 running, first pageview carries id, identified sessions above 0"
    human_judgment: true
    rationale: "Depends on the owner's release; read-only checks scripted in 229-VALIDATION.md"

duration: 35min
completed: 2026-10-03
---

# Phase 229 Plan 08: Bot actions, docs rule and pre-merge gate Summary

The last D-12 surface (bot in-game actions) now reports typed Umami events, the feature-event rule and identity notes are in `frontend/CLAUDE.md`, the changelog carries the analytics/privacy and Umami 3.4.0 notes, and the full pre-merge gate is green with knip clean.

## What was built

- `ResumeGate.tsx`: `handleResume` fires `action bot-resume`; `handleConfirmDiscard` fires `action bot-discard` (the first Discard click only opens the confirm and sends nothing).
- `GameResultDialog.tsx`: Rematch fires `bot-rematch`, New opponent `bot-new-game`, Analyze this game `analyze`.
- `BotDrawOfferActions.tsx`: Decline fires `bot-draw-decline`; Accept stays untracked.
- `MoveListPanel.tsx`: Return to live position fires `bot-return-live`.
- Tests: `GameResultDialog.test.tsx` (3 cases) and `ResumeGate.test.tsx` (2 cases, outside the plan's declared files but it is the plan's own `<verify>` suite and covers the resume/discard prohibition).
- `frontend/CLAUDE.md`: section renamed "Umami analytics (outbound links, feature events, identity)" with Outbound links, Feature events (D-15 rule) and Identity subsections; DB-known bullet reworded around `distinct_id`.
- `CHANGELOG.md`: user-facing account-ID analytics bullet plus the operator Umami 3.4.0 pin note under `[Unreleased]` / `### Changed`.
- `.planning/notes/active-engagement-time-tracking.md`: SEED-183 supersession pointer and the localStorage correction.
- `229-VALIDATION.md`: all rows green, `nyquist_compliant: true`, `wave_0_complete: true`, gate record, browser UAT script, post-deploy script.

## Tracked vs left out (DB-known evidence)

| Action | Decision | Evidence |
|---|---|---|
| bot-resume | Tracked | `ResumeGate` `onResume` is `game.confirmLive` (`pages/Bots.tsx:547`; `useBotGame.ts:473`), local state only |
| bot-discard | Tracked | `handleDiscard` (`pages/Bots.tsx:709-715`) calls `clearSnapshot(ownerKey)` (localStorage) and resets local state; no API call |
| bot-rematch | Tracked | `handleRematch` -> `handleStart` (`pages/Bots.tsx:379`, `:665-680`) starts a local game; the game row is stored only at finish |
| bot-new-game | Tracked | `handleNewGame` (`pages/Bots.tsx:684-689`) resets local state only |
| analyze | Tracked | Per plan; the click enqueues tier-1 analysis (`handleAnalyze`, `pages/Bots.tsx:360-376`) but the plan lists it as tracked, consistent with Train's `analyze` from 229-07 |
| bot-draw-decline | Tracked | Local state only |
| draw Accept, resign, results | Un-evented | Result is DB-known (bot game store at finish) |

`GameResultStrip` is referenced only in comments (no such component exists anymore), so the dialog is the single result surface.

## Gate transcript (task 3)

| Step | Result |
|---|---|
| `ruff format` / `ruff check --fix` | clean, no files modified |
| `ty check app/ tests/ scripts/` and `analysis/` | all checks passed |
| `check_function_size.py app/ --fail-over-depth 4` | OK, 1077 functions, no breaches |
| `pytest -n auto -x -q` | 4985 passed, 19 skipped |
| `npm run lint`, `npm run build` | clean |
| `npm test -- --run` | 293 files, 4780 tests passed |
| `npm run knip` | exit 0; only a pre-existing `.css` "compiled extension excluded" configuration hint. Every registry export has a consumer, so no consumer needed wiring and no export was removed |

The gate modified no files, so no style commit was needed. Worktree setup: `uv sync --group maia-inference` and `npm ci` in `frontend/` (lockfile installs, no package added).

## D-05 emitter check

Non-test emitters still present in `frontend/src` (excluding `lib/analytics.ts`): signup-cta (8 sites, Home/Welcome/SignupAskActions and others), import-cta (ImportAskActions), guest-start (Home), pwa-installed and pwa-install-outcome (useInstallPrompt), pwa-install-offer-shown (InstallPromptBanner), settings-change and settings-reset (SettingsPanel), engine-gate-shown/started/abandoned (EngineReadyGate). `git diff main --stat` over those 8 emitter files is empty, so none was touched by this phase. 32 `outbound-` references remain.

## Payload hygiene

86 `trackFeature` call sites (multi-line aware scan). The only template literal is `EloSelector.tsx:109`, `` `${snapToLadder(committed, ladder)}` ``, a `MAIA_ELO_LADDER` rung typed `${number}` in the registry. No call concatenates runtime strings. Popover targets go through `popoverTargetFromTestId`.

## Deviations from Plan

**1. [Scope] Extra tests in ResumeGate.test.tsx**
- The plan's file list names only `GameResultDialog.test.tsx`; `ResumeGate.test.tsx` is in the plan's verify command and carries the resume/confirmed-discard assertions (first click and Cancel send nothing), so tests were added there.

**2. [Rule 2 - wording] Feature-event rule wording**
- The plan's CLAUDE.md text did not say how to treat handlers that write to the backend; the DB-known guidance is stated as "a handler whose whole effect is a backend write that lands in a table (train retry, bookmark save) stays un-evented". Analyze (enqueue then navigate) is tracked, matching the plan and 229-07.

Notes on prior-wave deviations (reflected, not fixed): 229-07 tracks Analyze once in `handleAnalyzeClick` and leaves train retry un-evented; 229-06 acceptance greps print more than 1 because of pre-existing testid substrings; 229-05 added `snapToLadder` in `EloSelector`; 229-07 added tests in `SetupScreen.test.tsx` and `PersonaCard.test.tsx`. None blocked the gate.

**Total deviations:** 2 minor (scope and wording). **Impact:** none on behavior.

An in-task mutation check (changing `bot-rematch` to `bot-new-game`) failed the new Rematch test as required. The revert initially used `git checkout --` on the still-uncommitted file and dropped the edits; they were restored from a backup copy and re-verified (acceptance greps 2/1/1/1, lint, build, 415 bots+pages tests green) before the commit.

## Known Stubs

None.

## Threat Flags

None. Bot targets are fixed literals (T-229-21); draw accept, resign and results stay un-evented; resume/discard/rematch/new game were traced to their handlers; UAT evidence guidance restricts to dev ids (T-229-22); the CLAUDE.md rule plus the typed registry address T-229-23.

## Pending (not run here)

- Browser UAT (orchestrator, claude-in-chrome, dev build): script in `229-VALIDATION.md` "Browser UAT script".
- Post-deploy checks after the owner's release: script in `229-VALIDATION.md` "Post-deploy verification". Umami 3.4.0 image pull and two additive migrations happen on that deploy.

## Self-Check: PASSED

- Commits `99b0121f9`, `0f83b9a9a`, `68e29d9a3` exist on the worktree branch.
- Modified files listed in key-files exist; no STATE.md or ROADMAP.md changes.
