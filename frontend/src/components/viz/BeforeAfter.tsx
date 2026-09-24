import { cn } from '@/lib/cn'

/**
 * Two values on one shared scale: before vs after, no change vs simulated,
 * baseline vs measured. Answers "how big is the change?" at a glance; the
 * exact figures are printed at the end of each bar.
 */
export function BeforeAfter({
  before,
  after,
  format,
  beforeLabel = 'Before',
  afterLabel = 'After',
  afterColor = 'var(--color-actual)',
  max,
  className,
}: {
  before: number
  after: number
  format: (v: number) => string
  beforeLabel?: string
  afterLabel?: string
  afterColor?: string
  max?: number
  className?: string
}) {
  const m = max ?? Math.max(Math.abs(before), Math.abs(after), 1)
  const rows = [
    { label: beforeLabel, value: before, color: 'var(--color-before)' },
    { label: afterLabel, value: after, color: afterColor },
  ]
  return (
    <div
      className={cn('space-y-1.5', className)}
      role="group"
      aria-label={`${beforeLabel} ${format(before)}, ${afterLabel} ${format(after)}`}
    >
      {rows.map((r) => (
        <div key={r.label} className="grid grid-cols-[minmax(4.5rem,auto)_1fr_auto] items-center gap-3 text-xs">
          <span className="text-ink-3">{r.label}</span>
          <span className="h-2.5 rounded-r-[4px] bg-transparent">
            <span
              className="grow-x block h-full rounded-r-[4px]"
              style={{ width: `${Math.max(1.5, (Math.abs(r.value) / m) * 100)}%`, background: r.color }}
            />
          </span>
          <span className="tnum text-right font-medium text-ink">{format(r.value)}</span>
        </div>
      ))}
    </div>
  )
}
