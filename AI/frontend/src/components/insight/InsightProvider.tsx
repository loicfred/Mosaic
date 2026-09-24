import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from '@/lib/api'
import { answer, type AskContext, type InsightsData } from '@/lib/insight/engine'
import type { LedgerHealth, Opportunity, Overview } from '@/lib/types'
import { InsightCtx, type Entry, type InsightState } from './context'

/** Minimum time the "reading your data" state shows, so it does not flicker. */
const MIN_THINK_MS = 280

/**
 * Holds the Valora Insight conversation for the signed-in business. Answers are
 * computed in the browser from API responses the app already uses; nothing is
 * sent anywhere except the normal, authenticated Valora API calls.
 */
export function InsightProvider({ businessName, children }: { businessName: string; children: ReactNode }) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState<Entry[]>([])
  const [pending, setPending] = useState(false)
  const [justAnswered, setJustAnswered] = useState(false)
  const seq = useRef(0)

  const ask = useCallback(
    (question: string, ctx?: AskContext) => {
      const q = question.trim().slice(0, 200)
      if (!q) return
      const id = ++seq.current
      setOpen(true)
      setPending(true)
      setEntries((e) => [...e.slice(-19), { id, question: q, answer: null }])
      const load = <T,>(key: unknown[], path: string) =>
        qc.ensureQueryData<T>({ queryKey: key, queryFn: () => api<T>(path) }).catch(() => undefined)
      Promise.all([
        load<Overview>(['overview'], '/analytics/overview'),
        load<Opportunity[]>(['opportunities', false], '/opportunities?include_inactive=false'),
        load<InsightsData>(['insights'], '/insights'),
        load<LedgerHealth>(['health'], '/data-quality/health'),
        new Promise((r) => setTimeout(r, MIN_THINK_MS)),
      ]).then(([overview, opportunities, insights, health]) => {
        const a = answer(q, { businessName, overview, opportunities, insights, health }, ctx)
        setEntries((e) => e.map((x) => (x.id === id ? { ...x, answer: a } : x)))
        setPending(false)
        setJustAnswered(true)
        setTimeout(() => setJustAnswered(false), 700)
      })
    },
    [qc, businessName],
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
