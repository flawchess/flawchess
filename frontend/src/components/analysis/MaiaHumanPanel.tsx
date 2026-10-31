/**
 * MaiaHumanPanel — the "human" surface bundle for the analysis page: a charcoal
 * Card whose header reads "<User> Maia, Human Move Probability <info>"
 * and whose body holds the Moves-by-Rating chart (the ELO slider lives outside the
 * card on desktop — it drives both engines, not just Maia).
 *
 * The header info tooltip carries the compact Maia attribution: it links to the
 * maia3 source repo (the AGPL offer-source, in shortened form) and to maiachess.com.
 * The formal AGPL-3.0 notice lives in the README/LICENSE.
 *
 * Reused by the desktop/mid layout (DesktopMaiaPanel) and the mobile Maia tab
 * (HumanTab).
 */
import { User } from 'lucide-react';
import { MovesByRatingChart } from '@/components/analysis/MovesByRatingChart';
import type { MoveQualityEval, EngineLine } from '@/components/analysis/MovesByRatingChart';
import { MaiaMoveQualityBar } from '@/components/analysis/MaiaMoveQualityBar';
import { useEngineUnsupportedNotice } from '@/components/analysis/EngineUnsupportedNotice';
import type { HoveredQualityMove } from '@/components/analysis/MaiaMoveQualityBar';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { InfoPopover } from '@/components/ui/info-popover';
import { MAIA_ACCENT } from '@/lib/theme';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import type { MoverColor } from '@/lib/liveFlaw';
import { onlyGoodMoveSan } from '@/lib/gemMove';

const MAIA_SOURCE_URL = 'https://github.com/CSSLab/maia3';
const MAIA_SITE_URL = 'https://maiachess.com';

export interface MaiaHumanPanelProps {
  /** Current "you are here" ELO (useMaiaEloDefault's selectedElo). The ELO slider
   *  itself lives outside this card on desktop — it drives both the FlawChess and
   *  Maia engines, so it doesn't belong inside the Maia card. */
  selectedElo: number;
  /** useMaiaEngine's perElo verbatim — [] renders the chart's own waiting placeholder. */
  perElo: MoveCurvePoint[];
  /**
   * useMaiaEngine's isLadderComplete. Passed to
   * `MaiaMoveQualityBar` ONLY — that component freezes its verdict/buckets on
   * this flag; `MovesByRatingChart` stays ungated and paints from whatever
   * `perElo` holds.
   */
  isLadderComplete: boolean;
  playedSan: string | null;
  bestSan: string | null;
  /** Analysis.tsx's selectCandidatesByMass output — the exact candidate set to render. */
  shownSans: string[];
  /** Analysis.tsx's classifyMoveQuality output merged with grading evals, keyed by SAN. */
  qualityBySan: Map<string, MoveQualityEval>;
  /** Side to move at this position (sideToMoveFromFen) — threaded into MaiaMoveQualityBar so its
   *  prose can re-sign white-POV evals to the addressed player's frame. */
  mover: MoverColor;
  /** Primary engine's top PV lines (best + 2nd-best) for the tooltip's engine-reference header. */
  engineTopLines: EngineLine[];
  /** Fired with the move-quality bar's hovered segment moves so the page can draw board arrows. */
  onHoverMovesChange?: (moves: HoveredQualityMove[] | null) => void;
  /** Plays a named prose move (from the move-quality bar's position verdict) as a
   *  free move on the board. */
  onPlayMove?: (san: string) => void;
  /** True when the analysed position is the opponent's move — frames the verdict prose around
   *  the opponent rather than "you". */
  isOpponentToMove?: boolean;
  className?: string;
  /** Mobile compact mode: use a shorter chart to reclaim vertical space.
   * The header matches desktop (full title + info tooltip); it is dropped
   * only when compact AND no toggle is wired. */
  compact?: boolean;
  /**
   * The header toggle Switch's checked state. Provided
   * together with `onToggleEnabled` from Analysis.tsx's `maiaEnabled` state.
   * When BOTH are omitted, the header renders without a switch (and, in
   * `compact` mode, without a header row).
   */
  enabled?: boolean;
  /** Fired when the header Switch is toggled — wire directly to `setMaiaEnabled`. */
  onToggleEnabled?: (enabled: boolean) => void;
  /**
   * Optional footer rendered at the bottom of the card body: on mobile the
   * shared ELO slider lives inside each card, so the Maia tab passes it here. On
   * desktop the slider sits between the cards instead, so this is omitted.
   */
  footer?: React.ReactNode;
}

