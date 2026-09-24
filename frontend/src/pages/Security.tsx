import { CheckCircle2, ChevronDown, Cpu, Database, FileSearch, KeyRound, Lock, Server, ShieldAlert, ShieldCheck, Users } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/auth/AuthProvider'
import { PageHeader } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { EmptyState, ErrorState, PageSkeleton } from '@/components/ui/states'
import { CompositionBar } from '@/components/viz/CompositionBar'
import { useAudit, useSecuritySummary } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { dateTime } from '@/lib/format'

function Control({
  icon: Icon,
  title,
  headline,
  rows,
  ok = true,
}: {
  icon: typeof Lock
  title: string
  headline: string
  rows: [string, React.ReactNode][]
  ok?: boolean
}) {
  return (
    <Card className="flex flex-col">
      <div className="flex items-start gap-3 p-4">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent-50 text-accent-700" aria-hidden>
          <Icon className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <h2 className="text-sm font-semibold text-ink">{title}</h2>
            {ok ? (
              <CheckCircle2 className="size-4 text-good" aria-label="In place" />
            ) : (
              <ShieldAlert className="size-4 text-bad" aria-label="Needs attention" />
            )}
          </div>
          <p className="mt-0.5 text-sm text-ink-2">{headline}</p>
        </div>
      </div>
      <details className="group mt-auto border-t border-line">
        <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2 text-xs font-medium text-ink-3 hover:bg-surface-2 hover:text-ink">
          Details
          <ChevronDown className="size-3.5 transition-transform group-open:rotate-180" aria-hidden />
        </summary>
        <dl className="space-y-2 px-4 pb-4 pt-1 text-sm">
          {rows.map(([k, v]) => (
            <div key={k} className="grid grid-cols-[120px_1fr] gap-3">
              <dt className="text-ink-3">{k}</dt>
              <dd className="text-ink">{v}</dd>
            </div>
          ))}
        </dl>
      </details>
    </Card>
  )
}

