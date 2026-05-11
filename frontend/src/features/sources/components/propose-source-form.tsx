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

const TRUST_LABELS: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
}

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
        setError('名称为必填项')
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
          setError(`信息源 '${name.trim()}' 已存在`)
        } else {
          setError(err instanceof Error ? err.message : '创建信息源失败')
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
        label="名称"
        placeholder="例如 TechNews"
        value={name}
        onChange={(e) => setName(e.target.value)}
        data-testid="input-source-name"
      />

      <Select
        id="source-kind"
        label="类型"
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
        label="信任级别"
        data-testid="select-source-trust"
        value={trustLevel}
        onChange={(e) => setTrustLevel(e.target.value)}
      >
        {TRUST_OPTIONS.map((level) => (
          <option key={level} value={level}>
            {TRUST_LABELS[level]}
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
          {submitting ? '创建中...' : '创建信息源'}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          data-testid="cancel-propose-source"
        >
          取消
        </Button>
      </div>
    </form>
  )
}
