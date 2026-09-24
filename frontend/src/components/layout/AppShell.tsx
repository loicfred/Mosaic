import {
  BarChart3,
  Database,
  FileText,
  FlaskConical,
  LayoutDashboard,
  ListOrdered,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Target,
  X,
} from 'lucide-react'
import { Suspense, useState, type ReactNode } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { ValoraLogo, ValoraMark } from '@/components/brand/ValoraLogo'
import { InsightLauncher, InsightPanel } from '@/components/insight/InsightPanel'
import { InsightProvider } from '@/components/insight/InsightProvider'
import { Badge } from '@/components/ui/badge'
import { PageSkeleton } from '@/components/ui/states'
import { Tip } from '@/components/ui/tooltip'
import { useOpportunities, useOverview } from '@/hooks/queries'
import { cn } from '@/lib/cn'
import { date } from '@/lib/format'

type NavItem = { to: string; label: string; icon: typeof LayoutDashboard; end?: boolean; count?: 'opps' | 'data' }
const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: 'Understand',
    items: [
      { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
      { to: '/insights', label: 'Financial Insights', icon: BarChart3 },
      { to: '/transactions', label: 'Transactions', icon: ListOrdered },
    ],
  },
  {
    group: 'Decide',
    items: [
      { to: '/opportunities', label: 'Opportunities', icon: Target, count: 'opps' },
      { to: '/scenarios', label: 'Scenario Lab', icon: FlaskConical },
      { to: '/reports', label: 'Reports', icon: FileText },
    ],
  },
  {
    group: 'Trust',
    items: [
      { to: '/data-health', label: 'Data Health', icon: Database, count: 'data' },
      { to: '/security', label: 'Security & Audit', icon: ShieldCheck },
    ],
  },
]

function Logo() {
  return (
    <div className="px-3">
      <ValoraLogo size="md" />
    </div>
  )
}

function NavRow({
  n,
  count,
  onNavigate,
}: {
  n: NavItem
  count?: { value: number; tone: 'ink' | 'warn'; label: string }
  onNavigate?: () => void
}) {
  return (
    <NavLink
      to={n.to}
      end={n.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
          isActive
            ? 'bg-accent-50 font-semibold text-accent-700 before:absolute before:inset-y-2 before:-left-3 before:w-[3px] before:rounded-r-full before:bg-accent-500'
            : 'text-ink-2 hover:bg-ink/[0.04] hover:text-ink',
        )
      }
    >
      {({ isActive }) => (
        <>
          <n.icon
            className={cn('size-[18px]', isActive ? 'text-accent-600' : 'text-ink-3')}
            strokeWidth={isActive ? 2.2 : 1.8}
            aria-hidden
          />
          <span className="flex-1">{n.label}</span>
          {count && count.value > 0 && (
            <span
              className={cn(
                'tnum min-w-5 rounded-full px-1.5 text-center text-[11px] font-semibold leading-5',
                count.tone === 'warn' ? 'bg-warn-bg text-warn-ink' : 'bg-accent-600 text-white',
              )}
              aria-label={count.label}
            >
              {count.value}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const opps = useOpportunities()
  const ov = useOverview()
  const newCount = opps.data?.filter((o) => o.status === 'new' && o.is_active).length ?? 0
  const issues = ov.data?.data_health.issues ?? 0
  const counts = {
    opps: { value: newCount, tone: 'ink' as const, label: `${newCount} new findings` },
    data: { value: issues, tone: 'warn' as const, label: `${issues} data items to review` },
  }
  return (
    <nav aria-label="Main" className="flex h-full flex-col border-r border-line bg-surface px-3 py-5">
      <Logo />
      <div className="mt-7 flex flex-col gap-6">
        {NAV.map((g) => (
          <div key={g.group}>
            <div className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-ink-3">{g.group}</div>
            <ul className="flex flex-col gap-0.5">
              {g.items.map((n) => (
                <li key={n.to}>
                  <NavRow n={n} count={n.count ? counts[n.count] : undefined} onNavigate={onNavigate} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mt-auto border-t border-line pt-3">
        <NavRow n={{ to: '/settings', label: 'Settings', icon: Settings }} onNavigate={onNavigate} />
        <p className="mt-3 px-3 text-[11px] leading-relaxed text-ink-3">
          Facts come from a deterministic engine. Predictions and simulations are labelled.
        </p>
      </div>
    </nav>
  )
}

export function AppShell() {
  const { me, signOut } = useAuth()
  const ov = useOverview()
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  const synthetic = me?.business.data_label === 'synthetic_demo'
  return (
    <InsightProvider key={me?.business.id} businessName={me?.business.name ?? 'your business'}>
      <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
        <aside className="no-print hidden lg:sticky lg:top-0 lg:block lg:h-screen">
          <Sidebar />
        </aside>
        {open && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 bg-ink/30" onClick={() => setOpen(false)} />
            <div className="absolute inset-y-0 left-0 w-64">
              <Sidebar onNavigate={() => setOpen(false)} />
            </div>
          </div>
        )}
        <div className="min-w-0">
          <header className="no-print sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-page px-4 md:px-8">
            <button
              className="rounded-md p-1.5 text-ink-2 hover:bg-brand-50 lg:hidden"
              onClick={() => setOpen(!open)}
              aria-label="Open navigation"
            >
              {open ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
            <ValoraMark className="size-7 lg:hidden" orbit={false} title="Valora" />
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-ink">{me?.business.name}</div>
                <div className="truncate text-xs text-ink-3">
                  {me?.business.sector} · {me?.business.currency}
                  {ov.data && <> · data to {date(ov.data.as_of)}</>}
                </div>
              </div>
              {synthetic && (
                <Tip content="This tenant uses a synthetic, fictional demo ledger generated by scripts/seed_demo.py. It is not real business data.">
                  <span>
                    <Badge tone="warn" className="hidden cursor-help sm:inline-flex">
                      Synthetic demo data
                    </Badge>
                  </span>
                </Tip>
              )}
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden text-right sm:block">
                <div className="text-sm font-medium text-ink">{me?.full_name}</div>
                <div className="text-xs capitalize text-ink-3">{me?.role}</div>
              </div>
              <button
                onClick={() => signOut()}
                className="rounded-md p-2 text-ink-3 hover:bg-brand-50 hover:text-ink"
                aria-label="Sign out"
                title="Sign out"
              >
                <LogOut className="size-4" />
              </button>
            </div>
          </header>
          <main key={loc.pathname} className="fade-up print-full mx-auto max-w-[1320px] px-4 pb-28 pt-8 md:px-8 md:pb-28 md:pt-10">
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>
      <InsightLauncher />
      <InsightPanel businessName={me?.business.name ?? 'your business'} />
    </InsightProvider>
  )
}

export function PageHeader({
  title,
  description,
  actions,
  meta,
}: {
  title: string
  description?: ReactNode
  actions?: ReactNode
  /** Small context line above the title, e.g. the data date. */
  meta?: ReactNode
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {meta && <div className="mb-2 text-xs font-medium text-ink-3">{meta}</div>}
        <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.02em] text-ink md:text-[30px]">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-[15px] leading-relaxed text-ink-3">{description}</p>}
      </div>
      {actions && <div className="no-print flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
