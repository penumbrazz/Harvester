import type { ApiConfig } from '../types/api'
import type { CreateScheduleRequest, Schedule, ScheduleListResponse } from '../types/schedule'
import { apiRequest } from './api-client'

/** Fetch the list of schedules with pagination and optional filters. */
export function listSchedules(
  config: ApiConfig,
  params?: { status?: string; source_id?: string; recipe_id?: string; limit?: number; offset?: number },
): Promise<ScheduleListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.source_id) searchParams.set('source_id', params.source_id)
  if (params?.recipe_id) searchParams.set('recipe_id', params.recipe_id)
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  const query = searchParams.toString()
  const path = query ? `/schedules?${query}` : '/schedules'
  return apiRequest<ScheduleListResponse>(config, path)
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
