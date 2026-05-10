import type { ApiConfig } from '../types/api'
import type { CreateScheduleRequest, Schedule } from '../types/schedule'
import { apiRequest } from './api-client'

/** Fetch the list of schedules, optionally filtered. */
export function listSchedules(
  config: ApiConfig,
  filters?: { status?: string; source_id?: string; recipe_id?: string },
): Promise<Schedule[]> {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.source_id) params.set('source_id', filters.source_id)
  if (filters?.recipe_id) params.set('recipe_id', filters.recipe_id)
  const query = params.toString()
  const path = query ? `/schedules?${query}` : '/schedules'
  return apiRequest<Schedule[]>(config, path)
}

/** Create a new watch schedule. */
export function createSchedule(
  config: ApiConfig,
  data: CreateScheduleRequest,
): Promise<Schedule> {
  return apiRequest<Schedule>(config, '/schedules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
