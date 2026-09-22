import { Activity as ActivityIcon } from 'lucide-react'
import { Card, CardBody } from '@/components/ui/Card'
import { AsyncSection } from '@/components/ui/AsyncSection'
import { ActivityRow } from '@/components/ActivityRow'
import { useActivity } from '@/hooks/queries'

export function ActivityPage() {
  const activity = useActivity()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Activity</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          A full history of what NexaPilot has done and recommended for your account.
        </p>
      </div>

      <Card>
        <CardBody>
          <AsyncSection
            isLoading={activity.isLoading}
            error={activity.error}
            data={activity.data}
            onRetry={() => activity.refetch()}
            isEmpty={(data) => data.length === 0}
            emptyTitle="No activity yet"
            emptyDescription="Ask the AI Copilot something to get started."
            emptyIcon={<ActivityIcon className="size-5" />}
          >
            {(data) => (
              <ul className="flex flex-col divide-y divide-[var(--color-border)]">
                {[...data]
                  .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                  .map((item) => (
                    <ActivityRow key={item.id} activity={item} />
                  ))}
              </ul>
            )}
          </AsyncSection>
        </CardBody>
      </Card>
    </div>
  )
}
