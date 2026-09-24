import { cn } from '@/lib/cn'

/**
 * Signed effects around a zero line: which drivers push a result up (right, blue)
 * and which pull it down (left, red). Each bar also carries its signed value as
 * text, so direction never relies on colour.
 */
export function DivergingBars({
  rows,
  format,
  emptyLabel = 'No change',
}: {
  rows: { label: string; value: number }[]
  format: (v: number) => string
  emptyLabel?: string
}) {
  const max = Math.max(...rows.map((r) => Math.abs(r.value)), 1)
  return (
    <ul className="@container space-y-2">
      {rows.map((r) => {
        const w = (Math.abs(r.value) / max) * 50
        const zero = Math.abs(r.value) < 0.5
        return (
          <li
            key={r.label}
            className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 text-sm @md:grid-cols-[minmax(0,10rem)_1fr_6.5rem]"
          >
            <span className={cn('truncate', zero ? 'text-ink-3' : 'text-ink-2')} title={r.label}>
              {r.label}
            </span>
            <span className="relative col-span-2 row-start-2 h-3 @md:col-span-1 @md:col-start-2 @md:row-start-1" aria-hidden>
              <span className="absolute inset-y-[-3px] left-1/2 w-px bg-line-strong" />
              {!zero && (
                <span
                  className={cn('absolute inset-y-0', r.value > 0 ? 'rounded-r-[4px] bg-actual' : 'rounded-l-[4px] bg-bad')}
                  style={r.value > 0 ? { left: '50%', width: `${w}%` } : { right: '50%', width: `${w}%` }}
                />
              )}
            </span>
            <span
              className={cn(
                'tnum text-right whitespace-nowrap @md:col-start-3 @md:row-start-1',
                zero ? 'text-ink-3' : r.value > 0 ? 'font-medium text-good-ink' : 'font-medium text-bad-ink',
              )}
            >
              {zero ? emptyLabel : format(r.value)}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
