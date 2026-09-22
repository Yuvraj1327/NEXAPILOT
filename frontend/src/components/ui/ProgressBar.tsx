import clsx from 'clsx'

export function ProgressBar({ fraction, tone = 'accent' }: { fraction: number; tone?: 'accent' | 'warning' | 'danger' }) {
  const clamped = Math.max(0, Math.min(1, fraction))
  const colors: Record<typeof tone, string> = {
    accent: 'bg-[var(--color-accent)]',
    warning: 'bg-[var(--color-warning)]',
    danger: 'bg-[var(--color-danger)]',
  }
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-raised)]">
      <div
        className={clsx('h-full rounded-full transition-[width]', colors[tone])}
        style={{ width: `${clamped * 100}%` }}
      />
    </div>
  )
}
