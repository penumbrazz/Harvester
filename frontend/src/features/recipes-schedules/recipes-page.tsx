import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { Recipe, RecipeApprovalStatus } from '../../types/recipe'
import {
  APPROVAL_STATUS_LABELS,
  APPROVAL_STATUS_VARIANTS,
  EXECUTOR_OPTIONS,
  RISK_LEVEL_OPTIONS,
} from '../../types/recipe'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select } from '../../components/ui/select'
import { StatusPill } from '../../components/ui/status-pill'
import { formatDate } from '../../lib/format'
import { approveRecipe, createRecipe, listRecipes } from '../../lib/recipe-api'
import { cellStyle } from '../../lib/table-styles'

interface RecipesPageProps {
  config: ApiConfig
}

const APPROVAL_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  ...Object.entries(APPROVAL_STATUS_LABELS).map(([value, label]) => ({ value, label })),
]

const EXECUTOR_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Executors' },
  ...EXECUTOR_OPTIONS.map((opt) => ({ value: opt.value, label: opt.label })),
]

export function RecipesPage({ config }: RecipesPageProps) {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [approvalFilter, setApprovalFilter] = useState('')
  const [executorFilter, setExecutorFilter] = useState('')
  const [showForm, setShowForm] = useState(false)

  // Form state
  const [formName, setFormName] = useState('')
  const [formExecutor, setFormExecutor] = useState('http_fetch')
  const [formConfig, setFormConfig] = useState('')
  const [formRiskLevel, setFormRiskLevel] = useState('low')
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  const fetchRecipes = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listRecipes(config, {
        approval_status: approvalFilter || undefined,
        executor: executorFilter || undefined,
      })
      setRecipes(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recipes')
    } finally {
      setLoading(false)
    }
  }, [config, approvalFilter, executorFilter])

  useEffect(() => {
    if (config.baseUrl) {
      void fetchRecipes()
    }
  }, [config.baseUrl, fetchRecipes])

  // Client-side search filtering
  const filtered = search.trim()
    ? recipes.filter(
        (r) =>
          r.name.toLowerCase().includes(search.toLowerCase()) ||
          r.executor.toLowerCase().includes(search.toLowerCase()),
      )
    : recipes

  const handleCreateRecipe = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setFormError('')

      if (!formName.trim()) {
        setFormError('Name is required')
        return
      }

      // Validate config JSON if provided
      let parsedConfig: Record<string, unknown> | undefined
      if (formConfig.trim()) {
        try {
          parsedConfig = JSON.parse(formConfig.trim())
        } catch {
          setFormError('Config must be valid JSON')
          return
        }
      }

      setFormSubmitting(true)
      try {
        await createRecipe(config, {
          name: formName.trim(),
          executor: formExecutor,
          config: parsedConfig,
          risk_level: formRiskLevel,
        })
        setShowForm(false)
        setFormName('')
        setFormConfig('')
        setFormExecutor('http_fetch')
        setFormRiskLevel('low')
        void fetchRecipes()
      } catch (err) {
        setFormError(err instanceof Error ? err.message : 'Failed to create recipe')
      } finally {
        setFormSubmitting(false)
      }
    },
    [config, formName, formExecutor, formConfig, formRiskLevel, fetchRecipes],
  )

  const handleApprove = useCallback(
    async (recipeId: string) => {
      try {
        await approveRecipe(config, recipeId)
        void fetchRecipes()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to approve recipe')
      }
    },
    [config, fetchRecipes],
  )

  return (
    <div data-testid="page-recipes">
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
          Recipes
        </h2>
        <Button onClick={() => setShowForm(true)} data-testid="new-recipe-button">
          New Recipe
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
        Recipe lifecycle: Pending → Approved → Deprecated. Only approved recipes can be
        used in schedules.
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
            id="recipe-search"
            placeholder="Search by name or executor..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="input-recipe-search"
          />
        </div>
        <Select
          data-testid="select-approval-filter"
          value={approvalFilter}
          onChange={(e) => setApprovalFilter(e.target.value)}
        >
          {APPROVAL_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          data-testid="select-executor-filter"
          value={executorFilter}
          onChange={(e) => setExecutorFilter(e.target.value)}
        >
          {EXECUTOR_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </div>

      {/* Create recipe form */}
      {showForm && (
        <div
          data-testid="create-recipe-panel"
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
            Create New Recipe
          </h3>
          <form
            data-testid="create-recipe-form"
            onSubmit={handleCreateRecipe}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-3)',
            }}
          >
            <Input
              id="recipe-name"
              label="Name"
              placeholder="e.g. TechNews Scraper"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              data-testid="input-recipe-name"
            />

            <Select
              id="recipe-executor"
              label="Executor"
              data-testid="select-recipe-executor"
              value={formExecutor}
              onChange={(e) => setFormExecutor(e.target.value)}
            >
              {EXECUTOR_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                htmlFor="recipe-config"
                style={{
                  fontFamily: 'var(--font-family)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-warm-gray-500)',
                }}
              >
                Config (JSON)
              </label>
              <textarea
                id="recipe-config"
                placeholder='{"url": "https://example.com"}'
                value={formConfig}
                onChange={(e) => setFormConfig(e.target.value)}
                data-testid="input-recipe-config"
                rows={4}
                style={{
                  padding: '6px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'var(--border-input)',
                  fontFamily: 'var(--font-family)',
                  fontSize: 'var(--font-size-sm)',
                  color: 'rgba(0,0,0,0.9)',
                  backgroundColor: 'var(--color-white)',
                  outline: 'none',
                  resize: 'vertical',
                }}
              />
            </div>

            <Select
              id="recipe-risk"
              label="Risk Level"
              data-testid="select-recipe-risk"
              value={formRiskLevel}
              onChange={(e) => setFormRiskLevel(e.target.value)}
            >
              {RISK_LEVEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>

            {formError && (
              <p
                data-testid="create-recipe-error"
                style={{
                  color: 'var(--color-orange)',
                  fontSize: 'var(--font-size-sm)',
                  margin: 0,
                }}
              >
                {formError}
              </p>
            )}

            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button
                type="submit"
                disabled={formSubmitting}
                data-testid="submit-create-recipe"
              >
                {formSubmitting ? 'Creating...' : 'Create Recipe'}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowForm(false)
                  setFormError('')
                }}
                data-testid="cancel-create-recipe"
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <p
          data-testid="recipes-loading"
          style={{
            color: 'var(--color-warm-gray-500)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          Loading recipes...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="recipes-error"
          style={{ color: 'var(--color-orange)', fontSize: 'var(--font-size-sm)' }}
        >
          {error}
        </p>
      )}

      {/* Empty state */}
      {!loading && !error && filtered.length === 0 && (
        <div
          data-testid="recipes-empty"
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
            No recipes found
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {search || approvalFilter || executorFilter
              ? 'Try adjusting your filters.'
              : 'Click "New Recipe" to create your first recipe.'}
          </p>
        </div>
      )}

      {/* Recipe table */}
      {!loading && !error && filtered.length > 0 && (
        <div
          style={{
            overflowX: 'auto',
            border: 'var(--border-whisper)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <table
            data-testid="recipes-table"
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
                  'Executor',
                  'Approval',
                  'Risk',
                  'Version',
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
              {filtered.map((recipe) => (
                <tr key={recipe.id} data-testid={`recipe-row-${recipe.id}`}>
                  <td style={cellStyle}>
                    <span
                      style={{ fontWeight: 600, color: 'var(--color-primary-text)' }}
                    >
                      {recipe.name}
                    </span>
                  </td>
                  <td style={cellStyle}>
                    <span
                      style={{
                        textTransform: 'uppercase',
                        fontSize: 'var(--font-size-xs)',
                      }}
                    >
                      {recipe.executor}
                    </span>
                  </td>
                  <td style={cellStyle}>
                    <StatusPill
                      variant={
                        APPROVAL_STATUS_VARIANTS[
                          recipe.approval_status as RecipeApprovalStatus
                        ] || 'default'
                      }
                    >
                      {APPROVAL_STATUS_LABELS[
                        recipe.approval_status as RecipeApprovalStatus
                      ] || recipe.approval_status}
                    </StatusPill>
                  </td>
                  <td style={cellStyle}>{recipe.risk_level}</td>
                  <td style={cellStyle}>{recipe.version}</td>
                  <td style={cellStyle}>{formatDate(recipe.created_at)}</td>
                  <td style={cellStyle}>
                    <div
                      style={{
                        display: 'flex',
                        gap: 'var(--space-1)',
                        alignItems: 'center',
                      }}
                    >
                      {recipe.approval_status === 'pending' && (
                        <Button
                          variant="secondary"
                          data-testid={`approve-recipe-${recipe.id}`}
                          onClick={() => void handleApprove(recipe.id)}
                          style={{
                            padding: '4px 8px',
                            fontSize: 'var(--font-size-xs)',
                          }}
                        >
                          Approve
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
