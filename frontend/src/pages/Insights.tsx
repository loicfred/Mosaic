import { AlertCircle, ArrowRight, CalendarClock, ChevronDown, Clock } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartTooltipBox } from '@/charts/ChartTooltip'
import { CashChart } from '@/charts/CashChart'
import { HBarList } from '@/charts/HBarList'
import { MonthlyChart } from '@/charts/MonthlyChart'
import { axisTick, C } from '@/charts/theme'
import { MetricStrip } from '@/components/domain/MetricStrip'
import { PredictionCard } from '@/components/domain/PredictionCard'
import { DataKind, Delta } from '@/components/domain/labels'
import { PageHeader } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { ErrorState, PageSkeleton } from '@/components/ui/states'
import { CompositionBar } from '@/components/viz/CompositionBar'
import { Dumbbell } from '@/components/viz/Dumbbell'
import { Meter } from '@/components/viz/Meter'
import { useInsights, useOverview } from '@/hooks/queries'
import { axisMur, date, monthLabel, monthSpan, mur, murCompact } from '@/lib/format'
import type { MonthRow } from '@/lib/types'

interface Counterparty {
  name: string
  amount: number
  share_pct: number
  transactions: number
}
interface Concentration {
  side: 'customer' | 'supplier'
  top: Counterparty[]
  top_share_pct: number
  top3_share_pct: number
  hhi_identified: number
  unidentified_amount: number
  unidentified_label: string
}
interface Recurring {
  key: string
  name: string
  category: string
  cadence: string
  monthly_run_rate: number
  is_new: boolean
  first_seen: string
}

function TraceLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link to={to} className="inline-flex items-center gap-1 text-xs font-medium text-accent-600 hover:underline">
      {children} <ArrowRight className="size-3" />
    </Link>
  )
}

const SECTIONS = [
  ['cash', 'Cash forecast'],
  ['trend', 'Trend'],
  ['costs', 'Costs & sales'],
  ['concentration', 'Dependence'],
  ['commitments', 'Commitments'],
  ['collections', 'Collections'],
] as const

/** An open section heading that states the finding first; the cards below are the evidence. */
function Group({ id, title, insight }: { id: string; title: string; insight: ReactNode }) {
  return (
    <div id={id} className="mb-4 mt-12 scroll-mt-20">
      <h2 className="text-xs font-medium text-ink-3">{title}</h2>
      <p className="mt-1 max-w-3xl text-lg font-semibold text-ink">{insight}</p>
    </div>
  )
}

const change = (v: number | null | undefined, up = 'rose', down = 'fell') =>
  v === null || v === undefined ? 'was flat' : `${v >= 0 ? up : down} ${Math.abs(v).toFixed(1)}%`

function ConcentrationCard({ c }: { c: Concentration }) {
  const isCustomer = c.side === 'customer'
  return (
    <Card>
      <CardHeader
        title={isCustomer ? 'Who your revenue depends on' : 'Who you buy stock from'}
        subtitle={`${isCustomer ? 'Revenue' : 'Stock purchases'} by ${c.side}, last 180 days`}
        info={`Concentration index (HHI) among named ${c.side}s: ${Math.round(c.hhi_identified).toLocaleString('en-GB')}. Above 2,500 is usually read as highly concentrated.`}
      />
      <CardBody className="space-y-5">
        <div>
          <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2 text-sm">
            <span className="text-ink-2">Top 3 {c.side}s</span>
            <span className="flex items-center gap-2">
              {c.top3_share_pct >= 60 && (
                <Badge tone="warn">
                  <AlertCircle aria-hidden /> Highly concentrated
                </Badge>
              )}
              <span className="text-lg font-semibold text-ink">{c.top3_share_pct.toFixed(0)}%</span>
            </span>
          </div>
          <Meter value={c.top3_share_pct} max={100} tone="brand" label={`Top 3 ${c.side}s account for ${c.top3_share_pct.toFixed(0)}%`} />
        </div>
        <HBarList
          rows={[
            ...c.top.map((t, i) => ({
              label: t.name,
              value: t.amount,
              highlight: i === 0,
              trailing: <span className="tnum text-xs text-ink-3">{t.share_pct.toFixed(0)}%</span>,
            })),
          ]}
          format={murCompact}
          color={isCustomer ? C.actual : C.expense}
        />
        {c.unidentified_amount > 1 && (
          <p className="text-xs text-ink-3">
            Plus {murCompact(c.unidentified_amount)} of {c.unidentified_label.toLowerCase()} not attributable to a named {c.side}.
          </p>
        )}
        {c.top[0] && (
          <TraceLink to={`/transactions?counterparty=${encodeURIComponent(c.top[0].name)}`}>Transactions with {c.top[0].name}</TraceLink>
        )}
      </CardBody>
    </Card>
  )
}

