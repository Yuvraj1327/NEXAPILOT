import type { TransactionSerializable } from 'viem'
import type { UnsignedTransactionOut } from '@/types/api'

/** The backend serializes every numeric field of an unsigned tx as a hex
 * string (see UnsignedTransactionOut in backend/app/schemas/blockchain.py
 * -- done deliberately so wei-scale values never risk JS float precision
 * loss in transit). This is the single place that turns those hex strings
 * into the native number/bigint types each signer needs, so no
 * transaction-shape logic is duplicated across call sites. */
export interface NormalizedTx {
  from: `0x${string}`
  to: `0x${string}`
  data: `0x${string}`
  value: bigint
  nonce: number
  chainId: number
  gas: bigint
  maxFeePerGas?: bigint
  maxPriorityFeePerGas?: bigint
  gasPrice?: bigint
  isEip1559: boolean
}

export function normalizeUnsignedTx(tx: UnsignedTransactionOut): NormalizedTx {
  const isEip1559 = tx.maxFeePerGas != null && tx.maxPriorityFeePerGas != null

  return {
    from: tx.from as `0x${string}`,
    to: tx.to as `0x${string}`,
    data: tx.data as `0x${string}`,
    value: BigInt(tx.value),
    nonce: Number(BigInt(tx.nonce)),
    chainId: Number(BigInt(tx.chainId)),
    gas: BigInt(tx.gas),
    maxFeePerGas: tx.maxFeePerGas != null ? BigInt(tx.maxFeePerGas) : undefined,
    maxPriorityFeePerGas: tx.maxPriorityFeePerGas != null ? BigInt(tx.maxPriorityFeePerGas) : undefined,
    gasPrice: tx.gasPrice != null ? BigInt(tx.gasPrice) : undefined,
    isEip1559,
  }
}

/** For viem's local-account signer (the sandbox dev wallet path). */
export function toViemTransaction(tx: NormalizedTx): TransactionSerializable {
  if (tx.isEip1559) {
    return {
      type: 'eip1559',
      to: tx.to,
      data: tx.data,
      value: tx.value,
      nonce: tx.nonce,
      chainId: tx.chainId,
      gas: tx.gas,
      maxFeePerGas: tx.maxFeePerGas,
      maxPriorityFeePerGas: tx.maxPriorityFeePerGas,
    }
  }
  return {
    type: 'legacy',
    to: tx.to,
    data: tx.data,
    value: tx.value,
    nonce: tx.nonce,
    chainId: tx.chainId,
    gas: tx.gas,
    gasPrice: tx.gasPrice,
  }
}

/** For Privy's embedded-wallet `useSignTransaction` hook, whose field
 * names (`gasLimit` vs viem's `gas`) differ slightly from viem's. */
export function toPrivyTransactionRequest(tx: NormalizedTx) {
  return {
    to: tx.to,
    data: tx.data,
    value: tx.value,
    nonce: tx.nonce,
    chainId: tx.chainId,
    gasLimit: tx.gas,
    ...(tx.isEip1559
      ? { maxFeePerGas: tx.maxFeePerGas, maxPriorityFeePerGas: tx.maxPriorityFeePerGas, type: 2 }
      : { gasPrice: tx.gasPrice, type: 0 }),
  }
}
