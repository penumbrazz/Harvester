import { useCallback, useState } from 'react'

import type { ApiConfig } from '../../../types/api'
import type {
  Recipe,
  RecipeApprovalStatus,
  UpdateRecipeRequest,
} from '../../../types/recipe'
import {
  APPROVAL_STATUS_LABELS,
  APPROVAL_STATUS_VARIANTS,
  EXECUTOR_OPTIONS,
  RECIPE_ACTIONS,
  RISK_LEVEL_OPTIONS,
} from '../../../types/recipe'
import { Button } from '../../../components/ui/button'
import { ConfirmDialog } from '../../../components/ui/confirm-dialog'
import { Input } from '../../../components/ui/input'
import { Select } from '../../../components/ui/select'
import { StatusPill } from '../../../components/ui/status-pill'
import {
  approveRecipe,
  deprecateRecipe,
  rejectRecipe,
  resubmitRecipe,
  updateRecipe,
} from '../../../lib/recipe-api'
import { formatDate } from '../../../lib/format'
import { cellStyle } from '../../../lib/table-styles'

interface RecipeRowProps {
  recipe: Recipe
  config: ApiConfig
  onChanged: () => void
}

const ACTION_LABELS: Record<string, string> = {
  edit: '编辑',
  approve: '批准',
  reject: '拒绝',
  resubmit: '重新提交',
  deprecate: '废弃',
}

const DANGEROUS_ACTIONS = new Set(['reject', 'deprecate'])

export function RecipeRow({ recipe, config, onChanged }: RecipeRowProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [editError, setEditError] = useState('')
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [confirmAction, setConfirmAction] = useState<string | null>(null)

  const [editName, setEditName] = useState(recipe.name)
  const [editExecutor, setEditExecutor] = useState(recipe.executor)
  const [editRiskLevel, setEditRiskLevel] = useState(recipe.risk_level)

  const status = recipe.approval_status as RecipeApprovalStatus
  const allowedActions = RECIPE_ACTIONS[status] || []

  const handleAction = useCallback(
    async (action: string) => {
      setLoading(true)
      setError('')
      try {
        const apiCall: Record<string, (c: ApiConfig, id: string) => Promise<Recipe>> = {
          approve: approveRecipe,
          reject: rejectRecipe,
          resubmit: resubmitRecipe,
          deprecate: deprecateRecipe,
        }
        const fn = apiCall[action]
        if (fn) {
          await fn(config, recipe.id)
        }
        onChanged()
      } catch (err) {
        setError(err instanceof Error ? err.message : '操作失败')
      } finally {
        setLoading(false)
      }
    },
    [config, recipe.id, onChanged],
  )

  const handleEditSubmit = useCallback(async () => {
    setEditSubmitting(true)
    setEditError('')
    try {
      const data: UpdateRecipeRequest = {}
      if (editName !== recipe.name) data.name = editName
      if (editExecutor !== recipe.executor) data.executor = editExecutor
      if (editRiskLevel !== recipe.risk_level) data.risk_level = editRiskLevel

      if (Object.keys(data).length > 0) {
        await updateRecipe(config, recipe.id, data)
      }
      setEditing(false)
      onChanged()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setEditSubmitting(false)
    }
  }, [config, recipe, editName, editExecutor, editRiskLevel, onChanged])

  const startEdit = useCallback(() => {
    setEditName(recipe.name)
    setEditExecutor(recipe.executor)
    setEditRiskLevel(recipe.risk_level)
    setEditError('')
    setEditing(true)
  }, [recipe])

  const handleConfirmOk = useCallback(() => {
    if (confirmAction) {
      setConfirmAction(null)
      void handleAction(confirmAction)
    }
  }, [confirmAction, handleAction])

  if (editing) {
    return (
      <tr data-testid={`recipe-edit-row-${recipe.id}`}>
        <td colSpan={7}>
          <div
            style={{
              padding: 'var(--space-3)',
              backgroundColor: 'var(--color-warm-white)',
            }}
          >
            <div
              style={{
                display: 'flex',
                gap: 'var(--space-3)',
                flexWrap: 'wrap',
                alignItems: 'flex-end',
              }}
            >
              <Input
                label="名称"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                data-testid="edit-recipe-name"
              />
              <Select
                label="执行器"
                value={editExecutor}
                onChange={(e) => setEditExecutor(e.target.value)}
                data-testid="edit-recipe-executor"
              >
                {EXECUTOR_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
              <Select
                label="风险级别"
                value={editRiskLevel}
                onChange={(e) => setEditRiskLevel(e.target.value)}
                data-testid="edit-recipe-risk"
              >
                {RISK_LEVEL_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
              <Button
                onClick={() => void handleEditSubmit()}
                disabled={editSubmitting}
                data-testid="edit-recipe-save"
              >
                {editSubmitting ? '保存中...' : '保存'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => setEditing(false)}
                disabled={editSubmitting}
                data-testid="edit-recipe-cancel"
              >
                取消
              </Button>
            </div>
            {editError && (
              <p
                data-testid="edit-recipe-error"
                style={{
                  color: 'var(--color-orange)',
                  fontSize: 'var(--font-size-xs)',
                  margin: 'var(--space-2) 0 0',
                }}
              >
                {editError}
              </p>
            )}
          </div>
        </td>
      </tr>
    )
  }

  return (
    <>
      <tr data-testid={`recipe-row-${recipe.id}`}>
        <td style={cellStyle}>
          <span style={{ fontWeight: 600, color: 'var(--color-primary-text)' }}>
            {recipe.name}
          </span>
        </td>
        <td style={cellStyle}>
          <span style={{ textTransform: 'uppercase', fontSize: 'var(--font-size-xs)' }}>
            {recipe.executor}
          </span>
        </td>
        <td style={cellStyle}>
          <StatusPill variant={APPROVAL_STATUS_VARIANTS[status] || 'default'}>
            {APPROVAL_STATUS_LABELS[status] || status}
          </StatusPill>
        </td>
        <td style={cellStyle}>{recipe.risk_level}</td>
        <td style={cellStyle}>{recipe.version}</td>
        <td style={cellStyle}>{formatDate(recipe.created_at)}</td>
        <td style={cellStyle}>
          <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
            {allowedActions.map((action) => (
              <Button
                key={action}
                variant={DANGEROUS_ACTIONS.has(action) ? 'ghost' : 'secondary'}
                disabled={loading}
                onClick={() => {
                  if (action === 'edit') {
                    startEdit()
                  } else if (DANGEROUS_ACTIONS.has(action)) {
                    setConfirmAction(action)
                  } else {
                    void handleAction(action)
                  }
                }}
                data-testid={`action-${action}-${recipe.id}`}
                style={{
                  padding: '4px 8px',
                  fontSize: 'var(--font-size-xs)',
                }}
              >
                {ACTION_LABELS[action]}
              </Button>
            ))}
            {error && (
              <span
                data-testid={`action-error-${recipe.id}`}
                style={{
                  color: 'var(--color-orange)',
                  fontSize: 'var(--font-size-xs)',
                }}
              >
                错误
              </span>
            )}
          </div>
        </td>
      </tr>
      <ConfirmDialog
        open={confirmAction !== null}
        title="确认操作"
        message={`确定要${confirmAction ? ACTION_LABELS[confirmAction] : ''}配方「${recipe.name}」吗？`}
        confirmLabel={confirmAction ? ACTION_LABELS[confirmAction] : '确认'}
        loading={loading}
        onConfirm={handleConfirmOk}
        onCancel={() => setConfirmAction(null)}
      />
    </>
  )
}
