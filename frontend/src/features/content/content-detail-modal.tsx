import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { ContentDetailResponse } from '../../types/content'
import { CONTENT_STATUS_LABELS, CONTENT_STATUS_VARIANTS } from '../../types/content'
import { StatusPill } from '../../components/ui/status-pill'
import { getContentItemDetail } from '../../lib/content-api'
import { formatDate } from '../../lib/format'

interface ContentDetailModalProps {
  config: ApiConfig
  contentItemId: string | null
  onClose: () => void
}

export function ContentDetailModal({
  config,
  contentItemId,
  onClose,
}: ContentDetailModalProps) {
  const [detail, setDetail] = useState<ContentDetailResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchDetail = useCallback(async () => {
    if (!contentItemId) return
    setLoading(true)
    setError('')
    setDetail(null)
    try {
      const data = await getContentItemDetail(config, contentItemId)
      setDetail(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载详情失败')
    } finally {
      setLoading(false)
    }
  }, [config, contentItemId])

  useEffect(() => {
    if (contentItemId) {
      void fetchDetail()
    }
  }, [contentItemId, fetchDetail])

  useEffect(() => {
    if (!contentItemId) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [contentItemId, onClose])

  if (!contentItemId) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.4)',
        zIndex: 100,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        data-testid="content-detail-modal"
        style={{
          background: 'var(--color-bg-content)',
          borderRadius: 12,
          width: '100%',
          maxWidth: 720,
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid rgba(0,0,0,0.1)',
          boxShadow:
            'rgba(0,0,0,0.01) 0px 1px 3px, rgba(0,0,0,0.02) 0px 3px 7px, rgba(0,0,0,0.02) 0px 7px 15px, rgba(0,0,0,0.04) 0px 14px 28px, rgba(0,0,0,0.05) 0px 23px 52px',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            padding: '20px 24px 16px',
            borderBottom: '1px solid rgba(0,0,0,0.1)',
            flexShrink: 0,
          }}
        >
          <div style={{ flex: 1, marginRight: 16 }}>
            <h3
              style={{
                fontFamily: 'var(--font-family)',
                fontSize: 22,
                fontWeight: 700,
                margin: '0 0 8px',
                lineHeight: 1.27,
                letterSpacing: '-0.25px',
                color: 'rgba(0,0,0,0.95)',
              }}
            >
              {loading ? ' ' : detail?.title || '无标题'}
            </h3>
            {!loading && detail && (
              <div
                style={{
                  display: 'flex',
                  gap: 8,
                  alignItems: 'center',
                  flexWrap: 'wrap',
                }}
              >
                <StatusPill variant="default">{detail.item_type}</StatusPill>
                <StatusPill
                  variant={CONTENT_STATUS_VARIANTS[detail.status] || 'default'}
                >
                  {CONTENT_STATUS_LABELS[detail.status] || detail.status}
                </StatusPill>
                {detail.source_name && (
                  <span
                    style={{
                      fontSize: 12,
                      color: 'var(--color-text-body)',
                    }}
                  >
                    {detail.source_name}
                  </span>
                )}
              </div>
            )}
          </div>
          <button
            data-testid="close-content-detail-button"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 20,
              cursor: 'pointer',
              color: '#a39e98',
              padding: '4px 8px',
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* Meta info */}
        {!loading && detail && (
          <div
            style={{
              padding: '12px 24px',
              borderBottom: '1px solid rgba(0,0,0,0.1)',
              flexShrink: 0,
            }}
          >
            {detail.canonical_url && (
              <a
                href={detail.canonical_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: 'var(--color-accent)',
                  textDecoration: 'none',
                  fontSize: 13,
                  display: 'block',
                  marginBottom: 4,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {detail.canonical_url}
              </a>
            )}
            <div
              style={{
                fontSize: 12,
                color: '#a39e98',
              }}
            >
              创建于 {formatDate(detail.created_at)}
              {' / '}
              更新于 {formatDate(detail.updated_at)}
            </div>
          </div>
        )}

        {/* Body */}
        <div
          data-testid="content-detail-body"
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px 24px',
            minHeight: 0,
          }}
        >
          {loading && (
            <div style={{ color: 'var(--color-text-body)', fontSize: 14 }}>
              加载中...
            </div>
          )}
          {error && <div style={{ color: '#dd5b00', fontSize: 14 }}>{error}</div>}
          {!loading && !error && detail?.latest_version?.normalized_text && (
            <div
              style={{
                fontSize: 15,
                lineHeight: 1.6,
                color: 'rgba(0,0,0,0.95)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {detail.latest_version.normalized_text}
            </div>
          )}
          {!loading && !error && detail && !detail.latest_version && (
            <div style={{ color: '#a39e98', fontSize: 14 }}>暂无正文内容</div>
          )}
          {!loading &&
            !error &&
            detail?.latest_version &&
            !detail.latest_version.normalized_text && (
              <div style={{ color: '#a39e98', fontSize: 14 }}>暂无正文内容</div>
            )}
        </div>
      </div>
    </div>
  )
}
