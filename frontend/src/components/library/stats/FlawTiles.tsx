import type { ReactNode } from 'react';
import { Card, CardBody } from '@/components/ui/card';
import { InfoPopover } from '@/components/ui/info-popover';
import { LoadError } from '@/components/ui/load-error';
import { FACEPALM_CARD_INFO } from '@/lib/facepalm';
import { MoveQualityIcon } from '@/components/icons/MoveQualityIcon';
import { FacepalmBlunderIcon } from '@/components/icons/SeverityGlyphIcon';
import { FACEPALM_BAND_SWATCH, SEV_BLUNDER } from '@/lib/theme';
import {
  FACEPALM_GAP_META,
  FLAW_GAP_META,
  facepalmMetricCell,
  flawBulletToGapCell,
  libraryBasisText,
} from '@/lib/flawComparisonMeta';
import type { GapCell } from '@/lib/gapBar';
import { facepalmRangeNote } from './facepalmRangeNote';
import { GapBar, GapGateSlot } from './GapBar';
import { GapPopover } from './GapPopover';
import type { FacepalmBullet, FlawComparisonTc } from '@/types/library';

const RATE_DECIMALS = 2;
const COPY_NO_RATE = '—';
const TILE_ICON_CLASS = 'h-7 w-7 shrink-0';
const TILE_SKELETON_CLASS = 'h-28 animate-pulse rounded border border-border bg-charcoal';

function formatRate(rate: number | null): string {
  return rate === null ? COPY_NO_RATE : rate.toFixed(RATE_DECIMALS);
}

interface FlawTileFrameProps {
  testId: string;
  icon: ReactNode;
  color: string;
  label: string;
  cell: GapCell;
  tcStats: FlawComparisonTc;
  analyzedGate: number;
  popover: ReactNode;
  /** Optional info popover right of the label, for a metric that needs explaining. */
  info?: ReactNode;
}

/**
 * One headline tile: the player's rate big in the tile colour, the opponents' rate under it,
 * then the gap bar with its popover. Below the analyzed-games gate the numbers stay and the
 * bar slot reads the gate line.
 */
function FlawTileFrame({
  testId,
  icon,
  color,
  label,
  cell,
  tcStats,
  analyzedGate,
  popover,
  info,
}: FlawTileFrameProps) {
  const opponents = (
    <div className="text-sm text-muted-foreground" data-testid={`${testId}-opponents`}>
      Opponents {formatRate(cell.oppRate)}
    </div>
  );

  return (
    <Card data-testid={testId}>
      <CardBody className="flex flex-col gap-2">
        <div>
          <div className="flex items-center gap-2">
            {icon}
            <div
              className="text-3xl font-bold leading-tight tabular-nums"
              style={{ color }}
              data-testid={`${testId}-rate`}
            >
              {formatRate(cell.youRate)}
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-sm font-bold text-muted-foreground">
            {label} / 100 moves
            {info}
          </div>
        </div>
        {tcStats.below_gate ? (
          <>
            {opponents}
            <GapGateSlot analyzedN={tcStats.analyzed_n} gate={analyzedGate} testId={`${testId}-gate`} />
          </>
        ) : (
          <GapBar cell={cell} testId={`${testId}-bar`} leading={opponents} trailing={popover} />
        )}
      </CardBody>
    </Card>
  );
}

interface TileProps {
  tcStats: FlawComparisonTc;
  analyzedGate: number;
}

/** The Blunders tile. The verdict follows the same 99% significance gate as every other gap. */
function BlunderTile({ tcStats, analyzedGate }: TileProps) {
  const bullet = tcStats.bullets.find((b) => b.tag === 'blunder');
  if (!bullet) return null;
  const meta = FLAW_GAP_META.blunder;
  const cell = flawBulletToGapCell(bullet);
  return (
    <FlawTileFrame
      testId="flaw-tile-blunder"
      icon={<MoveQualityIcon quality="blunder" className={TILE_ICON_CLASS} />}
      color={SEV_BLUNDER}
      label={meta.label}
      cell={cell}
      tcStats={tcStats}
      analyzedGate={analyzedGate}
      popover={
        <GapPopover
          testId={`gap-popover-blunder-tc-${tcStats.tc}`}
          label={meta.label}
          definition={meta.definition}
          unit="per 100 moves"
          noun={meta.noun}
          basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)}
          cell={cell}
        />
      }
    />
  );
}

interface FacepalmTileProps extends TileProps {
  /** The selected TC's rows from /facepalm-comparison; undefined while that request loads. */
  bullets: readonly FacepalmBullet[] | undefined;
  isError: boolean;
}

/**
 * The Facepalm blunders tile: the total row of the Facepalm blunders card as a headline tile.
 * Neutral like that row (no band, no verdict, D-16), and it loads and fails on its own request
 * (D-21) without holding the Blunders tile.
 */
function FacepalmTile({ tcStats, analyzedGate, bullets, isError }: FacepalmTileProps) {
  if (isError) {
    return (
      <Card data-testid="flaw-tile-facepalm">
        <CardBody>
          <LoadError resource="facepalm blunders" />
        </CardBody>
      </Card>
    );
  }
  if (!bullets) return <div className={TILE_SKELETON_CLASS} data-testid="flaw-tile-facepalm-loading" />;
  const cell = facepalmMetricCell(bullets, 'facepalm');
  if (!cell) return null;
  const meta = FACEPALM_GAP_META.facepalm;
  return (
    <FlawTileFrame
      testId="flaw-tile-facepalm"
      icon={<FacepalmBlunderIcon className={TILE_ICON_CLASS} aria-hidden="true" />}
      color={FACEPALM_BAND_SWATCH}
      label={meta.label}
      cell={cell}
      tcStats={tcStats}
      analyzedGate={analyzedGate}
      info={
        <InfoPopover ariaLabel="About facepalm blunders" testId="flaw-tile-facepalm-info">
          <p>{FACEPALM_CARD_INFO}</p>
        </InfoPopover>
      }
      popover={
        cell.delta === null ? undefined : (
          // "tile" keeps this testid apart from the card row's popover of the same metric.
          <GapPopover
            testId={`gap-popover-facepalm-tile-tc-${tcStats.tc}`}
            label={meta.label}
            definition={meta.definition}
            unit="per 100 moves"
            noun={meta.noun}
            basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)}
            cell={cell}
            omitDirection
            rangeNote={facepalmRangeNote(cell)}
          />
        )
      }
    />
  );
}

interface FlawTilesProps {
  /** The selected time control's comparison entry. */
  tcStats: FlawComparisonTc;
  analyzedGate: number;
  /** The selected TC's facepalm rows; undefined while /facepalm-comparison loads. */
  facepalmBullets: readonly FacepalmBullet[] | undefined;
  facepalmError: boolean;
}

/**
 * The Blunders (left) and Facepalm blunders (right) tiles of the Flaw Stats section. The
 * familiar metric leads; the facepalm tile follows as its subset, with an info popover.
 */
export function FlawTiles({ tcStats, analyzedGate, facepalmBullets, facepalmError }: FlawTilesProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" data-testid="flaw-tiles">
      <BlunderTile tcStats={tcStats} analyzedGate={analyzedGate} />
      <FacepalmTile
        tcStats={tcStats}
        analyzedGate={analyzedGate}
        bullets={facepalmBullets}
        isError={facepalmError}
      />
    </div>
  );
}
