import { Link } from 'react-router-dom'
import { ArrowRight, Info, Sparkles, TrendingUp, Wallet2 } from 'lucide-react'
import type { ComponentType } from 'react'
import type { ActivityRead, ActivityType } from '@/types/api'
import { formatRelativeTime } from '@/lib/format'

const activityIcons: Record<ActivityType, ComponentType<{ className?: string }>> = {
  TRANSACTION: Wallet2,
  PORTFOLIO_UPDATE: TrendingUp,
  RECOMMENDATION: Sparkles,
  SYSTEM: Info,
}

/** One row of an activity feed (backend's Activity model / ActivityRead
 * schema). Shared by the Dashboard's "recent activity" card and the full
 * Activity screen so both render this feed identically. */
export function ActivityRow({ activity }: { activity: ActivityRead }) {
  const Icon = activityIcons[activity.type]

  const content = (
    <div className="flex items-start gap-3 py-3">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-raised)] text-[var(--color-text-muted)]">
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[var(--color-text-primary)]">{activity.title}</p>
        {activity.description && (
          <p className="truncate text-xs text-[var(--color-text-secondary)]">{activity.description}</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-1 whitespace-nowrap pt-0.5 text-xs text-[var(--color-text-muted)]">
        {formatRelativeTime(activity.created_at)}
        {activity.related_transaction_id && <ArrowRight className="size-3" />}
      </div>
    </div>
  )

  if (activity.related_transaction_id) {
    return (
      <Link to="/transactions" className="-mx-1 block rounded-lg px-1 transition-colors hover:bg-[var(--color-surface-hover)]">
        {content}
      </Link>
    )
  }

  return <div className="-mx-1 px-1">{content}</div>
}
