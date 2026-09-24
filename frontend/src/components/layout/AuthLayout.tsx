import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { ValoraLogo } from '@/components/brand/ValoraLogo'
import { cn } from '@/lib/cn'

const tab = 'rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150'

/** Sign-in and sign-up frame: the logo, a small account switch, and the form in one bordered panel. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-page">
      <header className="flex h-14 items-center justify-between gap-3 border-b border-line bg-surface px-4 sm:px-6">
        <ValoraLogo size="sm" />
        <nav aria-label="Account" className="flex items-center gap-1">
          <NavLink to="/login" className={({ isActive }) => cn(tab, isActive ? 'bg-accent-100 text-accent-600' : 'text-ink-2 hover:bg-mist')}>
            Log in
          </NavLink>
          <NavLink
            to="/register"
            className={({ isActive }) => cn(tab, isActive ? 'bg-accent-100 text-accent-600' : 'text-ink-2 hover:bg-mist')}
          >
            Create account
          </NavLink>
        </nav>
      </header>
      <main className="flex flex-1 items-start justify-center px-4 py-12 sm:items-center">
        <div className="panel w-full max-w-[420px] p-6 sm:p-8">{children}</div>
      </main>
      <footer className="px-4 pb-6 text-center text-xs text-ink-3">© 2026 Valora · Finnovate Web &amp; AI Hackathon 2026</footer>
    </div>
  )
}

export const inputClass =
  'mt-1 h-10 w-full rounded border border-line-strong bg-surface px-3 text-sm text-ink outline-none transition-colors duration-150 placeholder:text-ink-3 hover:border-ink-3 focus:border-accent-600 focus:ring-2 focus:ring-accent-500/30'
