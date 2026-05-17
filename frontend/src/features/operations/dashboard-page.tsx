import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { DashboardSummary, FailureItem } from '../../types/observability'
import { Card } from 'animal-island-ui'
import { StatusPill } from '../../components/ui/status-pill'
import { getDashboardSummary, getRecentFailures } from '../../lib/observability-api'
import { formatDate } from '../../lib/format'

interface DashboardPageProps {
  config: ApiConfig
}

/** Metric card displaying a label and value. */
function MetricCard({
  label,
  value,
  sublabel,
}: {
  label: string
  value: number | string
  sublabel?: string
}) {
  return (
    <Card type="default">
      <p
        style={{
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-text-secondary)',
          marginBottom: 'var(--space-2)',
        }}
      >
        {label}
      </p>
      <p
        style={{
          fontSize: 'var(--font-size-xl)',
          fontWeight: 700,
        }}
      >
        {value}
      </p>
      {sublabel && (
        <p
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-text-body)',
            marginTop: 'var(--space-1)',
          }}
        >
          {sublabel}
        </p>
      )}
    </Card>
  )
}

/** Status pill variant helper for failure items. */
function failureVariant(status: string): 'error' | 'warning' | 'default' {
  if (status === 'dead') return 'error'
  if (status === 'failed') return 'warning'
  return 'default'
}

/** Display a list of recent failures. */
function FailurePanel({ items, title }: { items: FailureItem[]; title: string }) {
  if (items.length === 0) return null
  return (
    <div style={{ marginBottom: 'var(--space-4)' }}>
      <h4
        style={{
          fontFamily: 'var(--font-family)',
          fontSize: 'var(--font-size-base)',
          fontWeight: 600,
          marginBottom: 'var(--space-2)',
        }}
      >
        {title}
      </h4>
      <div
        style={{
          overflowX: 'auto',
          border: 'var(--border-default)',
          borderRadius: 'var(--radius-lg)',
        }}
      >
        <table
          data-testid={`failures-${title.toLowerCase().replace(/\s+/g, '-')}`}
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
              {['ID', '状态', '错误', '创建时间'].map((header) => (
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
            {items.map((item) => (
              <tr key={item.id} style={{ borderBottom: 'var(--border-default)' }}>
                <td
                  style={{
                    padding: '10px var(--space-3)',
                    fontSize: 'var(--font-size-sm)',
                    verticalAlign: 'middle',
                    fontFamily: 'monospace',
                    maxWidth: '120px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {item.id.slice(0, 8)}
                </td>
                <td
                  style={{
                    padding: '10px var(--space-3)',
                    fontSize: 'var(--font-size-sm)',
                    verticalAlign: 'middle',
                  }}
                >
                  <StatusPill variant={failureVariant(item.status)}>
                    {item.status}
                  </StatusPill>
                </td>
                <td
                  style={{
                    padding: '10px var(--space-3)',
                    fontSize: 'var(--font-size-sm)',
                    verticalAlign: 'middle',
                    color: 'var(--color-text-body)',
                    maxWidth: '300px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {item.error_message || '--'}
                </td>
                <td
                  style={{
                    padding: '10px var(--space-3)',
                    fontSize: 'var(--font-size-sm)',
                    verticalAlign: 'middle',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  {formatDate(item.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function DashboardPage({ config }: DashboardPageProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [failures, setFailures] = useState<FailureItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [summaryData, failuresData] = await Promise.all([
        getDashboardSummary(config),
        getRecentFailures(config, 5),
      ])
      setSummary(summaryData)
      setFailures([...failuresData.crawl_runs, ...failuresData.jobs])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载仪表盘失败')
    } finally {
      setLoading(false)
    }
  }, [config])

  useEffect(() => {
    void fetchData()
  }, [config.baseUrl, fetchData])

  return (
    <div data-testid="page-dashboard">
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
          仪表盘
        </h2>
        <button
          onClick={() => void fetchData()}
          data-testid="refresh-dashboard"
          style={{
            padding: '6px 12px',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            fontFamily: 'var(--font-family)',
            color: 'var(--color-text-body)',
            background: 'transparent',
            border: 'var(--border-default)',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
          }}
        >
          刷新
        </button>
      </div>

      {loading && (
        <p
          data-testid="dashboard-loading"
          style={{
            color: 'var(--color-text-body)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          加载仪表盘中...
        </p>
      )}

      {!loading && error && (
        <p
          data-testid="dashboard-error"
          style={{ color: 'var(--color-orange)', fontSize: 'var(--font-size-sm)' }}
        >
          {error}
        </p>
      )}

      {!loading && !error && summary && (
        <>
          {/* Metric cards */}
          <div
            data-testid="dashboard-metrics"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--space-4)',
              marginBottom: 'var(--space-5)',
            }}
          >
            <MetricCard
              label="信息源"
              value={summary.sources.total}
              sublabel={formatBreakdown(summary.sources.by_status)}
            />
            <MetricCard
              label="抓取任务"
              value={summary.crawl_runs.total}
              sublabel={formatBreakdown(summary.crawl_runs.by_status)}
            />
            <MetricCard
              label="作业"
              value={summary.jobs.total}
              sublabel={formatBreakdown(summary.jobs.by_status)}
            />
            <MetricCard label="内容项" value={summary.content_items.total} />
            <MetricCard
              label="失败"
              value={summary.failures.total}
              sublabel={formatBreakdown(summary.failures.by_status)}
            />
            <MetricCard label="审计事件" value={summary.audit_events.total} />
          </div>

          {/* Recent failures */}
          <Card type="default">
            <h3
              style={{
                fontFamily: 'var(--font-family)',
                fontSize: 'var(--font-size-base)',
                fontWeight: 600,
                marginBottom: 'var(--space-3)',
              }}
            >
              近期失败
            </h3>
            {failures.length === 0 ? (
              <p
                data-testid="dashboard-no-failures"
                style={{
                  color: 'var(--color-text-secondary)',
                  fontSize: 'var(--font-size-sm)',
                  textAlign: 'center',
                  padding: 'var(--space-4)',
                }}
              >
                暂无近期失败记录
              </p>
            ) : (
              <FailurePanel items={failures.slice(0, 5)} title="近期失败" />
            )}
          </Card>
        </>
      )}
    </div>
  )
}

/** Format a status breakdown map into a readable string. */
function formatBreakdown(byStatus: Record<string, number>): string {
  const entries = Object.entries(byStatus).filter(([, count]) => count > 0)
  if (entries.length === 0) return ''
  return entries.map(([status, count]) => `${count} ${status}`).join(', ')
}
