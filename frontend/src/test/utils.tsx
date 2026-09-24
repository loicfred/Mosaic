import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'

export function renderWithProviders(ui: ReactElement, route = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <TooltipProvider>{ui}</TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

type Handler = (url: string, init?: RequestInit) => { status?: number; body?: unknown } | undefined

/** Minimal fetch mock: first matching handler wins. Records calls for assertions. */
export function mockFetch(handler: Handler) {
  const calls: { url: string; init?: RequestInit }[] = []
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    calls.push({ url, init })
    const r = handler(url, init) ?? { status: 404, body: { error: { code: 'not_found', message: 'Not found' } } }
    const status = r.status ?? 200
    return new Response(status === 204 ? null : JSON.stringify(r.body ?? {}), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fn)
  return calls
}

export const opportunity = (over: Record<string, unknown> = {}) => ({
  id: 'opp-1',
  detector: 'supplier_cost_inflation',
  kind: 'risk',
  category: 'cost_leakage',
  title: 'Supplier costs up 21% while revenue grew 8%',
  summary: 'Stock costs are growing faster than sales.',
  why_it_matters: 'Margins shrink.',
  explanation: 'Supplier spending rose 20.9% while revenue rose 7.8%.',
  severity: 'high',
  priority_score: 3,
  confidence: 0.9,
  confidence_basis: { method: 'evidence_score', strength: 1, coverage: 1, data_quality: 0.99, consistency: 1 },
  impact_low: 187000,
  impact_high: 375000,
  impact_kind: 'saving',
  impact_basis: 'Annual saving if prices fall 5-10%.',
  evidence: [{ label: 'Supplier costs', value: 20.9, display: '+20.9%' }],
  supporting_records: { transaction_ids: [] },
  actions: [{ title: 'Request a price review', detail: '', effort: 'medium' }],
  scenario_preset: { name: 'Supplier prices -10%', assumptions: { supplier_cost_pct: -10 } },
  provenance: { engine_version: 'opportunity-engine-1.0', detector: 'supplier_cost_inflation', data_window: ['2024-10-01', '2026-09-22'] },
  target: { key: 'cogs_to_revenue_pct', label: 'Supplier cost per MUR 100 of sales', unit: '%', better: 'lower', params: {} },
  baseline_value: 59.8,
  expected_change: -3.2,
  status: 'new',
  is_active: true,
  action_started_at: null,
  completed_at: null,
  outcome: null,
  data_as_of: '2026-09-22',
  detected_at: '2026-09-23T10:00:00Z',
  updated_at: '2026-09-23T10:00:00Z',
  events: [],
  ...over,
})
