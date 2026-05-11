import { type ChangeEvent, useEffect, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type { Recipe } from '../../../types/recipe'
import type { Source } from '../../../types/source'
import { listRecipes } from '../../../lib/recipe-api'
import { listSources } from '../../../lib/source-api'

interface SourceSelectorProps {
  config: ApiConfig
  value: string
  onChange: (e: ChangeEvent<HTMLSelectElement>) => void
  /** Only show sources that are schedulable (watched or active). */
  schedulableOnly?: boolean
  id?: string
  'data-testid'?: string
}

/** Selector for sources, optionally filtered to schedulable ones. */
export function SourceSelector({
  config,
  value,
  onChange,
  schedulableOnly = false,
  id,
  ...rest
}: SourceSelectorProps) {
  const [sources, setSources] = useState<Source[]>([])
  const { baseUrl, token } = config

  useEffect(() => {
    if (!baseUrl) return
    void listSources({ baseUrl, token })
      .then(setSources)
      .catch(() => setSources([]))
  }, [baseUrl, token])

  const filtered = schedulableOnly
    ? sources.filter((s) => s.status === 'watched' || s.status === 'active')
    : sources

  return (
    <select
      id={id}
      value={value}
      onChange={onChange}
      data-testid={rest['data-testid'] || 'select-source'}
      style={{
        padding: '6px',
        borderRadius: 'var(--radius-sm)',
        border: 'var(--border-input)',
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-base)',
        color: 'rgba(0,0,0,0.9)',
        backgroundColor: 'var(--color-white)',
        outline: 'none',
      }}
    >
      <option value="">选择信息源...</option>
      {filtered.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name} ({s.status})
        </option>
      ))}
    </select>
  )
}

interface ApprovedRecipeSelectorProps {
  config: ApiConfig
  value: string
  onChange: (e: ChangeEvent<HTMLSelectElement>) => void
  id?: string
  'data-testid'?: string
}

/** Selector that only shows approved recipes. Non-approved recipes show a reason. */
export function ApprovedRecipeSelector({
  config,
  value,
  onChange,
  id,
  ...rest
}: ApprovedRecipeSelectorProps) {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const { baseUrl, token } = config

  useEffect(() => {
    if (!baseUrl) return
    void listRecipes({ baseUrl, token })
      .then(setRecipes)
      .catch(() => setRecipes([]))
  }, [baseUrl, token])

  return (
    <select
      id={id}
      value={value}
      onChange={onChange}
      data-testid={rest['data-testid'] || 'select-approved-recipe'}
      style={{
        padding: '6px',
        borderRadius: 'var(--radius-sm)',
        border: 'var(--border-input)',
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--font-size-base)',
        color: 'rgba(0,0,0,0.9)',
        backgroundColor: 'var(--color-white)',
        outline: 'none',
      }}
    >
      <option value="">选择配方...</option>
      {recipes.map((r) => (
        <option key={r.id} value={r.id} disabled={r.approval_status !== 'approved'}>
          {r.name} ({r.executor})
          {r.approval_status !== 'approved' ? ` — ${r.approval_status}` : ''}
        </option>
      ))}
    </select>
  )
}
