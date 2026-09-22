import { Link } from 'react-router-dom'
import { ArrowRight, Coins, Landmark, ShieldCheck, TrendingUp } from 'lucide-react'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { StatTile } from '@/components/ui/StatTile'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { AsyncSection } from '@/components/ui/AsyncSection'
import { Skeleton } from '@/components/ui/States'
import { useSession } from '@/lib/auth/SessionContext'
import { useActivity, useMyPolicy, usePolicyUsage, useWalletBalance } from '@/hooks/queries'
import { formatMon, formatRelativeTime } from '@/lib/format'
import { ActivityRow } from '@/components/ActivityRow'

export function DashboardPage() {
  const { wallet, user } = useSession()
  const balance = useWalletBalance(wallet?.id)
  const policy = useMyPolicy()
  const usage = usePolicyUsage()
  const activity = useActivity()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
          Welcome{user?.display_name ? `, ${user.display_name}` : ''}
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)]">Here's where your portfolio stands right now.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <AsyncSection
          isLoading={balance.isLoading}
          error={balance.error}
          data={balance.data}
          onRetry={() => balance.refetch()}
        >
          {(data) => (
            <>
              <StatTile
                label="Wallet balance"
                value={formatMon(data.native_balance)}
                icon={<Coins className="size-4 text-[var(--color-text-muted)]" />}
                hint={`As of block ${data.as_of_block ?? '—'}`}
              />
              <StatTile
                label="Vault balance"
                value={formatMon(data.vault_balance)}
                icon={<Landmark className="size-4 text-[var(--color-text-muted)]" />}
                hint="Held in NexaPilotExecutor"
              />
            </>
          )}
        </AsyncSection>
        {balance.isLoading && (
          <>
            <Skeleton className="h-24 rounded-2xl" />
            <Skeleton className="h-24 rounded-2xl" />
          </>
        )}

        <AsyncSection isLoading={usage.isLoading} error={usage.error} data={usage.data} onRetry={() => usage.refetch()}>
          {(data) => {
            const limit = Number(data.daily_limit)
            const spent = Number(data.spent_today)
            return (
              <StatTile
                label="Daily limit used"
                value={formatMon(data.spent_today)}
                icon={<TrendingUp className="size-4 text-[var(--color-text-muted)]" />}
                hint={`of ${formatMon(data.daily_limit)} today`}
              >
                {limit > 0 && (
                  <div className="mt-2">
                    <ProgressBar fraction={spent / limit} tone={spent / limit > 0.8 ? 'warning' : 'accent'} />
                  </div>
                )}
              </StatTile>
            )
          }}
        </AsyncSection>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Your policy</CardTitle>
            <Link to="/settings" className="text-xs font-medium text-[var(--color-accent)] hover:underline">
              Edit
            </Link>
          </CardHeader>
          <CardBody>
            <AsyncSection
              isLoading={policy.isLoading}
              error={policy.error}
              data={policy.data}
              onRetry={() => policy.refetch()}
            >
              {(data) => (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                  <div>
                    <dt className="text-[var(--color-text-muted)]">Max transaction</dt>
                    <dd className="font-medium text-[var(--color-text-primary)]">{formatMon(data.max_transaction_amount)}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--color-text-muted)]">Daily limit</dt>
                    <dd className="font-medium text-[var(--color-text-primary)]">{formatMon(data.daily_limit)}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--color-text-muted)]">Max risk</dt>
                    <dd className="font-medium text-[var(--color-text-primary)]">{data.max_risk_level}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--color-text-muted)]">Approval</dt>
                    <dd className="font-medium text-[var(--color-text-primary)]">
                      {data.approval_required ? 'Required' : 'Automatic'}
                    </dd>
                  </div>
                </dl>
              )}
            </AsyncSection>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <Link
              to="/activity"
              className="flex items-center gap-1 text-xs font-medium text-[var(--color-accent)] hover:underline"
            >
              View all <ArrowRight className="size-3" />
            </Link>
          </CardHeader>
          <CardBody>
            <AsyncSection
              isLoading={activity.isLoading}
              error={activity.error}
              data={activity.data}
              onRetry={() => activity.refetch()}
              isEmpty={(data) => data.length === 0}
              emptyTitle="No activity yet"
              emptyDescription="Ask the AI Copilot something to get started."
              emptyIcon={<ShieldCheck className="size-5" />}
            >
              {(data) => (
                <ul className="flex flex-col divide-y divide-[var(--color-border)]">
                  {data.slice(0, 5).map((item) => (
                    <ActivityRow key={item.id} activity={item} />
                  ))}
                </ul>
              )}
            </AsyncSection>
          </CardBody>
        </Card>
      </div>

      <p className="text-xs text-[var(--color-text-muted)]">
        Last updated {balance.dataUpdatedAt ? formatRelativeTime(new Date(balance.dataUpdatedAt).toISOString()) : '—'}
      </p>
    </div>
  )
}
