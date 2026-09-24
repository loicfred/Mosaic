import { cn } from '@/lib/cn'

export type OrbState = 'idle' | 'hover' | 'open' | 'thinking' | 'answer' | 'static'

/**
 * The Valora Insight orb: one data point with three orbiting points in the
 * brand colours. Idle it drifts slowly, hovered it quickens a little, while
 * reading data it spins, and when an answer lands the centre pulses once.
 * All motion stops under prefers-reduced-motion.
 */
export function InsightOrb({ state = 'idle', className }: { state?: OrbState; className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={cn('orb shrink-0', className)} data-state={state} aria-hidden>
      <circle cx="24" cy="24" r="15" fill="none" stroke="currentColor" strokeOpacity="0.16" strokeWidth="1.2" />
      <g className="orb-ring">
        <circle cx="39" cy="24" r="3" fill="#7DB356" />
        <circle cx="16.5" cy="11" r="2.6" fill="#F5B82E" />
        <circle cx="16.5" cy="37" r="2.2" fill="#FF6B45" />
      </g>
      <circle className="orb-core" cx="24" cy="24" r="6" fill="#6770F7" />
      <circle cx="24" cy="24" r="2.2" fill="#fff" fillOpacity="0.9" />
    </svg>
  )
}
