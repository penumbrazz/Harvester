import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type {
  ContentItem,
  ContentListResponse,
  SearchMode,
  SearchResultItem,
  ViewMode,
} from '../../types/content'
import {
  CONTENT_STATUS_LABELS,
  CONTENT_STATUS_OPTIONS,
  CONTENT_STATUS_VARIANTS,
  ITEM_TYPE_OPTIONS,
} from '../../types/content'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Select } from '../../components/ui/select'
import { StatusPill } from '../../components/ui/status-pill'
import { PaginationControls } from '../../components/common/pagination-controls'
import { listContentItems, searchContentItems } from '../../lib/content-api'
import { formatDate } from '../../lib/format'
import { cellStyle } from '../../lib/table-styles'

interface ContentLibraryPageProps {
  config: ApiConfig
}

const PAGE_SIZE = 20

export function ContentLibraryPage({ config }: ContentLibraryPageProps) {
  // Content list state
  const [contentResponse, setContentResponse] = useState<ContentListResponse | null>(
    null,
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Filter state
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [offset, setOffset] = useState(0)

  // View mode
  const [viewMode, setViewMode] = useState<ViewMode>('list')

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('keyword')
  const [searchResults, setSearchResults] = useState<SearchResultItem[] | null>(null)
  const [searchError, setSearchError] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)

  const isSearching = searchResults !== null

  const fetchContent = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listContentItems(config, {
        status: statusFilter || undefined,
        item_type: typeFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      setContentResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载内容项失败')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter, typeFilter, offset])

  useEffect(() => {
    if (config.baseUrl) {
      void fetchContent()
    }
  }, [config.baseUrl, fetchContent])

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return
    setSearchLoading(true)
    setSearchError('')
    setSearchResults(null)
    try {
      const data = await searchContentItems(config, searchQuery.trim(), searchMode)
      setSearchResults(data.items)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : '搜索失败')
    } finally {
      setSearchLoading(false)
    }
  }, [config, searchQuery, searchMode])

  const handleClearSearch = useCallback(() => {
    setSearchQuery('')
    setSearchResults(null)
    setSearchError('')
  }, [])

  const items = contentResponse?.items || []
  const total = contentResponse?.total || 0
  const hasActiveFilters = statusFilter !== '' || typeFilter !== ''

  return (
    <div
      data-testid="page-content-library"
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
          内容库
        </h2>
      </div>

      {/* Search bar */}
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
            id="content-search"
            placeholder="搜索内容..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            data-testid="search-input"
          />
        </div>
        <Select
          data-testid="search-mode-select"
          value={searchMode}
          onChange={(e) => setSearchMode(e.target.value as SearchMode)}
        >
          <option value="keyword">关键词</option>
          <option value="vector">向量</option>
        </Select>
        <Button onClick={() => void handleSearch()} data-testid="search-button">
          搜索
        </Button>
        {isSearching && (
          <Button
            variant="secondary"
            onClick={handleClearSearch}
            data-testid="search-clear"
          >
            清除
          </Button>
        )}
      </div>

      {/* Search error */}
      {searchError && (
        <p
          data-testid="search-error"
          style={{
            color: 'var(--color-orange)',
            fontSize: 'var(--font-size-sm)',
            marginBottom: 'var(--space-4)',
            flexShrink: 0,
          }}
        >
          {searchError}
        </p>
      )}

      {/* Search loading */}
      {searchLoading && (
        <p
          data-testid="search-loading"
          style={{
            color: 'var(--color-warm-gray-500)',
            fontSize: 'var(--font-size-sm)',
            marginBottom: 'var(--space-4)',
            flexShrink: 0,
          }}
        >
          搜索中...
        </p>
      )}

      {/* Search results */}
      {isSearching && !searchLoading && (
        <div
          data-testid="search-results"
          style={{ marginBottom: 'var(--space-4)', flexShrink: 0 }}
        >
          <h3
            style={{
              fontFamily: 'var(--font-family)',
              fontSize: 'var(--font-size-base)',
              fontWeight: 600,
              marginBottom: 'var(--space-3)',
            }}
          >
            搜索结果 ({searchResults.length})
          </h3>
          {searchMode === 'vector' ? (
            <VectorResults items={searchResults} />
          ) : (
            <KeywordResults items={searchResults} />
          )}
        </div>
      )}

      {/* List view filters and content (hidden when searching) */}
      {!isSearching && (
        <>
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
            <Select
              data-testid="select-type-filter"
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value)
                setOffset(0)
              }}
            >
              {ITEM_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Select
              data-testid="select-status-filter"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setOffset(0)
              }}
            >
              {CONTENT_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            {/* View toggle */}
            <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
              <button
                data-testid="view-list"
                onClick={() => setViewMode('list')}
                style={{
                  padding: '6px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border:
                    viewMode === 'list'
                      ? '1px solid var(--color-notion-blue)'
                      : 'var(--border-whisper)',
                  backgroundColor:
                    viewMode === 'list'
                      ? 'var(--color-badge-blue-bg)'
                      : 'var(--color-white)',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-family)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: viewMode === 'list' ? 600 : 400,
                  color:
                    viewMode === 'list'
                      ? 'var(--color-badge-blue-text)'
                      : 'var(--color-warm-gray-500)',
                }}
              >
                列表
              </button>
              <button
                data-testid="view-grid"
                onClick={() => setViewMode('grid')}
                style={{
                  padding: '6px 10px',
                  borderRadius: 'var(--radius-sm)',
                  border:
                    viewMode === 'grid'
                      ? '1px solid var(--color-notion-blue)'
                      : 'var(--border-whisper)',
                  backgroundColor:
                    viewMode === 'grid'
                      ? 'var(--color-badge-blue-bg)'
                      : 'var(--color-white)',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-family)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: viewMode === 'grid' ? 600 : 400,
                  color:
                    viewMode === 'grid'
                      ? 'var(--color-badge-blue-text)'
                      : 'var(--color-warm-gray-500)',
                }}
              >
                网格
              </button>
            </div>
          </div>

          {/* Loading state */}
          {loading && (
            <p
              data-testid="content-loading"
              style={{
                color: 'var(--color-warm-gray-500)',
                fontSize: 'var(--font-size-sm)',
                flexShrink: 0,
              }}
            >
              加载内容项中...
            </p>
          )}

          {/* Error state */}
          {!loading && error && (
            <p
              data-testid="content-error"
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
          {!loading && !error && items.length === 0 && (
            <div
              data-testid="content-empty"
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
                未找到内容项
              </p>
              <p style={{ fontSize: 'var(--font-size-sm)' }}>
                {hasActiveFilters
                  ? '请尝试调整筛选条件。'
                  : '内容项将在提取后显示在这里。'}
              </p>
            </div>
          )}

          {/* List view */}
          {!loading && !error && items.length > 0 && viewMode === 'list' && (
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
                data-testid="content-table"
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
                    {['标题', '类型', '信息源', '状态', 'URL', '更新时间'].map(
                      (header) => (
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
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <ContentRow key={item.id} item={item} />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Grid view */}
          {!loading && !error && items.length > 0 && viewMode === 'grid' && (
            <div
              data-testid="content-grid"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                gap: 'var(--space-4)',
                flex: 1,
                minHeight: 0,
                overflow: 'auto',
              }}
            >
              {items.map((item) => (
                <ContentCard key={item.id} item={item} />
              ))}
            </div>
          )}

          {/* Pagination */}
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
        </>
      )}
    </div>
  )
}

