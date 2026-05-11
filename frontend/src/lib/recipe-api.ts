import type { ApiConfig } from '../types/api'
import type {
  CreateRecipeRequest,
  Recipe,
  RecipeListResponse,
  UpdateRecipeRequest,
} from '../types/recipe'
import { apiRequest } from './api-client'

/** Fetch the list of recipes with pagination and optional filters. */
export function listRecipes(
  config: ApiConfig,
  params?: {
    approval_status?: string
    executor?: string
    limit?: number
    offset?: number
  },
): Promise<RecipeListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.approval_status)
    searchParams.set('approval_status', params.approval_status)
  if (params?.executor) searchParams.set('executor', params.executor)
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  const query = searchParams.toString()
  const path = query ? `/recipes?${query}` : '/recipes'
  return apiRequest<RecipeListResponse>(config, path)
}

/** Create a new recipe. */
export function createRecipe(
  config: ApiConfig,
  data: CreateRecipeRequest,
): Promise<Recipe> {
  return apiRequest<Recipe>(config, '/recipes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

/** Approve a pending recipe. */
export function approveRecipe(config: ApiConfig, recipeId: string): Promise<Recipe> {
  return apiRequest<Recipe>(config, `/recipes/${recipeId}/approve`, {
    method: 'POST',
  })
}

/** Reject a pending recipe. */
export function rejectRecipe(config: ApiConfig, recipeId: string): Promise<Recipe> {
  return apiRequest<Recipe>(config, `/recipes/${recipeId}/reject`, {
    method: 'POST',
  })
}

/** Resubmit a rejected recipe. */
export function resubmitRecipe(config: ApiConfig, recipeId: string): Promise<Recipe> {
  return apiRequest<Recipe>(config, `/recipes/${recipeId}/resubmit`, {
    method: 'POST',
  })
}

/** Deprecate an approved recipe. */
export function deprecateRecipe(config: ApiConfig, recipeId: string): Promise<Recipe> {
  return apiRequest<Recipe>(config, `/recipes/${recipeId}/deprecate`, {
    method: 'POST',
  })
}

/** Update editable fields on a recipe. */
export function updateRecipe(
  config: ApiConfig,
  recipeId: string,
  data: UpdateRecipeRequest,
): Promise<Recipe> {
  return apiRequest<Recipe>(config, `/recipes/${recipeId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
