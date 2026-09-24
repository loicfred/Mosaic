import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { ScenarioLabPage } from '@/pages/ScenarioLab'
import { mockFetch, renderWithProviders } from './utils'

vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ can: () => true }) }))

const summary = (d: number) => ({
  starting_cash: 575000,
  cash_day_30: 475000 + d,
  cash_day_60: 500000 + d,
  cash_day_90: 533000 + d,
  lowest_cash: 330000 + d,
  lowest_cash_date: '2026-10-26',
  buffer_threshold: 453000,
  days_below_buffer: d ? 0 : 21,
  first_date_below_buffer: null,
  total_inflow: 3e6,
  total_outflow: 3e6,
})

describe('Scenario Lab', () => {
  it('sends assumptions to the simulator and labels results as simulated', async () => {
    const calls = mockFetch((url, init) => {
      if (url.endsWith('/scenarios/levers'))
        return { body: [{ key: 'supplier_cost_pct', label: 'Supplier prices', min: -30, max: 30, step: 1, unit: '%' }] }
      if (url.endsWith('/scenarios/simulate')) {
        const a = JSON.parse(String(init?.body)).assumptions
        const d = a.supplier_cost_pct ? 187000 : 0
        return {
          body: {
            as_of: '2026-09-22',
            horizon_days: 90,
            assumptions: a,
            baseline: summary(0),
            scenario: summary(d),
            difference: { cash_day_90: d },
            series: [],
            breakdown: [{ driver: 'suppliers', baseline: 1.9e6, scenario: 1.9e6 - d, difference: -d }],
            method_notes: ['No owner drawings or capital injections are assumed.'],
            label: 'SIMULATED',
            drivers: {},
            backtest_median_error_pct: 13.3,
          },
        }
      }
      if (url.endsWith('/scenarios')) return { body: [] }
      return undefined
    })
    renderWithProviders(<ScenarioLabPage />, '/scenarios')
    await screen.findByText('Cash in 90 days')
    await userEvent.click(screen.getByRole('button', { name: 'Supplier prices -10%' }))
    await waitFor(() => {
      const last = calls.filter((c) => c.url.endsWith('/scenarios/simulate')).pop()!
      expect(JSON.parse(String(last.init?.body)).assumptions.supplier_cost_pct).toBe(-10)
    })
    expect((await screen.findAllByText('+MUR 187K')).length).toBeGreaterThan(0)
    // The supplier driver shows as a positive effect on cash (paying suppliers less).
    expect(screen.getAllByText('+MUR 187K').length).toBeGreaterThan(1)
    expect(screen.getAllByText('Simulated').length).toBeGreaterThan(0)
    expect(screen.getByText(/never modified/i)).toBeInTheDocument()
  })
})
