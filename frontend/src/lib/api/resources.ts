/** One thin function per backend endpoint -- no business logic, just the
 * HTTP call and its types. Every rule (risk, policy, validation) lives in
 * the backend; this file never re-implements any of it. */

import { apiRequest } from '@/lib/api/client'
import type {
  ActivityRead,
  AIQueryRequest,
  AIQueryResponse,
  NetworkStatusResponse,
  PolicyEvaluationRequest,
  PolicyEvaluationResponse,
  PolicyRead,
  PolicyUpdate,
  PolicyUsage,
  PrepareTransactionRequest,
  PreparedTransactionResponse,
  RiskAssessment,
  RiskAssessmentRequest,
  SubmitTransactionRequest,
  TokenResponse,
  TransactionRead,
  UserRead,
  UserUpdate,
  VerifyTransactionResponse,
  WalletBalanceResponse,
  WalletRead,
} from '@/types/api'

// --- auth ---

export function connectWallet(address: string, chain = 'monad') {
  return apiRequest<TokenResponse>('/auth/connect', {
    method: 'POST',
    body: { address, chain },
    unauthenticated: true,
  })
}

// --- users ---

export function getMe() {
  return apiRequest<UserRead>('/users/me')
}

export function updateMe(payload: UserUpdate) {
  return apiRequest<UserRead>('/users/me', { method: 'PATCH', body: payload })
}

// --- wallets ---

export function listWallets() {
  return apiRequest<WalletRead[]>('/wallets')
}

// --- policies (CRUD) ---

export function getMyPolicy() {
  return apiRequest<PolicyRead>('/policies/me')
}

export function updateMyPolicy(payload: PolicyUpdate) {
  return apiRequest<PolicyRead>('/policies/me', { method: 'PUT', body: payload })
}

// --- policy engine (Phase 4 what-if) ---

export function evaluatePolicy(payload: PolicyEvaluationRequest) {
  return apiRequest<PolicyEvaluationResponse>('/policy/evaluate', { method: 'POST', body: payload })
}

export function getPolicyUsage() {
  return apiRequest<PolicyUsage>('/policy/usage')
}

// --- risk engine (Phase 4 what-if) ---

export function assessRisk(payload: RiskAssessmentRequest) {
  return apiRequest<RiskAssessment>('/risk/assess', { method: 'POST', body: payload })
}

// --- transactions ---

export function listTransactions() {
  return apiRequest<TransactionRead[]>('/transactions')
}

export function getTransaction(id: string) {
  return apiRequest<TransactionRead>(`/transactions/${id}`)
}

// --- activity ---

export function listActivity() {
  return apiRequest<ActivityRead[]>('/activity')
}

// --- AI copilot ---

export function queryAi(payload: AIQueryRequest) {
  return apiRequest<AIQueryResponse>('/ai/query', { method: 'POST', body: payload })
}

// --- blockchain ---

export function getNetworkStatus() {
  return apiRequest<NetworkStatusResponse>('/blockchain/network')
}

export function getWalletBalance(walletId: string) {
  return apiRequest<WalletBalanceResponse>(`/blockchain/wallets/${walletId}/balance`)
}

export function prepareTransaction(payload: PrepareTransactionRequest) {
  return apiRequest<PreparedTransactionResponse>('/blockchain/transactions/prepare', {
    method: 'POST',
    body: payload,
  })
}

export function approveTransaction(id: string) {
  return apiRequest<TransactionRead>(`/blockchain/transactions/${id}/approve`, { method: 'POST' })
}

export function submitTransaction(id: string, payload: SubmitTransactionRequest) {
  return apiRequest<TransactionRead>(`/blockchain/transactions/${id}/submit`, {
    method: 'POST',
    body: payload,
  })
}

export function verifyTransaction(id: string) {
  return apiRequest<VerifyTransactionResponse>(`/blockchain/transactions/${id}/verify`, { method: 'POST' })
}
