import { useCallback, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { StatusPill } from '../../components/ui/status-pill'
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
  const [editing, setEditing] = useState(!config.baseUrl)

  const handleSave = useCallback(() => {
    onConfigChange(editConfig)
    setEditing(false)
  }, [editConfig, onConfigChange])

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
      <Card style={{ marginBottom: 'var(--space-5)' }}>
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
            <Input
              id="api-base-url"
              label="API 地址"
              placeholder="http://localhost:8001"
              value={editConfig.baseUrl}
              onChange={(e) =>
                setEditConfig((prev) => ({ ...prev, baseUrl: e.target.value }))
              }
              data-testid="input-api-base-url"
            />
            <Input
              id="api-token"
              label="API 令牌"
              type="password"
              placeholder="可选的 Bearer 令牌"
              value={editConfig.token}
              onChange={(e) =>
                setEditConfig((prev) => ({ ...prev, token: e.target.value }))
              }
              data-testid="input-api-token"
            />
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button onClick={handleSave} data-testid="save-config-button">
                保存并连接
              </Button>
              <Button
                variant="secondary"
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
                color: 'var(--color-warm-gray-500)',
              }}
            >
              {config.baseUrl || '未配置地址'}
            </span>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button
                variant="secondary"
                onClick={() => setEditing(true)}
                data-testid="edit-config-button"
              >
                配置
              </Button>
              <Button
                variant="secondary"
                onClick={() => void check()}
                data-testid="retry-connection-button"
              >
                重试
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Quick Stats Placeholder */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        <Card>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-300)',
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
            --
          </p>
        </Card>
        <Card>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-300)',
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
            --
          </p>
        </Card>
        <Card>
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warm-gray-300)',
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
            --
          </p>
        </Card>
      </div>
    </div>
  )
}
