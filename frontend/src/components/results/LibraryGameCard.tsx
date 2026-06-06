import { BookOpen, Calendar, Clock, Equal, ExternalLink, Hash, Minus, Plus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WDL_BORDER_DRAW, WDL_BORDER_LOSS, WDL_BORDER_WIN } from '@/lib/theme';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { SeverityBadge } from '@/components/library/SeverityBadge';
import { TagChip } from '@/components/library/TagChip';
import { NoAnalysisState } from '@/components/library/NoAnalysisState';
import { gamePlatformUrl } from '@/lib/platformLinks';
import type { GameFlawCard, FlawSeverity } from '@/types/library';
import type { UserResult } from '@/types/api';

// Standalone component per D-05 — do NOT import from or modify GameCard.tsx.
// formatDate / formatTimeControl copied verbatim from GameCard.tsx (same display requirements).

interface LibraryGameCardProps {
  game: GameFlawCard;
}

const MOBILE_BOARD_SIZE = 105;
const DESKTOP_BOARD_SIZE = 100;

const RESULT_CLASSES: Record<UserResult, string> = {
  win: 'bg-green-600/20 text-green-400 border-green-600/30',
  draw: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  loss: 'bg-red-600/20 text-red-400 border-red-600/30',
};
const RESULT_ICONS: Record<UserResult, LucideIcon> = { win: Plus, draw: Equal, loss: Minus };
const BORDER_COLORS: Record<UserResult, string> = {
  win: WDL_BORDER_WIN,
  draw: WDL_BORDER_DRAW,
  loss: WDL_BORDER_LOSS,
};

// Severity order for the badge row (must not wrap — sized to full-label nowrap row).
const SEVERITY_ORDER: FlawSeverity[] = ['blunder', 'mistake', 'inaccuracy'];

// Copied verbatim from GameCard.tsx — same display requirements (D-05 forbids shared import).
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

const SECONDS_PER_DAY = 86400;

// Copied verbatim from GameCard.tsx — same display requirements (D-05 forbids shared import).
function formatTimeControl(tcStr: string): string {
  // PGN daily/correspondence format: "1/{seconds_per_move}" (e.g. "1/259200" = 3 days/move).
  // Used by chess.com daily and lichess correspondence. Render as "Nd".
  // Previously fell through to Number("1/259200") = NaN, producing "Classical · NaN".
  if (tcStr.startsWith('1/')) {
    const secondsPerMove = Number(tcStr.slice(2));
    const days = Math.round(secondsPerMove / SECONDS_PER_DAY);
    return `${days}d`;
  }
  if (tcStr.includes('+')) {
    const [baseSec, inc] = tcStr.split('+');
    const baseMin = Math.floor(Number(baseSec) / 60);
    return `${baseMin}+${inc}`;
  }
  // No increment — just convert seconds to minutes
  const baseMin = Math.floor(Number(tcStr) / 60);
  return String(baseMin);
}

/**
 * Analyzed game card for the Library Games subtab.
 *
 * Standalone component per D-05 — does NOT extend or modify GameCard. Borrows
 * GameCard's metadata/board/platform patterns but adds a full-width header,
 * 3-column desktop body with a dashed flaw column, and a flaw block on mobile.
 *
 * Flaw column branches on analysis_state:
 * - "analyzed"         → SeverityBadge × 3 (nowrap row) + TagChip row (flex-wrap)
 * - "no_engine_analysis" → NoAnalysisState pill (never shows "0 Blunders")
 *
 * Security: all user-provided strings (usernames, opening name, platform_url) are
 * rendered as React children or href (auto-escaped). platform_url uses
 * target="_blank" rel="noopener noreferrer" to prevent reverse-tabnabbing (T-107-10).
 */
