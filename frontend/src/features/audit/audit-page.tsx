import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { AuditEvent, AuditEventFilters } from '../../types/audit'
import { Button } from 'animal-island-ui'
import { Card } from 'animal-island-ui'
import { StatusPill } from '../../components/ui/status-pill'
import { formatDate } from '../../lib/format'
import { listAuditEvents } from '../../lib/audit-api'

const PAGE_SIZE = 20

/** Known entity types for the filter dropdown. */
const ENTITY_TYPES = [
  { value: '', label: '全部实体类型' },
  { value: 'source', label: '信息源' },
  { value: 'crawl_run', label: '抓取任务' },
  { value: 'job', label: '作业' },
  { value: 'content_item', label: '内容项' },
  { value: 'recipe', label: '配方' },
  { value: 'schedule', label: '调度计划' },
  { value: 'topic', label: '主题' },
]

/** Known actions for the filter dropdown. */
const ACTIONS = [
  { value: '', label: '全部操作' },
  { value: 'source.propose', label: '信息源提议' },
  { value: 'status_change', label: '状态变更' },
  { value: 'status_change_rejected', label: '状态变更拒绝' },
  { value: 'crawl.trigger', label: '抓取触发' },
  { value: 'crawl.complete', label: '抓取完成' },
]

/** Determine pill variant based on action name. */
function actionVariant(
  action: string,
): 'success' | 'error' | 'warning' | 'info' | 'default' {
  if (action.includes('rejected') || action.includes('fail')) return 'error'
  if (action.includes('complete') || action.includes('success')) return 'success'
  if (action.includes('trigger') || action.includes('propose')) return 'info'
  if (action.includes('status_change')) return 'warning'
  return 'default'
}

interface AuditPageProps {
  config: ApiConfig
  /** Optional initial filters for entity-specific views. */
  initialFilters?: AuditEventFilters
}

export function AuditPage({ config, initialFilters }: AuditPageProps) {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [entityType, setEntityType] = useState(initialFilters?.entity_type || '')
  const [actionFilter, setActionFilter] = useState(initialFilters?.action || '')
  const [offset, setOffset] = useState(0)

  const fetchEvents = useCallback(
    async (currentOffset: number, append = false) => {
      setLoading(true)
      setError('')
      try {
        const filters: AuditEventFilters = {
          limit: PAGE_SIZE,
          offset: currentOffset,
        }
        if (entityType) filters.entity_type = entityType
        if (actionFilter) filters.action = actionFilter

        const data = await listAuditEvents(config, filters)
        if (append) {
          setEvents((prev) => [...prev, ...data.items])
        } else {
          setEvents(data.items)
        }
        setTotal(data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载审计事件失败')
      } finally {
        setLoading(false)
      }
    },
    [config, entityType, actionFilter],
  )

  // Refetch when filters change
  useEffect(() => {
    setOffset(0)
    void fetchEvents(0)
  }, [config.baseUrl, entityType, actionFilter, fetchEvents])

  const handleLoadMore = () => {
    const newOffset = offset + PAGE_SIZE
    setOffset(newOffset)
    void fetchEvents(newOffset, true)
  }

  const hasMore = events.length < total

  return (
    <div data-testid="page-audit-log">
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
          审计日志
        </h2>
        <Button
          type="text"
          onClick={() => {
            setOffset(0)
            void fetchEvents(0)
          }}
          data-testid="refresh-audit"
          style={{
            color: 'var(--color-text-body)',
            border: 'var(--border-default)',
          }}
        >
          刷新
        </Button>
      </div>

      {/* Filters */}
      <div
        data-testid="audit-filters"
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
          flexWrap: 'wrap',
        }}
      >
        <select
          data-testid="select-entity-type-filter"
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          style={{
            borderRadius: 'var(--radius-sm)',
            border: 'var(--border-default)',
            backgroundColor: 'var(--color-bg-content)',
            color: 'var(--color-text-body)',
            padding: '6px 12px',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          {ENTITY_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          data-testid="select-action-filter"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          style={{
            borderRadius: 'var(--radius-sm)',
            border: 'var(--border-default)',
            backgroundColor: 'var(--color-bg-content)',
            color: 'var(--color-text-body)',
            padding: '6px 12px',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          {ACTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Loading state */}
      {loading && events.length === 0 && (
        <p
          data-testid="audit-loading"
          style={{
            color: 'var(--color-text-body)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          加载审计事件中...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="audit-error"
          style={{ color: 'var(--color-orange)', fontSize: 'var(--font-size-sm)' }}
        >
          {error}
        </p>
      )}

      {/* Empty state */}
      {!loading && !error && events.length === 0 && (
        <p
          data-testid="audit-empty"
          style={{
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-sm)',
            textAlign: 'center',
            padding: 'var(--space-5)',
          }}
        >
          未找到审计事件
        </p>
      )}

      {/* Timeline */}
      {!loading && !error && events.length > 0 && (
        <div data-testid="audit-timeline">
          {events.map((event) => (
            <Card
              key={event.id}
              style={{
                marginBottom: 'var(--space-3)',
                padding: 'var(--space-4)',
              }}
            >
              {/* Header row: action pill + timestamp */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 'var(--space-2)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                  }}
                >
                  <StatusPill variant={actionVariant(event.action)}>
                    {event.action}
                  </StatusPill>
                  <span
                    style={{
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {event.actor || 'system'}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  {formatDate(event.created_at)}
                </span>
              </div>

              {/* Entity info */}
              <div
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-text-primary)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                <span style={{ fontWeight: 500 }}>{event.entity_type}</span>
                {event.entity_id && (
                  <span
                    style={{
                      fontFamily: 'monospace',
                      color: 'var(--color-text-body)',
                      marginLeft: 'var(--space-2)',
                      fontSize: 'var(--font-size-xs)',
                    }}
                  >
                    {event.entity_id.slice(0, 8)}
                  </span>
                )}
              </div>

              {/* State summary — only summary text, no raw payload */}
              {(event.before_summary || event.after_summary) && (
                <div
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-body)',
                    marginTop: 'var(--space-2)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                  }}
                >
                  {event.before_summary && <span>变更前: {event.before_summary}</span>}
                  {event.after_summary && <span>变更后: {event.after_summary}</span>}
                </div>
              )}

              {/* Reason */}
              {event.reason && (
                <div
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-secondary)',
                    marginTop: 'var(--space-2)',
                    fontStyle: 'italic',
                  }}
                >
                  原因: {event.reason}
                </div>
              )}
            </Card>
          ))}

          {/* Load more */}
          {hasMore && (
            <div style={{ textAlign: 'center', marginTop: 'var(--space-3)' }}>
              <Button
                type="default"
                data-testid="audit-load-more"
                onClick={handleLoadMore}
                disabled={loading}
              >
                {loading ? '加载中...' : `加载更多（剩余 ${total - events.length} 条）`}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
