# Phase 173: Anchor ladder self-calibration (SEED-101) - Pattern Map

**Mapped:** 2026-07-15
**Files analyzed:** 8 (new) + 2 (modified)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `scripts/lib/calibration-game-loop.mjs` | service (game-loop engine) | event-driven (per-ply loop, terminal/adjudication) | `scripts/calibration-harness.mjs` (lines 351-524, `playGame` + helpers) | exact (extraction source) |
| `scripts/calibration-anchor-ladder.mjs` | controller/orchestrator (CLI script) | batch (probe→measure scheduling + TSV writes) | `scripts/calibration-harness.mjs` (whole file: CLI parsing, grid sweep, TSV emission, `--resume`) | exact |
| `scripts/lib/calibration-anchors.mjs` (modified, D-09) | config/utility | CRUD (lookup-table extension) | itself — extend `SF_SKILL_ELO` in place | exact (same file) |
| `scripts/lib/calibration-internal-scale.mjs` | config/utility (generated artifact, committed) | transform (Python fit output → JS-importable table) | `scripts/lib/calibration-anchors.mjs` (`SF_SKILL_ELO` export shape) | role-match |
| `scripts/calibration-anchor-fit.py` | service (offline stats/fit script) | batch/transform (TSV → fitted ratings + CI + residuals) | `scripts/backfill_eval.py` (argparse CLI skeleton, docstring runbook conventions) | role-match (CLI conventions only — math is novel, no Python analog) |
| `tests/scripts/test_calibration_anchor_fit.py` | test | request-response (pytest unit tests over pure functions) | `tests/scripts/test_backfill_eval.py` | role-match (structure/conventions; no DB fixtures needed here) |
| `scripts/lib/calibration-game-loop.check.mjs` | test (structural, synthesized fixture) | event-driven verification | `scripts/lib/calibration-pruning.check.mjs` | exact |
| `scripts/lib/calibration-anchor-schedule.check.mjs` | test (pure-logic, no engines) | transform verification | `scripts/lib/calibration-elo.check.mjs` | exact |
| `.planning/notes/<date>-anchor-ladder-self-calibration-findings.md` | doc | — | `.planning/notes/2026-07-13-bot-calibration-findings.md` | exact (explicitly named in D-12/CONTEXT.md) |

## Pattern Assignments

### `scripts/lib/calibration-game-loop.mjs` (service, event-driven)

**Analog:** `scripts/calibration-harness.mjs` lines 351-524 (`classifyTerminalResult`, `updateSustainState`, `adjudicatedResult`, `evaluateNonTerminalCutoffs`, `applyUciMove`, `playGame`)

**What to extract verbatim (rename `botIsWhite`-keyed params to color-keyed, per D-08):**

Terminal classification (lines 351-364) — keep exactly, just drop the `botIsWhite` bot-relative framing and return a plain `{ result: 'white_win'|'black_win'|'draw', reason }` or similar color-keyed shape, since anchor-vs-anchor games have no "bot":
```javascript
function classifyTerminalResult(chess, botIsWhite) {
  if (!chess.isGameOver()) return null;
  if (chess.isCheckmate()) {
    const checkmatedIsWhite = chess.turn() === 'w';
    const botWon = checkmatedIsWhite !== botIsWhite;
    return { result: botWon ? 'win' : 'loss', reason: 'checkmate' };
  }
  if (chess.isStalemate()) return { result: 'draw', reason: 'stalemate' };
  if (chess.isThreefoldRepetition()) return { result: 'draw', reason: 'threefold_repetition' };
  if (chess.isInsufficientMaterial()) return { result: 'draw', reason: 'insufficient_material' };
  if (chess.isDrawByFiftyMoves()) return { result: 'draw', reason: 'fifty_move_rule' };
  return { result: 'draw', reason: 'draw_other' };
}
```

