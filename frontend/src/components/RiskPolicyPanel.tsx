import { CheckCircle2, XCircle } from 'lucide-react'
import clsx from 'clsx'
import { StatusPill } from '@/components/ui/StatusPill'
import { riskStyles } from '@/lib/statusStyles'
import { formatPercent } from '@/lib/format'
import type { PolicyDecision, RiskAssessment } from '@/types/api'

/** Renders a backend RiskAssessment exactly as returned by the Risk engine
 * (app/schemas/risk.py) -- no score/level is ever recomputed client-side. */
export function RiskPanel({ risk }: { risk: RiskAssessment }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <StatusPill style={riskStyles[risk.risk_level]} />
        <span className="text-xs text-[var(--color-text-muted)]">Score {risk.score.toFixed(0)} / 100</span>
      </div>
      <p className="text-sm text-[var(--color-text-secondary)]">{risk.summary}</p>
      {risk.factors.length > 0 && (
        <ul className="flex flex-col gap-2">
          {risk.factors.map((factor) => (
            <li
              key={factor.name}
              className="flex items-center justify-between gap-3 rounded-lg bg-[var(--color-surface-raised)] px-3 py-2 text-xs"
            >
              <div className="min-w-0">
                <p className="font-medium text-[var(--color-text-primary)]">{factor.name}</p>
                <p className="truncate text-[var(--color-text-muted)]">{factor.detail}</p>
              </div>
              <span className="shrink-0 text-[var(--color-text-secondary)]">{formatPercent(factor.weight_percent)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Renders a backend PolicyDecision exactly as returned by the Policy
 * engine (app/schemas/policy.py) -- pass/fail and every check comes from
 * the backend; this only lays it out. */
export function PolicyPanel({ decision }: { decision: PolicyDecision }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={clsx(
            'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
            decision.passed
              ? 'bg-[var(--color-success-soft)] text-[var(--color-success)]'
              : 'bg-[var(--color-danger-soft)] text-[var(--color-danger)]',
          )}
        >
          {decision.passed ? 'Policy passed' : 'Policy failed'}
        </span>
        {decision.requires_approval && (
          <span className="inline-flex items-center rounded-full bg-[var(--color-warning-soft)] px-2.5 py-1 text-xs font-medium text-[var(--color-warning)]">
            Requires approval
          </span>
        )}
      </div>
      {decision.reasons.length > 0 && (
        <ul className="list-disc space-y-1 pl-4 text-xs text-[var(--color-text-secondary)]">
          {decision.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      {decision.checks.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {decision.checks.map((check) => (
            <li key={check.rule} className="flex items-start gap-2 text-xs">
              {check.passed ? (
                <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-[var(--color-success)]" />
              ) : (
                <XCircle className="mt-0.5 size-3.5 shrink-0 text-[var(--color-danger)]" />
              )}
              <span className="text-[var(--color-text-secondary)]">
                <span className="font-medium text-[var(--color-text-primary)]">{check.rule}:</span> {check.detail}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
