import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { Swords } from 'lucide-react';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { Tooltip } from '@/components/ui/tooltip';
import { PER_CLASS_TC_GAUGE_ZONES } from '@/generated/endgameZones';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import {
  ENDGAME_CLASS_TO_SLUG,
  ENDGAME_TYPE_DESCRIPTIONS,
  HIDDEN_ENDGAME_CLASSES,
} from '@/lib/endgameMetrics';
import {
  GAUGE_NEUTRAL,
  PERCENTILE_TRACK,
  PERCENTILE_TYPICAL_BAND,
  TYPICAL_ABOVE_VALUE,
  TYPICAL_BELOW_VALUE,
  ZONE_DANGER,
  ZONE_SUCCESS,
} from '@/lib/theme';
import { cn } from '@/lib/utils';
import type {
  EndgameCategoryStats,
  EndgameClass,
  RankedTcStats,
  TimeControlBucket,
} from '@/types/endgames';
import { TC_LABELS } from './rankedMetrics';
import { TcSwitch } from './TcSwitch';

// Cell domains: the value range each range cell maps onto its 0-100% track (D-00e).
type Domain = readonly [number, number];
const CONVERSION_DOMAIN: Domain = [0.4, 1.0];
const RECOVERY_DOMAIN: Domain = [0.0, 0.6];
const VS_ENGINE_DOMAIN: Domain = [-0.15, 0.15];

const PERCENT_SCALE = 100;
const NO_VALUE = '—';

type ZonedClass = keyof typeof PER_CLASS_TC_GAUGE_ZONES;
type RangeColumn = 'conversion' | 'recovery' | 'achievable_score_gap';

function isZonedClass(endgameClass: EndgameClass): endgameClass is ZonedClass {
  return endgameClass in PER_CLASS_TC_GAUGE_ZONES;
}

/** Position of a value on the cell's track in percent, clamped into the domain. */
function trackPosition(value: number, domain: Domain): number {
  const [min, max] = domain;
  const pct = ((value - min) / (max - min)) * PERCENT_SCALE;
  return Math.max(0, Math.min(PERCENT_SCALE, pct));
}

function formatPercent(fraction: number): string {
  return `${Math.round(fraction * PERCENT_SCALE)}%`;
}

function formatSignedPercent(fraction: number): string {
  const pct = Math.round(fraction * PERCENT_SCALE);
  return `${pct >= 0 ? '+' : ''}${pct}%`;
}

interface RangeCellProps {
  /** Column caption: the mobile cell caption and the stable testid fragment. */
  caption: string;
  slug: string;
  rowTestId: string;
  /** Fraction value, or null when the cell has no games. */
  value: number | null;
  band: readonly [number, number] | null;
  domain: Domain;
  format: (fraction: number) => string;
  /** 99% significance vs the band centre (rates) or 0 (gap); red/green needs it (D-14). */
  significant: boolean;
}

/**
 * Value text color: red below the typical range, green above it, default (white) inside
 * or when the difference is not significant (Phase 239 D-14).
 */
function rangeValueColor(
  value: number | null,
  band: readonly [number, number] | null,
  significant: boolean,
): string | undefined {
  if (value === null || band === null || !significant) return undefined;
  if (value < band[0]) return TYPICAL_BELOW_VALUE;
  if (value > band[1]) return TYPICAL_ABOVE_VALUE;
  return undefined;
}

/**
 * "You" dot color, matching the Endgame Metrics percentile dot: red below the typical
 * range, blue inside it (or when the class has no range, or the difference is not
 * significant, D-14), green above it.
 */
function rangeDotColor(
  value: number,
  band: readonly [number, number] | null,
  significant: boolean,
): string {
  if (!significant) return GAUGE_NEUTRAL;
  if (band !== null && value < band[0]) return ZONE_DANGER;
  if (band !== null && value > band[1]) return ZONE_SUCCESS;
  return GAUGE_NEUTRAL;
}

