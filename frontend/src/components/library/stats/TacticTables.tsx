import { ExpandHint } from '@/components/insights/ShellyQuote';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { useTrackedOpen } from '@/hooks/useTrackedOpen';
import { trackFeature } from '@/lib/analytics';
import { libraryBasisText } from '@/lib/flawComparisonMeta';
import { UNRELIABLE_OPACITY } from '@/lib/theme';
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
const SIDE_LABELS: Record<TacticSide, string> = { missed: 'Missed', allowed: 'Allowed' };
/** The group that starts collapsed: the rare motifs, mostly faded rows (D-00i). */
const COLLAPSED_GROUP_KEY: TacticGroupDef['key'] = 'advanced';
const COPY_NO_FLAWS = 'No flaws';
const COPY_FOOTER =
  "Per 100 games. Middle tick = same as your opponents, better to the right. Your and your opponents' rates are in each search-icon popover.";

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
 * A cell without flaws reads a muted "No flaws" and has no popover (D-00d); a low-sample
 * cell is faded and its bar shows a neutral dot and no verdict (D-12). On phones a side
 * label sits above the cell, since the column header row is hidden (D-00h).
 */
function TacticCell({ bullet, def, side, tcStats }: TacticCellProps) {
  const cell = tacticBulletToGapCell(bullet);
  const segment = tacticTestIdSegment(def.family);
  const copy = tacticSideCopy(def.name, side);
  const testId = `tactic-cell-${segment}-${side}`;
  const noFlaws = hasNoFlaws(bullet);
  return (
    <div
      style={bullet.low_sample && !noFlaws ? { opacity: UNRELIABLE_OPACITY } : undefined}
      data-testid={testId}
    >
      <div className="text-sm text-muted-foreground md:hidden" data-testid={`${testId}-side`}>
        {SIDE_LABELS[side]}
      </div>
      {noFlaws ? (
        <p className="text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
          {COPY_NO_FLAWS}
        </p>
      ) : (
        <GapBar
          cell={cell}
          testId={`${testId}-bar`}
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

interface TacticGroupProps {
  group: TacticGroupDef;
  bullets: BulletIndex;
  tcStats: TacticComparisonTc;
}

/**
 * The table of one group: header row, a row per family with flaws, and the families
 * without any listed under the table (D-00h).
 */
function TacticGroupTable({ group, bullets, tcStats }: TacticGroupProps) {
  // Families render in TACTIC_COMPARISON_FAMILIES order, never re-sorted by rate (D-00h).
  const families = TACTIC_COMPARISON_FAMILIES.filter((f) => f.group === group.key);
  const shown = families.filter((f) => familyFlaws(bullets, f.family) > 0);
  const empty = families.filter((f) => familyFlaws(bullets, f.family) === 0);
  return (
    <>
      <div
        className={cn('hidden gap-4 pb-2 font-semibold text-muted-foreground md:grid', TABLE_GRID_CLASS)}
        data-testid={`tactic-group-${group.key}-header`}
      >
        <div>Motif</div>
        <div>Missed</div>
        <div>Allowed</div>
      </div>
      {shown.map((def) => (
        <TacticRow key={def.family} def={def} bullets={bullets} tcStats={tcStats} />
      ))}
      {empty.length > 0 && (
        <p
          className="mt-3 text-sm text-muted-foreground"
          data-testid={`tactic-group-${group.key}-no-flaws`}
        >
          No flaws yet: {empty.map((f) => f.name).join(', ')}.
        </p>
      )}
    </>
  );
}

/** A group that is always open: a plain header-band card (D-00j). */
function StaticTacticGroup(props: TacticGroupProps) {
  return (
    <Card data-testid={`tactic-group-${props.group.key}`}>
      <CardHeader>{props.group.label}</CardHeader>
      <CardBody>
        <TacticGroupTable {...props} />
      </CardBody>
    </Card>
  );
}

/**
 * The collapsed-by-default group (D-00i): an accordion whose header band carries the
 * shared expand hint. Opening it sends one panel-open event per mount.
 */
function CollapsibleTacticGroup(props: TacticGroupProps) {
  const { group } = props;
  const [open, setOpen] = useTrackedOpen(
    () => trackFeature('panel-open', { target: 'tactic-advanced' }),
    { once: true },
  );
  return (
    <Accordion
      type="single"
      collapsible
      value={open ? group.key : ''}
      onValueChange={(value) => setOpen(value === group.key)}
    >
      <AccordionItem
        value={group.key}
        className="charcoal-texture overflow-hidden rounded-md"
        data-testid={`tactic-group-${group.key}`}
      >
        <AccordionTrigger band data-testid={`tactic-group-${group.key}-trigger`}>
          <span className="flex flex-1 flex-col gap-0.5">
            <span className="text-base font-semibold">{group.label}</span>
            <ExpandHint />
          </span>
        </AccordionTrigger>
        <AccordionContent className="p-4">
          <TacticGroupTable {...props} />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

interface TacticTablesProps {
  /** The selected time control's tactic comparison entry (at or above the gate). */
  tcStats: TacticComparisonTc;
}

/**
 * The three tactic tables of the Tactic motifs section (sketch 010 round 5): groups in
 * TACTIC_GROUPS order, families in the filter panel's order, each cell a gap bar per 100
 * games for the missed or allowed side. Advanced starts collapsed (D-00i).
 */
export function TacticTables({ tcStats }: TacticTablesProps) {
  const bullets = indexBullets(tcStats);
  return (
    <div className="flex flex-col gap-4" data-testid="tactic-tables">
      {TACTIC_GROUPS.map((group) =>
        group.key === COLLAPSED_GROUP_KEY ? (
          <CollapsibleTacticGroup key={group.key} group={group} bullets={bullets} tcStats={tcStats} />
        ) : (
          <StaticTacticGroup key={group.key} group={group} bullets={bullets} tcStats={tcStats} />
        ),
      )}
      <p className="text-sm text-muted-foreground" data-testid="tactic-tables-footer">
        {COPY_FOOTER}
      </p>
    </div>
  );
}
