/**
 * Shared confidence pill component used by:
 *  - OpeningFindingCard (Phase 75/76 — score-confidence refactor)
 *  - MostPlayedOpeningsTable (Phase 80 — eval-confidence, MG and EG columns)
 *
 * Renders a Tooltip-wrapped span showing 'low' | 'medium' | 'high' level text.
 * The ConfidenceTooltipContent handles the statistical breakdown in the tooltip body.
 */

import type { ReactElement } from 'react';
import { Tooltip } from '@/components/ui/tooltip';
import { ConfidenceTooltipContent } from '@/components/insights/ConfidenceTooltipContent';

interface ConfidencePillProps {
  /** Confidence level to display. */
  level: 'low' | 'medium' | 'high';
  /** p-value from the statistical test (passed to tooltip). */
  pValue?: number | null;
  /** Score value (0-1 range, passed to tooltip for OpeningFindingCard context). */
  score?: number | null;
  /** Game count used in the test (passed to tooltip). */
  gameCount?: number | null;
  /**
   * Average eval at phase entry in pawns (signed, user perspective).
   * When provided, the tooltip renders eval-context language instead of
   * WDL score/strength/weakness language.
   */
  evalMeanPawns?: number | null;
  /** Optional data-testid for the pill span. */
  testId?: string;
}

export function ConfidencePill({
  level,
  pValue = null,
  score = null,
  gameCount = null,
  evalMeanPawns,
  testId,
}: ConfidencePillProps): ReactElement {
  return (
    <Tooltip
      content={
        <ConfidenceTooltipContent
          level={level}
          pValue={pValue ?? 1}
          score={score ?? 0.5}
          gameCount={gameCount ?? 0}
          evalMeanPawns={evalMeanPawns}
        />
      }
    >
      <span className="font-medium" data-testid={testId}>
        {level}
      </span>
    </Tooltip>
  );
}
