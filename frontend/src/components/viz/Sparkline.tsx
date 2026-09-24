import { cn } from '@/lib/cn'

/**
 * A word-sized trend line for KPI tiles. It answers "which way is this going?"
 * and deliberately has no axis: the exact figure sits next to it in the tile.
 */
export function Sparkline({
  values,
  color = 'var(--color-actual)',
  label,
  className,
  area = true,
}: {
  values: number[]
  color?: string
  label: string
  className?: string
  area?: boolean
}) {
  const pts = values.filter((v) => Number.isFinite(v))
  if (pts.length < 2) return null
  const min = Math.min(...pts)
  const max = Math.max(...pts)
  const span = max - min || 1
  const W = 100
  const H = 32
  const pad = 3
  const xy = pts.map((v, i) => [(i / (pts.length - 1)) * W, pad + (1 - (v - min) / span) * (H - pad * 2)] as const)
  const line = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ')
  const last = xy[xy.length - 1]
  return (
    <div className={cn('relative h-8 w-full', className)} role="img" aria-label={label}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="size-full overflow-visible" aria-hidden>
        {area && <path d={`${line} L${W},${H} L0,${H} Z`} fill={color} fillOpacity={0.07} />}
        <path d={line} fill="none" stroke={color} strokeWidth={1.75} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
      </svg>
      {/* End dot drawn in HTML so it stays round when the SVG stretches. */}
      <span
        className="absolute size-2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface"
        style={{ left: `${last[0]}%`, top: `${(last[1] / H) * 100}%`, background: color }}
        aria-hidden
      />
    </div>
  )
}
