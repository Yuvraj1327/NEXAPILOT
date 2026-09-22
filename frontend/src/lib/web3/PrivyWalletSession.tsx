import { useCallback, type ReactNode } from 'react'
import { PrivyProvider, useLogin, useLogout, usePrivy, useSignTransaction, useWallets } from '@privy-io/react-auth'
import { WagmiProvider as PrivyWagmiProvider } from '@privy-io/wagmi'
import { config } from '@/lib/config'
import { monad } from '@/lib/web3/chains'
import { wagmiConfig } from '@/lib/web3/wagmiConfig'
import { WalletSessionContext, type WalletSession } from '@/lib/web3/WalletSessionContext'
import { normalizeUnsignedTx, toPrivyTransactionRequest } from '@/lib/web3/txConvert'
import type { UnsignedTransactionOut } from '@/types/api'

/** Reads Privy's own hooks and republishes them as the app's shared
 * WalletSession shape -- everything downstream (auth bridge, transaction
 * approval flow) is identical whether this or DevWalletSession is active. */
function PrivyWalletSessionBridge({ children }: { children: ReactNode }) {
  const { ready, authenticated, logout: privyLogout } = usePrivy()
  const { login } = useLogin()
  const { logout } = useLogout()
  const { wallets } = useWallets()
  const { signTransaction: privySignTransaction } = useSignTransaction()

  // The embedded wallet Privy created on login (embeddedWallets.ethereum
  // .createOnLogin is set to 'users-without-wallets' below) -- the one
  // wallet type that supports raw, detached transaction signing, which
  // the backend's prepare -> sign -> submit flow requires.
  const activeWallet = wallets.find((wallet) => wallet.walletClientType === 'privy') ?? wallets[0] ?? null

  const connect = useCallback(() => {
    login()
  }, [login])

  const disconnect = useCallback(async () => {
    try {
      await logout()
    } catch {
      await privyLogout()
    }
  }, [logout, privyLogout])

  const signTransaction = useCallback(
    async (unsignedTx: UnsignedTransactionOut): Promise<`0x${string}`> => {
      if (!activeWallet) throw new Error('No wallet connected.')
      const normalized = normalizeUnsignedTx(unsignedTx)
      const { signature } = await privySignTransaction(toPrivyTransactionRequest(normalized), {
        address: activeWallet.address,
      })
      return signature
    },
    [activeWallet, privySignTransaction],
  )

  const value: WalletSession = {
    address: authenticated ? ((activeWallet?.address as `0x${string}` | undefined) ?? null) : null,
    isConnected: authenticated && activeWallet != null,
    isConnecting: !ready,
    isReady: ready,
    connect,
    disconnect,
    signTransaction,
    mode: 'privy',
  }

  return <WalletSessionContext.Provider value={value}>{children}</WalletSessionContext.Provider>
}

export function PrivyWalletSessionProvider({ children }: { children: ReactNode }) {
  return (
    <PrivyProvider
      appId={config.privyAppId}
      config={{
        appearance: { theme: 'dark', accentColor: '#4fe0b0' },
        defaultChain: monad,
        supportedChains: [monad],
        embeddedWallets: { ethereum: { createOnLogin: 'users-without-wallets' } },
      }}
    >
      <PrivyWagmiProvider config={wagmiConfig}>
        <PrivyWalletSessionBridge>{children}</PrivyWalletSessionBridge>
      </PrivyWagmiProvider>
    </PrivyProvider>
  )
}
