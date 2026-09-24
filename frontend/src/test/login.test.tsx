import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { LoginPage } from '@/pages/Login'
import { ApiError } from '@/lib/api'
import { renderWithProviders } from './utils'

const signIn = vi.fn()
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ me: null, signIn }) }))

describe('Login', () => {
  it('shows the generic server message on failure and never echoes the password', async () => {
    signIn.mockRejectedValueOnce(new ApiError(401, 'invalid_credentials', 'Email or password is incorrect.'))
    renderWithProviders(<LoginPage />, '/login')
    await userEvent.type(screen.getByLabelText('Email'), 'owner@coastal.demo')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-secret')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Email or password is incorrect.')
    expect(document.body.textContent).not.toContain('wrong-secret')
  })
})
