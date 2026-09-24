import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as client from '@/lib/api'
import type { Me } from '@/lib/types'

interface AuthState {
  me: Me | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (input: client.RegisterInput) => Promise<void>
  signOut: () => Promise<void>
  can: (permission: string) => boolean
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const qc = useQueryClient()

  const loadMe = useCallback(async () => {
    const m = await client.api<Me>('/auth/me')
    setMe(m)
  }, [])

  useEffect(() => {
    client.setSessionLostHandler(() => {
      setMe(null)
      qc.clear()
    })
    // Restore a session from the httpOnly refresh cookie, if any.
    ;(async () => {
      try {
        if (await client.refreshSession()) await loadMe()
      } finally {
        setLoading(false)
      }
    })()
  }, [loadMe, qc])

  const value = useMemo<AuthState>(
    () => ({
      me,
      loading,
      signIn: async (email, password) => {
        await client.login(email, password)
        await loadMe()
      },
      signUp: async (input) => {
        await client.register(input)
        await loadMe()
      },
      signOut: async () => {
        await client.logout()
        setMe(null)
        qc.clear()
      },
      can: (p) => !!me?.permissions.includes(p),
    }),
    [me, loading, loadMe, qc],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