export function SecurityPage() {
  const s = useSecuritySummary()
  const { can } = useAuth()
  const [cat, setCat] = useState('')
  const events = useAudit(cat || undefined, can('view_audit'))
  if (s.isLoading) return <PageSkeleton />
  if (s.error || !s.data) return <ErrorState error={s.error} onRetry={() => s.refetch()} />
  const d = s.data
  const ti = d.tenant_isolation
  return (
    <>
      <PageHeader
        title="Security & Audit"
        description="Controls read live from the running system. Only implemented controls are listed."
      />
      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card
          className={cn('flex items-center gap-4 p-5 lg:col-span-2', ti.rls_effective_for_app_role ? 'border-good/30' : 'border-bad/30')}
        >
          <span
            className={cn(
              'flex size-12 shrink-0 items-center justify-center rounded-xl',
              ti.rls_effective_for_app_role ? 'bg-good-bg text-good-ink' : 'bg-bad-bg text-bad-ink',
            )}
            aria-hidden
          >
            {ti.rls_effective_for_app_role ? <ShieldCheck className="size-6" /> : <ShieldAlert className="size-6" />}
          </span>
          <div className="min-w-0">
            <p className="text-base font-semibold text-ink">
              {ti.rls_effective_for_app_role
                ? 'Tenant isolation enforced in the database'
                : 'Row-level security not enforced for this DB role'}
            </p>
            <p className="text-sm text-ink-3">
              {ti.rls_tables_protected} tenant tables protected by PostgreSQL row-level security. {ti.note}
            </p>
          </div>
        </Card>
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-ink">Audit events, last 7 days</h2>
          <CompositionBar
            className="mt-3"
            label="Audit events in the last 7 days by outcome"
            format={(v) => String(v)}
            segments={[
              {
                key: 'success',
                label: 'Success',
                value: d.audit.events_last_7_days.success ?? 0,
                color: 'var(--color-good)',
                icon: <CheckCircle2 className="size-3.5 text-good" aria-hidden />,
              },
              {
                key: 'denied',
                label: 'Denied',
                value: d.audit.events_last_7_days.denied ?? 0,
                color: 'var(--color-bad)',
                icon: <ShieldAlert className="size-3.5 text-bad" aria-hidden />,
              },
              {
                key: 'failure',
                label: 'Failed',
                value: d.audit.events_last_7_days.failure ?? 0,
                color: 'var(--color-warn)',
                icon: <ShieldAlert className="size-3.5 text-warn-ink" aria-hidden />,
              },
            ]}
          />
        </Card>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Control
          icon={KeyRound}
          title="Authentication"
          headline={`Argon2id passwords, ${d.authentication.access_token_minutes}-minute tokens, rotating refresh, lockout`}
          rows={[
            ['Passwords', d.authentication.password_hashing],
            ['Access token', `${d.authentication.access_token_minutes}-minute JWT, kept in memory only`],
            ['Refresh token', d.authentication.refresh_token],
            ['Lockout', d.authentication.lockout],
            ['Login rate limit', d.authentication.login_rate_limit],
          ]}
        />
        <Control
          icon={Users}
          title="Authorisation"
          headline={`Roles checked on every API call: ${d.authorization.roles.join(', ')}`}
          rows={[
            ['Model', `${d.authorization.model}: ${d.authorization.roles.join(', ')}`],
            [
              'Your role',
              <span key="role" className="capitalize">
                {d.authorization.your_role}
              </span>,
            ],
            ['Enforced', d.authorization.enforced_in],
          ]}
        />
        <Control
          icon={Database}
          title="Tenant isolation"
          ok={ti.rls_effective_for_app_role}
          headline="Each business sees only its own rows - enforced in the app and in PostgreSQL"
          rows={[
            ['Application', ti.app_layer],
            ['Database', ti.database_layer],
            ['Status', ti.rls_effective_for_app_role ? 'Effective for the application role' : 'Not effective (see note)'],
          ]}
        />
        <Control
          icon={FileSearch}
          title="Input validation"
          headline="Strict schemas, safe CSV parsing, parameterised SQL"
          rows={[
            ['API', d.input_validation.api],
            ['CSV uploads', d.input_validation.csv],
            ['SQL', d.input_validation.sql],
          ]}
        />
        <Control
          icon={Server}
          title="API security"
          headline={`Security headers, allow-listed origins, ${d.api.api_rate_limit}`}
          rows={[
            ['Versioning', d.api.versioned_prefix],
            ['CORS', d.api.cors_origins.join(', ')],
            ['Headers', d.api.security_headers.join(', ')],
            ['Rate limit', d.api.api_rate_limit],
            ['Errors', d.api.errors],
          ]}
        />
        <Control
          icon={Lock}
          title="Data protection"
          headline="Tokens and IPs stored only as hashes; no external AI"
          rows={[
            ['Stored secrets', d.data_protection.stored_secrets],
            ['Audit IPs', d.data_protection.audit_ip],
            ['External AI', d.data_protection.external_ai],
            ['HTTPS', d.data_protection.https],
            ['At rest', d.data_protection.at_rest],
          ]}
        />
        <Control
          icon={Cpu}
          title="Models & audit"
          headline="Local models only; audit log cannot be edited or deleted"
          rows={[
            ['Models', `cash pressure: ${d.models.cash_pressure} · anomaly: ${d.models.anomaly} · categoriser: ${d.models.categoriser}`],
            ['Audit log', d.audit.append_only],
            [
              'Last 7 days',
              Object.entries(d.audit.events_last_7_days)
                .map(([k, v]) => `${v} ${k}`)
                .join(' · ') || 'no events',
            ],
            ['Environment', d.environment],
          ]}
        />
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Audit trail"
          subtitle="Sign-ins, authorisation failures, data access, imports, data changes and opportunity decisions. Never contains passwords or tokens."
          action={
            can('view_audit') && (
              <select
                value={cat}
                onChange={(e) => setCat(e.target.value)}
                className="h-8 rounded-md border border-line-strong px-2 text-sm"
                aria-label="Event category"
              >
                <option value="">All events</option>
                <option value="auth">Sign-in</option>
                <option value="access">Access</option>
                <option value="data">Data</option>
                <option value="opportunity">Opportunities</option>
                <option value="security">Security</option>
              </select>
            )
          }
        />
        {!can('view_audit') ? (
          <CardBody className="text-sm text-ink-3">
            Only owners and accountants can view the audit trail. This restriction is enforced by the API.
          </CardBody>
        ) : events.error ? (
          <div className="p-5">
            <ErrorState error={events.error} />
          </div>
        ) : events.data?.length === 0 ? (
          <EmptyState title="No events" />
        ) : (
          <div className="max-h-[520px] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-2 text-left text-xs text-ink-3">
                <tr>
                  <th className="px-5 py-2">When</th>
                  <th className="px-3 py-2">Event</th>
                  <th className="px-3 py-2">Outcome</th>
                  <th className="px-3 py-2">Actor</th>
                  <th className="px-5 py-2">Context</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {events.data?.map((e) => (
                  <tr key={e.id}>
                    <td className="whitespace-nowrap px-5 py-2 text-ink-3">{dateTime(e.at)}</td>
                    <td className="px-3 py-2 font-mono text-xs text-ink">{e.event}</td>
                    <td className="px-3 py-2">
                      <Badge tone={e.outcome === 'success' ? 'good' : e.outcome === 'denied' ? 'bad' : 'warn'}>
                        {e.outcome === 'success' ? <CheckCircle2 /> : <ShieldAlert />} {e.outcome}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-ink-2">{e.actor ?? 'system'}</td>
                    <td className="max-w-md truncate px-5 py-2 text-xs text-ink-3" title={JSON.stringify(e.details)}>
                      {e.resource_type ? `${e.resource_type} · ` : ''}
                      {Object.entries(e.details)
                        .slice(0, 3)
                        .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
                        .join(' · ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
