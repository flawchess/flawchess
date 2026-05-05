/**
 * Board container layout helpers for the Openings page.
 *
 * Extracted to a standalone module so the react-refresh ESLint rule is
 * satisfied (component files may only export components) and so the logic
 * is directly unit-testable without rendering the full Openings page.
 */

/**
 * Returns the className for the desktop board container.
 * On the Stats and Insights subtabs, lg:hidden hides the board to free
 * horizontal space (Stats: D-03; Insights: 2-column white/black layout).
 * The ChessBoard JSX element is NOT removed so chess.js state is preserved
 * across tab switches (Pitfall 7).
 */
export function getBoardContainerClassName(activeTab: string): string {
  const hideOnLg = activeTab === 'stats' || activeTab === 'insights';
  return `flex flex-col gap-2 w-[400px] shrink-0${hideOnLg ? ' lg:hidden' : ''}`;
}
