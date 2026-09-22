import { useEffect, useState } from 'react'
import { Save, ShieldCheck, UserRound, Wallet2 } from 'lucide-react'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { AsyncSection } from '@/components/ui/AsyncSection'
import { useMyPolicy, useUpdatePolicy, useUpdateProfile } from '@/hooks/queries'
import { useSession } from '@/lib/auth/SessionContext'
import { useWalletSession } from '@/lib/web3/WalletSessionContext'
import { truncateAddress } from '@/lib/format'
import type { RiskLevel } from '@/types/api'

const riskLevels: RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH']

const inputClass =
  'h-10 w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] px-3 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none'
const labelClass = 'text-xs font-medium text-[var(--color-text-muted)]'

function ProfileSection() {
  const { user } = useSession()
  const updateProfile = useUpdateProfile()
  const [displayName, setDisplayName] = useState(user?.display_name ?? '')

  useEffect(() => {
    setDisplayName(user?.display_name ?? '')
  }, [user?.display_name])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserRound className="size-4" /> Profile
        </CardTitle>
      </CardHeader>
      <CardBody>
        <form
          className="flex flex-col gap-4 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault()
            updateProfile.mutate({ display_name: displayName || null })
          }}
        >
          <div className="flex-1">
            <label className={labelClass}>Display name</label>
            <input
              className={`${inputClass} mt-1`}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
            />
          </div>
          <Button type="submit" size="sm" isLoading={updateProfile.isPending}>
            <Save className="size-4" /> Save
          </Button>
        </form>
        {updateProfile.isSuccess && <p className="mt-2 text-xs text-[var(--color-success)]">Saved.</p>}
        {updateProfile.isError && (
          <p className="mt-2 text-xs text-[var(--color-danger)]">Could not save your profile. Try again.</p>
        )}
      </CardBody>
    </Card>
  )
}

function PolicySection() {
  const policy = useMyPolicy()
  const updatePolicy = useUpdatePolicy()

  const [form, setForm] = useState({
    max_transaction_amount: '',
    daily_limit: '',
    allowed_protocols: '',
    allowed_actions: '',
    max_risk_level: 'MEDIUM' as RiskLevel,
    approval_required: true,
  })
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    if (policy.data && !initialized) {
      setForm({
        max_transaction_amount: policy.data.max_transaction_amount,
        daily_limit: policy.data.daily_limit,
        allowed_protocols: policy.data.allowed_protocols.join(', '),
        allowed_actions: policy.data.allowed_actions.join(', '),
        max_risk_level: policy.data.max_risk_level,
        approval_required: policy.data.approval_required,
      })
      setInitialized(true)
    }
  }, [policy.data, initialized])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-4" /> Spending policy
        </CardTitle>
      </CardHeader>
      <CardBody>
        <AsyncSection isLoading={policy.isLoading} error={policy.error} data={policy.data} onRetry={() => policy.refetch()}>
          {() => (
            <form
              className="flex flex-col gap-4"
              onSubmit={(e) => {
                e.preventDefault()
                updatePolicy.mutate({
                  max_transaction_amount: form.max_transaction_amount,
                  daily_limit: form.daily_limit,
                  allowed_protocols: form.allowed_protocols
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                  allowed_actions: form.allowed_actions
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                  max_risk_level: form.max_risk_level,
                  approval_required: form.approval_required,
                })
              }}
            >
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelClass}>Max transaction amount (MON)</label>
                  <input
                    className={`${inputClass} mt-1`}
                    value={form.max_transaction_amount}
                    onChange={(e) => setForm((f) => ({ ...f, max_transaction_amount: e.target.value }))}
                  />
                </div>
                <div>
                  <label className={labelClass}>Daily limit (MON)</label>
                  <input
                    className={`${inputClass} mt-1`}
                    value={form.daily_limit}
                    onChange={(e) => setForm((f) => ({ ...f, daily_limit: e.target.value }))}
                  />
                </div>
                <div>
                  <label className={labelClass}>Allowed protocols (comma-separated)</label>
                  <input
                    className={`${inputClass} mt-1`}
                    value={form.allowed_protocols}
                    onChange={(e) => setForm((f) => ({ ...f, allowed_protocols: e.target.value }))}
                  />
                </div>
                <div>
                  <label className={labelClass}>Allowed actions (comma-separated)</label>
                  <input
                    className={`${inputClass} mt-1`}
                    value={form.allowed_actions}
                    onChange={(e) => setForm((f) => ({ ...f, allowed_actions: e.target.value }))}
                  />
                </div>
                <div>
                  <label className={labelClass}>Max risk level</label>
                  <select
                    className={`${inputClass} mt-1`}
                    value={form.max_risk_level}
                    onChange={(e) => setForm((f) => ({ ...f, max_risk_level: e.target.value as RiskLevel }))}
                  >
                    {riskLevels.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="flex items-center gap-2 self-end pb-2.5 text-sm text-[var(--color-text-secondary)]">
                  <input
                    type="checkbox"
                    checked={form.approval_required}
                    onChange={(e) => setForm((f) => ({ ...f, approval_required: e.target.checked }))}
                    className="size-4 rounded border-[var(--color-border-strong)] accent-[var(--color-accent)]"
                  />
                  Require my approval before every transaction
                </label>
              </div>

              <div className="flex items-center gap-3">
                <Button type="submit" size="sm" isLoading={updatePolicy.isPending}>
                  <Save className="size-4" /> Save policy
                </Button>
                {updatePolicy.isSuccess && <span className="text-xs text-[var(--color-success)]">Saved.</span>}
                {updatePolicy.isError && (
                  <span className="text-xs text-[var(--color-danger)]">Could not save. Try again.</span>
                )}
              </div>
            </form>
          )}
        </AsyncSection>
      </CardBody>
    </Card>
  )
}

function WalletSection() {
  const { wallet, logout } = useSession()
  const walletSession = useWalletSession()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wallet2 className="size-4" /> Wallet
        </CardTitle>
      </CardHeader>
      <CardBody className="flex flex-col gap-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-[var(--color-text-muted)]">Address</span>
          <span className="font-mono text-[var(--color-text-primary)]">
            {wallet ? truncateAddress(wallet.address) : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[var(--color-text-muted)]">Chain</span>
          <span className="text-[var(--color-text-primary)]">{wallet?.chain ?? '—'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[var(--color-text-muted)]">Connector</span>
          <span className="text-[var(--color-text-primary)]">
            {walletSession.mode === 'privy' ? 'Privy' : 'Local dev wallet'}
          </span>
        </div>
        <div className="pt-2">
          <Button variant="secondary" size="sm" onClick={() => logout()}>
            Disconnect wallet
          </Button>
        </div>
      </CardBody>
    </Card>
  )
}

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Settings</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">Manage your profile, spending policy, and wallet.</p>
      </div>

      <ProfileSection />
      <PolicySection />
      <WalletSection />
    </div>
  )
}
