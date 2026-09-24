import { ArrowRight, ArrowUp, Info, RotateCcw, X } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { DataKind } from '@/components/domain/labels'
import { Sparkline } from '@/components/viz/Sparkline'
import { cn } from '@/lib/cn'
import { suggestionsFor, type Answer, type Visual } from '@/lib/insight/engine'
import { InsightOrb } from './InsightOrb'
import { useInsight, type Entry } from './context'

const TONE = { good: 'text-good-ink', bad: 'text-bad-ink', warn: 'text-warn-ink' } as const

function MiniBars({ v }: { v: Extract<Visual, { type: 'bars' }> }) {
  const max = Math.max(...v.rows.map((r) => r.value), 1)
  return (
    <figure>
      <figcaption className="mb-2 text-xs text-ink-3">{v.label}</figcaption>
      <ul className="space-y-1.5" aria-label={v.label}>
        {v.rows.map((r) => (
          <li key={r.label} className="grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)_auto] items-center gap-2 text-xs">
            <span className="truncate text-ink-2" title={r.label}>
              {r.label}
            </span>
            <span className="h-2 rounded-full bg-track">
              <span
                className="grow-x block h-full rounded-full"
                style={{ width: `${Math.max(2, (r.value / max) * 100)}%`, background: v.color ?? 'var(--color-actual)' }}
              />
            </span>
            <span className="tnum text-right font-medium text-ink">{r.display}</span>
          </li>
        ))}
      </ul>
    </figure>
  )
}

