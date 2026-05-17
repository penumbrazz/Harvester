import { useCallback, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type { SourceKind } from '../../../types/source'
import { Button, Input } from 'animal-island-ui'
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <label
          htmlFor="source-name"
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            color: 'var(--color-text-body)',
          }}
        >
          名称
        </label>
        <Input
          id="source-name"
          placeholder="例如 TechNews"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="input-source-name"
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <label
          htmlFor="source-kind"
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            color: 'var(--color-text-body)',
          }}
        >
          类型
        </label>
        <Select
          id="source-kind"
          data-testid="select-source-kind"
          options={KIND_OPTIONS.map((opt) => ({ key: opt.value, label: opt.label }))}
          value={kind}
          onChange={(val) => setKind(val as SourceKind)}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <label
          htmlFor="source-url"
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            color: 'var(--color-text-body)',
          }}
        >
          URL
        </label>
        <Input
          id="source-url"
          placeholder="https://example.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          data-testid="input-source-url"
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <label
          htmlFor="source-trust"
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            color: 'var(--color-text-body)',
          }}
        >
          信任级别
        </label>
        <Select
          id="source-trust"
          data-testid="select-source-trust"
          options={TRUST_OPTIONS.map((level) => ({
            key: level,
            label: TRUST_LABELS[level],
          }))}
          value={trustLevel}
          onChange={setTrustLevel}
        />
      </div>

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
        <Button
          htmlType="submit"
          type="primary"
          disabled={submitting}
          data-testid="submit-propose-source"
        >
          {submitting ? '创建中...' : '创建信息源'}
        </Button>
        <Button
          htmlType="button"
          type="default"
          onClick={onCancel}
          data-testid="cancel-propose-source"
        >
          取消
        </Button>
      </div>
    </form>
  )
}
