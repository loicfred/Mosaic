import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAuth } from '@/auth/AuthProvider'
import { ChartTooltipBox, LegendKey } from '@/charts/ChartTooltip'
import { HBarList } from '@/charts/HBarList'
import { axisTick, C } from '@/charts/theme'
import { PageHeader } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { ErrorState, PageSkeleton } from '@/components/ui/states'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { BeforeAfter } from '@/components/viz/BeforeAfter'
import { Meter } from '@/components/viz/Meter'
import { useBusiness, useMembers, useModels } from '@/hooks/queries'
import { api, ApiError } from '@/lib/api'
import { date, dateTime, mur } from '@/lib/format'

const f3 = (v: number | undefined) => (v === undefined || v === null ? '—' : v.toFixed(3))

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-line p-3">
      <div className="text-xs text-ink-3">{label}</div>
      <div className="tnum text-lg font-semibold text-ink">{value}</div>
      {hint && <div className="text-xs text-ink-3">{hint}</div>}
    </div>
  )
}

/** 0-1 scores as labelled meters. */
function ScoreBars({ rows }: { rows: [string, number, string][] }) {
  return (
    <ul className="space-y-3">
      {rows.map(([label, v, hint]) => (
        <li key={label}>
          <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
            <span className="text-ink-2">
              {label} <span className="text-xs text-ink-3">· {hint}</span>
            </span>
            <span className="tnum font-semibold text-ink">{f3(v)}</span>
          </div>
          <Meter value={v} max={1} tone="actual" size="sm" label={`${label} ${f3(v)}`} />
        </li>
      ))}
    </ul>
  )
}

function Confusion({ cm }: { cm: { tn: number; fp: number; fn: number; tp: number } }) {
  const cell = 'tnum px-3 py-2 text-center'
  return (
    <table className="text-sm">
      <caption className="pb-1 text-left text-xs text-ink-3">Confusion matrix (held-out test, at the HIGH threshold)</caption>
      <thead>
        <tr>
          <th />
          <th className="px-3 py-1 text-xs font-medium text-ink-3">Predicted no</th>
          <th className="px-3 py-1 text-xs font-medium text-ink-3">Predicted yes</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th className="pr-3 text-right text-xs font-medium text-ink-3">Actual no</th>
          <td className={`${cell} bg-good-bg`}>{cm.tn}</td>
          <td className={`${cell} bg-bad-bg`}>{cm.fp}</td>
        </tr>
        <tr>
          <th className="pr-3 text-right text-xs font-medium text-ink-3">Actual yes</th>
          <td className={`${cell} bg-bad-bg`}>{cm.fn}</td>
          <td className={`${cell} bg-good-bg`}>{cm.tp}</td>
        </tr>
      </tbody>
    </table>
  )
}

