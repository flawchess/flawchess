/**
 * Test stand-in for the app shell's fixed bottom bar (App.tsx `MobileBottomBar`): renders the
 * Train reveal bar from the published mobileBoardControls payload exactly as
 * `renderBoardControlsBar` does. The stacked Train layout (phones, portrait tablets, unfolded
 * foldables) publishes its reveal controls instead of rendering them in the page, so a test
 * that renders the solve screen without the shell mounts this to reach Next and Analyze.
 */
import type { ReactElement } from 'react';
import { TrainRevealActionBar } from '@/components/train/TrainRevealActionBar';
import { useMobileBoardControls } from '@/lib/mobileBoardControls';

export function PublishedRevealBar(): ReactElement | null {
  const controls = useMobileBoardControls();
  if (controls?.onNext == null) return null;
  return (
    <TrainRevealActionBar
      onRewind={controls.onReset ?? (() => {})}
      onBack={controls.onBack}
      onForward={controls.onForward}
      canRewind={controls.canReset ?? controls.canGoBack}
      canGoBack={controls.canGoBack}
      canGoForward={controls.canGoForward}
      analyzeTo={controls.analyzeTo ?? null}
      onAnalyzeClick={controls.onAnalyzeClick ?? (() => {})}
      onNext={controls.onNext}
      spotlightAnalyze={controls.spotlightAnalyze === true}
    />
  );
}
