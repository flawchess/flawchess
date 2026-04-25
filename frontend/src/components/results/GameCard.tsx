import { useRef, useState, useEffect } from 'react';
import { BookOpen, Calendar, Clock, Equal, ExternalLink, Hash, Minus, Plus, Swords } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { MiniBoard } from '@/components/board/MiniBoard';
import type { GameRecord, UserResult } from '@/types/api';

interface GameCardProps {
  game: GameRecord;
}

/** Renders MiniBoard only when the card scrolls into view. */
function LazyMiniBoard({ fen, flipped, size }: { fen: string; flipped: boolean; size: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        // safe: IntersectionObserver always provides at least 1 entry when observing 1 element
        if (entries[0]!.isIntersecting) { setVisible(true); observer.disconnect(); }
      },
      { rootMargin: '200px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="shrink-0 rounded overflow-hidden bg-muted"
      style={{ width: size, height: size }}
    >
      {visible && <MiniBoard fen={fen} size={size} flipped={flipped} />}
    </div>
  );
}

const MOBILE_BOARD_SIZE = 105;
const DESKTOP_BOARD_SIZE = 100;

const RESULT_LABELS: Record<UserResult, string> = { win: 'W', draw: 'D', loss: 'L' };
const RESULT_CLASSES: Record<UserResult, string> = {
  win: 'bg-green-600/20 text-green-400 border-green-600/30',
  draw: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  loss: 'bg-red-600/20 text-red-400 border-red-600/30',
};
const RESULT_ICONS: Record<UserResult, LucideIcon> = { win: Plus, draw: Equal, loss: Minus };
const BORDER_CLASSES: Record<UserResult, string> = {
  win: 'border-l-green-600',
  draw: 'border-l-gray-500',
  loss: 'border-l-red-600',
};

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

export function GameCard({ game }: GameCardProps) {
  const whiteName = game.white_username ?? '?';
  const blackName = game.black_username ?? '?';
  const whiteRating = game.white_rating !== null ? `(${game.white_rating})` : '';
  const blackRating = game.black_rating !== null ? `(${game.black_rating})` : '';

  const resultBadge = (
    <span
      className={cn(
        'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold shrink-0',
        RESULT_CLASSES[game.user_result],
      )}
    >
      {RESULT_LABELS[game.user_result]}
    </span>
  );

  // Mobile result indicator: small colored chip with +/=/− icon — replaces the
  // swords icon next to termination so the W/D/L cue lives on the termination row.
  const ResultIcon = RESULT_ICONS[game.user_result];
  const mobileResultIndicator = (
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

  const platformIconAndLink = (
    <span className="ml-auto shrink-0 flex items-center gap-1.5 text-muted-foreground">
      <PlatformIcon platform={game.platform} className="h-4 w-4" />
      {game.platform_url ? (
        <Tooltip content="Open game on platform">
          <a
            href={game.platform_url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            aria-label="Open game on platform"
            data-testid={`game-card-link-${game.game_id}`}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </Tooltip>
      ) : null}
    </span>
  );

  // Mobile: player names stack on two lines (no "vs" separator); no W/D/L badge —
  // the result is shown next to the termination row via a small +/=/− chip instead.
  const mobileIdentifier = (
    <div className="flex items-center gap-2">
      <div className="flex-1 min-w-0 flex flex-col text-sm">
        <span className="text-foreground truncate">
          ■ {whiteName} {whiteRating}
        </span>
        <span className="text-foreground truncate">
          □ {blackName} {blackRating}
        </span>
      </div>
      {platformIconAndLink}
    </div>
  );

  // Desktop: single-line "White vs Black".
  const desktopIdentifier = (
    <div className="flex items-center gap-2">
      {resultBadge}
      <span className="text-sm truncate">
        <span className="text-foreground">
          ■ {whiteName} {whiteRating}
        </span>
        <span className="mx-1.5 text-muted-foreground">vs</span>
        <span className="text-foreground">
          □ {blackName} {blackRating}
        </span>
      </span>
      {platformIconAndLink}
    </div>
  );

  const openingLine = (
    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <BookOpen className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate" data-testid={`game-card-opening-${game.game_id}`}>
        {game.opening_name ?? <span className="italic">Unknown Opening</span>}
      </span>
    </div>
  );

  const dateItem = game.played_at && (
    <span className="inline-flex items-center gap-1">
      <Calendar className="h-3.5 w-3.5" />
      {formatDate(game.played_at)}
    </span>
  );

  const timeControlItem = game.time_control_bucket && (
    <span className="inline-flex items-center gap-1" data-testid={`game-card-tc-${game.game_id}`}>
      <Clock className="h-3.5 w-3.5" />
      <span className="capitalize">{game.time_control_bucket}</span>
      {game.time_control_str ? ` · ${formatTimeControl(game.time_control_str)}` : ''}
    </span>
  );

  const desktopTerminationItem = game.termination && game.termination !== 'unknown' && (
    <span className="inline-flex items-center gap-1 capitalize" data-testid={`game-card-termination-${game.game_id}`}>
      <Swords className="h-3.5 w-3.5" />
      {game.termination}
    </span>
  );

  // Mobile termination: swords icon replaced with the W/D/L color indicator.
  const mobileTerminationItem = game.termination && game.termination !== 'unknown' && (
    <span className="inline-flex items-center gap-1 capitalize" data-testid={`game-card-termination-${game.game_id}`}>
      {mobileResultIndicator}
      {game.termination}
    </span>
  );

  // Mobile: each indicator on its own line (vertical stack); move count omitted.
  const mobileMetadata = (
    <div className="flex flex-col gap-1 text-sm text-muted-foreground">
      {dateItem}
      {timeControlItem}
      {mobileTerminationItem}
    </div>
  );

  // Desktop: indicators wrap on a single row; includes move count.
  const desktopMetadata = (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
      {dateItem}
      {timeControlItem}
      {desktopTerminationItem}
      {game.move_count !== null && (
        <span className="inline-flex items-center gap-1">
          <Hash className="h-3.5 w-3.5" />
          {game.move_count} moves
        </span>
      )}
    </div>
  );

  return (
    <div
      data-testid={`game-card-${game.game_id}`}
      className={cn(
        'border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3',
        BORDER_CLASSES[game.user_result],
      )}
    >
      {/* Mobile layout: identifier line full width on top, then board + opening/metadata below */}
      <div className="flex flex-col gap-2 sm:hidden">
        {mobileIdentifier}
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
      </div>

      {/* Desktop layout: board left, identifier + opening + metadata stacked right */}
      <div className="hidden sm:flex gap-3 items-center">
        {game.result_fen && (
          <LazyMiniBoard
            fen={game.result_fen}
            flipped={game.user_color === 'black'}
            size={DESKTOP_BOARD_SIZE}
          />
        )}
        <div className="min-w-0 flex-1 flex flex-col gap-2">
          {desktopIdentifier}
          {openingLine}
          {desktopMetadata}
        </div>
      </div>
    </div>
  );
}
