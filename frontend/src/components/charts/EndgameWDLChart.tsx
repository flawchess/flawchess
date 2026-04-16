import { Link } from 'react-router-dom';
import { FolderOpen } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { Tooltip } from '@/components/ui/tooltip';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  UNRELIABLE_OPACITY,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

interface EndgameWDLChartProps {
  categories: EndgameCategoryStats[];
  onCategorySelect: (category: EndgameClass) => void;
}

// Map EndgameClass to slug used in data-testid
const CLASS_TO_SLUG: Record<EndgameClass, string> = {
  rook: 'rook',
  minor_piece: 'minor-piece',
  pawn: 'pawn',
  queen: 'queen',
  mixed: 'mixed',
  pawnless: 'pawnless',
};

const ENDGAME_TYPE_DESCRIPTIONS: Record<EndgameClass, string> = {
  rook: 'Endgames with rooks as the only non-king, non-pawn pieces. The most common endgame type besides Mixed.',
  minor_piece: 'Endgames with bishops and/or knights as the only non-king, non-pawn pieces.',
  pawn: 'King and pawn endgames only — no other pieces remain on the board.',
  queen: 'Endgames where queens are the only non-king, non-pawn pieces.',
  mixed: 'Endgames with pieces from two or more piece types — rooks, minor pieces (bishops/knights), and queens (e.g. queen + rook, rook + knight).',
  pawnless: 'Endgames with no pawns on the board — only kings and pieces.',
};

// Matches Endgame Conversion & Recovery: ±5pp neutral zone reads as
// "essentially matched" on the Diff color and bullet-chart neutral band.
const NEUTRAL_ZONE_MIN = -0.05;
const NEUTRAL_ZONE_MAX = 0.05;

// Bullet domain for endgame-type score gap. Per-type scores can swing wider
// than material-bucket mirror comparisons, so ±0.30 covers realistic ranges
// without clamping common outliers.
const BULLET_DOMAIN = 0.30;

/** Chess score 0.0-1.0 from the user's WDL counts on this category's games. */
function userScore(cat: EndgameCategoryStats): number {
  if (cat.total === 0) return 0;
  return (cat.wins + cat.draws / 2) / cat.total;
}

/** Opponent chess score in the same games: (losses + draws/2) / total = 1 - userScore.
 * In a per-endgame-type view both players share the same games, so the
 * opponent baseline is trivially the complement of the user's score. */
function opponentScore(cat: EndgameCategoryStats): number {
  if (cat.total === 0) return 0;
  return (cat.losses + cat.draws / 2) / cat.total;
}

function formatScorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function formatDiffPct(userR: number, oppR: number): string {
  const pct = Math.round(userR * 100) - Math.round(oppR * 100);
  return `${pct >= 0 ? '+' : ''}${pct}%`;
}

function diffColor(diff: number): string {
  if (diff >= NEUTRAL_ZONE_MAX) return ZONE_SUCCESS;
  if (diff >= NEUTRAL_ZONE_MIN) return ZONE_NEUTRAL;
  return ZONE_DANGER;
}

interface RowData extends EndgameCategoryStats {
  slug: string;
}

