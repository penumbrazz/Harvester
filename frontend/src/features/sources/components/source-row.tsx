import { useCallback, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type { Source, SourceStatus } from '../../../types/source'
import { SOURCE_ACTIONS, STATUS_LABELS, STATUS_VARIANTS } from '../../../types/source'
import { Button } from '../../../components/ui/button'
import { StatusPill } from '../../../components/ui/status-pill'
import {
  archiveSource,
  pauseSource,
  promoteSource,
  resumeSource,
} from '../../../lib/source-api'
import { formatDate } from '../../../lib/format'

interface SourceRowProps {
  source: Source
  config: ApiConfig
  onStatusChanged: () => void
}

const ACTION_LABELS: Record<string, string> = {
  promote: '提升',
  pause: '暂停',
  resume: '恢复',
  archive: '归档',
}

export function SourceRow({ source, config, onStatusChanged }: SourceRowProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const status = source.status as SourceStatus
  const allowedActions = SOURCE_ACTIONS[status] || []

  const handleAction = useCallback(
    async (action: string) => {
      setLoading(true)
      setError('')
      try {
        const apiCall: Record<string, (c: ApiConfig, id: string) => Promise<Source>> = {
          promote: promoteSource,
          pause: pauseSource,
          resume: resumeSource,
          archive: archiveSource,
        }
        const fn = apiCall[action]
        if (fn) {
          await fn(config, source.id)
        }
        onStatusChanged()
      } catch (err) {
        setError(err instanceof Error ? err.message : '操作失败')
      } finally {
        setLoading(false)
      }
    },
    [config, source.id, onStatusChanged],
  )

  const cellStyle: React.CSSProperties = {
    padding: '10px var(--space-3)',
    fontSize: 'var(--font-size-sm)',
    verticalAlign: 'middle',
    borderBottom: 'var(--border-whisper)',
  }

  return (
    <tr data-testid={`source-row-${source.id}`}>
      <td style={cellStyle}>
        <span
          style={{
            fontWeight: 600,
            color: 'var(--color-primary-text)',
          }}
        >
          {source.name}
        </span>
      </td>
      <td style={cellStyle}>
        <span style={{ textTransform: 'uppercase', fontSize: 'var(--font-size-xs)' }}>
          {source.kind}
        </span>
      </td>
      <td style={cellStyle}>
        <StatusPill variant={STATUS_VARIANTS[status] || 'default'}>
          {STATUS_LABELS[status] || status}
        </StatusPill>
      </td>
      <td
        style={{
          ...cellStyle,
          maxWidth: '200px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {source.url || '—'}
      </td>
      <td style={cellStyle}>{source.trust_level}</td>
      <td style={cellStyle}>{source.failure_count}</td>
      <td style={cellStyle}>{formatDate(source.created_at)}</td>
      <td style={cellStyle}>
        <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
          {allowedActions.map((action) => (
            <Button
              key={action}
              variant={action === 'archive' ? 'ghost' : 'secondary'}
              disabled={loading}
              onClick={() => void handleAction(action)}
              data-testid={`action-${action}-${source.id}`}
              style={{
                padding: '4px 8px',
                fontSize: 'var(--font-size-xs)',
              }}
            >
              {ACTION_LABELS[action]}
            </Button>
          ))}
          {error && (
            <span
              data-testid={`action-error-${source.id}`}
              style={{
                color: 'var(--color-orange)',
                fontSize: 'var(--font-size-xs)',
              }}
            >
              错误
            </span>
          )}
        </div>
      </td>
    </tr>
  )
}
