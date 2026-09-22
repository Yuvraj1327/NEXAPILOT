import { useState } from 'react'
import { CheckCircle2, ChevronDown, RefreshCw, Wallet2 } from 'lucide-react'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatusPill } from '@/components/ui/StatusPill'
import { AsyncSection } from '@/components/ui/AsyncSection'
import { RiskPanel, PolicyPanel } from '@/components/RiskPolicyPanel'
import {
  useApproveTransaction,
  usePrepareTransaction,
  useSubmitTransaction,
  useTransactions,
  useVerifyTransaction,
} from '@/hooks/queries'
import { useWalletSession } from '@/lib/web3/WalletSessionContext'
import { ApiError } from '@/lib/api/client'
import { riskStyles, transactionStatusStyles } from '@/lib/statusStyles'
import { formatDateTime, formatMon, truncateAddress } from '@/lib/format'
import type { OperationType, TransactionRead } from '@/types/api'

/** AI-created transactions never carry an unsigned_tx of their own (only
 * POST /blockchain/transactions/prepare populates that) -- see the
 * architecture note in blockchain.py. So "Review & sign" always calls
 * /prepare fresh with this row's own operation/amount/protocol, which
 * mints a new transaction record with a real unsigned_tx to approve, sign
 * and submit. Nothing about risk/policy is re-decided here; it already
 * happened for the row being reviewed. */
function toOperationType(actionType: string): OperationType {
  const lower = actionType.toLowerCase()
  if (lower === 'deposit' || lower === 'withdraw' || lower === 'execute') return lower
  return 'execute'
}

type FlowState =
  | { step: 'idle' }
  | { step: 'preparing' | 'approving' | 'signing' | 'submitting' | 'verifying' }
  | { step: 'done'; txHash: string | null; status: string }
  | { step: 'error'; message: string }

const flowLabels: Record<string, string> = {
  preparing: 'Preparing transaction…',
  approving: 'Recording your approval…',
  signing: 'Waiting for wallet signature…',
  submitting: 'Submitting to Monad…',
  verifying: 'Confirming on-chain…',
}

