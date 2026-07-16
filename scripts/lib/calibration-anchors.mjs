#!/usr/bin/env node
/**
 * calibration-anchors.mjs — known-strength anchor move-choosers (Phase 168,
 * CAL-01). Anchors are simple, deterministic-or-engine-native move-choosers
 * the bot plays AGAINST to measure its strength — they never call
 * `selectBotMove`/`mctsSearch` and are NOT the bot's own regime dispatch.
 *
 * `maiaArgmaxMove` shares the same `EngineProviders.policy` the bot's own
 * `deps.policy` uses (raw-Maia argmax rung, deterministic) via
 * `calibration-providers.mjs`'s `makeNodeProviders`. `stockfishSkillMove`
 * shares the same spawned Stockfish process, letting the engine's OWN
 * `Skill Level` weakening logic pick a move directly (never graded by us —
 * that would be the bot's own `grade()` regime, a different code path).
 *
 * Pitfall 2 (168-RESEARCH.md): both anchors set every UCI option their `go`
 * depends on immediately before that `go` — the shared Stockfish process also
 * serves the bot's own grading and adjudication, and option state persists
 * across roles unless explicitly reset each time.
 */
import { fallbackMove } from '@/lib/engine/botSampling';
import { parseBestmove } from '@/hooks/uciParser';

/** Movetime (ms) for one anchor move — no clock, fixed harness budget (D-11). */
export const ANCHOR_MOVETIME_MS = 1000;

/** Slack (ms) added above ANCHOR_MOVETIME_MS before giving up on a `bestmove` reply. */
export const ANCHOR_MOVETIME_SLACK_MS = 2500;

/**
 * Documented-APPROXIMATE Stockfish `Skill Level` -> Elo mapping
 * (168-RESEARCH.md Open Question 2). No authoritative Stockfish-18-specific
 * table exists; these are round, community-reported approximations, used
 * ONLY for the advisory per-cell Elo estimate (D-05) — never the primary
 * raw W/D/L matrix (D-04). Carries the same +/-100-150 Elo conversion-error
 * caveat SEED-091 already accepts for this milestone.
 *
 * Keys `8` and `10` (Phase 173, D-09) are `[ASSUMED]` — 173-RESEARCH.md
 * Assumption A1's round, explicitly-approximate continuations of the same
 * spacing above, added so the anchor-ladder orchestrator (Plan 02) has a
 * superhuman-end Stockfish anchor. Like `0`/`3`/`5` above, these are used
 * ONLY for labels/ordering and the scheduler's initial cross-family pairing
 * guess (Pitfall 3) — NEVER as a fit input; the joint Bradley-Terry fit
 * (`calibration-anchor-fit.py`) derives every anchor's real internal rating
 * from game outcomes, ignoring this nominal table entirely for sf8/sf10.
 */
export const SF_SKILL_ELO = { 0: 1320, 3: 1750, 5: 2200, 8: 2600, 10: 2800 };

/**
 * Known anchor rating for a parsed `--anchors` token (Phase 168.5-05 D-15):
 * raw-Maia rung -> its ELO directly, Stockfish skill -> its documented-
 * approximate Elo (`SF_SKILL_ELO`). Shared by the D-05 advisory per-cell Elo
 * summary AND D-15's anchor-pruning ascending-order sort — reuses these
 * existing rating tables rather than hand-rolling a second lookup
 * (CONTEXT.md "Don't Hand-Roll").
 */
export function anchorRatingFor(anchorSpec) {
  return anchorSpec.kind === 'maia' ? anchorSpec.rungElo : SF_SKILL_ELO[anchorSpec.skillLevel];
}

/**
 * Raw-Maia argmax anchor: ONE `providers.policy()` call (shares the bot's own
 * Maia session), deterministic argmax with a UCI-ascending tie-break — never
 * weighted sampling (weighted sampling is the bot's own `blend<=0` regime,
 * not an anchor). Falls back to a uniform-random legal move (`fallbackMove`)
 * on a fully degenerate (empty) policy — never re-derives that fallback.
 */
export async function maiaArgmaxMove(providers, fen, rungElo, rng) {
  const side = fen.split(' ')[1] === 'b' ? 'b' : 'w';
  const uciProbs = await providers.policy(fen, rungElo, side);

  let bestUci = null;
  let bestProb = -Infinity;
  for (const [uci, prob] of Object.entries(uciProbs).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
    if (prob > bestProb) {
      bestProb = prob;
      bestUci = uci;
    }
  }
  return bestUci ?? fallbackMove(fen, rng);
}

/**
 * Stockfish-skill anchor: sets the engine's own weakening option and reads
 * its `bestmove` directly — never grades candidates ourselves (grading is
 * the bot's own `grade()` regime, a structurally different code path).
 */
export async function stockfishSkillMove(stockfish, fen, skillLevel) {
  stockfish.send(`setoption name Skill Level value ${skillLevel}`);
  stockfish.send('setoption name UCI_LimitStrength value false'); // Skill Level, not UCI_Elo (D-07 wording)
  // WR-02: reset MultiPV to 1 before every go, mirroring this module's own
  // stated discipline (header comment) — a prior bot-grading go on this same
  // pooled engine can leave MultiPV set as high as candidateUcis.length.
  stockfish.send('setoption name MultiPV value 1');
  stockfish.send(`position fen ${fen}`);
  stockfish.send(`go movetime ${ANCHOR_MOVETIME_MS}`);
  const line = await stockfish.waitFor(
    (l) => l.startsWith('bestmove'),
    ANCHOR_MOVETIME_MS + ANCHOR_MOVETIME_SLACK_MS,
  );
  return parseBestmove(line);
}
