import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { libraryBasisText } from '@/lib/flawComparisonMeta';
import {
  TACTIC_COMPARISON_FAMILIES,
  TACTIC_GROUPS,
  tacticBulletToGapCell,
  tacticSideCopy,
  tacticTestIdSegment,
  type TacticFamilyDef,
  type TacticGroupDef,
} from '@/lib/tacticComparisonMeta';
import { cn } from '@/lib/utils';
import { GapBar } from './GapBar';
import { GapPopover } from './GapPopover';
import type { TacticBullet, TacticComparisonTc, TacticSide } from '@/types/library';

/** Fixed column widths so the three tables line up (D-00h); phones stack instead. */
const TABLE_GRID_CLASS = 'md:grid-cols-[24%_38%_38%]';
const SIDES: readonly TacticSide[] = ['missed', 'allowed'];

type BulletIndex = ReadonlyMap<string, TacticBullet>;

function bulletKey(family: string, side: TacticSide): string {
  return `${family}:${side}`;
}

function indexBullets(tcStats: TacticComparisonTc): BulletIndex {
  return new Map(tcStats.bullets.map((b) => [bulletKey(b.family, b.orientation), b]));
}

/** Total flaws on both sides and both orientations: a family with none gets no row. */
function familyFlaws(bullets: BulletIndex, family: string): number {
  return SIDES.reduce((sum, side) => {
    const b = bullets.get(bulletKey(family, side));
    return sum + (b ? b.you_events + b.opp_events : 0);
  }, 0);
}

/** The player's own flaws with this family, missed plus allowed ("N of your flaws"). */
function yourFlaws(bullets: BulletIndex, family: string): number {
  return SIDES.reduce((sum, side) => sum + (bullets.get(bulletKey(family, side))?.you_events ?? 0), 0);
}

interface TacticCellProps {
  bullet: TacticBullet;
  def: TacticFamilyDef;
  side: TacticSide;
  tcStats: TacticComparisonTc;
}

/** One Missed or Allowed cell: the gap bar per 100 games with its Search popover (D-00c). */
function TacticCell({ bullet, def, side, tcStats }: TacticCellProps) {
  const cell = tacticBulletToGapCell(bullet);
  const segment = tacticTestIdSegment(def.family);
  const copy = tacticSideCopy(def.name, side);
  return (
    <GapBar
      cell={cell}
      testId={`tactic-cell-${segment}-${side}`}
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

interface TacticGroupTableProps {
  group: TacticGroupDef;
  bullets: BulletIndex;
  tcStats: TacticComparisonTc;
}

function TacticGroupTable({ group, bullets, tcStats }: TacticGroupTableProps) {
  // Families render in TACTIC_COMPARISON_FAMILIES order, never re-sorted by rate (D-00h).
  const families = TACTIC_COMPARISON_FAMILIES.filter((f) => f.group === group.key);
  const shown = families.filter((f) => familyFlaws(bullets, f.family) > 0);
  return (
    <Card data-testid={`tactic-group-${group.key}`}>
      <CardHeader>{group.label}</CardHeader>
      <CardBody>
        <div className={cn('hidden gap-4 pb-2 font-semibold text-muted-foreground md:grid', TABLE_GRID_CLASS)}>
          <div>Motif</div>
          <div>Missed</div>
          <div>Allowed</div>
        </div>
        {shown.map((def) => (
          <TacticRow key={def.family} def={def} bullets={bullets} tcStats={tcStats} />
        ))}
      </CardBody>
    </Card>
  );
}

interface TacticTablesProps {
  /** The selected time control's tactic comparison entry (at or above the gate). */
  tcStats: TacticComparisonTc;
}

/**
 * The three tactic tables of the Tactic motifs section (sketch 010 round 5): groups in
 * TACTIC_GROUPS order, families in the filter panel's order, each cell a gap bar per 100
 * games for the missed or allowed side.
 */
export function TacticTables({ tcStats }: TacticTablesProps) {
  const bullets = indexBullets(tcStats);
  return (
    <div className="flex flex-col gap-4" data-testid="tactic-tables">
      {TACTIC_GROUPS.map((group) => (
        <TacticGroupTable key={group.key} group={group} bullets={bullets} tcStats={tcStats} />
      ))}
    </div>
  );
}
