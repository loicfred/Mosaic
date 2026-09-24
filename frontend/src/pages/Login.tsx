import { Eye, EyeOff } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { AuthLayout, inputClass } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'

export function LoginPage() {
  const { me, signIn } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (me) return <Navigate to="/" replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!email || !password) {
      setError('Enter your email and password.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await signIn(email, password)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold text-ink">Welcome back</h1>
      <p className="mt-1 text-sm text-ink-3">Sign in to continue to Valora.</p>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <label className="block text-sm">
          <span className="font-medium text-ink-2">Email</span>
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@business.mu"
            className={inputClass}
          />
        </label>
        <div className="text-sm">
          <label htmlFor="login-password" className="font-medium text-ink-2">
            Password
          </label>
          <div className="relative">
            <input
              id="login-password"
              type={show ? 'text' : 'password'}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`${inputClass} pr-11`}
            />
            <button
              type="button"
              onClick={() => setShow(!show)}
              className="absolute right-1.5 top-[calc(50%+3px)] -translate-y-1/2 rounded-md p-2 text-ink-3 hover:bg-mist hover:text-ink"
              aria-label={show ? 'Hide password' : 'Show password'}
            >
              {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
        </div>
        {error && (
          <p role="alert" className="rounded bg-bad-bg px-3 py-2 text-sm text-bad-ink">
            {error}
          </p>
        )}
        <Button type="submit" size="lg" className="w-full" disabled={busy}>
          {busy ? (
            'Signing in…'
          ) : (
            <>
              Sign in
            </>
          )}
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-ink-3">
        Don&apos;t have an account yet?{''}
        <Link to="/register" className="font-medium text-accent-600 underline-offset-2 hover:underline">
          Create account
        </Link>
      </p>
    </AuthLayout>
  )
}
