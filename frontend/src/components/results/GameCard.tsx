import { useRef, useState, useEffect } from 'react';
import { BookOpen, Calendar, Clock, ExternalLink, Hash, Swords } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { MiniBoard } from '@/components/board/MiniBoard';
import type { GameRecord, UserResult } from '@/types/api';

interface GameCardProps {
  game: GameRecord;
}

/** Renders MiniBoard only when the card scrolls into view. */
function LazyMiniBoard({ fen, flipped }: { fen: string; flipped: boolean }) {
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
    <div ref={ref} className="w-[100px] h-[100px] shrink-0 rounded overflow-hidden bg-muted">
      {visible && <MiniBoard fen={fen} size={100} flipped={flipped} />}
    </div>
  );
}

const RESULT_LABELS: Record<UserResult, string> = { win: 'W', draw: 'D', loss: 'L' };
const RESULT_CLASSES: Record<UserResult, string> = {
  win: 'bg-green-600/20 text-green-400 border-green-600/30',
  draw: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  loss: 'bg-red-600/20 text-red-400 border-red-600/30',
};
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

  return (
    <div
      data-testid={`game-card-${game.game_id}`}
      className={cn(
        'border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3 flex flex-col gap-2',
        BORDER_CLASSES[game.user_result],
      )}
    >
      {/* Top row: Result badge + both players + platform link (full width) */}
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold shrink-0',
            RESULT_CLASSES[game.user_result],
          )}
        >
          {RESULT_LABELS[game.user_result]}
        </span>
        <span className="text-sm truncate">
          <span className="text-foreground">
            ■ {whiteName} {whiteRating}
          </span>
          <span className="mx-1.5 text-muted-foreground">vs</span>
          <span className="text-foreground">
            □ {blackName} {blackRating}
          </span>
        </span>
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
      </div>

      {/* Body row: lazy-rendered minimap left, opening + metadata right */}
      <div className="flex gap-3 items-start">
        {game.result_fen && (
          <LazyMiniBoard
            fen={game.result_fen}
            flipped={game.user_color === 'black'}
          />
        )}

        <div className="flex-1 min-w-0 flex flex-col gap-2">
          {/* Opening name with BookOpen icon */}
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <BookOpen className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate" data-testid={`game-card-opening-${game.game_id}`}>
              {game.opening_name ?? <span className="italic">Unknown Opening</span>}
            </span>
          </div>

          {/* Metadata with icons — date first, then time control */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            {/* Date — omit entirely if played_at is null */}
            {game.played_at && (
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {formatDate(game.played_at)}
              </span>
            )}
            {/* Time control — omit entirely if time_control_bucket is null */}
            {game.time_control_bucket && (
              <span className="inline-flex items-center gap-1" data-testid={`game-card-tc-${game.game_id}`}>
                <Clock className="h-3.5 w-3.5" />
                <span className="capitalize">{game.time_control_bucket}</span>
                {game.time_control_str ? ` · ${formatTimeControl(game.time_control_str)}` : ''}
              </span>
            )}
            {/* Termination — omit if null or 'unknown' */}
            {game.termination && game.termination !== 'unknown' && (
              <span className="inline-flex items-center gap-1 capitalize" data-testid={`game-card-termination-${game.game_id}`}>
                <Swords className="h-3.5 w-3.5" />
                {game.termination}
              </span>
            )}
            {/* Move count — omit if null */}
            {game.move_count !== null && (
              <span className="inline-flex items-center gap-1">
                <Hash className="h-3.5 w-3.5" />
                {game.move_count} moves
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
