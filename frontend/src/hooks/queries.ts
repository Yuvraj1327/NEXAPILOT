import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from '@/lib/api/resources'
import { useSession } from '@/lib/auth/SessionContext'
import type {
  AIQueryRequest,
  PolicyEvaluationRequest,
  PolicyUpdate,
  PrepareTransactionRequest,
  RiskAssessmentRequest,
  SubmitTransactionRequest,
  UserUpdate,
} from '@/types/api'

/** `enabled: ready` on every query below -- nothing hits the backend
 * before the wallet -> /auth/connect handshake (SessionContext) has
 * actually produced a token. */
function useReady() {
  return useSession().status === 'ready'
}

export function useMyPolicy() {
  const ready = useReady()
  return useQuery({ queryKey: ['policy', 'me'], queryFn: api.getMyPolicy, enabled: ready })
}

export function usePolicyUsage() {
  const ready = useReady()
  return useQuery({ queryKey: ['policy', 'usage'], queryFn: api.getPolicyUsage, enabled: ready })
}

export function useWallets() {
  const ready = useReady()
  return useQuery({ queryKey: ['wallets'], queryFn: api.listWallets, enabled: ready })
}

export function useWalletBalance(walletId: string | undefined) {
  const ready = useReady()
  return useQuery({
    queryKey: ['blockchain', 'balance', walletId],
    queryFn: () => api.getWalletBalance(walletId as string),
    enabled: ready && Boolean(walletId),
    refetchInterval: 15_000,
  })
}

export function useNetworkStatus() {
  return useQuery({
    queryKey: ['blockchain', 'network'],
    queryFn: api.getNetworkStatus,
    refetchInterval: 20_000,
  })
}

export function useTransactions() {
  const ready = useReady()
  return useQuery({ queryKey: ['transactions'], queryFn: api.listTransactions, enabled: ready })
}

export function useTransaction(id: string | undefined) {
  const ready = useReady()
  return useQuery({
    queryKey: ['transactions', id],
    queryFn: () => api.getTransaction(id as string),
    enabled: ready && Boolean(id),
  })
}

export function useActivity() {
  const ready = useReady()
  return useQuery({ queryKey: ['activity'], queryFn: api.listActivity, enabled: ready })
}

export function useUpdatePolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: PolicyUpdate) => api.updateMyPolicy(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policy'] })
    },
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: UserUpdate) => api.updateMe(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useAiQuery() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: AIQueryRequest) => api.queryAi(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['activity'] })
      queryClient.invalidateQueries({ queryKey: ['policy', 'usage'] })
    },
  })
}

export function useAssessRisk() {
  return useMutation({ mutationFn: (payload: RiskAssessmentRequest) => api.assessRisk(payload) })
}

export function useEvaluatePolicy() {
  return useMutation({ mutationFn: (payload: PolicyEvaluationRequest) => api.evaluatePolicy(payload) })
}

export function usePrepareTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: PrepareTransactionRequest) => api.prepareTransaction(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

export function useApproveTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.approveTransaction(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['transactions'] }),
  })
}

export function useSubmitTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SubmitTransactionRequest }) => api.submitTransaction(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['activity'] })
    },
  })
}

export function useVerifyTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.verifyTransaction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['activity'] })
      queryClient.invalidateQueries({ queryKey: ['blockchain', 'balance'] })
    },
  })
}
