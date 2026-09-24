import { AlertTriangle, ChevronLeft, ChevronRight, Copy, ExternalLink, Search, Tag, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { DataKind } from '@/components/domain/labels'
import { PageHeader } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Sheet } from '@/components/ui/sheet'
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/states'
import { useDebounced } from '@/hooks/useDebounced'
import { useFacets, useHealth, useTransaction, useTransactions } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { date, dateTime, mur } from '@/lib/format'
import type { Transaction } from '@/lib/types'

const input =
  'h-9 rounded-lg border border-line-strong bg-surface px-3 text-sm outline-none focus:border-accent-600 focus:ring-2 focus:ring-accent-100'

function Flags({ t }: { t: Transaction }) {
  return (
    <span className="flex flex-wrap gap-1">
      {t.is_anomaly && (
        <Badge tone="serious">
          <AlertTriangle /> Unusual
        </Badge>
      )}
      {t.duplicate_group && !t.excluded && (
        <Badge tone="warn">
          <Copy /> Possible duplicate
        </Badge>
      )}
      {t.excluded && <Badge>Excluded</Badge>}
      {t.category === 'Uncategorised' && (
        <Badge tone="warn">
          <Tag /> Uncategorised
        </Badge>
      )}
    </span>
  )
}

/** Recent payments to the same payee as bars, this one highlighted, with the usual (median) amount marked. */
function HistoryBars({
  recent,
  current,
  median,
}: {
  recent: { id: string; date: string; amount: number }[]
  current: string
  median: number | null
}) {
  const max = Math.max(...recent.map((h) => h.amount), median ?? 0, 1)
  return (
    <div className="mt-3">
      <ul className="space-y-1.5">
        {recent.map((h) => (
          <li key={h.id} className="grid grid-cols-[5.5rem_1fr_6.5rem] items-center gap-2 text-xs">
            <span className={h.id === current ? 'font-medium text-ink' : 'text-ink-3'}>{date(h.date)}</span>
            <span className="relative h-2.5">
              <span
                className={cn('grow-x block h-full rounded-r-[4px]', h.id === current ? 'bg-actual' : 'bg-before')}
                style={{ width: `${Math.max(1.5, (h.amount / max) * 100)}%` }}
              />
              {median !== null && (
                <span
                  className="absolute -inset-y-1 w-px border-l border-dashed border-ink-2"
                  style={{ left: `${(median / max) * 100}%` }}
                  aria-hidden
                />
              )}
            </span>
            <span className={cn('tnum text-right', h.id === current ? 'font-semibold text-ink' : 'text-ink-2')}>{mur(h.amount)}</span>
          </li>
        ))}
      </ul>
      {median !== null && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-ink-3">
          <span className="h-3 w-0 border-l border-dashed border-ink-2" aria-hidden /> usual amount (median) {mur(median)}
          <span className="ml-2 inline-block size-2.5 rounded-sm bg-actual" aria-hidden /> this payment
        </p>
      )}
    </div>
  )
}

