import { Check, Circle, Eye, EyeOff, Info } from 'lucide-react'
import { useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { AuthLayout, inputClass } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'

/** Suggestions only; any sector can be typed. The sector is a label and does not change any calculation. */
const SECTORS = [
  'Retail',
  'Food & beverage',
  'Hospitality',
  'Professional services',
  'Construction',
  'Manufacturing',
  'Wholesale & distribution',
  'Health & beauty',
  'Transport & logistics',
  'Agriculture',
]

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Mirrors the server rules in backend/app/security/passwords.py; the server stays the authority. */
function passwordChecks(pw: string, email: string) {
  const name = email.split('@')[0]?.toLowerCase() ?? ''
  return [
    { ok: pw.length >= 12, label: 'At least 12 characters' },
    { ok: pw.length > 0 && (!name || !pw.toLowerCase().includes(name)), label: 'Does not contain your email name' },
    { ok: new Set(pw).size >= 5, label: 'Not too repetitive' },
  ]
}

function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="font-medium text-ink-2">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-xs text-ink-3">{hint}</span>}
    </label>
  )
}

export function RegisterPage() {
  const { me, signUp } = useAuth()
  const navigate = useNavigate()
  const [f, setF] = useState({
    full_name: '',
    email: '',
    password: '',
    business_name: '',
    sector: '',
    opening_cash: '',
    opening_date: '',
  })
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const checks = useMemo(() => passwordChecks(f.password, f.email), [f.password, f.email])
  if (me) return <Navigate to="/" replace />

  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const cash = Number(f.opening_cash.replace(/[\s,]/g, ''))
  const complete =
    f.full_name.trim().length >= 2 &&
    /\S+@\S+\.\S+/.test(f.email) &&
    checks.every((c) => c.ok) &&
    f.business_name.trim().length >= 2 &&
    f.sector.trim().length >= 2 &&
    f.opening_cash.trim() !== '' &&
    Number.isFinite(cash) &&
    cash >= 0 &&
    !!f.opening_date &&
    f.opening_date <= today()

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!complete) {
      setError('Fill in every field. The password must meet all three rules and the balance date cannot be in the future.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await signUp({ ...f, opening_cash: cash.toFixed(2) })
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the server.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-[24px] font-semibold leading-tight tracking-[-0.02em] text-ink">Create your Valora business account</h1>
      <p className="mt-1 text-sm text-ink-3">You become the owner of the new business in Valora.</p>

      <form onSubmit={submit} className="mt-8 space-y-8" noValidate>
        <fieldset className="space-y-5">
          <legend className="mb-4 text-xs font-semibold uppercase tracking-wider text-ink-3">You</legend>
          <Field label="Full name">
            <input autoComplete="name" required value={f.full_name} onChange={set('full_name')} className={inputClass} />
          </Field>
          <Field label="Work email">
            <input type="email" autoComplete="email" required value={f.email} onChange={set('email')} className={inputClass} />
          </Field>
          <div className="text-sm">
            <label htmlFor="reg-password" className="font-medium text-ink-2">
              Password
            </label>
            <div className="relative">
              <input
                id="reg-password"
                type={show ? 'text' : 'password'}
                autoComplete="new-password"
                required
                value={f.password}
                onChange={set('password')}
                aria-describedby="pw-rules"
                className={`${inputClass} pr-11`}
              />
              <button
                type="button"
                onClick={() => setShow(!show)}
                className="absolute right-1.5 top-[calc(50%+3px)] -translate-y-1/2 rounded-md p-2 text-ink-3 hover:bg-brand-50 hover:text-ink"
                aria-label={show ? 'Hide password' : 'Show password'}
              >
                {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            <ul id="pw-rules" className="mt-2 grid gap-1 text-xs">
              {checks.map((c) => (
                <li key={c.label} className={cn('flex items-center gap-1.5 transition-colors', c.ok ? 'text-good-ink' : 'text-ink-3')}>
                  {c.ok ? <Check className="size-3.5" aria-hidden /> : <Circle className="size-3" aria-hidden />}
                  {c.label}
                  <span className="sr-only">{c.ok ? '(met)' : '(not met yet)'}</span>
                </li>
              ))}
            </ul>
          </div>
        </fieldset>

        <fieldset className="space-y-5">
          <legend className="mb-4 text-xs font-semibold uppercase tracking-wider text-ink-3">Your business</legend>
          <Field label="Business name">
            <input autoComplete="organization" required value={f.business_name} onChange={set('business_name')} className={inputClass} />
          </Field>
          <Field label="Sector">
            <input list="sectors" required value={f.sector} onChange={set('sector')} className={inputClass} placeholder="Choose or type" />
            <datalist id="sectors">
              {SECTORS.map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
          </Field>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Opening cash (MUR)" hint="Cash in the bank on the date below.">
              <input
                inputMode="decimal"
                required
                value={f.opening_cash}
                onChange={set('opening_cash')}
                placeholder="0"
                className={cn(inputClass, 'tnum')}
              />
            </Field>
            <Field label="Balance date" hint="Your records start from this day.">
              <input
                type="date"
                required
                max={today()}
                value={f.opening_date}
                onChange={set('opening_date')}
                className={cn(inputClass, 'tnum')}
              />
            </Field>
          </div>
        </fieldset>

        <p className="flex gap-2.5 rounded-lg border border-line bg-surface px-3.5 py-3 text-xs leading-relaxed text-ink-2">
          <Info className="mt-0.5 size-4 shrink-0 text-accent-600" aria-hidden />
          <span>
            Your business starts empty. Nothing is generated for you: after signing up, import your transactions as a CSV from{' '}
            <strong className="font-medium text-ink">Data Health</strong>. Valora currently works in Mauritian rupees (MUR).
          </span>
        </p>

        {error && (
          <p role="alert" className="rounded-lg border border-bad/20 bg-bad-bg px-3 py-2 text-sm text-bad-ink">
            {error}
          </p>
        )}
        <Button type="submit" className="h-11 w-full text-[15px]" disabled={busy}>
          {busy ? 'Creating your account…' : 'Create account'}
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-ink-3">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent-700 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
