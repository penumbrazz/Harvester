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

/** Request payload for creating a new recipe. */
export interface CreateRecipeRequest {
  name: string
  executor: string
  config?: Record<string, unknown> | null
  risk_level?: string
  auth_profile?: Record<string, unknown> | null
}

/** All valid recipe approval statuses. */
export type RecipeApprovalStatus = 'pending' | 'approved' | 'rejected' | 'deprecated'

/** Human-readable labels for recipe approval statuses. */
export const APPROVAL_STATUS_LABELS: Record<RecipeApprovalStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  deprecated: 'Deprecated',
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
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
] as const
