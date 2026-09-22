import { AlertTriangle } from 'lucide-react'
import { ConnectWalletButton } from '@/components/wallet/ConnectWalletButton'
import { useSession } from '@/lib/auth/SessionContext'
import { usingDevWallet } from '@/lib/config'

export function LoginPage() {
  const session = useSession()

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-8 bg-[var(--color-canvas)] px-6 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-[var(--color-accent)] text-xl font-bold text-black">
        N
      </div>
      <div className="max-w-sm space-y-2">
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">NexaPilot</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Your AI financial copilot for Monad. Connect a wallet to see your portfolio, ask the AI Copilot for a plan,
          and review every recommendation before anything ever touches your funds.
        </p>
      </div>

      <ConnectWalletButton />

      {session.status === 'error' && (
        <div className="flex max-w-sm items-start gap-2 rounded-xl bg-[var(--color-danger-soft)] px-4 py-3 text-left text-sm text-[var(--color-danger)]">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span>{session.error}</span>
        </div>
      )}

      {usingDevWallet && (
        <p className="max-w-sm text-xs text-[var(--color-text-muted)]">
          Running with the local dev wallet (no <code>VITE_PRIVY_APP_ID</code> configured) — connecting signs you in
          with a local anvil devnet account. Set a real Privy App ID in <code>.env</code> to switch to production
          wallet login.
        </p>
      )}
    </div>
  )
}