function ModelsTab() {
  const q = useModels()
  if (q.isLoading) return <PageSkeleton />
  if (q.error || !q.data) return <ErrorState error={q.error} />
  const cp = q.data.cash_pressure.metadata
  const an = q.data.anomaly.metadata
  const ca = q.data.categoriser.metadata
  const bm = q.data.provided_dataset_benchmark
  const bt = q.data.projection_backtest
  if (!cp?.test)
    return (
      <Card>
        <CardBody>Cash-pressure model not trained ({q.data.cash_pressure.detail}).</CardBody>
      </Card>
    )
  const calib = cp.test.calibration_bins.map((b: { mean_predicted: number; observed_rate: number }) => ({ ...b, ideal: b.mean_predicted }))
  const coefs = Object.entries(cp.explainability?.coefficients ?? {}).sort(
    (a, b) => Math.abs(b[1] as number) - Math.abs(a[1] as number),
  ) as [string, number][]
  const labels = Object.fromEntries(cp.features.map((f: { name: string; label: string }) => [f.name, f.label]))
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="30-day cash-pressure model"
          subtitle={`${cp.algorithm.replaceAll('_', '')} · ${cp.version} · trained ${dateTime(cp.trained_at)} · scikit-learn ${cp.sklearn_version}`}
          action={<Badge tone={q.data.cash_pressure.status === 'loaded' ? 'good' : 'bad'}>{q.data.cash_pressure.status}</Badge>}
        />
        <CardBody className="space-y-5 text-sm">
          <p className="text-ink-2">
            <strong className="text-ink">Target:</strong> {cp.target.definition}. {cp.target.eligibility}
          </p>
          <p className="text-ink-2">
            <strong className="text-ink">Training data:</strong> {cp.training_data.source}.{''}
            {cp.training_data.n_rows_eligible.toLocaleString('en-GB')} labelled business-dates from {cp.training_data.n_businesses}{''}
            synthetic businesses; {cp.training_data.n_test_businesses} businesses held out entirely for testing. Positive rate{''}
            {(cp.training_data.positive_rate_test * 100).toFixed(1)}% (test).
          </p>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <div>
              <h3 className="mb-3 font-medium">Model vs rule of thumb, on {cp.training_data.n_test_businesses} unseen businesses</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {[
                  ['ROC-AUC', cp.test.roc_auc, cp.baseline_test.roc_auc, 'buffer days only'],
                  ['PR-AUC', cp.test.pr_auc, cp.baseline_test.pr_auc, 'buffer days only'],
                  ['F1 at HIGH', cp.test.at_high_threshold.f1, cp.baseline_test.rule_buffer_lt_21_days.f1, 'buffer < 21 days'],
                ].map(([label, model, rule, ruleName]) => (
                  <div key={label as string} className="rounded-lg border border-line p-3">
                    <div className="mb-2 flex items-baseline justify-between">
                      <span className="text-xs text-ink-3">{label as string}</span>
                      <span className="tnum text-xs font-semibold text-good-ink">+{((model as number) - (rule as number)).toFixed(3)}</span>
                    </div>
                    <BeforeAfter
                      before={rule as number}
                      after={model as number}
                      max={1}
                      format={(v) => v.toFixed(3)}
                      beforeLabel="Rule"
                      afterLabel="Model"
                    />
                    <div className="mt-1.5 text-xs text-ink-3">rule: {ruleName as string}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 self-start">
              <Metric label="Precision @ HIGH" value={f3(cp.test.at_high_threshold.precision)} hint="flags that were right" />
              <Metric label="Recall @ HIGH" value={f3(cp.test.at_high_threshold.recall)} hint="cases it caught" />
              <Metric label="Brier score" value={f3(cp.test.brier)} hint="lower is better" />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div>
              <h3 className="mb-2 font-medium">Cross-validation (GroupKFold by business)</h3>
              <table className="w-full">
                <thead className="text-left text-xs text-ink-3">
                  <tr>
                    <th className="py-1">Candidate</th>
                    <th className="py-1 text-right">ROC-AUC</th>
                    <th className="py-1 text-right">PR-AUC</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {Object.entries(cp.cross_validation.candidates).map(([k, v]) => {
                    const r = v as { roc_auc_mean: number; roc_auc_std: number; pr_auc_oof: number }
                    return (
                      <tr key={k}>
                        <td className="py-1.5">
                          {k.replaceAll('_', '')}
                          {k === cp.algorithm && (
                            <Badge tone="accent" className="ml-1">
                              chosen
                            </Badge>
                          )}
                        </td>
                        <td className="tnum py-1.5 text-right">
                          {f3(r.roc_auc_mean)} ± {f3(r.roc_auc_std)}
                        </td>
                        <td className="tnum py-1.5 text-right">{f3(r.pr_auc_oof)}</td>
                      </tr>
                    )
                  })}
                  <tr>
                    <td className="py-1.5 text-ink-3">rule of thumb (buffer days only)</td>
                    <td className="tnum py-1.5 text-right text-ink-3">{f3(cp.cross_validation.baseline_buffer_days.roc_auc)}</td>
                    <td className="tnum py-1.5 text-right text-ink-3">{f3(cp.cross_validation.baseline_buffer_days.pr_auc)}</td>
                  </tr>
                </tbody>
              </table>
              <p className="mt-2 text-xs text-ink-3">{cp.cross_validation.selection_rule}</p>
              {cp.temporal_check?.roc_auc && (
                <p className="mt-2 text-xs text-ink-3">
                  Temporal check (train before {cp.temporal_check.train_until}, test after on unseen businesses): ROC-AUC{''}
                  {f3(cp.temporal_check.roc_auc)} vs rule {f3(cp.temporal_check.baseline_buffer_days.roc_auc)}.
                </p>
              )}
            </div>
            <div>
              <h3 className="mb-2 font-medium">Calibration</h3>
              <LegendKey
                items={[
                  { label: 'Observed rate', color: C.actual },
                  { label: 'Perfect calibration', color: C.projected, dashed: true },
                ]}
              />
              <div style={{ height: 180 }} className="mt-2" role="img" aria-label="Calibration: predicted probability vs observed rate">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={calib} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke={C.grid} vertical={false} />
                    <XAxis
                      dataKey="mean_predicted"
                      type="number"
                      domain={[0, 1]}
                      tickFormatter={(v) => `${Math.round(v * 100)}%`}
                      tick={axisTick}
                      tickLine={false}
                      axisLine={{ stroke: C.axis }}
                    />
                    <YAxis
                      domain={[0, 1]}
                      tickFormatter={(v) => `${Math.round(v * 100)}%`}
                      tick={axisTick}
                      tickLine={false}
                      axisLine={false}
                      width={40}
                    />
                    <Tooltip
                      content={({ active, payload }) =>
                        active && payload?.length ? (
                          <ChartTooltipBox
                            title={`Predicted ${Math.round(payload[0].payload.mean_predicted * 100)}%`}
                            format={(v) => `${(v * 100).toFixed(1)}%`}
                            rows={[{ name: 'observed', value: payload[0].payload.observed_rate, color: C.actual }]}
                          />
                        ) : null
                      }
                    />
                    <Line
                      dataKey="ideal"
                      stroke={C.projected}
                      strokeDasharray="4 3"
                      dot={false}
                      strokeWidth={1.5}
                      isAnimationActive={false}
                    />
                    <Line
                      dataKey="observed_rate"
                      stroke={C.actual}
                      strokeWidth={2}
                      dot={{ r: 4, fill: C.actual, stroke: '#fff', strokeWidth: 2 }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="space-y-3">
              <Confusion cm={cp.test.at_high_threshold.confusion_matrix} />
              <p className="text-xs text-ink-3">
                Bands: MODERATE ≥ {Math.round(cp.bands.moderate_threshold * 100)}%, HIGH ≥ {Math.round(cp.bands.high_threshold * 100)}%
                (HIGH maximises F1 on out-of-fold predictions).
              </p>
            </div>
          </div>
          <div>
            <h3 className="mb-2 font-medium">Features and learned weights (standardised log-odds)</h3>
            <ul className="grid grid-cols-1 gap-x-8 gap-y-1 md:grid-cols-2">
              {coefs.map(([f, c]) => (
                <li key={f} className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-ink-2" title={labels[f]}>
                    {labels[f]}
                  </span>
                  <span className="tnum w-14 text-right text-xs">
                    {c > 0 ? '+' : ''}
                    {c.toFixed(2)}
                  </span>
                  <span className="h-1.5 w-24 rounded-full bg-brand-50">
                    <span
                      className="block h-full rounded-full"
                      style={{
                        width: `${Math.min(100, (Math.abs(c) / Math.abs(coefs[0][1])) * 100)}%`,
                        background: c > 0 ? 'var(--color-serious)' : 'var(--color-actual)',
                      }}
                    />
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-ink-3">
              Positive weights raise the risk. Each prediction shows its own per-feature contributions: weight × standardised value.
            </p>
          </div>
          <div>
            <h3 className="mb-1 font-medium">Limitations</h3>
            <ul className="list-disc space-y-0.5 pl-5 text-ink-3">
              {cp.limitations.map((l: string) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>
        </CardBody>
      </Card>

      {bm && (
        <Card>
          <CardHeader
            title="Benchmark on the hackathon-provided dataset"
            subtitle={`${bm.dataset} · ${bm.rows} rows · ${(bm.positive_rate * 100).toFixed(1)}% positive · ${bm.scheme}`}
          />
          <CardBody className="space-y-3 text-sm">
            <div className="max-w-2xl">
              <HBarList
                rows={Object.entries(bm.models).map(([k, v]) => ({
                  label: k.replaceAll('_', ''),
                  value: (v as { roc_auc_mean: number }).roc_auc_mean,
                }))}
                format={(v) => v.toFixed(3)}
                max={1}
                color={C.before}
              />
              <p className="mt-2 text-xs text-ink-3">
                ROC-AUC on a 0-1 scale: 0.5 is a coin flip, 1.0 is perfect. Our model on held-out synthetic businesses:{''}
                {f3(cp.test.roc_auc)}.
              </p>
            </div>
            <p className="text-ink-2">{bm.finding}</p>
          </CardBody>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader title="Unusual payments" subtitle={`${an.algorithm} + rule + materiality`} />
          <CardBody className="space-y-3 text-sm">
            <ScoreBars
              rows={[
                ['Precision', an.production_flags_test.precision, 'flags that were real'],
                ['Recall', an.production_flags_test.recall, 'injected anomalies caught'],
                ['F1', an.production_flags_test.f1, 'balance of both'],
              ]}
            />
            <p className="text-ink-3">
              {an.production_rule}. Tested on {an.training_data.n_test_businesses} held-out synthetic businesses with injected anomalies.
              Model alone: F1 {f3(an.test.f1)}, ROC-AUC {f3(an.test.roc_auc)}. Duplicate rule recall:{''}
              {f3(an.duplicate_rule.recall_injected_duplicates)}.
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Category suggestions" subtitle={ca.algorithm} />
          <CardBody className="space-y-3 text-sm">
            <ScoreBars
              rows={[
                ['Hand-written set', ca.test_handwritten_ood.accuracy, `accuracy, n=${ca.test_handwritten_ood.n} - the honest number`],
                ['Synthetic set', ca.test_in_distribution.accuracy, 'templated text, optimistic'],
              ]}
            />
            <p className="text-ink-3">
              The hand-written set is never used for training and is the honest number. Suggestions always need approval.
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Cash projection back-test" subtitle="Deterministic projection vs what actually happened" />
          <CardBody className="space-y-3 text-sm">
            <Metric
              label="Median 30-day error"
              value={
                bt.median_abs_error_pct_of_monthly_outflow !== null ? `${bt.median_abs_error_pct_of_monthly_outflow.toFixed(1)}%` : '—'
              }
              hint="of monthly outflows, this business"
            />
            <ul className="space-y-0.5 text-xs text-ink-3">
              {bt.points.slice(0, 5).map((p: { cut: string; predicted: number; actual: number }) => (
                <li key={p.cut}>
                  From {date(p.cut)}: projected {mur(p.predicted)}, actual {mur(p.actual)}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>
      <Card>
        <CardHeader title="Data provenance" />
        <CardBody className="text-sm text-ink-2">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>Synthetic demo dataset:</strong> the businesses in this app (Coastal Home &amp; Kitchen, Tamarind Cafe) are fictional,
              generated by <code>scripts/seed_demo.py</code>.
            </li>
            <li>
              <strong>Synthetic training panel:</strong> 210 fictional SMEs across 7 archetypes (<code>scripts/generate_synthetic.py</code>
              ), used to train and evaluate all three models.
            </li>
            <li>
              <strong>Hackathon-provided dataset:</strong> <code>data/public/small_business_cashflow.csv</code>, used only as an external
              benchmark (above).
            </li>
            <li>
              <strong>Model-generated values:</strong> probabilities, anomaly flags and category suggestions are labelled wherever they
              appear.
            </li>
          </ul>
        </CardBody>
      </Card>
    </div>
  )
}

function ProfileTab() {
  const { me } = useAuth()
  const [cur, setCur] = useState('')
  const [next, setNext] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  async function submit(e: FormEvent) {
    e.preventDefault()
    try {
      await api('/auth/change-password', { method: 'POST', body: { current_password: cur, new_password: next } })
      setMsg({ ok: true, text: 'Password changed. Other sessions were signed out.' })
      setCur('')
      setNext('')
    } catch (err) {
      setMsg({ ok: false, text: err instanceof ApiError ? err.message : 'Could not change password.' })
    }
  }
  const field = 'mt-1 h-9 w-full rounded-lg border border-line-strong px-3 text-sm outline-none focus:border-accent-600'
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card>
        <CardHeader title="Your account" />
        <CardBody>
          <dl className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
            <dt className="text-ink-3">Name</dt>
            <dd>{me?.full_name}</dd>
            <dt className="text-ink-3">Email</dt>
            <dd>{me?.email}</dd>
            <dt className="text-ink-3">Role</dt>
            <dd className="capitalize">{me?.role}</dd>
            <dt className="text-ink-3">Permissions</dt>
            <dd className="flex flex-wrap gap-1">
              {me?.permissions.map((p) => (
                <Badge key={p} tone="accent">
                  {p.replaceAll('_', '')}
                </Badge>
              ))}
            </dd>
          </dl>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Change password" subtitle="At least 12 characters. Changing it signs out your other sessions." />
        <CardBody>
          <form onSubmit={submit} className="space-y-3">
            <label className="block text-sm">
              Current password
              <input
                type="password"
                autoComplete="current-password"
                value={cur}
                onChange={(e) => setCur(e.target.value)}
                className={field}
              />
            </label>
            <label className="block text-sm">
              New password
              <input
                type="password"
                autoComplete="new-password"
                minLength={12}
                value={next}
                onChange={(e) => setNext(e.target.value)}
                className={field}
              />
            </label>
            {msg && (
              <p role="status" className={msg.ok ? 'text-sm text-good-ink' : 'text-sm text-bad-ink'}>
                {msg.text}
              </p>
            )}
            <Button type="submit" disabled={!cur || next.length < 12}>
              Update password
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}

function BusinessTab() {
  const { can } = useAuth()
  const b = useBusiness()
  const m = useMembers(can('view_members'))
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card>
        <CardHeader title="Business" />
        <CardBody>
          {b.data && (
            <dl className="grid grid-cols-[150px_1fr] gap-y-2 text-sm">
              <dt className="text-ink-3">Name</dt>
              <dd>{b.data.name}</dd>
              <dt className="text-ink-3">Sector</dt>
              <dd>{b.data.sector}</dd>
              <dt className="text-ink-3">Currency</dt>
              <dd>{b.data.currency}</dd>
              <dt className="text-ink-3">Opening balance</dt>
              <dd>
                {mur(b.data.opening_cash)} on {date(b.data.opening_date)}
              </dd>
              <dt className="text-ink-3">Records</dt>
              <dd>
                {b.data.transactions.toLocaleString('en-GB')} transactions · {b.data.invoices} invoices
              </dd>
              <dt className="text-ink-3">Data label</dt>
              <dd>{b.data.data_label === 'synthetic_demo' ? 'Synthetic demo data (fictional business)' : 'Business data'}</dd>
            </dl>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Team" subtitle="Roles are enforced by the API on every request" />
        {!can('view_members') ? (
          <CardBody className="text-sm text-ink-3">Only the business owner can see the team list.</CardBody>
        ) : (
          <ul className="divide-y divide-line">
            {m.data?.map((u) => (
              <li key={u.email} className="flex items-center justify-between px-5 py-3 text-sm">
                <div>
                  <div className="font-medium">{u.name}</div>
                  <div className="text-xs text-ink-3">{u.email}</div>
                </div>
                <Badge className="capitalize">{u.role}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

export function SettingsPage() {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') ?? 'profile'
  return (
    <>
      <PageHeader title="Settings" description="Account, business and the evaluation behind every model in the product." />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v })}>
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="business">Business &amp; team</TabsTrigger>
          <TabsTrigger value="models">Models &amp; data</TabsTrigger>
        </TabsList>
        <TabsContent value="profile" className="mt-4">
          <ProfileTab />
        </TabsContent>
        <TabsContent value="business" className="mt-4">
          <BusinessTab />
        </TabsContent>
        <TabsContent value="models" className="mt-4">
          <ModelsTab />
        </TabsContent>
      </Tabs>
    </>
  )
}