function EndgameCategoryRowDesktop({
  cat,
  onCategorySelect,
  isEvenRow,
}: {
  cat: RowData;
  onCategorySelect: (category: EndgameClass) => void;
  isEvenRow: boolean;
}) {
  const isUnreliable = cat.total > 0 && cat.total < MIN_GAMES_FOR_RELIABLE_STATS;
  const isEmpty = cat.total === 0;
  const userR = userScore(cat);
  const oppR = opponentScore(cat);
  const diff = userR - oppR;
  const rowOpacity = isUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined;

  return (
    <tr
      className={isEvenRow ? 'bg-white/[0.02]' : undefined}
      data-testid={`endgame-category-${cat.slug}-row`}
    >
      <td className="py-1.5 pr-3 text-sm">
        <span className="font-medium">{cat.label}</span>
      </td>
      <td className="py-1.5 px-2 text-right text-xs tabular-nums whitespace-nowrap">
        <Tooltip content={`View ${cat.label} endgame games`}>
          <Link
            to="/endgames/games"
            onClick={() => onCategorySelect(cat.endgame_class)}
            className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
            aria-label={`View ${cat.label} endgame games`}
            data-testid={`endgame-games-link-${cat.slug}`}
          >
            <span>
              {cat.total.toLocaleString()} games{isUnreliable && ' (low)'}
            </span>
            <FolderOpen className="h-3.5 w-3.5" />
          </Link>
        </Tooltip>
      </td>
      <td className="py-1.5 px-2" style={rowOpacity}>
        {isEmpty ? (
          <div className="h-5 rounded bg-muted" />
        ) : (
          <MiniWDLBar win_pct={cat.win_pct} draw_pct={cat.draw_pct} loss_pct={cat.loss_pct} />
        )}
      </td>
      <td
        className="py-1.5 px-2 text-right text-xs tabular-nums whitespace-nowrap"
        style={rowOpacity}
        data-testid={`endgame-category-${cat.slug}-you`}
      >
        {isEmpty ? '' : formatScorePct(userR)}
      </td>
      <td
        className="py-1.5 px-2 text-right text-xs tabular-nums text-muted-foreground whitespace-nowrap"
        style={rowOpacity}
        data-testid={`endgame-category-${cat.slug}-opp`}
      >
        {isEmpty ? '' : formatScorePct(oppR)}
      </td>
      <td
        className="py-1.5 px-2 text-right text-xs tabular-nums whitespace-nowrap"
        style={rowOpacity}
        data-testid={`endgame-category-${cat.slug}-diff`}
      >
        {isEmpty ? (
          ''
        ) : (
          <span className="font-semibold" style={{ color: diffColor(diff) }}>
            {formatDiffPct(userR, oppR)}
          </span>
        )}
      </td>
      <td className="py-1.5 px-2" style={rowOpacity}>
        {isEmpty ? null : (
          <MiniBulletChart
            value={diff}
            neutralMin={NEUTRAL_ZONE_MIN}
            neutralMax={NEUTRAL_ZONE_MAX}
            domain={BULLET_DOMAIN}
            ariaLabel={`${cat.label}: ${formatDiffPct(userR, oppR)} score gap`}
          />
        )}
      </td>
    </tr>
  );
}

