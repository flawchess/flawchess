---
status: resolved
trigger: "Phase 171 UAT gap: after a bot game, the post-game 'Analyze this game' link opens the analysis board NOT flipped to the player's own perspective when the player played black."
created: 2026-07-14
updated: 2026-07-14
resolved_by: "171-08 — orientation param added to the /analysis free-play URL contract; mutation-verified."
---

## Current Focus

hypothesis: The bot-game "Analyze this game" navigation does not carry the player's color, so the analysis board falls back to a white-at-bottom default.
test: Trace `onAnalyze` from GameResultDialog/GameResultStrip to the navigation target, then read how the analysis page derives boardOrientation.
expecting: A navigate(...) call missing a color param, OR an analysis page whose orientation logic reads a field the bot route never supplies.
next_action: Read frontend/src/components/bots/GameResultDialog.tsx and GameResultStrip.tsx, then grep for the onAnalyze owner (bots page/hook).

## Symptoms

expected: Analysis board opens oriented from the player's own color (black at bottom when the player played black).
actual: Analysis board opens white-at-bottom regardless of the color the player played in the bot game.
errors: none (silent wrong-orientation, not a crash)
reproduction: Play a bot game as black -> finish it -> click "Analyze this game" in the post-game panel -> analysis board shows white at bottom.
started: Phase 171 (bots page / setup screen / nav) — new surface.

## Eliminated

## Evidence

- timestamp: 2026-07-14
  checked: grep for "Analyze this game" in frontend/src
  found: Two bot post-game surfaces both expose an `onAnalyze` callback prop — components/bots/GameResultDialog.tsx:80 (data-testid="btn-analyze-game") and components/bots/GameResultStrip.tsx:53 (data-testid="strip-btn-analyze-game"). Neither owns the navigation; both delegate to an onAnalyze passed from a parent.
  implication: The navigation target (and any orientation param) is decided by the parent that supplies onAnalyze, not by the dialog/strip. Must find that parent.

- timestamp: 2026-07-14
  checked: pages/Bots.tsx handleAnalyze (309-311) + surrounding color state
  found: handleAnalyze = navigate(buildAnalysisLineUrl(game.moveHistory)) — carries ONLY the move list. settings.userColor is in scope right below (313-314: `const flipped = settings.userColor === 'black'`) but is never passed to the URL builder.
  implication: The player's color is available at the call site and simply dropped. Bot games land on /analysis in FREE-PLAY (?line=) mode, not game mode.

- timestamp: 2026-07-14
  checked: lib/analysisUrl.ts (whole module)
  found: Param consts are LINE/GAME_ID/PLY/FEN only (24-28). buildAnalysisLineUrl(sans: string[]) (39-52) has no color/orientation parameter in its signature. grep for flip|color|orient across analysisUrl.ts + its test file returns NONE.
  implication: There is no orientation param in the /analysis URL contract at all. The link is not merely "missing a param" — the param does not exist yet.

- timestamp: 2026-07-14
  checked: pages/Analysis.tsx param parsing + board-flip effect
  found: searchParams.get() is called ONLY for 'line', 'fen', 'game_id', 'ply'. isGameMode = gameId != null (464). boardFlipped = useState(false) (475). The auto-flip effect (666-670) reads `if (!isGameMode || gameData?.user_color == null || hasAutoFlipped.current) return;` then setBoardFlipped(gameData.user_color === 'black'). Its own comment (665) states: "Free play stays white."
  implication: ROOT CAUSE. The only "flip to my color" logic is gated on game mode AND derives color from backend-fetched gameData.user_color (via game_id). A ?line= URL is free-play → isGameMode false → the effect early-returns → boardFlipped stays at its `false` initial → white at bottom, regardless of the color the player played.

- timestamp: 2026-07-14
  checked: components/bots/GameResultDialog.tsx:87-89 + GameResultDialog.test.tsx V-17 tests
  found: Deliberate Phase 171 decision (D-20/D-21, V-17): the Analyze button is explicitly NOT gated on the store and NOT "re-pointed at the stored game" — it must work for guests and when storeSucceeded is false.
  implication: Constrains the fix. Switching handleAnalyze to buildGameAnalysisUrl(storedGameId) — which WOULD auto-flip via the existing game-mode effect — is off the table: it violates V-17 and breaks guests (no stored game). The fix must make free-play mode orientable.

## Resolution

root_cause: The bot "Analyze this game" button navigates to /analysis in free-play (?line=) mode, but Analysis.tsx's only board-auto-flip effect (pages/Analysis.tsx:666-670) is gated on `isGameMode` (game_id present) and sources the color from backend-fetched `gameData.user_color`; free play has no orientation input at all (no color param exists in lib/analysisUrl.ts), so boardFlipped stays at its `useState(false)` default — white at bottom — even though Bots.tsx has `settings.userColor` in scope at the call site.
fix: NOT APPLIED (diagnose-only mode)
verification: n/a
files_changed: []
