import type { ApiConfig } from '../types/api'
import type { CreateRecipeRequest, Recipe } from '../types/recipe'
import { apiRequest } from './api-client'

/** Fetch the list of recipes, optionally filtered. */
export function listRecipes(
  config: ApiConfig,
  filters?: { approval_status?: string; executor?: string },
): Promise<Recipe[]> {
  const params = new URLSearchParams()
  if (filters?.approval_status) params.set('approval_status', filters.approval_status)
  if (filters?.executor) params.set('executor', filters.executor)
  const query = params.toString()
  const path = query ? `/recipes?${query}` : '/recipes'
  return apiRequest<Recipe[]>(config, path)
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
