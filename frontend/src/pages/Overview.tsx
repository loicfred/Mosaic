import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Database,
  FileUp,
  FlaskConical,
  Minus,
  Target,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { CashChart } from '@/charts/CashChart'
import { SeverityBadge } from '@/components/domain/labels'
import { PageHeader } from '@/components/layout/AppShell'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { InsightStrip } from '@/components/ui/insight-strip'
import { ErrorState, Skeleton } from '@/components/ui/states'
import { Meter } from '@/components/viz/Meter'
import { useInsights, useOpportunities, useOverview } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { IMPACT_SHORT } from '@/lib/findings'
import { date, daysBetween, greeting, monthSpan, mur, murCompact } from '@/lib/format'
import type { Opportunity, Overview } from '@/lib/types'

/*
 * Overview: how is the business doing, and what needs attention now?
 * Laid out as a Z: the cash position (top left) and the recommended next step
 * (top right), then the last three months (left) and the cash outlook (right),
 * then the two most important findings. Every sentence is built from the
 * figures the API returned; nothing is estimated in the browser.
 */

const moved = (v: number) => `${v >= 0 ? 'rose' : 'fell'} ${Math.abs(v).toFixed(1)}%`

/** A change with an arrow and a colour that agree with the words. */
function Change({
  value,
  goodWhen = 'up',
  unit = '%',
  chip,
}: {
  value: number | null | undefined
  goodWhen?: 'up' | 'down'
  unit?: '%' | 'pp'
  chip?: boolean
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
        'inline-flex items-center gap-1 text-sm font-medium',
        chip && 'rounded-full px-2.5 py-1',
        good === null ? 'text-ink-3' : good ? 'text-good-ink' : 'text-bad-ink',
        chip && (good === null ? 'bg-brand-50' : good ? 'bg-good-bg' : 'bg-bad-bg'),
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      {flat ? 'No change' : `${size} ${up ? 'higher' : 'lower'}`}
    </span>
  )
}

