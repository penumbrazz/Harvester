import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { AuditEvent, AuditEventFilters } from '../../types/audit'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Select } from '../../components/ui/select'
import { StatusPill } from '../../components/ui/status-pill'
import { formatDate } from '../../lib/format'
import { listAuditEvents } from '../../lib/audit-api'

const PAGE_SIZE = 20

/** Known entity types for the filter dropdown. */
const ENTITY_TYPES = [
  { value: '', label: 'All Entity Types' },
  { value: 'source', label: 'Source' },
  { value: 'crawl_run', label: 'Crawl Run' },
  { value: 'job', label: 'Job' },
  { value: 'content_item', label: 'Content Item' },
  { value: 'recipe', label: 'Recipe' },
  { value: 'schedule', label: 'Schedule' },
  { value: 'topic', label: 'Topic' },
]

/** Known actions for the filter dropdown. */
const ACTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'source.propose', label: 'Source Propose' },
  { value: 'status_change', label: 'Status Change' },
  { value: 'status_change_rejected', label: 'Status Rejected' },
  { value: 'crawl.trigger', label: 'Crawl Trigger' },
  { value: 'crawl.complete', label: 'Crawl Complete' },
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
        setError(err instanceof Error ? err.message : 'Failed to load audit events')
      } finally {
        setLoading(false)
      }
    },
    [config, entityType, actionFilter],
  )

  // Refetch when filters change
  useEffect(() => {
    if (config.baseUrl) {
      setOffset(0)
      void fetchEvents(0)
    }
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
          Audit Log
        </h2>
        <Button
          variant="ghost"
          onClick={() => {
            setOffset(0)
            void fetchEvents(0)
          }}
          data-testid="refresh-audit"
          style={{
            color: 'var(--color-warm-gray-500)',
            border: 'var(--border-whisper)',
          }}
        >
          Refresh
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
        <Select
          label="Entity Type"
          data-testid="select-entity-type-filter"
          value={entityType}
          onChange={(e) => setEntityType((e.target as HTMLSelectElement).value)}
        >
          {ENTITY_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          label="Action"
          data-testid="select-action-filter"
          value={actionFilter}
          onChange={(e) => setActionFilter((e.target as HTMLSelectElement).value)}
        >
          {ACTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </div>

      {/* Loading state */}
      {loading && events.length === 0 && (
        <p
          data-testid="audit-loading"
          style={{
            color: 'var(--color-warm-gray-500)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          Loading audit events...
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
            color: 'var(--color-warm-gray-300)',
            fontSize: 'var(--font-size-sm)',
            textAlign: 'center',
            padding: 'var(--space-5)',
          }}
        >
          No audit events found
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
                      color: 'var(--color-warm-gray-300)',
                    }}
                  >
                    {event.actor || 'system'}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-warm-gray-300)',
                  }}
                >
                  {formatDate(event.created_at)}
                </span>
              </div>

              {/* Entity info */}
              <div
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-primary-text)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                <span style={{ fontWeight: 500 }}>{event.entity_type}</span>
                {event.entity_id && (
                  <span
                    style={{
                      fontFamily: 'monospace',
                      color: 'var(--color-warm-gray-500)',
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
                    color: 'var(--color-warm-gray-500)',
                    marginTop: 'var(--space-2)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                  }}
                >
                  {event.before_summary && <span>Before: {event.before_summary}</span>}
                  {event.after_summary && <span>After: {event.after_summary}</span>}
                </div>
              )}

              {/* Reason */}
              {event.reason && (
                <div
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-warm-gray-300)',
                    marginTop: 'var(--space-2)',
                    fontStyle: 'italic',
                  }}
                >
                  Reason: {event.reason}
                </div>
              )}
            </Card>
          ))}

          {/* Load more */}
          {hasMore && (
            <div style={{ textAlign: 'center', marginTop: 'var(--space-3)' }}>
              <Button
                variant="secondary"
                data-testid="audit-load-more"
                onClick={handleLoadMore}
                disabled={loading}
              >
                {loading
                  ? 'Loading...'
                  : `Load More (${total - events.length} remaining)`}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
