/**
 * Move info for the Analysis strip (the Explain bar's row) on moves that offer no Best / Punish
 * lines. In the mid layout the strip's height is kept free on every move so the height-fitted
 * board never resizes, which left an empty gap under the board on every move but a flaw. The
 * strip now always describes the current move there (and on desktop): a mistake or blunder gets
 * its usual headline (move, badge, tactics, facepalm score), any other move the badge the board
 * shows on its target square and a word for it. Phones keep the flaw-only strip (owner,
 * 2026-11-26), since there it costs the tab panel height.
 */

import type { SquareMarker } from '@/components/board/boardMarkers';
import type { FlawMarkerEntry } from '@/components/analysis/VariationTree';
import type { FlawMarker } from '@/types/library';
import { explainHeadline, type ExplainHeadline } from '@/lib/explainBar';

/** The board badges the strip can name, in the board's precedence order. */
export type MoveInfoQuality =
  | 'blunder'
  | 'mistake'
  | 'inaccuracy'
  | 'gem'
  | 'great'
  | 'best'
  | 'good'
  | 'book';

export type MoveInfo =
  /** A main-line mistake or blunder: the same headline the Best / Punish row shows. */
  | { kind: 'flaw'; headline: ExplainHeadline }
  /** Any other move: its SAN and board badge (null when the board shows none). */
  | {
      kind: 'quality';
      san: string;
      quality: MoveInfoQuality | null;
      facepalm: boolean;
      /** Gem / great only, when the move list has its detection data: feeds the badge popover. */
      rarity?: MoveRarity;
    };

/** A gem's or great move's detection data, as the move-list popover shows it. */
export interface MoveRarity {
  tier: 'gem' | 'great';
  /** Maia probability (0..1) at the detection rung: popover only, the strip copy stays vague. */
  maiaProbability: number | null;
  /** The ELO-slider value the move was detected at. */
  elo: number | null;
  byOpponent: boolean;
}

export interface MoveInfoInputs {
  isGameMode: boolean;
  fastForwardRunning: boolean;
  /** SAN of the move that led to the current node; null at the root. */
  san: string | null;
  /** Main-line ply of the current node, -1 off the main line. */
  landingPly: number;
  flawMarkers: FlawMarker[] | null | undefined;
  /** The board's square marker on the last move's target square, if any. */
  lastMoveMarker: SquareMarker | undefined;
  /** The current node's move-list marker entry (gem / great detection data), if any. */
  moveListMarker?: FlawMarkerEntry;
}

/** The move-list rarity data behind a gem / great badge; undefined when the entry lacks it. */
function moveRarity(quality: MoveInfoQuality | null, entry: FlawMarkerEntry | undefined): MoveRarity | undefined {
  if (entry === undefined) return undefined;
  if (quality === 'gem' && entry.gem === true) {
    return {
      tier: 'gem',
      maiaProbability: entry.gemMaiaProbability ?? null,
      elo: entry.gemElo ?? null,
      byOpponent: entry.gemByOpponent ?? false,
    };
  }
  if (quality === 'great' && entry.great === true) {
    return {
      tier: 'great',
      maiaProbability: entry.greatMaiaProbability ?? null,
      elo: entry.greatElo ?? null,
      byOpponent: entry.greatByOpponent ?? false,
    };
  }
  return undefined;
}

/** The badge a square marker draws, following boardMarkers' precedence. */
function markerQuality(marker: SquareMarker): MoveInfoQuality | null {
  if (marker.severity != null) return marker.severity;
  if (marker.gem) return 'gem';
  if (marker.great) return 'great';
  if (marker.best) return 'best';
  if (marker.good) return 'good';
  if (marker.book) return 'book';
  return null;
}

/** What the strip says about the current move, or null when it has nothing to say. */
export function resolveMoveInfo(inputs: MoveInfoInputs): MoveInfo | null {
  const { isGameMode, fastForwardRunning, san, landingPly, flawMarkers, lastMoveMarker, moveListMarker } = inputs;
  // Same gate as the Best / Punish row: game mode only, and quiet during a Jump run.
  if (!isGameMode || fastForwardRunning || san === null) return null;
  const headline = landingPly >= 0 ? explainHeadline(flawMarkers, landingPly) : null;
  // A flaw headline with tactics or a facepalm score says more than the badge's word; a bare
  // one ("Nxd6 ?") reads better as the worded badge, like every other move.
  if (headline !== null && (headline.tactics.length > 0 || headline.facepalmPct != null)) {
    return { kind: 'flaw', headline };
  }
  const quality = lastMoveMarker !== undefined ? markerQuality(lastMoveMarker) : null;
  const rarity = moveRarity(quality, moveListMarker);
  return {
    kind: 'quality',
    san,
    quality,
    facepalm: lastMoveMarker?.facepalm === true,
    ...(rarity !== undefined ? { rarity } : {}),
  };
}
