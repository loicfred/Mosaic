import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { LoginIllustration } from '@/components/brand/LoginIllustration'
import { ValoraLogo } from '@/components/brand/ValoraLogo'
import { InsightOrb } from '@/components/insight/InsightOrb'
import { cn } from '@/lib/cn'

/** Inverted rounded corner used where the bottom-left tab meets the coloured panel. */
function Corner({ className }: { className: string }) {
  return (
    <svg viewBox="0 0 28 28" className={cn('absolute size-7 text-page', className)} aria-hidden>
      <path d="M0 0 A28 28 0 0 0 28 28 H0 Z" fill="currentColor" />
    </svg>
  )
}

const pill = 'rounded-lg px-3.5 py-2 text-sm font-medium transition-colors'

/**
 * Sign-in and sign-up frame: a navy panel with the Valora
 * illustration, and the form in a white card on the right.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-page p-2 sm:p-4">
      <div className="relative flex min-h-[calc(100vh-1rem)] flex-col overflow-hidden rounded-[28px] lg:rounded-bl-none bg-[#1b2a4e] text-white sm:min-h-[calc(100vh-2rem)]">
        <header className="flex items-center justify-between gap-3 px-5 py-5 sm:px-10">
          <ValoraLogo onColor />
          <nav aria-label="Account" className="flex items-center gap-2">
            <NavLink
              to="/login"
              className={({ isActive }) =>
                cn(pill, isActive ? 'ring-1 ring-inset ring-white' : 'text-white/85 hover:bg-white/10 hover:text-white')
              }
            >
              Log in
            </NavLink>
            <NavLink
              to="/register"
              className={({ isActive }) => cn(pill, isActive ? 'bg-white text-[#1b2a4e]' : 'bg-[#0b8193] text-white hover:bg-[#086877]')}
            >
              Create account
            </NavLink>
          </nav>
        </header>

        <main className="flex flex-1 items-center gap-6 px-4 pb-10 sm:px-10 lg:items-stretch lg:gap-4 lg:pb-[96px]">
          {/* The illustration fills everything left of the card and hugs its edge. */}
          <div className="relative hidden min-w-0 flex-1 lg:block">
            {/* Sticky, so on the taller sign-up form the drawing stays in view while scrolling. */}
            <div className="sticky top-6 h-[calc(100vh-13rem)] max-h-full min-h-[320px]">
              <LoginIllustration className="size-full" />
            </div>
          </div>
          <div className="mx-auto flex w-full max-w-[460px] shrink-0 items-center lg:mx-0">
            <div className="fade-up w-full rounded-2xl bg-surface p-6 text-ink shadow-[0_24px_60px_-24px_rgba(8,14,30,0.6)] sm:p-7">
              {children}
            </div>
          </div>
        </main>

        <footer className="px-5 pb-6 text-xs text-white sm:px-10 lg:absolute lg:bottom-0 lg:right-0 lg:pb-7">
          © 2026 Valora · Finnovate Web &amp; AI Hackathon 2026 · Challenge 3
        </footer>

        {/* Bottom-left tab, cut out of the panel. */}
        <aside
          aria-label="About Valora Insight"
          className="absolute bottom-0 left-0 hidden h-[88px] w-[360px] rounded-tr-[28px] bg-page lg:block"
        >
          <Corner className="-top-7 left-0" />
          <Corner className="-right-7 bottom-0" />
          <div className="flex h-full items-center gap-3 pl-6 pr-5 text-ink">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-full border border-line bg-surface">
              <InsightOrb className="size-8" state="static" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold">Valora Insight</span>
              <span className="block text-xs leading-snug text-ink-3">After you log in, ask questions about your own business data.</span>
            </span>
          </div>
        </aside>
      </div>
    </div>
  )
}

export const inputClass =
  'mt-1.5 h-11 w-full rounded-lg border border-line-strong bg-surface px-3 text-sm text-ink outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-ink-3/70 hover:border-ink-3/60 focus:border-accent-600 focus:ring-4 focus:ring-accent-100'
