import { Check, ExternalLink, FlaskConical, MessageSquarePlus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet } from '@/components/ui/sheet'
import { ErrorState, Skeleton } from '@/components/ui/states'
import { useAddNote, useChangeStatus, useLookup, useOpportunity } from '@/hooks/queries'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { BeforeAfter } from '@/components/viz/BeforeAfter'
import { Meter } from '@/components/viz/Meter'
import { Timeline } from '@/components/viz/Timeline'
import { date, dateTime, metric, mur, num } from '@/lib/format'
import type { Opportunity, OppStatus, Outcome } from '@/lib/types'
import { ConfidenceMeter, OutcomeBadge, SeverityBadge, StatusBadge } from './labels'
import { IMPACT_LABEL, STATUS_META } from './meta'

const FLOW: OppStatus[] = ['new', 'reviewed', 'planned', 'in_progress', 'completed']
const NEXT: Record<OppStatus, OppStatus[]> = {
  new: ['reviewed', 'planned', 'in_progress', 'dismissed'],
  reviewed: ['planned', 'in_progress', 'dismissed'],
  planned: ['in_progress', 'reviewed', 'dismissed'],
  in_progress: ['completed', 'planned', 'dismissed'],
  completed: ['in_progress'],
  dismissed: ['new'],
}
const ACTION_LABEL: Record<OppStatus, string> = {
  new: 'Restore',
  reviewed: 'Mark reviewed',
  planned: 'Plan action',
  in_progress: 'Start action',
  completed: 'Mark completed',
  dismissed: 'Dismiss',
}

function Section({ step, title, children }: { step: string; title: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-line px-6 py-5">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
        <span className="rounded bg-brand-50 px-1.5 py-0.5 text-brand-800">{step}</span>
        {title}
      </h3>
      {children}
    </section>
  )
}

const fmtMetric = metric

/** The four parts of the evidence score, each as its own small meter. */
function ConfidenceBreakdown({ basis }: { basis: Record<string, unknown> }) {
  const parts = [
    { k: 'strength', label: 'Effect size', w: 0.5 },
    { k: 'coverage', label: 'Months of history', w: 0.2 },
    { k: 'data_quality', label: 'Data health', w: 0.2 },
    { k: 'consistency', label: 'Month-to-month consistency', w: 0.1 },
  ].filter((x) => typeof basis[x.k] === 'number')
  if (!parts.length) return null
  return (
    <ul className="mt-4 grid grid-cols-1 gap-x-6 gap-y-2.5 sm:grid-cols-2">
      {parts.map((x) => {
        const v = basis[x.k] as number
        return (
          <li key={x.k} className="text-xs">
            <div className="mb-1 flex justify-between gap-2">
              <span className="text-ink-2">
                {x.label} <span className="text-ink-3">· weight {Math.round(x.w * 100)}%</span>
              </span>
              <span className="tnum font-medium text-ink">{Math.round(v * 100)}%</span>
            </div>
            <Meter value={v} max={1} tone="brand" size="sm" label={`${x.label} ${Math.round(v * 100)}%`} />
          </li>
        )
      })}
    </ul>
  )
}

