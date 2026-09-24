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
          'group relative flex min-h-10 items-center gap-3 rounded-full px-4 py-2 text-sm transition-colors',
          isActive ? 'bg-accent-600 font-semibold text-white' : 'text-ink-2 hover:bg-accent-50 hover:text-ink',
        )
      }
    >
      {({ isActive }) => (
        <>
          <n.icon
            className={cn('size-[18px] shrink-0', isActive ? 'text-white' : 'text-ink-3')}
            strokeWidth={isActive ? 2.2 : 1.8}
            aria-hidden
          />
          <span className="flex-1">{n.label}</span>
          {count && count.value > 0 && (
            <span
              className={cn(
                'tnum min-w-5 rounded-full px-1.5 text-center text-xs font-medium leading-5',
                count.tone === 'warn' ? 'bg-warn-bg text-warn-ink' : 'bg-ink/[0.06] text-ink-2',
                'group-aria-[current=page]:bg-white/15 group-aria-[current=page]:text-white',
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
    <nav aria-label="Main" className="flex h-full flex-col border-r border-white/80 bg-white/70 px-4 py-6">
      <Logo />
      <div className="mt-7 flex flex-col gap-6">
        {NAV.map((g) => (
          <div key={g.group}>
            <div className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-ink-3">{g.group}</div>
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
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-xl focus:bg-ink focus:px-4 focus:py-2.5 focus:text-sm focus:font-medium focus:text-white"
      >
        Skip to main content
      </a>
      <div className="min-h-screen lg:grid lg:grid-cols-[15.5rem_1fr]">
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
        <div className="relative min-w-0">
          <header className="app-bg no-print sticky top-0 z-30 flex h-16 items-center gap-3 px-4 md:px-8">
            <button
              className="flex size-10 items-center justify-center rounded-full border border-line bg-surface text-ink-2 hover:text-ink lg:hidden"
              onClick={() => setOpen(!open)}
              aria-label={open ? 'Close navigation' : 'Open navigation'}
              aria-expanded={open}
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
                  <span
                    tabIndex={0}
                    className="inline-flex shrink-0 cursor-help items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-xs text-ink-2"
                  >
                    <span className="size-1.5 rounded-full bg-gold-500" aria-hidden />
                    <span className="hidden sm:inline">Synthetic demo data</span>
                    <span className="sm:hidden">Demo</span>
                  </span>
                </Tip>
              )}
            </div>
            <div className="flex items-center gap-2">
              <AccessibilityMenu />
              <div className="hidden items-center gap-2.5 rounded-full border border-line bg-surface py-1 pl-1 pr-4 sm:flex">
                <span
                  className="flex size-8 items-center justify-center rounded-full bg-periwinkle-100 text-xs font-semibold text-accent-700"
                  aria-hidden
                >
                  {initials(me?.full_name)}
                </span>
                <span className="leading-tight">
                  <span className="block text-sm font-medium text-ink">{me?.full_name}</span>
                  <span className="block text-xs capitalize text-ink-3">{me?.role}</span>
                </span>
              </div>
              <button
                onClick={() => signOut()}
                className="flex size-10 items-center justify-center rounded-full border border-line bg-surface text-ink-2 transition-colors hover:border-accent-500 hover:text-ink"
                aria-label="Sign out"
                title="Sign out"
              >
                <LogOut className="size-4" aria-hidden />
              </button>
            </div>
          </header>
          <main
            id="main-content"
            tabIndex={-1}
            key={loc.pathname}
            className="fade-up print-full relative mx-auto max-w-[1360px] px-4 pb-28 pt-6 outline-none md:px-8 md:pb-28 md:pt-8"
          >
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
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {meta && <div className="mb-2 text-xs font-medium text-ink-3">{meta}</div>}
        <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.02em] text-ink md:text-[30px]">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-[15px] leading-relaxed text-ink-3">{description}</p>}
      </div>
      {actions && <div className="no-print flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
