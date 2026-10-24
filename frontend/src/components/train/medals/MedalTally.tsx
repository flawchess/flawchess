/**
 * MedalTally — one row owner's lifetime medals for one board.
 * Non-zero types only, gold, silver, bronze order. Up to five medals of a
 * type stack as horizontally overlapping MedalIcons; from six up the type
 * collapses to one icon plus a text-sm count. Renders nothing
 * when the owner has no medals, so a board before the first deadline shows no
 * tally.
 *
 * It is its own nowrap item inside the row's wrapping name block (only the
 * name truncates), so it drops below the name on a narrow screen and the value
 * columns stay aligned. Presentational only: no popover, no history.
 */
import type { ReactElement } from 'react';
import { MedalIcon } from '@/components/train/medals/MedalIcon';
import { tallyAriaLabel, tallyEntries } from '@/lib/trainMedals';
import type { LeaderboardBoardKind, LeaderboardMedals } from '@/types/train';

/** Up to this many medals of a type render as stacked icons; above it, one icon plus a count. */
const MAX_STACKED_MEDALS = 5;
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
      className="inline-flex items-center whitespace-nowrap font-normal"
    >
      {entries.map(({ kind, count }) => {
        const showCount = count > MAX_STACKED_MEDALS;
        const iconCount = showCount ? 1 : count;
        return (
          // Bug fix: an SVG has no text baseline, so with items-center the icon's
          // bottom edge became the tally's baseline and the baseline-aligned row
          // name block lifted icon and count above the name. Baseline-align so the
          // count text sets the baseline, and center only the icons.
          <span key={kind} data-testid={`${testId}-${kind}`} className="inline-flex items-baseline">
            <span className="inline-flex self-center">
              {Array.from({ length: iconCount }, (_, i) => (
                // Each later icon overlaps the previous one by about 60% of its width.
                <MedalIcon key={i} kind={kind} className={i > 0 ? '-ml-2.5' : undefined} />
              ))}
            </span>
            {/* The count span stays even when the number is hidden: without a text
                child the icons would lose the baseline fix above and lift. */}
            {showCount ? (
              <span data-testid={`${testId}-${kind}-count`} className="mx-0.5 text-sm tabular-nums">
                {count}
              </span>
            ) : (
              <span aria-hidden="true" className="text-sm">
                {BASELINE_ANCHOR}
              </span>
            )}
          </span>
        );
      })}
    </span>
  );
}
