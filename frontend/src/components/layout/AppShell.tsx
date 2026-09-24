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
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { ValoraLogo } from '@/components/brand/ValoraLogo'
import { InsightLauncher, InsightPanel } from '@/components/insight/InsightPanel'
import { InsightProvider } from '@/components/insight/InsightProvider'
import { PageSkeleton } from '@/components/ui/states'
import { Tip } from '@/components/ui/tooltip'
import { useOpportunities, useOverview } from '@/hooks/queries'
import { AccessibilityMenu } from './AccessibilityMenu'
import { cn } from '@/lib/cn'
import { date } from '@/lib/format'

type NavItem = { to: string; label: string; icon: typeof LayoutDashboard; end?: boolean; count?: 'opps' | 'data' }
const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: 'Understand',
    items: [
      { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
      { to: '/insights', label: 'Financial insights', icon: BarChart3 },
      { to: '/transactions', label: 'Transactions', icon: ListOrdered },
    ],
  },
  {
    group: 'Decide',
    items: [
      { to: '/opportunities', label: 'Opportunities', icon: Target, count: 'opps' },
      { to: '/scenarios', label: 'Scenario lab', icon: FlaskConical },
      { to: '/reports', label: 'Reports', icon: FileText },
    ],
  },
  {
    group: 'Trust',
    items: [
      { to: '/data-health', label: 'Data health', icon: Database, count: 'data' },
      { to: '/security', label: 'Security & audit', icon: ShieldCheck },
    ],
  },
]

function initials(name?: string) {
  return (name ?? '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('')
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
          'flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors duration-150',
          isActive ? 'bg-accent-100 font-medium text-accent-600' : 'text-ink-2 hover:bg-mist hover:text-ink',
        )
      }
    >
      {({ isActive }) => (
        <>
          <n.icon className={cn('size-4 shrink-0', isActive ? 'text-accent-600' : 'text-ink-3')} aria-hidden />
          <span className="flex-1 truncate">{n.label}</span>
          {count && count.value > 0 && (
            <span
              className={cn('tnum text-xs font-medium', count.tone === 'warn' ? 'text-warn-ink' : 'text-ink-3')}
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
  const { me, signOut } = useAuth()
  const opps = useOpportunities()
  const ov = useOverview()
  const newCount = opps.data?.filter((o) => o.status === 'new' && o.is_active).length ?? 0
  const issues = ov.data?.data_health.issues ?? 0
  const counts = {
    opps: { value: newCount, tone: 'ink' as const, label: `${newCount} new findings` },
    data: { value: issues, tone: 'warn' as const, label: `${issues} data items to review` },
  }
  return (
    <nav aria-label="Main" className="flex h-full flex-col border-r border-line bg-surface px-3">
      <div className="flex h-14 shrink-0 items-center px-2.5">
        <ValoraLogo size="sm" />
      </div>
      <div className="mt-2 flex flex-col gap-5 overflow-y-auto">
        {NAV.map((g) => (
          <div key={g.group}>
            <div className="mb-1 px-2.5 text-xs text-ink-3">{g.group}</div>
            <ul className="flex flex-col gap-px">
              {g.items.map((n) => (
                <li key={n.to}>
                  <NavRow n={n} count={n.count ? counts[n.count] : undefined} onNavigate={onNavigate} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mt-auto border-t border-line py-3">
        <NavRow n={{ to: '/settings', label: 'Settings', icon: Settings }} onNavigate={onNavigate} />
        <div className="mt-2 flex items-center gap-2.5 px-2.5 py-1">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-mist text-xs font-medium text-ink-2" aria-hidden>
            {initials(me?.full_name)}
          </span>
          <span className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-sm text-ink">{me?.full_name}</span>
            <span className="block text-xs capitalize text-ink-3">{me?.role}</span>
          </span>
          <Tip content="Sign out">
            <button
              onClick={() => signOut()}
              className="flex size-8 items-center justify-center rounded-md text-ink-3 transition-colors hover:bg-mist hover:text-ink"
              aria-label="Sign out"
            >
              <LogOut className="size-4" aria-hidden />
            </button>
          </Tip>
        </div>
      </div>
    </nav>
  )
}

export function AppShell() {
  const { me } = useAuth()
  const ov = useOverview()
  const [open, setOpen] = useState(false)
  const synthetic = me?.business.data_label === 'synthetic_demo'
  return (
    <InsightProvider key={me?.business.id} businessName={me?.business.name ?? 'your business'}>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-ink focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-surface"
      >
        Skip to main content
      </a>
      <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
        <aside className="no-print hidden lg:sticky lg:top-0 lg:block lg:h-screen">
          <Sidebar />
        </aside>
        {open && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 bg-ink/20" onClick={() => setOpen(false)} />
            <div className="panel-in shadow-float absolute inset-y-0 left-0 w-64">
              <Sidebar onNavigate={() => setOpen(false)} />
            </div>
          </div>
        )}
        <div className="relative min-w-0">
          <header className="no-print sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface px-4 md:px-6">
            <button
              className="flex size-9 items-center justify-center rounded-md border border-line text-ink-2 hover:bg-mist hover:text-ink lg:hidden"
              onClick={() => setOpen(!open)}
              aria-label={open ? 'Close navigation' : 'Open navigation'}
              aria-expanded={open}
            >
              {open ? <X className="size-4" /> : <Menu className="size-4" />}
            </button>
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-ink">{me?.business.name}</div>
                <div className="truncate text-xs text-ink-3">
                  {me?.business.sector} · {me?.business.currency}
                  {ov.data && (
                    <>
                      {' · '}data to <span className="font-mono">{date(ov.data.as_of)}</span>
                    </>
                  )}
                </div>
              </div>
              {synthetic && (
                <Tip content="This tenant uses a synthetic, fictional demo ledger generated by scripts/seed_demo.py. It is not real business data.">
                  <span tabIndex={0} className="hidden shrink-0 cursor-help rounded bg-mist px-1.5 py-0.5 text-xs text-ink-2 sm:inline-flex">
                    Synthetic demo data
                  </span>
                </Tip>
              )}
            </div>
            <div className="flex items-center gap-2">
              <InsightLauncher />
              <AccessibilityMenu />
            </div>
          </header>
          <main
            id="main-content"
            tabIndex={-1}
            className="print-full relative mx-auto max-w-[1280px] px-4 pb-12 pt-6 outline-none md:px-6 md:pt-8"
          >
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>
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
  /** Context line under the description, e.g. the data date. */
  meta?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-ink">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-ink-3">{description}</p>}
        {meta && <p className="mt-1 text-xs text-ink-3">{meta}</p>}
      </div>
      {actions && <div className="no-print flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
