import { gapWords, withGapVerdict, type GapCell } from '@/lib/gapBar';

/**
 * The popover's first list item: the typical-gap range plus the shared chance / verdict
 * sentence. Shared with the Facepalm blunders tile of Flaw Stats. The facepalm band is per TC
 * without Elo keying, so the line names FlawChess players rather than players at your level,
 * and the copy never says benchmark. No provisional caveat in user copy (popover minimalism):
 * the provisional status lives in app/services/facepalm_zones.py and SEED-261120-bzq.
 */
export function facepalmRangeNote(cell: GapCell): string {
  return withGapVerdict(
    `Typical gap among FlawChess players: ${gapWords(cell.zoneLo)} to ${gapWords(cell.zoneHi)}.`,
    cell,
  );
}
