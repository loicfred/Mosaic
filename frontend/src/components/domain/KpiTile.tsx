import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { Sparkline } from '@/components/viz/Sparkline'
import { cn } from '@/lib/cn'

/**
 * Icon + label, one large number, the change, and a small visual that gives the
 * number context (a trend sparkline or a meter). Supporting text stays one line.
 */
export function KpiTile({
  label,
  value,
  delta,
  foot,
  kind,
  icon: Icon,
  spark,
  sparkColor,
  sparkLabel,
  children,
  className,
}: {
  label: string
  value: ReactNode
  delta?: ReactNode
  foot?: ReactNode
  kind?: ReactNode
  icon?: LucideIcon
  spark?: number[]
  sparkColor?: string
  sparkLabel?: string
  children?: ReactNode
  className?: string
}) {
  return (
    <Card className={cn('flex flex-col gap-1.5 p-4 transition- ', className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2 text-sm font-medium text-ink-3">
          {Icon && (
            <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700" aria-hidden>
              <Icon className="size-4" />
            </span>
          )}
          <span className="truncate">{label}</span>
        </span>
        {kind}
      </div>
      <div className="whitespace-nowrap text-lg font-semibold leading-tight text-ink sm:text-2xl">{value}</div>
      <div className="flex min-h-5 flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ink-3">
        {delta}
        {foot}
      </div>
      {spark && spark.length > 1 && (
        <Sparkline values={spark} color={sparkColor} label={sparkLabel ?? `${label} trend`} className="mt-auto pt-1" />
      )}
      {children && <div className="mt-auto pt-1">{children}</div>}
    </Card>
  )
}
