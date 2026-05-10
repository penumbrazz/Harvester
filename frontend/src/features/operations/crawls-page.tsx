import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { CrawlRun, TriggerCrawlResponse } from '../../types/observability'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select } from '../../components/ui/select'
import { StatusPill } from '../../components/ui/status-pill'
import { listCrawlRuns, triggerCrawlRun } from '../../lib/observability-api'
import { formatDate } from '../../lib/format'
import { cellStyle } from '../../lib/table-styles'

interface CrawlsPageProps {
  config: ApiConfig
}

const STATUS_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
]

/** Map crawl run status to StatusPill variant. */
function crawlStatusVariant(
  status: string,
): 'success' | 'error' | 'warning' | 'info' | 'default' {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'running':
      return 'info'
    case 'pending':
      return 'default'
    default:
      return 'default'
  }
}

export function CrawlsPage({ config }: CrawlsPageProps) {
  const [runs, setRuns] = useState<CrawlRun[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // Trigger crawl form state
  const [showForm, setShowForm] = useState(false)
  const [formSourceId, setFormSourceId] = useState('')
  const [formRecipeId, setFormRecipeId] = useState('')
  const [formError, setFormError] = useState('')
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [triggerResult, setTriggerResult] = useState<TriggerCrawlResponse | null>(null)

  const fetchRuns = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listCrawlRuns(config, {
        status: statusFilter || undefined,
      })
      setRuns(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load crawl runs')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter])

  useEffect(() => {
    if (config.baseUrl) {
      void fetchRuns()
    }
  }, [config.baseUrl, fetchRuns])

  const handleTriggerCrawl = useCallback(async () => {
    if (!formSourceId.trim() || !formRecipeId.trim()) {
      setFormError('Source ID and Recipe ID are required')
      return
    }
    setFormError('')
    setFormSubmitting(true)
    try {
      const result = await triggerCrawlRun(config, {
        source_id: formSourceId.trim(),
        recipe_id: formRecipeId.trim(),
      })
      setTriggerResult(result)
      setShowForm(false)
      setFormSourceId('')
      setFormRecipeId('')
      void fetchRuns()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to trigger crawl')
    } finally {
      setFormSubmitting(false)
    }
  }, [config, formSourceId, formRecipeId, fetchRuns])

  return (
    <div data-testid="page-crawls">
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
          Crawls
        </h2>
        <Button
          onClick={() => setShowForm(!showForm)}
          data-testid="trigger-crawl-button"
        >
          Trigger Crawl
        </Button>
      </div>

      {/* Trigger crawl result */}
      {triggerResult && (
        <div
          data-testid="trigger-crawl-result"
          style={{
            padding: 'var(--space-3)',
            marginBottom: 'var(--space-4)',
            borderRadius: 'var(--radius-sm)',
            border: 'var(--border-whisper)',
            backgroundColor: 'var(--color-warm-white)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          <span style={{ fontWeight: 600 }}>Crawl triggered:</span>{' '}
          <StatusPill variant={crawlStatusVariant(triggerResult.status)}>
            {triggerResult.status}
          </StatusPill>
          {triggerResult.error_message && (
            <span
              style={{ color: 'var(--color-orange)', marginLeft: 'var(--space-2)' }}
            >
              {triggerResult.error_message}
            </span>
          )}
        </div>
      )}

      {/* Trigger crawl form */}
      {showForm && (
        <div
          data-testid="trigger-crawl-form"
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
            Trigger New Crawl
          </h3>
          <div
            style={{
              display: 'flex',
              gap: 'var(--space-3)',
              alignItems: 'flex-end',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ flex: '1 1 200px', minWidth: '200px' }}>
              <Input
                id="source-id"
                label="Source ID"
                placeholder="UUID of the source"
                value={formSourceId}
                onChange={(e) => setFormSourceId(e.target.value)}
                data-testid="input-source-id"
              />
            </div>
            <div style={{ flex: '1 1 200px', minWidth: '200px' }}>
              <Input
                id="recipe-id"
                label="Recipe ID"
                placeholder="UUID of the recipe"
                value={formRecipeId}
                onChange={(e) => setFormRecipeId(e.target.value)}
                data-testid="input-recipe-id"
              />
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button
                onClick={() => void handleTriggerCrawl()}
                disabled={formSubmitting}
                data-testid="submit-trigger-crawl"
              >
                {formSubmitting ? 'Running...' : 'Start'}
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setShowForm(false)
                  setFormError('')
                  setFormSourceId('')
                  setFormRecipeId('')
                }}
                data-testid="cancel-trigger-crawl"
              >
                Cancel
              </Button>
            </div>
          </div>
          {formError && (
            <p
              data-testid="trigger-crawl-error"
              style={{
                color: 'var(--color-orange)',
                fontSize: 'var(--font-size-sm)',
                marginTop: 'var(--space-2)',
              }}
            >
              {formError}
            </p>
          )}
        </div>
      )}

      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
          alignItems: 'flex-end',
          flexWrap: 'wrap',
        }}
      >
        <Select
          data-testid="select-crawl-status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <span
          style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-warm-gray-500)',
          }}
        >
          {total} run{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Loading state */}
      {loading && (
        <p
          data-testid="crawls-loading"
          style={{
            color: 'var(--color-warm-gray-500)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          Loading crawl runs...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="crawls-error"
          style={{ color: 'var(--color-orange)', fontSize: 'var(--font-size-sm)' }}
        >
          {error}
        </p>
      )}

      {/* Empty state */}
      {!loading && !error && runs.length === 0 && (
        <div
          data-testid="crawls-empty"
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
            No crawl runs found
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {statusFilter
              ? 'Try adjusting your filters.'
              : 'Trigger a crawl to get started.'}
          </p>
        </div>
      )}

      {/* Crawl runs table */}
      {!loading && !error && runs.length > 0 && (
        <div
          style={{
            overflowX: 'auto',
            border: 'var(--border-whisper)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <table
            data-testid="crawls-table"
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
                  'ID',
                  'Source',
                  'Status',
                  'HTTP',
                  'Error',
                  'Started',
                  'Completed',
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
              {runs.map((run) => (
                <tr key={run.id} style={{ borderBottom: 'var(--border-whisper)' }}>
                  <td
                    style={{
                      ...cellStyle,
                      fontFamily: 'monospace',
                      maxWidth: '120px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={run.id}
                  >
                    {run.id.slice(0, 8)}
                  </td>
                  <td
                    style={{
                      ...cellStyle,
                      fontFamily: 'monospace',
                      maxWidth: '120px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={run.source_id || ''}
                  >
                    {run.source_id ? run.source_id.slice(0, 8) : '--'}
                  </td>
                  <td style={cellStyle}>
                    <StatusPill variant={crawlStatusVariant(run.status)}>
                      {run.status}
                    </StatusPill>
                  </td>
                  <td style={cellStyle}>{run.http_status ?? '--'}</td>
                  <td
                    style={{
                      ...cellStyle,
                      color: 'var(--color-warm-gray-500)',
                      maxWidth: '250px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={run.error_message || ''}
                  >
                    {run.error_message || '--'}
                  </td>
                  <td style={{ ...cellStyle, color: 'var(--color-warm-gray-300)' }}>
                    {run.started_at ? formatDate(run.started_at) : '--'}
                  </td>
                  <td style={{ ...cellStyle, color: 'var(--color-warm-gray-300)' }}>
                    {run.completed_at ? formatDate(run.completed_at) : '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
