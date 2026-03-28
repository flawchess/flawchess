import * as React from "react"
import { createPortal } from "react-dom"
import { Chessboard } from "react-chessboard"
import { BOARD_DARK_SQUARE, BOARD_LIGHT_SQUARE } from "@/lib/theme"

const MINIMAP_BOARD_SIZE = 180;

interface MinimapPopoverProps {
  fen: string;
  boardOrientation?: "white" | "black";
  children: React.ReactNode;
  testId: string;
}

/**
 * Minimap that follows the mouse cursor (top-left corner anchored to pointer).
 * On touch devices, opens on tap and closes on tap-outside.
 */
function MinimapPopover({ fen, boardOrientation = "white", children, testId }: MinimapPopoverProps) {
  const [visible, setVisible] = React.useState(false);
  const [pos, setPos] = React.useState({ x: 0, y: 0 });
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const triggerRef = React.useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent) => {
    setPos({ x: e.clientX + 12, y: e.clientY + 12 });
  };

  const handleMouseEnter = (e: React.MouseEvent) => {
    setPos({ x: e.clientX + 12, y: e.clientY + 12 });
    hoverTimeout.current = setTimeout(() => setVisible(true), 150);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setVisible(false);
  };

  // Touch: tap to toggle
  const handleClick = (e: React.MouseEvent) => {
    if ('ontouchstart' in window) {
      e.preventDefault();
      // Position near the trigger element for touch
      const rect = triggerRef.current?.getBoundingClientRect();
      if (rect) {
        setPos({ x: rect.right + 8, y: rect.top });
      }
      setVisible(v => !v);
    }
  };

  // Close on outside tap (touch)
  React.useEffect(() => {
    if (!visible || !('ontouchstart' in window)) return;
    const handleTouch = (e: TouchEvent) => {
      if (triggerRef.current && !triggerRef.current.contains(e.target as Node)) {
        setVisible(false);
      }
    };
    document.addEventListener('touchstart', handleTouch);
    return () => document.removeEventListener('touchstart', handleTouch);
  }, [visible]);

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onMouseMove={handleMouseMove}
        onClick={handleClick}
        data-testid={testId}
        className="cursor-pointer"
      >
        {children}
      </div>
      {visible && createPortal(
        <div
          style={{
            position: 'fixed',
            left: pos.x,
            top: pos.y,
            zIndex: 100,
            pointerEvents: 'none',
          }}
          className="rounded-md shadow-lg overflow-hidden"
          data-testid={`${testId}-popover`}
        >
          <Chessboard
            options={{
              id: "minimap-board",
              position: fen,
              boardOrientation,
              boardStyle: {
                width: MINIMAP_BOARD_SIZE,
                height: MINIMAP_BOARD_SIZE,
              },
              darkSquareStyle: { backgroundColor: BOARD_DARK_SQUARE },
              lightSquareStyle: { backgroundColor: BOARD_LIGHT_SQUARE },
            }}
          />
        </div>,
        document.body
      )}
    </>
  );
}

export { MinimapPopover };
