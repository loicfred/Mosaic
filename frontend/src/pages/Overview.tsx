import { AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, Database, FileUp, FlaskConical, Minus, Target } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { CashChart } from '@/charts/CashChart'
import { SeverityBadge } from '@/components/domain/labels'
import { PageHeader } from '@/components/layout/AppShell'
import { InsightStrip } from '@/components/ui/insight-strip'
import { ErrorState, Skeleton } from '@/components/ui/states'
import { useCashPressure, useInsights, useOpportunities, useOverview } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { IMPACT_SHORT } from '@/lib/findings'
import { date, daysBetween, greeting, monthSpan, mur, murCompact } from '@/lib/format'
import type { Overview } from '@/lib/types'

/*
 * Overview answers one question: what should I know today?
 * One dominant section (the 90-day cash projection and its chart), then a short
 * table of what needs attention, then the last three months in one row.
 * Every sentence is built from the figures the API returned; nothing is estimated in the browser.
 */

const moved = (v: number) => `${v >= 0 ? 'rose' : 'fell'} ${Math.abs(v).toFixed(1)}%`

/** A change with a sign, an arrow and a word, so colour never carries the meaning alone. */
function Change({
  value,
  goodWhen = 'up',
  unit = '%',
  suffix,
}: {
  value: number | null | undefined
  goodWhen?: 'up' | 'down'
  unit?: '%' | 'pp'
  suffix?: string
}) {
  if (value === null || value === undefined) return <span className="text-sm text-ink-3">No earlier period</span>
  const flat = Math.abs(value) < 0.05
  const up = value > 0
  const good = flat ? null : goodWhen === 'up' ? up : !up
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight
  const size = unit === '%' ? `${Math.abs(value).toFixed(1)}%` : `${Math.abs(value).toFixed(1)} pts`
  return (
    <span
      className={cn(
        'tnum inline-flex items-center gap-1 text-sm',
        good === null ? 'text-ink-3' : good ? 'text-good-ink' : 'text-bad-ink',
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      {flat ? 'No change' : `${up ? '+' : '−'}${size}`}
      {suffix && <span className="text-ink-3">{suffix}</span>}
    </span>
  )
}

/** Loading placeholder shaped like the page, so nothing jumps when data arrives. */
function OverviewSkeleton() {
  return (
    <div role="status" aria-label="Loading your overview">
      <h1 className="sr-only">Overview is loading</h1>
      <Skeleton className="h-7 w-40" />
      <Skeleton className="mt-2 h-4 w-72 max-w-full" />
      <div className="panel mt-6 p-5">
        <Skeleton className="h-4 w-56" />
        <Skeleton className="mt-3 h-8 w-40" />
        <Skeleton className="mt-2 h-4 w-64" />
        <Skeleton className="mt-6 h-72 w-full" />
      </div>
      <div className="panel mt-6 divide-y divide-line">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-3">
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  )
}

/** A brand-new business: no transactions yet, so no figures are shown, only the way in. */
function FirstSteps({ d, name }: { d: Overview; name: string }) {
  const steps = [
    {
      icon: FileUp,
      title: 'Import your transactions',
      body: 'Upload a bank or card export as CSV. Valora checks every row before anything is saved.',
      to: '/data-health?tab=import',
      cta: 'Import a CSV',
    },
    {
      icon: Database,
      title: 'Review data health',
      body: 'Approve or reject suggested fixes for duplicates, missing payees and categories.',
      to: '/data-health',
      cta: 'Open data health',
    },
    {
      icon: Target,
      title: 'See what the data says',
      body: 'Risks, opportunities and a 90-day cash projection appear once there is enough history.',
      to: '/opportunities',
      cta: 'Open opportunities',
    },
  ]
  return (
    <>
      <PageHeader
        title="Overview"
        meta={`${greeting()}, ${name}`}
        description="No sales data is available yet. Import your records to see a cash projection and signals."
      />
      <dl className="mb-8 flex flex-wrap gap-x-10 gap-y-3 border-y border-line py-4 text-sm">
        <div>
          <dt className="text-ink-3">Opening cash balance</dt>
          <dd className="tnum mt-0.5 text-lg font-medium text-ink">{mur(d.cash.balance)}</dd>
        </div>
        <div>
          <dt className="text-ink-3">Records start</dt>
          <dd className="mt-0.5 font-mono text-lg text-ink">{date(d.data_window[0])}</dd>
        </div>
      </dl>
      <ol className="panel grid divide-y divide-line md:grid-cols-3 md:divide-x md:divide-y-0">
        {steps.map((s, i) => (
          <li key={s.title} className="flex flex-col p-5">
            <span className="flex items-center gap-2 text-xs text-ink-3">
              <s.icon className="size-4 text-accent-600" aria-hidden /> Step {i + 1}
            </span>
            <span className="mt-2 text-sm font-semibold text-ink">{s.title}</span>
            <span className="mt-1 flex-1 text-sm text-ink-3">{s.body}</span>
            <Link to={s.to} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent-600 hover:underline">
              {s.cta} <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </li>
        ))}
      </ol>
    </>
  )
}

const BAND_WORD = { LOW: 'Low', MODERATE: 'Moderate', HIGH: 'High', UNKNOWN: 'Unknown' } as const

export function OverviewPage() {
  const ov = useOverview()
  const opps = useOpportunities()
  const ins = useInsights()
  const cp = useCashPressure()
  const { me } = useAuth()
  if (ov.isLoading) return <OverviewSkeleton />
  if (ov.error || !ov.data)
    return (
      <ErrorState
        error={ov.error}
        title="Your overview could not be loaded."
        meaning="The latest figures are temporarily unavailable. Nothing in your records has changed."
        onRetry={() => ov.refetch()}
      />
    )
  const d = ov.data
  const name = me?.business.name ?? 'there'
  if (d.monthly.length === 0) return <FirstSteps d={d} name={name} />

  const k = d.kpis_90d
  const p = d.projection
  const pred = d.prediction
  const below = p.first_date_below_buffer
  const inDays = below ? daysBetween(d.as_of, below) : null
  const staleDays = daysBetween(d.as_of, new Date().toISOString().slice(0, 10))
  const open = (opps.data ?? []).filter((o) => o.is_active && ['new', 'reviewed', 'planned'].includes(o.status))
  const urgent = open.filter((o) => o.severity === 'critical' || o.severity === 'high').length
  const ranked = [...open].sort((a, b) => b.priority_score - a.priority_score)
  const attention = ranked.slice(0, 5)
  const vsToday = d.cash.balance ? ((p.cash_day_90 - d.cash.balance) / Math.abs(d.cash.balance)) * 100 : null
  const cashChange = d.cash.balance_30d_ago ? ((d.cash.balance - d.cash.balance_30d_ago) / Math.abs(d.cash.balance_30d_ago)) * 100 : null
  const backtestErr: number | null | undefined = cp.data?.backtest?.median_abs_error_pct_of_monthly_outflow
  const backtestN: number = cp.data?.backtest?.points?.length ?? 0

  // Where margin went in the same three months (from /insights; hidden until it loads).
  const chg = ins.data?.comparison_90d?.change_pct as Record<string, number | null> | undefined
  const supplierFinding = open.find((o) => o.detector === 'supplier_cost_inflation')
  const marginStory =
    chg && chg.cost_of_goods != null && chg.revenue != null && k.gross_margin_change_pp < 0
      ? `Gross margin fell ${Math.abs(k.gross_margin_change_pp).toFixed(1)} points: stock costs ${moved(chg.cost_of_goods)} while revenue ${moved(chg.revenue)}.`
      : null

  return (
    <>
      <PageHeader
        title="Overview"
        description="Cash forecast and the signals that need attention."
        actions={
          <span className="text-xs text-ink-3">
            Data through <span className="font-mono text-ink-2">{date(d.as_of)}</span>
          </span>
        }
      />

      {staleDays > 7 && (
        <p role="status" className="mb-6 flex items-start gap-2 rounded bg-warn-bg px-3 py-2 text-sm text-ink-2">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn-ink" aria-hidden />
          <span>
            Transactions have not been updated since {date(d.as_of)}. Projections may not reflect recent activity.{' '}
            <Link to="/data-health?tab=import" className="font-medium text-accent-600 hover:underline">
              Import new data
            </Link>
          </span>
        </p>
      )}

      {/* Primary forecast: the dominant section */}
      <section aria-labelledby="forecast-title" className="panel p-5">
        <div className="flex flex-wrap items-start justify-between gap-x-10 gap-y-6">
          <div className="min-w-0">
            <h2 id="forecast-title" className="text-sm font-semibold text-ink">
              Projected cash · in 90 days <span className="font-normal text-ink-3">(MUR)</span>
            </h2>
            <div className="tnum mt-2 text-[28px] font-medium leading-[34px] text-ink" title={mur(p.cash_day_90)}>
              {murCompact(p.cash_day_90)}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
              <Change value={vsToday} suffix="vs cash today" />
            </div>
            <p className={cn('mt-3 flex items-start gap-1.5 text-sm', below ? 'text-warn-ink' : 'text-ink-2')}>
              {below && <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />}
              {below
                ? inDays !== null && inDays >= 0
                  ? `May fall below the 14-day safety buffer in ${inDays} ${inDays === 1 ? 'day' : 'days'} (${date(below)}).`
                  : `May fall below the 14-day safety buffer on ${date(below)}.`
                : 'Stays above the 14-day safety buffer for the next 90 days.'}
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-ink-3">Cash today</dt>
              <dd className="tnum mt-0.5 font-medium text-ink">{murCompact(d.cash.balance)}</dd>
              <dd className="mt-0.5">
                <Change value={cashChange} suffix="vs 30 days ago" />
              </dd>
            </div>
            <div>
              <dt className="text-xs text-ink-3">Low point</dt>
              <dd className="tnum mt-0.5 font-medium text-ink">{murCompact(p.lowest_cash)}</dd>
              <dd className="mt-0.5 font-mono text-xs text-ink-3">{date(p.lowest_cash_date)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-3">Cash pressure, 30 days</dt>
              <dd className="mt-0.5 font-medium text-ink">
                {BAND_WORD[pred.band]}
                {pred.probability !== null && <span className="tnum font-normal text-ink-3"> · {Math.round(pred.probability * 100)}% likely</span>}
              </dd>
              <dd className="mt-0.5 text-xs text-ink-3">{d.cash.buffer_days.toFixed(0)} days of outflows covered</dd>
            </div>
          </dl>
        </div>

        <div className="mt-6">
          <CashChart actual={d.cash_series} projected={d.projection_series} buffer={p.buffer_threshold} height={300} />
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-t border-line pt-4">
          <p className="text-sm text-ink-2">
            {backtestErr != null
              ? `Recent 30-day projections were within ${backtestErr.toFixed(0)}% of a month's outflows on average (median of ${backtestN} backtests).`
              : 'A projection at current run-rates, not a recorded value.'}
          </p>
          <Link to="/insights#cash" className="inline-flex items-center gap-1 text-sm font-medium text-accent-600 hover:underline">
            View forecast detail <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        </div>
        <p className="mt-2 font-mono text-xs text-ink-3">
          deterministic projection · pressure model {pred.model_version ?? 'n/a'} · data to {date(d.as_of)}
        </p>
      </section>

      {/* Needs attention: a short table, colour only on the signal */}
      <section aria-labelledby="attention-title" className="mt-8">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 id="attention-title" className="text-lg font-semibold text-ink">
              Needs attention
            </h2>
            <p className="text-sm text-ink-3">
              {open.length > 0
                ? `${open.length} findings waiting for a decision${urgent > 0 ? `, ${urgent} high priority` : ''}. You decide; Valora never changes your records.`
                : 'Ranked by the opportunity engine from your own records.'}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/scenarios" className="inline-flex items-center gap-1 text-sm font-medium text-accent-600 hover:underline">
              <FlaskConical className="size-4" aria-hidden /> Test a change
            </Link>
            {open.length > attention.length && (
              <Link to="/opportunities" className="inline-flex items-center gap-1 text-sm font-medium text-accent-600 hover:underline">
                View all {open.length} <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            )}
          </div>
        </div>
        <div className="panel overflow-x-auto">
          {opps.isLoading ? (
            <div className="divide-y divide-line">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-5 py-3">
                  <Skeleton className="h-4 flex-1" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-16" />
                </div>
              ))}
            </div>
          ) : attention.length === 0 ? (
            <p className="px-5 py-6 text-sm text-ink-3">
              Nothing needs a decision right now. Valora checks again after every import.{' '}
              <Link to="/scenarios" className="font-medium text-accent-600 hover:underline">
                Test a change in the scenario lab
              </Link>
            </p>
          ) : (
            <table className="w-full min-w-[640px] text-sm">
              <thead className="border-b border-line text-left text-ink-3">
                <tr>
                  <th className="px-5 py-2.5 font-medium">Finding</th>
                  <th className="px-3 py-2.5 font-medium">Next step</th>
                  <th className="px-3 py-2.5 text-right font-medium">Estimated impact</th>
                  <th className="px-3 py-2.5 font-medium">Signal</th>
                  <th className="px-5 py-2.5 text-right font-medium">
                    <span className="sr-only">Action</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {attention.map((o) => (
                  <tr key={o.id} className="transition-colors hover:bg-mist">
                    <td className="max-w-[22rem] px-5 py-2.5">
                      <div className="truncate text-ink" title={o.title}>
                        {o.title}
                      </div>
                      <div className="text-xs text-ink-3">{o.kind === 'risk' ? 'Risk' : 'Opportunity'}</div>
                    </td>
                    <td className="max-w-[16rem] px-3 py-2.5 text-ink-2">
                      <div className="truncate" title={o.actions[0]?.title}>
                        {o.actions[0]?.title ?? '—'}
                      </div>
                    </td>
                    <td className="tnum whitespace-nowrap px-3 py-2.5 text-right">
                      {o.impact_low !== null && o.impact_high !== null ? (
                        <>
                          <span className="text-ink">
                            {murCompact(o.impact_low)} – {murCompact(o.impact_high).replace('MUR ', '')}
                          </span>
                          <div className="text-xs text-ink-3">{IMPACT_SHORT[o.impact_kind]}</div>
                        </>
                      ) : (
                        <span className="text-ink-3">Not sized</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5">
                      <SeverityBadge severity={o.severity} />
                    </td>
                    <td className="px-5 py-2.5 text-right">
                      <Link to={`/opportunities?open=${o.id}`} className="font-medium text-accent-600 hover:underline">
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* Last three months: one row of figures, no cards */}
      <section aria-labelledby="period-title" className="mt-8">
        <h2 id="period-title" className="text-lg font-semibold text-ink">
          Last 3 months
        </h2>
        <p className="text-sm text-ink-3">{monthSpan(k.period)} compared with the 3 months before</p>
        <dl className="mt-3 grid grid-cols-1 divide-y divide-line border-y border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <div className="py-4 sm:pr-6">
            <dt className="text-xs text-ink-3">Revenue</dt>
            <dd className="tnum mt-1 text-lg font-medium text-ink" title={mur(k.revenue)}>
              {murCompact(k.revenue)}
            </dd>
            <dd>
              <Change value={k.revenue_change_pct} />
            </dd>
          </div>
          <div className="py-4 sm:px-6">
            <dt className="text-xs text-ink-3">Expenses</dt>
            <dd className="tnum mt-1 text-lg font-medium text-ink" title={mur(k.expenses)}>
              {murCompact(k.expenses)}
            </dd>
            <dd>
              <Change value={k.expenses_change_pct} goodWhen="down" />
            </dd>
          </div>
          <div className="py-4 sm:pl-6">
            <dt className="text-xs text-ink-3">Gross margin</dt>
            <dd className="tnum mt-1 text-lg font-medium text-ink">{k.gross_margin_pct.toFixed(1)}%</dd>
            <dd>
              <Change value={k.gross_margin_change_pp} unit="pp" />
            </dd>
          </div>
        </dl>
        {marginStory ? (
          <InsightStrip
            className="mt-0 border-t-0"
            tone="attention"
            action={{
              label: 'Review supplier costs',
              to: supplierFinding ? `/opportunities?open=${supplierFinding.id}` : '/insights#trend',
            }}
          >
            {marginStory}
          </InsightStrip>
        ) : (
          <InsightStrip className="mt-0 border-t-0" action={{ label: 'Open financial insights', to: '/insights' }}>
            Revenue and costs by month, customers, suppliers and recurring payments are on financial insights.
          </InsightStrip>
        )}
      </section>
    </>
  )
}
