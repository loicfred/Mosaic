import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, ApiError } from '@/lib/api'
import { answer, type Answer, type AskContext, type InsightsData } from '@/lib/insight/engine'
import type { LedgerHealth, Opportunity, Overview } from '@/lib/types'
import { InsightCtx, type Entry, type InsightState } from './context'

/** Minimum time the "reading your data" state shows, so it does not flicker. */
const MIN_THINK_MS = 280

/** Earlier turns sent with a question so follow-ups ("and last month?") make sense. */
const HISTORY_TURNS = 6

const asText = (a: Answer) => [a.headline, a.body, ...a.facts.map((f) => `${f.label}: ${f.value}`)].filter(Boolean).join(' ').slice(0, 800)

function busy(e: ApiError): Answer {
  const d = (e.details ?? {}) as { retry_after?: number; scope?: string }
  const wait = Math.max(1, Math.ceil(d.retry_after ?? 20))
  return {
    status: 'busy',
    intent: 'rate_limited',
    headline:
      d.scope === 'valora'
        ? 'You have asked a lot of questions in a short time.'
        : 'The AI assistant has reached its free-tier limit for a moment.',
    body: 'Your question is kept. You can retry when the timer ends, or get an answer from Valora’s built-in rules now.',
    facts: [],
    sources: [],
    followUps: [],
    via: 'llm',
    retryAfter: wait,
  }
}

/**
 * Holds the Valora Insight conversation for the signed-in business. Questions go
 * to the LLM endpoint (POST /insight/ask), which answers from figures Valora
 * already computed. When the AI is rate limited the answer says so and offers a
 * retry; if it is not configured or fails, the local rules answer instead.
 */
export function InsightProvider({ businessName, children }: { businessName: string; children: ReactNode }) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState<Entry[]>([])
  const [pending, setPending] = useState(false)
  const [justAnswered, setJustAnswered] = useState(false)
  const seq = useRef(0)
  const history = useRef<Entry[]>([])
  useEffect(() => {
    history.current = entries
  }, [entries])

  const local = useCallback(
    async (q: string, ctx?: AskContext): Promise<Answer> => {
      const load = <T,>(key: unknown[], path: string) =>
        qc.ensureQueryData<T>({ queryKey: key, queryFn: () => api<T>(path) }).catch(() => undefined)
      const [overview, opportunities, insights, health] = await Promise.all([
        load<Overview>(['overview'], '/analytics/overview'),
        load<Opportunity[]>(['opportunities', false], '/opportunities?include_inactive=false'),
        load<InsightsData>(['insights'], '/insights'),
        load<LedgerHealth>(['health'], '/data-quality/health'),
      ])
      return { ...answer(q, { businessName, overview, opportunities, insights, health }, ctx), via: 'rules' }
    },
    [qc, businessName],
  )

  /** Answers entry `id` (already in the list) with the AI, or with the rules when `rules` is set. */
  const run = useCallback(
    (id: number, q: string, ctx: AskContext | undefined, rules = false) => {
      const turns = history.current
        .filter((e): e is Entry & { answer: Answer } => e.id !== id && !!e.answer && e.answer.status !== 'busy')
        .slice(-HISTORY_TURNS)
        .map((e) => ({ question: e.question, answer: asText(e.answer) }))
      setPending(true)
      const get: Promise<Answer> = rules
        ? local(q, ctx)
        : api<Answer>('/insight/ask', { method: 'POST', body: { question: q, history: turns, context: ctx ?? null } }).catch((e) =>
            e instanceof ApiError && e.status === 429 ? busy(e) : local(q, ctx).then((a) => ({ ...a, fallback: true })),
          )
      Promise.all([get, new Promise((r) => setTimeout(r, MIN_THINK_MS))]).then(([a]) => {
        setEntries((e) => e.map((x) => (x.id === id ? { ...x, answer: a } : x)))
        setPending(false)
        setJustAnswered(true)
        setTimeout(() => setJustAnswered(false), 700)
      })
    },
    [local],
  )

  const ask = useCallback(
    (question: string, ctx?: AskContext) => {
      const q = question.trim().slice(0, 200)
      if (!q) return
      const id = ++seq.current
      setOpen(true)
      setEntries((e) => [...e.slice(-19), { id, question: q, answer: null, ctx }])
      run(id, q, ctx)
    },
    [run],
  )

  const redo = useCallback(
    (id: number, rules: boolean) => {
      const e = history.current.find((x) => x.id === id)
      if (!e) return
      setEntries((all) => all.map((x) => (x.id === id ? { ...x, answer: null } : x)))
      run(id, e.question, e.ctx, rules)
    },
    [run],
  )

  const value = useMemo<InsightState>(
    () => ({
      open,
      setOpen,
      entries,
      orb: pending ? 'thinking' : justAnswered ? 'answer' : open ? 'open' : 'idle',
      ask,
      retry: (id) => redo(id, false),
      useRules: (id) => redo(id, true),
      clear: () => setEntries([]),
    }),
    [open, entries, pending, justAnswered, ask, redo],
  )
  return <InsightCtx.Provider value={value}>{children}</InsightCtx.Provider>
}