function TransactionCard({ tx }: { tx: TransactionRead }) {
  const [flow, setFlow] = useState<FlowState>({ step: 'idle' })
  const [expanded, setExpanded] = useState(false)
  const walletSession = useWalletSession()
  const prepare = usePrepareTransaction()
  const approve = useApproveTransaction()
  const submit = useSubmitTransaction()
  const verify = useVerifyTransaction()

  const busy = flow.step !== 'idle' && flow.step !== 'done' && flow.step !== 'error'

  async function reviewAndSign() {
    setFlow({ step: 'preparing' })
    try {
      const prepared = await prepare.mutateAsync({
        wallet_id: tx.wallet_id,
        operation: toOperationType(tx.action_type),
        amount: tx.amount_in,
        protocol: tx.protocol,
        target_contract: tx.target_contract ?? undefined,
      })

      setFlow({ step: 'approving' })
      await approve.mutateAsync(prepared.transaction_id)

      setFlow({ step: 'signing' })
      const signedRawTx = await walletSession.signTransaction(prepared.unsigned_tx)

      setFlow({ step: 'submitting' })
      await submit.mutateAsync({ id: prepared.transaction_id, payload: { signed_raw_tx: signedRawTx } })

      setFlow({ step: 'verifying' })
      const verified = await verify.mutateAsync(prepared.transaction_id)
      setFlow({ step: 'done', txHash: verified.tx_hash, status: verified.status })
    } catch (err) {
      setFlow({
        step: 'error',
        message: err instanceof ApiError ? err.message : 'Something went wrong while signing this transaction.',
      })
    }
  }

  async function recheckStatus() {
    setFlow({ step: 'verifying' })
    try {
      const verified = await verify.mutateAsync(tx.id)
      setFlow({ step: 'done', txHash: verified.tx_hash, status: verified.status })
    } catch (err) {
      setFlow({
        step: 'error',
        message: err instanceof ApiError ? err.message : 'Could not check this transaction right now.',
      })
    }
  }

  return (
    <Card>
      <CardBody>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[var(--color-text-primary)]">
                {tx.action_type} · {tx.protocol}
              </p>
              <p className="text-xs text-[var(--color-text-muted)]">{formatDateTime(tx.created_at)}</p>
            </div>
            <div className="flex items-center gap-2">
              {tx.risk_level && <StatusPill style={riskStyles[tx.risk_level]} />}
              <StatusPill style={transactionStatusStyles[tx.status]} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-[var(--color-text-muted)]">Amount</p>
              <p className="font-medium text-[var(--color-text-primary)]">{formatMon(tx.amount_in)}</p>
            </div>
            {tx.amount_out && (
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">Amount out</p>
                <p className="font-medium text-[var(--color-text-primary)]">{formatMon(tx.amount_out)}</p>
              </div>
            )}
            {tx.tx_hash && (
              <div className="col-span-2">
                <p className="text-xs text-[var(--color-text-muted)]">Tx hash</p>
                <p className="truncate font-mono text-xs text-[var(--color-text-secondary)]">
                  {truncateAddress(tx.tx_hash, 8)}
                </p>
              </div>
            )}
          </div>

          {(tx.risk_explanation || tx.policy_decision) && (
            <div>
              <button
                onClick={() => setExpanded((v) => !v)}
                className="flex items-center gap-1 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              >
                <ChevronDown className={`size-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                {expanded ? 'Hide' : 'Show'} risk & policy detail
              </button>
              {expanded && (
                <div className="mt-3 grid grid-cols-1 gap-4 border-t border-[var(--color-border)] pt-3 lg:grid-cols-2">
                  {tx.risk_explanation && <RiskPanel risk={tx.risk_explanation} />}
                  {tx.policy_decision && <PolicyPanel decision={tx.policy_decision} />}
                </div>
              )}
            </div>
          )}

          {flow.step === 'error' && (
            <p className="rounded-lg bg-[var(--color-danger-soft)] px-3 py-2 text-xs text-[var(--color-danger)]">
              {flow.message}
            </p>
          )}
          {flow.step === 'done' && (
            <p className="flex flex-wrap items-center gap-1.5 rounded-lg bg-[var(--color-success-soft)] px-3 py-2 text-xs text-[var(--color-success)]">
              <CheckCircle2 className="size-3.5" />
              {flow.status === 'CONFIRMED' ? 'Confirmed on-chain.' : `Status: ${flow.status}.`}
              {flow.txHash && ` Tx ${truncateAddress(flow.txHash, 6)}`}
            </p>
          )}
          {busy && <p className="text-xs text-[var(--color-text-muted)]">{flowLabels[flow.step]}</p>}

          <div className="flex justify-end gap-2">
            {tx.status === 'AWAITING_APPROVAL' && (
              <Button size="sm" onClick={reviewAndSign} isLoading={busy}>
                <Wallet2 className="size-4" /> Review & sign
              </Button>
            )}
            {tx.status === 'SUBMITTED' && (
              <Button size="sm" variant="secondary" onClick={recheckStatus} isLoading={flow.step === 'verifying'}>
                <RefreshCw className="size-4" /> Check status
              </Button>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

export function TransactionsPage() {
  const transactions = useTransactions()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Transaction review</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Every AI-proposed action lands here after passing Risk and Policy. Nothing is signed or sent without your
          explicit approval.
        </p>
      </div>

      <AsyncSection
        isLoading={transactions.isLoading}
        error={transactions.error}
        data={transactions.data}
        onRetry={() => transactions.refetch()}
        isEmpty={(data) => data.length === 0}
        emptyTitle="No transactions yet"
        emptyDescription="Ask the AI Copilot to propose an action to see it here."
        emptyIcon={<Wallet2 className="size-5" />}
      >
        {(data) => (
          <div className="flex flex-col gap-4">
            {[...data]
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .map((tx) => (
                <TransactionCard key={tx.id} tx={tx} />
              ))}
          </div>
        )}
      </AsyncSection>
    </div>
  )
}
