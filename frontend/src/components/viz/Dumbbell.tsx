import { cn } from '@/lib/cn'

export interface DumbbellRow {
  label: string
  from: number | null
  to: number | null
  note?: string
}

/**
 * Before -> now per item on a shared scale (e.g. days each customer takes to pay).
 * A long bar pointing right means "got slower". An optional reference line marks
 * the target (payment terms).
 */
export function Dumbbell({
  rows,
  unit,
  reference,
  worseWhen = 'up',
  tolerance = 3,
}: {
  rows: DumbbellRow[]
  unit: string
  reference?: { value: number; label: string }
  worseWhen?: 'up' | 'down'
  tolerance?: number
}) {
  const vals = rows.flatMap((r) => [r.from, r.to]).filter((v): v is number => v !== null)
  const max = Math.max(...vals, reference?.value ?? 0, 1) * 1.1
  const x = (v: number) => `${(v / max) * 100}%`
  return (
    <div className="@container">
      <ul className="space-y-3">
        {rows.map((r) => {
          const has = r.from !== null && r.to !== null
          const delta = has ? (r.to as number) - (r.from as number) : 0
          const worse = has && (worseWhen === 'up' ? delta > tolerance : delta < -tolerance)
          const lo = has ? Math.min(r.from as number, r.to as number) : 0
          const hi = has ? Math.max(r.from as number, r.to as number) : 0
          return (
            <li
              key={r.label}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 text-sm @md:grid-cols-[minmax(0,10rem)_1fr_auto]"
            >
              <span className={cn('truncate', worse ? 'font-medium text-ink' : 'text-ink-2')} title={r.label}>
                {r.label}
              </span>
              <div
                className="relative col-span-2 row-start-2 h-5 @md:col-span-1 @md:col-start-2 @md:row-start-1"
                role="img"
                aria-label={`${r.label}: ${r.from ?? 'unknown'} to ${r.to ?? 'unknown'} ${unit}`}
              >
                <span className="absolute inset-x-0 top-1/2 h-px bg-line" aria-hidden />
                {reference && (
                  <span
                    className="absolute inset-y-0 w-px border-l border-dashed border-ink-3"
                    style={{ left: x(reference.value) }}
                    aria-hidden
                  />
                )}
                {has && (
                  <>
                    <span
                      className={cn('absolute top-1/2 h-1 -translate-y-1/2 rounded-full', worse ? 'bg-serious/60' : 'bg-actual/40')}
                      style={{ left: x(lo), width: `calc(${x(hi)} - ${x(lo)})` }}
                      aria-hidden
                    />
                    <span
                      className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-ink-3 bg-surface"
                      style={{ left: x(r.from as number) }}
                      aria-hidden
                    />
                    <span
                      className={cn(
                        'absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface',
                        worse ? 'bg-serious' : 'bg-actual',
                      )}
                      style={{ left: x(r.to as number) }}
                      aria-hidden
                    />
                  </>
                )}
              </div>
              <span className="tnum text-right text-xs whitespace-nowrap text-ink-3 @md:col-start-3 @md:row-start-1 @md:w-24">
                {has ? (
                  <>
                    {Math.round(r.from as number)} →{''}
                    <strong className={cn('text-sm', worse ? 'text-serious-ink' : 'text-ink')}>{Math.round(r.to as number)}</strong> {unit}
                  </>
                ) : (
                  '—'
                )}
              </span>
              {r.note && <span className="col-span-2 text-xs text-ink-3 @md:col-span-1 @md:col-start-2 @md:-mt-2">{r.note}</span>}
            </li>
          )
        })}
      </ul>
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-3">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full border-2 border-ink-3" aria-hidden /> Before
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-actual" aria-hidden /> Now
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-serious" aria-hidden /> Now, noticeably slower
        </span>
        {reference && (
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-0 border-l border-dashed border-ink-3" aria-hidden /> {reference.label}
          </span>
        )}
      </div>
    </div>
  )
}
