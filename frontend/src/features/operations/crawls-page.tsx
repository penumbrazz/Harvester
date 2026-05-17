import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { CrawlRun, TriggerCrawlResponse } from '../../types/observability'
import { Button, Select } from 'animal-island-ui'
import { StatusPill } from '../../components/ui/status-pill'
import { PaginationControls } from '../../components/common/pagination-controls'
import {
  ApprovedRecipeSelector,
  SourceSelector,
} from '../recipes-schedules/components/selectors'
import { listCrawlRuns, triggerCrawlRun } from '../../lib/observability-api'
import { formatDate } from '../../lib/format'
import { cellStyle } from '../../lib/table-styles'

interface CrawlsPageProps {
  config: ApiConfig
}

const PAGE_SIZE = 20

const STATUS_FILTER_OPTIONS: { key: string; label: string }[] = [
  { key: '', label: '全部状态' },
  { key: 'pending', label: '等待中' },
  { key: 'running', label: '运行中' },
  { key: 'completed', label: '已完成' },
  { key: 'failed', label: '已失败' },
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
  const [offset, setOffset] = useState(0)
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
        limit: PAGE_SIZE,
        offset,
      })
      setRuns(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载抓取任务失败')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter, offset])

  useEffect(() => {
    void fetchRuns()
  }, [config.baseUrl, fetchRuns])

  const handleTriggerCrawl = useCallback(async () => {
    if (!formSourceId || !formRecipeId) {
      setFormError('请选择信息源和配方')
      return
    }
    setFormError('')
    setFormSubmitting(true)
    try {
      const result = await triggerCrawlRun(config, {
        source_id: formSourceId,
        recipe_id: formRecipeId,
      })
      setTriggerResult(result)
      setShowForm(false)
      setFormSourceId('')
      setFormRecipeId('')
      void fetchRuns()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '触发抓取失败')
    } finally {
      setFormSubmitting(false)
    }
  }, [config, formSourceId, formRecipeId, fetchRuns])

  return (
    <div
      data-testid="page-crawls"
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
          抓取任务
        </h2>
        <Button
          onClick={() => setShowForm(!showForm)}
          data-testid="trigger-crawl-button"
        >
          触发抓取
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
            border: 'var(--border-default)',
            backgroundColor: 'var(--color-bg-content)',
            fontSize: 'var(--font-size-sm)',
            flexShrink: 0,
          }}
        >
          <span style={{ fontWeight: 600 }}>抓取已触发：</span>{' '}
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
            触发新抓取
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
              <label
                htmlFor="source-id"
                style={{
                  display: 'block',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  color: 'var(--color-text-body)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                信息源
              </label>
              <SourceSelector
                config={config}
                value={formSourceId}
                onChange={(e) => setFormSourceId(e.target.value)}
                id="source-id"
                data-testid="select-source"
              />
            </div>
            <div style={{ flex: '1 1 200px', minWidth: '200px' }}>
              <label
                htmlFor="recipe-id"
                style={{
                  display: 'block',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: 600,
                  color: 'var(--color-text-body)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                配方
              </label>
              <ApprovedRecipeSelector
                config={config}
                value={formRecipeId}
                onChange={(e) => setFormRecipeId(e.target.value)}
                id="recipe-id"
                data-testid="select-approved-recipe"
              />
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button
                onClick={() => void handleTriggerCrawl()}
                disabled={formSubmitting}
                data-testid="submit-trigger-crawl"
              >
                {formSubmitting ? '运行中...' : '开始'}
              </Button>
              <Button
                type="default"
                onClick={() => {
                  setShowForm(false)
                  setFormError('')
                  setFormSourceId('')
                  setFormRecipeId('')
                }}
                data-testid="cancel-trigger-crawl"
              >
                取消
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
          flexShrink: 0,
        }}
      >
        <Select
          data-testid="select-crawl-status-filter"
          options={STATUS_FILTER_OPTIONS}
          value={statusFilter}
          onChange={(val: string) => {
            setStatusFilter(val)
            setOffset(0)
          }}
        />
        <span
          style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-body)',
          }}
        >
          {total} 条记录
        </span>
      </div>

      {/* Loading state */}
      {loading && (
        <p
          data-testid="crawls-loading"
          style={{
            color: 'var(--color-text-body)',
            fontSize: 'var(--font-size-sm)',
            flexShrink: 0,
          }}
        >
          加载抓取任务中...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="crawls-error"
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
      {!loading && !error && runs.length === 0 && (
        <div
          data-testid="crawls-empty"
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
            未找到抓取任务
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {statusFilter ? '请尝试调整筛选条件。' : '触发一次抓取以开始。'}
          </p>
        </div>
      )}

      {/* Crawl runs table */}
      {!loading && !error && runs.length > 0 && (
        <div
          style={{
            overflow: 'auto',
            flex: 1,
            minHeight: 0,
            border: 'var(--border-default)',
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
                  borderBottom: 'var(--border-default)',
                  backgroundColor: 'var(--color-bg-content)',
                }}
              >
                {['ID', '信息源', '状态', 'HTTP', '错误', '开始时间', '完成时间'].map(
                  (header) => (
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
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} style={{ borderBottom: 'var(--border-default)' }}>
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
                      maxWidth: '120px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={run.source_name || run.source_id || ''}
                  >
                    {run.source_name || '--'}
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
                      color: 'var(--color-text-body)',
                      maxWidth: '250px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={run.error_message || ''}
                  >
                    {run.error_message || '--'}
                  </td>
                  <td style={{ ...cellStyle, color: 'var(--color-text-secondary)' }}>
                    {run.started_at ? formatDate(run.started_at) : '--'}
                  </td>
                  <td style={{ ...cellStyle, color: 'var(--color-text-secondary)' }}>
                    {run.completed_at ? formatDate(run.completed_at) : '--'}
                  </td>
                </tr>
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