/** Shorter chart on mobile (compact); desktop keeps MovesByRatingChart's default. */
const COMPACT_CHART_HEIGHT_CLASS = 'h-48';

/** Header info tooltip: what the chart shows + compact Maia attribution. */
function MaiaInfoTooltip(): React.ReactElement {
  return (
    <InfoPopover ariaLabel="About human-move predictions" testId="maia-info-popover">
      <div className="max-w-xs space-y-2">
        <p>
          This chart shows how often real players at each rating actually pick each
          move in this position — the human choice, not the engine's best move. Every
          curve traces one candidate move, so you can see its popularity rise or fall
          as players get stronger, and read off what a player at your level would most
          likely play.
        </p>
        <p>
          When the best move is the only good one, its line changes color with rating:
          violet (gem) where at most 30% of players at that rating would find it, blue
          (great) up to 70%, and green (best) above that.
        </p>
        <p>
          Predictions come from{' '}
          <a
            href={MAIA_SOURCE_URL}
            data-umami-event="outbound-maia-model"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="maia-info-link-maia3"
            className="underline"
          >
            maia3
          </a>
          , a neural network trained on millions of human games. Check out{' '}
          <a
            href={MAIA_SITE_URL}
            data-umami-event="outbound-maia-site"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="maia-info-link-maiachess"
            className="underline"
          >
            maiachess.com
          </a>
          .
        </p>
      </div>
    </InfoPopover>
  );
}

export function MaiaHumanPanel({
  selectedElo,
  perElo,
  isLadderComplete,
  playedSan,
  bestSan,
  shownSans,
  qualityBySan,
  mover,
  engineTopLines,
  onHoverMovesChange,
  isOpponentToMove = false,
  onPlayMove,
  className,
  compact = false,
  enabled,
  onToggleEnabled,
  footer,
}: MaiaHumanPanelProps): React.ReactElement {
  // The header Switch only renders when the caller wires both
  // enabled/onToggleEnabled (Analysis.tsx always does) — omitting them keeps the
  // "compact drops the header" behavior.
  const showToggle = onToggleEnabled !== undefined;
  // On a device that can never start Maia (no WASM SIMD)
  // the chart's skeleton would pulse forever — say why instead.
  const unsupportedNotice = useEngineUnsupportedNotice('maia');
  const toggleSwitch = showToggle && (
    <Switch
      checked={enabled ?? true}
      onCheckedChange={onToggleEnabled}
      aria-label="Toggle Maia"
      data-testid="btn-analysis-maia-toggle"
      style={enabled ? { backgroundColor: MAIA_ACCENT } : undefined}
    />
  );
  return (
    <Card className={className} data-testid="maia-human-panel">
      {/* Violet header pairs with the violet Maia eval bar. Rendered
          identically on desktop and mobile — full title + info tooltip (the mobile
          "Maia" tab shows the same header + tooltip as desktop). Dropped when
          compact AND no toggle is wired. */}
      {(!compact || showToggle) && (
        <CardHeader size="compact" data-testid="maia-human-header" style={{ color: MAIA_ACCENT }}>
          {toggleSwitch}
          {!compact && <User aria-hidden="true" className="h-4 w-4" />}
          <span>Maia, Human Move Probability</span>
          <MaiaInfoTooltip />
        </CardHeader>
      )}
      {/* The ELO slider sits between this card and the FlawChess card on desktop; on
          mobile the caller passes it as `footer` so it lives inside the card. */}
      <CardBody className="flex flex-col gap-3 p-3">
        {unsupportedNotice ?? (
          <>
            <MovesByRatingChart
              perElo={perElo}
              playedSan={playedSan}
              bestSan={bestSan}
              selectedElo={selectedElo}
              shownSans={shownSans}
              qualityBySan={qualityBySan}
              engineTopLines={engineTopLines}
              tieredSan={onlyGoodMoveSan(qualityBySan, bestSan, mover)}
              heightClass={compact ? COMPACT_CHART_HEIGHT_CLASS : undefined}
            />
            {/* Move-quality bar below the chart: the shown
                candidates' Maia mass split by Stockfish-graded severity. */}
            <MaiaMoveQualityBar
              perElo={perElo}
              isLadderComplete={isLadderComplete}
              selectedElo={selectedElo}
              shownSans={shownSans}
              qualityBySan={qualityBySan}
              mover={mover}
              onHoverMovesChange={onHoverMovesChange}
              isOpponentToMove={isOpponentToMove}
              onPlayMove={onPlayMove}
            />
          </>
        )}
        {footer}
      </CardBody>
    </Card>
  );
}
