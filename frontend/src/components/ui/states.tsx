import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { Button } from './button'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-ink/[0.07]', className)} aria-hidden />
}

export function PageSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading">
      <h1 className="sr-only">Loading</h1>
      <Skeleton className="h-8 w-64" />
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-72" />
    </div>
  )
}

export function EmptyState({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 rounded-full bg-brand-50 p-3 text-ink-3">{icon ?? <Inbox className="size-5" />}</div>
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="mt-1 max-w-md text-sm text-ink-3">{children}</div>}
    </div>
  )
}

/**
 * Says what happened, what it means, and what to do. The server's own message is
 * shown only as a small reference line, never as the headline.
 */
export function ErrorState({
  error,
  onRetry,
  title = 'This page could not be loaded.',
  meaning = 'The latest figures are temporarily unavailable. Nothing in your records has changed.',
}: {
  error: unknown
  onRetry?: () => void
  title?: string
  meaning?: string
}) {
  const e = error instanceof ApiError ? error : null
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-xl border border-bad/20 bg-bad-bg/50 px-6 py-10 text-center"
    >
      <AlertTriangle className="mb-2 size-6 text-bad" aria-hidden />
      <p className="font-semibold text-ink">{title}</p>
      <p className="mt-1 max-w-md text-sm text-ink-2">{meaning}</p>
      {e && (
        <p className="mt-2 text-xs text-ink-3">
          {e.message}
          {e.requestId && <> · reference {e.requestId}</>}
        </p>
      )}
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          <RefreshCw /> Try again
        </Button>
      )}
    </div>
  )
}
