import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from '@/lib/api'
import { answer, type Answer, type AskContext, type InsightsData } from '@/lib/insight/engine'
import type { LedgerHealth, Opportunity, Overview } from '@/lib/types'
import { InsightCtx, type Entry, type InsightState } from './context'

/** Minimum time the "reading your data" state shows, so it does not flicker. */
const MIN_THINK_MS = 280

/** Earlier turns sent with a question so follow-ups ("and last month?") make sense. */
const HISTORY_TURNS = 6

const asText = (a: Answer) => [a.headline, a.body, ...a.facts.map((f) => `${f.label}: ${f.value}`)].filter(Boolean).join(' ').slice(0, 800)

/**
 * Holds the Valora Insight conversation for the signed-in business. Questions go
 * to the LLM endpoint (POST /insight/ask), which answers from figures Valora
 * already computed. If it is not configured or fails, the answer is computed in
 * the browser by the local rules instead.
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

  const ask = useCallback(
    (question: string, ctx?: AskContext) => {
      const q = question.trim().slice(0, 200)
      if (!q) return
      const id = ++seq.current
      const turns = history.current
        .filter((e): e is Entry & { answer: Answer } => !!e.answer)
        .slice(-HISTORY_TURNS)
        .map((e) => ({ question: e.question, answer: asText(e.answer) }))
      setOpen(true)
      setPending(true)
      setEntries((e) => [...e.slice(-19), { id, question: q, answer: null }])
      Promise.all([
        api<Answer>('/insight/ask', { method: 'POST', body: { question: q, history: turns, context: ctx ?? null } }).catch(() =>
          local(q, ctx),
        ),
        new Promise((r) => setTimeout(r, MIN_THINK_MS)),
      ]).then(([a]) => {
        setEntries((e) => e.map((x) => (x.id === id ? { ...x, answer: a } : x)))
        setPending(false)
        setJustAnswered(true)
        setTimeout(() => setJustAnswered(false), 700)
      })
    },
    [local],
  )

  const value = useMemo<InsightState>(
    () => ({
      open,
      setOpen,
      entries,
      orb: pending ? 'thinking' : justAnswered ? 'answer' : open ? 'open' : 'idle',
      ask,
      clear: () => setEntries([]),
    }),
    [open, entries, pending, justAnswered, ask],
  )
  return <InsightCtx.Provider value={value}>{children}</InsightCtx.Provider>
}
