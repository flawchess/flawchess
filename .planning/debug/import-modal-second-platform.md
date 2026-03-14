---
status: diagnosed
trigger: "Import modal doesn't allow importing from second platform"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: Sync view conditionally renders Sync button only when username exists; shows plain "Not set" text with no action for unconfigured platforms
test: Read sync view rendering logic in ImportModal.tsx
expecting: Conditional rendering that omits any input/action for null usernames
next_action: Document root cause

## Symptoms

expected: Sync view should provide a way to add a username for a second platform (input field or "Add" button)
actual: Sync view shows "Not set" as plain text for unconfigured platforms with no input or action button — user must click "Edit usernames" to get back to the input view
errors: None (UX issue, not a runtime error)
reproduction: 1) Import from chess.com, 2) Open import modal again, 3) Sync view shows chess.com with Sync button but lichess only shows "Not set"
started: Always been this way since sync view was implemented

## Eliminated

(none needed - root cause found on first inspection)

## Evidence

- timestamp: 2026-03-14T00:00:00Z
  checked: ImportModal.tsx lines 167-233 (sync view branch)
  found: |
    Each platform row (lines 170-190 for chess.com, 192-212 for lichess) uses the same pattern:
    - If username exists: show username text + Sync button
    - If username is null: show "Not set" text and NO button/input at all

    Specifically, lines 180-189 and 202-211 wrap the Sync button in `{profile?.chess_com_username && (...)}`
    and `{profile?.lichess_username && (...)}` respectively. When username is null, nothing renders
    in that space — no "Add" button, no inline input.

    The only way to add a second platform username is the small "Edit usernames" link at the bottom (line 216-222)
    which sets editMode=true, switching back to the full input view.
  implication: The sync view was designed only for the "returning user syncing existing platforms" case, not the "user wants to add a new platform" case.

- timestamp: 2026-03-14T00:00:00Z
  checked: View selection logic (lines 49-50)
  found: |
    `isFirstTime` is true only when BOTH usernames are null. Once one is set, `isFirstTime` is false
    and the sync view renders (unless editMode is true). This means after importing from one platform,
    the user always lands in the sync view where the second platform has no action affordance.
  implication: Confirms the gap — the sync view needs an "Add" action for unconfigured platforms.

## Resolution

root_cause: |
  In ImportModal.tsx sync view (lines 170-212), each platform row conditionally renders the Sync button
  ONLY when `profile?.{platform}_username` is truthy. When a username is null, the row shows "Not set"
  as plain text with no interactive element. The user's only path to add a second platform username is
  the small "Edit usernames" link at the bottom, which is not discoverable.

  Specifically:
  - Line 180: `{profile?.chess_com_username && (<Button>Sync</Button>)}`
  - Line 202: `{profile?.lichess_username && (<Button>Sync</Button>)}`

  These conditionals need an `else` branch that renders an "Add" button (to enter editMode or show an
  inline input) for unconfigured platforms.

fix: (not applied — diagnosis only)
verification: (not applicable)
files_changed: []
