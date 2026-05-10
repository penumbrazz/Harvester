import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { Source } from '../../types/source'
import { STATUS_LABELS } from '../../types/source'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select } from '../../components/ui/select'
import { listSources } from '../../lib/source-api'
import { ProposeSourceForm } from './components/propose-source-form'
import { SourceRow } from './components/source-row'

interface SourcesPageProps {
  config: ApiConfig
}

const STATUS_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
]

const KIND_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Types' },
  { value: 'web', label: 'Web' },
  { value: 'rss', label: 'RSS' },
  { value: 'api', label: 'API' },
  { value: 'file', label: 'File' },
]

export function SourcesPage({ config }: SourcesPageProps) {
  const [sources, setSources] = useState<Source[]>([])
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
      })
      setSources(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources')
    } finally {
      setLoading(false)
    }
  }, [config, statusFilter, kindFilter])

  useEffect(() => {
    if (config.baseUrl) {
      void fetchSources()
    }
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
    <div data-testid="page-sources">
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
          Sources
        </h2>
        <Button onClick={() => setShowForm(true)} data-testid="new-source-button">
          New Source
        </Button>
      </div>

      {/* Lifecycle hint */}
      <p
        style={{
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-warm-gray-500)',
          marginBottom: 'var(--space-4)',
          lineHeight: 'var(--line-height-normal)',
        }}
      >
        Source lifecycle: Candidate → Testing → Watched ⇄ Paused → Archived
      </p>

      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
          flexWrap: 'wrap',
          alignItems: 'flex-end',
        }}
      >
        <div style={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Input
            id="source-search"
            placeholder="Search by name or URL..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="input-source-search"
          />
        </div>
        <Select
          data-testid="select-status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          data-testid="select-kind-filter"
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value)}
        >
          {KIND_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </div>

      {/* Propose form */}
      {showForm && (
        <div
          data-testid="propose-source-panel"
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
            Propose New Source
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
            color: 'var(--color-warm-gray-500)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          Loading sources...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="sources-error"
          style={{ color: 'var(--color-orange)', fontSize: 'var(--font-size-sm)' }}
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
            color: 'var(--color-warm-gray-300)',
          }}
        >
          <p
            style={{
              fontSize: 'var(--font-size-base)',
              marginBottom: 'var(--space-2)',
            }}
          >
            No sources found
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {search || statusFilter || kindFilter
              ? 'Try adjusting your filters.'
              : 'Click "New Source" to create your first source.'}
          </p>
        </div>
      )}

      {/* Source table */}
      {!loading && !error && filtered.length > 0 && (
        <div
          style={{
            overflowX: 'auto',
            border: 'var(--border-whisper)',
            borderRadius: 'var(--radius-lg)',
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
                  borderBottom: 'var(--border-whisper)',
                  backgroundColor: 'var(--color-warm-white)',
                }}
              >
                {[
                  'Name',
                  'Type',
                  'Status',
                  'URL',
                  'Trust',
                  'Failures',
                  'Created',
                  'Actions',
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
    </div>
  )
}
