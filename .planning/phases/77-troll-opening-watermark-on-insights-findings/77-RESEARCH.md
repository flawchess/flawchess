# Phase 77: Troll-opening watermark on Insights findings — Research

**Researched:** 2026-04-28
**Domain:** Frontend visual decoration + offline curation script (Node/TS)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Curation breadth**
- **D-01:** Strict (Bongcloud-tier) only. Curate to unambiguously meme/troll openings — Bongcloud, Grob, Borg, Halloween Gambit, Barnes, Fred, and any clearly non-serious entries from Lichess study `cEDAMVBB`. Exclude "fun but legitimate" gambits (Englund, Latvian, From's, Schliemann, Damiano). Final TSV will be hand-pruned during the curation script run; downstream agents must surface the pruned candidate list to the user before committing.

**Visual placement**
- **D-02:** Anchored bottom-right inside `OpeningFindingCard`. Sized like a stamp/seal (~60–80px), absolutely positioned, behind text via `z-index`. 30% opacity is locked.
- **D-03:** Mobile parity — same anchor (bottom-right), same opacity, same SVG sizing. Re-verify at 375px that the watermark doesn't clip or fight the prose/links column.
- **D-04:** Watermark must not block clicks on `Moves` / `Games` link buttons — use `pointer-events: none` on the SVG layer.

**Severity behavior**
- **D-05:** Show always. Watermark fires whenever the finding's position is in the troll set, regardless of `classification` or `severity`.

**Move Explorer surface**
- **D-06:** Add a small inline troll-face icon to `MoveList` rows in the Move Explorer when the *resulting* position (after applying the candidate move) is in the troll set for the side that just moved. Fully-opaque, small glyph next to the SAN.
- **D-07:** **Desktop only.** Mobile move list uses `h-12` row height vs. desktop's `h-18`; suppress on mobile via the existing `sm:` breakpoint or `hidden sm:inline-flex`.

**Matching strategy (frontend-only)**
- **D-08:** Derive a deterministic user-side-only key from FEN piece placement on the client. Strip opponent pieces from the placement field (lowercase chars for white-side keys, uppercase for black-side), re-canonicalize consecutive empty squares, and use the resulting string as a `Set<string>` key. Utility lives in `frontend/src/lib/trollOpenings.ts` (or sibling).
- **D-09:** Pre-compute keys offline with a small Node/TS curation script that walks `cEDAMVBB.pgn` via chess.js, extracts the defining position of each chapter, derives the side-only key for the troll player's color, and emits a literal TS data file `frontend/src/data/trollOpenings.ts` exporting two `Set<string>` (white-side keys, black-side keys). Hand-pruning per D-01 happens during the script run, before commit. Script is committed alongside the data file.
- **D-10:** Insights surface uses `finding.entry_fen` + `finding.color`. Move Explorer surface uses `entry.result_fen` + the side that just moved (derived from the parent position's side-to-move).

**Asset**
- **D-11:** Move `temp/Troll-Face.svg` → `frontend/src/assets/troll-face.svg` (kebab-case). Delete the `temp/` copy in the same commit. Imports via Vite's asset pipeline.

### Claude's Discretion

- Exact pixel size of the watermark on `OpeningFindingCard` (60–80px guideline; tune against `MOBILE_BOARD_SIZE = 105` and `DESKTOP_BOARD_SIZE = 100`).
- Exact pixel size of the inline icon in the Move Explorer move list — should match adjacent `lucide-react` icons (likely `h-3.5 w-3.5` or `h-4 w-4`).
- Whether the card watermark sits as a sibling element absolutely positioned via Tailwind (`absolute bottom-2 right-2 opacity-30 pointer-events-none`) or as a CSS `background-image`. Sibling element preferred.
- Where exactly the inline Move Explorer icon sits within the row.
- Test framing — frontend unit test for the user-side-key utility, snapshot/visual tests for both surfaces.
- Curation script's network behavior — local PGN cache fine; script must be re-runnable offline.

### Deferred Ideas (OUT OF SCOPE)

- Troll-opening icon on Bookmarks, Games tab, or Endgame surfaces.
- Mobile rendering of the Move Explorer icon.
- LLM narration referencing troll status.
- Per-user opt-out / settings toggle.
- Suppress-when-winning logic (rejected D-05).
- Score/severity adjustment for troll openings.
- Backend matching via Zobrist hash (rejected in favor of frontend FEN-key approach D-08).

</user_constraints>

## Summary

Phase 77 ships two purely visual decorations driven by a static client-side lookup. There is no backend work — `OpeningInsightFinding.entry_fen` and `NextMoveEntry.result_fen` already carry everything the matcher needs. The work decomposes cleanly into four units:

1. A pure-string utility (`stripOpponentPieces(boardFen, side)`) that produces a deterministic user-side-only key from a FEN piece-placement field. Pure function, fully unit-testable with golden inputs.
2. An offline curation script (Node/TS) that walks the Lichess study `cEDAMVBB.pgn` via chess.js, extracts the defining position of each chapter, derives the side-only key for the troll player's color, and emits a literal TS module `frontend/src/data/trollOpenings.ts` with two `Set<string>` exports.
3. A bottom-right `<img>` watermark layer on `OpeningFindingCard` (sibling element, `pointer-events: none`, `opacity-30`, both desktop and mobile branches).
4. An inline SAN-row icon in the Move Explorer (`MoveExplorer.tsx` `<MoveRow>`), gated on `hidden sm:inline-flex`.

**Primary recommendation:** Implement the utility module first with golden-FEN unit tests; run the curation script and surface the pruned candidate list to the user *before* committing `trollOpenings.ts`; then layer the visual changes onto the two consumers. Vite's default behavior for SVG imports (the project does not use `vite-plugin-svgr`) is URL-string, so the asset is rendered via `<img src={trollFace} />`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Curation of troll-opening positions | Build-time / offline script | — | One-shot data generation; output is committed static data. No runtime cost. |
| User-side key derivation | Browser / Client | — | Pure string transform on existing payload fields. Memoizable, testable in isolation. |
| Static curated set lookup | Browser / Client | — | `Set<string>` literal in a TS data module. Tree-shakable. Trivial memory cost. |
| Watermark rendering on `OpeningFindingCard` | Browser / Client | — | Decorative `<img>` sibling positioned via Tailwind utilities. |
| Inline icon rendering on Move Explorer rows | Browser / Client | — | Conditional `<img>` inside the existing `<MoveRow>` table cell. |

Backend, API, database, and CDN tiers are explicitly untouched. This is a frontend-only phase.

## Phase Requirements

No phase-level requirement IDs are mapped (the v1.14 milestone REQUIREMENTS.md catalogues INSIGHT-SCORE-* and INSIGHT-UI-* for Phases 75/76 only — Phase 77 is a discretionary v1.14 add-on per ROADMAP.md). The phase's deliverables are implicitly specified by CONTEXT.md decisions D-01..D-11 above. The plan-checker should treat the locked decisions as the requirement equivalents.

## Project Constraints (from CLAUDE.md)

The following project directives directly bear on this phase. The plan must honor each one.

- **Theme constants in `frontend/src/lib/theme.ts`** — colors with semantic meaning live in `theme.ts`. The 30% opacity value should be a named constant (e.g. `TROLL_WATERMARK_OPACITY`). `lib/theme.ts` already exports `UNRELIABLE_OPACITY` as precedent.
- **`noUncheckedIndexedAccess` is enabled** — every array/Record index access in the curation script and the utility returns `T | undefined`. Narrow before use; never use `// @ts-ignore`.
- **Knip runs in CI** — every export from `frontend/src/data/trollOpenings.ts` and `frontend/src/lib/trollOpenings.ts` (or wherever the helper lives) must be imported somewhere. Two unused `Set<string>` exports would fail CI.
- **`data-testid` on every interactive element; semantic decorative elements get one too for snapshot tests** — CONTEXT.md mandates `data-testid="opening-finding-card-{idx}-troll-watermark"` and `data-testid="move-list-row-{san}-troll-icon"` (or equivalent). Both are non-interactive (`pointer-events: none` on watermark; icon sits inside row click handler).
- **`aria-label` on icon-only elements** — the watermark `<img>` should have descriptive `alt=""` (decorative) or `alt="Troll opening"` (semantic). The Move Explorer inline icon should also carry `alt=""` to avoid screen-reader noise; the row already has the SAN as visible text.
- **Mobile parity rule** — `OpeningFindingCard` has separate mobile (`flex flex-col gap-2 sm:hidden`) and desktop (`hidden sm:flex`) branches sharing the same outer card div. The watermark is an absolutely-positioned child of the outer div, so it covers both layouts automatically. *Verify this in the plan.* The Move Explorer icon is the deliberate exception (D-07 desktop-only).
- **No magic numbers** — the watermark size (60–80px) and the inline icon size (`h-3.5 w-3.5` or similar) must be named constants if they appear in TS/TSX style props. Tailwind utility class strings are fine as-is.
- **Type safety** — prefer `Set<string>`, not `Set<unknown>`; explicit return type `string` on the key derivation function; `'white' | 'black'` not bare `string` for the side parameter (use the existing `Color` type from `@/types/api`).
- **Comment bug fixes** — N/A for this phase (no bug fixes), but if the curation script reveals a quirk in chess.js PGN parsing (e.g. study-comment handling), document it inline in the script.
- **Frontend-only** — no `app/` files touched; no Pydantic schemas changed; no DB migrations.

## Standard Stack

### Core (already in repo)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chess.js | ^1.4.0 | Parse `cEDAMVBB.pgn` in the curation script; produce `board.fen()` for each chapter's defining position. | Already used in `MoveExplorer.tsx` and `frontend/src/lib/zobrist.ts`. No new dependency. [VERIFIED: frontend/package.json:25] |
| vite | ^7.3.1 | SVG asset pipeline — `import troll from '@/assets/troll-face.svg'` resolves to a URL string. | Default behavior; the project does not install `vite-plugin-svgr`. [VERIFIED: frontend/package.json devDependencies + vite.config.ts] |
| vitest | ^4.1.1 | Unit + component tests. | Already the test framework; existing `frontend/src/lib/openingInsights.test.ts` and `frontend/src/components/insights/OpeningFindingCard.test.tsx` are the closest analogs. [VERIFIED: frontend/package.json:62] |
| @testing-library/react | ^16.3.2 | Component tests for the watermark + icon rendering. | Used throughout the existing component tests. [VERIFIED: frontend/package.json:51] |

### Supporting (already in repo)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsdom | ^25.0.1 | DOM environment for component tests (set via `// @vitest-environment jsdom` comment, see `OpeningFindingCard.test.tsx:1`). | Required for any test that mounts a React tree. |
| tsx (or `node --import` shim) | not installed | Running the TS curation script offline. | See "Curation Script Mechanics" below — recommendation is `npx tsx scripts/curate_troll_openings.ts` to avoid adding a permanent devDependency. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `<img src={troll}>` | `vite-plugin-svgr` + `import { ReactComponent as Troll } from '@/assets/troll-face.svg'` | Pulls a new devDependency for one SVG. The SVG is 26 KB — embedding as a React component bloats the JS bundle while `<img>` lets the asset be cached as a URL. **Recommend `<img>`.** [VERIFIED: package.json has no svgr; project uses raw `<img>` already in tests for `react.svg`] |
| `Set<string>` literals exported from a TS data module | Generated JSON loaded at runtime | TS module is tree-shakable, type-safe, and lets the curation script emit a typed file. JSON forces a runtime fetch or a `import data from './trollOpenings.json' assert { type: 'json' }` ceremony. **Recommend TS module.** |
| Side-only Zobrist hash (the rejected backend approach) | The existing `frontend/src/lib/zobrist.ts` *whiteHash/blackHash* helpers, computed in-browser | Zobrist hashes are 64-bit BigInt — `Set<bigint>` works but is overkill for this scale (~10–30 entries). FEN string keys are easier to debug and emit. **Recommend FEN string keys per D-08.** |

**Installation:** None — all required libraries are already present. The curation script can use `tsx` via `npx tsx <path>` without adding it to `package.json`.

**Version verification:** Skipped (no new packages added). `chess.js@1.4.0` was verified against `frontend/package.json:25`.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OFFLINE — runs once during phase execution, output committed                │
│                                                                             │
│  https://lichess.org/study/cEDAMVBB.pgn                                     │
│            │                                                                │
│            │ (curl/fetch — cache locally during dev)                        │
│            ▼                                                                │
│   scripts/curate_troll_openings.ts                                          │
│   (or frontend/scripts/curate_troll_openings.ts)                            │
│            │                                                                │
│            │ chess.js: load PGN → iterate chapters → board.fen()            │
│            │ stripOpponentPieces(boardFen, trollSide) → string key          │
│            ▼                                                                │
│   stdout: candidate list (name, color, key, defining moves)                 │
│            │                                                                │
│            │ HUMAN PRUNING STEP — surface to user, await approval per D-01  │
│            ▼                                                                │
│   frontend/src/data/trollOpenings.ts (committed)                            │
│   ── exports: WHITE_TROLL_KEYS: Set<string>, BLACK_TROLL_KEYS: Set<string>  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ static import at build time
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RUNTIME — browser                                                           │
│                                                                             │
│  OpeningInsightsBlock                MoveExplorer                           │
│        │                                  │                                 │
│        │ finding.entry_fen,               │ entry.result_fen,               │
│        │ finding.color                    │ side-just-moved (from parent)   │
│        ▼                                  ▼                                 │
│  isTrollPosition(fen, side) → boolean  (single shared helper)              │
│        │                                  │                                 │
│   ┌────┴─────┐                       ┌────┴─────┐                          │
│   │  true    │  false                │   true   │  false                   │
│   ▼          ▼                       ▼          ▼                          │
│  render     skip                    render     skip                        │
│  watermark  (no DOM)                inline     (no DOM)                    │
│  <img>                              icon                                   │
│  (mobile +                          <img>                                  │
│   desktop)                          (hidden sm:                            │
│                                      inline-flex)                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
frontend/
├── scripts/                              # NEW directory — Node/TS build-time scripts
│   └── curate_troll_openings.ts          # NEW — runs offline, emits the data file
├── src/
│   ├── assets/
│   │   └── troll-face.svg                # NEW (moved from temp/Troll-Face.svg)
│   ├── data/                             # NEW directory if absent — static curated data
│   │   └── trollOpenings.ts              # NEW — exports WHITE_TROLL_KEYS, BLACK_TROLL_KEYS
│   ├── lib/
│   │   ├── trollOpenings.ts              # NEW — stripOpponentPieces(), isTrollPosition()
│   │   └── trollOpenings.test.ts         # NEW — golden FEN unit tests
│   ├── components/
│   │   ├── insights/
│   │   │   ├── OpeningFindingCard.tsx    # MODIFIED — add bottom-right watermark
│   │   │   └── OpeningFindingCard.test.tsx  # MODIFIED — assertions for watermark
│   │   └── move-explorer/
│   │       ├── MoveExplorer.tsx          # MODIFIED — add inline icon to MoveRow
│   │       └── __tests__/
│   │           └── MoveExplorer.test.tsx # MODIFIED — assertions for inline icon
│   └── lib/theme.ts                      # MODIFIED — export TROLL_WATERMARK_OPACITY constant
└── temp/Troll-Face.svg                   # DELETED in same commit as the move
```

**Note on `frontend/scripts/`:** This directory does not exist yet. The repo has top-level `scripts/` (Python) — putting a TS curation script there would be inconsistent. Per CONTEXT.md "Integration Points": *"one new curation script under `frontend/scripts/` (or `scripts/`, matching repo convention for build-time codegen)"*. **Recommend `frontend/scripts/`** because (a) the script imports chess.js from `frontend/node_modules`, and (b) it emits a TS file rooted at `frontend/src/data/`. The script is run ad-hoc (`npx tsx frontend/scripts/curate_troll_openings.ts`); it does not need to be a `package.json` script entry.

### Pattern 1: Side-only FEN Key Derivation (the heart of this phase)

**What:** Strip opponent pieces from the FEN piece-placement field and re-canonicalize empty-square runs.

**Algorithm (executor-ready pseudocode):**

```typescript
// Source: derived from FEN spec — piece-placement field is 8 ranks separated by '/'.
// Each rank is a sequence of piece chars (PNBRQK uppercase = white, pnbrqk lowercase = black)
// and digits 1-8 representing consecutive empty squares.

import type { Color } from '@/types/api';

/**
 * Derive a deterministic user-side-only key from a board FEN.
 *
 * Accepts either a full FEN ("rnbq.../w KQkq -") or a piece-placement-only FEN
 * ("rnbq..."). Strips opponent pieces, re-canonicalizes empty-square runs, and
 * returns the rejoined 8-rank string. Stable across opponent variations.
 *
 * Edge cases handled:
 *   - Full FEN with side-to-move/castling/etc — only the first space-separated token is used.
 *   - Empty rank ("8") — passes through unchanged.
 *   - All-empty after stripping — produces "8".
 *   - Kings-only — produces "...K..." or "...k..." with surrounding empties.
 *   - Invalid input — caller's responsibility (defensive: throw if rank count != 8).
 */
export function deriveUserSideKey(fen: string, side: Color): string {
  const placement = fen.split(' ', 1)[0]!;                         // first token
  const ranks = placement.split('/');
  if (ranks.length !== 8) {
    throw new Error(`Invalid FEN piece-placement: expected 8 ranks, got ${ranks.length}`);
  }
  const opponentRegex = side === 'white' ? /[a-z]/ : /[A-Z]/;     // strip the OTHER side
  return ranks.map(rank => canonicalizeRank(rank, opponentRegex)).join('/');
}

function canonicalizeRank(rank: string, stripPattern: RegExp): string {
  // Walk the rank char-by-char, accumulating an empty-square run when we see
  // a digit OR a piece-char that matches stripPattern. Flush the run as a
  // single digit when we hit a kept piece-char or end-of-rank.
  let out = '';
  let emptyRun = 0;
  for (const ch of rank) {
    if (/\d/.test(ch)) {
      emptyRun += parseInt(ch, 10);
    } else if (stripPattern.test(ch)) {
      emptyRun += 1;                                                // stripped piece becomes empty
    } else {
      if (emptyRun > 0) { out += String(emptyRun); emptyRun = 0; }
      out += ch;
    }
  }
  if (emptyRun > 0) out += String(emptyRun);
  return out;
}
```

**Worked examples (use these as golden test inputs):**

| Input FEN (board) | Side | Output key | Notes |
|-------------------|------|------------|-------|
| `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR` (start) | white | `8/8/8/8/8/8/PPPPPPPP/RNBQKBNR` | All black ranks collapse to `8`. |
| `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR` (start) | black | `rnbqkbnr/pppppppp/8/8/8/8/8/8` | All white ranks collapse to `8`. |
| `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR` (after 1.e4 e5) | white | `8/8/8/8/4P3/8/PPPP1PPP/RNBQKBNR` | Black's e5 stripped → rank 5 becomes `8`. |
| `rnbqkbnr/pppppppp/8/8/8/8/PPPPKPPP/RNBQ1BNR` (Bongcloud after 2.Ke2 — illustrative) | white | `8/8/8/8/8/8/PPPPKPPP/RNBQ1BNR` | The defining "King on e2" position. |
| `8/8/8/8/8/8/8/4K2k` (kings-only endgame) | white | `8/8/8/8/8/8/8/4K3` | Black king stripped → 4 empties + K + 3 empties = `4K3`. |
| `8/8/8/8/8/8/8/8` (empty board) | white | `8/8/8/8/8/8/8/8` | Edge case: all-empty input passes through. |

**[VERIFIED]** by inspecting the input semantics: `OpeningInsightFinding.entry_fen` is set in `app/services/opening_insights_service.py:441` via `_replay_san_sequence(...)` which produces a full FEN. `NextMoveEntry.result_fen` is set in `app/services/openings_service.py:350` via `board.board_fen()` — piece-placement-only. The helper supports both.

### Pattern 2: Side That Just Moved (Move Explorer)

**What:** D-10 says the Move Explorer matcher uses "the side that just moved" — i.e., the side that played the candidate move. That is the OPPOSITE of the side-to-move encoded in `entry.result_fen`'s side-to-move field.

**But:** `result_fen` from the backend is **board FEN only** (piece-placement only — see `app/services/openings_service.py:350` and `app/schemas/openings.py:197` `# board FEN of resulting position (piece placement only)`). It does NOT contain a side-to-move field. So we cannot derive the side-just-moved from `result_fen` alone.

**Resolution:** Derive the side-just-moved from the **parent** position. `MoveExplorer` already receives a `position: string` prop (a full FEN — `chess.position` from the parent — see `MoveExplorer.tsx:26,69`). The side-to-move in that parent FEN is the side that's about to move, i.e., **the side that plays the candidate move**, which is **the side just moved on `result_fen`**.

```typescript
// Inside MoveExplorer, derived once from the `position` prop:
const sideToMoveAtParent = position.split(' ')[1] === 'w' ? 'white' : 'black';
// Pass sideToMoveAtParent down to each MoveRow; that's the troll-matching side.
```

**[VERIFIED]** by reading `MoveExplorer.tsx:69` — `const chess = new Chess(position);` confirms `position` is a full FEN parseable by chess.js (chess.js requires the full FEN with side-to-move + castling).

### Pattern 3: Watermark as Sibling Element (D-04)

**Recommended JSX shape for `OpeningFindingCard`:**

```tsx
import trollFaceUrl from '@/assets/troll-face.svg';
import { TROLL_WATERMARK_OPACITY } from '@/lib/theme';
import { isTrollPosition } from '@/lib/trollOpenings';

// Inside OpeningFindingCard, after computing cardStyle:
const showTroll = isTrollPosition(finding.entry_fen, finding.color);

return (
  <div
    data-testid={`opening-finding-card-${idx}`}
    className="block relative border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3"
    style={cardStyle}
  >
    {/* ... existing mobile + desktop branches ... */}

    {showTroll && (
      <img
        src={trollFaceUrl}
        alt=""                                              {/* decorative */}
        aria-hidden="true"
        data-testid={`opening-finding-card-${idx}-troll-watermark`}
        className="absolute bottom-2 right-2 h-16 w-16 sm:h-20 sm:w-20 pointer-events-none select-none"
        style={{ opacity: TROLL_WATERMARK_OPACITY }}        {/* 0.30 from theme.ts */}
      />
    )}
  </div>
);
```

Key points:
- `relative` added to outer card div (currently absent); the existing card has no positioned children, so adding it is a no-op for current layout.
- One element covers both mobile and desktop branches because both branches share the outer wrapper.
- `pointer-events-none` per D-04 — the `Moves` / `Games` link buttons stay clickable.
- `select-none` prevents accidental SVG selection drag on desktop.
- Tailwind sizing utilities are stable named values; the **opacity is the only theme-token-style constant** so it goes in `theme.ts`.

### Pattern 4: Inline Icon in MoveRow (D-06, D-07)

```tsx
// Inside MoveExplorer.tsx, parent computes once:
const sideToMoveAtParent: Color = position.split(' ')[1] === 'w' ? 'white' : 'black';

// Pass to MoveRow:
<MoveRow ... sideJustMoved={sideToMoveAtParent} />

// Inside MoveRow:
const showTroll = isTrollPosition(entry.result_fen, sideJustMoved);

return (
  <tr ...>
    <td className="py-1 text-sm text-foreground font-normal truncate">
      <span className="inline-flex items-center gap-1">
        <span>{entry.move_san}</span>
        {showTroll && (
          <img
            src={trollFaceUrl}
            alt=""
            aria-hidden="true"
            data-testid={`move-list-row-${entry.move_san}-troll-icon`}
            className="hidden sm:inline-block h-3.5 w-3.5"     {/* desktop only per D-07 */}
          />
        )}
      </span>
    </td>
    {/* ... rest of row ... */}
  </tr>
);
```

### Anti-Patterns to Avoid

- **Computing `isTrollPosition` inside a `useMemo` or hook.** It's a constant-time `Set.has(string)` lookup after a tiny string transform. Memoizing adds React-render bookkeeping for a function that runs in <1µs. Just call it inline.
- **Putting the SVG asset path in `theme.ts`.** Asset URLs aren't theme tokens; let the import sit at the call site.
- **Bundling the SVG as a React component via `vite-plugin-svgr`.** Pulls a devDependency for one asset; raw `<img>` lets browsers cache the URL. Confirmed by inspecting `vite.config.ts` and `package.json` — no SVGR plugin is installed.
- **Embedding the curation step as a `package.json` script in `frontend/`.** It runs once per phase; `npx tsx frontend/scripts/curate_troll_openings.ts` is sufficient. A perma-script slot would let stale runs trample the committed data.
- **Auto-committing `frontend/src/data/trollOpenings.ts` from the curation script.** The script must emit candidates to stdout (or a temp file) for human review FIRST per D-01 and D-09. Only after user approval does the executor write the final file.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Iterating chapters in a multi-game PGN | A custom split-on-`[Event ` parser | `new Chess(); chess.loadPgn(chunk)` per chapter, OR chess.js's PGN-aware parser | chess.js handles PGN comments, NAGs, RAVs, headers, escape sequences correctly. The Lichess study PGN contains study-specific NAGs that a regex split would mangle. [CITED: chess.js README — `loadPgn()` is the canonical entry point] |
| Computing a hash to dedupe positions | A custom string hash | `string` itself as the `Set<string>` key | The output of `deriveUserSideKey` is already canonical and ~70 chars max. `Set<string>` is exactly the right primitive. |
| FEN parsing | Hand-written FEN tokenizer | `new Chess(fen).board()` or `chess.fen()` | But for the **stripping step itself** we DO want a hand-written rank walker — chess.js's API doesn't expose "remove all pieces of color X and re-canonicalize" cheaply. The 20-line `canonicalizeRank` helper is purpose-built and unit-testable; that's not "hand-rolling," that's the feature. |
| Asset bundling | Inlining SVG as a base64 data URI | Vite's default `import` → URL string | Vite handles asset hashing, caching, prerender, and PWA caching automatically. |

**Key insight:** The "don't hand-roll" rule does NOT apply to the side-only key derivation — it's the new feature, not a problem with an existing solution. The curation script is also new but its scope is narrow (one PGN, one extraction), so writing it from scratch is correct.

## Runtime State Inventory

This is a greenfield-feature phase, not a rename/refactor/migration. Section omitted.

## Common Pitfalls

### Pitfall 1: The Lichess study PGN uses `;` line comments and `{}` block comments

**What goes wrong:** Hand-rolled PGN parsing breaks on study-specific annotations. Some chapters in `cEDAMVBB` have analysis sub-variations (RAVs in parentheses) that a naive split-on-double-newline would treat as separate games.

**Why it happens:** Lichess studies export each chapter as a separate `[Event "..."]` block, but with embedded annotations.

**How to avoid:** Use `chess.js`'s `loadPgn()` per chapter chunk. Split on the empty-line-after-empty-line pattern that PGN uses to separate games (chess.js documentation calls this the "separator" and handles it natively when given the full multi-game string via `loadPgn`).

**Warning signs:** Chapter count from the curation script doesn't match Lichess's chapter list shown on the study page.

### Pitfall 2: "Defining position" is ambiguous — last mainline ply vs. characteristic ply

**What goes wrong:** Some study chapters have long mainlines (e.g. a 15-move Bongcloud demo). Taking the LAST mainline position would key on a deep middlegame position the user almost never reaches by transposition. Taking the FIRST move position (e.g. `1.e4 e5 2.Ke2` for the Bongcloud) keys on the characteristic moment the troll opening is identified.

**How to avoid:** Per CONTEXT.md "Defining position only, not every position along the line" and the design-note guidance "established once the characteristic move(s) are on the board": **take the position after the LAST distinct move number on the mainline that defines the opening's identity, NOT the deep mainline tail.** The most pragmatic heuristic is "after the last move in the chapter title" — Lichess study chapters are named like `Bongcloud Attack: 2.Ke2`. The script should expose the move count it picked per chapter so the human pruning step can override it.

**Recommendation:** Make the script emit **all mainline positions** for each chapter to a dev-only file, then have the human (you) pick one per opening during the curation review. The committed data file gets ONE key per opening per color. This pushes the ambiguity into the human review step, which is the right place per D-01.

**Warning signs:** Watermark fires on positions that are NOT the canonical Bongcloud (false positive), or fails to fire when the user reaches the canonical Bongcloud move (false negative — the curated key was a deeper position).

### Pitfall 3: `result_fen` is board FEN, but the helper accepts both

**What goes wrong:** The helper signature `deriveUserSideKey(fen, side)` could be called with either a full FEN (`finding.entry_fen`) or a board-only FEN (`entry.result_fen`). If the helper assumes one form, the other path silently produces wrong keys.

**Why it happens:** The two consumers pass different shapes — confirmed by `app/services/openings_service.py:350` (`board.board_fen()`) vs. `app/services/opening_insights_service.py:441` (`_replay_san_sequence` produces a full FEN).

**How to avoid:** The helper does `fen.split(' ', 1)[0]` first to take only the placement field. Both inputs work transparently. **Add a unit test for each shape** to lock this in.

**Warning signs:** Insights watermark works but Move Explorer icon doesn't fire (or vice versa) on positions you know are in the curated set.

### Pitfall 4: Watermark interaction with `UNRELIABLE_OPACITY` (Phase 76 dimming)

**What goes wrong:** `OpeningFindingCard` already applies `opacity: UNRELIABLE_OPACITY` (~0.5) on the outer div when the finding is unreliable (n_games < 10 or confidence === 'low'). A watermark with its own `opacity: 0.30` *inside* a 0.5-opacity parent multiplies to 0.15 — too faint to see.

**How to avoid:** Two options:
1. Set the watermark opacity to compensate (e.g. 0.60 on its own would render 0.30 inside a 0.5 parent — but only on unreliable cards, breaking the "30% opacity is locked" decision).
2. Keep the locked 30% and accept the multiplied effect on dimmed cards. The watermark is decorative; users seeing a faint troll on a dimmed card is acceptable since the card itself is signalling "low data, take with salt."

**Recommend option 2.** Document the interaction in a comment so future readers don't think it's a bug. If user feedback flags the dimmed-watermark as a bug, revisit by hoisting the watermark out of the opacity-affected wrapper (sibling div with its own positioning context).

**Warning signs:** Visual review on a low-confidence card (e.g. n_games = 8) shows a barely-visible watermark.

### Pitfall 5: knip will fail CI if `WHITE_TROLL_KEYS` xor `BLACK_TROLL_KEYS` is unused

**What goes wrong:** If the curated set has only black troll openings (Bongcloud is white-only; some openings are color-asymmetric), one of the two exports might be empty. If `BLACK_TROLL_KEYS` is empty AND nothing imports it, knip flags it as a dead export.

**How to avoid:** The shared `isTrollPosition(fen, side)` helper imports BOTH sets — even if one is empty, the import keeps it alive. Make sure the helper is the ONLY caller of `WHITE_TROLL_KEYS` and `BLACK_TROLL_KEYS`; everywhere else uses `isTrollPosition()`.

**Warning signs:** CI fails with `knip` reporting unused exports.

### Pitfall 6: chess.js `loadPgn` returns void in newer versions; check before invoking

**What goes wrong:** chess.js 1.x changed `loadPgn` from returning a boolean to throwing on parse failure. Hand-coded retry loops that check the return value will silently skip every chapter.

**How to avoid:** Wrap `chess.loadPgn(chapter)` in try/catch; log + skip on failure. The script should report a chapter count to confirm none were silently dropped.

**[CITED]** chess.js@1.x changelog — `loadPgn` raises on invalid PGN rather than returning false.

### Pitfall 7: The `position` prop on `MoveExplorer` may not always be a FULL FEN

**What goes wrong:** If a future refactor passes `chess.fen()` vs `board.board_fen()` to `position`, the `split(' ')[1]` side-derivation breaks silently — `[1]` is `undefined`, the comparison `=== 'w'` is `false`, so every position is treated as black-side.

**How to avoid:** `noUncheckedIndexedAccess` already forces narrowing on `position.split(' ')[1]`. The plan's implementation should explicitly handle the undefined case with a fallback or throw:

```typescript
const tokens = position.split(' ');
const sideToken = tokens[1];
if (sideToken !== 'w' && sideToken !== 'b') {
  throw new Error(`MoveExplorer: position must be a full FEN with side-to-move, got: ${position}`);
}
const sideToMoveAtParent: Color = sideToken === 'w' ? 'white' : 'black';
```

**Warning signs:** Move Explorer icon never fires (always derives `'black'`) or fires inverted (the Bongcloud icon shows on Grob positions).

## Code Examples

### Curation Script Skeleton (Node/TS)

```typescript
// Source: hand-authored from chess.js docs + project conventions
// Path: frontend/scripts/curate_troll_openings.ts
// Run: npx tsx frontend/scripts/curate_troll_openings.ts > /tmp/troll-candidates.txt

import { Chess } from 'chess.js';
import { readFileSync, existsSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const STUDY_URL = 'https://lichess.org/study/cEDAMVBB.pgn';
const CACHE_PATH = resolve(import.meta.dirname, '.cache', 'cEDAMVBB.pgn');

async function loadPgn(): Promise<string> {
  if (existsSync(CACHE_PATH)) return readFileSync(CACHE_PATH, 'utf-8');
  const res = await fetch(STUDY_URL);
  if (!res.ok) throw new Error(`Lichess fetch failed: ${res.status}`);
  const text = await res.text();
  writeFileSync(CACHE_PATH, text);
  return text;
}

function deriveUserSideKey(fen: string, side: 'white' | 'black'): string {
  // ... per Pattern 1 above ...
  const placement = fen.split(' ', 1)[0]!;
  const ranks = placement.split('/');
  if (ranks.length !== 8) throw new Error(`Invalid FEN: ${placement}`);
  const stripPattern = side === 'white' ? /[a-z]/ : /[A-Z]/;
  return ranks.map(rank => canonicalizeRank(rank, stripPattern)).join('/');
}

function canonicalizeRank(rank: string, stripPattern: RegExp): string {
  let out = '';
  let emptyRun = 0;
  for (const ch of rank) {
    if (/\d/.test(ch)) emptyRun += parseInt(ch, 10);
    else if (stripPattern.test(ch)) emptyRun += 1;
    else { if (emptyRun > 0) { out += String(emptyRun); emptyRun = 0; } out += ch; }
  }
  if (emptyRun > 0) out += String(emptyRun);
  return out;
}

interface Candidate {
  chapterTitle: string;
  trollSide: 'white' | 'black';
  pgnMoves: string;
  finalKey: string;
}

async function main(): Promise<void> {
  const pgnText = await loadPgn();
  // chess.js's loadPgn handles multi-game PGNs natively as of 1.x.
  // Split on the chapter boundary marker, then loadPgn per chapter to extract headers.
  const chapters = pgnText.split(/\n\n(?=\[Event )/g).filter(c => c.trim().length > 0);

  const candidates: Candidate[] = [];
  for (const chapterText of chapters) {
    const chess = new Chess();
    try {
      chess.loadPgn(chapterText);
    } catch (err) {
      console.warn(`Skipping unparseable chapter: ${(err as Error).message}`);
      continue;
    }
    const headers = chess.header();
    const title = headers.Event ?? '<untitled>';

    // Heuristic: troll side is whichever side plays the characteristic move.
    // For curation, emit BOTH sides — the human review step picks the right one.
    // Use the position AT THE END of the mainline as the candidate key; if it's
    // too deep, the human review step picks an earlier ply via the SAN log
    // emitted alongside.
    const finalFen = chess.fen();
    const sanHistory = chess.history();

    for (const side of ['white', 'black'] as const) {
      candidates.push({
        chapterTitle: title,
        trollSide: side,
        pgnMoves: sanHistory.join(' '),
        finalKey: deriveUserSideKey(finalFen, side),
      });
    }
  }

  // Emit human-readable candidate list — DO NOT auto-write the data file.
  console.log('=== TROLL OPENING CANDIDATES (review and prune per D-01) ===');
  for (const c of candidates) {
    console.log(`[${c.trollSide}] ${c.chapterTitle}`);
    console.log(`  moves: ${c.pgnMoves}`);
    console.log(`  key:   ${c.finalKey}`);
    console.log('');
  }
  console.log(`Total candidates: ${candidates.length}. Hand-prune to strict Bongcloud-tier set per D-01 before committing.`);
}

main().catch(err => { console.error(err); process.exit(1); });
```

**Caveat:** The "use the final mainline position" heuristic is the simplest one and produces deep keys. If hand-pruning shows that's wrong for the canonical openings (Bongcloud after `1.e4 e5 2.Ke2` is the right key, not `1.e4 e5 2.Ke2 ...20 plies later`), enhance the script to emit ALL mainline positions per chapter so the human can pick a ply. **Recommend the executor add an iteration through `chess.history({ verbose: true })` and emit one candidate per ply, leaving the pruning to the human.** This keeps the script simple but gives the reviewer full visibility.

### Output Data Module (committed after pruning)

```typescript
// Source: emitted by frontend/scripts/curate_troll_openings.ts after human pruning.
// Path: frontend/src/data/trollOpenings.ts
// REGENERATE WITH: npx tsx frontend/scripts/curate_troll_openings.ts (then hand-prune).

/**
 * Curated troll-opening positions, keyed by user-side-only FEN piece-placement.
 * Generated 2026-04-28 from lichess.org/study/cEDAMVBB.pgn, hand-pruned to
 * strict Bongcloud-tier per Phase 77 D-01.
 */

export const WHITE_TROLL_KEYS: ReadonlySet<string> = new Set([
  // Bongcloud Attack — after 1.e4 e5 2.Ke2
  '8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR',
  // Grob — after 1.g4
  // ... entries hand-pruned ...
]);

export const BLACK_TROLL_KEYS: ReadonlySet<string> = new Set([
  // Borg (Grob reversed) — after 1.e4 g5
  // ... entries hand-pruned ...
]);
```

`ReadonlySet<string>` prevents accidental mutation; bundlers tree-shake unused entries fine.

### Shared Helper Module

```typescript
// Path: frontend/src/lib/trollOpenings.ts
import type { Color } from '@/types/api';
import { WHITE_TROLL_KEYS, BLACK_TROLL_KEYS } from '@/data/trollOpenings';

export function deriveUserSideKey(fen: string, side: Color): string {
  // ... per Pattern 1 ...
}

export function isTrollPosition(fen: string, side: Color): boolean {
  const key = deriveUserSideKey(fen, side);
  return side === 'white' ? WHITE_TROLL_KEYS.has(key) : BLACK_TROLL_KEYS.has(key);
}
```

Note: `deriveUserSideKey` is exported (not just internal) so the unit test can hit it directly. `isTrollPosition` is the only consumer in production code.

## State of the Art

No "old vs. new" applies to this phase — it's a greenfield easter egg. The relevant evolution is internal to the project:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Backend-computed `is_troll_opening: bool` on every finding payload (per design-note draft) | Frontend-only matching via FEN-derived keys | 2026-04-28 (CONTEXT.md D-08) | Drops a schema field, a TSV, a `frozenset[int]`, a Python curation script, and an API contract change. Phase scope shrinks ~50%. |

**Deprecated/outdated:**
- The `app/data/troll_openings.tsv` plan from `troll-openings-design.md` — superseded by frontend `trollOpenings.ts`.
- The `is_troll_opening` API field — explicitly out of scope per CONTEXT.md `<deferred>`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Lichess study `cEDAMVBB` PGN endpoint returns one `[Event "..."]` block per chapter, parseable by chess.js's `loadPgn` per chunk. | Curation script | If the format differs, the script must be adjusted to a different parsing strategy. Low-risk: easy to fix during script execution. |
| A2 | chess.js@1.4.0's `loadPgn` throws on invalid PGN rather than returning `false`. | Pitfall 6 | If it returns false silently, chapter count check still surfaces the issue. Defensive try/catch covers both cases. |
| A3 | Lichess study chapters in `cEDAMVBB` follow the naming convention `<Opening Name>: <key move sequence>`. | Pattern 2 | If chapter titles are bare opening names without move sequences, the human pruning step still works — title is informational only, the key derivation is mechanical. |
| A4 | The 60–80px stamp size won't clip on mobile at 375px against the existing card layout. | Pattern 3 | If it clips, the executor adjusts the size during visual verification. Low-risk: tunable in CSS without re-architecture. |
| A5 | Vite's prerender plugin (`vite-prerender-plugin`) handles SVG `import` URLs correctly during the prerender pass. | Standard Stack | Prerender is build-time SSR; it shouldn't touch SVG asset URLs. Verify by running `npm run build` after the change. |

**This table has 5 entries.** All are low-risk and verifiable during execution. None require pre-execution user confirmation.

## Open Questions

1. **Should the curation script's "defining position" be the LAST mainline position or an earlier ply?**
   - What we know: Lichess chapters have variable-length mainlines. The Bongcloud is ~3 plies; some study chapters demo 15-ply lines.
   - What's unclear: Is there a single-ply heuristic that works across all chapters?
   - Recommendation: **Emit ALL mainline plies per chapter; let the human reviewer pick.** Push the ambiguity into the curation step where it belongs (D-01 already mandates human pruning).

2. **Where exactly should the inline icon sit in the Move Explorer row — before or after the SAN?**
   - What we know: D-06 says "next to the SAN"; CONTEXT.md `<decisions>` defers to Claude's discretion.
   - What's unclear: Right of SAN reads more like a badge; left of SAN reads more like a column marker.
   - Recommendation: **Right of SAN, inside the same `<td>`.** Matches the existing `TranspositionInfo` pattern (it sits inside `Games` cell at line 308 of `MoveExplorer.tsx`). Single `<span className="inline-flex items-center gap-1">` wrapping `{san}` + the icon.

3. **Should the curation script auto-write `frontend/src/data/trollOpenings.ts`, or stop at stdout?**
   - What we know: D-01 mandates human review before commit.
   - What's unclear: Could the script write a `.draft.ts` file that the human edits, or should it stay stdout-only?
   - Recommendation: **Stdout-only.** A `.draft.ts` file invites accidental commits of the unpruned candidate list. Stdout forces the executor to copy/paste into the final file as part of the review step.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Curation script + frontend tooling | ✓ | (whatever runs `npm run dev`) | — |
| `npx` | One-shot `tsx` invocation | ✓ | bundled with npm | — |
| `tsx` (via `npx`) | Run TS curation script without compiling | available via `npx` (no install needed) | latest | Compile via `tsc` then `node` |
| chess.js | PGN parsing in script + existing browser usage | ✓ | 1.4.0 (`frontend/package.json:25`) | — |
| Internet access (one-shot) | Fetch `cEDAMVBB.pgn` | assumed ✓ | — | Cache the PGN locally on first run; subsequent runs use cache |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None — all required tools are present.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | vitest@4.1.1 |
| Config file | None — vitest auto-discovers; `// @vitest-environment jsdom` directive at the top of component test files |
| Quick run command | `cd frontend && npm test -- --run frontend/src/lib/trollOpenings.test.ts` |
| Full suite command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map

Since no formal REQ-IDs exist for this phase, decisions are mapped to tests:

| Decision | Behavior to verify | Test Type | Automated Command | File Exists? |
|----------|-------------------|-----------|-------------------|-------------|
| D-08 (key derivation) | `deriveUserSideKey` produces the correct key for starting position, post-1.e4, kings-only, all-empty, full-FEN-with-side-token, board-only-FEN | unit | `cd frontend && npm test -- --run trollOpenings.test.ts` | ❌ Wave 0 |
| D-08 (set lookup) | `isTrollPosition` returns true when the FEN is in the set, false otherwise; calls the right side-set | unit | `cd frontend && npm test -- --run trollOpenings.test.ts` | ❌ Wave 0 |
| D-02, D-03, D-04, D-05 (card watermark renders) | Watermark `<img>` with correct testid, opacity, `pointer-events: none`, present in BOTH mobile and desktop layouts when finding is in troll set | component | `cd frontend && npm test -- --run OpeningFindingCard.test.tsx` | ✅ extends existing |
| D-05 (always-on regardless of severity) | Watermark renders for both `weakness` + `strength` classifications | component | same as above | ✅ extends existing |
| D-04 (links remain clickable) | `Moves` and `Games` buttons are still clickable when watermark is present (assert via `fireEvent.click` after rendering with troll-position finding) | component | same as above | ✅ extends existing |
| D-06 (Move Explorer icon renders for matching `result_fen`) | Icon `<img>` with correct testid present when `result_fen` matches; absent otherwise | component | `cd frontend && npm test -- --run MoveExplorer.test.tsx` | ✅ extends existing |
| D-07 (mobile suppression) | Icon has `hidden sm:inline-block` class; jsdom default viewport is desktop-width so icon renders in tests — assert class instead of visibility | component | same as above | ✅ extends existing |
| D-10 (correct side-just-moved derived from parent FEN) | When parent `position` ends in ` w `, white-side keys are checked for white-just-moved logic — i.e. the side-to-move at parent IS the side that plays the candidate | component | same as above | ✅ extends existing |

### Sampling Rate

- **Per task commit:** `cd frontend && npm test -- --run trollOpenings.test.ts` (≈1s, pure unit)
- **Per wave merge:** `cd frontend && npm test -- --run` + `cd frontend && npm run lint && npm run knip`
- **Phase gate:** Full frontend suite green + `cd frontend && npm run build` succeeds (catches asset import + tsc errors) + manual visual verification at desktop and mobile (375px) per D-03.

### Wave 0 Gaps

- [ ] `frontend/src/lib/trollOpenings.test.ts` — unit tests for `deriveUserSideKey` + `isTrollPosition` (covers D-08).
- [ ] `frontend/src/data/trollOpenings.ts` — emitted by curation script after human pruning. **This file's existence IS a phase deliverable, not test infrastructure** — but tests need at least one entry to assert positive matches, so the unit test should mock the data module via `vi.mock('@/data/trollOpenings', () => ({ WHITE_TROLL_KEYS: new Set([...]), BLACK_TROLL_KEYS: new Set([...]) }))` to keep the test self-contained.
- [ ] No new framework install needed.
- [ ] No new shared fixtures needed — existing `makeFinding` (in `OpeningFindingCard.test.tsx`) and `makeEntry` (in `MoveExplorer.test.tsx`) are reused.

### Manual Verification Checkpoints (cannot be automated)

- **Curation review:** After running the curation script, the executor MUST surface the candidate list to the user (per D-01) before committing `frontend/src/data/trollOpenings.ts`. This is a human-in-the-loop gate; flag in the plan as a hard checkpoint.
- **Mobile visual check at 375px:** Watermark doesn't clip the prose/links column; doesn't visually fight the severity border-left tint. Desktop visual check at typical viewport.
- **Move Explorer mobile check at 375px:** Inline icon is suppressed (per D-07); confirm via responsive devtools.

## Sources

### Primary (HIGH confidence)

- `frontend/package.json` — chess.js@1.4.0, vitest@4.1.1, @testing-library/react@16.3.2 verified.
- `frontend/vite.config.ts` — no SVGR plugin; default Vite SVG-as-URL behavior confirmed.
- `frontend/tsconfig.app.json` — `noUncheckedIndexedAccess: true` confirmed.
- `frontend/src/components/insights/OpeningFindingCard.tsx` — current structure read line-by-line.
- `frontend/src/components/move-explorer/MoveExplorer.tsx` — `position` prop is full FEN; `MoveRow` is the candidate-move table row.
- `frontend/src/types/insights.ts` — `OpeningInsightFinding.entry_fen` and `.color` confirmed.
- `frontend/src/types/api.ts` — `NextMoveEntry.result_fen` confirmed as `string` (with comment "board FEN (piece placement only)").
- `app/services/openings_service.py:350` — confirmed `result_fen = board.board_fen()` produces piece-placement only.
- `app/schemas/openings.py:197` — confirmed `result_fen: str    # board FEN of resulting position (piece placement only)`.
- `app/services/opening_insights_service.py:441` — confirmed `entry_fen` is full FEN from `_replay_san_sequence`.
- `frontend/src/components/insights/OpeningFindingCard.test.tsx` — existing test pattern (vi.mock Tooltip, jsdom env, `makeFinding` helper).
- `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` — existing test pattern (`makeEntry` helper).

### Secondary (MEDIUM confidence)

- chess.js README + 1.x changelog (referenced for `loadPgn` behavior). Not fetched live in this session — claim based on the version pinned in `package.json` and existing in-repo usage.

### Tertiary (LOW confidence)

- Lichess study URL `https://lichess.org/study/cEDAMVBB.pgn` is reachable and returns multi-chapter PGN. Not fetched in this session; assumed available (CONTEXT.md cites it directly).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library is already installed and verified against `package.json`.
- Architecture: HIGH — every consumer file was read line-by-line; data flow is fully traced.
- Pitfalls: HIGH for items #1–5, MEDIUM for #6 (chess.js loadPgn behavior version-dependent), HIGH for #7.
- Curation mechanics: MEDIUM — the script skeleton is plausible but the actual PGN structure of `cEDAMVBB` was not fetched and parsed in this session; the executor may need to adjust the chapter-split regex.
- Test framing: HIGH — existing test files in the repo provide direct templates.

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (30 days; the underlying tech stack is stable; chess.js / vitest / Vite are unlikely to ship breaking changes in that window).
