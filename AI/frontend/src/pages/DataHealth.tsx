import { AlertCircle, CheckCircle2, Copy, Download, FileUp, Info, Tag, UserRound, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { PageHeader } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { EmptyState, ErrorState, PageSkeleton, Skeleton } from '@/components/ui/states'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CompositionBar } from '@/components/viz/CompositionBar'
import { Meter } from '@/components/viz/Meter'
import { ScoreRing } from '@/components/viz/ScoreRing'
import { useAudit, useBatchAction, useDecision, useHealth, useImport, useImports, useProposals, useUpload } from '@/hooks/queries'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { date, dateTime, mur } from '@/lib/format'
import type { ImportBatch, Proposal } from '@/lib/types'

const CATEGORIES = [
  'Sales',
  'Other income',
  'Owner contribution',
  'Loan proceeds',
  'Inventory & supplies',
  'Payroll',
  'Rent',
  'Utilities',
  'Telecom & internet',
  'Software & subscriptions',
  'Marketing',
  'Insurance',
  'Repairs & maintenance',
  'Professional fees',
  'Transport & logistics',
  'Bank fees',
  'Equipment',
  'Other expenses',
  'Taxes (VAT)',
  'Loan repayment',
  'Owner drawings',
]
const COMPONENT_LABEL: Record<string, string> = {
  validity: 'Valid rows',
  duplicates: 'Free of duplicates',
  coverage: 'Categorised',
  completeness: 'Payee recorded',
}
const KIND = {
  set_category: { label: 'Category suggestion', icon: Tag },
  exclude_duplicate: { label: 'Possible duplicate', icon: Copy },
  set_counterparty: { label: 'Payee match', icon: UserRound },
}

function ScoreCard({
  score,
  components,
  title,
  subtitle,
}: {
  score: number
  components: Record<string, number>
  title: string
  subtitle?: string
}) {
  return (
    <Card>
      <CardHeader
        title={title}
        subtitle={subtitle}
        info="Score = 40% valid rows + 20% duplicate-free + 20% categorised + 20% payee recorded. It is capped below 100 while any issue is open."
      />
      <CardBody className="flex flex-wrap items-center gap-8">
        <ScoreRing score={score} label="Data health" />
        <ul className="min-w-56 flex-1 space-y-3 text-sm">
          {Object.entries(components).map(([k, v]) => (
            <li key={k}>
              <div className="mb-1 flex justify-between">
                <span className="flex items-center gap-1.5 text-ink-2">
                  {v >= 100 ? (
                    <CheckCircle2 className="size-3.5 text-good" aria-label="Complete" />
                  ) : (
                    <AlertCircle className="size-3.5 text-warn" aria-label="Incomplete" />
                  )}
                  {COMPONENT_LABEL[k] ?? k}
                </span>
                <span className="tnum font-medium text-ink">{v.toFixed(1)}%</span>
              </div>
              <Meter
                value={v}
                max={100}
                tone={v >= 99.5 ? 'good' : v >= 90 ? 'warn' : 'bad'}
                size="sm"
                label={`${COMPONENT_LABEL[k] ?? k} ${v.toFixed(1)}%`}
              />
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  )
}

function ProposalRow({ p, canEdit }: { p: Proposal; canEdit: boolean }) {
  const decide = useDecision()
  const [value, setValue] = useState(p.new_value ?? '')
  const K = KIND[p.change_type]
  const low = p.confidence !== null && p.confidence < 0.45
  const amount = typeof p.target.amount === 'string' ? Number(p.target.amount) : (p.target.amount as number)
  return (
    <li className="grid gap-3 px-5 py-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_auto] lg:items-center">
      <div className="min-w-0">
        <Badge tone={p.change_type === 'exclude_duplicate' ? 'warn' : 'brand'}>
          <K.icon /> {K.label}
        </Badge>
        <div className="mt-1.5 truncate text-sm font-medium text-ink">{String(p.target.description ?? '')}</div>
        <div className="text-xs text-ink-3">
          {p.target.row_number ? `Row ${p.target.row_number} · ` : ''}
          {date(String(p.target.date ?? ''))} · {mur(p.target.direction === 'outflow' ? -amount : amount, { cents: true })}
          {p.target.counterparty ? ` · ${p.target.counterparty}` : ''}
        </div>
      </div>
      <div className="text-sm">
        {p.change_type === 'set_category' ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-ink-3 line-through">{p.old_value}</span>→
            {canEdit && p.status === 'pending' ? (
              <select
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="h-8 rounded-md border border-line-strong px-2 text-sm"
                aria-label="Category to apply"
              >
                {CATEGORIES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            ) : (
              <strong>{p.new_value}</strong>
            )}
          </div>
        ) : p.change_type === 'set_counterparty' ? (
          <div>
            Set payee to <strong>{p.new_value}</strong>
          </div>
        ) : (
          <div>{p.target_type === 'transaction' ? 'Exclude from analytics (record is kept)' : 'Do not import this row'}</div>
        )}
        <p className="mt-1 line-clamp-2 text-xs text-ink-3" title={`${p.reason} Source: ${p.source}`}>
          {p.reason}
        </p>
        {p.confidence !== null && (
          <div className="mt-1.5 flex max-w-56 items-center gap-2 text-xs text-ink-3">
            <Meter
              value={p.confidence}
              max={1}
              size="sm"
              tone={low ? 'warn' : 'brand'}
              label={`Suggestion confidence ${Math.round(p.confidence * 100)}%`}
            />
            <span className="tnum shrink-0 font-medium text-ink">{Math.round(p.confidence * 100)}%</span>
            <span className="shrink-0">sure</span>
          </div>
        )}
        {low && (
          <Badge tone="warn" className="mt-1">
            <AlertCircle /> Low confidence - check before approving
          </Badge>
        )}
      </div>
      <div className="flex gap-2 lg:justify-end">
        {p.status === 'pending' ? (
          canEdit ? (
            <>
              <Button
                size="sm"
                variant="accent"
                disabled={decide.isPending}
                onClick={() =>
                  decide.mutate({ id: p.id, decision: 'approve', newValue: p.change_type === 'set_category' ? value : undefined })
                }
              >
                <CheckCircle2 /> Approve
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ id: p.id, decision: 'reject' })}
              >
                <X /> Reject
              </Button>
            </>
          ) : (
            <span className="text-xs text-ink-3">Needs an owner or accountant</span>
          )
        ) : (
          <Badge tone={p.status === 'approved' ? 'good' : 'neutral'} className="capitalize">
            {p.status}
            {p.decided_by ? ` by ${p.decided_by}` : ''}
          </Badge>
        )}
      </div>
    </li>
  )
}

