#!/usr/bin/env node
/**
 * calibration-providers.mjs — the Node `EngineProviders` adapter (Phase 168,
 * CAL-02) satisfying `frontend/src/lib/engine/types.ts`'s frozen contract:
 * `policy(fen, elo, side)` UCI-keyed, `grade(fen, candidateUcis)`
 * UCI-keyed/searchmoves-restricted/depth-carrying.
 *
 * `nodeGrade` mirrors `frontend/src/lib/engine/workerPool.ts`'s
 * `sendGo`/`handleLine` (UCI-keyed by `parsed.pv[0]`, `bound === 'exact'`
 * only, `depth` carried) — this is deliberately NOT
 * `gem-elo-calibration.mjs`'s `gradePosition` (SAN-keyed, all-legal-move
 * MultiPV, no `depth` field — wrong contract for `mctsSearch`, 168-RESEARCH.md
 * Pitfall 1).
 *
 * `nodePolicy` adapts `gem-elo-calibration.mjs`'s `maiaProbsForPosition`
 * (multi-rung batched) down to a single-rung, single-call shape, then
 * converts each `maskAndSoftmax` SAN key to UCI via `sanToUci` — mirrors
 * `frontend/src/lib/engine/maiaQueue.ts`'s SAN->UCI conversion step.
 *
 * The harness fixes `SearchBudget.concurrency = 1` (168-RESEARCH.md
 * Pitfall 3: one spawned Stockfish process, no worker pool), so only ONE
 * `policy()`/`grade()` call is ever in flight at a time — no async queue is
 * needed here, unlike the browser's `maiaQueue.ts`/`workerPool.ts`.
 *
 * Pitfall 2 (168-RESEARCH.md): a shared Stockfish process (or, since Plan 03,
 * ANY process drawn from the `stockfish-pool.mjs` pool) also serves the
 * anchor move-choosers (`calibration-anchors.mjs`) and adjudication.
 * `nodeGrade` resets the engine to full strength on EVERY call so a prior
 * weakened anchor `Skill Level` never leaks into the bot's own grading.
 *
 * `nodeGrade` and `evalPositionCp` both take the engine as their FIRST
 * argument (not a closed-over shared instance) so `stockfish-pool.mjs` can
 * route each call through a freshly-ACQUIRED pool engine (Plan 03, Task 1) —
 * `makeNodeProviders` closes over `pool.grade` directly, not a single engine.
 */
import { sanToUci } from '@/lib/sanToSquares';
import {
  encodeBoard,
  maskAndSoftmax,
  eloToInput,
  NUM_SQUARES,
  PLANES_PER_SQUARE,
  POLICY_VOCAB_SIZE,
} from '@/lib/maiaEncoding';
import { parseInfoLine } from '@/hooks/uciParser';
import { MATE_CP_EQUIVALENT } from '@/generated/flawThresholds';

// ─── Constants (mirror frontend/src/lib/engine/workerPool.ts lines 36, 39) ────

/** Grading search depth target — matches the app's own `EngineProviders.grade` depth (D-11). */
export const GRADING_TARGET_DEPTH = 14;

/** Wall-clock safety valve (ms) so a slow position never stalls a `go` (D-11). */
export const GRADING_MOVETIME_SAFETY_CAP_MS = 2500;

/** Slack (ms) added above the movetime cap before giving up on a `bestmove` reply. */
export const SLACK_MS = 2500;

/** Full-strength `Skill Level` value — resets the engine before every bot-grading/adjudication `go` (Pitfall 2). */
const FULL_STRENGTH_SKILL_LEVEL = 20;

/** Wall-clock cap (ms) for a single-line adjudication `go` — a quick eval, not a full MultiPV grade. */
export const ADJUDICATION_MOVETIME_MS = 500;

/** Slack (ms) added above `ADJUDICATION_MOVETIME_MS` before giving up on a `bestmove` reply. */
export const ADJUDICATION_SLACK_MS = 2500;

/**
 * WR-06: mutable counter of how often `evalPositionCp` fell back to a neutral
 * 0 cp because no `bound === 'exact'` info line ever surfaced within
 * `ADJUDICATION_MOVETIME_MS`. Module-level (not a return value) so callers
 * that never see an individual position's result — `calibration-harness.mjs`'s
 * spike report — can still surface a systematic occurrence instead of it
 * being silently invisible for an entire multi-hour sweep.
 */
export const adjudicationFallbackStats = { neutralFallbackCount: 0 };

/**
 * Builds the Node `EngineProviders` adapter `{ policy, grade }` over one
 * shared Maia ONNX session + a `grade` function. `gradeFn` is
 * `(fen, candidateUcis) => Promise<Map<string, MoveGrade>>` — the caller
 * supplies either `pool.grade` (Plan 03, the pool-backed path) or a
 * single-engine-bound `nodeGrade` closure; this module never assumes which.
 */
export function makeNodeProviders(session, ort, gradeFn) {
  return {
    policy: (fen, elo, side) => nodePolicy(session, ort, fen, elo, side),
    grade: gradeFn,
  };
}

/**
 * UCI-keyed Maia move-probability distribution at `elo` for `side` to move
 * (`EngineProviders.policy` contract, D-08). One un-batched forward pass —
 * the harness only ever has one `policy()` call in flight (concurrency 1).
 */
