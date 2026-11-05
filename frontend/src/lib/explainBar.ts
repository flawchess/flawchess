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
import { flawKey, type OpenLine, type TacticRef } from '@/lib/analysisTactics';
import { resolveVisibleTactic } from '@/lib/tacticComparisonMeta';

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

/** The two lines the bar can open, keyed by tactic orientation (Best = missed, Punish = allowed). */
export type ExplainOrientation = 'missed' | 'allowed';
export type ExplainLineUsable = Record<ExplainOrientation, boolean>;

/**
 * Which stored lines can actually be grafted at `ply`. The graft effect
 * releases pendingFlaw on an empty PV or a missing fork without grafting,
 * so an ungraftable line's button is disabled instead of doing nothing.
 */
export function usableExplainLines(data: TacticLinesResponse, ply: number): ExplainLineUsable {
  return {
    missed: ply >= MIN_MISSED_FORK_PLY && (data.missed_moves?.length ?? 0) > 0,
    allowed: (data.allowed_moves?.length ?? 0) > ALLOWED_PREPEND_LEN,
  };
}

/** One tactic in the Explain headline, as text: "missed discovered-attack in 2". */
export interface ExplainTactic {
  orientation: ExplainOrientation;
  text: string;
}

/** The flaw the bar is about: its move, severity badge and tactics as text. */
export interface ExplainHeadline {
  san: string | null;
  severity: ExplainSeverity;
  /** Every visible tactic on this flaw (missed first, then allowed); empty: none. */
  tactics: ExplainTactic[];
}

export type ExplainBarState =
  | { kind: 'hidden' }
  | (ExplainHeadline & {
      kind: 'explain';
      ply: number;
      /** Per-button availability; at least one is true (both false hides the bar, D-10). */
      usable: ExplainLineUsable;
      /** The line being opened for this ply (both buttons disabled), or null. */
      pending: ExplainOrientation | null;
    })
  // Phase 245 UAT: no sibling-line switch inside a line (Best hides Punish and vice
  // versa). The open line's flaw headline stays visible while stepping through it; null
  // only when the markers have no mistake/blunder at the line's ply.
  | { kind: 'got-it'; line: OpenLine; headline: ExplainHeadline | null };

export interface ExplainBarInputs {
  isGameMode: boolean;
  fastForwardRunning: boolean;
  flawMarkers: FlawMarker[] | null | undefined;
  /** Main-line ply of the current node, -1 off the main line. */
  landingPly: number;
  pendingFlaw: TacticRef | null;
  /**
   * The page's existing `focusedFlaw` memo (one source of truth with the board overlays,
   * never a second containment walk). Drives the got-it state.
   */
  focusedFlaw: TacticRef | null;
  openLines: Map<string, OpenLine>;
  tacticLines: TacticLinesResponse | null | undefined;
  /** The ply `tacticLines` was fetched for, so a got-it bar never reads another flaw's lines. */
  tacticLinesPly: number | null;
}

/** The open line the focused flaw maps to, or null. */
function gotItLine({ focusedFlaw, openLines }: ExplainBarInputs): OpenLine | null {
  if (focusedFlaw === null) return null;
  return openLines.get(flawKey(focusedFlaw)) ?? null;
}

/**
 * The flaw's visible tactics as headline text, both orientations. resolveVisibleTactic
 * applies the family guard (family-less motifs show nothing), the same rule as the
 * move-list chip's depth label and the board depth badges. anchored=false: this is a navigable surface, so the allowed +1
 * decision-anchor offset is dropped (the chip's depth, spelled out).
 */
function explainTactics(marker: FlawMarker): ExplainTactic[] {
  const slots = [
    { orientation: 'missed', motif: marker.missed_tactic_motif, depth: marker.missed_tactic_depth },
    { orientation: 'allowed', motif: marker.allowed_tactic_motif, depth: marker.allowed_tactic_depth },
  ] as const;
  return slots.flatMap(({ orientation, motif, depth }) => {
    const visible = resolveVisibleTactic(orientation, motif, depth, undefined, false);
    if (visible === null) return [];
    const { motifLabel, depthLabel } = visible;
    const text = depthLabel != null ? `${orientation} ${motifLabel} in ${depthLabel}` : `${orientation} ${motifLabel}`;
    return [{ orientation, text }];
  });
}

/** The headline for the mistake/blunder at `ply`, or null when there is none. */
function explainHeadline(flawMarkers: FlawMarker[] | null | undefined, ply: number): ExplainHeadline | null {
  const marker = eligibleExplainMarker(flawMarkers, ply);
  if (marker === null || !isExplainSeverity(marker.severity)) return null;
  return { san: marker.move_san, severity: marker.severity, tactics: explainTactics(marker) };
}

/** Ordered early returns; see the numbered comments for each rule. */
export function resolveExplainBarState(inputs: ExplainBarInputs): ExplainBarState {
  const { isGameMode, fastForwardRunning, landingPly } = inputs;
  // (1) Not game mode, or a Jump run is animating: nothing to offer.
  if (!isGameMode || fastForwardRunning) return { kind: 'hidden' };
  // (1b) Got it (D-06): the board is in an open line. Following findFocusedFlaw semantics,
  // that covers the grafted subtree (including free moves played off a PV node), a missed
  // line's fork (ply-1) after stepping Back out, an allowed line's fork (the flaw node
  // itself) and a deep-link auto-opened line.
  const openLine = gotItLine(inputs);
  if (openLine === null) return explainState(inputs);
  // Bug fix (Phase 245 review WR-01): a missed line for P forks at mainLine[P-1]. When the
  // board sits on that fork (a main-line node that is not the line's own flaw ply) and P-1
  // is itself an explainable flaw, the landing ply's buttons win. Got it for P used to
  // shadow them, so P-1's lines were reachable only via Got it (which deletes P's line) and
  // then Back. Inside the subtree landingPly is -1, so Got it is unaffected there.
  if (landingPly >= 0 && landingPly !== openLine.ply) {
    const landing = explainState(inputs);
    if (landing.kind === 'explain') return landing;
  }
  return { kind: 'got-it', line: openLine, headline: explainHeadline(inputs.flawMarkers, openLine.ply) };
}

/** Rules (2)-(6): the Best / Punish offer for the landing ply, or hidden. */
function explainState(inputs: ExplainBarInputs): ExplainBarState {
  const { flawMarkers, landingPly, pendingFlaw, tacticLines, tacticLinesPly } = inputs;
  // (2) An unrelated chip or deep-link open is in flight.
  if (pendingFlaw != null && pendingFlaw.ply !== landingPly) return { kind: 'hidden' };
  // (3) Not on an eligible flaw ply (covers sidelines, the root and inaccuracies).
  const headline = explainHeadline(flawMarkers, landingPly);
  if (headline === null) return { kind: 'hidden' };
  // (4) D-11: loading and no-lines both render nothing, never a placeholder.
  if (tacticLines == null || tacticLinesPly !== landingPly) return { kind: 'hidden' };
  // (5) D-10: neither line is usable. One usable line still shows both buttons, the other
  // disabled, so the row layout is the same on every flaw.
  const usable = usableExplainLines(tacticLines, landingPly);
  if (!usable.missed && !usable.allowed) return { kind: 'hidden' };
  // (6) Offer both buttons (the D-04 direction rule is gone: Best and Punish name
  // their line, so neither side's flaw needs a default).
  return {
    kind: 'explain',
    ply: landingPly,
    ...headline,
    usable,
    pending: pendingFlaw?.ply === landingPly ? pendingFlaw.orientation : null,
  };
}
