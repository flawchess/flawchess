import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { DownloadIcon, LayoutDashboard } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { useUserProfile } from '@/hooks/useUserProfile';
import { ImportTab } from '@/pages/library/ImportTab';
import { OverviewTab } from '@/pages/library/OverviewTab';
import type { ImportPageProps } from '@/pages/Import';

export function LibraryPage({
  onImportStarted,
  activeJobIds,
  onJobDismissed,
}: ImportPageProps) {
  const { data: profile } = useUserProfile();
  const location = useLocation();
  const navigate = useNavigate();

  const totalGames =
    profile != null
      ? profile.chess_com_game_count + profile.lichess_game_count
      : 0;
  const noGames = profile != null && totalGames === 0;

  // State-dependent default subtab redirect (D-06): only redirect once profile is loaded
  // (profile != null), mirroring how Openings/Endgames gate their page-level Navigate.
  if (
    (location.pathname === '/library' || location.pathname === '/library/') &&
    profile != null
  ) {
    return (
      <Navigate to={noGames ? '/library/import' : '/library/overview'} replace />
    );
  }

  const activeTab = location.pathname.includes('/import') ? 'import' : 'overview';

  return (
    <div data-testid="library-page" className="flex min-h-0 flex-1 flex-col bg-background">
      {/* Wrapper is a <div>, not <main>: the embedded subtab pages (ImportPage,
          GlobalStatsPage) each render their own <main>, and App already wraps
          routes in a <main>. A <main> here would produce triple-nested <main>
          landmarks (invalid HTML, LIB-09). Openings/Endgames use <main> here
          because their subtabs are bare fragments; Library's are full pages. */}
      <div className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">

        {/* Desktop: Tabs above content */}
        <div className="hidden md:block">
          <Tabs value={activeTab} onValueChange={(val) => navigate(`/library/${val}`)}>
            <TabsList variant="brand" className="w-full" data-testid="library-tabs">
              <TabsTrigger value="import" data-testid="tab-import" className="flex-1">
                <DownloadIcon className="mr-1.5 h-4 w-4" />
                Import
              </TabsTrigger>
              <TabsTrigger value="overview" data-testid="tab-overview" className="flex-1">
                <LayoutDashboard className="mr-1.5 h-4 w-4" />
                Overview
              </TabsTrigger>
            </TabsList>
            <TabsContent value="import" className="mt-4">
              <ImportTab
                onImportStarted={onImportStarted}
                activeJobIds={activeJobIds}
                onJobDismissed={onJobDismissed}
              />
            </TabsContent>
            <TabsContent value="overview" className="mt-4">
              <OverviewTab />
            </TabsContent>
          </Tabs>
        </div>

        {/* Mobile: sticky subnav row + content */}
        <div className="md:hidden flex flex-col min-w-0">
          <Tabs
            value={activeTab}
            onValueChange={(val) => {
              navigate(`/library/${val}`);
              window.scrollTo({ top: 0 });
            }}
          >
            <div
              className="sticky top-0 z-20 flex items-center gap-2 h-[52px] bg-white/20 backdrop-blur-md rounded-md px-1 py-1"
              data-testid="library-mobile-control-row"
            >
              <TabsList
                variant="brand"
                className="flex-1 !h-full !p-0"
                data-testid="library-tabs-mobile"
              >
                <TabsTrigger
                  value="import"
                  className="flex-1"
                  data-testid="tab-import-mobile"
                >
                  <DownloadIcon className="mr-1.5 h-4 w-4" />
                  Import
                </TabsTrigger>
                <TabsTrigger
                  value="overview"
                  className="flex-1"
                  data-testid="tab-overview-mobile"
                >
                  <LayoutDashboard className="mr-1.5 h-4 w-4" />
                  Overview
                </TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="import" className="mt-4">
              <ImportTab
                onImportStarted={onImportStarted}
                activeJobIds={activeJobIds}
                onJobDismissed={onJobDismissed}
              />
            </TabsContent>
            <TabsContent value="overview" className="mt-4">
              <OverviewTab />
            </TabsContent>
          </Tabs>
        </div>

      </div>
    </div>
  );
}
