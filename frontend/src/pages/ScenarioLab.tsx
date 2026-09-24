import { ChevronDown, FlaskConical, RotateCcw, Save } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { ScenarioChart } from '@/charts/ScenarioChart'
import { DataKind } from '@/components/domain/labels'
import { PageHeader } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { InsightStrip } from '@/components/ui/insight-strip'
import { Slider } from '@/components/ui/slider'
import { ErrorState, Skeleton } from '@/components/ui/states'
import { BeforeAfter } from '@/components/viz/BeforeAfter'
import { DivergingBars } from '@/components/viz/DivergingBars'
import { useDebounced } from '@/hooks/useDebounced'
import { useLevers, useOpportunity, useSavedScenarios, useSaveScenario, useSimulate } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { date, dateTime, mur, murCompact } from '@/lib/format'
import type { Assumptions } from '@/lib/types'

const ZERO: Assumptions = {
  supplier_cost_pct: 0,
  price_pct: 0,
  sales_volume_pct: 0,
  recurring_expense_pct: 0,
  collection_days_change: 0,
  marketing_spend_pct: 0,
  staffing_cost_pct: 0,
  inventory_spend_pct: 0,
}

const PRESETS: { name: string; a: Partial<Assumptions> }[] = [
  { name: 'Supplier prices -10%', a: { supplier_cost_pct: -10 } },
  { name: 'Collect 10 days faster', a: { collection_days_change: -10 } },
  { name: 'Recurring costs -10%', a: { recurring_expense_pct: -10 } },
  { name: 'Combined plan', a: { supplier_cost_pct: -8, collection_days_change: -10, recurring_expense_pct: -5 } },
  { name: 'Stress: sales -15%', a: { sales_volume_pct: -15 } },
]

const DRIVER_LABEL: Record<string, string> = {
  sales_walk_in: 'Walk-in / POS sales',
  collections: 'Invoice collections',
  suppliers: 'Supplier purchases',
  recurring: 'Recurring costs',
  payroll: 'Payroll',
  marketing: 'Marketing',
  variable: 'Other variable costs',
  vat: 'VAT payments',
}

function parsePreset(raw: string | null): Assumptions {
  if (!raw) return ZERO
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>
    const out = { ...ZERO }
    for (const k of Object.keys(ZERO) as (keyof Assumptions)[]) if (typeof obj[k] === 'number') out[k] = obj[k] as number
    return out
  } catch {
    return ZERO
  }
}

const INFLOW_DRIVERS = new Set(['sales_walk_in', 'collections'])

function Figure({
  label,
  base,
  scen,
  kind = 'mur',
  goodWhen = 'up',
}: {
  label: string
  base: number
  scen: number
  kind?: 'mur' | 'days'
  goodWhen?: 'up' | 'down'
}) {
  const diff = scen - base
  const good = diff === 0 ? null : goodWhen === 'up' ? diff > 0 : diff < 0
  const f = (v: number) => (kind === 'mur' ? murCompact(v) : `${v} days`)
  return (
    <div className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-line bg-surface p-4">
      <div className="text-xs font-medium text-ink-3">{label}</div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-xl font-semibold text-ink" title={kind === 'mur' ? mur(scen) : undefined}>
          {f(scen)}
        </span>
        <span
          className={cn(
            'tnum rounded-md px-1.5 py-0.5 text-xs font-semibold',
            good === null ? 'bg-surface-2 text-ink-3' : good ? 'bg-good-bg text-good-ink' : 'bg-bad-bg text-bad-ink',
          )}
        >
          {diff === 0 ? 'No difference' : kind === 'mur' ? murCompact(diff, true) : `${diff > 0 ? '+' : '−'}${Math.abs(diff)} days`}
        </span>
      </div>
      <BeforeAfter
        before={base}
        after={scen}
        format={f}
        beforeLabel="No change"
        afterLabel="Simulated"
        afterColor="var(--color-simulated)"
      />
    </div>
  )
}

