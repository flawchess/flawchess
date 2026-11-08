/**
 * ExplainBar — the contextual flaw bar (SEED-208) under the move list. Presentational
 * only; state comes from `useExplainBar`, and Umami tracking lives in that hook's click
 * handlers.
 *
 * Phase 245 UAT replaced the single Explain button with two named lines:
 *   - Best: undo the mistake and play the better move (the MISSED line).
 *   - Punish: the refutation of the mistake (the ALLOWED line).
 * One row: the headline (move, severity badge and the tactics as colored text, e.g.
 * "c3 [blunder badge]: missed discovered-attack in 2", up to two lines) then both buttons. Inside a
 * line the headline stays and the buttons become a line stepper then Got it (the other
 * line's button is hidden there).
 * Clickable tactic chips live in the move list only.
 * Copy is neutral (never "your move"): `is_user` is the game OWNER and the viewer may
 * be someone else.
 */

import type { ReactElement, ReactNode } from 'react';
import { ChevronLeft, ChevronRight, Star, Swords } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { MoveQualityIcon } from '@/components/icons/MoveQualityIcon';
import { TAC_ALLOWED, TAC_MISSED } from '@/lib/theme';
import type {
  ExplainBarState,
  ExplainHeadline,
  ExplainOrientation,
  ExplainSeverity,
  ExplainTactic,
} from '@/lib/explainBar';
import type { ExplainLineStepper } from '@/hooks/analysis/useExplainBar';

type ExplainBarPlacement = 'desktop' | 'mid' | 'mobile';

// desktop: footer row inside the move-list Card. mid: its own Card under the board
// controls. mobile: a row directly above analysis-mobile-footer, mirroring that footer's
// border and background.
const PLACEMENT_CLASS: Record<ExplainBarPlacement, string> = {
  desktop: 'border-t border-border px-2 py-2',
  mid: 'w-full px-2 py-2',
  mobile: 'border-t border-border bg-background px-2 py-2',
};

/** Headline fallback when the marker has no SAN (the badge alone would read as nothing). */
const SEVERITY_NOUN: Record<ExplainSeverity, string> = {
  blunder: 'Blunder',
  mistake: 'Mistake',
};

/** Button copy, testid and icon per line. Best first: it starts one ply earlier. */
const LINE_BUTTON: Record<ExplainOrientation, { label: string; testId: string; icon: typeof Star }> = {
  missed: { label: 'Best', testId: 'btn-analysis-explain-best', icon: Star },
  allowed: { label: 'Punish', testId: 'btn-analysis-explain-punish', icon: Swords },
};
const LINE_ORDER: readonly ExplainOrientation[] = ['missed', 'allowed'];

const GOT_IT_LABEL = 'Done';

/** Line stepper buttons: wider than the square icon-lg (size-9) to use the room the
 *  shorter, icon-less Done button frees up. */
const STEPPER_BUTTON_CLASS = 'w-11';

const TACTIC_COLOR: Record<ExplainOrientation, string> = { missed: TAC_MISSED, allowed: TAC_ALLOWED };
const TACTIC_SEPARATOR = ', ';

/** Inline text (not a flex item), so it continues the headline's first line and wraps under the move. */
function TacticText({ tactics }: { tactics: ExplainTactic[] }): ReactElement | null {
  if (tactics.length === 0) return null;
  return (
    <span data-testid="analysis-explain-tactics">
      {tactics.map((t, i) => (
        <span key={t.orientation} data-orientation={t.orientation} style={{ color: TACTIC_COLOR[t.orientation] }}>
          {i > 0 && TACTIC_SEPARATOR}
          {t.text}
        </span>
      ))}
    </span>
  );
}

type ExplainBarProps = {
  state: ExplainBarState;
  onOpenLine: (orientation: ExplainOrientation) => void;
  onGotIt: () => void;
  stepper: ExplainLineStepper;
  placement: ExplainBarPlacement;
};

function LineButton({
  orientation,
  disabled,
  busy,
  onOpenLine,
}: {
  orientation: ExplainOrientation;
  disabled: boolean;
  busy: boolean;
  onOpenLine: (orientation: ExplainOrientation) => void;
}): ReactElement {
  const { label, testId, icon: Icon } = LINE_BUTTON[orientation];
  return (
    <Button
      type="button"
      variant="brand-outline"
      size="lg"
      data-testid={testId}
      disabled={disabled}
      aria-busy={busy || undefined}
      onClick={() => onOpenLine(orientation)}
    >
      <Icon data-icon="inline-start" aria-hidden="true" />
      {label}
    </Button>
  );
}

