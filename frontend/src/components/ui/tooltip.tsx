import * as T from '@radix-ui/react-tooltip'
import type { ReactNode } from 'react'

export const TooltipProvider = T.Provider

export function Tip({ content, children }: { content: ReactNode; children: ReactNode }) {
  return (
    <T.Root delayDuration={150}>
      <T.Trigger asChild>{children}</T.Trigger>
      <T.Portal>
        <T.Content sideOffset={6} className="z-50 max-w-xs rounded-md bg-brand-900 px-3 py-2 text-xs leading-relaxed text-white shadow-lg">
          {content}
          <T.Arrow className="fill-brand-900" />
        </T.Content>
      </T.Portal>
    </T.Root>
  )
}
