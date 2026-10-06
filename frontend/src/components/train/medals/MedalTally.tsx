/**
 * MedalTally — one row owner's lifetime medals for one board (Phase 231).
 * Non-zero types only, gold, silver, bronze order, each a tinted lucide Medal
 * plus a text-sm count from 2 up (a single medal is just the icon). Renders nothing when the owner has no medals, so a
 * board before the first deadline looks exactly as in Phase 230.
 *
 * It is its own nowrap item inside the row's wrapping name block (only the
 * name truncates), so it drops below the name on a narrow screen and the value
 * columns stay aligned. Presentational only: no popover, no history.
 */
import type { ReactElement } from 'react';
import { MedalIcon } from '@/components/train/medals/MedalIcon';
import { tallyAriaLabel, tallyEntries } from '@/lib/trainMedals';
import type { LeaderboardBoardKind, LeaderboardMedals } from '@/types/train';

/** A single medal reads as one without a number; counts show from here up. */
const MIN_SHOWN_TALLY_COUNT = 2;
/** Zero-width space: keeps a text baseline in the count span when the number is hidden. */
const BASELINE_ANCHOR = '\u200B';

interface MedalTallyProps {
  medals: LeaderboardMedals;
  board: LeaderboardBoardKind;
  testId: string;
}

export function MedalTally({ medals, board, testId }: MedalTallyProps): ReactElement | null {
  const entries = tallyEntries(medals);
  if (entries.length === 0) return null;
  return (
    <span
      role="img"
      aria-label={tallyAriaLabel(medals, board)}
      data-testid={testId}
      className="inline-flex items-center gap-1.5 whitespace-nowrap font-normal"
    >
      {entries.map(({ kind, count }) => (
        // Bug fix: an SVG has no text baseline, so with items-center the icon's
        // bottom edge became the tally's baseline and the baseline-aligned row
        // name block lifted icon and count above the name. Baseline-align so the
        // count text sets the baseline, and center only the icon.
        <span key={kind} data-testid={`${testId}-${kind}`} className="inline-flex items-baseline gap-0.5">
          <MedalIcon kind={kind} className="self-center" />
          {/* The count span stays even when the number is hidden: without a text
              child the icon would lose the baseline fix above and lift. */}
          {count >= MIN_SHOWN_TALLY_COUNT ? (
            <span className="text-sm tabular-nums">{count}</span>
          ) : (
            <span aria-hidden="true" className="text-sm">
              {BASELINE_ANCHOR}
            </span>
          )}
        </span>
      ))}
    </span>
  );
}
