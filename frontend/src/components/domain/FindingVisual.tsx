import { AlertTriangle, Copy } from 'lucide-react'
import { Sparkline } from '@/components/viz/Sparkline'
import { cn } from '@/lib/cn'
import { arrowPair } from '@/lib/findings'
import { axisMur, date, monthLabel, murCompact } from '@/lib/format'
import type { Opportunity, Overview } from '@/lib/types'

/**
 * One small, data-appropriate picture per kind of finding:
 * trend -> sparkline, cost change -> before/after, exposure -> position on a scale,
 * distribution -> segmented bar, flagged payments -> short list.
 * Every value comes from the finding's evidence or the overview the app already loaded.
 * Returns null when the data for a picture is not available.
 */
export function FindingVisual({ o, overview, large }: { o: Opportunity; overview?: Overview; large?: boolean }) {
  const ev = o.evidence
  switch (o.detector) {
    case 'supplier_cost_inflation': {
      const months = overview?.monthly.filter((m) => !m.partial && m.revenue > 0) ?? []
      if (months.length < 4) return null
      const ratio = months.map((m) => (m.cost_of_goods / m.revenue) * 100)
      return (
        <Figure caption="Supplier cost per MUR 100 of sales, by month">
          <div className="flex items-end gap-3">
            <Sparkline
              values={ratio}
              color="var(--color-serious)"
              label={`Supplier cost per MUR 100 of sales over ${months.length} months`}
              className={large ? 'h-14' : 'h-10'}
            />
            <div className="shrink-0 text-right leading-tight">
              <div className="text-lg font-semibold text-ink">{ratio[ratio.length - 1].toFixed(0)}</div>
              <div className="text-[11px] text-ink-3">
                in {monthLabel(months[months.length - 1].month)} · {ratio[0].toFixed(0)} in {monthLabel(months[0].month)}
              </div>
            </div>
          </div>
        </Figure>
      )
    }
    case 'slow_collections': {
      const days = arrowPair(ev[0]?.display)
      const terms = typeof ev[3]?.value === 'number' ? (ev[3].value as number) : null
      if (!days) return null
      return (
        <Figure caption="Average days to collect an invoice">
          <Compare
            rows={[
              { label: 'Before', value: days[0], tone: 'before' },
              { label: 'Now', value: days[1], tone: 'bad' },
            ]}
            format={(v) => `${Math.round(v)} days`}
            marker={terms !== null ? { value: terms, label: `${terms}-day terms` } : undefined}
          />
        </Figure>
      )
    }
    case 'cash_pressure': {
      if (!overview) return null
      const today = overview.cash.balance
      const buffer = overview.projection.buffer_threshold
      const low = overview.projection.lowest_cash
      const max = Math.max(today, buffer, low) * 1.08
      const x = (v: number) => `${(Math.max(0, v) / max) * 100}%`
      return (
        <Figure caption={`Next 90 days · shaded: below the 14-day buffer (${axisMur(buffer)})`}>
          <div
            className="relative mt-5 h-2 rounded-full bg-track"
            role="img"
            aria-label={`Cash today ${murCompact(today)}, lowest projected ${murCompact(low)}, buffer ${murCompact(buffer)}`}
          >
            <span className="absolute inset-y-0 left-0 rounded-full bg-bad/15" style={{ width: x(buffer) }} aria-hidden />
            <span
              className="absolute inset-y-0 rounded-full bg-ink-3/40"
              style={{ left: x(low), width: `calc(${x(today)} - ${x(low)})` }}
              aria-hidden
            />
            <Pin at={x(buffer)} tone="line" />
            <Pin
              at={x(low)}
              label={`low · ${date(overview.projection.lowest_cash_date).slice(0, 6)}`}
              value={axisMur(low)}
              tone="bad"
              below
            />
            <Pin at={x(today)} label="today" value={axisMur(today)} tone="ink" />
          </div>
          <div className="h-6" />
        </Figure>
      )
    }
    case 'customer_concentration':
    case 'supplier_concentration': {
      const shares =
        o.detector === 'supplier_concentration'
          ? ev.filter((e) => typeof e.value === 'number').map((e) => ({ label: e.label, v: e.value as number }))
          : (() => {
              const top = typeof ev[0]?.value === 'number' ? (ev[0].value as number) : null
              const top3 = typeof ev[2]?.value === 'number' ? (ev[2].value as number) : null
              if (top === null) return []
              return [
                { label: ev[0].label.replace(' share of revenue', ''), v: top },
                ...(top3 !== null ? [{ label: 'Next two customers', v: Math.max(0, top3 - top) }] : []),
              ]
            })()
      if (!shares.length) return null
      const rest = Math.max(0, 100 - shares.reduce((s, x) => s + x.v, 0))
      const tints = ['bg-ink/80', 'bg-ink/40', 'bg-ink/25', 'bg-ink/15']
      return (
        <Figure
          caption={o.detector === 'supplier_concentration' ? 'Share of stock purchases, last 180 days' : 'Share of revenue, last 180 days'}
        >
          <div
            className="flex h-2.5 w-full gap-[2px] overflow-hidden rounded-full"
            role="img"
            aria-label={shares.map((s) => `${s.label} ${s.v.toFixed(0)}%`).join(', ')}
          >
            {shares.map((s, i) => (
              <span key={s.label} className={cn('h-full first:rounded-l-full', tints[i] ?? tints[3])} style={{ width: `${s.v}%` }} />
            ))}
            {rest > 0.5 && <span className="h-full flex-1 rounded-r-full bg-track" />}
          </div>
          <div className="mt-1.5 flex justify-between gap-3 text-xs">
            <span className="truncate text-ink-2">
              <strong className="font-semibold text-ink">{shares[0].v.toFixed(0)}%</strong> {shares[0].label}
            </span>
            {rest > 0.5 && <span className="shrink-0 text-ink-3">{rest.toFixed(0)}% everyone else</span>}
          </div>
        </Figure>
      )
    }
    case 'growth_product_line': {
      const pair = arrowPair(ev[0]?.detail)
      if (!pair) return null
      return (
        <Figure caption={`${ev[0].label}: last 90 days vs the same period last year`}>
          <Compare
            rows={[
              { label: 'Last year', value: pair[0], tone: 'before' },
              { label: 'This year', value: pair[1], tone: 'good' },
            ]}
            format={murCompact}
          />
        </Figure>
      )
    }
    case 'recurring_cost_creep': {
      const pair = arrowPair(ev[0]?.display)
      if (!pair) return null
      return (
        <Figure caption="Fixed commitments per month">
          <Compare
            rows={[
              { label: '6 months ago', value: pair[0], tone: 'before' },
              { label: 'Now', value: pair[1], tone: 'bad' },
            ]}
            format={murCompact}
          />
        </Figure>
      )
    }
    case 'unusual_transactions':
      return (
        <Figure caption="Flagged payments">
          <ul className="space-y-1.5">
            {ev.slice(0, 3).map((e) => {
              const dup = e.label.startsWith('Possible duplicate')
              const Icon = dup ? Copy : AlertTriangle
              return (
                <li key={e.label} className="flex items-start gap-2 text-sm">
                  <Icon className={cn('mt-0.5 size-3.5 shrink-0', dup ? 'text-warn-ink' : 'text-serious-ink')} aria-hidden />
                  <span className="min-w-0">
                    <span className="block truncate text-ink">{e.label.replace(/^(Possible duplicate|Unusual): /, '')}</span>
                    <span className="block text-xs text-ink-3">{e.display}</span>
                  </span>
                </li>
              )
            })}
          </ul>
        </Figure>
      )
    case 'overlapping_subscriptions': {
      const rows = ev.filter((e) => typeof e.value === 'number').slice(0, 3)
      if (rows.length < 2) return null
      return (
        <Figure caption="Monthly cost of each tool">
          <Compare
            rows={rows.map((e, i) => ({ label: e.label.split(' ')[0], value: e.value as number, tone: i === 0 ? 'ink' : 'before' }))}
            format={(v) => murCompact(v)}
          />
        </Figure>
      )
    }
    default:
      return null
  }
}

