import * as React from "react"
import { Popover as PopoverPrimitive } from "radix-ui"
import { Info } from "lucide-react"
import { cn } from "@/lib/utils"

interface InfoPopoverProps {
  children: React.ReactNode
  ariaLabel: string
  testId: string
  side?: "top" | "bottom" | "left" | "right"
}

function InfoPopover({ children, ariaLabel, testId, side = "top" }: InfoPopoverProps) {
  return (
    <PopoverPrimitive.Root>
      <PopoverPrimitive.Trigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground"
          aria-label={ariaLabel}
          data-testid={testId}
        >
          <Info className="h-3.5 w-3.5" />
        </button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side={side}
          sideOffset={4}
          className={cn(
            "z-50 max-w-xs rounded-md bg-foreground px-3 py-1.5 text-xs text-background shadow-md",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
            "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2",
            "data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
          )}
        >
          {children}
          <PopoverPrimitive.Arrow className="z-50 size-2.5 translate-y-[calc(-50%_-_2px)] rotate-45 rounded-[2px] bg-foreground fill-foreground" />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}

export { InfoPopover }