Sustain-tracking + adjudication (lines 373-409) — reuse `ADJUDICATION_CP_THRESHOLD` (600), `ADJUDICATION_SUSTAIN_PLIES` (4), `PLY_CAP` (120) constants exactly, imported from `calibration-harness.mjs`'s existing exports (do not redefine — D-10 "keep harness conventions"):
```javascript
function updateSustainState(sustainState, whitePovCp) {
  const isBeyondThreshold = Math.abs(whitePovCp) >= ADJUDICATION_CP_THRESHOLD;
  if (!isBeyondThreshold) {
    sustainState.side = null;
    sustainState.count = 0;
    return null;
  }
  const favoredSide = whitePovCp > 0 ? 'w' : 'b';
  sustainState.count = sustainState.side === favoredSide ? sustainState.count + 1 : 1;
  sustainState.side = favoredSide;
  return sustainState.count >= ADJUDICATION_SUSTAIN_PLIES ? favoredSide : null;
}
```

Apply-move helper (lines 421-428) — reuse verbatim, no changes needed (already color-agnostic):
```javascript
function applyUciMove(chess, uci) {
  const squares = uciToSquares(uci);
  chess.move({
    from: squares?.from ?? uci.slice(0, 2),
    to: squares?.to ?? uci.slice(2, 4),
    promotion: uci.length > 4 ? uci[4] : undefined,
  });
}
```

**Core game-loop pattern** (lines 458-524, `playGame`) — the shape to generalize per the RESEARCH.md Pattern 1 example (`playTwoMoverGame({ Chess, pool, moverWhite, moverBlack, startFen, gameRng, onPly })`): keep the `pool.newGameAll()` TT-clear call, the `for(;;)` ply loop, the `classifyTerminalResult` → `evaluateNonTerminalCutoffs` → continue-loop order, and the `onPly` progress callback exactly as in the analog — only the move-dispatch line changes from `botToMove ? selectBotMove(...) : playAnchorMove(...)` to `whiteToMove ? moverWhite(fen, gameRng) : moverBlack(fen, gameRng)`.

`calibration-harness.mjs`'s own `playGame` becomes a thin wrapper calling into this shared loop (D-08 "no behavior change") — verify via the EXISTING `calibration-determinism.check.mjs` still passing unchanged after extraction.

**Error handling pattern:** none distinct — the analog has no try/catch around move application in the excerpt above (chess.js throws synchronously on an illegal move and that's allowed to propagate/crash the harness — this is a developer tool, not a service, consistent with the Security Domain section's "fail loudly" discipline).

---

### `scripts/calibration-anchor-ladder.mjs` (controller/orchestrator, batch)

**Analog:** `scripts/calibration-harness.mjs` (whole file)

**Imports pattern** (lines 65-86) — reuse the same import shape, but note this new script does NOT need `selectBotMove`/`botBudget`/bot-specific imports (D-08: no bot-cell concepts apply):
```javascript
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

import { createMaiaSession, resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { createStockfishPool, STOCKFISH_POOL_DEFAULT_SIZE } from './lib/stockfish-pool.mjs';
import { makeNodeProviders } from './lib/calibration-providers.mjs';
import { maiaArgmaxMove, SF_SKILL_ELO, anchorRatingFor, parseAnchorSpec } from './lib/calibration-anchors.mjs';
import { OPENING_BOOK, assertOpeningBookUciPrefixes } from './lib/calibration-openings.mjs';
import { playTwoMoverGame } from './lib/calibration-game-loop.mjs';

import { mulberry32 } from '@/lib/engine/botSampling';
```

**CLI parsing pattern (WR-02 discipline)** — reuse `requireFlagValue`/`parsePositiveIntFlag`/`parseIntList`/`parseFloatList` verbatim (lines 176-210) — either import them if exported, or copy exactly (they are small, pure, and unexported currently — D-08 discretion: export them from the harness or duplicate; prefer exporting to avoid drift):
```javascript
function requireFlagValue(value, key) {
  if (value === undefined || value.startsWith('--')) {
    throw new Error(`Missing value for --${key}`);
  }
  return value;
}
```

**Seeded PRNG + opening/color assignment pattern** (lines 132-139, `deriveGameSeed`) — reuse the SAME prime-multiplier derivation for per-game determinism:
```javascript
const SEED_GAME_INDEX_MULTIPLIER = 1_000_003;
function deriveGameSeed(seed, gameIndex) {
  return (seed + gameIndex * SEED_GAME_INDEX_MULTIPLIER) >>> 0;
}
```

