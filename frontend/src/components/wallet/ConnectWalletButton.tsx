import { LogOut, Wallet } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useSession } from '@/lib/auth/SessionContext'
import { useWalletSession } from '@/lib/web3/WalletSessionContext'
import { truncateAddress } from '@/lib/format'

export function ConnectWalletButton() {
  const walletSession = useWalletSession()
  const session = useSession()

  if (session.status === 'ready' && walletSession.address) {
    return (
      <div className="flex items-center gap-2">
        <span className="hidden rounded-lg bg-[var(--color-surface-raised)] px-3 py-1.5 font-mono text-xs text-[var(--color-text-secondary)] sm:inline-block">
          {truncateAddress(walletSession.address)}
        </span>
        <Button variant="ghost" size="sm" onClick={() => session.logout()} title="Disconnect wallet">
          <LogOut className="size-4" />
        </Button>
      </div>
    )
  }

  const busy = walletSession.isConnecting || session.status === 'authenticating'

  return (
    <Button size="sm" onClick={() => walletSession.connect()} isLoading={busy}>
      <Wallet className="size-4" />
      {busy ? 'Connecting…' : 'Connect wallet'}
    </Button>
  )
}
