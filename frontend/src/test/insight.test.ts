import { answer, matchIntent, type InsightContext } from '@/lib/insight/engine'
import type { Opportunity, Overview } from '@/lib/types'
import { opportunity } from './utils'

const month = (m: string, revenue: number, partial = false) => ({
  month: m,
  partial,
  days_covered: 30,
  revenue,
  cost_of_goods: revenue * 0.5,
  operating_expenses: 1000,
  tax: 0,
  expenses: revenue * 0.5 + 1000,
  gross_margin_pct: 50,
  net_cash_flow: revenue * 0.5 - 1000,
  closing_cash: 100000,
})

const overview = {
  as_of: '2026-09-22',
  data_window: ['2025-10-01', '2026-09-22'],
  cash: { balance: 474000, balance_30d_ago: 520000, buffer_days: 11.4, buffer_threshold: 580000 },
  kpis_90d: {
    period: ['2026-06-01', '2026-08-31'],
    previous_period: ['2026-03-01', '2026-05-31'],
    revenue: 2658830,
    revenue_change_pct: -2.6,
    expenses: 2633222,
    expenses_change_pct: 5.7,
    gross_margin_pct: 39.7,
    gross_margin_change_pp: -8.4,
    operating_cash_flow: 25607,
    operating_cash_flow_prev: 238722,
  },
  cash_series: [
    { date: '2026-09-21', cash: 480000, ma7: 0, ma30: 0 },
    { date: '2026-09-22', cash: 474000, ma7: 0, ma30: 0 },
  ],
  projection_series: [
    { date: '2026-09-23', cash: 470000 },
    { date: '2026-09-24', cash: 460000 },
  ],
  projection: {
    starting_cash: 474000,
    cash_day_30: 430000,
    cash_day_60: 400000,
    cash_day_90: 390000,
    lowest_cash: 350000,
    lowest_cash_date: '2026-11-02',
    buffer_threshold: 580000,
    days_below_buffer: 90,
    first_date_below_buffer: '2026-09-23',
    total_inflow: 1,
    total_outflow: 1,
  },
  monthly: [month('2026-07', 900000), month('2026-08', 1100000), month('2026-09', 500000, true)],
  prediction: { mode: 'model', band: 'HIGH', probability: 0.41, model_version: 'm1', reason: '', top_drivers: [] },
  data_health: { score: 99, issues: 3 },
} as unknown as Overview

const ctx: InsightContext = {
  businessName: 'Coastal Pantry',
  overview,
  opportunities: [
    opportunity() as unknown as Opportunity,
    opportunity({
      id: 'opp-2',
      title: 'Cancel an overlapping tool',
      kind: 'opportunity',
      impact_kind: 'saving',
      impact_low: 20000,
      impact_high: 40000,
    }) as unknown as Opportunity,
  ],
}

describe('Valora Insight answers only from loaded data', () => {
  it('routes common questions to the right intent', () => {
    expect(matchIntent('How much cash do we have?')).toBe('cash_now')
    expect(matchIntent('Will cash fall below the safety buffer?')).toBe('cash_outlook')
    expect(matchIntent('What is the 30-day cash pressure risk?')).toBe('cash_pressure')
    expect(matchIntent('What are our recurring costs?')).toBe('recurring')
    expect(matchIntent('Which customers owe us the most?')).toBe('collections')
    expect(matchIntent('How reliable is the data?')).toBe('data_health')
    expect(matchIntent('What should I look at first?')).toBe('priorities')
  })

  it('states the recorded cash figure and cites its source', () => {
    const a = answer('How much cash do we have?', ctx)
    expect(a.status).toBe('answer')
    expect(a.kind).toBe('actual')
    expect(a.headline).toContain('MUR 474K')
    expect(a.headline).toContain('22 Sep 2026')
    expect(a.sources[0].detail).toContain('Ledger, actual')
  })

  it('labels the cash outlook as a projection', () => {
    const a = answer('Will cash fall below the safety buffer?', ctx)
    expect(a.kind).toBe('projected')
    expect(a.headline).toContain('23 Sep 2026')
  })

  it('picks the biggest open opportunity by the engine’s own impact range', () => {
    const a = answer('What is the biggest opportunity?', ctx)
    // Both fixtures are savings; the supplier finding's range (187K-375K) is larger than 20K-40K.
    expect(a.headline).toContain('Supplier costs up 21%')
    expect(a.sources[0].to).toBe('/opportunities?open=opp-1')
    expect(a.visual?.type).toBe('bars')
  })

  it('explains a finding when asked from its card', () => {
    const a = answer('Explain this finding', ctx, { type: 'finding', id: 'opp-1' })
    expect(a.headline).toContain('Supplier costs up 21%')
    expect(a.facts.some((f) => f.value.includes('187K'))).toBe(true)
  })

  it('refuses forecasts it has no data for', () => {
    const a = answer('Predict our revenue for next year', ctx)
    expect(a.status).toBe('refusal')
    expect(a.headline).toBe("I don't have forecasting data for that in the current Valora dataset.")
    expect(a.facts).toHaveLength(0)
  })

  it('refuses questions outside the business data', () => {
    for (const q of ['What are my competitors charging?', 'Write me a poem', 'Tell me the weather tomorrow']) {
      const a = answer(q, ctx)
      expect(a.status).toBe('refusal')
      expect(a.facts).toHaveLength(0)
    }
    expect(answer('What are my competitors charging?', ctx).headline).toBe(
      'I can only answer questions using the business data available in Valora.',
    )
  })

  it('does not make decisions for the owner', () => {
    const a = answer('Should I take a loan?', ctx)
    expect(a.status).toBe('refusal')
    expect(a.headline).toContain('does not make business decisions')
  })

  it('says when a data source is not loaded instead of guessing', () => {
    const a = answer('Where does most of the money go?', { ...ctx, insights: undefined })
    expect(a.status).toBe('empty')
    expect(a.facts).toHaveLength(0)
  })

  it('points a new, empty business to the import step', () => {
    const empty = { ...ctx, overview: { ...overview, monthly: [] } as Overview }
    const a = answer('How much cash do we have?', empty)
    expect(a.status).toBe('empty')
    expect(a.sources[0].to).toBe('/data-health?tab=import')
  })
})
