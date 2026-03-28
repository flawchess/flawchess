/**
 * Canonical WDL data shape for the shared WDLChartRow component.
 * WDLStats, WDLByCategory, and EndgameWDLSummary all satisfy this interface.
 */
export interface WDLRowData {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}
