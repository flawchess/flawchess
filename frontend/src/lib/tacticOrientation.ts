import type { FlawMarker } from '@/types/library';
import type { TacticRef } from '@/lib/analysisTactics';

/**
 * Tactic orientation to auto-open when the board is deep-linked to a ply.
 *
 * Mirrors the user-scoping in Analysis.tsx's flawMarkerByNodeId: only the user's own flaw at
 * `ply` counts, and opponent motifs are ignored. Missed takes precedence over allowed when a
 * flaw carries both, so the more instructive "what you should have played" line opens first.
 * Returns null when there is no user tactic chip at `ply` (the board just navigates to the
 * ply as before, opening no line).
 */
export function tacticOrientationAtPly(
  flawMarkers: FlawMarker[] | null | undefined,
  ply: number | null,
): 'missed' | 'allowed' | null {
  if (flawMarkers == null || ply == null) return null;
  const fm = flawMarkers.find((m) => m.ply === ply && m.is_user);
  if (fm == null) return null;
  if (fm.missed_tactic_motif !== null) return 'missed';
  if (fm.allowed_tactic_motif !== null) return 'allowed';
  return null;
}

/**
 * Whether the line has a user-visible tactic motif, i.e. a numbered countdown overlay is honest.
 *
 * Mirrors the user-scoping of `tacticOrientationAtPly` and the move-list chips: opponent motifs
 * are hidden there, and the teal/crimson TAC_MISSED / TAC_ALLOWED colours read from the user's
 * side. The marker motif fields are confidence-gated while the TacticLinesResponse depth/motif
 * fields are not, so the marker is the right source. Every chip-opened or deep-link-opened line
 * passes (chips exist only for visible user motifs), so their overlay is unchanged; an Explain
 * on a non-motif flaw or on an opponent flaw does not.
 */
export function lineHasVisibleMotif(
  flawMarkers: FlawMarker[] | null | undefined,
  line: TacticRef | null,
): boolean {
  if (flawMarkers == null || line == null) return false;
  const fm = flawMarkers.find((m) => m.ply === line.ply && m.is_user);
  if (fm == null) return false;
  const motif = line.orientation === 'missed' ? fm.missed_tactic_motif : fm.allowed_tactic_motif;
  return motif !== null;
}
