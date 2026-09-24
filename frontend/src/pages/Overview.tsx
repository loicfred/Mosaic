import { AlertTriangle, ArrowRight, CheckCircle2, Database, FileUp, FlaskConical, Target } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { CashChart } from '@/charts/CashChart'
import { MonthlyChart } from '@/charts/MonthlyChart'
import { C } from '@/charts/theme'
import { DataKind, Delta, OutcomeBadge } from '@/components/domain/labels'
import { MetricStrip } from '@/components/domain/MetricStrip'
import { PredictionCard } from '@/components/domain/PredictionCard'
import { AskValora } from '@/components/insight/AskValora'
import { PageHeader } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { ErrorState, PageSkeleton } from '@/components/ui/states'
import { BeforeAfter } from '@/components/viz/BeforeAfter'
import { InfoTip } from '@/components/viz/InfoTip'
import { Meter } from '@/components/viz/Meter'
import { useOpportunities, useOverview } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { IMPACT_SHORT } from '@/lib/findings'
import { axisMur, date, daysBetween, greeting, metric, monthSpan, mur, murCompact } from '@/lib/format'
import type { Opportunity, Overview } from '@/lib/types'

const DOT: Record<Opportunity['severity'], string> = { critical: 'bg-bad', high: 'bg-serious', medium: 'bg-warn', low: 'bg-before' }

function SectionTitle({ children, action, info }: { children: React.ReactNode; action?: React.ReactNode; info?: React.ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
      <h2 className="flex items-center gap-1.5 text-lg font-semibold tracking-tight text-ink">
        {children}
        {info && <InfoTip content={info} />}
      </h2>
      {action}
    </div>
  )
}

const RANGES = [
  { key: 3, label: '3 months' },
  { key: 6, label: '6 months' },
  { key: 12, label: '12 months' },
] as const

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
      cta: 'Open Data Health',
    },
    {
      icon: Target,
      title: 'See what the data says',
      body: 'Risks, opportunities and a 90-day cash projection appear once there is enough history.',
      to: '/opportunities',
      cta: 'Open Opportunities',
    },
  ]
  return (
    <>
      <PageHeader
        title={`${greeting()}, ${name}`}
        meta="No data yet"
        description="Your business is set up. Valora has nothing to analyse until you import your records."
      />
      <dl className="mb-10 flex flex-wrap gap-x-10 gap-y-3 border-y border-line py-4 text-sm">
        <div>
          <dt className="text-ink-3">Opening cash balance</dt>
          <dd className="tnum mt-0.5 text-lg font-semibold text-ink">{mur(d.cash.balance)}</dd>
        </div>
        <div>
          <dt className="text-ink-3">Records start</dt>
          <dd className="mt-0.5 text-lg font-semibold text-ink">{date(d.data_window[0])}</dd>
        </div>
      </dl>
      <ol className="grid gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-3">
        {steps.map((s, i) => (
          <li key={s.title} className="flex flex-col bg-surface p-5">
            <span className="flex items-center gap-2 text-xs font-medium text-ink-3">
              <s.icon className="size-4 text-accent-600" aria-hidden /> Step {i + 1}
            </span>
            <span className="mt-2 font-semibold text-ink">{s.title}</span>
            <span className="mt-1 flex-1 text-sm text-ink-3">{s.body}</span>
            <Link to={s.to} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent-700 hover:underline">
              {s.cta} <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </li>
        ))}
      </ol>
    </>
  )
}