**TSV writer + `--resume` pattern** (lines 611-942, `mainTsvColumns`/`mainTsvRowLine`/`openMainTsvWriter`/`loadPriorSweep`) — reuse the incremental-write-per-game discipline (WR-01: one line written the instant a game finishes) and the `--resume` re-validation-of-axes/budget guard shape. Per RESEARCH.md Pitfall 4, the resumable unit here is "one (anchor_a, anchor_b) pair's played games so far" reconstructed by replaying the probe→measure decision from the ledger — NOT a direct copy of `loadPriorSweep`'s fixed-`gridKeys` assumption; use it as a structural reference for the guard-and-fail-loud style, not a literal copy.

**Two-tier TSV pattern** (D-12 artifact 1) — mirror the existing `<run>.tsv` + `<run>-summary.tsv` sibling convention (`emitEloSummary`, lines 730-760) with `anchor-ladder-<ts>.tsv` (raw per-game) + `anchor-ladder-<ts>-pairs.tsv` (per-pair aggregate).

**D-13 labeling discipline:** every column header must read `internal_rating`-style, with a leading TSV comment/header note "internal scale — NOT human ELO" — no existing analog has this exact header note; add it fresh, following the `SEED-091 caveat carried into the summary TSV's metadata` precedent already established in `calibration-elo.mjs`'s docstring (lines 22-25).

---

### `scripts/lib/calibration-anchors.mjs` (D-09 modification)

**Analog:** itself — extend the existing `SF_SKILL_ELO` table in place (line 37):
```javascript
export const SF_SKILL_ELO = { 0: 1320, 3: 1750, 5: 2200 };
```
becomes (RESEARCH.md Assumption A1, proposed values 2600/2800):
```javascript
export const SF_SKILL_ELO = { 0: 1320, 3: 1750, 5: 2200, 8: 2600, 10: 2800 };
```
`parseAnchorSpec` (lines 304-320 in `calibration-harness.mjs`) already gates on `skillLevel in SF_SKILL_ELO` — no parser change needed, only the map extension, per D-09/Pitfall 3's "used ONLY for labels/ordering, the fit ignores them" discipline. Update the doc comment above the table (lines 29-36) to note sf8/sf10 are `[ASSUMED]` round continuations, not authoritative.

---

### `scripts/lib/calibration-internal-scale.mjs` (new, D-12 artifact 2)

**Analog:** `scripts/lib/calibration-anchors.mjs`'s `SF_SKILL_ELO` export shape (plain object keyed by anchor label) — RESEARCH.md Open Question 2 recommendation:
```javascript
/**
 * calibration-internal-scale.mjs — SEED-101 fitted internal rating scale
 * (generated by scripts/calibration-anchor-fit.py, committed as a static
 * artifact — D-12 artifact 2).
 *
 * INTERNAL SCALE — NOT human ELO (D-13). Scale fixed arbitrarily at
 * maia1500 = 1500; see .planning/notes/<date>-anchor-ladder-self-
 * calibration-findings.md for the compression verdict and methodology.
 */
export const INTERNAL_RATING = {
  maia700: 0,      // [GENERATED — placeholder until the fit runs]
  maia1100: 0,
  maia1500: 1500,
  maia1900: 0,
  maia2300: 0,
  sf0: 0,
  sf3: 0,
  sf5: 0,
  sf8: 0,
  sf10: 0,
};
```
Follows the same `export const <NAME> = { ... }` plain-object convention as `SF_SKILL_ELO` — this is the primary Node-consumable artifact for SEED-102's future harness work (RESEARCH.md Assumption A5). Emit a sibling JSON/TSV (`reports/data/anchor-ladder-internal-scale.json` or similar) from the same Python fit run for human/Python readability.

---

### `scripts/calibration-anchor-fit.py` (new, service/batch)

**Analog (CLI/docstring conventions only):** `scripts/backfill_eval.py` — no direct Python analog exists for the Bradley-Terry math itself (RESEARCH.md: "genuinely new... standard, well-understood statistics").

