import { cn } from '@/lib/cn'

const FILL = {
  brand: 'bg-brand-700',
  actual: 'bg-actual',
  good: 'bg-good',
  warn: 'bg-warn',
  serious: 'bg-serious',
  bad: 'bg-bad',
  neutral: 'bg-ink-3',
} as const

export type MeterTone = keyof typeof FILL

/**
 * A single value against a scale, optionally with a target/threshold marker
 * (e.g. "18 days of cash vs the 14-day safety buffer"). The value and marker
 * are always also given as text by the caller, so colour never carries meaning alone.
 */
export function Meter({
  value,
  max,
  tone = 'brand',
  marker,
  label,
  size = 'md',
  className,
}: {
  value: number
  max: number
  tone?: MeterTone
  marker?: { value: number; label?: string }
  label: string
  size?: 'sm' | 'md'
  className?: string
}) {
  const clamp = (v: number) => Math.max(0, Math.min(100, (v / (max || 1)) * 100))
  const w = clamp(value)
  return (
    <div className={cn('w-full', className)}>
      <div
        className={cn('relative w-full rounded-full bg-track', size === 'sm' ? 'h-1.5' : 'h-2')}
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={Math.round(value * 100) / 100}
      >
        <div className={cn('h-full rounded-full', FILL[tone])} style={{ width: `${w}%` }} />
        {marker && (
          <span
            className="absolute -top-1 h-[calc(100%+8px)] w-0.5 -translate-x-1/2 rounded-full bg-ink"
            style={{ left: `${clamp(marker.value)}%` }}
            aria-hidden
          />
        )}
      </div>
      {marker?.label && (
        <div className="relative mt-1 h-4 text-xs text-ink-3">
          <span
            className="absolute whitespace-nowrap"
            style={{
              left: `${clamp(marker.value)}%`,
              transform: clamp(marker.value) > 70 ? 'translateX(-100%)' : clamp(marker.value) < 20 ? 'none' : 'translateX(-50%)',
            }}
          >
            {marker.label}
          </span>
        </div>
      )}
    </div>
  )
}
