import { ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GameRecord, UserResult } from '@/types/api';

interface GameCardProps {
  game: GameRecord;
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

function formatOpening(name: string | null, eco: string | null): string {
  if (eco && name) return `${eco} ${name}`;
  if (eco) return eco;
  if (name) return name;
  return '—';
}

export function GameCard({ game }: GameCardProps) {
  const whiteName = game.white_username ?? '?';
  const blackName = game.black_username ?? '?';
  const whiteRating = game.white_rating !== null ? `(${game.white_rating})` : '';
  const blackRating = game.black_rating !== null ? `(${game.black_rating})` : '';
  const isUserWhite = game.user_color === 'white';

  return (
    <div
      data-testid={`game-card-${game.game_id}`}
      className={cn(
        'border-l-4 bg-card border border-border rounded px-4 py-3',
        BORDER_CLASSES[game.user_result],
      )}
    >
      {/* Line 1: Result badge + both players + platform link */}
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
          <span
            className={!isUserWhite ? 'font-semibold text-foreground' : 'text-muted-foreground'}
          >
            ○ {whiteName} {whiteRating}
          </span>
          <span className="mx-1.5 text-muted-foreground">vs</span>
          <span
            className={isUserWhite ? 'font-semibold text-foreground' : 'text-muted-foreground'}
          >
            ● {blackName} {blackRating}
          </span>
        </span>
        {game.platform_url ? (
          <a
            href={game.platform_url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto shrink-0 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Open game on platform"
            data-testid={`game-card-link-${game.game_id}`}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        ) : (
          <span className="ml-auto shrink-0 text-muted-foreground text-xs">{game.platform}</span>
        )}
      </div>

      {/* Line 2: Opening, time control, date, moves */}
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
        <span className="truncate max-w-[200px]">{formatOpening(game.opening_name, game.opening_eco)}</span>
        {game.time_control_bucket && (
          <span className="capitalize">{game.time_control_bucket}</span>
        )}
        <span>{formatDate(game.played_at)}</span>
        <span>{game.move_count !== null ? `${game.move_count} moves` : '—'}</span>
      </div>
    </div>
  );
}
