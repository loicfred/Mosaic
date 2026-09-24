import { Printer } from 'lucide-react'
import { BandBadge, Delta, OutcomeBadge, SeverityBadge, StatusBadge } from '@/components/domain/labels'
import { IMPACT_LABEL } from '@/components/domain/meta'
import { PageHeader } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardBody } from '@/components/ui/card'
import { ErrorState, PageSkeleton } from '@/components/ui/states'
import { BandScale } from '@/components/viz/BandScale'
import { Meter } from '@/components/viz/Meter'
import { useBrief } from '@/hooks/queries'
import { date, murCompact, percent01 } from '@/lib/format'
import type { Opportunity, Outcome } from '@/lib/types'

export function ReportsPage() {
  const q = useBrief()
  if (q.isLoading) return <PageSkeleton />
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const b = q.data
  const k = b.kpis_90d
  return (
    <>
      <PageHeader
        title="Reports"
        description="A one-page decision brief for the owner, accountant or bank: position, risk, opportunities and tracked actions."
        actions={
          <Button variant="secondary" onClick={() => window.print()}>
            <Printer /> Print or save as PDF
          </Button>
        }
      />
      <Card className="mx-auto max-w-4xl">
        <CardBody className="space-y-8 p-8">
          <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-6">
            <div>
              <div className="text-xs text-ink-3">Decision brief</div>
              <h2 className="mt-1 text-2xl font-semibold">{b.business.name}</h2>
              <p className="text-sm text-ink-3">
                {b.business.sector} · data to {date(b.as_of)} · amounts in {b.business.currency}
              </p>
            </div>
            <div className="text-right text-xs text-ink-3">
              Prepared by {b.generated_by}
              {b.business.data_label === 'synthetic_demo' && (
                <div className="mt-1 font-medium text-warn-ink">Synthetic demo data - not a real business</div>
              )}
            </div>
          </header>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-ink">1. Position (actual, last 3 complete months)</h3>
            <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div className="rounded-lg bg-surface-2 p-3">
                <div className="text-ink-3">Cash today</div>
                <div className="tnum text-lg font-semibold">{murCompact(b.cash.balance)}</div>
                <Meter
                  className="mt-2"
                  value={b.cash.buffer_days}
                  max={Math.max(30, b.cash.buffer_days * 1.25)}
                  size="sm"
                  tone={b.cash.buffer_days < 14 ? 'bad' : b.cash.buffer_days < 21 ? 'warn' : 'good'}
                  marker={{ value: 14 }}
                  label={`${b.cash.buffer_days.toFixed(0)} days of outflows, buffer 14 days`}
                />
                <div className="mt-1 text-xs text-ink-3">{b.cash.buffer_days.toFixed(0)} days of outflows (buffer 14)</div>
              </div>
              <div className="rounded-lg bg-surface-2 p-3">
                <div className="text-ink-3">Revenue</div>
                <div className="tnum text-lg font-semibold">{murCompact(k.revenue)}</div>
                <Delta value={k.revenue_change_pct} unit="vs prior 3 months" />
              </div>
              <div className="rounded-lg bg-surface-2 p-3">
                <div className="text-ink-3">Expenses</div>
                <div className="tnum text-lg font-semibold">{murCompact(k.expenses)}</div>
                <Delta value={k.expenses_change_pct} goodWhen="down" unit="vs prior 3 months" />
              </div>
              <div className="rounded-lg bg-surface-2 p-3">
                <div className="text-ink-3">Gross margin</div>
                <div className="tnum text-lg font-semibold">{k.gross_margin_pct.toFixed(1)}%</div>
                <Delta value={k.gross_margin_change_pp} suffix=" pp" />
              </div>
            </div>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-ink">2. Outlook</h3>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  {b.prediction.probability !== null && (
                    <span className="text-3xl font-semibold">{percent01(b.prediction.probability)}</span>
                  )}
                  <BandBadge band={b.prediction.band} />
                </div>
                {b.prediction.probability !== null && b.prediction.thresholds && (
                  <BandScale
                    probability={b.prediction.probability}
                    moderate={b.prediction.thresholds.moderate_threshold}
                    high={b.prediction.thresholds.high_threshold}
                  />
                )}
                <p className="text-sm text-ink-2">Predicted probability that cash falls below 14 days of outflows within 30 days.</p>
              </div>
              {b.projection?.lowest_cash !== undefined && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-lg bg-surface-2 p-3">
                    <div className="text-xs text-ink-3">Lowest projected cash</div>
                    <div className="tnum font-semibold">{murCompact(b.projection.lowest_cash)}</div>
                    <div className="text-xs text-ink-3">on {date(b.projection.lowest_cash_date)}</div>
                  </div>
                  <div className="rounded-lg bg-surface-2 p-3">
                    <div className="text-xs text-ink-3">Days below buffer</div>
                    <div className="tnum font-semibold">{b.projection.days_below_buffer} of 90</div>
                    <div className="text-xs text-ink-3">buffer {murCompact(b.projection.buffer_threshold)}</div>
                  </div>
                  <p className="col-span-2 text-xs text-ink-3">Projected at current run-rates; not a recorded value.</p>
                </div>
              )}
            </div>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-ink">3. Opportunities and risks to decide on</h3>
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-ink-3">
                <tr>
                  <th className="py-2">Finding</th>
                  <th className="py-2">Impact</th>
                  <th className="py-2 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {b.open_opportunities.map((o: Opportunity & { top_action: string }) => (
                  <tr key={o.title} className="align-top">
                    <td className="py-2.5 pr-3">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={o.severity} />
                        <span className="font-medium">{o.title}</span>
                      </div>
                      <div className="mt-1 text-xs text-ink-3">Next step: {o.top_action}</div>
                    </td>
                    <td className="tnum py-2.5 pr-3">
                      {o.impact_high !== null ? `${murCompact(o.impact_low)} – ${murCompact(o.impact_high).replace('MUR ', '')}` : '—'}
                      <div className="text-xs text-ink-3">{IMPACT_LABEL[o.impact_kind]}</div>
                    </td>
                    <td className="py-2.5 text-right">
                      <span className="inline-flex items-center gap-2">
                        <Meter
                          value={o.confidence}
                          max={1}
                          size="sm"
                          className="hidden w-12 sm:block"
                          label={`Confidence ${percent01(o.confidence)}`}
                        />
                        <span className="tnum">{percent01(o.confidence)}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-ink">4. Actions and measured outcomes</h3>
            <ul className="space-y-2 text-sm">
              {b.tracked_actions.length === 0 && <li className="text-ink-3">No actions started yet.</li>}
              {b.tracked_actions.map(
                (t: { title: string; status: Opportunity['status']; action_started_at: string | null; outcome: Outcome | null }) => (
                  <li key={t.title} className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{t.title}</span>
                    <StatusBadge status={t.status} />
                    {t.outcome && <OutcomeBadge outcome={t.outcome} />}
                    {t.action_started_at && <span className="text-xs text-ink-3">started {date(t.action_started_at)}</span>}
                  </li>
                ),
              )}
            </ul>
          </section>
          <footer className="border-t border-line pt-4 text-xs text-ink-3">
            Figures are calculated by the Valora deterministic engine from recorded transactions. Predictions come from a locally trained
            model and are labelled as such. Impact ranges are estimates with stated assumptions, not guarantees.
          </footer>
        </CardBody>
      </Card>
    </>
  )
}
