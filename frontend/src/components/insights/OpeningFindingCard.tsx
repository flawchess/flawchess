// Stub for OpeningFindingCard — will be replaced by Plan 04 output.
// Plan 05 runs in parallel and needs a compilable import target.
import type { OpeningInsightFinding } from '@/types/insights';

interface OpeningFindingCardProps {
  finding: OpeningInsightFinding;
  idx: number;
  onFindingClick: (finding: OpeningInsightFinding) => void;
}

export function OpeningFindingCard({ finding, idx, onFindingClick }: OpeningFindingCardProps) {
  return (
    <div
      data-testid={`opening-finding-card-${idx}`}
      onClick={() => onFindingClick(finding)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onFindingClick(finding); }}
    >
      {finding.display_name}
    </div>
  );
}
