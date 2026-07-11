---
phase: 165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l
reviewed: 2026-07-11T13:44:11Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - scripts/lib/frontend-alias-hook.mjs
  - scripts/lib/gem-parity.check.mjs
  - scripts/gem-elo-calibration.mjs
  - frontend/src/lib/analysisUrl.ts
  - frontend/src/lib/analysisUrl.test.ts
  - frontend/src/pages/Analysis.tsx
findings:
  critical: 1
  warning: 2
  info: 5
  total: 8
status: issues_found
---

# Phase 165: Code Review Report

**Reviewed:** 2026-07-11T13:44:11Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the phase-165 additions: a headless Node gem-move ELO calibration harness
(`gem-elo-calibration.mjs`) plus its `@/` resolve hook and Wave-0 parity check, and the
additive `?fen=` analysis deep-link (`analysisUrl.ts` + seeding effects in `Analysis.tsx`).

The harness wiring is sound in the important places: it imports the live frontend
`classifyGem`/`summarizeForGem`/`maskAndSoftmax`/`eloToInput`/`parseInfoLine` through the
`@/` hook (no re-derivation), the SAN keyspaces are all chess.js-generated and therefore
consistent across sampling / grading / Maia-policy lookup, the white-POV sign conversion in
`gradePosition` is correct, and `maiaProbsForPosition` faithfully mirrors production
`maia-worker.js` (elo_self === elo_oppo, same tensor layout and slicing) — so calibration
fidelity is preserved.

One BLOCKER: the `?fen=` defensive guard (`parseAnalysisFenParam`), whose entire stated
purpose (T-165-03) is to prevent a garbage URL from crashing the board, itself throws an
uncaught `URIError` on a malformed percent-escape because `decodeURIComponent` sits outside
its try/catch (and is a redundant double-decode of an already-decoded param). The remaining
findings are harness robustness (a single Stockfish timeout discards the whole multi-hour
run; silent NaN coercion of CLI numeric flags) and minor notes.

## Critical Issues

### CR-01: `?fen=` guard crashes on malformed percent-escape (uncaught URIError, defeats T-165-03)

**File:** `frontend/src/lib/analysisUrl.ts:114-123`

**Issue:** `parseAnalysisFenParam` places `decodeURIComponent(fenParam)` OUTSIDE its
try/catch:

```ts
export function parseAnalysisFenParam(fenParam: string | null): string | null {
  if (!fenParam) return null;
  const fen = decodeURIComponent(fenParam);   // <-- outside try: throws on bad %
  try {
    new Chess(fen);
    return fen;
  } catch {
    return null;
  }
}
```

`react-router`'s `useSearchParams().get('fen')` (Analysis.tsx:446) already returns a
percent-decoded value, and `URLSearchParams` is lenient about malformed escapes — it leaves
a stray `%` literal. `decodeURIComponent` is NOT lenient: it throws `URIError`. Verified:

```
"%"    -> URLSearchParams.get -> "%"   -> decodeURIComponent throws URIError
"50%"  -> URLSearchParams.get -> "50%" -> decodeURIComponent throws URIError
"%zz"  -> URLSearchParams.get -> "%zz" -> decodeURIComponent throws URIError
```

`parseAnalysisFenParam` is called from a `useMemo` during render (Analysis.tsx:447), so a URL
like `/analysis?fen=%` or `/analysis?fen=50%` throws during render and crashes the Analysis
page — exactly the "hand-typed or garbage URL degrades to free-play-start rather than
crashing the board" scenario the guard's own doc comment and the security header
(Analysis.tsx:18) promise it prevents. The test suite's "garbage input" case (`'not-a-fen'`)
never exercises the decode path, so this slips through.

Note this is also a **redundant double-decode**: the incoming param is already decoded by
react-router (and by `URLSearchParams` in the round-trip test), so the second decode is both
unnecessary and the sole crash source. FENs contain no `%`, so for valid input the second
decode is a harmless no-op — which is why existing tests pass.

**Fix:** Drop the redundant decode (the param is already decoded), or at minimum move it
inside the try. Cleanest:

```ts
export function parseAnalysisFenParam(fenParam: string | null): string | null {
  if (!fenParam) return null;
  try {
    new Chess(fenParam);      // param already URL-decoded by URLSearchParams
    return fenParam;
  } catch {
    return null;              // malformed/garbage -> free-play start (T-165-03)
  }
}
```

Add a regression test with a raw `%` value (e.g. `expect(parseAnalysisFenParam('50%')).toBeNull()`).

## Warnings

### WR-01: A single Stockfish timeout aborts the entire run and discards all accumulated rows

**File:** `scripts/gem-elo-calibration.mjs:463-509, 631-673`

