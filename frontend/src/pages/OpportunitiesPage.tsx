import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { AsyncSection } from '@/components/ui/AsyncSection'
import { StatusPill } from '@/components/ui/StatusPill'
import { useAiQuery } from '@/hooks/queries'
import { riskStyles } from '@/lib/statusStyles'
import { formatPercent } from '@/lib/format'

/** There's no dedicated "list opportunities" backend endpoint -- the AI
 * Copilot (POST /ai/query) is the single source of opportunity data, so
 * this screen asks it the same question a person would and renders
 * whatever OpportunityItem[] it returns, rather than inventing a separate
 * opportunities dataset on the frontend. */
const OPPORTUNITIES_PROMPT = 'What are the best yield opportunities available right now, across all allowed protocols?'

export function OpportunitiesPage() {
  const aiQuery = useAiQuery()

  useEffect(() => {
    aiQuery.mutate({ message: OPPORTUNITIES_PROMPT })
    // Fire once on mount only -- refreshing is a manual, explicit action.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const opportunities = aiQuery.data ? (aiQuery.data.action.opportunities ?? []) : undefined

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Opportunities</h1>
          <p className="text-sm text-[var(--color-text-secondary)]">
            AI-surfaced yield opportunities across your allowed protocols.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => aiQuery.mutate({ message: OPPORTUNITIES_PROMPT })}
          isLoading={aiQuery.isPending}
        >
          <RefreshCw className="size-4" /> Refresh
        </Button>
      </div>

      <AsyncSection
        isLoading={aiQuery.isPending}
        error={aiQuery.error}
        data={opportunities}
        onRetry={() => aiQuery.mutate({ message: OPPORTUNITIES_PROMPT })}
        isEmpty={(data) => data.length === 0}
        emptyTitle="No opportunities surfaced"
        emptyDescription="The AI Copilot didn't find any matching opportunities just now. Try asking it directly in the Copilot tab."
        emptyIcon={<Sparkles className="size-5" />}
      >
        {(data) => (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.map((opp, i) => (
              <div
                key={i}
                className="flex flex-col gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-[var(--color-text-primary)]">{opp.protocol}</p>
                    <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">{opp.action_type}</p>
                  </div>
                  <StatusPill style={riskStyles[opp.risk_category]} />
                </div>
                <p className="text-sm text-[var(--color-text-secondary)]">{opp.description}</p>
                <div className="mt-auto flex items-center justify-between pt-2">
                  {opp.estimated_apy_percent ? (
                    <span className="text-lg font-semibold text-[var(--color-accent)]">
                      {formatPercent(opp.estimated_apy_percent)}{' '}
                      <span className="text-xs font-normal text-[var(--color-text-muted)]">APY</span>
                    </span>
                  ) : (
                    <span className="text-xs text-[var(--color-text-muted)]">APY not estimated</span>
                  )}
                  <Link to="/copilot" className="text-xs font-medium text-[var(--color-accent)] hover:underline">
                    Ask Copilot
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </AsyncSection>
    </div>
  )
}
