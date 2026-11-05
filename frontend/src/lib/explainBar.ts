/**
 * explainBar — pure rules for the contextual Explain bar on /analysis (SEED-208).
 *
 * Module-scope pure functions (no React imports) for the same reason as
 * `findFocusedFlaw`: the React Compiler memoization lint cannot analyze nested
 * control flow inline in a component, and a plain function called FROM
 * `useMemo` satisfies it. Keeping the rules as ordered early returns also keeps
 * eslint `max-depth` (4) well clear.
 */

import type { FlawMarker, FlawSeverity, TacticLinesResponse } from '@/types/library';
import type { TacticRef } from '@/lib/analysisTactics';

/** allowed_moves[0] is the prepended flaw move, already on the main line. */
const ALLOWED_PREPEND_LEN = 1;
/** A missed line forks at ply-1, so ply 0 would need a fork at the root, which the graft cannot address. */
const MIN_MISSED_FORK_PLY = 1;

/** Severities the bar is offered for (D-08: inaccuracies are out of scope). */
export type ExplainSeverity = Extract<FlawSeverity, 'mistake' | 'blunder'>;

function isExplainSeverity(severity: FlawSeverity): severity is ExplainSeverity {
  return severity === 'mistake' || severity === 'blunder';
}

/**
 * The mistake/blunder marker at `ply`, for either side (D-08), or null.
 * Inaccuracies are never eligible: game_flaws holds M/B only and the
 * tactic-lines endpoint 404s for them.
 */
export function eligibleExplainMarker(
  markers: FlawMarker[] | null | undefined,
  ply: number,
): FlawMarker | null {
  if (markers == null || ply < 0) return null;
  return markers.find((m) => m.ply === ply && isExplainSeverity(m.severity)) ?? null;
}

/**
 * Which stored lines can actually be grafted at `ply`. The graft effect
 * early-returns on an empty PV or a missing fork WITHOUT clearing pendingFlaw,
 * so offering Explain on an ungraftable line would leave the bar stuck pending.
 */
export function usableExplainLines(
  data: TacticLinesResponse,
  ply: number,
): { missed: boolean; allowed: boolean } {
  return {
    missed: ply >= MIN_MISSED_FORK_PLY && (data.missed_moves?.length ?? 0) > 0,
    allowed: (data.allowed_moves?.length ?? 0) > ALLOWED_PREPEND_LEN,
  };
}

/**
 * Direction rule (D-04): the game owner's own flaw opens the MISSED line, the
 * opponent's flaw the ALLOWED line. Falls back to the other line when the
 * preferred one is unusable (D-09); null when neither (D-10). `is_user` is
 * relative to the game OWNER, not the viewer.
 */
export function chooseExplainOrientation(
  isUser: boolean,
  usable: { missed: boolean; allowed: boolean },
): 'missed' | 'allowed' | null {
  const preferred = isUser ? 'missed' : 'allowed';
  const fallback = isUser ? 'allowed' : 'missed';
  if (usable[preferred]) return preferred;
  if (usable[fallback]) return fallback;
  return null;
}

export type ExplainBarState =
  | { kind: 'hidden' }
  | {
      kind: 'explain';
      flaw: TacticRef;
      san: string | null;
      severity: ExplainSeverity;
      pending: boolean;
    };

export interface ExplainBarInputs {
  isGameMode: boolean;
  fastForwardRunning: boolean;
  flawMarkers: FlawMarker[] | null | undefined;
  /** Main-line ply of the current node, -1 off the main line. */
  landingPly: number;
  pendingFlaw: TacticRef | null;
  tacticLines: TacticLinesResponse | null | undefined;
}

/** Ordered early returns; see the numbered comments for each rule. */
export function resolveExplainBarState(inputs: ExplainBarInputs): ExplainBarState {
  const { isGameMode, fastForwardRunning, flawMarkers, landingPly, pendingFlaw, tacticLines } = inputs;
  // (1) Not game mode, or a Jump run is animating: nothing to offer.
  if (!isGameMode || fastForwardRunning) return { kind: 'hidden' };
  // (2) An unrelated chip or deep-link open is in flight.
  if (pendingFlaw != null && pendingFlaw.ply !== landingPly) return { kind: 'hidden' };
  // (3) Not on an eligible flaw ply (covers sidelines, the root and inaccuracies).
  const marker = eligibleExplainMarker(flawMarkers, landingPly);
  if (marker === null || !isExplainSeverity(marker.severity)) return { kind: 'hidden' };
  // (4) D-11: loading and no-lines both render nothing, never a placeholder.
  if (tacticLines == null) return { kind: 'hidden' };
  // (5) D-10: neither line is usable.
  const orientation = chooseExplainOrientation(marker.is_user, usableExplainLines(tacticLines, landingPly));
  if (orientation === null) return { kind: 'hidden' };
  // (6) Offer Explain.
  return {
    kind: 'explain',
    flaw: { ply: landingPly, orientation },
    san: marker.move_san,
    severity: marker.severity,
    pending: pendingFlaw?.ply === landingPly,
  };
}
