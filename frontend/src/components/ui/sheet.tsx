import * as D from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export function Sheet({
  open,
  onOpenChange,
  title,
  description,
  children,
  wide,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  title: ReactNode
  description?: ReactNode
  children: ReactNode
  wide?: boolean
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-40 bg-brand-950/30" />
        <D.Content
          className={cn(
            'fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-line bg-surface shadow-xl outline-none',
            wide ? 'max-w-3xl' : 'max-w-xl',
          )}
        >
          <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
            <div className="min-w-0">
              <D.Title className="text-base font-semibold text-ink">{title}</D.Title>
              {description ? (
                <D.Description className="mt-1 text-sm text-ink-3">{description}</D.Description>
              ) : (
                <D.Description className="sr-only">Details</D.Description>
              )}
            </div>
            <D.Close className="rounded-md p-1.5 text-ink-3 hover:bg-brand-50 hover:text-ink" aria-label="Close">
              <X className="size-5" />
            </D.Close>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </D.Content>
      </D.Portal>
    </D.Root>
  )
}

export function Modal({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  title: ReactNode
  children: ReactNode
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-40 bg-brand-950/30" />
        <D.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-line bg-surface p-6 shadow-xl outline-none">
          <D.Title className="text-base font-semibold">{title}</D.Title>
          <D.Description className="sr-only">Dialog</D.Description>
          <div className="mt-4">{children}</div>
        </D.Content>
      </D.Portal>
    </D.Root>
  )
}
