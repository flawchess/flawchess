import { InfoPopover } from '@/components/ui/info-popover';
import { WDL_WIN, WDL_DRAW, WDL_LOSS } from '@/components/results/WDLBar';
import { cn } from '@/lib/utils';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

interface EndgameWDLChartProps {
  categories: EndgameCategoryStats[];
  selectedCategory: EndgameClass | null;
  onCategoryClick: (category: EndgameClass) => void;
  onSelectedCategoryClick: () => void;
}

// Glass-effect overlay matching WDLBar.tsx
const GLASS_OVERLAY =
  'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

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
  rook: 'Endgames with rooks as the only non-king, non-pawn pieces. The most common endgame type.',
  minor_piece: 'Endgames with bishops and/or knights as the only non-king, non-pawn pieces.',
  pawn: 'King and pawn endgames only — no other pieces remain on the board.',
  queen: 'Endgames where queens are the only non-king, non-pawn pieces.',
  mixed: 'Endgames with pieces from two or more families (e.g. queen + rook, rook + knight).',
  pawnless: 'Endgames with no pawns on the board — only kings and pieces.',
};

const MIN_GAMES_FOR_RELIABLE_STATS = 10;

function formatConversionMetric(pct: number, saves: number, games: number): string {
  if (games === 0) return '—';
  return `${pct.toFixed(0)}% (${saves}/${games})`;
}

