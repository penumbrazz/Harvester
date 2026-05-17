import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { Source } from '../../types/source'
import { STATUS_LABELS } from '../../types/source'
import { Button, Input } from 'animal-island-ui'
import { Select } from '../../components/ui/select'
import { PaginationControls } from '../../components/common/pagination-controls'
import { listSources } from '../../lib/source-api'
import { ProposeSourceForm } from './components/propose-source-form'
import { SourceRow } from './components/source-row'

interface SourcesPageProps {
  config: ApiConfig
}

const PAGE_SIZE = 20

const STATUS_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部状态' },
  ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
]

const KIND_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '全部类型' },
  { value: 'web', label: 'Web' },
  { value: 'rss', label: 'RSS' },
  { value: 'api', label: 'API' },
  { value: 'file', label: 'File' },
]

export function SourcesPage({ config }: SourcesPageProps) {
  const [sources, setSources] = useState<Source[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [kindFilter, setKindFilter] = useState('')
  const [showForm, setShowForm] = useState(false)

  const fetchSources = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listSources(config, {
        status: statusFilter || undefined,
        kind: kindFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      setSources(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载信息源失败')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter, kindFilter, offset])

  useEffect(() => {
    void fetchSources()
  }, [config.baseUrl, fetchSources])

  // Client-side search filtering
  const filtered = search.trim()
    ? sources.filter(
        (s) =>
          s.name.toLowerCase().includes(search.toLowerCase()) ||
          (s.url && s.url.toLowerCase().includes(search.toLowerCase())),
      )
    : sources

  const handleSourceCreated = useCallback(() => {
    setShowForm(false)
    void fetchSources()
  }, [fetchSources])

  return (
    <div
      data-testid="page-sources"
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
          信息源
        </h2>
        <Button onClick={() => setShowForm(true)} data-testid="new-source-button">
          新建信息源
        </Button>
      </div>

      {/* Lifecycle hint */}
      <p
        style={{
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-text-body)',
          marginBottom: 'var(--space-4)',
          lineHeight: 'var(--line-height-normal)',
          flexShrink: 0,
        }}
      >
        信息源生命周期：候选 → 测试中 → 监控中 ⇄ 已暂停 → 已归档
      </p>

      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
          flexWrap: 'wrap',
          alignItems: 'flex-end',
          flexShrink: 0,
        }}
      >
        <div style={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Input
            id="source-search"
            placeholder="按名称或 URL 搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="input-source-search"
          />
        </div>
        <Select
          data-testid="select-status-filter"
          options={STATUS_FILTER_OPTIONS.map((opt) => ({ key: opt.value, label: opt.label }))}
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(val)
            setOffset(0)
          }}
        />
        <Select
          data-testid="select-kind-filter"
          options={KIND_FILTER_OPTIONS.map((opt) => ({ key: opt.value, label: opt.label }))}
          value={kindFilter}
          onChange={(val) => {
            setKindFilter(val)
            setOffset(0)
          }}
        />
      </div>

      {/* Propose form */}
      {showForm && (
        <div
          data-testid="propose-source-panel"
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
            提议新信息源
          </h3>
          <ProposeSourceForm
            config={config}
            onCreated={handleSourceCreated}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <p
          data-testid="sources-loading"
          style={{
            color: 'var(--color-text-body)',
            fontSize: 'var(--font-size-sm)',
            flexShrink: 0,
          }}
        >
          加载信息源中...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="sources-error"
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
      {!loading && !error && filtered.length === 0 && (
        <div
          data-testid="sources-empty"
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
            未找到信息源
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {search || statusFilter || kindFilter
              ? '请尝试调整筛选条件。'
              : '点击"新建信息源"来创建第一个信息源。'}
          </p>
        </div>
      )}

      {/* Source table */}
      {!loading && !error && filtered.length > 0 && (
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
            data-testid="sources-table"
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
                  '名称',
                  '类型',
                  '状态',
                  'URL',
                  '信任度',
                  '失败次数',
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
              {filtered.map((source) => (
                <SourceRow
                  key={source.id}
                  source={source}
                  config={config}
                  onStatusChanged={() => void fetchSources()}
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