/** Table row for a content item in list view. */
function ContentRow({ item }: { item: ContentItem }) {
  return (
    <tr style={{ borderBottom: 'var(--border-whisper)' }}>
      <td style={{ ...cellStyle, fontWeight: 500, maxWidth: '300px' }}>
        <div
          style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {item.title || '无标题'}
        </div>
      </td>
      <td style={cellStyle}>
        <StatusPill variant="default">{item.item_type}</StatusPill>
      </td>
      <td style={cellStyle}>{item.source_name || '-'}</td>
      <td style={cellStyle}>
        <StatusPill variant={CONTENT_STATUS_VARIANTS[item.status] || 'default'}>
          {CONTENT_STATUS_LABELS[item.status] || item.status}
        </StatusPill>
      </td>
      <td style={cellStyle}>
        {item.canonical_url ? (
          <a
            href={item.canonical_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: 'var(--color-notion-blue)',
              textDecoration: 'none',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            {item.canonical_url.length > 40
              ? item.canonical_url.substring(0, 40) + '...'
              : item.canonical_url}
          </a>
        ) : (
          '-'
        )}
      </td>
      <td style={cellStyle}>
        <span
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-warm-gray-300)',
          }}
        >
          {formatDate(item.updated_at)}
        </span>
      </td>
    </tr>
  )
}