function ImportReview({ id, onClose }: { id: string; onClose: () => void }) {
  const q = useImport(id)
  const act = useBatchAction()
  const { can } = useAuth()
  const [filter, setFilter] = useState<'problems' | 'all'>('problems')
  if (q.isLoading) return <Skeleton className="h-96" />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const b = q.data
  const rows = (b.rows ?? []).filter((r) => filter === 'all' || r.status !== 'valid')
  const open = b.status === 'validated'
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1fr]">
        <ScoreCard
          title={`Import health: ${b.filename}`}
          subtitle={`${b.row_count} rows · uploaded ${dateTime(b.created_at)} by ${b.uploaded_by ?? '—'}`}
          score={b.health.score}
          components={b.health.components}
        />
        <Card>
          <CardHeader title="What we found" subtitle="Nothing is written to your records until you commit" />
          <CardBody className="space-y-4 text-sm">
            <CompositionBar
              label={`Rows in ${b.filename} by status`}
              format={(v) => `${v} rows`}
              segments={[
                {
                  key: 'valid',
                  label: 'Ready',
                  value: b.valid_count,
                  color: 'var(--color-good)',
                  icon: <CheckCircle2 className="size-3.5 text-good" aria-hidden />,
                },
                {
                  key: 'warning',
                  label: 'Ready, with a note',
                  value: b.warning_count,
                  color: 'var(--color-actual)',
                  icon: <Info className="size-3.5 text-actual" aria-hidden />,
                },
                {
                  key: 'duplicate',
                  label: 'Possible duplicate',
                  value: b.duplicate_count,
                  color: 'var(--color-warn)',
                  icon: <Copy className="size-3.5 text-warn-ink" aria-hidden />,
                },
                {
                  key: 'error',
                  label: 'Error - will be skipped',
                  value: b.error_count,
                  color: 'var(--color-bad)',
                  icon: <AlertCircle className="size-3.5 text-bad" aria-hidden />,
                },
              ]}
            />
            <div className="grid grid-cols-1 gap-2 border-t border-line pt-3 sm:grid-cols-2">
              <Stat ok label={`${b.valid_count + b.warning_count} usable rows`} />
              <Stat ok={b.health.valid_dates_pct === 100} label={`${b.health.valid_dates_pct}% valid dates`} />
              <Stat ok={b.error_count === 0} label={`${b.error_count} rows with errors (will be skipped)`} />
              <Stat ok={b.duplicate_count === 0} label={`${b.duplicate_count} possible duplicates`} />
              <Stat ok={b.health.uncategorised === 0} label={`${b.health.uncategorised} without a category`} />
              <Stat ok={b.health.missing_payee === 0} label={`${b.health.missing_payee} expenses without a payee`} />
            </div>
          </CardBody>
          {open && can('import_data') && (
            <footer className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3">
              <Button
                variant="accent"
                disabled={act.isPending || (b.pending_duplicates ?? 0) > 0}
                onClick={() => act.mutate({ id: b.id, action: 'commit' })}
              >
                Commit {b.valid_count + b.warning_count} rows
              </Button>
              <Button
                variant="secondary"
                disabled={act.isPending}
                onClick={() => act.mutate({ id: b.id, action: 'discard' }, { onSuccess: onClose })}
              >
                Discard
              </Button>
              {(b.pending_duplicates ?? 0) > 0 && (
                <span className="text-xs text-warn-ink">Decide on {b.pending_duplicates} possible duplicate(s) first.</span>
              )}
              {act.error && <span className="text-xs text-bad-ink">{(act.error as ApiError).message}</span>}
            </footer>
          )}
          {!open && (
            <p className="border-t border-line px-5 py-3 text-sm text-ink-2">
              This import was {b.status}
              {b.status === 'committed' ? ` - ${b.committed_rows} rows added. Opportunities were re-evaluated.` : '.'}
            </p>
          )}
        </Card>
      </div>
      {(b.proposals?.length ?? 0) > 0 && (
        <Card>
          <CardHeader
            title="Proposed fixes for this file"
            subtitle="Approve, correct or reject each one. Decisions are recorded in the audit trail."
          />
          <ul className="divide-y divide-line">
            {b.proposals!.map((p) => (
              <ProposalRow key={p.id} p={p} canEdit={open && can('approve_changes')} />
            ))}
          </ul>
        </Card>
      )}
      <Card>
        <CardHeader
          title="Rows"
          action={
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as 'problems' | 'all')}
              className="h-8 rounded-md border border-line-strong px-2 text-sm"
              aria-label="Rows to show"
            >
              <option value="problems">Rows with issues</option>
              <option value="all">All rows</option>
            </select>
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs text-ink-3">
              <tr>
                <th className="px-4 py-2">Row</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">As uploaded</th>
                <th className="px-4 py-2">Issues</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.id} className="align-top">
                  <td className="tnum px-4 py-2 text-ink-3">{r.row_number}</td>
                  <td className="px-4 py-2">
                    <Badge
                      tone={r.status === 'error' ? 'bad' : r.status === 'duplicate' ? 'warn' : r.status === 'warning' ? 'warn' : 'good'}
                      className="capitalize"
                    >
                      {r.status}
                    </Badge>
                  </td>
                  <td className="max-w-md px-4 py-2 text-ink-2">
                    <span className="text-ink-3">{r.raw.date}</span> · {r.raw.description} · <span className="tnum">{r.raw.amount}</span>
                  </td>
                  <td className="px-4 py-2 text-ink-2">
                    <ul className="space-y-0.5">
                      {r.issues.map((i, k) => (
                        <li key={k} className={cn('flex gap-1.5', i.level === 'error' ? 'text-bad-ink' : 'text-ink-2')}>
                          {i.level === 'error' ? (
                            <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
                          ) : (
                            <Info className="mt-0.5 size-3.5 shrink-0" />
                          )}
                          {i.message}
                        </li>
                      ))}
                      {r.issues.length === 0 && <li className="text-ink-3">No issues</li>}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