export function ScenarioLabPage() {
  const [params] = useSearchParams()
  const oppId = params.get('opp')
  const opp = useOpportunity(oppId)
  const [a, setA] = useState<Assumptions>(() => parsePreset(params.get('preset')))
  const debounced = useDebounced(a, 250)
  const levers = useLevers()
  const sim = useSimulate(debounced)
  const saved = useSavedScenarios()
  const save = useSaveScenario()
  const { can } = useAuth()
  const [name, setName] = useState('')
  const changed = useMemo(() => Object.entries(a).filter(([, v]) => v !== 0), [a])
  const r = sim.data

  return (
    <>
      <PageHeader
        title="Scenario Lab"
        description="Try a decision before you make it: see its effect on the next 90 days of cash. Your actual transactions are never modified."
        actions={<DataKind kind="simulated" />}
      />
      {oppId && opp.data && (
        <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-serious/30 bg-serious-bg/40 px-4 py-3 text-sm">
          <FlaskConical className="size-4 text-serious-ink" aria-hidden />
          Simulating an action for: <strong className="text-ink">{opp.data.title}</strong>
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_1fr]">
        <Card className="h-fit">
          <CardHeader
            title="Assumptions"
            subtitle="Relative to current run-rates"
            action={
              <Button variant="ghost" size="sm" onClick={() => setA(ZERO)} disabled={!changed.length}>
                <RotateCcw /> Reset
              </Button>
            }
          />
          <CardBody className="space-y-5">
            <div className="flex flex-wrap gap-1.5">
              {PRESETS.map((p) => (
                <button
                  key={p.name}
                  type="button"
                  aria-pressed={Object.entries({ ...ZERO, ...p.a }).every(([k, v]) => a[k as keyof Assumptions] === v)}
                  onClick={() => setA({ ...ZERO, ...p.a })}
                  className="rounded border border-line px-2 py-1 text-xs text-ink-2 transition-colors hover:border-serious hover:bg-serious-bg/40 aria-pressed:border-serious aria-pressed:bg-serious-bg aria-pressed:font-medium aria-pressed:text-serious-ink"
                >
                  {p.name}
                </button>
              ))}
            </div>
            {levers.data?.map((l) => (
              <div key={l.key}>
                <div className="mb-2 flex items-center justify-between gap-2 text-sm">
                  <label className="text-ink-2" htmlFor={`lever-${l.key}`}>
                    {l.label}
                  </label>
                  <span
                    className={cn(
                      'tnum rounded px-1.5 text-sm font-medium',
                      a[l.key] !== 0 ? 'bg-serious-bg text-serious-ink' : 'text-ink-3',
                    )}
                  >
                    {a[l.key] > 0 ? '+' : ''}
                    {a[l.key]}
                    {l.unit === '%' ? '%' : ' days'}
                  </span>
                </div>
                <Slider
                  label={l.label}
                  value={a[l.key]}
                  min={l.min}
                  max={l.max}
                  step={l.step}
                  onChange={(v) => setA((s) => ({ ...s, [l.key]: v }))}
                />
              </div>
            ))}
            {!levers.data && <Skeleton className="h-64" />}
          </CardBody>
        </Card>

        <div className="space-y-4">
          {sim.error && <ErrorState error={sim.error} onRetry={() => sim.refetch()} />}
          {!r && !sim.error && <Skeleton className="h-96" />}
          {r && (
            <>
              <div className={cn('grid grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-4', sim.isFetching && 'opacity-60')}>
                <Figure label="Cash in 30 days" base={r.baseline.cash_day_30} scen={r.scenario.cash_day_30} />
                <Figure label="Cash in 90 days" base={r.baseline.cash_day_90} scen={r.scenario.cash_day_90} />
                <Figure label="Lowest cash (90 days)" base={r.baseline.lowest_cash} scen={r.scenario.lowest_cash} />
                <Figure
                  label="Days below 14-day buffer"
                  base={r.baseline.days_below_buffer}
                  scen={r.scenario.days_below_buffer}
                  kind="days"
                  goodWhen="down"
                />
              </div>
              <Card>
                <CardHeader
                  title="Projected cash: no change vs your scenario"
                  subtitle={`Starting from actual cash of ${mur(r.baseline.starting_cash)} on ${date(r.as_of)}`}
                  action={
                    <>
                      <DataKind kind="projected" />
                      <DataKind kind="simulated" />
                    </>
                  }
                />
                <CardBody className={cn(sim.isFetching && 'opacity-60')}>
                  <ScenarioChart series={r.series} buffer={r.baseline.buffer_threshold} />
                  {changed.length === 0 ? (
                    <InsightStrip>
                      Pick a preset or move a slider on the left to see how a decision would change the next 90 days. Nothing you try here
                      is saved to your records.
                    </InsightStrip>
                  ) : (
                    <InsightStrip tone={r.scenario.cash_day_90 >= r.baseline.cash_day_90 ? 'good' : 'attention'}>
                      With these assumptions, cash in 90 days would be{''}
                      <strong className="font-semibold">{murCompact(r.scenario.cash_day_90)}</strong> instead of{''}
                      {murCompact(r.baseline.cash_day_90)} ({murCompact(r.scenario.cash_day_90 - r.baseline.cash_day_90, true)}), with{''}
                      {r.scenario.days_below_buffer} of 90 days under the buffer instead of {r.baseline.days_below_buffer}. This is a
                      simulation, not a forecast.
                    </InsightStrip>
                  )}
                </CardBody>
              </Card>
              <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
                <Card>
                  <CardHeader
                    title="What moves the 90-day cash"
                    subtitle="Effect of each driver on cash, vs no change"
                    info="Money in (sales, collections) counts as it is; money out counts in reverse, so paying suppliers less shows as a positive effect on cash."
                  />
                  <CardBody className="space-y-4">
                    <DivergingBars
                      rows={r.breakdown.map((b) => ({
                        label: DRIVER_LABEL[b.driver] ?? b.driver,
                        value: INFLOW_DRIVERS.has(b.driver) ? b.difference : -b.difference,
                      }))}
                      format={(v) => murCompact(v, true)}
                    />
                    <details className="group rounded-lg border border-line">
                      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-medium text-ink-2 hover:bg-mist">
                        90-day totals by driver
                        <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden />
                      </summary>
                      <div className="overflow-x-auto border-t border-line">
                        <table className="w-full text-sm">
                          <thead className="bg-surface-2 text-left text-xs text-ink-3">
                            <tr>
                              <th className="px-4 py-2 font-medium">Driver</th>
                              <th className="px-3 py-2 text-right font-medium">No change</th>
                              <th className="px-3 py-2 text-right font-medium">Simulated</th>
                              <th className="px-4 py-2 text-right font-medium">Difference</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-line">
                            {r.breakdown.map((b) => (
                              <tr key={b.driver}>
                                <td className="px-4 py-2 text-ink-2">{DRIVER_LABEL[b.driver] ?? b.driver}</td>
                                <td className="tnum px-3 py-2 text-right">{mur(b.baseline)}</td>
                                <td className="tnum px-3 py-2 text-right">{mur(b.scenario)}</td>
                                <td className="tnum px-4 py-2 text-right font-medium">
                                  {b.difference === 0 ? '—' : mur(b.difference, { signed: true })}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </details>
                  </CardBody>
                </Card>
                <Card>
                  <CardHeader title="Assumptions used" subtitle="Shown with every result" />
                  <CardBody className="space-y-3 text-sm">
                    {changed.length ? (
                      <ul className="flex flex-wrap gap-1.5">
                        {changed.map(([k, v]) => (
                          <Badge key={k} tone="simulated">
                            {levers.data?.find((l) => l.key === k)?.label}: {v > 0 ? '+' : ''}
                            {v}
                            {k === 'collection_days_change' ? ' days' : '%'}
                          </Badge>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-ink-3">No changes - this is the baseline projection.</p>
                    )}
                    <details className="group">
                      <summary className="flex cursor-pointer list-none items-center gap-1 text-xs font-medium text-accent-600">
                        How the projection works
                        <ChevronDown className="size-3.5 transition-transform group-open:rotate-180" aria-hidden />
                      </summary>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-ink-3">
                        {r.method_notes.map((n) => (
                          <li key={n}>{n}</li>
                        ))}
                        <li>Selling-price changes assume sales volume stays the same unless you also change volume.</li>
                        {r.backtest_median_error_pct !== null && (
                          <li>
                            Back-test: 30-day projections from past dates missed actual cash by a median of{''}
                            {r.backtest_median_error_pct.toFixed(1)}% of monthly outflows.
                          </li>
                        )}
                      </ul>
                    </details>
                    {can('save_scenarios') && (
                      <form
                        className="flex gap-2 pt-2"
                        onSubmit={(e) => {
                          e.preventDefault()
                          save.mutate(
                            { name: name || `Scenario ${new Date().toLocaleDateString('en-GB')}`, assumptions: a, opportunity_id: oppId },
                            { onSuccess: () => setName('') },
                          )
                        }}
                      >
                        <input
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          maxLength={120}
                          placeholder="Scenario name"
                          aria-label="Scenario name"
                          className="h-9 min-w-0 flex-1 rounded-lg border border-line-strong px-3 text-sm outline-none focus:border-accent-600"
                        />
                        <Button type="submit" variant="secondary" disabled={save.isPending || !changed.length}>
                          <Save /> Save
                        </Button>
                      </form>
                    )}
                  </CardBody>
                </Card>
              </div>
            </>
          )}
          <Card>
            <CardHeader title="Saved scenarios" subtitle="Kept separately from actual records" />
            <ul className="divide-y divide-line">
              {saved.data?.length === 0 && <li className="px-5 py-4 text-sm text-ink-3">No saved scenarios yet.</li>}
              {saved.data?.map((s) => (
                <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
                  <div>
                    <div className="font-medium text-ink">{s.name}</div>
                    <div className="text-xs text-ink-3">
                      {s.created_by} · {dateTime(s.created_at)} · data to {date(s.data_as_of)}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="tnum text-ink-2">90-day cash {mur(s.result_summary.difference.cash_day_90, { signed: true })}</span>
                    <Button size="sm" variant="ghost" onClick={() => setA({ ...ZERO, ...s.assumptions })}>
                      Load
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
