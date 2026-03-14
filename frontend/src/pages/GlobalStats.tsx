import { useState } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useGlobalStats } from '@/hooks/useStats';
import { GlobalStatsCharts } from '@/components/stats/GlobalStatsCharts';
import type { Recency } from '@/types/api';

export function GlobalStatsPage() {
  const [recency, setRecency] = useState<Recency | null>(null);
  const { data: globalStats, isLoading } = useGlobalStats(recency);

  return (
    <div data-testid="global-stats-page" className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Global Stats</h1>

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
        <GlobalStatsCharts
          byTimeControl={globalStats?.by_time_control ?? []}
          byColor={globalStats?.by_color ?? []}
        />
      )}
    </div>
  );
}
