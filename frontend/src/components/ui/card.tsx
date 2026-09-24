import type { HTMLAttributes, ReactNode } from 'react'
import { InfoTip } from '@/components/viz/InfoTip'
import { cn } from '@/lib/cn'

/** A bordered panel. Use only where grouping helps; sections can also sit directly on the page. */
export function Card({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <section className={cn('panel', className)} {...p} />
}

export function CardHeader({
  title,
  subtitle,
  action,
  info,
  className,
  plain,
}: {
  title: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  /** Method or definition text, shown on demand behind an (i) instead of in the card. */
  info?: ReactNode
  className?: string
  /** Kept for compatibility: headers never draw a divider. */
  plain?: boolean
}) {
  return (
    <header className={cn('flex flex-wrap items-start justify-between gap-3 px-5 pb-3 pt-5', plain && 'pt-4', className)}>
      <div className="min-w-0">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
          {title}
          {info && <InfoTip content={info} />}
        </h2>
        {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </header>
  )
}

export function CardBody({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5 [header+&]:pt-0', className)} {...p} />
}
