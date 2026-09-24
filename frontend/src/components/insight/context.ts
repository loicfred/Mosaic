import { createContext, useContext } from 'react'
import type { Answer, AskContext } from '@/lib/insight/engine'
import type { OrbState } from './InsightOrb'

export interface Entry {
  id: number
  question: string
  answer: Answer | null
}

export interface InsightState {
  open: boolean
  setOpen: (v: boolean) => void
  entries: Entry[]
  orb: OrbState
  ask: (question: string, ctx?: AskContext) => void
  clear: () => void
}

export const InsightCtx = createContext<InsightState | null>(null)

/** Null outside the signed-in shell (e.g. in isolated component tests), so callers can render nothing. */
export function useInsight() {
  return useContext(InsightCtx)
}
