/** Central place for every env-derived value -- nothing else in the app
 * reads import.meta.env directly, so a missing/renamed var is caught here. */

function readEnv(key: string, fallback = ''): string {
  const value = import.meta.env[key as keyof ImportMetaEnv]
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

export const config = {
  apiBaseUrl: readEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
  monadChainId: Number(readEnv('VITE_MONAD_CHAIN_ID', '10143')),
  monadRpcUrl: readEnv('VITE_MONAD_RPC_URL', 'http://127.0.0.1:8545'),
  monadChainName: readEnv('VITE_MONAD_CHAIN_NAME', 'Monad (local devnet)'),
  privyAppId: readEnv('VITE_PRIVY_APP_ID', ''),
  devWalletPrivateKey: readEnv('VITE_DEV_WALLET_PRIVATE_KEY', ''),
} as const

/** True when no real Privy App ID is configured -- the app falls back to
 * the local dev wallet connector so the rest of the product can still be
 * built and tested end-to-end (see src/lib/web3/wagmiConfig.ts). */
export const usingDevWallet = config.privyAppId.length === 0
