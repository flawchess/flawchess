import { useState } from 'react';
import { BookMarked, ChevronDown, Sparkles } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { Button } from '@/components/ui/button';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictCompact } from '@/components/openings/stats/VerdictBar';
import {
  EvalVerdictPopover,
  ScoreVerdictPopover,
} from '@/components/openings/stats/VerdictPopover';
import { useReadiness } from '@/hooks/useReadiness';
import type { RepertoireRowModel } from '@/pages/openings/useRepertoireRows';
import { trackFeature } from '@/lib/analytics';
import { gapVerdictColor, type GapVerdict } from '@/lib/gapBar';
import {
  EVAL_VERDICT_BAND,
  REPERTOIRE_MIN_GAMES_FOR_VERDICT,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatEvalCompact,
  formatScorePercent,
  isFadedRow,
  openingVerdict,
  openingVerdictReason,
  scoreDelta,
} from '@/lib/openingVerdict';
import { formatRelativeDate } from '@/lib/relativeDate';
import { UNRELIABLE_OPACITY } from '@/lib/theme';

/** Top offset of the sticky header: py-2 plus the h-8 switch row of the colour bar on lg and the
 * Filters row on md both measure 48 px. */
const REPERTOIRE_HEADER_STICKY_TOP_PX = 48;
const MINI_BOARD_SIZE = 44;
const COLUMN_HEADERS = ['Opening', 'Games', 'Results', 'Score', 'Eval after opening'] as const;
const COLUMN_COUNT = COLUMN_HEADERS.length;
const NO_VALUE = '—';
const NOT_PLAYED_RECENTLY = 'not played recently';

const CELL_BASE = 'px-3 py-2.5 align-middle max-md:p-0';
const GROUP_ROW_CLASS =
  'bg-white/[0.02] px-3 py-1.5 text-sm font-semibold uppercase tracking-wide text-muted-foreground';

interface RepertoireTableProps {
  color: 'white' | 'black';
  bookmarkRows: RepertoireRowModel[];
  currentRows: RepertoireRowModel[];
  pastRows: RepertoireRowModel[];
  /** ISO cutoff of the current repertoire for this colour; null when every opening is current. */
  currentCutoff: string | null;
  onOpenSuggestions: () => void;
}

function colorLabel(color: 'white' | 'black'): string {
  return color === 'white' ? 'White' : 'Black';
}

/** "14 Feb 2026" from the backend cutoff, so the frontend hard-codes no window length. */
function formatCutoffDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function lastPlayedText(row: RepertoireRowModel): string {
  return row.lastPlayedAt ? formatRelativeDate(row.lastPlayedAt) : '';
}