function Stat({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-start gap-2">
      {ok ? (
        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-good" aria-label="OK" />
      ) : (
        <AlertCircle className="mt-0.5 size-4 shrink-0 text-warn" aria-label="Needs attention" />
      )}
      <span className="text-ink-2">{label}</span>
    </div>
  )
}

function Uploader({ onUploaded }: { onUploaded: (b: ImportBatch) => void }) {
  const up = useUpload()
  const ref = useRef<HTMLInputElement>(null)
  return (
    <Card>
      <CardHeader
        title="Import financial data"
        subtitle="Bank or card export as CSV (max 5 MB). Required columns: date, description, and amount or debit + credit."
      />
      <CardBody className="flex flex-wrap items-center gap-3">
        <input
          ref={ref}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) up.mutate(f, { onSuccess: onUploaded })
            e.target.value = ''
          }}
        />
        <Button onClick={() => ref.current?.click()} disabled={up.isPending}>
          <FileUp /> {up.isPending ? 'Checking file…' : 'Choose CSV file'}
        </Button>
        <Button variant="link" asChild>
          <a href="/demo/coastal_petty_cash_sep2026.csv" download>
            <Download className="size-4" /> Sample file (synthetic, deliberately messy)
          </a>
        </Button>
        {up.error && (
          <p role="alert" className="w-full text-sm text-bad-ink">
            {(up.error as ApiError).message}
          </p>
        )}
      </CardBody>
    </Card>
  )
}

