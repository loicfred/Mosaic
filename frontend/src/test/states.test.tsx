import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { OverviewPage } from '@/pages/Overview'
import { mockFetch, renderWithProviders } from './utils'

vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ can: () => true }) }))

describe('error states', () => {
  it('shows a safe error with a request reference and retry', async () => {
    mockFetch(() => ({
      status: 500,
      body: { error: { code: 'internal_error', message: 'Something went wrong. The error has been logged.', request_id: 'abc123' } },
    }))
    renderWithProviders(<OverviewPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Your overview could not be loaded.')
    expect(screen.getByRole('alert')).toHaveTextContent('Try again')
    expect(screen.getByText(/abc123/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
  })
})
