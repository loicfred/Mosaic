import { vi } from 'vitest'
import { api, setAccessToken } from '@/lib/api'

describe('api client', () => {
  it('refreshes once on 401 then retries with the new token, keeping tokens out of URLs', async () => {
    setAccessToken('old')
    const seen: { url: string; auth?: string; csrf?: string }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init: RequestInit) => {
        const h = (init.headers ?? {}) as Record<string, string>
        seen.push({ url, auth: h.Authorization, csrf: h['X-Requested-With'] })
        if (url.endsWith('/auth/refresh')) return new Response(JSON.stringify({ access_token: 'new' }), { status: 200 })
        if (h.Authorization === 'Bearer old') return new Response('{}', { status: 401 })
        return new Response(JSON.stringify({ ok: true }), { status: 200 })
      }),
    )
    await expect(api('/analytics/overview')).resolves.toEqual({ ok: true })
    expect(seen.map((s) => s.url)).toEqual(['/api/v1/analytics/overview', '/api/v1/auth/refresh', '/api/v1/analytics/overview'])
    expect(seen[1].csrf).toBe('Valora')
    expect(seen[2].auth).toBe('Bearer new')
    expect(seen.every((s) => !s.url.includes('token'))).toBe(true)
  })
})