/**
 * The detailed cash forecast that the Overview links to: history and 90-day
 * projection against the buffer, the projection's key points, and the model's
 * 30-day cash-pressure estimate.
 */
function CashForecast() {
  const ov = useOverview()
  if (!ov.data || ov.data.monthly.length === 0) return null
  const d = ov.data
  const p = d.projection
  const below = p.first_date_below_buffer
  return (
    <>
      <Group
        id="cash"
        title="Cash forecast"
        insight={
          below
            ? `At current run-rates cash falls below the 14-day buffer on ${date(below)} and bottoms out at ${murCompact(p.lowest_cash)} on ${date(p.lowest_cash_date)}.`
            : `At current run-rates cash stays above the 14-day buffer; the low point is ${murCompact(p.lowest_cash)} on ${date(p.lowest_cash_date)}.`
        }
      />
      <div className="panel grid grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 p-5 lg:p-6">
          <CashChart actual={d.cash_series} projected={d.projection_series} buffer={p.buffer_threshold} height={300} />
          <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-line pt-4 text-sm sm:grid-cols-4">
            {[
              ['Cash in 30 days', murCompact(p.cash_day_30)],
              ['Cash in 60 days', murCompact(p.cash_day_60)],
              ['Cash in 90 days', murCompact(p.cash_day_90)],
              ['Days below buffer', `${p.days_below_buffer} of 90`],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-ink-3">{k}</dt>
                <dd className="tnum mt-0.5 font-semibold text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-ink-3">
            How it is built: recent sales and supplier run-rates, recurring payments on their usual dates, open and expected invoices at
            each customer's recent payment speed, and VAT due dates. It is a projection, not a recorded value.
          </p>
        </div>
        <div className="border-t border-line bg-surface p-5 lg:border-l lg:border-t-0 lg:p-6">
          <PredictionCard p={d.prediction} />
        </div>
      </div>
    </>
  )
}

export function InsightsPage() {
  const q = useInsights()
  const { hash } = useLocation()
  // Arriving from "View forecast detail": scroll to the section once the page has rendered.
  useEffect(() => {
    if (hash && q.data) document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' })
  }, [hash, q.data])
  if (q.isLoading) return <PageSkeleton />
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const d = q.data
  const cmp = d.comparison_90d
  const col = d.collections
  const months: MonthRow[] = d.monthly
  const full = months.filter((m) => !m.partial)
  const recurring: Recurring[] = d.recurring
  const recurringTotal = recurring.reduce((s, r) => s + r.monthly_run_rate, 0)
  const byCategory = Object.entries(
    recurring.reduce<Record<string, number>>((acc, r) => ({ ...acc, [r.category]: (acc[r.category] ?? 0) + r.monthly_run_rate }), {}),
  ).sort((a, b) => b[1] - a[1])
  const newOnes = recurring.filter((r) => r.is_new)
  const spark = (key: keyof MonthRow) => full.map((m) => m[key] as number)
  const topCost = d.expense_categories[0] as { category: string; share_pct: number } | undefined
  const bestLine = [...d.product_lines].sort(
    (a: { yoy_change_pct: number | null }, b: { yoy_change_pct: number | null }) => (b.yoy_change_pct ?? -999) - (a.yoy_change_pct ?? -999),
  )[0] as { line: string; yoy_change_pct: number | null } | undefined
  const cc = d.customer_concentration as Concentration
  const sc = d.supplier_concentration as Concentration

  return (
    <>
      <PageHeader
        title="Financial insights"
        meta={`Actual data to ${date(d.as_of)} · ${monthSpan(cmp.current_period)} vs ${monthSpan(cmp.previous_period)}`}
        description="What changed, where the money goes, and who the business depends on. Figures link to their transactions."
        actions={<DataKind kind="actual" />}
      />

      <nav
        aria-label="Sections"
        className="no-print mb-6 inline-flex max-w-full gap-1 overflow-x-auto rounded-md border border-line bg-surface p-1"
      >
        {SECTIONS.map(([id, label]) => (
          <a
            key={id}
            href={`#${id}`}
            className="shrink-0 whitespace-nowrap rounded px-3 py-1 text-sm font-medium text-ink-2 transition-colors hover:bg-mist hover:text-ink"
          >
            {label}
          </a>
        ))}
      </nav>

      <MetricStrip
        items={[
          {
            label: 'Revenue',
            value: murCompact(cmp.current.revenue),
            delta: <Delta value={cmp.change_pct.revenue} />,
            spark: spark('revenue'),
          },
          {
            label: 'Cost of goods',
            value: murCompact(cmp.current.cost_of_goods),
            delta: <Delta value={cmp.change_pct.cost_of_goods} goodWhen="down" />,
            spark: spark('cost_of_goods'),
            sparkColor: C.expense,
          },
          {
            label: 'Operating expenses',
            value: murCompact(cmp.current.operating_expenses),
            delta: <Delta value={cmp.change_pct.operating_expenses} goodWhen="down" />,
            spark: spark('operating_expenses'),
            sparkColor: C.expense,
          },
          {
            label: 'Gross margin',
            value: `${cmp.current.gross_margin_pct.toFixed(1)}%`,
            delta: <Delta value={cmp.change_pct.gross_margin_pct} suffix=" pp" />,
            spark: spark('gross_margin_pct'),
          },
          {
            label: 'Net cash flow',
            value: murCompact(cmp.current.net_cash_flow),
            delta: <Delta value={cmp.change_pct.net_cash_flow} />,
            note: (
              <span title="Operating cash flow excludes loans, owner drawings and injections">
                operating {murCompact(cmp.current.operating_cash_flow)}
              </span>
            ),
            spark: spark('net_cash_flow'),
          },
        ]}
      />

      <CashForecast />

      <Group
        id="trend"
        title="Trend"
        insight={
          <>
            Revenue {change(cmp.change_pct.revenue)} while cost of goods {change(cmp.change_pct.cost_of_goods)} - gross margin is{''}
            {cmp.current.gross_margin_pct.toFixed(1)}%.
          </>
        }
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Revenue vs expenses" subtitle="Monthly totals, last 12 months" />
          <CardBody>
            <MonthlyChart months={months} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Gross margin" subtitle="By complete month" info="Gross margin = (revenue - cost of goods) / revenue." />
          <CardBody>
            <div style={{ height: 262 }} role="img" aria-label="Gross margin by month">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={full} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis
                    dataKey="month"
                    tickFormatter={monthLabel}
                    tick={axisTick}
                    axisLine={{ stroke: C.axis }}
                    tickLine={false}
                    minTickGap={12}
                  />
                  <YAxis
                    tickFormatter={(v) => `${v}%`}
                    tick={axisTick}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    cursor={{ stroke: C.axis, strokeWidth: 1 }}
                    content={({ active, payload, label }) =>
                      active && payload?.length ? (
                        <ChartTooltipBox
                          title={monthLabel(String(label))}
                          format={(v) => `${v.toFixed(1)}%`}
                          rows={[{ name: 'gross margin', value: payload[0].value as number, color: C.actual }]}
                        />
                      ) : null
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="gross_margin_pct"
                    stroke={C.actual}
                    strokeWidth={2}
                    dot={{ r: 3, fill: C.actual, stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardBody>
        </Card>
      </div>

      <Group
        id="costs"
        title="Costs & sales"
        insight={
          <>
            {topCost ? `${topCost.category} takes ${topCost.share_pct.toFixed(0)}% of every rupee spent.` : 'Where the money goes.'}{''}
            {bestLine &&
              bestLine.yoy_change_pct !== null &&
              `${bestLine.line} is the fastest-growing line (+${bestLine.yoy_change_pct.toFixed(0)}% a year).`}
          </>
        }
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader
            title="Where the money goes"
            subtitle={`Outflows by category, ${monthSpan(cmp.current_period)} · change vs previous 3 months`}
          />
          <CardBody>
            <HBarList
              rows={d.expense_categories
                .slice(0, 9)
                .map((c: { category: string; amount: number; change_pct: number | null; share_pct: number }) => ({
                  label: c.category,
                  value: c.amount,
                  trailing: c.change_pct === null ? <Badge tone="warn">new</Badge> : <Delta value={c.change_pct} goodWhen="down" />,
                }))}
              format={murCompact}
              color={C.expense}
            />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Sales by product line" subtitle="Walk-in sales, last 90 days · change vs same period last year" />
          <CardBody className="space-y-5">
            <HBarList
              rows={d.product_lines.map((l: { line: string; revenue: number; yoy_change_pct: number | null; share_pct: number }) => ({
                label: l.line,
                value: l.revenue,
                trailing:
                  l.yoy_change_pct === null ? (
                    <span className="text-xs text-ink-3">no prior year</span>
                  ) : (
                    <Delta value={l.yoy_change_pct} />
                  ),
              }))}
              format={murCompact}
            />
            <TraceLink to="/transactions?category=Sales">See sales transactions</TraceLink>
          </CardBody>
        </Card>
      </div>

      <Group
        id="concentration"
        title="Dependence"
        insight={
          <>
            {sc.top[0] && `${sc.top[0].name} supplies ${sc.top[0].share_pct.toFixed(0)}% of your stock`}
            {sc.top[0] && cc.top[0] ? '; ' : ''}
            {cc.top[0] && `${cc.top[0].name} is your largest named customer (${cc.top[0].share_pct.toFixed(0)}% of revenue).`}
          </>
        }
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ConcentrationCard c={d.customer_concentration} />
        <ConcentrationCard c={d.supplier_concentration} />
      </div>

      <Group
        id="commitments"
        title="Commitments & collections"
        insight={
          <>
            {murCompact(recurringTotal)} leaves every month before a single sale
            {col.has_invoices && col.collection_days_recent != null
              ? `, and customers now take ${col.collection_days_recent.toFixed(0)} days to pay on ${col.standard_terms_days}-day terms.`
              : '.'}
          </>
        }
      />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader title="Recurring commitments" subtitle="Payments that repeat on a schedule, per month" />
          <CardBody className="space-y-5">
            <div className="flex flex-wrap items-end gap-x-8 gap-y-2">
              <div>
                <div className="text-xs text-ink-3">Committed every month</div>
                <div className="tnum text-2xl font-medium text-ink">{murCompact(recurringTotal)}</div>
              </div>
              <div className="text-sm text-ink-2">
                {recurring.length} payments
                {newOnes.length > 0 && (
                  <>
                    {' · '}
                    <span className="font-medium text-warn-ink">{newOnes.length} new this year</span>
                  </>
                )}
              </div>
            </div>
            <HBarList rows={byCategory.map(([label, value]) => ({ label, value }))} format={murCompact} color={C.expense} />
            {newOnes.length > 0 && (
              <ul className="space-y-1.5 rounded-lg border border-warn/40 bg-warn-bg/50 p-3 text-sm">
                {newOnes.map((r) => (
                  <li key={r.key} className="flex items-center gap-2">
                    <AlertCircle className="size-4 shrink-0 text-warn-ink" aria-hidden />
                    <span className="min-w-0 flex-1 truncate text-ink">
                      {r.name} <span className="text-ink-3">· since {date(r.first_seen)}</span>
                    </span>
                    <span className="tnum text-ink">{mur(r.monthly_run_rate)}/mo</span>
                  </li>
                ))}
              </ul>
            )}
            <details className="group rounded-lg border border-line">
              <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-medium text-ink-2 hover:bg-mist">
                All {recurring.length} recurring payments
                <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden />
              </summary>
              <div className="overflow-x-auto border-t border-line">
                <table className="w-full text-sm">
                  <thead className="bg-surface-2 text-left text-xs text-ink-3">
                    <tr>
                      <th className="px-4 py-2 font-medium">Payee</th>
                      <th className="px-3 py-2 font-medium">Category</th>
                      <th className="px-3 py-2 font-medium">Cadence</th>
                      <th className="px-4 py-2 text-right font-medium">Per month</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {recurring.map((r) => (
                      <tr key={r.key}>
                        <td className="px-4 py-2 text-ink">{r.name}</td>
                        <td className="px-3 py-2 text-ink-2">{r.category}</td>
                        <td className="px-3 py-2 capitalize text-ink-3">{r.cadence}</td>
                        <td className="tnum whitespace-nowrap px-4 py-2 text-right">{mur(r.monthly_run_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </CardBody>
        </Card>

        <Card id="collections" className="scroll-mt-20">
          <CardHeader title="How fast customers pay" subtitle="Business customers with invoices · amounts in MUR" />
          {col.has_invoices ? (
            <CardBody className="space-y-6">
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-surface-2 p-3">
                  <div className="flex items-center gap-1.5 text-xs text-ink-3">
                    <Clock className="hidden size-3.5 sm:block" aria-hidden /> Days to collect
                  </div>
                  <div className="mt-1 text-lg font-semibold text-ink">{col.collection_days_recent?.toFixed(0)}</div>
                  <div className="text-xs text-ink-3">
                    was {col.collection_days_prior?.toFixed(0)} · terms {col.standard_terms_days}
                  </div>
                </div>
                <div className="rounded-lg bg-surface-2 p-3">
                  <div className="flex items-center gap-1.5 text-xs text-ink-3">
                    <CalendarClock className="hidden size-3.5 sm:block" aria-hidden /> Open receivables
                  </div>
                  <div className="mt-1 text-lg font-semibold whitespace-nowrap text-ink">{axisMur(col.open_receivables)}</div>
                </div>
                <div className="rounded-lg bg-surface-2 p-3">
                  <div className="flex items-center gap-1.5 text-xs text-ink-3">
                    <AlertCircle className="hidden size-3.5 sm:block" aria-hidden /> Overdue
                  </div>
                  <div className="mt-1 text-lg font-semibold whitespace-nowrap text-bad-ink">
                    {axisMur(col.overdue_receivables)}
                  </div>
                </div>
              </div>
              <div>
                <h3 className="mb-2 text-xs font-medium text-ink-3">Receivables by age</h3>
                <CompositionBar
                  label="Open receivables by how overdue they are"
                  format={murCompact}
                  segments={[
                    { key: 'nd', label: 'Not due yet', value: col.aging.not_due, color: 'var(--color-actual)' },
                    { key: 'a', label: '1–30 days late', value: col.aging['1_30'], color: 'var(--color-warn)' },
                    { key: 'b', label: '31–60 days late', value: col.aging['31_60'], color: 'var(--color-serious)' },
                    { key: 'c', label: '60+ days late', value: col.aging.over_60, color: 'var(--color-bad)' },
                  ]}
                />
              </div>
              <div>
                <h3 className="mb-3 text-xs font-medium text-ink-3">Average days to pay, before → last 90 days</h3>
                <Dumbbell
                  unit="days"
                  reference={{ value: col.standard_terms_days, label: `${col.standard_terms_days}-day terms` }}
                  rows={col.by_customer.map(
                    (c: {
                      customer: string
                      avg_days_to_pay_prior: number | null
                      avg_days_to_pay_recent: number | null
                      overdue_amount: number
                    }) => ({
                      label: c.customer,
                      from: c.avg_days_to_pay_prior,
                      to: c.avg_days_to_pay_recent,
                      note: c.overdue_amount ? `${mur(c.overdue_amount)} overdue` : undefined,
                    }),
                  )}
                />
              </div>
            </CardBody>
          ) : (
            <CardBody className="text-sm text-ink-3">No invoices recorded for this business.</CardBody>
          )}
        </Card>
      </div>
    </>
  )
}
