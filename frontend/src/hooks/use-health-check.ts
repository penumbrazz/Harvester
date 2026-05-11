import { useCallback, useEffect, useRef, useState } from 'react'

import type { ApiConfig, HealthResponse } from '../types/api'
import { apiRequest } from '../lib/api-client'

export type ConnectionStatus = 'unknown' | 'checking' | 'connected' | 'error'

interface UseHealthCheckReturn {
  status: ConnectionStatus
  errorMessage: string
  check: () => Promise<void>
}

/** Poll the backend /health endpoint and report connection status. */
export function useHealthCheck(config: ApiConfig): UseHealthCheckReturn {
  const [status, setStatus] = useState<ConnectionStatus>('unknown')
  const [errorMessage, setErrorMessage] = useState('')
  const mountedRef = useRef(true)

  // Track mounted state to avoid setState on unmounted component
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const safeSetStatus = useCallback((value: ConnectionStatus) => {
    if (mountedRef.current) setStatus(value)
  }, [])

  const safeSetErrorMessage = useCallback((value: string) => {
    if (mountedRef.current) setErrorMessage(value)
  }, [])

  const check = useCallback(async () => {
    if (!config.baseUrl) {
      safeSetStatus('error')
      safeSetErrorMessage('API 地址未配置')
      return
    }

    safeSetStatus('checking')
    safeSetErrorMessage('')

    try {
      const result = await apiRequest<HealthResponse>(config, '/health')
      if (result.status === 'ok') {
        safeSetStatus('connected')
      } else {
        safeSetStatus('error')
        safeSetErrorMessage(`意外的健康状态: ${result.status}`)
      }
    } catch (err) {
      safeSetStatus('error')
      safeSetErrorMessage(err instanceof Error ? err.message : '连接 API 失败')
    }
  }, [config, safeSetStatus, safeSetErrorMessage])

  // Run check on mount and when config changes
  const configStr = JSON.stringify(config)
  useEffect(() => {
    void check()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configStr])

  return { status, errorMessage, check }
}
