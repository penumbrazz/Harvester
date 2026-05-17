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
  const configRef = useRef(config)

  // Keep configRef in sync so check() always uses the latest config
  useEffect(() => {
    configRef.current = config
  }, [config])

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
    safeSetStatus('checking')
    safeSetErrorMessage('')

    try {
      const result = await apiRequest<HealthResponse>(configRef.current, '/health')
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
  }, [safeSetStatus, safeSetErrorMessage])

  // Run check on mount and when config changes
  const configStr = JSON.stringify(config)
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: health check updates status
    void check()
  }, [configStr, check])

  return { status, errorMessage, check }
}
