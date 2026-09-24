/**
 * API client.
 * - The access token lives only in memory (never localStorage, never in URLs).
 * - The refresh token is an httpOnly cookie the browser sends to /api/v1/auth only.
 * - On a 401 the client refreshes once (single flight) and retries.
 */

const BASE = '/api/v1'
const CSRF = { 'X-Requested-With': 'Valora' }

let accessToken: string | null = null
let refreshing: Promise<boolean> | null = null
let onSessionLost: (() => void) | null = null

export class ApiError extends Error {
  status: number
  code: string
  details: unknown
  requestId?: string
  constructor(status: number, code: string, message: string, details?: unknown, requestId?: string) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }
}

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function hasAccessToken() {
  return accessToken !== null
}

export function setSessionLostHandler(fn: () => void) {
  onSessionLost = fn
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json()
    const e = body?.error ?? {}
    return new ApiError(res.status, e.code ?? 'error', e.message ?? res.statusText, e.details, e.request_id)
  } catch {
    return new ApiError(res.status, 'error', res.statusText || 'Request failed')
  }
}

export async function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, { method: 'POST', credentials: 'same-origin', headers: CSRF })
        if (!res.ok) {
          accessToken = null
          return false
        }
        const body = await res.json()
        accessToken = body.access_token
        return true
      } catch {
        return false
      } finally {
        setTimeout(() => (refreshing = null), 0)
      }
    })()
  }
  return refreshing
}

type Options = { method?: string; body?: unknown; form?: FormData; signal?: AbortSignal }

export async function api<T>(path: string, opts: Options = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = {}
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  let body: BodyInit | undefined
  if (opts.form) body = opts.form
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const res = await fetch(`${BASE}${path}`, {
    method: opts.method ?? 'GET',
    headers,
    body,
    credentials: 'same-origin',
    signal: opts.signal,
  })
  if (res.status === 401 && retry && !path.startsWith('/auth/login') && !path.startsWith('/auth/register')) {
    if (await refreshSession()) return api<T>(path, opts, false)
    onSessionLost?.()
  }
  if (!res.ok) throw await parseError(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export async function login(email: string, password: string) {
  const res = await api<{ access_token: string }>('/auth/login', { method: 'POST', body: { email, password } }, false)
  accessToken = res.access_token
}

export interface RegisterInput {
  full_name: string
  email: string
  password: string
  business_name: string
  sector: string
  opening_cash: string
  opening_date: string
}

/** Creates an owner account and an empty business, then signs in (refresh cookie set by the server). */
export async function register(input: RegisterInput) {
  const res = await api<{ access_token: string }>('/auth/register', { method: 'POST', body: input }, false)
  accessToken = res.access_token
}

export async function logout() {
  try {
    await fetch(`${BASE}/auth/logout`, { method: 'POST', credentials: 'same-origin', headers: CSRF })
  } finally {
    accessToken = null
  }
}
