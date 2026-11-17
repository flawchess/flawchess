import type { FlawMarker } from '@/types/library';
import type { TacticRef } from '@/lib/analysisTactics';

/**
 * Whether the line has a user-visible tactic motif, i.e. a numbered countdown overlay is honest.
 *
 * Mirrors the move-list chips, which show motifs for BOTH colors. The marker motif fields are
 * confidence-gated while the TacticLinesResponse depth/motif fields are not, so the marker is the
 * right source. Every chip-opened line passes (chips exist only for visible
 * motifs); an Explain on a non-motif flaw does not.
 *
 * Bug fix: this used to also require `is_user`, left over from when opponent chips were hidden.
 * Once opponent chips were shown, their lines lost the numbered depth countdown on the board.
 */
export function lineHasVisibleMotif(
  flawMarkers: FlawMarker[] | null | undefined,
  line: TacticRef | null,
): boolean {
  if (flawMarkers == null || line == null) return false;
  const fm = flawMarkers.find((m) => m.ply === line.ply);
  if (fm == null) return false;
  const motif = line.orientation === 'missed' ? fm.missed_tactic_motif : fm.allowed_tactic_motif;
  return motif !== null;
}