function Detail({ id, onClose }: { id: string | null; onClose: () => void }) {
  const q = useTransaction(id)
  const t = q.data
  return (
    <Sheet
      open={!!id}
      onOpenChange={(o) => !o && onClose()}
      title={t ? (t.counterparty ?? t.description) : 'Transaction'}
      description={t ? `${date(t.date)} · ${t.category}` : undefined}
    >
      {q.isLoading && <Skeleton className="m-6 h-48" />}
      {q.error && (
        <div className="p-6">
          <ErrorState error={q.error} />
        </div>
      )}
      {t && (
        <div className="space-y-6 p-6 text-sm">
          <div className="flex items-baseline justify-between">
            <div className={cn('tnum text-3xl font-semibold', t.direction === 'inflow' ? 'text-good-ink' : 'text-ink')}>
              {mur(t.direction === 'outflow' ? -t.amount : t.amount, { cents: true, signed: true })}
            </div>
            <DataKind kind="actual" />
          </div>
          <Flags t={t} />
          {t.is_anomaly && (
            <div className="rounded-lg border border-serious/30 bg-serious-bg/50 p-3">
              <div className="font-medium text-ink">Why this was flagged</div>
              <p className="mt-1 text-ink-2">{t.anomaly_reason}</p>
              <p className="mt-1 text-xs text-ink-3">
                A flag is a prompt to review, not a confirmed error.
                {t.anomaly_score !== null && ` Isolation Forest score ${t.anomaly_score.toFixed(3)}.`}
              </p>
            </div>
          )}
          <dl className="grid grid-cols-[140px_1fr] gap-y-2">
            {[
              ['Description', t.description],
              ['Payee / customer', t.counterparty ?? '—'],
              ['Category', `${t.category}${t.subcategory ? ` · ${t.subcategory}` : ''}`],
              ['Direction', t.direction === 'inflow' ? 'Money in' : 'Money out'],
              ['Reference', t.reference ?? '—'],
              ['Payment method', t.payment_method ?? '—'],
              ['Source', t.source === 'seed' ? 'Synthetic demo seed' : t.source === 'import' ? 'CSV import' : t.source],
              ['Recorded', dateTime(t.created_at)],
            ].map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-ink-3">{k}</dt>
                <dd className="text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          {t.counterparty_history && (
            <div>
              <h3 className="mb-2 font-medium text-ink">History with {t.counterparty}</h3>
              <p className="text-ink-3">
                {t.counterparty_history.count} payments · median {mur(t.counterparty_history.median)} · total{' '}
                {mur(t.counterparty_history.total)}
              </p>
              <HistoryBars recent={t.counterparty_history.recent} current={t.id} median={t.counterparty_history.median} />
            </div>
          )}
          {t.duplicates.length > 1 && (
            <div>
              <h3 className="mb-2 font-medium text-ink">Same date, amount and payee</h3>
              <ul className="space-y-1 text-ink-2">
                {t.duplicates.map((d) => (
                  <li key={d.id}>
                    {date(d.date)} · {mur(d.amount)} {d.id === t.id && '(this one)'} {d.excluded && '· excluded'}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {t.pending_changes.length > 0 && (
            <div>
              <h3 className="mb-2 font-medium text-ink">Proposed data changes</h3>
              {t.pending_changes.map((p) => (
                <p key={p.id} className="text-ink-2">
                  {p.change_type === 'set_category' ? `Set category to ${p.new_value}` : 'Exclude as duplicate'} ·{' '}
                  <span className="capitalize">{p.status}</span>
                </p>
              ))}
              <Link to="/data-health" className="text-accent-700 hover:underline">
                Review in Data Health
              </Link>
            </div>
          )}
          {t.related_opportunities.length > 0 && (
            <div>
              <h3 className="mb-2 font-medium text-ink">Used as evidence in</h3>
              {t.related_opportunities.map((o) => (
                <Link key={o.id} to={`/opportunities?open=${o.id}`} className="flex items-center gap-1 text-accent-700 hover:underline">
                  {o.title} <ExternalLink className="size-3.5" />
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </Sheet>
  )
}

export function TransactionsPage() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState(params.get('category') ?? '')
  const [counterparty, setCounterparty] = useState(params.get('counterparty') ?? '')
  const [direction, setDirection] = useState('')
  const [flag, setFlag] = useState(params.get('flag') ?? '')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(1)
  const dq = useDebounced(q, 300)
  const facets = useFacets()
  const list = useTransactions({ q: dq, category, counterparty, direction, flag, date_from: from, date_to: to, page, page_size: 50 })
  const openId = params.get('open')
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1
  const reset = (fn: () => void) => {
    fn()
    setPage(1)
  }

  const health = useHealth()
  const suspicious = health.data?.checks.find((c) => c.key === 'suspicious')?.count ?? 0
  const quick = [
    { key: 'anomaly', label: 'Unusual payments', count: suspicious, icon: AlertTriangle, tone: 'text-serious-ink' },
    {
      key: 'duplicate',
      label: 'Possible duplicates',
      count: Number(health.data?.totals.duplicate_groups ?? 0),
      icon: Copy,
      tone: 'text-warn-ink',
    },
    {
      key: 'uncategorised',
      label: 'Uncategorised',
      count: Number(health.data?.totals.uncategorised ?? 0),
      icon: Tag,
      tone: 'text-warn-ink',
    },
  ]
  const active = !!(q || category || counterparty || direction || flag || from || to)
  const clearAll = () =>
    reset(() => {
      setQ('')
      setCategory('')
      setCounterparty('')
      setDirection('')
      setFlag('')
      setFrom('')
      setTo('')
    })
  const signed = (t: Transaction) =>
    mur(t.direction === 'outflow' ? -t.amount : t.amount, { cents: true, signed: t.direction === 'inflow' })

  return (
    <>
      <PageHeader
        title="Transactions"
        meta={facets.data?.date_min ? `${date(facets.data.date_min)} – ${date(facets.data.date_max)}` : undefined}
        description="Every recorded transaction, with anomaly and data-quality flags. Click a row for its history and evidence."
        actions={<DataKind kind="actual" />}
      />

      <div className="mb-5 flex flex-wrap items-center gap-2 text-sm">
        <span className="mr-1 text-ink-3">Worth a look:</span>
        {quick.map((f) => {
          const on = flag === f.key
          return (
            <button
              key={f.key}
              type="button"
              aria-pressed={on}
              onClick={() => reset(() => setFlag(on ? '' : f.key))}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 transition-colors',
                on ? 'border-ink bg-ink text-white' : 'border-line bg-surface text-ink-2 hover:border-line-strong hover:text-ink',
              )}
            >
              <f.icon className={cn('size-3.5', on ? 'text-white' : f.tone)} aria-hidden />
              <span className="font-semibold">{f.count}</span> {f.label.toLowerCase()}
            </button>
          )
        })}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2 border-y border-line py-3">
        <div className="relative min-w-0 flex-1 basis-60">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-ink-3" aria-hidden />
          <input
            value={q}
            onChange={(e) => reset(() => setQ(e.target.value))}
            placeholder="Search description, payee, reference"
            aria-label="Search"
            className={cn(input, 'w-full pl-8')}
            maxLength={80}
          />
        </div>
        <select
          value={category}
          onChange={(e) => reset(() => setCategory(e.target.value))}
          className={cn(input, 'max-w-52')}
          aria-label="Category"
        >
          <option value="">All categories</option>
          {facets.data?.categories.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name} ({c.count})
            </option>
          ))}
        </select>
        <select value={direction} onChange={(e) => reset(() => setDirection(e.target.value))} className={input} aria-label="Direction">
          <option value="">In and out</option>
          <option value="inflow">Money in</option>
          <option value="outflow">Money out</option>
        </select>
        <select value={flag} onChange={(e) => reset(() => setFlag(e.target.value))} className={input} aria-label="Flag">
          <option value="">Any flag</option>
          <option value="anomaly">Unusual payments</option>
          <option value="duplicate">Possible duplicates</option>
          <option value="uncategorised">Uncategorised</option>
          <option value="excluded">Excluded</option>
        </select>
        <div className="flex items-center gap-1 text-sm text-ink-3">
          <input
            type="date"
            value={from}
            onChange={(e) => reset(() => setFrom(e.target.value))}
            className={cn(input, 'w-36 px-2')}
            aria-label="From date"
            min={facets.data?.date_min ?? undefined}
            max={facets.data?.date_max ?? undefined}
          />
          <span aria-hidden>–</span>
          <input
            type="date"
            value={to}
            onChange={(e) => reset(() => setTo(e.target.value))}
            className={cn(input, 'w-36 px-2')}
            aria-label="To date"
            min={facets.data?.date_min ?? undefined}
            max={facets.data?.date_max ?? undefined}
          />
        </div>
        {counterparty && (
          <Badge tone="brand">
            Payee: {counterparty}
            <button onClick={() => reset(() => setCounterparty(''))} aria-label="Clear payee filter" className="ml-1">
              <X className="size-3" />
            </button>
          </Badge>
        )}
        {active && (
          <Button variant="ghost" size="sm" onClick={clearAll}>
            <X /> Clear filters
          </Button>
        )}
      </div>

      <Card className="overflow-hidden">
        {list.error ? (
          <div className="p-6">
            <ErrorState error={list.error} onRetry={() => list.refetch()} />
          </div>
        ) : !list.data ? (
          <div className="space-y-2 p-4" role="status" aria-label="Loading transactions">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : list.data.items.length === 0 ? (
          <EmptyState title="No transactions match these filters" icon={<Search className="size-5" />}>
            {active && (
              <Button variant="link" onClick={clearAll}>
                Clear all filters
              </Button>
            )}
          </EmptyState>
        ) : (
          <div className={cn('transition-opacity', list.isFetching && 'opacity-60')}>
            {/* Phone: one card per transaction, amount always visible. */}
            <ul className="divide-y divide-line md:hidden">
              {list.data.items.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => setParams({ open: t.id })}
                    className={cn(
                      'flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-2',
                      t.excluded && 'text-ink-3 line-through',
                    )}
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-ink">{t.counterparty ?? t.description}</span>
                      <span className="block truncate text-xs text-ink-3">
                        {date(t.date)} · {t.category}
                      </span>
                      <span className="mt-1 block">
                        <Flags t={t} />
                      </span>
                    </span>
                    <span className={cn('tnum shrink-0 text-sm font-medium', t.direction === 'inflow' ? 'text-good-ink' : 'text-ink')}>
                      {signed(t)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead className="bg-surface-2 text-left text-xs text-ink-3">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Date</th>
                    <th className="px-4 py-2.5 font-medium">Description</th>
                    <th className="px-4 py-2.5 font-medium">Category</th>
                    <th className="px-4 py-2.5 font-medium">Flags</th>
                    <th className="px-4 py-2.5 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {list.data.items.map((t) => (
                    <tr
                      key={t.id}
                      className={cn(
                        'cursor-pointer transition-colors hover:bg-surface-2',
                        t.excluded && 'text-ink-3 line-through decoration-ink-3/40',
                      )}
                      onClick={() => setParams({ open: t.id })}
                    >
                      <td className="whitespace-nowrap px-4 py-2.5 text-ink-3">{date(t.date)}</td>
                      <td className="max-w-md px-4 py-2.5">
                        <button
                          className="block max-w-full truncate text-left font-medium text-ink hover:underline"
                          onClick={(e) => {
                            e.stopPropagation()
                            setParams({ open: t.id })
                          }}
                        >
                          {t.counterparty ?? t.description}
                        </button>
                        {t.counterparty && <div className="truncate text-xs text-ink-3">{t.description}</div>}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-ink-2">{t.category}</td>
                      <td className="px-4 py-2.5">
                        <Flags t={t} />
                      </td>
                      <td
                        className={cn(
                          'tnum whitespace-nowrap px-4 py-2.5 text-right font-medium',
                          t.direction === 'inflow' ? 'text-good-ink' : 'text-ink',
                        )}
                      >
                        {signed(t)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {list.data && list.data.total > 0 && (
          <footer className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-ink-3">
            <span className="tnum">
              {(page - 1) * 50 + 1}–{Math.min(page * 50, list.data.total)} of {list.data.total.toLocaleString('en-GB')}
              {active && ' matching'}
            </span>
            <div className="flex items-center gap-2">
              <span className="tnum hidden text-xs sm:inline">
                Page {page} of {pages}
              </span>
              <Button variant="secondary" size="icon" onClick={() => setPage((p) => p - 1)} disabled={page <= 1} aria-label="Previous page">
                <ChevronLeft />
              </Button>
              <Button variant="secondary" size="icon" onClick={() => setPage((p) => p + 1)} disabled={page >= pages} aria-label="Next page">
                <ChevronRight />
              </Button>
            </div>
          </footer>
        )}
      </Card>
      <Detail id={openId} onClose={() => setParams({})} />
    </>
  )
}