/** Card for a content item in grid view. */
function ContentCard({ item }: { item: ContentItem }) {
  return (
    <Card
      style={{
        padding: 'var(--space-4)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <h4
          style={{
            fontFamily: 'var(--font-family)',
            fontSize: 'var(--font-size-base)',
            fontWeight: 600,
            margin: 0,
            lineHeight: 1.3,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {item.title || '无标题'}
        </h4>
      </div>
      <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
        <StatusPill variant={CONTENT_STATUS_VARIANTS[item.status] || 'default'}>
          {CONTENT_STATUS_LABELS[item.status] || item.status}
        </StatusPill>
        <StatusPill variant="default">{item.item_type}</StatusPill>
      </div>
      <div
        style={{
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-warm-gray-500)',
        }}
      >
        {item.source_name || '未知信息源'}
      </div>
      {item.canonical_url && (
        <a
          href={item.canonical_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--color-notion-blue)',
            textDecoration: 'none',
            fontSize: 'var(--font-size-xs)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {item.canonical_url}
        </a>
      )}
      <div
        style={{
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-warm-gray-300)',
          marginTop: 'auto',
        }}
      >
        {formatDate(item.updated_at)}
      </div>
    </Card>
  )
}

/** Display keyword search results. */
function KeywordResults({ items }: { items: SearchResultItem[] }) {
  if (items.length === 0) {
    return (
      <p
        style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}
      >
        未找到结果。
      </p>
    )
  }

  return (
    <div
      style={{
        overflowX: 'auto',
        border: 'var(--border-whisper)',
        borderRadius: 'var(--radius-lg)',
      }}
    >
      <table
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
            {['标题', '信息源', 'URL', '创建时间'].map((header) => (
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
          {items.map((item, idx) => (
            <tr
              key={item.item_id || idx}
              style={{ borderBottom: 'var(--border-whisper)' }}
            >
              <td style={{ ...cellStyle, fontWeight: 500 }}>{item.title}</td>
              <td style={cellStyle}>
                <span style={{ fontSize: 'var(--font-size-xs)' }}>
                  {item.source_id ? item.source_id.substring(0, 8) + '...' : '-'}
                </span>
              </td>
              <td style={cellStyle}>
                {item.canonical_url ? (
                  <a
                    href={item.canonical_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: 'var(--color-notion-blue)',
                      textDecoration: 'none',
                      fontSize: 'var(--font-size-sm)',
                    }}
                  >
                    {item.canonical_url.length > 40
                      ? item.canonical_url.substring(0, 40) + '...'
                      : item.canonical_url}
                  </a>
                ) : (
                  '-'
                )}
              </td>
              <td style={cellStyle}>
                <span
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-warm-gray-300)',
                  }}
                >
                  {item.created_at ? formatDate(item.created_at) : '-'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Display vector search results with distance and chunk text. */
function VectorResults({ items }: { items: SearchResultItem[] }) {
  if (items.length === 0) {
    return (
      <p
        style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}
      >
        未找到结果。
      </p>
    )
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
      }}
    >
      {items.map((item, idx) => (
        <div
          key={item.chunk_id || idx}
          style={{
            backgroundColor: 'var(--color-white)',
            border: 'var(--border-whisper)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-4)',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              marginBottom: 'var(--space-2)',
            }}
          >
            <h4
              style={{
                fontFamily: 'var(--font-family)',
                fontSize: 'var(--font-size-base)',
                fontWeight: 600,
                margin: 0,
              }}
            >
              {item.title}
            </h4>
            {item.distance !== undefined && (
              <span
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--color-warm-gray-500)',
                  fontWeight: 500,
                  marginLeft: 'var(--space-3)',
                  whiteSpace: 'nowrap',
                }}
              >
                距离: {item.distance.toFixed(4)}
              </span>
            )}
          </div>
          {item.text && (
            <p
              style={{
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-warm-gray-500)',
                margin: 0,
                lineHeight: 1.5,
              }}
            >
              {item.text}
            </p>
          )}
          <div
            style={{
              display: 'flex',
              gap: 'var(--space-3)',
              marginTop: 'var(--space-2)',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-warm-gray-300)',
            }}
          >
            {item.content_item_id && (
              <span>内容项: {item.content_item_id.substring(0, 8)}...</span>
            )}
            {item.chunk_id && <span>分块: {item.chunk_id.substring(0, 8)}...</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
