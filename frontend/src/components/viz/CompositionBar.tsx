import type { ReactNode } from 'react'
import { Tip } from '@/components/ui/tooltip'
import { cn } from '@/lib/cn'

export interface Segment {
  key: string
  label: string
  value: number
  color: string
  /** Shown in the legend next to the swatch (status segments pass an icon so colour is never alone). */
  icon?: ReactNode
  display?: string
}

/**
 * Part-to-whole in one line: e.g. receivables not yet due vs overdue, or import
 * rows by status. Segments are separated by a 2px gap, not borders, and every
 * segment is also listed in the legend with its value and share.
 */
export function CompositionBar({
  segments,
  format,
  label,
  legend = true,
  className,
  height = 'h-3',
}: {
  segments: Segment[]
  format: (v: number) => string
  label: string
  legend?: boolean
  className?: string
  height?: string
}) {
  const total = segments.reduce((s, x) => s + Math.max(0, x.value), 0)
  const visible = segments.filter((s) => s.value > 0)
  return (
    <div className={className}>
      <div className={cn('flex w-full gap-[2px] overflow-hidden rounded-full bg-track', height)} role="img" aria-label={label}>
        {total > 0 &&
          visible.map((s) => (
            <Tip key={s.key} content={`${s.label}: ${s.display ?? format(s.value)} (${Math.round((s.value / total) * 100)}%)`}>
              <span
                className="grow-x h-full first:rounded-l-full last:rounded-r-full"
                style={{ width: `${(s.value / total) * 100}%`, background: s.color }}
              />
            </Tip>
          ))}
      </div>
      {legend && (
        <ul className="mt-3 grid grid-cols-1 gap-x-5 gap-y-1.5 text-sm sm:grid-cols-2">
          {segments.map((s) => (
            <li key={s.key} className="flex items-center gap-2">
              {s.icon ?? <span className="size-2.5 shrink-0 rounded-sm" style={{ background: s.color }} aria-hidden />}
              <span className="min-w-0 flex-1 truncate text-ink-2">{s.label}</span>
              <span className="tnum font-medium text-ink">{s.display ?? format(s.value)}</span>
              <span className="tnum w-9 text-right text-xs text-ink-3">{total ? Math.round((s.value / total) * 100) : 0}%</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
