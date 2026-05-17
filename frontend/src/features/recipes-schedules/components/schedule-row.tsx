import { useCallback, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type {
  Schedule,
  ScheduleStatus,
  UpdateScheduleRequest,
} from '../../../types/schedule'
import {
  SCHEDULE_ACTIONS,
  SCHEDULE_STATUS_LABELS,
  SCHEDULE_STATUS_VARIANTS,
} from '../../../types/schedule'
import { Button, Input, Modal } from 'animal-island-ui'
import { StatusPill } from '../../../components/ui/status-pill'
import {
  disableSchedule,
  pauseSchedule,
  resumeSchedule,
  updateSchedule,
} from '../../../lib/schedule-api'
import { formatDate } from '../../../lib/format'
import { cellStyle } from '../../../lib/table-styles'

interface ScheduleRowProps {
  schedule: Schedule
  config: ApiConfig
  onChanged: () => void
}

const ACTION_LABELS: Record<string, string> = {
  edit: '编辑',
  pause: '暂停',
  resume: '恢复',
  disable: '停用',
}

const DANGEROUS_ACTIONS = new Set(['disable'])

function formatInterval(seconds: number): string {
  if (seconds >= 3600) {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  }
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60)
    return `${mins}m`
  }
  return `${seconds}s`
}

export function ScheduleRow({ schedule, config, onChanged }: ScheduleRowProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [editError, setEditError] = useState('')
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [confirmAction, setConfirmAction] = useState<string | null>(null)

  const [editInterval, setEditInterval] = useState(String(schedule.interval_seconds))
  const [editPriority, setEditPriority] = useState(String(schedule.priority))
  const [editLane, setEditLane] = useState(schedule.lane || '')

  const status = schedule.status as ScheduleStatus
  const allowedActions = SCHEDULE_ACTIONS[status] || []

  const handleAction = useCallback(
    async (action: string) => {
      setLoading(true)
      setError('')
      try {
        const apiCall: Record<string, (c: ApiConfig, id: string) => Promise<Schedule>> =
          {
            pause: pauseSchedule,
            resume: resumeSchedule,
            disable: disableSchedule,
          }
        const fn = apiCall[action]
        if (fn) {
          await fn(config, schedule.id)
        }
        onChanged()
      } catch (err) {
        setError(err instanceof Error ? err.message : '操作失败')
      } finally {
        setLoading(false)
      }
    },
    [config, schedule.id, onChanged],
  )

  const handleEditSubmit = useCallback(async () => {
    setEditSubmitting(true)
    setEditError('')
    try {
      const interval = parseInt(editInterval, 10)
      if (isNaN(interval) || interval < 60) {
        setEditError('间隔时间至少为 60 秒')
        setEditSubmitting(false)
        return
      }

      const data: UpdateScheduleRequest = {}
      if (interval !== schedule.interval_seconds) data.interval_seconds = interval
      const priority = parseInt(editPriority, 10) || 0
      if (priority !== schedule.priority) data.priority = priority
      const lane = editLane.trim() || null
      if (lane !== schedule.lane) data.lane = lane

      if (Object.keys(data).length > 0) {
        await updateSchedule(config, schedule.id, data)
      }
      setEditing(false)
      onChanged()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setEditSubmitting(false)
    }
  }, [config, schedule, editInterval, editPriority, editLane, onChanged])

  const startEdit = useCallback(() => {
    setEditInterval(String(schedule.interval_seconds))
    setEditPriority(String(schedule.priority))
    setEditLane(schedule.lane || '')
    setEditError('')
    setEditing(true)
  }, [schedule])

  const handleConfirmOk = useCallback(() => {
    if (confirmAction) {
      setConfirmAction(null)
      void handleAction(confirmAction)
    }
  }, [confirmAction, handleAction])

  if (editing) {
    return (
      <tr data-testid={`schedule-edit-row-${schedule.id}`}>
        <td colSpan={10}>
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
                <label
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 500,
                    color: 'var(--color-text-body)',
                  }}
                >
                  间隔（秒）
                </label>
                <Input
                  value={editInterval}
                  onChange={(e) => setEditInterval(e.target.value)}
                  data-testid="edit-schedule-interval"
                  type="number"
                  min={60}
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 500,
                    color: 'var(--color-text-body)',
                  }}
                >
                  优先级
                </label>
                <Input
                  value={editPriority}
                  onChange={(e) => setEditPriority(e.target.value)}
                  data-testid="edit-schedule-priority"
                  type="number"
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 500,
                    color: 'var(--color-text-body)',
                  }}
                >
                  通道
                </label>
                <Input
                  value={editLane}
                  onChange={(e) => setEditLane(e.target.value)}
                  data-testid="edit-schedule-lane"
                />
              </div>
              <Button
                onClick={() => void handleEditSubmit()}
                disabled={editSubmitting}
                data-testid="edit-schedule-save"
              >
                {editSubmitting ? '保存中...' : '保存'}
              </Button>
              <Button
                type="text"
                onClick={() => setEditing(false)}
                disabled={editSubmitting}
                data-testid="edit-schedule-cancel"
              >
                取消
              </Button>
            </div>
            {editError && (
              <p
                data-testid="edit-schedule-error"
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
      <tr data-testid={`schedule-row-${schedule.id}`}>
        <td
          style={{
            ...cellStyle,
            maxWidth: '200px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
            {schedule.schedule_key}
          </span>
        </td>
        <td style={cellStyle}>
          <span style={{ fontSize: 'var(--font-size-xs)' }}>
            {schedule.source_name || '--'}
          </span>
        </td>
        <td style={cellStyle}>
          <span style={{ fontSize: 'var(--font-size-xs)', fontFamily: 'monospace' }}>
            {schedule.recipe_id.slice(0, 8)}...
          </span>
        </td>
        <td style={cellStyle}>
          <StatusPill variant={SCHEDULE_STATUS_VARIANTS[status] || 'default'}>
            {SCHEDULE_STATUS_LABELS[status] || status}
          </StatusPill>
        </td>
        <td style={cellStyle}>{formatInterval(schedule.interval_seconds)}</td>
        <td style={cellStyle}>{formatDate(schedule.next_run_at)}</td>
        <td style={cellStyle}>{schedule.priority}</td>
        <td style={cellStyle}>{schedule.lane || '—'}</td>
        <td style={cellStyle}>{formatDate(schedule.created_at)}</td>
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
                data-testid={`action-${action}-${schedule.id}`}
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
                data-testid={`action-error-${schedule.id}`}
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
      <Modal
        open={confirmAction !== null}
        title="确认操作"
        onClose={() => setConfirmAction(null)}
        footer={
          <>
            <Button
              type="default"
              onClick={() => setConfirmAction(null)}
              data-testid="confirm-cancel"
            >
              取消
            </Button>
            <Button type="primary" onClick={handleConfirmOk} data-testid="confirm-ok">
              {confirmAction ? ACTION_LABELS[confirmAction] : '确认'}
            </Button>
          </>
        }
      >
        <p>
          确定要{confirmAction ? ACTION_LABELS[confirmAction] : ''}
          调度计划「{schedule.schedule_key.slice(0, 24)}...」吗？
        </p>
      </Modal>
    </>
  )
}
