import { cn } from '@/lib/cn'

/**
 * Where a probability sits relative to the model's LOW / MODERATE / HIGH bands.
 * Answers "how close is this to the next band?" - something the bare 64% cannot.
 */
export function BandScale({
  probability,
  moderate,
  high,
  className,
}: {
  probability: number
  moderate: number
  high: number
  className?: string
}) {
  const segs = [
    { key: 'Low', from: 0, to: moderate, cls: 'bg-good/25', on: 'bg-good/60', ink: 'text-good-ink' },
    { key: 'Moderate', from: moderate, to: high, cls: 'bg-warn/30', on: 'bg-warn/70', ink: 'text-warn-ink' },
    { key: 'High', from: high, to: 1, cls: 'bg-bad/20', on: 'bg-bad/45', ink: 'text-bad-ink' },
  ]
  const active = probability >= high ? 'High' : probability >= moderate ? 'Moderate' : 'Low'
  const p = Math.max(0, Math.min(1, probability)) * 100
  return (
    <div className={cn('w-full', className)}>
      <div
        className="relative flex h-2.5 w-full gap-[2px]"
        role="meter"
        aria-label={`Probability ${Math.round(p)}%, in the ${active.toLowerCase()} band`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(p)}
      >
        {segs.map((s, i) => (
          <span
            key={s.key}
            className={cn(
              'h-full',
              s.key === active ? s.on : s.cls,
              i === 0 && 'rounded-l-full',
              i === segs.length - 1 && 'rounded-r-full',
            )}
            style={{ width: `${(s.to - s.from) * 100}%` }}
          />
        ))}
        <span
          className="absolute -top-1 h-[18px] w-1 -translate-x-1/2 rounded-full bg-ink ring-2 ring-surface"
          style={{ left: `${p}%` }}
          aria-hidden
        />
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px]">
        {segs.map((s) => (
          <li key={s.key} className={s.key === active ? cn('font-semibold', s.ink) : 'text-ink-3'}>
            {s.key}{' '}
            <span className="font-normal">
              {s.from === 0
                ? `<${Math.round(s.to * 100)}%`
                : s.to === 1
                  ? `≥${Math.round(s.from * 100)}%`
                  : `${Math.round(s.from * 100)}–${Math.round(s.to * 100)}%`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
