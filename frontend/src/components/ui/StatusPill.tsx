import clsx from 'clsx'
import type { StatusStyle } from '@/lib/statusStyles'

export function StatusPill({ style, className }: { style: StatusStyle; className?: string }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap',
        style.className,
        className,
      )}
    >
      {style.label}
    </span>
  )
}
