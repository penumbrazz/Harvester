/** Recipe entity type matching the backend RecipeResponse. */
export interface Recipe {
  id: string
  name: string
  executor: string
  risk_level: string
  approval_status: string
  version: number
  created_at: string
  updated_at: string | null
}

/** Paginated recipe list response. */
export interface RecipeListResponse {
  items: Recipe[]
  total: number
  limit: number
  offset: number
}

/** Request payload for creating a new recipe. */
export interface CreateRecipeRequest {
  name: string
  executor: string
  config?: Record<string, unknown> | null
  risk_level?: string
  auth_profile?: Record<string, unknown> | null
}

/** Request payload for updating an existing recipe. */
export interface UpdateRecipeRequest {
  name?: string
  executor?: string
  risk_level?: string
}

/** All valid recipe approval statuses. */
export type RecipeApprovalStatus = 'pending' | 'approved' | 'rejected' | 'deprecated'

/** Human-readable labels for recipe approval statuses. */
export const APPROVAL_STATUS_LABELS: Record<RecipeApprovalStatus, string> = {
  pending: '待审批',
  approved: '已批准',
  rejected: '已拒绝',
  deprecated: '已废弃',
}

/** StatusPill variant mapping for recipe approval statuses. */
export const APPROVAL_STATUS_VARIANTS: Record<
  RecipeApprovalStatus,
  'success' | 'error' | 'warning' | 'info' | 'default'
> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'error',
  deprecated: 'default',
}

/** Approved executor options. */
export const EXECUTOR_OPTIONS = [
  { value: 'firecrawl', label: 'Firecrawl' },
  { value: 'http_fetch', label: 'HTTP Fetch' },
  { value: 'rss_parse', label: 'RSS Parse' },
  { value: 'static', label: 'Static' },
] as const

/** Risk level options. */
export const RISK_LEVEL_OPTIONS = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
] as const

/** Mapping from recipe approval status to allowed management actions. */
export const RECIPE_ACTIONS: Record<RecipeApprovalStatus, string[]> = {
  pending: ['approve', 'reject', 'edit'],
  approved: ['deprecate'],
  rejected: ['resubmit', 'edit'],
  deprecated: [],
}
