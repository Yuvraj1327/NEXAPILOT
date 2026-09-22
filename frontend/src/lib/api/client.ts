import { config } from '@/lib/config'
import type { ApiErrorBody } from '@/types/api'

/** Thrown for every non-2xx response, carrying the backend's own error
 * envelope ({error: {code, message, details}} -- see
 * backend/app/core/exceptions.py) so callers can branch on `code` instead
 * of parsing prose. */
export class ApiError extends Error {
  code: string
  status: number
  details?: unknown

  constructor(status: number, body: ApiErrorBody | null, fallbackMessage: string) {
    super(body?.error?.message ?? fallbackMessage)
    this.name = 'ApiError'
    this.status = status
    this.code = body?.error?.code ?? 'UNKNOWN_ERROR'
    this.details = body?.error?.details
  }
}

const TOKEN_STORAGE_KEY = 'nexapilot.access_token'

let inMemoryToken: string | null = localStorage.getItem(TOKEN_STORAGE_KEY)
const listeners = new Set<(token: string | null) => void>()

export const tokenStore = {
  get: () => inMemoryToken,
  set(token: string | null) {
    inMemoryToken = token
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
    listeners.forEach((listener) => listener(token))
  },
  subscribe(listener: (token: string | null) => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  /** Skip attaching the bearer token -- only /auth/connect needs this. */
  unauthenticated?: boolean
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, unauthenticated = false } = options

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (!unauthenticated) {
    const token = tokenStore.get()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  let response: Response
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, null, 'Could not reach the NexaPilot backend. Is it running?')
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  const json = text.length > 0 ? JSON.parse(text) : null

  if (!response.ok) {
    if (response.status === 401) {
      tokenStore.set(null)
    }
    throw new ApiError(response.status, json as ApiErrorBody, `Request failed with status ${response.status}.`)
  }

  return json as T
}
