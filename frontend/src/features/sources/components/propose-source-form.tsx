import { useCallback, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type { SourceKind } from '../../../types/source'
import { Button } from '../../../components/ui/button'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { proposeSource } from '../../../lib/source-api'

interface ProposeSourceFormProps {
  config: ApiConfig
  onCreated: () => void
  onCancel: () => void
}

const KIND_OPTIONS: { value: SourceKind; label: string }[] = [
  { value: 'web', label: 'Web' },
  { value: 'rss', label: 'RSS' },
  { value: 'api', label: 'API' },
  { value: 'file', label: 'File' },
]

const TRUST_OPTIONS = ['low', 'medium', 'high'] as const

export function ProposeSourceForm({
  config,
  onCreated,
  onCancel,
}: ProposeSourceFormProps) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState<SourceKind>('web')
  const [url, setUrl] = useState('')
  const [trustLevel, setTrustLevel] = useState('medium')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError('')

      if (!name.trim()) {
        setError('Name is required')
        return
      }

      setSubmitting(true)
      try {
        await proposeSource(config, {
          name: name.trim(),
          kind,
          url: url.trim() || null,
          trust_level: trustLevel,
        })
        onCreated()
      } catch (err) {
        if (err instanceof Error && err.message.includes('409')) {
          setError(`Source '${name.trim()}' already exists`)
        } else {
          setError(err instanceof Error ? err.message : 'Failed to create source')
        }
      } finally {
        setSubmitting(false)
      }
    },
    [config, name, kind, url, trustLevel, onCreated],
  )

  return (
    <form
      data-testid="propose-source-form"
      onSubmit={handleSubmit}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
      }}
    >
      <Input
        id="source-name"
        label="Name"
        placeholder="e.g. TechNews"
        value={name}
        onChange={(e) => setName(e.target.value)}
        data-testid="input-source-name"
      />

      <Select
        id="source-kind"
        label="Type"
        data-testid="select-source-kind"
        value={kind}
        onChange={(e) => setKind(e.target.value as SourceKind)}
      >
        {KIND_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </Select>

      <Input
        id="source-url"
        label="URL"
        placeholder="https://example.com"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        data-testid="input-source-url"
      />

      <Select
        id="source-trust"
        label="Trust Level"
        data-testid="select-source-trust"
        value={trustLevel}
        onChange={(e) => setTrustLevel(e.target.value)}
      >
        {TRUST_OPTIONS.map((level) => (
          <option key={level} value={level}>
            {level.charAt(0).toUpperCase() + level.slice(1)}
          </option>
        ))}
      </Select>

      {error && (
        <p
          data-testid="propose-source-error"
          style={{
            color: 'var(--color-orange)',
            fontSize: 'var(--font-size-sm)',
            margin: 0,
          }}
        >
          {error}
        </p>
      )}

      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <Button type="submit" disabled={submitting} data-testid="submit-propose-source">
          {submitting ? 'Creating...' : 'Create Source'}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          data-testid="cancel-propose-source"
        >
          Cancel
        </Button>
      </div>
    </form>
  )
}
