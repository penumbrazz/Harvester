/** Watch schedule entity type matching the backend ScheduleResponse. */
export interface Schedule {
  id: string
  schedule_key: string
  source_id: string
  topic_watch_id: string | null
  recipe_id: string
  status: string
  interval_seconds: number
  next_run_at: string
  last_enqueued_at: string | null
  priority: number
  lane: string | null
  created_at: string
}

/** Request payload for creating a new schedule. */
export interface CreateScheduleRequest {
  source_id: string
  topic_watch_id?: string | null
  recipe_id: string
  interval_seconds: number
  priority?: number
  lane?: string | null
}

/** Schedule status options. */
export const SCHEDULE_STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '活跃' },
] as const
