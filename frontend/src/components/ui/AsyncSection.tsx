import type { ReactNode } from 'react'
import { ApiError } from '@/lib/api/client'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/States'

interface AsyncSectionProps<T> {
  isLoading: boolean
  error: unknown
  data: T | undefined
  onRetry?: () => void
  loadingLabel?: string
  /** Returns true when `data` should be treated as "nothing to show yet"
   * (e.g. an empty array) rather than rendered. */
  isEmpty?: (data: T) => boolean
  emptyTitle?: string
  emptyDescription?: string
  emptyIcon?: ReactNode
  children: (data: T) => ReactNode
}

/** The one place loading/error/empty rendering is decided, so every
 * screen shows these states the same way instead of five slightly
 * different spinners. */
export function AsyncSection<T>({
  isLoading,
  error,
  data,
  onRetry,
  loadingLabel,
  isEmpty,
  emptyTitle = 'Nothing here yet',
  emptyDescription,
  emptyIcon,
  children,
}: AsyncSectionProps<T>) {
  if (isLoading) return <LoadingState label={loadingLabel} />

  if (error) {
    const message = error instanceof ApiError ? error.message : 'Something went wrong loading this.'
    return <ErrorState message={message} onRetry={onRetry} />
  }

  if (data === undefined) return null

  if (isEmpty?.(data)) {
    return <EmptyState title={emptyTitle} description={emptyDescription} icon={emptyIcon} />
  }

  return <>{children(data)}</>
}
