import { cn } from '@/lib/cn'

export interface RangeRow {
  id: string
  label: string
  low: number
  high: number
  sub?: string
}

/**
 * Low-high estimate ranges on one shared scale, largest first. Answers
 * "which findings are worth the most, and how certain is the size?".
 * Rows are buttons when `onSelect` is given, so the chart doubles as navigation.
 */
export function RangeBars({
  rows,
  format,
  color = 'var(--color-actual)',
  onSelect,
}: {
  rows: RangeRow[]
  format: (v: number) => string
  color?: string
  onSelect?: (id: string) => void
}) {
  const max = Math.max(...rows.map((r) => r.high), 1)
  const x = (v: number) => (v / max) * 100
  return (
    <ul className="@container space-y-1">
      {rows.map((r) => {
        const body = (
          <>
            <span className="min-w-0 text-left">
              <span className="line-clamp-2 block text-sm leading-snug text-ink" title={r.label}>
                {r.label}
              </span>
              {r.sub && <span className="block truncate text-xs text-ink-3">{r.sub}</span>}
            </span>
            <span
              className="relative col-span-2 row-start-2 h-2.5 rounded-full bg-track @sm:col-span-1 @sm:col-start-2 @sm:row-start-1"
              aria-hidden
            >
              <span
                className="grow-x absolute inset-y-0 rounded-full"
                style={{ left: `${x(r.low)}%`, width: `${Math.max(1.5, x(r.high) - x(r.low))}%`, background: color }}
              />
            </span>
            <span className="tnum text-right text-xs font-medium whitespace-nowrap text-ink @sm:col-start-3 @sm:row-start-1">
              {format(r.low)}–{format(r.high)}
            </span>
          </>
        )
        const cls =
          'grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 rounded-md px-2 py-1.5 @sm:grid-cols-[minmax(0,1.5fr)_minmax(4rem,1fr)_5.5rem]'
        return (
          <li key={r.id}>
            {onSelect ? (
              <button type="button" onClick={() => onSelect(r.id)} className={cn(cls, 'transition-colors hover:bg-surface-2')}>
                {body}
              </button>
            ) : (
              <div className={cls}>{body}</div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
