import { ArrowRight, FlaskConical, RefreshCw, Search, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { FindingVisual } from '@/components/domain/FindingVisual'
import { ConfidenceNote, OutcomeBadge, StatusBadge } from '@/components/domain/labels'
import { IMPACT_LABEL, STATUS_META } from '@/components/domain/meta'
import { OpportunityDetail } from '@/components/domain/OpportunityDetail'
import { PageHeader } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { EmptyState, ErrorState, PageSkeleton } from '@/components/ui/states'
import { useOpportunities, useOverview, useRefreshEngine } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { GAIN_KINDS, IMPACT_SHORT, RISK_KINDS, supportStats } from '@/lib/findings'
import { axisMur, date, murCompact } from '@/lib/format'
import type { Opportunity, OppStatus, Overview } from '@/lib/types'

const FILTERS = {
  open: (o: Opportunity) => o.is_active && ['new', 'reviewed', 'planned'].includes(o.status),
  tracking: (o: Opportunity) => ['in_progress', 'completed'].includes(o.status),
  dismissed: (o: Opportunity) => o.status === 'dismissed',
  all: () => true,
}
type Filter = keyof typeof FILTERS
const FILTER_LABEL: Record<Filter, string> = { open: 'To decide', tracking: 'Acting on', dismissed: 'Dismissed', all: 'All' }

const SORTS = {
  priority: { label: 'Priority', fn: (a: Opportunity, b: Opportunity) => b.priority_score - a.priority_score },
  impact: { label: 'Largest impact', fn: (a: Opportunity, b: Opportunity) => (b.impact_high ?? -1) - (a.impact_high ?? -1) },
  confidence: { label: 'Most confident', fn: (a: Opportunity, b: Opportunity) => b.confidence - a.confidence },
}
type Sort = keyof typeof SORTS

const PIPELINE: OppStatus[] = ['new', 'reviewed', 'planned', 'in_progress', 'completed']
const SEVERITY = {
  critical: { label: 'Critical', dot: 'bg-bad', ink: 'text-bad-ink' },
  high: { label: 'High', dot: 'bg-serious', ink: 'text-serious-ink' },
  medium: { label: 'Medium', dot: 'bg-warn', ink: 'text-warn-ink' },
  low: { label: 'Low', dot: 'bg-before', ink: 'text-ink-3' },
} as const

function range(o: Pick<Opportunity, 'impact_low' | 'impact_high'>) {
  if (o.impact_high === null) return 'Not quantified'
  return `${murCompact(o.impact_low)}–${axisMur(o.impact_high)}`
}

/* ---------- 1. The headline: four facts, no boxes ---------- */

function Headline({
  open,
  gain,
  risk,
  onOpen,
}: {
  open: Opportunity[]
  gain?: Opportunity
  risk?: Opportunity
  onOpen: (id: string) => void
}) {
  const urgent = open.filter((o) => o.severity === 'critical' || o.severity === 'high').length
  return (
    <dl className="panel grid grid-cols-2 gap-y-6 px-6 py-6 lg:grid-cols-[auto_auto_1fr_1fr] lg:divide-x lg:divide-line">
      <div className="pr-8">
        <dt className="text-sm text-ink-3">Open findings</dt>
        <dd className="mt-1 text-[32px] font-semibold leading-none tracking-tight text-ink">{open.length}</dd>
      </div>
      <div className="lg:px-8">
        <dt className="text-sm text-ink-3">Need a decision now</dt>
        <dd className={cn('mt-1 text-[32px] font-semibold leading-none tracking-tight', urgent ? 'text-serious-ink' : 'text-ink')}>
          {urgent}
        </dd>
      </div>
      {[
        { o: gain, title: 'Biggest opportunity', tone: 'text-good-ink' },
        { o: risk, title: 'Biggest risk', tone: 'text-bad-ink' },
      ].map(
        ({ o, title, tone }) =>
          o && (
            <div key={title} className="col-span-2 min-w-0 lg:col-span-1 lg:px-8">
              <dt className={cn('text-sm font-medium', tone)}>{title}</dt>
              <dd className="mt-1">
                <button type="button" onClick={() => onOpen(o.id)} className="group block max-w-full text-left">
                  <span className="text-2xl font-semibold tracking-tight text-ink">{range(o)}</span>
                  <span className="ml-2 text-sm text-ink-3">{IMPACT_SHORT[o.impact_kind]}</span>
                  <span className="mt-0.5 block truncate text-sm text-ink-2 group-hover:text-ink group-hover:underline">{o.title}</span>
                </button>
              </dd>
            </div>
          ),
      )}
    </dl>
  )
}

/* ---------- 2. The focal visual: what each finding is worth ---------- */

function niceMax(v: number) {
  const p = 10 ** Math.floor(Math.log10(v || 1))
  const n = v / p
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p
}

function WorthColumn({
  title,
  hint,
  rows,
  color,
  onOpen,
}: {
  title: string
  hint: string
  rows: Opportunity[]
  color: string
  onOpen: (id: string) => void
}) {
  const max = niceMax(Math.max(...rows.map((r) => r.impact_high ?? 0), 1))
  const ticks = [0, max / 2, max]
  const x = (v: number) => `${(v / max) * 100}%`
  return (
    <div className="min-w-0">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="text-[13px] font-semibold uppercase tracking-wider text-ink-2">
          {title} <span className="ml-1 font-normal text-ink-3">{rows.length}</span>
        </h3>
        <span className="text-xs text-ink-3">{hint}</span>
      </div>
      <ul className="@container">
        {rows.map((o) => (
          <li key={o.id}>
            <button
              type="button"
              onClick={() => onOpen(o.id)}
              aria-label={`${o.title}: ${range(o)} ${IMPACT_SHORT[o.impact_kind]}`}
              className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1.5 rounded-lg px-2 py-2.5 text-left transition-colors hover:bg-surface-2 @sm:grid-cols-[minmax(0,1.3fr)_minmax(5rem,1fr)_8.5rem]"
            >
              <span className="min-w-0">
                <span className="line-clamp-2 text-[14.5px] font-medium leading-snug text-ink">{o.title}</span>
                <span className="text-xs text-ink-3">{IMPACT_SHORT[o.impact_kind]}</span>
              </span>
              <span className="relative col-span-2 row-start-2 h-3 @sm:col-span-1 @sm:col-start-2 @sm:row-start-1" aria-hidden>
                <span className="absolute inset-x-0 top-1/2 h-px bg-line" />
                <span className="absolute top-1/2 h-px bg-ink-3/40" style={{ width: x(o.impact_low ?? 0) }} />
                <span
                  className="grow-x absolute inset-y-0 rounded-full transition-[filter] group-hover:brightness-90"
                  style={{
                    left: x(o.impact_low ?? 0),
                    width: `max(6px, calc(${x(o.impact_high ?? 0)} - ${x(o.impact_low ?? 0)}))`,
                    background: color,
                  }}
                />
              </span>
              <span className="tnum whitespace-nowrap text-right text-sm font-semibold text-ink @sm:col-start-3 @sm:row-start-1">
                {range(o)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <div className="@container">
        <div className="hidden grid-cols-[minmax(0,1.3fr)_minmax(5rem,1fr)_8.5rem] gap-x-4 px-2 pt-1 @sm:grid" aria-hidden>
          <span />
          <span className="relative h-4 border-t border-line text-xs text-ink-3">
            {ticks.map((t, i) => (
              <span
                key={t}
                className="absolute top-1"
                style={{ left: x(t), transform: i === 0 ? 'none' : i === ticks.length - 1 ? 'translateX(-100%)' : 'translateX(-50%)' }}
              >
                {t === 0 ? '0' : axisMur(t)}
              </span>
            ))}
          </span>
          <span />
        </div>
      </div>
    </div>
  )
}

/* ---------- 3. Where each finding stands ---------- */

function PipelineTrack({ all, onPick }: { all: Opportunity[]; onPick: (f: Filter) => void }) {
  const live = all.filter((o) => o.status === 'completed' || o.status === 'in_progress' || o.is_active)
  return (
    <ol className="relative grid grid-cols-5" aria-label="Findings by stage">
      <span className="absolute left-[10%] right-[10%] top-[46px] h-px bg-line-strong" aria-hidden />
      {PIPELINE.map((s) => {
        const n = live.filter((o) => o.status === s).length
        const dot =
          n === 0
            ? 'bg-surface border-2 border-line-strong'
            : s === 'completed'
              ? 'bg-good'
              : s === 'in_progress'
                ? 'bg-accent-600'
                : 'bg-ink'
        return (
          <li key={s} className="relative">
            <button
              type="button"
              onClick={() => onPick(s === 'in_progress' || s === 'completed' ? 'tracking' : 'open')}
              className="group flex w-full flex-col items-center rounded-lg px-1 pb-1 text-center"
              aria-label={`${n} ${STATUS_META[s].label}`}
            >
              <span className={cn('text-2xl font-semibold leading-8 tracking-tight', n ? 'text-ink' : 'text-ink-3/60')}>{n}</span>
              <span
                className={cn('relative z-10 my-2 size-3 rounded-full ring-4 ring-page transition-transform group-hover:scale-125', dot)}
                aria-hidden
              />
              <span className={cn('text-xs', n ? 'font-medium text-ink-2' : 'text-ink-3')}>{STATUS_META[s].label}</span>
            </button>
          </li>
        )
      })}
    </ol>
  )
}

/* ---------- 4. A finding ---------- */

function FindingCard({ o, overview, featured, onOpen }: { o: Opportunity; overview?: Overview; featured?: boolean; onOpen: () => void }) {
  const sev = SEVERITY[o.severity]
  const support = supportStats(o)
  const visual = <FindingVisual o={o} overview={overview} large={featured} />
  return (
    <article
      className={cn(
        'panel flex flex-col p-6 transition-shadow hover:shadow-[0_12px_32px_-18px_rgba(20,22,48,0.3)]',
        o.kind === 'risk' ? 'fade-coral' : 'fade-sage',
        featured && 'lg:col-span-2',
      )}
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider">
          <span className={cn('size-2 rounded-full', sev.dot)} aria-hidden />
          <span className={sev.ink}>{sev.label}</span>
          <span className="font-medium text-ink-3">· {o.kind === 'risk' ? 'Risk' : 'Opportunity'}</span>
          {featured && <span className="font-medium text-ink-3">· Top priority</span>}
        </span>
        <span className="flex flex-wrap gap-1.5">
          {o.status !== 'new' && <StatusBadge status={o.status} />}
          {o.outcome && ['in_progress', 'completed'].includes(o.status) && <OutcomeBadge outcome={o.outcome} />}
        </span>
      </header>

      <div className={cn('mt-3 grid gap-6', featured && 'lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-10')}>
        <div className="min-w-0">
          <h2 className={cn('font-semibold leading-snug tracking-tight text-ink', featured ? 'text-xl' : 'text-[17px]')}>{o.title}</h2>
          <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-ink-3">{o.summary}</p>
          <div className="mt-5">
            <div className={cn('font-semibold tracking-tight text-ink', featured ? 'text-[30px]' : 'text-2xl')}>
              {o.impact_high === null ? 'Not quantified' : `${murCompact(o.impact_low)} – ${axisMur(o.impact_high)}`}
            </div>
            <div className="text-sm text-ink-3">{IMPACT_LABEL[o.impact_kind]}</div>
          </div>
          {support.length > 0 && (
            <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-sm">
              {support.map((s) => (
                <li key={s.label}>
                  <span className="tnum font-semibold text-ink">{s.value}</span> <span className="text-ink-3">{s.label.toLowerCase()}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        {featured && <div className="min-w-0 self-center rounded-lg bg-surface-2 p-5">{visual}</div>}
      </div>
      {!featured && <div className="mt-5">{visual}</div>}

      <div className="mt-auto pt-5">
        {o.actions[0] && (
          <p className="border-t border-line pt-4 text-sm">
            <span className="mr-2 text-xs font-semibold uppercase tracking-wider text-ink-3">Next</span>
            <span className="text-ink">{o.actions[0].title}</span>
          </p>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={onOpen}>
            View evidence <ArrowRight />
          </Button>
          {o.scenario_preset && (
            <Button size="sm" variant="ghost" asChild>
              <Link to={`/scenarios?opp=${o.id}&preset=${encodeURIComponent(JSON.stringify(o.scenario_preset.assumptions))}`}>
                <FlaskConical /> Simulate
              </Link>
            </Button>
          )}
          <span className="ml-auto">
            <ConfidenceNote value={o.confidence} basis={o.confidence_basis} />
          </span>
        </div>
      </div>
    </article>
  )
}

/* ---------- Page ---------- */

export function OpportunitiesPage() {
  const q = useOpportunities(true)
  const ov = useOverview()
  const refresh = useRefreshEngine()
  const { can } = useAuth()
  const [params, setParams] = useSearchParams()
  const [filter, setFilter] = useState<Filter>('open')
  const [kind, setKind] = useState<'all' | 'risk' | 'opportunity'>('all')
  const [sort, setSort] = useState<Sort>('priority')
  const [text, setText] = useState('')
  const openId = params.get('open')
  const list = useMemo(() => {
    const t = text.trim().toLowerCase()
    return (q.data ?? [])
      .filter(FILTERS[filter])
      .filter((o) => kind === 'all' || o.kind === kind)
      .filter((o) => !t || `${o.title} ${o.summary}`.toLowerCase().includes(t))
      .sort(SORTS[sort].fn)
  }, [q.data, filter, kind, sort, text])
  if (q.isLoading) return <PageSkeleton />
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />
  const all = q.data ?? []
  const counts = Object.fromEntries(Object.entries(FILTERS).map(([k, f]) => [k, all.filter(f).length])) as Record<Filter, number>
  const open = all.filter(FILTERS.open)
  const byHigh = (kinds: Opportunity['impact_kind'][]) =>
    open.filter((o) => kinds.includes(o.impact_kind) && o.impact_high !== null).sort((a, b) => (b.impact_high ?? 0) - (a.impact_high ?? 0))
  const gains = byHigh(GAIN_KINDS)
  const risks = byHigh(RISK_KINDS)
  const openDetail = (id: string) => setParams({ open: id })
  const featureFirst = filter === 'open' && sort === 'priority' && kind === 'all' && !text && list.length > 2
  const dismissed = all.filter((o) => o.status === 'dismissed').length

  return (
    <>
      <PageHeader
        title="Opportunities"
        meta={all[0] ? `Data to ${date(all[0].data_as_of)}` : undefined}
        description="What your ledger says you could gain, what is at risk, and what to do next."
        actions={
          can('manage_opportunities') && (
            <Button variant="ghost" size="sm" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
              <RefreshCw className={refresh.isPending ? 'animate-spin' : ''} /> Re-run engine
            </Button>
          )
        }
      />

      {open.length > 0 && <Headline open={open} gain={gains[0]} risk={risks[0]} onOpen={openDetail} />}

      {(gains.length > 0 || risks.length > 0) && (
        <Card className="mt-5" aria-labelledby="worth">
          <CardHeader
            title={<span id="worth">What each finding is worth</span>}
            subtitle="Estimated yearly range. Longer bar, bigger money. Gains and risks are never added together."
          />
          <CardBody className="grid grid-cols-1 gap-x-12 gap-y-8 lg:grid-cols-2">
            {gains.length > 0 && (
              <WorthColumn title="Opportunities" hint="to gain or free up" rows={gains} color="var(--color-gain)" onOpen={openDetail} />
            )}
            {risks.length > 0 && (
              <div className="lg:border-l lg:border-line lg:pl-10">
                <WorthColumn title="Risks" hint="money exposed" rows={risks} color="var(--color-coral-600)" onOpen={openDetail} />
              </div>
            )}
          </CardBody>
        </Card>
      )}

      <Card className="mt-5" aria-labelledby="stages">
        <CardHeader
          title={<span id="stages">Where each finding stands</span>}
          subtitle={`${dismissed} dismissed · results are measured after an action starts`}
        />
        <CardBody>
          <PipelineTrack all={all} onPick={setFilter} />
        </CardBody>
      </Card>

      <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-3">
        <div
          className="flex max-w-full gap-1 overflow-x-auto rounded-full border border-line bg-surface p-1 shadow-card"
          role="tablist"
          aria-label="Filter by stage"
        >
          {(Object.keys(FILTERS) as Filter[]).map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={filter === f}
              onClick={() => setFilter(f)}
              className={cn(
                'min-h-9 shrink-0 whitespace-nowrap rounded-full px-4 text-sm transition-colors',
                filter === f ? 'bg-accent-600 font-semibold text-white' : 'text-ink-2 hover:text-ink',
              )}
            >
              {FILTER_LABEL[f]} <span className={cn('tnum', filter === f ? 'text-white/80' : 'text-ink-3')}>{counts[f]}</span>
            </button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="flex rounded-full border border-line bg-surface p-1 text-sm shadow-card" role="group" aria-label="Filter by type">
            {(['all', 'risk', 'opportunity'] as const).map((k) => (
              <button
                key={k}
                type="button"
                aria-pressed={kind === k}
                onClick={() => setKind(k)}
                className={cn(
                  'min-h-8 rounded-full px-3',
                  kind === k ? 'bg-accent-50 font-semibold text-accent-700' : 'text-ink-2 hover:text-ink',
                )}
              >
                {k === 'all' ? 'All' : k === 'risk' ? 'Risks' : 'Opportunities'}
              </button>
            ))}
          </div>
          <label className="relative">
            <span className="sr-only">Search findings</span>
            <Search className="pointer-events-none absolute left-3 top-3 size-4 text-ink-3" aria-hidden />
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Search"
              maxLength={60}
              className="h-10 w-40 rounded-full border border-line bg-surface pl-9 pr-8 text-sm shadow-card outline-none focus:border-accent-600 focus:ring-2 focus:ring-accent-100 sm:w-48"
            />
            {text && (
              <button
                type="button"
                onClick={() => setText('')}
                className="absolute right-2.5 top-3 text-ink-3 hover:text-ink"
                aria-label="Clear search"
              >
                <X className="size-4" />
              </button>
            )}
          </label>
          <label className="flex h-10 items-center gap-1 rounded-full border border-line bg-surface pl-4 pr-2 text-sm text-ink-3 shadow-card">
            Sort:
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as Sort)}
              className="h-8 rounded-full bg-transparent pr-1 font-medium text-ink outline-none focus:ring-2 focus:ring-accent-100"
            >
              {Object.entries(SORTS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {list.length === 0 ? (
        <EmptyState title="Nothing here" icon={<Search className="size-5" />}>
          No findings match this view. Try another filter, import new data or re-run the engine.
        </EmptyState>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {list.map((o, i) => (
            <FindingCard key={o.id} o={o} overview={ov.data} featured={featureFirst && i === 0} onOpen={() => openDetail(o.id)} />
          ))}
        </div>
      )}
      <OpportunityDetail id={openId} onClose={() => setParams({})} />
    </>
  )
}
