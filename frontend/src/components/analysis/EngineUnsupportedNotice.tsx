/**
 * EngineUnsupportedNotice — the in-card copy for a device on which Maia can
 * never start.
 *
 * Why a card-level notice: `EngineReadyGate` carries the same message, but
 * it is deliberately suppressed on /analysis for the `unsupported` status
 * (it would lock the board out), and it never mounts on a returning device
 * whose engine assets were already cached. Without this notice a gated device
 * would see the Maia card's pulsing skeleton forever and an empty FlawChess
 * Engine card, with no explanation. Both cards render this instead of their
 * loading state whenever the store reports `unsupported`.
 *
 * Copy mirrors the gate's `unsupported` variant, minus the "you can still
 * use the analysis board" pointer (the reader is on it).
 */
import type { ReactElement } from 'react';
import { useEngineUnsupportedReason } from '@/hooks/useEngineAssets';
import type { EngineUnsupportedReason } from '@/lib/engine/engineAssetProgress';

const NOTICE_COPY: Record<EngineUnsupportedReason, { title: string; body: string }> = {
  'no-wasm-simd': {
    title: "This device can't run Maia",
    body:
      "Your browser or device doesn't support the technology Maia needs, and that " +
      "isn't something a retry can fix. Stockfish analysis keeps working.",
  },
};

interface EngineUnsupportedNoticeProps {
  /** Which card renders it — only the test id differs. */
  card: 'maia' | 'flawchess';
}

/**
 * Renders the notice, or `null` when the store is not in the `unsupported`
 * status — so a caller can place it unconditionally ahead of its own
 * loading/empty branches and short-circuit on a non-null result.
 */
export function useEngineUnsupportedNotice(card: EngineUnsupportedNoticeProps['card']): ReactElement | null {
  const reason = useEngineUnsupportedReason();
  if (reason === null) return null;
  const copy = NOTICE_COPY[reason];
  return (
    <div
      role="status"
      data-testid={`analysis-${card}-unsupported`}
      className="flex h-full flex-col justify-center gap-1 px-2 py-1 text-sm text-muted-foreground"
    >
      <span className="font-medium text-foreground">{copy.title}</span>
      <span>{copy.body}</span>
    </div>
  );
}
