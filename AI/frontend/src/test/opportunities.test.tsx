import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { OpportunitiesPage } from '@/pages/Opportunities'
import { mockFetch, opportunity, renderWithProviders } from './utils'

const auth = { can: vi.fn(() => true), me: { role: 'owner' } }
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => auth }))

describe('Opportunities', () => {
  beforeEach(() => auth.can.mockImplementation(() => true))

  it('shows evidence, impact and confidence on each card', async () => {
    mockFetch((url) => (url.includes('/opportunities?') ? { body: [opportunity()] } : undefined))
    renderWithProviders(<OpportunitiesPage />)
    const card = (await screen.findByRole('heading', { name: 'Supplier costs up 21% while revenue grew 8%' })).closest('article')!
    expect(within(card).getByText('+20.9%')).toBeInTheDocument()
    expect(within(card).getByText('Potential saving / year')).toBeInTheDocument()
    expect(within(card).getByText('90%')).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: /simulate/i })).toHaveAttribute('href', expect.stringContaining('supplier_cost_pct'))
    // The same finding is placed on the shared "what it is worth" scale, labelled with its range.
    expect(screen.getByRole('button', { name: /Supplier costs up 21%.*187K–375K/ })).toBeInTheDocument()
  })

  it('moves an opportunity through the action workflow', async () => {
    const calls = mockFetch((url, init) => {
      if (url.includes('/opportunities?')) return { body: [opportunity()] }
      if (url.endsWith('/opportunities/opp-1/status') && init?.method === 'PATCH') return { body: opportunity({ status: 'reviewed' }) }
      if (url.endsWith('/opportunities/opp-1')) return { body: opportunity() }
      return undefined
    })
    renderWithProviders(<OpportunitiesPage />, '/opportunities?open=opp-1')
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText(/What was found/i)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Mark reviewed' }))
    await waitFor(() => expect(calls.some((c) => c.init?.method === 'PATCH')).toBe(true))
    const patch = calls.find((c) => c.init?.method === 'PATCH')!
    expect(JSON.parse(String(patch.init?.body))).toEqual({ status: 'reviewed', note: null })
  })

  it('hides status controls from read-only users', async () => {
    auth.can.mockImplementation(() => false)
    mockFetch((url) => {
      if (url.includes('/opportunities?')) return { body: [opportunity()] }
      if (url.endsWith('/opportunities/opp-1')) return { body: opportunity() }
      return undefined
    })
    renderWithProviders(<OpportunitiesPage />, '/opportunities?open=opp-1')
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText(/can view but not change/i)).toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: 'Mark reviewed' })).not.toBeInTheDocument()
  })

  it('shows measured outcome for completed actions', async () => {
    const done = opportunity({
      status: 'completed',
      outcome: {
        status: 'achieved',
        message: 'The measured change meets or exceeds the expected effect.',
        baseline: 4100,
        current: 1650,
        change: -2450,
        expected_change: -1650,
        unit: 'MUR',
        metric_label: 'Monthly cost of overlapping tools',
        window: ['2026-05-12', '2026-09-22'],
        days_observed: 133,
      },
    })
    mockFetch((url) => (url.includes('/opportunities?') ? { body: [done] } : url.endsWith('/opp-1') ? { body: done } : undefined))
    renderWithProviders(<OpportunitiesPage />, '/opportunities?open=opp-1')
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText('Outcome achieved')).toBeInTheDocument()
    expect(within(dialog).getByText('MUR 4,100')).toBeInTheDocument()
  })
})
