/**
 * ExplainBar — the contextual flaw bar (SEED-208) under the move list. Presentational
 * only; state comes from `useExplainBar`, and Umami tracking lives in that hook's click
 * handlers.
 *
 * Phase 245 UAT replaced the single Explain button with two named lines:
 *   - Best: undo the mistake and play the better move (the MISSED line).
 *   - Punish: the refutation of the mistake (the ALLOWED line).
 * One row: the headline (move and severity badge, as in the move list) or, inside a
 * line, a line stepper, then the buttons. Tactic chips live in the move list only.
 * Copy is neutral (never "your move"): `is_user` is the game OWNER and the viewer may
 * be someone else.
 */

import type { ReactElement, ReactNode } from 'react';
import { Check, ChevronLeft, ChevronRight, Star, Swords } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { MoveQualityIcon } from '@/components/icons/MoveQualityIcon';
import {
  otherOrientation,
  type ExplainBarState,
  type ExplainOrientation,
  type ExplainSeverity,
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

const GOT_IT_LABEL = 'Got it';

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
    <div data-testid="analysis-explain-stepper" className="flex min-w-0 flex-1 items-center gap-1">
      <Button
        type="button"
        variant="brand-outline"
        size="icon-lg"
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

export function ExplainBar({
  state,
  onOpenLine,
  onGotIt,
  stepper,
  placement,
}: ExplainBarProps): ReactElement | null {
  if (state.kind === 'hidden') return null;
  if (state.kind === 'got-it') {
    const other = otherOrientation(state.line.orientation);
    return (
      <BarShell state="got-it" orientation={state.line.orientation} placement={placement}>
        <LineStepper stepper={stepper} />
        <LineButton orientation={other} disabled={!state.otherUsable} busy={false} onOpenLine={onOpenLine} />
        <Button type="button" variant="brand-outline" size="lg" data-testid="btn-analysis-explain-got-it" onClick={onGotIt}>
          <Check data-icon="inline-start" aria-hidden="true" />
          {GOT_IT_LABEL}
        </Button>
      </BarShell>
    );
  }
  return (
    <BarShell state="explain" placement={placement}>
      {/* Move then badge, as in the move list. */}
      <span
        data-testid="analysis-explain-headline"
        data-severity={state.severity}
        className="flex min-w-0 flex-1 items-center gap-1.5 text-sm"
      >
        <span
          data-testid="analysis-explain-headline-text"
          className={cn('truncate', state.san !== null && 'font-mono font-bold text-foreground')}
        >
          {state.san ?? SEVERITY_NOUN[state.severity]}
        </span>
        <MoveQualityIcon quality={state.severity} className="size-4 shrink-0" />
      </span>
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