export function OverviewPage() {
  const ov = useOverview()
  const opps = useOpportunities()
  const { me } = useAuth()
  const [range, setRange] = useState<(typeof RANGES)[number]['key']>(12)
  if (ov.isLoading) return <PageSkeleton />
  if (ov.error || !ov.data) return <ErrorState error={ov.error} onRetry={() => ov.refetch()} />
  const d = ov.data
  const name = me?.business.name ?? 'there'
  if (d.monthly.length === 0) return <FirstSteps d={d} name={name} />
  const k = d.kpis_90d
  const open = (opps.data ?? []).filter((o) => o.is_active && ['new', 'reviewed', 'planned'].includes(o.status))
  const urgent = open.filter((o) => o.severity === 'critical' || o.severity === 'high').length
  const tracked = (opps.data ?? []).filter((o) => ['in_progress', 'completed'].includes(o.status))
  const cashDelta = ((d.cash.balance - d.cash.balance_30d_ago) / Math.abs(d.cash.balance_30d_ago || 1)) * 100
  const full = d.monthly.filter((m) => !m.partial)
  const below = d.projection.first_date_below_buffer
  const inDays = below ? daysBetween(d.as_of, below) : null
  const bufferTone = d.cash.buffer_days < 14 ? 'bad' : d.cash.buffer_days < 21 ? 'warn' : 'good'

  return (
    <>
      <PageHeader
        title={`${greeting()}, ${name}`}
        meta={`Overview · data to ${date(d.as_of)}`}
        description="How the business is doing, and what needs you this week."
      />

      {/* Level 1: one sentence and the three things waiting for a decision. */}
      <section className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:gap-12">
        <div className={cn('rounded-xl border-l-4 p-5 sm:p-6', below ? 'border-coral-500 bg-coral-50' : 'border-sage-500 bg-sage-50')}>
          <div
            className={cn(
              'flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider',
              below ? 'text-bad-ink' : 'text-good-ink',
            )}
          >
            {below ? <AlertTriangle className="size-3.5" aria-hidden /> : <CheckCircle2 className="size-3.5" aria-hidden />}
            {below ? 'Needs attention' : 'On track'}
          </div>
          <p className="mt-2 max-w-3xl text-[22px] font-semibold leading-snug tracking-tight text-ink md:text-2xl">
            {below ? (
              <>
                Cash is projected to fall below your safety buffer on {date(below)}
                {inDays !== null && inDays >= 0 && <span className="text-bad-ink"> - in {inDays} days</span>}.
              </>
            ) : (
              'Cash stays above your 14-day safety buffer for the next 90 days.'
            )}
          </p>
          <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-ink-3">
            Lowest point {murCompact(d.projection.lowest_cash)} on {date(d.projection.lowest_cash_date)}
            {below && (
              <>
                {' '}
                · {d.projection.days_below_buffer} of the next 90 days below {murCompact(d.projection.buffer_threshold)}
              </>
            )}
            <DataKind kind="projected" />
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button asChild>
              <Link to="/opportunities">
                See what to do <ArrowRight />
              </Link>
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/scenarios">
                <FlaskConical /> Test a fix
              </Link>
            </Button>
          </div>
        </div>

        <ul aria-label="Waiting for you" className="divide-y divide-line self-start border-y border-line text-sm">
          <li>
            <Link to="/opportunities" className="flex items-baseline gap-3 py-3 hover:bg-surface-2/60">
              <span className="w-10 text-2xl font-semibold tracking-tight text-ink">{open.length}</span>
              <span className="text-ink-2">
                findings to decide
                {urgent > 0 && <span className="block text-xs text-serious-ink">{urgent} high or critical</span>}
              </span>
            </Link>
          </li>
          <li>
            <Link to="/data-health" className="flex items-baseline gap-3 py-3 hover:bg-surface-2/60">
              <span className={cn('w-10 text-2xl font-semibold tracking-tight', d.data_health.issues ? 'text-warn-ink' : 'text-ink')}>
                {d.data_health.issues}
              </span>
              <span className="text-ink-2">
                data items to review
                <span className="block text-xs text-ink-3">data health {d.data_health.score}/100</span>
              </span>
            </Link>
          </li>
          <li>
            <Link to="/opportunities" className="flex items-baseline gap-3 py-3 hover:bg-surface-2/60">
              <span className="w-10 text-2xl font-semibold tracking-tight text-ink">{tracked.length}</span>
              <span className="text-ink-2">
                actions being measured
                <span className="block text-xs text-ink-3">{tracked.filter((o) => o.outcome?.status === 'achieved').length} achieved</span>
              </span>
            </Link>
          </li>
        </ul>
      </section>

      {/* Level 2: the four numbers that describe the business, with how they got here. */}
      <section className="mt-12">
        <SectionTitle
          info={`Revenue, expenses and margin compare ${monthSpan(k.period)} with ${monthSpan(k.previous_period)}. Trend lines show each complete month.`}
          action={<AskValora question="How did revenue change recently?" context={{ type: 'chart', chart: 'kpis' }} />}
        >
          Last three months
        </SectionTitle>
        <MetricStrip
          items={[
            {
              label: 'Cash today',
              title: mur(d.cash.balance),
              value: murCompact(d.cash.balance),
              delta: <Delta value={cashDelta} unit="vs 30 days ago" />,
              visual: (
                <div>
                  <div className="mb-1 text-xs text-ink-2">
                    <strong className="font-semibold text-ink">{d.cash.buffer_days.toFixed(0)} days</strong> of outflows covered
                  </div>
                  <Meter
                    value={d.cash.buffer_days}
                    max={Math.max(30, Math.ceil(d.cash.buffer_days * 1.25))}
                    tone={bufferTone}
                    size="sm"
                    marker={{ value: 14, label: '14-day buffer' }}
                    label={`Cash covers ${d.cash.buffer_days.toFixed(0)} days of outflows; the safety buffer is 14 days`}
                  />
                </div>
              ),
            },
            {
              label: 'Revenue',
              value: murCompact(k.revenue),
              delta: <Delta value={k.revenue_change_pct} unit="vs previous 3" />,
              spark: full.map((m) => m.revenue),
              sparkLabel: `Monthly revenue over ${full.length} months`,
            },
            {
              label: 'Expenses',
              value: murCompact(k.expenses),
              delta: <Delta value={k.expenses_change_pct} goodWhen="down" unit="vs previous 3" />,
              spark: full.map((m) => m.expenses),
              sparkColor: C.expense,
              sparkLabel: `Monthly expenses over ${full.length} months`,
            },
            {
              label: 'Gross margin',
              value: `${k.gross_margin_pct.toFixed(1)}%`,
              delta: <Delta value={k.gross_margin_change_pp} suffix=" pp" unit="vs previous 3" />,
              spark: full.map((m) => m.gross_margin_pct),
              sparkLabel: `Monthly gross margin over ${full.length} months`,
            },
          ]}
        />
      </section>

      {/* The cash story: what happened, what is projected, and the model's read on it. */}
      <section className="mt-12">
        <SectionTitle
          info="Actual: end-of-day balance from recorded transactions. Projected: deterministic projection at current run-rates. The red line is 14 days of committed outflows."
          action={<AskValora question="What does the cash chart show?" context={{ type: 'chart', chart: 'cash' }} />}
        >
          Cash, past 180 days and next 90
        </SectionTitle>
        <div className="grid grid-cols-1 overflow-hidden rounded-xl border border-line bg-surface lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="min-w-0 p-5 lg:p-6">
            <CashChart actual={d.cash_series} projected={d.projection_series} buffer={d.projection.buffer_threshold} height={330} />
          </div>
          <div className="border-t border-line bg-periwinkle-50 p-5 lg:border-l lg:border-t-0 lg:p-6">
            <PredictionCard p={d.prediction} />
          </div>
        </div>
      </section>

      <div className="mt-12 grid gap-12 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section>
          <SectionTitle
            action={
              <Link to="/opportunities" className="inline-flex items-center gap-1 text-sm font-medium text-accent-700 hover:underline">
                All {open.length} findings <ArrowRight className="size-4" />
              </Link>
            }
          >
            What needs attention
          </SectionTitle>
          <ul className="divide-y divide-line border-y border-line">
            {open.slice(0, 5).map((o) => (
              <li key={o.id}>
                <Link
                  to={`/opportunities?open=${o.id}`}
                  className="group grid grid-cols-[auto_minmax(0,1fr)_auto] items-baseline gap-x-3 py-3.5 transition-colors hover:bg-surface-2/60 sm:gap-x-4"
                >
                  <span className={cn('size-2 translate-y-[-1px] rounded-full', DOT[o.severity])} aria-label={`${o.severity} severity`} />
                  <span className="min-w-0">
                    <span className="block font-medium text-ink group-hover:underline">{o.title}</span>
                    <span className="block truncate text-sm text-ink-3">{o.summary}</span>
                  </span>
                  <span className="text-right">
                    <span className="tnum block text-sm font-semibold text-ink">
                      {o.impact_high === null ? '—' : `${murCompact(o.impact_low)}–${axisMur(o.impact_high)}`}
                    </span>
                    <span className="block text-xs text-ink-3">{IMPACT_SHORT[o.impact_kind]}</span>
                  </span>
                </Link>
              </li>
            ))}
            {open.length === 0 && (
              <li className="py-6 text-sm text-ink-3">Nothing waiting for a decision. New findings appear after each import.</li>
            )}
          </ul>
        </section>

        <section>
          <SectionTitle info="When an action starts, its target metric is frozen and re-measured on later data. Evidence, not proof of cause.">
            Did the actions work?
          </SectionTitle>
          {tracked.length === 0 ? (
            <p className="border-y border-line py-6 text-sm text-ink-3">
              No actions started yet. Start one from a finding and its result is measured here.
            </p>
          ) : (
            <ul className="divide-y divide-line border-y border-line">
              {tracked.map((o) => {
                const oc = o.outcome
                return (
                  <li key={o.id}>
                    <Link to={`/opportunities?open=${o.id}`} className="block space-y-3 py-4 hover:bg-surface-2/60">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium text-ink">{o.title}</span>
                        {oc && <OutcomeBadge outcome={oc} />}
                      </div>
                      {oc && oc.baseline !== undefined && oc.current !== undefined && (
                        <>
                          <BeforeAfter
                            before={oc.baseline}
                            after={oc.current}
                            format={(v) => metric(v, oc.unit)}
                            afterColor={oc.status === 'achieved' ? 'var(--color-good)' : 'var(--color-actual)'}
                          />
                          <p className="text-xs text-ink-3">{oc.metric_label}</p>
                        </>
                      )}
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>

      <section className="mt-12">
        <SectionTitle
          action={
            <div className="flex flex-wrap items-center gap-3">
              <AskValora question="What happened month by month?" context={{ type: 'chart', chart: 'monthly' }} />
              <div role="group" aria-label="Months shown" className="inline-flex rounded-lg border border-line bg-surface p-0.5">
                {RANGES.map((r) => (
                  <button
                    key={r.key}
                    type="button"
                    aria-pressed={range === r.key}
                    onClick={() => setRange(r.key)}
                    className={cn(
                      'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                      range === r.key ? 'bg-accent-50 text-accent-700' : 'text-ink-3 hover:text-ink',
                    )}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
              <DataKind kind="actual" />
            </div>
          }
        >
          Revenue and expenses by month
        </SectionTitle>
        <div className="rounded-xl border border-line bg-surface p-5 lg:p-6">
          <MonthlyChart months={d.monthly.slice(-range)} />
        </div>
      </section>
    </>
  )
}
