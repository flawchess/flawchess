---
id: SEED-068
status: dormant
planted: 2026-06-26
planted_during: Phase 136 verify-work — UAT item 1 ("tab visible auto re-go after hidden pause") could not be tested manually (no UI until 137/138) and was deferred per user decision; this seed carries the confirmed bug found while reviewing the code.
trigger_when: when wiring `useStockfishEngine` into a real board UI in Phase 137 or 138 (the moment the tab-hide/visible path becomes observable), OR immediately if anyone touches the visibility / stale-eval guard logic in `useStockfishEngine.ts`.
scope: Tiny — frontend only. One early-return guard in `analyze()` + one deterministic mock-Worker unit test. No new deps, no API, no schema, no browser needed.
---

# SEED-068: Fix `useStockfishEngine` double-go when tab becomes visible during the 'stopping' window

## Why This Matters

Phase 136's verifier flagged a suspected ordering bug in the tab-hide → visible re-go path
(D-04). During Phase 136 verify-work the code was traced and the bug **confirmed**. It was
deferred (not fixed) because the path is only observable once a board UI wires up the hook —
rendering is deferred to Phases 137/138. When 137/138 build that UI, this needs fixing or the
engine will misbehave on the first real tab switch.

## The confirmed bug (verified 2026-06-26, `frontend/src/hooks/useStockfishEngine.ts`)

When the tab becomes **visible again during the brief `'stopping'` window** (after a
hide-triggered `stop`, but before the stale `bestmove` arrives):

1. `handleVisibility` visible branch (line ~296-302) calls `analyzeRef.current(current)`.
2. `analyze()` (line 150) only guards the `'thinking'` state (line 154) — **not** `'stopping'`.
   So it falls through and sends `position fen … ` + `go …` while `stopPendingRef` is still
   `true`.
3. The stale `bestmove` (termination response to the hide's `stop`) then arrives, hits the
   discard branch (line 225-235), sets `stateRef = 'idle'`, and re-analyzes the current FEN
   **again** → a *second* `position` + `go`.

Net result: two `go` commands with no intervening `stop` — a UCI protocol violation
(Stockfish requires `stop` before a new `go`). Manifests as stale-eval jitter or a missed
re-analysis on tab return.

Note the symmetric path is already correct: if the stale `bestmove` arrives *while still
hidden*, the discard branch skips re-analysis (`document.visibilityState !== 'hidden'` guard,
line 232), and a later visible event re-analyzes cleanly from `'idle'`. The bug is specific to
visible-during-`'stopping'`.

## The fix (when promoted — keep it tiny)

In `analyze()`, add an early return for the `'stopping'` state, mirroring the `'thinking'`
guard:

```ts
if (stateRef.current === 'thinking') { worker.postMessage('stop'); stopPendingRef.current = true; stateRef.current = 'stopping'; return; }
if (stateRef.current === 'stopping') return; // a stop is already pending; its bestmove-discard
                                             // handler (line ~231-234) re-analyzes currentFenRef
                                             // once visible → a single clean re-go.
```

Because `currentFenRef` already holds the latest FEN and the discard handler re-reads it, the
visible event needs no action while stopping — the in-flight stop's completion drives exactly
one re-go.

## Test (deterministic — no real browser)

Add a mock-Worker unit test to `frontend/src/hooks/__tests__/useStockfishEngine.test.ts`:
hide-during-`thinking` (assert `stop` sent, worker alive), then fire `visibilitychange` →
visible while still `'stopping'`, then deliver the stale `bestmove`. Assert **exactly one**
`position`+`go` pair is sent after the stale bestmove (no double-go), and `isAnalyzing`
settles true. This also closes the coverage gap the verifier noted (the visible→re-go
transition is currently untested).

## Cross-References

- Phase 136 `136-VERIFICATION.md` (status `human_needed`, item 1) and `136-UAT.md` (test 1
  skipped, Gaps section) — the origin of this seed.
- `SEED-066-live-engine-analysis-page.md` — the live-engine milestone this hook feeds.
- `useStockfishEngine.ts` Pitfall 3 (stale eval race) comments — the same stale-eval guard
  machinery this bug lives inside.