/** Loading placeholder shaped like the card grid, so nothing jumps when data arrives. */
function OverviewSkeleton() {
  return (
    <div role="status" aria-label="Loading your overview">
      <h1 className="sr-only">Overview is loading</h1>
      <Skeleton className="h-4 w-40" />
      <Skeleton className="mt-3 h-9 w-[min(520px,90%)]" />
      <div className="mt-7 grid gap-5 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
        <Skeleton className="h-72 rounded-[20px]" />
        <Skeleton className="h-72 rounded-[20px]" />
        <Skeleton className="h-80 rounded-[20px]" />
        <Skeleton className="h-80 rounded-[20px]" />
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
      <ol className="grid gap-px overflow-hidden rounded-[20px] border border-line bg-line shadow-card md:grid-cols-3">
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
  const ins = useInsights()
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
  const below = p.first_date_below_buffer
  const inDays = below ? daysBetween(d.as_of, below) : null
  const open = (opps.data ?? []).filter((o) => o.is_active && ['new', 'reviewed', 'planned'].includes(o.status))
  const urgent = open.filter((o) => o.severity === 'critical' || o.severity === 'high').length
  const ranked = [...open].sort((a, b) => b.priority_score - a.priority_score)
  const cashFinding = open.find((o) => o.detector === 'cash_pressure')
  // The recommended next step: the cash finding when cash is the headline, otherwise the top-ranked finding.
  const next = below && cashFinding ? cashFinding : ranked[0]
  const top = ranked.filter((o) => o.id !== next?.id).slice(0, 2)
  const buffer = d.cash.buffer_days
  const cashChange = d.cash.balance_30d_ago ? ((d.cash.balance - d.cash.balance_30d_ago) / Math.abs(d.cash.balance_30d_ago)) * 100 : null

  // Where the money went in the same three months (from /insights; hidden until it loads).
  const cur = ins.data?.comparison_90d?.current as Record<string, number> | undefined
  const chg = ins.data?.comparison_90d?.change_pct as Record<string, number | null> | undefined
  const spend = cur
    ? [
        { label: 'Stock & supplies', value: cur.cost_of_goods, color: 'bg-periwinkle-500' },
        { label: 'Operating costs', value: cur.operating_expenses, color: 'bg-sage-500' },
        { label: 'VAT', value: cur.tax, color: 'bg-gold-500' },
      ].filter((x) => x.value > 0)
    : []
  const spendTotal = spend.reduce((s, x) => s + x.value, 0)
  const supplierFinding = open.find((o) => o.detector === 'supplier_cost_inflation')
  const marginStory =
    chg && chg.cost_of_goods !== null && chg.revenue !== null && k.gross_margin_change_pp < 0
      ? `Gross margin fell ${Math.abs(k.gross_margin_change_pp).toFixed(1)} points: stock costs ${moved(chg.cost_of_goods)} while revenue ${moved(chg.revenue)}.`
      : null

  return (
    <>
      <PageHeader
        title={`${greeting()}, ${name}`}
        meta={`Overview · data to ${date(d.as_of)}`}
        description="Here's what needs your attention this week."
      />

      {/* ROW 1 (Z, top): where cash stands  →  what to do about it */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
        <Card aria-labelledby="cash-status" className="fade-coral flex flex-col">
          <CardHeader
            title="Cash position"
            subtitle="End-of-day balance from recorded transactions"
            action={
              <span
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold',
                  below ? 'bg-serious-bg text-serious-ink' : 'bg-good-bg text-good-ink',
                )}
              >
                {below ? <AlertTriangle className="size-4" aria-hidden /> : <CheckCircle2 className="size-4" aria-hidden />}
                {below ? 'Needs attention' : 'On track'}
              </span>
            }
          />
          <CardBody className="flex flex-1 flex-col">
            <p id="cash-status" className="max-w-2xl text-2xl font-semibold leading-snug tracking-tight text-ink sm:text-[26px]">
              {below
                ? inDays !== null && inDays >= 0
                  ? `Cash may fall below your safety buffer in ${inDays} ${inDays === 1 ? 'day' : 'days'}.`
                  : `Cash may fall below your safety buffer on ${date(below)}.`
                : 'Cash stays above your safety buffer for the next 90 days.'}
            </p>
            <div className="mt-6">
              <div className="text-sm text-ink-3">Cash today, compared with 30 days ago</div>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <span className="tnum text-[40px] font-semibold leading-none tracking-tight text-ink" title={mur(d.cash.balance)}>
                  {murCompact(d.cash.balance)}
                </span>
                <Change value={cashChange} chip />
              </div>
            </div>
            <div className="mt-6">
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
                <span className="font-medium text-ink">{buffer.toFixed(0)} days of outflows covered</span>
                <span className="text-ink-3">Safety buffer: 14 days (black line)</span>
              </div>
              <Meter
                value={buffer}
                max={Math.max(30, Math.ceil(buffer * 1.25))}
                tone={buffer < 14 ? 'bad' : buffer < 21 ? 'warn' : 'good'}
                marker={{ value: 14 }}
                label={`Cash covers ${buffer.toFixed(0)} days of outflows; the safety buffer is 14 days`}
              />
            </div>
            <div className="mt-auto">
              <InsightStrip tone={below ? 'attention' : 'good'} action={{ label: 'View forecast', to: '/insights#cash' }}>
                Projected low point <strong className="font-semibold">{murCompact(p.lowest_cash)}</strong> on {date(p.lowest_cash_date)}
                {below && <>, {p.days_below_buffer} of the next 90 days under the buffer</>}. This is a projection at current run-rates, not
                a recorded value.
              </InsightStrip>
            </div>
          </CardBody>
        </Card>

        <NextStep o={next} />
      </div>

      {/* ROW 2 (Z, middle): the last three months  →  the cash outlook */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.55fr)]">
        <Card className="fade-sage flex flex-col">
          <CardHeader title="Last 3 months" subtitle={`${monthSpan(k.period)} compared with the 3 months before`} />
          <CardBody className="flex flex-1 flex-col">
            <div className="text-sm text-ink-3">Revenue</div>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <span className="tnum text-[36px] font-semibold leading-none tracking-tight text-ink" title={mur(k.revenue)}>
                {murCompact(k.revenue)}
              </span>
              <Change value={k.revenue_change_pct} chip />
            </div>

            <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-line pt-5">
              <div>
                <dt className="text-sm text-ink-3">Expenses</dt>
                <dd className="tnum mt-0.5 text-xl font-semibold text-ink" title={mur(k.expenses)}>
                  {murCompact(k.expenses)}
                </dd>
                <dd className="mt-0.5">
                  <Change value={k.expenses_change_pct} goodWhen="down" />
                </dd>
              </div>
              <div>
                <dt className="text-sm text-ink-3">Gross margin</dt>
                <dd className="tnum mt-0.5 text-xl font-semibold text-ink">{k.gross_margin_pct.toFixed(1)}%</dd>
                <dd className="mt-0.5">
                  <Change value={k.gross_margin_change_pp} unit="pp" />
                </dd>
              </div>
            </dl>

            {spendTotal > 0 && (
              <figure className="mt-6">
                <figcaption className="mb-2 text-sm font-medium text-ink">Where the money went</figcaption>
                <div className="flex h-3 gap-1 overflow-hidden rounded-full" aria-hidden>
                  {spend.map((x) => (
                    <span
                      key={x.label}
                      className={cn('grow-x h-full rounded-full', x.color)}
                      style={{ width: `${(x.value / spendTotal) * 100}%` }}
                    />
                  ))}
                </div>
                <ul className="mt-3 grid grid-cols-3 gap-2">
                  {spend.map((x) => (
                    <li key={x.label} className="min-w-0">
                      <span className="tnum block text-base font-semibold text-ink">{murCompact(x.value)}</span>
                      <span className="flex items-center gap-1.5 text-xs text-ink-3">
                        <span className={cn('size-2 shrink-0 rounded-full', x.color)} aria-hidden />
                        <span className="truncate">{x.label}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </figure>
            )}

            <div className="mt-auto">
              {marginStory ? (
                <InsightStrip
                  action={{
                    label: 'Review supplier costs',
                    to: supplierFinding ? `/opportunities?open=${supplierFinding.id}` : '/insights#trend',
                  }}
                >
                  {marginStory}
                </InsightStrip>
              ) : (
                <InsightStrip action={{ label: 'Open Financial Insights', to: '/insights' }}>
                  Revenue and costs by month, customers, suppliers and recurring payments are on Financial Insights.
                </InsightStrip>
              )}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Cash outlook" subtitle="Actual cash for the past 180 days, projected for the next 90" />
          <CardBody>
            <CashChart actual={d.cash_series} projected={d.projection_series} buffer={p.buffer_threshold} height={280} />
            <InsightStrip tone="insight" action={{ label: 'View detailed forecast', to: '/insights#cash' }}>
              {below
                ? `The projection crosses the 14-day safety buffer (${murCompact(p.buffer_threshold)}) on ${date(below)} and stays under it for ${p.days_below_buffer} of the 90 days.`
                : `The projection stays above the 14-day safety buffer (${murCompact(p.buffer_threshold)}) for the next 90 days.`}
            </InsightStrip>
          </CardBody>
        </Card>
      </div>

      {/* ROW 3 (Z, bottom): what else deserves a look */}
      <Card className="fade-gold mt-5">
        <CardHeader title="Other important findings" subtitle="Ranked by the opportunity engine from your own records" />
        <CardBody>
          {top.length === 0 ? (
            <div className="rounded-2xl border border-line bg-surface-2 px-6 py-8 text-center">
              <p className="font-medium text-ink">No new opportunities right now</p>
              <p className="mt-1 text-sm text-ink-3">Valora checks again after every import and will list anything worth reviewing here.</p>
            </div>
          ) : (
            <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {top.map((o) => (
                <FindingSummary key={o.id} o={o} />
              ))}
            </ul>
          )}
          {open.length > 0 && (
            <InsightStrip action={{ label: 'Review all findings', to: '/opportunities' }}>
              <strong className="font-semibold">{open.length} findings</strong> are waiting for a decision
              {urgent > 0 && <>, {urgent} of them high priority</>}.
            </InsightStrip>
          )}
        </CardBody>
      </Card>
    </>
  )
}

/** The highlighted card: one recommended next step, from a real finding. The user decides. */
function NextStep({ o }: { o?: Opportunity }) {
  if (!o)
    return (
      <section aria-labelledby="next-step" className="panel flex flex-col p-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-ink-3">Recommended next step</p>
        <h2 id="next-step" className="mt-3 text-xl font-semibold text-ink">
          Nothing needs a decision right now
        </h2>
        <p className="mt-2 text-sm text-ink-2">You can still test a change to prices, costs or collections before making it.</p>
        <Link to="/scenarios" className="mt-auto pt-6 text-sm font-medium text-accent-700 underline underline-offset-2">
          Open the Scenario Lab
        </Link>
      </section>
    )
  const action = o.actions[0]?.title ?? o.title
  return (
    <section
      aria-labelledby="next-step"
      className="flex flex-col rounded-[20px] bg-[#4f57eb] bg-[linear-gradient(150deg,#5b63f5_0%,#4f57eb_50%,#4148d6_100%)] p-6 text-white shadow-[0_18px_40px_-24px_rgba(63,70,207,0.9)]"
    >
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider">
        <Target className="size-4" aria-hidden /> Recommended next step
      </p>
      <h2 id="next-step" className="mt-4 text-[22px] font-semibold leading-snug">
        {action}
      </h2>
      <p className="mt-2 text-[15px] leading-relaxed">Why: {o.title.charAt(0).toLowerCase() + o.title.slice(1)}.</p>
      {o.impact_low !== null && o.impact_high !== null && (
        <div className="mt-5 rounded-2xl bg-[#3f46cf] px-4 py-3">
          <p className="text-sm">{IMPACT_SHORT[o.impact_kind].replace(/^./, (c) => c.toUpperCase())} (estimate)</p>
          <p className="tnum mt-0.5 text-2xl font-semibold">
            {murCompact(o.impact_low)} – {murCompact(o.impact_high)}
          </p>
        </div>
      )}
      <div className="mt-auto flex flex-col gap-2 pt-6">
        <Link
          to={`/opportunities?open=${o.id}`}
          className="flex h-11 items-center justify-center gap-2 rounded-xl bg-white text-[15px] font-semibold text-[#3f46cf] transition-colors hover:bg-periwinkle-50"
        >
          See what to do <ArrowRight className="size-4" aria-hidden />
        </Link>
        <Link
          to="/scenarios"
          className="flex h-11 items-center justify-center gap-2 rounded-xl text-[15px] font-medium text-white ring-1 ring-inset ring-white/70 bg-[#3f46cf] transition-colors hover:bg-[#353bb5]"
        >
          <FlaskConical className="size-4" aria-hidden /> Test a fix
        </Link>
      </div>
      <p className="mt-3 text-center text-xs">You decide. Valora never changes your records.</p>
    </section>
  )
}

/** What was found, why it matters, and the next step. */
function FindingSummary({ o }: { o: Opportunity }) {
  return (
    <li className="flex flex-col rounded-2xl border border-line bg-white/80 p-5">
      <div className="flex items-center gap-2">
        <SeverityBadge severity={o.severity} />
        <span className="text-sm text-ink-3">{o.kind === 'risk' ? 'Risk' : 'Opportunity'}</span>
      </div>
      <h3 className="mt-3 text-base font-semibold leading-snug text-ink">{o.title}</h3>
      <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-ink-2">{o.summary}</p>
      <p className="mt-3 text-sm text-ink-2">
        {o.impact_low !== null && o.impact_high !== null ? (
          <>
            <strong className="tnum text-lg font-semibold text-ink">
              {murCompact(o.impact_low)} – {murCompact(o.impact_high)}
            </strong>{' '}
            {IMPACT_SHORT[o.impact_kind]} <span className="text-ink-3">(estimate)</span>
          </>
        ) : (
          <span className="text-ink-3">Not sized</span>
        )}
      </p>
      {o.actions[0] && (
        <p className="mt-2 text-sm text-ink-2">
          <span className="font-medium text-ink">Next step:</span> {o.actions[0].title}
        </p>
      )}
      <Link
        to={`/opportunities?open=${o.id}`}
        className="mt-4 inline-flex w-fit items-center gap-1 rounded-xl border border-line bg-surface px-3 py-2 text-sm font-medium text-accent-700 transition-colors hover:border-accent-500 hover:bg-accent-50"
      >
        Review this finding <ArrowRight className="size-4" aria-hidden />
      </Link>
    </li>
  )
}
