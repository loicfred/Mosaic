import type { HTMLAttributes, ReactNode } from 'react'
import { InfoTip } from '@/components/viz/InfoTip'
import { cn } from '@/lib/cn'

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
  /** Kept for compatibility: headers no longer draw a divider; spacing separates them from the body. */
  plain?: boolean
}) {
  return (
    <header className={cn('flex flex-wrap items-start justify-between gap-3 px-6 pb-4 pt-6', plain && 'pt-5', className)}>
      <div className="min-w-0">
        <h2 className="flex items-center gap-1.5 text-[17px] font-semibold tracking-tight text-ink">
          {title}
          {info && <InfoTip content={info} />}
        </h2>
        {subtitle && <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </header>
  )
}

export function CardBody({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6 [header+&]:pt-0', className)} {...p} />
}
