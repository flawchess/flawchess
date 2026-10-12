import { Card, CardBody } from '@/components/ui/card';
import { SEV_BLUNDER, SEV_MISTAKE } from '@/lib/theme';
import {
  FLAW_GAP_META,
  flawBulletToGapCell,
  libraryBasisText,
} from '@/lib/flawComparisonMeta';
import { GapBar, GapGateSlot } from './GapBar';
import { GapPopover } from './GapPopover';
import type { FlawComparisonTc } from '@/types/library';

type TileMetric = 'blunder' | 'mistake';

const TILE_METRICS: readonly TileMetric[] = ['blunder', 'mistake'];
const TILE_COLORS: Record<TileMetric, string> = {
  blunder: SEV_BLUNDER,
  mistake: SEV_MISTAKE,
};
const RATE_DECIMALS = 2;
const COPY_NO_RATE = '—';

function formatRate(rate: number | null): string {
  return rate === null ? COPY_NO_RATE : rate.toFixed(RATE_DECIMALS);
}

interface FlawTileProps {
  metric: TileMetric;
  tcStats: FlawComparisonTc;
  analyzedGate: number;
}

/**
 * One headline tile (D-00e): the player's rate big in the severity colour, the opponents'
 * rate under it, then the gap bar with its Search popover (D-00a to D-00c). Below the
 * analyzed-games gate the numbers stay and the bar slot reads the gate line (D-03).
 * Tiles are never faded (research open question 4: D-12 fades tactic cells and context
 * rows only).
 */
function FlawTile({ metric, tcStats, analyzedGate }: FlawTileProps) {
  const bullet = tcStats.bullets.find((b) => b.tag === metric);
  if (!bullet) return null;

  const meta = FLAW_GAP_META[metric];
  const cell = flawBulletToGapCell(bullet);
  const testId = `flaw-tile-${metric}`;

  return (
    <Card data-testid={testId}>
      <CardBody className="flex flex-col gap-2">
        <div>
          <div
            className="font-brand text-3xl font-medium leading-tight tabular-nums"
            style={{ color: TILE_COLORS[metric] }}
            data-testid={`${testId}-rate`}
          >
            {formatRate(bullet.player_rate)}
          </div>
          <div className="text-sm font-bold uppercase tracking-wide text-muted-foreground">
            {meta.label} / 100 moves
          </div>
        </div>
        <div className="text-sm text-muted-foreground" data-testid={`${testId}-opponents`}>
          Opponents {formatRate(bullet.opp_rate)}
        </div>
        {tcStats.below_gate ? (
          <GapGateSlot
            analyzedN={tcStats.analyzed_n}
            gate={analyzedGate}
            testId={`${testId}-gate`}
          />
        ) : (
          <GapBar
            cell={cell}
            testId={`${testId}-bar`}
            trailing={
              <GapPopover
                testId={`gap-popover-${metric}-tc-${tcStats.tc}`}
                label={meta.label}
                definition={meta.definition}
                unit="per 100 moves"
                noun={meta.noun}
                basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)}
                cell={cell}
              />
            }
          />
        )}
      </CardBody>
    </Card>
  );
}

interface FlawTilesProps {
  /** The selected time control's comparison entry. */
  tcStats: FlawComparisonTc;
  analyzedGate: number;
}

/** The Blunders and Mistakes tiles of the Flaw Stats section (no Inaccuracies tile, D-00e). */
export function FlawTiles({ tcStats, analyzedGate }: FlawTilesProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" data-testid="flaw-tiles">
      {TILE_METRICS.map((metric) => (
        <FlawTile key={metric} metric={metric} tcStats={tcStats} analyzedGate={analyzedGate} />
      ))}
    </div>
  );
}
