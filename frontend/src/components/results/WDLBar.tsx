import { WDLChartRow } from '@/components/charts/WDLChartRow';
import type { WDLStats } from '@/types/api';

interface WDLBarProps {
  stats: WDLStats;
}

export function WDLBar({ stats }: WDLBarProps) {
  return <WDLChartRow data={stats} barHeight="h-6" />;
}
