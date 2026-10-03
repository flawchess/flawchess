import type { ReactElement } from 'react';
import { Cpu } from 'lucide-react';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { EngineLines, EngineLinesSkeleton, engineLinesMinHeightPx } from '@/components/analysis/EngineLines';
import { MaiaHumanPanel } from '@/components/analysis/MaiaHumanPanel';
import type { MaiaHumanPanelProps } from '@/components/analysis/MaiaHumanPanel';
import { PasteModal } from '@/components/analysis/PasteModal';
import type { PasteParseResult } from '@/lib/pastedGame';
import { VariationTreePanel, MoveListHeaderContent } from '@/components/analysis/AnalysisTabs';
import type { VariationTreePanelProps } from '@/components/analysis/AnalysisTabs';
import { EngineToggleHeader } from '@/components/analysis/EngineToggleHeader';
import { STOCKFISH_ACCENT } from '@/lib/theme';
import type { MoveGrade } from '@/lib/moveQuality';
import type { PvLine } from '@/hooks/uciParser';

/**
 * AnalysisDesktopCards — the shared desktop/mid cards, extracted from
 * `Analysis.tsx`'s `stockfishCard`/`movesCard`/`desktopMaiaPanel`/`pasteModalNode`
 * render fragments (215-06). Each is reused verbatim between the mid-range
 * two-column layout and the desktop 3-column layout (single mount — only one
 * return branch renders).
 */

const ENGINE_NAME = 'Stockfish 18';
/** Card-body chrome (px) on top of the engine-lines region: 78 - 60, so the default
 *  2-line card keeps its pre-Phase-228 78px body height exactly. */
const STOCKFISH_CARD_BODY_CHROME_PX = 18;

// ─── StockfishCard ──────────────────────────────────────────────────────────────

export type StockfishCardProps = {
  /** Stockfish lines setting (1-5): rows and skeleton rows (Phase 228 D-16). */
  sfLines: number;
  engineEnabled: boolean;
  setEngineEnabled: (enabled: boolean) => void;
  reconciledBestEval: MoveGrade;
  engineLoading: boolean;
  reconciledPvLines: PvLine[];
  isAnalyzing: boolean;
  currentPly: number;
  position: string;
  boardFlipped: boolean;
  onMoveClick: (uciMoves: string[]) => void;
};

// Stockfish engine info + lines card (155/162 UAT: reconciled top-N over the
// grading union).
export function StockfishCard({
  sfLines,
  engineEnabled,
  setEngineEnabled,
  reconciledBestEval,
  engineLoading,
  reconciledPvLines,
  isAnalyzing,
  currentPly,
  position,
  boardFlipped,
  onMoveClick,
}: StockfishCardProps): ReactElement {
  return (
    <Card data-testid="analysis-engine-card">
      <CardHeader size="compact" data-testid="analysis-engine-info" className="font-normal text-muted-foreground">
        <EngineToggleHeader
          checked={engineEnabled}
          onCheckedChange={setEngineEnabled}
          accent={STOCKFISH_ACCENT}
          testId="btn-analysis-engine-toggle"
          ariaLabel="Toggle Stockfish engine"
          icon={Cpu}
        >
          {ENGINE_NAME}
          {engineEnabled && reconciledBestEval.depth > 0 ? `, Depth ${reconciledBestEval.depth}` : ''}
        </EngineToggleHeader>
      </CardHeader>
      <CardBody
        className="p-2"
        style={{ minHeight: engineLinesMinHeightPx(sfLines) + STOCKFISH_CARD_BODY_CHROME_PX }}
      >
        {engineLoading ? (
          <EngineLinesSkeleton testId="analysis-engine-loading" rows={sfLines} />
        ) : !engineEnabled ? (
          <div className="flex h-full items-center px-2 text-sm text-muted-foreground">Engine off</div>
        ) : (
          <EngineLines
            pvLines={reconciledPvLines}
            maxLines={sfLines}
            isAnalyzing={isAnalyzing}
            startPly={currentPly}
            baseFen={position}
            flipped={boardFlipped}
            onMoveClick={onMoveClick}
          />
        )}
      </CardBody>
    </Card>
  );
}

// ─── MovesCard ──────────────────────────────────────────────────────────────────

export type MovesCardProps = {
  onOpenPasteModal: () => void;
  variationTreeProps: Omit<VariationTreePanelProps, 'variant'>;
};

// Move-list card (desktop side panel): variation tree fills and scrolls
// internally. `flex-1 min-h-0` needs a height-bounded flex parent (the
// board-height region) so the tree's absolute-fill scroller has a definite
// height (a 0-height parent would render an empty list). The board controls no
// longer sit in a footer band here — they moved under the board inside
// DesktopBoardStage (hugging the board like the mid layout).
export function MovesCard({ onOpenPasteModal, variationTreeProps }: MovesCardProps): ReactElement {
  return (
    <Card data-testid="analysis-movelist-card" className="relative flex min-h-0 flex-1 flex-col">
      <CardHeader size="compact" data-testid="analysis-movelist-header">
        <MoveListHeaderContent onOpenPasteModal={onOpenPasteModal} />
      </CardHeader>
      <VariationTreePanel variant="responsive" {...variationTreeProps} />
    </Card>
  );
}

// ─── DesktopMaiaPanel ───────────────────────────────────────────────────────────

export type DesktopMaiaPanelProps = MaiaHumanPanelProps;

// Maia move-quality panel (desktop/mid, non-compact — no in-card ELO footer; the
// slider is a standalone row/cell next to it). The mobile Maia tab renders its own
// compact copy (`HumanTab` in AnalysisTabs.tsx).
export function DesktopMaiaPanel(props: DesktopMaiaPanelProps): ReactElement {
  return <MaiaHumanPanel {...props} />;
}

// ─── PasteModalNode ─────────────────────────────────────────────────────────────

export type PasteModalNodeProps = {
  pasteModalOpen: boolean;
  setPasteModalOpen: (open: boolean) => void;
  onLoad: (result: PasteParseResult, userColor: 'white' | 'black') => void;
  onSaved: (savedGameId: number) => void;
};

// Phase 208 (D-19/D-20): the paste modal — rendered into all three layout
// branches (mid/mobile/desktop return at different points), mirroring the
// "analysis-page" testid pattern already used the same way. Only one branch
// mounts per render, and Dialog itself portals its content, so duplicating the
// render site across branches is safe and matches the existing per-branch
// pattern in this file rather than introducing a new one.
export function PasteModalNode({
  pasteModalOpen,
  setPasteModalOpen,
  onLoad,
  onSaved,
}: PasteModalNodeProps): ReactElement {
  return (
    <PasteModal open={pasteModalOpen} onOpenChange={setPasteModalOpen} onLoad={onLoad} onSaved={onSaved} />
  );
}