function AnswerBlock({ a, onAsk, onNavigate }: { a: Answer; onAsk: (q: string) => void; onNavigate: () => void }) {
  const refused = a.status === 'refusal'
  return (
    <div className={cn('rounded-xl border bg-surface p-4', refused ? 'border-gold-500/50' : 'border-line')}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-ink-3">
          {refused ? 'Outside Valora’s data' : a.status === 'empty' ? 'Not available yet' : 'From your data'}
        </span>
        {a.kind && <DataKind kind={a.kind} />}
      </div>
      <p className="flex gap-2 text-[15px] font-semibold leading-snug text-ink">
        {refused && <Info className="mt-0.5 size-4 shrink-0 text-gold-700" aria-hidden />}
        {a.headline}
      </p>
      {a.body && <p className="mt-1.5 text-sm leading-relaxed text-ink-2">{a.body}</p>}
      {a.facts.length > 0 && (
        <dl className="mt-3 divide-y divide-line border-y border-line">
          {a.facts.map((f) => (
            <div key={f.label} className="flex items-baseline justify-between gap-3 py-2 text-sm">
              <dt className="min-w-0 text-ink-3">{f.label}</dt>
              <dd className={cn('tnum max-w-[60%] text-right font-medium', f.tone ? TONE[f.tone] : 'text-ink')}>{f.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {a.visual && (
        <div className="mt-4">
          {a.visual.type === 'spark' ? (
            <figure>
              <Sparkline values={a.visual.values} color={a.visual.color} label={a.visual.label} className="h-12" />
              {a.visual.caption && <figcaption className="mt-1.5 text-xs text-ink-3">{a.visual.caption}</figcaption>}
            </figure>
          ) : (
            <MiniBars v={a.visual} />
          )}
        </div>
      )}
      {a.sources.length > 0 && (
        <div className="mt-4 space-y-1 border-t border-line pt-3 text-xs">
          {a.sources.map((s) => (
            <div key={s.label + s.detail} className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
              <span className="text-ink-3">
                <span className="font-medium text-ink-2">Source:</span> {s.label} · {s.detail}
              </span>
              {s.to && (
                <Link
                  to={s.to}
                  onClick={onNavigate}
                  className="inline-flex items-center gap-0.5 font-medium text-accent-700 hover:underline"
                >
                  Open <ArrowRight className="size-3" aria-hidden />
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
      {a.followUps.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {a.followUps.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onAsk(q)}
              className="rounded-full border border-line px-2.5 py-1 text-xs text-ink-2 transition-colors hover:border-accent-500 hover:bg-accent-50 hover:text-accent-700"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Thinking() {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-3 text-sm text-ink-3" role="status">
      <InsightOrb state="thinking" className="size-5 text-ink" />
      Reading your data…
    </div>
  )
}

function Turn({ e, onAsk, onNavigate }: { e: Entry; onAsk: (q: string) => void; onNavigate: () => void }) {
  return (
    <li className="space-y-2">
      <p className="ml-auto w-fit max-w-[85%] rounded-xl bg-brand-100 px-3 py-2 text-sm text-ink">{e.question}</p>
      {e.answer ? <AnswerBlock a={e.answer} onAsk={onAsk} onNavigate={onNavigate} /> : <Thinking />}
    </li>
  )
}

export function InsightPanel({ businessName }: { businessName: string }) {
  const ins = useInsight()
  const { pathname } = useLocation()
  const [q, setQ] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const end = useRef<HTMLDivElement>(null)
  const open = !!ins?.open
  const count = ins?.entries.length ?? 0
  const lastAnswered = !!ins?.entries[count - 1]?.answer

  useEffect(() => {
    if (open) input.current?.focus()
  }, [open])
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'end', behavior: 'smooth' })
  }, [count, lastAnswered])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && ins?.setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, ins])

  if (!ins || !open) return null
  const submit = (e: FormEvent) => {
    e.preventDefault()
    ins.ask(q)
    setQ('')
  }
  // Following a source link keeps the panel open on wide screens and closes it on phones.
  const onNavigate = () => window.matchMedia?.('(max-width: 640px)').matches && ins.setOpen(false)

  return (
    <section
      role="dialog"
      aria-modal="false"
      aria-labelledby="insight-title"
      className="panel-in no-print fixed inset-0 z-50 flex flex-col bg-page sm:inset-auto sm:bottom-24 sm:right-6 sm:h-[min(680px,calc(100vh-8rem))] sm:w-[420px] sm:overflow-hidden sm:rounded-2xl sm:border sm:border-line sm:shadow-[0_18px_48px_-18px_rgba(44,44,44,0.35)]"
    >
      <div className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
        <InsightOrb state={ins.orb} className="size-8 text-ink" />
        <div className="min-w-0 flex-1">
          <h2 id="insight-title" className="text-[15px] font-semibold text-ink">
            Valora Insight
          </h2>
          <p className="truncate text-xs text-ink-3">Answers only from {businessName}</p>
        </div>
        {count > 0 && (
          <button
            type="button"
            onClick={ins.clear}
            className="rounded-md p-2 text-ink-3 hover:bg-brand-50 hover:text-ink"
            aria-label="Clear answers"
            title="Clear answers"
          >
            <RotateCcw className="size-4" />
          </button>
        )}
        <button
          type="button"
          onClick={() => ins.setOpen(false)}
          className="rounded-md p-2 text-ink-3 hover:bg-brand-50 hover:text-ink"
          aria-label="Close Valora Insight"
        >
          <X className="size-4" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4" aria-live="polite">
        {count === 0 ? (
          <div>
            <p className="text-sm leading-relaxed text-ink-2">
              Ask about cash, revenue, costs, customers, suppliers, findings or data quality. Every answer shows the figures it uses and
              where they come from.
            </p>
            <h3 className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wider text-ink-3">Suggested for this page</h3>
            <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
              {suggestionsFor(pathname).map((s) => (
                <li key={s}>
                  <button
                    type="button"
                    onClick={() => ins.ask(s)}
                    className="group flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left text-sm text-ink transition-colors hover:bg-accent-50"
                  >
                    {s}
                    <ArrowRight className="size-3.5 shrink-0 text-ink-3 transition-transform group-hover:translate-x-0.5 group-hover:text-accent-600" />
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-5 text-xs leading-relaxed text-ink-3">
              Valora Insight matches your question to figures Valora has already calculated. It does not guess, forecast beyond
              Valora&apos;s 90-day cash projection, or send your records to an external AI service.
            </p>
          </div>
        ) : (
          <ul className="space-y-5">
            {ins.entries.map((e) => (
              <Turn key={e.id} e={e} onAsk={ins.ask} onNavigate={onNavigate} />
            ))}
          </ul>
        )}
        <div ref={end} />
      </div>

      <form onSubmit={submit} className="border-t border-line bg-surface p-3">
        <label htmlFor="insight-q" className="sr-only">
          Ask Valora about your business data
        </label>
        <div className="flex items-center gap-2 rounded-xl border border-line-strong bg-surface pl-3 pr-1.5 transition-[border-color,box-shadow] focus-within:border-accent-600 focus-within:ring-4 focus-within:ring-accent-100">
          <input
            id="insight-q"
            ref={input}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            maxLength={200}
            autoComplete="off"
            placeholder="Ask about your business data"
            className="h-11 min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-3/80"
          />
          <button
            type="submit"
            disabled={!q.trim() || ins.orb === 'thinking'}
            className="flex size-8 items-center justify-center rounded-lg bg-accent-600 text-white transition-colors hover:bg-accent-700 disabled:bg-brand-100 disabled:text-ink-3"
            aria-label="Ask"
          >
            <ArrowUp className="size-4" />
          </button>
        </div>
      </form>
    </section>
  )
}

/** The floating launcher. Label slides out on hover or focus. */
/**
 * The single entry point to Valora Insight: a labelled button, bottom right, on
 * every page. The orb only moves on hover and while Valora is reading data.
 */
export function InsightLauncher() {
  const ins = useInsight()
  const [hover, setHover] = useState(false)
  if (!ins) return null
  const state = ins.orb === 'idle' && hover ? 'hover' : ins.orb
  return (
    <button
      type="button"
      onClick={() => ins.setOpen(!ins.open)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      aria-expanded={ins.open}
      aria-label={ins.open ? 'Close Valora Insight' : 'Ask Valora'}
      className={cn(
        'no-print fixed bottom-5 right-5 z-40 h-12 items-center gap-2 rounded-full border border-line bg-surface pl-1.5 pr-1.5 text-sm font-medium text-ink shadow-[0_8px_24px_-12px_rgba(44,44,44,0.35)] transition-colors duration-150 hover:border-accent-500 hover:text-accent-700 sm:bottom-6 sm:right-6 sm:pr-4',
        ins.open ? 'hidden sm:flex' : 'flex',
      )}
    >
      <InsightOrb state={state} className="size-9" />
      <span className="hidden sm:inline">{ins.open ? 'Close' : 'Ask Valora'}</span>
    </button>
  )
}
