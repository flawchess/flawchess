/**
 * Shared confidence pill for WDL-context findings (binomial-style test against
 * 50% baseline). Used by:
 *  - OpeningFindingCard (Phase 75/76 — score-confidence refactor)
 *  - move-explorer confidence column (via Tooltip)
 *
 * The eval-context counterpart lives in BulletConfidencePopover, which renders
 * EvalConfidenceTooltip directly.
 */

import type { ReactElement } from 'react';
import { Tooltip } from '@/components/ui/tooltip';
import { WdlConfidenceTooltip } from '@/components/insights/WdlConfidenceTooltip';

interface ConfidencePillProps {
  /** Confidence level to display. */
  level: 'low' | 'medium' | 'high';
  /** p-value from the statistical test. */
  pValue?: number | null;
  /** Score value (0-1 range). */
  score?: number | null;
  /** Game count used in the test. */
  gameCount?: number | null;
  /** Optional data-testid for the pill span. */
  testId?: string;
}

export function ConfidencePill({
  level,
  pValue = null,
  score = null,
  gameCount = null,
  testId,
}: ConfidencePillProps): ReactElement {
  return (
    <Tooltip
      content={
        <WdlConfidenceTooltip
          level={level}
          pValue={pValue ?? 1}
          score={score ?? 0.5}
          gameCount={gameCount ?? 0}
        />
      }
    >
      <span className="font-medium" data-testid={testId}>
        {level}
      </span>
    </Tooltip>
  );
}
