import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface HBarRow {
  label: string
  value: number
  note?: string
  highlight?: boolean
  /** Small element after the value, e.g. a change indicator. */
  trailing?: ReactNode
}

/**
 * Horizontal bars in plain HTML: label, bar, value (and an optional change
 * indicator). Uses a container query so that in a narrow card the bar moves
 * under the label instead of being squeezed to nothing.
 */
export function HBarList({
  rows,
  format,
  color = 'var(--color-series-1)',
  max,
}: {
  rows: HBarRow[]
  format: (v: number) => string
  color?: string
  max?: number
}) {
  const m = max ?? Math.max(...rows.map((r) => r.value), 1)
  const hasTrailing = rows.some((r) => r.trailing)
  return (
    <div className="@container">
      <ul className="space-y-3 @md:space-y-2.5">
        {rows.map((r) => (
          <li
            key={r.label}
            className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 text-sm @md:grid-cols-[minmax(0,11rem)_minmax(0,1fr)_auto]"
          >
            <span className={cn('truncate', r.highlight ? 'font-medium text-ink' : 'text-ink-2')} title={r.label}>
              {r.label}
            </span>
            <div className="col-span-2 row-start-2 h-2.5 @md:col-span-1 @md:row-start-1 @md:col-start-2 @md:h-3">
              <div
                className="h-full rounded-r-sm"
                style={{ width: `${Math.max(1, (r.value / m) * 100)}%`, background: color, opacity: r.highlight === false ? 0.45 : 1 }}
              />
            </div>
            <span className="flex items-center justify-end gap-2 @md:col-start-3 @md:row-start-1">
              <span className="tnum whitespace-nowrap text-right text-ink @md:w-20">{format(r.value)}</span>
              {hasTrailing && <span className="flex min-w-14 justify-end">{r.trailing}</span>}
            </span>
            {r.note && <span className="col-span-2 text-xs text-ink-3 @md:col-span-1 @md:col-start-2">{r.note}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