**Docstring/module-header convention** (backfill_eval.py lines 1-40) — mirror the runbook-style header: what the script does, usage examples, any external binary/dependency notes:
```python
"""calibration-anchor-fit.py — SEED-101 joint Bradley-Terry/Elo rating fit
over the anchor-ladder self-calibration game graph (Phase 173, D-05).

Reads the raw per-game TSV emitted by calibration-anchor-ladder.mjs, fits a
joint MLE rating for every anchor via Zermelo/MM iteration, fixes the scale
at maia1500 := 1500 (NOT human ELO — D-13), and emits bootstrap CIs +
per-pair residuals (D-06).

Usage:
    uv run python scripts/calibration-anchor-fit.py \\
        --input reports/data/anchor-ladder-<ts>.tsv \\
        --out-js scripts/lib/calibration-internal-scale.mjs \\
        --out-json reports/data/anchor-ladder-internal-scale.json
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
```

**CLI parsing pattern** (backfill_eval.py's `argparse` setup, not shown above but standard argparse with `--db`, `--limit`, `--dry-run` flags) — mirror with `--input`, `--out-js`, `--out-json`, `--bootstrap-samples`, `--seed` flags; fail loudly (`parser.error(...)`) on malformed input per the Security Domain section's V5 discipline.

**Core fit pattern (RESEARCH.md Pattern 2, Zermelo/MM iteration)** — use verbatim as given in RESEARCH.md:
```python
def fit_bradley_terry(win_counts: dict[tuple[str, str], float], anchors: list[str],
                       tol: float = 1e-9, max_iter: int = 10_000) -> dict[str, float]:
    """win_counts[(i, j)] = i's wins vs j (draws pre-split 0.5/0.5, D-05)."""
    strength = {a: 1.0 for a in anchors}
    total_wins = {a: sum(win_counts.get((a, b), 0.0) for b in anchors if b != a) for a in anchors}
    for _ in range(max_iter):
        new_strength = {}
        for i in anchors:
            denom = sum(
                (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0))
                / (strength[i] + strength[j])
                for j in anchors if j != i and (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0)) > 0
            )
            new_strength[i] = total_wins[i] / denom if denom > 0 else strength[i]
        max_rel_change = max(abs(new_strength[a] - strength[a]) / strength[a] for a in anchors)
        strength = new_strength
        if max_rel_change < tol:
            break
    return strength  # convert to 400*log10(pi) scale, then fix maia1500 := 1500
```

**TSV reading pattern (stdlib, RESEARCH.md Code Examples)**:
```python
def load_games(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        return [dict(zip(header, line.rstrip("\n").split("\t"))) for line in f if line.strip()]
```

**Connectivity guard pattern (D-04, defensive re-check on the Python side)**:
```python
def check_connectivity(pairs: set[tuple[str, str]], anchors: list[str]) -> None:
    adjacency: dict[str, set[str]] = {a: set() for a in anchors}
    for a, b in pairs:
        adjacency[a].add(b)
        adjacency[b].add(a)
    visited = {anchors[0]}
    frontier = [anchors[0]]
    while frontier:
        node = frontier.pop()
        for neighbor in adjacency[node] - visited:
            visited.add(neighbor)
            frontier.append(neighbor)
    if visited != set(anchors):
        raise RuntimeError(f"Anchor graph is disconnected — unreached: {sorted(set(anchors) - visited)}")
    cross_family_edges = [(a, b) for a, b in pairs if a.startswith("maia") != b.startswith("maia")]
    if len(cross_family_edges) < 2:
        raise RuntimeError(f"D-04 violated: only {len(cross_family_edges)} cross-family link(s), need >= 2")
```

**Degenerate-score guard (Pitfall 2, reuse the SAME clamp pattern as `calibration-elo.mjs`'s `SCORE_CLAMP_EPSILON_DIVISOR`)** — port the JS clamp idea into Python: `epsilon = 1 / (2 * games)`, applied to any lopsided pair's raw win-count before feeding it into Zermelo/MM, rather than inventing a new constant.

**Error handling:** fail-loud `RuntimeError`/`parser.error` on connectivity failure, non-convergence, or malformed TSV — this is a research tool; no Sentry capture needed (CLAUDE.md Sentry rules apply to `app/services`/`app/routers` web-app code only, not `scripts/`).

---

### `tests/scripts/test_calibration_anchor_fit.py` (new, test)

**Analog:** `tests/scripts/test_backfill_eval.py`

**Structure pattern** — mirror the module docstring summarizing test coverage (lines 1-13), `pytestmark = pytest.mark.asyncio` is NOT needed here (no DB/async — this is pure-function testing over the fit script), so the closest applicable convention is just the plain `import pytest` + helper-function-per-fixture-shape style:
```python
"""Anchor-ladder rating-fit tests (Phase 173, D-04/D-05/D-06).

Tests cover:
- fit convergence to known ground-truth strengths on a synthetic fixture
- scale fix: maia1500 pinned to exactly 1500
- draws folded 0.5/0.5 (not dropped, not double-counted)
- disconnected-graph / insufficient-cross-family-link guard (D-04) raises
- bootstrap CI produces a finite, sane-width interval
- per-pair residuals computed correctly, cross-family pairs flagged
"""

from __future__ import annotations

import pytest

from scripts.calibration_anchor_fit import (
    fit_bradley_terry,
    check_connectivity,
    bootstrap_ci,
    compute_residuals,
)
```
(Public API import pattern mirrors `from scripts.backfill_eval import run_backfill`, line 31 of the analog — expose the fit's callables as a public, directly-testable API rather than only a `main()` CLI entry point.)

**No DB fixtures needed** — unlike `test_backfill_eval.py`'s `_seed_game`/`_seed_span` SQLAlchemy helpers, this test file needs only small synthetic dicts (a hand-built `win_counts` graph with known ground truth) — simpler than the analog's DB-seeding style; use the analog only for the module-docstring-as-test-index convention and the "public API import, not CLI-only" pattern.

---

### `scripts/lib/calibration-game-loop.check.mjs` (new, structural test)

**Analog:** `scripts/lib/calibration-pruning.check.mjs`

**Structure pattern** — mirror the module header (explains this is a STRUCTURAL check against a SYNTHESIZED fixture, no real engines), the `node:assert/strict` usage, and the "run via" comment line:
```javascript
#!/usr/bin/env node
/**
 * calibration-game-loop.check.mjs — structural check that the extracted
 * two-mover game loop produces byte-identical terminal/adjudication
 * decisions to the pre-extraction bot-vs-anchor `playGame` (D-08 "no
 * behavior change"). No real engines — synthesized fixtures only.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-game-loop.check.mjs
 */
import assert from 'node:assert/strict';
import { playTwoMoverGame } from './calibration-game-loop.mjs';
```
Use `mkdtempSync`/`rmSync` in a `finally` block if any fixture needs on-disk state (lines 152-185 of the analog), though this check likely needs none (pure in-memory chess.js fixtures).

---

### `scripts/lib/calibration-anchor-schedule.check.mjs` (new, pure-logic test)

**Analog:** `scripts/lib/calibration-elo.check.mjs`

**Structure pattern** — mirror the canned-fixture assertion style (no engines/network), testing pure math/logic functions directly with `assert.ok`/`assert.equal` and a `console.log('PASS: ...')` + `process.exit(0)` tail:
```javascript
#!/usr/bin/env node
/**
 * calibration-anchor-schedule.check.mjs — pure-logic assertion for the
 * D-01/D-02/D-04 probe→measure gate + connectivity guard (Phase 173).
 * No engines/network — mirrors calibration-elo.check.mjs's canned-fixture
 * assertion style.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchor-schedule.check.mjs
 */
import assert from 'node:assert/strict';
import { scoreInInformativeBand, checkConnectivity } from './calibration-anchor-schedule.mjs';

const TOLERANCE = 1e-6;
// [example] a probe-predicted score of 0.5 must be judged informative (inside [0.2, 0.8])
assert.ok(scoreInInformativeBand(0.5), 'a 0.5 probe score must be inside the informative band');
assert.ok(!scoreInInformativeBand(0.95), 'a 0.95 probe score must be OUTSIDE the informative band (D-01 drop)');

console.log('PASS: calibration-anchor-schedule — probe/measure gate + connectivity guard correct on canned fixtures');
process.exit(0);
```

---

### `.planning/notes/<date>-anchor-ladder-self-calibration-findings.md` (doc, D-12 artifact 3)

**Analog:** `.planning/notes/2026-07-13-bot-calibration-findings.md` — explicitly named in D-12; read its section structure (Findings 1-4, numbered, each stating what was measured / what it means / what it unblocks) and mirror that shape exactly, closing 168-RESEARCH.md Open Question 2 as the final finding.

## Shared Patterns

### WR-02 CLI flag validation discipline
**Source:** `scripts/calibration-harness.mjs` lines 176-210 (`requireFlagValue`, `parsePositiveIntFlag`, `parseIntList`, `parseFloatList`)
**Apply to:** `scripts/calibration-anchor-ladder.mjs` (Node CLI) and `scripts/calibration-anchor-fit.py` (argparse `type=`/`parser.error` equivalents)
```javascript
function requireFlagValue(value, key) {
  if (value === undefined || value.startsWith('--')) {
    throw new Error(`Missing value for --${key}`);
  }
  return value;
}
```
Fail loudly on malformed input — never silently default (Security Domain V5).

### Seeded determinism (mulberry32 PRNG + prime-multiplier game-index derivation)
**Source:** `scripts/calibration-harness.mjs` lines 132-139 (`deriveGameSeed`), `@/lib/engine/botSampling` (`mulberry32`)
**Apply to:** `scripts/calibration-anchor-ladder.mjs` — every game's PRNG and opening/color assignment must derive the same way so `--resume` reproduces byte-identical results.

### UCI option reset before every `go` (shared-process discipline)
**Source:** `scripts/lib/calibration-anchors.mjs` lines 78-91 (`stockfishSkillMove`)
**Apply to:** any new anchor-vs-anchor move dispatch reusing `stockfishSkillMove`/`pool.skillMove` — since anchor-vs-anchor pits TWO Stockfish-skill anchors against each other on a shared pool, option state (Skill Level, MultiPV) must be reset immediately before every `go`, exactly as already required for bot-grading vs anchor-move sharing.

### Two-tier TSV (raw ledger + aggregate) durability
**Source:** `scripts/calibration-harness.mjs` `mainTsvColumns`/`mainTsvRowLine`/`emitEloSummary` (lines 611-760)
**Apply to:** `scripts/calibration-anchor-ladder.mjs` — write one line per completed game immediately (WR-01), derive the pair-aggregate summary from the ledger at the end (never held only in memory) so a killed run's completed games are never lost.

### "Internal scale — NOT human ELO" labeling (D-13)
**Source:** `scripts/lib/calibration-elo.mjs` docstring lines 22-25 (SEED-091 caveat precedent)
**Apply to:** every D-12 artifact (`calibration-anchor-ladder.mjs`'s TSV headers, `calibration-internal-scale.mjs`'s module docstring, `calibration-anchor-fit.py`'s output columns, the findings note) — carry the caveat verbatim into every field/column/header, not just one artifact.

## No Analog Found

None — every file has at least a role-match analog in the codebase (the Bradley-Terry math itself in `calibration-anchor-fit.py` has no direct Python precedent, but the CLI/docstring/testing CONVENTIONS it must follow do, and the math is fully specified in RESEARCH.md Pattern 2 with no ambiguity left for the planner).

## Metadata

**Analog search scope:** `scripts/`, `scripts/lib/`, `tests/scripts/`, `.planning/notes/`
**Files scanned:** `scripts/calibration-harness.mjs`, `scripts/lib/calibration-anchors.mjs`, `scripts/lib/calibration-elo.mjs`, `scripts/lib/calibration-elo.check.mjs`, `scripts/lib/calibration-pruning.check.mjs`, `scripts/backfill_eval.py`, `tests/scripts/test_backfill_eval.py`, `.planning/notes/2026-07-13-bot-calibration-findings.md` (referenced, not re-read — already summarized in CONTEXT.md/RESEARCH.md)
**Pattern extraction date:** 2026-07-15
