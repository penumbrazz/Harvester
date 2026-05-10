import { type ChangeEvent, useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { Schedule } from '../../types/schedule'
import { SCHEDULE_STATUS_OPTIONS } from '../../types/schedule'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select } from '../../components/ui/select'
import { StatusPill } from '../../components/ui/status-pill'
import { formatDate } from '../../lib/format'
import { listSchedules, createSchedule } from '../../lib/schedule-api'
import { cellStyle } from '../../lib/table-styles'
import { ApprovedRecipeSelector } from './components/selectors'
import { SourceSelector } from './components/selectors'

interface SchedulesPageProps {
  config: ApiConfig
}

/** Format interval seconds to a human-readable string. */
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

export function SchedulesPage({ config }: SchedulesPageProps) {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showForm, setShowForm] = useState(false)

  // Form state
  const [formSourceId, setFormSourceId] = useState('')
  const [formRecipeId, setFormRecipeId] = useState('')
  const [formInterval, setFormInterval] = useState('3600')
  const [formPriority, setFormPriority] = useState('0')
  const [formLane, setFormLane] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  const fetchSchedules = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listSchedules(config, {
        status: statusFilter || undefined,
      })
      setSchedules(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schedules')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter])

  useEffect(() => {
    if (config.baseUrl) {
      void fetchSchedules()
    }
  }, [config.baseUrl, fetchSchedules])

  const handleSourceChange = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    setFormSourceId(e.target.value)
  }, [])

  const handleRecipeChange = useCallback((e: ChangeEvent<HTMLSelectElement>) => {
    setFormRecipeId(e.target.value)
  }, [])

  const handleCreateSchedule = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setFormError('')

      if (!formSourceId) {
        setFormError('Source is required')
        return
      }
      if (!formRecipeId) {
        setFormError('Recipe is required')
        return
      }

      const interval = parseInt(formInterval, 10)
      if (isNaN(interval) || interval < 60) {
        setFormError('Interval must be at least 60 seconds')
        return
      }

      setFormSubmitting(true)
      try {
        await createSchedule(config, {
          source_id: formSourceId,
          recipe_id: formRecipeId,
          interval_seconds: interval,
          priority: parseInt(formPriority, 10) || 0,
          lane: formLane.trim() || null,
        })
        setShowForm(false)
        setFormSourceId('')
        setFormRecipeId('')
        setFormInterval('3600')
        setFormPriority('0')
        setFormLane('')
        void fetchSchedules()
      } catch (err) {
        setFormError(err instanceof Error ? err.message : 'Failed to create schedule')
      } finally {
        setFormSubmitting(false)
      }
    },
    [
      config,
      formSourceId,
      formRecipeId,
      formInterval,
      formPriority,
      formLane,
      fetchSchedules,
    ],
  )

  return (
    <div data-testid="page-schedules">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-5)',
        }}
      >
        <h2
          style={{
            fontFamily: 'var(--font-family)',
            fontSize: 'var(--font-size-2xl)',
            fontWeight: 700,
            letterSpacing: '-0.625px',
            lineHeight: 'var(--line-height-tight)',
          }}
        >
          Schedules
        </h2>
        <Button onClick={() => setShowForm(true)} data-testid="new-schedule-button">
          New Schedule
        </Button>
      </div>

      {/* Hint */}
      <p
        style={{
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-warm-gray-500)',
          marginBottom: 'var(--space-4)',
          lineHeight: 'var(--line-height-normal)',
        }}
      >
        Watch schedules define when and how sources are crawled. Only watched/active
        sources and approved recipes can be scheduled.
      </p>

      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
          flexWrap: 'wrap',
          alignItems: 'flex-end',
        }}
      >
        <Select
          data-testid="select-schedule-status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {SCHEDULE_STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </div>

      {/* Create schedule form */}
      {showForm && (
        <div
          data-testid="create-schedule-panel"
          style={{
            marginBottom: 'var(--space-4)',
            padding: 'var(--space-4)',
            backgroundColor: 'var(--color-warm-white)',
            borderRadius: 'var(--radius-lg)',
            border: 'var(--border-whisper)',
          }}
        >
          <h3
            style={{
              fontFamily: 'var(--font-family)',
              fontSize: 'var(--font-size-base)',
              fontWeight: 600,
              marginBottom: 'var(--space-3)',
            }}
          >
            Create New Schedule
          </h3>
          <form
            data-testid="create-schedule-form"
            onSubmit={handleCreateSchedule}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-3)',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                style={{
                  fontFamily: 'var(--font-family)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-warm-gray-500)',
                }}
              >
                Source (schedulable only)
              </label>
              <SourceSelector
                config={config}
                value={formSourceId}
                onChange={handleSourceChange}
                schedulableOnly
                data-testid="select-schedule-source"
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                style={{
                  fontFamily: 'var(--font-family)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-warm-gray-500)',
                }}
              >
                Recipe (approved only)
              </label>
              <ApprovedRecipeSelector
                config={config}
                value={formRecipeId}
                onChange={handleRecipeChange}
                data-testid="select-schedule-recipe"
              />
            </div>

            <Input
              id="schedule-interval"
              label="Interval (seconds)"
              placeholder="3600"
              value={formInterval}
              onChange={(e) => setFormInterval(e.target.value)}
              data-testid="input-schedule-interval"
              type="number"
              min={60}
            />

            <Input
              id="schedule-priority"
              label="Priority"
              placeholder="0"
              value={formPriority}
              onChange={(e) => setFormPriority(e.target.value)}
              data-testid="input-schedule-priority"
              type="number"
            />

            <Input
              id="schedule-lane"
              label="Lane (optional)"
              placeholder="e.g. default"
              value={formLane}
              onChange={(e) => setFormLane(e.target.value)}
              data-testid="input-schedule-lane"
            />

            {formError && (
              <p
                data-testid="create-schedule-error"
                style={{
                  color: 'var(--color-orange)',
                  fontSize: 'var(--font-size-sm)',
                  margin: 0,
                }}
              >
                {formError}
              </p>
            )}

            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button
                type="submit"
                disabled={formSubmitting}
                data-testid="submit-create-schedule"
              >
                {formSubmitting ? 'Creating...' : 'Create Schedule'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowForm(false)
                  setFormError('')
                }}
                data-testid="cancel-create-schedule"
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <p
          data-testid="schedules-loading"
          style={{
            color: 'var(--color-warm-gray-500)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          Loading schedules...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="schedules-error"
          style={{ color: 'var(--color-orange)', fontSize: 'var(--font-size-sm)' }}
        >
          {error}
        </p>
      )}

      {/* Empty state */}
      {!loading && !error && schedules.length === 0 && (
        <div
          data-testid="schedules-empty"
          style={{
            textAlign: 'center',
            padding: 'var(--space-8) var(--space-4)',
            color: 'var(--color-warm-gray-300)',
          }}
        >
          <p
            style={{
              fontSize: 'var(--font-size-base)',
              marginBottom: 'var(--space-2)',
            }}
          >
            No schedules found
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {statusFilter
              ? 'Try adjusting your filters.'
              : 'Click "New Schedule" to create your first schedule.'}
          </p>
        </div>
      )}

      {/* Schedule table */}
      {!loading && !error && schedules.length > 0 && (
        <div
          style={{
            overflowX: 'auto',
            border: 'var(--border-whisper)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <table
            data-testid="schedules-table"
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontFamily: 'var(--font-family)',
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: 'var(--border-whisper)',
                  backgroundColor: 'var(--color-warm-white)',
                }}
              >
                {[
                  'Key',
                  'Source',
                  'Recipe',
                  'Status',
                  'Interval',
                  'Next Run',
                  'Priority',
                  'Lane',
                  'Created',
                ].map((header) => (
                  <th
                    key={header}
                    style={{
                      padding: '10px var(--space-3)',
                      fontSize: 'var(--font-size-xs)',
                      fontWeight: 600,
                      color: 'var(--color-warm-gray-500)',
                      textAlign: 'left',
                      textTransform: 'uppercase',
                      letterSpacing: '0.125px',
                    }}
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {schedules.map((schedule) => (
                <tr key={schedule.id} data-testid={`schedule-row-${schedule.id}`}>
                  <td
                    style={{
                      ...cellStyle,
                      maxWidth: '200px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <span
                      style={{ fontWeight: 600, color: 'var(--color-primary-text)' }}
                    >
                      {schedule.schedule_key}
                    </span>
                  </td>
                  <td style={cellStyle}>
                    <span
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        fontFamily: 'monospace',
                      }}
                    >
                      {schedule.source_id.slice(0, 8)}...
                    </span>
                  </td>
                  <td style={cellStyle}>
                    <span
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        fontFamily: 'monospace',
                      }}
                    >
                      {schedule.recipe_id.slice(0, 8)}...
                    </span>
                  </td>
                  <td style={cellStyle}>
                    <StatusPill
                      variant={schedule.status === 'active' ? 'success' : 'default'}
                    >
                      {schedule.status}
                    </StatusPill>
                  </td>
                  <td style={cellStyle}>{formatInterval(schedule.interval_seconds)}</td>
                  <td style={cellStyle}>{formatDate(schedule.next_run_at)}</td>
                  <td style={cellStyle}>{schedule.priority}</td>
                  <td style={cellStyle}>{schedule.lane || '—'}</td>
                  <td style={cellStyle}>{formatDate(schedule.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
