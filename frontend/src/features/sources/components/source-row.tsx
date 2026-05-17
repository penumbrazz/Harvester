import { useCallback, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type { Source, SourceStatus, UpdateSourceRequest } from '../../../types/source'
import { SOURCE_ACTIONS, STATUS_LABELS, STATUS_VARIANTS } from '../../../types/source'
import { Button, Input } from 'animal-island-ui'
import { ConfirmDialog } from '../../../components/ui/confirm-dialog'
import { StatusPill } from '../../../components/ui/status-pill'
import {
  archiveSource,
  pauseSource,
  promoteSource,
  resumeSource,
  updateSource,
} from '../../../lib/source-api'
import { formatDate } from '../../../lib/format'
import { cellStyle } from '../../../lib/table-styles'

interface SourceRowProps {
  source: Source
  config: ApiConfig
  onStatusChanged: () => void
}

const ACTION_LABELS: Record<string, string> = {
  edit: '编辑',
  promote: '提升',
  pause: '暂停',
  resume: '恢复',
  archive: '归档',
}

const DANGEROUS_ACTIONS = new Set(['archive'])

export function SourceRow({ source, config, onStatusChanged }: SourceRowProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [editError, setEditError] = useState('')
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [confirmAction, setConfirmAction] = useState<string | null>(null)

  const [editName, setEditName] = useState(source.name)
  const [editUrl, setEditUrl] = useState(source.url || '')

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

  const handleEditSubmit = useCallback(async () => {
    setEditSubmitting(true)
    setEditError('')
    try {
      const data: UpdateSourceRequest = {}
      if (editName !== source.name) data.name = editName
      const url = editUrl.trim() || null
      if (url !== source.url) data.url = url

      if (Object.keys(data).length > 0) {
        await updateSource(config, source.id, data)
      }
      setEditing(false)
      onStatusChanged()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setEditSubmitting(false)
    }
  }, [config, source, editName, editUrl, onStatusChanged])

  const startEdit = useCallback(() => {
    setEditName(source.name)
    setEditUrl(source.url || '')
    setEditError('')
    setEditing(true)
  }, [source])

  const handleConfirmOk = useCallback(() => {
    if (confirmAction) {
      setConfirmAction(null)
      void handleAction(confirmAction)
    }
  }, [confirmAction, handleAction])

  if (editing) {
    return (
      <tr data-testid={`source-edit-row-${source.id}`}>
        <td colSpan={8}>
          <div
            style={{
              padding: 'var(--space-3)',
              backgroundColor: 'var(--color-bg-content)',
            }}
          >
            <div
              style={{
                display: 'flex',
                gap: 'var(--space-3)',
                flexWrap: 'wrap',
                alignItems: 'flex-end',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label htmlFor="edit-source-name" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--color-text-body)' }}>名称</label>
                <Input
                  id="edit-source-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  data-testid="edit-source-name"
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label htmlFor="edit-source-url" style={{ fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--color-text-body)' }}>URL</label>
                <Input
                  id="edit-source-url"
                  value={editUrl}
                  onChange={(e) => setEditUrl(e.target.value)}
                  data-testid="edit-source-url"
                  placeholder="https://..."
                />
              </div>
              <Button
                onClick={() => void handleEditSubmit()}
                disabled={editSubmitting}
                data-testid="edit-source-save"
              >
                {editSubmitting ? '保存中...' : '保存'}
              </Button>
              <Button
                type="text"
                onClick={() => setEditing(false)}
                disabled={editSubmitting}
                data-testid="edit-source-cancel"
              >
                取消
              </Button>
            </div>
            {editError && (
              <p
                data-testid="edit-source-error"
                style={{
                  color: 'var(--color-orange)',
                  fontSize: 'var(--font-size-xs)',
                  margin: 'var(--space-2) 0 0',
                }}
              >
                {editError}
              </p>
            )}
          </div>
        </td>
      </tr>
    )
  }

  return (
    <>
      <tr data-testid={`source-row-${source.id}`}>
        <td style={cellStyle}>
          <span
            style={{
              fontWeight: 600,
              color: 'var(--color-text-primary)',
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
                type={DANGEROUS_ACTIONS.has(action) ? 'text' : 'default'}
                disabled={loading}
                onClick={() => {
                  if (action === 'edit') {
                    startEdit()
                  } else if (DANGEROUS_ACTIONS.has(action)) {
                    setConfirmAction(action)
                  } else {
                    void handleAction(action)
                  }
                }}
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
      <ConfirmDialog
        open={confirmAction !== null}
        title="确认操作"
        message={`确定要${confirmAction ? ACTION_LABELS[confirmAction] : ''}信息源「${source.name}」吗？`}
        confirmLabel={confirmAction ? ACTION_LABELS[confirmAction] : '确认'}
        loading={loading}
        onConfirm={handleConfirmOk}
        onCancel={() => setConfirmAction(null)}
      />
    </>
  )
}
