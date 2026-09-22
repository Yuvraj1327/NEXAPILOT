import { defineChain } from 'viem'
import { config } from '@/lib/config'

/** Monad, defined from the same env vars the backend uses
 * (BLOCKCHAIN_NETWORK/MONAD_RPC_URL/MONAD_CHAIN_ID -- see
 * backend/app/core/config.py) so the two can never point at different
 * networks. Defaults to the local anvil devnet pinned to Monad's real
 * chain id, exactly like the backend's own default. */
export const monad = defineChain({
  id: config.monadChainId,
  name: config.monadChainName,
  nativeCurrency: { name: 'Monad', symbol: 'MON', decimals: 18 },
  rpcUrls: {
    default: { http: [config.monadRpcUrl] },
  },
})
