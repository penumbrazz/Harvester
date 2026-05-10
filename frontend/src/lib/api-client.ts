import type { ApiConfig } from '../types/api'

const API_CONFIG_KEY = 'harvester-api-config'

/** Load API configuration from localStorage. */
export function loadApiConfig(): ApiConfig {
  try {
    const raw = localStorage.getItem(API_CONFIG_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<ApiConfig>
      return {
        baseUrl: parsed.baseUrl || '',
        token: parsed.token || '',
      }
    }
  } catch {
    // ignore parse errors
  }
  return { baseUrl: '', token: '' }
}

/** Save API configuration to localStorage. */
export function saveApiConfig(config: ApiConfig): void {
  localStorage.setItem(API_CONFIG_KEY, JSON.stringify(config))
}

/** Build headers for API requests, including Authorization if token is set. */
function buildHeaders(token: string): HeadersInit {
  const headers: HeadersInit = {
    Accept: 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/** Generic API request with error normalization. */
export async function apiRequest<T>(
  config: ApiConfig,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${config.baseUrl.replace(/\/+$/, '')}${path}`
  const response = await fetch(url, {
    ...options,
    headers: {
      ...buildHeaders(config.token),
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new ApiError(response.status, response.statusText, body)
  }

  return response.json() as Promise<T>
}

/** Normalized API error. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: string,
  ) {
    super(`API ${status} ${statusText}: ${body}`)
    this.name = 'ApiError'
  }
}
