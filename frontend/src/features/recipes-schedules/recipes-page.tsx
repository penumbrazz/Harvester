import { useCallback, useEffect, useState } from 'react'

import type { ApiConfig } from '../../types/api'
import type { Recipe } from '../../types/recipe'
import {
  APPROVAL_STATUS_LABELS,
  EXECUTOR_OPTIONS,
  RISK_LEVEL_OPTIONS,
} from '../../types/recipe'
import { Button, Input } from 'animal-island-ui'
import { Select } from '../../components/ui/select'
import { PaginationControls } from '../../components/common/pagination-controls'
import { createRecipe, listRecipes } from '../../lib/recipe-api'
import { RecipeRow } from './components/recipe-row'

interface RecipesPageProps {
  config: ApiConfig
}

const PAGE_SIZE = 20

const APPROVAL_FILTER_OPTIONS = [
  { key: '', label: '全部状态' },
  ...Object.entries(APPROVAL_STATUS_LABELS).map(([key, label]) => ({ key, label })),
]

const EXECUTOR_FILTER_OPTIONS = [
  { key: '', label: '全部执行器' },
  ...EXECUTOR_OPTIONS.map((opt) => ({ key: opt.value, label: opt.label })),
]

const EXECUTOR_FORM_OPTIONS = EXECUTOR_OPTIONS.map((opt) => ({
  key: opt.value,
  label: opt.label,
}))

const RISK_FORM_OPTIONS = RISK_LEVEL_OPTIONS.map((opt) => ({
  key: opt.value,
  label: opt.label,
}))

export function RecipesPage({ config }: RecipesPageProps) {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
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
        limit: PAGE_SIZE,
        offset,
      })
      setRecipes(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载配方失败')
    } finally {
      setLoading(false)
    }
  }, [config, approvalFilter, executorFilter, offset])

  useEffect(() => {
    void fetchRecipes()
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
        setFormError('名称为必填项')
        return
      }

      // Validate config JSON if provided
      let parsedConfig: Record<string, unknown> | undefined
      if (formConfig.trim()) {
        try {
          parsedConfig = JSON.parse(formConfig.trim())
        } catch {
          setFormError('配置必须是有效的 JSON')
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
        setFormError(err instanceof Error ? err.message : '创建配方失败')
      } finally {
        setFormSubmitting(false)
      }
    },
    [config, formName, formExecutor, formConfig, formRiskLevel, fetchRecipes],
  )

  return (
    <div
      data-testid="page-recipes"
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
          采集配方
        </h2>
        <Button onClick={() => setShowForm(true)} data-testid="new-recipe-button">
          新建配方
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
        配方生命周期：待审批 → 已批准 → 已废弃。只有已批准的配方才能用于调度计划。
      </p>

      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-4)',
          flexWrap: 'wrap',
          flexShrink: 0,
          alignItems: 'flex-end',
        }}
      >
        <div style={{ flex: '1 1 200px', minWidth: '200px' }}>
          <Input
            id="recipe-search"
            placeholder="按名称或执行器搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="input-recipe-search"
          />
        </div>
        <Select
          data-testid="select-approval-filter"
          options={APPROVAL_FILTER_OPTIONS}
          value={approvalFilter}
          onChange={(val) => {
            setApprovalFilter(val)
            setOffset(0)
          }}
        />
        <Select
          data-testid="select-executor-filter"
          options={EXECUTOR_FILTER_OPTIONS}
          value={executorFilter}
          onChange={(val) => {
            setExecutorFilter(val)
            setOffset(0)
          }}
        />
      </div>

      {/* Create recipe form */}
      {showForm && (
        <div
          data-testid="create-recipe-panel"
          style={{
            marginBottom: 'var(--space-4)',
            padding: 'var(--space-4)',
            backgroundColor: 'var(--color-bg-content)',
            borderRadius: 'var(--radius-lg)',
            border: 'var(--border-default)',
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
            创建新配方
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                htmlFor="recipe-name"
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                名称
              </label>
              <Input
                id="recipe-name"
                placeholder="例如 TechNews Scraper"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                data-testid="input-recipe-name"
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                执行器
              </label>
              <Select
                id="recipe-executor"
                data-testid="select-recipe-executor"
                options={EXECUTOR_FORM_OPTIONS}
                value={formExecutor}
                onChange={setFormExecutor}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                htmlFor="recipe-config"
                style={{
                  fontFamily: 'var(--font-family)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                配置 (JSON)
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
                  backgroundColor: 'var(--color-bg-content)',
                  outline: 'none',
                  resize: 'vertical',
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label
                style={{
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  color: 'var(--color-text-body)',
                }}
              >
                风险级别
              </label>
              <Select
                id="recipe-risk"
                data-testid="select-recipe-risk"
                options={RISK_FORM_OPTIONS}
                value={formRiskLevel}
                onChange={setFormRiskLevel}
              />
            </div>

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
                htmlType="submit"
                disabled={formSubmitting}
                data-testid="submit-create-recipe"
              >
                {formSubmitting ? '创建中...' : '创建配方'}
              </Button>
              <Button
                type="default"
                onClick={() => {
                  setShowForm(false)
                  setFormError('')
                }}
                data-testid="cancel-create-recipe"
              >
                取消
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
            color: 'var(--color-text-body)',
            fontSize: 'var(--font-size-sm)',
            flexShrink: 0,
          }}
        >
          加载配方中...
        </p>
      )}

      {/* Error state */}
      {!loading && error && (
        <p
          data-testid="recipes-error"
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
          data-testid="recipes-empty"
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
            未找到配方
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)' }}>
            {search || approvalFilter || executorFilter
              ? '请尝试调整筛选条件。'
              : '点击"新建配方"来创建第一个配方。'}
          </p>
        </div>
      )}

      {/* Recipe table */}
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
                  borderBottom: 'var(--border-default)',
                  backgroundColor: 'var(--color-bg-content)',
                }}
              >
                {['名称', '执行器', '审批状态', '风险', '版本', '创建时间', '操作'].map(
                  (header) => (
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
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.map((recipe) => (
                <RecipeRow
                  key={recipe.id}
                  recipe={recipe}
                  config={config}
                  onChanged={() => void fetchRecipes()}
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
