/**
 * ExplainBar — the contextual Explain bar (SEED-208): one headline and one
 * button under the move list. Presentational only; state comes from
 * `useExplainBar`, and Umami tracking lives in that hook's click handlers.
 *
 * D-01/D-02: exactly one button and static label copy, no coach prose.
 * Copy is neutral (never "your move"): `is_user` is the game OWNER and the
 * viewer may be someone else.
 */

import type { ReactElement, ReactNode } from 'react';
import { Check, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { SEVERITY_GLYPH } from '@/lib/severityGlyph';
import type { ExplainBarState, ExplainSeverity } from '@/lib/explainBar';

type ExplainBarPlacement = 'desktop';

const PLACEMENT_CLASS: Record<ExplainBarPlacement, string> = {
  desktop: 'border-t border-border px-2 py-2',
};

const EXPLAIN_LABEL = 'Explain';
const SEVERITY_SUFFIX: Record<ExplainSeverity, string> = {
  blunder: ' is a blunder',
  mistake: ' is a mistake',
};
const SEVERITY_NOUN: Record<ExplainSeverity, string> = {
  blunder: ' Blunder',
  mistake: ' Mistake',
};

const GOT_IT_LABEL = 'Got it';
const GOT_IT_PREFIX: Record<LineOrientation, string> = { missed: 'Better than', allowed: 'Punishing' };
const GOT_IT_FALLBACK: Record<LineOrientation, string> = { missed: 'Better line', allowed: 'Refutation' };

type LineOrientation = 'missed' | 'allowed';

type ExplainBarProps = {
  state: ExplainBarState;
  onExplain: () => void;
  onGotIt: () => void;
  placement: ExplainBarPlacement;
};

type BarShellProps = {
  state: 'explain' | 'got-it';
  orientation: LineOrientation;
  placement: ExplainBarPlacement;
  children: ReactNode;
};

/** Same root, classes and row structure for both states, so the Explain/Got it swap never shifts the row height. */
function BarShell({ state, orientation, placement, children }: BarShellProps): ReactElement {
  return (
    <div
      data-testid="analysis-explain-bar"
      data-state={state}
      data-orientation={orientation}
      data-placement={placement}
      className={cn('flex shrink-0 items-center gap-2', PLACEMENT_CLASS[placement])}
    >
      {children}
    </div>
  );
}

export function ExplainBar({ state, onExplain, onGotIt, placement }: ExplainBarProps): ReactElement | null {
  if (state.kind === 'hidden') return null;
  if (state.kind === 'got-it') {
    return (
      <BarShell state="got-it" orientation={state.line.orientation} placement={placement}>
        <span data-testid="analysis-explain-headline" className="min-w-0 flex-1 truncate text-sm">
          {state.san !== null ? (
            <>
              <span className="text-muted-foreground">{GOT_IT_PREFIX[state.line.orientation]} </span>
              <span className="font-mono font-bold text-foreground">{state.san}</span>
            </>
          ) : (
            <span className="text-muted-foreground">{GOT_IT_FALLBACK[state.line.orientation]}</span>
          )}
        </span>
        <Button
          type="button"
          variant="brand-outline"
          size="lg"
          data-testid="btn-analysis-explain-got-it"
          onClick={onGotIt}
        >
          <Check data-icon="inline-start" aria-hidden="true" />
          {GOT_IT_LABEL}
        </Button>
      </BarShell>
    );
  }
  const glyph = SEVERITY_GLYPH[state.severity];
  return (
    <BarShell state="explain" orientation={state.flaw.orientation} placement={placement}>
      <span data-testid="analysis-explain-headline" className="min-w-0 flex-1 truncate text-sm">
        <span className="font-mono font-bold" style={{ color: glyph.color }}>
          {state.san ?? ''}
          {glyph.symbol}
        </span>
        {state.san !== null ? SEVERITY_SUFFIX[state.severity] : SEVERITY_NOUN[state.severity]}
      </span>
      <Button
        type="button"
        variant="default"
        size="lg"
        data-testid="btn-analysis-explain"
        disabled={state.pending}
        aria-busy={state.pending || undefined}
        onClick={onExplain}
      >
        <Lightbulb data-icon="inline-start" aria-hidden="true" />
        {EXPLAIN_LABEL}
      </Button>
    </BarShell>
  );
}
