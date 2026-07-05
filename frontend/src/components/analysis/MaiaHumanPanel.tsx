/**
 * MaiaHumanPanel — the "human" surface bundle for the analysis page (Phase 151 Plan 06,
 * D-01/D-03): a charcoal Card whose header reads "<User> Maia - Human Move Probability <info>"
 * and whose body holds the interactive ELO selector + the Moves-by-Rating chart.
 *
 * The header info tooltip carries the compact Maia attribution (UAT quick 260705-bm3):
 * it links to the maia3 source repo (the AGPL offer-source, in shortened form) and to
 * maiachess.com. This replaced the always-visible MaiaAttribution legal box (removed in
 * the same UAT) — the formal AGPL-3.0 notice lives in the README/LICENSE.
 *
 * Extracted into its own component (rather than inlined helper-const JSX like
 * Analysis.tsx's `boardRow`/`variationTree`) because it is reused across THREE surfaces
 * — the desktop left column, the mobile game-mode "Human" tab, and the mobile free-play
 * "Human" tab — keeping all three call sites one line instead of tripling this JSX.
 */
import { User } from 'lucide-react';
import { EloSelector } from '@/components/analysis/EloSelector';
import { MovesByRatingChart } from '@/components/analysis/MovesByRatingChart';
import type { MoveQualityEval, EngineLine } from '@/components/analysis/MovesByRatingChart';
import { MaiaMoveQualityBar } from '@/components/analysis/MaiaMoveQualityBar';
import type { HoveredQualityMove } from '@/components/analysis/MaiaMoveQualityBar';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { InfoPopover } from '@/components/ui/info-popover';
import { MAIA_ACCENT } from '@/lib/theme';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';

const MAIA_SOURCE_URL = 'https://github.com/CSSLab/maia3';
const MAIA_SITE_URL = 'https://maiachess.com';

export interface MaiaHumanPanelProps {
  /** Current "you are here" ELO (useMaiaEloDefault's selectedElo). */
  selectedElo: number;
  /** Fired when the user drags the ELO selector (useMaiaEloDefault's setSelectedElo). */
  onEloChange: (elo: number) => void;
  /** useMaiaEngine's perElo verbatim — [] renders the chart's own waiting placeholder. */
  perElo: MoveCurvePoint[];
  playedSan: string | null;
  bestSan: string | null;
  /** Analysis.tsx's selectCandidatesByMass output — the exact candidate set to render (Phase 151.1). */
  shownSans: string[];
  /** Analysis.tsx's classifyMoveQuality output merged with grading evals, keyed by SAN (Phase 151.1, D-08). */
  qualityBySan: Map<string, MoveQualityEval>;
  /** Primary engine's top PV lines (best + 2nd-best) for the tooltip's engine-reference header (151.1 UAT). */
  engineTopLines: EngineLine[];
  /** Fired with the move-quality bar's hovered segment moves so the page can draw board arrows (quick 260705-kfg). */
  onHoverMovesChange?: (moves: HoveredQualityMove[] | null) => void;
  /** Plays a named prose move (from the move-quality bar's position verdict) as a
   *  free move on the board (quick 260705-mth). */
  onPlayMove?: (san: string) => void;
  /** True when the analysed position is the opponent's move — frames the verdict prose around
   *  the opponent rather than "you" (quick 260705-m3z). */
  isOpponentToMove?: boolean;
  className?: string;
  /** Mobile compact mode (151.1 UAT): drop the card header and use a shorter chart to
   * reclaim vertical space — the mobile "Maia" tab is already labeled by its tab. */
  compact?: boolean;
}

/** Shorter chart on mobile (compact); desktop keeps MovesByRatingChart's default. */
const COMPACT_CHART_HEIGHT_CLASS = 'h-48';

/** Compact Maia attribution shown in the header info tooltip (UAT quick 260705-bm3). */
function MaiaInfoTooltip(): React.ReactElement {
  return (
    <InfoPopover ariaLabel="About human-move predictions" testId="maia-info-popover">
      <p className="max-w-xs">
        Human-move predictions are based on{' '}
        <a
          href={MAIA_SOURCE_URL}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="maia-info-link-maia3"
          className="underline"
        >
          maia3
        </a>
        . Check out{' '}
        <a
          href={MAIA_SITE_URL}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="maia-info-link-maiachess"
          className="underline"
        >
          maiachess.com
        </a>
        .
      </p>
    </InfoPopover>
  );
}

export function MaiaHumanPanel({
  selectedElo,
  onEloChange,
  perElo,
  playedSan,
  bestSan,
  shownSans,
  qualityBySan,
  engineTopLines,
  onHoverMovesChange,
  isOpponentToMove = false,
  onPlayMove,
  className,
  compact = false,
}: MaiaHumanPanelProps): React.ReactElement {
  return (
    <Card className={className} data-testid="maia-human-panel">
      {/* Violet header pairs with the violet Maia eval bar (151.1 UAT). Dropped on
          mobile (compact) — the "Maia" tab already names the surface. */}
      {!compact && (
        <CardHeader size="compact" data-testid="maia-human-header" style={{ color: MAIA_ACCENT }}>
          <User aria-hidden="true" className="h-4 w-4" />
          <span>Maia - Human Move Probability</span>
          <MaiaInfoTooltip />
        </CardHeader>
      )}
      {/* ELO slider sits BELOW the chart (151.1 UAT). */}
      <CardBody className="flex flex-col gap-3 p-3">
        <MovesByRatingChart
          perElo={perElo}
          playedSan={playedSan}
          bestSan={bestSan}
          selectedElo={selectedElo}
          shownSans={shownSans}
          qualityBySan={qualityBySan}
          engineTopLines={engineTopLines}
          heightClass={compact ? COMPACT_CHART_HEIGHT_CLASS : undefined}
        />
        <EloSelector value={selectedElo} onChange={onEloChange} />
        {/* Move-quality bar below the chart + slider (quick 260705-kfg): the shown
            candidates' Maia mass split by Stockfish-graded severity. */}
        <MaiaMoveQualityBar
          perElo={perElo}
          selectedElo={selectedElo}
          shownSans={shownSans}
          qualityBySan={qualityBySan}
          onHoverMovesChange={onHoverMovesChange}
          isOpponentToMove={isOpponentToMove}
          onPlayMove={onPlayMove}
        />
      </CardBody>
    </Card>
  );
}
