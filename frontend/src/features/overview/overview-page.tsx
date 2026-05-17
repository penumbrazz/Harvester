import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { DashboardSummary } from '../../types/observability'
import { Button, Card, Input } from 'animal-island-ui'
import { StatusPill } from '../../components/ui/status-pill'
import { getDashboardSummary } from '../../lib/observability-api'
import { useHealthCheck } from '../../hooks/use-health-check'
import type { ConnectionStatus } from '../../hooks/use-health-check'

interface OverviewPageProps {
  config: ApiConfig
  onConfigChange: (config: ApiConfig) => void
}

const statusLabels: Record<ConnectionStatus, string> = {
  unknown: '未检测',
  checking: '检测中...',
  connected: '已连接',
  error: '已断开',
}

const statusVariants: Record<
  ConnectionStatus,
  'success' | 'error' | 'warning' | 'info' | 'default'
> = {
  unknown: 'default',
  checking: 'info',
  connected: 'success',
  error: 'error',
}

export function OverviewPage({ config, onConfigChange }: OverviewPageProps) {
  const { status, errorMessage, check } = useHealthCheck(config)
  const [editConfig, setEditConfig] = useState<ApiConfig>(config)
  const [editing, setEditing] = useState(false)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)

  const fetchSummary = useCallback(async () => {
    if (status !== 'connected') return
    try {
      const data = await getDashboardSummary(config)
      setSummary(data)
    } catch {
      // silent — stats will show --
    }
  }, [config, status])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: fetch summary updates state
    void fetchSummary()
  }, [fetchSummary])

  const handleSave = useCallback(() => {
    onConfigChange(editConfig)
    setEditing(false)
    // Trigger health check after save; check() uses a ref so it picks up the latest config
    void check()
  }, [editConfig, onConfigChange, check])

  const startEditing = useCallback(() => {
    setEditConfig(config)
    setEditing(true)
  }, [config])

  const handleCancel = useCallback(() => {
    setEditConfig(config)
    setEditing(false)
  }, [config])

  return (
    <div data-testid="page-overview">
      <h2
        style={{
          fontFamily: 'var(--font-family)',
          fontSize: 'var(--font-size-2xl)',
          fontWeight: 700,
          letterSpacing: '-0.625px',
          lineHeight: 'var(--line-height-tight)',
          marginBottom: 'var(--space-5)',
        }}
      >
        概览
      </h2>

      {/* Connection Status Card */}
      <Card type="default" style={{ marginBottom: 'var(--space-5)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--space-3)',
          }}
        >
          <h3
            style={{
              fontFamily: 'var(--font-family)',
              fontSize: 'var(--font-size-base)',
              fontWeight: 600,
            }}
          >
            API 连接
          </h3>
          <StatusPill variant={statusVariants[status]}>
            {statusLabels[status]}
          </StatusPill>
        </div>

        {errorMessage && (
          <p
            data-testid="connection-error"
            style={{
              color: 'var(--color-orange)',
              fontSize: 'var(--font-size-sm)',
              marginBottom: 'var(--space-3)',
            }}
          >
            {errorMessage}
          </p>
        )}

        {editing ? (
          <div
            data-testid="api-config-form"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-3)',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                htmlFor="api-base-url"
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                API 地址
              </label>
              <Input
                id="api-base-url"
                placeholder="http://localhost:8001"
                value={editConfig.baseUrl}
                onChange={(e) =>
                  setEditConfig((prev) => ({ ...prev, baseUrl: e.target.value }))
                }
                data-testid="input-api-base-url"
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                htmlFor="api-token"
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                API 令牌
              </label>
              <Input
                id="api-token"
                type="password"
                placeholder="可选的 Bearer 令牌"
                value={editConfig.token}
                onChange={(e) =>
                  setEditConfig((prev) => ({ ...prev, token: e.target.value }))
                }
                data-testid="input-api-token"
              />
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button onClick={handleSave} data-testid="save-config-button">
                保存并连接
              </Button>
              <Button
                type="default"
                onClick={handleCancel}
                data-testid="cancel-config-button"
              >
                取消
              </Button>
            </div>
          </div>
        ) : (
          <div
            data-testid="api-config-display"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span
              style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-body)',
              }}
            >
              {config.baseUrl || 'http://localhost:8001'}
            </span>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button
                type="default"
                onClick={startEditing}
                data-testid="edit-config-button"
              >
                配置
              </Button>
              <Button
                type="default"
                onClick={() => void check()}
                data-testid="retry-connection-button"
              >
                重试
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Quick Stats */}
      <div
        data-testid="overview-stats"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        <Card type="default">
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)',
              marginBottom: 'var(--space-2)',
            }}
          >
            信息源
          </p>
          <p
            style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: 700,
            }}
          >
            {summary?.sources.total ?? '--'}
          </p>
        </Card>
        <Card type="default">
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)',
              marginBottom: 'var(--space-2)',
            }}
          >
            活跃抓取
          </p>
          <p
            style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: 700,
            }}
          >
            {summary?.crawl_runs.by_status
              ? (summary.crawl_runs.by_status['running'] ?? 0)
              : '--'}
          </p>
        </Card>
        <Card type="default">
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)',
              marginBottom: 'var(--space-2)',
            }}
          >
            内容项
          </p>
          <p
            style={{
              fontSize: 'var(--font-size-xl)',
              fontWeight: 700,
            }}
          >
            {summary?.content_items.total ?? '--'}
          </p>
        </Card>
      </div>
    </div>
  )
}