export function LibraryGameCard({ game }: LibraryGameCardProps) {
  const whiteName = game.white_username ?? '?';
  const blackName = game.black_username ?? '?';
  const whiteRating = game.white_rating !== null ? `(${game.white_rating})` : '';
  const blackRating = game.black_rating !== null ? `(${game.black_rating})` : '';

  // Result indicator: small colored chip with +/=/− icon.
  const ResultIcon = RESULT_ICONS[game.user_result];
  const resultIndicator = (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded border h-3.5 w-3.5 shrink-0',
        RESULT_CLASSES[game.user_result],
      )}
      aria-label={game.user_result}
    >
      <ResultIcon className="h-2.5 w-2.5" strokeWidth={3} />
    </span>
  );

  // Platform icon + external link — verbatim from GameCard.tsx (T-107-10 mitigated).
  // lichess link opens from the user's side (board flipped for black); chess.com
  // has no orientation URL param, so it is unchanged (see lib/platformLinks.ts).
  const gameUrl = gamePlatformUrl(game.platform, game.platform_url, game.user_color);
  const platformIconAndLink = (
    <span className="ml-auto shrink-0 flex items-center gap-1.5 text-muted-foreground">
      <PlatformIcon platform={game.platform} className="h-4 w-4" />
      {gameUrl ? (
        <Tooltip content="Open game on platform">
          <a
            href={gameUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
            aria-label="Open game on platform"
            data-testid={`game-card-link-${game.game_id}`}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </Tooltip>
      ) : null}
    </span>
  );

  // HEADER — full-width, bottom-bordered.
  // Desktop: single-line "■ White (rating) vs □ Black (rating)" in text-sm font-bold.
  // Mobile: two stacked lines in text-sm (weight 400), no "vs".

  const desktopHeader = (
    <div className="hidden sm:flex items-center gap-2 pb-2 mb-2 border-b border-border">
      <span className="text-sm font-bold truncate">
        <span className="text-foreground">■ {whiteName} {whiteRating}</span>
        <span className="mx-1.5 text-muted-foreground">vs</span>
        <span className="text-foreground">□ {blackName} {blackRating}</span>
      </span>
      {platformIconAndLink}
    </div>
  );

  const mobileHeader = (
    <div className="flex sm:hidden items-center gap-2 pb-2 mb-2 border-b border-border">
      <div className="flex-1 min-w-0 flex flex-col text-sm">
        <span className="text-foreground truncate">■ {whiteName} {whiteRating}</span>
        <span className="text-foreground truncate">□ {blackName} {blackRating}</span>
      </div>
      {platformIconAndLink}
    </div>
  );

  // Opening line
  const openingLine = (
    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <BookOpen className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">
        {game.opening_name ?? <span className="italic">Unknown Opening</span>}
      </span>
    </div>
  );

  // Metadata items
  const dateItem = game.played_at && (
    <span className="inline-flex items-center gap-1">
      <Calendar className="h-3.5 w-3.5" />
      {formatDate(game.played_at)}
    </span>
  );

  const timeControlItem = game.time_control_bucket && (
    <span className="inline-flex items-center gap-1">
      <Clock className="h-3.5 w-3.5" />
      <span className="capitalize">{game.time_control_bucket}</span>
      {game.time_control_str ? ` · ${formatTimeControl(game.time_control_str)}` : ''}
    </span>
  );

  const terminationItem = game.termination && game.termination !== 'unknown' && (
    <span className="inline-flex items-center gap-1 capitalize">
      {resultIndicator}
      {game.termination}
    </span>
  );

  // Mobile: vertical stack; move count omitted (matching GameCard mobile behavior).
  const mobileMetadata = (
    <div className="flex flex-col gap-1 text-sm text-muted-foreground">
      {dateItem}
      {timeControlItem}
      {terminationItem}
    </div>
  );

  // Desktop: wrap row; order: termination · date · tc · move count.
  const desktopMetadata = (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
      {terminationItem}
      {dateItem}
      {timeControlItem}
      {game.move_count !== null && (
        <span className="inline-flex items-center gap-1">
          <Hash className="h-3.5 w-3.5" />
          {game.move_count} moves
        </span>
      )}
    </div>
  );

  // Flaw column / block content — branches on analysis_state.
  // When "no_engine_analysis": severity_counts is null; never read it (T-107-11 mitigated).
  const flawContent =
    game.analysis_state === 'analyzed' ? (
      <>
        {/* Severity count row — nowrap so the flaw column sizes to fit all three badges */}
        <div
          className="flex items-center gap-1.5 flex-nowrap"
          data-testid={`severity-row-${game.game_id}`}
        >
          {SEVERITY_ORDER.map((sev) => {
            const counts = game.severity_counts;
            // noUncheckedIndexedAccess: narrow severity_counts before reading.
            const count = counts !== null ? (counts[sev] ?? 0) : 0;
            return (
              <SeverityBadge
                key={sev}
                severity={sev}
                count={count}
                gameId={game.game_id}
              />
            );
          })}
        </div>
        {/* Tag chip row — flex-wrap allowed */}
        {game.chips.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {game.chips.map((tag) => (
              <TagChip key={tag} tag={tag} gameId={game.game_id} />
            ))}
          </div>
        )}
      </>
    ) : (
      <NoAnalysisState gameId={game.game_id} />
    );

  return (
    <article
      data-testid={`library-game-card-${game.game_id}`}
      className="charcoal-texture border border-border/20 border-l-4 rounded px-4 py-3"
      style={{ borderLeftColor: BORDER_COLORS[game.user_result] }}
    >
      {/* Full-width header (desktop single-line, mobile two-line) */}
      {desktopHeader}
      {mobileHeader}

      {/* Mobile body: board + info row, then full-width flaw block below */}
      <div className="flex flex-col gap-2 sm:hidden">
        <div className="flex gap-3 items-start">
          {game.result_fen && (
            <LazyMiniBoard
              fen={game.result_fen}
              flipped={game.user_color === 'black'}
              size={MOBILE_BOARD_SIZE}
            />
          )}
          <div className="flex-1 min-w-0 flex flex-col gap-1">
            {openingLine}
            {mobileMetadata}
          </div>
        </div>
        {/* Full-width flaw block on mobile */}
        <div className="flex flex-col gap-2">
          {flawContent}
        </div>
      </div>

      {/* Desktop body: 3 columns — board / info / flaw column */}
      <div className="hidden sm:flex gap-3 items-start">
        {/* Col 1: mini board */}
        {game.result_fen && (
          <LazyMiniBoard
            fen={game.result_fen}
            flipped={game.user_color === 'black'}
            size={DESKTOP_BOARD_SIZE}
          />
        )}
        {/* Col 2: info (opening + metadata) */}
        <div className="min-w-0 flex-1 flex flex-col gap-2">
          {openingLine}
          {desktopMetadata}
        </div>
        {/* Col 3: flaw column — dashed left border, flex: 0 0 auto so it sizes to the nowrap badge row */}
        <div
          className="pl-4 border-l border-dashed border-border flex flex-col gap-2"
          style={{ flex: '0 0 auto' }}
        >
          {flawContent}
        </div>
      </div>
    </article>
  );
}
