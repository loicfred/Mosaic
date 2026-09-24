import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  AuditEvent,
  Assumptions,
  Facets,
  ImportBatch,
  LedgerHealth,
  Lever,
  Opportunity,
  OppStatus,
  Overview,
  Proposal,
  SimulationResult,
  Transaction,
  TransactionDetail,
} from '@/lib/types'

export const useOverview = () => useQuery({ queryKey: ['overview'], queryFn: () => api<Overview>('/analytics/overview') })
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useInsights = () => useQuery({ queryKey: ['insights'], queryFn: () => api<any>('/insights') })

export const useOpportunities = (includeInactive = false) =>
  useQuery({
    queryKey: ['opportunities', includeInactive],
    queryFn: () => api<Opportunity[]>(`/opportunities?include_inactive=${includeInactive}`),
  })

export const useOpportunity = (id: string | null) =>
  useQuery({ queryKey: ['opportunity', id], queryFn: () => api<Opportunity>(`/opportunities/${id}`), enabled: !!id })

export function useChangeStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status, note }: { id: string; status: OppStatus; note?: string }) =>
      api<Opportunity>(`/opportunities/${id}/status`, { method: 'PATCH', body: { status, note: note || null } }),
    onSuccess: (_, v) => {
      qc.invalidateQueries({ queryKey: ['opportunities'] })
      qc.invalidateQueries({ queryKey: ['opportunity', v.id] })
    },
  })
}

export function useAddNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) => api<void>(`/opportunities/${id}/notes`, { method: 'POST', body: { note } }),
    onSuccess: (_, v) => qc.invalidateQueries({ queryKey: ['opportunity', v.id] }),
  })
}

export function useRefreshEngine() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<{ detected: number }>('/opportunities/refresh', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export const useTransactions = (params: Record<string, string | number | undefined>) => {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== '') as [string, string][]).toString()
  return useQuery({
    queryKey: ['transactions', qs],
    queryFn: () => api<{ items: Transaction[]; total: number; page: number; page_size: number }>(`/transactions?${qs}`),
    placeholderData: keepPreviousData,
  })
}

export const useTransaction = (id: string | null) =>
  useQuery({ queryKey: ['transaction', id], queryFn: () => api<TransactionDetail>(`/transactions/${id}`), enabled: !!id })

export const useFacets = () => useQuery({ queryKey: ['facets'], queryFn: () => api<Facets>('/transactions/facets') })

export const useLookup = (ids: string[]) =>
  useQuery({
    queryKey: ['lookup', ids.join(',')],
    queryFn: () => api<Transaction[]>('/transactions/lookup', { method: 'POST', body: ids.slice(0, 50) }),
    enabled: ids.length > 0,
  })

export const useHealth = () => useQuery({ queryKey: ['health'], queryFn: () => api<LedgerHealth>('/data-quality/health') })
export const useProposals = (status = 'pending') =>
  useQuery({ queryKey: ['proposals', status], queryFn: () => api<Proposal[]>(`/data-quality/proposals?status=${status}`) })
export const useImports = () => useQuery({ queryKey: ['imports'], queryFn: () => api<ImportBatch[]>('/data-quality/imports') })
export const useImport = (id: string | null) =>
  useQuery({ queryKey: ['import', id], queryFn: () => api<ImportBatch>(`/data-quality/imports/${id}`), enabled: !!id })

export function useDecision() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, decision, newValue }: { id: string; decision: 'approve' | 'reject'; newValue?: string }) =>
      api(`/data-quality/proposals/${id}/decision`, { method: 'POST', body: { decision, new_value: newValue ?? null } }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export function useUpload() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api<ImportBatch>('/data-quality/imports', { method: 'POST', form })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['imports'] }),
  })
}

export function useBatchAction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'commit' | 'discard' }) =>
      api<ImportBatch>(`/data-quality/imports/${id}/${action}`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export const useLevers = () => useQuery({ queryKey: ['levers'], queryFn: () => api<Lever[]>('/scenarios/levers'), staleTime: Infinity })

export function useSimulate(assumptions: Assumptions) {
  return useQuery({
    queryKey: ['simulate', assumptions],
    queryFn: ({ signal }) =>
      api<SimulationResult>('/scenarios/simulate', { method: 'POST', body: { assumptions, horizon_days: 90 }, signal }),
    placeholderData: keepPreviousData,
  })
}

export const useSavedScenarios = () =>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useQuery({ queryKey: ['scenarios'], queryFn: () => api<any[]>('/scenarios') })

export function useSaveScenario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: { name: string; assumptions: Assumptions; opportunity_id?: string | null }) =>
      api('/scenarios', { method: 'POST', body: b }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scenarios'] }),
  })
}

export const useAudit = (category?: string, enabled = true) =>
  useQuery({
    queryKey: ['audit', category],
    queryFn: () => api<AuditEvent[]>(`/audit/events?limit=200${category ? `&category=${category}` : ''}`),
    enabled,
  })
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useSecuritySummary = () => useQuery({ queryKey: ['security'], queryFn: () => api<any>('/audit/security-summary') })
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useModels = () => useQuery({ queryKey: ['models'], queryFn: () => api<any>('/ml/models') })
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useCashPressure = () => useQuery({ queryKey: ['cash-pressure'], queryFn: () => api<any>('/ml/cash-pressure') })
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useBrief = () => useQuery({ queryKey: ['brief'], queryFn: () => api<any>('/reports/decision-brief') })
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useBusiness = () => useQuery({ queryKey: ['business'], queryFn: () => api<any>('/business') })
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useMembers = (enabled: boolean) => useQuery({ queryKey: ['members'], queryFn: () => api<any[]>('/business/members'), enabled })
