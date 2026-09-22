import type { ReactNode } from 'react'

export function StatTile({
  label,
  value,
  hint,
  icon,
  children,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  children?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">{label}</span>
        {icon}
      </div>
      <span className="text-2xl font-semibold text-[var(--color-text-primary)]">{value}</span>
      {hint && <span className="text-xs text-[var(--color-text-secondary)]">{hint}</span>}
      {children}
    </div>
  )
}