export function EndgameWDLChart({
  categories,
  selectedCategory,
  onCategoryClick,
  onSelectedCategoryClick,
}: EndgameWDLChartProps) {
  // Backend already sorts by total desc — transform for display
  const data = categories.map((cat) => ({
    endgame_class: cat.endgame_class,
    label: cat.label,
    slug: CLASS_TO_SLUG[cat.endgame_class],
    win_pct: cat.win_pct,
    draw_pct: cat.draw_pct,
    loss_pct: cat.loss_pct,
    wins: cat.wins,
    draws: cat.draws,
    losses: cat.losses,
    total: cat.total,
    conversion_pct: cat.conversion.conversion_pct,
    conversion_games: cat.conversion.conversion_games,
    conversion_wins: cat.conversion.conversion_wins,
    recovery_pct: cat.conversion.recovery_pct,
    recovery_games: cat.conversion.recovery_games,
    recovery_saves: cat.conversion.recovery_saves,
  }));

  const maxTotal = Math.max(...categories.map((c) => c.total));

  return (
    <div data-testid="endgame-wdl-chart">
      <h2 className="text-lg font-medium mb-3">
        <span className="inline-flex items-center gap-1">
          Results by Endgame Type
          <InfoPopover ariaLabel="Results by endgame type info" testId="endgame-chart-info" side="top">
            <p className="mb-2">
              Shows your win, draw, and loss percentages for each endgame type, based on games that reached that endgame.
            </p>
            <p className="mb-2">
              Conversion is your win rate when you entered the endgame with more material.
              Recovery is your draw+win rate when you entered with less material.
            </p>
            <p className="mb-2">
              Endgame phase is defined as positions where the total count of major and minor pieces
              (queens, rooks, bishops, knights) across both sides is at most 6. Kings and pawns are not counted.
              This follows the Lichess definition.
            </p>
            <p>
              Click a row to select it and view details. Click the same row again to jump to matching games.
            </p>
          </InfoPopover>
        </span>
      </h2>

      {/* Per-category clickable rows with inline conversion/recovery metrics */}
      <div className="space-y-1">
        {data.map((cat) => {
          const isSelected = selectedCategory === cat.endgame_class;
          const conversionText = formatConversionMetric(cat.conversion_pct, cat.conversion_wins, cat.conversion_games);
          const recoveryText = formatConversionMetric(cat.recovery_pct, cat.recovery_saves, cat.recovery_games);

          return (
            <button
              key={cat.endgame_class}
              data-testid={`endgame-category-${cat.slug}`}
              aria-pressed={isSelected}
              aria-label={`${cat.label} endgame category`}
              onClick={() => {
                if (isSelected) {
                  onSelectedCategoryClick();
                } else {
                  onCategoryClick(cat.endgame_class);
                }
              }}
              className={cn(
                'w-full text-left rounded px-2 py-1.5 transition-colors cursor-pointer',
                isSelected
                  ? 'bg-muted/50 ring-1 ring-primary/40'
                  : 'hover:bg-muted/30',
              )}
            >
              {/* Category label with per-type info popover and game count */}
              <div className="flex items-center justify-between mb-1">
                <span className="inline-flex items-center gap-1">
                  <span className="text-sm font-medium">{cat.label}</span>
                  <InfoPopover
                    ariaLabel={`${cat.label} endgame type info`}
                    testId={`endgame-type-info-${cat.slug}`}
                    side="top"
                  >
                    {ENDGAME_TYPE_DESCRIPTIONS[cat.endgame_class]}
                  </InfoPopover>
                </span>
                <span className="text-xs text-muted-foreground">
                  {cat.total} games
                  {cat.total < MIN_GAMES_FOR_RELIABLE_STATS && (
                    <span className="text-xs text-amber-500 ml-1" title="Small sample size — percentages may be unreliable">
                      (low sample)
                    </span>
                  )}
                </span>
              </div>

              {/* Stacked WDL bar with glass overlay — dimmed for low sample size categories */}
              <div className={cn('flex h-5 w-full overflow-hidden rounded mb-0', cat.total < MIN_GAMES_FOR_RELIABLE_STATS && 'opacity-50')}>
                {cat.win_pct > 0 && (
                  <div
                    className="transition-all"
                    style={{ width: `${cat.win_pct}%`, backgroundColor: WDL_WIN, backgroundImage: GLASS_OVERLAY }}
                  />
                )}
                {cat.draw_pct > 0 && (
                  <div
                    className="transition-all"
                    style={{ width: `${cat.draw_pct}%`, backgroundColor: WDL_DRAW, backgroundImage: GLASS_OVERLAY }}
                  />
                )}
                {cat.loss_pct > 0 && (
                  <div
                    className="transition-all"
                    style={{ width: `${cat.loss_pct}%`, backgroundColor: WDL_LOSS, backgroundImage: GLASS_OVERLAY }}
                  />
                )}
              </div>

              {/* Grey-outlined game count bar — proportional to max category total */}
              <div className="h-2 mt-0.5 mb-1">
                <div
                  className="h-full rounded-sm"
                  style={{
                    width: `${(cat.total / maxTotal) * 100}%`,
                    border: '1px solid oklch(0.6 0 0)',
                    backgroundColor: 'transparent',
                  }}
                />
              </div>

              {/* WDL percentages */}
              <div className="flex gap-3 text-xs text-muted-foreground mb-1">
                <span style={{ color: WDL_WIN }}>W: {cat.win_pct.toFixed(0)}%</span>
                <span style={{ color: WDL_DRAW }}>D: {cat.draw_pct.toFixed(0)}%</span>
                <span style={{ color: WDL_LOSS }}>L: {cat.loss_pct.toFixed(0)}%</span>
              </div>

              {/* Conversion mini-bar */}
              {cat.conversion_games > 0 && (
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-[10px] text-muted-foreground w-7 shrink-0">Conv</span>
                  <div className="flex h-3 flex-1 overflow-hidden rounded">
                    <div style={{ width: `${cat.conversion_pct}%`, backgroundColor: WDL_WIN }} />
                    <div style={{ width: `${100 - cat.conversion_pct}%`, backgroundColor: WDL_LOSS }} />
                  </div>
                  <span className="text-[10px] text-muted-foreground shrink-0">{conversionText}</span>
                </div>
              )}

              {/* Recovery mini-bar */}
              {cat.recovery_games > 0 && (
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[10px] text-muted-foreground w-7 shrink-0">Recv</span>
                  <div className="flex h-3 flex-1 overflow-hidden rounded">
                    <div style={{ width: `${cat.recovery_pct}%`, backgroundColor: WDL_DRAW }} />
                    <div style={{ width: `${100 - cat.recovery_pct}%`, backgroundColor: WDL_LOSS }} />
                  </div>
                  <span className="text-[10px] text-muted-foreground shrink-0">{recoveryText}</span>
                </div>
              )}

              {/* Fallback: show text if no mini-bars */}
              {cat.conversion_games === 0 && cat.recovery_games === 0 && (
                <p className="text-xs text-muted-foreground">
                  Conversion: {conversionText} · Recovery: {recoveryText}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
