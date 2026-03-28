import * as React from "react"
import { Popover as PopoverPrimitive } from "radix-ui"
import { Chessboard } from "react-chessboard"
import { BOARD_DARK_SQUARE, BOARD_LIGHT_SQUARE } from "@/lib/theme"

const MINIMAP_BOARD_SIZE = 180;

interface MinimapPopoverProps {
  fen: string;
  children: React.ReactNode;
  testId: string;
}

function MinimapPopover({ fen, children, testId }: MinimapPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), 150);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <div
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          data-testid={testId}
          className="cursor-pointer"
        >
          {children}
        </div>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="right"
          sideOffset={8}
          avoidCollisions
          onMouseEnter={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
          }}
          onMouseLeave={handleMouseLeave}
          className="z-[100] rounded-md shadow-lg overflow-hidden"
          data-testid={`${testId}-popover`}
        >
          <Chessboard
            options={{
              id: "minimap-board",
              position: fen,
              boardStyle: {
                width: MINIMAP_BOARD_SIZE,
                height: MINIMAP_BOARD_SIZE,
              },
              darkSquareStyle: { backgroundColor: BOARD_DARK_SQUARE },
              lightSquareStyle: { backgroundColor: BOARD_LIGHT_SQUARE },
            }}
          />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

export { MinimapPopover };
