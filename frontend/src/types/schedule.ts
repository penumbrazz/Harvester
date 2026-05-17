/** Watch schedule entity type matching the backend ScheduleResponse. */
export interface Schedule {
  id: string
  schedule_key: string
  source_id: string
  source_name: string | null
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

/** Paginated schedule list response. */
export interface ScheduleListResponse {
  items: Schedule[]
  total: number
  limit: number
  offset: number
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
  { value: 'paused', label: '已暂停' },
  { value: 'disabled', label: '已停用' },
] as const

/** All valid schedule statuses. */
export type ScheduleStatus = 'active' | 'paused' | 'disabled'

/** Request payload for updating a schedule. */
export interface UpdateScheduleRequest {
  interval_seconds?: number
  priority?: number
  lane?: string | null
}

/** Human-readable labels for schedule statuses. */
export const SCHEDULE_STATUS_LABELS: Record<ScheduleStatus, string> = {
  active: '活跃',
  paused: '已暂停',
  disabled: '已停用',
}

/** StatusPill variant mapping for schedule statuses. */
export const SCHEDULE_STATUS_VARIANTS: Record<
  ScheduleStatus,
  'success' | 'error' | 'warning' | 'info' | 'default'
> = {
  active: 'success',
  paused: 'warning',
  disabled: 'default',
}

/** Mapping from schedule status to allowed management actions. */
export const SCHEDULE_ACTIONS: Record<ScheduleStatus, string[]> = {
  active: ['edit', 'pause', 'disable'],
  paused: ['edit', 'resume', 'disable'],
  disabled: [],
}
