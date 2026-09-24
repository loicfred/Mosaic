import { mur } from '@/lib/format'

export interface TooltipRow {
  name: string
  value: number | null | undefined
  color: string
  dashed?: boolean
}

/** Values lead, labels follow; series keyed by a short line in the series colour. */
export function ChartTooltipBox({ title, rows, format = mur }: { title: string; rows: TooltipRow[]; format?: (v: number) => string }) {
  return (
    <div className="min-w-44 rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-float">
      <div className="mb-1.5 font-medium text-ink-3">{title}</div>
      {rows
        .filter((r) => r.value !== null && r.value !== undefined)
        .map((r) => (
          <div key={r.name} className="flex items-center gap-2 py-0.5">
            <svg width="14" height="4" aria-hidden>
              <line x1="0" y1="2" x2="14" y2="2" stroke={r.color} strokeWidth="2" strokeDasharray={r.dashed ? '3 2' : undefined} />
            </svg>
            <span className="tnum font-semibold text-ink">{format(r.value as number)}</span>
            <span className="text-ink-3">{r.name}</span>
          </div>
        ))}
    </div>
  )
}

export function LegendKey({ items }: { items: { label: string; color: string; dashed?: boolean; kind?: 'line' | 'rect' }[] }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-2">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          {i.kind === 'rect' ? (
            <span className="size-2.5 rounded-sm" style={{ background: i.color }} aria-hidden />
          ) : (
            <svg width="16" height="4" aria-hidden>
              <line x1="0" y1="2" x2="16" y2="2" stroke={i.color} strokeWidth="2" strokeDasharray={i.dashed ? '4 3' : undefined} />
            </svg>
          )}
          {i.label}
        </li>
      ))}
    </ul>
  )
}
