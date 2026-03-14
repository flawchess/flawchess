import { useState } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useRatingHistory } from '@/hooks/useStats';
import { RatingChart } from '@/components/stats/RatingChart';
import type { Recency } from '@/types/api';

export function RatingPage() {
  const [recency, setRecency] = useState<Recency | null>(null);
  const { data: ratingData, isLoading } = useRatingHistory(recency);

  return (
    <div data-testid="rating-page" className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Rating</h1>

      {/* Recency filter */}
      <div>
        <p className="mb-1 text-xs text-muted-foreground">Recency</p>
        <Select
          value={recency ?? 'all'}
          onValueChange={(v) => setRecency(v === 'all' ? null : (v as Recency))}
        >
          <SelectTrigger size="sm" data-testid="filter-recency">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All time</SelectItem>
            <SelectItem value="week">Past week</SelectItem>
            <SelectItem value="month">Past month</SelectItem>
            <SelectItem value="3months">3 months</SelectItem>
            <SelectItem value="6months">6 months</SelectItem>
            <SelectItem value="year">1 year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground">Loading...</div>
      ) : (
        <>
          <section className="space-y-3">
            <h2 className="text-lg font-medium">Chess.com Rating</h2>
            <RatingChart data={ratingData?.chess_com ?? []} platform="Chess.com" />
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-medium">Lichess Rating</h2>
            <RatingChart data={ratingData?.lichess ?? []} platform="Lichess" />
          </section>
        </>
      )}
    </div>
  );
}
