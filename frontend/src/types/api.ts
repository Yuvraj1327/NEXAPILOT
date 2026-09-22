/**
 * TypeScript mirrors of the backend's Pydantic schemas (see
 * backend/app/schemas/*.py and backend/app/models/enums.py). Kept as
 * plain types with no validation logic of their own -- the backend is the
 * single source of truth for every rule; this file only describes the
 * JSON shapes so the frontend can stay type-safe without re-implementing
 * anything.
 */

// --- enums (app/models/enums.py) ---

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export type TransactionStatus =
  | 'PENDING'
  | 'RISK_REJECTED'
  | 'POLICY_REJECTED'
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED_BY_USER'
  | 'SUBMITTED'
  | 'CONFIRMED'
  | 'FAILED'

export type ActivityType = 'TRANSACTION' | 'PORTFOLIO_UPDATE' | 'RECOMMENDATION' | 'SYSTEM'

export type OperationType = 'deposit' | 'withdraw' | 'execute'

// --- auth / users / wallets (app/schemas/{auth,user,wallet}.py) ---

export interface UserRead {
  id: string
  created_at: string
  updated_at: string
  display_name: string | null
  risk_preference: RiskLevel
  is_active: boolean
}

export interface UserUpdate {
  display_name?: string | null
  risk_preference?: RiskLevel | null
}

export interface WalletRead {
  id: string
  created_at: string
  updated_at: string
  address: string
  chain: string
  is_primary: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserRead
  wallet: WalletRead
}

// --- policy (app/schemas/policy.py) ---

export interface PolicyRead {
  id: string
  created_at: string
  updated_at: string
  max_transaction_amount: string
  daily_limit: string
  allowed_protocols: string[]
  allowed_actions: string[]
  max_risk_level: RiskLevel
  approval_required: boolean
}

export interface PolicyUpdate {
  max_transaction_amount: string
  daily_limit: string
  allowed_protocols: string[]
  allowed_actions: string[]
  max_risk_level: RiskLevel
  approval_required: boolean
}

export interface PolicyCheckResult {
  rule: string
  passed: boolean
  detail: string
}

export interface PolicyDecision {
  passed: boolean
  requires_approval: boolean
  checks: PolicyCheckResult[]
  reasons: string[]
}

export interface PolicyEvaluationRequest {
  operation: OperationType
  amount: string
  protocol: string
  action_type?: string | null
}

export interface PolicyEvaluationResponse {
  risk_level: RiskLevel
  risk_score: number
  policy_decision: PolicyDecision
  final_status: TransactionStatus
}

export interface PolicyUsage {
  daily_limit: string
  spent_today: string
  remaining_today: string
}

// --- risk (app/schemas/risk.py) ---

export interface RiskFactor {
  name: string
  detail: string
  raw_value: string | null
  score: number
  weight_percent: number
  contribution: number
}

export interface RiskAssessment {
  risk_level: RiskLevel
  score: number
  summary: string
  factors: RiskFactor[]
}

export interface RiskAssessmentRequest {
  operation: OperationType
  amount: string
  protocol: string
  action_type?: string | null
}

// --- transactions (app/schemas/transaction.py) ---

export interface TransactionRead {
  id: string
  created_at: string
  updated_at: string
  wallet_id: string
  action_type: string
  protocol: string
  token_in: string
  amount_in: string
  token_out: string | null
  amount_out: string | null
  status: TransactionStatus
  risk_level: RiskLevel | null
  risk_explanation: RiskAssessment | null
  policy_decision: PolicyDecision | null
  chain: string
  tx_hash: string | null
  target_contract: string | null
  calldata: string | null
  block_number: number | null
  confirmed_at: string | null
}

// --- activity (app/schemas/activity.py) ---

export interface ActivityRead {
  id: string
  created_at: string
  updated_at: string
  type: ActivityType
  title: string
  description: string | null
  related_transaction_id: string | null
  activity_metadata: Record<string, unknown> | null
}

// --- AI (app/schemas/ai.py) ---

export type AIIntent =
  | 'PORTFOLIO_ANALYSIS'
  | 'OPPORTUNITY_DISCOVERY'
  | 'COMPARISON'
  | 'TRANSACTION_PLAN'
  | 'EXPLANATION'
  | 'CLARIFICATION_NEEDED'

export interface OpportunityItem {
  protocol: string
  action_type: string
  estimated_apy_percent: string | null
  risk_category: RiskLevel
  description: string
}

export interface ProposedTransactionAction {
  operation: OperationType
  amount: string
  protocol: string
  action_type: string | null
  target_contract: string | null
  reasoning: string
  risk_notes: string
}

export interface NexaPilotAIAction {
  intent: AIIntent
  summary: string
  explanation: string
  opportunities: OpportunityItem[] | null
  proposed_transaction: ProposedTransactionAction | null
  clarifying_question: string | null
}

export interface AIQueryRequest {
  message: string
}

export interface AIQueryResponse {
  action: NexaPilotAIAction
  transaction_id: string | null
  tools_used: string[]
  transaction_status: TransactionStatus | null
  risk_level: RiskLevel | null
}

// --- blockchain (app/schemas/blockchain.py) ---

export interface PrepareTransactionRequest {
  wallet_id: string
  operation: OperationType
  amount: string
  protocol?: string
  action_type?: string | null
  target_contract?: string | null
  calldata?: string
}

export interface UnsignedTransactionOut {
  from: string
  to: string
  data: string
  value: string
  nonce: string
  chainId: string
  gas: string
  maxFeePerGas?: string | null
  maxPriorityFeePerGas?: string | null
  gasPrice?: string | null
  type?: string | null
}

export interface PreparedTransactionResponse {
  transaction_id: string
  unsigned_tx: UnsignedTransactionOut
}

export interface SubmitTransactionRequest {
  signed_raw_tx: string
}

export interface VerifyTransactionResponse {
  transaction_id: string
  status: TransactionStatus
  tx_hash: string | null
  block_number: number | null
  confirmations: number | null
  message: string
}

export interface WalletBalanceResponse {
  address: string
  chain: string
  native_balance: string
  vault_balance: string
  as_of_block: number | null
}

export interface NetworkStatusResponse {
  connected: boolean
  chain_id: number | null
  expected_chain_id: number
  chain_id_matches: boolean | null
  latest_block: number | null
  rpc_url: string
  network: string
  contract_address: string | null
  error: string | null
}

// --- error envelope (app/core/exceptions.py) ---

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details?: unknown
  }
}
