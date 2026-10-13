import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { libraryBasisText } from '@/lib/flawComparisonMeta';
import {
  LIBRARY_STATS_TACTIC_FAMILIES,
  TACTIC_COMPARISON_FAMILIES,
  tacticBulletToGapCell,
  tacticSideCopy,
  tacticTestIdSegment,
  type TacticFamilyDef,
} from '@/lib/tacticComparisonMeta';
import { cn } from '@/lib/utils';
import { GapBar } from './GapBar';
import { GapPopover } from './GapPopover';
import type { TacticBullet, TacticComparisonTc, TacticSide } from '@/types/library';

/**
 * Fixed column proportions for the Motif | Missed | Allowed table (D-00h); phones stack.
 * fr, not %: percentage tracks summing to 100% ignore the md:gap-4 gutters, so the
 * row overflowed its card by 32px and the card's overflow-hidden clipped the
 * Allowed column's search icon at every desktop width (found in the 239-09 UAT).
 */
const TABLE_GRID_CLASS = 'md:grid-cols-[24fr_38fr_38fr]';
const SIDES: readonly TacticSide[] = ['missed', 'allowed'];
const SIDE_LABELS: Record<TacticSide, string> = { missed: 'Missed', allowed: 'Allowed' };
const CARD_TITLE = 'Most common tactics';
const COPY_NO_FLAWS = 'No flaws';
const COPY_FOOTER =
  "Per 100 games. Middle tick = same as your opponents, fewer (better) to the left. Your and your opponents' rates are in each search-icon popover.";

/** The shown families in filter-panel order (D-17), never re-sorted by rate. */
const SHOWN_FAMILIES: readonly TacticFamilyDef[] = TACTIC_COMPARISON_FAMILIES.filter((def) =>
  LIBRARY_STATS_TACTIC_FAMILIES.includes(def.family),
);

type BulletIndex = ReadonlyMap<string, TacticBullet>;

function bulletKey(family: string, side: TacticSide): string {
  return `${family}:${side}`;
}

function indexBullets(tcStats: TacticComparisonTc): BulletIndex {
  return new Map(tcStats.bullets.map((b) => [bulletKey(b.family, b.orientation), b]));
}

/** The player's own flaws with this family, missed plus allowed ("N of your flaws"). */
function yourFlaws(bullets: BulletIndex, family: string): number {
  return SIDES.reduce((sum, side) => sum + (bullets.get(bulletKey(family, side))?.you_events ?? 0), 0);
}

/** True when neither you nor your opponents have a flaw with this family-side. */
function hasNoFlaws(bullet: TacticBullet): boolean {
  return bullet.you_events + bullet.opp_events === 0;
}

interface TacticCellProps {
  bullet: TacticBullet;
  def: TacticFamilyDef;
  side: TacticSide;
  tcStats: TacticComparisonTc;
}

/**
 * One Missed or Allowed cell: the gap bar per 100 games with its Search popover (D-00c).
 * A cell without flaws reads a muted "No flaws" and has no popover (D-00d); the bar owns
 * the verdict and its significance gate (D-14). On phones a side label sits on the
 * words line, left of the words, since the column header row is hidden (D-00h).
 */
function TacticCell({ bullet, def, side, tcStats }: TacticCellProps) {
  const cell = tacticBulletToGapCell(bullet);
  const segment = tacticTestIdSegment(def.family);
  const copy = tacticSideCopy(def.name, side);
  const testId = `tactic-cell-${segment}-${side}`;
  const noFlaws = hasNoFlaws(bullet);
  const sideLabel = (
    <div className="text-sm text-muted-foreground md:hidden" data-testid={`${testId}-side`}>
      {SIDE_LABELS[side]}
    </div>
  );
  return (
    <div data-testid={testId}>
      {noFlaws ? (
        <>
          {sideLabel}
          <p className="text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
            {COPY_NO_FLAWS}
          </p>
        </>
      ) : (
        <GapBar
          cell={cell}
          testId={`${testId}-bar`}
          layout="stacked"
          mobileLabel={sideLabel}
          trailing={
            <GapPopover
              testId={`gap-popover-tactic-${segment}-${side}-tc-${tcStats.tc}`}
              label={copy.label}
              definition={copy.definition}
              unit="per 100 games"
              noun={copy.noun}
              basis={libraryBasisText(tcStats.analyzed_n, tcStats.tc)}
              cell={cell}
            />
          }
        />
      )}
    </div>
  );
}

interface TacticRowProps {
  def: TacticFamilyDef;
  bullets: BulletIndex;
  tcStats: TacticComparisonTc;
}

function TacticRow({ def, bullets, tcStats }: TacticRowProps) {
  const segment = tacticTestIdSegment(def.family);
  return (
    <div
      className={cn(
        'grid grid-cols-1 items-center gap-2 border-b border-card-edge py-3 last:border-b-0 md:gap-4',
        TABLE_GRID_CLASS,
      )}
      data-testid={`tactic-row-${segment}`}
    >
      <div>
        <div className="font-bold text-foreground">{def.name}</div>
        <div className="text-sm text-muted-foreground" data-testid={`tactic-row-${segment}-flaws`}>
          {yourFlaws(bullets, def.family).toLocaleString('en-US')} of your flaws
        </div>
      </div>
      {SIDES.map((side) => {
        const bullet = bullets.get(bulletKey(def.family, side));
        return bullet ? (
          <TacticCell key={side} bullet={bullet} def={def} side={side} tcStats={tcStats} />
        ) : null;
      })}
    </div>
  );
}

interface TacticTablesProps {
  /** The selected time control's tactic comparison entry (at or above the gate). */
  tcStats: TacticComparisonTc;
}

/**
 * The Tactic motifs section body (Phase 239 D-17, UAT): one card with the four most common
 * tactic families, the only ones with a benchmark typical range on both sides. The rarer
 * families happen less than once per 100 games, so their gaps were mostly noise. Every
 * row is shown, also without flaws; each cell is a gap bar per 100 games.
 */
export function TacticTables({ tcStats }: TacticTablesProps) {
  const bullets = indexBullets(tcStats);
  return (
    <div className="flex flex-col gap-4" data-testid="tactic-tables">
      <Card data-testid="tactic-card">
        <CardHeader>{CARD_TITLE}</CardHeader>
        <CardBody>
          <div
            className={cn('hidden gap-4 pb-2 font-semibold text-muted-foreground md:grid', TABLE_GRID_CLASS)}
            data-testid="tactic-card-header"
          >
            <div>Motif</div>
            <div>Missed</div>
            <div>Allowed</div>
          </div>
          {SHOWN_FAMILIES.map((def) => (
            <TacticRow key={def.family} def={def} bullets={bullets} tcStats={tcStats} />
          ))}
        </CardBody>
      </Card>
      <p className="text-sm text-muted-foreground" data-testid="tactic-tables-footer">
        {COPY_FOOTER}
      </p>
    </div>
  );
}
