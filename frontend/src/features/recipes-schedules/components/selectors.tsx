import { useEffect, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type { Recipe } from '../../../types/recipe'
import type { Source } from '../../../types/source'
import { listRecipes } from '../../../lib/recipe-api'
import { listSources } from '../../../lib/source-api'
import { Select } from '../../../components/ui/select'

interface SourceSelectorProps {
  config: ApiConfig
  value: string
  onChange: (value: string) => void
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
      .then((res) => setSources(res.items))
      .catch(() => setSources([]))
  }, [baseUrl, token])

  const filtered = schedulableOnly
    ? sources.filter((s) => s.status === 'watched' || s.status === 'active')
    : sources

  const options = [
    { key: '', label: '选择信息源...' },
    ...filtered.map((s) => ({ key: s.id, label: `${s.name} (${s.status})` })),
  ]

  return (
    <Select
      id={id}
      options={options}
      value={value}
      onChange={onChange}
      data-testid={rest['data-testid'] || 'select-source'}
    />
  )
}

interface ApprovedRecipeSelectorProps {
  config: ApiConfig
  value: string
  onChange: (value: string) => void
  id?: string
  'data-testid'?: string
}

/** Selector that only shows approved recipes. Non-approved recipes are excluded. */
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
      .then((res) => setRecipes(res.items))
      .catch(() => setRecipes([]))
  }, [baseUrl, token])

  const options = [
    { key: '', label: '选择配方...' },
    ...recipes.map((r) => ({
      key: r.id,
      label: `${r.name} (${r.executor})${r.approval_status !== 'approved' ? ` — ${r.approval_status}` : ''}`,
    })),
  ]

  return (
    <Select
      id={id}
      options={options}
      value={value}
      onChange={onChange}
      data-testid={rest['data-testid'] || 'select-approved-recipe'}
    />
  )
}