export function OutcomePanel({ outcome, o }: { outcome: Outcome | null; o: Opportunity }) {
  if (!o.target) return <p className="text-sm text-ink-3">This finding is closed by confirming the review; there is no metric to track.</p>
  if (!outcome || outcome.status === 'not_started')
    return (
      <p className="text-sm text-ink-2">
        When the action starts, Valora will re-measure <strong>{o.target.label}</strong> (now {fmtMetric(o.baseline_value, o.target.unit)})
        on data recorded after the start date and compare it with the expected change of {fmtMetric(o.expected_change, o.target.unit)}.
      </p>
    )
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <OutcomeBadge outcome={outcome} />
        <span className="text-sm text-ink-2">{outcome.message}</span>
      </div>
      {outcome.baseline !== undefined && outcome.current !== undefined && (
        <div className="space-y-3 rounded-lg bg-surface-2 p-4 text-sm">
          <BeforeAfter
            before={outcome.baseline}
            after={outcome.current}
            format={(v) => fmtMetric(v, outcome.unit)}
            beforeLabel="Before (baseline)"
            afterLabel="After action"
            afterColor={outcome.status === 'achieved' ? 'var(--color-good)' : 'var(--color-actual)'}
          />
          <div className="flex flex-wrap justify-between gap-2 border-t border-line pt-2 text-xs">
            <span className="text-ink-3">Change vs expected</span>
            <span className="tnum font-semibold text-ink">
              {fmtMetric(outcome.change, outcome.unit)}{''}
              <span className="font-normal text-ink-3">/ {fmtMetric(outcome.expected_change, outcome.unit)}</span>
            </span>
          </div>
          <div className="text-xs text-ink-3">
            {outcome.metric_label}. Measured on actual data{''}
            {outcome.window ? `${date(outcome.window[0])} – ${date(outcome.window[1])}` : ''} ({outcome.days_observed} days since the action
            started).
          </div>
        </div>
      )}
      {outcome.status === 'too_early' && <p className="text-sm text-ink-3">{outcome.message}</p>}
      {outcome.caveat && <p className="text-xs text-ink-3">{outcome.caveat}</p>}
    </div>
  )
}

