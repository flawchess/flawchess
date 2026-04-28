import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';
import type { OpeningInsightFinding } from '@/types/insights';

// OPENING_INSIGHTS_POPOVER_COPY lives in OpeningInsightsBlock.tsx (JSX co-location).

type ConfidenceLevel = 'low' | 'medium' | 'high';

const CONFIDENCE_BASE_COPY: Record<ConfidenceLevel, string> = {
  low: 'Not enough evidence — this could plausibly be chance',
  medium: 'Likely a real effect (p < 0.10)',
  high: 'Strong evidence of a real effect (p < 0.05)',
};

/** Tooltip copy for confidence indicators — significance level explainer plus the actual p-value. */
export function formatConfidenceTooltip(level: ConfidenceLevel, pValue: number): string {
  return `${CONFIDENCE_BASE_COPY[level]} (p = ${pValue.toFixed(3)})`;
}

/**
 * Map a classification + severity tuple to the appropriate border-left color hex.
 * Mirrors getArrowColor's two-tier shade scheme — guarantees the card border and
 * the on-board arrow render the same color after the deep-link.
 */
export function getSeverityBorderColor(
  classification: OpeningInsightFinding['classification'],
  severity: OpeningInsightFinding['severity'],
): string {
  if (classification === 'weakness') {
    return severity === 'major' ? DARK_RED : LIGHT_RED;
  }
  return severity === 'major' ? DARK_GREEN : LIGHT_GREEN;
}

/**
 * Trim a SAN sequence + candidate move down to a compact "...N.move N+1.candidate"
 * string per D-05. Keeps the last 2 entry plys + candidate when the entry sequence
 * has 3+ plys, otherwise renders the whole sequence without ellipsis.
 *
 * If keeping the last 2 entry plys would start the trimmed render mid-move on a
 * Black ply, the orphan black ply is dropped so the render starts on a White ply.
 * This matches the user-facing examples in CONTEXT.md D-05 / RESEARCH.md table.
 *
 * @param entrySanSequence - SAN tokens from start to entry position (candidate excluded). May be empty.
 * @param candidateMoveSan - The candidate move SAN (always present).
 * @returns Compact rendering, e.g. "...3.d4 cxd4 4.Nxd4" or "1.e4 c5".
 */
export function trimMoveSequence(
  entrySanSequence: string[],
  candidateMoveSan: string,
): string {
  const totalEntryPlys = entrySanSequence.length;

  // Build the working sequence to render and decide whether ellipsis is needed.
  let workingEntry: string[];
  let firstPlyIndexInFull: number;  // 0-based index of the first rendered ply in the full sequence
  let needsEllipsis: boolean;

  if (totalEntryPlys < 2) {
    // 0 or 1 entry plys: render whole sequence, no ellipsis.
    workingEntry = entrySanSequence;
    firstPlyIndexInFull = 0;
    needsEllipsis = false;
  } else {
    // Default: keep last 2 entry plys.
    workingEntry = entrySanSequence.slice(-2);
    firstPlyIndexInFull = totalEntryPlys - workingEntry.length;
    // If the first trimmed ply is a Black ply (odd index), drop it so the
    // render starts on a White ply. This matches the D-05 examples exactly.
    if (firstPlyIndexInFull % 2 === 1) {
      workingEntry = workingEntry.slice(1);
      firstPlyIndexInFull += 1;
    }
    // Ellipsis if any entry ply was omitted from the front.
    needsEllipsis = firstPlyIndexInFull > 0;
  }

  const trimmed = [...workingEntry, candidateMoveSan];

  // Render each token with PGN move-number notation.
  const tokens: string[] = [];
  for (let i = 0; i < trimmed.length; i += 1) {
    const plyIndex = firstPlyIndexInFull + i;
    const isWhitePly = plyIndex % 2 === 0;
    const moveNumber = Math.floor(plyIndex / 2) + 1;
    const san = trimmed[i]!;  // safe: i is a valid index into trimmed

    if (isWhitePly) {
      tokens.push(`${moveNumber}.${san}`);
    } else if (i === 0) {
      // First rendered ply is a Black ply (only happens when totalEntryPlys < 2
      // produced workingEntry = [] and the candidate itself is Black-on-move —
      // unreachable for entry_ply >= 3 backend, but defensive).
      tokens.push(`${moveNumber}...${san}`);
    } else {
      // Black follow-up to a White ply we just rendered.
      tokens.push(san);
    }
  }

  const body = tokens.join(' ');
  return needsEllipsis ? `...${body}` : body;
}
