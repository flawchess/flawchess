import { ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { GameRecord, UserResult } from '@/types/api';

interface GameTableProps {
  games: GameRecord[];
  matchedCount: number;
  totalGames: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

const RESULT_LABELS: Record<UserResult, string> = { win: 'W', draw: 'D', loss: 'L' };
const RESULT_CLASSES: Record<UserResult, string> = {
  win: 'bg-green-600/20 text-green-400 border-green-600/30',
  draw: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  loss: 'bg-red-600/20 text-red-400 border-red-600/30',
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

export function GameTable({
  games,
  matchedCount,
  totalGames,
  offset,
  limit,
  onPageChange,
}: GameTableProps) {
  const totalPages = Math.max(1, Math.ceil(matchedCount / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-3">
      {/* Matched count */}
      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{matchedCount}</span> of{' '}
        <span className="font-medium text-foreground">{totalGames}</span> games matched
      </p>

      {games.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">No games to display</p>
      ) : (
        <>
          {/* Table */}
          <div className="overflow-x-auto rounded border border-border">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">Result</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">Opponent</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">Date</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">TC</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {games.map((game) => (
                  <tr key={game.game_id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold',
                          RESULT_CLASSES[game.user_result],
                        )}
                      >
                        {RESULT_LABELS[game.user_result]}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-foreground">
                      {game.opponent_username ?? '—'}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {formatDate(game.played_at)}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground capitalize">
                      {game.time_control_bucket ?? '—'}
                    </td>
                    <td className="px-3 py-2">
                      {game.platform_url ? (
                        <a
                          href={game.platform_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-muted-foreground hover:text-foreground transition-colors"
                          aria-label="Open game"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => onPageChange(offset - limit)}
              >
                &lt;
              </Button>

              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <Button
                  key={page}
                  variant={page === currentPage ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => onPageChange((page - 1) * limit)}
                  className="min-w-8"
                >
                  {page}
                </Button>
              ))}

              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage === totalPages}
                onClick={() => onPageChange(offset + limit)}
              >
                &gt;
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
