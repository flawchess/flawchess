import { GAP_AXIS_LABELS } from '@/lib/gapBar';

/**
 * Right margin that ends the caption row where the bar track ends: on phones the words
 * column (6rem) and popover sit right of the track; from md up the track is full width.
 */
const AXIS_CAPTION_CLASS = 'mr-34 md:mr-0 flex justify-between text-sm text-muted-foreground';

interface GapAxisCaptionProps {
  testId: string;
}

/** The better / worse axis caption under a card's gap bars: fewer flaws (better) sit left. */
export function GapAxisCaption({ testId }: GapAxisCaptionProps) {
  return (
    <div className={AXIS_CAPTION_CLASS} data-testid={testId}>
      {GAP_AXIS_LABELS.map((label) => (
        <span key={label}>{label}</span>
      ))}
    </div>
  );
}