function OpeningCell({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const stale = row.kind === 'bookmark' && !row.isCurrent;
  return (
    <td className={`${CELL_BASE} max-md:col-start-1 max-md:row-span-2 max-md:row-start-1 max-md:min-w-0`}>
      <div className="flex min-w-0 items-center gap-2.5">
        <LazyMiniBoard fen={row.fen} flipped={row.color === 'black'} size={MINI_BOARD_SIZE} />
        <div className="min-w-0">
          <div className="font-bold" data-testid={`${testId}-name`}>
            {row.kind === 'bookmark' && (
              <BookMarked
                className="mr-1 inline-block h-3.5 w-3.5 align-[-2px] text-brand-brown-light"
                aria-label="Bookmarked"
              />
            )}
            {row.name}
            {stale && (
              <span
                className="ml-1.5 inline-block rounded-full bg-white/10 px-2 py-px align-[1px] text-sm font-semibold whitespace-nowrap text-muted-foreground"
                data-testid={`${testId}-stale-chip`}
              >
                {NOT_PLAYED_RECENTLY}
              </span>
            )}
          </div>
          <div className="truncate text-sm text-muted-foreground max-md:max-w-56 md:max-w-80">
            {row.moveLine}
          </div>
        </div>
      </div>
    </td>
  );
}

function ScoreCell({ row, testId }: { row: RepertoireRowModel; testId: string }) {
  const input = {
    delta: scoreDelta(row.score),
    band: SCORE_VERDICT_BAND,
    confidence: row.scoreConfidence,
    games: row.games,
  };
  return (
    <td className={`${CELL_BASE} max-md:col-start-2 max-md:row-start-1 max-md:justify-self-end`}>
      <span className="inline-flex items-center gap-2">
        <span className="w-10 text-right text-sm text-muted-foreground md:hidden">Score</span>
        <VerdictCompact
          verdict={openingVerdict(input)}
          valueText={formatScorePercent(row.score)}
          testId={`${testId}-score`}
          trailing={
            <ScoreVerdictPopover
              testId={`${testId}-score-info`}
              score={row.score}
              games={row.games}
              wins={row.wins}
              draws={row.draws}
              losses={row.losses}
              reason={openingVerdictReason(input)}
              ci99Low={row.scoreCi99Low}
              ci99High={row.scoreCi99High}
              pValue={row.scorePValue}
            />
          }
        />
      </span>
    </td>
  );
}

function EvalValue({ row, testId, tier2 }: { row: RepertoireRowModel; testId: string; tier2: boolean }) {
  // Eval needs Stockfish analysis: show the pending placeholder until tier 2 is reached.
  if (!tier2) return <EvalCpuPlaceholder />;
  if (row.avgEvalPawns === null || row.evalN <= 0) {
    return <span className="text-muted-foreground">{NO_VALUE}</span>;
  }
  const input = {
    delta: row.avgEvalPawns - evalBaselinePawns(row.color),
    band: EVAL_VERDICT_BAND,
    confidence: row.evalConfidence,
    games: row.games,
  };
  return (
    <VerdictCompact
      verdict={openingVerdict(input)}
      valueText={formatEvalCompact(row.avgEvalPawns)}
      testId={`${testId}-eval`}
      trailing={
        <EvalVerdictPopover
          testId={`${testId}-eval-info`}
          label="Eval after opening"
          avgEvalPawns={row.avgEvalPawns}
          evalN={row.evalN}
          color={row.color}
          reason={openingVerdictReason(input)}
          ci99Low={row.evalCi99Low}
          ci99High={row.evalCi99High}
          pValue={row.evalPValue}
        />
      }
    />
  );
}

function RepertoireRow({
  row,
  index,
  tier2,
}: {
  row: RepertoireRowModel;
  index: number;
  tier2: boolean;
}) {
  // Indices, never opening names, build the testids: names repeat once ECO codes are dropped.
  const testId = `repertoire-row-${index}`;
  const lastPlayed = lastPlayedText(row);
  return (
    <tr
      className="border-b border-card-edge max-md:grid max-md:grid-cols-[minmax(0,1fr)_auto] max-md:gap-x-3 max-md:gap-y-2 max-md:p-3"
      style={isFadedRow(row.games) ? { opacity: UNRELIABLE_OPACITY } : undefined}
      data-testid={testId}
    >
      <OpeningCell row={row} testId={testId} />
      <td className={`${CELL_BASE} text-right tabular-nums max-md:hidden`} data-testid={`${testId}-games`}>
        <div>{row.games.toLocaleString('en-US')}</div>
        <div className="text-sm font-normal text-muted-foreground whitespace-nowrap">{lastPlayed}</div>
      </td>
      <td className={`${CELL_BASE} max-md:col-span-full max-md:row-start-3`}>
        <div className="flex items-center gap-2 md:min-w-40">
          <MiniWDLBar win_pct={row.winPct} draw_pct={row.drawPct} loss_pct={row.lossPct} />
          <span className="whitespace-nowrap text-sm text-muted-foreground tabular-nums md:hidden">
            {row.games.toLocaleString('en-US')} games{lastPlayed ? ` · ${lastPlayed}` : ''}
          </span>
        </div>
      </td>
      <ScoreCell row={row} testId={testId} />
      <td
        className={`${CELL_BASE} max-md:col-start-2 max-md:row-start-2 max-md:self-start max-md:justify-self-end`}
      >
        <span className="inline-flex items-center gap-2" data-testid={`${testId}-eval-cell`}>
          <span className="w-10 text-right text-sm text-muted-foreground md:hidden">Eval</span>
          <EvalValue row={row} testId={testId} tier2={tier2} />
        </span>
      </td>
    </tr>
  );
}

function GroupRow({ label, testId }: { label: string; testId: string }) {
  return (
    <tr data-testid={testId}>
      <td colSpan={COLUMN_COUNT} className={GROUP_ROW_CLASS}>
        {label}
      </td>
    </tr>
  );
}

function PlayedBeforeToggle({
  count,
  hint,
  expanded,
  onToggle,
}: {
  count: number;
  hint: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <tr>
      <td colSpan={COLUMN_COUNT} className="p-0">
        <button
          type="button"
          className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-white/5"
          aria-expanded={expanded}
          onClick={onToggle}
          data-testid="repertoire-played-before-toggle"
        >
          <span>Played before ({count})</span>
          {hint && <span className="font-normal normal-case tracking-normal">{hint}</span>}
          <ChevronDown
            className={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
            aria-hidden="true"
          />
        </button>
      </td>
    </tr>
  );
}

function VerdictLegend({ color }: { color: 'white' | 'black' }) {
  const baseline = evalBaselinePawns(color);
  const dots: Array<{ verdict: GapVerdict; label: string }> = [
    { verdict: 'better', label: 'clearly better' },
    { verdict: 'typical', label: 'typical or not clear' },
    { verdict: 'worse', label: 'clearly worse' },
  ];
  return (
    <p
      className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 text-sm text-muted-foreground"
      data-testid="repertoire-legend"
    >
      {dots.map((d) => (
        <span key={d.verdict} className="inline-flex items-center gap-1.5">
          <span
            className="size-2.5 rounded-full"
            style={{ backgroundColor: gapVerdictColor(d.verdict) }}
          />
          {d.label}
        </span>
      ))}
      <span>
        Typical: score {formatScorePercent(0.5 - SCORE_VERDICT_BAND)} to{' '}
        {formatScorePercent(0.5 + SCORE_VERDICT_BAND)}, eval within {EVAL_VERDICT_BAND.toFixed(2)} of an
        average {colorLabel(color)} game ({baseline > 0 ? '+' : '−'}
        {Math.abs(baseline).toFixed(2)}). Faded rows have fewer than {REPERTOIRE_MIN_GAMES_FOR_VERDICT}{' '}
        games.
      </span>
    </p>
  );
}

function FooterRow({
  color,
  bookmarkCount,
  currentCount,
  pastCount,
  onOpenSuggestions,
}: {
  color: 'white' | 'black';
  bookmarkCount: number;
  currentCount: number;
  pastCount: number;
  onOpenSuggestions: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-2.5 text-sm text-muted-foreground">
      <span data-testid="repertoire-footer-counts">
        {bookmarkCount} bookmarks · {currentCount} most played as {colorLabel(color).toLowerCase()}
        {pastCount > 0 ? ` · ${pastCount} played before` : ''}
      </span>
      <Button
        size="sm"
        variant="brand-outline"
        onClick={onOpenSuggestions}
        data-testid="btn-suggest-bookmarks-footer"
      >
        <Sparkles className="h-4 w-4" />
        Suggest bookmarks
      </Button>
    </div>
  );
}

export function RepertoireTable({
  color,
  bookmarkRows,
  currentRows,
  pastRows,
  currentCutoff,
  onOpenSuggestions,
}: RepertoireTableProps) {
  const { tier2 } = useReadiness();
  const [pastExpanded, setPastExpanded] = useState(false);
  const visiblePast = pastExpanded ? pastRows : [];
  const ordered = [...bookmarkRows, ...currentRows, ...visiblePast];
  const indexOf = new Map(ordered.map((row, i) => [row.key, i]));
  const renderRow = (row: RepertoireRowModel) => (
    <RepertoireRow key={row.key} row={row} index={indexOf.get(row.key) ?? 0} tier2={tier2} />
  );

  const handleTogglePast = () => {
    // Discovery only: track the expand, never the collapse.
    if (!pastExpanded) trackFeature('panel-open', { target: 'opening-stats-more' });
    setPastExpanded((prev) => !prev);
  };
  const hint = currentCutoff
    ? `not played as ${colorLabel(color)} since ${formatCutoffDate(currentCutoff)}`
    : '';

  // No ancestor of this section may set overflow-*: the sticky header would stop sticking
  // (.charcoal-texture clips by default, hence overflow-visible).
  return (
    <section
      className="charcoal-texture overflow-visible rounded-md"
      data-testid={`repertoire-table-${color}`}
    >
      <table className="w-full border-collapse">
        <thead className="max-md:hidden">
          <tr>
            {COLUMN_HEADERS.map((header, i) => (
              <th
                key={header}
                scope="col"
                className={`sticky z-10 border-b border-card-edge bg-charcoal px-3 py-2 text-sm font-semibold whitespace-nowrap text-muted-foreground ${i === 1 ? 'text-right' : 'text-left'} ${i === 0 ? 'rounded-tl-md' : ''} ${i === COLUMN_COUNT - 1 ? 'rounded-tr-md' : ''}`}
                style={{ top: REPERTOIRE_HEADER_STICKY_TOP_PX }}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bookmarkRows.length > 0 && <GroupRow label="Bookmarks" testId="repertoire-group-bookmarks" />}
          {bookmarkRows.map(renderRow)}
          {currentRows.length > 0 && (
            <GroupRow label="Most played" testId="repertoire-group-most-played" />
          )}
          {currentRows.map(renderRow)}
          {ordered.length === 0 && pastRows.length === 0 && (
            <tr data-testid="repertoire-empty">
              <td colSpan={COLUMN_COUNT} className="px-3 py-6 text-center text-sm text-muted-foreground">
                No {colorLabel(color)} games match the current filters.
              </td>
            </tr>
          )}
          {pastRows.length > 0 && (
            <PlayedBeforeToggle
              count={pastRows.length}
              hint={hint}
              expanded={pastExpanded}
              onToggle={handleTogglePast}
            />
          )}
          {visiblePast.map(renderRow)}
        </tbody>
      </table>
      <FooterRow
        color={color}
        bookmarkCount={bookmarkRows.length}
        currentCount={currentRows.length}
        pastCount={pastRows.length}
        onOpenSuggestions={onOpenSuggestions}
      />
      <VerdictLegend color={color} />
    </section>
  );
}
