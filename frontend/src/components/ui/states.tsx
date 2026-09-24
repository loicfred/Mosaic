import { AlertTriangle, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { Button } from './button'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-mist', className)} aria-hidden />
}

/** Shaped like a page: header, a primary panel with a chart area, then table rows. */
export function PageSkeleton() {
  return (
    <div role="status" aria-label="Loading">
      <h1 className="sr-only">Loading</h1>
      <Skeleton className="h-7 w-56" />
      <Skeleton className="mt-2 h-4 w-80 max-w-full" />
      <div className="panel mt-6 p-5">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="mt-3 h-8 w-48" />
        <Skeleton className="mt-6 h-56 w-full" />
      </div>
      <div className="panel mt-6 divide-y divide-line">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-3">
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-4 w-24" />
          </div>
        ))}
      </div>
    </div>
  )
}

/** Says why there is nothing to show and, through children, what to do next. */
export function EmptyState({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
      {icon && <div className="mb-2 text-ink-4 [&_svg]:size-5">{icon}</div>}
      <p className="text-sm font-medium text-ink">{title}</p>
      {children && <div className="mt-1 max-w-md text-sm text-ink-3">{children}</div>}
    </div>
  )
}

/**
 * Says what failed and what to do next. The server's own message is shown only
 * as a small reference line, never as the headline.
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
    <div role="alert" className="panel flex items-start gap-3 px-5 py-5">
      <AlertTriangle className="mt-0.5 size-5 shrink-0 text-bad" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-ink">{title}</p>
        <p className="mt-0.5 text-sm text-ink-2">{meaning}</p>
        {e && (
          <p className="mt-2 font-mono text-xs text-ink-3">
            {e.message}
            {e.requestId && <> · reference {e.requestId}</>}
          </p>
        )}
        {onRetry && (
          <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
            <RefreshCw /> Try again
          </Button>
        )}
      </div>
    </div>
  )
}
