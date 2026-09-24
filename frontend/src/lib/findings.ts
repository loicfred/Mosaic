/**
 * Presentation helpers for findings. They only reshape values the engine already
 * returned (evidence items, impact ranges); nothing here computes new facts.
 */
import { murCompact } from './format'
import type { Evidence, Opportunity } from './types'

/** "MUR 79,490 → MUR 89,790" or "34 days → 48 days" -> [79490, 89790]. Null when the text is not a before→after pair. */
export function arrowPair(text?: string | null): [number, number] | null {
  if (!text || !text.includes('→')) return null
  const [a, b] = text.split('→')
  const num = (s: string) => {
    const m = s.replace(/,/g, '').match(/-?\d+(\.\d+)?/)
    return m ? Number(m[0]) : NaN
  }
  const x = num(a)
  const y = num(b)
  return Number.isFinite(x) && Number.isFinite(y) ? [x, y] : null
}

/** Shorter display for a supporting number: "MUR 121,633" -> "MUR 122K". */
export function compactDisplay(display: string) {
  const m = display.match(/^(−|-)?MUR ([\d,]+(\.\d+)?)$/)
  if (!m) return display
  const v = Number(m[2].replace(/,/g, '')) * (m[1] ? -1 : 1)
  return murCompact(v)
}

/** Evidence rows each detector's visual already shows, so they are not repeated as text. */
const SHOWN_IN_VISUAL: Record<string, number[]> = {
  supplier_cost_inflation: [2],
  slow_collections: [0, 3],
  cash_pressure: [4, 5, 6],
  customer_concentration: [0, 2, 3],
  supplier_concentration: [0, 1, 2, 3],
  growth_product_line: [0],
  recurring_cost_creep: [0],
  unusual_transactions: [0, 1],
  overlapping_subscriptions: [0, 1],
}

export interface SupportStat {
  value: string
  label: string
  trend?: 'up' | 'down'
}

/** At most two short supporting facts for a finding, taken in the engine's own order. */
export function supportStats(o: Pick<Opportunity, 'detector' | 'evidence'>, max = 2): SupportStat[] {
  const skip = new Set(SHOWN_IN_VISUAL[o.detector] ?? [])
  const out: SupportStat[] = []
  o.evidence.forEach((e: Evidence, i) => {
    if (out.length >= max || skip.has(i) || e.source === 'model driver') return
    const value = compactDisplay(e.display)
    if (value.length > 16) return
    const trend = /^\+/.test(value) ? 'up' : /^(-|−)/.test(value) ? 'down' : undefined
    out.push({ value, label: e.label.replace(/^New: /, 'new: '), trend })
  })
  return out
}

/** Gains and risks are never added together: several findings can concern the same money. */
export const GAIN_KINDS: Opportunity['impact_kind'][] = ['saving', 'cash_release', 'revenue_upside']
export const RISK_KINDS: Opportunity['impact_kind'][] = ['exposure', 'shortfall']

export const IMPACT_SHORT: Record<Opportunity['impact_kind'], string> = {
  saving: 'saving a year',
  cash_release: 'cash to free up',
  revenue_upside: 'gross profit a year',
  exposure: 'revenue at risk a year',
  shortfall: 'cash gap to the buffer',
  none: '',
}
