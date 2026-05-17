import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { Schedule } from '../../types/schedule'
import { SCHEDULE_STATUS_OPTIONS } from '../../types/schedule'
import { Button, Input } from 'animal-island-ui'
import { Select } from '../../components/ui/select'
import { PaginationControls } from '../../components/common/pagination-controls'
import { listSchedules, createSchedule } from '../../lib/schedule-api'
import { ApprovedRecipeSelector } from './components/selectors'
import { SourceSelector } from './components/selectors'
import { ScheduleRow } from './components/schedule-row'

interface SchedulesPageProps {
  config: ApiConfig
}

const PAGE_SIZE = 20

const SCHEDULE_STATUS_FILTER_OPTIONS = SCHEDULE_STATUS_OPTIONS.map((opt) => ({
  key: opt.value,
  label: opt.label,
}))

export function SchedulesPage({ config }: SchedulesPageProps) {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
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
        limit: PAGE_SIZE,
        offset,
      })
      setSchedules(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载调度计划失败')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter, offset])

  useEffect(() => {
    void fetchSchedules()
  }, [config.baseUrl, fetchSchedules])

  const handleSourceChange = useCallback((value: string) => {
    setFormSourceId(value)
  }, [])

  const handleRecipeChange = useCallback((value: string) => {
    setFormRecipeId(value)
  }, [])

  const handleCreateSchedule = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setFormError('')

      if (!formSourceId) {
        setFormError('信息源为必填项')
        return
      }
      if (!formRecipeId) {
        setFormError('配方为必填项')
        return
      }

      const interval = parseInt(formInterval, 10)
      if (isNaN(interval) || interval < 60) {
        setFormError('间隔时间至少为 60 秒')
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
        setFormError(err instanceof Error ? err.message : '创建调度计划失败')
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
    <div
      data-testid="page-schedules"
      style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-5)',
          flexShrink: 0,
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
          调度计划
        </h2>
        <Button onClick={() => setShowForm(true)} data-testid="new-schedule-button">
          新建调度
        </Button>
      </div>

      {/* Hint */}
      <p
        style={{
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-text-body)',
          marginBottom: 'var(--space-4)',
          lineHeight: 'var(--line-height-normal)',
          flexShrink: 0,
        }}
      >
        监控调度定义了信息源的抓取时间和方式。只有监控中/活跃的信息源和已批准的配方才能被调度。
      </p>

      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
          flexWrap: 'wrap',
          flexShrink: 0,
          alignItems: 'flex-end',
        }}
      >
        <Select
          data-testid="select-schedule-status-filter"
          options={SCHEDULE_STATUS_FILTER_OPTIONS}
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(val)
            setOffset(0)
          }}
        />
      </div>

      {/* Create schedule form */}
      {showForm && (
        <div
          data-testid="create-schedule-panel"
          style={{
            marginBottom: 'var(--space-4)',
            padding: 'var(--space-4)',
            backgroundColor: 'var(--color-bg-content)',
            borderRadius: 'var(--radius-lg)',
            border: 'var(--border-default)',
            flexShrink: 0,
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
            创建新调度
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
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                信息源（仅可调度的）
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
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                配方（仅已批准的）
              </label>
              <ApprovedRecipeSelector
                config={config}
                value={formRecipeId}
                onChange={handleRecipeChange}
                data-testid="select-schedule-recipe"
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
                间隔时间（秒）
              </label>
              <Input
                id="schedule-interval"
                placeholder="3600"
                value={formInterval}
                onChange={(e) => setFormInterval(e.target.value)}
                data-testid="input-schedule-interval"
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
                id="schedule-priority"
                placeholder="0"
                value={formPriority}
                onChange={(e) => setFormPriority(e.target.value)}
                data-testid="input-schedule-priority"
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
                通道（可选）
              </label>
              <Input
                id="schedule-lane"
                placeholder="例如 default"
                value={formLane}
                onChange={(e) => setFormLane(e.target.value)}
                data-testid="input-schedule-lane"
              />
            </div>

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
                htmlType="submit"
                disabled={formSubmitting}
                data-testid="submit-create-schedule"
              >
                {formSubmitting ? '创建中...' : '创建调度'}
              </Button>
              <Button
                type="default"
                onClick={() => {
                  setShowForm(false)
                  setFormError('')
                }}
                data-testid="cancel-create-schedule"
              >
                取消
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
            color: 'var(--color-text-body)',
            fontSize: 'var(--font-size-sm)',
            flexShrink: 0,
          }}
        >
          加载调度计划中...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="schedules-error"
          style={{
            color: 'var(--color-orange)',
            fontSize: 'var(--font-size-sm)',
            flexShrink: 0,
          }}
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
            color: 'var(--color-text-secondary)',
            flexShrink: 0,
          }}
        >
          <p
            style={{
              fontSize: 'var(--font-size-base)',
              marginBottom: 'var(--space-2)',
            }}
          >
            未找到调度计划
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {statusFilter
              ? '请尝试调整筛选条件。'
              : '点击"新建调度"来创建第一个调度计划。'}
          </p>
        </div>
      )}

      {/* Schedule table */}
      {!loading && !error && schedules.length > 0 && (
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            border: 'var(--border-default)',
            borderRadius: 'var(--radius-lg)',
            minHeight: 0,
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
                  borderBottom: 'var(--border-default)',
                  backgroundColor: 'var(--color-bg-content)',
                }}
              >
                {[
                  '标识',
                  '信息源',
                  '配方',
                  '状态',
                  '间隔',
                  '下次运行',
                  '优先级',
                  '通道',
                  '创建时间',
                  '操作',
                ].map((header) => (
                  <th
                    key={header}
                    style={{
                      padding: '10px var(--space-3)',
                      fontSize: 'var(--font-size-xs)',
                      fontWeight: 600,
                      color: 'var(--color-text-body)',
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
                <ScheduleRow
                  key={schedule.id}
                  schedule={schedule}
                  config={config}
                  onChanged={() => void fetchSchedules()}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && (
        <div style={{ flexShrink: 0 }}>
          <PaginationControls
            total={total}
            offset={offset}
            pageSize={PAGE_SIZE}
            onPageChange={setOffset}
          />
        </div>
      )}
    </div>
  )
}