function Records({ ids }: { ids: string[] }) {
  const q = useLookup(ids)
  if (!ids.length) return null
  if (q.isLoading) return <Skeleton className="h-24" />
  const rows = q.data ?? []
  return (
    <div className="mt-4 overflow-hidden rounded-lg border border-line">
      <table className="w-full text-sm">
        <caption className="bg-surface-2 px-3 py-2 text-left text-xs font-medium text-ink-3">
          Supporting transactions ({rows.length})
        </caption>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 8).map((t) => (
            <tr key={t.id}>
              <td className="whitespace-nowrap px-3 py-2 text-ink-3">{date(t.date)}</td>
              <td className="px-3 py-2 text-ink">{t.counterparty ?? t.description}</td>
              <td className="tnum px-3 py-2 text-right text-ink">{mur(t.direction === 'outflow' ? -t.amount : t.amount)}</td>
              <td className="px-3 py-2 text-right">
                <Link to={`/transactions?open=${t.id}`} className="text-accent-600 hover:underline" aria-label="Open transaction">
                  <ExternalLink className="inline size-3.5" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function OpportunityDetail({ id, onClose }: { id: string | null; onClose: () => void }) {
  const q = useOpportunity(id)
  const { can } = useAuth()
  const change = useChangeStatus()
  const addNote = useAddNote()
  const [note, setNote] = useState('')
  const o = q.data
  const prov = (o?.provenance ?? {}) as Record<string, unknown>
  const recIds = [...(((o?.supporting_records as Record<string, unknown>)?.transaction_ids as string[]) ?? [])]
  const evIds = o?.evidence.flatMap((e) => e.transaction_ids ?? []) ?? []
  const allIds = Array.from(new Set([...evIds, ...recIds]))

  return (
    <Sheet open={!!id} onOpenChange={(v) => !v && onClose()} wide title={o?.title ?? 'Opportunity'} description={o ? o.summary : undefined}>
      {q.isLoading && (
        <div className="space-y-3 p-6">
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-40" />
        </div>
      )}
      {q.error && (
        <div className="p-6">
          <ErrorState error={q.error} />
        </div>
      )}
      {o && (
        <div>
          <div className="flex flex-wrap items-center gap-2 border-b border-line px-6 py-3">
            <SeverityBadge severity={o.severity} />
            <Badge tone={o.kind === 'risk' ? 'serious' : 'accent'}>{o.kind === 'risk' ? 'Risk' : 'Opportunity'}</Badge>
            <StatusBadge status={o.status} />
            {!o.is_active && <Badge>No longer detected in latest data</Badge>}
            <span className="ml-auto text-xs text-ink-3">
              Detected {dateTime(o.detected_at)} · data to {date(o.data_as_of)}
            </span>
          </div>

          <Section step="1" title="What was found">
            <p className="text-sm leading-relaxed text-ink">{o.explanation}</p>
            <p className="mt-3 text-sm text-ink-3">
              <strong className="text-ink-2">Why it matters: </strong>
              {o.why_it_matters}
            </p>
          </Section>

          <Section step="2" title="Evidence - why this was flagged">
            <dl className="divide-y divide-line rounded-lg border border-line">
              {o.evidence.map((e, i) => (
                <div key={i} className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-0.5 px-4 py-2.5 text-sm">
                  <dt className="text-ink-2">{e.label}</dt>
                  <dd className="tnum text-right font-medium text-ink">{e.display}</dd>
                  {(e.detail || e.period || e.source) && (
                    <dd className="col-span-2 text-xs text-ink-3">
                      {[e.detail, e.period && `${e.period}${e.compared_to ? ` vs ${e.compared_to}` : ''}`, e.source]
                        .filter(Boolean)
                        .join(' · ')}
                    </dd>
                  )}
                </div>
              ))}
            </dl>
            <p className="mt-3 text-xs text-ink-3">
              Data period{''}
              {Array.isArray(prov.data_window) ? `${date(String(prov.data_window[0]))} – ${date(String(prov.data_window[1]))}` : ''} ·{''}
              {num(prov.transactions_analysed as number)} transactions · {num(prov.invoices_analysed as number)} invoices analysed
            </p>
            <Records ids={allIds} />
          </Section>

          <Section step="3" title="How confident">
            <ConfidenceMeter value={o.confidence} basis={o.confidence_basis} />
            <p className="mt-2 text-xs text-ink-3">
              {o.confidence_basis.method === 'model_probability'
                ? String(o.confidence_basis.note)
                : 'Evidence score from effect size, months of history, data health and month-to-month consistency, capped at 95%.'}
            </p>
            {o.confidence_basis.method !== 'model_probability' && <ConfidenceBreakdown basis={o.confidence_basis} />}
          </Section>

          <Section step="4" title="Financial impact">
            {o.impact_high !== null ? (
              <>
                <div className="text-xs text-ink-3">{IMPACT_LABEL[o.impact_kind]}</div>
                <div className="tnum text-2xl font-semibold text-ink">
                  {mur(o.impact_low)} – {mur(o.impact_high).replace('MUR ', '')}
                </div>
                <p className="mt-1 text-sm text-ink-3">{o.impact_basis}</p>
              </>
            ) : (
              <p className="text-sm text-ink-3">Not quantified.</p>
            )}
          </Section>

          <Section step="5" title="What you can do">
            <ul className="space-y-2">
              {o.actions.map((a, i) => (
                <li key={i} className="flex gap-3 rounded-lg border border-line p-3">
                  <Check className="mt-0.5 size-4 shrink-0 text-accent-600" aria-hidden />
                  <div>
                    <div className="text-sm font-medium text-ink">{a.title}</div>
                    {a.detail && <div className="text-sm text-ink-3">{a.detail}</div>}
                  </div>
                  <Badge className="ml-auto h-fit capitalize">{a.effort} effort</Badge>
                </li>
              ))}
            </ul>
          </Section>

          {o.scenario_preset && (
            <Section step="6" title="What happens if you do it">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-serious-bg/50 p-4">
                <p className="text-sm text-ink-2">
                  Simulate <strong className="text-ink">{o.scenario_preset.name}</strong> on a copy of your projection. Your records are not
                  changed.
                </p>
                <Button variant="secondary" asChild>
                  <Link to={`/scenarios?opp=${o.id}&preset=${encodeURIComponent(JSON.stringify(o.scenario_preset.assumptions))}`}>
                    <FlaskConical /> Simulate
                  </Link>
                </Button>
              </div>
            </Section>
          )}

          <Section step="7" title="Track the action">
            <ol className="flex flex-wrap items-center gap-1 text-xs" aria-label="Progress">
              {FLOW.map((s, i) => {
                const reached = FLOW.indexOf(o.status) >= i && o.status !== 'dismissed'
                const Icon = STATUS_META[s].icon
                return (
                  <li key={s} className="flex items-center gap-1">
                    <span
                      className={cn(
                        'flex items-center gap-1 rounded-full px-2.5 py-1',
                        reached ? 'bg-accent-50 font-medium text-accent-600' : 'bg-surface-2 text-ink-3',
                      )}
                    >
                      <Icon className="size-3.5" aria-hidden /> {STATUS_META[s].label}
                    </span>
                    {i < FLOW.length - 1 && <span className="text-line-strong">—</span>}
                  </li>
                )
              })}
            </ol>
            {can('manage_opportunities') ? (
              <div className="mt-4 space-y-3">
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  maxLength={1000}
                  rows={2}
                  placeholder="Optional note (who, what, by when)"
                  className="w-full rounded-lg border border-line-strong p-2.5 text-sm outline-none focus:border-accent-600 focus:ring-2 focus:ring-accent-100"
                  aria-label="Note"
                />
                <div className="flex flex-wrap gap-2">
                  {NEXT[o.status].map((s) => (
                    <Button
                      key={s}
                      size="sm"
                      variant={s === 'dismissed' ? 'danger' : s === NEXT[o.status][0] ? 'accent' : 'secondary'}
                      disabled={change.isPending}
                      onClick={() => change.mutate({ id: o.id, status: s, note }, { onSuccess: () => setNote('') })}
                    >
                      {ACTION_LABEL[s]}
                    </Button>
                  ))}
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={!note.trim() || addNote.isPending}
                    onClick={() => addNote.mutate({ id: o.id, note }, { onSuccess: () => setNote('') })}
                  >
                    <MessageSquarePlus /> Add note
                  </Button>
                </div>
                {change.error && <p className="text-sm text-bad-ink">{(change.error as ApiError).message}</p>}
              </div>
            ) : (
              <p className="mt-3 text-sm text-ink-3">Your role can view but not change action status.</p>
            )}
            {o.events && o.events.length > 0 && (
              <Timeline
                className="mt-5"
                items={o.events.map((e) => ({
                  id: e.id,
                  title:
                    e.type === 'detected'
                      ? 'Detected by the engine'
                      : e.type === 'note'
                        ? 'Note added'
                        : `${STATUS_META[e.from as OppStatus]?.label ?? e.from} → ${STATUS_META[e.to as OppStatus]?.label ?? e.to}`,
                  meta: `${e.by ?? 'System'} · ${dateTime(e.at)}`,
                  note: e.note,
                  tone: e.to === 'completed' ? 'good' : e.to === 'dismissed' ? 'neutral' : e.type === 'detected' ? 'accent' : 'neutral',
                }))}
              />
            )}
          </Section>

          <Section step="8" title="Did it work?">
            <OutcomePanel outcome={o.outcome} o={o} />
          </Section>

          <section className="px-6 py-5">
            <h3 className="mb-2 text-sm font-semibold text-ink">Provenance</h3>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-1 text-xs text-ink-3 sm:grid-cols-2">
              <div>Engine: {String(prov.engine_version)}</div>
              <div>Detector: {String(prov.detector)}</div>
              <div>Data health at detection: {String(prov.data_health_score)}/100</div>
              <div>Data version: {String(prov.data_version ?? '').split('|')[0]} rows</div>
              {(prov.models as { name: string; version: string }[] | undefined)?.map((m) => (
                <div key={m.name}>
                  Model: {m.name} {m.version}
                </div>
              ))}
              <div className="sm:col-span-2">Facts: {String(prov.facts_source)}</div>
              {prov.note ? <div className="sm:col-span-2">{String(prov.note)}</div> : null}
            </dl>
          </section>
        </div>
      )}
    </Sheet>
  )
}
