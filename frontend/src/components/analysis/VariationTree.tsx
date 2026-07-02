/**
 * VariationTree — responsive move list for the analysis board (Phase 137 Plan 03).
 *
 * Renders the flat main line plus up to two active nesting levels (Phase 140):
 *   Level 0 — main game line
 *   Level 1 — PV sideline (tactic chip expanded via insertPvLine)
 *   Level 2 — user fork within PV (ephemeral sub-sideline)
 *
 * Responsive split (D-02): mobile extends HorizontalMoveList (horizontal chips
 * with variation inline in parentheses, double-paren for Level-2); desktop uses
 * a vertical paired N. white black list with indented sub-sections.
 * Split is Tailwind dual-DOM (sm:hidden / hidden sm:block) — no media-query hook.
 *
 * Security: node.san comes from chess.js-validated moves, not user input.
 * React auto-escapes all JSX children — no unsafe HTML injection.
 */

import { useRef, useEffect, useState, Fragment } from 'react';
import type { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';
import { HorizontalMoveList } from '@/components/board/HorizontalMoveList';
import type { HorizontalMoveItem } from '@/components/board/HorizontalMoveList';
import { BlunderIcon, MistakeIcon } from '@/components/icons/SeverityGlyphIcon';
import { moveLabel } from '@/lib/moveNumberLabel';
import { tacticMotifLabel, tacticDepthBadge } from '@/lib/tacticComparisonMeta';
import { cn } from '@/lib/utils';
import {
  TAC_MISSED,
  TAC_MISSED_BG,
  TAC_MISSED_BORDER,
  TAC_ALLOWED,
  TAC_ALLOWED_BG,
  TAC_ALLOWED_BORDER,
  ACTIVE_FILTER_RING_CLASS,
} from '@/lib/theme';
import type { FlawSeverity } from '@/types/library';

// Subtle zebra stripe for the desktop move list (Quick 260627-r9g item 2). A faint
// light wash on odd rows; not a semantic color, so a Tailwind opacity utility is fine.
const ZEBRA_ROW_BG = 'bg-foreground/[0.03]';
/** Zebra background for a 0-based row index (odd rows striped). */
function zebraBg(rowIdx: number): string {
  return rowIdx % 2 === 1 ? ZEBRA_ROW_BG : '';
}

// ─── Props ───────────────────────────────────────────────────────────────────

/** Flaw marker entry for a mainLine node — tactic motifs + non-tactic severity. */
export interface FlawMarkerEntry {
  missedMotif: string | null;
  allowedMotif: string | null;
  /** 0-based depth of the missed tactic (display offset applied by tacticDepthBadge). */
  missedDepth: number | null;
  /** 0-based depth of the allowed tactic (display offset applied by tacticDepthBadge). */
  allowedDepth: number | null;
  severity?: FlawSeverity;
  /** FlawMarker.ply — passed to onPvChipClick for the useTacticLines fetch key
   *  (this node's own flaw — allowed chip + severity glyph). */
  ply: number;
  /**
   * Flaw ply for the MISSED chip when it is shown one ply before its flaw
   * (Quick w8k item 5): the decision node hosts the missed tactic that belongs to
   * the flaw at this ply. Defaults to `ply` when the missed tactic is the node's own.
   */
  missedPly?: number;
}

export interface VariationTreeProps {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  currentNodeId: NodeId | null;
  /** Game ply of rootFen, for move-number labels. Default 0. */
  rootPly?: number;
  /** Called with the node id when a move chip is clicked. Wired to goToNode in Phase 138. */
  onNodeClick: (nodeId: NodeId) => void;
  /** Height override passed to the mobile HorizontalMoveList. */
  heightClass?: string;
  /**
   * Optional per-node text color (CSS color string), keyed by node id. Used in
   * tactic mode to mark the depth-0 target (blue) and the blunder (red) in the
   * desktop move list. Applied only on desktop; the current node keeps its
   * primary highlight. Ignored on mobile (the tactic SAN ladder carries the
   * mobile decorations).
   */
  decorations?: Map<NodeId, string>;

  // ── Phase 140: PV nesting + flaw chips ──────────────────────────────────────

  /**
   * IDs of PV nodes grafted by insertPvLine, ordered fork→end. Used to
   * distinguish Level-1 (in pvLine) from Level-2 (forked off pvLine).
   */
  pvLine?: NodeId[];
  /**
   * Flaw marker data keyed by mainLine node id. Only nodes that have at least one
   * tactic motif (missed/allowed) or a non-inaccuracy severity receive an entry.
   * Built by Analysis.tsx from gameData.flaw_markers.
   */
  flawMarkerByNodeId?: Map<NodeId, FlawMarkerEntry>;
  /**
   * Called when the user clicks a missed/allowed chip. Analysis.tsx fetches the
   * PV via useTacticLines and calls insertPvLine on arrival (toggle off if same).
   */
  onPvChipClick?: (nodeId: NodeId, flaw: { ply: number; orientation: 'missed' | 'allowed' }) => void;
  /** The mainLine nodeId whose chip is currently expanded (one at a time). */
  activePvNodeId?: NodeId | null;
  /**
   * Orientation of the currently expanded chip. With the missed chip shown one ply
   * before the flaw (item 5), a single node can host both a missed chip (from the
   * next flaw) and its own allowed chip; the orientation disambiguates which one
   * gets the active ring. Null/undefined → match by node only (legacy behavior).
   */
  activePvOrientation?: 'missed' | 'allowed' | null;
  /** True while the tactic-lines fetch for the active chip is in flight. */
  pvFetchPending?: boolean;
  /** True when the tactic-lines fetch for the active chip returned an error. */
  pvFetchError?: boolean;
  /**
   * Layout variant. `'responsive'` (default) keeps the breakpoint split — horizontal
   * strip on mobile, vertical paired list on desktop. `'vertical'` forces the vertical
   * paired list at every width (used in the mobile analysis Moves tab so the move list
   * fills the available vertical space instead of collapsing to a single horizontal row).
   */
  variant?: 'responsive' | 'vertical';
  /**
   * Game-mode ply the board first lands on (the URL `ply` param, defaulting to 0 — or the
   * tactic fork ply when the entry ply auto-opens a tactic line: decision board `ply-1` for
   * missed, flaw ply for allowed, Quick 260702-fog). When set, the desktop move list aligns
   * the move at this ply to the TOP of the scroller on first open instead of minimal-
   * scrolling it to the bottom (Quick 260628-qta UAT). Omitted / null in free play, where
   * the initial-align is skipped.
   */
  initialPly?: number | null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

interface VariationChain {
  /** mainLine node at which the variation splits off (null when on main line). */
  forkParentId: NodeId | null;
  /** Level-1 chain nodes (pvLine nodes, or regular variation nodes). */
  chain: NodeId[];
  /** Level-2 chain nodes (user forks within the PV). Empty unless level === 2. */
  subChain: NodeId[];
  /** 0 = main line, 1 = in/off pvLine, 2 = user forked within pvLine. */
  level: 0 | 1 | 2;
}

/**
 * Walk from currentNodeId up through parentId pointers to the nearest mainLine
 * ancestor. Returns chain in fork-to-current order and the nesting level.
 *
 * Level 2 detection: if currentNodeId is NOT in pvLine but we cross a pvLine
 * node during the walk (before reaching mainLine), level is 2. The chain is split
 * at the pvLine crossing point into chain (pvLine nodes) and subChain (user fork).
 */
function buildVariationChain(
  nodes: Map<NodeId, MoveNode>,
  mainLine: NodeId[],
  pvLine: NodeId[],
  currentNodeId: NodeId | null,
): VariationChain {
  const empty: VariationChain = { forkParentId: null, chain: [], subChain: [], level: 0 };
  if (currentNodeId === null) return empty;

  const mainLineSet = new Set(mainLine);
  if (mainLineSet.has(currentNodeId)) return empty;

  const pvLineSet = new Set(pvLine);
  const startedOnPvLine = pvLineSet.has(currentNodeId);

  const reversed: NodeId[] = [];
  // Index in reversed where we FIRST hit a pvLine node (only when NOT started on pvLine).
  let pvLineCrossIdx = -1;
  let id: NodeId | null = currentNodeId;

  while (id !== null && !mainLineSet.has(id)) {
    reversed.push(id);
    // Detect pvLine crossing (only meaningful when started off pvLine).
    if (!startedOnPvLine && pvLineSet.has(id) && pvLineCrossIdx === -1) {
      pvLineCrossIdx = reversed.length - 1;
    }
    const node = nodes.get(id);
    id = node?.parentId ?? null;
  }

  const fullChain = reversed.reverse();

  if (pvLineCrossIdx === -1) {
    // Level 1: on the pvLine itself, or a variation off mainLine without pvLine crossing.
    return { forkParentId: id, chain: fullChain, subChain: [], level: 1 };
  }

  // Level 2: started off pvLine, crossed a pvLine node during the walk.
  // pvLineCrossIdx is the index in reversed (reverse-walk order) of the first pvLine node.
  // In fullChain (forward order), the crossing node is at fullChain.length - 1 - pvLineCrossIdx.
  const pvCrossForwardIdx = fullChain.length - 1 - pvLineCrossIdx;
  // chain = pvLine portion (mainLine fork → pvLine crossing node, inclusive).
  const chain = fullChain.slice(0, pvCrossForwardIdx + 1);
  // subChain = user's sub-fork nodes after the pvLine crossing.
  const subChain = fullChain.slice(pvCrossForwardIdx + 1);
  return { forkParentId: id, chain, subChain, level: 2 };
}

/**
 * Resolve which variation chain to render. When a PV sideline exists and the user
 * has NOT forked off it (level !== 2), always render the FULL pvLine as the Level-1
 * variation — even while parked at the fork node on the main line (insertPvLine
 * parks currentNodeId there). Without this the grafted PV stays invisible until the
 * user steps into it, so clicking a tactic chip appeared to do nothing
 * (UAT 260627 item 3 — "load and show the PV as a sideline").
 */
function resolvePvDisplayChain(
  vc: VariationChain,
  pvLine: NodeId[],
  nodes: Map<NodeId, MoveNode>,
): VariationChain {
  if (pvLine.length === 0 || vc.level === 2) return vc;
  const firstPvId = pvLine[0];
  const firstPvNode = firstPvId !== undefined ? nodes.get(firstPvId) : undefined;
  if (firstPvNode === undefined) return vc;
  return { forkParentId: firstPvNode.parentId, chain: pvLine, subChain: [], level: 1 };
}

// ─── Desktop row types and builders ──────────────────────────────────────────

interface DesktopRow {
  moveNumber: number;
  whiteNodeId: NodeId | undefined;
  blackNodeId: NodeId | undefined;
}

function buildDesktopRows(mainLine: NodeId[], rootPly: number): DesktopRow[] {
  const rows: DesktopRow[] = [];
  let idx = 0;

  // When rootPly is odd (black to move at root), first row has only a black cell.
  if (rootPly % 2 !== 0 && mainLine.length > 0) {
    rows.push({
      moveNumber: Math.ceil((rootPly + 1) / 2),
      whiteNodeId: undefined,
      blackNodeId: mainLine[0]!, // safe: length > 0 checked above
    });
    idx = 1;
  }

  while (idx < mainLine.length) {
    const ply = rootPly + idx;
    rows.push({
      moveNumber: Math.ceil((ply + 1) / 2),
      whiteNodeId: mainLine[idx]!, // safe: idx < length (loop invariant)
      blackNodeId: idx + 1 < mainLine.length ? mainLine[idx + 1]! : undefined,
    });
    idx += 2;
  }

  return rows;
}

function buildVariationRows(
  chain: NodeId[],
  forkIdx: number,
  rootPly: number,
): DesktopRow[] {
  const rows: DesktopRow[] = [];
  const startPly = rootPly + forkIdx + 1; // ply of the first variation move
  let idx = 0;

  // When the first variation move is black's turn, open with a black-only row.
  if (startPly % 2 !== 0 && chain.length > 0) {
    rows.push({
      moveNumber: Math.ceil((startPly + 1) / 2),
      whiteNodeId: undefined,
      blackNodeId: chain[0]!, // safe: length > 0 checked above
    });
    idx = 1;
  }

  while (idx < chain.length) {
    const ply = startPly + idx;
    rows.push({
      moveNumber: Math.ceil((ply + 1) / 2),
      whiteNodeId: chain[idx]!, // safe: idx < length (loop invariant)
      blackNodeId: idx + 1 < chain.length ? chain[idx + 1]! : undefined,
    });
    idx += 2;
  }

  return rows;
}

// ─── Inline flaw chip renderer ────────────────────────────────────────────────

// Same highlight-bg helper as TacticMotifChip/TagChip: bump the translucent alpha
// from 0.15 to 0.3 on hover so the chip clearly reads as highlighted.
const HIGHLIGHT_BG = (bg: string): string => bg.replace('/ 0.15)', '/ 0.3)');

interface FlawChipProps {
  nodeId: NodeId;
  motif: string;
  orientation: 'missed' | 'allowed';
  ply: number;
  depth: number | null;
  activePvNodeId: NodeId | null | undefined;
  activePvOrientation: 'missed' | 'allowed' | null | undefined;
  pvFetchPending: boolean | undefined;
  pvFetchError: boolean | undefined;
  onPvChipClick:
    | ((nodeId: NodeId, flaw: { ply: number; orientation: 'missed' | 'allowed' }) => void)
    | undefined;
}

/**
 * Render a missed or allowed flaw pill chip for a mainLine move-list row.
 * Sibling to the SAN <button>, NOT nested inside it (D-02).
 * Loading: spinner on chip while pvFetchPending for this node.
 * Error: error text next to the chip when pvFetchError for this node.
 *
 * Hover affordance (Quick 260628): mirrors the Games-card TacticMotifChip — pointer
 * cursor, lift, and brightened background on hover so the chip reads as clickable.
 */
function FlawChip({
  nodeId,
  motif,
  orientation,
  ply,
  depth,
  activePvNodeId,
  activePvOrientation,
  pvFetchPending,
  pvFetchError,
  onPvChipClick,
}: FlawChipProps): ReactNode {
  // Match by node AND orientation when an orientation is supplied — one node can host
  // both a missed (next flaw, shown early) and its own allowed chip (item 5).
  const isActive =
    nodeId === activePvNodeId &&
    (activePvOrientation == null || activePvOrientation === orientation);
  const isMissed = orientation === 'missed';
  const color = isMissed ? TAC_MISSED : TAC_ALLOWED;
  const bg = isMissed ? TAC_MISSED_BG : TAC_ALLOWED_BG;
  const border = isMissed ? TAC_MISSED_BORDER : TAC_ALLOWED_BORDER;
  // UAT 260627: show the motif name + depth (e.g. "checkmate 4", "hanging-piece 2")
  // instead of the orientation word. Mate-family motifs collapse to "checkmate";
  // depth uses the same orientation-anchored display offset as the board badges.
  const motifLabel = tacticMotifLabel(motif);
  // anchored=false (Quick 260628-1t5 DECISION 2): the move list is a navigable surface,
  // so the allowed +1 decision-anchor offset is dropped here (allowed reads like missed).
  const depthLabel = tacticDepthBadge(motif, depth, orientation, false);
  const label = depthLabel != null ? `${motifLabel} ${depthLabel}` : motifLabel;
  const testId = `flaw-inline-tag-${orientation}-${nodeId}`;
  const ariaCollapse = `${label} tactic. Click to collapse tactic line.`;
  const ariaExpand = `${label} tactic. Click to expand tactic line.`;

  // Brighten the chip while hovered/focused (tap-focus on mobile), like the Games card.
  const [highlighted, setHighlighted] = useState(false);

  const chipLabel =
    isActive && pvFetchPending ? (
      <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
    ) : (
      <span className="text-sm font-medium">{label}</span>
    );

  return (
    <span className="inline-flex items-center gap-1">
      <button
        type="button"
        data-testid={testId}
        aria-label={isActive ? ariaCollapse : ariaExpand}
        className={cn(
          'inline-flex items-center h-5 px-1.5 rounded-full border ml-1',
          'cursor-pointer transition-all hover:-translate-y-px',
          isActive && ACTIVE_FILTER_RING_CLASS,
          isActive && pvFetchError && 'opacity-60',
        )}
        style={{
          color,
          backgroundColor: highlighted ? HIGHLIGHT_BG(bg) : bg,
          borderColor: border,
          filter: highlighted ? 'brightness(1.2)' : undefined,
        }}
        onMouseEnter={() => setHighlighted(true)}
        onMouseLeave={() => setHighlighted(false)}
        onFocus={() => setHighlighted(true)}
        onBlur={() => setHighlighted(false)}
        onClick={(e) => {
          e.stopPropagation();
          onPvChipClick?.(nodeId, { ply, orientation });
        }}
      >
        {chipLabel}
      </button>
      {isActive && pvFetchError && (
        <span className="text-sm text-muted-foreground ml-1" role="alert">
          Tactic line not available for this flaw.
        </span>
      )}
    </span>
  );
}

// ─── Mobile sub-component ────────────────────────────────────────────────────

function MobileTree({
  nodes,
  mainLine,
  currentNodeId,
  pvLine,
  rootPly,
  onNodeClick,
  heightClass,
  flawMarkerByNodeId,
}: VariationTreeProps) {
  const rootPlyVal = rootPly ?? 0;
  const resolvedPvLine = pvLine ?? [];
  const { forkParentId, chain, subChain, level } = resolvePvDisplayChain(
    buildVariationChain(nodes, mainLine, resolvedPvLine, currentNodeId),
    resolvedPvLine,
    nodes,
  );
  const forkIdx = forkParentId !== null ? mainLine.indexOf(forkParentId) : -1;

  // Combined flat variation chain for mobile rendering: PV nodes + sub-fork nodes.
  const fullVarChain: NodeId[] = level === 2 ? [...chain, ...subChain] : chain;

  // Map main-line nodes to chip items.
  const mainItems = mainLine.map((nodeId, idx): HorizontalMoveItem | null => {
    const node = nodes.get(nodeId);
    if (!node) return null;
    const plyOffset = rootPlyVal + idx;
    const isWhite = plyOffset % 2 === 0;
    const label = isWhite ? moveLabel(rootPlyVal, idx) : null;
    const isFork = idx === forkIdx;
    const isAfterFork = forkIdx >= 0 && idx > forkIdx;

    // Severity marker for blunders/mistakes (mobile parity — D-02). Shown regardless
    // of a tactic chip on the move (UAT thl item 3); mobile renders no inline chip, so
    // the glyph is the only flaw cue here.
    const flaw = flawMarkerByNodeId?.get(nodeId);
    const showSeverityMarker =
      flaw != null && (flaw.severity === 'blunder' || flaw.severity === 'mistake');
    const SeverityIcon = flaw?.severity === 'blunder' ? BlunderIcon : MistakeIcon;

    // Opening paren: single for Level-1, double for Level-2.
    const parenOpen =
      isFork && fullVarChain.length > 0 ? (level === 2 ? '((' : '(') : null;

    return {
      key: nodeId,
      ply: nodeId,
      numberLabel: label,
      san: node.san,
      isCurrent: nodeId === currentNodeId,
      dimmed: isAfterFork,
      testId: `variation-node-${nodeId}`,
      ariaLabel: `Move ${label ?? ''} ${node.san}`.trim(),
      trailing:
        parenOpen != null ? (
          <span className="text-muted-foreground select-none ml-0.5">
            {parenOpen}
            {showSeverityMarker && (
              <SeverityIcon className="inline h-4 w-4 ml-0.5 align-middle" aria-hidden />
            )}
          </span>
        ) : showSeverityMarker ? (
          <SeverityIcon className="inline h-4 w-4 ml-0.5 align-middle" aria-hidden />
        ) : undefined,
    };
  });

  // Map variation-chain nodes to chip items.
  const varItems = fullVarChain.map((nodeId, varIdx): HorizontalMoveItem | null => {
    const node = nodes.get(nodeId);
    if (!node) return null;
    const varPlyIdx = (forkIdx >= 0 ? forkIdx + 1 : 0) + varIdx;
    const plyOffset = rootPlyVal + varPlyIdx;
    const isWhite = plyOffset % 2 === 0;
    const label = isWhite ? moveLabel(rootPlyVal, varPlyIdx) : null;
    const isLast = varIdx === fullVarChain.length - 1;
    // Closing paren: single for Level-1, double for Level-2.
    const parenClose = level === 2 ? '))' : ')';
    const isCurrent = nodeId === currentNodeId;

    // Live free-move severity glyph on EVERY variation/free node, not just the current one
    // (Quick 260628-r5v UAT — icons used to vanish when stepping forward): blunder/mistake
    // only, glyph-only (no tactic chip on mobile variations). Mirrors the desktop renderer +
    // the main-line mobile glyph; entries come from the per-node live-flaw cache.
    const flaw = flawMarkerByNodeId?.get(nodeId);
    const showSeverityMarker =
      flaw != null && (flaw.severity === 'blunder' || flaw.severity === 'mistake');
    const SeverityIcon = flaw?.severity === 'blunder' ? BlunderIcon : MistakeIcon;
    const severityGlyph = showSeverityMarker ? (
      <SeverityIcon className="inline h-4 w-4 ml-0.5 align-middle" aria-hidden />
    ) : null;

    return {
      key: nodeId,
      ply: nodeId,
      numberLabel: label,
      san: node.san,
      isCurrent,
      testId: `variation-node-${nodeId}`,
      ariaLabel: `Move ${label ?? ''} ${node.san}`.trim(),
      trailing: isLast ? (
        <span className="text-muted-foreground select-none">
          {severityGlyph}
          {parenClose}
        </span>
      ) : (
        severityGlyph ?? undefined
      ),
    };
  });

  const filteredMain = mainItems.filter((i): i is HorizontalMoveItem => i !== null);
  const filteredVar = varItems.filter((i): i is HorizontalMoveItem => i !== null);

  // Insert variation items between the fork node and the rest of the main line.
  const finalItems: HorizontalMoveItem[] =
    forkIdx >= 0
      ? [
          ...filteredMain.slice(0, forkIdx + 1),
          ...filteredVar,
          ...filteredMain.slice(forkIdx + 1),
        ]
      : filteredMain;

  return (
    <HorizontalMoveList
      items={finalItems}
      onMoveClick={(ply) => onNodeClick(ply)}
      heightClass={heightClass ?? 'h-20 sm:h-20'}
      emptyText="No moves yet"
      testId="variation-tree-mobile"
    />
  );
}

// ─── Desktop sub-component ───────────────────────────────────────────────────

function DesktopTree({
  nodes,
  mainLine,
  currentNodeId,
  pvLine,
  rootPly,
  onNodeClick,
  decorations,
  flawMarkerByNodeId,
  onPvChipClick,
  activePvNodeId,
  activePvOrientation,
  pvFetchPending,
  pvFetchError,
  initialPly,
}: VariationTreeProps) {
  const activeRef = useRef<HTMLButtonElement | null>(null);
  const rootPlyVal = rootPly ?? 0;
  const resolvedPvLine = pvLine ?? [];

  // The node the board opens at in game mode (initialPly, defaulting to ply 0).
  // undefined in free play (empty mainLine) — the initial top-align branch is skipped.
  const initialNodeId = mainLine.length > 0 ? mainLine[initialPly ?? 0] : undefined;
  // Last mainLine node — used to detect (and skip) the initial-load last-node transient
  // in the scroll effect. A primitive NodeId (not the mainLine array) so it can sit in the
  // effect deps without re-running on every render.
  const lastNodeId = mainLine.length > 0 ? mainLine[mainLine.length - 1] : undefined;
  const didInitialAlign = useRef(false);

  // Scroll the active node into view whenever currentNodeId changes. On the FIRST settle
  // at the game's initial ply, align it to the TOP of the scroller (Quick 260628-qta UAT:
  // the selected move should sit at the top, not the bottom). loadMainLine first parks
  // currentNodeId at the game's LAST node before the board navigates to initialPly, so the
  // top-align is held until currentNodeId actually reaches initialNodeId — otherwise the
  // transient last node scrolls first and the initial ply lands via minimal-scroll at the
  // bottom. All later navigation uses minimal keep-in-view scrolling.
  useEffect(() => {
    if (currentNodeId === null) return;
    const el = activeRef.current;
    if (!el) return;
    if (!didInitialAlign.current && initialNodeId !== undefined) {
      // Skip ONLY the initial-load last-node transient: loadMainLine parks currentNodeId at
      // the last mainLine node before the board navigates to the initial ply, and we don't
      // want that transient to scroll before the initial ply top-aligns. A mid-session
      // remount (mobile tab switch back to Moves after cycling tags) has no such transient —
      // currentNodeId is already the user's actual position — so fall through and top-align
      // to it instead of waiting forever for an initialNodeId settle that never comes.
      // (Quick 260702-nm8 follow-up. Edge case: a remount while genuinely parked on the last
      // node is indistinguishable from the transient and won't auto-scroll — acceptable.)
      if (currentNodeId !== initialNodeId && currentNodeId === lastNodeId && initialNodeId !== lastNodeId) {
        return;
      }
      didInitialAlign.current = true;
      el.scrollIntoView({ block: 'start', behavior: 'auto' });
      return;
    }
    el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [currentNodeId, initialNodeId, lastNodeId]);

  const { forkParentId, chain, subChain, level } = resolvePvDisplayChain(
    buildVariationChain(nodes, mainLine, resolvedPvLine, currentNodeId),
    resolvedPvLine,
    nodes,
  );
  const forkIdx = forkParentId !== null ? mainLine.indexOf(forkParentId) : -1;

  if (mainLine.length === 0 && nodes.size === 0) {
    return (
      <div
        data-testid="variation-tree-desktop"
        aria-label="Move list"
        role="navigation"
        className="min-h-0 flex-1 overflow-y-auto thin-scrollbar"
      >
        <p className="text-sm text-muted-foreground p-2">No moves yet</p>
      </div>
    );
  }

  const mainRows = buildDesktopRows(mainLine, rootPlyVal);
  const varRows =
    chain.length > 0 && forkIdx >= 0 ? buildVariationRows(chain, forkIdx, rootPlyVal) : [];
  // Level-2 sub-rows start after all Level-1 chain nodes.
  const subVarRows =
    level === 2 && subChain.length > 0 && forkIdx >= 0
      ? buildVariationRows(subChain, forkIdx + chain.length, rootPlyVal)
      : [];

  const forkRowIdx =
    forkIdx >= 0
      ? mainRows.findIndex(
          (r) => r.whiteNodeId === forkParentId || r.blackNodeId === forkParentId,
        )
      : -1;

  const renderMoveButton = (
    nodeId: NodeId,
    label: string,
    isVariation: boolean,
    isSubVariation = false,
  ): ReactNode => {
    const node = nodes.get(nodeId);
    if (!node) return null;
    const isCurrent = nodeId === currentNodeId;
    const decoColor = !isCurrent ? decorations?.get(nodeId) : undefined;

    // Flaw marker for mainLine nodes only (not variation/sub-variation nodes) — drives the
    // tactic chips, which stay main-line-only.
    const flaw = !isVariation ? flawMarkerByNodeId?.get(nodeId) : undefined;
    const hasTacticChip = flaw != null && (flaw.missedMotif != null || flaw.allowedMotif != null);
    // Severity glyph source: main-line nodes use their flaw entry; variation/free nodes read
    // the same map (moveListMarkers) for ANY node, not only the current one — so the live
    // blunder/mistake glyph persists on every explored sideline move instead of vanishing when
    // the user steps forward (Quick 260628-r5v UAT). The variation entries come from the
    // per-node live-flaw cache merged in by Analysis.tsx.
    const severityFlaw = flaw ?? flawMarkerByNodeId?.get(nodeId);
    // Show the blunder/mistake glyph whenever the severity warrants it, even when a
    // tactic chip is also present (UAT thl item 3 — icon + chip read as complementary).
    const showSeverityMarker =
      severityFlaw != null &&
      (severityFlaw.severity === 'blunder' || severityFlaw.severity === 'mistake');
    const SeverityIcon = severityFlaw?.severity === 'blunder' ? BlunderIcon : MistakeIcon;

    // Tactic chips render on their OWN line below the move (Quick w8k item 3), so the
    // move text stays scannable and the pills don't crowd the SAN.
    return (
      <span className="inline-flex flex-col items-start gap-1">
        <span className="inline-flex items-center gap-0.5">
          <button
            ref={isCurrent ? activeRef : undefined}
            data-testid={`variation-node-${nodeId}`}
            aria-label={`Move ${label} ${node.san}`}
            aria-current={isCurrent ? 'step' : undefined}
            onClick={() => onNodeClick(nodeId)}
            className={cn(
              'text-sm font-mono px-1 py-0.5 rounded transition-colors hover:bg-accent',
              isCurrent && 'bg-primary text-primary-foreground hover:bg-primary/90',
              !isCurrent && (isVariation || isSubVariation) && !decoColor && 'text-muted-foreground',
              isSubVariation && !isCurrent && 'opacity-80',
              decoColor && 'font-bold',
            )}
            style={decoColor ? { color: decoColor } : undefined}
          >
            {node.san}
          </button>
          {/* Non-tactic blunder/mistake severity glyph stays inline with the SAN —
              it reads as standard move annotation (e.g. "Qh4 ??"). */}
          {showSeverityMarker && (
            <SeverityIcon className="h-4 w-4 inline-block shrink-0" aria-hidden />
          )}
        </span>
        {/* Tactic pill chips on a new line below the move (Quick w8k item 3). Extra
            vertical gap + bottom padding keep stacked chips from crowding each other
            and the next row (Quick 260628). */}
        {hasTacticChip && (flaw.missedMotif != null || flaw.allowedMotif != null) && (
          <span className="inline-flex items-center flex-wrap gap-1 pb-1">
            {flaw.missedMotif != null && (
              <FlawChip
                key={`flaw-inline-tag-missed-${nodeId}`}
                nodeId={nodeId}
                motif={flaw.missedMotif}
                orientation="missed"
                // The missed chip's fetch/fork ply is its flaw's ply, even though the
                // chip is rendered on the decision node one ply earlier (item 5).
                ply={flaw.missedPly ?? flaw.ply}
                depth={flaw.missedDepth}
                activePvNodeId={activePvNodeId}
                activePvOrientation={activePvOrientation}
                pvFetchPending={pvFetchPending}
                pvFetchError={pvFetchError}
                onPvChipClick={onPvChipClick}
              />
            )}
            {flaw.allowedMotif != null && (
              <FlawChip
                key={`flaw-inline-tag-allowed-${nodeId}`}
                nodeId={nodeId}
                motif={flaw.allowedMotif}
                orientation="allowed"
                ply={flaw.ply}
                depth={flaw.allowedDepth}
                activePvNodeId={activePvNodeId}
                activePvOrientation={activePvOrientation}
                pvFetchPending={pvFetchPending}
                pvFetchError={pvFetchError}
                onPvChipClick={onPvChipClick}
              />
            )}
          </span>
        )}
      </span>
    );
  };

  const renderDesktopRow = (
    row: DesktopRow,
    isVariation: boolean,
    isSubVariation = false,
    rowBg = '',
  ): ReactNode => {
    const whiteLabel = `${row.moveNumber}.`;
    const blackLabel = `${row.moveNumber}...`;
    return (
      <div className={cn('flex items-start min-h-[28px]', rowBg)}>
        <span className="w-8 shrink-0 py-0.5 text-sm text-muted-foreground select-none">
          {row.moveNumber}.
        </span>
        <div className="flex-1 min-w-0">
          {row.whiteNodeId !== undefined &&
            renderMoveButton(row.whiteNodeId, whiteLabel, isVariation, isSubVariation)}
        </div>
        <div className="flex-1 min-w-0">
          {row.blackNodeId !== undefined &&
            renderMoveButton(row.blackNodeId, blackLabel, isVariation, isSubVariation)}
        </div>
      </div>
    );
  };

  return (
    <div
      data-testid="variation-tree-desktop"
      aria-label="Move list"
      role="navigation"
      // Absolute-fill the `relative` flex parent so the move list NEVER inflates the
      // outer row's intrinsic height (Quick w8k item 2 — the 4th alignment attempt).
      // Root cause measured in-browser: the outer row is lg:items-stretch and the left
      // board column (board + eval chart) is SHORTER than the right column; a
      // max-h/mb-capped flex-grow list still reports its content height as the row's
      // intrinsic height, so items-stretch stretched the left column past the eval
      // slider (42px dead space) while the controls pinned to the true bottom. Taking
      // the scroller out of flow (absolute inset-0) lets the board column drive the row
      // height, so the controls bottom-align with the eval-chart slider — no magic px.
      className="absolute inset-0 overflow-y-auto thin-scrollbar"
    >
      {mainRows.map((row, rowIdx) => (
        <Fragment key={rowIdx}>
          {renderDesktopRow(row, false, false, zebraBg(rowIdx))}
          {rowIdx === forkRowIdx && varRows.length > 0 && (
            <div
              data-testid="variation-pv-section"
              // The whole sideline inherits the fork row's zebra band (item 2).
              className={cn('ml-8 border-l-2 border-muted/40 pl-2', zebraBg(forkRowIdx))}
            >
              {varRows.map((vRow, vIdx) => (
                <Fragment key={vIdx}>{renderDesktopRow(vRow, true)}</Fragment>
              ))}
              {/* Level-2 sub-PV block nested inside Level-1. */}
              {level === 2 && subVarRows.length > 0 && (
                <div
                  data-testid="variation-subpv-section"
                  className="ml-8 border-l-2 border-muted/30 pl-2"
                >
                  {subVarRows.map((sRow, sIdx) => (
                    <Fragment key={sIdx}>{renderDesktopRow(sRow, true, true)}</Fragment>
                  ))}
                </div>
              )}
            </div>
          )}
        </Fragment>
      ))}
    </div>
  );
}

// ─── Main export ─────────────────────────────────────────────────────────────

/**
 * VariationTree — navigable move list showing the main line + up to two active
 * nesting levels. Click any node to call onNodeClick(nodeId) (→ goToNode).
 *
 * Phase 140 additions: pvLine/flawMarkerByNodeId/onPvChipClick/activePvNodeId
 * enable inline tactic chip expansion (Level-1) and sub-sideline navigation (Level-2).
 * All new props are optional so existing callers require no changes.
 */
export function VariationTree(props: VariationTreeProps) {
  // `variant='vertical'` forces the paired vertical list at every width (mobile
  // analysis Moves tab); the default `'responsive'` keeps the breakpoint split.
  if (props.variant === 'vertical') {
    return (
      <div
        data-testid="analysis-variation-tree"
        aria-label="Move list"
        role="navigation"
        className="relative flex min-h-0 flex-1 flex-col"
      >
        <DesktopTree {...props} />
      </div>
    );
  }
  return (
    <div
      data-testid="analysis-variation-tree"
      aria-label="Move list"
      role="navigation"
      className="flex min-h-0 flex-1 flex-col"
    >
      {/* Mobile path — HorizontalMoveList with variation inline in parentheses */}
      <div className="sm:hidden">
        <MobileTree {...props} />
      </div>
      {/* Desktop path — vertical paired N. white black list, fills the column so the
          board controls below it bottom-align with the eval-chart slider. `relative`
          so DesktopTree's absolute-fill scroller anchors here (Quick w8k item 2). */}
      <div className="relative hidden min-h-0 flex-1 sm:flex sm:flex-col">
        <DesktopTree {...props} />
      </div>
    </div>
  );
}
