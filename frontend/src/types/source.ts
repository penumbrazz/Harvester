/** Source entity type matching the backend SourceResponse. */
export interface Source {
  id: string
  name: string
  kind: string
  status: string
  url: string | null
  trust_level: string
  failure_count: number
  created_at: string
  updated_at: string
}

/** Paginated source list response. */
export interface SourceListResponse {
  items: Source[]
  total: number
  limit: number
  offset: number
}

/** Request payload for proposing a new source. */
export interface ProposeSourceRequest {
  name: string
  kind: string
  url?: string | null
  trust_level?: string
  auth_required?: boolean
}

/** Request payload for updating an existing source. */
export interface UpdateSourceRequest {
  name?: string
  url?: string | null
  trust_level?: string
}

/** All valid source statuses from the state machine. */
export type SourceStatus = 'candidate' | 'testing' | 'watched' | 'paused' | 'archived'

/** Source kind options. */
export type SourceKind = 'web' | 'rss' | 'api' | 'file'

/** Mapping from source status to the allowed actions. */
export const SOURCE_ACTIONS: Record<SourceStatus, string[]> = {
  candidate: ['edit', 'promote', 'archive'],
  testing: ['edit', 'promote', 'archive'],
  watched: ['edit', 'pause', 'archive'],
  paused: ['edit', 'resume', 'archive'],
  archived: [],
}

/** Human-readable labels for source statuses. */
export const STATUS_LABELS: Record<SourceStatus, string> = {
  candidate: '候选',
  testing: '测试中',
  watched: '监控中',
  paused: '已暂停',
  archived: '已归档',
}

/** StatusPill variant mapping for source statuses. */
export const STATUS_VARIANTS: Record<
  SourceStatus,
  'success' | 'error' | 'warning' | 'info' | 'default'
> = {
  candidate: 'default',
  testing: 'info',
  watched: 'success',
  paused: 'warning',
  archived: 'default',
}