function LineStepper({ stepper }: { stepper: ExplainLineStepper }): ReactElement {
  return (
    <div data-testid="analysis-explain-stepper" className="flex shrink-0 items-center gap-1">
      <Button
        type="button"
        variant="brand-outline"
        size="icon-lg"
        className={STEPPER_BUTTON_CLASS}
        aria-label="Previous move in line"
        data-testid="btn-analysis-explain-line-back"
        disabled={!stepper.canBack}
        onClick={stepper.onBack}
      >
        <ChevronLeft aria-hidden="true" />
      </Button>
      <Button
        type="button"
        variant="brand-outline"
        size="icon-lg"
        className={STEPPER_BUTTON_CLASS}
        aria-label="Next move in line"
        data-testid="btn-analysis-explain-line-forward"
        disabled={!stepper.canForward}
        onClick={stepper.onForward}
      >
        <ChevronRight aria-hidden="true" />
      </Button>
    </div>
  );
}

type BarShellProps = {
  state: 'explain' | 'got-it';
  orientation?: ExplainOrientation;
  placement: ExplainBarPlacement;
  children: ReactNode;
};

/** Same root, classes and row structure for both states, so the swap never shifts the row height. */
function BarShell({ state, orientation, placement, children }: BarShellProps): ReactElement {
  // The mid placement is a charcoal Card (matches the BoardControls Card it sits under);
  // the other placements are plain rows.
  const Root = placement === 'mid' ? Card : 'div';
  return (
    <Root
      data-testid="analysis-explain-bar"
      data-state={state}
      data-orientation={orientation}
      data-placement={placement}
      className={cn('flex shrink-0 items-center gap-2', PLACEMENT_CLASS[placement])}
    >
      {children}
    </Root>
  );
}

/**
 * Same headline in both states, so it stays put when a line opens or closes.
 *
 * One inline text flow: move, badge and colon, then the tactics on the same first line,
 * wrapping under the move. At most two lines; normal wrapping only breaks at spaces and
 * after hyphens ("discovered-|attack"), and line-clamp ellipsizes the rest.
 * leading-tight!: the unlayered mobile .text-sm bump in index.css (line-height 1.5rem)
 * otherwise beats the utility, and two 24px lines outgrow the button row. max-h-10: the
 * mono move's font metrics add ~1px to the line box, which would make the row taller
 * than the button height.
 */
function Headline({ headline }: { headline: ExplainHeadline }): ReactElement {
  return (
    <span
      data-testid="analysis-explain-headline"
      data-severity={headline.severity}
      className="line-clamp-2 max-h-10 min-w-0 flex-1 text-sm leading-tight!"
    >
      {/* nowrap: the move, its badge and the colon always stay together on line one. */}
      <span className="whitespace-nowrap">
        <span
          data-testid="analysis-explain-headline-text"
          className={cn(headline.san !== null && 'font-mono font-bold text-foreground')}
        >
          {headline.san ?? SEVERITY_NOUN[headline.severity]}
        </span>
        <MoveQualityIcon quality={headline.severity} className="ml-1.5 inline-block size-4 align-text-bottom" />
        {headline.tactics.length > 0 && ':'}
      </span>
      {headline.tactics.length > 0 && ' '}
      <TacticText tactics={headline.tactics} />
    </span>
  );
}

export function ExplainBar({
  state,
  onOpenLine,
  onGotIt,
  stepper,
  placement,
}: ExplainBarProps): ReactElement | null {
  if (state.kind === 'hidden') return null;
  if (state.kind === 'got-it') {
    return (
      <BarShell state="got-it" orientation={state.line.orientation} placement={placement}>
        {/* No headline (no mistake/blunder marker at the line's ply): a spacer keeps the
            stepper and Got it on the right. */}
        {state.headline !== null ? <Headline headline={state.headline} /> : <span className="flex-1" />}
        <LineStepper stepper={stepper} />
        <Button type="button" variant="brand-outline" size="lg" data-testid="btn-analysis-explain-got-it" onClick={onGotIt}>
          {GOT_IT_LABEL}
        </Button>
      </BarShell>
    );
  }
  return (
    <BarShell state="explain" placement={placement}>
      <Headline headline={state} />
      {LINE_ORDER.map((orientation) => (
        <LineButton
          key={orientation}
          orientation={orientation}
          disabled={state.pending !== null || !state.usable[orientation]}
          busy={state.pending === orientation}
          onOpenLine={onOpenLine}
        />
      ))}
    </BarShell>
  );
}