async function nodePolicy(session, ort, fen, elo, side) {
  void side; // side-to-move is implicit in fen's own 'w'/'b' field (D-08), mirrors maiaQueue.ts's convention.
  const boardTokens = encodeBoard(fen);
  const eloInput = Float32Array.of(eloToInput(elo));
  const feeds = {
    tokens: new ort.Tensor('float32', boardTokens, [1, NUM_SQUARES, PLANES_PER_SQUARE]),
    elo_self: new ort.Tensor('float32', eloInput, [1]),
    elo_oppo: new ort.Tensor('float32', eloInput, [1]), // symmetric self/oppo ELO — BOT-03
  };
  const result = await session.run(feeds);
  const policySlice = result.logits_move.data.slice(0, POLICY_VOCAB_SIZE);
  const sanProbs = maskAndSoftmax(policySlice, fen);

  const uciProbs = {};
  for (const [san, prob] of Object.entries(sanProbs)) {
    const uci = sanToUci(fen, san);
    if (uci !== null) uciProbs[uci] = prob;
  }
  return uciProbs;
}

/**
 * UCI-keyed Stockfish shallow-eval grades for `candidateUcis`, white-POV cp,
 * `depth`-carrying (`EngineProviders.grade` contract, D-08). Mirrors
 * `workerPool.ts`'s `sendGo`/`handleLine`: `searchmoves`-restricted MultiPV,
 * keyed by `parsed.pv[0]` — NEVER the `multipv` rank field (SC5 landmine) —
 * filtered to `bound === 'exact'` only.
 */
export async function nodeGrade(stockfish, fen, candidateUcis) {
  if (candidateUcis.length === 0) return new Map(); // mirror workerPool.ts WR-05

  const whitePovSign = fen.split(' ')[1] === 'b' ? -1 : 1;
  const grades = new Map();

  const off = stockfish.onLine((line) => {
    if (!line.startsWith('info ')) return;
    const parsed = parseInfoLine(line);
    if (parsed === null || parsed.bound !== 'exact') return;
    const uci = parsed.pv[0];
    if (uci === undefined) return;
    grades.set(uci, {
      evalCp: parsed.scoreCp !== null ? parsed.scoreCp * whitePovSign : null,
      evalMate: parsed.scoreMate !== null ? parsed.scoreMate * whitePovSign : null,
      depth: parsed.depth,
    });
  });

  // Pitfall 2: reset the shared engine to full strength FIRST — a prior
  // Stockfish-skill anchor move must never leak a weakened Skill Level into
  // the bot's own grading search.
  stockfish.send(`setoption name Skill Level value ${FULL_STRENGTH_SKILL_LEVEL}`);
  stockfish.send('setoption name UCI_LimitStrength value false');
  stockfish.send(`setoption name MultiPV value ${candidateUcis.length}`);
  stockfish.send(`position fen ${fen}`);
  stockfish.send(
    `go depth ${GRADING_TARGET_DEPTH} searchmoves ${candidateUcis.join(' ')} movetime ${GRADING_MOVETIME_SAFETY_CAP_MS}`,
  );
  try {
    await stockfish.waitFor((line) => line.startsWith('bestmove'), GRADING_MOVETIME_SAFETY_CAP_MS + SLACK_MS);
  } finally {
    off();
  }
  return grades;
}

/**
 * Single-line Stockfish eval (white-POV cp) at `fen` — D-10 cutoff 2
 * (adjudication) and the pool's `evalPosition` surface (Plan 03). Resets
 * every option it depends on first (Pitfall 2): a prior weakened anchor
 * `Skill Level` must never leak into an adjudication `go`.
 */
export async function evalPositionCp(stockfish, fen) {
  const whitePovSign = fen.split(' ')[1] === 'b' ? -1 : 1;
  let lastExact = null;
  const off = stockfish.onLine((line) => {
    if (!line.startsWith('info ')) return;
    const parsed = parseInfoLine(line);
    if (parsed === null || parsed.bound !== 'exact') return;
    lastExact = parsed; // deepest-seen wins (later info lines overwrite earlier ones)
  });
  stockfish.send(`setoption name Skill Level value ${FULL_STRENGTH_SKILL_LEVEL}`);
  stockfish.send('setoption name UCI_LimitStrength value false');
  stockfish.send('setoption name MultiPV value 1');
  stockfish.send(`position fen ${fen}`);
  stockfish.send(`go movetime ${ADJUDICATION_MOVETIME_MS}`);
  try {
    await stockfish.waitFor((line) => line.startsWith('bestmove'), ADJUDICATION_MOVETIME_MS + ADJUDICATION_SLACK_MS);
  } finally {
    off();
  }
  if (lastExact === null) {
    // WR-06: was a silent, uninstrumented fallback — a systematic occurrence
    // could degrade adjudication accuracy for a whole sweep with zero
    // visibility. Now counted so the harness's throughput report can surface
    // it (see calibration-harness.mjs's printSpikeReport).
    adjudicationFallbackStats.neutralFallbackCount++;
    return 0; // no exact info line surfaced -- treat as neutral (should not normally occur)
  }
  const cp =
    lastExact.scoreMate !== null
      ? lastExact.scoreMate > 0
        ? MATE_CP_EQUIVALENT
        : -MATE_CP_EQUIVALENT
      : (lastExact.scoreCp ?? 0);
  return cp * whitePovSign;
}
