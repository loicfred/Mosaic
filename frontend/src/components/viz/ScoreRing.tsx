import { cn } from '@/lib/cn'

/** A 0-100 score as a ring with the number in the middle. Good >= 90, fair >= 70, otherwise poor. */
export function ScoreRing({ score, size = 120, label }: { score: number; size?: number; label: string }) {
  const r = 42
  const c = 2 * Math.PI * r
  const v = Math.max(0, Math.min(100, score))
  const tone = v >= 90 ? 'var(--color-good)' : v >= 70 ? 'var(--color-warn)' : 'var(--color-bad)'
  const word = v >= 90 ? 'Good' : v >= 70 ? 'Fair' : 'Poor'
  return (
    <div className="flex shrink-0 flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }} role="img" aria-label={`${label}: ${score} out of 100 (${word})`}>
        <svg viewBox="0 0 100 100" className="size-full -rotate-90" aria-hidden>
          <circle cx="50" cy="50" r={r} fill="none" stroke="var(--color-track)" strokeWidth="9" />
          <circle
            cx="50"
            cy="50"
            r={r}
            fill="none"
            stroke={tone}
            strokeWidth="9"
            strokeLinecap="round"
            strokeDasharray={`${(v / 100) * c} ${c}`}
            className="transition-[stroke-dasharray] duration-500"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('font-semibold leading-none text-ink', size >= 110 ? 'text-4xl' : 'text-2xl')}>{score}</span>
          <span className="mt-1 text-xs text-ink-3">of 100</span>
        </div>
      </div>
      <span className="text-xs font-medium text-ink-2">{word}</span>
    </div>
  )
}