/** One typical-range cell: value text, grey band, colored dot; red/green text outside the band. */
function RangeCell({
  caption,
  slug,
  rowTestId,
  value,
  band,
  domain,
  format,
  significant,
}: RangeCellProps) {
  const testId = `${rowTestId}-${slug}`;
  const valueColor = rangeValueColor(value, band, significant);
  return (
    <td className="max-md:min-w-0 md:text-right md:align-middle">
      <span
        className="block text-sm text-muted-foreground md:hidden"
        data-testid={`${testId}-caption`}
      >
        {caption}
      </span>
      <span className="flex flex-col gap-1 md:items-end">
        <span
          className="font-semibold tabular-nums"
          style={valueColor ? { color: valueColor } : undefined}
          data-testid={`${testId}-value`}
        >
          {value === null ? NO_VALUE : format(value)}
        </span>
        <span
          className="relative block h-2 w-full rounded-sm md:w-24"
          style={{ backgroundColor: PERCENTILE_TRACK }}
          aria-hidden="true"
        >
          {band !== null && (
            <span
              className="absolute inset-y-0 rounded-sm"
              style={{
                left: `${trackPosition(band[0], domain)}%`,
                width: `${trackPosition(band[1], domain) - trackPosition(band[0], domain)}%`,
                backgroundColor: PERCENTILE_TYPICAL_BAND,
              }}
              data-testid={`${testId}-band`}
            />
          )}
          {value !== null && (
            <span
              className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background"
              style={{
                left: `${trackPosition(value, domain)}%`,
                backgroundColor: rangeDotColor(value, band, significant),
              }}
              data-testid={`${testId}-dot`}
            />
          )}
        </span>
      </span>
    </td>
  );
}

/** Win rate when entering the endgame ahead, as a fraction; null without such games. */
function conversionValue(category: EndgameCategoryStats): number | null {
  const { conversion_games: games, conversion_pct: pct } = category.conversion;
  return games > 0 ? pct / PERCENT_SCALE : null;
}

/** Save rate when entering the endgame behind, as a fraction; null without such games. */
function recoveryValue(category: EndgameCategoryStats): number | null {
  const { recovery_games: games, recovery_pct: pct } = category.conversion;
  return games > 0 ? pct / PERCENT_SCALE : null;
}

/** Mean score gap vs. the engine's expectation; null when no span carries an eval. */
function vsEngineValue(category: EndgameCategoryStats): number | null {
  if ((category.type_achievable_score_gap_n ?? 0) === 0) return null;
  return category.type_achievable_score_gap_mean;
}

/** The class' typical range for one column in one TC; null for a class without zones. */
function typicalBand(
  endgameClass: EndgameClass,
  tc: TimeControlBucket,
  column: RangeColumn,
): readonly [number, number] | null {
  if (!isZonedClass(endgameClass)) return null;
  return PER_CLASS_TC_GAUGE_ZONES[endgameClass][tc][column];
}

interface TypeRowProps {
  category: EndgameCategoryStats;
  tc: TimeControlBucket;
  onCategorySelect: (category: EndgameClass) => void;
}

function TypeRow({ category, tc, onCategorySelect }: TypeRowProps) {
  const rowTestId = `type-row-${category.endgame_class}`;
  const score = category.total > 0 ? (category.wins + category.draws / 2) / category.total : null;

  return (
    <tr
      className="border-b border-card-edge last:border-b-0 max-md:grid max-md:grid-cols-2 max-md:gap-x-3 max-md:gap-y-2 max-md:py-3"
      data-testid={rowTestId}
    >
      <td className="py-2.5 text-left max-md:col-span-2 max-md:py-0 md:pr-2">
        <div className="flex items-center gap-1 font-bold">
          {category.label}
          {category.endgame_class !== 'pawnless' && (
            <InfoPopover
              ariaLabel={`${category.label} info`}
              testId={`${rowTestId}-info`}
              side="top"
            >
              <p>
                <strong>{category.label}:</strong>{' '}
                {ENDGAME_TYPE_DESCRIPTIONS[category.endgame_class]}
              </p>
            </InfoPopover>
          )}
        </div>
        <Tooltip content={`View ${category.label} endgame games`}>
          <Link
            to={`/endgames/games?type=${ENDGAME_CLASS_TO_SLUG[category.endgame_class]}`}
            onClick={() => onCategorySelect(category.endgame_class)}
            className="inline-flex items-center gap-1 text-sm tabular-nums no-underline whitespace-nowrap text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
            aria-label={`View ${category.label} endgame games`}
            data-testid={`${rowTestId}-games-link`}
          >
            {category.total.toLocaleString()} games
            <Swords className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </Tooltip>
      </td>
      <td className="py-2.5 max-md:col-span-2 max-md:py-0">
        <span className="block text-sm text-muted-foreground md:hidden">Results</span>
        <div className="md:w-40 md:ml-auto">
          <MiniWDLBar
            win_pct={category.win_pct}
            draw_pct={category.draw_pct}
            loss_pct={category.loss_pct}
          />
        </div>
      </td>
      <td className="py-2.5 md:text-right max-md:py-0">
        <span
          className="block text-sm text-muted-foreground md:hidden"
          data-testid={`${rowTestId}-score-caption`}
        >
          Score
        </span>
        <span className="font-semibold tabular-nums" data-testid={`${rowTestId}-score-value`}>
          {score === null ? NO_VALUE : formatPercent(score)}
        </span>
      </td>
      <RangeCell
        caption="Conversion"
        slug="conversion"
        rowTestId={rowTestId}
        value={conversionValue(category)}
        band={typicalBand(category.endgame_class, tc, 'conversion')}
        domain={CONVERSION_DOMAIN}
        format={formatPercent}
        significant={category.conversion_significant}
      />
      <RangeCell
        caption="Recovery"
        slug="recovery"
        rowTestId={rowTestId}
        value={recoveryValue(category)}
        band={typicalBand(category.endgame_class, tc, 'recovery')}
        domain={RECOVERY_DOMAIN}
        format={formatPercent}
        significant={category.recovery_significant}
      />
      <RangeCell
        caption="vs. expected"
        slug="gap"
        rowTestId={rowTestId}
        value={vsEngineValue(category)}
        band={typicalBand(category.endgame_class, tc, 'achievable_score_gap')}
        domain={VS_ENGINE_DOMAIN}
        format={formatSignedPercent}
        significant={category.type_achievable_score_gap_significant}
      />
    </tr>
  );
}

