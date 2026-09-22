import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Send, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { StatusPill } from '@/components/ui/StatusPill'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'
import { RiskPanel, PolicyPanel } from '@/components/RiskPolicyPanel'
import { useAiQuery, useTransaction } from '@/hooks/queries'
import { ApiError } from '@/lib/api/client'
import { riskStyles, transactionStatusStyles } from '@/lib/statusStyles'
import { formatMon, formatPercent } from '@/lib/format'
import type { AIIntent, AIQueryResponse } from '@/types/api'

const intentLabels: Record<AIIntent, string> = {
  PORTFOLIO_ANALYSIS: 'Portfolio analysis',
  OPPORTUNITY_DISCOVERY: 'Opportunity discovery',
  COMPARISON: 'Comparison',
  TRANSACTION_PLAN: 'Transaction plan',
  EXPLANATION: 'Explanation',
  CLARIFICATION_NEEDED: 'Needs clarification',
}

const suggestions = [
  'What are the best yield opportunities right now?',
  'Deposit 10 MON into the safest protocol',
  "What's my current portfolio risk?",
]

interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  text: string
  response?: AIQueryResponse
  error?: string
}

/** Renders one AI Copilot turn: the recommendation/explanation, the risk
 * level, any opportunities or a proposed transaction, and -- once a
 * transaction has been created -- its live status plus a link to the
 * Transactions screen, which is the only place a transaction is actually
 * approved and signed (kept in one place so the sign flow is never
 * duplicated). */
function AiResponseCard({ response }: { response: AIQueryResponse }) {
  const { action, transaction_id, risk_level, transaction_status } = response
  const transaction = useTransaction(transaction_id ?? undefined)

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-full bg-[var(--color-surface-raised)] px-2.5 py-1 text-xs font-medium text-[var(--color-text-secondary)]">
          {intentLabels[action.intent]}
        </span>
        {risk_level && <StatusPill style={riskStyles[risk_level]} />}
      </div>

      <div>
        <p className="text-sm font-medium text-[var(--color-text-primary)]">{action.summary}</p>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{action.explanation}</p>
      </div>

      {action.clarifying_question && (
        <div className="rounded-xl bg-[var(--color-info-soft)] px-3 py-2 text-sm text-[var(--color-info)]">
          {action.clarifying_question}
        </div>
      )}

      {action.opportunities && action.opportunities.length > 0 && (
        <ul className="flex flex-col gap-2">
          {action.opportunities.map((opp, i) => (
            <li
              key={i}
              className="flex items-center justify-between gap-3 rounded-xl bg-[var(--color-surface-raised)] px-3 py-2.5"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-[var(--color-text-primary)]">
                  {opp.protocol} — {opp.action_type}
                </p>
                <p className="truncate text-xs text-[var(--color-text-muted)]">{opp.description}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {opp.estimated_apy_percent && (
                  <span className="text-xs font-semibold text-[var(--color-accent)]">
                    {formatPercent(opp.estimated_apy_percent)} APY
                  </span>
                )}
                <StatusPill style={riskStyles[opp.risk_category]} />
              </div>
            </li>
          ))}
        </ul>
      )}

      {action.proposed_transaction && (
        <div className="rounded-xl border border-[var(--color-border-strong)] p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
            Proposed transaction
          </p>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Operation</dt>
              <dd className="font-medium capitalize text-[var(--color-text-primary)]">
                {action.proposed_transaction.operation}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Amount</dt>
              <dd className="font-medium text-[var(--color-text-primary)]">{formatMon(action.proposed_transaction.amount)}</dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Protocol</dt>
              <dd className="font-medium text-[var(--color-text-primary)]">{action.proposed_transaction.protocol}</dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-[var(--color-text-secondary)]">{action.proposed_transaction.reasoning}</p>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">{action.proposed_transaction.risk_notes}</p>
        </div>
      )}

      {transaction_id && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[var(--color-surface-raised)] px-3 py-2.5">
          <div className="flex items-center gap-2">
            {transaction_status && <StatusPill style={transactionStatusStyles[transaction_status]} />}
            <span className="text-xs text-[var(--color-text-muted)]">Transaction created</span>
          </div>
          <Link
            to="/transactions"
            className="flex items-center gap-1 text-xs font-medium text-[var(--color-accent)] hover:underline"
          >
            Review & approve <ArrowRight className="size-3" />
          </Link>
        </div>
      )}

      {transaction.data?.risk_explanation && (
        <details className="rounded-xl border border-[var(--color-border)] p-3">
          <summary className="cursor-pointer text-xs font-medium text-[var(--color-text-secondary)]">
            Risk assessment detail
          </summary>
          <div className="mt-3">
            <RiskPanel risk={transaction.data.risk_explanation} />
          </div>
        </details>
      )}
      {transaction.data?.policy_decision && (
        <details className="rounded-xl border border-[var(--color-border)] p-3">
          <summary className="cursor-pointer text-xs font-medium text-[var(--color-text-secondary)]">
            Policy decision detail
          </summary>
          <div className="mt-3">
            <PolicyPanel decision={transaction.data.policy_decision} />
          </div>
        </details>
      )}
    </div>
  )
}

export function CopilotPage() {
  const [entries, setEntries] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const aiQuery = useAiQuery()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries, aiQuery.isPending])

  function send(message: string) {
    const trimmed = message.trim()
    if (!trimmed || aiQuery.isPending) return

    setEntries((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', text: trimmed }])
    setInput('')

    aiQuery.mutate(
      { message: trimmed },
      {
        onSuccess: (response) => {
          setEntries((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: 'assistant', text: response.action.summary, response },
          ])
        },
        onError: (err) => {
          setEntries((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: 'assistant',
              text: '',
              error: err instanceof ApiError ? err.message : 'Something went wrong asking the AI Copilot.',
            },
          ])
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">AI Copilot</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Ask in plain language. Every plan is checked by Risk and Policy before anything is proposed.
        </p>
      </div>

      <div className="min-h-[55vh] max-h-[70vh] overflow-y-auto rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        {entries.length === 0 ? (
          <EmptyState
            title="Ask NexaPilot anything"
            description="Try one of these, or type your own request below."
            icon={<Sparkles className="size-5" />}
            action={
              <div className="flex flex-wrap justify-center gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-full border border-[var(--color-border-strong)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]"
                  >
                    {s}
                  </button>
                ))}
              </div>
            }
          />
        ) : (
          <div className="flex flex-col gap-4">
            {entries.map((entry) => {
              if (entry.role === 'user') {
                return (
                  <div key={entry.id} className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl bg-[var(--color-accent-soft)] px-4 py-2.5 text-sm text-[var(--color-text-primary)]">
                      {entry.text}
                    </div>
                  </div>
                )
              }
              if (entry.error) {
                return (
                  <div key={entry.id} className="max-w-[85%]">
                    <ErrorState message={entry.error} />
                  </div>
                )
              }
              return (
                <div key={entry.id} className="max-w-[85%]">
                  <AiResponseCard response={entry.response as AIQueryResponse} />
                </div>
              )
            })}
            {aiQuery.isPending && (
              <div className="max-w-[85%]">
                <LoadingState label="NexaPilot is thinking…" />
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
        className="flex items-end gap-2"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(input)
            }
          }}
          rows={1}
          placeholder="Ask NexaPilot to analyze, compare, or act…"
          className="min-h-11 flex-1 resize-none rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none"
        />
        <Button type="submit" isLoading={aiQuery.isPending} disabled={!input.trim()}>
          <Send className="size-4" />
        </Button>
      </form>
    </div>
  )
}