**Issue:** `gradePosition` awaits `bestmove` with a timeout (`movetimeMs + slack`, line 477).
On timeout it rejects; the rejection propagates out of the per-position loop (which has only
a `finally` that terminates Stockfish, no `catch`), up to `main().catch` → `process.exitCode
= 1`. The TSV/summary are written only AFTER the loop completes (lines 668-673), so a single
slow/hung position on a 3000-position, multi-hour run discards every result gathered so far
with zero output. A transient engine hiccup shouldn't cost the whole run.

**Fix:** Wrap the per-position body in try/catch to skip-and-count a failed position
(increment a `skippedGradeFailure` counter, emit an empty/NA row) and continue, and/or write
the TSV incrementally (append per row) so partial results survive an abort.

### WR-02: CLI numeric flags silently coerce to NaN (empty output with no error)

**File:** `scripts/gem-elo-calibration.mjs:87-136`

**Issue:** `parseArgs` does `Number.parseInt(value, 10)` with no validation. A flag given
with no following value (e.g. `--n` at the end, or a typo consuming the next flag as its
value) yields `NaN`. With `args.n = NaN`, `sampleStratified` computes `baseCapacity =
Math.floor(NaN / S) = NaN`, every capacity is `NaN`, all `capacity > 0` checks are false, and
nothing is sampled — the harness loads Maia + Stockfish, iterates zero positions, and writes
an EMPTY TSV with exit code 0. A developer running an expensive job gets a silent empty
result. Separately, `--csv`/`--out-dir` with no value calls `path.resolve(undefined)`, which
throws an opaque `TypeError`. Only `--rungs` is validated (via `validateRungs`).

**Fix:** After parsing, validate each numeric arg (`Number.isFinite` and `> 0` where
applicable) and the presence of string-arg values; throw a clear error naming the offending
flag before any engine is loaded.

## Info

### IN-01: Reservoir sampling increments `seenCounts` before lazy validation (slight bias)

**File:** `scripts/gem-elo-calibration.mjs:266-315`

**Issue:** `seenCounts[stratum]++` runs before the FEN/SAN validation. A row that wins a
replacement-phase slot but then fails validation returns early (keeping the old sample) while
having already advanced the stratum's Algorithm-R counter, which slightly biases selection
probabilities. Negligible in practice because the input CSV (`brilliants_no_stalemates.csv`)
is pre-validated, so validation failures are rare — but worth a note if a rawer CSV is ever
fed in. Consider validating before consuming a reservoir slot, or documenting the assumption.

### IN-02: `frontend-alias-hook.mjs` hardcodes the `.ts` extension

**File:** `scripts/lib/frontend-alias-hook.mjs:38-42`

**Issue:** The resolve hook always maps `@/x` → `frontend/src/x.ts`. A future `@/` import of a
`.tsx` file or a directory/index module would fail to resolve. Current imports are all `.ts`
and the module doc scopes this deliberately, so this is just a maintainer footgun to note
(consider a small extension-probe or a clearer throw if the `.ts` file is absent).

### IN-03: Stockfish temp `.cjs`/`.wasm` copies are never cleaned up

**File:** `scripts/gem-elo-calibration.mjs:433-454`

**Issue:** `spawnStockfish` copies the engine glue + wasm into `os.tmpdir()` keyed by pid.
`terminate()` kills the child but never removes the temp files, so each run leaves ~a few MB
of litter in the temp dir. Minor. Consider `fs.rmSync` of both paths in `terminate()` or a
`process.on('exit')` cleanup.

### IN-04: Changing `?fen=`/`?line=` on an already-mounted Analysis page won't reseed

**File:** `frontend/src/pages/Analysis.tsx:641-704`

**Issue:** All three seeding effects gate on `hasLoadedMainLine.current`, a ref that persists
for the component's lifetime. A soft (SPA) navigation from `/analysis?fen=A` to
`/analysis?fen=B` (same route, changed query) would not reseed and would show a stale board.
This matches the pre-existing `?line=`/game-mode behavior and is largely moot because TSV
deep-links open as fresh full-page loads (remount), but flagging for awareness — if any
in-app UI ever soft-links between two `?fen=` targets it will surface.

### IN-05: `computeStrataEdges` yields `undefined` edges on a fully-empty/all-skipped CSV

**File:** `scripts/gem-elo-calibration.mjs:207-221`

**Issue:** With `scores.length === 0`, `Math.min(scores.length - 1, ...)` is `-1`, so
`scores[-1]` (`undefined`) is pushed into `rawEdges`. Degenerate-input only (empty or fully
unparseable CSV) — downstream `stratumIndex` then misbehaves silently. Low priority; a guard
that throws a clear "no valid rows in CSV" error would be friendlier than producing an empty
output.

---

_Reviewed: 2026-07-11T13:44:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