const COLUMN_HEADERS = ['Type', 'Results', 'Score', 'Conversion', 'Recovery', 'vs. expected'] as const;

interface TypeTableProps {
  tcs: readonly RankedTcStats[];
  onCategorySelect: (category: EndgameClass) => void;
  /** Rendered under the section question, above the table: the narration slot. */
  children?: ReactNode;
}

/**
 * Endgame Type Breakdown (D-00e, D-05): one row per endgame type for the selected
 * time control, from the ranked sample. Conversion, recovery and vs.-engine cells
 * show where the value sits against the typical range for that type and time
 * control. There is no per-type percentile: the value text is red below the range,
 * green above it and white inside it (238 UAT).
 */
export function TypeTable({ tcs, onCategorySelect, children }: TypeTableProps) {
  const [selectedTc] = useEndgameStatsTc(tcs);
  const tcStats = tcs.find((t) => t.tc === selectedTc);
  if (!tcStats) return null;

  const categories = tcStats.type_categories.filter(
    (category) => !HIDDEN_ENDGAME_CLASSES.has(category.endgame_class),
  );

  return (
    <section
      className="flex flex-col gap-4"
      data-testid="endgame-type-breakdown-section"
      // aria-label, not aria-labelledby: the tab mounts twice (desktop + mobile), so a
      // fixed heading id is duplicated in the DOM (Phase 238 review FE-IN-02).
      aria-label="Endgame Type Breakdown"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2
          className="scroll-mt-16 font-brand text-lg font-semibold text-foreground"
        >
          <span className="inline-flex items-center gap-1">
            Endgame Type Breakdown
            <InfoPopover
              ariaLabel="Endgame Type Breakdown info"
              testId="endgame-type-breakdown-info"
              side="bottom"
            >
              <div className="space-y-2">
                <p>
                  <strong>Endgame Type Breakdown:</strong> how you perform across the different
                  kinds of endgames (rook, minor piece, pawn, queen) in your {TC_LABELS[tcStats.tc]}{' '}
                  games.
                </p>
                <p>
                  Each cell shows your value and a grey typical range for that endgame type and time
                  control. The colored dot marks you. The value turns red when you are below the
                  typical range and green when you are above it, but only when you have enough games
                  to be sure it is not chance.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h2>
        <TcSwitch sectionId="type-breakdown" tcs={tcs} />
      </div>
      <p className="text-sm text-muted-foreground">
        Which endgame types do you convert or defend worse than usual?
      </p>
      {children}
      {categories.length === 0 ? (
        <div
          className="text-sm text-muted-foreground"
          data-testid="endgame-type-breakdown-empty"
        >
          No endgame type data yet. Import more games to see this section.
        </div>
      ) : (
        <div className="charcoal-texture rounded-md p-4">
          <table className="w-full border-collapse max-md:block">
            <thead className="max-md:hidden">
              <tr className="border-b border-card-edge">
                {COLUMN_HEADERS.map((header, index) => (
                  <th
                    key={header}
                    scope="col"
                    className={cn(
                      'whitespace-nowrap px-0 py-1.5 text-sm font-semibold text-muted-foreground',
                      index === 0 ? 'text-left' : 'text-right',
                    )}
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="max-md:block">
              {categories.map((category) => (
                <TypeRow
                  key={category.endgame_class}
                  category={category}
                  tc={tcStats.tc}
                  onCategorySelect={onCategorySelect}
                />
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-sm text-muted-foreground" data-testid="type-table-legend">
            Grey band = typical range for all players in this time control and endgame type. Dot
            = you. <span style={{ color: TYPICAL_BELOW_VALUE }}>Red</span> = below,{' '}
            <span style={{ color: TYPICAL_ABOVE_VALUE }}>green</span> = above the typical range, when there are enough games to be sure.
          </p>
        </div>
      )}
    </section>
  );
}