function Figure({ caption, children }: { caption: string; children: React.ReactNode }) {
  return (
    <figure className="min-w-0">
      {children}
      <figcaption className="mt-1.5 text-[11px] text-ink-3">{caption}</figcaption>
    </figure>
  )
}

const TONE = { before: 'bg-before', good: 'bg-good', bad: 'bg-serious', ink: 'bg-ink/70' } as const

/** Two or three values on one scale, optional reference marker (e.g. payment terms). */
function Compare({
  rows,
  format,
  marker,
}: {
  rows: { label: string; value: number; tone: keyof typeof TONE }[]
  format: (v: number) => string
  marker?: { value: number; label: string }
}) {
  const max = Math.max(...rows.map((r) => r.value), marker?.value ?? 0) * 1.05 || 1
  return (
    <div className="space-y-1.5" role="group" aria-label={rows.map((r) => `${r.label} ${format(r.value)}`).join(', ')}>
      {rows.map((r) => (
        <div key={r.label} className="grid grid-cols-[5.5rem_1fr_auto] items-center gap-2.5 text-xs">
          <span className="truncate text-ink-3">{r.label}</span>
          <span className="relative h-2">
            <span
              className={cn('grow-x block h-full rounded-r-[3px]', TONE[r.tone])}
              style={{ width: `${Math.max(2, (r.value / max) * 100)}%` }}
            />
            {marker && (
              <span
                className="absolute -inset-y-1 w-px border-l border-dashed border-ink-2"
                style={{ left: `${(marker.value / max) * 100}%` }}
                aria-hidden
              />
            )}
          </span>
          <span className="tnum text-right font-medium text-ink">{format(r.value)}</span>
        </div>
      ))}
      {marker && (
        <div className="grid grid-cols-[5.5rem_1fr] gap-2.5 text-[11px] text-ink-3">
          <span />
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-0 border-l border-dashed border-ink-2" aria-hidden /> {marker.label}
          </span>
        </div>
      )}
    </div>
  )
}

function Pin({
  at,
  label,
  value,
  tone,
  below,
}: {
  at: string
  label?: string
  value?: string
  tone: 'ink' | 'bad' | 'line'
  below?: boolean
}) {
  return (
    <span className="absolute top-1/2" style={{ left: at }} aria-hidden>
      <span
        className={cn(
          'absolute left-0 block -translate-x-1/2 -translate-y-1/2',
          tone === 'line'
            ? 'h-4 w-0.5 rounded-full bg-bad'
            : cn('size-2.5 rounded-full ring-2 ring-surface', tone === 'bad' ? 'bg-bad' : 'bg-ink'),
        )}
      />
      {label && (
        <span
          className={cn(
            'absolute left-0 -translate-x-1/2 whitespace-nowrap text-center text-[10px] leading-tight',
            below ? 'top-2.5' : 'bottom-2.5',
            tone === 'bad' ? 'text-bad-ink' : 'text-ink-3',
          )}
        >
          <span className="font-semibold text-ink">{value}</span> {label}
        </span>
      )}
    </span>
  )
}
