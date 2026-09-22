import type { RiskLevel, TransactionStatus } from '@/types/api'

export interface StatusStyle {
  label: string
  className: string
}

export const riskStyles: Record<RiskLevel, StatusStyle> = {
  LOW: { label: 'Low risk', className: 'text-[var(--color-success)] bg-[var(--color-success-soft)]' },
  MEDIUM: { label: 'Medium risk', className: 'text-[var(--color-warning)] bg-[var(--color-warning-soft)]' },
  HIGH: { label: 'High risk', className: 'text-[var(--color-danger)] bg-[var(--color-danger-soft)]' },
}

export const transactionStatusStyles: Record<TransactionStatus, StatusStyle> = {
  PENDING: { label: 'Pending review', className: 'text-[var(--color-info)] bg-[var(--color-info-soft)]' },
  RISK_REJECTED: { label: 'Rejected — risk', className: 'text-[var(--color-danger)] bg-[var(--color-danger-soft)]' },
  POLICY_REJECTED: { label: 'Rejected — policy', className: 'text-[var(--color-danger)] bg-[var(--color-danger-soft)]' },
  AWAITING_APPROVAL: { label: 'Awaiting your approval', className: 'text-[var(--color-warning)] bg-[var(--color-warning-soft)]' },
  APPROVED: { label: 'Approved', className: 'text-[var(--color-success)] bg-[var(--color-success-soft)]' },
  REJECTED_BY_USER: { label: 'Declined', className: 'text-[var(--color-text-muted)] bg-[var(--color-surface-raised)]' },
  SUBMITTED: { label: 'Submitted to Monad', className: 'text-[var(--color-info)] bg-[var(--color-info-soft)]' },
  CONFIRMED: { label: 'Confirmed', className: 'text-[var(--color-success)] bg-[var(--color-success-soft)]' },
  FAILED: { label: 'Failed on-chain', className: 'text-[var(--color-danger)] bg-[var(--color-danger-soft)]' },
}