function EndgameCategoryCardMobile({
  cat,
  onCategorySelect,
}: {
  cat: RowData;
  onCategorySelect: (category: EndgameClass) => void;
}) {
  const isUnreliable = cat.total > 0 && cat.total < MIN_GAMES_FOR_RELIABLE_STATS;
  const isEmpty = cat.total === 0;
  const userR = userScore(cat);
  const oppR = opponentScore(cat);
  const diff = userR - oppR;

  return (
    <div
      className={
        'rounded border border-border p-3 space-y-2' + (isEmpty ? ' opacity-50' : '')
      }
      data-testid={`endgame-category-card-${cat.slug}`}
    >
      <div className="flex items-baseline justify-between">
        <div className="text-sm font-medium">{cat.label}</div>
        <Tooltip content={`View ${cat.label} endgame games`}>
          <Link
            to="/endgames/games"
            onClick={() => onCategorySelect(cat.endgame_class)}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors tabular-nums"
            aria-label={`View ${cat.label} endgame games`}
            data-testid={`endgame-games-link-${cat.slug}-mobile`}
          >
            <span>
              {cat.total.toLocaleString()} games{isUnreliable && ' (low)'}
            </span>
            <FolderOpen className="h-3.5 w-3.5" />
          </Link>
        </Tooltip>
      </div>
      <div style={isUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}>
        <div className="text-xs text-muted-foreground mb-1">Win / Draw / Loss</div>
        {isEmpty ? (
          <div className="h-5 rounded bg-muted" />
        ) : (
          <MiniWDLBar win_pct={cat.win_pct} draw_pct={cat.draw_pct} loss_pct={cat.loss_pct} />
        )}
      </div>
      {!isEmpty && (
        <div style={isUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs tabular-nums mb-1">
            <div>
              <span className="text-muted-foreground">You: </span>
              <span
                className="font-medium"
                data-testid={`endgame-category-card-${cat.slug}-you`}
              >
                {formatScorePct(userR)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Opp: </span>
              <span
                className="font-medium"
                data-testid={`endgame-category-card-${cat.slug}-opp`}
              >
                {formatScorePct(oppR)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Diff: </span>
              <span
                className="font-semibold"
                style={{ color: diffColor(diff) }}
                data-testid={`endgame-category-card-${cat.slug}-diff`}
              >
                {formatDiffPct(userR, oppR)}
              </span>
            </div>
          </div>
          <MiniBulletChart
            value={diff}
            neutralMin={NEUTRAL_ZONE_MIN}
            neutralMax={NEUTRAL_ZONE_MAX}
            domain={BULLET_DOMAIN}
            ariaLabel={`${cat.label}: ${formatDiffPct(userR, oppR)} score gap`}
          />
        </div>
      )}
    </div>
  );
}

export function EndgameWDLChart({
  categories,
  onCategorySelect,
}: EndgameWDLChartProps) {
  // Backend already sorts by total desc — transform for display
  const data: RowData[] = categories.map((cat) => ({
    ...cat,
    slug: CLASS_TO_SLUG[cat.endgame_class],
  }));

  return (
    <div data-testid="endgame-wdl-chart">
      <div className="mb-3">
        <h2 className="text-lg font-medium">
          <span className="inline-flex items-center gap-1">
            Results by Endgame Type
            <InfoPopover ariaLabel="Results by endgame type info" testId="endgame-chart-info" side="top">
              <div className="space-y-2">
                <p>
                  Shows your win, draw, and loss percentages for each endgame type, based on games
                  that included the endgame type. Note that a game can include more than one type of endgame.
                </p>
                <p>
                  <strong>You</strong> is your Score % in these games
                  (100% per win, 50% per draw, averaged over games). <strong>Opp</strong>{' '}
                  is the complement — your opponents' Score % in the same games. <strong>Diff</strong>{' '}
                  and the bullet chart visualize the signed gap, with a ±5pp neutral band
                  around 50/50.
                </p>
                <p><strong>Rook:</strong> {ENDGAME_TYPE_DESCRIPTIONS.rook}</p>
                <p><strong>Minor Piece:</strong> {ENDGAME_TYPE_DESCRIPTIONS.minor_piece}</p>
                <p><strong>Pawn:</strong> {ENDGAME_TYPE_DESCRIPTIONS.pawn}</p>
                <p><strong>Queen:</strong> {ENDGAME_TYPE_DESCRIPTIONS.queen}</p>
                <p><strong>Mixed:</strong> {ENDGAME_TYPE_DESCRIPTIONS.mixed}</p>
              </div>
            </InfoPopover>
          </span>
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Win/draw/loss rate for each endgame type — a game can count toward multiple types.
        </p>
      </div>

      {/* Desktop (lg+): table layout mirroring Endgame Conversion & Recovery */}
      <div className="hidden lg:block overflow-x-auto">
        <table
          className="w-full min-w-[600px] text-sm sm:text-base table-fixed"
          data-testid="endgame-type-table"
        >
          <colgroup>
            <col style={{ width: '110px' }} />
            <col style={{ width: '120px' }} />
            <col style={{ width: '150px' }} />
            <col style={{ width: '90px' }} />
            <col style={{ width: '100px' }} />
            <col style={{ width: '70px' }} />
            <col style={{ width: '160px' }} />
          </colgroup>
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b border-border">
              <th className="py-1 pr-3 font-medium" aria-label="Endgame type" />
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">You</th>
              <th className="py-1 px-2 font-medium text-right">Opp</th>
              <th className="py-1 px-2 font-medium text-right">Diff</th>
              <th className="py-1 px-2 font-medium">You − Opp</th>
            </tr>
          </thead>
          <tbody>
            {data.map((cat, i) => (
              <EndgameCategoryRowDesktop
                key={cat.endgame_class}
                cat={cat}
                onCategorySelect={onCategorySelect}
                isEvenRow={i % 2 === 0}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile (<lg): stacked cards */}
      <div className="lg:hidden space-y-3">
        {data.map((cat) => (
          <EndgameCategoryCardMobile
            key={cat.endgame_class}
            cat={cat}
            onCategorySelect={onCategorySelect}
          />
        ))}
      </div>
    </div>
  );
}
