import type { ReactNode } from 'react'
import { Sparkline } from '@/components/viz/Sparkline'
import { cn } from '@/lib/cn'

export interface StripMetric {
  label: string
  value: ReactNode
  delta?: ReactNode
  note?: ReactNode
  spark?: number[]
  sparkColor?: string
  sparkLabel?: string
  /** Replaces the sparkline, e.g. a meter. */
  visual?: ReactNode
  title?: string
}

/**
 * A row of related numbers in one panel, separated by hairlines instead of
 * each living in its own card. Label, one large figure, the change, and a
 * small picture of how it got there.
 */
export function MetricStrip({ items, className }: { items: StripMetric[]; className?: string }) {
  return (
    <dl
      className={cn(
        'grid grid-cols-2 overflow-hidden rounded-xl border border-line bg-surface',
        items.length >= 5 ? 'lg:grid-cols-5' : 'lg:grid-cols-4',
        className,
      )}
    >
      {items.map((m, i) => (
        <div
          key={m.label}
          className={cn(
            'flex min-w-0 flex-col gap-1 p-5',
            // hairlines between cells: right edge except last in row, top edge for the second row on small screens
            'border-line',
            i % 2 === 0 && 'border-r',
            i >= 2 && 'border-t lg:border-t-0',
            'lg:border-r lg:last:border-r-0',
          )}
          title={m.title}
        >
          <dt className="text-sm text-ink-3">{m.label}</dt>
          <dd className="whitespace-nowrap text-[26px] font-semibold leading-tight tracking-tight text-ink lg:text-[28px]">{m.value}</dd>
          <dd className="flex min-h-5 flex-wrap items-center gap-x-2 text-xs text-ink-3">
            {m.delta}
            {m.note}
          </dd>
          <dd className="mt-auto pt-2">
            {m.visual ??
              (m.spark && m.spark.length > 1 && (
                <Sparkline values={m.spark} color={m.sparkColor} label={m.sparkLabel ?? `${m.label} trend`} />
              ))}
          </dd>
        </div>
      ))}
    </dl>
  )
}
