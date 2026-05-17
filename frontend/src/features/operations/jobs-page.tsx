import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { Job } from '../../types/observability'
import { Card } from '../../components/ui/card'
import { Select } from '../../components/ui/select'
import { StatusPill } from '../../components/ui/status-pill'
import { PaginationControls } from '../../components/common/pagination-controls'
import { listJobs } from '../../lib/observability-api'
import { formatDate } from '../../lib/format'
import { cellStyle } from '../../lib/table-styles'

interface JobsPageProps {
  config: ApiConfig
}

const PAGE_SIZE = 20

const STATUS_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '等待中' },
  { value: 'running', label: '运行中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '已失败' },
  { value: 'dead', label: '已死亡' },
]

const JOB_TYPE_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部类型' },
  { value: 'crawl', label: '抓取' },
  { value: 'extract', label: '提取' },
  { value: 'embed', label: '嵌入' },
]

const LANE_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部通道' },
  { value: 'default', label: '默认' },
  { value: 'priority', label: '优先' },
]

/** Map job status to StatusPill variant. */
function jobStatusVariant(
  status: string,
): 'success' | 'error' | 'warning' | 'info' | 'default' {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'warning'
    case 'dead':
      return 'error'
    case 'running':
      return 'info'
    case 'pending':
      return 'default'
    default:
      return 'default'
  }
}

export function JobsPage({ config }: JobsPageProps) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [jobTypeFilter, setJobTypeFilter] = useState('')
  const [laneFilter, setLaneFilter] = useState('')

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listJobs(config, {
        status: statusFilter || undefined,
        job_type: jobTypeFilter || undefined,
        lane: laneFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      setJobs(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载作业失败')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter, jobTypeFilter, laneFilter, offset])

  useEffect(() => {
    void fetchJobs()
  }, [config.baseUrl, fetchJobs])

  // Compute summary stats from current jobs
  const statusCounts = jobs.reduce<Record<string, number>>((acc, job) => {
    acc[job.status] = (acc[job.status] || 0) + 1
    return acc
  }, {})

  return (
    <div
      data-testid="page-jobs"
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
          作业队列
        </h2>
        <button
          onClick={() => void fetchJobs()}
          data-testid="refresh-jobs"
          style={{
            padding: '6px 12px',
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            fontFamily: 'var(--font-family)',
            color: 'var(--color-warm-gray-500)',
            background: 'transparent',
            border: 'var(--border-whisper)',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
          }}
        >
          刷新
        </button>
      </div>

      {/* Summary cards */}
      {!loading && !error && (
        <div
          data-testid="jobs-summary"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: 'var(--space-3)',
            marginBottom: 'var(--space-5)',
            flexShrink: 0,
          }}
        >
          {STATUS_FILTER_OPTIONS.filter((opt) => opt.value).map((opt) => (
            <Card key={opt.value}>
              <p
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-warm-gray-300)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                {opt.label}
              </p>
              <p
                style={{
                  fontSize: 'var(--font-size-lg)',
                  fontWeight: 700,
                }}
              >
                {statusCounts[opt.value] || 0}
              </p>
            </Card>
          ))}
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
          data-testid="select-job-type-filter"
          value={jobTypeFilter}
          onChange={(e) => {
            setJobTypeFilter(e.target.value)
            setOffset(0)
          }}
        >
          {JOB_TYPE_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          data-testid="select-job-status-filter"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setOffset(0)
          }}
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          data-testid="select-job-lane-filter"
          value={laneFilter}
          onChange={(e) => {
            setLaneFilter(e.target.value)
            setOffset(0)
          }}
        >
          {LANE_FILTER_OPTIONS.map((opt) => (
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
          {total} 个作业
        </span>
      </div>

      {/* Loading state */}
      {loading && (
        <p
          data-testid="jobs-loading"
          style={{
            color: 'var(--color-warm-gray-500)',
            fontSize: 'var(--font-size-sm)',
            flexShrink: 0,
          }}
        >
          加载作业中...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="jobs-error"
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
      {!loading && !error && jobs.length === 0 && (
        <div
          data-testid="jobs-empty"
          style={{
            textAlign: 'center',
            padding: 'var(--space-8) var(--space-4)',
            color: 'var(--color-warm-gray-300)',
            flexShrink: 0,
          }}
        >
          <p
            style={{
              fontSize: 'var(--font-size-base)',
              marginBottom: 'var(--space-2)',
            }}
          >
            未找到作业
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {statusFilter || jobTypeFilter || laneFilter
              ? '请尝试调整筛选条件。'
              : '作业将在系统处理抓取任务时出现。'}
          </p>
        </div>
      )}

      {/* Jobs table */}
      {!loading && !error && jobs.length > 0 && (
        <div
          style={{
            overflow: 'auto',
            flex: 1,
            minHeight: 0,
            border: 'var(--border-whisper)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <table
            data-testid="jobs-table"
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
                  '类型',
                  '状态',
                  '优先级',
                  '尝试次数',
                  '通道',
                  '信息源',
                  '错误',
                  '创建时间',
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
              {jobs.map((job) => (
                <tr key={job.id} style={{ borderBottom: 'var(--border-whisper)' }}>
                  <td style={cellStyle}>
                    <StatusPill variant="default">{job.job_type}</StatusPill>
                  </td>
                  <td style={cellStyle}>
                    <StatusPill variant={jobStatusVariant(job.status)}>
                      {job.status}
                    </StatusPill>
                  </td>
                  <td style={cellStyle}>{job.priority}</td>
                  <td style={cellStyle}>
                    {job.attempts}/{job.max_attempts}
                  </td>
                  <td style={cellStyle}>{job.lane || '--'}</td>
                  <td
                    style={{
                      ...cellStyle,
                      fontFamily: 'monospace',
                      maxWidth: '120px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={job.source_id || ''}
                  >
                    {job.source_id ? job.source_id.slice(0, 8) : '--'}
                  </td>
                  <td
                    style={{
                      ...cellStyle,
                      color: 'var(--color-warm-gray-500)',
                      maxWidth: '250px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={job.last_error || ''}
                  >
                    {job.last_error || '--'}
                  </td>
                  <td style={{ ...cellStyle, color: 'var(--color-warm-gray-300)' }}>
                    {formatDate(job.created_at)}
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