export function DataHealthPage() {
  const health = useHealth()
  const proposals = useProposals('pending')
  const imports = useImports()
  const { can } = useAuth()
  const audit = useAudit('data', can('view_audit'))
  const [batch, setBatch] = useState<string | null>(null)
  const [params] = useSearchParams()
  const [tab, setTab] = useState(params.get('tab') === 'import' ? 'import' : 'ledger')
  if (health.isLoading) return <PageSkeleton />
  if (health.error || !health.data) return <ErrorState error={health.error} onRetry={() => health.refetch()} />
  const h = health.data
  const changes = (audit.data ?? []).filter((e) => e.event.startsWith('data.change_'))

  return (
    <>
      <PageHeader
        title="Data Health"
        description="Is the data good enough to trust? Fixes are proposed, never applied silently: each needs approval and is logged."
      />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="ledger">Ledger health</TabsTrigger>
          <TabsTrigger value="import">Import data{batch ? ' · review' : ''}</TabsTrigger>
          <TabsTrigger value="trail">Change history</TabsTrigger>
        </TabsList>
        <TabsContent value="ledger" className="mt-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="flex flex-col gap-4">
              <ScoreCard
                title="Data health"
                subtitle={`${Number(h.totals.transactions).toLocaleString('en-GB')} transactions · ${date(String(h.totals.date_min))} – ${date(String(h.totals.date_max))}`}
                score={h.score}
                components={h.components}
              />
              <a
                href="#proposals"
                className={cn(
                  'flex items-center gap-3 rounded-[var(--radius-card)] border px-5 py-4 text-sm transition-colors',
                  (proposals.data?.length ?? 0) > 0 ? 'border-warn/40 bg-warn-bg/60 hover:bg-warn-bg' : 'border-good/30 bg-good-bg/60',
                )}
              >
                {(proposals.data?.length ?? 0) > 0 ? (
                  <AlertCircle className="size-5 shrink-0 text-warn-ink" aria-hidden />
                ) : (
                  <CheckCircle2 className="size-5 shrink-0 text-good-ink" aria-hidden />
                )}
                <span className="flex-1 text-ink">
                  {(proposals.data?.length ?? 0) > 0 ? (
                    <>
                      <strong>{proposals.data?.length} proposed changes</strong> are waiting for a decision
                    </>
                  ) : (
                    'No changes waiting for a decision'
                  )}
                </span>
                {(proposals.data?.length ?? 0) > 0 && <span className="text-xs font-medium text-accent-700">Review ↓</span>}
              </a>
            </div>
            <Card>
              <CardHeader title="Checks" subtitle="Run on every record before it is analysed" />
              <ul className="divide-y divide-line">
                {h.checks.map((c) => (
                  <li key={c.key} className="flex gap-3 px-5 py-3 text-sm">
                    {c.status === 'ok' ? (
                      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-good" aria-label="OK" />
                    ) : c.status === 'warning' ? (
                      <AlertCircle className="mt-0.5 size-4 shrink-0 text-warn" aria-label="Warning" />
                    ) : (
                      <Info className="mt-0.5 size-4 shrink-0 text-actual" aria-label="Info" />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-ink">{c.label}</div>
                      <div className="text-ink-3">{c.detail}</div>
                    </div>
                    {c.status !== 'ok' && c.key !== 'valid' && (
                      <Link
                        to={`/transactions?flag=${c.key === 'coverage' ? 'uncategorised' : c.key === 'duplicates' ? 'duplicate' : 'anomaly'}`}
                        className="shrink-0 self-center text-xs font-medium text-accent-700 hover:underline"
                      >
                        View
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          </div>
          <Card id="proposals" className="scroll-mt-20">
            <CardHeader
              title={`Proposed changes (${proposals.data?.length ?? 0})`}
              subtitle="Approve, correct or reject each one"
              info="Category suggestions come from a local text model; duplicates from an exact-match rule (same date, direction, amount and payee). Nothing changes until someone approves."
            />
            {proposals.data?.length === 0 ? (
              <EmptyState title="Nothing to review" />
            ) : (
              <ul className="divide-y divide-line">
                {proposals.data?.map((p) => (
                  <ProposalRow key={p.id} p={p} canEdit={can('approve_changes')} />
                ))}
              </ul>
            )}
          </Card>
        </TabsContent>
        <TabsContent value="import" className="mt-4 space-y-4">
          {can('import_data') ? (
            <Uploader onUploaded={(b) => setBatch(b.id)} />
          ) : (
            <Card>
              <CardBody className="text-sm text-ink-3">Your role can view imports but not upload data.</CardBody>
            </Card>
          )}
          {batch && <ImportReview id={batch} onClose={() => setBatch(null)} />}
          <Card>
            <CardHeader title="Import history" />
            {imports.data?.length === 0 ? (
              <EmptyState title="No imports yet" />
            ) : (
              <ul className="divide-y divide-line">
                {imports.data?.map((b) => (
                  <li key={b.id}>
                    <button
                      onClick={() => setBatch(b.id)}
                      className="flex w-full flex-wrap items-center justify-between gap-2 px-5 py-3 text-left text-sm hover:bg-surface-2"
                    >
                      <span>
                        <span className="font-medium text-ink">{b.filename}</span>{' '}
                        <span className="text-ink-3">
                          · {dateTime(b.created_at)} · {b.uploaded_by}
                        </span>
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="flex w-28 items-center gap-2">
                          <Meter
                            value={b.health.score}
                            max={100}
                            size="sm"
                            tone={b.health.score >= 90 ? 'good' : b.health.score >= 70 ? 'warn' : 'bad'}
                            label={`Import health ${b.health.score}`}
                          />
                          <span className="tnum text-xs text-ink-3">{b.health.score}</span>
                        </span>
                        <Badge
                          tone={b.status === 'committed' ? 'good' : b.status === 'discarded' ? 'neutral' : 'warn'}
                          className="capitalize"
                        >
                          {b.status === 'validated' ? 'awaiting review' : b.status}
                        </Badge>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </TabsContent>
        <TabsContent value="trail" className="mt-4">
          <Card>
            <CardHeader
              title="Approved and rejected data changes"
              subtitle="From the append-only audit log: who changed what, from which value to which"
            />
            {!can('view_audit') ? (
              <CardBody className="text-sm text-ink-3">Your role cannot view the audit log.</CardBody>
            ) : changes.length === 0 ? (
              <EmptyState title="No data changes decided yet" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-surface-2 text-left text-xs text-ink-3">
                    <tr>
                      <th className="px-5 py-2">When</th>
                      <th className="px-3 py-2">Who</th>
                      <th className="px-3 py-2">Decision</th>
                      <th className="px-3 py-2">Change</th>
                      <th className="px-5 py-2">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {changes.map((e) => (
                      <tr key={e.id}>
                        <td className="whitespace-nowrap px-5 py-2 text-ink-3">{dateTime(e.at)}</td>
                        <td className="px-3 py-2">{e.actor}</td>
                        <td className="px-3 py-2">
                          <Badge tone={e.event.endsWith('approved') ? 'good' : 'neutral'}>
                            {e.event.endsWith('approved') ? 'Approved' : 'Rejected'}
                          </Badge>
                        </td>
                        <td className="px-3 py-2 text-ink-2">
                          {String(e.details.field)}: {String(e.details.before ?? '—')} → {String(e.details.after ?? '—')}
                        </td>
                        <td className="px-5 py-2 text-xs text-ink-3">{String(e.details.source)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </>
  )
}
