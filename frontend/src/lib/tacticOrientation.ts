import type { FlawMarker } from '@/types/library';

/**
 * Tactic orientation to auto-open when the board is deep-linked to a ply (Quick 260702-fog).
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
